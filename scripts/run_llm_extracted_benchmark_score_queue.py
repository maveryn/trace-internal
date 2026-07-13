#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

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
    run_dir,
    spec_by_key,
    write_json,
)
from run_external_benchmark_score_queue import PersistentJudge  # noqa: E402


DEFAULT_BENCHMARKS = (
    "blink",
    "chartqapro",
    "game_qa_lite",
    "countbenchqa",
    "erqa",
    "vstarbench",
    "cvbench_3d",
)
DEFAULT_MODELS = (
    ("qwen25vl7b-base", "Qwen/Qwen2.5-VL-7B-Instruct"),
    (
        "trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500",
        "/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500",
    ),
)


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
        match = re.match(r"^\s*([A-H])\s*[\.\)]\s*(.+?)\s*$", line)
        if not match:
            continue
        letter, text = match.groups()
        # Some datasets wrap long options onto following indented lines. Keep
        # this conservative so normal prompt text is not pulled into a choice.
        extra = []
        for nxt in lines[i + 1 :]:
            if re.match(r"^\s*[A-H]\s*[\.\)]\s+", nxt):
                break
            if not nxt.startswith((" ", "\t")):
                break
            extra.append(nxt.strip())
        options[letter] = " ".join([text.strip(), *extra]).strip()
    return options


def _valid_letters_for(benchmark: str, row: dict[str, Any]) -> str:
    explicit = "".join(_option_columns(row, "ABCDEFG").keys())
    if explicit:
        return explicit
    embedded = "".join(_embedded_option_columns(_question_for(benchmark, row)).keys())
    if embedded:
        return embedded
    answer = _clean_cell(row.get("answer")).upper()
    if benchmark == "erqa":
        return "ABCD"
    if len(answer) == 1 and answer in "ABCDEFG":
        return "ABCDEFG"[: max("ABCDEFG".index(answer) + 1, 4)]
    return "ABCDEFG"


def _question_for(benchmark: str, row: dict[str, Any]) -> str:
    question = _clean_cell(row.get("question"))
    if benchmark == "cvbench_3d" and _clean_cell(row.get("prompt")):
        question = _clean_cell(row.get("prompt"))
    return question


def _answer_kind(benchmark: str, row: dict[str, Any]) -> str:
    answer = _clean_cell(row.get("answer"))
    if benchmark == "countbenchqa":
        return "number"
    if benchmark == "chartqapro":
        return "short"
    if benchmark == "game_qa_lite":
        # Game-QA-Lite mixes MCQ, numeric, coordinate, and short-text answers.
        if re.fullmatch(r"[A-H]", answer.strip(), flags=re.I):
            return "option"
        if re.fullmatch(r"-?\d+(?:\.\d+)?", answer.strip()):
            return "number"
        return "short"
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
    if kind == "number":
        return (
            "You are extracting the final numeric answer from a visual counting benchmark response.\n"
            "Do not judge correctness. Extract only the count stated as the final answer.\n"
            "If no count is selected, return an empty string.\n\n"
            f"Question:\n{question}\n\n"
            f"Model response:\n{response}\n\n"
            "Return exactly one JSON object: {\"answer\": \"<integer>\"}."
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


def _build_items(args: argparse.Namespace) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
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
                    options = _embedded_option_columns(_question_for(benchmark, row))
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
                    "answer_kind": _answer_kind(benchmark, row),
                    "valid_letters": list(valid_letters),
                    "options": options,
                    "prediction_table": str(pred_path),
                }
                item["prompt"] = _build_prompt(item)
                items.append(item)
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


def mark_done(args: argparse.Namespace, item: dict[str, Any], result: dict[str, Any]) -> None:
    done_path = _done_path(args, item["job_id"])
    done_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(done_path, result)
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


def normalize_extracted(item: dict[str, Any], value: str) -> str:
    kind = item["answer_kind"]
    if kind == "option":
        return _normalize_option(value, item["valid_letters"])
    if kind == "number":
        return _normalize_number(value)
    return _clean_short(value)


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
                    parsed = _parse_json_answer(raw)
                    normalized = normalize_extracted(item, parsed)
                    mark_done(
                        args,
                        item,
                        {
                            **{k: item[k] for k in ("job_id", "benchmark", "model_slug", "index", "ordinal", "answer", "answer_kind")},
                            "valid_letters": item.get("valid_letters"),
                            "extracted_raw": parsed,
                            "extracted": normalized,
                            "judge_output": raw,
                            "judge_model": args.judge_model,
                            "prediction": item["prediction"],
                        },
                    )
                except Exception as exc:
                    mark_failed(args, item, repr(exc))
    finally:
        judge.cleanup()


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
        elif item["answer_kind"] == "number":
            gt = _normalize_number(answer)
            pred = _normalize_number(item.get("extracted", ""))
        else:
            gt = _normalize_short_for_exact(answer)
            pred = _normalize_short_for_exact(item.get("extracted", ""))
        hit = int(bool(gt) and pred == gt)
        correct += hit
        rows.append({**item, "eval_gt": gt, "eval_pred": pred, "eval_score": hit})
    return (correct / len(rows) * 100.0 if rows else 0.0), rows


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
    for benchmark in args.benchmarks:
        for model_slug, model_path in args.model_entries:
            group = [r for r in results if r["benchmark"] == benchmark and r["model_slug"] == model_slug]
            if not group:
                continue
            if benchmark == "chartqapro":
                score, rows, extra_scores = _score_chartqapro(group, args)
            else:
                score, rows = _score_option_or_number(group)
                extra_scores = {"Overall": score}
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
                "score": score,
                "scores": extra_scores,
                "judge_model": args.judge_model,
                "artifacts": {"judged_table": str(score_dir / "llm_extracted_judged.xlsx")},
            }
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
    parser.add_argument("--model-entry", action="append", type=parse_model_entry, dest="model_entries")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--queue-root", type=Path, default=DEFAULT_QUEUE_ROOT)
    parser.add_argument("--output-root", type=Path, default=LIB_REPO_ROOT / "benchmark" / "llm_extracted")
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
    parser.add_argument("--finalize", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.model_entries:
        args.model_entries = list(DEFAULT_MODELS)
    if args.prepare:
        items = _build_items(args)
        write_manifest(args, items)
        print(f"[llm-extract:prepare] rows={len(items)} manifest={_manifest_path(args)}")
    if args.worker:
        run_worker(args)
    if args.finalize:
        finalize(args)


if __name__ == "__main__":
    main()
