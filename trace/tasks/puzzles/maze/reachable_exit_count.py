"""Public maze task for counting exits reachable from START."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import (
    build_maze_task_output,
    prepare_maze_visual_case,
    resolve_maze_public_branch,
    resolve_maze_scene_variant,
    retry_maze_generation,
)
from .shared.annotations import item_bbox_set
from .shared.sampling import sample_reachable_exit_count_maze
from .shared.state import DOMAIN, SCENE_ID

TASK_ID = "task_puzzles__maze__reachable_exit_count"
PROMPT_TASK_KEY = "reachable_exit_count_query"
PROMPT_QUERY_KEY = "reachable_exit_count"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.reachable_exit_count"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


@register_task
class PuzzlesMazeReachableExitCountTask:
    """Count all labeled boundary exits connected to START."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = (SINGLE_QUERY_ID,)

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        """Generate one reachable-exit count task with bbox-set annotation."""

        return retry_maze_generation(
            build_case=_build_reachable_exit_count_case,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=max_attempts,
        )


def _build_reachable_exit_count_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> TaskOutput:
    """Sample a maze, count reachable exits, and bind bbox-set witnesses."""

    selected_branch, branch_probabilities, task_params = resolve_maze_public_branch(
        instance_seed=int(instance_seed),
        params=params,
        task_id=TASK_ID,
        namespace=_NAMESPACE_BASE,
    )
    scene_variant, scene_variant_probabilities = resolve_maze_scene_variant(
        params=task_params,
        instance_seed=int(instance_seed),
        namespace=_NAMESPACE_BASE,
    )
    dataset = sample_reachable_exit_count_maze(
        scene_variant=str(scene_variant),
        params=task_params,
        instance_seed=int(instance_seed),
        generation_defaults=_GEN_DEFAULTS,
        max_attempts=int(max_attempts),
    )
    visual = prepare_maze_visual_case(
        dataset=dataset,
        params=task_params,
        generation_defaults=_GEN_DEFAULTS,
        rendering_defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        scene_variant=str(scene_variant),
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_query_key=PROMPT_QUERY_KEY,
        prompt_dynamic_slots={},
        namespace=_NAMESPACE_BASE,
    )
    supporting_item_ids = [str(value) for value in dataset["supporting_item_ids"]]
    annotation_gt, projected_annotation, witness_symbolic = item_bbox_set(
        visual["rendered_scene"].item_bbox_map,
        supporting_item_ids,
    )
    answer_gt = TypedValue(type="integer", value=int(dataset["answer_value"]))
    reachable_labels = [str(value) for value in dataset["reachable_exit_labels"]]
    if int(answer_gt.value) != len(reachable_labels):
        raise ValueError("maze reachable-exit answer drifted from reachable labels")
    if len(supporting_item_ids) != len(reachable_labels):
        raise ValueError("maze reachable-exit annotation count drifted from answer")
    return build_maze_task_output(
        dataset=dataset,
        visual=visual,
        public_query_id=str(selected_branch),
        branch_probabilities=branch_probabilities,
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        projected_annotation=projected_annotation,
        witness_symbolic=witness_symbolic,
        prompt_query_key=PROMPT_QUERY_KEY,
        semantic_params={
            "scene_variant_probabilities": dict(scene_variant_probabilities),
        },
        relation_fields={},
        execution_fields={
            "scene_variant_probabilities": dict(scene_variant_probabilities),
        },
    )
