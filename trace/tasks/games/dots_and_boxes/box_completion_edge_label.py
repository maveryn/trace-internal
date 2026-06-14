"""Choose which dashed missing edge would complete a dots-and-boxes box."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.mcq import option_label_for_index
from trace.tasks.shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant

from ._lifecycle import DotsAndBoxesAttemptResult, DotsAndBoxesObjectivePlan, run_dots_and_boxes_lifecycle
from .shared.defaults import DEFAULTS, DOTS_AND_BOXES_NAMESPACE, SCENE_ID
from .shared.rules import build_dots_and_boxes_completion_option_board_state
from .shared.state import DotsAndBoxesBoardShapeAxis


TASK_ID = "task_games__dots_and_boxes__box_completion_edge_label"
QUERY_ID = "box_completion_edge_label"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS = (QUERY_ID,)
OPTION_LABELS = tuple(option_label_for_index(index) for index in range(6))
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _resolve_answer_label(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> tuple[str, Mapping[str, float]]:
    """Resolve the correct visible option label from the fixed A..F set."""

    raw_support = params.get("option_label_support", gen_defaults.get("option_label_support", DEFAULTS.option_label_support))
    support = tuple(str(label) for label in raw_support)
    if support != OPTION_LABELS:
        raise ValueError("dots-and-boxes option_label_support must be exactly A..F")
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{DOTS_AND_BOXES_NAMESPACE}.box_completion_edge_label.answer"),
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=support,
        explicit_key="target_label",
        weights_key="option_label_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=dict(probabilities),
        supported_variants=support,
        balance_flag_key="balanced_target_answer_sampling",
        explicit_key="target_label",
        weights_key="option_label_weights",
        sampling_namespace=f"{DOTS_AND_BOXES_NAMESPACE}.box_completion_edge_label.answer",
    )
    return str(selected), dict(probabilities)


def _prepare_box_completion_edge_objective(
    instance_seed: int,
    params: Mapping[str, Any],
    query_probabilities: Mapping[str, float],
    query_id: str,
    board_shape: DotsAndBoxesBoardShapeAxis,
) -> DotsAndBoxesObjectivePlan:
    """Bind the six-option box-completion move objective."""

    del query_probabilities, query_id
    answer_label, answer_label_probabilities = _resolve_answer_label(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
    )

    def construct_attempt(rng: Any) -> DotsAndBoxesAttemptResult:
        board_state = build_dots_and_boxes_completion_option_board_state(
            rng=rng,
            answer_label=str(answer_label),
            box_rows=int(board_shape.box_rows),
            box_cols=int(board_shape.box_cols),
            option_count=6,
        )
        return DotsAndBoxesAttemptResult(
            board_state=board_state,
            annotation_kind="edge_point_pair",
            annotation_entity_ids=(str(board_state.answer_edge_id),),
            execution_extra={
                "answer_label": str(answer_label),
                "answer_edge_id": str(board_state.answer_edge_id),
                "option_labels": list(OPTION_LABELS),
            },
        )

    return DotsAndBoxesObjectivePlan(
        prompt_query_key=PROMPT_QUERY_KEY,
        annotation_example_shape="point_pair_set",
        answer_gt=TypedValue(type="option_letter", value=str(answer_label)),
        query_params={
            "answer_label": str(answer_label),
            "option_count": 6,
            "option_labels": list(OPTION_LABELS),
            "prompt_query_key": PROMPT_QUERY_KEY,
            "answer_label_probabilities": dict(answer_label_probabilities),
        },
        attempt_namespace=TASK_ID,
        construct_attempt=construct_attempt,
    )


@register_task
class GamesDotsAndBoxesBoxCompletionEdgeLabelTask:
    """Choose the dashed candidate edge that immediately completes one box."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_dots_and_boxes_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_box_completion_edge_objective,
        )


__all__ = ["GamesDotsAndBoxesBoxCompletionEdgeLabelTask"]
