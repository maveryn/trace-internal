"""Identity-free sampling helpers for composite-shape cases."""

from __future__ import annotations

from typing import Any, Mapping, Sequence, TypeVar

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

T = TypeVar("T")


def select_case_value(
    values: Sequence[T],
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> T:
    """Select one case value, honoring explicit review case indices."""

    if not values:
        raise ValueError("case values must be non-empty")
    explicit_case = params.get("case_index")
    if explicit_case is not None:
        index = int(explicit_case) % len(values)
    else:
        raw_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
        index = int(raw_index) % len(values)
    return values[index]
