"""Prompt helpers for solid-formula tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.tasks.shared.config_defaults import required_group_defaults
from trace.tasks.shared.prompt_json_example import dump_prompt_json_examples
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .defaults import DOMAIN, SCENE_ID


def _example_bbox_for_key(key: str) -> list[int]:
    examples = {
        "target_radius_label": [380, 230, 455, 266],
        "target_cylinder_height_label": [590, 310, 675, 350],
        "target_prism_height_label": [185, 286, 245, 332],
        "target_length_label": [540, 334, 620, 382],
        "volume_label": [112, 74, 222, 118],
        "total_height_label": [160, 250, 238, 292],
        "cone_height_label": [602, 146, 690, 188],
        "radius_label": [356, 230, 454, 266],
        "known_length_label": [330, 452, 445, 492],
        "known_width_label": [530, 438, 612, 486],
        "pyramid_height_label": [534, 126, 624, 170],
        "triangle_base_label": [330, 450, 440, 492],
        "wall_height_label": [178, 312, 250, 354],
        "roof_height_label": [420, 188, 502, 230],
    }
    return list(examples.get(str(key), [120, 120, 180, 160]))


def solid_formula_prompt_artifacts(
    *,
    prompt_defaults: Mapping[str, Any],
    prompt_key: str,
    annotation_keys: Sequence[str],
    answer: float,
    instance_seed: int,
):
    """Render prompt variants from external prompt assets."""

    defaults = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
        ),
        context="prompt defaults for solid_formula",
    )
    annotation_names = ", ".join(f'"{key}"' for key in annotation_keys)
    annotation_hint = (
        "set \"annotation\" to a JSON object whose values are pixel bounding boxes "
        f"[x0,y0,x1,y1] for the required visible measurement labels. Required keys: {annotation_names}"
    )
    annotation = {str(key): _example_bbox_for_key(str(key)) for key in annotation_keys}
    json_example, json_example_answer_only = dump_prompt_json_examples(
        annotation=annotation,
        answer=float(answer),
    )
    prompt_selection = render_scene_prompt_variants(
        domain=DOMAIN,
        scene_id=SCENE_ID,
        bundle_id=str(defaults["bundle_id"]),
        scene_key=str(defaults["scene_key"]),
        task_key=str(defaults["task_key"]),
        query_key=str(prompt_key),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "annotation_hint": str(annotation_hint),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    return dict(defaults), build_prompt_trace_artifacts(prompt_selection)


__all__ = ["solid_formula_prompt_artifacts"]
