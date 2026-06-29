"""Public Tents task for counting legal candidate cells."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.tasks.registry import register_task

from ._lifecycle import (
    TentsObjectiveBinding,
    TentsSceneTask,
)
from .shared.annotations import candidate_bbox_set_annotation
from .shared.sampling import sample_neighbor_legality_count_board
from .shared.state import DOMAIN, SCENE_ID, TentsSample

TASK_ID = "task_puzzles__tents__valid_candidate_count"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "valid_candidate_count_query"
PROMPT_QUERY_KEY = "valid_candidate_count"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.valid_candidate_count"


def _sample_valid_candidate_count(params, instance_seed, generation_defaults, rng):
    """Construct the objective sample with a sampled legal-candidate count."""

    return sample_neighbor_legality_count_board(
        params=params,
        instance_seed=int(instance_seed),
        generation_defaults=generation_defaults,
        rng=rng,
    )


def _bind_valid_candidate_count_output(
    sample: TentsSample,
    visual,
    selected_query,
    branch_probabilities,
):
    """Validate count cardinality and bind legal candidate bboxes only."""

    _ = (str(selected_query), dict(branch_probabilities))
    legal_labels = [
        str(spec.label) for spec in sample.candidate_specs if bool(spec.is_legal)
    ]
    if len(legal_labels) != len(sample.legal_candidate_cells):
        raise ValueError("Tents candidate specs drifted from legal cell set")
    answer_value = len(legal_labels)
    if sample.target_count_range is None:
        raise ValueError("Tents count sample must record target_count_range")
    lower, upper = sample.target_count_range
    if not int(lower) <= int(answer_value) <= int(upper):
        raise ValueError("Tents count answer drifted outside configured support")

    annotation_gt, projected_annotation, witness_symbolic = (
        candidate_bbox_set_annotation(
            visual["rendered_scene"].item_bbox_map,
            legal_labels,
        )
    )
    return TentsObjectiveBinding(
        answer_gt=TypedValue(type="integer", value=int(answer_value)),
        annotation_gt=annotation_gt,
        projected_annotation=projected_annotation,
        witness_symbolic=witness_symbolic,
        semantic_params={
            "target_count_range": [int(lower), int(upper)],
            "answer_schema": "integer",
        },
        execution_fields={
            "legal_candidate_labels": [str(label) for label in legal_labels],
            "annotation_policy": "bbox_set_legal_candidate_cells",
            "supporting_item_ids": [f"candidate_{label}" for label in legal_labels],
        },
    )


@register_task
class PuzzlesTentsValidCandidateCountTask(TentsSceneTask):
    """Count labeled candidate cells that can legally hold the marked tree's tent."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    prompt_task_key = PROMPT_TASK_KEY
    prompt_query_key = PROMPT_QUERY_KEY
    namespace = _NAMESPACE_BASE
    sample_builder = staticmethod(_sample_valid_candidate_count)
    output_binder = staticmethod(_bind_valid_candidate_count_output)

    def generate(self, instance_seed, *, params, max_attempts):
        """Generate one legal-candidate count case."""

        output = super().generate(
            instance_seed,
            params=params,
            max_attempts=max_attempts,
        )
        return output
