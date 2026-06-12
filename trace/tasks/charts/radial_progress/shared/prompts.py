"""Prompt assembly for radial-progress tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .progress_chart import SCENE_ID, _Dataset, _PROMPT_DEFAULTS, _query_slots


DOMAIN = "charts"
PROMPT_BUNDLE_ID = "charts_radial_progress_v1"
SCENE_PROMPT_KEY = "radial_progress_scene"
COUNT_TASK_PROMPT_KEY = "radial_progress_condition_count_query"
EXTREMUM_TASK_PROMPT_KEY = "radial_progress_remaining_extremum_query"

OBJECT_DESCRIPTION_BY_VARIANT = {
    "full_progress_rings": "a grid of labeled circular progress rings. Each ring shows completion from 0 to 100 percent",
    "semicircle_gauges": "a grid of labeled semicircle progress gauges. Each gauge shows completion from 0 to 100 percent",
    "segmented_radial_bars": "a grid of labeled segmented radial progress bars. Filled segments show completion from 0 to 100 percent",
}


def dynamic_slots(*, dataset: _Dataset) -> dict[str, Any]:
    return {
        "object_description": str(OBJECT_DESCRIPTION_BY_VARIANT[str(dataset.scene_variant)]),
        **_query_slots(str(dataset.query_id), dict(dataset.query.params)),
    }


def build_prompt_artifacts(
    *,
    prompt_query_key: str,
    is_label_answer: bool,
    dynamic_slot_values: Mapping[str, Any],
    instance_seed: int,
) -> PromptTraceArtifacts:
    rendered_prompt = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(_PROMPT_DEFAULTS.get("bundle_id", PROMPT_BUNDLE_ID)),
        scene_key=SCENE_PROMPT_KEY,
        task_key=EXTREMUM_TASK_PROMPT_KEY if bool(is_label_answer) else COUNT_TASK_PROMPT_KEY,
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slot_values),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["build_prompt_artifacts", "dynamic_slots"]
