"""Trace assembly helpers for parallel-coordinates chart tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec

from .profile_common import SCENE_ID, _Dataset
from .runtime import ParallelCoordsRenderResult, profile_rows, render_map_payload, render_spec_payload


def build_trace_payload(
    *,
    dataset: _Dataset,
    rendered: ParallelCoordsRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    annotation_type: str,
    projected_annotation: Mapping[str, Any],
) -> dict[str, Any]:
    answer_value: int | str = (
        int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
    )
    axis_pair = [int(dataset.query.axis_i), int(dataset.query.axis_j)]
    rows = profile_rows(dataset)
    return {
        "scene_ir": {
            "scene_kind": "chart_parallel_coords",
            "entities": [dict(entity) for entity in rendered.rendered_scene.entities],
            "relations": {
                "query_id": str(dataset.query.query_id),
                "scene_variant": str(dataset.scene_variant),
                "answer": answer_value,
                "axis_pair": list(axis_pair),
                "annotation_profile_ids": [str(value) for value in dataset.query.annotation_profile_ids],
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(dataset.query.query_id),
            params=dict(dataset.query.params),
        ),
        "render_spec": render_spec_payload(rendered, dataset),
        "render_map": render_map_payload(rendered),
        "execution_trace": {
            "query_id": str(dataset.query.query_id),
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            "question_format": "parallel_coords_query",
            "answer": answer_value,
            "answer_type": str(dataset.query.answer_type),
            "annotation_type": str(annotation_type),
            "axis_i": int(dataset.query.axis_i),
            "axis_j": int(dataset.query.axis_j),
            "axis_i_label": str(dataset.metrics[int(dataset.query.axis_i)]),
            "axis_j_label": str(dataset.metrics[int(dataset.query.axis_j)]),
            "metrics": [str(value) for value in dataset.metrics],
            "profiles": list(rows),
            "threshold": dataset.query.threshold,
            "reference_profile_id": dataset.query.reference_profile_id,
            "annotation_profile_ids": [str(value) for value in dataset.query.annotation_profile_ids],
            "crossing_pairs": [list(pair) for pair in dataset.query.crossing_pairs],
            **dict(dataset.query.params),
        },
        "witness_symbolic": {
            "type": "parallel_coordinates_witness",
            "answer": answer_value,
            "axis_pair": list(axis_pair),
            "profile_ids": [str(value) for value in dataset.query.annotation_profile_ids],
        },
        "projected_annotation": dict(projected_annotation),
    }


__all__ = ["build_trace_payload"]
