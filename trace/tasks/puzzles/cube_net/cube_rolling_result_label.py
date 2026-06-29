"""Public cube rolling result label task."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import run_rolling_lifecycle
from .shared.state import DOMAIN, SCENE_ID


TASK_ID = "task_puzzles__cube_net__cube_rolling_result_label"
SUPPORTED_QUERY_IDS = (
    "final_top_face_label",
    "final_front_face_label",
    "final_right_face_label",
)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


def _build_target_slot_by_query() -> dict[str, str]:
    """Map public target-face queries onto cube orientation slots."""

    return {
        "final_top_face_label": "top",
        "final_front_face_label": "south",
        "final_right_face_label": "east",
    }


@register_task
class PuzzlesCubeRollingResultLabelTask:
    """Select which labeled face ends on a named cube slot after rolling."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def _build_objective_map(self) -> dict[str, str]:
        """Return this task's query-to-orientation-slot mapping."""

        return _build_target_slot_by_query()

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        """Run the rolling task with task-owned target-slot mapping."""

        return run_rolling_lifecycle(
            task_identity=TASK_ID,
            supported_queries=SUPPORTED_QUERY_IDS,
            target_slot_by_query=self._build_objective_map(),
            generation_defaults=_GEN_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = ["PuzzlesCubeRollingResultLabelTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
