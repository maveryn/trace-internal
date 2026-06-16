"""Sum scored objects hit by a drawn pinball path."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID

from ._lifecycle import AttemptPinballResult, ObjectivePinballPlan, run_pinball_lifecycle
from .shared.annotations import point_sequence_for_entity_ids
from .shared.defaults import PATH_SCORE_VALUES, SCENE_ID
from .shared.sampling import (
    PinballVisualAxes,
    resolve_pinball_score_path_axes,
    sample_path_score_playfield,
)


TASK_ID = "task_games__pinball_table__path_score_value"
QUERY_ID = DEFAULT_QUERY_ID
PROMPT_QUERY_KEY = "path_score_value"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _json_examples() -> tuple[str, str]:
    """Return valid format examples for pinball path-score output."""

    return (
        json.dumps({"annotation": [[310, 250], [420, 330], [520, 270]], "answer": 90}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": 90}, separators=(",", ":"), ensure_ascii=False),
    )


def _prepare_path_score_objective(
    instance_seed: int,
    params: Mapping[str, Any],
    query_probabilities: Mapping[str, float],
    _query_id: str,
    axes: PinballVisualAxes,
) -> ObjectivePinballPlan:
    """Resolve the drawn-path axes and bind the scoring constructor."""

    score_axes = resolve_pinball_score_path_axes(
        int(instance_seed),
        gen_defaults=_GEN_DEFAULTS,
        namespace=f"{TASK_ID}.score_path",
        params=params,
        object_count=int(axes.object_count),
    )

    def construct_attempt(rng: Any, attempt_axes: PinballVisualAxes) -> AttemptPinballResult:
        return _construct_path_score_attempt(
            rng=rng,
            axes=attempt_axes,
            path_shape=str(score_axes.path_shape),
            path_hit_count=int(score_axes.path_hit_count),
        )

    json_example, json_example_answer_only = _json_examples()
    return ObjectivePinballPlan(
        attempt_namespace="games.pinball_table.path_score_value",
        prompt_query_key=PROMPT_QUERY_KEY,
        object_description_key="object_description_score_path",
        answer_hint='set "answer" to the integer total score',
        annotation_hint='set "annotation" to an ordered JSON array of [x, y] pixel points at the centers of scored targets hit along the path, repeating a point for repeated hits',
        json_example=json_example,
        json_example_answer_only=json_example_answer_only,
        query_params={
            "query_id_probabilities": dict(query_probabilities),
            "path_shape": str(score_axes.path_shape),
            "path_hit_count": int(score_axes.path_hit_count),
            "path_shape_probabilities": dict(score_axes.path_shape_probabilities),
            "path_hit_count_probabilities": dict(score_axes.path_hit_count_probabilities),
            "score_value_support": [int(value) for value in PATH_SCORE_VALUES],
        },
        construct_attempt=construct_attempt,
    )


def _construct_path_score_attempt(
    *,
    rng: Any,
    axes: PinballVisualAxes,
    path_shape: str,
    path_hit_count: int,
) -> AttemptPinballResult:
    """Construct a complete path and bind ordered scored-target hits."""

    construction = sample_path_score_playfield(
        rng=rng,
        axes=axes,
        path_shape=str(path_shape),
        hit_count=int(path_hit_count),
    )
    score_by_id = {str(obj.object_id): int(obj.score_value or 0) for obj in construction.scene.objects}
    if any(str(entity_id) not in score_by_id for entity_id in construction.annotation_entity_ids):
        raise ValueError("pinball score annotation ids must be visible objects")
    if any(int(score_by_id[str(entity_id)]) <= 0 for entity_id in construction.annotation_entity_ids):
        raise ValueError("pinball score annotation ids must have positive scores")
    expected_score = sum(int(score_by_id[str(entity_id)]) for entity_id in construction.annotation_entity_ids)
    if int(expected_score) != int(construction.score_total):
        raise ValueError("pinball score answer does not match annotation-object score total")
    return AttemptPinballResult(
        scene=construction.scene,
        answer_gt=TypedValue(type="integer", value=int(construction.score_total)),
        annotation_entity_ids=tuple(str(entity_id) for entity_id in construction.annotation_entity_ids),
        build_annotation=lambda rendered: point_sequence_for_entity_ids(rendered.rendered_scene, construction.annotation_entity_ids),
        witness_type="object_sequence",
        relations_extra={
            "path_shape": str(path_shape),
            "path_hit_count": int(path_hit_count),
            "score_total": int(construction.score_total),
            "hit_score_values": [int(value) for value in construction.hit_score_values],
        },
        execution_extra={
            "path_shape": str(path_shape),
            "path_hit_count": int(path_hit_count),
            "score_value_support": [int(value) for value in PATH_SCORE_VALUES],
            "score_total": int(construction.score_total),
            "hit_score_values": [int(value) for value in construction.hit_score_values],
            "repeated_hit_object_ids": [str(entity_id) for entity_id in construction.repeated_hit_object_ids],
        },
    )


@register_task
class GamesPinballPathScoreValueTask:
    """Sum score values along the complete drawn pinball path."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_pinball_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            gen_defaults=_GEN_DEFAULTS,
            render_defaults=_RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_path_score_objective,
        )


__all__ = ["GamesPinballPathScoreValueTask"]
