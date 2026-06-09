"""Count icons that moved in a requested direction between two icon panels."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import hash64
from ....core.task_group_config import get_task_group_defaults
from ...registry import register_task
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ..shared.icon_task_rendering import resolve_icon_render_params
from ..shared.paired_canvas_common import (
    PairedCanvasDefaults,
    PairedCanvasPayload,
    build_paired_prompt,
    choose_query_id,
    annotation_from_indices,
    make_icon_spec,
    paired_complexity,
    paired_task_output,
    render_paired_canvas,
    required_paired_prompt_defaults,
    resolve_icon_pool,
    resolve_paired_counts,
    sample_base_attributes,
    sample_palette,
    spawn_rng,
)


TASK_ID = "task_icons__paired_canvas__panel_movement_direction_count"
QUERY_IDS = ("moved_left_count", "moved_right_count", "moved_up_count", "moved_down_count")
_QUERY_TO_DIRECTION = {
    "moved_left_count": "left",
    "moved_right_count": "right",
    "moved_up_count": "up",
    "moved_down_count": "down",
}
_DEFAULTS = PairedCanvasDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


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


def _make_scene(*, instance_seed: int, params: Mapping[str, Any], render_params: Mapping[str, Any]) -> PairedCanvasPayload:
    rng = spawn_rng(int(instance_seed), "scene")
    query_id, query_probabilities = choose_query_id(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        query_ids=QUERY_IDS,
        weight_key="movement_direction_query_weights",
    )
    active_direction = _QUERY_TO_DIRECTION[str(query_id)]
    counting_params = dict(params)
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
        params=counting_params,
        gen_defaults=_GEN_DEFAULTS,
        defaults=_DEFAULTS,
    )
    pool = list(resolve_icon_pool(str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))))
    rng.shuffle(pool)
    palette = sample_palette(rng, render_params=render_params)
    rotation_candidates = tuple(
        int(value)
        for value in params.get(
            "rotation_candidates_degrees",
            group_default(_GEN_DEFAULTS, "rotation_candidates_degrees", _DEFAULTS.rotation_candidates_degrees),
        )
    )
    attrs = sample_base_attributes(
        rng,
        pool=pool,
        palette=palette,
        count=int(object_count),
        render_params=render_params,
        rotation_candidates=rotation_candidates,
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
    delta_min = float(params.get("movement_delta_min", group_default(_GEN_DEFAULTS, "movement_delta_min", _DEFAULTS.movement_delta_min)))
    delta_max = float(params.get("movement_delta_max", group_default(_GEN_DEFAULTS, "movement_delta_max", _DEFAULTS.movement_delta_max)))
    gap = float(params.get("min_center_gap_frac", group_default(_RENDER_DEFAULTS, "min_center_gap_frac", _DEFAULTS.min_center_gap_frac)))
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
    image, panel_geometry, left_icons_raw, right_icons_raw = render_paired_canvas(
        left_icons=left_specs,
        right_icons=right_specs,
        render_params=render_params,
    )
    left_icons = []
    right_icons = []
    for index, icon in enumerate(left_icons_raw):
        item = dict(icon)
        item["pair_index"] = int(index)
        item["movement_direction"] = str(directions[int(index)])
        left_icons.append(item)
    for index, icon in enumerate(right_icons_raw):
        item = dict(icon)
        item["pair_index"] = int(index)
        item["movement_direction"] = str(directions[int(index)])
        item["is_match"] = bool(int(index) in match_indices)
        right_icons.append(item)
    return PairedCanvasPayload(
        image=image,
        panel_geometry=panel_geometry,
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
    domain = "icons"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int):
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        payload = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                attempt_seed = int(hash64(int(instance_seed), self.task_id, int(attempt_index)))
                payload = _make_scene(instance_seed=attempt_seed, params=params, render_params=render_params)
                break
            except Exception as exc:
                last_error = exc
                continue
        if payload is None:
            raise RuntimeError(f"failed to generate {TASK_ID} instance") from last_error

        prompt_defaults = required_paired_prompt_defaults(_PROMPT_DEFAULTS, task_id=self.task_id)
        question_text = str(prompt_defaults[f"question_text_{payload.query_id}"])
        prompt_artifacts = build_paired_prompt(
            domain=self.domain,
            task_group=self.task_group,
            prompt_defaults=prompt_defaults,
            question_text=question_text,
            instance_seed=int(instance_seed),
        )
        annotation = annotation_from_indices(panel_icons=payload.right_icons, indices=payload.matching_right_indices)
        complexity = paired_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            object_count=int(payload.object_count),
            target_count=int(payload.target_count),
            object_count_min=int(group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min)),
            object_count_max=int(group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max)),
            left_icons=payload.left_icons,
            right_icons=payload.right_icons,
            render_params=render_params,
            rule_score=0.86,
        )
        return paired_task_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            payload=payload,
            prompt_artifacts=prompt_artifacts,
            prompt_defaults=prompt_defaults,
            render_params=render_params,
            annotation_panel="right",
            answer_value=int(payload.target_count),
            annotation_bboxes=annotation,
            complexity=complexity,
        )


__all__ = ["IconsRelationPanelMovementDirectionCountTask"]
