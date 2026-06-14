"""Count fixture elements with a target state."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import ResolvedSurfaceFixtureAxes, SurfaceFixturePlan, run_surface_fixture_lifecycle
from .shared.metrics import build_state_surface_data
from .shared.state import SCENE_ID, STATE_SUPPORT_BY_SCENE_VARIANT


TASK_ID = "task_three_d__surface_fixture__state_element_count"
QUERY_ID = "single"
PROMPT_QUERY_KEY = "element_state_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "three_d",
    SCENE_ID,
    task_id=TASK_ID,
)


def _prepare_state_objective(
    instance_seed: int,
    params: Mapping[str, Any],
    axes: ResolvedSurfaceFixtureAxes,
    _branch_probabilities: Mapping[str, float],
    _selected_branch: str,
) -> SurfaceFixturePlan:
    """Bind the target-state count objective."""

    dataset, answer_probabilities = build_state_surface_data(
        namespace=f"{TASK_ID}.objective",
        scene_variant=axes.scene_variant,
        element_type=axes.element_type,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
    )
    return SurfaceFixturePlan(
        dataset=dataset,
        answer_gt=TypedValue(type="integer", value=int(dataset["answer_value"])),
        target_element_ids=tuple(str(element_id) for element_id in dataset["target_element_ids"]),
        answer_value_probabilities=dict(answer_probabilities),
        object_description="a fixture surface with repeated elements that have visible states",
        objective_params={
            "target_state": str(dataset["target_state"]),
            "target_state_label": str(dataset["target_state_label"]),
        },
    )


@register_task
class ThreeDSurfaceFixtureStateElementCountTask:
    """Count fixture elements with a target state."""

    task_id = TASK_ID
    domain = "three_d"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_surface_fixture_lifecycle(
            public_name=TASK_ID,
            domain_name=self.domain,
            prompt_query_key=PROMPT_QUERY_KEY,
            supported_branches=SUPPORTED_QUERY_IDS,
            default_branch=QUERY_ID,
            supported_scenes=tuple(STATE_SUPPORT_BY_SCENE_VARIANT.keys()),
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_state_objective,
        )


__all__ = ["SUPPORTED_QUERY_IDS", "TASK_ID", "ThreeDSurfaceFixtureStateElementCountTask"]
