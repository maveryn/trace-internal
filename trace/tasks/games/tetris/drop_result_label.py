"""Result-board option label after a fixed Tetris drop."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import TetrisObjectivePlan, run_tetris_lifecycle
from .shared.prompts import format_json_examples
from .shared.rendering import RENDER_MODE_RESULT_OPTIONS
from .shared.sampling import build_drop_result_sample, sample_label
from .shared.state import OPTION_LABELS


TASK_ID = "task_games__tetris__drop_result_label"
SUPPORTED_QUERY_IDS = ("no_clear_result", "single_clear_result", "multi_clear_result")
_CLEAR_COUNT_BY_QUERY = {
    "no_clear_result": 0,
    "single_clear_result": 1,
    "multi_clear_result": 2,
}
JSON_EXAMPLE, JSON_EXAMPLE_ANSWER_ONLY = format_json_examples(annotation=[520, 180, 760, 520], answer="B")


def _prepare_drop_result_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    selected_query: str,
    query_probabilities: Mapping[str, float],
    axes,
) -> TetrisObjectivePlan:
    """Bind the fixed-drop clear-count branch and answer option label."""

    if str(selected_query) not in _CLEAR_COUNT_BY_QUERY:
        raise ValueError(f"unsupported Tetris drop-result query: {selected_query}")
    target_clear_count = int(_CLEAR_COUNT_BY_QUERY[str(selected_query)])
    labels = OPTION_LABELS[: int(axes.option_count)]
    answer_label, answer_label_probabilities = sample_label(
        int(instance_seed),
        namespace=f"{TASK_ID}.answer_label.{int(axes.option_count)}",
        labels=labels,
    )

    def construct_attempt(rng, resolved_axes):
        return build_drop_result_sample(
            rng,
            scene_variant=str(resolved_axes.scene_variant),
            board_rows=int(resolved_axes.board_rows),
            board_cols=int(resolved_axes.board_cols),
            target_clear_count=int(target_clear_count),
            option_count=int(resolved_axes.option_count),
            answer_label=str(answer_label),
        )

    return TetrisObjectivePlan(
        attempt_namespace=f"games.tetris.drop_result.{str(selected_query)}.{str(answer_label)}",
        prompt_query_key=str(selected_query),
        answer_hint_key="answer_hint_drop_result_label",
        annotation_hint_key="annotation_hint_drop_result_label",
        json_example=JSON_EXAMPLE,
        json_example_answer_only=JSON_EXAMPLE_ANSWER_ONLY,
        render_mode=RENDER_MODE_RESULT_OPTIONS,
        query_params={
            "target_clear_count": int(target_clear_count),
            "drop_result_branch_probabilities": dict(query_probabilities),
            "answer_label": str(answer_label),
            "answer_label_probabilities": dict(answer_label_probabilities),
        },
        construct_attempt=construct_attempt,
    )


@register_task
class GamesTetrisDropResultLabelTask:
    """Choose the labeled board produced by the shown fixed drop."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_tetris_lifecycle(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_drop_result_objective,
        )


__all__ = ["GamesTetrisDropResultLabelTask"]
