"""Choose the labeled Connect Four column that wins immediately."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.connect_four._lifecycle import ConnectFourObjectivePlan, run_connect_four_lifecycle
from trace.tasks.games.connect_four.shared.defaults import SCENE_ID
from trace.tasks.games.connect_four.shared.prompts import (
    connect_four_object_description,
    connect_four_output_slots,
    connect_four_rule_slots,
    json_examples_for_label_answer,
)
from trace.tasks.games.connect_four.shared.sampling import (
    resolve_connect_four_scene_axes,
    sample_winning_column_label_scene,
)
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults


TASK_ID = "task_games__connect_four__winning_move_column_label"
QUERY_ID = "winning_move_column_label"
PROMPT_QUERY_KEY = QUERY_ID
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _prepare_winning_column_label_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    selected_query_id: str,
    _query_probabilities: Mapping[str, float],
) -> ConnectFourObjectivePlan:
    """Bind single winning-column label semantics and construction."""

    axes = resolve_connect_four_scene_axes(
        int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        namespace_suffix=str(selected_query_id),
    )

    def construct_attempt(rng):
        return sample_winning_column_label_scene(
            rng=rng,
            axes=axes,
            params=task_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
        )

    def prompt_slots(sample) -> dict[str, Any]:
        json_example, json_example_answer_only = json_examples_for_label_answer()
        return {
            "object_description": connect_four_object_description(str(sample.scene_variant)),
            **connect_four_rule_slots(current_player=int(sample.current_player)),
            **connect_four_output_slots(
                prompt_query_key=PROMPT_QUERY_KEY,
                json_example=json_example,
                json_example_answer_only=json_example_answer_only,
            ),
        }

    def query_spec_params(sample) -> dict[str, Any]:
        return {
            "answer_label": str(sample.answer_label),
            "answer_column": int(sample.answer_column),
            "answer_support": [str(label) for label in sample.column_labels],
            "threat_kind": str(sample.threat_kind),
            "threat_kind_probabilities": dict(sample.threat_kind_probabilities),
        }

    def execution_updates(sample) -> dict[str, Any]:
        return {
            "answer_label": str(sample.answer_label),
            "answer_column": int(sample.answer_column),
            "answer_support": [str(label) for label in sample.column_labels],
            "column_labels": [str(label) for label in sample.column_labels],
            "winning_line_coords": [[int(row), int(col)] for row, col in sample.winning_line_coords],
            "threat_kind": str(sample.threat_kind),
        }

    return ConnectFourObjectivePlan(
        axes=axes,
        attempt_namespace=TASK_ID,
        construct_attempt=construct_attempt,
        prompt_query_key=PROMPT_QUERY_KEY,
        prompt_dynamic_slots=prompt_slots,
        answer_gt=lambda sample: TypedValue(type="string", value=str(sample.answer_label)),
        annotation_coords=lambda sample: sample.evaluation.annotation_coords,
        render_marked_square=lambda _sample: None,
        render_column_labels=lambda sample: sample.column_labels,
        query_spec_params=query_spec_params,
        execution_updates=execution_updates,
    )


@register_task
class GamesConnectFourWinningMoveColumnLabelTask:
    """Return the visible column label for the immediate winning drop."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one board with a unique immediate winning column."""

        return run_connect_four_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_winning_column_label_objective,
        )


__all__ = ["GamesConnectFourWinningMoveColumnLabelTask"]
