"""Rendering and trace helpers for geometry graphing-count tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from PIL import ImageDraw

from ..function_scene import (
    build_query_line_color,
    draw_function_polyline,
    draw_horizontal_query_line,
    graph_units_to_pixel_float,
)
from ....shared.labeled_point_annotation import (
    empty_graph_point_set_annotation_artifacts,
    graph_point_set_annotation_artifacts,
)
from ....shared.single_object_scene import GraphSceneContext

from .count_common import (
    HORIZONTAL_REFERENCE_LINE,
    LOCAL_EXTREMUM_COUNT,
    MAXIMUM_EXTREMUM,
    MINIMUM_EXTREMUM,
    REFERENCE_LINE_CROSSING_COUNT,
    TURNING_POINT_COUNT,
    X_AXIS_REFERENCE_LINE,
    GraphPoint,
    GraphPolylinePoint,
    _RenderedGraphScene,
    _ResolvedQuery,
    _SampledGraphScene,
)

def _build_object_description(
    *,
    prompt_defaults: Mapping[str, Any],
    scene_variant: str,
    query_id: str,
    reference_line_kind: str | None,
) -> str:
    """Resolve one prompt-facing scene description without hardcoding prose here."""

    suffix = (
        "_with_guide_line"
        if str(query_id) == REFERENCE_LINE_CROSSING_COUNT
        and str(reference_line_kind) == HORIZONTAL_REFERENCE_LINE
        else ""
    )
    key = f"object_description_{str(scene_variant).strip().lower()}{suffix}"
    value = prompt_defaults.get(key)
    if value is None:
        raise ValueError(f"missing prompt default for {key}")
    return str(value)


def _prompt_default(prompt_defaults: Mapping[str, Any], key: str) -> str:
    """Return one required prompt default string."""

    value = prompt_defaults.get(str(key))
    if value is None:
        raise ValueError(f"missing prompt default for {key}")
    return str(value)


def _reference_line_prompt_description(
    *,
    prompt_defaults: Mapping[str, Any],
    reference_line_kind: str | None,
    query_line_y: int | None,
) -> str:
    """Resolve the prompt description for the selected reference-line parameter."""

    if str(reference_line_kind) == X_AXIS_REFERENCE_LINE:
        return _prompt_default(prompt_defaults, "reference_line_description_x_axis")
    if str(reference_line_kind) == HORIZONTAL_REFERENCE_LINE:
        template = _prompt_default(prompt_defaults, "reference_line_description_horizontal_line")
        if query_line_y is None:
            raise ValueError("horizontal reference-line prompts require query_line_y")
        return str(template).format(query_line_equation=f"y = {int(query_line_y)}")
    return ""


def _extremum_prompt_slots(
    *,
    prompt_defaults: Mapping[str, Any],
    extremum_kind: str | None,
) -> Dict[str, str]:
    """Resolve prompt slots for the selected local-extremum parameter."""

    if str(extremum_kind) == MINIMUM_EXTREMUM:
        suffix = "minimum"
    elif str(extremum_kind) == MAXIMUM_EXTREMUM:
        suffix = "maximum"
    else:
        return {
            "extremum_kind_adjective": "",
            "extremum_visual_description": "",
        }
    return {
        "extremum_kind_adjective": _prompt_default(prompt_defaults, f"extremum_kind_adjective_{suffix}"),
        "extremum_visual_description": _prompt_default(prompt_defaults, f"extremum_visual_description_{suffix}"),
    }


def _pixel_point(point: GraphPoint | GraphPolylinePoint, *, context: GraphSceneContext) -> Tuple[float, float]:
    """Project one graph point into canonical pixel coordinates."""

    return graph_units_to_pixel_float(
        point,
        graph_origin=context.graph_origin,
        graph_spacing=int(context.graph_spacing),
    )


def _render_scene(
    draw: ImageDraw.ImageDraw,
    *,
    context: GraphSceneContext,
    sampled_scene: _SampledGraphScene,
    shape_style,
    line_width: int,
    guide_line_width: int,
    label_font_size_px: int,
) -> _RenderedGraphScene:
    """Render one sampled graphing scene and build annotation artifacts."""

    render_polyline = draw_function_polyline(
        draw,
        polyline_graph=sampled_scene.polyline_graph,
        graph_origin=context.graph_origin,
        graph_spacing=int(context.graph_spacing),
        scene_scale=int(context.scene_scale),
        line_width=int(line_width),
        line_color=shape_style.line_color,
    )
    render_map = dict(sampled_scene.render_map)
    render_map["function_polyline_pixel"] = [
        [round(float(_pixel_point(point, context=context)[0]), 3), round(float(_pixel_point(point, context=context)[1]), 3)]
        for point in sampled_scene.polyline_graph
    ]
    render_map["function_polyline_render"] = [
        [round(float(point[0]), 3), round(float(point[1]), 3)]
        for point in render_polyline
    ]

    if sampled_scene.query_line_y is not None:
        query_line_meta = draw_horizontal_query_line(
            draw,
            y_value=int(sampled_scene.query_line_y),
            x_min=-9,
            x_max=9,
            graph_origin=context.graph_origin,
            graph_spacing=int(context.graph_spacing),
            scene_scale=int(context.scene_scale),
            dash_px=14.0 * float(context.scene_scale),
            gap_px=8.0 * float(context.scene_scale),
            line_width=int(guide_line_width),
            line_color=build_query_line_color(
                line_color=shape_style.line_color,
                label_color=shape_style.label_color,
            ),
            label_text=f"y = {int(sampled_scene.query_line_y)}",
            label_font_size_px=int(label_font_size_px),
            label_color=shape_style.label_color,
            canvas_size=int(context.canvas_size),
        )
        render_map.update(dict(query_line_meta))

    points_by_label = {
        f"point_{index + 1}": _pixel_point(point, context=context)
        for index, point in enumerate(sampled_scene.annotation_graph_points)
    }
    annotation = (
        graph_point_set_annotation_artifacts(
            points_by_label=points_by_label,
            graph_origin=context.graph_origin,
            graph_spacing=int(context.graph_spacing),
            witness_type="graph_feature_points",
            ordered_labels=tuple(points_by_label.keys()),
        )
        if points_by_label
        else empty_graph_point_set_annotation_artifacts(witness_type="graph_feature_points")
    )
    return _RenderedGraphScene(
        answer_value=int(len(sampled_scene.annotation_graph_points)),
        annotation_type=str(annotation["annotation_type"]),
        annotation_value=[list(point) for point in annotation["annotation_value"]],
        projected_annotation=dict(annotation["projected_annotation"]),
        witness_symbolic=dict(annotation["witness_symbolic"]),
        required_annotation_labels=list(annotation["required_labels"]),
        scene_entities=list(sampled_scene.scene_entities),
        render_map=dict(render_map),
        execution_trace=dict(sampled_scene.execution_trace),
        object_count=int(sampled_scene.object_count),
    )


def _query_params_for_trace(query: _ResolvedQuery) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "scene_variant": str(query.scene_variant),
        "query_id": str(query.query_id),
        "query_id_probabilities": dict(query.query_id_probabilities),
        "scene_variant_probabilities": dict(query.scene_variant_probabilities),
        "target_count": int(query.target_count),
        "target_count_probabilities": dict(query.target_count_probabilities),
    }
    if query.reference_line_kind is not None:
        params["reference_line_kind"] = str(query.reference_line_kind)
        params["reference_line_kind_probabilities"] = dict(query.reference_line_kind_probabilities)
    if query.extremum_kind is not None:
        params["extremum_kind"] = str(query.extremum_kind)
        params["extremum_kind_probabilities"] = dict(query.extremum_kind_probabilities)
    return dict(params)


def _scene_relations_for_trace(query: _ResolvedQuery) -> Dict[str, Any]:
    relations: Dict[str, Any] = {
        "scene_variant": str(query.scene_variant),
        "query_id": str(query.query_id),
        "target_count": int(query.target_count),
    }
    if query.reference_line_kind is not None:
        relations["reference_line_kind"] = str(query.reference_line_kind)
    if query.extremum_kind is not None:
        relations["extremum_kind"] = str(query.extremum_kind)
    return dict(relations)


def _execution_trace_for_trace(query: _ResolvedQuery, rendered_scene: _RenderedGraphScene) -> Dict[str, Any]:
    execution_trace: Dict[str, Any] = {
        "scene_variant": str(query.scene_variant),
        "query_id": str(query.query_id),
        "scene_variant_probabilities": dict(query.scene_variant_probabilities),
        "query_id_probabilities": dict(query.query_id_probabilities),
        "target_count": int(query.target_count),
        "target_count_probabilities": dict(query.target_count_probabilities),
        "question_format": "count_graph_feature_points",
        "required_annotation_labels": list(rendered_scene.required_annotation_labels),
        **dict(rendered_scene.execution_trace),
    }
    if query.reference_line_kind is not None:
        execution_trace["reference_line_kind"] = str(query.reference_line_kind)
        execution_trace["reference_line_kind_probabilities"] = dict(query.reference_line_kind_probabilities)
    if query.extremum_kind is not None:
        execution_trace["extremum_kind"] = str(query.extremum_kind)
        execution_trace["extremum_kind_probabilities"] = dict(query.extremum_kind_probabilities)
    return dict(execution_trace)

__all__ = [
    "_build_object_description",
    "_extremum_prompt_slots",
    "_reference_line_prompt_description",
    "_render_scene",
    "_query_params_for_trace",
    "_scene_relations_for_trace",
    "_execution_trace_for_trace",
]
