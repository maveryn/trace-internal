"""Public logic-grid uniqueness completion task."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.sampling import support_probability_map, uniform_choice_with_probabilities
from trace.core.seed import spawn_rng
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import build_logic_grid_task_output, prepare_logic_grid_visual_case
from .shared.sampling import sample_uniqueness_dataset
from .shared.state import (
    DOMAIN,
    ROW_AND_COLUMN_AXIS,
    SCENE_ID,
    SUPPORTED_UNIQUENESS_AXES,
)


TASK_ID = "task_puzzles__logic_grid__grid_uniqueness_completion_label"
AXIS_UNIQUENESS_QUERY = "axis_uniqueness"
ROW_AND_COLUMN_UNIQUENESS_QUERY = "row_and_column_uniqueness"
SUPPORTED_QUERY_IDS = (AXIS_UNIQUENESS_QUERY, ROW_AND_COLUMN_UNIQUENESS_QUERY)
PROMPT_TASK_KEY = "grid_uniqueness_completion_label_query"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.grid_uniqueness_completion_label"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


@register_task
class PuzzlesLogicGridUniquenessCompletionLabelTask:
    """Choose the option that completes a row/column uniqueness grid."""

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
        """Generate one logic-grid MCQ with role-bound bbox-map annotation."""

        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                return _generate_once(
                    instance_seed=int(instance_seed) + int(attempt_index),
                    params=params,
                )
            except ValueError as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        raise RuntimeError("logic-grid uniqueness generation failed without a captured error")


def _generate_once(*, instance_seed: int, params: Mapping[str, Any]) -> TaskOutput:
    """Select the uniqueness branch, sample its board, and assemble output."""

    selected_branch, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=AXIS_UNIQUENESS_QUERY,
        task_id=TASK_ID,
        namespace=f"{_NAMESPACE_BASE}.branch",
    )
    uniqueness_axis: str | None = None
    uniqueness_axis_probabilities: dict[str, float] = {}
    if str(selected_branch) == AXIS_UNIQUENESS_QUERY:
        uniqueness_axis, uniqueness_axis_probabilities = _select_uniqueness_axis(
            params=task_params,
            instance_seed=int(instance_seed),
        )
        axis_kind = str(uniqueness_axis)
    elif str(selected_branch) == ROW_AND_COLUMN_UNIQUENESS_QUERY:
        axis_kind = ROW_AND_COLUMN_AXIS
    else:
        raise ValueError(f"unsupported logic-grid uniqueness branch: {selected_branch}")

    dataset = sample_uniqueness_dataset(
        axis_kind=str(axis_kind),
        params=task_params,
        instance_seed=int(instance_seed),
        generation_defaults=_GEN_DEFAULTS,
        namespace_base=f"{_NAMESPACE_BASE}.dataset",
    )
    semantic_rule = str(dataset.solver_trace["rule_type"])
    visual = prepare_logic_grid_visual_case(
        dataset=dataset,
        params=task_params,
        generation_defaults=_GEN_DEFAULTS,
        rendering_defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=_NAMESPACE_BASE,
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_query_key=str(selected_branch),
        prompt_dynamic_slots={"uniqueness_axis": str(uniqueness_axis or "")},
    )
    return build_logic_grid_task_output(
        dataset=dataset,
        visual=visual,
        selected_branch=str(selected_branch),
        branch_probabilities=branch_probabilities,
        semantic_rule=semantic_rule,
        semantic_params={
            "internal_query_id": semantic_rule,
            "uniqueness_axis": uniqueness_axis,
            "uniqueness_axis_probabilities": dict(uniqueness_axis_probabilities),
        },
        relation_fields={
            "internal_rule": semantic_rule,
            "uniqueness_axis": uniqueness_axis,
        },
        execution_fields={
            "internal_query_id": semantic_rule,
            "uniqueness_axis": uniqueness_axis,
            "uniqueness_axis_probabilities": dict(uniqueness_axis_probabilities),
        },
    )


def _select_uniqueness_axis(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[str, dict[str, float]]:
    """Sample row or column using explicit support rather than seed modulo."""

    explicit = params.get("uniqueness_axis", params.get("axis"))
    if explicit is not None:
        selected = str(explicit).strip().lower()
        if selected not in set(SUPPORTED_UNIQUENESS_AXES):
            raise ValueError(f"unsupported uniqueness_axis: {explicit}")
        return (
            str(selected),
            support_probability_map(SUPPORTED_UNIQUENESS_AXES, selected=selected, sort_keys=True),
        )
    rng = spawn_rng(int(instance_seed), f"{_NAMESPACE_BASE}.uniqueness_axis")
    selected, probabilities = uniform_choice_with_probabilities(
        rng,
        SUPPORTED_UNIQUENESS_AXES,
        sort_keys=True,
    )
    return str(selected), dict(probabilities)


__all__ = [
    "AXIS_UNIQUENESS_QUERY",
    "PuzzlesLogicGridUniquenessCompletionLabelTask",
    "ROW_AND_COLUMN_UNIQUENESS_QUERY",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
