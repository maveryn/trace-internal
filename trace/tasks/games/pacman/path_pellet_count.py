"""Count normal pellets on the highlighted Pac-Man route."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID

from ._lifecycle import AttemptPacmanResult, ObjectivePacmanPlan, run_pacman_lifecycle
from .shared.annotations import bbox_set_for_entity_ids
from .shared.defaults import DEFAULTS, SCENE_ID
from .shared.sampling import (
    resolve_pacman_integer_target,
    sample_route_pellet_scene_parts,
    wall_cells,
)
from .shared.state import PacmanSceneState, pellet_entity_id


TASK_ID = "task_games__pacman__path_pellet_count"
QUERY_ID = DEFAULT_QUERY_ID
PROMPT_QUERY_KEY = "path_pellet_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _json_examples() -> tuple[str, str]:
    """Return valid format examples for route pellet-count output."""

    answer_value = 5
    annotation_value = [[302, 196, 328, 222], [356, 196, 382, 222]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _prepare_path_pellet_count_objective(
    instance_seed: int,
    params: Mapping[str, Any],
    query_probabilities: Mapping[str, float],
    _query_id: str,
) -> ObjectivePacmanPlan:
    """Resolve the target route-pellet count and bind the attempt constructor."""

    target_axis = resolve_pacman_integer_target(
        int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="path_pellet_count_support",
        fallback_support=DEFAULTS.path_pellet_count_support,
        namespace=f"{TASK_ID}.target_answer",
    )
    target = int(target_axis.target_answer)

    def construct_attempt(rng: Any, axes: Any) -> AttemptPacmanResult:
        return _construct_path_pellet_count_attempt(rng=rng, axes=axes, target=target)

    json_example, json_example_answer_only = _json_examples()
    return ObjectivePacmanPlan(
        attempt_namespace="games.pacman.path_pellet_count",
        prompt_query_key=PROMPT_QUERY_KEY,
        answer_hint='set "answer" to the number of normal pellets on the highlighted route',
        annotation_hint='set "annotation" to bounding boxes [x0, y0, x1, y1], one for each normal pellet on the highlighted route',
        json_example=json_example,
        json_example_answer_only=json_example_answer_only,
        query_params={
            "query_id_probabilities": dict(query_probabilities),
            "target_answer": int(target_axis.target_answer),
            "target_answer_support": [int(value) for value in target_axis.target_answer_support],
            "target_answer_probabilities": dict(target_axis.target_answer_probabilities),
        },
        construct_attempt=construct_attempt,
    )


def _construct_path_pellet_count_attempt(*, rng: Any, axes: Any, target: int) -> AttemptPacmanResult:
    """Construct a maze where exactly target normal pellets lie on the route."""

    rows, cols = int(axes.row_count), int(axes.col_count)
    parts = sample_route_pellet_scene_parts(rng=rng, axes=axes, counted_pellet_count=int(target))
    annotation_ids = tuple(pellet_entity_id(coord) for coord in parts.counted_pellets)
    scene = PacmanSceneState(
        row_count=rows,
        col_count=cols,
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        open_cells=tuple(parts.open_cells),
        wall_cells=wall_cells(rows=rows, cols=cols, open_cells=parts.open_cells),
        pacman_coord=tuple(parts.route[0]),
        route_coords=tuple(parts.route),
        pellets=tuple(parts.pellets),
        items=tuple(),
        ghosts=tuple(parts.ghosts),
        construction_mode="count_visible_route_pellets",
    )
    return AttemptPacmanResult(
        scene=scene,
        answer_gt=TypedValue(type="integer", value=int(target)),
        annotation_entity_ids=annotation_ids,
        build_annotation=lambda rendered: bbox_set_for_entity_ids(rendered.rendered_scene, annotation_ids),
        execution_extra={"target_answer": int(target)},
    )


@register_task
class GamesPacmanPathPelletCountTask:
    """Count normal pellets on the highlighted Pac-Man route."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_pacman_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_path_pellet_count_objective,
        )


__all__ = ["GamesPacmanPathPelletCountTask"]
