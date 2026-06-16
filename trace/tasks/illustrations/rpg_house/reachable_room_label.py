"""Choose the lettered RPG house room reachable through open doorways."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import hash64
from trace.core.scene_config import get_scene_defaults
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.illustrations.shared.canvas_profiles import resolve_profile_render_params
from trace.tasks.illustrations.shared.option_rendering import sample_visual_label_font_trace
from trace.tasks.illustrations.shared.task_support import uniform_string_probability_map

from .shared.output import (
    bbox_projection,
    room_bbox_map,
    rpg_house_reachability_render_map,
    rpg_house_render_spec,
    rpg_house_scene_ir,
)
from .shared.prompts import build_rpg_house_prompt_artifacts
from .shared.rendering import (
    DEFAULT_CANVAS_HEIGHT,
    DEFAULT_CANVAS_WIDTH,
    DEFAULT_TILE_PX,
    SCENE_ID,
    reachable_room_ids,
    render_rpg_house_scene,
)


TASK_ID = "task_illustrations__rpg_house__reachable_room_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "reachable_room_label"
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D")
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@dataclass(frozen=True)
class _ReachableRoomSample:
    start_room_id: str
    answer_room_id: str
    candidate_room_ids: Tuple[str, ...]
    room_labels: Mapping[str, str]
    door_states: Mapping[str, str]
    start_room_probabilities: Mapping[str, float]
    answer_room_probabilities: Mapping[str, float]
    answer_label_probabilities: Mapping[str, float]


def _select_string_from_support(
    *,
    params: Mapping[str, Any],
    support: Tuple[str, ...],
    explicit_key: str,
    namespace: str,
    instance_seed: int,
) -> tuple[str, Mapping[str, float]]:
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = str(explicit)
        if value not in set(support):
            raise ValueError(f"{explicit_key} must be one of {support}")
        return value, uniform_string_probability_map(support, selected=value)
    if params.get("_sample_cursor") is not None:
        index = abs(int(params["_sample_cursor"]))
    else:
        index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    value = support[int(index) % len(support)]
    return str(value), uniform_string_probability_map(support)


def _sample_reachability_query(
    *,
    params: Mapping[str, Any],
    rooms: Tuple[Any, ...],
    doors: Tuple[Any, ...],
    instance_seed: int,
) -> _ReachableRoomSample:
    """Resolve one start room and one directly reachable candidate room."""

    room_ids = tuple(str(room.room_id) for room in rooms)
    neighbor_map: dict[str, set[str]] = {room_id: set() for room_id in room_ids}
    door_by_pair: dict[tuple[str, str], str] = {}
    for door in doors:
        room_a = str(door.room_a_id)
        room_b = str(door.room_b_id)
        neighbor_map.setdefault(room_a, set()).add(room_b)
        neighbor_map.setdefault(room_b, set()).add(room_a)
        door_by_pair[tuple(sorted((room_a, room_b)))] = str(door.door_id)
    start_support = tuple(room_id for room_id in room_ids if neighbor_map.get(room_id))
    start_room_id, start_probabilities = _select_string_from_support(
        params=params,
        support=start_support,
        explicit_key="start_room_id",
        namespace=f"{TASK_ID}:start_room_id",
        instance_seed=int(instance_seed),
    )
    candidate_room_ids = tuple(room_id for room_id in room_ids if room_id != start_room_id)
    answer_support = tuple(sorted(neighbor_map[str(start_room_id)]))
    answer_room_id, answer_probabilities = _select_string_from_support(
        params=params,
        support=answer_support,
        explicit_key="answer_room_id",
        namespace=f"{TASK_ID}:answer_room_id",
        instance_seed=int(instance_seed),
    )
    if len(candidate_room_ids) > len(OPTION_LABELS):
        raise ValueError(f"reachable-room label task supports at most {len(OPTION_LABELS)} candidates")
    answer_label_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:answer_label",
    ) % len(candidate_room_ids)
    ordered_candidate_room_ids = [room_id for room_id in candidate_room_ids if room_id != answer_room_id]
    ordered_candidate_room_ids.insert(int(answer_label_index), str(answer_room_id))
    candidate_room_ids = tuple(ordered_candidate_room_ids)
    room_labels = {room_id: OPTION_LABELS[index] for index, room_id in enumerate(candidate_room_ids)}
    door_states = {str(door.door_id): "closed" for door in doors}
    selected_door_id = door_by_pair[tuple(sorted((str(start_room_id), str(answer_room_id))))]
    door_states[str(selected_door_id)] = "open"
    answer_label = str(room_labels[str(answer_room_id)])
    return _ReachableRoomSample(
        start_room_id=str(start_room_id),
        answer_room_id=str(answer_room_id),
        candidate_room_ids=tuple(str(value) for value in candidate_room_ids),
        room_labels=room_labels,
        door_states=door_states,
        start_room_probabilities=dict(start_probabilities),
        answer_room_probabilities=dict(answer_probabilities),
        answer_label_probabilities=uniform_string_probability_map(OPTION_LABELS[: len(candidate_room_ids)], selected=answer_label),
    )


@register_task
class IllustrationsRpgHouseReachableRoomLabelTask:
    """Select the lettered room reachable from a marked start room."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one reachability instance and bind the single reachable candidate."""

        resolved_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SINGLE_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}:query",
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
                "answer_hint_rpg_house_reachable_room",
                "annotation_hint_rpg_house_reachable_room",
                "json_example_rpg_house_reachable_room",
                "json_example_answer_only_rpg_house_reachable_room",
            ],
            context="prompt defaults for RPG house reachable-room label",
        )
        font_trace = sample_visual_label_font_trace(
            namespace_prefix=TASK_ID,
            instance_seed=int(instance_seed),
            params=task_params,
            namespace_suffix="room_labels",
            explicit_key="label_font_family",
            weights_key="label_font_family_weights",
        )

        scene = None
        reachable_candidates: tuple[str, ...] = ()
        last_error: Exception | None = None
        sample: _ReachableRoomSample | None = None
        for attempt in range(max(1, int(max_attempts))):
            render_seed = hash64(int(instance_seed), f"{TASK_ID}:render", int(attempt))
            room_count = int(
                task_params.get(
                    "room_count",
                    group_default(_RENDER_DEFAULTS, "rpg_house_reachable_room_count", 5),
                )
            )
            try:
                probe_scene = render_rpg_house_scene(
                    render_seed,
                    width=int(render_params["canvas_width"]),
                    height=int(render_params["canvas_height"]),
                    tile_px=int(task_params.get("tile_px", group_default(_RENDER_DEFAULTS, "rpg_house_tile_px", DEFAULT_TILE_PX))),
                    room_count=room_count,
                    render_metadata={
                        "canvas_profile": str(render_params.get("canvas_profile", "")),
                        "canvas_profile_size": list(render_params.get("canvas_profile_size", [])),
                        "canvas_profile_probabilities": dict(render_params.get("canvas_profile_probabilities", {})),
                    },
                )
                sample = _sample_reachability_query(
                    params=task_params,
                    rooms=probe_scene.rooms,
                    doors=probe_scene.doors,
                    instance_seed=int(instance_seed),
                )
                scene = render_rpg_house_scene(
                    render_seed,
                    width=int(render_params["canvas_width"]),
                    height=int(render_params["canvas_height"]),
                    tile_px=int(task_params.get("tile_px", group_default(_RENDER_DEFAULTS, "rpg_house_tile_px", DEFAULT_TILE_PX))),
                    room_count=room_count,
                    start_room_id=sample.start_room_id,
                    room_labels=sample.room_labels,
                    door_states=sample.door_states,
                    label_font_family=str(font_trace.get("font_family", "")),
                    label_font_trace=font_trace,
                    render_metadata={
                        "canvas_profile": str(render_params.get("canvas_profile", "")),
                        "canvas_profile_size": list(render_params.get("canvas_profile_size", [])),
                        "canvas_profile_probabilities": dict(render_params.get("canvas_profile_probabilities", {})),
                    },
                )
                reachable_ids = set(reachable_room_ids(scene.doors, start_room_id=sample.start_room_id))
                reachable_candidates = tuple(
                    room_id for room_id in sample.candidate_room_ids if room_id in reachable_ids
                )
                if reachable_candidates == (sample.answer_room_id,):
                    break
                last_error = RuntimeError(
                    f"RPG house reachability mismatch: expected {sample.answer_room_id}, got {reachable_candidates}"
                )
                scene = None
            except Exception as exc:  # pragma: no cover - retry path
                last_error = exc
                scene = None
        if scene is None:
            raise RuntimeError(f"could not generate RPG house reachable-room label: {last_error}") from last_error
        if sample is None:
            raise RuntimeError("could not sample RPG house reachable-room query")

        room_boxes = room_bbox_map(scene)
        annotation_value = room_boxes[sample.answer_room_id]
        answer = str(sample.room_labels[sample.answer_room_id])
        prompt_artifacts = build_rpg_house_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=required_defaults,
            prompt_query_key=PROMPT_QUERY_KEY,
            slots={
                "json_output_contract": str(required_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(required_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(required_defaults["answer_hint_rpg_house_reachable_room"]),
                "annotation_hint": str(required_defaults["annotation_hint_rpg_house_reachable_room"]),
                "json_example": str(required_defaults["json_example_rpg_house_reachable_room"]),
                "json_example_answer_only": str(required_defaults["json_example_answer_only_rpg_house_reachable_room"]),
            },
            instance_seed=int(instance_seed),
        )
        query_params = {
            "query_id": str(resolved_query_id),
            "prompt_query_key": PROMPT_QUERY_KEY,
            "query_id_probabilities": dict(query_probabilities),
            "start_room_id": sample.start_room_id,
            "answer_room_id": sample.answer_room_id,
            "answer_letter": answer,
            "candidate_room_ids": list(sample.candidate_room_ids),
            "candidate_room_labels": dict(sample.room_labels),
            "door_states": dict(sample.door_states),
            "reachable_candidate_room_ids": list(reachable_candidates),
            "start_room_probabilities": dict(sample.start_room_probabilities),
            "answer_room_probabilities": dict(sample.answer_room_probabilities),
            "answer_label_probabilities": dict(sample.answer_label_probabilities),
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
                    "start_room_id": sample.start_room_id,
                    "candidate_room_ids": list(sample.candidate_room_ids),
                    "answer_room_id": sample.answer_room_id,
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
            "render_map": rpg_house_reachability_render_map(
                scene=scene,
                start_room_id=sample.start_room_id,
                candidate_room_ids=sample.candidate_room_ids,
                answer_room_id=sample.answer_room_id,
            ),
            "execution_trace": {
                "query_id": str(resolved_query_id),
                "prompt_query_key": PROMPT_QUERY_KEY,
                "scene_id": SCENE_ID,
                "start_room_id": sample.start_room_id,
                "candidate_room_ids": list(sample.candidate_room_ids),
                "candidate_room_labels": dict(sample.room_labels),
                "door_states": dict(sample.door_states),
                "reachable_candidate_room_ids": list(reachable_candidates),
                "answer_room_id": sample.answer_room_id,
                "answer": answer,
                "renderer": dict(scene.trace),
            },
            "witness_symbolic": {
                "start_room_id": sample.start_room_id,
                "answer_room_id": sample.answer_room_id,
                "answer_letter": answer,
                "reachable_candidate_room_ids": list(reachable_candidates),
            },
            "projected_annotation": bbox_projection(annotation_value),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="string", value=answer),
            annotation_gt=TypedValue(type="bbox", value=annotation_value),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(resolved_query_id),
        )


__all__ = [
    "IllustrationsRpgHouseReachableRoomLabelTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
