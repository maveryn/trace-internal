"""Count treasure chests reachable in a top-down RPG dungeon."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

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
    entity_point_map,
    player_entity,
    point_set_map_projection,
    rpg_dungeon_reachable_chest_count_render_map,
    rpg_dungeon_render_spec,
    rpg_dungeon_scene_ir,
)
from .shared.prompts import build_rpg_dungeon_prompt_artifacts
from .shared.rendering import (
    DEFAULT_TILE_PX,
    MAX_REACHABLE_CHEST_COUNT,
    MIN_REACHABLE_CHEST_COUNT,
    SCENE_ID,
    render_rpg_dungeon_profile_scene,
)
from .shared.sampling import select_count_from_support


TASK_ID = "task_illustrations__rpg_dungeon__reachable_chest_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "reachable_chest_count"
_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@register_task
class IllustrationsRpgDungeonReachableChestCountTask:
    """Count chests reachable from the player through unblocked dungeon floor."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one instance whose answer comes from the renderer graph."""

        resolved_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SINGLE_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}:query",
        )
        target_count, target_probabilities = select_count_from_support(
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="reachable_chest_count_support",
            explicit_key="reachable_chest_count",
            fallback_support=tuple(range(MIN_REACHABLE_CHEST_COUNT, MAX_REACHABLE_CHEST_COUNT + 1)),
            namespace=f"{TASK_ID}:reachable_chest_count",
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
        required_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_rpg_dungeon_reachable_chest_count",
                "annotation_hint_rpg_dungeon_reachable_chest_count",
                "json_example_rpg_dungeon_reachable_chest_count",
                "json_example_answer_only_rpg_dungeon_reachable_chest_count",
            ],
            context="prompt defaults for RPG dungeon reachable-chest count task",
        )

        scene = render_rpg_dungeon_profile_scene(
            int(instance_seed),
            render_params=render_params,
            tile_px=tile_px,
            reachable_chest_count=int(target_count),
        )
        answer = int(len(scene.reachable_chest_ids))
        if answer != int(target_count):
            raise ValueError(f"renderer produced {answer} reachable chests for requested count {target_count}")
        player = player_entity(scene)
        if player is None:
            raise ValueError("RPG dungeon reachable-chest task requires a player entity")
        reachable_points = entity_point_map(scene, scene.reachable_chest_ids)
        annotation_value = {
            "player": [[round(float(player.point_xy[0]), 3), round(float(player.point_xy[1]), 3)]],
            "reachable_chests": [
                reachable_points[str(entity_id)]
                for entity_id in scene.reachable_chest_ids
            ],
        }
        prompt_artifacts = build_rpg_dungeon_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=required_defaults,
            prompt_query_key=PROMPT_QUERY_KEY,
            slots={
                "json_output_contract": str(required_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(required_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(required_defaults["answer_hint_rpg_dungeon_reachable_chest_count"]),
                "annotation_hint": str(required_defaults["annotation_hint_rpg_dungeon_reachable_chest_count"]),
                "json_example": str(required_defaults["json_example_rpg_dungeon_reachable_chest_count"]),
                "json_example_answer_only": str(required_defaults["json_example_answer_only_rpg_dungeon_reachable_chest_count"]),
            },
            instance_seed=int(instance_seed),
        )
        query_params = {
            "query_id": str(resolved_query_id),
            "prompt_query_key": PROMPT_QUERY_KEY,
            "query_id_probabilities": dict(query_probabilities),
            "reachable_chest_count": int(target_count),
            "reachable_chest_count_probabilities": dict(target_probabilities),
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
                    "player_entity_id": str(scene.player_entity_id),
                    "chest_entity_ids": [str(entity_id) for entity_id in scene.chest_entity_ids],
                    "reachable_chest_ids": [str(entity_id) for entity_id in scene.reachable_chest_ids],
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
            "render_spec": rpg_dungeon_render_spec(scene, scene_id=SCENE_ID),
            "render_map": rpg_dungeon_reachable_chest_count_render_map(scene=scene),
            "execution_trace": {
                "query_id": str(resolved_query_id),
                "prompt_query_key": PROMPT_QUERY_KEY,
                "scene_id": SCENE_ID,
                "reachable_chest_count": int(answer),
                "player_entity_id": str(scene.player_entity_id),
                "reachable_chest_ids": [str(entity_id) for entity_id in scene.reachable_chest_ids],
                "renderer": dict(scene.trace),
            },
            "witness_symbolic": {
                "reachable_chest_count": int(answer),
                "player_entity_id": str(scene.player_entity_id),
                "reachable_chest_ids": [str(entity_id) for entity_id in scene.reachable_chest_ids],
            },
            "projected_annotation": point_set_map_projection(annotation_value),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=answer),
            annotation_gt=TypedValue(type="point_set_map", value=annotation_value),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(resolved_query_id),
        )


__all__ = [
    "IllustrationsRpgDungeonReachableChestCountTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
