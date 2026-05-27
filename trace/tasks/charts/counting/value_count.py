"""Chart counting task over supported labeled single-series chart scenes."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
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
from ..shared.chart_scene import render_labeled_chart_scene, value_axis_render_metadata
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.labeled_chart_common import (
    LabeledChartDefaults,
    build_chart_mark_specs,
    build_value_count_dataset_for_variant,
    projected_mark_evidence,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.information_style import prepare_chart_information_scene
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


QueryVariant = str
SceneVariant = str

TASK_ID = "charts_counting_value_count_base"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "threshold_count",
    "in_interval",
)
_SUPPORTED_THRESHOLD_COMPARISONS: Tuple[str, ...] = (
    "greater_than",
    "less_than",
)
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "area",
    "bar",
    "line",
    "scatter",
    "horizontal_bar",
    "dot_plot",
    "lollipop",
)

_DEFAULTS = LabeledChartDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="counting")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="counting", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "threshold_count": 0.0,
    "in_interval": 1.0,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "bar": 0.0,
    "horizontal_bar": 0.08,
    "line": 0.18,
    "area": 0.24,
    "dot_plot": 0.44,
    "lollipop": 0.52,
    "scatter": 0.62,
}


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic chart counting variant."""

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
    """Use a per-public-variant occurrence index for comparator and answer support cycling."""

    support_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_id_cycle(params, query_id_probabilities=query_id_probabilities):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_QUERY_IDS))
    return support_params


def _resolve_threshold_comparison(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the threshold comparator for the merged threshold-count variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_THRESHOLD_COMPARISONS,
        task_id=TASK_ID,
        explicit_key="comparison",
        weights_key="comparison_weights",
        balance_flag_key="balanced_comparison_sampling",
        axis_namespace="threshold_comparison",
    )


def _internal_count_variant(query_id: str, *, comparison: str | None) -> str:
    """Map the public query id plus query parameter to the construction variant."""

    if str(query_id) == "threshold_count":
        if str(comparison) == "greater_than":
            return "above_threshold"
        if str(comparison) == "less_than":
            return "below_threshold"
        raise ValueError(f"unsupported threshold comparison: {comparison}")
    return str(query_id)


def _comparison_phrase(comparison: str) -> str:
    """Return prompt wording for one threshold comparison."""

    if str(comparison) == "greater_than":
        return "greater than"
    if str(comparison) == "less_than":
        return "less than"
    raise ValueError(f"unsupported threshold comparison: {comparison}")


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the chart scene variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


class ChartsCountingValueCountTask:
    """Count labeled chart marks that satisfy a threshold or interval query."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        support_params = _support_params_for_query_id_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
        )
        comparison = None
        comparison_probabilities: Dict[str, float] = {}
        if str(query_id) == "threshold_count":
            comparison, comparison_probabilities = _resolve_threshold_comparison(
                support_params,
                instance_seed=int(instance_seed),
            )
        count_variant = _internal_count_variant(str(query_id), comparison=comparison)
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        values, answer_value, evidence_labels, trace_extras = build_value_count_dataset_for_variant(
            count_variant=str(count_variant),
            scene_variant=str(scene_variant),
            params=support_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
        )

        labels = [str(label) for label in trace_extras["labels"]]
        mark_style = resolve_chart_mark_colors(
            support_params,
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
            {**dict(support_params), **mark_style},
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )

        render_params, background, background_meta, information_style_meta = prepare_chart_information_scene(
            instance_seed=int(instance_seed),
            params=support_params,
            scene_id="single_series",
            task_group=self.task_group,
            render_params=render_params,
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
            params=support_params,
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
                "object_description_area",
                "object_description_bar",
                "object_description_horizontal_bar",
                "object_description_line",
                "object_description_scatter",
                "object_description_dot_plot",
                "object_description_lollipop",
                "evidence_hint_threshold_count",
                "evidence_hint_in_interval",
                "json_example_threshold_count",
                "json_example_in_interval",
                "json_example_answer_only_threshold_count",
                "json_example_answer_only_in_interval",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(query_id)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_id)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "threshold": str(trace_extras.get("threshold", "")),
                "threshold_comparison_phrase": _comparison_phrase(str(comparison)) if comparison is not None else "",
                "interval_min": str(trace_extras.get("interval_min", "")),
                "interval_max": str(trace_extras.get("interval_max", "")),
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
        label_centers = {
            str(mark["label"]): list(mark["label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        values_by_label = {
            str(mark["label"]): int(mark["value"])
            for mark in rendered_scene.mark_traces
        }
        evidence_projection = projected_mark_evidence(rendered_scene, evidence_labels)
        evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
        evidence_gt = TypedValue(type="point_set", value=list(evidence_points))

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_counting",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "evidence_labels": list(evidence_labels),
                    **({"comparison_probabilities": dict(comparison_probabilities)} if comparison_probabilities else {}),
                    **{
                        str(key): value
                        for key, value in trace_extras.items()
                        if key in {"threshold", "comparison", "interval_min", "interval_max", "interval_inclusive"}
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
                    "scene_variant": str(scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    **({"comparison_probabilities": dict(comparison_probabilities)} if comparison_probabilities else {}),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "mark_count": int(trace_extras["mark_count"]),
                    "target_answer": int(trace_extras["target_answer"]),
                    "target_answer_range": list(trace_extras["target_answer_range"]),
                    **{
                        str(key): value
                        for key, value in trace_extras.items()
                        if key in {"threshold", "comparison", "interval_min", "interval_max", "interval_inclusive"}
                    },
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "information_scene_style": dict(information_style_meta),
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
                "scene_variant": str(scene_variant),
                "answer_value": int(answer_value),
                "evidence_labels": list(evidence_labels),
                "labels": [str(label) for label in labels],
                "values": [int(value) for value in values],
                "values_by_label": dict(values_by_label),
                **({"comparison_probabilities": dict(comparison_probabilities)} if comparison_probabilities else {}),
                "mark_count": int(trace_extras["mark_count"]),
                "mark_count_range": list(trace_extras["mark_count_range"]),
                "target_answer": int(trace_extras["target_answer"]),
                "target_answer_range": list(trace_extras["target_answer_range"]),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
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
                        "values_by_label",
                        "mark_count",
                        "mark_count_range",
                        "target_answer",
                        "target_answer_range",
                    }
                },
            },
            "witness_symbolic": {
                "type": "object_set",
                "labels": list(evidence_labels),
            },
            "projected_evidence": {
                "point_set": list(evidence_points),
                **dict(evidence_projection),
            },
        }

        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(
                    int(trace_extras["mark_count"]),
                    trace_extras["mark_count_range"],
                ),
                "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(query_id)]),
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
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsCountingValuePredicateCountTask(MergedChartQueryVariantTaskMixin, ChartsCountingValueCountTask):
    """Count labeled marks satisfying one sampled value predicate."""

    task_id = "task_charts__single_series__value_predicate_count"
    allowed_query_ids = ("threshold_count", "in_interval")


__all__ = [
    "ChartsCountingValuePredicateCountTask",
    "ChartsCountingValueCountTask",
]
