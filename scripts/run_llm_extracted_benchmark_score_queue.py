#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import concurrent.futures
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    DEFAULT_QUEUE_ROOT,
    DEFAULT_RUN_ROOT,
    REPO_ROOT as LIB_REPO_ROOT,
    file_lock,
    json_default,
    load_json,
    parse_lettered_option_blob,
    run_dir,
    spec_by_key,
    write_json,
)
from run_external_benchmark_score_queue import PersistentJudge  # noqa: E402
from trace_benchmark_answer_parsing import parse_binary_score as _strict_parse_binary_score  # noqa: E402
from trace_final25_contract import (  # noqa: E402
    LLM_EXTRACT_SCORE_KEYS,
    OPTION_TEXT_REQUIRED_KEYS,
    SOURCE_ROW_EXCLUSIONS,
)


DEFAULT_BENCHMARKS = (
    "blink",
    "chartqapro",
    "game_qa_lite",
    "countbenchqa",
    "erqa",
    "vstarbench",
    "cvbench_3d",
)
HIGH_RISK_DIRECT_BENCHMARKS = (
    "puzzlevqa",
    "treebench",
    "phyx_mini_mc",
    "physics",
    "mmmu_pro_vision",
    "visiongraph_q3",
    "mmstar",
)
DEFAULT_MODELS = (
    ("qwen25vl7b-base", "Qwen/Qwen2.5-VL-7B-Instruct"),
    (
        "trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500",
        "/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500",
    ),
)
LETTERS = "ABCDEFGHIJK"
FIXED_OPTION_CONTRACTS = {
    "phyx_mini_mc": "ABCD",
    "visualpuzzles": "ABCD",
}
VARIABLE_SOURCE_OPTION_CONTRACTS = {
    "erqa": (2, 4),
    "mmstar": (2, 4),
}
SOURCE_OPTION_OVERRIDES = {
    # The official ERQA prompt has empty A/D markers but valid B/C choices.
    # Preserve exactly the two choices that were visible during generation.
    ("erqa", "271"): {"B": "No", "C": "Yes"},
}
REQUIRED_CHOICE_TEXT_CONTRACTS = set(OPTION_TEXT_REQUIRED_KEYS)


def _load_prediction_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_excel(path)


def _prediction_path(run_root: Path, benchmark: str, model_slug: str) -> Path:
    spec = spec_by_key(benchmark)
    output_dir = run_dir(spec, model_slug, run_root)
    candidates = [
        output_dir / f"{spec.alias}_predictions.xlsx",
        output_dir / f"{spec.alias}_predictions_table.xlsx",
    ]
    for path in candidates:
        if path.exists():
            return path
    matches = sorted(output_dir.glob("*_predictions.xlsx"))
    matches = [p for p in matches if "extracted" not in p.name and "result" not in p.name and "detail" not in p.name]
    if matches:
        return matches[0]
    raise FileNotFoundError(f"No prediction table found under {output_dir}")


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def _row_index(row: dict[str, Any], fallback: int) -> str:
    value = row.get("index")
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return str(fallback)
    return _clean_cell(value)


def _option_columns(row: dict[str, Any], valid_letters: Iterable[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for letter in valid_letters:
        value = _clean_cell(row.get(letter))
        if value:
            out[letter] = value
    return out


def _embedded_option_columns(question: str) -> dict[str, str]:
    options: dict[str, str] = {}
    lines = str(question or "").splitlines()
    for i, line in enumerate(lines):
        match = re.match(r"^\s*([A-K])\s*[\.\)]\s*(.+?)\s*$", line)
        if not match:
            continue
        letter, text = match.groups()
        # Some datasets wrap long options onto following indented lines. Keep
        # this conservative so normal prompt text is not pulled into a choice.
        extra = []
        for nxt in lines[i + 1 :]:
            if re.match(r"^\s*[A-K]\s*[\.\)]\s+", nxt):
                break
            if not nxt.startswith((" ", "\t")):
                break
            extra.append(nxt.strip())
        options[letter] = " ".join([text.strip(), *extra]).strip()
    return options


def _inline_option_columns(question: str) -> dict[str, str]:
    text = str(question or "")
    if not re.search(r"\bOPTION(?:S)?\s*:", text, flags=re.I):
        return {}
    tail = re.split(r"\bOPTION(?:S)?\s*:", text, maxsplit=1, flags=re.I)[-1]
    out: dict[str, str] = {}
    for match in re.finditer(r"\b([A-K])\s*:\s*(.*?)(?=\s+\b[A-K]\s*:|$)", tail, flags=re.S):
        letter, value = match.groups()
        value = re.sub(r"\s+", " ", value).strip()
        if value:
            out[letter] = value
    return out


def _inline_dot_option_columns(question: str) -> dict[str, str]:
    """Parse inline ``Choices: A. ... B. ...`` option blocks."""

    text = str(question or "")
    marker = re.search(r"\b(?:choices|options)\s*:\s*", text, flags=re.I)
    if marker is None:
        return {}
    tail = text[marker.end() :]
    matches = list(re.finditer(r"(?<!\w)([A-K])\s*[\.)]\s+", tail))
    out: dict[str, str] = {}
    for pos, match in enumerate(matches):
        end = matches[pos + 1].start() if pos + 1 < len(matches) else len(tail)
        value = re.sub(r"\s+", " ", tail[match.end() : end]).strip()
        if value:
            out[match.group(1)] = value
    return out


def _ordered_fixed_option_columns(question: str, letters: str = "ABCD") -> dict[str, str]:
    """Parse an ordered inline option block with a known label contract.

    ERQA includes pointing rows such as ``A. A. B. B. C. C. D. D.``.
    Parsing all letter-period tokens as markers loses the option values, while
    the benchmark's fixed ordered A-D layout makes the boundaries unambiguous.
    """

    text = str(question or "")
    marker = re.search(r"\b(?:choices|options)\s*[:.]\s*", text, flags=re.I)
    if marker is not None:
        tail = text[marker.end() :]
    else:
        first = re.search(r"(?<!\w)A\s*[\.):]\s*", text)
        if first is None:
            return {}
        tail = text[first.start() :]
    parts = []
    for pos, letter in enumerate(letters):
        next_letter = letters[pos + 1] if pos + 1 < len(letters) else None
        if next_letter is None:
            pattern = rf"^{re.escape(letter)}\s*[\.):]\s*(.*?)(?=\s+Please\s+answer\b|$)"
        else:
            pattern = (
                rf"^{re.escape(letter)}\s*[\.):]\s*(.*?)\s+"
                rf"(?={re.escape(next_letter)}\s*[\.):]\s+)"
            )
        match = re.search(pattern, tail, flags=re.I | re.S)
        if match is None:
            return {}
        value = re.sub(r"\s+", " ", match.group(1)).strip().rstrip(".").strip()
        if not value:
            return {}
        parts.append((letter, value))
        consumed = match.end()
        tail = tail[consumed:].lstrip()
    return dict(parts)


def _source_option_override(benchmark: str, row: dict[str, Any]) -> dict[str, str]:
    return dict(SOURCE_OPTION_OVERRIDES.get((benchmark, _row_index(row, -1)), {}))


def _ordered_source_option_columns(question: str) -> dict[str, str]:
    for letters in ("ABCD", "ABC", "AB"):
        options = _ordered_fixed_option_columns(question, letters)
        if options:
            return options
    return {}


def _literal_options(row: dict[str, Any]) -> dict[str, str]:
    raw = _clean_cell(row.get("options") or row.get("multi-choice options"))
    if not raw:
        return {}
    # VisualPuzzles serializes some option arrays in NumPy display form, e.g.
    # ``['32' '35' '37' '40']``. Python accepts adjacent string literals by
    # concatenating them, so detect this representation before literal_eval.
    quoted = re.findall(r"(['\"])(.*?)\1", raw)
    if raw.lstrip().startswith(("[", "(")) and len(quoted) > 1:
        values = [_clean_cell(value) for _, value in quoted]
        return {LETTERS[i]: value for i, value in enumerate(values) if i < len(LETTERS) and value}
    try:
        parsed = ast.literal_eval(raw)
    except Exception:
        parsed = None
    if isinstance(parsed, (list, tuple)):
        return {LETTERS[i]: _clean_cell(value) for i, value in enumerate(parsed) if i < len(LETTERS)}
    if isinstance(parsed, dict):
        return {
            str(letter).strip().upper(): _clean_cell(value)
            for letter, value in parsed.items()
            if str(letter).strip().upper() in LETTERS and _clean_cell(value)
        }
    return parse_lettered_option_blob(raw)


def _valid_letters_for(benchmark: str, row: dict[str, Any]) -> str:
    if benchmark in FIXED_OPTION_CONTRACTS:
        return FIXED_OPTION_CONTRACTS[benchmark]
    override = _source_option_override(benchmark, row)
    if override:
        return "".join(letter for letter in LETTERS if letter in override)
    if benchmark == "erqa":
        ordered = _ordered_source_option_columns(_question_for(benchmark, row))
        if ordered:
            return "".join(ordered)

    question = _question_for(benchmark, row)
    candidates = (
        "".join(_option_columns(row, LETTERS).keys()),
        "".join(_literal_options(row).keys()),
        "".join(_inline_option_columns(question).keys()),
        "".join(_inline_dot_option_columns(question).keys()),
        "".join(_embedded_option_columns(question).keys()),
    )
    parsed = next((candidate for candidate in candidates if candidate), "")
    answer = _clean_cell(row.get("answer")).upper()
    if parsed:
        return "".join(letter for letter in LETTERS if letter in parsed)
    if benchmark in REQUIRED_CHOICE_TEXT_CONTRACTS:
        return ""
    if len(answer) == 1 and answer in LETTERS:
        return LETTERS[: max(LETTERS.index(answer) + 1, 4)]
    return "ABCDEFG"


def _question_for(benchmark: str, row: dict[str, Any]) -> str:
    question = _clean_cell(row.get("question"))
    if benchmark == "cvbench_3d" and _clean_cell(row.get("prompt")):
        question = _clean_cell(row.get("prompt"))
    return question


def _answer_kind(benchmark: str, row: dict[str, Any]) -> str:
    answer = _clean_cell(row.get("answer"))
    if benchmark in {"countbenchqa", "countqa"}:
        return "number"
    if benchmark in {"chartqapro", "evochart"}:
        return "short"
    if benchmark == "game_qa_lite":
        # Game-QA-Lite mixes MCQ, numeric, coordinate, and short-text answers.
        if re.fullmatch(r"[A-H]", answer.strip(), flags=re.I):
            return "option"
        if re.fullmatch(r"-?\d+(?:\.\d+)?", answer.strip()):
            return "number"
        return "short"
    if benchmark == "puzzlevqa":
        return "option_value"
    if benchmark == "physics":
        return "judge_binary"
    if benchmark == "visiongraph_q3":
        return "short"
    if benchmark == "vlmbias":
        return "braced"
    return "option"


def _build_prompt(item: dict[str, Any]) -> str:
    kind = item["answer_kind"]
    question = item["question"]
    response = item["prediction"]
    if kind == "option":
        options = item.get("options") or {}
        option_text = "\n".join(f"{letter}. {text}" for letter, text in options.items())
        if not option_text:
            option_text = f"Valid option letters: {', '.join(item['valid_letters'])}"
        return (
            "You are extracting the final answer from a model response for a multiple-choice visual reasoning benchmark.\n"
            "Use the question and choices to infer which option the model selected. Do not judge whether the model is correct; only extract its selected option.\n"
            "If the model clearly selects an option by letter or by matching the option text, return that option letter.\n"
            "If it does not select any option, return Z.\n\n"
            f"Question:\n{question}\n\n"
            f"Choices:\n{option_text}\n\n"
            f"Model response:\n{response}\n\n"
            "Return exactly one JSON object: {\"answer\": \"A\"}\n"
            f"The answer must be one of: {', '.join(item['valid_letters'])}, Z."
        )
    if kind == "option_value":
        options = item.get("options") or {}
        option_text = "\n".join(f"{letter}. {text}" for letter, text in options.items())
        return (
            "You are extracting the final selected option from a multiple-choice visual reasoning response.\n"
            "Use the question, choices, and model response to infer which option the model selected. Do not judge correctness.\n"
            "Return the selected option letter. If the response gives only the option value, map it back to the matching option letter.\n"
            "If no option is selected, return Z.\n\n"
            f"Question:\n{question}\n\n"
            f"Choices:\n{option_text}\n\n"
            f"Model response:\n{response}\n\n"
            "Return exactly one JSON object: {\"answer\": \"A\"}\n"
            f"The answer must be one of: {', '.join(item['valid_letters'])}, Z."
        )
    if kind == "number":
        return (
            "You are extracting the final numeric answer from a visual counting benchmark response.\n"
            "Do not judge correctness. Extract only the count stated as the final answer.\n"
            "If no count is selected, return an empty string.\n\n"
            f"Question:\n{question}\n\n"
            f"Model response:\n{response}\n\n"
            "Return exactly one JSON object: {\"answer\": \"<integer>\"}."
        )
    if kind == "judge_binary":
        return (
            "You are judging whether a model response is correct for a physics problem.\n"
            "Compare the model response against the reference answer. Accept mathematically equivalent formulas, units, and approximations when they mean the same thing.\n"
            "Do not require the same wording. Mark incorrect if the final answer is missing, contradicts the reference, or only solves a different subproblem.\n\n"
            f"Question:\n{question}\n\n"
            f"Reference answer:\n{item['answer']}\n\n"
            f"Model response:\n{response}\n\n"
            "Return exactly one JSON object: {\"score\": 1, \"answer\": \"<model final answer>\"} where score is 1 for correct and 0 for incorrect."
        )
    if kind == "braced":
        return (
            "You are extracting the final answer from a visual reasoning benchmark response.\n"
            "Do not judge correctness. Extract only the model's final answer value.\n"
            "The benchmark asks for answers in curly brackets such as {9}, {Yes}, or {No}; if a braced answer is present, use the content inside the final braces.\n"
            "If no final answer is selected, return an empty string.\n\n"
            f"Question:\n{question}\n\n"
            f"Model response:\n{response}\n\n"
            "Return exactly one JSON object: {\"answer\": \"<final answer>\"}."
        )
    return (
        "You are extracting the final short answer from a visual question answering response.\n"
        "Do not judge correctness. Extract only the final answer, with no explanation.\n"
        "If the response uses a boxed final answer, extract the boxed content. Preserve coordinate/list/text answers.\n"
        "For plain numbers, remove percent signs, currency symbols, and commas. For choices, return only the chosen letter or value.\n"
        "If the response says the question is unanswerable, return Unanswerable.\n\n"
        f"Question:\n{question}\n\n"
        f"Model response:\n{response}\n\n"
        "Return exactly one JSON object: {\"answer\": \"<final answer>\"}."
    )


def _validate_required_choice_contract(item: dict[str, Any]) -> None:
    benchmark = str(item["benchmark"])
    if benchmark not in REQUIRED_CHOICE_TEXT_CONTRACTS:
        return

    index = str(item["index"])
    options = item.get("options") or {}
    if not options:
        raise ValueError(f"{benchmark} index={index} has no parseable option text")
    expected = set(item.get("valid_letters") or [])
    observed = set(options)
    if benchmark in FIXED_OPTION_CONTRACTS and observed != expected:
        raise ValueError(
            f"{benchmark} index={index} violates fixed option contract "
            f"{''.join(item.get('valid_letters') or [])}: parsed={sorted(observed)}"
        )
    if benchmark in VARIABLE_SOURCE_OPTION_CONTRACTS:
        minimum, maximum = VARIABLE_SOURCE_OPTION_CONTRACTS[benchmark]
        observed_labels = "".join(letter for letter in LETTERS if letter in observed)
        if not minimum <= len(observed_labels) <= maximum:
            raise ValueError(
                f"{benchmark} index={index} violates variable source option contract "
                f"with {minimum}-{maximum} choices: parsed={sorted(observed)}"
            )

    answer_kind = item["answer_kind"]
    if answer_kind == "option":
        gt = _normalize_option(item["answer"], item["valid_letters"])
    elif answer_kind == "option_value":
        gt = _option_value_to_letter(item)
    else:
        raise ValueError(f"{benchmark} index={index} unexpectedly uses answer kind {answer_kind!r}")
    if not gt or gt == "Z" or gt not in options:
        raise ValueError(
            f"{benchmark} index={index} is missing ground-truth choice "
            f"{item['answer']!r} from parsed options {sorted(options)}"
        )


def _source_row_exclusion_reason(
    benchmark: str,
    index: str,
    answer: str,
    options: dict[str, str],
) -> str:
    reason = SOURCE_ROW_EXCLUSIONS.get(benchmark, {}).get(index, "")
    if not reason:
        return ""
    gold = _clean_cell(answer).upper()
    if gold in options:
        return ""
    if benchmark == "mmstar" and gold != "A":
        raise ValueError(
            f"{benchmark} index={index} exclusion contract drifted: "
            f"expected missing gold A, found {answer!r}"
        )
    return reason


def _build_items(args: argparse.Namespace) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for benchmark in args.benchmarks:
        for model_slug, model_path in args.model_entries:
            pred_path = _prediction_path(args.run_root, benchmark, model_slug)
            df = _load_prediction_table(pred_path)
            for ordinal, row_obj in enumerate(df.to_dict(orient="records")):
                row = dict(row_obj)
                index = _row_index(row, ordinal)
                valid_letters = _valid_letters_for(benchmark, row)
                options = _option_columns(row, valid_letters)
                if not options:
                    options = _literal_options(row)
                if not options:
                    options = _source_option_override(benchmark, row)
                if not options and benchmark == "erqa":
                    options = _ordered_source_option_columns(_question_for(benchmark, row))
                if not options:
                    options = _inline_option_columns(_question_for(benchmark, row))
                if not options:
                    options = _inline_dot_option_columns(_question_for(benchmark, row))
                if not options:
                    options = _embedded_option_columns(_question_for(benchmark, row))
                answer_kind = _answer_kind(benchmark, row)
                exclusion_reason = _source_row_exclusion_reason(
                    benchmark,
                    index,
                    _clean_cell(row.get("answer")),
                    options,
                )
                if exclusion_reason:
                    exclusions.append(
                        {
                            "benchmark": benchmark,
                            "model_slug": model_slug,
                            "index": index,
                            "reason": exclusion_reason,
                        }
                    )
                    continue
                item = {
                    "job_id": f"{benchmark}__{model_slug}__{index}",
                    "benchmark": benchmark,
                    "model_slug": model_slug,
                    "model_path": model_path,
                    "index": index,
                    "ordinal": ordinal,
                    "question": _question_for(benchmark, row),
                    "prediction": _clean_cell(row.get("prediction")),
                    "answer": _clean_cell(row.get("answer")),
                    "answer_kind": answer_kind,
                    "valid_letters": list(valid_letters),
                    "options": options,
                    "prediction_table": str(pred_path),
                }
                _validate_required_choice_contract(item)
                item["prompt"] = _build_prompt(item)
                items.append(item)
    args.source_row_exclusions = exclusions
    return items


def _safe_job_filename(job_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.=-]+", "__", job_id) + ".json"


def _done_path(args: argparse.Namespace, job_id: str) -> Path:
    return args.output_root / args.queue_name / "items" / _safe_job_filename(job_id)


def _manifest_path(args: argparse.Namespace) -> Path:
    return args.output_root / args.queue_name / "manifest.jsonl"


def write_manifest(args: argparse.Namespace, items: list[dict[str, Any]]) -> None:
    path = _manifest_path(args)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False, default=json_default) + "\n")
    write_json(
        args.output_root / args.queue_name / "manifest_summary.json",
        {
            "queue_name": args.queue_name,
            "benchmarks": args.benchmarks,
            "model_slugs": [slug for slug, _ in args.model_entries],
            "rows": len(items),
            "source_rows_excluded": len(getattr(args, "source_row_exclusions", [])),
            "source_row_exclusions": getattr(args, "source_row_exclusions", []),
            "created_at": time.time(),
        },
    )


def load_manifest(args: argparse.Namespace) -> list[dict[str, Any]]:
    path = _manifest_path(args)
    if not path.exists():
        items = _build_items(args)
        write_manifest(args, items)
        return items
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def _pid_alive(pid: Any) -> bool:
    try:
        pid_int = int(pid)
    except Exception:
        return False
    if pid_int <= 0:
        return False
    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def claim_many(args: argparse.Namespace, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queue_path = args.queue_root / f"llm_extract_{args.queue_name}.json"
    now = time.time()
    claimed: list[dict[str, Any]] = []
    lock_path = queue_path.with_suffix(queue_path.suffix + ".lock")
    with file_lock(lock_path):
        state = load_json(queue_path, {"jobs": {}})
        state_jobs = state.setdefault("jobs", {})
        for item in items:
            job_id = item["job_id"]
            done_path = _done_path(args, job_id)
            info = state_jobs.get(job_id, {})
            if done_path.exists():
                state_jobs[job_id] = {**info, "status": "done", "done_path": str(done_path), "updated_at": now}
                continue
            attempts = int(info.get("attempts") or 0)
            if info.get("status") == "failed" and attempts >= args.max_attempts:
                continue
            if info.get("status") == "running" and _pid_alive(info.get("pid")):
                continue
            if info.get("status") == "running" and now - float(info.get("updated_at", 0)) < args.stale_after_sec:
                continue
            if info.get("status") == "done":
                continue
            state_jobs[job_id] = {
                "status": "running",
                "worker": args.worker_id,
                "pid": os.getpid(),
                "updated_at": now,
                "attempts": attempts + 1,
            }
            claimed.append(item)
            if len(claimed) >= args.claim_batch_size:
                break
        write_json(queue_path, state)
    return claimed


def write_done_result(args: argparse.Namespace, item: dict[str, Any], result: dict[str, Any]) -> None:
    done_path = _done_path(args, item["job_id"])
    done_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(done_path, result)


def mark_done(args: argparse.Namespace, item: dict[str, Any], result: dict[str, Any]) -> None:
    write_done_result(args, item, result)
    done_path = _done_path(args, item["job_id"])
    queue_path = args.queue_root / f"llm_extract_{args.queue_name}.json"
    now = time.time()
    lock_path = queue_path.with_suffix(queue_path.suffix + ".lock")
    with file_lock(lock_path):
        state = load_json(queue_path, {"jobs": {}})
        state.setdefault("jobs", {})[item["job_id"]] = {
            "status": "done",
            "worker": args.worker_id,
            "pid": os.getpid(),
            "updated_at": now,
            "done_path": str(done_path),
        }
        write_json(queue_path, state)


def mark_failed(args: argparse.Namespace, item: dict[str, Any], error: str) -> None:
    queue_path = args.queue_root / f"llm_extract_{args.queue_name}.json"
    now = time.time()
    lock_path = queue_path.with_suffix(queue_path.suffix + ".lock")
    with file_lock(lock_path):
        state = load_json(queue_path, {"jobs": {}})
        previous = state.setdefault("jobs", {}).get(item["job_id"], {})
        state["jobs"][item["job_id"]] = {
            "status": "failed",
            "worker": args.worker_id,
            "pid": os.getpid(),
            "updated_at": now,
            "attempts": previous.get("attempts", 1),
            "error": error,
        }
        write_json(queue_path, state)


def _parse_json_answer(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            value = obj.get("answer", obj.get("extracted_answer", ""))
            return _clean_cell(value)
    except Exception:
        pass
    match = re.search(r"\{.*?\}", raw, flags=re.S)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                value = obj.get("answer", obj.get("extracted_answer", ""))
                return _clean_cell(value)
        except Exception:
            pass
    match = re.search(r'"?(?:answer|extracted_answer)"?\s*[:=]\s*"?([^"\n}]+)', raw, flags=re.I)
    if match:
        return match.group(1).strip()
    return raw.splitlines()[0].strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    match = re.search(r"\{.*?\}", raw, flags=re.S)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    answer = _parse_json_answer(raw)
    return {"answer": answer} if answer else {}


def _normalize_option(value: str, valid_letters: Iterable[str]) -> str:
    letters = "".join(valid_letters)
    text = str(value or "").strip().upper()
    text = text.strip("()[]{}.:;\"'`* ")
    if text in letters or text == "Z":
        return text
    match = re.search(rf"\b([{re.escape(letters)}Z])\b", text)
    return match.group(1) if match else ""


def _normalize_number(value: str) -> str:
    text = str(value or "").replace(",", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return ""
    number = float(match.group(0))
    if number.is_integer():
        return str(int(number))
    return str(number)


def _clean_short(value: str) -> str:
    text = str(value or "").strip()
    text = text.strip(" \t\r\n\"'`")
    text = re.sub(r"^(?:the\s+)?(?:final\s+)?answer\s*(?:is|=|:|：)?\s*", "", text, flags=re.I).strip()
    text = text.strip(" \t\r\n\"'`")
    while len(text) >= 2:
        changed = False
        for marker in ("**", "__", "*", "_"):
            if text.startswith(marker) and text.endswith(marker):
                text = text[len(marker): -len(marker)].strip()
                changed = True
                break
        if not changed:
            break
    return text.rstrip(".。").strip()


def _normalize_short_for_exact(value: str) -> str:
    text = _clean_short(value)
    text = re.sub(r"\\boxed\s*\{([^{}]*)\}", r"\1", text)
    text = text.replace("\\", "")
    text = text.replace("，", ",").replace("（", "(").replace("）", ")")
    text = re.sub(r"\s+", " ", text).strip().lower()
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\(\s*", "(", text)
    text = re.sub(r"\s*\)", ")", text)
    text = re.sub(r"\[\s*", "[", text)
    text = re.sub(r"\s*\]", "]", text)
    return text


def _normalize_braced_answer(value: str) -> str:
    text = str(value or "").strip()
    braced = re.findall(r"\{([^{}]+)\}", text)
    if braced:
        text = braced[-1]
    else:
        final = list(
            re.finditer(
                r"\b(?:final\s+answer|answer)\b\s*(?:is|=|:|：)?\s*(.+)",
                text,
                flags=re.I | re.S,
            )
        )
        if final:
            text = final[-1].group(1).strip().splitlines()[0].strip()
    text = _normalize_short_for_exact(text)
    try:
        from vlmeval.dataset.utils.omni_verifier import _process_digit_article

        text = _process_digit_article(text)
    except Exception:
        text = re.sub(r"^(a|an|the)\s+", "", text)
    return text.strip(" .,:;")


def normalize_extracted(item: dict[str, Any], value: str) -> str:
    kind = item["answer_kind"]
    if kind in {"option", "option_value"}:
        return _normalize_option(value, item["valid_letters"])
    if kind == "number":
        return _normalize_number(value)
    if kind == "braced":
        return _normalize_braced_answer(value)
    return _clean_short(value)


def _result_from_judge_output(item: dict[str, Any], raw: str) -> dict[str, Any]:
    obj = _parse_json_object(raw)
    parsed = _clean_cell(obj.get("answer", obj.get("extracted_answer", "")))
    normalized = normalize_extracted(item, parsed)
    out = {
        **{k: item[k] for k in ("job_id", "benchmark", "model_slug", "index", "ordinal", "answer", "answer_kind")},
        "valid_letters": item.get("valid_letters"),
        "options": item.get("options"),
        "extracted_raw": parsed,
        "extracted": normalized,
        "judge_output": raw,
        "prediction": item["prediction"],
    }
    if item["answer_kind"] == "judge_binary":
        score_value = obj.get("score", obj.get("judgement", obj.get("judgment", raw)))
        judge_score = _strict_parse_binary_score(score_value)
        if judge_score is None:
            raise ValueError(f"Malformed binary judge output for {item['job_id']}: {raw!r}")
        out["judge_score"] = judge_score
    elif item["answer_kind"] in {"option", "option_value"} and not normalized:
        raise ValueError(f"Malformed option extraction for {item['job_id']}: {raw!r}")
    return out


def run_worker(args: argparse.Namespace) -> None:
    if args.gpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    os.environ.setdefault("VLLM_ATTENTION_BACKEND", args.attention_backend)
    os.environ.setdefault("VLLM_DISABLE_COMPILE_CACHE", "1")
    items = load_manifest(args)
    judge = PersistentJudge(args)
    try:
        while True:
            batch = claim_many(args, items)
            if not batch:
                print(f"[llm-extract:done] worker={args.worker_id} no remaining jobs")
                break
            print(f"[llm-extract:claim] worker={args.worker_id} rows={len(batch)}")
            prompts = [(item["job_id"], item["prompt"]) for item in batch]
            outputs = judge.run_cached(
                output_dir=args.output_root / args.queue_name / "worker_caches",
                prompts=prompts,
                cache_name=f"{args.worker_id}.jsonl",
                max_tokens=args.judge_max_tokens,
                no_resume=False,
                desc=f"{args.worker_id} extract",
            )
            for item in batch:
                try:
                    raw = outputs[str(item["job_id"])]["judge_output"]
                    mark_done(
                        args,
                        item,
                        {
                            **_result_from_judge_output(item, raw),
                            "judge_output": raw,
                            "judge_model": args.judge_model,
                        },
                    )
                except Exception as exc:
                    mark_failed(args, item, repr(exc))
    finally:
        judge.cleanup()


def _completion_url(base: str) -> str:
    base = base.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/completions"
    if base.endswith("/v1/completions"):
        return base
    return f"{base}/v1/completions"


def _load_api_tokenizer(args: argparse.Namespace):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(args.api_tokenizer_model, trust_remote_code=True)


def _render_api_prompt(tokenizer: Any, prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]
    try:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    except TypeError:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def _call_completion_endpoint_batch(args: argparse.Namespace, endpoint: str, prompts: list[str]) -> list[str]:
    payload = {
        "model": args.api_model,
        "prompt": prompts,
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": args.judge_max_tokens,
    }
    last_error = None
    for attempt in range(args.api_max_retries):
        try:
            response = requests.post(_completion_url(endpoint), json=payload, timeout=args.api_timeout)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            outputs = [""] * len(prompts)
            for pos, choice in enumerate(choices):
                index = int(choice.get("index", pos))
                if 0 <= index < len(outputs):
                    outputs[index] = str(choice.get("text", "")).strip()
            if len(choices) != len(prompts) or any(output == "" for output in outputs):
                raise RuntimeError(f"expected {len(prompts)} completion choices, got {len(choices)}")
            return outputs
        except Exception as exc:
            last_error = exc
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"{endpoint} failed after {args.api_max_retries} attempts: {last_error}")


def _make_api_batches(
    pending: list[dict[str, Any]],
    rendered: dict[str, str],
    *,
    batch_size: int,
    max_batch_chars: int,
) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    for item in pending:
        prompt_chars = len(rendered[item["job_id"]])
        if current and (len(current) >= batch_size or current_chars + prompt_chars > max_batch_chars):
            batches.append(current)
            current = []
            current_chars = 0
        current.append(item)
        current_chars += prompt_chars
        if prompt_chars >= max_batch_chars:
            batches.append(current)
            current = []
            current_chars = 0
    if current:
        batches.append(current)
    return batches


def run_api_pool(args: argparse.Namespace) -> None:
    items = load_manifest(args)
    tokenizer = _load_api_tokenizer(args)
    pending = [item for item in items if not _done_path(args, item["job_id"]).exists()]
    print(
        "[llm-extract:api] "
        f"queue={args.queue_name} total={len(items)} pending={len(pending)} endpoints={len(args.api_bases)}"
    )
    if not pending:
        return

    rendered = {item["job_id"]: _render_api_prompt(tokenizer, item["prompt"]) for item in pending}
    batches = _make_api_batches(
        pending,
        rendered,
        batch_size=max(1, int(args.api_batch_size)),
        max_batch_chars=max(1, int(args.api_max_batch_chars)),
    )
    batch_workers = min(
        max(1, int(args.api_parallelism)),
        max(1, len(args.api_bases) * int(args.api_batches_per_endpoint)),
        len(batches),
    )
    print(
        "[llm-extract:api-batches] "
        f"batches={len(batches)} batch_size={args.api_batch_size} "
        f"max_batch_chars={args.api_max_batch_chars} workers={batch_workers}"
    )

    def run_batch(pos_batch: tuple[int, list[dict[str, Any]]]) -> tuple[int, list[str]]:
        pos, batch = pos_batch
        endpoint = args.api_bases[pos % len(args.api_bases)]
        prompts = [rendered[item["job_id"]] for item in batch]
        try:
            raw_outputs = _call_completion_endpoint_batch(args, endpoint, prompts)
        except Exception as exc:
            if len(batch) > 1:
                mid = len(batch) // 2
                left_errors, left_messages = run_batch((pos, batch[:mid]))
                right_errors, right_messages = run_batch((pos, batch[mid:]))
                return left_errors + right_errors, left_messages + right_messages
            mark_failed(args, batch[0], repr(exc))
            return 1, [repr(exc)]

        errors = 0
        messages: list[str] = []
        for item, raw in zip(batch, raw_outputs):
            try:
                result = _result_from_judge_output(item, raw)
                result["judge_model"] = args.judge_model
                result["api_endpoint"] = endpoint
                write_done_result(args, item, result)
            except Exception as exc:
                errors += 1
                messages.append(repr(exc))
                mark_failed(args, item, repr(exc))
        return errors, messages

    errors = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=batch_workers) as pool:
        futures = [pool.submit(run_batch, pair) for pair in enumerate(batches)]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc=f"{args.queue_name} api"):
            batch_errors, _ = future.result()
            errors += batch_errors
    if errors:
        raise RuntimeError(f"API extraction finished with {errors} failed rows")


def _load_results(args: argparse.Namespace, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    missing = []
    for item in items:
        path = _done_path(args, item["job_id"])
        if not path.exists():
            missing.append(item["job_id"])
            continue
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    if missing:
        raise RuntimeError(f"Missing {len(missing)} extraction results, first={missing[:5]}")
    return rows


def _score_option_or_number(group: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    rows = []
    correct = 0
    for item in group:
        answer = item["answer"]
        if item["answer_kind"] == "option":
            gt = _normalize_option(answer, item.get("valid_letters") or "ABCDEFG")
            pred = _normalize_option(item.get("extracted", ""), item.get("valid_letters") or "ABCDEFG")
        elif item["answer_kind"] == "option_value":
            gt = _option_value_to_letter(item)
            pred = _normalize_option(item.get("extracted", ""), item.get("valid_letters") or "ABCDEFG")
        elif item["answer_kind"] == "number":
            gt = _normalize_number(answer)
            pred = _normalize_number(item.get("extracted", ""))
        elif item["answer_kind"] == "braced":
            gt = _normalize_braced_answer(answer)
            pred = _normalize_braced_answer(item.get("extracted", ""))
        else:
            gt = _normalize_short_for_exact(answer)
            pred = _normalize_short_for_exact(item.get("extracted", ""))
        if not gt:
            raise ValueError(
                f"Could not normalize ground truth for {item.get('benchmark')} index={item.get('index')}: {answer!r}"
            )
        hit = int(bool(gt) and pred == gt)
        correct += hit
        rows.append({**item, "eval_gt": gt, "eval_pred": pred, "eval_score": hit})
    return (correct / len(rows) * 100.0 if rows else 0.0), rows


def _option_value_to_letter(item: dict[str, Any]) -> str:
    answer = _clean_cell(item.get("answer"))
    direct = _normalize_option(answer, item.get("valid_letters") or "ABCDEFG")
    if direct:
        return direct
    norm_answer = _normalize_short_for_exact(answer)
    for letter, value in (item.get("options") or {}).items():
        if _normalize_short_for_exact(value) == norm_answer:
            return letter
    return ""


def _score_binary_judge(group: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]], dict[str, Any]]:
    rows = []
    scores = []
    for item in group:
        if item.get("judge_score") is None:
            raise ValueError(f"Missing binary judge score for {item.get('job_id')}")
        score = float(item["judge_score"])
        score = 1.0 if score >= 0.5 else 0.0
        rows.append({**item, "eval_gt": item.get("answer", ""), "eval_pred": item.get("extracted", ""), "eval_score": score})
        scores.append(score)
    overall = float(sum(scores) / len(scores) * 100.0) if scores else 0.0
    return overall, rows, {"Overall": overall}


def _score_with_category_breakdowns(
    group: list[dict[str, Any]],
    args: argparse.Namespace,
    benchmark: str,
    score: float,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    df_by_model: dict[str, pd.DataFrame] = {}
    for model_slug, _ in args.model_entries:
        df_by_model[model_slug] = _load_prediction_table(_prediction_path(args.run_root, benchmark, model_slug))
    scores: dict[str, Any] = {"Overall": score}
    enriched = []
    for row in rows:
        original = df_by_model[row["model_slug"]].iloc[int(row["ordinal"])].to_dict()
        enriched.append({**original, **row})
    for col in ("category", "subfield", "reasoning_type", "task", "l2-category"):
        vals: dict[str, list[float]] = {}
        for row in enriched:
            if col in row and _clean_cell(row.get(col)):
                vals.setdefault(_clean_cell(row.get(col)), []).append(float(row.get("eval_score", 0.0)))
        for key, values in sorted(vals.items()):
            scores[f"{col}/{key}"] = float(sum(values) / len(values) * 100.0) if values else 0.0
    return scores


def _score_visiongraph(group: list[dict[str, Any]], args: argparse.Namespace) -> tuple[float, list[dict[str, Any]], dict[str, Any]]:
    vlmeval_root = REPO_ROOT / "external" / "VLMEvalKit"
    if str(vlmeval_root) not in sys.path:
        sys.path.insert(0, str(vlmeval_root))
    from vlmeval.dataset.visiongraph import _score_row

    by_model: dict[str, pd.DataFrame] = {}
    for model_slug, _ in args.model_entries:
        by_model[model_slug] = _load_prediction_table(_prediction_path(args.run_root, "visiongraph_q3", model_slug))
    rows = []
    scores_by_task: dict[str, list[float]] = {}
    for item in group:
        original = by_model[item["model_slug"]].iloc[int(item["ordinal"])].to_dict()
        original["prediction"] = item.get("extracted", "")
        score, parsed_pred, parsed_gt, error = _score_row(pd.Series(original))
        score_f = float(score)
        task = _clean_cell(original.get("task")) or "unknown"
        scores_by_task.setdefault(task, []).append(score_f)
        rows.append(
            {
                **original,
                **item,
                "eval_pred": parsed_pred,
                "eval_gt": parsed_gt,
                "eval_error": error,
                "eval_score": score_f,
            }
        )
    table = []
    for task, values in sorted(scores_by_task.items()):
        table.append({"split": task, "tot": len(values), "hit": sum(values), "acc": sum(values) / len(values) * 100.0})
    task_acc = [row["acc"] for row in table]
    macro = float(sum(task_acc) / len(task_acc)) if task_acc else 0.0
    micro_values = [float(row["eval_score"]) for row in rows]
    micro = float(sum(micro_values) / len(micro_values) * 100.0) if micro_values else 0.0
    table.append({"split": "Macro Avg", "tot": len(task_acc), "hit": sum(task_acc), "acc": macro})
    table.append({"split": "Micro Avg", "tot": len(micro_values), "hit": sum(micro_values), "acc": micro})
    return macro, rows, {"Overall": macro, "Micro Avg": micro, "table": table}


def _score_chartqapro(group: list[dict[str, Any]], args: argparse.Namespace) -> tuple[float, list[dict[str, Any]], dict[str, Any]]:
    scripts_root = REPO_ROOT / "external" / "VLMEvalKit" / "scripts"
    vlmeval_root = REPO_ROOT / "external" / "VLMEvalKit"
    for path in (vlmeval_root, scripts_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import batched_chartqapro_vllm as chartqapro

    # Rejoin extracted answers with the original metadata because ChartQAPro's
    # evaluator needs question_type/year fields.
    by_model: dict[str, pd.DataFrame] = {}
    for model_slug, _ in args.model_entries:
        by_model[model_slug] = _load_prediction_table(_prediction_path(args.run_root, "chartqapro", model_slug))
    rows = []
    for item in group:
        original = by_model[item["model_slug"]].iloc[int(item["ordinal"])].to_dict()
        out = {**original, **item, "llm_extracted_answer": item["extracted"]}
        rows.append(out)
    scores = chartqapro.evaluate_rows(rows, "llm_extracted_answer")
    overall = float(scores.get("Overall", 0.0)) * 100.0
    for row in rows:
        row["eval_pred"] = row["llm_extracted_answer"]
    return overall, rows, scores


def finalize(args: argparse.Namespace) -> None:
    items = load_manifest(args)
    results = _load_results(args, items)
    out_root = args.output_root / args.queue_name / "scores"
    summary_rows = []
    detailed_rows_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    manifest_summary = load_json(args.output_root / args.queue_name / "manifest_summary.json", {})
    source_exclusions = manifest_summary.get("source_row_exclusions") or []
    for benchmark in args.benchmarks:
        for model_slug, model_path in args.model_entries:
            group = [r for r in results if r["benchmark"] == benchmark and r["model_slug"] == model_slug]
            if not group:
                continue
            if benchmark == "chartqapro":
                score, rows, extra_scores = _score_chartqapro(group, args)
            elif benchmark == "physics":
                score, rows, extra_scores = _score_binary_judge(group)
                extra_scores = _score_with_category_breakdowns(group, args, benchmark, score, rows)
            elif benchmark == "visiongraph_q3":
                score, rows, extra_scores = _score_visiongraph(group, args)
            else:
                score, rows = _score_option_or_number(group)
                extra_scores = _score_with_category_breakdowns(group, args, benchmark, score, rows)
            detailed_rows_by_key[(benchmark, model_slug)] = rows
            score_dir = out_root / benchmark / model_slug / "llm_extracted"
            score_dir.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows).to_excel(score_dir / "llm_extracted_judged.xlsx", index=False)
            summary = {
                "dataset": spec_by_key(benchmark).display,
                "benchmark_key": benchmark,
                "model": model_path,
                "model_slug": model_slug,
                "run_name": "llm_extracted",
                "rows": len(group),
                "source_rows_excluded": sum(
                    exclusion.get("benchmark") == benchmark and exclusion.get("model_slug") == model_slug
                    for exclusion in source_exclusions
                ),
                "source_row_exclusions": [
                    exclusion
                    for exclusion in source_exclusions
                    if exclusion.get("benchmark") == benchmark and exclusion.get("model_slug") == model_slug
                ],
                "score": score,
                "scores": extra_scores,
                "judge_model": args.judge_model,
                "extraction_integrity": {
                    "empty_extractions": int(sum(not _clean_cell(item.get("extracted")) for item in group)),
                    "explicit_abstentions_z": int(sum(_clean_cell(item.get("extracted")).upper() == "Z" for item in group)),
                    "missing_binary_decisions": int(
                        sum(item.get("answer_kind") == "judge_binary" and item.get("judge_score") is None for item in group)
                    ),
                },
                "artifacts": {"judged_table": str(score_dir / "llm_extracted_judged.xlsx")},
            }
            if args.benchmark_root is not None:
                benchmark_score_dir = args.benchmark_root / benchmark / model_slug / "llm_extracted"
                summary["benchmark_score_path"] = str(benchmark_score_dir / "scores.json")
                write_json(benchmark_score_dir / "scores.json", summary)
            write_json(score_dir / "scores.json", summary)
            summary_rows.append(summary)
    write_json(out_root / "summary.json", summary_rows)
    print(json.dumps(summary_rows, indent=2, ensure_ascii=False, default=json_default))


def parse_model_entry(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--model-entry must be slug=path")
    slug, path = value.split("=", 1)
    return slug.strip(), path.strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-name", required=True)
    parser.add_argument("--benchmarks", nargs="*", default=list(DEFAULT_BENCHMARKS))
    parser.add_argument("--high-risk-direct", action="store_true", help="Use the legacy high-risk extraction benchmark set.")
    parser.add_argument("--final25", action="store_true", help="Use the canonical 15 Final25 LLM-extraction routes.")
    parser.add_argument("--model-entry", action="append", type=parse_model_entry, dest="model_entries")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--queue-root", type=Path, default=DEFAULT_QUEUE_ROOT)
    parser.add_argument("--output-root", type=Path, default=LIB_REPO_ROOT / "benchmark" / "llm_extracted")
    parser.add_argument("--benchmark-root", type=Path)
    parser.add_argument("--worker-id", default=f"llm-extract-{os.getpid()}")
    parser.add_argument("--gpu", default=os.environ.get("CUDA_VISIBLE_DEVICES", ""))
    parser.add_argument("--claim-batch-size", type=int, default=128)
    parser.add_argument("--stale-after-sec", type=float, default=900)
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--judge-model", default="Qwen/Qwen3-32B")
    parser.add_argument("--judge-batch-size", type=int, default=128)
    parser.add_argument("--judge-tensor-parallel-size", type=int, default=1)
    parser.add_argument("--judge-gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--judge-max-model-len", type=int, default=8192)
    parser.add_argument("--judge-max-num-seqs", type=int, default=128)
    parser.add_argument("--judge-max-num-batched-tokens", type=int, default=8192)
    parser.add_argument("--judge-max-tokens", type=int, default=64)
    parser.add_argument("--attention-backend", default="FLASH_ATTN")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--api-run", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--api-base", action="append", dest="api_bases")
    parser.add_argument("--api-model", default="qwen3-32b-judge")
    parser.add_argument("--api-tokenizer-model", default="Qwen/Qwen3-32B")
    parser.add_argument("--api-parallelism", type=int, default=128)
    parser.add_argument("--api-batch-size", type=int, default=16)
    parser.add_argument("--api-batches-per-endpoint", type=int, default=1)
    parser.add_argument("--api-max-batch-chars", type=int, default=24000)
    parser.add_argument("--api-timeout", type=float, default=120.0)
    parser.add_argument("--api-max-retries", type=int, default=5)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.final25:
        args.benchmarks = list(LLM_EXTRACT_SCORE_KEYS)
    elif args.high_risk_direct:
        args.benchmarks = list(HIGH_RISK_DIRECT_BENCHMARKS)
    if not args.model_entries:
        args.model_entries = list(DEFAULT_MODELS)
    if args.api_bases is None:
        args.api_bases = [f"http://127.0.0.1:{18100 + i}" for i in range(8)]
    if args.prepare:
        items = _build_items(args)
        write_manifest(args, items)
        print(f"[llm-extract:prepare] rows={len(items)} manifest={_manifest_path(args)}")
    if args.worker:
        run_worker(args)
    if args.api_run:
        run_api_pool(args)
    if args.finalize:
        finalize(args)


if __name__ == "__main__":
    main()
