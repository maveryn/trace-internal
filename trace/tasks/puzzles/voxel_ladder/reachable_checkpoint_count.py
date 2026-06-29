"""Public voxel-ladder task for counting reachable checkpoints."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.tasks.registry import register_task

from ._lifecycle import (
    VoxelLadderBinding,
    load_voxel_ladder_task_defaults,
    run_voxel_ladder_single_query_case,
)
from .shared.annotations import bbox_set_annotation
from .shared.sampling import (
    VoxelLadderPlan,
    checkpoint_bboxes_for_reachable,
    explicit_or_cursor_int,
    route_checkpoint_count,
    sample_voxel_ladder_scene,
)
from .shared.defaults import get_int_range
from .shared.state import DOMAIN, SCENE_ID, VoxelLadderDataset

TASK_ID = "task_puzzles__voxel_ladder__reachable_checkpoint_count"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "reachable_checkpoint_count_query"
PROMPT_QUERY_KEY = "reachable_checkpoint_count"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.reachable_checkpoint_count"


def _build_reachable_count_scene(params, generation_defaults, rng):
    """Construct one reachable checkpoint count dataset."""

    lower, upper = get_int_range(
        params,
        generation_defaults,
        min_key="reachable_checkpoint_count_min",
        max_key="reachable_checkpoint_count_max",
        fallback_min=2,
        fallback_max=5,
    )
    target_count = explicit_or_cursor_int(
        params,
        key="reachable_checkpoint_count",
        lower=lower,
        upper=upper,
        rng=rng,
    )
    return sample_voxel_ladder_scene(
        params=params,
        generation_defaults=generation_defaults,
        rng=rng,
        plan=VoxelLadderPlan(
            route_checkpoint_count=min(
                route_checkpoint_count(params, generation_defaults, rng),
                int(target_count),
            ),
            target_reachable_count=int(target_count),
            unreachable_checkpoint_count=1,
        ),
    )


def _resolve_reachable_prompt_query(_dataset: VoxelLadderDataset) -> str:
    """Return this task's prompt query key."""

    return PROMPT_QUERY_KEY


def _bind_reachable_count_output(
    dataset: VoxelLadderDataset,
    visual,
    selected_query,
    branch_probabilities,
):
    """Bind reachable count and bbox-set over reachable checkpoint cubes."""

    _ = (str(selected_query), dict(branch_probabilities))
    reachable_bboxes = checkpoint_bboxes_for_reachable(
        dataset,
        visual["rendered_scene"].item_bbox_map,
    )
    answer_value = int(dataset.reachable_checkpoint_count)
    if len(reachable_bboxes) != int(answer_value):
        raise ValueError("reachable checkpoint bboxes do not match answer")
    annotation_gt, projected_annotation, witness_symbolic = bbox_set_annotation(
        reachable_bboxes,
        role="reachable_checkpoint_cubes",
    )
    return VoxelLadderBinding(
        answer_gt=TypedValue(type="integer", value=answer_value),
        annotation_gt=annotation_gt,
        projected_annotation=projected_annotation,
        witness_symbolic=witness_symbolic,
        semantic_params={
            "answer_schema": "integer_count",
            "target_reachable_checkpoint_count": answer_value,
        },
        execution_fields={
            "annotation_policy": "bbox_set_reachable_checkpoint_cubes",
        },
    )


@register_task
class PuzzlesVoxelLadderReachableCheckpointCountTask:
    """Count checkpoint cubes reachable from START through cube tops and ladders."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Generate one voxel-ladder reachable-count case."""

        generation_defaults, rendering_defaults, prompt_defaults = (
            load_voxel_ladder_task_defaults(TASK_ID)
        )
        return run_voxel_ladder_single_query_case(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            namespace=_NAMESPACE_BASE,
            prompt_task_key=PROMPT_TASK_KEY,
            instance_seed=int(instance_seed),
            params=params,
            generation_defaults=generation_defaults,
            rendering_defaults=rendering_defaults,
            prompt_defaults=prompt_defaults,
            sample_builder=_build_reachable_count_scene,
            prompt_query_key_resolver=_resolve_reachable_prompt_query,
            output_binder=_bind_reachable_count_output,
            attempt_limit=int(max_attempts),
        )
