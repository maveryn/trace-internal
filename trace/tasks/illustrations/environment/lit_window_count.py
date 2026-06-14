"""Count lit windows in environment buildings."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from ....core.query_ids import SINGLE_QUERY_ID
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from ._count_contracts import lit_window_plan
from ._lifecycle import EnvironmentCountPlan, run_environment_count_lifecycle


TASK_ID = "task_illustrations__environment__lit_window_count"
SCENE_ID = "environment"
QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "illustrations",
    SCENE_ID,
    task_id=TASK_ID,
)


def _build_plan() -> EnvironmentCountPlan:
    """Build the public-owned lit-window count objective plan."""

    return lit_window_plan(TASK_ID, SINGLE_QUERY_ID)


@register_task
class IllustrationsEnvironmentLitWindowCountTask:
    """Count lit windows visible on environment buildings."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_environment_count_lifecycle(
            plan=_build_plan(),
            domain=self.domain,
            generation_defaults=_GEN_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            prompt_defaults=_PROMPT_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = ["IllustrationsEnvironmentLitWindowCountTask"]
