"""Public Tangram task for selecting the missing piece option."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    load_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import build_tangram_output, retry_tangram_generation
from .shared.annotations import missing_piece_bbox_map
from .shared.rules import require_unique_correct_option
from .shared.sampling import make_missing_piece_sample, sample_rng
from .shared.state import DOMAIN, SCENE_ID, RenderedTangramScene, TangramSample

TASK_ID = "task_puzzles__tangram__missing_piece_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "missing_piece_label_query"
PROMPT_QUERY_KEY = "missing_piece_label"
OBJECT_DESCRIPTION = (
    "a Tangram-style assembly with one black missing region and labeled piece options"
)
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.missing_piece_label"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


@register_task
class PuzzlesTangramMissingPieceLabelTask:
    """Choose the labeled piece that matches the black missing Tangram region."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        """Generate one missing-piece option task with role-bound annotation."""

        return retry_tangram_generation(
            build_case=_build_missing_piece_case,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


def _build_missing_piece_case(
    instance_seed: int,
    params: Mapping[str, Any],
) -> TaskOutput:
    """Select the fixed branch, construct options, and bind answer label."""

    selected_branch, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SINGLE_QUERY_ID,
        task_id=TASK_ID,
        namespace=f"{_NAMESPACE_BASE}.branch",
    )
    rng = sample_rng(int(instance_seed), _NAMESPACE_BASE)
    sample, sampling_metadata = make_missing_piece_sample(
        rng=rng,
        params=task_params,
        generation_defaults=_GEN_DEFAULTS,
    )
    _validate_missing_piece_sample(sample)
    return build_tangram_output(
        source_id=TASK_ID,
        namespace=_NAMESPACE_BASE,
        sample=sample,
        answer_gt=TypedValue(
            type="option_letter", value=str(sample.answer_option_label)
        ),
        annotation_builder=_missing_piece_annotation,
        selected_branch=str(selected_branch),
        branch_probabilities=branch_probabilities,
        task_params=task_params,
        generation_defaults=_GEN_DEFAULTS,
        rendering_defaults=_RENDER_DEFAULTS,
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_query_key=PROMPT_QUERY_KEY,
        object_description=OBJECT_DESCRIPTION,
        task_trace_fields=_missing_piece_trace_fields(sample),
        task_scene_relations=_missing_piece_scene_relations(sample),
        sampling_metadata=sampling_metadata,
        instance_seed=int(instance_seed),
    )


def _validate_missing_piece_sample(sample: TangramSample) -> None:
    """Validate the correct option and answer label are bound together."""

    require_unique_correct_option(sample.option_specs)
    correct_options = [
        option for option in sample.option_specs if bool(option.is_correct)
    ]
    correct = correct_options[0]
    if str(correct.option_label) != str(sample.answer_option_label):
        raise ValueError("Tangram missing-piece answer label drifted from options")
    if str(correct.option_id) != str(sample.correct_option_panel_id):
        raise ValueError("Tangram missing-piece correct option id drifted")
    if str(correct.shape_id) != str(sample.target_shape_id):
        raise ValueError("Tangram missing-piece option shape does not match target")


def _missing_piece_annotation(
    rendered_scene: RenderedTangramScene,
    sample: TangramSample,
):
    """Project missing region and selected option to bbox_map."""

    return missing_piece_bbox_map(
        piece_bbox_map=rendered_scene.piece_bbox_map,
        option_panel_bbox_map=rendered_scene.option_panel_bbox_map,
        target_piece_id=str(sample.target_piece_id),
        correct_option_panel_id=str(sample.correct_option_panel_id),
    )


def _missing_piece_trace_fields(sample: TangramSample) -> dict[str, Any]:
    """Return task-owned trace fields for labeled visual options."""

    return {
        "option_specs": [asdict(option) for option in sample.option_specs],
        "option_count": int(sample.option_count),
        "option_count_range": list(sample.option_count_range),
        "correct_option_index": sample.correct_option_index,
        "answer_option_label": str(sample.answer_option_label),
        "correct_option_panel_id": str(sample.correct_option_panel_id),
    }


def _missing_piece_scene_relations(sample: TangramSample) -> dict[str, Any]:
    """Return task-owned symbolic relation metadata for missing-piece matching."""

    return {
        "option_count": int(sample.option_count),
        "answer_option_label": str(sample.answer_option_label),
        "correct_option_panel_id": str(sample.correct_option_panel_id),
    }


__all__ = [
    "PROMPT_QUERY_KEY",
    "PuzzlesTangramMissingPieceLabelTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
