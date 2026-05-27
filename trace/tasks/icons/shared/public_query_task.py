"""Helpers for exposing icon query branches as one public task unit."""

from __future__ import annotations

from typing import Mapping

from ...base import TaskOutput
from ...shared.fixed_query import rewrite_public_query_output


def rewrite_icons_query_output(
    output: TaskOutput,
    *,
    query_id: str,
    scene_id: str,
    task_id: str | None = None,
    query_probabilities: Mapping[str, float] | None = None,
) -> TaskOutput:
    """Rewrite generated output so public icon tasks do not expose semantic variants."""

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
        task_id=None if task_id is None else str(task_id),
        include_render_spec=True,
        include_scene_ir_root=True,
        query_variant_probabilities=dict(query_probability_map),
        variant_probabilities={"default": 1.0},
        preserve_internal_query_variant_as=("source_query_variant", "internal_query_variant"),
        preserve_prior_task_id_as="source_task_id",
        update_existing_taxonomy=True,
    )


__all__ = ["rewrite_icons_query_output"]
