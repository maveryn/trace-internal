"""Identify the labeled moving object that hits the marked crossing route."""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.crossing._lifecycle import CrossingObjectivePlan, run_crossing_lifecycle
from trace.tasks.games.crossing.shared.defaults import SCENE_ID, VEHICLE_OPTION_LABELS
from trace.tasks.games.crossing.shared.prompts import (
    crossing_motion_rule_text,
    crossing_object_description,
    crossing_output_slots,
    json_examples_for_label_answer,
)
from trace.tasks.games.crossing.shared.sampling import resolve_crossing_scene_axes, sample_labeled_route_collision_scene
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support


TASK_ID = "task_games__crossing__hit_object_label"
QUERY_ID = "hit_object_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
TARGET_LABEL_INDEX_SUPPORT: Tuple[int, ...] = (0, 1, 2, 3)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _resolve_target_label(
    *,
    instance_seed: int,
    task_params: Mapping[str, Any],
) -> tuple[str, int, tuple[int, ...], dict[str, float]]:
    """Resolve the visible option label that should be the unique collision."""

    labels = tuple(str(label) for label in VEHICLE_OPTION_LABELS)
    support = resolve_integer_support(
        task_params,
        gen_defaults=_GEN_DEFAULTS,
        key="hit_object_label_index_support",
        fallback=TARGET_LABEL_INDEX_SUPPORT,
    )
    if task_params.get("target_label") is not None:
        label = str(task_params["target_label"])
        if label not in labels:
            raise ValueError(f"unsupported crossing target label: {label}")
        index = int(labels.index(label))
        if index not in set(int(value) for value in support):
            raise ValueError(f"target label {label} is outside configured support")
        probabilities = {str(value): 1.0 if int(value) == int(index) else 0.0 for value in support}
        return label, index, tuple(int(value) for value in support), probabilities

    index, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="hit_object_label_index_support",
        explicit_key="target_label_index",
        fallback_support=tuple(int(value) for value in support),
        namespace=f"{TASK_ID}.target_label_index",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    label_index = int(index)
    if label_index < 0 or label_index >= len(labels):
        raise ValueError(f"target label index out of range: {label_index}")
    return str(labels[label_index]), label_index, tuple(int(value) for value in support), dict(probabilities)


def _prepare_hit_object_label_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    selected_query_id: str,
    _query_probabilities: Mapping[str, float],
) -> CrossingObjectivePlan:
    """Bind straight-route hit-object semantics and label answer construction."""

    target_label, target_label_index, target_label_support, target_label_probabilities = _resolve_target_label(
        instance_seed=int(instance_seed),
        task_params=task_params,
    )
    axes = resolve_crossing_scene_axes(
        int(instance_seed),
        params=task_params,
        gen_defaults=_GEN_DEFAULTS,
        min_lane_count=5,
        min_row_count=5,
        namespace_suffix=str(selected_query_id),
    )
    max_extra_per_row = int(group_default(_GEN_DEFAULTS, "hit_object_max_extra_per_row", 1))

    def construct_attempt(rng):
        return sample_labeled_route_collision_scene(
            rng=rng,
            axes=axes,
            target_label=str(target_label),
            max_extra_per_row=int(max_extra_per_row),
        )

    def prompt_slots(_sample) -> dict[str, Any]:
        json_example, json_example_answer_only = json_examples_for_label_answer()
        return {
            "object_description": crossing_object_description(include_route=True),
            "crossing_motion_rule_text": crossing_motion_rule_text(),
            **crossing_output_slots(
                prompt_query_key=QUERY_ID,
                json_example=json_example,
                json_example_answer_only=json_example_answer_only,
            ),
        }

    def query_spec_params(sample) -> dict[str, Any]:
        return {
            "count_mode": "hit_object_label",
            "vehicle_option_labels": [str(label) for label in VEHICLE_OPTION_LABELS],
            "target_label": str(sample.target_object_label),
            "target_label_index": int(target_label_index),
            "target_label_index_support": [int(value) for value in target_label_support],
            "target_label_index_probabilities": dict(target_label_probabilities),
        }

    return CrossingObjectivePlan(
        axes=axes,
        attempt_namespace=TASK_ID,
        construct_attempt=construct_attempt,
        prompt_query_key=QUERY_ID,
        prompt_dynamic_slots=prompt_slots,
        answer_gt=lambda sample: TypedValue(type="string", value=str(sample.answer)),
        annotation_entity_ids=lambda sample: sample.annotation_entity_ids,
        query_spec_params=query_spec_params,
        execution_updates=lambda sample: {
            "target_label": str(sample.target_object_label),
            "target_label_index": int(sample.target_label_index) if sample.target_label_index is not None else None,
        },
    )


@register_task
class GamesCrossingHitObjectLabelTask:
    """Identify which labeled moving object collides with the marked route."""

    task_id = TASK_ID
    domain = "games"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate a straight marked-route collision label question."""

        return run_crossing_lifecycle(
            task_id=TASK_ID,
            domain=self.domain,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_hit_object_label_objective,
        )


__all__ = ["GamesCrossingHitObjectLabelTask"]
