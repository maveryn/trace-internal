"""Count legal capture moves for a marked radial hunt-board piece."""

from __future__ import annotations

from typing import Any, Dict

from trace.core.seed import spawn_rng
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.scene import (
    CAPTURE_MOVE_QUERY_ID,
    SCENE_ID,
    build_radial_hunt_board_output_parts,
    resolve_radial_hunt_board_axes,
    sample_radial_hunt_board_capture_scene,
)


TASK_ID = "task_games__radial_hunt_board__capture_move_count"
SUPPORTED_QUERY_IDS = (CAPTURE_MOVE_QUERY_ID,)


@register_task
class GamesRadialHuntBoardCaptureMoveCountTask:
    """Count legal jump-over capture moves for one marked piece on a radial board."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        query_id, _query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=dict(params or {}),
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=CAPTURE_MOVE_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        axes = resolve_radial_hunt_board_axes(int(instance_seed), params=task_params)
        sampled = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled = sample_radial_hunt_board_capture_scene(rng=rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled is None:
            raise RuntimeError(f"{self.task_id} failed to generate after {max_attempts} attempts")

        parts = build_radial_hunt_board_output_parts(
            query_id=str(query_id),
            sampled=sampled,
            axes=axes,
            instance_seed=int(instance_seed),
            params=task_params,
        )
        return TaskOutput(
            prompt=str(parts.prompt),
            prompt_variants=dict(parts.prompt_variants),
            answer_gt=parts.answer_gt,
            annotation_gt=parts.annotation_gt,
            image=parts.image,
            image_id="img0",
            trace_payload=dict(parts.trace_payload),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


__all__ = ["GamesRadialHuntBoardCaptureMoveCountTask"]
