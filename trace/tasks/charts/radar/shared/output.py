
from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.tasks.charts.radar.shared.profile_common import (
    _Dataset,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    _resolve_gen_int,
    _resolve_int,
)
from trace.tasks.charts.radar.shared.runtime import RadarRenderResult, font_assets_payload
from trace.tasks.shared.prompt_variants import PromptTraceArtifacts, build_prompt_query_spec




def _values_by_panel_profile(dataset: _Dataset) -> dict[str, dict[str, dict[str, int]]]:
    return {
        str(panel.panel_label): {
            str(profile.profile_label): dict(profile.values)
            for profile in panel.profiles
        }
        for panel in dataset.panels
    }


def build_trace_payload(
    *,
    dataset: _Dataset,
    rendered: RadarRenderResult,
    prompt_artifacts: PromptTraceArtifacts,
    query_id_probabilities: Mapping[str, float],
    annotation_type: str,
    annotation_value: Sequence[Any],
    projected_annotation: Mapping[str, Any],
    params: Mapping[str, Any],
) -> dict[str, Any]:
    rendered_scene = rendered.rendered_scene
    query_id = str(dataset.query.query_id)
    return {
        "scene_ir": {
            "scene_kind": f"chart_radar_{str(dataset.query.scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "scene_variant": str(dataset.query.scene_variant),
                "answer": dataset.query.answer,
                "annotation_point_ids": list(dataset.query.annotation_point_ids),
                "annotation_type": str(annotation_type),
                "annotation_count": len(annotation_value),
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(query_id),
            params={
                "query_id": str(query_id),
                "scene_variant": str(dataset.query.scene_variant),
                "query_id_probabilities": dict(query_id_probabilities),
                "metric_count": int(len(dataset.metrics)),
                "panel_count": int(len(dataset.panels)),
                "question_format": "radar_profile_query",
            },
        ),
        "render_spec": {
            "canvas_width": _resolve_int(params, "canvas_width", 1600),
            "canvas_height": _resolve_int(params, "canvas_height", 1000),
            "coord_space": "pixel",
            "scene_variant": str(dataset.query.scene_variant),
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "font_assets": font_assets_payload(chart_font_family=rendered.chart_font_family),
            **dict(rendered_scene.render_meta),
        },
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "point_bboxes_px": dict(rendered_scene.point_bboxes),
            "panel_bboxes_px": dict(rendered_scene.panel_bboxes),
            "panel_title_bboxes_px": dict(rendered_scene.panel_title_bboxes),
            "legend_bboxes_px": dict(rendered_scene.legend_bboxes),
        },
        "execution_trace": {
            "query_id": str(query_id),
            "scene_variant": str(dataset.query.scene_variant),
            "answer": dataset.query.answer,
            "answer_type": str(dataset.query.answer_type),
            "metrics": list(dataset.metrics),
            "metric_count": int(len(dataset.metrics)),
            "panel_labels": [str(panel.panel_label) for panel in dataset.panels if str(panel.panel_label)],
            "panel_count": int(len(dataset.panels)),
            "values_by_panel_profile": _values_by_panel_profile(dataset),
            "annotation_point_ids": list(dataset.query.annotation_point_ids),
            "query_id_probabilities": dict(query_id_probabilities),
            "question_format": "radar_profile_query",
            **dict(dataset.query.trace),
        },
        "witness_symbolic": {
            "type": "radar_vertices",
            "point_ids": list(dataset.query.annotation_point_ids),
            "answer": dataset.query.answer,
        },
        "projected_annotation": dict(projected_annotation),
    }


