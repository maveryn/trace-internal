"""Count people performing one activity in a park/playground scene."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.query_ids import SINGLE_QUERY_ID
from ...base import TaskOutput
from ...registry import register_task
from ._count_contracts import CountDefaults, build_count_runtime, run_activity_people, sample_activity_people


TASK_ID = "task_illustrations__park_playground__activity_person_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "activity_person_count"
_RUNTIME = build_count_runtime(
    namespace=TASK_ID,
    prompt_query_key=PROMPT_QUERY_KEY,
    supported_query_ids=SUPPORTED_QUERY_IDS,
    defaults=CountDefaults(person_count_min=7, person_count_max=12, target_count_min=1, target_count_max=6),
)


def _prepare_activity_runtime():
    """Return the local activity-count runtime contract."""

    return _RUNTIME


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int):
    """Expose the objective sampler for focused contract tests."""

    return sample_activity_people(
        instance_seed=int(instance_seed),
        params=params,
        attempt_index=int(attempt_index),
        runtime=_prepare_activity_runtime(),
    )


@register_task
class IllustrationsParkPlaygroundActivityPersonCountTask:
    """Count visible people matching one sampled activity."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        runtime = _prepare_activity_runtime()
        return run_activity_people(self, instance_seed=int(instance_seed), params=params, max_attempts=int(max_attempts), runtime=runtime)


__all__ = ["IllustrationsParkPlaygroundActivityPersonCountTask", "TASK_ID", "SUPPORTED_QUERY_IDS", "_sample_spec"]
