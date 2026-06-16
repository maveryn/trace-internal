"""Count rooms reachable from a visible player through open doors."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.scene_config import get_scene_defaults
from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support
from trace.tasks.illustrations.shared.canvas_profiles import resolve_profile_render_params
from trace.tasks.illustrations.shared.task_support import uniform_string_probability_map

from .shared.output import (
    keyed_point_set_map_projection,
    player_entity,
    room_point_map,
    rpg_house_reachable_room_count_render_map,
    rpg_house_render_spec,
    rpg_house_scene_ir,
)
from .shared.prompts import build_rpg_house_prompt_artifacts
from .shared.rendering import (
    DEFAULT_CANVAS_HEIGHT,
    DEFAULT_CANVAS_WIDTH,
    DEFAULT_TILE_PX,
    MAX_ROOM_COUNT,
    MIN_ROOM_COUNT,
    SCENE_ID,
    reachable_room_ids,
    render_rpg_house_scene,
)


TASK_ID = "task_illustrations__rpg_house__reachable_room_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "reachable_room_count"
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@dataclass(frozen=True)
class _ReachableCountSample:
    start_room_id: str
    reachable_room_ids: Tuple[str, ...]
    door_states: Mapping[str, str]
    reachable_count_probabilities: Mapping[str, float]
    start_room_probabilities: Mapping[str, float]


def _select_room_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> tuple[int, Mapping[str, float]]:
    return resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="room_count_support",
        explicit_key="room_count",
        fallback_support=tuple(range(MIN_ROOM_COUNT, MAX_ROOM_COUNT + 1)),
        namespace=f"{TASK_ID}:room_count",
        balanced_flag_key="balanced_sampling",
        use_instance_seed_cycle=True,
    )


def _select_reachable_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    max_count: int,
) -> tuple[int, Mapping[str, float]]:
    configured = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="reachable_room_count_support",
        fallback=tuple(range(0, MAX_ROOM_COUNT)),
    )
    support = tuple(value for value in configured if 0 <= int(value) <= int(max_count))
    if not support:
        raise ValueError(f"reachable_room_count_support has no feasible values for max_count={max_count}")
    explicit = params.get("reachable_room_count")
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"reachable_room_count must be in {support}, got {selected}")
        return selected, uniform_probability_map(support, selected=selected)
    if params.get("_sample_cursor") is not None:
        index = abs(int(params["_sample_cursor"]))
    else:
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:reachable_room_count",
        )
    selected = int(support[int(index) % len(support)])
    return selected, uniform_probability_map(support)


def _door_edges(doors: Sequence[Any]) -> dict[str, list[tuple[str, str]]]:
    edges: dict[str, list[tuple[str, str]]] = {}
    for door in doors:
        room_a = str(door.room_a_id)
        room_b = str(door.room_b_id)
        door_id = str(door.door_id)
        edges.setdefault(room_a, []).append((room_b, door_id))
        edges.setdefault(room_b, []).append((room_a, door_id))
    return {room_id: sorted(values) for room_id, values in edges.items()}


def _connected_component(edges: Mapping[str, Sequence[tuple[str, str]]], *, start_room_id: str) -> set[str]:
    seen = {str(start_room_id)}
    queue = [str(start_room_id)]
    while queue:
        room_id = queue.pop(0)
        for other_room_id, _door_id in edges.get(room_id, ()):
            if str(other_room_id) in seen:
                continue
            seen.add(str(other_room_id))
            queue.append(str(other_room_id))
    return seen


def _select_start_room(
    *,
    params: Mapping[str, Any],
    room_ids: Sequence[str],
    edges: Mapping[str, Sequence[tuple[str, str]]],
    target_count: int,
    instance_seed: int,
) -> tuple[str, Mapping[str, float]]:
    support = tuple(
        room_id
        for room_id in sorted(str(room_id) for room_id in room_ids)
        if len(_connected_component(edges, start_room_id=room_id)) >= int(target_count) + 1
    )
    if not support:
        raise ValueError(f"no start room can support reachable count {target_count}")
    explicit = params.get("start_room_id")
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(support):
            raise ValueError(f"start_room_id must be one of {support}")
        return selected, uniform_string_probability_map(support, selected=selected)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:start_room_id:{target_count}",
    )
    selected = support[int(index) % len(support)]
    return str(selected), uniform_string_probability_map(support)


def _grow_reachable_subset(
    *,
    edges: Mapping[str, Sequence[tuple[str, str]]],
    start_room_id: str,
    target_count: int,
    instance_seed: int,
) -> tuple[tuple[str, ...], frozenset[str]]:
    selected_rooms = {str(start_room_id)}
    open_door_ids: set[str] = set()
    rng = random.Random(hash64(int(instance_seed), f"{TASK_ID}:{start_room_id}:{target_count}"))
    while len(selected_rooms) < int(target_count) + 1:
        frontier = sorted(
            (str(room_id), str(other_room_id), str(door_id))
            for room_id in selected_rooms
            for other_room_id, door_id in edges.get(room_id, ())
            if str(other_room_id) not in selected_rooms
        )
        if not frontier:
            raise ValueError(f"could not grow reachable subset to count {target_count}")
        _room_id, other_room_id, door_id = frontier[int(rng.randrange(len(frontier)))]
        selected_rooms.add(str(other_room_id))
        open_door_ids.add(str(door_id))
    return tuple(sorted(room_id for room_id in selected_rooms if room_id != str(start_room_id))), frozenset(open_door_ids)


def _sample_reachable_room_count(
    *,
    params: Mapping[str, Any],
    rooms: Sequence[Any],
    doors: Sequence[Any],
    instance_seed: int,
) -> _ReachableCountSample:
    room_ids = tuple(str(room.room_id) for room in rooms)
    target_count, target_probabilities = _select_reachable_count(
        instance_seed=int(instance_seed),
        params=params,
        max_count=len(room_ids) - 1,
    )
    edges = _door_edges(doors)
    start_room_id, start_probabilities = _select_start_room(
        params=params,
        room_ids=room_ids,
        edges=edges,
        target_count=int(target_count),
        instance_seed=int(instance_seed),
    )
    reachable_ids, open_door_ids = _grow_reachable_subset(
        edges=edges,
        start_room_id=start_room_id,
        target_count=int(target_count),
        instance_seed=int(instance_seed),
    )
    door_states = {str(door.door_id): ("open" if str(door.door_id) in open_door_ids else "closed") for door in doors}
    return _ReachableCountSample(
        start_room_id=str(start_room_id),
        reachable_room_ids=tuple(reachable_ids),
        door_states=door_states,
        reachable_count_probabilities=dict(target_probabilities),
        start_room_probabilities=dict(start_probabilities),
    )


@register_task
class IllustrationsRpgHouseReachableRoomCountTask:
    """Count rooms reachable from the player's room through open doors."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate a player-reachability count while keeping graph construction exact."""

        resolved_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SINGLE_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}:query",
        )
        room_count, room_count_probabilities = _select_room_count(
            instance_seed=int(instance_seed),
            params=task_params,
        )
        render_params = resolve_profile_render_params(
            task_params,
            _RENDER_DEFAULTS,
            prefix="rpg_house",
            fallback_width=DEFAULT_CANVAS_WIDTH,
            fallback_height=DEFAULT_CANVAS_HEIGHT,
            fallback_scale=1,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:canvas_profile",
        )
        required_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_rpg_house_reachable_room_count",
                "annotation_hint_rpg_house_reachable_room_count",
                "json_example_rpg_house_reachable_room_count",
                "json_example_answer_only_rpg_house_reachable_room_count",
            ],
            context="prompt defaults for RPG house reachable-room count task",
        )

        scene = None
        sample: _ReachableCountSample | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            render_seed = hash64(int(instance_seed), f"{TASK_ID}:render", int(attempt))
            try:
                probe_scene = render_rpg_house_scene(
                    render_seed,
                    width=int(render_params["canvas_width"]),
                    height=int(render_params["canvas_height"]),
                    tile_px=int(task_params.get("tile_px", group_default(_RENDER_DEFAULTS, "rpg_house_tile_px", DEFAULT_TILE_PX))),
                    room_count=int(room_count),
                    render_metadata={
                        "canvas_profile": str(render_params.get("canvas_profile", "")),
                        "canvas_profile_size": list(render_params.get("canvas_profile_size", [])),
                        "canvas_profile_probabilities": dict(render_params.get("canvas_profile_probabilities", {})),
                    },
                )
                sample = _sample_reachable_room_count(
                    params=task_params,
                    rooms=probe_scene.rooms,
                    doors=probe_scene.doors,
                    instance_seed=int(hash64(int(instance_seed), "sample", int(attempt))),
                )
                scene = render_rpg_house_scene(
                    render_seed,
                    width=int(render_params["canvas_width"]),
                    height=int(render_params["canvas_height"]),
                    tile_px=int(task_params.get("tile_px", group_default(_RENDER_DEFAULTS, "rpg_house_tile_px", DEFAULT_TILE_PX))),
                    room_count=int(room_count),
                    player_room_id=sample.start_room_id,
                    door_states=sample.door_states,
                    render_metadata={
                        "canvas_profile": str(render_params.get("canvas_profile", "")),
                        "canvas_profile_size": list(render_params.get("canvas_profile_size", [])),
                        "canvas_profile_probabilities": dict(render_params.get("canvas_profile_probabilities", {})),
                    },
                )
                actual_reachable_ids = tuple(
                    room_id
                    for room_id in reachable_room_ids(scene.doors, start_room_id=sample.start_room_id)
                    if room_id != sample.start_room_id
                )
                if tuple(sorted(actual_reachable_ids)) == tuple(sorted(sample.reachable_room_ids)):
                    break
                last_error = RuntimeError(
                    f"reachable-room count mismatch: expected {sample.reachable_room_ids}, got {actual_reachable_ids}"
                )
                scene = None
            except Exception as exc:  # pragma: no cover - retry path
                last_error = exc
                scene = None
        if scene is None:
            raise RuntimeError(f"could not generate RPG house reachable-room count: {last_error}") from last_error
        if sample is None:
            raise RuntimeError("could not sample RPG house reachable-room count")

        room_points = room_point_map(scene)
        player = player_entity(scene)
        if player is None:
            raise RuntimeError("reachable-room count scene did not render a player")
        annotation_value = {
            "player": [[round(float(player.point_xy[0]), 3), round(float(player.point_xy[1]), 3)]],
            "reachable_rooms": [room_points[room_id] for room_id in sample.reachable_room_ids],
        }
        answer = int(len(sample.reachable_room_ids))
        prompt_artifacts = build_rpg_house_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=required_defaults,
            prompt_query_key=PROMPT_QUERY_KEY,
            slots={
                "json_output_contract": str(required_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(required_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(required_defaults["answer_hint_rpg_house_reachable_room_count"]),
                "annotation_hint": str(required_defaults["annotation_hint_rpg_house_reachable_room_count"]),
                "json_example": str(required_defaults["json_example_rpg_house_reachable_room_count"]),
                "json_example_answer_only": str(required_defaults["json_example_answer_only_rpg_house_reachable_room_count"]),
            },
            instance_seed=int(instance_seed),
        )
        query_params = {
            "query_id": str(resolved_query_id),
            "prompt_query_key": PROMPT_QUERY_KEY,
            "query_id_probabilities": dict(query_probabilities),
            "room_count": int(room_count),
            "room_count_probabilities": dict(room_count_probabilities),
            "start_room_id": sample.start_room_id,
            "player_room_id": sample.start_room_id,
            "player_room": sample.start_room_id,
            "reachable_room_ids": list(sample.reachable_room_ids),
            "reachable_room_count": int(answer),
            "reachable_room_count_probabilities": dict(sample.reachable_count_probabilities),
            "player_room_probabilities": dict(sample.start_room_probabilities),
            "door_states": dict(sample.door_states),
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
                    "prompt_query_key": PROMPT_QUERY_KEY,
                    "player_room_id": sample.start_room_id,
                    "reachable_room_ids": list(sample.reachable_room_ids),
                    "answer": int(answer),
                },
            ),
            "query_spec": {
                "task_id": TASK_ID,
                "query_id": str(resolved_query_id),
                "prompt_query_key": PROMPT_QUERY_KEY,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": query_params,
            },
            "render_spec": rpg_house_render_spec(scene, scene_id=SCENE_ID),
            "render_map": rpg_house_reachable_room_count_render_map(
                scene=scene,
                player_room_id=sample.start_room_id,
                reachable_room_ids=sample.reachable_room_ids,
            ),
            "execution_trace": {
                "query_id": str(resolved_query_id),
                "prompt_query_key": PROMPT_QUERY_KEY,
                "scene_id": SCENE_ID,
                "player_room_id": sample.start_room_id,
                "reachable_room_ids": list(sample.reachable_room_ids),
                "reachable_room_count": int(answer),
                "door_states": dict(sample.door_states),
                "renderer": dict(scene.trace),
            },
            "witness_symbolic": {
                "player_room_id": sample.start_room_id,
                "reachable_room_ids": list(sample.reachable_room_ids),
                "reachable_room_count": int(answer),
            },
            "projected_annotation": keyed_point_set_map_projection(annotation_value),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=answer),
            annotation_gt=TypedValue(type="keyed_point_set_map", value=annotation_value),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(resolved_query_id),
        )


__all__ = [
    "IllustrationsRpgHouseReachableRoomCountTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
