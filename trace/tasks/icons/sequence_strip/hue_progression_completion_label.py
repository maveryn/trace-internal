"""Choose the visual option that completes an icon-color hue progression."""

from __future__ import annotations

import colorsys
from typing import Any, Dict, Mapping, Tuple

from ....core.query_ids import SINGLE_QUERY_ID
from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.annotation_artifacts import bbox_annotation_artifacts
from ...shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from .shared.output import build_completion_trace_payload, render_completion_artifacts
from .shared.prompts import render_sequence_strip_prompt_artifacts
from .shared.rendering import validate_sequence_cell_box_bounds
from .shared.sampling import (
    SequenceCompletionDefaults,
    SequenceCompletionPlan,
    option_values,
    resolve_completion_render_params,
    resolve_cyclic_progression_sample,
    sample_sequence_icon_id,
    sequence_missing_index,
    single_icon_completion_cells,
)


TASK_ID = "task_icons__sequence_strip__hue_progression_completion_label"
DOMAIN = "icons"
SCENE_ID = "sequence_strip"
QUERY_ID = SINGLE_QUERY_ID
PROMPT_QUERY_KEY = "hue_progression_completion_label"
SCENE_KIND = "icons_sequence_hue_completion"
QUESTION_FORMAT = "choose_hue_progression_completion_option"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
COMMON_IDS = {"domain": DOMAIN, "scene_id": SCENE_ID, "task_id": TASK_ID, "query_id": QUERY_ID}
TASK_VERSIONS = default_task_versions()
_DEFAULTS = SequenceCompletionDefaults(scene_icon_size_min_px=62, scene_icon_size_max_px=74)


def _hue_rgb(hue_degrees: int) -> Tuple[int, int, int]:
    red, green, blue = colorsys.hsv_to_rgb(float(int(hue_degrees) % 360) / 360.0, 0.78, 0.86)
    return (int(round(red * 255)), int(round(green * 255)), int(round(blue * 255)))


def _visible_hue_values(*, progression_values: Tuple[int, ...], option_values: Mapping[str, int]) -> Tuple[int, ...]:
    """Return the set of rendered hue anchors for trace and palette metadata."""

    return tuple(int(value) for value in sorted(set((*progression_values, *option_values.values()))))


def _hue_palette(visible_hues: Tuple[int, ...]) -> Tuple[Tuple[int, int, int], ...]:
    """Convert rendered hue anchors into RGB palette entries."""

    return tuple(tuple(int(channel) for channel in _hue_rgb(value)) for value in visible_hues)


def _hue_trace_extra(
    *,
    progression_start: int,
    progression_step: int,
    support_values: Tuple[int, ...],
    visible_hues: Tuple[int, ...],
    nominal_size: int,
) -> Dict[str, Any]:
    """Serialize hue-specific symbolic support and RGB anchors."""

    return {
        "start_hue_degrees": int(progression_start),
        "hue_step_degrees": int(progression_step),
        "hue_value_support_degrees": [int(value) for value in support_values],
        "hue_rgb_by_value": {str(int(value)): list(_hue_rgb(int(value))) for value in visible_hues},
        "hue_icon_size_px": int(nominal_size),
    }


def _build_plan(
    instance_seed: int,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    render_params: Mapping[str, Any],
    fallback_defaults: SequenceCompletionDefaults,
) -> SequenceCompletionPlan:
    """Build hue-specific visual cells and symbolic option bindings."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:plan")
    missing_index = sequence_missing_index(params=params, generation_defaults=generation_defaults, instance_seed=int(instance_seed))
    progression = resolve_cyclic_progression_sample(
        params=params,
        defaults=generation_defaults,
        instance_seed=int(instance_seed),
        missing_index=int(missing_index),
        value_key="hue_value_candidates_degrees",
        step_key="hue_step_candidates_degrees",
        answer_key="answer_hue_degrees",
        start_key="start_hue_degrees",
        fallback_values=tuple(range(0, 360, 30)),
        fallback_steps=(30, 60, 300, 330),
        selection_namespace="hue_progression",
        probability_value_key="hue_values_degrees",
        probability_step_key="hue_steps_degrees",
    )
    icon_id = sample_sequence_icon_id(rng, params=params, generation_defaults=generation_defaults, fallback=fallback_defaults.pool_manifest)
    distractors = [value for value in progression.value_support if int(value) != int(progression.answer_value)]
    correct_label, option_map = option_values(rng, correct_value=int(progression.answer_value), distractor_values=distractors)
    nominal_size = int(params.get("hue_icon_size_px", group_default(generation_defaults, "hue_icon_size_px", 68)))
    sequence_cells, option_cells = single_icon_completion_cells(
        instance_seed=int(instance_seed),
        noise_stem="hue_progression",
        sequence_values=progression.sequence_values,
        option_values_by_label={label: int(value) for label, value in option_map.items()},
        missing_index=int(missing_index),
        icon_id=str(icon_id),
        render_params=render_params,
        tint_for_value=_hue_rgb,
        size_for_value=lambda _value: int(nominal_size),
    )

    visible_hues = _visible_hue_values(
        progression_values=progression.sequence_values,
        option_values={label: int(value) for label, value in option_map.items()},
    )
    return SequenceCompletionPlan(
        attribute_id="hue",
        sequence_rule="constant_hue_step",
        sequence_icon_id=str(icon_id),
        full_sequence_values=tuple(int(value) for value in progression.sequence_values),
        missing_index=int(missing_index),
        correct_option_label=str(correct_label),
        correct_option_value=int(progression.answer_value),
        option_values_by_label={label: int(value) for label, value in option_map.items()},
        sequence_cells=sequence_cells,
        option_cells=option_cells,
        sampled_palette_rgb=_hue_palette(visible_hues),
        support_probabilities=dict(progression.support_probabilities),
        extra_trace=_hue_trace_extra(
            progression_start=int(progression.start_value),
            progression_step=int(progression.step_value),
            support_values=progression.value_support,
            visible_hues=visible_hues,
            nominal_size=int(nominal_size),
        ),
    )


@register_task
class IconsSequenceStripHueProgressionCompletionTask:
    task_id = TASK_ID
    domain = "icons"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate hue-completion output while binding answer and annotation locally."""

        generation_defaults, render_defaults, prompt_defaults = load_scene_generation_rendering_prompt_defaults(
            DOMAIN,
            SCENE_ID,
            task_id=TASK_ID,
        )
        render_params = resolve_completion_render_params(
            params=params,
            render_defaults=render_defaults,
            fallback_defaults=_DEFAULTS,
            instance_seed=instance_seed,
        )
        validate_sequence_cell_box_bounds(render_params)
        plan = _build_plan(instance_seed, params, generation_defaults, render_params, _DEFAULTS)
        rendered = render_completion_artifacts(plan=plan, render_params=render_params)
        annotation_payload = bbox_annotation_artifacts(rendered.correct_option_bbox)
        prompt_defaults, prompt_artifacts = render_sequence_strip_prompt_artifacts(
            instance_seed=instance_seed,
            prompt_defaults=prompt_defaults,
            prompt_query_key=PROMPT_QUERY_KEY,
        )
        trace_payload = build_completion_trace_payload(
            common_ids=COMMON_IDS,
            scene_kind=SCENE_KIND,
            question_format=QUESTION_FORMAT,
            prompt_defaults=prompt_defaults,
            prompt_artifacts=prompt_artifacts,
            plan=plan,
            rendered=rendered,
            annotation_payload=annotation_payload,
            render_params=render_params,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue("string", str(plan.correct_option_label)),
            annotation_gt=annotation_payload.annotation_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=TASK_VERSIONS,
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsSequenceStripHueProgressionCompletionTask"]
