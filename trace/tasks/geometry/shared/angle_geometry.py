"""Shared angle-geometry primitives and layout samplers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ...shared.geometry_primitives import Point, point_inside_square_canvas
from ...shared.layout_constraints import mapping_entities_have_min_clearance
from .graph_paper import sample_vertices_on_graph_paper
from .graph_rendering import pixel_point_to_graph_units

_AXIS_DIRECTIONS_DEG: Tuple[float, ...] = (0.0, 90.0, 180.0, 270.0)
_ANGLE_POINT_KEYS: Tuple[str, ...] = ("vertex", "ray_1", "ray_2")
_ANGLE_SEGMENT_KEYS: Tuple[Tuple[str, str], ...] = (("vertex", "ray_1"), ("vertex", "ray_2"))


@dataclass(frozen=True)
class _AngleEvidenceArtifacts:
    """Resolved evidence/witness payloads for one sampled angle query outcome."""

    evidence_type: str
    evidence_value: Any
    witness_symbolic: Dict[str, Any]
    selected_vertices: List[List[float]]
    selected_vertices_graph: List[List[int]]
    projected_evidence: Dict[str, Any]


def _ray_endpoint(vertex: Point, angle_deg: float, length: float) -> Point:
    """Compute endpoint of a ray emitted from `vertex` at `angle_deg`."""
    radians = math.radians(float(angle_deg))
    x = float(vertex[0]) + float(length) * math.cos(radians)
    y = float(vertex[1]) + float(length) * math.sin(radians)
    return (x, y)


def _sample_axis_anchored_rays(
    rng,
    *,
    vertex: Point,
    angle_value: int,
    ray_length: int,
    canvas_size: int,
) -> Tuple[Point, Point] | None:
    """Sample ray endpoints while forcing one angle arm to be axis-aligned."""
    for _orient_attempt in range(120):
        axis_theta = float(rng.choice(_AXIS_DIRECTIONS_DEG))
        signed_delta = float(angle_value) if rng.random() < 0.5 else -float(angle_value)
        axis_is_first = rng.random() < 0.5

        theta_axis = axis_theta
        theta_other = axis_theta + signed_delta
        theta1 = theta_axis if axis_is_first else theta_other
        theta2 = theta_other if axis_is_first else theta_axis

        end1 = _ray_endpoint(vertex, theta1, ray_length)
        end2 = _ray_endpoint(vertex, theta2, ray_length)
        if point_inside_square_canvas(end1, canvas_size=canvas_size) and point_inside_square_canvas(
            end2,
            canvas_size=canvas_size,
        ):
            return end1, end2
    return None


def draw_angle(draw: ImageDraw.ImageDraw, *, vertex: Point, end1: Point, end2: Point, line_width: int) -> None:
    """Draw one angle primitive (two rays + highlighted vertex marker)."""
    vx, vy = vertex
    draw.line([vx, vy, end1[0], end1[1]], fill=(22, 22, 22), width=line_width)
    draw.line([vx, vy, end2[0], end2[1]], fill=(22, 22, 22), width=line_width)
    radius = max(3, line_width)
    draw.ellipse(
        [vx - radius, vy - radius, vx + radius, vy + radius],
        fill=(35, 89, 154),
        outline=(18, 18, 18),
        width=1,
    )


def sample_angle_entities_layout(
    rng,
    *,
    ids: Sequence[str],
    values_by_id: Mapping[str, int],
    canvas_size: int,
    margin: int,
    min_vertex_dist: float,
    graph_spacing: int,
    ray_length: int,
    min_layout_clearance: float,
) -> Dict[str, Dict[str, Any]] | None:
    """Sample one non-overlapping angle layout keyed by stable entity ids."""
    try:
        vertices = sample_vertices_on_graph_paper(
            rng,
            count=len(ids),
            canvas_size=int(canvas_size),
            margin=int(margin),
            min_dist=float(min_vertex_dist),
            spacing=int(graph_spacing),
        )
    except ValueError:
        return None

    entities: Dict[str, Dict[str, Any]] = {}
    for entity_id, vertex in zip(ids, vertices):
        angle_value = int(values_by_id[str(entity_id)])
        ray_pair = _sample_axis_anchored_rays(
            rng,
            vertex=vertex,
            angle_value=angle_value,
            ray_length=int(ray_length),
            canvas_size=int(canvas_size),
        )
        if ray_pair is None:
            return None
        end1, end2 = ray_pair
        entities[str(entity_id)] = {
            "value": int(angle_value),
            "vertex": [float(vertex[0]), float(vertex[1])],
            "ray_1": [float(end1[0]), float(end1[1])],
            "ray_2": [float(end2[0]), float(end2[1])],
        }
        if len(entities) > 1 and (
            not mapping_entities_have_min_clearance(
                entities,
                point_keys=_ANGLE_POINT_KEYS,
                segment_keys=_ANGLE_SEGMENT_KEYS,
                min_clearance=float(min_layout_clearance),
            )
        ):
            return None
    return entities


def build_angle_scene_entities(entities: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Build `scene_ir.entities` entries for angle scenes."""
    return [
        {
            "entity_id": entity_id,
            "entity_type": "angle",
            "attrs": {
                "angle_degrees": int(entity["value"]),
                "vertex": list(entity["vertex"]),
                "ray_1": list(entity["ray_1"]),
                "ray_2": list(entity["ray_2"]),
            },
        }
        for entity_id, entity in sorted(entities.items())
    ]


def build_angle_render_anchors(entities: Mapping[str, Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build deterministic render-map anchor payloads for angle entities."""
    return {
        entity_id: {
            "point": list(entity["vertex"]),
            "polyline": [
                list(entity["vertex"]),
                list(entity["ray_1"]),
                list(entity["vertex"]),
                list(entity["ray_2"]),
            ],
            "coord_space": "pixel",
        }
        for entity_id, entity in sorted(entities.items())
    }


def build_angle_evidence_artifacts(
    *,
    query_type: str,
    selected_ids: Sequence[str],
    entities: Mapping[str, Mapping[str, Any]],
    graph_origin: Point,
    graph_spacing: int,
) -> _AngleEvidenceArtifacts:
    """Resolve evidence/witness payloads from selected angle ids and graph frame."""
    ids = [str(entity_id) for entity_id in selected_ids]
    if not ids:
        raise ValueError("selected_ids must be non-empty")

    selected_vertices = [
        [float(entities[entity_id]["vertex"][0]), float(entities[entity_id]["vertex"][1])]
        for entity_id in ids
    ]
    selected_vertices_graph = [
        pixel_point_to_graph_units(
            (float(point[0]), float(point[1])),
            origin=(float(graph_origin[0]), float(graph_origin[1])),
            spacing=int(graph_spacing),
        )
        for point in selected_vertices
    ]

    if str(query_type) == "difference_max_min":
        evidence_type = "grid_point_path"
        evidence_value: Any = [list(point) for point in selected_vertices_graph]
        witness_symbolic = {"type": "id_path", "ids": list(ids)}
    else:
        evidence_type = "grid_point_set"
        evidence_value = [list(selected_vertices_graph[0])]
        witness_symbolic = {"type": "id_set", "ids": [ids[0]]}

    projected_evidence = {
        "point_set": [list(point) for point in selected_vertices],
        "point_path": [list(point) for point in selected_vertices],
        "grid_point_set": [list(point) for point in selected_vertices_graph],
        "grid_point_path": [list(point) for point in selected_vertices_graph],
    }

    return _AngleEvidenceArtifacts(
        evidence_type=evidence_type,
        evidence_value=evidence_value,
        witness_symbolic=witness_symbolic,
        selected_vertices=selected_vertices,
        selected_vertices_graph=selected_vertices_graph,
        projected_evidence=projected_evidence,
    )
