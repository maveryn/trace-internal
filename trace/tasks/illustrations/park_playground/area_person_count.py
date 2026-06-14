"""Count people in one semantic area of a park/playground scene."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.query_ids import SINGLE_QUERY_ID
from ...base import TaskOutput
from ...registry import register_task
from ._count_contracts import CountDefaults, build_count_runtime, run_area_people, sample_area_people


TASK_ID = "task_illustrations__park_playground__area_person_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "area_person_count"
_RUNTIME = build_count_runtime(
    namespace=TASK_ID,
    prompt_query_key=PROMPT_QUERY_KEY,
    supported_query_ids=SUPPORTED_QUERY_IDS,
    defaults=CountDefaults(person_count_min=7, person_count_max=12, target_count_min=1, target_count_max=6),
)


def _prepare_area_runtime():
    """Return the local area-count runtime contract."""

    return _RUNTIME


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int):
    """Expose the objective sampler for focused contract tests."""

    return sample_area_people(
        instance_seed=int(instance_seed),
        params=params,
        attempt_index=int(attempt_index),
        runtime=_prepare_area_runtime(),
    )


@register_task
class IllustrationsParkPlaygroundAreaPersonCountTask:
    """Count visible people whose final placement is inside one named area."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        runtime = _prepare_area_runtime()
        return run_area_people(self, instance_seed=int(instance_seed), params=params, max_attempts=int(max_attempts), runtime=runtime)


__all__ = ["IllustrationsParkPlaygroundAreaPersonCountTask", "TASK_ID", "SUPPORTED_QUERY_IDS", "_sample_spec"]
