"""Public voxel-ladder task for naming the unreachable checkpoint."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.tasks.registry import register_task

from ._lifecycle import (
    VoxelLadderBinding,
    load_voxel_ladder_task_defaults,
    run_voxel_ladder_single_query_case,
)
from .shared.annotations import scalar_bbox_annotation
from .shared.rules import checkpoint_item_id
from .shared.sampling import (
    VoxelLadderPlan,
    route_checkpoint_count,
    sample_voxel_ladder_scene,
    unreachable_checkpoint,
)
from .shared.state import DOMAIN, SCENE_ID

TASK_ID = "task_puzzles__voxel_ladder__unreachable_checkpoint_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "unreachable_checkpoint_label_query"
PROMPT_QUERY_KEY = "unreachable_checkpoint_label"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.unreachable_checkpoint_label"


def _build_unreachable_scene(params, generation_defaults, rng):
    """Construct one unreachable-checkpoint label dataset."""

    return sample_voxel_ladder_scene(
        params=params,
        generation_defaults=generation_defaults,
        rng=rng,
        plan=VoxelLadderPlan(
            route_checkpoint_count=route_checkpoint_count(
                params,
                generation_defaults,
                rng,
            ),
            unreachable_checkpoint_count=1,
        ),
    )


def _resolve_unreachable_prompt_query(_dataset) -> str:
    """Return this task's prompt query key."""

    return PROMPT_QUERY_KEY


def _bind_unreachable_output(dataset, visual, selected_query, branch_probabilities):
    """Bind unreachable checkpoint color and scalar checkpoint bbox."""

    _ = (str(selected_query), dict(branch_probabilities))
    checkpoint = unreachable_checkpoint(dataset)
    item_id = checkpoint_item_id(checkpoint.color_name)
    annotation_gt, projected_annotation, witness_symbolic = scalar_bbox_annotation(
        visual["rendered_scene"].item_bbox_map[item_id],
        role="unreachable_checkpoint_cube",
    )
    return VoxelLadderBinding(
        answer_gt=TypedValue(type="string", value=str(checkpoint.color_name)),
        annotation_gt=annotation_gt,
        projected_annotation=projected_annotation,
        witness_symbolic=witness_symbolic,
        semantic_params={
            "answer_schema": "checkpoint_color_name",
        },
        execution_fields={
            "annotation_policy": "scalar_bbox_unreachable_checkpoint_cube",
            "unreachable_checkpoint_color": str(checkpoint.color_name),
        },
    )


@register_task
class PuzzlesVoxelLadderUnreachableCheckpointLabelTask:
    """Name the single checkpoint cube unreachable from START."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed, *, params, max_attempts):
        """Generate one voxel-ladder unreachable-label case."""

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
            sample_builder=_build_unreachable_scene,
            prompt_query_key_resolver=_resolve_unreachable_prompt_query,
            output_binder=_bind_unreachable_output,
            attempt_limit=int(max_attempts),
        )
