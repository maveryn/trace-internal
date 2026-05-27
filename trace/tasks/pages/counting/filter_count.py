"""Consolidated GUI filter-counting task."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.public_query_task import rewrite_pages_query_output
from .control_filter_count import (
    SUPPORTED_QUERY_VARIANTS as CONTROL_QUERY_VARIANTS,
    GuiCountingControlFilterCountTask,
)
from .table_row_filter_count import (
    SUPPORTED_QUERY_VARIANTS as TABLE_QUERY_VARIANTS,
    GuiCountingTableRowFilterCountTask,
)


TASK_ID = "task_pages__control_board__filter_count"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = tuple(CONTROL_QUERY_VARIANTS) + tuple(TABLE_QUERY_VARIANTS)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "counting")
_GEN_DEFAULTS, _, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _resolve_query_variant(instance_seed: int, *, params: Mapping[str, Any]) -> tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_variant")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_VARIANTS,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_QUERY_VARIANTS,
        balance_flag_key="balanced_query_variant_sampling",
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        sampling_namespace=f"{TASK_ID}:query_variant",
    )
    return str(balanced), {str(key): float(value) for key, value in sorted(probabilities.items())}


_PROMPT_DEFAULTS_REQUIRED = required_group_defaults(
    _PROMPT_DEFAULTS,
    (
        "scene_key_control_filter_count",
        "task_key_control_filter_count",
        "object_description_control_filter_count",
        "evidence_hint_control_filter_count",
        "scene_key_table_row_filter_count",
        "task_key_table_row_filter_count",
        "object_description_table_row_filter_count",
        "evidence_hint_table_row_filter_count",
    ),
    context=f"prompt defaults for {TASK_ID}",
)

_CONTROL_PROMPT_DEFAULTS: Dict[str, Any] = {
    **dict(_PROMPT_DEFAULTS),
    "scene_key": str(_PROMPT_DEFAULTS_REQUIRED["scene_key_control_filter_count"]),
    "task_key": str(_PROMPT_DEFAULTS_REQUIRED["task_key_control_filter_count"]),
    "object_description": str(_PROMPT_DEFAULTS_REQUIRED["object_description_control_filter_count"]),
    "evidence_hint": str(_PROMPT_DEFAULTS_REQUIRED["evidence_hint_control_filter_count"]),
}
_TABLE_PROMPT_DEFAULTS: Dict[str, Any] = {
    **dict(_PROMPT_DEFAULTS),
    "scene_key": str(_PROMPT_DEFAULTS_REQUIRED["scene_key_table_row_filter_count"]),
    "task_key": str(_PROMPT_DEFAULTS_REQUIRED["task_key_table_row_filter_count"]),
    "object_description": str(_PROMPT_DEFAULTS_REQUIRED["object_description_table_row_filter_count"]),
    "evidence_hint": str(_PROMPT_DEFAULTS_REQUIRED["evidence_hint_table_row_filter_count"]),
}


def _rewrite_variant_probabilities(payload: Dict[str, Any], probabilities: Mapping[str, float]) -> None:
    for section_key in ("execution_trace",):
        section = payload.get(section_key)
        if isinstance(section, dict):
            section["query_variant_probabilities"] = dict(probabilities)
    query_spec = payload.get("query_spec")
    if isinstance(query_spec, dict):
        params = query_spec.get("params")
        if isinstance(params, dict):
            params["query_variant_probabilities"] = dict(probabilities)


@register_task
class PagesCountingFilterCountTask:
    """Count GUI controls or table rows satisfying a visible filter condition."""

    task_id = TASK_ID
    domain = "pages"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_variant, probabilities = _resolve_query_variant(int(instance_seed), params=params)
        delegated_params = dict(_GEN_DEFAULTS)
        delegated_params.update(dict(params))
        delegated_params["query_variant"] = str(query_variant)

        if str(query_variant) in set(CONTROL_QUERY_VARIANTS):
            source_task = GuiCountingControlFilterCountTask()
            delegated_params["_prompt_defaults_override"] = dict(_CONTROL_PROMPT_DEFAULTS)
        elif str(query_variant) in set(TABLE_QUERY_VARIANTS):
            source_task = GuiCountingTableRowFilterCountTask()
            delegated_params["_prompt_defaults_override"] = dict(_TABLE_PROMPT_DEFAULTS)
        else:
            raise ValueError(f"unsupported query_variant for {TASK_ID}: {query_variant}")

        output = source_task.generate(
            int(instance_seed),
            params=delegated_params,
            max_attempts=int(max_attempts),
        )
        output.query_variant = str(query_variant)
        _rewrite_variant_probabilities(output.trace_payload, probabilities)
        return rewrite_pages_query_output(
            output,
            query_id=str(query_variant),
            scene_id="control_board",
            query_probabilities=probabilities,
        )


__all__ = ["PagesCountingFilterCountTask", "SUPPORTED_QUERY_VARIANTS"]
