"""Public cube-net face-relation label task."""

from __future__ import annotations

from typing import Any, Dict

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults

from ._lifecycle import run_face_relation_lifecycle
from .shared.state import DOMAIN, SCENE_ID


TASK_ID = "task_puzzles__cube_net__cube_net_face_relation_label"
SUPPORTED_QUERY_IDS = ("opposite_face_label", "marked_edge_neighbor_face_label")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = (
    load_scene_generation_rendering_prompt_defaults(DOMAIN, SCENE_ID, task_id=TASK_ID)
)


def _build_relation_kind_by_query() -> dict[str, str]:
    """Map public semantic queries onto cube-net relation operators."""

    return {
        "opposite_face_label": "opposite",
        "marked_edge_neighbor_face_label": "edge_neighbor",
    }


@register_task
class PuzzlesCubeNetFaceRelationLabelTask:
    """Select a labeled option for an opposite or folded-edge face relation."""

    task_id = TASK_ID
    domain = DOMAIN
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def _build_objective_map(self) -> dict[str, str]:
        """Return this task's query-to-relation mapping."""

        return _build_relation_kind_by_query()

    def generate(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
    ) -> TaskOutput:
        """Run the face-relation task with task-owned query mapping."""

        return run_face_relation_lifecycle(
            task_identity=TASK_ID,
            supported_queries=SUPPORTED_QUERY_IDS,
            relation_kind_by_query=self._build_objective_map(),
            generation_defaults=_GEN_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = ["PuzzlesCubeNetFaceRelationLabelTask", "SUPPORTED_QUERY_IDS", "TASK_ID"]
