"""Histogram distribution task with integer-count answers."""

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
from ..shared.chart_scene import render_histogram_scene, value_axis_render_metadata
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.distribution_chart_common import (
    DistributionChartDefaults,
    LabeledChartDefaults,
    build_histogram_dataset_for_variant,
    projected_mark_evidence,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


QueryVariant = str

TASK_ID = "charts_distribution_histogram_count_base"
SCENE_VARIANT = "histogram"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "interval_mass",
    "bin_count_between_values",
    "rank_item_bin_label",
)
_SUPPORTED_INTERVAL_RELATIONS: Tuple[str, ...] = (
    "inside",
    "outside",
)
_CUMULATIVE_RANK_QUERY_IDS: Tuple[str, ...] = (
    "rank_item_bin_label",
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
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
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


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the histogram query id."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_interval_relation(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve whether interval-mass evidence is inside or outside the queried interval."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_INTERVAL_RELATIONS,
        task_id=TASK_ID,
        explicit_key="interval_relation",
        weights_key="interval_relation_weights",
        balance_flag_key="balanced_interval_relation_sampling",
        axis_namespace="interval_relation",
    )


def _internal_histogram_variant(query_id: str, *, interval_relation: str | None) -> str:
    """Map the public histogram variant plus relation parameter to the construction variant."""

    if str(query_id) == "interval_mass":
        if interval_relation is None:
            return "interval_mass"
        if str(interval_relation) == "inside":
            return "interval_mass"
        if str(interval_relation) == "outside":
            return "outside_interval_mass"
        raise ValueError(f"unsupported interval_relation: {interval_relation}")
    return str(query_id)


def _interval_relation_phrase(interval_relation: str) -> str:
    """Return prompt wording for one interval relation."""

    if str(interval_relation) == "inside":
        return "inside"
    if str(interval_relation) == "outside":
        return "outside"
    raise ValueError(f"unsupported interval_relation: {interval_relation}")


def _histogram_reasoning_load(query_id: str, *, interval_relation: str | None) -> float:
    """Return a calibrated reasoning load for the public histogram variant."""

    if str(query_id) == "interval_mass" and str(interval_relation) == "outside":
        return 0.85
    return float(_REASONING_LOAD_BY_VARIANT[str(query_id)])


def _uses_uniform_query_id_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> bool:
    """Return true when `_sample_cursor` is driving the default query-id cycle."""

    if params.get("query_id") is not None or params.get("query_id_weights") is not None:
        return False
    enabled = bool(params.get("balanced_query_id_sampling", _GEN_DEFAULTS.get("balanced_query_id_sampling", True)))
    if not bool(enabled):
        return False
    positives = [float(value) for value in query_id_probabilities.values() if float(value) > 0.0]
    if len(positives) != len(_SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _support_params_for_query_id_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-variant occurrence index for balanced support cycling."""

    support_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_id_cycle(params, query_id_probabilities=query_id_probabilities):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_QUERY_IDS))
    return support_params


class ChartsDistributionHistogramCountTask:
    """Answer integer-count questions over one rendered histogram."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "distribution"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = _support_params_for_query_id_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
        )
        interval_relation = None
        interval_relation_probabilities: Dict[str, float] = {}
        if str(query_id) == "interval_mass":
            interval_relation, interval_relation_probabilities = _resolve_interval_relation(
                support_params,
                instance_seed=int(instance_seed),
            )
        histogram_variant = _internal_histogram_variant(
            str(query_id),
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
        bins, answer_value, evidence_labels, trace_extras = build_histogram_dataset_for_variant(
            query_id=str(histogram_variant),
            params=support_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
            mark_style=mark_style,
        )
        render_params = resolve_chart_render_params_for_task(
            {**dict(support_params), **mark_style},
            render_defaults=_RENDER_DEFAULTS,
            defaults=_RENDER_DEFAULTS_FALLBACK,
            instance_seed=int(instance_seed),
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
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "answer_hint_cumulative_rank",
                "object_description_histogram",
                "evidence_hint_interval_mass",
                "evidence_hint_bin_count_between_values",
                "evidence_hint_rank_item_bin_label",
                "json_example_interval_mass",
                "json_example_bin_count_between_values",
                "json_example_rank_item_bin_label",
                "json_example_answer_only_interval_mass",
                "json_example_answer_only_bin_count_between_values",
                "json_example_answer_only_rank_item_bin_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        if interval_relation is not None:
            trace_extras["interval_relation"] = str(interval_relation)
        answer_hint_key = (
            "answer_hint_cumulative_rank"
            if str(query_id) in _CUMULATIVE_RANK_QUERY_IDS
            else "answer_hint"
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_histogram"]),
                "query_interval_label": str(trace_extras.get("query_interval_label", "")),
                "query_bin_label": str(trace_extras.get("query_bin_label", "")),
                "target_rank": str(trace_extras.get("target_rank", "")),
                "interval_relation_phrase": (
                    _interval_relation_phrase(str(interval_relation)) if interval_relation is not None else ""
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(query_id)}"]),
                "answer_hint": str(prompt_defaults[answer_hint_key]),
                "json_example": str(prompt_defaults[f"json_example_{str(query_id)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_projection = projected_mark_evidence(rendered_scene, evidence_labels)
        evidence_bboxes = [list(bbox) for bbox in evidence_projection["bbox_set"]]
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
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
                    "query_id": str(query_id),
                    "scene_variant": SCENE_VARIANT,
                    "evidence_labels": list(evidence_labels),
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
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "scene_variant": SCENE_VARIANT,
                    "query_id_probabilities": dict(query_id_probabilities),
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
                "post_image_noise": dict(post_noise_meta),
                "layout_jitter": dict(render_params.layout_jitter_meta or {}),
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
                **value_axis_render_metadata(rendered_scene),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "label_centers_px": dict(label_centers),
            },
            "execution_trace": {
                "query_id": str(query_id),
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
                "query_id_probabilities": dict(query_id_probabilities),
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
                "type": "object_set",
                "value": list(evidence_labels),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
                **dict(evidence_projection),
            },
        }

        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(
                    int(trace_extras["bin_count"]),
                    trace_extras["bin_count_range"],
                ),
                "reasoning_load": _histogram_reasoning_load(
                    str(query_id),
                    interval_relation=interval_relation,
                ),
                "scene_variant_load": 0.55,
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
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsDistributionHistogramIntervalValueTask(
    MergedChartQueryVariantTaskMixin,
    ChartsDistributionHistogramCountTask,
):
    """Return one sampled integer value over a histogram interval."""

    task_id = "task_charts__histogram__interval_value"
    allowed_query_ids = ("interval_mass", "bin_count_between_values")


@register_task
class ChartsDistributionHistogramCumulativeRankLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsDistributionHistogramCountTask,
):
    """Return the x-axis value containing a cumulative rank in the histogram."""

    task_id = "task_charts__histogram__cumulative_rank_bin_label"
    allowed_query_ids = (
        "rank_item_bin_label",
    )


__all__ = [
    "ChartsDistributionHistogramCumulativeRankLabelTask",
    "ChartsDistributionHistogramCountTask",
    "ChartsDistributionHistogramIntervalValueTask",
]
