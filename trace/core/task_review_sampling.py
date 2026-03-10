"""Shared sampling helpers for task review and distribution scripts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Any, Dict, List, Sequence

from .seed import hash64
from ..tasks import create_task


CollectorFn = Callable[[Any, int], Dict[str, Any]]
_THREAD_LOCAL = threading.local()


def _thread_local_task(task_id: str):
    """Return one thread-local task instance for repeated generate calls."""
    cache = getattr(_THREAD_LOCAL, "task_cache", None)
    if not isinstance(cache, dict):
        cache = {}
        _THREAD_LOCAL.task_cache = cache
    if str(task_id) not in cache:
        cache[str(task_id)] = create_task(str(task_id))
    return cache[str(task_id)]


def extract_variant_probability_keys(output: Any) -> List[str]:
    """Extract declared task-variant ids from one task output trace payload."""
    trace_payload = getattr(output, "trace_payload", {})
    if not isinstance(trace_payload, Mapping):
        return []
    exec_trace = trace_payload.get("execution_trace", {})
    if isinstance(exec_trace, Mapping):
        probabilities = exec_trace.get("task_variant_probabilities")
        if isinstance(probabilities, Mapping):
            return [str(key) for key, value in probabilities.items() if float(value) > 0.0]
    query_spec = trace_payload.get("query_spec", {})
    if isinstance(query_spec, Mapping):
        params = query_spec.get("params", {})
        if isinstance(params, Mapping):
            probabilities = params.get("variant_probabilities")
            if isinstance(probabilities, Mapping):
                return [str(key) for key, value in probabilities.items() if float(value) > 0.0]
    return []


def _generate_single_output(job: tuple[str, int, int]) -> Dict[str, Any]:
    """Generate one task sample for one deterministic seed job tuple."""
    task_id, instance_seed, max_attempts = job
    task = _thread_local_task(str(task_id))
    try:
        out = task.generate(int(instance_seed), params={}, max_attempts=int(max_attempts))
        return {
            "instance_seed": int(instance_seed),
            "output": out,
            "error_type": "",
        }
    except Exception as exc:
        return {
            "instance_seed": int(instance_seed),
            "output": None,
            "error_type": str(type(exc).__name__),
        }


def _generate_batch_outputs(
    *,
    task_id: str,
    start_index: int,
    batch_size: int,
    seed: int,
    max_attempts: int,
    executor: ThreadPoolExecutor | None,
) -> List[Dict[str, Any]]:
    """Generate one deterministic seed batch, optionally in parallel threads."""
    jobs = [
        (
            str(task_id),
            int(hash64(int(seed), str(task_id), int(index))),
            int(max_attempts),
        )
        for index in range(int(start_index), int(start_index) + int(batch_size))
    ]
    if executor is None:
        return [_generate_single_output(job) for job in jobs]
    return list(executor.map(_generate_single_output, jobs))


def collect_variant_samples(
    *,
    task_id: str,
    target_count_per_variant: int,
    seed: int,
    max_attempts_per_instance: int,
    max_total_samples_per_task: int,
    workers: int,
    collector: CollectorFn,
) -> Dict[str, Any]:
    """Collect sampled records until each discovered/declared variant reaches target count."""
    target_count = int(target_count_per_variant)
    if int(target_count) <= 0:
        raise ValueError("target_count_per_variant must be > 0")
    if int(max_total_samples_per_task) <= 0:
        raise ValueError("max_total_samples_per_task must be > 0")

    samples_by_variant: Dict[str, List[Dict[str, Any]]] = {}
    generated_variant_counts: Dict[str, int] = {}
    expected_variants: set[str] = set()
    known_from_probabilities = False
    no_new_variant_streak = 0
    total_generated = 0
    generation_error_counts: Dict[str, int] = {}

    max_workers = max(1, int(workers))
    executor = ThreadPoolExecutor(max_workers=max_workers) if int(max_workers) > 1 else None
    try:
        while int(total_generated) < int(max_total_samples_per_task):
            base_batch = max(16, int(max_workers * 8))
            remaining = int(max_total_samples_per_task) - int(total_generated)
            batch_size = max(1, min(int(base_batch), int(remaining)))
            rows = _generate_batch_outputs(
                task_id=str(task_id),
                start_index=int(total_generated),
                batch_size=int(batch_size),
                seed=int(seed),
                max_attempts=int(max_attempts_per_instance),
                executor=executor,
            )

            task_complete = False
            for row in rows:
                total_generated += 1
                output = row["output"]
                instance_seed = int(row["instance_seed"])
                if output is None:
                    error_type = str(row.get("error_type", "")).strip() or "GenerationError"
                    generation_error_counts[error_type] = int(generation_error_counts.get(error_type, 0) + 1)
                    continue
                task_variant = str(getattr(output, "task_variant", "") or "")
                generated_variant_counts[task_variant] = int(generated_variant_counts.get(task_variant, 0) + 1)
                variant_rows = samples_by_variant.setdefault(str(task_variant), [])
                if len(variant_rows) < int(target_count):
                    variant_rows.append(dict(collector(output, instance_seed)))

                expected_before = len(expected_variants)
                expected_variants.add(str(task_variant))
                probability_keys = extract_variant_probability_keys(output)
                if probability_keys:
                    known_from_probabilities = True
                    expected_variants.update(str(value) for value in probability_keys)
                if len(expected_variants) > int(expected_before):
                    no_new_variant_streak = 0
                else:
                    no_new_variant_streak += 1

                if expected_variants and all(
                    len(samples_by_variant.get(str(variant), [])) >= int(target_count)
                    for variant in expected_variants
                ):
                    if known_from_probabilities or int(no_new_variant_streak) >= int(target_count):
                        task_complete = True
                        break

            if task_complete:
                break
    finally:
        if executor is not None:
            executor.shutdown(wait=True)

    expected_variants_sorted = sorted(str(value) for value in expected_variants)
    collected_variant_counts = {
        str(variant): int(len(samples_by_variant.get(str(variant), [])))
        for variant in expected_variants_sorted
    }
    incomplete_variants = [
        str(variant)
        for variant in expected_variants_sorted
        if int(collected_variant_counts.get(str(variant), 0)) < int(target_count)
    ]

    return {
        "total_generated": int(total_generated),
        "target_count_per_variant": int(target_count),
        "expected_variants": list(expected_variants_sorted),
        "generated_variant_counts": {
            str(key): int(value) for key, value in sorted(generated_variant_counts.items(), key=lambda item: item[0])
        },
        "collected_variant_counts": dict(collected_variant_counts),
        "incomplete_variants": list(incomplete_variants),
        "generation_error_counts": {
            str(key): int(value) for key, value in sorted(generation_error_counts.items(), key=lambda item: item[0])
        },
        "samples_by_variant": {
            str(variant): list(samples_by_variant.get(str(variant), []))
            for variant in expected_variants_sorted
        },
    }


def generate_random_samples(
    *,
    task_id: str,
    count: int,
    seed: int,
    max_attempts_per_instance: int,
    workers: int,
    collector: CollectorFn,
) -> List[Dict[str, Any]]:
    """Generate one fixed-size random sample list using deterministic seeds."""
    target = int(count)
    if int(target) <= 0:
        raise ValueError("count must be > 0")

    accepted: List[Dict[str, Any]] = []
    total_generated = 0
    max_total_samples = max(int(target), int(target) * 20)

    max_workers = max(1, int(workers))
    executor = ThreadPoolExecutor(max_workers=max_workers) if int(max_workers) > 1 else None
    try:
        while int(len(accepted)) < int(target) and int(total_generated) < int(max_total_samples):
            remaining_needed = int(target) - int(len(accepted))
            remaining_budget = int(max_total_samples) - int(total_generated)
            batch_size = max(1, min(max(16, int(max_workers * 8), int(remaining_needed)), int(remaining_budget)))
            rows = _generate_batch_outputs(
                task_id=str(task_id),
                start_index=int(total_generated),
                batch_size=int(batch_size),
                seed=int(seed),
                max_attempts=int(max_attempts_per_instance),
                executor=executor,
            )
            for row in rows:
                total_generated += 1
                output = row.get("output")
                if output is None:
                    continue
                accepted.append(dict(collector(output, int(row["instance_seed"]))))
                if int(len(accepted)) >= int(target):
                    break
    finally:
        if executor is not None:
            executor.shutdown(wait=True)
    return list(accepted)
