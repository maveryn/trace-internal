#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from datasets import load_dataset
from tqdm import tqdm

from lmms_eval.llm_judge.utils import JudgePromptBuilder, ResponseParser
from lmms_eval.tasks._task_utils.answer_extraction import extract_final_answer
from lmms_eval.tasks._task_utils.response_truncation import truncate_response_tail_tiktoken
from lmms_eval.tasks._task_utils.vllm_judge import get_judge_engine


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


def _build_full_question(doc: dict[str, Any]) -> str:
    question = str(doc["question"])
    options = list(doc.get("options") or [])
    if not options:
        return question
    choices_str = "\n".join(f"{chr(ord('A') + i)}. {choice}" for i, choice in enumerate(options))
    return f"{question}\nChoices:\n{choices_str}"


def _extract_doc_identifier(doc: dict[str, Any]) -> str:
    for key in ("id", "question_id", "image_id", "pid"):
        value = doc.get(key)
        if value not in (None, ""):
            return str(value)
    return str(doc.get("question", ""))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", required=True, help="JSONL from lmms_eval --predict_only --log_samples")
    parser.add_argument("--output", required=True, help="Output JSON summary path")
    parser.add_argument("--dataset-path", default="MathLLMs/MathVision")
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
        model_answer = extract_final_answer(raw_response.strip())
        model_answer = truncate_response_tail_tiktoken(model_answer)
        full_question = _build_full_question(doc)
        gt_answer = str(doc["answer"])

        prompts.append(
            JudgePromptBuilder.build_binary_prompt(
                question=full_question,
                answer=gt_answer,
                prediction=model_answer,
                output_format="0/1",
            )
        )
        rows.append(
            {
                "doc_id": int(sample["doc_id"]),
                "question_id": _extract_doc_identifier(doc),
                "question": str(doc["question"]),
                "answer": gt_answer,
                "raw_response": raw_response,
                "prediction": model_answer,
                "judge_raw": "",
                "judge_binary": False,
                "score": 0.0,
            }
        )

    for start in tqdm(range(0, len(prompts), args.batch_size), desc="Judge scoring"):
        batch_prompts = prompts[start : start + args.batch_size]
        raw_outputs = judge.generate_json_batch(batch_prompts, max_tokens=args.max_tokens, use_tqdm=False)
        for row, raw_output in zip(rows[start : start + args.batch_size], raw_outputs):
            row["judge_raw"] = raw_output
            decision = ResponseParser.parse_binary_response(raw_output, "0/1")
            row["judge_binary"] = bool(decision)
            row["score"] = 1.0 if decision else 0.0

    scores = [float(row["score"]) for row in rows]
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
