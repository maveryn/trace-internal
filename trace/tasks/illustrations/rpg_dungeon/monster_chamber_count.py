"""Count dungeon treasure chambers that contain a monster."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.scene_config import get_scene_defaults
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
    bbox_set_projection,
    monster_entities,
    rpg_dungeon_monster_chamber_count_render_map,
    rpg_dungeon_render_spec,
    rpg_dungeon_scene_ir,
)
from .shared.prompts import build_rpg_dungeon_prompt_artifacts
from .shared.rendering import (
    DEFAULT_TILE_PX,
    MAX_MONSTER_CHAMBER_COUNT,
    MAX_TOTAL_CHEST_COUNT,
    MIN_MONSTER_CHAMBER_COUNT,
    MIN_TOTAL_CHEST_COUNT,
    SCENE_ID,
    render_rpg_dungeon_profile_scene,
)
from .shared.sampling import select_count_from_support


TASK_ID = "task_illustrations__rpg_dungeon__monster_chamber_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "monster_chamber_count"
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@dataclass(frozen=True)
class _MonsterWitnesses:
    answer: int
    annotation_bboxes: list[list[float]]
    entity_ids: list[str]
    chamber_ids: list[str]
    object_types: list[str]


def _prompt_default_keys() -> tuple[str, ...]:
    return (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        "answer_hint_rpg_dungeon_monster_chamber_count",
        "annotation_hint_rpg_dungeon_monster_chamber_count",
        "json_example_rpg_dungeon_monster_chamber_count",
        "json_example_answer_only_rpg_dungeon_monster_chamber_count",
    )


def _select_monster_target_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    total_chambers: int,
) -> tuple[int, Mapping[str, float]]:
    return select_count_from_support(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="monster_chamber_count_support",
        explicit_key="monster_chamber_count",
        fallback_support=tuple(range(MIN_MONSTER_CHAMBER_COUNT, MAX_MONSTER_CHAMBER_COUNT + 1)),
        namespace=f"{TASK_ID}:monster_chamber_count",
        max_value=int(total_chambers),
    )


def _monster_bbox_annotation(monsters: Sequence[Any]) -> list[list[float]]:
    return [
        [round(float(value), 3) for value in entity.bbox_xyxy]
        for entity in monsters
    ]


def _monster_ids(monsters: Sequence[Any]) -> tuple[list[str], list[str]]:
    return (
        [str(entity.entity_id) for entity in monsters],
        [str(entity.chamber_id) for entity in monsters],
    )


def _monster_witnesses(scene: Any, *, expected_count: int) -> _MonsterWitnesses:
    monsters = monster_entities(scene)
    entity_ids, chamber_ids = _monster_ids(monsters)
    chamber_set = set(chamber_ids)
    if len(chamber_set) != len(monsters):
        raise ValueError(f"each counted dungeon chamber must contain at most one monster, got {chamber_ids}")
    answer = int(len(chamber_set))
    if answer != int(expected_count):
        raise ValueError(
            f"renderer produced {answer} monster chambers for requested count {expected_count}"
        )
    object_types = [str(entity.object_type) for entity in monsters]
    if any(not object_type.startswith("monster_") for object_type in object_types):
        raise ValueError(f"unexpected non-monster witness in monster count task: {object_types}")
    return _MonsterWitnesses(
        answer=answer,
        annotation_bboxes=_monster_bbox_annotation(monsters),
        entity_ids=entity_ids,
        chamber_ids=chamber_ids,
        object_types=object_types,
    )


def _monster_count_prompt_defaults() -> Mapping[str, Any]:
    return required_group_defaults(
        _PROMPT_DEFAULTS,
        _prompt_default_keys(),
        context="prompt defaults for RPG dungeon monster-chamber count task",
    )


@register_task
class IllustrationsRpgDungeonMonsterChamberCountTask:
    """Count treasure chambers containing one visible monster."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one dungeon monster-chamber count instance."""

        resolved_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SINGLE_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}:query",
        )
        total_chest_count, total_count_probabilities = select_count_from_support(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="total_chest_count_support",
            explicit_key="total_chest_count",
            fallback_support=tuple(range(MIN_TOTAL_CHEST_COUNT, MAX_TOTAL_CHEST_COUNT + 1)),
            namespace=f"{TASK_ID}:total_chest_count",
        )
        monster_chamber_count, monster_count_probabilities = _select_monster_target_count(
            instance_seed=int(instance_seed),
            params=task_params,
            total_chambers=int(total_chest_count),
        )
        render_params = resolve_rpg_tile_render_params(
            task_params,
            _RENDER_DEFAULTS,
            tile_px_key="rpg_dungeon_tile_px",
            fallback_tile_px=DEFAULT_TILE_PX,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:canvas_profile",
        )
        tile_px = int(render_params["tile_px"])
        required_defaults = _monster_count_prompt_defaults()

        scene = render_rpg_dungeon_profile_scene(
            int(instance_seed),
            render_params=render_params,
            tile_px=tile_px,
            reachable_chest_count=int(total_chest_count),
            total_chest_count=int(total_chest_count),
            monster_chamber_count=int(monster_chamber_count),
        )
        witnesses = _monster_witnesses(scene, expected_count=int(monster_chamber_count))
        prompt_artifacts = build_rpg_dungeon_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=required_defaults,
            prompt_query_key=PROMPT_QUERY_KEY,
            slots={
                "json_output_contract": str(required_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(required_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(required_defaults["answer_hint_rpg_dungeon_monster_chamber_count"]),
                "annotation_hint": str(required_defaults["annotation_hint_rpg_dungeon_monster_chamber_count"]),
                "json_example": str(required_defaults["json_example_rpg_dungeon_monster_chamber_count"]),
                "json_example_answer_only": str(required_defaults["json_example_answer_only_rpg_dungeon_monster_chamber_count"]),
            },
            instance_seed=int(instance_seed),
        )
        query_params = {
            "query_id": str(resolved_query_id),
            "prompt_query_key": PROMPT_QUERY_KEY,
            "query_id_probabilities": dict(query_probabilities),
            "total_chest_count": int(total_chest_count),
            "total_chest_count_probabilities": dict(total_count_probabilities),
            "monster_chamber_count": int(monster_chamber_count),
            "monster_chamber_count_probabilities": dict(monster_count_probabilities),
            "canvas_profile": str(render_params.get("canvas_profile", "")),
            "canvas_profile_probabilities": dict(render_params.get("canvas_profile_probabilities", {})),
        }
        trace_payload = {
            "scene_ir": rpg_dungeon_scene_ir(
                domain=self.domain,
                scene_id=SCENE_ID,
                scene=scene,
                relations={
                    "query_id": str(resolved_query_id),
                    "prompt_query_key": PROMPT_QUERY_KEY,
                    "monster_entity_ids": witnesses.entity_ids,
                    "monster_chamber_ids": witnesses.chamber_ids,
                    "monster_object_types": witnesses.object_types,
                    "total_chest_count": int(len(scene.chest_entity_ids)),
                    "answer": int(witnesses.answer),
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
            "render_spec": rpg_dungeon_render_spec(scene, scene_id=SCENE_ID),
            "render_map": rpg_dungeon_monster_chamber_count_render_map(scene=scene),
            "execution_trace": {
                "query_id": str(resolved_query_id),
                "prompt_query_key": PROMPT_QUERY_KEY,
                "scene_id": SCENE_ID,
                "monster_chamber_count": int(witnesses.answer),
                "monster_entity_ids": witnesses.entity_ids,
                "monster_chamber_ids": witnesses.chamber_ids,
                "monster_object_types": witnesses.object_types,
                "total_chest_count": int(len(scene.chest_entity_ids)),
                "renderer": dict(scene.trace),
            },
            "witness_symbolic": {
                "monster_chamber_count": int(witnesses.answer),
                "monster_entity_ids": witnesses.entity_ids,
                "monster_chamber_ids": witnesses.chamber_ids,
                "monster_object_types": witnesses.object_types,
                "total_chest_count": int(len(scene.chest_entity_ids)),
            },
            "projected_annotation": bbox_set_projection(witnesses.annotation_bboxes),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=witnesses.answer),
            annotation_gt=TypedValue(type="bbox_set", value=witnesses.annotation_bboxes),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(resolved_query_id),
        )


__all__ = [
    "IllustrationsRpgDungeonMonsterChamberCountTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
