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
    """Extract declared review-unit ids from one task output trace payload."""

    def _positive_keys(probabilities: Any) -> List[str]:
        if not isinstance(probabilities, Mapping):
            return []
        keys = [str(key) for key, value in probabilities.items() if float(value) > 0.0]
        review_key = resolve_review_variant_key(output)
        if str(review_key).strip() == "default":
            return [key for key in keys if str(key).strip() == "default"]
        non_default = [key for key in keys if str(key).strip() not in {"", "default"}]
        return non_default or keys

    trace_payload = getattr(output, "trace_payload", {})
    if not isinstance(trace_payload, Mapping):
        return []
    exec_trace = trace_payload.get("execution_trace", {})
    if isinstance(exec_trace, Mapping):
        probabilities = exec_trace.get("query_variant_probabilities")
        keys = _positive_keys(probabilities)
        if keys:
            return keys
    query_spec = trace_payload.get("query_spec", {})
    if isinstance(query_spec, Mapping):
        params = query_spec.get("params", {})
        if isinstance(params, Mapping):
            probabilities = params.get("query_variant_probabilities")
            keys = _positive_keys(probabilities)
            if keys:
                return keys
            probabilities = params.get("variant_probabilities")
            keys = _positive_keys(probabilities)
            if keys:
                return keys
    return []


def resolve_review_variant_key(output: Any) -> str:
    """Return the key used for review sheets and per-query sampling buckets."""

    query_variant = str(getattr(output, "query_variant", "") or "")
    query_id = str(getattr(output, "query_id", "") or "")
    if not query_id:
        trace_payload = getattr(output, "trace_payload", {})
        if isinstance(trace_payload, Mapping):
            query_spec = trace_payload.get("query_spec", {})
            execution_trace = trace_payload.get("execution_trace", {})
            if isinstance(query_spec, Mapping):
                query_id = str(query_spec.get("query_id", "") or "")
            if not query_id and isinstance(execution_trace, Mapping):
                query_id = str(execution_trace.get("query_id", "") or "")
    if query_variant.strip() in {"", "default"} and query_id.strip():
        return str(query_id)
    return str(query_variant)


def _generate_single_output(job: tuple[str, int, int, Mapping[str, Any] | None]) -> Dict[str, Any]:
    """Generate one task sample for one deterministic seed job tuple."""
    task_id, instance_seed, max_attempts, params = job
    task = _thread_local_task(str(task_id))
    try:
        task_params = dict(params) if isinstance(params, Mapping) else {}
        forbidden = [
            key
            for key in task_params
            if str(key).endswith("sampling_index") or str(key).endswith("sample_cursor")
        ]
        if forbidden:
            raise ValueError(f"manual sampler controls are not allowed in task-review params: {forbidden}")
        out = task.generate(
            int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
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
    params: Mapping[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Generate one deterministic seed batch, optionally in parallel threads."""
    jobs = [
        (
            str(task_id),
            int(hash64(int(seed), str(task_id), int(index))),
            int(max_attempts),
            dict(params) if isinstance(params, Mapping) else None,
        )
        for index in range(int(start_index), int(start_index) + int(batch_size))
    ]
    if executor is None:
        return [_generate_single_output(job) for job in jobs]
    return list(executor.map(_generate_single_output, jobs))


def _generate_explicit_variant_batch(
    *,
    task_id: str,
    expected_variants: Sequence[str],
    samples_by_variant: Mapping[str, Sequence[Dict[str, Any]]],
    target_count: int,
    seed: int,
    max_attempts: int,
    executor: ThreadPoolExecutor | None,
    request_counts_by_variant: Dict[str, int],
    batch_size: int,
) -> List[Dict[str, Any]]:
    """Generate one round-robin batch that explicitly targets missing query variants."""

    pending_variants = [
        str(variant)
        for variant in expected_variants
        if len(samples_by_variant.get(str(variant), [])) < int(target_count)
    ]
    if not pending_variants or int(batch_size) <= 0:
        return []

    jobs: List[tuple[str, int, int, Mapping[str, Any] | None]] = []
    variant_index = 0
    while len(jobs) < int(batch_size):
        pending_variants = [
            str(variant)
            for variant in expected_variants
            if len(samples_by_variant.get(str(variant), [])) < int(target_count)
        ]
        if not pending_variants:
            break
        variant = str(pending_variants[int(variant_index) % len(pending_variants)])
        request_index = int(request_counts_by_variant.get(str(variant), 0))
        request_counts_by_variant[str(variant)] = int(request_index + 1)
        jobs.append(
            (
                str(task_id),
                int(hash64(int(seed), f"{str(task_id)}|query_variant:{variant}", int(request_index))),
                int(max_attempts),
                {
                    "query_variant": str(variant),
                    "query_id": str(variant),
                },
            )
        )
        variant_index += 1

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
    request_counts_by_variant: Dict[str, int] = {}
    known_from_probabilities = False
    no_new_variant_streak = 0
    total_generated = 0
    generation_error_counts: Dict[str, int] = {}

    max_workers = max(1, int(workers))
    executor = ThreadPoolExecutor(max_workers=max_workers) if int(max_workers) > 1 else None
    try:
        while int(total_generated) < int(max_total_samples_per_task):
            if expected_variants and all(
                len(samples_by_variant.get(str(variant), [])) >= int(target_count)
                for variant in expected_variants
            ):
                if known_from_probabilities or int(no_new_variant_streak) >= int(target_count):
                    break

            base_batch = max(16, int(max_workers * 8))
            remaining = int(max_total_samples_per_task) - int(total_generated)
            batch_size = max(1, min(int(base_batch), int(remaining)))
            if expected_variants and bool(known_from_probabilities):
                rows = _generate_explicit_variant_batch(
                    task_id=str(task_id),
                    expected_variants=sorted(expected_variants),
                    samples_by_variant=samples_by_variant,
                    target_count=int(target_count),
                    seed=int(seed),
                    max_attempts=int(max_attempts_per_instance),
                    executor=executor,
                    request_counts_by_variant=request_counts_by_variant,
                    batch_size=int(batch_size),
                )
            else:
                rows = _generate_batch_outputs(
                    task_id=str(task_id),
                    start_index=int(total_generated),
                    batch_size=int(batch_size),
                    seed=int(seed),
                    max_attempts=int(max_attempts_per_instance),
                    executor=executor,
                )
            if not rows:
                break

            task_complete = False
            restart_with_explicit = False
            for row in rows:
                total_generated += 1
                output = row["output"]
                instance_seed = int(row["instance_seed"])
                if output is None:
                    error_type = str(row.get("error_type", "")).strip() or "GenerationError"
                    generation_error_counts[error_type] = int(generation_error_counts.get(error_type, 0) + 1)
                    continue
                query_variant = resolve_review_variant_key(output)
                probability_keys = extract_variant_probability_keys(output)
                non_default_probability_keys = [
                    str(value) for value in probability_keys if str(value).strip() not in {"", "default"}
                ]
                effective_probability_keys = non_default_probability_keys or [str(value) for value in probability_keys]
                if str(query_variant).strip() == "default" and len(effective_probability_keys) == 1:
                    query_variant = str(effective_probability_keys[0])
                generated_variant_counts[query_variant] = int(generated_variant_counts.get(query_variant, 0) + 1)

                expected_before = len(expected_variants)
                expected_variants.add(str(query_variant))
                transitioned_to_explicit = False
                if effective_probability_keys:
                    if len(effective_probability_keys) > 1 and not known_from_probabilities:
                        transitioned_to_explicit = True
                    if len(effective_probability_keys) > 1:
                        known_from_probabilities = True
                    expected_variants.update(str(value) for value in effective_probability_keys)
                    if any(str(value).strip() not in {"", "default"} for value in expected_variants):
                        expected_variants.discard("default")
                        samples_by_variant.pop("default", None)
                if len(expected_variants) > int(expected_before):
                    no_new_variant_streak = 0
                else:
                    no_new_variant_streak += 1

                if transitioned_to_explicit:
                    samples_by_variant = {}
                    restart_with_explicit = True
                    break

                if not transitioned_to_explicit:
                    variant_rows = samples_by_variant.setdefault(str(query_variant), [])
                    if len(variant_rows) < int(target_count):
                        variant_rows.append(dict(collector(output, instance_seed)))

                if expected_variants and all(
                    len(samples_by_variant.get(str(variant), [])) >= int(target_count)
                    for variant in expected_variants
                ):
                    if known_from_probabilities or int(no_new_variant_streak) >= int(target_count):
                        task_complete = True
                        break

            if restart_with_explicit:
                continue
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
