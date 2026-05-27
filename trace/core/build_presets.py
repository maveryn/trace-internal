"""Reusable build-config presets for common TRACE dataset recipes."""

from __future__ import annotations

from typing import Any, Dict, Mapping

import trace.tasks  # noqa: F401  # Ensure task registration side effects run.

from ..tasks import create_task
from ..tasks.base import TaskOutput
from ..tasks.registry import list_default_task_ids
from .config import BuildConfig, BuildTaskConfig
from .seed import hash64


_QUERY_ID_PROBABILITY_KEYS = (
    "query_id_probabilities",
)


def resolve_equal_split_task_count(*, num_instances: int, task_count: int) -> int:
    """Resolve one exact per-task count for an equal-split build."""

    if int(num_instances) <= 0:
        raise ValueError("num_instances must be positive")
    if int(task_count) <= 0:
        raise ValueError("task_count must be positive")
    if int(num_instances) % int(task_count) != 0:
        raise ValueError(
            "num_instances must be divisible by task_count for an equal-split build "
            f"(got num_instances={num_instances}, task_count={task_count})"
        )
    return int(num_instances) // int(task_count)


def resolve_weighted_task_counts(*, num_instances: int, task_weights: Mapping[str, float]) -> Dict[str, int]:
    """Resolve exact integer task counts from positive task weights.

    Counts are assigned by largest remainder after flooring the ideal fractional counts.
    Ties are broken by task id for deterministic builds.
    """

    total = int(num_instances)
    if total <= 0:
        raise ValueError("num_instances must be positive")
    weights: Dict[str, float] = {}
    for task_id, raw_weight in task_weights.items():
        weight = float(raw_weight)
        if weight < 0.0:
            raise ValueError(f"task weight must be non-negative for {task_id}")
        weights[str(task_id)] = weight
    if not weights:
        raise ValueError("at least one task weight is required")
    weight_sum = sum(weights.values())
    if weight_sum <= 0.0:
        raise ValueError("at least one task weight must be positive")

    fractional = {
        task_id: (float(total) * weight / weight_sum)
        for task_id, weight in weights.items()
    }
    counts = {task_id: int(value) for task_id, value in fractional.items()}
    remainder = total - sum(counts.values())
    if remainder > 0:
        ranked = sorted(
            fractional,
            key=lambda task_id: (-(fractional[task_id] - counts[task_id]), str(task_id)),
        )
        for task_id in ranked[:remainder]:
            counts[task_id] += 1
    return dict(sorted(counts.items()))


def _positive_probability_count(value: Any) -> int | None:
    """Return positive-key count for a probability mapping, if present."""

    if not isinstance(value, Mapping):
        return None
    count = 0
    for key, raw_weight in value.items():
        key_text = str(key).strip()
        if not key_text:
            continue
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            continue
        if weight > 0.0:
            count += 1
    return count if count > 0 else None


def _variant_probability_count_from_output(output: TaskOutput) -> int | None:
    """Extract the active query branch support size from one output."""

    payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
    execution_trace = payload.get("execution_trace", {})
    query_spec = payload.get("query_spec", {})
    query_params = query_spec.get("params", {}) if isinstance(query_spec, Mapping) else {}

    for source in (execution_trace, query_params):
        if not isinstance(source, Mapping):
            continue
        for key in _QUERY_ID_PROBABILITY_KEYS:
            count = _positive_probability_count(source.get(key))
            if count is not None:
                return int(count)
    return None


def resolve_task_active_variant_count(
    task_id: str,
    *,
    probe_samples: int = 8,
    max_attempts_per_instance: int = 100,
) -> int:
    """Resolve one task's active query branch count.

    Most tasks report `query_id_probabilities` in the generated trace,
    which gives the full active support from a single probe. Tasks without such
    a map fall back to observed non-default `query_id` labels over a small,
    deterministic probe prefix.
    """

    task = create_task(str(task_id))
    observed_variants: set[str] = set()
    probe_total = max(1, int(probe_samples))
    last_error: Exception | None = None
    for probe_index in range(probe_total):
        instance_seed = hash64(0, f"{task_id}:variant_count_probe", probe_index)
        try:
            output = task.generate(
                int(instance_seed),
                params={},
                max_attempts=int(max_attempts_per_instance),
            )
        except Exception as exc:  # pragma: no cover - exercised only for unlucky probes.
            last_error = exc
            continue

        probability_count = _variant_probability_count_from_output(output)
        if probability_count is not None:
            return max(1, int(probability_count))

        variant_label = str(getattr(output, "query_id", "") or "").strip()
        if variant_label and variant_label != "default":
            observed_variants.add(variant_label)

    if observed_variants:
        return len(observed_variants)
    if last_error is not None:
        raise ValueError(f"failed to probe query ids for {task_id}: {last_error}") from last_error
    return 1


def resolve_variant_aware_task_weights(
    *,
    task_ids: list[str],
    alpha: float,
    probe_samples: int = 8,
    max_attempts_per_instance: int = 100,
) -> tuple[Dict[str, float], Dict[str, int]]:
    """Resolve task weights from active query branch counts."""

    alpha_value = float(alpha)
    if alpha_value < 0.0:
        raise ValueError("alpha must be non-negative")
    variant_counts: Dict[str, int] = {}
    weights: Dict[str, float] = {}
    for task_id in task_ids:
        count = resolve_task_active_variant_count(
            str(task_id),
            probe_samples=int(probe_samples),
            max_attempts_per_instance=int(max_attempts_per_instance),
        )
        variant_counts[str(task_id)] = int(count)
        weights[str(task_id)] = 1.0 + alpha_value * max(0, int(count) - 1)
    return dict(sorted(weights.items())), dict(sorted(variant_counts.items()))


def build_equal_split_all_tasks_config(
    *,
    output_root: str,
    dataset_name: str,
    num_instances: int,
    instance_version: str = "v0",
    image_format: str = "png",
    strict_repro: bool = False,
    max_attempts_per_instance: int = 100,
    sampling_seed: int = 0,
    workers: int = 0,
    max_in_flight: int = 0,
    task_params_by_id: Mapping[str, Mapping[str, Any]] | None = None,
) -> BuildConfig:
    """Build a config that splits instances evenly across default-selected tasks."""

    task_ids = list_default_task_ids()
    per_task_count = resolve_equal_split_task_count(
        num_instances=int(num_instances),
        task_count=len(task_ids),
    )
    params_by_id = task_params_by_id or {}
    return BuildConfig(
        output_root=str(output_root),
        dataset_name=str(dataset_name),
        instance_version=str(instance_version),
        image_format=str(image_format).lower(),
        tasks=[
            BuildTaskConfig(
                task_id=str(task_id),
                count=per_task_count,
                params=dict(params_by_id.get(task_id, {})),
            )
            for task_id in task_ids
        ],
        num_instances=None,
        strict_repro=bool(strict_repro),
        max_attempts_per_instance=int(max_attempts_per_instance),
        sampling_seed=int(sampling_seed),
        workers=int(workers),
        max_in_flight=int(max_in_flight),
    )


def build_variant_weighted_all_tasks_config(
    *,
    output_root: str,
    dataset_name: str,
    num_instances: int,
    variant_weight_alpha: float,
    instance_version: str = "v0",
    image_format: str = "png",
    strict_repro: bool = False,
    max_attempts_per_instance: int = 100,
    sampling_seed: int = 0,
    workers: int = 0,
    max_in_flight: int = 0,
    task_params_by_id: Mapping[str, Mapping[str, Any]] | None = None,
    variant_count_probe_samples: int = 8,
) -> BuildConfig:
    """Build a config with exact task counts scaled by active variant count.

    The task weight formula is:

    `1 + variant_weight_alpha * (active_query_branch_count - 1)`.
    """

    task_ids = list_default_task_ids()
    weights, _variant_counts = resolve_variant_aware_task_weights(
        task_ids=[str(task_id) for task_id in task_ids],
        alpha=float(variant_weight_alpha),
        probe_samples=int(variant_count_probe_samples),
        max_attempts_per_instance=int(max_attempts_per_instance),
    )
    target_counts = resolve_weighted_task_counts(
        num_instances=int(num_instances),
        task_weights=weights,
    )
    params_by_id = task_params_by_id or {}
    return BuildConfig(
        output_root=str(output_root),
        dataset_name=str(dataset_name),
        instance_version=str(instance_version),
        image_format=str(image_format).lower(),
        tasks=[
            BuildTaskConfig(
                task_id=str(task_id),
                count=int(target_counts[str(task_id)]),
                weight=float(weights[str(task_id)]),
                params=dict(params_by_id.get(task_id, {})),
            )
            for task_id in task_ids
        ],
        num_instances=None,
        strict_repro=bool(strict_repro),
        max_attempts_per_instance=int(max_attempts_per_instance),
        sampling_seed=int(sampling_seed),
        workers=int(workers),
        max_in_flight=int(max_in_flight),
    )
