"""Output component assembly for style-legend chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from .....core.types import TypedValue
from ....shared.config_defaults import required_group_defaults
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ....shared.text_rendering import temporary_default_font_family
from ...shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from .style_legend_common import (
    EXTREMUM_QUERY_IDS,
    GAP_QUERY_IDS,
    SCENE_ID,
    THRESHOLD_QUERY_IDS,
    _PALETTE_MODE_LOAD,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_QUERY,
    _Dataset,
    _Rendered,
    _gen_int,
    _point,
)
from .style_legend_rendering import _render_dataset
from .style_legend_sampling import _build_dataset, _style_support_trace


@dataclass(frozen=True)
class StyleLegendTaskComponents:
    prompt: str
    prompt_variants: Dict[str, str]
    answer_type: str
    answer_value: Any
    annotation_type: str
    annotation_value: Any
    image: Any
    query_id: str
    trace_payload: Dict[str, Any]


def _build_annotation(dataset: _Dataset, rendered: _Rendered) -> TypedValue:
    points: List[list[float]] = []
    for point_id in dataset.query.annotation_point_ids:
        bbox = rendered.point_bboxes_px[str(point_id)]
        points.append(_point(0.5 * (float(bbox[0]) + float(bbox[2])), 0.5 * (float(bbox[1]) + float(bbox[3]))))
    return TypedValue(type="point_set", value=[list(point) for point in points])


def _projected_annotation(annotation_gt: TypedValue) -> Dict[str, Any]:
    return {
        "type": "point_set",
        "point_set": [list(point) for point in annotation_gt.value],
        "pixel_point_set": [list(point) for point in annotation_gt.value],
    }


def build_style_legend_task_components(
    *,
    task_id: str,
    selected_query_id: str,
    query_id_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> StyleLegendTaskComponents:

    params = dict(params)
    query_id = str(selected_query_id)
    dataset: _Dataset | None = None
    last_error: Exception | None = None
    for attempt_index in range(max(1, int(max_attempts))):
        try:
            attempt_params = {**params, "_attempt_index": int(attempt_index)}
            dataset = _build_dataset(
                attempt_params,
                instance_seed=int(instance_seed) + int(attempt_index),
                query_id=str(query_id),
                query_probabilities=query_id_probabilities,
            )
            break
        except Exception as exc:
            last_error = exc
    if dataset is None:
        raise RuntimeError(f"failed to generate {task_id} instance") from last_error

    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.chart_font",
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered = _render_dataset(
            dataset,
            params={**params, "_render_style_seed": int(instance_seed)},
            instance_seed=int(instance_seed),
            chart_font_family=str(chart_font_family),
        )
    annotation_gt = _build_annotation(dataset, rendered)

    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key_style_legend",
            "task_key_style_legend",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_style_legend",
            "answer_hint_count",
            "answer_hint_label",
            "answer_hint_value",
            "annotation_hint_style_legend_point_set",
            "json_example_style_legend_extremum_label",
            "json_example_style_legend_pairwise_gap_value",
            "json_example_style_legend_threshold_count",
            "json_example_answer_only_style_legend_extremum_label",
            "json_example_answer_only_style_legend_pairwise_gap_value",
            "json_example_answer_only_style_legend_threshold_count",
        ),
        context=f"prompt defaults for {task_id}",
    )
    prompt_profile = (
        "style_legend_extremum_label"
        if str(dataset.query.query_id) in set(EXTREMUM_QUERY_IDS)
        else "style_legend_pairwise_gap_value"
        if str(dataset.query.query_id) in set(GAP_QUERY_IDS)
        else "style_legend_threshold_count"
    )
    answer_hint_key = (
        "answer_hint_label"
        if str(dataset.query.answer_type) == "string"
        else "answer_hint_count"
        if str(dataset.query.query_id) in set(THRESHOLD_QUERY_IDS)
        else "answer_hint_value"
    )
    query_slots = {
        "x_label": str(dataset.query.params.get("x_label", "")),
        "extremum_direction": str(dataset.query.params.get("extremum_direction", "")),
        "left_series_label": str(dataset.query.params.get("left_series_label", "")),
        "right_series_label": str(dataset.query.params.get("right_series_label", "")),
        "threshold_value": "" if dataset.threshold_value is None else str(dataset.threshold_value),
        "threshold_relation_phrase": str(dataset.query.params.get("threshold_relation_phrase", "")),
    }
    prompt_selection = render_scene_prompt_variants(
        domain="charts",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key_style_legend"]),
        task_key=str(prompt_defaults["task_key_style_legend"]),
        query_key=str(dataset.query.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "object_description": str(prompt_defaults["object_description_style_legend"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint_style_legend_point_set"]),
            "answer_hint": str(prompt_defaults[answer_hint_key]),
            "json_example": str(prompt_defaults[f"json_example_{prompt_profile}"]),
            "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{prompt_profile}"]),
            **dict(query_slots),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    execution_trace = {
        "query_id": str(dataset.query.query_id),
        "scene_id": SCENE_ID,
        "question_format": "style_legend",
        "answer_value": dataset.query.answer,
        "answer_type": str(dataset.query.answer_type),
        "x_count": int(len(dataset.x_labels)),
        "series_count": int(len(dataset.series)),
        "x_labels": list(dataset.x_labels),
        "x_label_meta": dict(dataset.x_label_meta),
        "series_label_meta": dict(dataset.series_label_meta),
        "series": _style_support_trace(dataset.series),
        "target_x_index": int(dataset.target_x_index),
        "target_x_label": str(dataset.x_labels[int(dataset.target_x_index)]),
        "threshold_value": dataset.threshold_value,
        "pair_series_ids": list(dataset.pair_series_ids),
        "annotation_point_ids": list(dataset.query.annotation_point_ids),
        "query_params": dict(dataset.query.params),
        "query_id_probabilities": dict(dataset.query_id_probabilities),
        "style_palette_mode": str(dataset.palette_mode),
        "style_palette_mode_probabilities": dict(dataset.palette_mode_probabilities),
        "legend_position": str(dataset.legend_position),
        "legend_position_probabilities": dict(dataset.legend_position_probabilities),
    }
    trace_payload = {
        "scene_ir": {
            "scene_kind": "chart_style_legend",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "query_id": str(dataset.query.query_id),
                "scene_id": SCENE_ID,
                "target_x_index": int(dataset.target_x_index),
                "annotation_point_ids": list(dataset.query.annotation_point_ids),
            },
        },
        "query_spec": {
            "query_id": str(dataset.query.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "query_id": str(dataset.query.query_id),
                "scene_id": SCENE_ID,
                "query_id_probabilities": dict(dataset.query_id_probabilities),
                "style_palette_mode": str(dataset.palette_mode),
                "style_palette_mode_probabilities": dict(dataset.palette_mode_probabilities),
                "legend_position": str(dataset.legend_position),
                "legend_position_probabilities": dict(dataset.legend_position_probabilities),
                "answer_support": list(dataset.query.params.get("answer_support", [])),
                **dict(dataset.query.params),
            },
        },
        "render_spec": {
            "canvas_width": int(rendered.image.size[0]),
            "canvas_height": int(rendered.image.size[1]),
            "coord_space": "pixel",
            "scene_id": SCENE_ID,
            "plot_bbox_px": list(rendered.plot_bbox_px),
            "legend_bbox_px": list(rendered.legend_bbox_px),
            "font_assets": chart_font_asset_metadata(str(chart_font_family)),
            **dict(rendered.render_meta),
        },
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered.plot_bbox_px),
            "legend_bbox_px": list(rendered.legend_bbox_px),
            "legend_item_bboxes_px": dict(rendered.legend_item_bboxes_px),
            "point_bboxes_px": dict(rendered.point_bboxes_px),
            "threshold_bbox_px": rendered.threshold_bbox_px,
        },
        "execution_trace": dict(execution_trace),
        "witness_symbolic": {
            "type": "style_legend_point_witness",
            "point_ids": list(dataset.query.annotation_point_ids),
            "answer": dataset.query.answer,
        },
        "projected_annotation": _projected_annotation(annotation_gt),
    }
    visual_count = int(len(dataset.x_labels)) * int(len(dataset.series))
    visual_max = int(_gen_int(params, "style_legend_x_count_max", 9)) * int(_gen_int(params, "style_legend_series_count_max", 6))
    return StyleLegendTaskComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type=str(dataset.query.answer_type),
        answer_value=dataset.query.answer,
        annotation_type=str(annotation_gt.type),
        annotation_value=annotation_gt.value,
        image=rendered.image,
        query_id=str(dataset.query.query_id),
        trace_payload=trace_payload,
    )


__all__ = ["StyleLegendTaskComponents", "build_style_legend_task_components"]
