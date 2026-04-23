from __future__ import annotations

import argparse
from concurrent.futures import Future, ThreadPoolExecutor
import json
import math
import os
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARN")

RLVR_ROOT = Path(__file__).resolve().parents[1]
if str(RLVR_ROOT) not in sys.path:
    sys.path.insert(0, str(RLVR_ROOT))


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _maybe_parse_json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{"):
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
    raise TypeError(f"Expected a mapping-like TRACE metadata value, got {type(value).__name__}")


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _probe_jsonable(value: Any) -> Any:
    if value is Ellipsis:
        return "..."
    if isinstance(value, dict):
        return {str(key): _probe_jsonable(item_value) for key, item_value in value.items()}
    if isinstance(value, (list, tuple)):
        return [_probe_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [_probe_jsonable(item) for item in value]
    if not isinstance(value, (str, bytes)):
        if hasattr(value, "tolist"):
            try:
                return _probe_jsonable(value.tolist())
            except Exception:
                pass
        if hasattr(value, "item"):
            try:
                return _probe_jsonable(value.item())
            except Exception:
                pass
    return value


def _resolve_system_prompt_arg(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized.lower() in {"", "none", "null", "__none__"}:
        return None
    return normalized


def _build_dataset(
    parquet_path: str,
    model: str,
    *,
    trace_output_mode: str,
    prompt_key: str,
    system_prompt: str | None,
    max_prompt_length: int,
    max_pixels: int,
    filter_overlong_prompts: bool,
) -> Any:
    from omegaconf import OmegaConf
    from transformers import AutoProcessor, AutoTokenizer

    from verl.utils.dataset.trace_rl_dataset import TraceRLHFDataset

    tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=False)
    processor = AutoProcessor.from_pretrained(model, trust_remote_code=False)
    config = OmegaConf.create(
        {
            "trace_output_mode": trace_output_mode,
            "prompt_key": prompt_key,
            "answer_key": "answer_gt",
            "image_key": "images",
            "video_key": "videos",
            "system_prompt": system_prompt if system_prompt is not None else "__TRACE_NO_SYSTEM_PROMPT__",
            "max_prompt_length": max_prompt_length,
            "truncation": "error",
            "min_pixels": None,
            "max_pixels": max_pixels,
            "filter_overlong_prompts": filter_overlong_prompts,
            "filter_overlong_prompts_workers": 1,
            "default_data_source": "trace_curriculum_probe",
        }
    )
    dataset = TraceRLHFDataset(parquet_path, tokenizer=tokenizer, processor=processor, config=config)
    if system_prompt is None:
        dataset.system_prompt = None
    return dataset


def _normalize_probe_response(
    *,
    response: str,
    trace_reward_mode: str,
) -> tuple[str, str]:
    """Normalize one probe response for lenient curriculum scoring.

    Probe-only extraction policy:
    1. prefer JSON recovered from `<answer>...</answer>`
    2. otherwise fall back to valid JSON found anywhere in the response
    """

    from verl.utils.trace_reward import extract_trace_prediction

    answer_value, evidence_value, json_found = extract_trace_prediction(response)
    if not json_found:
        return response, "none"

    normalized_mode = str(trace_reward_mode or "").strip().lower()
    if normalized_mode in {"answer", "answer_only"}:
        if answer_value is None:
            return response, "none"
        payload: dict[str, Any] = {"answer": answer_value}
    else:
        payload = {}
        if evidence_value is not None:
            payload["evidence"] = evidence_value
        if answer_value is not None:
            payload["answer"] = answer_value
        if not payload:
            return response, "none"
    payload = _probe_jsonable(payload)
    return (
        f"<answer>{json.dumps(payload, ensure_ascii=False, default=_json_default)}</answer>",
        "answer_tag_then_json_fallback",
    )


def _build_requests(batch_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for item in batch_items:
        request: dict[str, Any] = {"prompt_token_ids": list(item["raw_prompt_ids"])}
        if "multi_modal_data" in item:
            request["multi_modal_data"] = item["multi_modal_data"]
        requests.append(request)
    return requests


def _prepare_batch_payload(
    *,
    dataset: Any,
    batch_indices: list[int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    batch_items = [dataset[index] for index in batch_indices]
    requests = _build_requests(batch_items)
    return batch_items, requests


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _detect_visible_gpu_ids() -> list[str]:
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
    if visible:
        return [part.strip() for part in visible.split(",") if part.strip()]
    output = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
        text=True,
    )
    return [line.strip() for line in output.splitlines() if line.strip()]


def _split_prompt_ranges(start_index: int, end_index: int, shard_count: int) -> list[tuple[int, int]]:
    total = max(0, end_index - start_index)
    if total <= 0:
        return []
    shard_count = max(1, min(shard_count, total))
    base = total // shard_count
    remainder = total % shard_count
    cursor = start_index
    ranges: list[tuple[int, int]] = []
    for shard_rank in range(shard_count):
        shard_size = base + (1 if shard_rank < remainder else 0)
        shard_end = cursor + shard_size
        ranges.append((cursor, shard_end))
        cursor = shard_end
    return ranges


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, default=_json_default), encoding="utf-8")
    tmp_path.replace(path)


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for count, _ in enumerate(handle, 1):
            pass
    return count


def _build_instance_row(
    *,
    dataset_index: int,
    item: dict[str, Any],
    rollout_scores: list[dict[str, float]],
    token_counts: list[int],
    extraction_sources: list[str],
) -> dict[str, Any]:
    task_rewards = [float(score["task_reward_raw"]) for score in rollout_scores]
    answer_rewards = [float(score["answer_reward"]) for score in rollout_scores]
    overall_rewards = [float(score["overall"]) for score in rollout_scores]
    format_rewards = [float(score["format"]) for score in rollout_scores]
    json_found = [float(score["json_found"]) for score in rollout_scores]
    format_json_ok = [float(score["format_json_ok"]) for score in rollout_scores]
    format_schema_ok = [float(score["format_schema_ok"]) for score in rollout_scores]

    positive_rollout_count = sum(1 for reward in task_rewards if float(reward) > 0.0)
    perfect_rollout_count = sum(1 for reward in task_rewards if float(reward) >= 1.0)
    rollout_count = len(rollout_scores)
    answer_gt = _maybe_parse_json_mapping(item["answer_gt"])
    evidence_gt = _maybe_parse_json_mapping(item["evidence_gt"])

    return {
        "dataset_index": int(dataset_index),
        "uid": str(item.get("uid", "")),
        "domain": str(item.get("domain", "")),
        "task_group": str(item.get("task_group", "")),
        "task": str(item.get("task", "")),
        "complexity_score": _as_float(item.get("complexity_score")),
        "difficulty_bin": None if item.get("difficulty_bin") is None else int(item.get("difficulty_bin")),
        "bucket_id_str": None if item.get("bucket_id_str") is None else str(item.get("bucket_id_str")),
        "prompt_length": int(len(item["raw_prompt_ids"])),
        "rollout_count": int(rollout_count),
        "positive_rollout_count": int(positive_rollout_count),
        "perfect_rollout_count": int(perfect_rollout_count),
        "solve_rate": float(positive_rollout_count / rollout_count) if rollout_count else 0.0,
        "perfect_rate": float(perfect_rollout_count / rollout_count) if rollout_count else 0.0,
        "zero_solve": bool(positive_rollout_count == 0),
        "perfect_solve": bool(perfect_rollout_count == rollout_count and rollout_count > 0),
        "mean_task_reward": _mean(task_rewards),
        "mean_answer_reward": _mean(answer_rewards),
        "mean_overall_reward": _mean(overall_rewards),
        "mean_format_reward": _mean(format_rewards),
        "json_found_rate": _mean(json_found),
        "format_json_ok_rate": _mean(format_json_ok),
        "format_schema_ok_rate": _mean(format_schema_ok),
        "probe_extraction_fallback_rate": _mean([1.0 if source != "none" else 0.0 for source in extraction_sources]),
        "mean_generated_tokens": _mean([float(count) for count in token_counts]),
        "max_generated_tokens": max(token_counts) if token_counts else 0,
        "answer_type": str(answer_gt.get("type", "")),
        "evidence_type": str(evidence_gt.get("type", "")),
    }


def _empty_aggregate() -> dict[str, float]:
    return {
        "prompt_count": 0,
        "rollout_count": 0,
        "positive_rollout_count": 0,
        "perfect_rollout_count": 0,
        "zero_solve_count": 0,
        "perfect_solve_count": 0,
        "sum_mean_task_reward": 0.0,
        "sum_mean_answer_reward": 0.0,
        "sum_mean_overall_reward": 0.0,
        "sum_mean_format_reward": 0.0,
        "sum_prompt_length": 0.0,
        "sum_mean_generated_tokens": 0.0,
        "max_generated_tokens": 0.0,
    }


def _update_aggregate(aggregate: dict[str, float], row: dict[str, Any]) -> None:
    aggregate["prompt_count"] += 1
    aggregate["rollout_count"] += int(row["rollout_count"])
    aggregate["positive_rollout_count"] += int(row["positive_rollout_count"])
    aggregate["perfect_rollout_count"] += int(row["perfect_rollout_count"])
    aggregate["zero_solve_count"] += 1 if bool(row["zero_solve"]) else 0
    aggregate["perfect_solve_count"] += 1 if bool(row["perfect_solve"]) else 0
    aggregate["sum_mean_task_reward"] += float(row["mean_task_reward"])
    aggregate["sum_mean_answer_reward"] += float(row["mean_answer_reward"])
    aggregate["sum_mean_overall_reward"] += float(row["mean_overall_reward"])
    aggregate["sum_mean_format_reward"] += float(row["mean_format_reward"])
    aggregate["sum_prompt_length"] += float(row["prompt_length"])
    aggregate["sum_mean_generated_tokens"] += float(row["mean_generated_tokens"])
    aggregate["max_generated_tokens"] = max(float(aggregate["max_generated_tokens"]), float(row["max_generated_tokens"]))


def _finalize_aggregate(name: str, aggregate: dict[str, float]) -> dict[str, Any]:
    prompt_count = int(aggregate["prompt_count"])
    rollout_count = int(aggregate["rollout_count"])
    return {
        "name": str(name),
        "prompt_count": prompt_count,
        "rollout_count": rollout_count,
        "positive_rollout_rate": float(aggregate["positive_rollout_count"] / rollout_count) if rollout_count else 0.0,
        "perfect_rollout_rate": float(aggregate["perfect_rollout_count"] / rollout_count) if rollout_count else 0.0,
        "zero_solve_rate": float(aggregate["zero_solve_count"] / prompt_count) if prompt_count else 0.0,
        "perfect_solve_rate": float(aggregate["perfect_solve_count"] / prompt_count) if prompt_count else 0.0,
        "mean_task_reward": float(aggregate["sum_mean_task_reward"] / prompt_count) if prompt_count else 0.0,
        "mean_answer_reward": float(aggregate["sum_mean_answer_reward"] / prompt_count) if prompt_count else 0.0,
        "mean_overall_reward": float(aggregate["sum_mean_overall_reward"] / prompt_count) if prompt_count else 0.0,
        "mean_format_reward": float(aggregate["sum_mean_format_reward"] / prompt_count) if prompt_count else 0.0,
        "mean_prompt_length": float(aggregate["sum_prompt_length"] / prompt_count) if prompt_count else 0.0,
        "mean_generated_tokens": float(aggregate["sum_mean_generated_tokens"] / prompt_count) if prompt_count else 0.0,
        "max_generated_tokens": int(aggregate["max_generated_tokens"]),
    }


def _run_single_probe(args: argparse.Namespace) -> dict[str, Any]:
    from tqdm.auto import tqdm
    from vllm import LLM, SamplingParams

    from verl.utils.trace_reward import score_trace_response

    args.output_dir.mkdir(parents=True, exist_ok=True)

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

    start_index = max(0, int(args.start_index))
    dataset_len = len(dataset)
    if start_index >= dataset_len:
        raise ValueError(f"start_index={start_index} is outside dataset length {dataset_len}")
    end_index = dataset_len if args.count is None else min(dataset_len, start_index + max(0, int(args.count)))
    total_prompts = max(0, end_index - start_index)
    if total_prompts <= 0:
        raise ValueError("No prompts selected for probing")

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
    )
    sampling_params = SamplingParams(
        n=args.rollouts_per_prompt,
        temperature=args.temperature,
        top_p=1.0,
        top_k=-1,
        max_tokens=args.max_tokens,
        skip_special_tokens=True,
    )

    per_instance_path = args.output_dir / "per_instance.jsonl"
    summary_path = args.output_dir / "summary.json"
    task_summary_path = args.output_dir / "per_task_summary.json"
    bucket_summary_path = args.output_dir / "per_task_bucket_summary.json"
    progress_path = Path(args.progress_file) if getattr(args, "progress_file", None) else None
    append_output = bool(getattr(args, "append_output", False))
    existing_rows = _count_jsonl_rows(per_instance_path) if append_output else 0

    overall_aggregate = _empty_aggregate()
    task_aggregates: dict[str, dict[str, float]] = defaultdict(_empty_aggregate)
    bucket_aggregates: dict[str, dict[str, float]] = defaultdict(_empty_aggregate)
    batch_ranges = [
        (batch_start, min(end_index, batch_start + args.batch_size))
        for batch_start in range(start_index, end_index, args.batch_size)
    ]

    file_mode = "a" if append_output else "w"
    with per_instance_path.open(file_mode, encoding="utf-8") as handle, tqdm(
        total=total_prompts,
        desc="Curriculum probe",
        unit="prompt",
        disable=bool(progress_path),
    ) as progress:
        completed_prompts = existing_rows
        prefetch_workers = max(0, int(args.prefetch_workers))
        with ThreadPoolExecutor(max_workers=max(1, prefetch_workers or 1)) as executor:
            current_indices = list(range(*batch_ranges[0]))
            if prefetch_workers > 0:
                current_batch_items, current_requests = _prepare_batch_payload(
                    dataset=dataset,
                    batch_indices=current_indices,
                )
                prefetch_future: Future[tuple[list[dict[str, Any]], list[dict[str, Any]]]] | None = None
            else:
                current_batch_items, current_requests = _prepare_batch_payload(
                    dataset=dataset,
                    batch_indices=current_indices,
                )
                prefetch_future = None

            for batch_idx, batch_range in enumerate(batch_ranges):
                batch_start, batch_end = batch_range
                batch_indices = list(range(batch_start, batch_end))

                if batch_idx > 0:
                    if prefetch_future is not None:
                        current_batch_items, current_requests = prefetch_future.result()
                    else:
                        current_batch_items, current_requests = _prepare_batch_payload(
                            dataset=dataset,
                            batch_indices=batch_indices,
                        )

                next_batch_idx = batch_idx + 1
                if prefetch_workers > 0 and next_batch_idx < len(batch_ranges):
                    next_batch_start, next_batch_end = batch_ranges[next_batch_idx]
                    next_batch_indices = list(range(next_batch_start, next_batch_end))
                    prefetch_future = executor.submit(
                        _prepare_batch_payload,
                        dataset=dataset,
                        batch_indices=next_batch_indices,
                    )
                else:
                    prefetch_future = None

                outputs = llm.generate(current_requests, sampling_params=sampling_params, use_tqdm=False)

                batch_solve_rates: list[float] = []
                for dataset_index, item, generated in zip(batch_indices, current_batch_items, outputs, strict=True):
                    rollout_scores: list[dict[str, float]] = []
                    token_counts: list[int] = []
                    extraction_sources: list[str] = []
                    answer_gt = _maybe_parse_json_mapping(item["answer_gt"])
                    evidence_gt = _maybe_parse_json_mapping(item["evidence_gt"])
                    reward_contract = _maybe_parse_json_mapping(item["reward_contract"])

                    for completion in generated.outputs:
                        response = completion.text
                        normalized_response, extraction_source = _normalize_probe_response(
                            response=response,
                            trace_reward_mode=args.trace_reward_mode,
                        )
                        rollout_scores.append(
                            score_trace_response(
                                response=normalized_response,
                                answer_gt=answer_gt,
                                evidence_gt=evidence_gt,
                                reward_contract=reward_contract,
                                trace_reward_mode=args.trace_reward_mode,
                                trace_answer_scoring=args.trace_answer_scoring,
                                format_weight=args.trace_format_weight,
                            )
                        )
                        extraction_sources.append(str(extraction_source))
                        token_counts.append(len(completion.token_ids or []))

                    row = _build_instance_row(
                        dataset_index=dataset_index,
                        item=item,
                        rollout_scores=rollout_scores,
                        token_counts=token_counts,
                        extraction_sources=extraction_sources,
                    )
                    handle.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")

                    _update_aggregate(overall_aggregate, row)
                    task_key = str(row["task"])
                    bucket_key = f"{task_key}::{row['bucket_id_str'] if row['bucket_id_str'] is not None else row['difficulty_bin']}"
                    _update_aggregate(task_aggregates[task_key], row)
                    _update_aggregate(bucket_aggregates[bucket_key], row)
                    batch_solve_rates.append(float(row["solve_rate"]))

                progress.update(len(batch_indices))
                completed_prompts += len(batch_indices)
                progress.set_postfix(
                    batch_prompts=len(batch_indices),
                    batch_solve_rate=f"{_mean(batch_solve_rates):.3f}",
                    global_solve_rate=f"{_finalize_aggregate('overall', overall_aggregate)['positive_rollout_rate']:.3f}",
                    prefetch_workers=prefetch_workers,
                )
                if progress_path is not None:
                    _write_json_atomic(
                        progress_path,
                        {
                            "prompts_completed": completed_prompts,
                            "prompts_total": total_prompts,
                            "last_batch_size": len(batch_indices),
                            "last_batch_solve_rate": _mean(batch_solve_rates),
                        },
                    )

    summary = {
        "parquet": str(Path(args.parquet).resolve()),
        "model": args.model,
        "selected_range": {
            "start_index": start_index,
            "end_index_exclusive": end_index,
            "prompt_count": total_prompts,
        },
        "settings": {
            "trace_output_mode": args.trace_output_mode,
            "prompt_key": args.prompt_key,
            "system_prompt": system_prompt,
            "trace_reward_mode": args.trace_reward_mode,
            "trace_answer_scoring": args.trace_answer_scoring,
            "probe_extraction_mode": "answer_tag_then_json_fallback",
            "trace_format_weight": args.trace_format_weight,
            "batch_size": args.batch_size,
            "rollouts_per_prompt": args.rollouts_per_prompt,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "tensor_parallel_size": args.tensor_parallel_size,
            "gpu_memory_utilization": args.gpu_memory_utilization,
            "max_model_len": args.max_model_len,
            "max_num_batched_tokens": args.max_num_batched_tokens,
            "max_num_seqs": args.max_num_seqs,
            "max_prompt_length": args.max_prompt_length,
            "max_pixels": args.max_pixels,
            "filter_overlong_prompts": args.filter_overlong_prompts,
            "prefetch_workers": args.prefetch_workers,
            "seed": args.seed,
            "enforce_eager": args.enforce_eager,
            "replica_workers": 1,
            "effective_batch_size_per_worker": args.batch_size,
            "append_output": append_output,
            "existing_rows_before_run": existing_rows,
        },
        "overall": _finalize_aggregate("overall", overall_aggregate),
        "outputs": {
            "per_instance_jsonl": str(per_instance_path),
            "task_summary_json": str(task_summary_path),
            "bucket_summary_json": str(bucket_summary_path),
        },
    }

    task_summaries = []
    for task_name, aggregate in sorted(task_aggregates.items()):
        payload = _finalize_aggregate(task_name, aggregate)
        payload["task"] = str(task_name)
        task_summaries.append(payload)

    bucket_summaries = []
    for bucket_name, aggregate in sorted(bucket_aggregates.items()):
        task_name, _, bucket_id = str(bucket_name).partition("::")
        payload = _finalize_aggregate(bucket_name, aggregate)
        payload["task"] = str(task_name)
        payload["bucket"] = str(bucket_id)
        bucket_summaries.append(payload)

    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    task_summary_path.write_text(json.dumps(task_summaries, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    bucket_summary_path.write_text(
        json.dumps(bucket_summaries, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    print(f"[done] wrote {summary_path}")
    print(f"[done] wrote {task_summary_path}")
    print(f"[done] wrote {bucket_summary_path}")
    if progress_path is not None:
        _write_json_atomic(
            progress_path,
            {
                "prompts_completed": completed_prompts,
                "prompts_total": existing_rows + total_prompts,
                "done": True,
            },
        )
    return summary


def _run_sharded_probe(args: argparse.Namespace) -> dict[str, Any]:
    from tqdm.auto import tqdm

    args.output_dir.mkdir(parents=True, exist_ok=True)
    visible_gpu_ids = _detect_visible_gpu_ids()
    requested_workers = int(args.replica_workers)
    if requested_workers <= 0:
        requested_workers = len(visible_gpu_ids)
    worker_count = max(1, min(requested_workers, len(visible_gpu_ids)))

    dataset = _build_dataset(
        args.parquet,
        args.model,
        trace_output_mode=args.trace_output_mode,
        prompt_key=args.prompt_key,
        system_prompt=_resolve_system_prompt_arg(args.system_prompt),
        max_prompt_length=args.max_prompt_length,
        max_pixels=args.max_pixels,
        filter_overlong_prompts=args.filter_overlong_prompts,
    )
    start_index = max(0, int(args.start_index))
    dataset_len = len(dataset)
    if start_index >= dataset_len:
        raise ValueError(f"start_index={start_index} is outside dataset length {dataset_len}")
    end_index = dataset_len if args.count is None else min(dataset_len, start_index + max(0, int(args.count)))
    total_prompts = max(0, end_index - start_index)
    if total_prompts <= 0:
        raise ValueError("No prompts selected for probing")

    worker_ranges = _split_prompt_ranges(start_index, end_index, worker_count)
    effective_worker_count = len(worker_ranges)
    per_worker_batch_size = max(1, math.ceil(args.batch_size / effective_worker_count))
    resume = bool(getattr(args, "resume", False))

    worker_processes: list[tuple[subprocess.Popen[str], Path, Path, int]] = []
    existing_rows_by_worker: dict[int, int] = {}
    script_path = Path(__file__).resolve()
    for worker_rank, ((worker_start, worker_end), gpu_id) in enumerate(
        zip(worker_ranges, visible_gpu_ids[:effective_worker_count], strict=True)
    ):
        worker_dir = args.output_dir / f"worker_{worker_rank:02d}"
        if worker_dir.exists() and not resume:
            shutil.rmtree(worker_dir)
        worker_dir.mkdir(parents=True, exist_ok=True)
        progress_file = worker_dir / "_progress.json"
        log_file = worker_dir / "worker.log"
        existing_rows = _count_jsonl_rows(worker_dir / "per_instance.jsonl") if resume else 0
        shard_size = worker_end - worker_start
        existing_rows = min(existing_rows, shard_size)
        existing_rows_by_worker[worker_rank] = existing_rows
        remaining_count = shard_size - existing_rows
        if remaining_count <= 0:
            continue
        cmd = [
            sys.executable,
            str(script_path),
            "--parquet",
            str(args.parquet),
            "--output-dir",
            str(worker_dir),
            "--model",
            str(args.model),
            "--trace-output-mode",
            str(args.trace_output_mode),
            "--prompt-key",
            str(args.prompt_key),
            "--system-prompt",
            str(args.system_prompt),
            "--trace-reward-mode",
            str(args.trace_reward_mode),
            "--trace-answer-scoring",
            str(args.trace_answer_scoring),
            "--trace-format-weight",
            str(args.trace_format_weight),
            "--start-index",
            str(worker_start + existing_rows),
            "--count",
            str(remaining_count),
            "--batch-size",
            str(per_worker_batch_size),
            "--rollouts-per-prompt",
            str(args.rollouts_per_prompt),
            "--temperature",
            str(args.temperature),
            "--max-tokens",
            str(args.max_tokens),
            "--tensor-parallel-size",
            "1",
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
            "--prefetch-workers",
            str(args.prefetch_workers),
            "--seed",
            str(args.seed + worker_rank),
            "--progress-file",
            str(progress_file),
            "--replica-workers",
            "1",
            "--append-output",
        ]
        if args.filter_overlong_prompts:
            cmd.append("--filter-overlong-prompts")
        if args.enforce_eager:
            cmd.append("--enforce-eager")
        else:
            cmd.append("--no-enforce-eager")
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        log_mode = "a" if resume else "w"
        with log_file.open(log_mode, encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                cmd,
                cwd=str(Path.cwd()),
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
        worker_processes.append((process, progress_file, log_file, worker_rank))

    completed = sum(existing_rows_by_worker.values())
    with tqdm(total=total_prompts, desc="Curriculum probe", unit="prompt") as progress:
        if completed:
            progress.update(completed)
        while True:
            total_completed = 0
            active_workers = 0
            batch_solve_rates: list[float] = []
            for process, progress_file, _, worker_rank in worker_processes:
                if process.poll() is None:
                    active_workers += 1
                worker_completed = existing_rows_by_worker.get(worker_rank, 0)
                if progress_file.exists():
                    try:
                        payload = json.loads(progress_file.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        payload = {}
                    worker_completed = max(worker_completed, int(payload.get("prompts_completed", 0)))
                    if "last_batch_solve_rate" in payload:
                        batch_solve_rates.append(float(payload["last_batch_solve_rate"]))
                total_completed += worker_completed
            if total_completed > completed:
                progress.update(total_completed - completed)
                completed = total_completed
            progress.set_postfix(active_workers=active_workers, batch_solve_rate=f"{_mean(batch_solve_rates):.3f}")

            finished = [process.poll() for process, _, _, _ in worker_processes]
            if all(code is not None for code in finished):
                break
            time.sleep(1.0)

    failures = [(process.returncode, log_file) for process, _, log_file, _ in worker_processes if process.returncode != 0]
    if failures:
        failed_code, failed_log = failures[0]
        raise RuntimeError(f"One or more probe workers failed; first failure exit code={failed_code}, log={failed_log}")

    per_instance_path = args.output_dir / "per_instance.jsonl"
    task_summary_path = args.output_dir / "per_task_summary.json"
    bucket_summary_path = args.output_dir / "per_task_bucket_summary.json"
    summary_path = args.output_dir / "summary.json"

    overall_aggregate = _empty_aggregate()
    task_aggregates: dict[str, dict[str, float]] = defaultdict(_empty_aggregate)
    bucket_aggregates: dict[str, dict[str, float]] = defaultdict(_empty_aggregate)

    with per_instance_path.open("w", encoding="utf-8") as merged_handle:
        for worker_rank in range(effective_worker_count):
            worker_instance_path = args.output_dir / f"worker_{worker_rank:02d}" / "per_instance.jsonl"
            with worker_instance_path.open("r", encoding="utf-8") as worker_handle:
                for line in worker_handle:
                    row = json.loads(line)
                    merged_handle.write(line)
                    _update_aggregate(overall_aggregate, row)
                    task_key = str(row["task"])
                    bucket_key = f"{task_key}::{row['bucket_id_str'] if row['bucket_id_str'] is not None else row['difficulty_bin']}"
                    _update_aggregate(task_aggregates[task_key], row)
                    _update_aggregate(bucket_aggregates[bucket_key], row)

    task_summaries = []
    for task_name, aggregate in sorted(task_aggregates.items()):
        payload = _finalize_aggregate(task_name, aggregate)
        payload["task"] = str(task_name)
        task_summaries.append(payload)

    bucket_summaries = []
    for bucket_name, aggregate in sorted(bucket_aggregates.items()):
        task_name, _, bucket_id = str(bucket_name).partition("::")
        payload = _finalize_aggregate(bucket_name, aggregate)
        payload["task"] = str(task_name)
        payload["bucket"] = str(bucket_id)
        bucket_summaries.append(payload)

    system_prompt = _resolve_system_prompt_arg(args.system_prompt)
    summary = {
        "parquet": str(Path(args.parquet).resolve()),
        "model": args.model,
        "selected_range": {
            "start_index": start_index,
            "end_index_exclusive": end_index,
            "prompt_count": total_prompts,
        },
        "settings": {
            "trace_output_mode": args.trace_output_mode,
            "prompt_key": args.prompt_key,
            "system_prompt": system_prompt,
            "trace_reward_mode": args.trace_reward_mode,
            "trace_answer_scoring": args.trace_answer_scoring,
            "probe_extraction_mode": "answer_tag_then_json_fallback",
            "trace_format_weight": args.trace_format_weight,
            "batch_size": args.batch_size,
            "rollouts_per_prompt": args.rollouts_per_prompt,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "tensor_parallel_size": 1,
            "gpu_memory_utilization": args.gpu_memory_utilization,
            "max_model_len": args.max_model_len,
            "max_num_batched_tokens": args.max_num_batched_tokens,
            "max_num_seqs": args.max_num_seqs,
            "max_prompt_length": args.max_prompt_length,
            "max_pixels": args.max_pixels,
            "filter_overlong_prompts": args.filter_overlong_prompts,
            "prefetch_workers": args.prefetch_workers,
            "seed": args.seed,
            "enforce_eager": args.enforce_eager,
            "resume": resume,
            "replica_workers": effective_worker_count,
            "effective_batch_size_per_worker": per_worker_batch_size,
            "effective_global_batch_size": per_worker_batch_size * effective_worker_count,
            "visible_gpu_ids": visible_gpu_ids[:effective_worker_count],
        },
        "overall": _finalize_aggregate("overall", overall_aggregate),
        "outputs": {
            "per_instance_jsonl": str(per_instance_path),
            "task_summary_json": str(task_summary_path),
            "bucket_summary_json": str(bucket_summary_path),
        },
    }

    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    task_summary_path.write_text(json.dumps(task_summaries, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    bucket_summary_path.write_text(
        json.dumps(bucket_summaries, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    print(f"[done] wrote {summary_path}")
    print(f"[done] wrote {task_summary_path}")
    print(f"[done] wrote {bucket_summary_path}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Probe a TRACE RLVR parquet with sampled base-model rollouts, then emit "
            "per-instance and aggregated solve statistics for curriculum construction."
        )
    )
    parser.add_argument(
        "--parquet",
        default="rlvr/dataset/train/trace_rlvr_train_128k_all_tasks_verojson.parquet",
        help="TRACE RLVR parquet to probe.",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for per-instance and summary outputs.")
    parser.add_argument("--model", default="Qwen/Qwen3-VL-2B-Instruct")
    parser.add_argument("--trace-output-mode", default="answer", choices=("answer", "answer_and_evidence", "evidence"))
    parser.add_argument("--prompt-key", default="prompt_answer")
    parser.add_argument(
        "--system-prompt",
        default=str(RLVR_ROOT / "examples/prompts/trace_vero_json_system_prompt_answer.txt"),
        help="Path to the system prompt file, or 'none' to disable.",
    )
    parser.add_argument("--trace-reward-mode", default="answer", choices=("answer", "answer_and_evidence", "auto"))
    parser.add_argument("--trace-answer-scoring", default="legacy_strict", choices=("legacy_strict", "exact_json", "strict", "legacy", "exact"))
    parser.add_argument("--trace-format-weight", type=float, default=0.1)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--count", type=int, default=None, help="Number of prompts to probe. Default: all remaining rows.")
    parser.add_argument("--batch-size", type=int, default=1024, help="Global prompt batch size per wave of vLLM generate() calls.")
    parser.add_argument("--rollouts-per-prompt", type=int, default=32)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--tensor-parallel-size", type=int, default=1)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.9)
    parser.add_argument("--max-model-len", type=int, default=4096)
    parser.add_argument("--max-num-batched-tokens", type=int, default=16384)
    parser.add_argument("--max-num-seqs", type=int, default=1024)
    parser.add_argument("--max-prompt-length", type=int, default=1536)
    parser.add_argument("--max-pixels", type=int, default=4194304)
    parser.add_argument("--filter-overlong-prompts", action="store_true")
    parser.add_argument(
        "--prefetch-workers",
        type=int,
        default=1,
        help="CPU workers used to prebuild the next batch while vLLM generates the current batch. Set 0 to disable.",
    )
    parser.add_argument(
        "--replica-workers",
        type=int,
        default=0,
        help="Number of single-GPU probe workers when tensor_parallel_size=1. Default 0 means use all visible GPUs.",
    )
    parser.add_argument("--resume", action="store_true", help="Resume from existing worker shard outputs under output-dir.")
    parser.add_argument("--progress-file", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--append-output", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--seed", type=int, default=18)
    parser.add_argument("--enforce-eager", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    if int(args.tensor_parallel_size) == 1:
        visible_gpu_count = len(_detect_visible_gpu_ids())
        requested_workers = int(args.replica_workers) if int(args.replica_workers) > 0 else visible_gpu_count
        if min(requested_workers, visible_gpu_count) > 1:
            _run_sharded_probe(args)
            return
    _run_single_probe(args)


if __name__ == "__main__":
    main()
