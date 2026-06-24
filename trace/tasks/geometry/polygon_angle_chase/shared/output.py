"""Trace formatting helpers for polygon angle-chase tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ...shared.annotation_values import PixelAnnotationArtifacts
from ...shared.metadata_serialization import geometry_json_ready

from .defaults import SCENE_ID
from .measurements import angle_name, polygon_angle_sum
from .state import (
    ParallelAnglePlan,
    PolygonAnglePlan,
    RenderContext,
    RenderedParallelAngleScene,
    RenderedPolygonAngleScene,
    RenderedSymmetryAngleScene,
    SymmetryAnglePlan,
)


def point_payload(points: Mapping[str, Sequence[float]]) -> dict[str, list[float]]:
    """Serialize point coordinates for trace payloads."""

    return {
        str(key): [round(float(point[0]), 3), round(float(point[1]), 3)]
        for key, point in points.items()
    }


def polygon_render_map(rendered: RenderedPolygonAngleScene) -> dict[str, Any]:
    """Build the render map for polygon angle scenes."""

    return {
        "point_label_bboxes": geometry_json_ready(rendered.point_label_bboxes, round_floats=False),
        "angle_arc_bboxes": geometry_json_ready(rendered.angle_arc_bboxes, round_floats=False),
        "angle_label_bboxes": geometry_json_ready(rendered.angle_label_bboxes, round_floats=False),
        "polygon_vertices": {
            str(label): [round(float(point[0]), 3), round(float(point[1]), 3)]
            for label, point in zip(rendered.annotation_roles, rendered.vertices)
        },
    }


def parallel_render_map(rendered: RenderedParallelAngleScene) -> dict[str, Any]:
    """Build the render map for parallel-line angle scenes."""

    return {
        "angle_arc_bboxes": geometry_json_ready(rendered.angle_arc_bboxes, round_floats=False),
        "angle_label_bboxes": geometry_json_ready(rendered.angle_label_bboxes, round_floats=False),
        "line_segments": geometry_json_ready(rendered.line_segments, round_floats=False),
        "intersections": point_payload(rendered.intersections),
    }


def symmetry_render_map(rendered: RenderedSymmetryAngleScene) -> dict[str, Any]:
    """Build the render map for symmetry angle scenes."""

    return {
        "angle_arc_bboxes": geometry_json_ready(rendered.angle_arc_bboxes, round_floats=False),
        "angle_label_bboxes": geometry_json_ready(rendered.angle_label_bboxes, round_floats=False),
        "construction_segments": geometry_json_ready(rendered.construction_segments, round_floats=False),
        "construction_points": point_payload(rendered.construction_points),
    }


def render_spec_base(
    *,
    ctx: RenderContext,
    noise_meta: Mapping[str, Any],
    prompt_trace: Mapping[str, Any],
    prompt_active_key: str,
    prompt_variants: Mapping[str, Any],
    include_scene_rotation: bool = False,
) -> dict[str, Any]:
    """Build task-neutral render spec fields."""

    style: dict[str, Any] = {
        "technical_diagram": dict(ctx.diagram_style_meta),
        "background": dict(ctx.background_meta),
        "post_image_noise": dict(noise_meta),
    }
    spec: dict[str, Any] = {
        "scene_id": SCENE_ID,
        "canvas": {"width": int(ctx.width), "height": int(ctx.height)},
        "style": style,
        "prompt": {
            "prompt_variant": dict(prompt_trace),
            "prompt_variant_active_key": str(prompt_active_key),
            "prompt_variants": dict(prompt_variants),
        },
    }
    if bool(include_scene_rotation):
        spec["single_object_scene_rotation"] = ctx.scene_transform.metadata()
    return spec


def polygon_trace_common(
    *,
    plan: PolygonAnglePlan,
    rendered: RenderedPolygonAngleScene,
    annotation_artifacts: PixelAnnotationArtifacts,
) -> dict[str, Any]:
    """Build task-neutral trace fields for polygon angle scenes."""

    vertices_payload = {
        str(label): [round(float(point[0]), 3), round(float(point[1]), 3)]
        for label, point in zip(plan.labels, rendered.vertices)
    }
    angle_names = [angle_name(plan.labels, index) for index in range(plan.side_count)]
    return {
        "entities": [
            {
                "type": "convex_polygon",
                "labels": list(plan.labels),
                "vertices": dict(vertices_payload),
            },
        ],
        "relations": {
            "type": "polygon_interior_angle_sum",
            "side_count": int(plan.side_count),
            "interior_angle_sum": polygon_angle_sum(plan.side_count),
        },
        "execution": {
            "target_angle_name": str(plan.target_angle_name),
            "target_index": int(plan.target_index),
            "target_vertex": str(plan.labels[int(plan.target_index)]),
            "angle_names": list(angle_names),
            "numeric_angles": [int(value) for value in plan.numeric_angles],
            "display_angle_labels": list(plan.display_angle_labels),
            "answer": int(plan.answer),
            "annotation_keys": list(rendered.annotation_roles),
            "annotation_type": str(annotation_artifacts.annotation_type),
            **dict(plan.witness),
        },
        "witness": dict(plan.witness),
        "query_params": {
            "polygon_side_count": int(plan.side_count),
            "label_style": str(plan.label_style),
            "label_style_probabilities": dict(plan.label_style_probabilities),
            "target_index": int(plan.target_index),
        },
    }


def parallel_trace_common(
    *,
    plan: ParallelAnglePlan,
    rendered: RenderedParallelAngleScene,
    annotation_artifacts: PixelAnnotationArtifacts,
) -> dict[str, Any]:
    """Build task-neutral trace fields for parallel-line angle scenes."""

    line_keys = sorted(rendered.line_segments)
    return {
        "entities": {
            "parallel_lines": [key for key in line_keys if key.startswith("parallel_line_")],
            "transversals": [key for key in line_keys if key.startswith("transversal")],
            "intersections": point_payload(rendered.intersections),
        },
        "relations": {
            "type": "parallel_line_angle_chain",
            "construction_kind": str(plan.construction_kind),
            "relation_id": str(plan.relation_id),
        },
        "execution": {
            "target_angle_label": str(plan.target_angle_label),
            "support_angles": [int(value) for value in plan.support_angles],
            "answer": int(plan.answer),
            "annotation_keys": list(rendered.annotation_roles),
            "annotation_type": str(annotation_artifacts.annotation_type),
            **dict(plan.witness),
        },
        "witness": dict(plan.witness),
        "query_params": {
            "construction_kind": str(plan.construction_kind),
            "relation_id": str(plan.relation_id),
            "relation_id_probabilities": dict(plan.relation_probabilities),
        },
    }


def symmetry_trace_common(
    *,
    plan: SymmetryAnglePlan,
    rendered: RenderedSymmetryAngleScene,
    annotation_artifacts: PixelAnnotationArtifacts,
) -> dict[str, Any]:
    """Build task-neutral trace fields for symmetry angle scenes."""

    return {
        "entities": {
            "construction_points": point_payload(rendered.construction_points),
            "construction_segments": geometry_json_ready(rendered.construction_segments, round_floats=False),
        },
        "relations": {
            "type": "symmetry_angle_chain",
            "construction_kind": str(plan.construction_kind),
            "relation_id": str(plan.relation_id),
            "target_role": str(plan.target_role),
        },
        "execution": {
            "target_angle_label": str(plan.target_angle_label),
            "support_angle": int(plan.support_angle),
            "answer": int(plan.answer),
            "annotation_keys": list(rendered.annotation_roles),
            "annotation_type": str(annotation_artifacts.annotation_type),
            **dict(plan.witness),
        },
        "witness": dict(plan.witness),
        "query_params": {
            "construction_kind": str(plan.construction_kind),
            "relation_id": str(plan.relation_id),
            "target_role": str(plan.target_role),
            "target_role_probabilities": dict(plan.target_role_probabilities),
        },
    }


__all__ = [
    "parallel_render_map",
    "parallel_trace_common",
    "point_payload",
    "polygon_render_map",
    "polygon_trace_common",
    "render_spec_base",
    "symmetry_render_map",
    "symmetry_trace_common",
]
