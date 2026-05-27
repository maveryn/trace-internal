"""Helpers for exposing page query branches as one public task unit."""

from __future__ import annotations

from typing import Mapping

from ...base import TaskOutput
from ...shared.fixed_query import rewrite_public_query_output


def rewrite_pages_query_output(
    output: TaskOutput,
    *,
    query_id: str,
    scene_id: str,
    query_probabilities: Mapping[str, float] | None = None,
) -> TaskOutput:
    """Rewrite generated output so public page tasks do not expose semantic variants."""

    query_id_text = str(query_id)
    scene_id_text = str(scene_id)
    query_probability_map = {
        str(key): float(value)
        for key, value in dict(query_probabilities or {query_id_text: 1.0}).items()
    }
    return rewrite_public_query_output(
        output,
        query_id=query_id_text,
        scene_id=scene_id_text,
        include_render_spec=True,
        include_scene_ir_root=True,
        query_variant_probabilities=dict(query_probability_map),
        variant_probabilities={"default": 1.0},
        preserve_internal_query_variant_as=("source_query_variant", "internal_query_variant"),
    )


__all__ = ["rewrite_pages_query_output"]
