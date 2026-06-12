"""Semantic branch sampling helpers for boxplot tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.seed import spawn_rng


def _probabilities(values: Sequence[str], selected: str | None = None) -> dict[str, float]:
    labels = tuple(str(value) for value in values)
    if selected is not None:
        return {label: (1.0 if label == str(selected) else 0.0) for label in labels}
    if not labels:
        return {}
    weight = 1.0 / float(len(labels))
    return {label: float(weight) for label in labels}


def choose_branch(
    *,
    params: Mapping[str, Any],
    branch_key: str,
    support: Sequence[str],
    instance_seed: int,
    namespace: str,
) -> tuple[str, dict[str, float], dict[str, Any]]:
    """Select a semantic branch while cycling review cursors when present."""

    values = tuple(str(value) for value in support if str(value))
    if not values:
        raise ValueError("branch support must be non-empty")
    requested = params.get(str(branch_key))
    if requested is not None:
        selected = str(requested)
        if selected not in values:
            raise ValueError(f"unsupported {branch_key}: {selected}; supported: {values}")
        stripped = dict(params)
        stripped.pop(str(branch_key), None)
        return selected, _probabilities(values, selected), stripped

    sample_cursor = params.get("_sample_cursor")
    if sample_cursor is not None:
        cursor = abs(int(sample_cursor))
        selected = values[cursor % len(values)]
        branch_params = dict(params)
        branch_params["_sample_cursor"] = cursor // len(values)
        return str(selected), _probabilities(values), branch_params

    rng = spawn_rng(int(instance_seed), str(namespace))
    return str(rng.choice(values)), _probabilities(values), dict(params)


__all__ = ["choose_branch"]
