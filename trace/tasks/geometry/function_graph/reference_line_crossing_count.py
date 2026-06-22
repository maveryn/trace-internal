from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.registry import register_task

from ._lifecycle import (
    REFERENCE_COUNT_PROMPT_KEYS,
    integer_count_prompt_slots,
    prepare_function_graph_count_plan,
    run_function_graph_count_entry,
)
from .shared.defaults import DOMAIN
from .shared.prompts import function_object_description
from .shared.sampling import (
    reference_count_support_by_family,
    resolve_horizontal_reference_y,
    sample_reference_scene,
)

TASK_ID = "task_geometry__function_graph__reference_line_crossing_count"
SUPPORTED_QUERY_IDS = ("x_axis", "horizontal_line")
PROMPT_TEMPLATE_KEY = "reference_line_crossing_count"


def _prompt_slots(defaults: Mapping[str, Any], *, family: str, query_id: str, reference_y: int | None):
    reference_description = (
        str(defaults["reference_line_description_x_axis"])
        if str(query_id) == "x_axis"
        else str(defaults["reference_line_description_horizontal_line"]).format(query_line_equation=f"y = {int(reference_y)}")
    )
    return integer_count_prompt_slots(
        defaults,
        object_description=function_object_description(defaults=defaults, family=str(family), has_guide_line=reference_y is not None),
        reference_line_description=str(reference_description),
        query_line_equation="" if reference_y is None else f"y = {int(reference_y)}",
        annotation_hint=str(defaults["annotation_hint_reference_line_crossing_count"]).format(reference_line_description=str(reference_description)),
        json_example=str(defaults["json_example_reference_line_crossing_count"]),
        json_example_answer_only=str(defaults["json_example_answer_only_reference_line_crossing_count"]),
    )


def _prepare_reference_line_objective(
    instance_seed: int,
    task_params: Mapping[str, Any],
    query_id: str,
    query_probabilities: Mapping[str, float],
):
    """Reference-line objective: branch selects the line; support stays here."""
    reference_y = None
    reference_y_probs: Mapping[str, float] = {}
    if str(query_id) == "horizontal_line":
        reference_y, reference_y_probs = resolve_horizontal_reference_y(instance_seed=int(instance_seed), params=task_params)
    extra_query = {}
    if reference_y is not None:
        extra_query["reference_line_y"] = int(reference_y)
        extra_query["reference_line_y_probabilities"] = dict(reference_y_probs)
    return prepare_function_graph_count_plan(
        instance_seed=int(instance_seed),
        task_params=task_params,
        task_id=TASK_ID,
        branch_name=str(query_id),
        branch_probabilities=query_probabilities,
        support_by_family=reference_count_support_by_family(),
        prompt_template_key=PROMPT_TEMPLATE_KEY,
        prompt_default_keys=REFERENCE_COUNT_PROMPT_KEYS,
        build_prompt_slots=lambda defaults, family, _target: _prompt_slots(
            defaults,
            family=str(family),
            query_id=str(query_id),
            reference_y=reference_y,
        ),
        sample_scene=lambda rng, family, target: sample_reference_scene(
            rng,
            family=str(family),
            target_count=int(target),
            reference_y=reference_y,
        ),
        build_scene_relations=lambda family, target: {
            "reference_line_y": reference_y,
            "target_count": int(target),
            "scene_variant": str(family),
        },
        extra_query_params=extra_query,
    )


@register_task
class GeometryGraphingReferenceLineCrossingCountTask:
    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_function_graph_count_entry(
            task_id=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id="x_axis",
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            prepare_objective=_prepare_reference_line_objective,
        )
