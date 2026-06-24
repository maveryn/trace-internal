"""Private lifecycle plumbing for RPG dungeon count tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from trace.core.scene_config import get_scene_defaults
from trace.core.seed import hash64
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.illustrations.shared.rpg_tile_profiles import resolve_rpg_tile_render_params

from .shared.output import (
    bbox_set_projection,
    entity_bbox_map,
    monster_entities,
    player_entity,
    rpg_dungeon_monster_chamber_count_render_map,
    rpg_dungeon_reachable_chest_count_render_map,
    rpg_dungeon_render_spec,
    rpg_dungeon_safe_reachable_chest_count_render_map,
    rpg_dungeon_scene_ir,
    safe_reachable_chest_ids,
)
from .shared.prompts import build_rpg_dungeon_prompt_artifacts
from .shared.rendering import (
    DEFAULT_TILE_PX,
    MAX_MONSTER_CHAMBER_COUNT,
    MAX_REACHABLE_CHEST_COUNT,
    MAX_TOTAL_CHEST_COUNT,
    MIN_REACHABLE_CHEST_COUNT,
    MIN_TOTAL_CHEST_COUNT,
    SCENE_ID,
    render_rpg_dungeon_profile_scene,
)
from .shared.sampling import select_count_from_support
from .shared.state import RpgDungeonScene


@dataclass(frozen=True)
class DungeonCountSample:
    """Resolved count operands for one public dungeon task."""

    scene_kwargs: Mapping[str, Any]
    query_params: Mapping[str, Any]


@dataclass(frozen=True)
class DungeonCountWitnesses:
    """Task-owned answer, annotation, and verifier fields."""

    answer: int
    annotation_bboxes: Sequence[Sequence[float]]
    relations: Mapping[str, Any]
    execution_fields: Mapping[str, Any]
    witness_fields: Mapping[str, Any]


@dataclass(frozen=True)
class DungeonPromptKeys:
    """Prompt template keys needed by one count objective."""

    required: tuple[str, ...]
    answer_hint: str
    annotation_hint: str
    json_example: str
    json_example_answer_only: str


@dataclass(frozen=True)
class DungeonCountPlan:
    """Public-owned hooks for one RPG dungeon integer-count objective."""

    task_id: str
    operation: str
    prompt_query_key: str
    supported_query_ids: tuple[str, ...]
    prompt_keys: DungeonPromptKeys
    sample: Callable[[int, Mapping[str, Any], Mapping[str, Any]], DungeonCountSample]
    bind_witnesses: Callable[[RpgDungeonScene, DungeonCountSample], DungeonCountWitnesses]
    render_map: Callable[[RpgDungeonScene, DungeonCountWitnesses], Mapping[str, Any]]


class RpgDungeonCountTaskBase:
    """Shared generate implementation for public RPG dungeon count tasks."""

    domain = "illustrations"
    default_dataset_enabled = True
    _plan: DungeonCountPlan
    _generation_defaults: Mapping[str, Any]
    _rendering_defaults: Mapping[str, Any]
    _prompt_defaults: Mapping[str, Any]

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one count instance using the task-owned plan."""

        return run_rpg_dungeon_count_lifecycle(
            plan=self._plan,
            domain=self.domain,
            generation_defaults=self._generation_defaults,
            rendering_defaults=self._rendering_defaults,
            prompt_defaults=self._prompt_defaults,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


def dungeon_prompt_keys(suffix: str) -> DungeonPromptKeys:
    """Return the standard RPG dungeon prompt key bundle for one objective suffix."""

    stem = str(suffix)
    return DungeonPromptKeys(
        required=(
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            f"answer_hint_{stem}",
            f"annotation_hint_{stem}",
            f"json_example_{stem}",
            f"json_example_answer_only_{stem}",
        ),
        answer_hint=f"answer_hint_{stem}",
        annotation_hint=f"annotation_hint_{stem}",
        json_example=f"json_example_{stem}",
        json_example_answer_only=f"json_example_answer_only_{stem}",
    )


def sample_total_chest_count(
    *,
    task_id: str,
    instance_seed: int,
    task_params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> tuple[int, Mapping[str, float]]:
    """Sample the shared total treasure-chamber count for dungeon count tasks."""

    return select_count_from_support(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=generation_defaults,
        support_key="total_chest_count_support",
        explicit_key="total_chest_count",
        fallback_support=tuple(range(MIN_TOTAL_CHEST_COUNT, MAX_TOTAL_CHEST_COUNT + 1)),
        namespace=f"{task_id}:total_chest_count",
    )


def sample_dungeon_count_operand(
    *,
    task_id: str,
    instance_seed: int,
    task_params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    namespace_suffix: str,
    max_value: int | None = None,
) -> tuple[int, Mapping[str, float]]:
    """Sample a task-owned integer operand from config with explicit support metadata."""

    kwargs: dict[str, Any] = {}
    if max_value is not None:
        kwargs["max_value"] = int(max_value)
    return select_count_from_support(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=generation_defaults,
        support_key=str(support_key),
        explicit_key=str(explicit_key),
        fallback_support=tuple(int(value) for value in fallback_support),
        namespace=f"{task_id}:{namespace_suffix}",
        **kwargs,
    )


def rpg_dungeon_task_defaults(task_id: str) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
    """Load generation, rendering, and prompt defaults for one dungeon task."""

    defaults = get_scene_defaults("illustrations", SCENE_ID)
    return split_scene_generation_rendering_prompt_defaults(
        defaults if isinstance(defaults, Mapping) else {},
        task_id=str(task_id),
    )


def build_reachable_chest_count_plan(task_id: str, supported_query_ids: tuple[str, ...]) -> DungeonCountPlan:
    """Build the task plan for counting all reachable chests."""

    def sample(instance_seed: int, task_params: Mapping[str, Any], generation_defaults: Mapping[str, Any]) -> DungeonCountSample:
        total_chest_count, total_count_probabilities = sample_total_chest_count(
            task_id=task_id,
            instance_seed=instance_seed,
            task_params=task_params,
            generation_defaults=generation_defaults,
        )
        target_count, target_probabilities = sample_dungeon_count_operand(
            task_id=task_id,
            instance_seed=instance_seed,
            task_params=task_params,
            generation_defaults=generation_defaults,
            support_key="reachable_chest_count_support",
            explicit_key="reachable_chest_count",
            fallback_support=tuple(range(MIN_REACHABLE_CHEST_COUNT, MAX_REACHABLE_CHEST_COUNT + 1)),
            namespace_suffix="reachable_chest_count",
            max_value=int(total_chest_count),
        )
        return DungeonCountSample(
            scene_kwargs={
                "reachable_chest_count": int(target_count),
                "total_chest_count": int(total_chest_count),
            },
            query_params={
                "total_chest_count": int(total_chest_count),
                "total_chest_count_probabilities": dict(total_count_probabilities),
                "reachable_chest_count": int(target_count),
                "reachable_chest_count_probabilities": dict(target_probabilities),
            },
        )

    def bind(scene: RpgDungeonScene, current_sample: DungeonCountSample) -> DungeonCountWitnesses:
        answer = int(len(scene.reachable_chest_ids))
        requested = int(current_sample.scene_kwargs["reachable_chest_count"])
        if answer != requested:
            raise ValueError(f"renderer produced {answer} reachable chests for requested count {requested}")
        if player_entity(scene) is None:
            raise ValueError("RPG dungeon reachable-chest task requires a player entity")
        reachable_bboxes = entity_bbox_map(scene, scene.reachable_chest_ids)
        reachable_ids = [str(entity_id) for entity_id in scene.reachable_chest_ids]
        fields = {
            "reachable_chest_count": int(answer),
            "total_chest_count": int(len(scene.chest_entity_ids)),
            "player_entity_id": str(scene.player_entity_id),
            "reachable_chest_ids": reachable_ids,
        }
        return DungeonCountWitnesses(
            answer=answer,
            annotation_bboxes=[reachable_bboxes[str(entity_id)] for entity_id in scene.reachable_chest_ids],
            relations={**fields, "chest_entity_ids": [str(entity_id) for entity_id in scene.chest_entity_ids]},
            execution_fields=fields,
            witness_fields=fields,
        )

    return DungeonCountPlan(
        task_id=str(task_id),
        operation="count_reachable_chests_from_player",
        prompt_query_key="reachable_chest_count",
        supported_query_ids=tuple(str(query_id) for query_id in supported_query_ids),
        prompt_keys=dungeon_prompt_keys("rpg_dungeon_reachable_chest_count"),
        sample=sample,
        bind_witnesses=bind,
        render_map=lambda scene, _witnesses: rpg_dungeon_reachable_chest_count_render_map(scene=scene),
    )


def build_monster_chamber_count_plan(task_id: str, supported_query_ids: tuple[str, ...]) -> DungeonCountPlan:
    """Build the task plan for counting monster-occupied chambers."""

    def sample(instance_seed: int, task_params: Mapping[str, Any], generation_defaults: Mapping[str, Any]) -> DungeonCountSample:
        total_chest_count, total_count_probabilities = sample_total_chest_count(
            task_id=task_id,
            instance_seed=instance_seed,
            task_params=task_params,
            generation_defaults=generation_defaults,
        )
        monster_chamber_count, monster_count_probabilities = sample_dungeon_count_operand(
            task_id=task_id,
            instance_seed=instance_seed,
            task_params=task_params,
            generation_defaults=generation_defaults,
            support_key="monster_chamber_count_support",
            explicit_key="monster_chamber_count",
            fallback_support=tuple(range(1, MAX_MONSTER_CHAMBER_COUNT + 1)),
            namespace_suffix="monster_chamber_count",
            max_value=int(total_chest_count),
        )
        return DungeonCountSample(
            scene_kwargs={
                "reachable_chest_count": int(total_chest_count),
                "total_chest_count": int(total_chest_count),
                "monster_chamber_count": int(monster_chamber_count),
            },
            query_params={
                "total_chest_count": int(total_chest_count),
                "total_chest_count_probabilities": dict(total_count_probabilities),
                "monster_chamber_count": int(monster_chamber_count),
                "monster_chamber_count_probabilities": dict(monster_count_probabilities),
            },
        )

    def bind(scene: RpgDungeonScene, current_sample: DungeonCountSample) -> DungeonCountWitnesses:
        monsters = monster_entities(scene)
        chamber_ids = [str(entity.chamber_id) for entity in monsters]
        if len(set(chamber_ids)) != len(monsters):
            raise ValueError(f"each counted dungeon chamber must contain at most one monster, got {chamber_ids}")
        answer = int(len(chamber_ids))
        requested = int(current_sample.scene_kwargs["monster_chamber_count"])
        if answer != requested:
            raise ValueError(f"renderer produced {answer} monster chambers for requested count {requested}")
        object_types = [str(entity.object_type) for entity in monsters]
        if any(not object_type.startswith("monster_") for object_type in object_types):
            raise ValueError(f"unexpected non-monster witness in monster count task: {object_types}")
        fields = {
            "monster_chamber_count": int(answer),
            "monster_entity_ids": [str(entity.entity_id) for entity in monsters],
            "monster_chamber_ids": chamber_ids,
            "monster_object_types": object_types,
            "total_chest_count": int(len(scene.chest_entity_ids)),
        }
        return DungeonCountWitnesses(
            answer=answer,
            annotation_bboxes=[[round(float(value), 3) for value in entity.bbox_xyxy] for entity in monsters],
            relations=fields,
            execution_fields=fields,
            witness_fields=fields,
        )

    return DungeonCountPlan(
        task_id=str(task_id),
        operation="count_chambers_containing_monsters",
        prompt_query_key="monster_chamber_count",
        supported_query_ids=tuple(str(query_id) for query_id in supported_query_ids),
        prompt_keys=dungeon_prompt_keys("rpg_dungeon_monster_chamber_count"),
        sample=sample,
        bind_witnesses=bind,
        render_map=lambda scene, _witnesses: rpg_dungeon_monster_chamber_count_render_map(scene=scene),
    )


@dataclass(frozen=True)
class _HazardRenderCounts:
    reachable_chest_count: int
    monster_chamber_count: int
    reachable_monster_chamber_count: int


def _choose_safe_chest_hazard_counts(
    *,
    task_id: str,
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
            candidates.append(_HazardRenderCounts(int(reachable_count), 1, 0))
            continue
        max_extra_unreachable_monsters = min(MAX_MONSTER_CHAMBER_COUNT - int(reachable_monsters), int(unreachable_slots))
        for extra_unreachable in range(max_extra_unreachable_monsters + 1):
            candidates.append(
                _HazardRenderCounts(
                    int(reachable_count),
                    int(reachable_monsters) + int(extra_unreachable),
                    int(reachable_monsters),
                )
            )
    if not candidates:
        raise ValueError(f"no RPG dungeon hazard count plan for total={total_chambers}, target={target_safe_count}")
    index = hash64(int(instance_seed), f"{task_id}:hazard_counts:{total_chambers}:{target_safe_count}") % len(candidates)
    return candidates[int(index)]


def build_safe_reachable_chest_count_plan(task_id: str, supported_query_ids: tuple[str, ...]) -> DungeonCountPlan:
    """Build the task plan for counting reachable chests outside monster chambers."""

    max_safe_count = int(MAX_TOTAL_CHEST_COUNT) - 1

    def sample(instance_seed: int, task_params: Mapping[str, Any], generation_defaults: Mapping[str, Any]) -> DungeonCountSample:
        total_chest_count, total_count_probabilities = sample_total_chest_count(
            task_id=task_id,
            instance_seed=instance_seed,
            task_params=task_params,
            generation_defaults=generation_defaults,
        )
        target_count, target_probabilities = sample_dungeon_count_operand(
            task_id=task_id,
            instance_seed=instance_seed,
            task_params=task_params,
            generation_defaults=generation_defaults,
            support_key="safe_reachable_chest_count_support",
            explicit_key="safe_reachable_chest_count",
            fallback_support=tuple(range(0, max_safe_count + 1)),
            namespace_suffix="safe_reachable_chest_count",
            max_value=int(total_chest_count) - 1,
        )
        hazard_counts = _choose_safe_chest_hazard_counts(
            task_id=task_id,
            instance_seed=int(instance_seed),
            total_chambers=int(total_chest_count),
            target_safe_count=int(target_count),
        )
        return DungeonCountSample(
            scene_kwargs={
                "reachable_chest_count": int(hazard_counts.reachable_chest_count),
                "total_chest_count": int(total_chest_count),
                "monster_chamber_count": int(hazard_counts.monster_chamber_count),
                "reachable_monster_chamber_count": int(hazard_counts.reachable_monster_chamber_count),
            },
            query_params={
                "total_chest_count": int(total_chest_count),
                "total_chest_count_probabilities": dict(total_count_probabilities),
                "safe_reachable_chest_count": int(target_count),
                "safe_reachable_chest_count_probabilities": dict(target_probabilities),
                "reachable_chest_count": int(hazard_counts.reachable_chest_count),
                "monster_chamber_count": int(hazard_counts.monster_chamber_count),
                "reachable_monster_chamber_count": int(hazard_counts.reachable_monster_chamber_count),
            },
        )

    def bind(scene: RpgDungeonScene, current_sample: DungeonCountSample) -> DungeonCountWitnesses:
        if player_entity(scene) is None:
            raise ValueError("safe reachable chest task requires a player entity")
        counted_ids = safe_reachable_chest_ids(scene)
        expected = int(current_sample.query_params["safe_reachable_chest_count"])
        if len(counted_ids) != expected:
            raise ValueError(f"renderer produced {len(counted_ids)} safe reachable chests for target {expected}")
        counted_bboxes = entity_bbox_map(scene, counted_ids)
        fields = {
            "safe_reachable_chest_count": int(len(counted_ids)),
            "player_entity_id": str(scene.player_entity_id),
            "reachable_chest_ids": [str(entity_id) for entity_id in scene.reachable_chest_ids],
            "monster_chamber_ids": [str(entity.chamber_id) for entity in monster_entities(scene)],
            "counted_chest_ids": [str(entity_id) for entity_id in counted_ids],
        }
        return DungeonCountWitnesses(
            answer=int(len(counted_ids)),
            annotation_bboxes=[counted_bboxes[str(entity_id)] for entity_id in counted_ids],
            relations=fields,
            execution_fields={
                "safe_reachable_chest_count": int(len(counted_ids)),
                "reachable_chest_ids": list(fields["reachable_chest_ids"]),
                "monster_chamber_ids": list(fields["monster_chamber_ids"]),
                "counted_chest_ids": list(fields["counted_chest_ids"]),
            },
            witness_fields=fields,
        )

    return DungeonCountPlan(
        task_id=str(task_id),
        operation="count_reachable_chests_outside_monster_chambers",
        prompt_query_key="safe_reachable_chest_count",
        supported_query_ids=tuple(str(query_id) for query_id in supported_query_ids),
        prompt_keys=dungeon_prompt_keys("rpg_dungeon_safe_reachable_chest_count"),
        sample=sample,
        bind_witnesses=bind,
        render_map=lambda scene, _witnesses: rpg_dungeon_safe_reachable_chest_count_render_map(scene=scene),
    )


def _prompt_slots(prompt_defaults: Mapping[str, Any], prompt_keys: DungeonPromptKeys) -> dict[str, str]:
    return {
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults[prompt_keys.answer_hint]),
        "annotation_hint": str(prompt_defaults[prompt_keys.annotation_hint]),
        "json_example": str(prompt_defaults[prompt_keys.json_example]),
        "json_example_answer_only": str(prompt_defaults[prompt_keys.json_example_answer_only]),
    }


def _rounded_bbox_set(bboxes: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[round(float(value), 3) for value in bbox] for bbox in bboxes]


def run_rpg_dungeon_count_lifecycle(
    *,
    plan: DungeonCountPlan,
    domain: str,
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Resolve operands, render a dungeon scene, and package a bbox-set count output."""

    if not plan.supported_query_ids:
        raise ValueError(f"{plan.task_id} must declare at least one query id")
    resolved_query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(query_id) for query_id in plan.supported_query_ids),
        default_query_id=str(plan.supported_query_ids[0]),
        task_id=str(plan.task_id),
        namespace=f"{plan.task_id}:query",
    )
    sample = plan.sample(int(instance_seed), task_params, generation_defaults)
    render_params = resolve_rpg_tile_render_params(
        task_params,
        rendering_defaults,
        tile_px_key="rpg_dungeon_tile_px",
        fallback_tile_px=DEFAULT_TILE_PX,
        instance_seed=int(instance_seed),
        namespace=f"{plan.task_id}:canvas_profile",
    )
    checked_prompt_defaults = required_group_defaults(
        prompt_defaults,
        list(plan.prompt_keys.required),
        context=f"prompt defaults for {plan.task_id}",
    )

    last_error: Exception | None = None
    scene: RpgDungeonScene | None = None
    witnesses: DungeonCountWitnesses | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            scene_seed = int(instance_seed) + int(attempt) * 1009
            candidate_scene = render_rpg_dungeon_profile_scene(
                scene_seed,
                render_params=render_params,
                tile_px=int(render_params["tile_px"]),
                **dict(sample.scene_kwargs),
            )
            candidate_witnesses = plan.bind_witnesses(candidate_scene, sample)
            scene = candidate_scene
            witnesses = candidate_witnesses
            break
        except Exception as exc:  # pragma: no cover - random layout feasibility is retry based
            last_error = exc
            scene = None
            witnesses = None
    if scene is None or witnesses is None:
        raise RuntimeError(f"could not generate RPG dungeon count instance: {last_error}") from last_error

    annotation_value = _rounded_bbox_set(witnesses.annotation_bboxes)
    prompt_artifacts = build_rpg_dungeon_prompt_artifacts(
        domain=str(domain),
        scene_id=SCENE_ID,
        prompt_defaults=checked_prompt_defaults,
        prompt_query_key=str(plan.prompt_query_key),
        slots=_prompt_slots(checked_prompt_defaults, plan.prompt_keys),
        instance_seed=int(instance_seed),
    )
    query_params = {
        "query_id": str(resolved_query_id),
        "prompt_query_key": str(plan.prompt_query_key),
        "query_id_probabilities": dict(query_probabilities),
        **dict(sample.query_params),
        "canvas_profile": str(render_params.get("canvas_profile", "")),
        "canvas_profile_probabilities": dict(render_params.get("canvas_profile_probabilities", {})),
    }
    trace_payload = {
        "scene_ir": rpg_dungeon_scene_ir(
            domain=str(domain),
            scene_id=SCENE_ID,
            scene=scene,
            relations={
                "operation": str(plan.operation),
                "query_id": str(resolved_query_id),
                "prompt_query_key": str(plan.prompt_query_key),
                **dict(witnesses.relations),
                "answer": int(witnesses.answer),
            },
        ),
        "query_spec": {
            "task_id": str(plan.task_id),
            "query_id": str(resolved_query_id),
            "prompt_query_key": str(plan.prompt_query_key),
            "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": query_params,
        },
        "render_spec": rpg_dungeon_render_spec(scene, scene_id=SCENE_ID),
        "render_map": dict(plan.render_map(scene, witnesses)),
        "execution_trace": {
            "query_id": str(resolved_query_id),
            "prompt_query_key": str(plan.prompt_query_key),
            "scene_id": SCENE_ID,
            "operation": str(plan.operation),
            "answer": int(witnesses.answer),
            **dict(witnesses.execution_fields),
            "renderer": dict(scene.trace),
        },
        "witness_symbolic": dict(witnesses.witness_fields),
        "projected_annotation": bbox_set_projection(annotation_value),
    }
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        answer_gt=TypedValue(type="integer", value=int(witnesses.answer)),
        annotation_gt=TypedValue(type="bbox_set", value=annotation_value),
        image=scene.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(resolved_query_id),
    )


__all__ = [
    "DungeonCountPlan",
    "DungeonCountSample",
    "DungeonCountWitnesses",
    "DungeonPromptKeys",
    "RpgDungeonCountTaskBase",
    "build_monster_chamber_count_plan",
    "build_reachable_chest_count_plan",
    "build_safe_reachable_chest_count_plan",
    "dungeon_prompt_keys",
    "rpg_dungeon_task_defaults",
    "sample_dungeon_count_operand",
    "sample_total_chest_count",
    "run_rpg_dungeon_count_lifecycle",
]
