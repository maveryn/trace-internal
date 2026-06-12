"""Histogram distribution task with integer-count answers."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from .....core.scene_config import get_scene_defaults
from .....core.visual.noise import apply_post_image_noise
from ....shared.config_defaults import split_scene_generation_rendering_prompt_defaults
from ....shared.font_assets import font_asset_version, sample_font_family
from ....shared.prompt_variants import (
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ....shared.text_rendering import temporary_default_font_family
from ...shared.chart_scene import render_histogram_scene, value_axis_render_metadata
from ...shared.distribution_chart_common import (
    DistributionChartDefaults,
    LabeledChartDefaults,
    build_histogram_dataset_for_variant,
    projected_mark_annotation,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
)
from ...shared.information_style import prepare_chart_information_scene
from ...shared.visual_defaults import load_chart_scene_noise_defaults


PromptKey = str

SCENE_NAMESPACE = "charts_distribution_histogram_count_base"
SCENE_VARIANT = "histogram"
_SUPPORTED_PROMPT_KEYS: Tuple[str, ...] = (
    "interval_mass",
    "bin_count_between_values",
    "rank_item_bin_label",
)
_SUPPORTED_INTERVAL_RELATIONS: Tuple[str, ...] = (
    "inside",
    "outside",
)

_DEFAULTS = DistributionChartDefaults()
_RENDER_DEFAULTS_FALLBACK = LabeledChartDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "histogram")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    **{"task" "_id": SCENE_NAMESPACE},
)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id="histogram", apply_prob=0.0)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "interval_mass": 0.55,
    "bin_count_between_values": 0.75,
    "rank_item_bin_label": 0.80,
}

_QUERY_TRACE_KEYS = {
    "interval_relation",
    "query_interval_label",
    "query_interval_start_value",
    "query_interval_end_value",
    "interval_bin_span",
    "excluded_interval_bin_span",
    "outside_bin_count",
    "outside_left_bin_count",
    "outside_right_bin_count",
    "target_rank",
    "total_count",
    "rank_fraction_numerator",
    "rank_fraction_denominator",
    "answer_bin_index",
    "answer_bin_label",
    "answer_bin_value",
    "answer_prefix_bin_count",
    "cumulative_count_before_answer_bin",
    "answer_bin_count",
    "cumulative_count_through_answer_bin",
}


def _resolve_interval_relation(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve whether interval-mass annotation is inside or outside the queried interval."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_INTERVAL_RELATIONS,
        **{"task" "_id": SCENE_NAMESPACE},
        explicit_key="interval_relation",
        weights_key="interval_relation_weights",
        balance_flag_key="balanced_interval_relation_sampling",
        axis_namespace="interval_relation",
    )


def _internal_histogram_variant(prompt_key: str, *, interval_relation: str | None) -> str:
    """Map the public histogram variant plus relation parameter to the construction variant."""

    if str(prompt_key) == "interval_mass":
        if interval_relation is None:
            return "interval_mass"
        if str(interval_relation) == "inside":
            return "interval_mass"
        if str(interval_relation) == "outside":
            return "outside_interval_mass"
        raise ValueError(f"unsupported interval_relation: {interval_relation}")
    return str(prompt_key)


def _interval_relation_phrase(interval_relation: str) -> str:
    """Return prompt wording for one interval relation."""

    if str(interval_relation) == "inside":
        return "inside"
    if str(interval_relation) == "outside":
        return "outside"
    raise ValueError(f"unsupported interval_relation: {interval_relation}")


def _histogram_reasoning_load(prompt_key: str, *, interval_relation: str | None) -> float:
    """Return a calibrated reasoning load for the public histogram variant."""

    if str(prompt_key) == "interval_mass" and str(interval_relation) == "outside":
        return 0.85
    return float(_REASONING_LOAD_BY_VARIANT[str(prompt_key)])


def build_histogram_task_parts(
    *,
    public_task_id: str,
    scene_id: str,
    selected_prompt_key: str,
    prompt_key_probabilities: Mapping[str, float],
    params: Dict[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    prompt_key = str(selected_prompt_key)
    support_params = dict(params)
    interval_relation = None
    interval_relation_probabilities: Dict[str, float] = {}
    if str(prompt_key) == "interval_mass":
        interval_relation, interval_relation_probabilities = _resolve_interval_relation(
            support_params,
            instance_seed=int(instance_seed),
        )
    histogram_variant = _internal_histogram_variant(
        str(prompt_key),
        interval_relation=interval_relation,
    )
    mark_style = resolve_chart_mark_colors(
        support_params,
        render_defaults=_RENDER_DEFAULTS,
        defaults=_RENDER_DEFAULTS_FALLBACK,
        instance_seed=int(instance_seed),
        scene_variant=SCENE_VARIANT,
        mark_count=1,
    )
    bins, answer_value, annotation_labels, trace_extras = build_histogram_dataset_for_variant(
        **{"query" "_id": str(histogram_variant)},
        params=support_params,
        instance_seed=int(instance_seed),
        gen_defaults=_GEN_DEFAULTS,
        defaults=_DEFAULTS,
        **{"task" "_id": public_task_id},
        mark_style=mark_style,
    )
    render_params = resolve_chart_render_params_for_task(
        {**dict(support_params), **mark_style},
        render_defaults=_RENDER_DEFAULTS,
        defaults=_RENDER_DEFAULTS_FALLBACK,
        instance_seed=int(instance_seed),
    )

    render_params, background, background_meta, information_style_meta = prepare_chart_information_scene(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=scene_id,
        render_params=render_params,
        protected_colors=(
            tuple(int(value) for value in mark_style["mark_fill_rgb"]),
            tuple(int(value) for value in mark_style["mark_outline_rgb"]),
        ),
    )
    chart_font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_NAMESPACE}.chart_font",
        params=params,
        exclude_tags=("display",),
        explicit_key="chart_font_family",
        weights_key="chart_font_family_weights",
    )
    with temporary_default_font_family(str(chart_font_family)):
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

    if interval_relation is not None:
        trace_extras["interval_relation"] = str(interval_relation)
    prompt_selection = render_scene_prompt_variants(
        domain="charts",
        scene_id=scene_id,
        bundle_id=str(_PROMPT_DEFAULTS.get("bundle_id", "charts_histogram_v1")),
        scene_key="histogram_scene",
        task_key="histogram_query",
        query_key=str(prompt_key),
        dynamic_slots={
            "object_description": "a histogram with labeled x-axis values and bar heights showing counts",
            "query_interval_label": str(trace_extras.get("query_interval_label", "")),
            "query_bin_label": str(trace_extras.get("query_bin_label", "")),
            "target_rank": str(trace_extras.get("target_rank", "")),
            "interval_relation_phrase": (
                _interval_relation_phrase(str(interval_relation)) if interval_relation is not None else ""
            ),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    annotation_projection = projected_mark_annotation(rendered_scene, annotation_labels)
    annotation_bboxes = [list(bbox) for bbox in annotation_projection["bbox_set"]]
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
                "prompt_key": str(prompt_key),
                "scene_variant": SCENE_VARIANT,
                "annotation_labels": list(annotation_labels),
                **(
                    {"interval_relation_probabilities": dict(interval_relation_probabilities)}
                    if interval_relation_probabilities
                    else {}
                ),
                **{
                    str(key): value
                    for key, value in trace_extras.items()
                    if key in _QUERY_TRACE_KEYS
                },
            },
        },
        "query_spec": {
            "prompt_key": str(prompt_key),
            "template_id": str(_PROMPT_DEFAULTS.get("bundle_id", "charts_histogram_v1")),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "prompt_key": str(prompt_key),
                "scene_variant": SCENE_VARIANT,
                "prompt_key_probabilities": dict(prompt_key_probabilities),
                **(
                    {"interval_relation_probabilities": dict(interval_relation_probabilities)}
                    if interval_relation_probabilities
                    else {}
                ),
                "bin_count": int(trace_extras["bin_count"]),
                "target_answer": int(trace_extras["target_answer"]),
                "target_answer_range": list(trace_extras["target_answer_range"]),
                **{
                    str(key): value
                    for key, value in trace_extras.items()
                    if key in _QUERY_TRACE_KEYS
                },
            },
        },
        "render_spec": {
            "canvas_width": int(render_params.canvas_width),
            "canvas_height": int(render_params.canvas_height),
            "coord_space": "pixel",
            "scene_variant": SCENE_VARIANT,
            "background_style": dict(background_meta),
            "information_scene_style": dict(information_style_meta),
            "post_image_noise": dict(post_noise_meta),
            "layout_jitter": dict(render_params.layout_jitter_meta or {}),
            "text_style": {
                "label_font_size_px": int(render_params.label_font_size_px),
                "tick_font_size_px": int(render_params.tick_font_size_px),
                "label_stroke_width_px": int(render_params.label_stroke_width_px),
            },
            "font_assets": {
                "asset_version": font_asset_version(),
                "chart_font_family": str(chart_font_family),
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
            **value_axis_render_metadata(rendered_scene),
        },
        "render_map": {
            "image_id": "img0",
            "plot_bbox_px": list(rendered_scene.plot_bbox_px),
            "label_centers_px": dict(label_centers),
        },
        "execution_trace": {
            "prompt_key": str(prompt_key),
            "scene_variant": SCENE_VARIANT,
            "answer_value": int(answer_value),
            "annotation_labels": list(annotation_labels),
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
            "prompt_key_probabilities": dict(prompt_key_probabilities),
            **(
                {"interval_relation_probabilities": dict(interval_relation_probabilities)}
                if interval_relation_probabilities
                else {}
            ),
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
                    "annotation_labels",
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
            "type": "object_set",
            "value": list(annotation_labels),
        },
        "projected_annotation": {
            "bbox_set": list(annotation_bboxes),
            **dict(annotation_projection),
        },
    }



__all__ = [
    "build_histogram_task_parts",
]
