#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
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
BLINK_TASK_DIR = EVAL_ROOT / "vendor/vero_eval/lmms_eval/tasks/blink"
BLINK_UTILS_PATH = BLINK_TASK_DIR / "utils.py"


def _load_blink_utils():
    spec = importlib.util.spec_from_file_location("trace_eval_blink_utils", BLINK_UTILS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load BLINK utils from {BLINK_UTILS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


blink_utils = _load_blink_utils()


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


def _infer_task_name(sample_path: Path) -> str:
    match = re.search(r"_samples_(.+)\.jsonl$", sample_path.name)
    if not match:
        raise ValueError(f"Could not infer BLINK task name from {sample_path.name}")
    return match.group(1)


def _load_samples(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_task_to_dataset_name() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for yaml_path in sorted(BLINK_TASK_DIR.glob("blink_*.yaml")):
        if yaml_path.name in {
            "blink.yaml",
            "blink_qwen3_zs.yaml",
            "blink_qwen25_zs.yaml",
            "blink_qwen3_thinking_zs.yaml",
            "blink_reasoning.yaml",
            "blink_reasoning_samplingq3.yaml",
            "blink_mimo_zs.yaml",
            "blink_gpt5nano_zs.yaml",
        }:
            continue
        with yaml_path.open() as handle:
            config = yaml.safe_load(handle)
        task_name = config.get("task")
        dataset_name = config.get("dataset_name")
        if isinstance(task_name, str) and isinstance(dataset_name, str):
            mapping[task_name] = dataset_name
    return mapping


def _build_extraction_prompt(question: str, response: str) -> str:
    return (
        EXTRACT_ANSWER_PROMPT.replace("<|question|>", question or "")
        .replace("<|response|>", response)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--samples-dir",
        required=True,
        help="Output directory containing lmms_eval --predict_only sample JSONLs",
    )
    parser.add_argument("--output", required=True, help="Output JSON summary path")
    parser.add_argument("--dataset-path", default="BLINK-Benchmark/BLINK")
    parser.add_argument("--split", default="val")
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--limit-per-task", type=int, default=None)
    args = parser.parse_args()

    samples_dir = Path(args.samples_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sample_paths = sorted(samples_dir.glob("*_samples_*.jsonl"))
    if not sample_paths:
        raise FileNotFoundError(f"No sample JSONLs found under {samples_dir}")

    task_to_dataset = _load_task_to_dataset_name()
    judge = get_judge_engine(args.judge_model)

    dataset_cache: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    prompts: list[str] = []

    for sample_path in sample_paths:
        task_name = _infer_task_name(sample_path)
        if task_name not in task_to_dataset:
            continue
        dataset_name = task_to_dataset[task_name]
        if dataset_name not in dataset_cache:
            dataset_cache[dataset_name] = load_dataset(
                args.dataset_path,
                dataset_name,
                split=args.split,
                token=True,
            )
        dataset = dataset_cache[dataset_name]
        samples = _load_samples(sample_path)
        if args.limit_per_task is not None:
            samples = samples[: args.limit_per_task]

        for sample in samples:
            doc = dataset[int(sample["doc_id"])]
            raw_response = _extract_raw_response(sample)
            parsed_response = extract_final_answer(raw_response.strip())
            question = blink_utils._build_extraction_question(doc)
            grounded_output = str(doc["answer"]).strip("()")

            prompts.append(_build_extraction_prompt(question, parsed_response))
            rows.append(
                {
                    "task": task_name,
                    "dataset_name": dataset_name,
                    "doc_id": int(sample["doc_id"]),
                    "idx": str(doc["idx"]),
                    "sub_task": str(doc["sub_task"]),
                    "question": question,
                    "ground_truth": grounded_output,
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
            choices = dataset_cache[row["dataset_name"]][row["doc_id"]].get("choices")
            option_labels = blink_utils._build_option_labels(choices)
            index2ans = blink_utils._build_index2ans(option_labels, choices)
            pred_letter = blink_utils._extract_answer_letter(
                response_for_parse,
                option_labels=option_labels or None,
                index2ans=index2ans or None,
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

    per_task_counts: dict[str, dict[str, float]] = {}
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[row["task"]].append(float(row["score"]))
    for task_name, task_scores in sorted(grouped.items()):
        acc = sum(task_scores) / len(task_scores) if task_scores else 0.0
        per_task_counts[task_name] = {
            "count": len(task_scores),
            "accuracy": acc,
        }

    details_path = output_path.with_suffix(".jsonl")
    with output_path.open("w") as handle:
        json.dump(
            {
                "samples_dir": str(samples_dir),
                "count": len(scores),
                "submission": mean_score,
                "submission_stderr": stderr,
                "details_file": str(details_path),
                "per_task": per_task_counts,
            },
            handle,
            indent=2,
        )

    with details_path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
