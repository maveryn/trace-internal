"""Runtime helpers for curve-panel chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from trace.tasks.charts.curve_panels.shared.multipanel_common import (
    SCENE_ID,
    SCENE_NAMESPACE,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    _Dataset,
    _Rendered,
    _gen_int,
    _resolve_int,
)
from trace.tasks.charts.curve_panels.shared.multipanel_rendering import _render_dataset
from trace.tasks.charts.shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from trace.tasks.shared.text_rendering import temporary_default_font_family


def _bbox_center(bbox: Sequence[float]) -> List[float]:
    if len(bbox) < 4:
        raise ValueError("bbox must have at least four coordinates")
    x0, y0, x1, y1 = [float(value) for value in bbox[:4]]
    return [round((x0 + x1) * 0.5, 3), round((y0 + y1) * 0.5, 3)]


def _annotation_points(dataset: _Dataset, rendered: _Rendered) -> List[List[float]]:
    points: List[List[float]] = []
    for point_id in dataset.query.annotation_point_ids:
        point_box = rendered.point_bboxes.get(str(point_id))
        if point_box is not None:
            points.append(_bbox_center(point_box))
    for intersection_id in dataset.query.annotation_intersection_ids:
        intersection_box = rendered.intersection_bboxes.get(str(intersection_id))
        if intersection_box is not None:
            points.append(_bbox_center(intersection_box))
    for crossing_id in dataset.query.annotation_threshold_crossing_ids:
        crossing_box = rendered.threshold_crossing_bboxes.get(str(crossing_id))
        if crossing_box is not None:
            points.append(_bbox_center(crossing_box))
    return points


def _cross_panel_delta_annotation_map(dataset: _Dataset, rendered: _Rendered) -> Dict[str, List[float]]:
    annotation: Dict[str, List[float]] = {}
    for point_id in dataset.query.annotation_point_ids:
        point_box = rendered.point_bboxes.get(str(point_id))
        if point_box is None:
            continue
        parts = str(point_id).split("|")
        if len(parts) != 3:
            continue
        panel_label, _method_label, x_value = parts
        role = "start" if int(x_value) == int(dataset.query.start_x_value) else "end"
        annotation[f"{str(panel_label)}_{role}"] = _bbox_center(point_box)
    expected_key_count = int(len(dataset.panels)) * 2
    if len(annotation) != int(expected_key_count):
        raise RuntimeError("cross-panel delta annotation map is incomplete")
    return annotation


def values_by_panel_method(dataset: _Dataset) -> Dict[str, Dict[str, List[int]]]:
    return {
        str(panel.panel_label): {
            str(curve.method_label): [int(value) for value in curve.values]
            for curve in panel.curves
        }
        for panel in dataset.panels
    }


def render_dataset(dataset: _Dataset, *, params: Mapping[str, Any], instance_seed: int) -> tuple[_Rendered, str]:
    chart_font_family = sample_chart_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.chart_font",
        params=params,
    )
    with temporary_default_font_family(str(chart_font_family)):
        rendered = _render_dataset(dataset, params=params, instance_seed=int(instance_seed))
    return rendered, str(chart_font_family)


def annotation_payload(dataset: _Dataset, rendered: _Rendered) -> tuple[str, List[List[float]] | Dict[str, List[float]]]:
    if str(dataset.query.prompt_key) == "cross_panel_delta_extremum_label":
        value: List[List[float]] | Dict[str, List[float]] = _cross_panel_delta_annotation_map(dataset, rendered)
        annotation_type = "keyed_point_map"
    else:
        value = _annotation_points(dataset, rendered)
        annotation_type = "point_set"
    if not value and str(dataset.query.prompt_key) != "curve_intersection_count":
        raise RuntimeError("curve-panel task produced empty annotation")
    return str(annotation_type), value


def projected_annotation(
    *,
    dataset: _Dataset,
    annotation_type: str,
    value: List[List[float]] | Dict[str, List[float]],
) -> Dict[str, Any]:
    if str(annotation_type) == "keyed_point_map":
        keyed_point_map = {str(key): list(point) for key, point in dict(value).items()}
        return {
            "type": "keyed_point_map",
            "keyed_point_map": dict(keyed_point_map),
            "pixel_keyed_point_map": dict(keyed_point_map),
            "panel_labels": list(dataset.query.annotation_panel_labels),
            "point_ids": list(dataset.query.annotation_point_ids),
            "intersection_ids": list(dataset.query.annotation_intersection_ids),
            "threshold_crossing_ids": list(dataset.query.annotation_threshold_crossing_ids),
        }
    point_set = [list(point) for point in list(value)]
    return {
        "type": "point_set",
        "point_set": list(point_set),
        "pixel_point_set": list(point_set),
        "panel_labels": list(dataset.query.annotation_panel_labels),
        "point_ids": list(dataset.query.annotation_point_ids),
        "intersection_ids": list(dataset.query.annotation_intersection_ids),
        "threshold_crossing_ids": list(dataset.query.annotation_threshold_crossing_ids),
    }


def build_trace_scaffold(
    *,
    dataset: _Dataset,
    rendered: _Rendered,
    annotation_type: str,
    annotation: List[List[float]] | Dict[str, List[float]],
    chart_font_family: str,
    params: Mapping[str, Any],
) -> Dict[str, Any]:
    method_labels = [str(curve.method_label) for curve in dataset.panels[0].curves]
    return {
        "scene_ir": {
            "scene_kind": f"chart_scientific_{str(dataset.scene_variant)}",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_variant": str(dataset.scene_variant),
                "answer": dataset.query.answer,
                "annotation_panel_labels": list(dataset.query.annotation_panel_labels),
                "annotation_point_ids": list(dataset.query.annotation_point_ids),
                "annotation_intersection_ids": list(dataset.query.annotation_intersection_ids),
                "annotation_threshold_crossing_ids": list(dataset.query.annotation_threshold_crossing_ids),
            },
        },
        "render_spec": {
            "canvas_width": _resolve_int(params, "canvas_width", 1600),
            "canvas_height": _resolve_int(params, "canvas_height", 1000),
            "coord_space": "pixel",
            "scene_variant": str(dataset.scene_variant),
            "plot_bbox_px": list(rendered.plot_bbox_px),
            "font_assets": chart_font_asset_metadata(str(chart_font_family)),
            **dict(rendered.render_meta),
        },
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered.plot_bbox_px),
            "panel_bboxes_px": dict(rendered.panel_bboxes),
            "panel_plot_bboxes_px": dict(rendered.panel_plot_bboxes),
            "point_bboxes_px": dict(rendered.point_bboxes),
            "intersection_bboxes_px": dict(rendered.intersection_bboxes),
            "threshold_crossing_bboxes_px": dict(rendered.threshold_crossing_bboxes),
            "legend_bboxes_px": dict(rendered.legend_bboxes),
        },
        "execution_trace": {
            "scene_id": SCENE_ID,
            "scene_variant": str(dataset.scene_variant),
            "answer": dataset.query.answer,
            "answer_type": str(dataset.query.answer_type),
            "panel_labels": [str(panel.panel_label) for panel in dataset.panels],
            "method_labels": list(method_labels),
            "x_values": list(dataset.x_values),
            "y_range": [int(dataset.y_min), int(dataset.y_max)],
            "panel_count": int(len(dataset.panels)),
            "method_count": int(len(method_labels)),
            "values_by_panel_method": values_by_panel_method(dataset),
            "annotation_panel_labels": list(dataset.query.annotation_panel_labels),
            "annotation_point_ids": list(dataset.query.annotation_point_ids),
            "annotation_intersection_ids": list(dataset.query.annotation_intersection_ids),
            "annotation_threshold_crossing_ids": list(dataset.query.annotation_threshold_crossing_ids),
            "question_format": "curve_panels_subplot_query",
            **dict(dataset.query.trace),
        },
        "witness_symbolic": {
            "type": "curve_panels_subplot",
            "panel_labels": list(dataset.query.annotation_panel_labels),
            "point_ids": list(dataset.query.annotation_point_ids),
            "intersection_ids": list(dataset.query.annotation_intersection_ids),
            "threshold_crossing_ids": list(dataset.query.annotation_threshold_crossing_ids),
            "answer": dataset.query.answer,
        },
        "projected_annotation": projected_annotation(
            dataset=dataset,
            annotation_type=str(annotation_type),
            value=annotation,
        ),
    }




