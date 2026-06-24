"""Prompt helpers for circular-sector formula objectives."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.prompt_json_example import dump_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    PromptTraceArtifacts,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .defaults import DOMAIN, SCENE_ID


def _bbox_example_for_roles(roles: tuple[str, ...]) -> dict[str, list[int]]:
    annotation: dict[str, list[int]] = {}
    for index, role in enumerate(roles):
        row = int(index) // 3
        col = int(index) % 3
        x0 = 120 + col * 120
        y0 = 150 + row * 80
        annotation[str(role)] = [x0, y0, x0 + 54, y0 + 38]
    return annotation


def sector_prompt_artifacts(
    *,
    prompt_defaults: Mapping[str, Any],
    prompt_task_key: str,
    prompt_branch_key: str,
    annotation_roles: tuple[str, ...],
    answer: float,
    arc_length: float,
    sector_area: float,
    instance_seed: int,
) -> tuple[dict[str, Any], PromptTraceArtifacts]:
    """Render prompt variants for one selected sector formula branch."""

    defaults = required_group_defaults(
        prompt_defaults,
        ("bundle_id", "scene_key"),
        context="prompt defaults for sector",
    )
    json_example, json_example_answer_only = dump_prompt_json_examples(
        annotation=_bbox_example_for_roles(tuple(annotation_roles)),
        answer=round(float(answer), 1),
    )
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(defaults["bundle_id"]),
        scene_key=str(defaults["scene_key"]),
        task_key=str(prompt_task_key),
        query_key=str(prompt_branch_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "arc_length": f"{float(arc_length):.1f}",
            "sector_area": f"{float(sector_area):.1f}",
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    return dict(defaults), build_prompt_trace_artifacts(prompt_selection)


__all__ = ["sector_prompt_artifacts"]
