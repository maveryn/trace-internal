"""Public task for `task_icons__named_field__counterfactual_attribute_count`."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID, select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.output import COUNTERFACTUAL_SHAPE_REPLACEMENT, materialize_counterfactual_count_plan


TASK_ID = "task_icons__named_field__counterfactual_attribute_count"
SCENE_ID = "named_field"
QUERY_ID = DEFAULT_QUERY_ID
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
INTERNAL_QUERY_ID = "target_count_after_shape_replacement"
EDIT_KIND = COUNTERFACTUAL_SHAPE_REPLACEMENT

_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "icons",
    SCENE_ID,
    task_id=TASK_ID,
)


def _strip_validated_legacy_query_param(params: Dict[str, Any]) -> Dict[str, Any]:
    """Accept only this task's historical internal counterfactual query selector."""

    resolved = dict(params)
    requested = resolved.pop("counterfactual_query_id", None)
    if requested is not None and str(requested) != INTERNAL_QUERY_ID:
        raise ValueError(f"{TASK_ID} only supports query_id values {(INTERNAL_QUERY_ID,)}")
    return resolved


@register_task
class IconsNamedFieldCounterfactualAttributeCountTask:
    """Count target-shape icons after a hypothetical shape replacement."""

    task_id = TASK_ID
    domain = "icons"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_input = _strip_validated_legacy_query_param(dict(params))
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=task_input,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
        )
        materialized = materialize_counterfactual_count_plan(
            seed_namespace=TASK_ID,
            domain=self.domain,
            generation_defaults=_GEN_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            prompt_defaults_map=_PROMPT_DEFAULTS,
            selected_query_id=str(selected_query_id),
            internal_query_id=INTERNAL_QUERY_ID,
            edit_kind=EDIT_KIND,
            query_probabilities=query_probabilities,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
        return TaskOutput(
            prompt=materialized.prompt,
            answer_gt=materialized.answer_gt,
            annotation_gt=materialized.annotation_gt,
            image=materialized.image,
            image_id="img0",
            trace_payload=materialized.trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=materialized.selected_public_query,
            prompt_variants=materialized.prompt_variants,
        )
