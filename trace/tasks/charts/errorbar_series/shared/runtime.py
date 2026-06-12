"""Runtime helpers for errorbar-series chart tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.tasks.charts.errorbar_series.shared.series_query import (
    BOUND_EXTREMUM_PROMPT_KEYS,
    SCENE_ID,
    _Dataset,
    _QUERY_REASONING_LOADS,
    _Rendered,
    _SCENE_VARIANT_LOADS,
    errorbar_series_records,
    render_errorbar_series_chart,
)
from trace.tasks.charts.shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from trace.tasks.shared.text_rendering import temporary_default_font_family


def render_dataset(
    dataset: _Dataset,
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[_Rendered, Dict[str, Any], str]:
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace="charts_errorbar_series.chart_font",
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered = render_errorbar_series_chart(
            dataset,
            params=params,
            instance_seed=int(instance_seed),
            chart_font_family=str(chart_font_family),
        )
    render_meta = {
        "canvas_width": int(rendered.image.size[0]),
        "canvas_height": int(rendered.image.size[1]),
        "coord_space": "pixel",
        "scene_variant": str(dataset.scene_variant),
        "plot_bbox_px": list(rendered.plot_bbox_px),
        "font_assets": chart_font_asset_metadata(str(chart_font_family)),
        **dict(rendered.render_meta),
    }
    return rendered, dict(render_meta), str(chart_font_family)


def answer_typed_value(dataset: _Dataset) -> TypedValue:
    answer_value: int | str = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
    return TypedValue(type=str(dataset.query.answer_type), value=answer_value)


def annotation_payload(
    *,
    dataset: _Dataset,
    rendered: _Rendered,
) -> tuple[str, Any, Dict[str, Any], list[dict[str, Any]]]:
    if str(dataset.query.annotation_kind) == "bbox_set":
        boxes = []
        refs = []
        for key in dataset.query.annotation_item_keys:
            if str(key) not in rendered.errorbar_bboxes_px:
                raise RuntimeError(f"missing errorbar bbox for {key}")
            boxes.append(list(rendered.errorbar_bboxes_px[str(key)]))
            refs.append({"key": str(key), "bbox_px": list(rendered.errorbar_bboxes_px[str(key)])})
        projected = {"type": "bbox_set", "bbox_set": list(boxes), "pixel_bbox_set": list(boxes), "annotation_refs": list(refs)}
        return "bbox_set", list(boxes), dict(projected), [dict(ref) for ref in refs]

    if str(dataset.query.annotation_kind) == "keyed_point_map":
        key = str(dataset.query.annotation_item_keys[0])
        series_label, x_label = key.split(":", 1)
        bound_kind = str(dataset.query.params["bound_kind"])
        point = list(rendered.point_map_px[str(series_label)][str(x_label)][f"{bound_kind}_bound"])
        value = {"selected_bound_endpoint": list(point)}
        refs = [{"key": str(key), "series_label": str(series_label), "x_label": str(x_label), "point_xy": list(point)}]
        projected = {
            "type": "keyed_point_map",
            "keyed_point_map": dict(value),
            "pixel_keyed_point_map": dict(value),
            "annotation_refs": list(refs),
        }
        return "keyed_point_map", dict(value), dict(projected), [dict(ref) for ref in refs]

    if str(dataset.query.annotation_kind) == "keyed_bbox_map":
        mapping: Dict[str, list[float]] = {}
        refs = []
        for index, key in enumerate(dataset.query.annotation_item_keys):
            if str(key) not in rendered.errorbar_bboxes_px:
                raise RuntimeError(f"missing errorbar bbox for {key}")
            role = "target_errorbar" if int(index) == 0 else str(key).split(":", 1)[0]
            mapping[str(role)] = list(rendered.errorbar_bboxes_px[str(key)])
            refs.append({"key": str(key), "role": str(role), "bbox_px": list(rendered.errorbar_bboxes_px[str(key)])})
        projected = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(mapping),
            "pixel_keyed_bbox_map": dict(mapping),
            "annotation_refs": list(refs),
        }
        return "keyed_bbox_map", dict(mapping), dict(projected), [dict(ref) for ref in refs]

    raise ValueError(f"unsupported annotation kind: {dataset.query.annotation_kind}")


def build_trace_scaffold(
    *,
    dataset: _Dataset,
    rendered: _Rendered,
    render_meta: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
    annotation_refs: list[dict[str, Any]],
    answer_value: int | str,
) -> Dict[str, Any]:
    execution_trace = {
        "scene_id": SCENE_ID,
        "scene_variant": str(dataset.scene_variant),
        "question_format": "errorbar_series",
        "answer_value": answer_value,
        "answer_type": str(dataset.query.answer_type),
        "x_count": int(len(dataset.x_labels)),
        "series_count": int(len(dataset.series)),
        "x_labels": list(dataset.x_labels),
        "x_label_meta": dict(dataset.x_label_meta),
        "series_label_meta": dict(dataset.series_label_meta),
        "series": errorbar_series_records(dataset),
        "target_series_id": str(dataset.target_series_id),
        "target_x_index": dataset.target_x_index,
        "threshold_value": dataset.threshold_value,
        "query_params": dict(dataset.query.params),
        "annotation_item_keys": list(dataset.query.annotation_item_keys),
        "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
    }
    return {
        "scene_ir": {
            "scene_kind": "chart_errorbar_series",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_variant": str(dataset.scene_variant),
                "target_series_id": str(dataset.target_series_id),
                "target_x_index": dataset.target_x_index,
            },
        },
        "render_spec": dict(render_meta),
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered.plot_bbox_px),
            "errorbar_bboxes_px": dict(rendered.errorbar_bboxes_px),
            "point_map_px": dict(rendered.point_map_px),
            "threshold_bbox_px": rendered.threshold_bbox_px,
        },
        "execution_trace": dict(execution_trace),
        "witness_symbolic": {
            "type": "errorbar_series_witness",
            "annotation_kind": str(dataset.query.annotation_kind),
            "annotation_item_keys": list(dataset.query.annotation_item_keys),
            "answer": answer_value,
        },
        "projected_annotation": dict(projected_annotation),
        "annotation_refs": [dict(ref) for ref in annotation_refs],
    }




def prompt_profile(dataset: _Dataset) -> str:
    if str(dataset.query.prompt_key) in set(BOUND_EXTREMUM_PROMPT_KEYS):
        return "bound_extremum_x_label"
    if str(dataset.query.annotation_kind) == "keyed_bbox_map":
        return "same_x_interval_overlap_count"
    return "threshold_support_count"

