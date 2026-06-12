"""Runtime helpers for error-interval chart tasks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.charts.error_interval.shared.interval_chart import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    _Dataset,
    _QUERY_LOADS,
    _Rendered,
    _SCENE_LOADS,
    render_error_interval_chart,
    resolve_error_interval_render_params,
)
from trace.tasks.shared.font_assets import font_asset_version


def render_dataset(
    dataset: _Dataset,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[_Rendered, Dict[str, Any], Dict[str, Any]]:
    render_params = resolve_error_interval_render_params(params, instance_seed=int(instance_seed))
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=dict(params),
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    rendered = render_error_interval_chart(
        background,
        dataset=dataset,
        params=params,
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
        "scene_variant": str(dataset.scene_variant),
        "canvas_width": int(image.size[0]),
        "canvas_height": int(image.size[1]),
        "coord_space": "pixel",
        "category_labels": [str(item.label) for item in dataset.items],
        "render_meta": dict(rendered.render_meta),
        "layout_jitter": dict(rendered.render_meta.get("layout_jitter", {})),
        "font_assets": dict(rendered.render_meta.get("font_assets", {}))
        or {"asset_version": str(font_asset_version())},
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
    item_by_id = {str(item.item_id): item for item in dataset.items}
    annotation_item_ids = [str(value) for value in dataset.query.annotation_item_ids]
    annotation = [list(rendered.interval_bboxes_px[str(item_id)]) for item_id in annotation_item_ids]
    records = [
        {
            "item_id": str(item_id),
            "item_label": str(item_by_id[str(item_id)].label),
            "lower": int(item_by_id[str(item_id)].lower),
            "midpoint": int(item_by_id[str(item_id)].midpoint),
            "upper": int(item_by_id[str(item_id)].upper),
            "interval_width": int(item_by_id[str(item_id)].upper) - int(item_by_id[str(item_id)].lower),
            "interval_bbox_px": list(rendered.interval_bboxes_px[str(item_id)]),
        }
        for item_id in annotation_item_ids
    ]
    projected = {
        "type": "bbox_set",
        "bbox_set": list(annotation),
        "pixel_bbox_set": list(annotation),
        "bbox_map": {str(item_id): list(rendered.interval_bboxes_px[str(item_id)]) for item_id in annotation_item_ids},
        "item_ids": list(annotation_item_ids),
        "item_labels": [str(record["item_label"]) for record in records],
        "annotation_refs": [dict(record) for record in records],
    }
    return "bbox_set", list(annotation), dict(projected), [dict(record) for record in records]


def interval_records(dataset: _Dataset) -> list[dict[str, Any]]:
    return [
        {
            "item_id": str(item.item_id),
            "label": str(item.label),
            "lower": int(item.lower),
            "midpoint": int(item.midpoint),
            "upper": int(item.upper),
            "interval_width": int(item.upper) - int(item.lower),
        }
        for item in dataset.items
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
    label_to_interval = {
        item.label: {"lower": int(item.lower), "midpoint": int(item.midpoint), "upper": int(item.upper)}
        for item in dataset.items
    }
    return {
        "scene_ir": {
            "scene_kind": SCENE_ID,
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_variant": str(dataset.scene_variant),
                "reference_value": dataset.reference_value,
                "answer_value": answer_value,
                "annotation_item_ids": [str(value) for value in dataset.query.annotation_item_ids],
            },
        },
        "render_spec": dict(render_meta),
        "render_map": {
            "plot_bbox_px": list(rendered.plot_bbox_px),
            "item_bboxes_px": dict(rendered.item_bboxes_px),
            "interval_bboxes_px": dict(rendered.interval_bboxes_px),
        },
        "execution_trace": {
            "scene_id": SCENE_ID,
            "question_format": "error_interval",
            "scene_variant": str(dataset.scene_variant),
            "category_count": int(len(dataset.items)),
            "reference_value": dataset.reference_value,
            "items": interval_records(dataset),
            "label_to_interval": dict(label_to_interval),
            "answer_value": answer_value,
            "answer_type": str(dataset.query.answer_type),
            "annotation_item_ids": [str(value) for value in dataset.query.annotation_item_ids],
            "annotation_labels": [str(record["item_label"]) for record in annotation_refs],
            **dict(dataset.query.params),
        },
        "witness_symbolic": {
            "type": "error_interval_witness",
            "answer_value": answer_value,
            "annotation_item_ids": [str(value) for value in dataset.query.annotation_item_ids],
        },
        "projected_annotation": dict(projected_annotation),
        "sidecar": dict(sidecar_meta),
        "annotation_refs": [dict(record) for record in annotation_refs],
    }




