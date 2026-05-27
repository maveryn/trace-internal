"""Helpers for exposing time-artifact query contracts as narrow task ids."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ..base import TaskOutput
from .fixed_query import rewrite_public_query_output


def force_time_artifact_query_params(
    params: Mapping[str, Any],
    *,
    query_variant: str,
    fixed_params: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return params that force one internal time-artifact query variant."""

    forced = dict(params)
    variant_text = str(query_variant)
    explicit_variant = forced.get("query_variant")
    if explicit_variant is not None and str(explicit_variant) not in {"default", variant_text}:
        raise ValueError(f"query_variant={explicit_variant!r} is not valid for this time-artifact task")
    forced["query_variant"] = variant_text

    for key, value in dict(fixed_params or {}).items():
        explicit_value = forced.get(str(key))
        if explicit_value is not None and str(explicit_value) != str(value):
            raise ValueError(f"{key}={explicit_value!r} is not valid for this time-artifact task")
        forced[str(key)] = value
    return forced


def rewrite_time_artifact_query_output(
    output: TaskOutput,
    *,
    query_id: str,
    scene_id: str,
    query_probabilities: Mapping[str, float] | None = None,
) -> TaskOutput:
    """Rewrite generated output so the public task has no semantic query variant."""

    query_id_text = str(query_id)
    scene_id_text = str(scene_id)
    query_probability_map = {
        str(key): float(value)
        for key, value in dict(query_probabilities or {query_id_text: 1.0}).items()
    }
    return rewrite_public_query_output(
        output,
        scene_id=scene_id_text,
        query_id=query_id_text,
        include_render_spec=True,
        query_variant_probabilities=dict(query_probability_map),
        variant_probabilities={"default": 1.0},
        preserve_internal_query_variant_as="source_query_variant",
    )


__all__ = [
    "force_time_artifact_query_params",
    "rewrite_time_artifact_query_output",
]
