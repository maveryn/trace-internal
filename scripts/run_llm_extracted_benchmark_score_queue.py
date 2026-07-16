#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import concurrent.futures
import hashlib
import json
import math
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
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
    score_path,
    spec_by_key,
    write_json,
)
from run_external_benchmark_score_queue import (  # noqa: E402
    PersistentJudge,
    _judge_cache_entry_needs_retry,
    _judge_retry_token_limits,
)
from trace_benchmark_answer_parsing import (  # noqa: E402
    extract_final_answer as _extract_final_answer,
    parse_binary_score as _strict_parse_binary_score,
)
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
EXTRACTION_CONTRACT_VERSION = "trace-final25-qwen3-extraction-v2"
SHADOW_CONTRACT_VERSION = "trace-final25-shadow-extraction-v1"
EXTRACTION_PROMPT_RENDERER_CONTRACT = (
    "user/add_generation_prompt/enable_thinking_false_when_supported-v1"
)
_VALIDATED_MANIFESTS: set[tuple[str, int, int]] = set()


@dataclass(frozen=True)
class ValidatedJudgeOutput:
    value: str
    normalized: str
    score: float | None
    method: str
    candidates: tuple[dict[str, Any], ...]
    explicit_abstention: bool


class JudgeOutputValidationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        status: str = "invalid",
        candidates: Iterable[dict[str, Any]] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.candidates = tuple(candidates)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "code": self.code,
            "message": str(self),
            "candidates": list(self.candidates),
            "contract_version": EXTRACTION_CONTRACT_VERSION,
        }


class _DuplicateJSONKeyError(ValueError):
    def __init__(self, key: str, first: Any, second: Any) -> None:
        super().__init__(f"duplicate JSON key {key!r}")
        self.key = key
        self.first = first
        self.second = second


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKeyError(key, result[key], value)
        result[key] = value
    return result


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=json_default)
    return _sha256_bytes(encoded.encode("utf-8"))


def _source_row_hash_from_prediction(row: dict[str, Any]) -> str:
    persisted = _clean_cell(row.get("source_row_hash"))
    if persisted:
        return persisted
    generated_fields = {
        "prediction",
        "raw_prediction",
        "finish_reason",
        "output_token_count",
        "prompt_token_count",
        "request_hash",
        "source_ordinal",
        "source_row_hash",
        "prompt",
        "usage",
    }
    return _canonical_hash({key: value for key, value in row.items() if key not in generated_fields})


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


def _chartqapro_final_turn(question: str) -> str:
    try:
        turns = ast.literal_eval(question)
    except (SyntaxError, ValueError):
        return question
    if not isinstance(turns, (list, tuple)) or len(turns) <= 1:
        return question
    final_turn = _clean_cell(turns[-1])
    return final_turn or question


def _countqa_needs_combined_total_instruction(question: str, response: str) -> bool:
    if not re.search(
        r"^\s*how\s+many\b.*(?:,|\band\b).*\b(?:are|is)\s+there\b",
        question,
        flags=re.I | re.S,
    ):
        return False
    selected, method = _extract_final_answer(response)
    if method in {"raw", "empty"}:
        return False
    return len(re.findall(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?![\w.])", selected)) > 1


def _build_prompt(item: dict[str, Any]) -> str:
    kind = item["answer_kind"]
    question = item["question"]
    response = item["prediction"]
    chartqapro_conversational = False
    if item.get("benchmark") == "chartqapro":
        final_turn = _chartqapro_final_turn(question)
        chartqapro_conversational = final_turn != question
        question = final_turn
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
        countqa_instruction = ""
        if item.get("benchmark") == "countqa" and _countqa_needs_combined_total_instruction(
            question, response
        ):
            countqa_instruction = (
                "CountQA expects one combined total. If the response explicitly states that total, return it. "
                "Otherwise, only when the question explicitly asks for the combined count of multiple object "
                "categories and the model's final answer gives one labeled count for every requested category, "
                "add those component counts and return their total. For example, '3 cups and 2 plates' in "
                "response to 'How many cups and plates are there?' means 5. Do not infer a missing category, "
                "recount the image, or choose between conflicting counts. If the component counts do not cover "
                "every requested category exactly once, return an empty string.\n"
            )
        return (
            "You are extracting the final numeric answer from a visual counting benchmark response.\n"
            "Do not judge correctness. Extract only the count stated as the final answer.\n"
            "If no count is selected, return an empty string.\n\n"
            f"{countqa_instruction}"
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
            "Return exactly one JSON object: {\"score\": 1} where score is 1 for correct and 0 for incorrect.\n"
            "Do not include an answer field, explanation, markdown fence, or any other text."
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
    conversational_instruction = ""
    if chartqapro_conversational:
        conversational_instruction = (
            "This is a conversational ChartQAPro item. The official evaluator scores only the final turn shown below. "
            "Extract only the response's answer to that final question; ignore answers to earlier turns.\n"
        )
    return (
        "You are extracting the final short answer from a visual question answering response.\n"
        "Do not judge correctness. Extract only the final answer, with no explanation.\n"
        "If the response uses a boxed final answer, extract the boxed content. Preserve coordinate/list/text answers.\n"
        "For plain numbers, remove percent signs, currency symbols, and commas. For choices, return only the chosen letter or value.\n"
        "If the response says the question is unanswerable, return Unanswerable.\n\n"
        f"{conversational_instruction}"
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


def _job_id_for_row(
    benchmark: str,
    model_slug: str,
    index: str,
    ordinal: int,
    index_counts: Counter[str],
    last_ordinal_by_index: dict[str, int],
) -> str:
    base = f"{benchmark}__{model_slug}__{index}"
    if index_counts[index] > 1 and ordinal != last_ordinal_by_index[index]:
        return f"{base}__ordinal{ordinal}"
    return base


def _request_hash_for_item(args: argparse.Namespace, item: dict[str, Any]) -> str:
    execution_backend = str(getattr(args, "execution_backend", "api"))
    return _canonical_hash(
        {
            "contract_version": EXTRACTION_CONTRACT_VERSION,
            "benchmark": item["benchmark"],
            "model_slug": item["model_slug"],
            "model_path": item["model_path"],
            "index": item["index"],
            "ordinal": item["ordinal"],
            "question": item["question"],
            "prediction": item["prediction"],
            "answer": item["answer"],
            "answer_kind": item["answer_kind"],
            "valid_letters": item.get("valid_letters"),
            "options": item.get("options"),
            "prompt": item["prompt"],
            "judge_model": getattr(args, "judge_model", "Qwen/Qwen3-32B"),
            "execution_backend": execution_backend,
            "prompt_renderer_contract": EXTRACTION_PROMPT_RENDERER_CONTRACT,
            "api_model": (
                getattr(args, "api_model", "qwen3-32b-judge")
                if execution_backend == "api"
                else None
            ),
            "api_tokenizer_model": (
                getattr(args, "api_tokenizer_model", "Qwen/Qwen3-32B")
                if execution_backend == "api"
                else None
            ),
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": int(getattr(args, "judge_max_tokens", 256)),
        }
    )


def _build_items(args: argparse.Namespace) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    source_workbooks: dict[str, dict[str, Any]] = {}
    for benchmark in args.benchmarks:
        for model_slug, model_path in args.model_entries:
            pred_path = _prediction_path(args.run_root, benchmark, model_slug)
            workbook_sha256 = _sha256_file(pred_path)
            source_workbooks[str(pred_path)] = {
                "benchmark": benchmark,
                "model_slug": model_slug,
                "sha256": workbook_sha256,
            }
            df = _load_prediction_table(pred_path)
            records = df.to_dict(orient="records")
            row_indices = [_row_index(row, ordinal) for ordinal, row in enumerate(records)]
            index_counts = Counter(row_indices)
            last_ordinal_by_index = {index: ordinal for ordinal, index in enumerate(row_indices)}
            for ordinal, row_obj in enumerate(records):
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
                    source_row_hash = _source_row_hash_from_prediction(row)
                    exclusion_request_hash = _canonical_hash(
                        {
                            "contract_version": EXTRACTION_CONTRACT_VERSION,
                            "benchmark": benchmark,
                            "model_slug": model_slug,
                            "index": index,
                            "ordinal": ordinal,
                            "source_row_hash": source_row_hash,
                            "exclusion_reason": exclusion_reason,
                        }
                    )
                    exclusions.append(
                        {
                            "benchmark": benchmark,
                            "model_slug": model_slug,
                            "index": index,
                            "ordinal": ordinal,
                            "reason": exclusion_reason,
                            "question": _question_for(benchmark, row),
                            "prediction": _clean_cell(row.get("prediction")),
                            "answer": _clean_cell(row.get("answer")),
                            "source_row_hash": source_row_hash,
                            "request_hash": exclusion_request_hash,
                        }
                    )
                    continue
                item = {
                    "job_id": _job_id_for_row(
                        benchmark,
                        model_slug,
                        index,
                        ordinal,
                        index_counts,
                        last_ordinal_by_index,
                    ),
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
                    "prediction_table_sha256": workbook_sha256,
                    "source_row_hash": _source_row_hash_from_prediction(row),
                    "response_sha256": _sha256_bytes(_clean_cell(row.get("prediction")).encode("utf-8")),
                    "contract_version": EXTRACTION_CONTRACT_VERSION,
                }
                _validate_required_choice_contract(item)
                item["prompt"] = _build_prompt(item)
                item["request_hash"] = _request_hash_for_item(args, item)
                items.append(item)
    args.source_row_exclusions = exclusions
    args.source_workbooks = source_workbooks
    return items


def _safe_job_filename(job_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.=-]+", "__", job_id) + ".json"


def _done_path(args: argparse.Namespace, job_id: str) -> Path:
    return args.output_root / args.queue_name / "items" / _safe_job_filename(job_id)


def _failure_path(args: argparse.Namespace, job_id: str) -> Path:
    return args.output_root / args.queue_name / "failures" / _safe_job_filename(job_id)


def _manifest_path(args: argparse.Namespace) -> Path:
    return args.output_root / args.queue_name / "manifest.jsonl"


def _shadow_manifest_path(args: argparse.Namespace) -> Path:
    return args.output_root / args.queue_name / "shadow_extraction.jsonl"


def _shadow_extraction_record(item: dict[str, Any]) -> dict[str, Any]:
    response = _clean_cell(item.get("prediction"))
    selected, method = _extract_final_answer(response)
    explicit_candidates: list[tuple[str, str]] = []
    for match in re.finditer(r"<answer>\s*(.*?)\s*</answer>", response, flags=re.I | re.S):
        explicit_candidates.append(("answer_tag", match.group(1)))
    for match in re.finditer(
        r"(?is)(?:^|\n|\b)(?:the\s+)?(?:final\s+)?answer\s*(?:is|=|:|：)\s*(.+)",
        response,
    ):
        explicit_candidates.append(("answer_marker", match.group(1).splitlines()[0]))
    if method not in {"raw", "empty"}:
        explicit_candidates.append((method, selected))

    normalized_candidates: list[tuple[str, str, str]] = []
    ambiguity_candidates: list[dict[str, Any]] = []
    scalar_conflict = False
    for candidate_method, candidate in explicit_candidates:
        evidence = _scalar_ambiguity_evidence(
            item, _clean_cell(candidate), candidate_method
        )
        if evidence:
            scalar_conflict = True
            ambiguity_candidates.extend(evidence)
        normalized = normalize_extracted(item, candidate)
        if normalized:
            normalized_candidates.append((candidate_method, _clean_cell(candidate), normalized))
    distinct = list(dict.fromkeys(candidate[2] for candidate in normalized_candidates))
    if scalar_conflict or len(distinct) > 1:
        status = "conflict"
        candidate = ""
    elif len(distinct) == 1:
        status = "resolved_explicit"
        candidate = distinct[0]
    else:
        status = "unresolved_raw" if response else "empty_response"
        candidate = ""
    audit_candidates: list[dict[str, Any]] = []
    seen_candidates: set[tuple[str, str, str]] = set()
    for method_name, raw_value, normalized_value in [
        *normalized_candidates,
        *(
            (
                str(evidence["source"]),
                _clean_cell(evidence["raw"]),
                _clean_cell(evidence["normalized"]),
            )
            for evidence in ambiguity_candidates
        ),
    ]:
        key = (method_name, raw_value, normalized_value)
        if key in seen_candidates:
            continue
        seen_candidates.add(key)
        audit_candidates.append(
            {"method": method_name, "raw": raw_value, "normalized": normalized_value}
        )
    return {
        "job_id": item["job_id"],
        "benchmark": item["benchmark"],
        "model_slug": item["model_slug"],
        "index": item["index"],
        "ordinal": item["ordinal"],
        "response_sha256": item["response_sha256"],
        "status": status,
        "selected_method": method,
        "candidate": candidate,
        "candidates": audit_candidates,
        "contract_version": SHADOW_CONTRACT_VERSION,
        "score_neutral": True,
    }


def write_manifest(args: argparse.Namespace, items: list[dict[str, Any]]) -> None:
    path = _manifest_path(args)
    path.parent.mkdir(parents=True, exist_ok=True)
    job_ids = [item["job_id"] for item in items]
    if len(job_ids) != len(set(job_ids)):
        duplicates = [job_id for job_id, count in Counter(job_ids).items() if count > 1]
        raise ValueError(f"Manifest contains duplicate job ids: {duplicates[:10]}")
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False, default=json_default) + "\n")
    shadow_path = _shadow_manifest_path(args)
    shadow_tmp = shadow_path.with_suffix(shadow_path.suffix + ".tmp")
    with shadow_tmp.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(_shadow_extraction_record(item), ensure_ascii=False, default=json_default) + "\n")
    shadow_tmp.replace(shadow_path)
    write_json(
        args.output_root / args.queue_name / "manifest_summary.json",
        {
            "queue_name": args.queue_name,
            "benchmarks": args.benchmarks,
            "model_slugs": [slug for slug, _ in args.model_entries],
            "rows": len(items),
            "source_rows_excluded": len(getattr(args, "source_row_exclusions", [])),
            "source_row_exclusions": getattr(args, "source_row_exclusions", []),
            "source_workbooks": getattr(args, "source_workbooks", {}),
            "contract_version": EXTRACTION_CONTRACT_VERSION,
            "shadow_contract_version": SHADOW_CONTRACT_VERSION,
            "shadow_extraction": str(shadow_path),
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
    stat = path.stat()
    validation_key = (str(path.resolve()), int(stat.st_mtime_ns), int(stat.st_size))
    if validation_key not in _VALIDATED_MANIFESTS:
        workbooks: dict[str, str] = {}
        for item in out:
            if item.get("contract_version") != EXTRACTION_CONTRACT_VERSION:
                raise RuntimeError(
                    f"Extraction manifest contract changed for {item.get('job_id')}; rerun with --prepare"
                )
            workbook = _clean_cell(item.get("prediction_table"))
            workbook_hash = _clean_cell(item.get("prediction_table_sha256"))
            if workbook and workbook_hash:
                workbooks[workbook] = workbook_hash
        for workbook, expected in workbooks.items():
            workbook_path = Path(workbook)
            if not workbook_path.exists() or _sha256_file(workbook_path) != expected:
                raise RuntimeError(f"Prediction workbook changed after extraction prepare: {workbook}; rerun --prepare")
        _VALIDATED_MANIFESTS.add(validation_key)
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


def _done_result_is_current(args: argparse.Namespace, item: dict[str, Any]) -> bool:
    path = _done_path(args, item["job_id"])
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not (
        payload.get("request_hash") == item.get("request_hash")
        and payload.get("contract_version") == EXTRACTION_CONTRACT_VERSION
        and payload.get("validation_contract_version") == EXTRACTION_CONTRACT_VERSION
        and payload.get("response_sha256") == item.get("response_sha256")
        and payload.get("extraction_status") == "resolved"
    ):
        return False
    try:
        reparsed = _result_from_judge_output(item, str(payload.get("judge_output", "")))
    except JudgeOutputValidationError:
        return False
    for key in (
        "job_id",
        "benchmark",
        "model_slug",
        "index",
        "ordinal",
        "answer",
        "answer_kind",
        "valid_letters",
        "options",
        "prediction",
        "extracted_raw",
        "extracted",
        "judge_score",
        "extraction_method",
        "extraction_candidates",
        "explicit_abstention",
    ):
        if payload.get(key) != reparsed.get(key):
            return False
    expected_judge_model = getattr(args, "judge_model", None)
    if expected_judge_model is not None and payload.get("judge_model") != expected_judge_model:
        return False
    return True


def _quarantine_stale_done_result(
    args: argparse.Namespace,
    item: dict[str, Any],
    *,
    known_stale: bool = False,
) -> None:
    path = _done_path(args, item["job_id"])
    if not path.exists() or (not known_stale and _done_result_is_current(args, item)):
        return
    stale_dir = args.output_root / args.queue_name / "stale_items"
    stale_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    destination = stale_dir / f"{path.stem}.{digest}.json"
    if destination.exists():
        path.unlink()
    else:
        shutil.move(str(path), str(destination))


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
            if info.get("request_hash") != item.get("request_hash"):
                info = {}
            if _done_result_is_current(args, item):
                state_jobs[job_id] = {
                    **info,
                    "status": "done",
                    "done_path": str(done_path),
                    "request_hash": item["request_hash"],
                    "updated_at": now,
                }
                continue
            _quarantine_stale_done_result(args, item)
            attempts = int(info.get("attempts") or 0)
            if info.get("status") == "failed" and attempts >= args.max_attempts:
                continue
            if info.get("status") == "running" and _pid_alive(info.get("pid")):
                continue
            if info.get("status") == "running" and now - float(info.get("updated_at", 0)) < args.stale_after_sec:
                continue
            state_jobs[job_id] = {
                "status": "running",
                "worker": args.worker_id,
                "pid": os.getpid(),
                "updated_at": now,
                "attempts": attempts + 1,
                "request_hash": item["request_hash"],
            }
            claimed.append(item)
            if len(claimed) >= args.claim_batch_size:
                break
        write_json(queue_path, state)
    return claimed


def write_done_result(args: argparse.Namespace, item: dict[str, Any], result: dict[str, Any]) -> None:
    done_path = _done_path(args, item["job_id"])
    done_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        done_path,
        {
            **result,
            "request_hash": item["request_hash"],
            "contract_version": EXTRACTION_CONTRACT_VERSION,
            "validation_contract_version": EXTRACTION_CONTRACT_VERSION,
            "response_sha256": item["response_sha256"],
        },
    )


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
            "request_hash": item["request_hash"],
        }
        write_json(queue_path, state)


def mark_failed(
    args: argparse.Namespace,
    item: dict[str, Any],
    error: str,
    *,
    raw_output: str | None = None,
    validation_failure: dict[str, Any] | None = None,
) -> None:
    failure_path = _failure_path(args, item["job_id"])
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        failure_path,
        {
            "job_id": item["job_id"],
            "error": error,
            "raw_output": raw_output,
            "validation_failure": validation_failure,
            "request_hash": item["request_hash"],
            "response_sha256": item["response_sha256"],
            "contract_version": EXTRACTION_CONTRACT_VERSION,
            "updated_at": time.time(),
        },
    )
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
            "request_hash": item["request_hash"],
        }
        write_json(queue_path, state)


def _decode_first_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", raw):
        try:
            obj, _ = decoder.raw_decode(raw[match.start() :])
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue
    return {}


def _parse_json_answer(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    obj = _decode_first_json_object(raw)
    if obj:
        value = obj.get("answer", obj.get("extracted_answer", ""))
        return _clean_cell(value)
    match = re.search(r'"?(?:answer|extracted_answer)"?\s*[:=]\s*"?([^"\n}]+)', raw, flags=re.I)
    if match:
        return match.group(1).strip()
    return raw.splitlines()[0].strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    obj = _decode_first_json_object(raw)
    if obj:
        return obj
    answer = _parse_json_answer(raw)
    return {"answer": answer} if answer else {}


def _normalize_option(value: str, valid_letters: Iterable[str]) -> str:
    letters = "".join(valid_letters)
    text = str(value or "").strip().upper()
    text = text.strip("()[]{}.:;\"'`* ")
    if (len(text) == 1 and text in set(letters)) or text == "Z":
        return text
    if re.fullmatch(r"[A-Z]{1,2}", text):
        # A response that explicitly selects an unavailable or multiple option
        # is an invalid single-choice answer, not an extraction-system error.
        return "Z"
    match = re.search(rf"\b([{re.escape(letters)}Z])\b", text)
    return match.group(1) if match else ""


def _legacy_raw_output_from_error(job_id: str, error: str) -> str:
    """Recover judge output embedded by the pre-raw-artifact failure format."""

    text = str(error or "")
    if text.startswith("ValueError(") and text.endswith(")"):
        try:
            text = str(ast.literal_eval(text[len("ValueError(") : -1]))
        except Exception:
            return ""
    marker = f"{job_id}: "
    if marker not in text:
        return ""
    encoded = text.split(marker, 1)[1]
    try:
        return str(ast.literal_eval(encoded))
    except Exception:
        return ""


def _recover_failed_outputs(
    args: argparse.Namespace,
    items: list[dict[str, Any]],
) -> tuple[int, int]:
    queue_path = args.queue_root / f"llm_extract_{args.queue_name}.json"
    state = load_json(queue_path, {"jobs": {}})
    failed = {
        job_id: info
        for job_id, info in (state.get("jobs") or {}).items()
        if info.get("status") == "failed"
    }
    if not failed:
        return 0, 0

    item_by_id = {item["job_id"]: item for item in items}
    recovered = 0
    unrecoverable = 0
    for job_id, info in failed.items():
        item = item_by_id.get(job_id)
        if item is None or _done_path(args, job_id).exists():
            continue
        failure_payload = load_json(_failure_path(args, job_id), {})
        if not (
            failure_payload.get("request_hash") == item.get("request_hash")
            and failure_payload.get("response_sha256") == item.get("response_sha256")
            and failure_payload.get("contract_version") == EXTRACTION_CONTRACT_VERSION
        ):
            unrecoverable += 1
            continue
        # Current-contract terminal failures must be regenerated. In
        # particular, a truncated generation can contain parseable JSON that
        # is still unsafe to score.
        if (failure_payload.get("validation_failure") or {}).get("code") != (
            "parser_migration_recoverable"
        ):
            unrecoverable += 1
            continue
        raw = _clean_cell(failure_payload.get("raw_output"))
        if not raw:
            raw = _legacy_raw_output_from_error(job_id, info.get("error", ""))
        if not raw:
            unrecoverable += 1
            continue
        try:
            result = _result_from_judge_output(item, raw)
            result["judge_model"] = args.judge_model
            result["recovered_from_failed_output"] = True
            write_done_result(args, item, result)
            recovered += 1
        except Exception:
            unrecoverable += 1
    return recovered, unrecoverable


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


def _decode_json_objects(text: str) -> list[dict[str, Any]]:
    raw = str(text or "").strip()
    if not raw:
        return []
    try:
        decoded = json.loads(raw, object_pairs_hook=_reject_duplicate_json_keys)
    except _DuplicateJSONKeyError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    else:
        return [decoded] if isinstance(decoded, dict) else []

    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw, flags=re.I | re.S)
    if fenced:
        try:
            decoded = json.loads(
                fenced.group(1), object_pairs_hook=_reject_duplicate_json_keys
            )
        except _DuplicateJSONKeyError:
            raise
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        else:
            return [decoded] if isinstance(decoded, dict) else []

    decoder = json.JSONDecoder(object_pairs_hook=_reject_duplicate_json_keys)
    objects: list[dict[str, Any]] = []
    position = 0
    while position < len(raw):
        start = raw.find("{", position)
        if start < 0:
            break
        try:
            candidate, consumed = decoder.raw_decode(raw[start:])
        except _DuplicateJSONKeyError:
            raise
        except (TypeError, ValueError, json.JSONDecodeError):
            position = start + 1
            continue
        position = start + max(consumed, 1)
        if isinstance(candidate, dict):
            objects.append(candidate)
    return objects


def _mask_json_objects(text: str) -> str:
    """Hide decoded JSON spans before looking for surrounding prose claims."""

    raw = str(text or "")
    masked = list(raw)
    decoder = json.JSONDecoder(object_pairs_hook=_reject_duplicate_json_keys)
    position = 0
    while position < len(raw):
        start = raw.find("{", position)
        if start < 0:
            break
        try:
            candidate, consumed = decoder.raw_decode(raw[start:])
        except _DuplicateJSONKeyError:
            raise
        except (TypeError, ValueError, json.JSONDecodeError):
            position = start + 1
            continue
        end = start + max(consumed, 1)
        position = end
        if not isinstance(candidate, dict):
            continue
        for index in range(start, end):
            if masked[index] not in {"\n", "\r"}:
                masked[index] = " "
    return "".join(masked)


def _judge_json_method(raw: str) -> str:
    text = str(raw or "").strip()
    try:
        if isinstance(json.loads(text), dict):
            return "judge_json"
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.I | re.S)
    if fenced:
        try:
            if isinstance(json.loads(fenced.group(1)), dict):
                return "judge_fenced_json"
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return "judge_embedded_json"


_LABELED_BINARY_OUTPUT = re.compile(
    r"^(?:final\s+)?[\"']?(?:score|judg(?:e)?ment|judge\s+output|correct)[\"']?\s*[:=]\s*"
    r"(?:\*{1,3}|_{1,3})?\s*([01])\s*(?:\*{1,3}|_{1,3})?\s*[.!]?\s*$",
    flags=re.I | re.S,
)


def _parse_binary_scalar(value: Any) -> float | None:
    if isinstance(value, (bool, int, float)):
        return _strict_parse_binary_score(value)
    text = _clean_cell(value)
    if not text:
        return None
    if text.lower() in {"1", "true", "yes", "correct", "0", "false", "no", "incorrect"}:
        return _strict_parse_binary_score(text)
    match = _LABELED_BINARY_OUTPUT.fullmatch(text)
    return float(match.group(1)) if match else None


def _explicit_binary_candidates(text: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for line_number, line in enumerate(str(text or "").splitlines()):
        value = _parse_binary_scalar(line)
        if value is not None:
            candidates.append(
                {
                    "source": f"explicit.binary_line[{line_number}]",
                    "raw": line.strip(),
                    "normalized": value,
                }
            )
    return candidates


def _answer_scalar_text(item: dict[str, Any], value: Any, source: str) -> str:
    kind = item["answer_kind"]
    if kind in {"option", "option_value"}:
        if not isinstance(value, str):
            raise JudgeOutputValidationError(
                f"{item['job_id']} {source} must be a string",
                code="answer_type",
                candidates=({"source": source, "raw": value},),
            )
        return _clean_cell(value)
    if value is None or isinstance(value, (list, dict)):
        raise JudgeOutputValidationError(
            f"{item['job_id']} {source} must be a scalar",
            code="answer_type",
            candidates=({"source": source, "raw": value},),
        )
    if kind == "number" and isinstance(value, bool):
        raise JudgeOutputValidationError(
            f"{item['job_id']} {source} must be numeric text or a number",
            code="answer_type",
            candidates=({"source": source, "raw": value},),
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise JudgeOutputValidationError(
            f"{item['job_id']} {source} must be finite",
            code="answer_type",
            candidates=({"source": source, "raw": value},),
        )
    if not isinstance(value, (str, int, float, bool)):
        raise JudgeOutputValidationError(
            f"{item['job_id']} {source} must be a scalar",
            code="answer_type",
            candidates=({"source": source, "raw": value},),
        )
    return _clean_cell(value)


_NUMBER_CANDIDATE = re.compile(
    r"(?<![\w.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w.])"
)
_EXPLICIT_ANSWER_LINE = re.compile(
    r"^[ \t]*(?:the[ \t]+)?(?:final[ \t]+)?answer[ \t]*(?:is|=|:|：)[ \t]*(.*?)[ \t]*$",
    flags=re.I | re.M,
)


def _option_candidates(value: str, valid_letters: Iterable[str]) -> list[str]:
    allowed = "".join(dict.fromkeys([*valid_letters, "Z"]))
    if not allowed:
        return []
    text = str(value or "").strip()
    compact = text.upper().strip("()[]{}.:;\"'`* ")
    if len(compact) > 1 and re.fullmatch(rf"[{re.escape(allowed)}]+", compact):
        return list(dict.fromkeys(compact))

    token_pattern = re.compile(
        rf"(?<![A-Za-z])([{re.escape(allowed)}])(?![A-Za-z])"
    )
    tokens = list(token_pattern.finditer(text))
    candidates: list[str] = []
    for left, right in zip(tokens, tokens[1:]):
        connector = text[left.end() : right.start()]
        if re.fullmatch(
            r"\s*(?:(?:/|,|;|&)|(?:or|and))\s*(?:(?:maybe|option|choice)\s+)?",
            connector,
            flags=re.I,
        ):
            candidates.extend((left.group(1), right.group(1)))
    if candidates:
        return list(dict.fromkeys(candidates))

    structured = re.fullmatch(
        rf"\s*(?:either\s+)?[{re.escape(allowed)}]"
        rf"(?:\s*(?:(?:/|,|;|&)|(?:or|and))\s*"
        rf"(?:(?:maybe|option|choice)\s+)?[{re.escape(allowed)}])+\s*[.!]?\s*",
        text,
        flags=re.I,
    )
    if structured is not None:
        return list(
            dict.fromkeys(
                candidate.upper()
                for candidate in re.findall(
                    rf"(?<![A-Za-z])([{re.escape(allowed)}])(?![A-Za-z])",
                    text,
                    flags=re.I,
                )
            )
        )
    return []


def _scalar_ambiguity_evidence(
    item: dict[str, Any], value: str, source: str
) -> list[dict[str, Any]]:
    kind = item["answer_kind"]
    if kind in {"option", "option_value"}:
        option_candidates = _option_candidates(value, item["valid_letters"])
        if len(option_candidates) > 1:
            return [
                {"source": source, "raw": candidate, "normalized": candidate}
                for candidate in option_candidates
            ]
    elif kind == "number" and value:
        numeric_candidates = _NUMBER_CANDIDATE.findall(value)
        normalized_numbers = list(
            dict.fromkeys(_normalize_number(candidate) for candidate in numeric_candidates)
        )
        normalized_numbers = [candidate for candidate in normalized_numbers if candidate]
        if len(normalized_numbers) > 1:
            return [
                {
                    "source": source,
                    "raw": candidate,
                    "normalized": _normalize_number(candidate),
                }
                for candidate in numeric_candidates
            ]
    return []


def _validated_scalar_candidate(
    item: dict[str, Any],
    value: Any,
    source: str,
    prior_candidates: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    scalar = _answer_scalar_text(item, value, source)
    kind = item["answer_kind"]
    evidence = _scalar_ambiguity_evidence(item, scalar, source)
    if evidence:
        raise JudgeOutputValidationError(
            f"{item['job_id']} {source} contains multiple answer candidates",
            code="conflicting_answers",
            status="ambiguous",
            candidates=(*prior_candidates, *evidence),
        )

    normalized = normalize_extracted(item, scalar)
    if kind in {"option", "option_value"} and not normalized:
        raise JudgeOutputValidationError(
            f"{item['job_id']} {source} is not a selected option or Z",
            code="answer_value",
            candidates=(*prior_candidates, {"source": source, "raw": value, "normalized": normalized}),
        )
    if kind in {"number", "short", "braced"} and scalar and not normalized:
        raise JudgeOutputValidationError(
            f"{item['job_id']} {source} cannot be normalized",
            code="answer_value",
            candidates=(*prior_candidates, {"source": source, "raw": value, "normalized": normalized}),
        )
    return {"source": source, "raw": value, "normalized": normalized}


def _explicit_answer_candidates(item: dict[str, Any], text: str) -> list[dict[str, Any]]:
    raw_candidates: list[tuple[str, str]] = []
    for position, match in enumerate(
        re.finditer(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    ):
        raw_candidates.append((f"explicit.answer_tag[{position}]", match.group(1)))
    for position, match in enumerate(_EXPLICIT_ANSWER_LINE.finditer(text)):
        raw_candidates.append((f"explicit.answer_marker[{position}]", match.group(1)))
    for position, match in enumerate(
        re.finditer(r"\\boxed\s*\{([^{}]*)\}", text, flags=re.I | re.S)
    ):
        raw_candidates.append((f"explicit.boxed[{position}]", match.group(1)))

    candidates: list[dict[str, Any]] = []
    for source, value in raw_candidates:
        scalar = value
        for pattern in (
            r"\s*<answer>\s*(.*?)\s*</answer>\s*[.!]?\s*",
            r"\s*\\boxed\s*\{([^{}]*)\}\s*[.!]?\s*",
        ):
            nested = re.fullmatch(pattern, scalar, flags=re.I | re.S)
            if nested is not None:
                scalar = nested.group(1)
        candidate = _validated_scalar_candidate(item, scalar, source, candidates)
        candidate["raw"] = value
        candidates.append(candidate)
    return candidates


def _validated_answer_candidates(
    item: dict[str, Any],
    objects: list[dict[str, Any]],
    *,
    text: str = "",
) -> tuple[str, str, tuple[dict[str, Any], ...]]:
    candidates: list[dict[str, Any]] = []
    for object_index, obj in enumerate(objects):
        for field in ("answer", "extracted_answer"):
            if field not in obj:
                continue
            source = f"json[{object_index}].{field}"
            candidates.append(
                _validated_scalar_candidate(item, obj[field], source, candidates)
            )
    if text:
        for candidate in _explicit_answer_candidates(item, _mask_json_objects(text)):
            if candidate not in candidates:
                candidates.append(candidate)
    if not candidates:
        raise JudgeOutputValidationError(
            f"{item['job_id']} judge JSON is missing answer/extracted_answer",
            code="missing_answer",
        )
    distinct = list(dict.fromkeys(str(candidate["normalized"]) for candidate in candidates))
    if len(distinct) != 1:
        raise JudgeOutputValidationError(
            f"{item['job_id']} judge JSON contains conflicting answer candidates",
            code="conflicting_answers",
            status="ambiguous",
            candidates=candidates,
        )
    first = candidates[0]
    return _clean_cell(first["raw"]), distinct[0], tuple(candidates)


def _validate_binary_judge_output(
    item: dict[str, Any],
    raw: str,
    objects: list[dict[str, Any]],
) -> ValidatedJudgeOutput:
    score_candidates: list[dict[str, Any]] = []
    for object_index, obj in enumerate(objects):
        for field in ("score", "judgement", "judgment"):
            if field not in obj:
                continue
            source = f"json[{object_index}].{field}"
            score = _parse_binary_scalar(obj[field])
            candidate = {"source": source, "raw": obj[field], "normalized": score}
            if score is None:
                raise JudgeOutputValidationError(
                    f"{item['job_id']} {source} is not an explicit binary decision",
                    code="binary_score_value",
                    candidates=(*score_candidates, candidate),
                )
            score_candidates.append(candidate)

    if objects:
        for candidate in _explicit_binary_candidates(_mask_json_objects(raw)):
            if candidate not in score_candidates:
                score_candidates.append(candidate)

    if not score_candidates:
        if objects:
            raise JudgeOutputValidationError(
                f"{item['job_id']} judge JSON is missing a binary score",
                code="missing_binary_score",
            )
        if "{" in raw or "}" in raw:
            raise JudgeOutputValidationError(
                f"{item['job_id']} judge output contains malformed JSON",
                code="malformed_json",
            )
        score = _parse_binary_scalar(raw)
        if score is None:
            raise JudgeOutputValidationError(
                f"{item['job_id']} judge output is not JSON or an explicit atomic binary decision",
                code="missing_binary_score",
            )
        candidate = {"source": "atomic_binary", "raw": raw, "normalized": score}
        return ValidatedJudgeOutput(
            value="",
            normalized="",
            score=score,
            method="judge_atomic_binary",
            candidates=(candidate,),
            explicit_abstention=True,
        )

    distinct_scores = list(dict.fromkeys(float(candidate["normalized"]) for candidate in score_candidates))
    if len(distinct_scores) != 1:
        raise JudgeOutputValidationError(
            f"{item['job_id']} judge JSON contains conflicting binary decisions",
            code="conflicting_binary_scores",
            status="ambiguous",
            candidates=score_candidates,
        )

    answer_candidates: tuple[dict[str, Any], ...] = ()
    value = ""
    normalized = ""
    if any(field in obj for obj in objects for field in ("answer", "extracted_answer")):
        value, normalized, answer_candidates = _validated_answer_candidates(
            item, objects, text=raw
        )
    return ValidatedJudgeOutput(
        value=value,
        normalized=normalized,
        score=distinct_scores[0],
        method=_judge_json_method(raw),
        candidates=tuple(score_candidates) + answer_candidates,
        explicit_abstention=not normalized,
    )


def _validate_judge_output(item: dict[str, Any], raw: str) -> ValidatedJudgeOutput:
    text = str(raw or "").strip()
    if not text:
        raise JudgeOutputValidationError(
            f"{item['job_id']} judge output is empty",
            code="empty_output",
        )
    try:
        objects = _decode_json_objects(text)
    except _DuplicateJSONKeyError as exc:
        raise JudgeOutputValidationError(
            f"{item['job_id']} judge JSON repeats field {exc.key!r}",
            code="duplicate_json_field",
            status="ambiguous",
            candidates=(
                {
                    "source": f"json.duplicate.{exc.key}",
                    "raw": exc.first,
                    "normalized": None,
                },
                {
                    "source": f"json.duplicate.{exc.key}",
                    "raw": exc.second,
                    "normalized": None,
                },
            ),
        ) from exc
    if item["answer_kind"] == "judge_binary":
        return _validate_binary_judge_output(item, text, objects)
    if not objects:
        raise JudgeOutputValidationError(
            f"{item['job_id']} judge output does not contain a valid JSON object",
            code="malformed_json" if "{" in text else "missing_json",
        )
    value, normalized, candidates = _validated_answer_candidates(item, objects, text=text)
    return ValidatedJudgeOutput(
        value=value,
        normalized=normalized,
        score=None,
        method=_judge_json_method(text),
        candidates=candidates,
        explicit_abstention=(normalized == "" or normalized == "Z"),
    )


def _result_from_judge_output(item: dict[str, Any], raw: str) -> dict[str, Any]:
    validated = _validate_judge_output(item, raw)
    out = {
        **{k: item[k] for k in ("job_id", "benchmark", "model_slug", "index", "ordinal", "answer", "answer_kind")},
        "valid_letters": item.get("valid_letters"),
        "options": item.get("options"),
        "extracted_raw": validated.value,
        "extracted": validated.normalized,
        "judge_output": raw,
        "prediction": item["prediction"],
        "extraction_status": "resolved",
        "extraction_method": validated.method,
        "extraction_candidates": list(validated.candidates),
        "explicit_abstention": validated.explicit_abstention,
        "validation_contract_version": EXTRACTION_CONTRACT_VERSION,
    }
    if validated.score is not None:
        out["judge_score"] = validated.score
    return out


def _validate_runtime_contract(
    args: argparse.Namespace,
    items: list[dict[str, Any]],
    *,
    expected_backend: str,
) -> None:
    configured_backend = str(getattr(args, "execution_backend", "api"))
    if configured_backend != expected_backend:
        raise RuntimeError(
            f"Extraction manifest is configured for {configured_backend!r}, but this is the "
            f"{expected_backend!r} runner; rerun --prepare with "
            f"--execution-backend {expected_backend}"
        )
    contract_mismatches = [
        item["job_id"]
        for item in items
        if item.get("request_hash") != _request_hash_for_item(args, item)
    ]
    if contract_mismatches:
        raise RuntimeError(
            "Extraction runtime settings differ from the prepared manifest; rerun --prepare. "
            f"First mismatches={contract_mismatches[:5]}"
        )


def run_worker(args: argparse.Namespace) -> None:
    if args.gpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    os.environ.setdefault("VLLM_ATTENTION_BACKEND", args.attention_backend)
    os.environ.setdefault("VLLM_DISABLE_COMPILE_CACHE", "1")
    items = load_manifest(args)
    _validate_runtime_contract(args, items, expected_backend="local")
    for item in items:
        _quarantine_stale_done_result(args, item)
    judge = PersistentJudge(args)
    try:
        while True:
            batch = claim_many(args, items)
            if not batch:
                print(f"[llm-extract:done] worker={args.worker_id} no remaining jobs")
                break
            print(f"[llm-extract:claim] worker={args.worker_id} rows={len(batch)}")
            prompts = [(item["job_id"], item["prompt"]) for item in batch]
            item_by_job_id = {str(item["job_id"]): item for item in batch}

            def validate_output(job_id: str, raw: str) -> bool:
                item = item_by_job_id.get(str(job_id))
                if item is None:
                    return False
                try:
                    _result_from_judge_output(item, raw)
                except Exception:
                    return False
                return True

            outputs = judge.run_cached(
                output_dir=args.output_root / args.queue_name / "worker_caches",
                prompts=prompts,
                cache_name=f"{args.worker_id}.jsonl",
                max_tokens=args.judge_max_tokens,
                no_resume=False,
                desc=f"{args.worker_id} extract",
                output_validator_by_index=validate_output,
                contract_version=EXTRACTION_CONTRACT_VERSION,
            )
            for item in batch:
                raw = ""
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
                except JudgeOutputValidationError as exc:
                    mark_failed(
                        args,
                        item,
                        repr(exc),
                        raw_output=raw,
                        validation_failure=exc.as_dict(),
                    )
                except Exception as exc:
                    mark_failed(args, item, repr(exc), raw_output=raw or None)
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


def _iter_api_batches(
    pending: list[dict[str, Any]],
    tokenizer: Any,
    *,
    batch_size: int,
    max_batch_chars: int,
) -> Iterable[list[tuple[dict[str, Any], str]]]:
    current: list[tuple[dict[str, Any], str]] = []
    current_chars = 0
    for item in pending:
        if current and len(current) >= batch_size:
            yield current
            current = []
            current_chars = 0
        rendered_prompt = _render_api_prompt(tokenizer, item["prompt"])
        prompt_chars = len(rendered_prompt)
        if current and current_chars + prompt_chars > max_batch_chars:
            yield current
            current = []
            current_chars = 0
        current.append((item, rendered_prompt))
        current_chars += prompt_chars
        if prompt_chars >= max_batch_chars:
            yield current
            current = []
            current_chars = 0
    if current:
        yield current


def run_api_pool(args: argparse.Namespace) -> None:
    items = load_manifest(args)
    _validate_runtime_contract(args, items, expected_backend="api")
    pending = []
    for item in items:
        done_path = _done_path(args, item["job_id"])
        if not done_path.exists():
            pending.append(item)
            continue
        if _done_result_is_current(args, item):
            continue
        _quarantine_stale_done_result(args, item, known_stale=True)
        pending.append(item)
    print(
        "[llm-extract:api] "
        f"queue={args.queue_name} total={len(items)} pending={len(pending)} endpoints={len(args.api_bases)}"
    )
    if not pending:
        return

    tokenizer = _load_api_tokenizer(args)
    batch_workers = min(
        max(1, int(args.api_parallelism)),
        max(1, len(args.api_bases) * int(args.api_batches_per_endpoint)),
        len(pending),
    )
    configured_capacity = int(getattr(args, "api_queue_capacity", 0) or 0)
    queue_capacity = max(1, configured_capacity or batch_workers * 2)
    print(
        "[llm-extract:api-stream] "
        f"batch_size={args.api_batch_size} max_batch_chars={args.api_max_batch_chars} "
        f"workers={batch_workers} in_flight_capacity={queue_capacity}"
    )

    judge_args = argparse.Namespace(**vars(args))
    judge_args.judge_api_bases = list(args.api_bases)
    judge_args.judge_api_model = args.api_model
    judge_args.judge_api_tokenizer_model = args.api_tokenizer_model
    judge_args.judge_api_timeout = args.api_timeout
    judge_args.judge_api_max_retries = args.api_max_retries
    judge_args.judge_api_endpoint_failure_threshold = getattr(args, "api_endpoint_failure_threshold", 3)
    judge_args.judge_api_endpoint_cooldown_seconds = getattr(
        args, "api_endpoint_cooldown_seconds", 30.0
    )
    judge_args.judge_api_retry_base_delay = getattr(args, "api_retry_base_delay", 0.5)
    api_judge = PersistentJudge(judge_args)
    endpoint_health = api_judge._get_endpoint_health()

    def run_batch(
        pos_batch: tuple[int, list[tuple[dict[str, Any], str]]],
    ) -> tuple[int, list[str]]:
        pos, batch = pos_batch
        try:
            active = list(batch)
            accepted: dict[str, dict[str, Any]] = {}
            last_envelopes: dict[str, dict[str, Any]] = {}
            last_validation_failures: dict[str, dict[str, Any]] = {}
            retry_counts = {item["job_id"]: 0 for item, _ in batch}
            for retry_round, token_limit in enumerate(_judge_retry_token_limits(int(args.judge_max_tokens))):
                envelopes = api_judge._call_api_completion_batch(
                    endpoint_health,
                    pos + retry_round,
                    [rendered_prompt for _, rendered_prompt in active],
                    max_tokens=token_limit,
                    temperature=0.0,
                    top_p=1.0,
                )
                unresolved: list[tuple[dict[str, Any], str]] = []
                for (item, rendered_prompt), envelope in zip(active, envelopes):
                    job_id = item["job_id"]
                    last_envelopes[job_id] = envelope
                    raw = _clean_cell(envelope.get("judge_output"))
                    if _judge_cache_entry_needs_retry(envelope):
                        retry_counts[job_id] += 1
                        last_validation_failures[job_id] = {
                            "status": "invalid",
                            "code": "incomplete_generation",
                            "message": "judge output was empty or truncated",
                            "candidates": [],
                            "contract_version": EXTRACTION_CONTRACT_VERSION,
                        }
                        unresolved.append((item, rendered_prompt))
                        continue
                    try:
                        result = _result_from_judge_output(item, raw)
                    except JudgeOutputValidationError as exc:
                        retry_counts[job_id] += 1
                        last_validation_failures[job_id] = exc.as_dict()
                        unresolved.append((item, rendered_prompt))
                        continue
                    accepted[job_id] = {
                        **result,
                        "judge_model": args.judge_model,
                        "api_endpoint": envelope.get("judge_api_endpoint"),
                        "judge_finish_reason": envelope.get("judge_finish_reason"),
                        "judge_output_token_count": envelope.get("judge_output_token_count"),
                        "judge_api_batch_usage": envelope.get("judge_api_batch_usage"),
                        "judge_api_response_id": envelope.get("judge_api_response_id"),
                        "judge_retry_count": retry_counts[job_id],
                        "judge_max_tokens_used": token_limit,
                    }
                active = unresolved
                if not active:
                    break
            for item, _ in active:
                job_id = item["job_id"]
                envelope = last_envelopes.get(job_id, {})
                raw = _clean_cell(envelope.get("judge_output"))
                error = RuntimeError(
                    f"Extractor produced incomplete or unparseable output after retries for {job_id}: {raw!r}"
                )
                mark_failed(
                    args,
                    item,
                    repr(error),
                    raw_output=raw,
                    validation_failure=last_validation_failures.get(job_id),
                )
            for item, _ in batch:
                result = accepted.get(item["job_id"])
                if result is not None:
                    write_done_result(args, item, result)
            if active:
                return len(active), [
                    f"terminal extraction failure: {item['job_id']}" for item, _ in active
                ]
            return 0, []
        except Exception as exc:
            if len(batch) > 1:
                mid = len(batch) // 2
                left_errors, left_messages = run_batch((pos, batch[:mid]))
                right_errors, right_messages = run_batch((pos + 1, batch[mid:]))
                return left_errors + right_errors, left_messages + right_messages
            mark_failed(args, batch[0][0], repr(exc))
            return 1, [repr(exc)]

    errors = 0
    batch_count = 0
    batch_iterator = enumerate(
        _iter_api_batches(
            pending,
            tokenizer,
            batch_size=max(1, int(args.api_batch_size)),
            max_batch_chars=max(1, int(args.api_max_batch_chars)),
        )
    )
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_workers) as pool:
            in_flight: dict[concurrent.futures.Future[tuple[int, list[str]]], int] = {}

            def submit_next() -> bool:
                nonlocal batch_count
                try:
                    pair = next(batch_iterator)
                except StopIteration:
                    return False
                batch_count += 1
                future = pool.submit(run_batch, pair)
                in_flight[future] = len(pair[1])
                return True

            while len(in_flight) < queue_capacity and submit_next():
                pass
            with tqdm(total=len(pending), desc=f"{args.queue_name} api rows") as progress:
                while in_flight:
                    done, _ = concurrent.futures.wait(
                        tuple(in_flight),
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    for future in done:
                        row_count = in_flight.pop(future)
                        batch_errors, _ = future.result()
                        errors += batch_errors
                        progress.update(row_count)
                    while len(in_flight) < queue_capacity and submit_next():
                        pass
    finally:
        api_judge.cleanup()
    print(
        "[llm-extract:api-stream-done] "
        f"rows={len(pending)} batches={batch_count} errors={errors}"
    )
    if errors:
        raise RuntimeError(f"API extraction finished with {errors} failed rows")


def _load_results(args: argparse.Namespace, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    missing = []
    for item in items:
        path = _done_path(args, item["job_id"])
        if not _done_result_is_current(args, item):
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


def _cached_prediction_table(
    cache: dict[tuple[str, str], pd.DataFrame],
    args: argparse.Namespace,
    benchmark: str,
    model_slug: str,
) -> pd.DataFrame:
    key = (benchmark, model_slug)
    if key not in cache:
        cache[key] = _load_prediction_table(_prediction_path(args.run_root, benchmark, model_slug))
    return cache[key]


def _score_with_category_breakdowns(
    group: list[dict[str, Any]],
    args: argparse.Namespace,
    benchmark: str,
    score: float,
    rows: list[dict[str, Any]],
    prediction_cache: dict[tuple[str, str], pd.DataFrame],
) -> dict[str, Any]:
    scores: dict[str, Any] = {"Overall": score}
    enriched = []
    for row in rows:
        original = _cached_prediction_table(
            prediction_cache,
            args,
            benchmark,
            row["model_slug"],
        ).iloc[int(row["ordinal"])].to_dict()
        enriched.append({**original, **row})
    for col in ("category", "subfield", "reasoning_type", "task", "l2-category"):
        vals: dict[str, list[float]] = {}
        for row in enriched:
            if col in row and _clean_cell(row.get(col)):
                vals.setdefault(_clean_cell(row.get(col)), []).append(float(row.get("eval_score", 0.0)))
        for key, values in sorted(vals.items()):
            scores[f"{col}/{key}"] = float(sum(values) / len(values) * 100.0) if values else 0.0
    return scores


def _score_visiongraph(
    group: list[dict[str, Any]],
    args: argparse.Namespace,
    prediction_cache: dict[tuple[str, str], pd.DataFrame],
) -> tuple[float, list[dict[str, Any]], dict[str, Any]]:
    vlmeval_root = REPO_ROOT / "external" / "VLMEvalKit"
    if str(vlmeval_root) not in sys.path:
        sys.path.insert(0, str(vlmeval_root))
    from vlmeval.dataset.visiongraph import _score_row

    rows = []
    scores_by_task: dict[str, list[float]] = {}
    for item in group:
        original = _cached_prediction_table(
            prediction_cache,
            args,
            "visiongraph_q3",
            item["model_slug"],
        ).iloc[int(item["ordinal"])].to_dict()
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


def _score_chartqapro(
    group: list[dict[str, Any]],
    args: argparse.Namespace,
    prediction_cache: dict[tuple[str, str], pd.DataFrame],
) -> tuple[float, list[dict[str, Any]], dict[str, Any]]:
    scripts_root = REPO_ROOT / "external" / "VLMEvalKit" / "scripts"
    vlmeval_root = REPO_ROOT / "external" / "VLMEvalKit"
    for path in (vlmeval_root, scripts_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    import batched_chartqapro_vllm as chartqapro

    # Rejoin extracted answers with the original metadata because ChartQAPro's
    # evaluator needs question_type/year fields.
    rows = []
    for item in group:
        original = _cached_prediction_table(
            prediction_cache,
            args,
            "chartqapro",
            item["model_slug"],
        ).iloc[int(item["ordinal"])].to_dict()
        out = {**original, **item, "llm_extracted_answer": item["extracted"]}
        rows.append(out)
    scores = chartqapro.evaluate_rows(rows, "llm_extracted_answer")
    overall = float(scores.get("Overall", 0.0)) * 100.0
    for row in rows:
        row["eval_pred"] = row["llm_extracted_answer"]
    return overall, rows, scores


def _archive_extracted_group(
    args: argparse.Namespace,
    *,
    benchmark: str,
    model_slug: str,
    model_path: str,
    manifest_items: dict[str, dict[str, Any]],
    exclusions: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> tuple[Path | None, Path | None]:
    if not os.environ.get("TRACE_FINAL25_HF_SPOOL_ROOT", "").strip():
        return None, None
    from final25_archive_hooks import emit_extraction_slice, emit_score_slice

    spec = spec_by_key(benchmark)
    extraction_records: list[dict[str, Any]] = []
    score_records: list[dict[str, Any]] = []
    for row in rows:
        item = manifest_items[row["job_id"]]
        common = {
            "source_index": str(row["index"]),
            "source_ordinal": int(row["ordinal"]),
            "source_row_hash": item.get("source_row_hash")
            or _canonical_hash(
                {
                    "index": item["index"],
                    "question": item["question"],
                    "answer": item["answer"],
                    "prediction": item["prediction"],
                }
            ),
            "question": item["question"],
            "ground_truth": item["answer"],
            "options": item.get("options") or {},
            "metadata": {"answer_kind": item["answer_kind"], "job_id": item["job_id"]},
        }
        extraction_records.append(
            {
                **common,
                "request_hash": item["request_hash"],
                "model_response": item["prediction"],
                "judge_prompt": item["prompt"],
                "judge_response": row.get("judge_output", ""),
                "normalized_extraction": {
                    "status": row.get("extraction_status", "resolved"),
                    "value": row.get("extracted"),
                    "raw": row.get("extracted_raw"),
                    "raw_value": row.get("extracted_raw"),
                    "method": row.get("extraction_method"),
                    "candidates": row.get("extraction_candidates") or [],
                    "explicit_abstention": bool(row.get("explicit_abstention", False)),
                    "answer_kind": item["answer_kind"],
                    "judge_score": row.get("judge_score"),
                    "response_hash": item.get("response_sha256")
                    or _sha256_bytes(_clean_cell(item.get("prediction")).encode("utf-8")),
                    "contract_version": row.get(
                        "validation_contract_version", EXTRACTION_CONTRACT_VERSION
                    ),
                },
                "retries": {
                    "count": int(row.get("judge_retry_count") or 0),
                    "recovered_from_failed_output": bool(row.get("recovered_from_failed_output", False)),
                    "finish_reason": row.get("judge_finish_reason"),
                    "max_tokens_used": row.get("judge_max_tokens_used"),
                },
            }
        )
        prediction = row.get("eval_pred", row.get("extracted", ""))
        score_value = row.get("eval_score")
        score_request_hash = _canonical_hash(
            {
                "contract_version": "trace-final25-score-v1",
                "extraction_request_hash": item["request_hash"],
                "prediction": prediction,
                "score": score_value,
                "scorer": summary.get("run_name", "llm_extracted"),
            }
        )
        score_records.append(
            {
                **common,
                "request_hash": score_request_hash,
                "prediction": prediction,
                "score": score_value,
                "scorer": summary.get("run_name", "llm_extracted"),
                "excluded": False,
            }
        )

    for excluded in exclusions:
        common = {
            "source_index": str(excluded["index"]),
            "source_ordinal": int(excluded["ordinal"]),
            "source_row_hash": excluded["source_row_hash"],
            "question": excluded.get("question"),
            "ground_truth": excluded.get("answer"),
            "metadata": {"exclusion_reason": excluded["reason"]},
        }
        extraction_records.append(
            {
                **common,
                "request_hash": excluded["request_hash"],
                "model_response": excluded.get("prediction", ""),
                "judge_prompt": "",
                "judge_response": "",
                "normalized_extraction": {
                    "status": "excluded",
                    "value": None,
                    "reason": excluded["reason"],
                },
                "retries": {"count": 0},
            }
        )
        score_records.append(
            {
                **common,
                "request_hash": _canonical_hash(
                    {
                        "contract_version": "trace-final25-score-v1",
                        "extraction_request_hash": excluded["request_hash"],
                        "excluded": excluded["reason"],
                    }
                ),
                "prediction": None,
                "score": None,
                "scorer": summary.get("run_name", "llm_extracted"),
                "excluded": {"reason": excluded["reason"]},
            }
        )

    from final25_archive_hooks import resolve_model_revision, resolve_model_source

    archive_identity = {
        "model": resolve_model_source(model_slug, model_path),
        "model_slug": model_slug,
        "model_revision": resolve_model_revision(model_slug, model_path),
        "seed": int(args.seed),
        "benchmark": benchmark,
        "dataset_alias": spec.alias,
        "dataset_split": spec.split or "default",
        "dataset_revision": os.environ.get(
            "TRACE_FINAL25_DATASET_REVISION",
            os.environ.get("TRACE_VLMEVALKIT_GIT_COMMIT", "unknown"),
        ),
    }
    extraction_path = emit_extraction_slice(
        records=extraction_records,
        contract_version=EXTRACTION_CONTRACT_VERSION,
        aggregate={
            "rows": len(rows),
            "excluded_rows": len(exclusions),
            "judge_model": args.judge_model,
        },
        **archive_identity,
    )
    score_archive_path = emit_score_slice(
        records=score_records,
        contract_version="trace-final25-score-v1",
        aggregate=summary,
        **archive_identity,
    )
    return extraction_path, score_archive_path


def _write_benchmark_score_mirrors(
    args: argparse.Namespace,
    *,
    benchmark: str,
    model_slug: str,
    summary: dict[str, Any],
) -> tuple[Path, ...]:
    if args.benchmark_root is None:
        return ()

    canonical_path = score_path(spec_by_key(benchmark), model_slug, args.benchmark_root)
    extracted_path = args.benchmark_root / benchmark / model_slug / "llm_extracted" / "scores.json"
    summary["benchmark_score_path"] = str(canonical_path)
    summary["llm_extracted_benchmark_score_path"] = str(extracted_path)

    destinations = tuple(dict.fromkeys((canonical_path, extracted_path)))
    for destination in destinations:
        write_json(destination, summary)
    return destinations


def finalize(args: argparse.Namespace) -> None:
    items = load_manifest(args)
    results = _load_results(args, items)
    out_root = args.output_root / args.queue_name / "scores"
    summary_rows = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        groups[(result["benchmark"], result["model_slug"])].append(result)
    prediction_cache: dict[tuple[str, str], pd.DataFrame] = {}
    manifest_summary = load_json(args.output_root / args.queue_name / "manifest_summary.json", {})
    source_exclusions = manifest_summary.get("source_row_exclusions") or []
    manifest_items = {item["job_id"]: item for item in items}
    for benchmark in args.benchmarks:
        for model_slug, model_path in args.model_entries:
            group = groups.get((benchmark, model_slug), [])
            if not group:
                continue
            if benchmark == "chartqapro":
                score, rows, extra_scores = _score_chartqapro(group, args, prediction_cache)
            elif benchmark == "physics":
                score, rows, extra_scores = _score_binary_judge(group)
                extra_scores = _score_with_category_breakdowns(
                    group,
                    args,
                    benchmark,
                    score,
                    rows,
                    prediction_cache,
                )
            elif benchmark == "visiongraph_q3":
                score, rows, extra_scores = _score_visiongraph(group, args, prediction_cache)
            else:
                score, rows = _score_option_or_number(group)
                extra_scores = _score_with_category_breakdowns(
                    group,
                    args,
                    benchmark,
                    score,
                    rows,
                    prediction_cache,
                )
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
                _write_benchmark_score_mirrors(
                    args,
                    benchmark=benchmark,
                    model_slug=model_slug,
                    summary=summary,
                )
            write_json(score_dir / "scores.json", summary)
            archive_paths = _archive_extracted_group(
                args,
                benchmark=benchmark,
                model_slug=model_slug,
                model_path=model_path,
                manifest_items=manifest_items,
                exclusions=[
                    exclusion
                    for exclusion in source_exclusions
                    if exclusion.get("benchmark") == benchmark and exclusion.get("model_slug") == model_slug
                ],
                rows=rows,
                summary=summary,
            )
            if any(archive_paths):
                summary["archive_descriptors"] = [str(path) for path in archive_paths if path is not None]
                if args.benchmark_root is not None:
                    _write_benchmark_score_mirrors(
                        args,
                        benchmark=benchmark,
                        model_slug=model_slug,
                        summary=summary,
                    )
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
    parser.add_argument("--seed", type=int, default=int(os.environ.get("TRACE_FINAL25_SEED", "42")))
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
    parser.add_argument(
        "--execution-backend",
        choices=("api", "local"),
        default="api",
        help="Backend bound into prepared extraction request hashes.",
    )
    parser.add_argument("--api-base", action="append", dest="api_bases")
    parser.add_argument("--api-model", default="qwen3-32b-judge")
    parser.add_argument("--api-tokenizer-model", default="Qwen/Qwen3-32B")
    parser.add_argument("--api-parallelism", type=int, default=128)
    parser.add_argument("--api-batch-size", type=int, default=16)
    parser.add_argument("--api-batches-per-endpoint", type=int, default=1)
    parser.add_argument("--api-max-batch-chars", type=int, default=24000)
    parser.add_argument(
        "--api-queue-capacity",
        type=int,
        default=0,
        help="Maximum rendered batches kept in flight; 0 uses twice the active worker count.",
    )
    parser.add_argument("--api-timeout", type=float, default=120.0)
    parser.add_argument("--api-max-retries", type=int, default=5)
    parser.add_argument("--api-endpoint-failure-threshold", type=int, default=3)
    parser.add_argument("--api-endpoint-cooldown-seconds", type=float, default=30.0)
    parser.add_argument("--api-retry-base-delay", type=float, default=0.5)
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
