"""Count open or closed doors in a top-down RPG house layout."""

from __future__ import annotations

import random
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.illustrations.shared.rpg_tile_profiles import resolve_rpg_tile_render_params

from .shared.output import (
    door_point_map,
    point_set_projection,
    rpg_house_door_state_count_render_map,
    rpg_house_render_spec,
    rpg_house_scene_ir,
)
from .shared.prompts import build_rpg_house_prompt_artifacts
from .shared.rendering import (
    DEFAULT_TILE_PX,
    MAX_ROOM_COUNT,
    MIN_ROOM_COUNT,
    SCENE_ID,
    render_rpg_house_profile_scene,
)
from .shared.sampling import select_count_from_support, select_feasible_count_from_support


TASK_ID = "task_illustrations__rpg_house__door_state_count"
OPEN_DOOR_COUNT_QUERY_ID = "open_door_count"
CLOSED_DOOR_COUNT_QUERY_ID = "closed_door_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (OPEN_DOOR_COUNT_QUERY_ID, CLOSED_DOOR_COUNT_QUERY_ID)
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _select_target_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    total_doors: int,
) -> tuple[int, Mapping[str, float]]:
    return select_feasible_count_from_support(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="door_state_count_support",
        explicit_key="door_state_count",
        fallback_support=tuple(range(1, MAX_ROOM_COUNT + 1)),
        feasible=lambda value: 1 <= int(value) <= max(1, int(total_doors) - 1),
        namespace=f"{TASK_ID}:door_state_count",
        empty_context=f"total_doors={total_doors}",
    )


def _door_states_for_query(
    *,
    doors: Sequence[Any],
    query_id: str,
    target_count: int,
    instance_seed: int,
) -> tuple[str, dict[str, str], tuple[str, ...]]:
    target_state = "open" if str(query_id) == OPEN_DOOR_COUNT_QUERY_ID else "closed"
    opposite_state = "closed" if target_state == "open" else "open"
    door_ids = sorted(str(door.door_id) for door in doors)
    if int(target_count) >= len(door_ids):
        raise ValueError("target_count must leave at least one opposite-state door")
    rng = random.Random(hash64(int(instance_seed), f"{TASK_ID}:{query_id}:{target_count}:{len(door_ids)}"))
    matching_ids = tuple(sorted(rng.sample(door_ids, int(target_count))))
    matching_set = set(matching_ids)
    door_states = {door_id: (target_state if door_id in matching_set else opposite_state) for door_id in door_ids}
    return target_state, door_states, matching_ids


@register_task
class IllustrationsRpgHouseDoorStateCountTask:
    """Count visible doors in the requested open/closed state."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one open-door or closed-door count instance."""

        resolved_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=OPEN_DOOR_COUNT_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}:query",
        )
        room_count, room_count_probabilities = select_count_from_support(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="room_count_support",
            explicit_key="room_count",
            fallback_support=tuple(range(MIN_ROOM_COUNT, MAX_ROOM_COUNT + 1)),
            namespace=f"{TASK_ID}:room_count",
        )
        render_params = resolve_rpg_tile_render_params(
            task_params,
            _RENDER_DEFAULTS,
            tile_px_key="rpg_house_tile_px",
            fallback_tile_px=DEFAULT_TILE_PX,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:canvas_profile",
        )
        tile_px = int(render_params["tile_px"])
        required_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_rpg_house_door_state_count",
                "annotation_hint_rpg_house_door_state_count",
                "json_example_rpg_house_door_state_count",
                "json_example_answer_only_rpg_house_door_state_count",
            ],
            context="prompt defaults for RPG house door-state count task",
        )

        scene = None
        target_state = ""
        matching_door_ids: tuple[str, ...] = ()
        target_count_probabilities: Mapping[str, float] = {}
        door_states: Mapping[str, str] = {}
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            render_seed = hash64(int(instance_seed), f"{TASK_ID}:render", int(attempt))
            try:
                probe_scene = render_rpg_house_profile_scene(
                    render_seed,
                    render_params=render_params,
                    tile_px=tile_px,
                    room_count=int(room_count),
                )
                target_count, target_count_probabilities = _select_target_count(
                    instance_seed=int(hash64(int(instance_seed), "target_count", int(attempt))),
                    params=task_params,
                    total_doors=len(probe_scene.doors),
                )
                target_state, door_states, matching_door_ids = _door_states_for_query(
                    doors=probe_scene.doors,
                    query_id=str(resolved_query_id),
                    target_count=int(target_count),
                    instance_seed=int(hash64(int(instance_seed), "door_states", int(attempt))),
                )
                scene = render_rpg_house_profile_scene(
                    render_seed,
                    render_params=render_params,
                    tile_px=tile_px,
                    room_count=int(room_count),
                    door_states=door_states,
                )
                actual_matching = tuple(sorted(str(door.door_id) for door in scene.doors if str(door.state) == str(target_state)))
                if actual_matching == matching_door_ids:
                    break
                last_error = RuntimeError(
                    f"door-state count mismatch: expected {matching_door_ids}, got {actual_matching}"
                )
                scene = None
            except Exception as exc:  # pragma: no cover - retry path
                last_error = exc
                scene = None
        if scene is None:
            raise RuntimeError(f"could not generate RPG house door-state count: {last_error}") from last_error

        door_points = door_point_map(scene)
        annotation_value = [door_points[door_id] for door_id in matching_door_ids]
        answer = int(len(matching_door_ids))
        prompt_artifacts = build_rpg_house_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=required_defaults,
            prompt_query_key=str(resolved_query_id),
            slots={
                "json_output_contract": str(required_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(required_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(required_defaults["answer_hint_rpg_house_door_state_count"]),
                "annotation_hint": str(required_defaults["annotation_hint_rpg_house_door_state_count"]),
                "json_example": str(required_defaults["json_example_rpg_house_door_state_count"]),
                "json_example_answer_only": str(required_defaults["json_example_answer_only_rpg_house_door_state_count"]),
            },
            instance_seed=int(instance_seed),
        )
        query_params = {
            "query_id": str(resolved_query_id),
            "prompt_query_key": str(resolved_query_id),
            "query_id_probabilities": dict(query_probabilities),
            "target_door_state": str(target_state),
            "matching_door_ids": list(matching_door_ids),
            "door_state_count": int(answer),
            "door_state_count_probabilities": dict(target_count_probabilities),
            "room_count": int(room_count),
            "room_count_probabilities": dict(room_count_probabilities),
            "door_states": dict(door_states),
            "canvas_profile": str(render_params.get("canvas_profile", "")),
            "canvas_profile_probabilities": dict(render_params.get("canvas_profile_probabilities", {})),
        }
        trace_payload = {
            "scene_ir": rpg_house_scene_ir(
                domain=self.domain,
                scene_id=SCENE_ID,
                scene=scene,
                relations={
                    "query_id": str(resolved_query_id),
                    "prompt_query_key": str(resolved_query_id),
                    "target_door_state": str(target_state),
                    "matching_door_ids": list(matching_door_ids),
                    "answer": int(answer),
                },
            ),
            "query_spec": {
                "task_id": TASK_ID,
                "query_id": str(resolved_query_id),
                "prompt_query_key": str(resolved_query_id),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": query_params,
            },
            "render_spec": rpg_house_render_spec(scene, scene_id=SCENE_ID),
            "render_map": rpg_house_door_state_count_render_map(
                scene=scene,
                target_state=str(target_state),
                matching_door_ids=matching_door_ids,
            ),
            "execution_trace": {
                "query_id": str(resolved_query_id),
                "prompt_query_key": str(resolved_query_id),
                "scene_id": SCENE_ID,
                "target_door_state": str(target_state),
                "matching_door_ids": list(matching_door_ids),
                "door_state_count": int(answer),
                "door_states": dict(door_states),
                "renderer": dict(scene.trace),
            },
            "witness_symbolic": {
                "target_door_state": str(target_state),
                "matching_door_ids": list(matching_door_ids),
                "door_state_count": int(answer),
            },
            "projected_annotation": point_set_projection(annotation_value),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=answer),
            annotation_gt=TypedValue(type="point_set", value=annotation_value),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(resolved_query_id),
        )


__all__ = [
    "CLOSED_DOOR_COUNT_QUERY_ID",
    "IllustrationsRpgHouseDoorStateCountTask",
    "OPEN_DOOR_COUNT_QUERY_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
