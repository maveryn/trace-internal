"""Count categories where one queried series exceeds the other."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
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
from ..shared.chart_scene import render_multiseries_chart_scene
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.labeled_chart_common import resolve_chart_axis_variant, resolve_chart_render_params_for_task
from ..shared.multiseries_chart_common import (
    MultiseriesChartDefaults,
    SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS,
    build_multiseries_mark_specs,
    build_pairwise_comparison_count_dataset,
    projected_category_evidence,
    resolve_multiseries_chart_colors,
)
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TaskVariant = str
SceneVariant = str

TASK_ID = "task_charts_multiseries_pairwise_comparison_count"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "series_a_gt_b_count",
    "series_a_lt_b_count",
)

_DEFAULTS = MultiseriesChartDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "multiseries")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="multiseries")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="multiseries", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "series_a_gt_b_count": 0.0,
    "series_a_lt_b_count": 0.0,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "grouped_bar": 0.0,
    "grouped_horizontal_bar": 0.18,
    "grouped_lollipop": 0.55,
    "multi_line": 1.0,
}


def _normalize_multiseries_visual_scan(trace_extras: Mapping[str, Any]) -> float:
    """Normalize multiseries visual load from the total plotted mark count."""
    category_range = trace_extras.get("category_count_range", [0, 0])
    series_range = trace_extras.get("series_count_range", [0, 0])
    total_marks = int(trace_extras["category_count"]) * int(trace_extras["series_count"])
    total_bounds = [
        int(category_range[0]) * int(series_range[0]),
        int(category_range[1]) * int(series_range[1]),
    ]
    return normalize_int_with_bounds(int(total_marks), total_bounds)


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic multiseries comparison variant."""

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
    """Resolve the multiseries chart scene variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_MULTISERIES_CHART_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


@register_task
class ChartsMultiseriesPairwiseComparisonCountTask:
    """Count categories where one queried series is greater than or less than the other."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "multiseries"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = _resolve_task_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        (
            values_by_category,
            answer_value,
            evidence_labels,
            trace_extras,
        ) = build_pairwise_comparison_count_dataset(
            task_variant=str(task_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )

        category_labels = [str(label) for label in trace_extras["category_labels"]]
        series_labels = [str(label) for label in trace_extras["series_labels"]]
        mark_style = resolve_multiseries_chart_colors(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
            series_count=len(series_labels),
        )
        marks = build_multiseries_mark_specs(
            category_labels=category_labels,
            series_labels=series_labels,
            values_by_category=values_by_category,
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
        rendered_scene = render_multiseries_chart_scene(
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
                "object_description_grouped_bar",
                "object_description_grouped_horizontal_bar",
                "object_description_multi_line",
                "object_description_grouped_lollipop",
                "evidence_hint_series_a_gt_b_count",
                "evidence_hint_series_a_lt_b_count",
                "json_example_series_a_gt_b_count",
                "json_example_series_a_lt_b_count",
                "json_example_answer_only_series_a_gt_b_count",
                "json_example_answer_only_series_a_lt_b_count",
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
                "left_series": str(trace_extras["left_series_label"]),
                "right_series": str(trace_extras["right_series_label"]),
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

        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="label_set", value=list(evidence_labels))

        category_label_centers = {
            str(mark["category_label"]): list(mark["category_label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        evidence_projection = projected_category_evidence(rendered_scene, evidence_labels)

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_multiseries",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "evidence_labels": list(evidence_labels),
                    "queried_series_labels": list(trace_extras["queried_series_labels"]),
                    "comparison": str(trace_extras["comparison"]),
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
                    "task_variant_probabilities": dict(task_variant_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "target_answer": int(trace_extras["target_answer"]),
                    "target_answer_range": list(trace_extras["target_answer_range"]),
                    "series_count": int(trace_extras["series_count"]),
                    "series_count_range": list(trace_extras["series_count_range"]),
                    "category_count": int(trace_extras["category_count"]),
                    "category_count_range": list(trace_extras["category_count_range"]),
                    "queried_series_labels": list(trace_extras["queried_series_labels"]),
                    "comparison": str(trace_extras["comparison"]),
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
                    **{
                        str(key): value
                        for key, value in mark_style.items()
                    },
                },
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "y_axis_max": int(rendered_scene.y_axis_max),
                "y_ticks": [int(value) for value in rendered_scene.y_ticks],
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "category_label_centers_px": dict(category_label_centers),
            },
            "execution_trace": {
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "answer_value": int(answer_value),
                "evidence_labels": list(evidence_labels),
                "category_labels": list(category_labels),
                "series_labels": list(series_labels),
                "queried_series_labels": list(trace_extras["queried_series_labels"]),
                "left_series_label": str(trace_extras["left_series_label"]),
                "right_series_label": str(trace_extras["right_series_label"]),
                "series_count": int(trace_extras["series_count"]),
                "series_count_range": list(trace_extras["series_count_range"]),
                "category_count": int(trace_extras["category_count"]),
                "category_count_range": list(trace_extras["category_count_range"]),
                "target_answer": int(trace_extras["target_answer"]),
                "target_answer_range": list(trace_extras["target_answer_range"]),
                "values_by_category": dict(trace_extras["values_by_category"]),
                "task_variant_probabilities": dict(task_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "numeric_open",
                "comparison": str(trace_extras["comparison"]),
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                **{
                    str(key): value
                    for key, value in mark_style.items()
                    if key != "sampling_policy"
                },
            },
            "witness_symbolic": {
                "type": "label_set",
                "labels": list(evidence_labels),
            },
            "projected_evidence": {
                "label_set": list(evidence_labels),
                **dict(evidence_projection),
            },
        }

        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": _normalize_multiseries_visual_scan(trace_extras),
                "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(task_variant)]),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
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


__all__ = ["ChartsMultiseriesPairwiseComparisonCountTask"]
