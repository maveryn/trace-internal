"""Neutral deterministic sampling helpers for solid-formula tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence, TypeVar

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

T = TypeVar("T")


def select_support_value(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    support: Sequence[T],
) -> T:
    """Select one value from a public task's answer support."""

    values = tuple(support)
    if not values:
        raise ValueError("answer support must be non-empty")
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    return values[int(index) % len(values)]


def select_case_option(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    options: Sequence[T],
) -> tuple[T, int]:
    """Select one construction option for an already selected answer."""

    values = tuple(options)
    if not values:
        raise ValueError("construction option support must be non-empty")
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )
    return values[int(index) % len(values)], len(values)


__all__ = ["select_case_option", "select_support_value"]
