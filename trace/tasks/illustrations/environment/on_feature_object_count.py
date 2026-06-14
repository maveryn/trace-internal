"""Count foreground objects located on an environment feature."""

from __future__ import annotations

from functools import partial
from typing import Any, Dict, Tuple

from ....core.query_ids import SINGLE_QUERY_ID
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from ._lifecycle import EnvironmentCountPlan, run_environment_count_lifecycle
from .shared.defaults import ON_FEATURE_DEFAULTS, render_fallback
from .shared.output import bind_on_feature_result
from .shared.prompts import prompt_slots_on_feature
from .shared.rendering import on_feature_render_overrides
from .shared.sampling import resolve_feature_choice, sample_scene_object_count, sample_target_count_by_keys


TASK_ID = "task_illustrations__environment__on_feature_object_count"
SCENE_ID = "environment"
QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "on_feature_object_count"
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "illustrations",
    SCENE_ID,
    task_id=TASK_ID,
)


def _build_plan() -> EnvironmentCountPlan:
    """Build the public-owned on-feature count objective plan."""

    return EnvironmentCountPlan(
        public_id=TASK_ID,
        local_query_id=SINGLE_QUERY_ID,
        seed_namespace=f"{TASK_ID}:scene",
        prompt_query_key=PROMPT_QUERY_KEY,
        resolve_choice=partial(resolve_feature_choice, public_id=TASK_ID, include_relation=False),
        object_count_sampler=partial(sample_scene_object_count, public_id=TASK_ID, defaults=ON_FEATURE_DEFAULTS),
        target_count_sampler=partial(
            sample_target_count_by_keys,
            low_key="on_feature_target_count_min",
            high_key="on_feature_target_count_max",
            defaults=ON_FEATURE_DEFAULTS,
        ),
        render_overrides=on_feature_render_overrides,
        bind_result=bind_on_feature_result,
        prompt_slots=partial(prompt_slots_on_feature, public_id=TASK_ID),
        render_fallback=render_fallback(ON_FEATURE_DEFAULTS),
    )


@register_task
class IllustrationsEnvironmentOnFeatureObjectCountTask:
    """Count foreground objects on or in a road/river feature."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_environment_count_lifecycle(
            plan=_build_plan(),
            domain=self.domain,
            generation_defaults=_GEN_DEFAULTS,
            rendering_defaults=_RENDER_DEFAULTS,
            prompt_defaults=_PROMPT_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = ["IllustrationsEnvironmentOnFeatureObjectCountTask"]
