#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from datasets import load_dataset
from tqdm import tqdm

from lmms_eval.tasks._task_utils.answer_extraction import extract_final_answer
from lmms_eval.tasks._task_utils.answer_parsing import EXTRACT_ANSWER_PROMPT
from lmms_eval.tasks._task_utils.vllm_judge import (
    extract_json_candidate,
    get_judge_engine,
)


SCRIPT_DIR = Path(__file__).resolve().parent
EVAL_ROOT = SCRIPT_DIR.parent
ERQA_TASK_DIR = EVAL_ROOT / "vendor/vero_eval/lmms_eval/tasks/erqa"
ERQA_UTILS_PATH = ERQA_TASK_DIR / "utils.py"


def _load_erqa_utils():
    spec = importlib.util.spec_from_file_location(
        "trace_eval_erqa_utils",
        ERQA_UTILS_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load ERQA utils from {ERQA_UTILS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


erqa_utils = _load_erqa_utils()


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


def _build_extraction_prompt(question: str, response: str) -> str:
    return (
        EXTRACT_ANSWER_PROMPT.replace("<|question|>", question or "")
        .replace("<|response|>", response)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--samples",
        required=True,
        help="Single lmms_eval sample JSONL from --predict_only --log_samples",
    )
    parser.add_argument("--output", required=True, help="Output JSON summary path")
    parser.add_argument("--dataset-path", default="FlagEval/ERQA")
    parser.add_argument("--split", default="test")
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    sample_path = Path(args.samples)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    samples = _load_samples(sample_path)
    if args.limit is not None:
        samples = samples[: args.limit]

    dataset = load_dataset(args.dataset_path, split=args.split, token=True)
    judge = get_judge_engine(args.judge_model)

    rows: list[dict[str, Any]] = []
    prompts: list[str] = []

    for sample in samples:
        doc = dataset[int(sample["doc_id"])]
        raw_response = _extract_raw_response(sample)
        parsed_response = extract_final_answer(raw_response.strip())
        question = erqa_utils._build_extraction_question(doc)
        grounded_output = str(doc["answer"]).strip().upper()

        prompts.append(_build_extraction_prompt(question, parsed_response))
        rows.append(
            {
                "doc_id": int(sample["doc_id"]),
                "question_id": str(doc["question_id"]),
                "question_type": str(doc["question_type"]),
                "ground_truth": grounded_output,
                "question": question,
                "raw_response": raw_response,
                "parsed_response": parsed_response,
                "judge_raw": "",
                "judge_extracted": "",
                "pred_letter": "",
                "score": 0.0,
            }
        )

    for start in tqdm(range(0, len(prompts), args.batch_size), desc="Judge extracting"):
        batch_prompts = prompts[start : start + args.batch_size]
        raw_outputs = judge.generate_json_batch(
            batch_prompts,
            max_tokens=args.max_tokens,
            use_tqdm=False,
        )
        for row, raw_output in zip(rows[start : start + args.batch_size], raw_outputs):
            row["judge_raw"] = raw_output
            content = extract_json_candidate(raw_output)
            extracted = ""
            if content is not None:
                value = content.get("extracted_answer", "")
                if value is None:
                    extracted = ""
                else:
                    extracted = value if isinstance(value, str) else str(value)
            row["judge_extracted"] = extracted

            response_for_parse = extracted or row["parsed_response"]
            question_text = dataset[row["doc_id"]].get("question", "")
            if erqa_utils._is_mcq_question(question_text):
                option_labels = ["A", "B", "C", "D"]
            else:
                option_labels = None
            pred_letter = erqa_utils._extract_answer_letter(
                response_for_parse,
                option_labels=option_labels,
                index2ans=None,
            )
            row["pred_letter"] = pred_letter
            row["score"] = 1.0 if pred_letter == row["ground_truth"] else 0.0

    scores = [float(row["score"]) for row in rows]
    mean_score = (sum(scores) / len(scores)) if scores else 0.0
    stderr = 0.0
    if len(scores) > 1:
        mean = mean_score
        variance = sum((x - mean) ** 2 for x in scores) / (len(scores) - 1)
        stderr = (variance / len(scores)) ** 0.5

    per_question_type: dict[str, dict[str, float]] = {}
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[row["question_type"]].append(float(row["score"]))
    for question_type, type_scores in sorted(grouped.items()):
        per_question_type[question_type] = {
            "count": len(type_scores),
            "accuracy": (sum(type_scores) / len(type_scores)) if type_scores else 0.0,
        }

    details_path = output_path.with_suffix(".jsonl")
    with output_path.open("w") as handle:
        json.dump(
            {
                "samples_file": str(sample_path),
                "count": len(scores),
                "submission": mean_score,
                "submission_stderr": stderr,
                "details_file": str(details_path),
                "per_question_type": per_question_type,
            },
            handle,
            indent=2,
        )

    with details_path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
