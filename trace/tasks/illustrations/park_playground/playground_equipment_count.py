"""Count playground equipment of one type in a park/playground scene."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.query_ids import SINGLE_QUERY_ID
from ...base import TaskOutput
from ...registry import register_task
from ._count_contracts import CountDefaults, build_count_runtime, run_equipment_items, sample_equipment_items


TASK_ID = "task_illustrations__park_playground__playground_equipment_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "playground_equipment_count"
_RUNTIME = build_count_runtime(
    namespace=TASK_ID,
    prompt_query_key=PROMPT_QUERY_KEY,
    supported_query_ids=SUPPORTED_QUERY_IDS,
    defaults=CountDefaults(
        equipment_count_min=4,
        equipment_count_max=7,
        person_count_min=5,
        person_count_max=9,
        target_count_min=1,
        target_count_max=5,
    ),
)


def _prepare_equipment_item_runtime():
    """Return the local equipment-item runtime contract."""

    return _RUNTIME


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any], attempt_index: int):
    """Expose the objective sampler for focused contract tests."""

    return sample_equipment_items(
        instance_seed=int(instance_seed),
        params=params,
        attempt_index=int(attempt_index),
        runtime=_prepare_equipment_item_runtime(),
    )


@register_task
class IllustrationsParkPlaygroundEquipmentCountTask:
    """Count visible playground equipment items of one sampled type."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        runtime = _prepare_equipment_item_runtime()
        return run_equipment_items(self, instance_seed=int(instance_seed), params=params, max_attempts=int(max_attempts), runtime=runtime)


__all__ = ["IllustrationsParkPlaygroundEquipmentCountTask", "TASK_ID", "SUPPORTED_QUERY_IDS", "_sample_spec"]
