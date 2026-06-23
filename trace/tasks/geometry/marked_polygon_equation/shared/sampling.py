"""Sampling primitives for marked polygon equation constructions."""

from __future__ import annotations

from typing import Callable, Mapping, Sequence, Tuple, TypeVar

from trace.core.seed import spawn_rng

T = TypeVar("T")


def _uniform_probability_map(values: Sequence[str], selected: str | None = None) -> dict[str, float]:
    entries = tuple(str(value) for value in values)
    if not entries:
        return {}
    if selected is not None:
        return {entry: (1.0 if entry == str(selected) else 0.0) for entry in entries}
    weight = 1.0 / float(len(entries))
    return {entry: float(weight) for entry in entries}


def select_construction_family(
    *,
    options: Sequence[tuple[str, T]],
    params: Mapping[str, object],
    instance_seed: int,
    namespace: str,
) -> tuple[str, T, dict[str, float], Mapping[str, object]]:
    """Select one non-public construction family from task-owned options."""

    families = tuple((str(name), builder) for name, builder in options)
    if not families:
        raise ValueError("construction family options must be non-empty")
    names = tuple(name for name, _builder in families)
    task_params = dict(params)
    forced = task_params.pop("construction_family", None)
    if forced is not None:
        forced_name = str(forced)
        for name, builder in families:
            if name == forced_name:
                return name, builder, _uniform_probability_map(names, forced_name), task_params
        raise ValueError(f"unsupported construction_family: {forced_name}; supported: {names}")

    rng = spawn_rng(int(instance_seed), str(namespace))
    selected_name, selected_builder = families[int(rng.randrange(len(families)))]
    return selected_name, selected_builder, _uniform_probability_map(names), task_params


def select_case_variant(*, instance_seed: int, namespace: str, support_size: int = 503) -> int:
    """Return a deterministic construction-variant index from a large support."""

    rng = spawn_rng(int(instance_seed), str(namespace))
    return int(rng.randrange(max(1, int(support_size))))


__all__ = ["select_case_variant", "select_construction_family"]
