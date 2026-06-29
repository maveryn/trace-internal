"""Public voxel-ladder task for selecting the route checkpoint sequence."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.tasks.registry import register_task

from ._lifecycle import (
    VoxelLadderBinding,
    load_voxel_ladder_task_defaults,
    run_voxel_ladder_single_query_case,
)
from .shared.annotations import option_bbox_annotation
from .shared.sampling import (
    VoxelLadderPlan,
    explicit_or_cursor_choice,
    route_checkpoint_count,
    route_option_count,
    sample_voxel_ladder_scene,
)
from .shared.state import DOMAIN, OPTION_LABELS, SCENE_ID, VoxelLadderDataset

TASK_ID = "task_puzzles__voxel_ladder__checkpoint_sequence_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "checkpoint_sequence_label_query"
PROMPT_QUERY_KEY = "checkpoint_sequence_label"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.checkpoint_sequence_label"


@register_task
class PuzzlesVoxelLadderCheckpointSequenceLabelTask:
    """Choose the color-sequence option for the shortest START-to-GOAL route."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def _build_sequence_scene(self, params, generation_defaults, rng):
        """Construct one route-sequence option dataset."""

        option_count = route_option_count(params, generation_defaults, rng)
        answer_label = explicit_or_cursor_choice(
            params,
            key="answer_option_label",
            support=OPTION_LABELS[: int(option_count)],
            rng=rng,
        )
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
                route_option_count=int(option_count),
                answer_option_label=str(answer_label),
                add_reachable_branch=True,
            ),
        )

    def _resolve_sequence_prompt_query(self, _dataset: VoxelLadderDataset) -> str:
        """Return this task's prompt query key."""

        return PROMPT_QUERY_KEY

    def _bind_sequence_output(
        self,
        dataset: VoxelLadderDataset,
        visual,
        selected_query,
        branch_probabilities,
    ):
        """Bind selected option label and scalar option-panel bbox."""

        _ = (str(selected_query), dict(branch_probabilities))
        self._validate_route_option_cards(dataset)
        correct_options = [
            option.option_label
            for option in dataset.option_specs
            if bool(option.is_correct)
        ]
        if len(correct_options) != 1:
            raise ValueError("voxel-ladder sequence task must have one correct option")
        answer_label = str(correct_options[0])
        annotation_gt, projected_annotation, witness_symbolic = option_bbox_annotation(
            visual["rendered_scene"].item_bbox_map,
            answer_label,
        )
        return VoxelLadderBinding(
            answer_gt=TypedValue(type="option_letter", value=answer_label),
            annotation_gt=annotation_gt,
            projected_annotation=projected_annotation,
            witness_symbolic=witness_symbolic,
            semantic_params={
                "answer_schema": "option_letter",
                "option_count": int(len(dataset.option_specs)),
            },
            execution_fields={
                "annotation_policy": "scalar_bbox_selected_route_sequence_option",
                "route_checkpoint_sequence": list(dataset.route_checkpoint_sequence),
            },
        )

    def _validate_route_option_cards(self, dataset: VoxelLadderDataset) -> None:
        """Check option-card uniqueness before binding the answer label."""

        option_labels = [str(option.option_label) for option in dataset.option_specs]
        option_sequences = [
            tuple(str(item) for item in option.sequence_items)
            for option in dataset.option_specs
        ]
        if option_labels != list(OPTION_LABELS[: len(option_labels)]):
            raise ValueError("voxel-ladder option labels must be ordered A..F")
        if len(option_sequences) != len(set(option_sequences)):
            raise ValueError("voxel-ladder option sequences must be unique")
        if tuple(dataset.route_checkpoint_sequence) not in set(option_sequences):
            raise ValueError("voxel-ladder options must include the route sequence")

    def generate(self, instance_seed, *, params, max_attempts):
        """Generate one voxel-ladder route-sequence label case."""

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
            sample_builder=self._build_sequence_scene,
            prompt_query_key_resolver=self._resolve_sequence_prompt_query,
            output_binder=self._bind_sequence_output,
            attempt_limit=int(max_attempts),
        )
