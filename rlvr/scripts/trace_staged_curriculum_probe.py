from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARN")

RLVR_ROOT = Path(__file__).resolve().parents[1]
if str(RLVR_ROOT) not in sys.path:
    sys.path.insert(0, str(RLVR_ROOT))
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from trace_curriculum_probe import (  # noqa: E402
    _build_dataset,
    _json_default,
    _maybe_parse_json_mapping,
    _normalize_probe_response,
    _prepare_batch_payload,
    _prompt_batch_size_from_rollout_budget,
    _resolve_system_prompt_arg,
    _score_trace_response_with_item,
    _split_prompt_ranges,
    _write_json_atomic,
)


def _detect_visible_gpu_ids() -> list[str]:
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    if visible:
        return [part.strip() for part in visible.split(",") if part.strip()]
    output = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
        text=True,
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def _parse_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _ceil_rate_count(rate: float, rollout_count: int) -> int:
    return int(math.ceil(float(rate) * int(rollout_count) - 1e-12))


def _ensure_record(records: dict[int, dict[str, Any]], dataset_index: int, item: dict[str, Any]) -> dict[str, Any]:
    record = records.get(dataset_index)
    if record is not None:
        return record

    metadata = _parse_metadata(item.get("metadata"))
    answer_gt = _maybe_parse_json_mapping(item["answer_gt"])
    evidence_gt = _maybe_parse_json_mapping(item["evidence_gt"])
    query_id = metadata.get("query_id")
    record = {
        "dataset_index": int(dataset_index),
        "uid": str(item.get("uid", "")),
        "domain": str(item.get("domain", "")),
        "task_group": str(item.get("task_group", "")),
        "task": str(item.get("task", "")),
        "query_id": None if query_id is None else str(query_id),
        "complexity_score": None if item.get("complexity_score") is None else float(item.get("complexity_score")),
        "difficulty_bin": None if item.get("difficulty_bin") is None else int(item.get("difficulty_bin")),
        "bucket_id_str": None if item.get("bucket_id_str") is None else str(item.get("bucket_id_str")),
        "prompt_length": int(len(item["raw_prompt_ids"])),
        "answer_type": str(answer_gt.get("type", "")),
        "evidence_type": str(evidence_gt.get("type", "")),
        "rollout_count": 0,
        "positive_rollout_count": 0,
        "perfect_rollout_count": 0,
        "generated_token_sum": 0,
        "max_generated_tokens": 0,
        "max_token_rollout_count": 0,
        "json_found_count": 0,
        "answer_parse_ok_count": 0,
        "format_json_ok_count": 0,
        "format_schema_ok_count": 0,
        "extraction_none_count": 0,
        "stage_history": [],
    }
    records[dataset_index] = record
    return record


def _score_generated_outputs(
    *,
    args: argparse.Namespace,
    records: dict[int, dict[str, Any]],
    batch_indices: list[int],
    batch_items: list[dict[str, Any]],
    outputs: Any,
) -> dict[str, int]:
    stage_stats = {
        "prompt_count": 0,
        "rollout_count": 0,
        "positive_rollout_count": 0,
        "perfect_rollout_count": 0,
        "max_token_rollout_count": 0,
        "json_found_count": 0,
        "extraction_none_count": 0,
    }
    for dataset_index, item, generated in zip(batch_indices, batch_items, outputs, strict=True):
        record = _ensure_record(records, dataset_index, item)
        answer_gt = _maybe_parse_json_mapping(item["answer_gt"])
        evidence_gt = _maybe_parse_json_mapping(item["evidence_gt"])
        reward_contract = _maybe_parse_json_mapping(item["reward_contract"])

        stage_positive = 0
        stage_perfect = 0
        stage_rollouts = 0
        for completion in generated.outputs:
            response = completion.text
            token_count = len(completion.token_ids or [])
            strict_score = _score_trace_response_with_item(
                response=response,
                item=item,
                answer_gt=answer_gt,
                evidence_gt=evidence_gt,
                reward_contract=reward_contract,
                trace_reward_mode=args.trace_reward_mode,
                trace_answer_scoring=args.trace_answer_scoring,
                format_weight=args.trace_format_weight,
            )
            normalized_response, extraction_source = _normalize_probe_response(
                response=response,
                trace_reward_mode=args.trace_reward_mode,
            )
            fallback_score = _score_trace_response_with_item(
                response=normalized_response,
                item=item,
                answer_gt=answer_gt,
                evidence_gt=evidence_gt,
                reward_contract=reward_contract,
                trace_reward_mode=args.trace_reward_mode,
                trace_answer_scoring=args.trace_answer_scoring,
                format_weight=args.trace_format_weight,
            )
            score = fallback_score
            positive = float(score.get("task_reward_raw", 0.0)) > 0.0
            perfect = float(score.get("task_reward_raw", 0.0)) >= 1.0

            stage_rollouts += 1
            stage_positive += 1 if positive else 0
            stage_perfect += 1 if perfect else 0

            record["rollout_count"] += 1
            record["positive_rollout_count"] += 1 if positive else 0
            record["perfect_rollout_count"] += 1 if perfect else 0
            record["generated_token_sum"] += int(token_count)
            record["max_generated_tokens"] = max(int(record["max_generated_tokens"]), int(token_count))
            record["max_token_rollout_count"] += 1 if int(token_count) >= int(args.max_tokens) else 0
            record["json_found_count"] += 1 if float(score.get("json_found", 0.0)) > 0.0 else 0
            record["answer_parse_ok_count"] += 1 if float(score.get("answer_parse_ok", 0.0)) > 0.0 else 0
            record["format_json_ok_count"] += 1 if float(score.get("format_json_ok", 0.0)) > 0.0 else 0
            record["format_schema_ok_count"] += 1 if float(score.get("format_schema_ok", 0.0)) > 0.0 else 0
            record["extraction_none_count"] += 1 if str(extraction_source) == "none" else 0

            stage_stats["rollout_count"] += 1
            stage_stats["positive_rollout_count"] += 1 if positive else 0
            stage_stats["perfect_rollout_count"] += 1 if perfect else 0
            stage_stats["max_token_rollout_count"] += 1 if int(token_count) >= int(args.max_tokens) else 0
            stage_stats["json_found_count"] += 1 if float(score.get("json_found", 0.0)) > 0.0 else 0
            stage_stats["extraction_none_count"] += 1 if str(extraction_source) == "none" else 0

        record["stage_history"].append(
            {
                "stage_rollout_count": int(stage_rollouts),
                "stage_positive_rollout_count": int(stage_positive),
                "stage_perfect_rollout_count": int(stage_perfect),
                "cumulative_rollout_count": int(record["rollout_count"]),
                "cumulative_positive_rollout_count": int(record["positive_rollout_count"]),
            }
        )
        stage_stats["prompt_count"] += 1
    return stage_stats


def _merge_counter_stats(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] += int(value)


def _finalize_record(record: dict[str, Any], *, easy_rate: float) -> dict[str, Any]:
    rollout_count = int(record["rollout_count"])
    positive_count = int(record["positive_rollout_count"])
    easy_cutoff = _ceil_rate_count(easy_rate, rollout_count)
    if positive_count == 0:
        status = "filtered_hard_zero"
    elif positive_count >= easy_cutoff:
        status = "filtered_easy_high"
    else:
        status = "retained_band"

    generated_sum = int(record.pop("generated_token_sum"))
    row = {
        **record,
        "solve_rate": float(positive_count / rollout_count) if rollout_count else 0.0,
        "perfect_rate": float(int(record["perfect_rollout_count"]) / rollout_count) if rollout_count else 0.0,
        "mean_generated_tokens": float(generated_sum / rollout_count) if rollout_count else 0.0,
        "max_token_rollout_rate": float(int(record["max_token_rollout_count"]) / rollout_count) if rollout_count else 0.0,
        "json_found_rate": float(int(record["json_found_count"]) / rollout_count) if rollout_count else 0.0,
        "answer_parse_ok_rate": float(int(record["answer_parse_ok_count"]) / rollout_count) if rollout_count else 0.0,
        "format_json_ok_rate": float(int(record["format_json_ok_count"]) / rollout_count) if rollout_count else 0.0,
        "format_schema_ok_rate": float(int(record["format_schema_ok_count"]) / rollout_count) if rollout_count else 0.0,
        "extraction_none_rate": float(int(record["extraction_none_count"]) / rollout_count) if rollout_count else 0.0,
        "easy_cutoff_positive_count": int(easy_cutoff),
        "filter_status": status,
    }
    return row


def _aggregate_rows(rows: list[dict[str, Any]], *, name: str) -> dict[str, Any]:
    prompt_count = len(rows)
    rollout_count = sum(int(row["rollout_count"]) for row in rows)
    positive_count = sum(int(row["positive_rollout_count"]) for row in rows)
    retained_count = sum(1 for row in rows if row["filter_status"] == "retained_band")
    hard_count = sum(1 for row in rows if row["filter_status"] == "filtered_hard_zero")
    easy_count = sum(1 for row in rows if row["filter_status"] == "filtered_easy_high")
    return {
        "name": name,
        "prompt_count": int(prompt_count),
        "rollout_count": int(rollout_count),
        "positive_rollout_count": int(positive_count),
        "positive_rollout_rate": float(positive_count / rollout_count) if rollout_count else 0.0,
        "mean_observed_solve_rate": float(sum(float(row["solve_rate"]) for row in rows) / prompt_count) if prompt_count else 0.0,
        "retained_count": int(retained_count),
        "retained_fraction": float(retained_count / prompt_count) if prompt_count else 0.0,
        "filtered_hard_zero_count": int(hard_count),
        "filtered_hard_zero_fraction": float(hard_count / prompt_count) if prompt_count else 0.0,
        "filtered_easy_high_count": int(easy_count),
        "filtered_easy_high_fraction": float(easy_count / prompt_count) if prompt_count else 0.0,
        "mean_rollouts_per_prompt": float(rollout_count / prompt_count) if prompt_count else 0.0,
        "max_observed_rollouts": max((int(row["rollout_count"]) for row in rows), default=0),
    }


def _summarize_by_task(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["task"])].append(row)
    summaries = []
    for task, task_rows in sorted(grouped.items()):
        payload = _aggregate_rows(task_rows, name=task)
        payload["task"] = task
        payload["domain"] = str(task_rows[0].get("domain", ""))
        summaries.append(payload)
    return summaries


def _run_worker(args: argparse.Namespace) -> dict[str, Any]:
    from tqdm.auto import tqdm
    from vllm import LLM, SamplingParams

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "summary.json"
    per_instance_path = args.output_dir / "per_instance_staged.jsonl"
    if args.resume and summary_path.exists() and per_instance_path.exists():
        return json.loads(summary_path.read_text(encoding="utf-8"))

    system_prompt = _resolve_system_prompt_arg(args.system_prompt)
    dataset = _build_dataset(
        args.parquet,
        args.model,
        trace_output_mode=args.trace_output_mode,
        prompt_key=args.prompt_key,
        system_prompt=system_prompt,
        max_prompt_length=args.max_prompt_length,
        max_pixels=args.max_pixels,
        filter_overlong_prompts=args.filter_overlong_prompts,
    )
    dataset_len = len(dataset)
    start_index = max(0, int(args.start_index))
    end_index = dataset_len if args.count is None else min(dataset_len, start_index + max(0, int(args.count)))
    if start_index >= end_index:
        raise ValueError(f"No rows selected: start={start_index}, end={end_index}, dataset_len={dataset_len}")

    attention_config = {}
    if args.attention_backend:
        attention_config["backend"] = args.attention_backend
    if args.disable_trtllm_attention:
        attention_config["use_trtllm_attention"] = False

    llm = LLM(
        model=args.model,
        tensor_parallel_size=args.tensor_parallel_size,
        dtype="bfloat16",
        gpu_memory_utilization=args.gpu_memory_utilization,
        max_model_len=args.max_model_len,
        max_num_batched_tokens=args.max_num_batched_tokens,
        max_num_seqs=args.max_num_seqs,
        enforce_eager=args.enforce_eager,
        enable_chunked_prefill=True,
        enable_prefix_caching=True,
        limit_mm_per_prompt={"image": 4},
        trust_remote_code=False,
        seed=args.seed,
        attention_config=attention_config or None,
    )
    sampling_params = SamplingParams(
        n=args.stage_rollouts,
        temperature=args.temperature,
        top_p=1.0,
        top_k=-1,
        max_tokens=args.max_tokens,
        skip_special_tokens=True,
    )

    active_indices = list(range(start_index, end_index))
    original_prompt_count = len(active_indices)
    prompt_batch_size = _prompt_batch_size_from_rollout_budget(args.batch_size, args.stage_rollouts)
    prefetch_workers = max(0, int(args.prefetch_workers))
    score_workers = 1 if int(args.score_workers) > 0 else 0
    score_backlog = max(1, int(args.score_backlog))
    records: dict[int, dict[str, Any]] = {}
    stage_summaries: list[dict[str, Any]] = []
    next_stage_number = 1
    checkpoint_path = args.output_dir / "checkpoint.json"
    if args.resume and checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        records = {int(key): value for key, value in dict(checkpoint.get("records", {})).items()}
        active_indices = [int(index) for index in checkpoint.get("active_indices", active_indices)]
        stage_summaries = list(checkpoint.get("stage_summaries", []))
        next_stage_number = max(1, int(checkpoint.get("next_stage_number", 1)))
        original_prompt_count = int(checkpoint.get("original_prompt_count", original_prompt_count))
    started_at = time.time()

    stage_plan = list(enumerate(range(args.stage_rollouts, args.max_rollouts + 1, args.stage_rollouts), start=1))
    for stage_number, cumulative_rollouts in stage_plan:
        if stage_number < next_stage_number:
            continue
        stage_input_count = len(active_indices)
        if stage_input_count <= 0:
            break

        stage_stats_total = defaultdict(int)
        stage_desc = f"worker {args.worker_rank} stage {stage_number} ({cumulative_rollouts}x)"
        batch_ranges = [
            (batch_start, min(stage_input_count, batch_start + prompt_batch_size))
            for batch_start in range(0, stage_input_count, prompt_batch_size)
        ]
        score_futures: list[Future[dict[str, int]]] = []

        def drain_score_future() -> None:
            future = score_futures.pop(0)
            _merge_counter_stats(stage_stats_total, future.result())

        with ThreadPoolExecutor(max_workers=max(1, prefetch_workers or 1)) as prefetch_executor:
            score_executor = ThreadPoolExecutor(max_workers=score_workers) if score_workers else None
            try:
                prefetch_future: Future[tuple[list[dict[str, Any]], list[dict[str, Any]]]] | None = None
                current_batch_items: list[dict[str, Any]] | None = None
                current_requests: list[dict[str, Any]] | None = None

                if prefetch_workers > 0 and batch_ranges:
                    first_start, first_end = batch_ranges[0]
                    first_indices = active_indices[first_start:first_end]
                    current_batch_items, current_requests = _prepare_batch_payload(
                        dataset=dataset,
                        batch_indices=first_indices,
                    )

                for batch_idx, (batch_start, batch_end) in enumerate(
                    tqdm(
                        batch_ranges,
                        desc=stage_desc,
                        unit="batch",
                        disable=bool(args.quiet),
                    )
                ):
                    batch_indices = active_indices[batch_start:batch_end]
                    if prefetch_workers > 0:
                        if batch_idx > 0:
                            if prefetch_future is None:
                                raise RuntimeError("Internal prefetch state error: missing future")
                            current_batch_items, current_requests = prefetch_future.result()
                        next_idx = batch_idx + 1
                        if next_idx < len(batch_ranges):
                            next_start, next_end = batch_ranges[next_idx]
                            next_indices = active_indices[next_start:next_end]
                            prefetch_future = prefetch_executor.submit(
                                _prepare_batch_payload,
                                dataset=dataset,
                                batch_indices=next_indices,
                            )
                        else:
                            prefetch_future = None
                        if current_batch_items is None or current_requests is None:
                            raise RuntimeError("Internal prefetch state error: missing current batch")
                        batch_items = current_batch_items
                        requests = current_requests
                    else:
                        batch_items, requests = _prepare_batch_payload(dataset=dataset, batch_indices=batch_indices)

                    outputs = llm.generate(requests, sampling_params=sampling_params, use_tqdm=False)
                    if score_executor is not None:
                        score_futures.append(
                            score_executor.submit(
                                _score_generated_outputs,
                                args=args,
                                records=records,
                                batch_indices=batch_indices,
                                batch_items=batch_items,
                                outputs=outputs,
                            )
                        )
                        while len(score_futures) >= score_backlog:
                            drain_score_future()
                    else:
                        batch_stats = _score_generated_outputs(
                            args=args,
                            records=records,
                            batch_indices=batch_indices,
                            batch_items=batch_items,
                            outputs=outputs,
                        )
                        _merge_counter_stats(stage_stats_total, batch_stats)
                while score_futures:
                    drain_score_future()
            finally:
                if score_executor is not None:
                    score_executor.shutdown(wait=True)

        easy_cutoff = _ceil_rate_count(args.easy_rate, cumulative_rollouts)
        if cumulative_rollouts >= args.max_rollouts:
            next_active: list[int] = []
        else:
            next_active = [
                index
                for index in active_indices
                if int(records[index]["positive_rollout_count"]) == 0
                or int(records[index]["positive_rollout_count"]) >= easy_cutoff
            ]
        stage_summary = {
            "stage_number": int(stage_number),
            "stage_rollouts": int(args.stage_rollouts),
            "cumulative_rollouts": int(cumulative_rollouts),
            "easy_rate": float(args.easy_rate),
            "easy_cutoff_positive_count": int(easy_cutoff),
            "input_prompt_count": int(stage_input_count),
            "input_fraction_of_original": float(stage_input_count / original_prompt_count) if original_prompt_count else 0.0,
            "active_for_next_count": int(len(next_active)),
            "active_for_next_fraction_of_original": float(len(next_active) / original_prompt_count) if original_prompt_count else 0.0,
            "newly_retained_count": int(stage_input_count - len(next_active)),
            **{key: int(value) for key, value in sorted(stage_stats_total.items())},
        }
        stage_summaries.append(stage_summary)
        _write_json_atomic(args.output_dir / "stage_summary.json", {"stages": stage_summaries})
        active_indices = next_active
        _write_json_atomic(
            checkpoint_path,
            {
                "original_prompt_count": int(original_prompt_count),
                "next_stage_number": int(stage_number + 1),
                "active_indices": active_indices,
                "stage_summaries": stage_summaries,
                "records": {str(key): value for key, value in records.items()},
            },
        )

    final_rows = [_finalize_record(records[index], easy_rate=args.easy_rate) for index in sorted(records)]
    with per_instance_path.open("w", encoding="utf-8") as handle:
        for row in final_rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")

    retained_path = args.output_dir / "retained_indices.txt"
    retained_path.write_text(
        "\n".join(str(row["dataset_index"]) for row in final_rows if row["filter_status"] == "retained_band") + "\n",
        encoding="utf-8",
    )

    task_summary = _summarize_by_task(final_rows)
    (args.output_dir / "per_task_summary.json").write_text(
        json.dumps(task_summary, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    summary = {
        "parquet": str(Path(args.parquet).resolve()),
        "model": args.model,
        "worker": {
            "rank": int(args.worker_rank),
            "count": int(args.worker_count),
            "start_index": int(start_index),
            "end_index_exclusive": int(end_index),
            "prompt_count": int(original_prompt_count),
        },
        "settings": {
            "trace_output_mode": args.trace_output_mode,
            "prompt_key": args.prompt_key,
            "system_prompt": system_prompt,
            "trace_reward_mode": args.trace_reward_mode,
            "trace_answer_scoring": args.trace_answer_scoring,
            "trace_format_weight": args.trace_format_weight,
            "probe_extraction_mode": "final_json_then_json_fallback",
            "stage_rollouts": args.stage_rollouts,
            "max_rollouts": args.max_rollouts,
            "easy_rate": args.easy_rate,
            "batch_size": args.batch_size,
            "effective_prompt_batch_size": prompt_batch_size,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "tensor_parallel_size": args.tensor_parallel_size,
            "max_prompt_length": args.max_prompt_length,
            "max_pixels": args.max_pixels,
            "filter_overlong_prompts": args.filter_overlong_prompts,
            "prefetch_workers": args.prefetch_workers,
            "score_workers": score_workers,
            "score_backlog": score_backlog,
            "resume": args.resume,
            "seed": args.seed,
        },
        "overall": _aggregate_rows(final_rows, name="overall"),
        "stages": stage_summaries,
        "elapsed_seconds": float(time.time() - started_at),
        "outputs": {
            "per_instance_jsonl": str(per_instance_path),
            "retained_indices": str(retained_path),
            "task_summary_json": str(args.output_dir / "per_task_summary.json"),
            "stage_summary_json": str(args.output_dir / "stage_summary.json"),
        },
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    return summary


def _merge_summaries(output_dir: Path, worker_dirs: list[Path], *, started_at: float) -> dict[str, Any]:
    worker_summaries = [json.loads((worker_dir / "summary.json").read_text(encoding="utf-8")) for worker_dir in worker_dirs]
    all_rows: list[dict[str, Any]] = []
    for worker_dir in worker_dirs:
        with (worker_dir / "per_instance_staged.jsonl").open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    all_rows.append(json.loads(line))

    stage_totals: dict[int, dict[str, Any]] = {}
    for worker_summary in worker_summaries:
        for stage in worker_summary.get("stages", []):
            stage_number = int(stage["stage_number"])
            aggregate = stage_totals.setdefault(
                stage_number,
                {
                    "stage_number": stage_number,
                    "stage_rollouts": int(stage["stage_rollouts"]),
                    "cumulative_rollouts": int(stage["cumulative_rollouts"]),
                    "easy_rate": float(stage["easy_rate"]),
                    "easy_cutoff_positive_count": int(stage["easy_cutoff_positive_count"]),
                    "input_prompt_count": 0,
                    "active_for_next_count": 0,
                    "newly_retained_count": 0,
                    "rollout_count": 0,
                    "positive_rollout_count": 0,
                    "perfect_rollout_count": 0,
                    "max_token_rollout_count": 0,
                    "json_found_count": 0,
                    "extraction_none_count": 0,
                },
            )
            for key in (
                "input_prompt_count",
                "active_for_next_count",
                "newly_retained_count",
                "rollout_count",
                "positive_rollout_count",
                "perfect_rollout_count",
                "max_token_rollout_count",
                "json_found_count",
                "extraction_none_count",
            ):
                aggregate[key] += int(stage.get(key, 0))

    total_original = sum(
        int(stage["input_prompt_count"])
        for stage in stage_totals.values()
        if int(stage["stage_number"]) == 1
    )
    merged_stages = []
    for stage_number in sorted(stage_totals):
        stage = stage_totals[stage_number]
        stage["input_fraction_of_original"] = (
            float(stage["input_prompt_count"] / total_original) if total_original else 0.0
        )
        stage["active_for_next_fraction_of_original"] = (
            float(stage["active_for_next_count"] / total_original) if total_original else 0.0
        )
        merged_stages.append(stage)

    task_summary = _summarize_by_task(all_rows)
    (output_dir / "per_task_summary.json").write_text(
        json.dumps(task_summary, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    with (output_dir / "per_instance_staged.jsonl").open("w", encoding="utf-8") as handle:
        for row in sorted(all_rows, key=lambda row: int(row["dataset_index"])):
            handle.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")
    (output_dir / "retained_indices.txt").write_text(
        "\n".join(str(row["dataset_index"]) for row in sorted(all_rows, key=lambda row: int(row["dataset_index"])) if row["filter_status"] == "retained_band") + "\n",
        encoding="utf-8",
    )

    merged = {
        "worker_count": len(worker_summaries),
        "workers": worker_summaries,
        "overall": _aggregate_rows(all_rows, name="overall"),
        "stages": merged_stages,
        "elapsed_seconds": float(time.time() - started_at),
        "outputs": {
            "per_instance_jsonl": str(output_dir / "per_instance_staged.jsonl"),
            "retained_indices": str(output_dir / "retained_indices.txt"),
            "task_summary_json": str(output_dir / "per_task_summary.json"),
            "worker_dirs": [str(path) for path in worker_dirs],
        },
    }
    (output_dir / "summary.json").write_text(
        json.dumps(merged, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    return merged


def _run_parent(args: argparse.Namespace) -> dict[str, Any]:
    started_at = time.time()
    output_dir = args.output_dir
    if output_dir.exists() and args.overwrite:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gpu_ids = _detect_visible_gpu_ids()
    worker_count = int(args.replica_workers) if int(args.replica_workers) > 0 else len(gpu_ids)
    if worker_count <= 0:
        raise RuntimeError("No GPUs detected; set CUDA_VISIBLE_DEVICES or --replica-workers explicitly.")
    if worker_count > len(gpu_ids):
        raise ValueError(f"Requested {worker_count} workers but only {len(gpu_ids)} visible GPUs: {gpu_ids}")
    if int(args.tensor_parallel_size) > 1 and worker_count > 1:
        raise ValueError("Use either replica workers or tensor parallelism, not both in the staged launcher.")

    dataset_len = args.count if args.count is not None else None
    if dataset_len is None:
        import pyarrow.parquet as pq

        dataset_len = pq.ParquetFile(args.parquet).metadata.num_rows - int(args.start_index)
    ranges = _split_prompt_ranges(int(args.start_index), int(args.start_index) + int(dataset_len), worker_count)

    worker_dirs: list[Path] = []
    processes: list[subprocess.Popen[Any]] = []
    for rank, (start, end) in enumerate(ranges):
        worker_dir = output_dir / f"worker_{rank:02d}"
        worker_dir.mkdir(parents=True, exist_ok=True)
        worker_dirs.append(worker_dir)
        env = os.environ.copy()
        if int(args.tensor_parallel_size) > 1:
            env["CUDA_VISIBLE_DEVICES"] = ",".join(gpu_ids[: int(args.tensor_parallel_size)])
        else:
            env["CUDA_VISIBLE_DEVICES"] = gpu_ids[rank]
        env["PYTHONPATH"] = f"{RLVR_ROOT}:{env.get('PYTHONPATH', '')}".rstrip(":")
        cmd = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker-mode",
            "--worker-rank",
            str(rank),
            "--worker-count",
            str(worker_count),
            "--parquet",
            str(args.parquet),
            "--output-dir",
            str(worker_dir),
            "--model",
            args.model,
            "--trace-output-mode",
            args.trace_output_mode,
            "--prompt-key",
            args.prompt_key,
            "--system-prompt",
            str(args.system_prompt),
            "--trace-reward-mode",
            args.trace_reward_mode,
            "--trace-answer-scoring",
            args.trace_answer_scoring,
            "--trace-format-weight",
            str(args.trace_format_weight),
            "--start-index",
            str(start),
            "--count",
            str(end - start),
            "--batch-size",
            str(args.batch_size),
            "--stage-rollouts",
            str(args.stage_rollouts),
            "--max-rollouts",
            str(args.max_rollouts),
            "--easy-rate",
            str(args.easy_rate),
            "--temperature",
            str(args.temperature),
            "--max-tokens",
            str(args.max_tokens),
            "--tensor-parallel-size",
            str(args.tensor_parallel_size),
            "--gpu-memory-utilization",
            str(args.gpu_memory_utilization),
            "--max-model-len",
            str(args.max_model_len),
            "--max-num-batched-tokens",
            str(args.max_num_batched_tokens),
            "--max-num-seqs",
            str(args.max_num_seqs),
            "--max-prompt-length",
            str(args.max_prompt_length),
            "--max-pixels",
            str(args.max_pixels),
            "--seed",
            str(args.seed + rank),
            "--prefetch-workers",
            str(args.prefetch_workers),
            "--score-workers",
            str(args.score_workers),
            "--score-backlog",
            str(args.score_backlog),
        ]
        if args.attention_backend:
            cmd.extend(["--attention-backend", str(args.attention_backend)])
        if args.disable_trtllm_attention:
            cmd.append("--disable-trtllm-attention")
        if args.resume:
            cmd.append("--resume")
        if args.filter_overlong_prompts:
            cmd.append("--filter-overlong-prompts")
        if args.enforce_eager:
            cmd.append("--enforce-eager")
        if args.quiet:
            cmd.append("--quiet")

        log_handle = (worker_dir / "worker.log").open("w", encoding="utf-8")
        process = subprocess.Popen(cmd, env=env, stdout=log_handle, stderr=subprocess.STDOUT)
        processes.append(process)
        print(f"[launch] worker={rank} gpu={env['CUDA_VISIBLE_DEVICES']} rows={start}:{end} log={worker_dir / 'worker.log'}", flush=True)

    failed = []
    for rank, process in enumerate(processes):
        return_code = process.wait()
        if return_code != 0:
            failed.append((rank, return_code, worker_dirs[rank] / "worker.log"))
    if failed:
        details = ", ".join(f"worker {rank} rc={rc} log={log}" for rank, rc, log in failed)
        raise RuntimeError(f"Staged probe worker failure: {details}")

    return _merge_summaries(output_dir, worker_dirs, started_at=started_at)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run staged TRACE curriculum rollouts and keep probing only extreme prompts.")
    parser.add_argument("--parquet", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default="Qwen/Qwen3-VL-4B-Instruct")
    parser.add_argument("--trace-output-mode", default="answer", choices=("answer", "answer_and_evidence", "evidence"))
    parser.add_argument("--prompt-key", default="prompt_answer")
    parser.add_argument("--system-prompt", default=str(RLVR_ROOT / "examples/prompts/trace_vero_json_system_prompt_answer.txt"))
    parser.add_argument("--trace-reward-mode", default="answer", choices=("answer", "answer_and_evidence", "auto"))
    parser.add_argument("--trace-answer-scoring", default="exact_json", choices=("legacy_strict", "exact_json", "strict", "legacy", "exact"))
    parser.add_argument("--trace-format-weight", type=float, default=0.0)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--count", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=1024, help="Rollout batch budget per worker per generate() call.")
    parser.add_argument("--stage-rollouts", type=int, default=4)
    parser.add_argument("--max-rollouts", type=int, default=16)
    parser.add_argument("--easy-rate", type=float, default=0.875)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=1536)
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--replica-workers", type=int, default=0)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.9)
    parser.add_argument("--max-model-len", type=int, default=4096)
    parser.add_argument("--max-num-batched-tokens", type=int, default=16384)
    parser.add_argument("--max-num-seqs", type=int, default=1024)
    parser.add_argument("--max-prompt-length", type=int, default=1536)
    parser.add_argument("--max-pixels", type=int, default=1048576)
    parser.add_argument("--filter-overlong-prompts", action="store_true")
    parser.add_argument("--prefetch-workers", type=int, default=1)
    parser.add_argument("--score-workers", type=int, default=1)
    parser.add_argument("--score-backlog", type=int, default=2)
    parser.add_argument("--seed", type=int, default=18)
    parser.add_argument("--enforce-eager", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--attention-backend", default=None)
    parser.add_argument("--disable-trtllm-attention", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--worker-mode", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker-rank", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--worker-count", type=int, default=1, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if int(args.max_rollouts) % int(args.stage_rollouts) != 0:
        raise ValueError("--max-rollouts must be divisible by --stage-rollouts")
    if args.worker_mode:
        summary = _run_worker(args)
    else:
        summary = _run_parent(args)
    print(json.dumps({"overall": summary.get("overall"), "outputs": summary.get("outputs")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
