#!/usr/bin/env python3
"""Score judge-deferred VERO samples without rerunning the vision model."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

from tqdm import tqdm


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = REPO_ROOT / "runs/external_benchmarks/qwen25vl7b/20260522T062435Z"
DEFAULT_VERO_ROOT = Path("/home/jovyan/work/vero/vero-eval")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def latest_samples(bench_dir: Path) -> Path:
    files = sorted(bench_dir.glob("*_samples_*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No samples JSONL found in {bench_dir}")
    return files[-1]


def generation_samples(bench_dir: Path) -> Path:
    """Return the original response sample file, not a judge-only rerun artifact."""

    files = sorted(bench_dir.glob("*_samples_*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No samples JSONL found in {bench_dir}")
    candidates: list[Path] = []
    for path in files:
        if "direct_judge" in path.name:
            continue
        rows = read_jsonl(path)
        if not rows:
            continue
        first = rows[0]
        if "bypass" in first:
            return path
        if not any(key in first for key in ("judge_accuracy", "llm_as_judge_eval", "simplevqa_acc")):
            candidates.append(path)
    return candidates[0] if candidates else files[0]


def selected_rows(bench_dir: Path, max_samples: int, *, source: str = "latest") -> list[dict[str, Any]]:
    sample_path = generation_samples(bench_dir) if source == "generation" else latest_samples(bench_dir)
    rows = read_jsonl(sample_path)
    manifest = read_jsonl(bench_dir / "sample_manifest.jsonl")
    selected_ids = [row.get("original_index") for row in manifest if row.get("original_index") is not None]
    if not selected_ids:
        selected_ids = [row.get("sample_doc_id") for row in manifest if row.get("sample_doc_id") is not None]
    if not selected_ids:
        selected_ids = [row.get("doc_id") for row in manifest if row.get("doc_id") is not None]
    if selected_ids and len(selected_ids) <= max_samples:
        wanted = {int(value) for value in selected_ids if isinstance(value, int)}
        rows = [row for row in rows if row.get("doc_id") in wanted]
    return rows[:max_samples]


def first_response(row: dict[str, Any]) -> str:
    value = row.get("filtered_resps")
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        item = value[0]
        if isinstance(item, str):
            return item
        if isinstance(item, list) and item and isinstance(item[0], str):
            return item[0]
    return ""


def setup_imports(vero_root: Path) -> None:
    if str(vero_root) not in sys.path:
        sys.path.insert(0, str(vero_root))


def score_mathvista(rows: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    from lmms_eval.tasks._task_utils.answer_extraction import extract_final_answer
    from lmms_eval.tasks.mathvista.utils import get_mathvista_evaluator

    evaluator = get_mathvista_evaluator()
    scored: list[dict[str, Any]] = []
    for row in tqdm(rows, desc="MathVista judge"):
        base = dict(row.get("submission") or row.get("llm_as_judge_eval") or {})
        raw_prediction = first_response(row)
        prediction_text = extract_final_answer(raw_prediction.strip())
        problem = {
            "question_type": base.get("question_type"),
            "answer_type": base.get("answer_type"),
            "query": base.get("query") or row.get("input") or "",
            "choices": base.get("choices"),
            "answer": base.get("answer") if "answer" in base else row.get("target"),
            "precision": base.get("precision", 0),
        }
        extraction = evaluator.extract_answer(prediction_text, problem, quick_extract=False)
        prediction = evaluator.normalize_extracted_answer(
            extraction,
            problem["choices"],
            problem["question_type"],
            problem["answer_type"],
            problem["precision"],
        )
        correct = evaluator.safe_equal(prediction, problem["answer"]) if problem["answer"] is not None else False
        result = dict(base)
        result.update(
            {
                "extraction": extraction,
                "prediction": prediction,
                "true_false": bool(correct),
            }
        )
        out = dict(row)
        out["llm_as_judge_eval"] = result
        out["submission"] = result
        out["individual_score"] = 1.0 if correct else 0.0
        out["extracted_answer"] = prediction
        scored.append(out)
    accuracy = round(sum(row["individual_score"] for row in scored) / len(scored), 4) if scored else 0.0
    return accuracy, scored


def score_mathvision(rows: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    from lmms_eval.llm_judge.utils import JudgePromptBuilder, ResponseParser
    from lmms_eval.tasks._task_utils.answer_extraction import extract_final_answer
    from lmms_eval.tasks._task_utils.response_truncation import truncate_response_tail_tiktoken
    from lmms_eval.tasks._task_utils.vllm_judge import get_judge_engine

    engine = get_judge_engine(os.getenv("JUDGE_MODEL_PATH") or os.getenv("MODEL_VERSION") or "Qwen/Qwen3-32B")
    prompts: list[str] = []
    metadata: list[tuple[dict[str, Any], str]] = []
    for row in rows:
        model_answer = truncate_response_tail_tiktoken(extract_final_answer(first_response(row)))
        question = str(row.get("input") or "").replace("<image1>", "").strip()
        answer = str(row.get("target") or "")
        prompts.append(
            JudgePromptBuilder.build_binary_prompt(
                question=question,
                answer=answer,
                prediction=model_answer,
                output_format="0/1",
            )
        )
        metadata.append((row, model_answer))
    raw_outputs = engine.generate_json_batch(prompts, max_tokens=512, use_tqdm=True)
    scored: list[dict[str, Any]] = []
    for (row, model_answer), raw in zip(metadata, raw_outputs):
        correct = bool(ResponseParser.parse_binary_response(raw, "0/1"))
        result = {
            "response": [first_response(row)],
            "scores": [correct],
            "resp_key": str(row.get("doc_id")),
            "judge_output": raw,
            "extracted_answer": model_answer,
        }
        out = dict(row)
        out["llm_as_judge_eval"] = 1.0 if correct else 0.0
        out["mathvision_standard_eval"] = result
        out["individual_score"] = 1.0 if correct else 0.0
        scored.append(out)
    accuracy = round(sum(row["individual_score"] for row in scored) / len(scored), 4) if scored else 0.0
    return accuracy, scored


def score_simplevqa(rows: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    from lmms_eval.tasks.simplevqa.utils import simplevqa_aggregate_results

    payloads = []
    for row in rows:
        prediction = first_response(row)
        payloads.append(
            {
                "resp_key": str(row.get("doc_id")),
                "question": row.get("input") or "",
                "answer": row.get("target") or "",
                "prediction": prediction,
                "model_response": prediction,
                "reference": row.get("target") or "",
                "predictions": [prediction],
                "raw_predictions": [prediction],
            }
        )
    accuracy = float(simplevqa_aggregate_results(payloads))
    details = getattr(simplevqa_aggregate_results, "details", [])
    score_by_key = {str(item.get("resp_key") or idx): item for idx, item in enumerate(details)}
    scored: list[dict[str, Any]] = []
    for row in rows:
        key = str(row.get("doc_id"))
        detail = score_by_key.get(key, {})
        out = dict(row)
        out["simplevqa_acc"] = {
            "score": float(detail.get("score", 0.0)),
            "judge_output": detail.get("judge_output"),
            "judge_res": detail.get("judge_res"),
        }
        out["individual_score"] = float(detail.get("score", 0.0))
        scored.append(out)
    return round(accuracy, 4), scored


def score_chartmuseum(rows: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    from lmms_eval.tasks.chartmuseum.utils import (
        chartmuseum_aggregate_judge_results,
        chartmuseum_process_results,
    )

    payloads = []
    row_by_key: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(rows):
        question = str(row.get("input") or "").split("\n", 1)[0].strip()
        resp_key = str(row.get("doc_id") if row.get("doc_id") is not None else idx)
        payload = chartmuseum_process_results(
            {
                "id": resp_key,
                "question": question,
                "answer": row.get("target"),
                "reasoning_type": row.get("reasoning_type"),
                "source": row.get("source"),
            },
            [first_response(row)],
        )["judge_accuracy"]
        payloads.append(payload)
        row_by_key[resp_key] = row
    accuracy = float(chartmuseum_aggregate_judge_results(payloads))
    details = getattr(chartmuseum_aggregate_judge_results, "individual_scores", {})
    scored: list[dict[str, Any]] = []
    for key, row in row_by_key.items():
        detail = details.get(str(key), {})
        out = dict(row)
        out["judge_accuracy"] = detail
        out["individual_score"] = float(detail.get("score", 0.0))
        out["extracted_answer"] = detail.get("extracted_answer", first_response(row))
        scored.append(out)
    return round(accuracy, 4), scored


SCORERS = {
    "chartmuseum": ("judge_accuracy", score_chartmuseum),
    "mathvista_testmini": ("llm_as_judge_eval", score_mathvista),
    "mathvision": ("llm_as_judge_eval", score_mathvision),
    "simplevqaen": ("simplevqa_acc", score_simplevqa),
}


def score_benchmark(run_dir: Path, benchmark: str, max_samples: int) -> dict[str, Any]:
    bench_dir = run_dir / benchmark
    metric, scorer = SCORERS[benchmark]
    source = "generation" if benchmark == "chartmuseum" else "latest"
    rows = selected_rows(bench_dir, max_samples, source=source)
    accuracy, scored = scorer(rows)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    samples_path = bench_dir / f"{stamp}_samples_{benchmark}_direct_judge.jsonl"
    results_path = bench_dir / f"{stamp}_direct_judge_results.json"
    write_jsonl(samples_path, scored)
    write_json(
        results_path,
        {
            "results": {
                benchmark: {
                    "alias": benchmark,
                    f"{metric},none": accuracy,
                    f"{metric}_stderr,none": "N/A",
                }
            },
            "date": stamp,
            "judge_direct_from_samples": True,
            "n-samples": {benchmark: {"original": len(scored), "effective": len(scored)}},
        },
    )
    summary_path = bench_dir / "run_summary.json"
    summary = read_json(summary_path, {})
    summary.update(
        {
            "judge_deferred": False,
            "judge_metrics_enabled": True,
            "judge_direct_from_samples": True,
            "judge_metric": metric,
            "judge_score": accuracy,
            "judge_datetime": stamp,
            "judge_results_path": str(results_path),
            "judge_samples_path": str(samples_path),
            "sample_summary": {
                **(summary.get("sample_summary") or {}),
                "total_selected": len(scored),
            },
            "response_stats": {
                "responses_total": len(scored),
                "responses_empty": sum(1 for row in scored if not first_response(row).strip()),
            },
        }
    )
    write_json(summary_path, summary)
    return {
        "benchmark": benchmark,
        "metric": metric,
        "accuracy": accuracy,
        "samples": len(scored),
        "results_path": str(results_path),
    }


def update_manifest(run_dir: Path) -> None:
    manifest_path = run_dir / "RUN_MANIFEST.json"
    manifest = read_json(manifest_path, {})
    by_key = {row.get("benchmark"): row for row in manifest.get("benchmarks", []) if isinstance(row, dict)}
    for summary_path in sorted(run_dir.glob("*/run_summary.json")):
        summary = read_json(summary_path, {})
        key = summary.get("benchmark")
        if key:
            by_key[key] = summary
    manifest["benchmarks"] = list(by_key.values())
    write_json(manifest_path, manifest)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--vero-root", type=Path, default=DEFAULT_VERO_ROOT)
    parser.add_argument("--benchmarks", nargs="+", default=["mathvista_testmini", "mathvision", "simplevqaen"])
    parser.add_argument("--max-samples", type=int, default=500)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_imports(args.vero_root)
    results = []
    for benchmark in args.benchmarks:
        if benchmark not in SCORERS:
            raise SystemExit(f"Unsupported benchmark for direct judge scoring: {benchmark}")
        results.append(score_benchmark(args.run_dir, benchmark, args.max_samples))
    update_manifest(args.run_dir)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
