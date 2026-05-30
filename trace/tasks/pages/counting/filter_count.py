"""Consolidated GUI filter-counting task."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import split_generation_rendering_prompt_defaults
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.public_query_task import rewrite_pages_query_output
from .control_filter_count import (
    SUPPORTED_QUERY_IDS as CONTROL_QUERY_IDS,
    GuiCountingControlFilterCountTask,
)
from .table_row_filter_count import (
    SUPPORTED_QUERY_IDS as TABLE_QUERY_IDS,
    GuiCountingTableRowFilterCountTask,
)


CONTROL_FILTER_COUNT_TASK_ID = "task_pages__control_board__control_filter_count"
ROW_FILTER_COUNT_TASK_ID = "task_pages__data_table__row_filter_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = tuple(CONTROL_QUERY_IDS) + tuple(TABLE_QUERY_IDS)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "counting")


def _resolve_defaults(task_id: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    gen_defaults, _render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    return dict(gen_defaults), dict(prompt_defaults)


def _resolve_query_id(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    task_id: str,
    supported_query_ids: Tuple[str, ...],
) -> tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.query_id")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=supported_query_ids,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=supported_query_ids,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{task_id}:query_id",
    )
    return str(balanced), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _rewrite_query_id_probabilities(payload: Dict[str, Any], probabilities: Mapping[str, float]) -> None:
    for section_key in ("execution_trace",):
        section = payload.get(section_key)
        if isinstance(section, dict):
            section["query_id_probabilities"] = dict(probabilities)
    query_spec = payload.get("query_spec")
    if isinstance(query_spec, dict):
        params = query_spec.get("params")
        if isinstance(params, dict):
            params["query_id_probabilities"] = dict(probabilities)


class _PagesCountingFilterCountBase:
    """Count GUI controls or table rows satisfying a visible filter condition."""

    task_id = ""
    domain = "pages"
    task_group = "counting"
    scene_id = ""
    supported_query_ids: Tuple[str, ...] = ()
    source_task_cls: type

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, prompt_defaults = _resolve_defaults(str(self.task_id))
        query_id, probabilities = _resolve_query_id(
            int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            task_id=str(self.task_id),
            supported_query_ids=tuple(self.supported_query_ids),
        )
        delegated_params = dict(gen_defaults)
        delegated_params.update(dict(params))
        delegated_params["query_id"] = str(query_id)
        delegated_params["_prompt_defaults_override"] = dict(prompt_defaults)

        source_task = self.source_task_cls()

        output = source_task.generate(
            int(instance_seed),
            params=delegated_params,
            max_attempts=int(max_attempts),
        )
        output.query_id = str(query_id)
        _rewrite_query_id_probabilities(output.trace_payload, probabilities)
        return rewrite_pages_query_output(
            output,
            query_id=str(query_id),
            scene_id=str(self.scene_id),
            query_probabilities=probabilities,
        )


@register_task
class PagesControlBoardControlFilterCountTask(_PagesCountingFilterCountBase):
    """Count grouped GUI controls satisfying a visible state predicate."""

    task_id = CONTROL_FILTER_COUNT_TASK_ID
    scene_id = "control_board"
    supported_query_ids = CONTROL_QUERY_IDS
    source_task_cls = GuiCountingControlFilterCountTask


@register_task
class PagesDataTableRowFilterCountTask(_PagesCountingFilterCountBase):
    """Count sectioned GUI table rows satisfying a visible row predicate."""

    task_id = ROW_FILTER_COUNT_TASK_ID
    scene_id = "data_table"
    supported_query_ids = TABLE_QUERY_IDS
    source_task_cls = GuiCountingTableRowFilterCountTask


__all__ = [
    "CONTROL_FILTER_COUNT_TASK_ID",
    "ROW_FILTER_COUNT_TASK_ID",
    "CONTROL_QUERY_IDS",
    "TABLE_QUERY_IDS",
    "SUPPORTED_QUERY_IDS",
    "PagesControlBoardControlFilterCountTask",
    "PagesDataTableRowFilterCountTask",
]
