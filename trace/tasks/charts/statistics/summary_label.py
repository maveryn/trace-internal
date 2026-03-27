"""Chart statistics task that returns the winning mark label."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.chart_scene import render_labeled_chart_scene
from ..shared.labeled_chart_common import (
    LabeledChartDefaults,
    SUPPORTED_LABELED_CHART_SCENE_VARIANTS,
    build_chart_mark_specs,
    build_summary_statistics_dataset_for_variant,
    projected_mark_evidence,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
)
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


StatisticKind = str
SceneVariant = str

TASK_ID = "task_charts_statistics_summary_label"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "argmax",
    "argmin",
    "median_label",
)
_TASK_VARIANT_TO_STATISTIC: Dict[str, str] = {
    "argmax": "max",
    "argmin": "min",
    "median_label": "median",
}
_TARGET_ANSWER_RANGES: Dict[str, Tuple[int, int]] = {
    "max": (4, 12),
    "min": (1, 8),
    "median": (3, 10),
}

_DEFAULTS = LabeledChartDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "statistics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="statistics")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="statistics", apply_prob=0.0)


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic label-answer chart variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_TASK_VARIANTS,
        task_id=TASK_ID,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the chart scene variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_LABELED_CHART_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


@register_task
class ChartsStatisticsSummaryLabelTask:
    """Return the label of the mark that matches a requested statistic."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "statistics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = _resolve_task_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        statistic_kind = str(_TASK_VARIANT_TO_STATISTIC[str(task_variant)])
        values, evidence_value, evidence_labels, trace_extras = build_summary_statistics_dataset_for_variant(
            statistic_kind=str(statistic_kind),
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            target_answer_ranges=_TARGET_ANSWER_RANGES,
            task_id=self.task_id,
        )

        answer_label = str(evidence_labels[0])
        labels = [str(label) for label in trace_extras["labels"]]
        mark_style = resolve_chart_mark_colors(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
            scene_variant=str(scene_variant),
            mark_count=len(labels),
        )
        marks = build_chart_mark_specs(
            labels=labels,
            values=values,
            scene_variant=str(scene_variant),
            mark_style=mark_style,
        )
        render_params = resolve_chart_render_params_for_task(
            {**dict(params), **mark_style},
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_labeled_chart_scene(
            background,
            scene_variant=str(scene_variant),
            marks=marks,
            render_params=render_params,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_area",
                "object_description_bar",
                "object_description_pie",
                "object_description_donut",
                "object_description_horizontal_bar",
                "object_description_line",
                "object_description_scatter",
                "object_description_radar",
                "object_description_dot_plot",
                "object_description_lollipop",
                "evidence_hint_argmax",
                "evidence_hint_argmin",
                "evidence_hint_median_label",
                "json_example_argmax",
                "json_example_argmin",
                "json_example_median_label",
                "json_example_answer_only_argmax",
                "json_example_answer_only_argmin",
                "json_example_answer_only_median_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(task_variant)}"])
        json_example = str(prompt_defaults[f"json_example_{str(task_variant)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(task_variant)}"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        evidence_gt = TypedValue(type="integer", value=int(evidence_value))
        label_centers = {
            str(mark["label"]): list(mark["label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        values_by_label = {
            str(mark["label"]): int(mark["value"])
            for mark in rendered_scene.mark_traces
        }
        evidence_projection = projected_mark_evidence(rendered_scene, [answer_label])

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_statistics",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "statistic_kind": str(statistic_kind),
                    "answer_label": str(answer_label),
                    "evidence_value": int(evidence_value),
                },
            },
            "query_spec": {
                "task_variant": str(task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "statistic_kind": str(statistic_kind),
                    "task_variant_probabilities": dict(task_variant_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "mark_count": int(trace_extras["mark_count"]),
                    "target_answer": int(trace_extras["target_answer"]),
                    "target_answer_range": list(trace_extras["target_answer_range"]),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "text_style": {
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "tick_font_size_px": int(render_params.tick_font_size_px),
                    "label_stroke_width_px": int(render_params.label_stroke_width_px),
                },
                "axis_style": {
                    "axis_line_width_px": int(render_params.axis_line_width_px),
                    "grid_line_width_px": int(render_params.grid_line_width_px),
                    "tick_length_px": int(render_params.tick_length_px),
                },
                "mark_style": {
                    "sampling_policy": str(mark_style["sampling_policy"]),
                    "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                    "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                    **{
                        str(key): value
                        for key, value in mark_style.items()
                        if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                    },
                },
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "y_axis_max": int(rendered_scene.y_axis_max),
                "y_ticks": [int(value) for value in rendered_scene.y_ticks],
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "label_centers_px": dict(label_centers),
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "statistic_kind": str(statistic_kind),
                "answer_label": str(answer_label),
                "evidence_value": int(evidence_value),
                "labels": [str(label) for label in labels],
                "values": [int(value) for value in values],
                "values_by_label": dict(values_by_label),
                "mark_count": int(trace_extras["mark_count"]),
                "mark_count_range": list(trace_extras["mark_count_range"]),
                "target_answer": int(trace_extras["target_answer"]),
                "target_answer_range": list(trace_extras["target_answer_range"]),
                "task_variant_probabilities": dict(task_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "label_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                **{
                    str(key): value
                    for key, value in mark_style.items()
                    if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                },
                **{
                    str(key): value
                    for key, value in trace_extras.items()
                    if key not in {"labels", "values_by_label", "mark_count", "mark_count_range", "target_answer", "target_answer_range"}
                },
            },
            "witness_symbolic": {
                "type": "integer",
                "value": int(evidence_value),
            },
            "projected_evidence": {
                "integer": int(evidence_value),
                **dict(evidence_projection),
            },
        }

        complexity = TaskComplexity(
            complexity_score=float(0.2 + 0.05 * int(trace_extras["mark_count"])),
            complexity_components={
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "mark_count": int(trace_extras["mark_count"]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["ChartsStatisticsSummaryLabelTask"]
