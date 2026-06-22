"""Count reachable treasure chests outside monster chambers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from trace.core.query_ids import SINGLE_QUERY_ID
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
    bbox_set_map_projection,
    entity_bbox_map,
    monster_entities,
    player_entity,
    rpg_dungeon_render_spec,
    rpg_dungeon_safe_reachable_chest_count_render_map,
    rpg_dungeon_scene_ir,
    safe_reachable_chest_ids,
)
from .shared.prompts import build_rpg_dungeon_prompt_artifacts
from .shared.rendering import (
    DEFAULT_TILE_PX,
    MAX_MONSTER_CHAMBER_COUNT,
    MAX_TOTAL_CHEST_COUNT,
    MIN_TOTAL_CHEST_COUNT,
    SCENE_ID,
    render_rpg_dungeon_profile_scene,
)
from .shared.sampling import select_count_from_support


TASK_ID = "task_illustrations__rpg_dungeon__safe_reachable_chest_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "safe_reachable_chest_count"
MIN_SAFE_REACHABLE_CHEST_COUNT = 0
MAX_SAFE_REACHABLE_CHEST_COUNT = MAX_TOTAL_CHEST_COUNT - 1
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@dataclass(frozen=True)
class _HazardRenderCounts:
    reachable_chest_count: int
    monster_chamber_count: int
    reachable_monster_chamber_count: int


@dataclass(frozen=True)
class _SafeChestWitnesses:
    answer: int
    annotation_value: dict[str, list[list[float]]]
    player_entity_id: str
    counted_chest_ids: list[str]
    reachable_chest_ids: list[str]
    monster_chamber_ids: list[str]


def _select_safe_target_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    total_chambers: int,
) -> tuple[int, Mapping[str, float]]:
    return select_count_from_support(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="safe_reachable_chest_count_support",
        explicit_key="safe_reachable_chest_count",
        fallback_support=tuple(range(MIN_SAFE_REACHABLE_CHEST_COUNT, MAX_SAFE_REACHABLE_CHEST_COUNT + 1)),
        namespace=f"{TASK_ID}:safe_reachable_chest_count",
        max_value=int(total_chambers) - 1,
    )


def _choose_hazard_render_counts(
    *,
    instance_seed: int,
    total_chambers: int,
    target_safe_count: int,
) -> _HazardRenderCounts:
    candidates: list[_HazardRenderCounts] = []
    for reachable_count in range(max(1, int(target_safe_count)), int(total_chambers)):
        reachable_monsters = int(reachable_count) - int(target_safe_count)
        if not 0 <= reachable_monsters <= MAX_MONSTER_CHAMBER_COUNT:
            continue
        unreachable_slots = int(total_chambers) - int(reachable_count)
        if int(reachable_monsters) == 0:
            candidates.append(
                _HazardRenderCounts(
                    reachable_chest_count=int(reachable_count),
                    monster_chamber_count=1,
                    reachable_monster_chamber_count=0,
                )
            )
            continue
        max_extra_unreachable_monsters = min(
            MAX_MONSTER_CHAMBER_COUNT - int(reachable_monsters),
            int(unreachable_slots),
        )
        for extra_unreachable in range(max_extra_unreachable_monsters + 1):
            candidates.append(
                _HazardRenderCounts(
                    reachable_chest_count=int(reachable_count),
                    monster_chamber_count=int(reachable_monsters) + int(extra_unreachable),
                    reachable_monster_chamber_count=int(reachable_monsters),
                )
            )
    if not candidates:
        raise ValueError(
            f"no RPG dungeon hazard count plan for total={total_chambers}, target={target_safe_count}"
        )
    index = hash64(int(instance_seed), f"{TASK_ID}:hazard_counts:{total_chambers}:{target_safe_count}") % len(candidates)
    return candidates[int(index)]


def _safe_chest_witnesses(scene: Any, *, expected_count: int) -> _SafeChestWitnesses:
    player = player_entity(scene)
    if player is None:
        raise ValueError("safe reachable chest task requires a player entity")
    counted_ids = safe_reachable_chest_ids(scene)
    if len(counted_ids) != int(expected_count):
        raise ValueError(f"renderer produced {len(counted_ids)} safe reachable chests for target {expected_count}")
    counted_bboxes = entity_bbox_map(scene, counted_ids)
    annotation_value = {
        "player": [[round(float(value), 3) for value in player.bbox_xyxy]],
        "counted_chests": [counted_bboxes[str(entity_id)] for entity_id in counted_ids],
    }
    return _SafeChestWitnesses(
        answer=int(len(counted_ids)),
        annotation_value=annotation_value,
        player_entity_id=str(scene.player_entity_id),
        counted_chest_ids=[str(entity_id) for entity_id in counted_ids],
        reachable_chest_ids=[str(entity_id) for entity_id in scene.reachable_chest_ids],
        monster_chamber_ids=[str(entity.chamber_id) for entity in monster_entities(scene)],
    )


def _safe_count_prompt_defaults() -> Mapping[str, Any]:
    return required_group_defaults(
        _PROMPT_DEFAULTS,
        [
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_rpg_dungeon_safe_reachable_chest_count",
            "annotation_hint_rpg_dungeon_safe_reachable_chest_count",
            "json_example_rpg_dungeon_safe_reachable_chest_count",
            "json_example_answer_only_rpg_dungeon_safe_reachable_chest_count",
        ],
        context="prompt defaults for RPG dungeon safe reachable chest count task",
    )


@register_task
class IllustrationsRpgDungeonSafeReachableChestCountTask:
    """Count reachable chests while excluding monster chambers."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one exact safe-reachable chest count instance."""

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
        target_count, target_probabilities = _select_safe_target_count(
            instance_seed=int(instance_seed),
            params=task_params,
            total_chambers=int(total_chest_count),
        )
        hazard_counts = _choose_hazard_render_counts(
            instance_seed=int(instance_seed),
            total_chambers=int(total_chest_count),
            target_safe_count=int(target_count),
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
        required_defaults = _safe_count_prompt_defaults()

        scene = render_rpg_dungeon_profile_scene(
            int(instance_seed),
            render_params=render_params,
            tile_px=tile_px,
            reachable_chest_count=int(hazard_counts.reachable_chest_count),
            total_chest_count=int(total_chest_count),
            monster_chamber_count=int(hazard_counts.monster_chamber_count),
            reachable_monster_chamber_count=int(hazard_counts.reachable_monster_chamber_count),
        )
        witnesses = _safe_chest_witnesses(scene, expected_count=int(target_count))
        prompt_artifacts = build_rpg_dungeon_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=required_defaults,
            prompt_query_key=PROMPT_QUERY_KEY,
            slots={
                "json_output_contract": str(required_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(required_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(required_defaults["answer_hint_rpg_dungeon_safe_reachable_chest_count"]),
                "annotation_hint": str(required_defaults["annotation_hint_rpg_dungeon_safe_reachable_chest_count"]),
                "json_example": str(required_defaults["json_example_rpg_dungeon_safe_reachable_chest_count"]),
                "json_example_answer_only": str(required_defaults["json_example_answer_only_rpg_dungeon_safe_reachable_chest_count"]),
            },
            instance_seed=int(instance_seed),
        )
        query_params = {
            "query_id": str(resolved_query_id),
            "prompt_query_key": PROMPT_QUERY_KEY,
            "query_id_probabilities": dict(query_probabilities),
            "total_chest_count": int(total_chest_count),
            "total_chest_count_probabilities": dict(total_count_probabilities),
            "safe_reachable_chest_count": int(target_count),
            "safe_reachable_chest_count_probabilities": dict(target_probabilities),
            "reachable_chest_count": int(hazard_counts.reachable_chest_count),
            "monster_chamber_count": int(hazard_counts.monster_chamber_count),
            "reachable_monster_chamber_count": int(hazard_counts.reachable_monster_chamber_count),
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
                    "player_entity_id": witnesses.player_entity_id,
                    "reachable_chest_ids": witnesses.reachable_chest_ids,
                    "monster_chamber_ids": witnesses.monster_chamber_ids,
                    "counted_chest_ids": witnesses.counted_chest_ids,
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
            "render_map": rpg_dungeon_safe_reachable_chest_count_render_map(scene=scene),
            "execution_trace": {
                "query_id": str(resolved_query_id),
                "prompt_query_key": PROMPT_QUERY_KEY,
                "scene_id": SCENE_ID,
                "safe_reachable_chest_count": int(witnesses.answer),
                "reachable_chest_ids": witnesses.reachable_chest_ids,
                "monster_chamber_ids": witnesses.monster_chamber_ids,
                "counted_chest_ids": witnesses.counted_chest_ids,
                "renderer": dict(scene.trace),
            },
            "witness_symbolic": {
                "safe_reachable_chest_count": int(witnesses.answer),
                "player_entity_id": witnesses.player_entity_id,
                "reachable_chest_ids": witnesses.reachable_chest_ids,
                "monster_chamber_ids": witnesses.monster_chamber_ids,
                "counted_chest_ids": witnesses.counted_chest_ids,
            },
            "projected_annotation": bbox_set_map_projection(witnesses.annotation_value),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=witnesses.answer),
            annotation_gt=TypedValue(type="bbox_set_map", value=witnesses.annotation_value),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(resolved_query_id),
        )


__all__ = [
    "IllustrationsRpgDungeonSafeReachableChestCountTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
