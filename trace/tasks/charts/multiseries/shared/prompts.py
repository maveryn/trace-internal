"""Prompt assembly for multiseries chart tasks."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.prompt_variants import (
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .comparison_common import DOMAIN, PROMPT_BUNDLE_ID, PROMPT_DEFAULTS, SCENE_ID


TASK_PROMPT_KEY = "multiseries_query"

_OBJECT_DESCRIPTIONS = {
    "grouped_bar": (
        "a grouped bar chart with labeled category groups on the horizontal axis and a legend. "
        "Each colored bar height gives that series value for its category"
    ),
    "grouped_horizontal_bar": (
        "a grouped horizontal bar chart with labeled category groups on the vertical axis and a legend. "
        "Each colored bar length gives that series value for its category"
    ),
    "multi_line": (
        "a multi-line chart with labeled categories on the horizontal axis and a legend. "
        "Each colored series has one point per category, and the relevant values are the points' y-values"
    ),
    "grouped_lollipop": (
        "a grouped lollipop chart with labeled categories on the horizontal axis and a legend. "
        "Each colored point gives that series value for its category"
    ),
}


def object_description(scene_variant: str) -> str:
    return str(_OBJECT_DESCRIPTIONS.get(str(scene_variant), "a multiseries chart with labeled categories and a legend"))


def build_prompt_artifacts(
    *,
    prompt_query_key: str,
    dynamic_slots: Mapping[str, Any],
    instance_seed: int,
) -> PromptTraceArtifacts:
    rendered_prompt = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(PROMPT_DEFAULTS.get("bundle_id", PROMPT_BUNDLE_ID)),
        scene_key="multiseries_chart",
        task_key=TASK_PROMPT_KEY,
        query_key=str(prompt_query_key),
        dynamic_slots=dict(dynamic_slots),
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(rendered_prompt)


__all__ = ["TASK_PROMPT_KEY", "build_prompt_artifacts", "object_description"]
