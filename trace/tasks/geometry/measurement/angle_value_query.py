"""Geometry angle measurement task with query-type variants and grounded evidence."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from PIL import Image, ImageDraw

from ....core.prompts import render_prompt
from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ..shared.value_queries import QueryOutcome, run_value_query, supported_value_query_types
from .background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from .noise_defaults import POST_IMAGE_NOISE_DEFAULTS


Point = Tuple[float, float]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for geometry angle value queries."""

    canvas_size: int = 768
    candidate_count: int = 7
    min_angle: int = 15
    max_angle: int = 165
    angle_step: int = 15
    target_x: int = 90
    ray_length: int = 84
    line_width: int = 4


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "measurement")
_RAW_GEN_DEFAULTS = _TASK_GROUP_DEFAULTS.get("generation", {}) if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {}
_RAW_RENDER_DEFAULTS = _TASK_GROUP_DEFAULTS.get("rendering", {}) if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {}
_RAW_PROMPT_DEFAULTS = _TASK_GROUP_DEFAULTS.get("prompt", {}) if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {}
_GEN_DEFAULTS: Mapping[str, Any] = _RAW_GEN_DEFAULTS if isinstance(_RAW_GEN_DEFAULTS, Mapping) else {}
_RENDER_DEFAULTS: Mapping[str, Any] = _RAW_RENDER_DEFAULTS if isinstance(_RAW_RENDER_DEFAULTS, Mapping) else {}
_PROMPT_DEFAULTS: Mapping[str, Any] = _RAW_PROMPT_DEFAULTS if isinstance(_RAW_PROMPT_DEFAULTS, Mapping) else {}


def _group_default(mapping: Mapping[str, Any], key: str, fallback: Any) -> Any:
    """Return task-group config value when present, otherwise fallback."""
    if key in mapping:
        return mapping.get(key)
    return fallback


def _deg_to_rad(angle_deg: float) -> float:
    """Convert degrees to radians."""
    return math.radians(float(angle_deg))


def _ray_endpoint(vertex: Point, angle_deg: float, length: float) -> Point:
    """Compute endpoint of a ray emitted from `vertex` at `angle_deg`."""
    rad = _deg_to_rad(angle_deg)
    x = float(vertex[0]) + float(length) * math.cos(rad)
    y = float(vertex[1]) + float(length) * math.sin(rad)
    return (x, y)


def _inside_canvas(point: Point, canvas_size: int, padding: float = 2.0) -> bool:
    """Check whether a point lies inside canvas bounds with padding."""
    x, y = point
    return padding <= x <= float(canvas_size) - padding and padding <= y <= float(canvas_size) - padding


def _distance_sq(a: Point, b: Point) -> float:
    """Return squared Euclidean distance between two points."""
    dx = float(a[0]) - float(b[0])
    dy = float(a[1]) - float(b[1])
    return dx * dx + dy * dy


def _sample_vertices(rng, *, count: int, canvas_size: int, margin: int, min_dist: float) -> List[Point]:
    """Sample separated vertex points for angle entities on the canvas."""
    vertices: List[Point] = []
    min_dist_sq = float(min_dist * min_dist)
    for _ in range(count):
        placed = False
        for _attempt in range(300):
            point = (
                float(rng.uniform(margin, canvas_size - margin)),
                float(rng.uniform(margin, canvas_size - margin)),
            )
            if all(_distance_sq(point, existing) >= min_dist_sq for existing in vertices):
                vertices.append(point)
                placed = True
                break
        if not placed:
            raise ValueError("failed to place non-overlapping angle vertices")
    return vertices


def _draw_angle(draw: ImageDraw.ImageDraw, *, vertex: Point, end1: Point, end2: Point, line_width: int) -> None:
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


def _complexity_score(*, candidate_count: int, min_gap: int, step: int) -> float:
    """Compute a task-local complexity proxy from candidate density/gap."""
    # Heuristic task-local complexity proxy for curriculum/debug only.
    density = min(1.0, float(candidate_count) / 9.0)
    gap_component = 1.0 - min(1.0, float(min_gap) / max(1.0, float(step * 2)))
    return max(0.0, min(1.0, 0.55 * density + 0.45 * gap_component))


@register_task
class GeometryAngleValueQueryTask:
    """Geometry angle measurement task with query variants and grounded vertex evidence."""

    task_id = "geometry_angle_value_query"
    domain = "geometry"
    task_group = "measurement"

    @staticmethod
    def supported_query_types(_params: Dict[str, Any] | None = None) -> List[str]:
        return list(supported_value_query_types())

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_type = str(params.get("query_type", "closest_to_x"))
        if query_type not in set(self.supported_query_types(params)):
            raise ValueError(f"unsupported query_type: {query_type}")

        canvas_size = int(params.get("canvas_size", _group_default(_RENDER_DEFAULTS, "canvas_size", _DEFAULTS.canvas_size)))
        candidate_count = int(params.get("candidate_count", _group_default(_GEN_DEFAULTS, "candidate_count", _DEFAULTS.candidate_count)))
        min_angle = int(params.get("min_angle", _group_default(_GEN_DEFAULTS, "min_angle", _DEFAULTS.min_angle)))
        max_angle = int(params.get("max_angle", _group_default(_GEN_DEFAULTS, "max_angle", _DEFAULTS.max_angle)))
        angle_step = int(params.get("angle_step", _group_default(_GEN_DEFAULTS, "angle_step", _DEFAULTS.angle_step)))
        target_x = int(params.get("target_x", _group_default(_GEN_DEFAULTS, "target_x", _DEFAULTS.target_x)))
        ray_length = int(params.get("ray_length", _group_default(_RENDER_DEFAULTS, "ray_length", _DEFAULTS.ray_length)))
        line_width = int(params.get("line_width", _group_default(_RENDER_DEFAULTS, "line_width", _DEFAULTS.line_width)))

        if candidate_count < 2:
            raise ValueError("candidate_count must be >= 2")

        candidates = list(range(min_angle, max_angle + 1, angle_step))
        if len(candidates) < candidate_count:
            raise ValueError("angle candidate space too small for requested candidate_count")

        if query_type == "median" and candidate_count % 2 == 0:
            raise ValueError("median query requires odd candidate_count")

        scene_rng = spawn_rng(instance_seed, "scene")
        entities: Dict[str, Dict[str, Any]] = {}
        outcome: QueryOutcome | None = None

        margin = ray_length + 40
        min_vertex_dist = float(max(70, int(ray_length * 1.6)))

        for _ in range(max_attempts):
            angle_values = scene_rng.sample(candidates, candidate_count)
            ids = [f"angle_{idx + 1}" for idx in range(candidate_count)]
            values_by_id = {entity_id: int(value) for entity_id, value in zip(ids, angle_values)}

            try:
                outcome = run_value_query(
                    values_by_id,
                    query_type=query_type,
                    target_x=(target_x if query_type in {"closest_to_x", "smallest_above_x", "largest_below_x"} else None),
                )
            except ValueError:
                continue

            try:
                vertices = _sample_vertices(
                    scene_rng,
                    count=candidate_count,
                    canvas_size=canvas_size,
                    margin=margin,
                    min_dist=min_vertex_dist,
                )
            except ValueError:
                continue

            local_entities: Dict[str, Dict[str, Any]] = {}
            valid_layout = True
            for entity_id, vertex in zip(ids, vertices):
                angle_value = int(values_by_id[entity_id])
                placed = False
                for _orient_attempt in range(120):
                    bisector = float(scene_rng.uniform(0.0, 360.0))
                    theta1 = bisector - (float(angle_value) / 2.0)
                    theta2 = bisector + (float(angle_value) / 2.0)
                    end1 = _ray_endpoint(vertex, theta1, ray_length)
                    end2 = _ray_endpoint(vertex, theta2, ray_length)
                    if _inside_canvas(end1, canvas_size) and _inside_canvas(end2, canvas_size):
                        local_entities[entity_id] = {
                            "value": angle_value,
                            "vertex": [float(vertex[0]), float(vertex[1])],
                            "ray_1": [float(end1[0]), float(end1[1])],
                            "ray_2": [float(end2[0]), float(end2[1])],
                        }
                        placed = True
                        break
                if not placed:
                    valid_layout = False
                    break

            if not valid_layout:
                continue

            entities = local_entities
            break

        if outcome is None or not entities:
            raise RuntimeError("failed to generate geometry_angle_value_query instance")

        image, background_meta = make_background_canvas(
            canvas_size=canvas_size,
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_color=(248, 248, 248),
        )
        draw = ImageDraw.Draw(image)
        for entity in entities.values():
            vertex = (float(entity["vertex"][0]), float(entity["vertex"][1]))
            end1 = (float(entity["ray_1"][0]), float(entity["ray_1"][1]))
            end2 = (float(entity["ray_2"][0]), float(entity["ray_2"][1]))
            _draw_angle(draw, vertex=vertex, end1=end1, end2=end2, line_width=line_width)

        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=instance_seed,
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        selected_vertices = [[float(entities[sid]["vertex"][0]), float(entities[sid]["vertex"][1])] for sid in outcome.selected_ids]
        if query_type == "difference_max_min":
            evidence_type = "point_path"
            evidence_value: Any = selected_vertices
            witness_symbolic = {"type": "id_path", "ids": list(outcome.selected_ids)}
        else:
            evidence_type = "point_set"
            evidence_value = [selected_vertices[0]]
            witness_symbolic = {"type": "id_set", "ids": [outcome.selected_ids[0]]}

        prompt_bundle_id = str(_group_default(_PROMPT_DEFAULTS, "bundle_id", "geometry_measurement_v1"))
        prompt_task_type_key = str(_group_default(_PROMPT_DEFAULTS, "task_type_key", "angle_measurement"))
        entity_plural = str(_group_default(_PROMPT_DEFAULTS, "entity_plural", "angles"))
        prompt_result = render_prompt(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=prompt_bundle_id,
            task_type_key=prompt_task_type_key,
            query_type=query_type,
            slots={
                "candidate_count": int(candidate_count),
                "entity_plural": entity_plural,
                "target_x": int(target_x),
            },
            instance_seed=instance_seed,
        )
        prompt = prompt_result.prompt

        values_by_id_sorted = {entity_id: int(entities[entity_id]["value"]) for entity_id in sorted(entities.keys())}
        sorted_values = sorted(values_by_id_sorted.values())
        min_gap = min(
            (sorted_values[idx + 1] - sorted_values[idx] for idx in range(len(sorted_values) - 1)),
            default=angle_step,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_angles",
                "entities": [
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
                ],
                "relations": {},
            },
            "query_spec": {
                "query_type": query_type,
                "template_id": "geometry_angle_value_query_v1",
                "prompt_variant": dict(prompt_result.metadata),
                "params": {
                    "target_x": int(target_x),
                    "candidate_count": int(candidate_count),
                    "angle_step": int(angle_step),
                },
            },
            "render_spec": {
                "canvas_size": int(canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
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
                },
            },
            "execution_trace": {
                "candidate_values_by_id": values_by_id_sorted,
                "selected_ids": list(outcome.selected_ids),
                "selected_values": list(outcome.selected_values),
                "answer_value": int(outcome.answer_value),
                "query_aux": dict(outcome.aux),
            },
            "witness_symbolic": witness_symbolic,
            "projected_evidence": {
                "point_set": [list(point) for point in selected_vertices],
                "point_path": [list(point) for point in selected_vertices],
            },
        }

        complexity = TaskComplexity(
            complexity_score=_complexity_score(candidate_count=candidate_count, min_gap=int(min_gap), step=angle_step),
            complexity_components={
                "candidate_count": int(candidate_count),
                "min_gap": int(min_gap),
                "query_type": query_type,
            },
        )

        return TaskOutput(
            prompt=prompt,
            answer_gt=TypedValue(type="integer", value=int(outcome.answer_value)),
            evidence_gt=TypedValue(type=evidence_type, value=evidence_value),
            image=image,
            image_id="img0",
            image_rel_path=f"images/{self.domain}/{self.task_id}/{int(instance_seed)}.png",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions={
                "dsl_spec_version": "v1",
                "template_version": "v1",
                "operator_bundle_version": "v1",
                "domain_capability_version": "v1",
                "renderer_version": "v1",
            },
            query_type=query_type,
        )
