"""Public folded cube-net path endpoint task."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import run_surface_path_lifecycle
from .shared.state import DOMAIN, SCENE_ID


TASK_ID = "task_puzzles__cube_net__folded_path_endpoint_label"
SUPPORTED_QUERY_IDS = ("single",)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


def _build_surface_path_objective() -> dict[str, str]:
    """Return prompt and answer-mode metadata for endpoint selection."""

    return {
        "option_mode": "endpoint",
        "prompt_task_key": "folded_path_endpoint_label_query",
        "prompt_query_key": "folded_path_endpoint_prompt",
        "answer_mode": "endpoint",
    }


@register_task
class PuzzlesCubeFoldedPathEndpointLabelTask:
    """Choose the final face reached by folded-edge moves from START."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def _build_objective(self) -> dict[str, str]:
        """Return this task's endpoint objective wiring."""

        return _build_surface_path_objective()

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        """Run endpoint selection with task-owned objective metadata."""

        objective = self._build_objective()
        return run_surface_path_lifecycle(
            task_identity=TASK_ID,
            supported_queries=SUPPORTED_QUERY_IDS,
            option_mode=objective["option_mode"],
            prompt_task_key=objective["prompt_task_key"],
            prompt_query_key=objective["prompt_query_key"],
            answer_mode=objective["answer_mode"],
            generation_defaults=_GEN_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = ["PuzzlesCubeFoldedPathEndpointLabelTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
