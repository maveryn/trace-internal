"""Histogram distribution task with integer-count answers."""

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
from ..shared.chart_scene import render_histogram_scene
from ..shared.distribution_chart_common import (
    DistributionChartDefaults,
    LabeledChartDefaults,
    build_histogram_dataset_for_variant,
    projected_mark_evidence,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
)
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TaskVariant = str

TASK_ID = "task_charts_distribution_histogram_count"
SCENE_VARIANT = "histogram"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "modal_bin_count",
    "interval_mass",
    "cumulative_count_to_bin",
)

_DEFAULTS = DistributionChartDefaults()
_RENDER_DEFAULTS_FALLBACK = LabeledChartDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "distribution")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="distribution")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="distribution", apply_prob=0.0)


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the histogram query variant."""

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


@register_task
class ChartsDistributionHistogramCountTask:
    """Answer integer-count questions over one rendered histogram."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "distribution"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = _resolve_task_variant(params, instance_seed=int(instance_seed))
        mark_style = resolve_chart_mark_colors(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_RENDER_DEFAULTS_FALLBACK,
            instance_seed=int(instance_seed),
            scene_variant=SCENE_VARIANT,
            mark_count=1,
        )
        bins, answer_value, evidence_labels, trace_extras = build_histogram_dataset_for_variant(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
            mark_style=mark_style,
        )
        render_params = resolve_chart_render_params_for_task(
            {**dict(params), **mark_style},
            render_defaults=_RENDER_DEFAULTS,
            defaults=_RENDER_DEFAULTS_FALLBACK,
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_histogram_scene(
            background,
            bins=bins,
            render_params=render_params,
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
                "object_description_histogram",
                "evidence_hint_modal_bin_count",
                "evidence_hint_interval_mass",
                "evidence_hint_cumulative_count_to_bin",
                "json_example_modal_bin_count",
                "json_example_interval_mass",
                "json_example_cumulative_count_to_bin",
                "json_example_answer_only_modal_bin_count",
                "json_example_answer_only_interval_mass",
                "json_example_answer_only_cumulative_count_to_bin",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_histogram"]),
                "query_interval_label": str(trace_extras.get("query_interval_label", "")),
                "query_bin_label": str(trace_extras.get("query_bin_label", "")),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(task_variant)}"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults[f"json_example_{str(task_variant)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(task_variant)}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="label_set", value=list(evidence_labels))
        evidence_projection = projected_mark_evidence(rendered_scene, evidence_labels)
        label_centers = {
            str(mark["label"]): list(mark["label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        counts_by_label = {
            str(mark["label"]): int(mark["value"])
            for mark in rendered_scene.mark_traces
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_histogram_distribution",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": SCENE_VARIANT,
                    "evidence_labels": list(evidence_labels),
                    **{
                        str(key): value
                        for key, value in trace_extras.items()
                        if key in {"query_interval_label", "query_bin_label", "modal_bin_label", "interval_bin_span", "prefix_bin_count"}
                    },
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
                    "scene_variant": SCENE_VARIANT,
                    "task_variant_probabilities": dict(task_variant_probabilities),
                    "bin_count": int(trace_extras["bin_count"]),
                    "target_answer": int(trace_extras["target_answer"]),
                    "target_answer_range": list(trace_extras["target_answer_range"]),
                    **{
                        str(key): value
                        for key, value in trace_extras.items()
                        if key in {"query_interval_label", "query_bin_label", "modal_bin_label", "interval_bin_span", "prefix_bin_count"}
                    },
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": SCENE_VARIANT,
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
                "scene_variant": SCENE_VARIANT,
                "answer_value": int(answer_value),
                "evidence_labels": list(evidence_labels),
                "labels": [str(item["label"]) for item in rendered_scene.mark_traces],
                "bin_counts": [int(item["value"]) for item in rendered_scene.mark_traces],
                "counts_by_label": dict(counts_by_label),
                "bin_count": int(trace_extras["bin_count"]),
                "bin_count_range": list(trace_extras["bin_count_range"]),
                "bin_width": int(trace_extras["bin_width"]),
                "bin_width_range": list(trace_extras["bin_width_range"]),
                "bin_start": int(trace_extras["bin_start"]),
                "bin_start_range": list(trace_extras["bin_start_range"]),
                "bin_frequency_range": list(trace_extras["bin_frequency_range"]),
                "target_answer": int(trace_extras["target_answer"]),
                "target_answer_range": list(trace_extras["target_answer_range"]),
                "task_variant_probabilities": dict(task_variant_probabilities),
                "question_format": "numeric_open",
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
                    if key
                    not in {
                        "labels",
                        "bin_counts",
                        "evidence_labels",
                        "bin_count",
                        "bin_count_range",
                        "bin_width",
                        "bin_width_range",
                        "bin_start",
                        "bin_start_range",
                        "bin_frequency_range",
                        "target_answer",
                        "target_answer_range",
                    }
                },
            },
            "witness_symbolic": {
                "type": "label_set",
                "value": list(evidence_labels),
            },
            "projected_evidence": {
                "label_set": list(evidence_labels),
                **dict(evidence_projection),
            },
        }

        complexity = TaskComplexity(
            complexity_score=float(0.24 + 0.04 * int(trace_extras["bin_count"])),
            complexity_components={
                "task_variant": str(task_variant),
                "scene_variant": SCENE_VARIANT,
                "bin_count": int(trace_extras["bin_count"]),
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


__all__ = ["ChartsDistributionHistogramCountTask"]
