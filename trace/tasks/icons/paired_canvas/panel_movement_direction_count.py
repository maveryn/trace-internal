"""Count icons that moved in a requested direction between two icon panels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    load_scene_generation_rendering_prompt_defaults,
)
from ...shared.fixed_query import select_task_query_id
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import build_prompt_query_spec
from ..shared.annotation import bbox_set_annotation
from ..shared.icon_task_rendering import resolve_icon_render_params

from .shared.annotations import bboxes_from_icon_indices
from .shared.defaults import SCENE_ID, PairedCanvasDefaults
from .shared.output import build_paired_canvas_trace_payload
from .shared.prompts import build_paired_prompt, required_paired_prompt_defaults
from .shared.rendering import render_paired_canvas
from .shared.sampling import (
    load_icon_pool_from_params,
    make_icon_spec,
    resolve_paired_counts,
    sample_base_attributes,
    sample_palette,
)


DOMAIN = "icons"
TASK_ID = "task_icons__paired_canvas__panel_movement_direction_count"
QUERY_IDS: Tuple[str, ...] = ("moved_left_count", "moved_right_count", "moved_up_count", "moved_down_count")
_QUERY_TO_DIRECTION = {
    "moved_left_count": "left",
    "moved_right_count": "right",
    "moved_up_count": "up",
    "moved_down_count": "down",
}

_DEFAULTS = PairedCanvasDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    DOMAIN,
    SCENE_ID,
    task_id=TASK_ID,
)


@dataclass(frozen=True)
class _MovementScene:
    """Task-owned symbolic payload for one movement-direction count instance."""

    image: Any
    panel_geometry: Dict[str, Any]
    left_icons: Tuple[Dict[str, Any], ...]
    right_icons: Tuple[Dict[str, Any], ...]
    matching_right_indices: Tuple[int, ...]
    matching_left_indices: Tuple[int, ...]
    target_count: int
    object_count: int
    distractor_count: int
    query_id: str
    query_probabilities: Dict[str, float]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    object_count_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    distractor_count_probabilities: Dict[str, float]
    question_format: str
    trace_relation: Dict[str, Any]


def _select_query(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float], Dict[str, Any]]:
    """Select and validate one semantic movement-direction query branch."""

    return select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=QUERY_IDS,
        default_query_id=QUERY_IDS[0],
        task_id=TASK_ID,
        namespace=f"{TASK_ID}.query",
    )


def _rotation_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    raw = params.get(
        "rotation_candidates_degrees",
        group_default(_GEN_DEFAULTS, "rotation_candidates_degrees", _DEFAULTS.rotation_candidates_degrees),
    )
    return tuple(int(value) for value in raw)


def _direction_delta(direction: str, delta: float) -> Tuple[float, float]:
    if direction == "left":
        return (-float(delta), 0.0)
    if direction == "right":
        return (float(delta), 0.0)
    if direction == "up":
        return (0.0, -float(delta))
    if direction == "down":
        return (0.0, float(delta))
    raise ValueError(f"unsupported direction: {direction}")


def _can_place_pair(
    *,
    left_pos: Tuple[float, float],
    right_pos: Tuple[float, float],
    placed: Sequence[Tuple[Tuple[float, float], Tuple[float, float]]],
    gap: float,
) -> bool:
    for other_left, other_right in placed:
        if ((left_pos[0] - other_left[0]) ** 2 + (left_pos[1] - other_left[1]) ** 2) ** 0.5 < float(gap):
            return False
        if ((right_pos[0] - other_right[0]) ** 2 + (right_pos[1] - other_right[1]) ** 2) ** 0.5 < float(gap):
            return False
    return True


def _sample_movement_positions(
    rng,
    *,
    directions: Sequence[str],
    delta_min: float,
    delta_max: float,
    gap: float,
) -> Tuple[Tuple[Tuple[float, float], Tuple[float, float]], ...]:
    """Sample paired normalized positions with the requested movement directions."""

    placed: list[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    for direction in directions:
        placed_one = False
        for _ in range(900):
            delta = float(rng.uniform(float(delta_min), float(delta_max)))
            dx, dy = _direction_delta(str(direction), delta)
            min_x = 0.14 + max(0.0, -dx)
            max_x = 0.86 - max(0.0, dx)
            min_y = 0.15 + max(0.0, -dy)
            max_y = 0.86 - max(0.0, dy)
            if min_x >= max_x or min_y >= max_y:
                continue
            left = (float(rng.uniform(min_x, max_x)), float(rng.uniform(min_y, max_y)))
            right = (float(left[0] + dx), float(left[1] + dy))
            jitter_axis = 0.025
            if direction in {"left", "right"}:
                jitter = float(rng.uniform(-jitter_axis, jitter_axis))
                left = (left[0], max(0.13, min(0.88, left[1] + jitter)))
                right = (right[0], max(0.13, min(0.88, right[1] + jitter)))
            else:
                jitter = float(rng.uniform(-jitter_axis, jitter_axis))
                left = (max(0.12, min(0.88, left[0] + jitter)), left[1])
                right = (max(0.12, min(0.88, right[0] + jitter)), right[1])
            if _can_place_pair(left_pos=left, right_pos=right, placed=placed, gap=float(gap)):
                placed.append((left, right))
                placed_one = True
                break
        if not placed_one:
            raise ValueError("failed to sample separated movement positions")
    return tuple(placed)


def _make_scene(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_params: Mapping[str, Any],
    query_id: str,
    query_probabilities: Mapping[str, float],
) -> _MovementScene:
    """Render a paired-panel scene with controlled movement directions."""

    rng = spawn_rng(int(instance_seed), "scene")
    active_direction = _QUERY_TO_DIRECTION[str(query_id)]
    (
        object_count,
        object_count_probabilities,
        target_count,
        target_count_probabilities,
        distractor_count,
        distractor_count_probabilities,
    ) = resolve_paired_counts(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        defaults=_DEFAULTS,
    )
    pool = list(load_icon_pool_from_params(params=params, gen_defaults=_GEN_DEFAULTS, defaults=_DEFAULTS))
    rng.shuffle(pool)
    palette = sample_palette(rng, render_params=render_params)
    attrs = sample_base_attributes(
        rng,
        pool=pool,
        palette=palette,
        count=int(object_count),
        render_params=render_params,
        rotation_candidates=_rotation_candidates(params),
    )
    match_indices = set(rng.sample(list(range(int(object_count))), int(target_count)))
    other_directions = [value for value in ("left", "right", "up", "down") if value != active_direction]
    directions = []
    distractor_index = 0
    for index in range(int(object_count)):
        if int(index) in match_indices:
            directions.append(str(active_direction))
        else:
            directions.append(str(other_directions[int(distractor_index) % len(other_directions)]))
            distractor_index += 1

    delta_min = float(
        params.get(
            "movement_delta_min",
            group_default(_GEN_DEFAULTS, "movement_delta_min", _DEFAULTS.movement_delta_min),
        )
    )
    delta_max = float(
        params.get(
            "movement_delta_max",
            group_default(_GEN_DEFAULTS, "movement_delta_max", _DEFAULTS.movement_delta_max),
        )
    )
    gap = float(
        params.get(
            "min_center_gap_frac",
            group_default(_RENDER_DEFAULTS, "min_center_gap_frac", _DEFAULTS.min_center_gap_frac),
        )
    )
    position_pairs = _sample_movement_positions(
        rng,
        directions=directions,
        delta_min=float(delta_min),
        delta_max=float(delta_max),
        gap=float(gap),
    )
    left_specs = []
    right_specs = []
    for index, (attr, pair) in enumerate(zip(attrs, position_pairs)):
        left_pos, right_pos = pair
        left_specs.append(
            make_icon_spec(
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}:left:{index}",
                render_params=render_params,
                instance_id=f"left_{index}",
                identity_id=str(attr["identity_id"]),
                icon_id=str(attr["icon_id"]),
                panel="left",
                position=left_pos,
                tint_rgb=tuple(attr["tint_rgb"]),
                size_px=int(attr["size_px"]),
                rotation_degrees=int(attr["rotation_degrees"]),
            )
        )
        right_specs.append(
            make_icon_spec(
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}:right:{index}",
                render_params=render_params,
                instance_id=f"right_{index}",
                identity_id=str(attr["identity_id"]),
                icon_id=str(attr["icon_id"]),
                panel="right",
                position=right_pos,
                tint_rgb=tuple(attr["tint_rgb"]),
                size_px=int(attr["size_px"]),
                rotation_degrees=int(attr["rotation_degrees"]),
            )
        )
    rendered = render_paired_canvas(left_icons=left_specs, right_icons=right_specs, render_params=render_params)
    left_icons = []
    right_icons = []
    for index, icon in enumerate(rendered.left_icons):
        item = dict(icon)
        item["pair_index"] = int(index)
        item["movement_direction"] = str(directions[int(index)])
        left_icons.append(item)
    for index, icon in enumerate(rendered.right_icons):
        item = dict(icon)
        item["pair_index"] = int(index)
        item["movement_direction"] = str(directions[int(index)])
        item["is_match"] = bool(int(index) in match_indices)
        right_icons.append(item)

    return _MovementScene(
        image=rendered.image,
        panel_geometry=dict(rendered.panel_geometry),
        left_icons=tuple(left_icons),
        right_icons=tuple(right_icons),
        matching_right_indices=tuple(sorted(int(index) for index in match_indices)),
        matching_left_indices=tuple(sorted(int(index) for index in match_indices)),
        target_count=int(target_count),
        object_count=int(object_count),
        distractor_count=int(distractor_count),
        query_id=str(query_id),
        query_probabilities=dict(query_probabilities),
        sampled_palette_rgb=tuple(palette),
        object_count_probabilities=dict(object_count_probabilities),
        target_count_probabilities=dict(target_count_probabilities),
        distractor_count_probabilities=dict(distractor_count_probabilities),
        question_format="count_icons_moved_in_requested_direction_from_left_to_right",
        trace_relation={
            "counting_target": str(query_id),
            "active_direction": str(active_direction),
            "movement_directions_by_pair": list(directions),
            "movement_delta_range": [float(delta_min), float(delta_max)],
        },
    )


@register_task
class IconsRelationPanelMovementDirectionCountTask:
    """Count icons that moved in the requested direction from Left to Right."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic paired-panel movement count instance."""

        query_id, query_probabilities, task_params = _select_query(int(instance_seed), params)
        render_params = resolve_icon_render_params(
            params=task_params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        scene = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                attempt_seed = int(hash64(int(instance_seed), TASK_ID, int(attempt_index)))
                scene = _make_scene(
                    instance_seed=attempt_seed,
                    params=task_params,
                    render_params=render_params,
                    query_id=str(query_id),
                    query_probabilities=query_probabilities,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene is None:
            raise RuntimeError(f"failed to generate {TASK_ID} instance") from last_error

        prompt_defaults = required_paired_prompt_defaults(
            _PROMPT_DEFAULTS,
            run_namespace=TASK_ID,
            extra_required_keys=(f"question_text_{scene.query_id}",),
        )
        annotation_bboxes = bboxes_from_icon_indices(
            panel_icons=scene.right_icons,
            indices=scene.matching_right_indices,
        )
        query_params = {
            "query_id": str(scene.query_id),
            "query_id_probabilities": dict(scene.query_probabilities),
            "object_count": int(scene.object_count),
            "object_count_probabilities": dict(scene.object_count_probabilities),
            "target_count": int(scene.target_count),
            "target_count_probabilities": dict(scene.target_count_probabilities),
            "distractor_count": int(scene.distractor_count),
            "distractor_count_probabilities": dict(scene.distractor_count_probabilities),
            "annotation_panel": "right",
        }
        execution_trace = {
            "scene_variant": SCENE_ID,
            "query_id": str(scene.query_id),
            "query_id_probabilities": dict(scene.query_probabilities),
            "question_format": str(scene.question_format),
            "object_count": int(scene.object_count),
            "object_count_probabilities": dict(scene.object_count_probabilities),
            "target_count": int(scene.target_count),
            "target_count_probabilities": dict(scene.target_count_probabilities),
            "distractor_count": int(scene.distractor_count),
            "distractor_count_probabilities": dict(scene.distractor_count_probabilities),
            "matching_right_indices": list(scene.matching_right_indices),
            "matching_left_indices": list(scene.matching_left_indices),
            "annotation_panel": "right",
            **dict(scene.trace_relation),
        }
        prompt_artifacts = build_paired_prompt(
            domain=self.domain,
            prompt_defaults=prompt_defaults,
            question_text=str(prompt_defaults[f"question_text_{scene.query_id}"]),
            instance_seed=int(instance_seed),
        )
        annotation_artifacts = bbox_set_annotation(annotation_bboxes)
        query_spec = build_prompt_query_spec(
            prompt_artifacts=prompt_artifacts,
            query_id=str(scene.query_id),
            params=query_params,
        )
        trace_payload = build_paired_canvas_trace_payload(
            scene_kind=f"icons_{SCENE_ID}",
            panel_geometry=scene.panel_geometry,
            left_icons=scene.left_icons,
            right_icons=scene.right_icons,
            relations=scene.trace_relation,
            query_spec=query_spec,
            render_params=render_params,
            sampled_palette_rgb=scene.sampled_palette_rgb,
            render_map_extra=None,
            execution_trace=execution_trace,
            witness_symbolic={
                "query_id": str(scene.query_id),
                "matching_right_indices": list(scene.matching_right_indices),
                "matching_left_indices": list(scene.matching_left_indices),
                "annotation_panel": "right",
            },
            annotation_payload=annotation_artifacts,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(scene.target_count)),
            annotation_gt=TypedValue(
                type=str(annotation_artifacts["annotation_type"]),
                value=[list(bbox) for bbox in annotation_artifacts["annotation_value"]],
            ),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(scene.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsRelationPanelMovementDirectionCountTask", "QUERY_IDS", "TASK_ID"]
