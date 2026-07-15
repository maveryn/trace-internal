#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
for path in (SCRIPTS_ROOT, VLMEVAL_ROOT, VLMEVAL_ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import benchmark_queue_lib as benchmark_lib  # noqa: E402
from benchmark_queue_lib import (  # noqa: E402
    MME_REASONING_MD5,
    MME_REASONING_TSV_URL,
    extract_score_and_rows,
    json_default,
    run_dir,
    spec_by_key,
    write_json,
)
from run_external_benchmark_score_queue import PersistentJudge  # noqa: E402


MME_REASONING_SPEC = spec_by_key("mme_reasoning")


def _patch_mme_reasoning_dataset() -> None:
    from vlmeval.dataset.image_vqa import MMEReasoning

    MMEReasoning.DATASET_URL["MME-Reasoning"] = MME_REASONING_TSV_URL
    MMEReasoning.DATASET_MD5 = {"MME-Reasoning": MME_REASONING_MD5}


def _install_runtime_spec() -> None:
    if not any(spec.key == MME_REASONING_SPEC.key for spec in benchmark_lib.ALL_BENCHMARKS):
        benchmark_lib.ALL_BENCHMARKS = benchmark_lib.ALL_BENCHMARKS + (MME_REASONING_SPEC,)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _clean_optional(value: Any) -> Any:
    return None if _is_missing(value) else value


def _safe_literal_eval(value: Any) -> Any:
    if _is_missing(value):
        return None
    if not isinstance(value, str):
        return value
    try:
        return ast.literal_eval(value)
    except Exception:
        return eval(value, {"__builtins__": {}}, {})  # noqa: S307 - matches VLMEvalKit evaluator contract.


def _ensure_eval_prompt_function(line: pd.Series) -> tuple[str, str]:
    eval_prompt = _clean_optional(line.get("prompt_id"))
    eval_function = _clean_optional(line.get("function_id"))
    if eval_function is None:
        question_type = str(line.get("question_type", "")).lower()
        if question_type == "choice":
            return "choice_prompt", "choice_function"
        if question_type == "open":
            return "open_question_prompt", "open_function"
        raise NotImplementedError(f"Question type requires function_id: {line.get('question_type')}")
    if eval_prompt is None:
        raise ValueError(f"Row {line.get('index')} has function_id={eval_function!r} but no prompt_id")
    return str(eval_prompt), str(eval_function)


def _extract_prompt(line: pd.Series) -> tuple[str, str]:
    from vlmeval.dataset.utils.mme_reasoning import mme_reasoning_eval_prompts

    eval_prompt, eval_function = _ensure_eval_prompt_function(line)
    prompt = mme_reasoning_eval_prompts[eval_prompt].format(
        question=line["question"],
        response=line["prediction"],
    )
    return prompt, eval_prompt


def _extract_json_from_response(text: str) -> str | None:
    from vlmeval.dataset.utils.mme_reasoning import extract_json_from_response

    return extract_json_from_response(text)


def _normalize_choice_extraction(output: str) -> str | None:
    """Normalize the MME judge's single- or multi-option extraction."""

    text = str(output or "").strip()
    if not text:
        return None
    try:
        parsed = ast.literal_eval(text)
    except Exception:
        parsed = None
    if isinstance(parsed, (list, tuple)):
        values = [str(value).strip().upper() for value in parsed]
    else:
        inner = text.strip("[]() ")
        values = [part.strip().strip("\"'").upper() for part in inner.split(",")]
    if not values or any(re.fullmatch(r"[A-Z]", value) is None for value in values):
        return None
    return ",".join(values)


def _validate_extraction(eval_prompt: str, output: str) -> tuple[bool, str]:
    if not str(output or "").strip():
        return False, output
    from vlmeval.dataset.utils.mme_reasoning import FAIL_MSG

    if FAIL_MSG in output:
        return False, output
    if eval_prompt == "choice_prompt":
        normalized = _normalize_choice_extraction(output)
        return (normalized is not None), (normalized or output)
    if eval_prompt in {"open_question_prompt", "points24_prompt"}:
        return True, output
    try:
        json.loads(output)
        return True, output
    except Exception:
        extracted = _extract_json_from_response(output)
        if extracted is None:
            return False, output
        try:
            json.loads(extracted)
            return True, extracted
        except Exception:
            return False, output


def _openeval_prompt(line: pd.Series) -> str:
    return """
Please read the following example. Then judge the answer and type it at the end of the prompt.
Below are two examples. Question is [Question], [Standard Answer] is the standard answer to the question, and [Model_answer] is the answer extracted from a model's output to this question.  Determine whether these two answers are consistent.
Note:
    Different expressions of the same number should also be considered consistent, for example, \\frac{{7}}{{2}} and 3.5.
    If a conversion results in a decimal approximation, the expressions can be considered consistent if the values are equal up to two decimal places, for example, \\sqrt{{3}} and 1.73.
If they are consistent, Judgement is 1; if they are different, Judgement is 0.\n
Example 1:
    [Question]: What is the minimize length of the line?
    [Standard answer]: \\sqrt{{2}}
    [Model answer]: 1.414
    [Judgement]: 1
Example 2:
    [Question]: Given an image of a 3x3 maze. How to reach the end cell marked 'E' from the start cell is marked 'S'.
    [Standard answer]: ['Left', 'Right']
    [Model answer]: 'Left', 'Right'
    [Judgement]: 1

Now, judge the anwser for the following question:
    [Question]: {question}
    [Standard answer]: {answer}
    [Model answer]: {response}
    [Judgement]:
You should only output the judgement without any other texts.
""".format(question=line["question"], answer=line["answer"], response=line["res"])


def _load_eval_table(output_dir: Path) -> pd.DataFrame:
    eval_file = output_dir / f"{MME_REASONING_SPEC.alias}_predictions.xlsx"
    if not eval_file.exists():
        raise FileNotFoundError(f"Missing prediction table: {eval_file}")
    return pd.read_excel(eval_file).replace({float("nan"): None})


def _mme_reasoning_acc(data: pd.DataFrame) -> pd.DataFrame:
    capabilities = [
        "planning and exploring",
        "calculation",
        "spatial-temporal",
        "casual chaining analysis",
        "pattern analysis",
    ]
    reasoning_types = ["inductive", "deductive", "abductive"]

    result: dict[str, list[float]] = {"Overall": [float(data["score"].mean() * 100)]}
    for capability in capabilities:
        sub = data[data["capability"].apply(lambda value: capability in str(value))]
        result[capability] = [float(sub["score"].mean() * 100) if len(sub) else float("nan")]
    for reasoning_type in reasoning_types:
        sub = data[data["reasoning_type"].apply(lambda value: reasoning_type in str(value))]
        result[reasoning_type] = [float(sub["score"].mean() * 100) if len(sub) else float("nan")]
    return pd.DataFrame(result)


def run_prepare(args: argparse.Namespace) -> None:
    _patch_mme_reasoning_dataset()
    from vlmeval.dataset import build_dataset

    dataset = build_dataset(MME_REASONING_SPEC.alias)
    if dataset is None:
        raise RuntimeError(f"VLMEvalKit could not build dataset {MME_REASONING_SPEC.alias}")
    if args.limit is not None:
        dataset.data = dataset.data.sample(n=min(int(args.limit), len(dataset.data)), random_state=args.sample_seed)

    materialized: list[str] = []
    for _, row in dataset.data.iterrows():
        for item in dataset.build_prompt(row):
            if item.get("type") == "image":
                path = str(item.get("value"))
                with Image.open(path) as image:
                    image.verify()
                materialized.append(path)
    print(
        "[mme-prepare:done] "
        f"rows={len(dataset.data)} images={len(materialized)} root={getattr(dataset, 'img_root', '')}"
    )


def run_generation(args: argparse.Namespace) -> None:
    import run_external_benchmark_generation_api_queue as generation_queue

    _patch_mme_reasoning_dataset()
    _install_runtime_spec()
    generation_args = SimpleNamespace(
        model=args.model,
        model_slug=args.model_slug,
        api_model=args.api_model,
        api_bases=args.api_base,
        api_key=args.api_key,
        api_timeout=args.api_timeout,
        api_max_retries=args.api_max_retries,
        endpoint_failure_threshold=args.endpoint_failure_threshold,
        parallelism_per_endpoint=args.parallelism_per_endpoint,
        run_set="full",
        run_root=args.run_root,
        result_mirror_root=args.result_mirror_root,
        queue_root=args.queue_root,
        only=[MME_REASONING_SPEC.key],
        exclude=[],
        exact_only=True,
        subset_root=None,
        limit=args.limit,
        sample_seed=args.sample_seed,
        max_image_pixels=args.max_image_pixels,
        max_image_side=args.max_image_side,
        image_jpeg_quality=args.image_jpeg_quality,
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        presence_penalty=args.presence_penalty,
        repetition_penalty=args.repetition_penalty,
        max_tokens=args.max_tokens,
        seed=args.seed,
        no_resume=args.no_resume,
    )
    generation_queue.run(generation_args)


def run_score(args: argparse.Namespace) -> dict[str, Any]:
    from vlmeval.dataset.utils.mme_reasoning import FAIL_MSG, mme_reasoning_eval_functions
    from vlmeval.smp import dump

    _patch_mme_reasoning_dataset()
    output_dir = run_dir(MME_REASONING_SPEC, args.model_slug, args.run_root)
    benchmark_output_dir = run_dir(MME_REASONING_SPEC, args.model_slug, args.benchmark_root)
    benchmark_output_dir.mkdir(parents=True, exist_ok=True)

    data = _load_eval_table(output_dir)
    judge = PersistentJudge(args)

    extraction_rows: dict[str, dict[str, Any]] = {}
    pending_indices = [str(idx) for idx in data["index"]]
    eval_prompt_by_idx: dict[str, str] = {}
    prompt_by_idx: dict[str, str] = {}
    for _, line in data.iterrows():
        idx = str(line["index"])
        prompt, eval_prompt = _extract_prompt(line)
        prompt_by_idx[idx] = prompt
        eval_prompt_by_idx[idx] = eval_prompt

    for attempt in range(5):
        pending = [(idx, prompt_by_idx[idx]) for idx in pending_indices]
        if not pending:
            break
        cache = judge.run_cached(
            output_dir=benchmark_output_dir,
            prompts=pending,
            cache_name=f"mme_reasoning_extract_attempt{attempt}.jsonl",
            max_tokens=args.extract_max_tokens,
            temperature=0.0,
            top_p=1.0,
            no_resume=args.no_resume,
            desc=f"{args.model_slug} MME extract attempt {attempt}",
        )
        next_pending: list[str] = []
        for idx, _prompt in pending:
            line = data[data["index"].astype(str) == idx].iloc[0]
            if str(line.get("prediction", "")) == FAIL_MSG:
                extraction_rows[idx] = {"log": f"Try {attempt}: output is {FAIL_MSG}, failed to parse.\n", "res": ""}
                continue
            raw = str(cache.get(idx, {}).get("judge_output", "")).strip()
            ok, res = _validate_extraction(eval_prompt_by_idx[idx], raw)
            if ok:
                extraction_rows[idx] = {"log": "Succeed", "res": res}
            else:
                next_pending.append(idx)
        pending_indices = next_pending

    if pending_indices:
        failure_path = benchmark_output_dir / "mme_reasoning_extraction_failures.json"
        write_json(
            failure_path,
            {
                "stage": "answer_extraction",
                "count": len(pending_indices),
                "indices": pending_indices,
                "retries": 5,
                "temperature": 0.0,
            },
        )
        judge.cleanup()
        raise RuntimeError(
            "MME-Reasoning judge failed to produce parseable extractions for "
            f"{len(pending_indices)} rows; first indices={pending_indices[:10]}"
        )

    data["res"] = [extraction_rows[str(idx)]["res"] for idx in data["index"]]
    data["log"] = [extraction_rows[str(idx)]["log"] for idx in data["index"]]
    extract_file = benchmark_output_dir / f"{MME_REASONING_SPEC.alias}_predictions_qwen3_32b_extract.xlsx"
    data.to_excel(extract_file, index=False)

    score_rows: dict[str, dict[str, Any]] = {}
    open_prompts: list[tuple[str, str]] = []
    for _, line in data.iterrows():
        idx = str(line["index"])
        function_id = _clean_optional(line.get("function_id"))
        is_open = (str(line["question_type"]).lower() == "open" and function_id is None) or function_id == "open_function"
        if is_open:
            open_prompts.append((idx, _openeval_prompt(line)))

    pending_open = [idx for idx, _ in open_prompts]
    prompt_open = dict(open_prompts)
    for attempt in range(5):
        pending = [(idx, prompt_open[idx]) for idx in pending_open]
        if not pending:
            break
        cache = judge.run_cached(
            output_dir=benchmark_output_dir,
            prompts=pending,
            cache_name=f"mme_reasoning_score_open_attempt{attempt}.jsonl",
            max_tokens=args.score_max_tokens,
            temperature=0.0,
            top_p=1.0,
            no_resume=args.no_resume,
            desc=f"{args.model_slug} MME open score attempt {attempt}",
        )
        next_pending: list[str] = []
        for idx, _prompt in pending:
            line = data[data["index"].astype(str) == idx].iloc[0]
            prediction = _clean_optional(line.get("res"))
            if prediction is None or FAIL_MSG in str(prediction):
                score_rows[idx] = {"log_score": f"Try {attempt}: output is {prediction}, failed to parse.\n", "score": False}
                continue
            raw = str(cache.get(idx, {}).get("judge_output", "")).strip()
            if raw in {"0", "1"}:
                score_rows[idx] = {"log_score": "Succeed", "score": raw == "1"}
            else:
                next_pending.append(idx)
        pending_open = next_pending

    if pending_open:
        failure_path = benchmark_output_dir / "mme_reasoning_open_judge_failures.json"
        write_json(
            failure_path,
            {
                "stage": "open_answer_scoring",
                "count": len(pending_open),
                "indices": pending_open,
                "retries": 5,
                "temperature": 0.0,
            },
        )
        judge.cleanup()
        raise RuntimeError(
            "MME-Reasoning judge failed to produce binary decisions for "
            f"{len(pending_open)} open-answer rows; first indices={pending_open[:10]}"
        )

    for _, line in data.iterrows():
        idx = str(line["index"])
        if idx in score_rows:
            continue
        res = _clean_optional(line.get("res"))
        if res is None or FAIL_MSG in str(res):
            score_rows[idx] = {"log_score": "Failed to evaluate", "score": False}
            continue
        function_id = _clean_optional(line.get("function_id"))
        if function_id is None:
            if str(line["question_type"]).lower() != "choice":
                raise ValueError(f"Unexpected non-choice deterministic row {idx}: {line['question_type']}")
            function_id = "choice_function"
        function = mme_reasoning_eval_functions[str(function_id)]
        try:
            if function_id not in {"open_function", "choice_function"}:
                response = str(res) if function_id == "judge_24points_function" else json.loads(str(res))
                answer = _safe_literal_eval(line.get("answer"))
                if function_id in {
                    "calculate_answer_function_hashi",
                    "calculate_answer_function_skyscraper",
                    "calculate_answer_function_sudoku_4",
                    "calculate_answer_function_sudoku_6",
                    "calculate_answer_function_yinyang",
                    "judge_24points_function",
                }:
                    special_info = _safe_literal_eval(line.get("special_info"))
                else:
                    special_info = None
            else:
                response = str(res)
                answer = line.get("answer")
                special_info = None
            answer_judge = function(response, answer) if special_info is None else function(response, answer, special_info)
            if answer_judge not in {True, False}:
                answer_judge = False
            score_rows[idx] = {"log_score": "Succeed", "score": bool(answer_judge)}
        except Exception as exc:
            score_rows[idx] = {"log_score": f"Failed to evaluate: {exc!r}", "score": False}

    data["score"] = [bool(score_rows[str(idx)]["score"]) for idx in data["index"]]
    data["log_score"] = [score_rows[str(idx)]["log_score"] for idx in data["index"]]
    score_file = benchmark_output_dir / f"{MME_REASONING_SPEC.alias}_predictions_qwen3_32b_score.xlsx"
    data.to_excel(score_file, index=False)

    acc_df = _mme_reasoning_acc(data)
    acc_csv = benchmark_output_dir / "MME-Reasoning_acc.csv"
    acc_xlsx = benchmark_output_dir / "MME-Reasoning_acc.xlsx"
    acc_df.to_csv(acc_csv, index=False)
    acc_df.to_excel(acc_xlsx, index=False)
    score_dict = {key: float(value) for key, value in acc_df.iloc[0].to_dict().items()}
    scores = {
        "dataset": MME_REASONING_SPEC.alias,
        "display": MME_REASONING_SPEC.display,
        "model": args.model,
        "model_slug": args.model_slug,
        "rows": int(len(data)),
        "accuracy": float(score_dict.get("Overall", 0.0)),
        "scores": score_dict,
        "artifacts": {
            "predictions": str(output_dir / f"{MME_REASONING_SPEC.alias}_predictions.xlsx"),
            "extracted": str(extract_file),
            "scored": str(score_file),
            "acc_csv": str(acc_csv),
        },
        "judge": {
            "model": args.judge_model,
            "api_model": args.judge_api_model,
            "api_bases": args.judge_api_bases,
            "temperature": 0.0,
            "extraction_retries": 5,
            "unresolved_extractions": 0,
            "unresolved_open_scores": 0,
        },
    }
    write_json(benchmark_output_dir / "scores.json", scores)
    dump(score_dict, str(benchmark_output_dir / "scores_raw.json"))
    judge.cleanup()
    print(f"[mme-score:done] slug={args.model_slug} rows={len(data)} accuracy={scores['accuracy']:.2f} output={benchmark_output_dir}")
    return scores


def run_summary(args: argparse.Namespace) -> None:
    rows: list[dict[str, Any]] = []
    for model_slug in args.model_slug:
        score_file = run_dir(MME_REASONING_SPEC, model_slug, args.benchmark_root) / "scores.json"
        if not score_file.exists():
            raise FileNotFoundError(score_file)
        scores = json.loads(score_file.read_text(encoding="utf-8"))
        acc, n = extract_score_and_rows(scores)
        rows.append(
            {
                "benchmark": MME_REASONING_SPEC.display,
                "model": model_slug,
                "rows": n or scores.get("rows"),
                "accuracy": acc,
            }
        )
    frame = pd.DataFrame(rows)
    if len(frame) == 2:
        base = float(frame.iloc[0]["accuracy"])
        tuned = float(frame.iloc[1]["accuracy"])
        frame.loc[frame.index[1], "delta_vs_base"] = tuned - base
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame.to_excel(args.output_dir / "mme_reasoning_results.xlsx", index=False)
    lines = [
        "# MME-Reasoning Temp0.6 Seed42 Results",
        "",
        "| Benchmark | Model | Rows | Accuracy | Delta vs Base |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, row in frame.iterrows():
        delta = row.get("delta_vs_base")
        delta_text = "" if pd.isna(delta) else f"{float(delta):.2f}"
        lines.append(
            f"| {row['benchmark']} | `{row['model']}` | {int(row['rows'])} | {float(row['accuracy']):.2f} | {delta_text} |"
        )
    (args.output_dir / "mme_reasoning_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[mme-summary:done] {args.output_dir / 'mme_reasoning_results.xlsx'}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MME-Reasoning with TRACE endpoint-pool eval settings.")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate")
    gen.add_argument("--model", required=True)
    gen.add_argument("--model-slug", required=True)
    gen.add_argument("--api-model", required=True)
    gen.add_argument("--api-base", action="append", required=True)
    gen.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "EMPTY"))
    gen.add_argument("--api-timeout", type=float, default=300.0)
    gen.add_argument("--api-max-retries", type=int, default=5)
    gen.add_argument("--endpoint-failure-threshold", type=int, default=2)
    gen.add_argument("--parallelism-per-endpoint", type=int, default=32)
    gen.add_argument("--run-root", type=Path, required=True)
    gen.add_argument("--result-mirror-root", type=Path, default=None)
    gen.add_argument("--queue-root", type=Path, default=benchmark_lib.DEFAULT_QUEUE_ROOT)
    gen.add_argument("--limit", type=int, default=None)
    gen.add_argument("--sample-seed", type=int, default=0)
    gen.add_argument("--max-image-pixels", type=int, default=1_000_000)
    gen.add_argument("--max-image-side", type=int, default=1280)
    gen.add_argument("--image-jpeg-quality", type=int, default=85)
    gen.add_argument("--temperature", type=float, default=0.6)
    gen.add_argument("--top-p", type=float, default=1.0)
    gen.add_argument("--top-k", type=int, default=-1)
    gen.add_argument("--presence-penalty", type=float, default=0.0)
    gen.add_argument("--repetition-penalty", type=float, default=1.0)
    gen.add_argument("--max-tokens", type=int, default=4096)
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--no-resume", action="store_true")
    gen.set_defaults(func=run_generation)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--limit", type=int, default=None)
    prepare.add_argument("--sample-seed", type=int, default=0)
    prepare.set_defaults(func=run_prepare)

    score = sub.add_parser("score")
    score.add_argument("--model", required=True)
    score.add_argument("--model-slug", required=True)
    score.add_argument("--run-root", type=Path, required=True)
    score.add_argument("--benchmark-root", type=Path, required=True)
    score.add_argument("--gpu", default=os.environ.get("CUDA_VISIBLE_DEVICES", ""))
    score.add_argument("--judge-model", default="Qwen/Qwen3-32B")
    score.add_argument("--judge-batch-size", type=int, default=1024)
    score.add_argument("--judge-tensor-parallel-size", type=int, default=1)
    score.add_argument("--judge-gpu-memory-utilization", type=float, default=0.90)
    score.add_argument("--judge-max-model-len", type=int, default=8192)
    score.add_argument("--judge-max-num-seqs", type=int, default=128)
    score.add_argument("--judge-max-num-batched-tokens", type=int, default=32768)
    score.add_argument("--judge-max-tokens", type=int, default=256)
    score.add_argument("--judge-api-base", action="append", dest="judge_api_bases")
    score.add_argument("--judge-api-model", default="qwen3-32b-judge")
    score.add_argument("--judge-api-tokenizer-model", default="Qwen/Qwen3-32B")
    score.add_argument("--judge-api-parallelism", type=int, default=128)
    score.add_argument("--judge-api-timeout", type=float, default=120.0)
    score.add_argument("--judge-api-max-retries", type=int, default=5)
    score.add_argument("--attention-backend", default="FLASH_ATTN")
    score.add_argument("--extract-max-tokens", type=int, default=1024)
    score.add_argument("--score-max-tokens", type=int, default=16)
    score.add_argument("--no-resume", action="store_true")
    score.set_defaults(func=run_score)

    summary = sub.add_parser("summary")
    summary.add_argument("--model-slug", action="append", required=True)
    summary.add_argument("--benchmark-root", type=Path, required=True)
    summary.add_argument("--output-dir", type=Path, required=True)
    summary.set_defaults(func=run_summary)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    os.environ.setdefault("LMUData", "/dev/shm/trace_rlvr/lmudata")
    Path(os.environ["LMUData"]).mkdir(parents=True, exist_ok=True)
    args.func(args)


if __name__ == "__main__":
    main()
