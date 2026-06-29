"""Public logic-grid king-non-touch completion task."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import build_logic_grid_task_output, prepare_logic_grid_visual_case
from .shared.sampling import sample_king_non_touch_dataset
from .shared.state import DOMAIN, SCENE_ID


TASK_ID = "task_puzzles__logic_grid__grid_king_non_touch_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_TASK_KEY = "grid_king_non_touch_label_query"
PROMPT_QUERY_KEY = "king_non_touch"
_NAMESPACE_BASE = f"{DOMAIN}.{SCENE_ID}.grid_king_non_touch_label"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


@register_task
class PuzzlesLogicGridKingNonTouchLabelTask:
    """Choose the option allowed by the no-touching-identical-shapes rule."""

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
        """Generate one king-non-touch grid task with bbox-map annotation."""

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
        raise RuntimeError("logic-grid king generation failed without a captured error")


def _generate_once(*, instance_seed: int, params: Mapping[str, Any]) -> TaskOutput:
    """Sample the fixed no-touch puzzle and assemble output."""

    selected_branch, branch_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id=SINGLE_QUERY_ID,
        task_id=TASK_ID,
        namespace=f"{_NAMESPACE_BASE}.branch",
    )
    if str(selected_branch) != SINGLE_QUERY_ID:
        raise ValueError(f"unsupported logic-grid king branch: {selected_branch}")

    dataset = sample_king_non_touch_dataset(
        params=task_params,
        instance_seed=int(instance_seed),
        generation_defaults=_GEN_DEFAULTS,
        namespace_base=f"{_NAMESPACE_BASE}.dataset",
    )
    visual = prepare_logic_grid_visual_case(
        dataset=dataset,
        params=task_params,
        generation_defaults=_GEN_DEFAULTS,
        rendering_defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=_NAMESPACE_BASE,
        prompt_task_key=PROMPT_TASK_KEY,
        prompt_query_key=PROMPT_QUERY_KEY,
        prompt_dynamic_slots={},
    )
    semantic_rule = "king_non_touch"
    return build_logic_grid_task_output(
        dataset=dataset,
        visual=visual,
        selected_branch=str(selected_branch),
        branch_probabilities=branch_probabilities,
        semantic_rule=semantic_rule,
        semantic_params={
            "query_neighbor_count": int(len(dataset.extra_trace["neighbor_coords"])),
        },
        relation_fields={},
        execution_fields={
            "neighbor_coords": [list(coords) for coords in dataset.extra_trace["neighbor_coords"]],
            "forced_neighbor_coords": [
                list(coords) for coords in dataset.extra_trace["forced_neighbor_coords"]
            ],
            "forced_neighbor_types": [
                str(value) for value in dataset.extra_trace["forced_neighbor_types"]
            ],
            "query_neighbor_object_types": [
                str(value) for value in dataset.extra_trace["query_neighbor_object_types"]
            ],
            "valid_option_object_types": [
                str(value) for value in dataset.extra_trace["valid_option_object_types"]
            ],
        },
    )


__all__ = [
    "PROMPT_QUERY_KEY",
    "PuzzlesLogicGridKingNonTouchLabelTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
