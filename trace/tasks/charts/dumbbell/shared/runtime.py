"""Runtime helpers for dumbbell chart tasks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.charts.dumbbell.shared.pairwise_comparison_query import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    SCENE_NAMESPACE,
    _Dataset,
    _REASONING_LOAD_BY_VARIANT,
    _Rendered,
    _SCENE_LOAD_BY_VARIANT,
    render_dumbbell_chart,
    resolve_dumbbell_render_params,
)
from trace.tasks.shared.font_assets import font_asset_version


def render_dataset(
    dataset: _Dataset,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[_Rendered, Dict[str, Any], Dict[str, Any]]:
    render_params = resolve_dumbbell_render_params(params, instance_seed=int(instance_seed))
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    rendered = render_dumbbell_chart(
        background,
        dataset=dataset,
        render_params=render_params,
        instance_seed=int(instance_seed),
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    rendered = replace(rendered, image=image)
    render_meta = {
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "scene_variant": str(dataset.scene_variant),
        "row_count": int(len(dataset.rows)),
        "plot_bbox_px": list(rendered.plot_bbox_px),
        "legend_bboxes_px": dict(rendered.legend_bboxes_px),
        "layout_jitter": dict(render_params.layout_jitter_meta or {}),
        "font_assets": {
            "asset_version": str(font_asset_version()),
            "chart_font_family": str(render_params.font_family),
        },
        "chart_font_family": str(render_params.font_family),
        "font_asset_version": str(font_asset_version()),
        "post_image_noise": dict(post_noise_meta),
    }
    return rendered, dict(render_meta), {"background": dict(background_meta), "post_image_noise": dict(post_noise_meta)}


def answer_typed_value(dataset: _Dataset) -> TypedValue:
    answer_value: int | str = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
    return TypedValue(type=str(dataset.query.answer_type), value=answer_value)


def annotation_payload(
    *,
    dataset: _Dataset,
    rendered: _Rendered,
) -> tuple[str, list[list[float]], Dict[str, Any], list[dict[str, Any]]]:
    rows_by_id = {str(row.row_id): row for row in dataset.rows}
    annotation_rows = [str(row_id) for row_id in dataset.query.annotation_row_ids]
    annotation = [list(rendered.row_pair_bboxes_px[str(row_id)]) for row_id in annotation_rows]
    records = [
        {
            "row_id": str(row_id),
            "row_label": str(rows_by_id[str(row_id)].label),
            "value_a": int(rows_by_id[str(row_id)].value_a),
            "value_b": int(rows_by_id[str(row_id)].value_b),
            "gap": int(rows_by_id[str(row_id)].gap),
            "row_pair_bbox_px": list(rendered.row_pair_bboxes_px[str(row_id)]),
            "connector_bbox_px": list(rendered.connector_bboxes_px[str(row_id)]),
            "point_a_bbox_px": list(rendered.point_bboxes_px[f"{row_id}:series_a"]),
            "point_b_bbox_px": list(rendered.point_bboxes_px[f"{row_id}:series_b"]),
        }
        for row_id in annotation_rows
    ]
    projected = {
        "type": "bbox_set",
        "bbox_set": list(annotation),
        "pixel_bbox_set": list(annotation),
        "annotation_refs": [dict(record) for record in records],
    }
    return "bbox_set", list(annotation), dict(projected), [dict(record) for record in records]


def row_records(dataset: _Dataset) -> list[dict[str, Any]]:
    return [
        {
            "row_id": str(row.row_id),
            "label": str(row.label),
            "value_a": int(row.value_a),
            "value_b": int(row.value_b),
            "gap": int(row.gap),
        }
        for row in dataset.rows
    ]


def build_trace_scaffold(
    *,
    dataset: _Dataset,
    rendered: _Rendered,
    render_meta: Mapping[str, Any],
    sidecar_meta: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
    annotation_refs: list[dict[str, Any]],
    answer_value: int | str,
) -> Dict[str, Any]:
    return {
        "scene_ir": {
            "scene_kind": "chart_dumbbell",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_variant": str(dataset.scene_variant),
                "series_a_name": str(dataset.series_a_name),
                "series_b_name": str(dataset.series_b_name),
                "answer": answer_value,
                "annotation_row_ids": [str(row_id) for row_id in dataset.query.annotation_row_ids],
            },
        },
        "render_spec": dict(render_meta),
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered.plot_bbox_px),
            "row_label_bboxes_px": dict(rendered.row_label_bboxes_px),
            "point_bboxes_px": dict(rendered.point_bboxes_px),
            "row_pair_bboxes_px": dict(rendered.row_pair_bboxes_px),
            "connector_bboxes_px": dict(rendered.connector_bboxes_px),
            "legend_bboxes_px": dict(rendered.legend_bboxes_px),
        },
        "execution_trace": {
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            "series_a_name": str(dataset.series_a_name),
            "series_b_name": str(dataset.series_b_name),
            "row_records": row_records(dataset),
            "query_params": dict(dataset.query.params),
            "answer": answer_value,
            "question_format": "dumbbell_pairwise_comparison",
        },
        "witness_symbolic": {
            "type": "row_set",
            "value": [str(row_id) for row_id in dataset.query.annotation_row_ids],
        },
        "projected_annotation": dict(projected_annotation),
        "sidecar": dict(sidecar_meta),
        "annotation_refs": [dict(record) for record in annotation_refs],
    }




