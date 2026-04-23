#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from datasets import load_dataset
from tqdm import tqdm

from lmms_eval.tasks._task_utils.answer_extraction import extract_final_answer
from lmms_eval.tasks._task_utils.response_truncation import truncate_response_tail_tiktoken
from lmms_eval.tasks._task_utils.vllm_judge import extract_json_candidate, get_judge_engine
from lmms_eval.tasks.mathvista.mathvista_evals import DEMO_PROMPT, MathVistaEvaluator


def _extract_raw_response(sample: dict[str, Any]) -> str:
    resps = sample.get("resps")
    if isinstance(resps, list) and resps:
        first = resps[0]
        if isinstance(first, list) and first:
            item = first[0]
            return "" if item is None else str(item)
        return "" if first is None else str(first)
    filtered = sample.get("filtered_resps")
    if isinstance(filtered, list) and filtered:
        return "" if filtered[0] is None else str(filtered[0])
    return ""


def _load_samples(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _maybe_from_json(text: str) -> str:
    parsed = extract_json_candidate(text)
    if parsed:
        for key in ("Extracted answer", "extracted_answer", "answer"):
            value = parsed.get(key)
            if value not in (None, {}):
                try:
                    return str(value)
                except Exception:
                    pass
    return text


def _direct_extract(prediction: str, problem: dict[str, Any]) -> str | None:
    if not prediction:
        return ""

    response = _maybe_from_json(prediction)
    response = truncate_response_tail_tiktoken(response)

    if problem["question_type"] == "multi_choice" and response in (problem.get("choices") or []):
        return response

    if problem["answer_type"] == "integer":
        try:
            return str(int(response))
        except Exception:
            pass

    if problem["answer_type"] == "float":
        try:
            return str(float(response))
        except Exception:
            pass

    return None


def _judge_extraction_from_output(raw_output: str) -> str:
    parsed = extract_json_candidate(raw_output)
    if parsed is None:
        return raw_output.strip()
    for key in ("Extracted answer", "extracted_answer", "answer"):
        value = parsed.get(key)
        if value not in (None, {}):
            try:
                return str(value)
            except Exception:
                pass
    return raw_output.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", required=True, help="JSONL from lmms_eval --predict_only --log_samples")
    parser.add_argument("--output", required=True, help="Output JSON summary path")
    parser.add_argument("--dataset-path", default="AI4Math/MathVista")
    parser.add_argument("--split", default="testmini")
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    sample_path = Path(args.samples)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    samples = _load_samples(sample_path)
    if args.limit is not None:
        samples = samples[: args.limit]

    dataset = load_dataset(args.dataset_path, split=args.split, token=True)
    evaluator = MathVistaEvaluator()
    judge = get_judge_engine(args.judge_model)

    rows: list[dict[str, Any]] = []
    pending_prompts: list[str] = []
    pending_indices: list[int] = []

    for sample in samples:
        doc = dataset[int(sample["doc_id"])]
        raw_response = _extract_raw_response(sample)
        prediction = extract_final_answer(raw_response.strip())
        problem = {
            "question_type": doc["question_type"],
            "answer_type": doc["answer_type"],
            "query": doc["query"],
            "choices": doc["choices"],
            "answer": doc["answer"] if "answer" in doc else None,
            "precision": doc["precision"] if "precision" in doc else 0,
        }

        direct = _direct_extract(prediction, problem)
        row = {
            "doc_id": int(sample["doc_id"]),
            "question_id": doc["pid"],
            "query": doc["query"],
            "answer": problem["answer"],
            "raw_response": raw_response,
            "initial_prediction": prediction,
            "judge_extraction": "",
            "prediction": "",
            "score": 0.0,
            "used_judge": False,
        }
        rows.append(row)

        if direct is not None:
            row["judge_extraction"] = direct
            continue

        response = _maybe_from_json(prediction)
        response = truncate_response_tail_tiktoken(response)
        pending_prompts.append(evaluator.create_test_prompt(DEMO_PROMPT, problem["query"], response))
        pending_indices.append(len(rows) - 1)

    for start in tqdm(range(0, len(pending_prompts), args.batch_size), desc="Judge extracting"):
        batch_prompts = pending_prompts[start : start + args.batch_size]
        raw_outputs = judge.generate_json_batch(batch_prompts, max_tokens=args.max_tokens, use_tqdm=False)
        for row_idx, raw_output in zip(pending_indices[start : start + args.batch_size], raw_outputs):
            rows[row_idx]["used_judge"] = True
            rows[row_idx]["judge_extraction"] = _judge_extraction_from_output(raw_output)

    scores: list[float] = []
    for row in rows:
        doc = dataset[int(row["doc_id"])]
        problem = {
            "question_type": doc["question_type"],
            "answer_type": doc["answer_type"],
            "choices": doc["choices"],
            "answer": doc["answer"] if "answer" in doc else None,
            "precision": doc["precision"] if "precision" in doc else 0,
        }
        normalized = evaluator.normalize_extracted_answer(
            row["judge_extraction"],
            problem["choices"],
            problem["question_type"],
            problem["answer_type"],
            problem["precision"],
        )
        score = 1.0 if evaluator.safe_equal(normalized, problem["answer"]) else 0.0
        row["prediction"] = normalized
        row["score"] = score
        scores.append(score)

    mean_score = (sum(scores) / len(scores)) if scores else 0.0
    stderr = 0.0
    if len(scores) > 1:
        mean = mean_score
        variance = sum((x - mean) ** 2 for x in scores) / (len(scores) - 1)
        stderr = (variance / len(scores)) ** 0.5

    with output_path.open("w") as handle:
        json.dump(
            {
                "samples_file": str(sample_path),
                "count": len(scores),
                "submission": mean_score,
                "submission_stderr": stderr,
                "details_file": str(output_path.with_suffix(".jsonl")),
            },
            handle,
            indent=2,
        )

    with output_path.with_suffix(".jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
