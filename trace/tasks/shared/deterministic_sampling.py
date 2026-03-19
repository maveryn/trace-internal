"""Shared deterministic sampling helpers for task-local support selection."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...core.seed import hash64


def resolve_selection_index(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> int:
    """Return a deterministic selection index.

    Tasks use `_sampling_index` when a caller explicitly wants balanced cycling
    over feasible support. Otherwise a namespaced hash keeps target-answer
    sampling deterministic while avoiding accidental coupling with unrelated
    decisions that also depend on `instance_seed`.
    """

    explicit_index = params.get("_sampling_index")
    if explicit_index is not None:
        return abs(int(explicit_index))
    return abs(int(hash64(int(instance_seed), str(namespace), 0)))
