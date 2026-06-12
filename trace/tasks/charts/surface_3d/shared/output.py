"""Output component assembly for synthetic 3D chart panel tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from .....core.visual.background import make_background_canvas
from .....core.visual.noise import apply_post_image_noise
from ....shared.config_defaults import required_group_defaults
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ....shared.text_rendering import temporary_default_font_family
from ...shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from .panel_common import (
    BBox,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    _Dataset,
    _Rendered,
)
from .panel_rendering import _render_dataset, _resolve_render_params
from .panel_sampling import _build_dataset


@dataclass(frozen=True)
class Surface3DTaskComponents:
    prompt: str
    prompt_variants: Dict[str, str]
    answer_type: str
    answer_value: Any
    annotation_type: str
    annotation_value: List[List[float]]
    image: Any
    query_id: str
    trace_payload: Dict[str, Any]


def _projected_annotation(dataset: _Dataset, rendered: _Rendered) -> Dict[str, Any]:
    boxes: List[BBox] = []
    for point_id in dataset.query.annotation_point_ids:
        if str(point_id) in rendered.point_bboxes_px:
            boxes.append(list(rendered.point_bboxes_px[str(point_id)]))
    for cell_id in dataset.query.annotation_cell_ids:
        if str(cell_id) in rendered.surface_cell_bboxes_px:
            boxes.append(list(rendered.surface_cell_bboxes_px[str(cell_id)]))
    for panel_label in dataset.query.annotation_panel_labels:
        if str(panel_label) in rendered.panel_bboxes_px:
            boxes.append(list(rendered.panel_bboxes_px[str(panel_label)]))
    return {
        "type": "bbox_set",
        "bbox_set": list(boxes),
        "point_ids": [str(value) for value in dataset.query.annotation_point_ids],
        "surface_cell_ids": [str(value) for value in dataset.query.annotation_cell_ids],
        "panel_labels": [str(value) for value in dataset.query.annotation_panel_labels],
    }


def _prompt_slots(dataset: _Dataset, prompt_defaults: Mapping[str, Any]) -> Dict[str, str]:
    query = dataset.query
    trace = dict(query.trace or {})
    answer_hint = str(prompt_defaults["answer_hint_count"] if query.answer_type == "integer" else prompt_defaults["answer_hint_label"])
    return {
        "object_description": str(prompt_defaults["object_description"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": answer_hint,
        "annotation_hint": str(prompt_defaults["annotation_hint"]),
        "json_example": str(prompt_defaults["json_example_count"] if query.answer_type == "integer" else prompt_defaults["json_example_label"]),
        "json_example_answer_only": str(prompt_defaults["json_example_answer_only_count"] if query.answer_type == "integer" else prompt_defaults["json_example_answer_only_label"]),
        "target_axis_label": str(trace.get("target_axis_label", "Distance")),
        "target_axis_value": str(trace.get("target_axis_value", "")),
        "target_y_category": str(trace.get("target_y_category", "")),
        "extremum_phrase": str(trace.get("extremum_direction", "highest")),
        "trend_direction_phrase": "increase" if str(trace.get("trend_direction", "increase")) == "increase" else "decrease",
        "panel_variation_phrase": "largest vertical range",
    }


def build_surface_3d_task_components(
    *,
    task_id: str,
    selected_query_id: str,
    query_id_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
) -> Surface3DTaskComponents:
    """Build output components for one synthetic 3D chart panel task."""

    params = dict(params)
    dataset = _build_dataset(str(selected_query_id), params, instance_seed=int(instance_seed))
    render_params = _resolve_render_params(params)
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.chart_font",
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered = _render_dataset(background, dataset=dataset, params=render_params)
    image, post_noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_label",
            "answer_hint_count",
            "annotation_hint",
            "json_example_label",
            "json_example_count",
            "json_example_answer_only_label",
            "json_example_answer_only_count",
            "object_description",
        ),
        context=f"prompt defaults for {task_id}",
    )
    prompt_selection = render_scene_prompt_variants(
        domain="charts",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(dataset.query.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots=_prompt_slots(dataset, prompt_defaults),
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    projected = _projected_annotation(dataset, rendered)
    trace_params = dict(dataset.query.trace or {})
    trace_params.update(
        {
            "query_id": str(dataset.query.query_id),
            "scene_variant": str(dataset.scene_variant),
            "query_id_probabilities": dict(query_id_probabilities),
            "answer": dataset.query.answer,
            "answer_type": str(dataset.query.answer_type),
            "x_axis_label": str(dataset.x_axis_label),
            "y_axis_label": str(dataset.y_axis_label),
            "z_axis_label": str(dataset.z_axis_label),
            "x_range": [float(value) for value in dataset.x_range],
            "y_range": [float(value) for value in dataset.y_range],
            "z_range": [float(value) for value in dataset.z_range],
            "point_count": len(dataset.points),
            "surface_cell_count": len(dataset.surface_cells),
            "panel_count": len(dataset.panels),
        }
    )
    trace_payload = {
        "scene_ir": {
            "scene_kind": "chart_three_d_panel",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "query_id": str(dataset.query.query_id),
                "scene_variant": str(dataset.scene_variant),
                "answer": dataset.query.answer,
                "annotation_point_ids": [str(value) for value in dataset.query.annotation_point_ids],
                "annotation_cell_ids": [str(value) for value in dataset.query.annotation_cell_ids],
                "annotation_panel_labels": [str(value) for value in dataset.query.annotation_panel_labels],
            },
        },
        "query_spec": {
            "query_id": str(dataset.query.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(trace_params),
        },
        "render_spec": {
            "canvas_width": int(render_params.canvas_width),
            "canvas_height": int(render_params.canvas_height),
            "coord_space": "pixel",
            "scene_variant": str(dataset.scene_variant),
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "font_assets": chart_font_asset_metadata(str(chart_font_family)),
            "layout_jitter": dict(render_params.layout_jitter_meta),
            "plot_bbox_px": list(rendered.plot_bbox_px),
            "axis_labels": {
                "x": str(dataset.x_axis_label),
                "y": str(dataset.y_axis_label),
                "z": str(dataset.z_axis_label),
            },
        },
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered.plot_bbox_px),
            "point_bboxes_px": dict(rendered.point_bboxes_px),
            "surface_cell_bboxes_px": dict(rendered.surface_cell_bboxes_px),
            "panel_bboxes_px": dict(rendered.panel_bboxes_px),
        },
        "execution_trace": {
            "question_format": "surface_3d_query",
            **dict(trace_params),
            "points": [
                {
                    "point_id": str(point.point_id),
                    "label": str(point.label),
                    "x_value": round(float(point.x_value), 3),
                    "y_value": round(float(point.y_value), 3),
                    "z_value": round(float(point.z_value), 3),
                }
                for point in dataset.points
            ],
            "surface_cells": [
                {
                    "cell_id": str(cell.cell_id),
                    "x_label": str(cell.x_label),
                    "y_label": str(cell.y_label),
                    "value": int(cell.value),
                }
                for cell in dataset.surface_cells
            ],
            "panels": [
                {
                    "panel_label": str(panel.panel_label),
                    "values": [int(value) for value in panel.values],
                    "value_range": int(max(panel.values) - min(panel.values)),
                }
                for panel in dataset.panels
            ],
        },
        "witness_symbolic": {
            "type": "integer" if dataset.query.answer_type == "integer" else "label",
            "value": dataset.query.answer,
        },
        "projected_annotation": dict(projected),
    }
    visual_count = max(1, len(dataset.points) + len(dataset.surface_cells) + len(dataset.panels))
    return Surface3DTaskComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type="integer" if dataset.query.answer_type == "integer" else "string",
        answer_value=dataset.query.answer,
        annotation_type="bbox_set",
        annotation_value=list(projected["bbox_set"]),
        image=image,
        query_id=str(dataset.query.query_id),
        trace_payload=trace_payload,
    )


__all__ = ["Surface3DTaskComponents", "build_surface_3d_task_components"]
