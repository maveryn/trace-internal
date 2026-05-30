"""Chart statistics task over labeled single-series axis-based chart scenes."""

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
from ...shared.text_rendering import temporary_default_font_family
from ..shared.chart_scene import render_labeled_chart_scene, value_axis_render_metadata
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.labeled_chart_common import (
    LabeledChartDefaults,
    SUPPORTED_LABELED_CHART_SCENE_VARIANTS,
    build_chart_mark_specs,
    build_summary_statistics_dataset_for_variant,
    is_pie_like_scene_variant,
    projected_mark_evidence,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.information_style import prepare_chart_information_scene
from ..shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_background_defaults,
    load_chart_noise_defaults,
    sample_chart_font_family,
)


StatisticKind = str
SceneVariant = str

TASK_ID = "charts_statistics_summary_query_base"
_VALUE_QUERY_IDS: Tuple[str, ...] = (
    "order_statistic_value",
)
_LABEL_QUERY_IDS: Tuple[str, ...] = (
    "order_statistic_label",
)
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = _VALUE_QUERY_IDS + _LABEL_QUERY_IDS
_SUPPORTED_STATISTIC_KINDS: Tuple[str, ...] = (
    "median",
    "nth_highest",
    "nth_lowest",
)
_TARGET_ANSWER_RANGES: Dict[str, Tuple[int, int]] = {
    "median": (1, 99),
}
_SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = tuple(
    str(scene_variant)
    for scene_variant in SUPPORTED_LABELED_CHART_SCENE_VARIANTS
    if not is_pie_like_scene_variant(str(scene_variant)) and str(scene_variant) != "radar"
)

_DEFAULTS = LabeledChartDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "statistics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="statistics")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="statistics", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
_REASONING_LOAD_BY_STATISTIC: Dict[str, float] = {
    "median": 0.75,
    "nth_highest": 1.0,
    "nth_lowest": 1.0,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "bar": 0.0,
    "horizontal_bar": 0.10,
    "line": 0.25,
    "area": 0.35,
    "dot_plot": 0.45,
    "lollipop": 0.55,
    "scatter": 1.0,
}


def _public_task_param_overrides(task_id: str) -> Dict[str, Any]:
    """Return task-id-specific generation/rendering params for public wrappers."""

    overrides: Dict[str, Any] = {}
    if not isinstance(_TASK_GROUP_DEFAULTS, Mapping):
        return overrides
    for section in ("generation", "rendering"):
        section_cfg = _TASK_GROUP_DEFAULTS.get(section)
        if not isinstance(section_cfg, Mapping):
            continue
        task_overrides = section_cfg.get("task_overrides")
        if not isinstance(task_overrides, Mapping):
            continue
        task_values = task_overrides.get(str(task_id))
        if isinstance(task_values, Mapping):
            overrides.update(dict(task_values))
    return overrides


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic chart statistic variant."""

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


def _resolve_statistic_kind(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the order statistic requested inside the public answer-target variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_STATISTIC_KINDS,
        task_id=TASK_ID,
        explicit_key="statistic_kind",
        weights_key="statistic_kind_weights",
        balance_flag_key="balanced_statistic_kind_sampling",
        axis_namespace="statistic_kind",
    )


def _support_sampling_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Decorrelate statistic support sampling from balanced public/query axes."""

    support_params = dict(params)
    if "_sample_cursor" not in support_params:
        return support_params
    divisor = 1
    if "query_id" not in support_params and "query_id_weights" not in support_params:
        divisor *= max(1, len(_SUPPORTED_QUERY_IDS))
    if "statistic_kind" not in support_params and "statistic_kind_weights" not in support_params:
        divisor *= max(1, len(_SUPPORTED_STATISTIC_KINDS))
    support_params["_sample_cursor"] = int(support_params["_sample_cursor"]) // max(1, divisor)
    return support_params


def _ordinal(value: int) -> str:
    """Return a compact English ordinal for prompt slots."""

    number = int(value)
    suffix = "th"
    if number % 100 not in {11, 12, 13}:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def _statistic_prompt(statistic_kind: str, *, rank_n_ordinal: str) -> str:
    """Return public prompt wording for the sampled order-statistic knob."""

    if str(statistic_kind) == "median":
        return "median value"
    if str(statistic_kind) == "nth_highest":
        return f"{str(rank_n_ordinal)}-highest distinct displayed value"
    if str(statistic_kind) == "nth_lowest":
        return f"{str(rank_n_ordinal)}-lowest distinct displayed value"
    raise ValueError(f"unsupported statistic_kind: {statistic_kind}")


class ChartsStatisticsSummaryQueryTask:
    """Return either a requested statistic value or the matching mark label."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "statistics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        public_overrides = (
            _public_task_param_overrides(str(self.task_id))
            if str(self.task_id) != str(TASK_ID)
            else {}
        )
        if public_overrides:
            merged_params = dict(public_overrides)
            merged_params.update(dict(params))
            params = merged_params
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        statistic_kind, statistic_kind_probabilities = _resolve_statistic_kind(
            params,
            instance_seed=int(instance_seed),
        )
        answer_is_label = str(query_id) == "order_statistic_label"
        support_params = _support_sampling_params(params)
        values, answer_value, evidence_labels, trace_extras = build_summary_statistics_dataset_for_variant(
            statistic_kind=str(statistic_kind),
            scene_variant=str(scene_variant),
            params=support_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            target_answer_ranges=_TARGET_ANSWER_RANGES,
            task_id=self.task_id,
        )

        labels = [str(label) for label in trace_extras["labels"]]
        answer_label = str(evidence_labels[0]) if answer_is_label else ""
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
            instance_seed=int(instance_seed),
        )

        render_params, background, background_meta, information_style_meta = prepare_chart_information_scene(
            instance_seed=int(instance_seed),
            params=params,
            scene_id="single_series",
            task_group=self.task_group,
            render_params=render_params,
        )
        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
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
                "scene_key",
                "task_key_value",
                "task_key_label",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_value",
                "answer_hint_label",
                "object_description_area",
                "object_description_bar",
                "object_description_horizontal_bar",
                "object_description_line",
                "object_description_scatter",
                "object_description_dot_plot",
                "object_description_lollipop",
                "evidence_hint_median",
                "evidence_hint_nth_highest",
                "evidence_hint_nth_lowest",
                "evidence_hint_label_median",
                "evidence_hint_label_nth_highest",
                "evidence_hint_label_nth_lowest",
                "json_example_median",
                "json_example_nth_highest",
                "json_example_nth_lowest",
                "json_example_label_median",
                "json_example_label_nth_highest",
                "json_example_label_nth_lowest",
                "json_example_answer_only_median",
                "json_example_answer_only_nth_highest",
                "json_example_answer_only_nth_lowest",
                "json_example_answer_only_label_median",
                "json_example_answer_only_label_nth_highest",
                "json_example_answer_only_label_nth_lowest",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        rank_n = trace_extras.get("rank_n", None)
        rank_n_ordinal = _ordinal(int(rank_n)) if rank_n is not None else ""
        evidence_key = f"label_{str(statistic_kind)}" if answer_is_label else str(statistic_kind)
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(evidence_key)}"])
        json_example = str(prompt_defaults[f"json_example_{str(evidence_key)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(evidence_key)}"])
        task_key = str(prompt_defaults["task_key_label" if answer_is_label else "task_key_value"])
        answer_hint = str(prompt_defaults["answer_hint_label" if answer_is_label else "answer_hint_value"])

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(task_key),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "rank_n_ordinal": str(rank_n_ordinal),
                "statistic_prompt": _statistic_prompt(str(statistic_kind), rank_n_ordinal=str(rank_n_ordinal)),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        if answer_is_label:
            answer_gt = TypedValue(type="option_letter", value=str(answer_label))
            evidence_projection = projected_mark_evidence(rendered_scene, [str(answer_label)])
            evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
            evidence_gt = TypedValue(type="point_set", value=list(evidence_points))
            witness_symbolic = {"type": "integer", "value": int(answer_value)}
            projected_evidence = {
                "type": "point_set",
                "point_set": list(evidence_points),
                **dict(evidence_projection),
            }
            question_format = "label_open"
        else:
            answer_gt = TypedValue(type="integer", value=int(answer_value))
            evidence_projection = projected_mark_evidence(rendered_scene, evidence_labels)
            evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
            evidence_gt = TypedValue(type="point_set", value=list(evidence_points))
            witness_symbolic = {"type": "object_set", "labels": list(evidence_labels)}
            projected_evidence = {
                "type": "point_set",
                "point_set": list(evidence_points),
                **dict(evidence_projection),
            }
            question_format = "numeric_open"

        label_centers = {
            str(mark["label"]): list(mark["label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        values_by_label = {
            str(mark["label"]): int(mark["value"])
            for mark in rendered_scene.mark_traces
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_statistics",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "statistic_kind": str(statistic_kind),
                    "answer_value": int(answer_value),
                    "evidence_labels": list(evidence_labels),
                    **({"answer_label": str(answer_label)} if answer_is_label else {}),
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
                    "statistic_kind": str(statistic_kind),
                    "answer_target": "label" if answer_is_label else "value",
                    "query_id_probabilities": dict(query_id_probabilities),
                    "statistic_kind_probabilities": dict(statistic_kind_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "mark_count": int(trace_extras["mark_count"]),
                    "target_answer": int(trace_extras["target_answer"]),
                    "target_answer_range": list(trace_extras["target_answer_range"]),
                    **({"rank_n": int(rank_n)} if rank_n is not None else {}),
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
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
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
                "statistic_kind": str(statistic_kind),
                "answer_value": int(answer_value),
                "evidence_labels": list(evidence_labels),
                **({"answer_label": str(answer_label), "evidence_value": int(answer_value)} if answer_is_label else {}),
                "labels": [str(label) for label in labels],
                "values": [int(value) for value in values],
                "values_by_label": dict(values_by_label),
                "mark_count": int(trace_extras["mark_count"]),
                "mark_count_range": list(trace_extras["mark_count_range"]),
                "target_answer": int(trace_extras["target_answer"]),
                "target_answer_range": list(trace_extras["target_answer_range"]),
                "query_id_probabilities": dict(query_id_probabilities),
                "statistic_kind_probabilities": dict(statistic_kind_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": str(question_format),
                "answer_target": "label" if answer_is_label else "value",
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
            "witness_symbolic": dict(witness_symbolic),
            "projected_evidence": dict(projected_evidence),
        }

        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(
                    int(trace_extras["mark_count"]),
                    trace_extras["mark_count_range"],
                ),
                "reasoning_load": min(
                    1.0,
                    float(_REASONING_LOAD_BY_STATISTIC[str(statistic_kind)]) + (0.05 if answer_is_label else 0.0),
                ),
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
            scene_id="single_series",
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsSingleSeriesOrderStatisticValueTask(MergedChartQueryVariantTaskMixin, ChartsStatisticsSummaryQueryTask):
    """Return a sampled order-statistic value from a labeled chart."""

    task_id = "task_charts__single_series__order_statistic_value"
    allowed_query_ids = _VALUE_QUERY_IDS


@register_task
class ChartsSingleSeriesOrderStatisticLabelTask(MergedChartQueryVariantTaskMixin, ChartsStatisticsSummaryQueryTask):
    """Return the label matching a sampled order statistic from a labeled chart."""

    task_id = "task_charts__single_series__order_statistic_label"
    allowed_query_ids = _LABEL_QUERY_IDS


__all__ = [
    "ChartsSingleSeriesOrderStatisticLabelTask",
    "ChartsSingleSeriesOrderStatisticValueTask",
    "ChartsStatisticsSummaryQueryTask",
]
