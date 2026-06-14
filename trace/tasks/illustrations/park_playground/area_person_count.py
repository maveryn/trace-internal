"""Count people in one semantic area of a park/playground scene."""

from __future__ import annotations

from functools import partial
from typing import Any, Dict, Mapping, Tuple

from ....core.query_ids import SINGLE_QUERY_ID
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from ._lifecycle import ParkCountPlan, run_park_count_lifecycle
from .shared.defaults import CountDefaults
from .shared.output import bind_area_people
from .shared.sampling import sample_area_people


TASK_ID = "task_illustrations__park_playground__area_person_count"
SCENE_ID = "park_playground"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "area_person_count"
_DEFAULTS = CountDefaults(person_count_min=7, person_count_max=12, target_count_min=1, target_count_max=6)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "illustrations",
    SCENE_ID,
    task_id=TASK_ID,
)


def _build_plan() -> ParkCountPlan:
    """Build the public-owned area count objective plan."""

    return ParkCountPlan(
        public_id=TASK_ID,
        prompt_query_key=PROMPT_QUERY_KEY,
        sample_spec=partial(
            sample_area_people,
            namespace=TASK_ID,
            query_support=SUPPORTED_QUERY_IDS,
            generation_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
        ),
        person_specs=lambda sample: sample.person_specs,
        equipment_specs=lambda _sample: None,
        required_zones=lambda sample: (str(sample.target_zone),),
        bind_result=partial(bind_area_people, context=TASK_ID),
        fallback_width=_DEFAULTS.canvas_width,
        fallback_height=_DEFAULTS.canvas_height,
        fallback_scale=_DEFAULTS.render_scale,
    )


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int):
    """Expose the objective sampler for focused contract tests."""

    return _build_plan().sample_spec(instance_seed=int(instance_seed), params=params, attempt_index=int(attempt_index))


@register_task
class IllustrationsParkPlaygroundAreaPersonCountTask:
    """Count visible people whose final placement is inside one named area."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return run_park_count_lifecycle(
            task=self,
            plan=_build_plan(),
            rendering_defaults=_RENDER_DEFAULTS,
            prompt_defaults=_PROMPT_DEFAULTS,
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
        )


__all__ = ["IllustrationsParkPlaygroundAreaPersonCountTask", "TASK_ID", "SUPPORTED_QUERY_IDS", "_sample_spec"]
