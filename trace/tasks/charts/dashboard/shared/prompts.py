"""Prompt assembly for dashboard chart tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.scene_config import get_scene_defaults
from trace.tasks.charts.dashboard.shared.cross_panel_common import SCENE_ID, _Dataset, _join_quoted_labels
from trace.tasks.shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)


DOMAIN = "charts"
PROMPT_BUNDLE_ID = "charts_dashboard_v1"
_DEFAULTS = get_scene_defaults(DOMAIN, SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _DEFAULTS if isinstance(_DEFAULTS, Mapping) else {},
    **{"task" "_id": "charts_dashboard_prompt"},
)
_DYNAMIC_SLOT_NAMES = {
    "condition_category_label",
    "first_condition_panel_name",
    "first_condition_phrase",
    "first_gap_panel_name",
    "first_rank_gap_panel_name",
    "first_rank_phrase",
    "first_source_panel_name",
    "first_topk_panel_name",
    "gap_extremum_phrase",
    "object_description",
    "panel_condition_phrase",
    "rank_direction_phrase",
    "rank_phrase",
    "requested_truth_phrase",
    "second_condition_panel_name",
    "second_condition_phrase",
    "second_gap_panel_name",
    "second_rank_gap_panel_name",
    "second_rank_phrase",
    "second_source_panel_name",
    "second_topk_panel_name",
    "source_panel_name",
    "target_panel_name",
    "top_k_phrase",
}


def _object_description(dataset: _Dataset) -> str:
    return (
        f"a dashboard with {int(len(dataset.panels))} titled panels named "
        f"{_join_quoted_labels([str(panel.name) for panel in dataset.panels])}. "
        f"Styles may be bar, line, donut, or radar, and a style may repeat. "
        f"All panels share the same {int(len(dataset.categories))} category labels and colors, "
        "with exact integer values shown"
    )


def build_prompt_slots(
    *,
    dataset: _Dataset,
    extra_slots: Mapping[str, Any] | None = None,
) -> Dict[str, str]:
    slots: Dict[str, str] = {
        "object_description": _object_description(dataset),
    }
    for key, value in dataset.query.params.items():
        if str(key) in _DYNAMIC_SLOT_NAMES and isinstance(value, (str, int, float)):
            slots[str(key)] = str(value)
    if extra_slots:
        for key, value in extra_slots.items():
            if str(key) in _DYNAMIC_SLOT_NAMES:
                slots[str(key)] = str(value)
    return slots


def build_prompt_artifacts(
    *,
    prompt_query_key: str,
    dynamic_slots: Mapping[str, Any],
    instance_seed: int,
) -> PromptTraceArtifacts:
    rendered_prompt = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(_PROMPT_DEFAULTS.get("bundle_id", PROMPT_BUNDLE_ID)),
        scene_key="dashboard_mixed_chart",
        task_key="dashboard_cross_panel_query",
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slots),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["build_prompt_artifacts", "build_prompt_slots"]
