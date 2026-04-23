"""Stacked composition-chart arithmetic tasks over category/legend subsets."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

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
from ..shared.chart_scene import render_stacked_chart_scene
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.composition_chart_common import (
    CompositionChartDefaults,
    SUPPORTED_COMPOSITION_TASK_VARIANTS,
    build_composition_subset_dataset_for_variant,
    build_stacked_composition_mark_specs,
    projected_composition_evidence,
    resolve_stacked_chart_colors,
    supported_scene_variants_for_task_variant,
)
from ..shared.labeled_chart_common import resolve_chart_axis_variant, resolve_chart_render_params_for_task
from ..shared.param_overrides import apply_scene_variant_overrides, apply_task_variant_overrides
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TaskVariant = str
SceneVariant = str

TASK_ID = "task_charts_composition_subset_value"

_DEFAULTS = CompositionChartDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "composition")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="composition")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="composition", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "category_subset_sum": 0.42,
    "series_across_categories_sum": 0.62,
    "subset_margin_sum": 1.0,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "stacked_bar": 0.0,
    "stacked_horizontal_bar": 0.16,
}


def _normalize_composition_visual_scan(dataset: Mapping[str, Any]) -> float:
    """Normalize visual load from total visible stacked cells."""

    category_range = dataset.get("category_count_range", [0, 0])
    series_range = dataset.get("series_count_range", [0, 0])
    effective_total = int(dataset["series_count"]) * int(dataset["category_count"])
    effective_bounds = [
        int(series_range[0]) * max(1, int(category_range[0])),
        int(series_range[1]) * max(1, int(category_range[1])),
    ]
    return normalize_int_with_bounds(int(effective_total), effective_bounds)


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic composition query variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_COMPOSITION_TASK_VARIANTS,
        task_id=TASK_ID,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    task_variant: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one stacked scene variant compatible with the selected query."""

    supported = supported_scene_variants_for_task_variant(str(task_variant))
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=supported,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace=f"scene_variant:{str(task_variant)}",
    )


def _format_label_list(labels: Sequence[str]) -> str:
    """Format one short label list for prompt slots."""

    parts = [str(label) for label in labels if str(label).strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return f"{', '.join(parts[:-1])}, and {parts[-1]}"


@register_task
class ChartsCompositionSubsetValueTask:
    """Answer integer composition queries over stacked charts only."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "composition"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        base_params = dict(params)
        task_variant, task_variant_probabilities = _resolve_task_variant(base_params, instance_seed=int(instance_seed))
        variant_params = apply_task_variant_overrides(base_params, task_variant=str(task_variant))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            variant_params,
            task_variant=str(task_variant),
            instance_seed=int(instance_seed),
        )
        effective_params = apply_scene_variant_overrides(
            variant_params,
            task_variant=str(task_variant),
            scene_variant=str(scene_variant),
        )
        dataset = build_composition_subset_dataset_for_variant(
            task_variant=str(task_variant),
            scene_variant=str(scene_variant),
            params=effective_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )

        render_params = resolve_chart_render_params_for_task(
            effective_params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=effective_params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )

        mark_style = resolve_stacked_chart_colors(
            effective_params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
            series_count=int(dataset["series_count"]),
        )
        marks = build_stacked_composition_mark_specs(
            category_labels=dataset["category_labels"],
            series_labels=dataset["series_labels"],
            values_by_category=dataset["values_by_category"],
            mark_style=mark_style,
        )
        rendered_scene = render_stacked_chart_scene(
            background,
            scene_variant=str(scene_variant),
            marks=marks,
            render_params=render_params,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=effective_params,
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
                "object_description_stacked_bar",
                "object_description_stacked_horizontal_bar",
                "evidence_hint_category_subset_sum",
                "evidence_hint_series_across_categories_sum",
                "evidence_hint_subset_margin_sum",
                "json_example_category_subset_sum",
                "json_example_series_across_categories_sum",
                "json_example_subset_margin_sum",
                "json_example_answer_only_category_subset_sum",
                "json_example_answer_only_series_across_categories_sum",
                "json_example_answer_only_subset_margin_sum",
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
                "query_category_label": str(dataset["query_category_label"]),
                "query_series_label": str(dataset["query_series_label"]),
                "query_series_subset_labels": _format_label_list(dataset.get("query_series_subset_labels", [])),
                "query_category_subset_labels": _format_label_list(dataset.get("query_category_subset_labels", [])),
                "left_series_subset_labels": _format_label_list(dataset.get("left_series_subset_labels", [])),
                "right_series_subset_labels": _format_label_list(dataset.get("right_series_subset_labels", [])),
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

        evidence_projection = projected_composition_evidence(
            rendered_scene=rendered_scene,
            evidence_cells=dataset["evidence_cells"],
        )

        answer_value = int(dataset["answer_value"])
        evidence_values = [int(value) for value in dataset["evidence_values"]]
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="integer_list", value=list(evidence_values))

        representative_fill = list(mark_style["series_fill_palette_rgb"][0])
        representative_outline = list(mark_style["series_outline_palette_rgb"][0])
        label_centers = {
            str(mark["category_label"]): list(mark["category_label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        mark_style_trace = {
            "sampling_policy": str(mark_style["sampling_policy"]),
            "mark_fill_rgb": list(representative_fill),
            "mark_outline_rgb": list(representative_outline),
            **{
                str(key): value
                for key, value in mark_style.items()
                if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
            },
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_composition",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "query_category_label": str(dataset["query_category_label"]),
                    "query_category_labels": list(dataset.get("query_category_labels", [])),
                    "query_series_label": str(dataset["query_series_label"]),
                    "query_series_subset_labels": list(dataset.get("query_series_subset_labels", [])),
                    "query_category_subset_labels": list(dataset.get("query_category_subset_labels", [])),
                    "left_series_subset_labels": list(dataset.get("left_series_subset_labels", [])),
                    "right_series_subset_labels": list(dataset.get("right_series_subset_labels", [])),
                    "evidence_labels": list(dataset["evidence_labels"]),
                    "answer_value": int(answer_value),
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
                    "series_count": int(dataset["series_count"]),
                    "series_count_range": list(dataset["series_count_range"]),
                    "category_count": int(dataset["category_count"]),
                    "category_count_range": list(dataset["category_count_range"]),
                    "target_answer": int(dataset["target_answer"]),
                    "target_answer_range": list(dataset["target_answer_range"]),
                    "query_category_label": str(dataset["query_category_label"]),
                    "query_category_labels": list(dataset.get("query_category_labels", [])),
                    "query_series_label": str(dataset["query_series_label"]),
                    "query_series_subset_labels": list(dataset.get("query_series_subset_labels", [])),
                    "query_category_subset_labels": list(dataset.get("query_category_subset_labels", [])),
                    "left_series_subset_labels": list(dataset.get("left_series_subset_labels", [])),
                    "right_series_subset_labels": list(dataset.get("right_series_subset_labels", [])),
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
                "mark_style": dict(mark_style_trace),
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
                "answer_value": int(answer_value),
                "series_labels": list(dataset["series_labels"]),
                "category_labels": list(dataset["category_labels"]),
                "query_category_label": str(dataset["query_category_label"]),
                "query_category_labels": list(dataset.get("query_category_labels", [])),
                "query_series_label": str(dataset["query_series_label"]),
                "query_series_subset_labels": list(dataset.get("query_series_subset_labels", [])),
                "query_category_subset_labels": list(dataset.get("query_category_subset_labels", [])),
                "left_series_subset_labels": list(dataset.get("left_series_subset_labels", [])),
                "right_series_subset_labels": list(dataset.get("right_series_subset_labels", [])),
                "evidence_labels": list(dataset["evidence_labels"]),
                "evidence_values": list(evidence_values),
                "evidence_cells": list(dataset["evidence_cells"]),
                "series_count": int(dataset["series_count"]),
                "series_count_range": list(dataset["series_count_range"]),
                "category_count": int(dataset["category_count"]),
                "category_count_range": list(dataset["category_count_range"]),
                "target_answer": int(dataset["target_answer"]),
                "target_answer_range": list(dataset["target_answer_range"]),
                "task_variant_probabilities": dict(task_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "numeric_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                "mark_fill_rgb": list(representative_fill),
                "mark_outline_rgb": list(representative_outline),
                **{
                    str(key): value
                    for key, value in mark_style.items()
                    if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                },
                **{
                    str(key): value
                    for key, value in dataset.items()
                    if key
                    not in {
                        "answer_value",
                        "series_labels",
                        "category_labels",
                        "query_category_label",
                        "query_category_labels",
                        "query_series_label",
                        "query_series_subset_labels",
                        "query_category_subset_labels",
                        "left_series_subset_labels",
                        "right_series_subset_labels",
                        "evidence_labels",
                        "evidence_values",
                        "evidence_cells",
                        "series_count",
                        "series_count_range",
                        "category_count",
                        "category_count_range",
                        "target_answer",
                        "target_answer_range",
                    }
                },
                "values_by_category": {
                    str(category_label): {
                        str(series_label): int(value)
                        for series_label, value in values.items()
                    }
                    for category_label, values in dataset["values_by_category"].items()
                },
            },
            "witness_symbolic": {
                "type": "integer_list",
                "labels": list(dataset["evidence_labels"]),
                "values": list(evidence_values),
            },
            "projected_evidence": {
                "integer_list": list(evidence_values),
                **dict(evidence_projection),
            },
        }

        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": _normalize_composition_visual_scan(dataset),
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


__all__ = ["ChartsCompositionSubsetValueTask"]
