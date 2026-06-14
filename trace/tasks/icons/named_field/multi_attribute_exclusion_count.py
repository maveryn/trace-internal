"""Public task for `task_icons__named_field__multi_attribute_exclusion_count`."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import select_task_query_id

from ._lifecycle import run_boolean_named_field_task
from .shared.metrics import BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE, BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE


TASK_ID = "task_icons__named_field__multi_attribute_exclusion_count"
SCENE_ID = "named_field"
SHAPE_WITHOUT_ATTRIBUTE_QUERY_ID = "shape_and_not_color_count"
ATTRIBUTE_WITHOUT_SHAPE_QUERY_ID = "color_and_not_shape_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    SHAPE_WITHOUT_ATTRIBUTE_QUERY_ID,
    ATTRIBUTE_WITHOUT_SHAPE_QUERY_ID,
)
PREDICATE_KIND_BY_QUERY_ID = {
    SHAPE_WITHOUT_ATTRIBUTE_QUERY_ID: BOOLEAN_PREDICATE_SHAPE_WITHOUT_ATTRIBUTE,
    ATTRIBUTE_WITHOUT_SHAPE_QUERY_ID: BOOLEAN_PREDICATE_ATTRIBUTE_WITHOUT_SHAPE,
}

_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "icons",
    SCENE_ID,
    task_id=TASK_ID,
)


@register_task
class IconsNamedFieldMultiAttributeExclusionCountTask:
    """Count icons satisfying one named predicate while excluding the other."""

    task_id = TASK_ID
    domain = "icons"
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        selected_query_id, query_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=SHAPE_WITHOUT_ATTRIBUTE_QUERY_ID,
            task_id=TASK_ID,
        )
        prompt_query_key = str(selected_query_id)
        predicate_kind = str(PREDICATE_KIND_BY_QUERY_ID[prompt_query_key])
        return run_boolean_named_field_task(
            task_id=TASK_ID,
            domain=self.domain,
            scene_id=SCENE_ID,
            selected_query_key=prompt_query_key,
            query_probabilities=query_probabilities,
            prompt_query_key=prompt_query_key,
            predicate_kind=predicate_kind,
            generation_defaults=_GEN_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            prompt_defaults_map=_PROMPT_DEFAULTS,
            instance_seed=int(instance_seed),
            params=task_params,
            max_attempts=int(max_attempts),
        )


__all__ = [
    "ATTRIBUTE_WITHOUT_SHAPE_QUERY_ID",
    "IconsNamedFieldMultiAttributeExclusionCountTask",
    "PREDICATE_KIND_BY_QUERY_ID",
    "SHAPE_WITHOUT_ATTRIBUTE_QUERY_ID",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
