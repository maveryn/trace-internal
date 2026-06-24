"""Scene-private lifecycle helpers for RPG tactical map public tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.output import (
    bbox_set_projection,
    rounded_bbox,
    rpg_tactical_map_render_spec,
    rpg_tactical_map_scene_ir,
)
from .shared.prompts import build_rpg_tactical_map_task_prompt_with_default_slots
from .shared.rendering import (
    DEFAULT_TILE_PX,
    SCENE_ID,
    render_rpg_tactical_map_scene,
    resolve_tactical_map_render_params,
)
from .shared.state import RpgTacticalMapScene, RpgTacticalTile


TileSelector = Callable[[RpgTacticalMapScene], Sequence[RpgTacticalTile]]
RenderMapBuilder = Callable[[RpgTacticalMapScene, Sequence[str]], Mapping[str, Any]]
CountPlanBuilder = Callable[[int, Mapping[str, Any], Mapping[str, float], str], "RpgTacticalMapTileCountPlan"]


@dataclass(frozen=True)
class RpgTacticalMapTileCountPlan:
    """Task-owned count semantics consumed by neutral tactical-map rendering."""

    prompt_query_key: str
    prompt_slots: Mapping[str, str]
    answer_hint_key: str
    annotation_hint_key: str
    json_example_key: str
    json_example_answer_only_key: str
    min_answer_count: int
    max_answer_count: int
    query_params: Mapping[str, Any]
    relation_fields: Mapping[str, Any]
    execution_fields: Mapping[str, Any]
    witness_fields: Mapping[str, Any]
    select_tiles: TileSelector
    build_render_map: RenderMapBuilder
    failure_label: str = "tile count"


def run_rpg_tactical_map_tile_count_lifecycle(
    *,
    task_id: str,
    domain: str,
    supported_query_ids: tuple[str, ...],
    prompt_defaults_source: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
    prepare_plan: CountPlanBuilder,
) -> TaskOutput:
    """Run neutral retry, prompt, trace, and output plumbing for tile-count tasks."""

    query_id, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=tuple(str(value) for value in supported_query_ids),
        default_query_id=SINGLE_QUERY_ID,
        task_id=str(task_id),
        namespace=f"{task_id}:query",
    )
    plan = prepare_plan(
        int(instance_seed),
        task_params,
        dict(query_probabilities),
        str(query_id),
    )
    if int(plan.min_answer_count) < 0 or int(plan.max_answer_count) < int(plan.min_answer_count):
        raise ValueError("tile count range must satisfy 0 <= min <= max")
    render_params = resolve_tactical_map_render_params(
        task_params,
        rendering_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:canvas_profile",
    )
    _prompt_defaults, prompt_artifacts = build_rpg_tactical_map_task_prompt_with_default_slots(
        domain=str(domain),
        scene_id=SCENE_ID,
        prompt_defaults_source=prompt_defaults_source,
        prompt_query_key=str(plan.prompt_query_key),
        answer_hint_key=str(plan.answer_hint_key),
        annotation_hint_key=str(plan.annotation_hint_key),
        json_example_key=str(plan.json_example_key),
        json_example_answer_only_key=str(plan.json_example_answer_only_key),
        context_label=str(task_id),
        slots=dict(plan.prompt_slots),
        instance_seed=int(instance_seed),
    )

    selected_scene: RpgTacticalMapScene | None = None
    selected_tiles: list[RpgTacticalTile] | None = None
    rejection_notes: list[str] = []
    for attempt_index in range(max(1, int(max_attempts))):
        candidate_scene = render_rpg_tactical_map_scene(
            int(instance_seed) + int(attempt_index) * 7919,
            width=int(render_params["canvas_width"]),
            height=int(render_params["canvas_height"]),
            grid_cols=int(render_params["grid_cols"]),
            grid_rows=int(render_params["grid_rows"]),
            tile_px=int(render_params.get("tile_px", DEFAULT_TILE_PX)),
            render_metadata=render_params,
        )
        candidate_tiles = list(plan.select_tiles(candidate_scene))
        candidate_count = len(candidate_tiles)
        if int(plan.min_answer_count) <= int(candidate_count) <= int(plan.max_answer_count):
            selected_scene = candidate_scene
            selected_tiles = candidate_tiles
            break
        rejection_notes.append(
            f"{plan.failure_label} {candidate_count} outside {int(plan.min_answer_count)}..{int(plan.max_answer_count)}"
        )
    if selected_scene is None or selected_tiles is None:
        raise ValueError("failed to generate valid tactical-map tile count: " + "; ".join(rejection_notes[-3:]))

    counted_tile_ids = [str(tile.tile_id) for tile in selected_tiles]
    annotation_value = [rounded_bbox(tile.bbox_xyxy) for tile in selected_tiles]
    render_map = dict(plan.build_render_map(selected_scene, counted_tile_ids))
    query_params = {
        "query_id": str(query_id),
        "prompt_query_key": str(plan.prompt_query_key),
        "query_id_probabilities": dict(query_probabilities),
        **dict(plan.query_params),
        "answer_count": int(len(selected_tiles)),
        "answer_count_range": [int(plan.min_answer_count), int(plan.max_answer_count)],
        "counted_tile_ids": list(counted_tile_ids),
        "canvas_profile": str(render_params.get("canvas_profile", "")),
        "canvas_profile_probabilities": dict(render_params.get("canvas_profile_probabilities", {})),
    }
    trace_payload = {
        "scene_ir": rpg_tactical_map_scene_ir(
            domain=str(domain),
            scene_id=SCENE_ID,
            scene=selected_scene,
            relations={
                **dict(plan.relation_fields),
                "counted_tile_ids": list(counted_tile_ids),
                "answer_count": int(len(selected_tiles)),
            },
        ),
        "query_spec": {
            "task_id": str(task_id),
            "query_id": str(query_id),
            "prompt_query_key": str(plan.prompt_query_key),
            "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": query_params,
        },
        "render_spec": rpg_tactical_map_render_spec(selected_scene, scene_id=SCENE_ID),
        "render_map": render_map,
        "execution_trace": {
            "query_id": str(query_id),
            "prompt_query_key": str(plan.prompt_query_key),
            "scene_id": SCENE_ID,
            "answer": int(len(selected_tiles)),
            "counted_tile_ids": list(counted_tile_ids),
            "terrain_by_tile_id": {
                str(tile.tile_id): str(tile.terrain)
                for tile in selected_scene.tiles
            },
            "renderer": dict(selected_scene.trace),
            **dict(plan.execution_fields),
        },
        "witness_symbolic": {
            "answer_count": int(len(selected_tiles)),
            "counted_tile_ids": list(counted_tile_ids),
            "counted_tile_bboxes": [list(bbox) for bbox in annotation_value],
            **dict(plan.witness_fields),
        },
        "projected_annotation": bbox_set_projection(annotation_value),
    }
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        answer_gt=TypedValue(type="integer", value=int(len(selected_tiles))),
        annotation_gt=TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_value]),
        image=selected_scene.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(query_id),
    )


__all__ = [
    "CountPlanBuilder",
    "RenderMapBuilder",
    "RpgTacticalMapTileCountPlan",
    "TileSelector",
    "run_rpg_tactical_map_tile_count_lifecycle",
]
