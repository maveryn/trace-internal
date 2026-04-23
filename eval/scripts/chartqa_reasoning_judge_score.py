#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from datasets import load_dataset
from tqdm import tqdm

from lmms_eval.tasks._task_utils.answer_parsing import EXTRACT_ANSWER_PROMPT
from lmms_eval.tasks._task_utils.vllm_judge import extract_json_candidate, get_judge_engine
from lmms_eval.tasks.chartqa_pro.utils import relaxed_correctness


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


def _build_prompt(question: str, response: str) -> str:
    return EXTRACT_ANSWER_PROMPT.replace("<|question|>", question or "").replace("<|response|>", response or "")


def _load_samples(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", required=True, help="JSONL from lmms_eval --predict_only --log_samples with API_VERBOSE=1")
    parser.add_argument("--output", required=True, help="Output JSON summary path")
    parser.add_argument("--dataset-path", default="ahmed-masry/ChartQAPro")
    parser.add_argument("--split", default="test")
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--batch-size", type=int, default=128)
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

    prompts: list[str] = []
    docs: list[dict[str, Any]] = []
    raw_responses: list[str] = []
    for sample in samples:
        doc = dataset[int(sample["doc_id"])]
        raw = _extract_raw_response(sample)
        prompts.append(_build_prompt(sample.get("input", ""), raw))
        docs.append(doc)
        raw_responses.append(raw)

    extracted_answers: list[str] = []
    for start in tqdm(range(0, len(prompts), args.batch_size), desc="Judge extracting"):
        batch_prompts = prompts[start : start + args.batch_size]
        raw_outputs = judge.generate_json_batch(batch_prompts, max_tokens=args.max_tokens, use_tqdm=False)
        for raw_output in raw_outputs:
            parsed = extract_json_candidate(raw_output)
            if parsed is None:
                extracted_answers.append("")
                continue
            answer = parsed.get("extracted_answer", "")
            extracted_answers.append("" if answer is None else str(answer))

    rows: list[dict[str, Any]] = []
    scores: list[float] = []
    for sample, doc, raw_response, extracted in zip(samples, docs, raw_responses, extracted_answers):
        score = float(relaxed_correctness(extracted, doc["Answer"], doc=doc))
        scores.append(score)
        rows.append(
            {
                "doc_id": int(sample["doc_id"]),
                "question": sample.get("input", ""),
                "target": doc["Answer"],
                "raw_response": raw_response,
                "judge_extracted_answer": extracted,
                "score": score,
            }
        )

    mean_score = (sum(scores) / len(scores)) if scores else 0.0
    stderr = 0.0
    if len(scores) > 1:
        mean = mean_score
        variance = sum((x - mean) ** 2 for x in scores) / (len(scores) - 1)
        stderr = (variance / len(scores)) ** 0.5

    with output_path.open("w") as f:
        json.dump(
            {
                "samples_file": str(sample_path),
                "count": len(scores),
                "relaxed_overall": mean_score,
                "relaxed_overall_stderr": stderr,
                "details_file": str(output_path.with_suffix(".jsonl")),
            },
            f,
            indent=2,
        )

    with output_path.with_suffix(".jsonl").open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
