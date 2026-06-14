"""Public task for `task_icons__named_field__multi_attribute_complement_count`."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID, select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions

from .shared.output import BOOLEAN_PREDICATE_NEITHER, materialize_boolean_count_plan


TASK_ID = "task_icons__named_field__multi_attribute_complement_count"
SCENE_ID = "named_field"
QUERY_ID = DEFAULT_QUERY_ID
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
INTERNAL_QUERY_ID = "neither_shape_nor_color_count"
PREDICATE_KIND = BOOLEAN_PREDICATE_NEITHER

_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "icons",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class IconsNamedFieldMultiAttributeComplementCountTask:
    """Count icons satisfying neither the named shape nor the visual attribute."""

    task_id = TASK_ID
    domain = "icons"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
        )
        materialized = materialize_boolean_count_plan(
            seed_namespace=TASK_ID,
            domain=self.domain,
            generation_defaults=_GEN_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            prompt_defaults_map=_PROMPT_DEFAULTS,
            selected_query_id=str(selected_query_id),
            internal_query_id=INTERNAL_QUERY_ID,
            predicate_kind=PREDICATE_KIND,
            query_probabilities=query_probabilities,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )
        trace_payload = dict(materialized.trace_payload)
        prompt_variants = dict(materialized.prompt_variants)
        return TaskOutput(
            prompt=materialized.prompt,
            answer_gt=materialized.answer_gt,
            annotation_gt=materialized.annotation_gt,
            image=materialized.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=materialized.selected_public_query,
            prompt_variants=prompt_variants,
        )


__all__ = [
    "IconsNamedFieldMultiAttributeComplementCountTask",
    "INTERNAL_QUERY_ID",
    "PREDICATE_KIND",
    "QUERY_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
