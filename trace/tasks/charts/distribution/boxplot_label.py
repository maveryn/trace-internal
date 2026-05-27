"""Boxplot distribution task that returns the winning category label."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

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
from ..shared.chart_scene import render_boxplot_scene, render_paired_boxplot_scene, value_axis_render_metadata
from ..shared.complexity import (
    build_chart_complexity,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.distribution_chart_common import (
    DistributionChartDefaults,
    LabeledChartDefaults,
    build_boxplot_dataset_for_variant,
    build_boxplot_median_rank_difference_dataset,
    build_boxplot_paired_median_shift_dataset,
    projected_mark_evidence,
    resolve_chart_axis_variant,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
)
from ..shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from ..shared.param_overrides import apply_query_id_overrides
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


QueryVariant = str

TASK_ID = "charts_distribution_boxplot_label_base"
MEDIAN_RANK_DIFFERENCE_TASK_ID = "task_charts__boxplot__median_rank_difference_value"
PAIRED_MEDIAN_SHIFT_TASK_ID = "task_charts__boxplot__paired_median_shift_label"
SCENE_VARIANT = "boxplot"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "median_reference_label",
    "iqr_extremum_label",
)
_SUPPORTED_MEDIAN_REFERENCE_DIRECTIONS: Tuple[str, ...] = (
    "above_reference_q3",
    "below_reference_q1",
)
_SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = (
    "largest",
    "smallest",
)
_SUPPORTED_PAIRED_SHIFT_QUERY_IDS: Tuple[str, ...] = (
    "paired_median_greatest_increase_label",
    "paired_median_greatest_decrease_label",
    "paired_median_greatest_absolute_change_label",
)
_SUPPORTED_MEDIAN_RANK_QUERY_IDS: Tuple[str, ...] = (
    "median_top_second_difference_value",
    "median_top_third_difference_value",
    "median_top_bottom_difference_value",
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
_MEDIAN_RANK_GEN_DEFAULTS, _MEDIAN_RANK_RENDER_DEFAULTS, _MEDIAN_RANK_PROMPT_DEFAULTS = (
    split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=MEDIAN_RANK_DIFFERENCE_TASK_ID,
    )
)
_PAIRED_SHIFT_GEN_DEFAULTS, _PAIRED_SHIFT_RENDER_DEFAULTS, _PAIRED_SHIFT_PROMPT_DEFAULTS = (
    split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=PAIRED_MEDIAN_SHIFT_TASK_ID,
    )
)
_MEDIAN_RANK_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(
    _TASK_GROUP_DEFAULTS,
    task_id=MEDIAN_RANK_DIFFERENCE_TASK_ID,
)
_PAIRED_SHIFT_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(
    _TASK_GROUP_DEFAULTS,
    task_id=PAIRED_MEDIAN_SHIFT_TASK_ID,
)
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "median_reference_label": 1.0,
    "iqr_extremum_label": 1.0,
}
_PAIRED_SHIFT_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "paired_median_greatest_increase_label": 0.72,
    "paired_median_greatest_decrease_label": 0.72,
    "paired_median_greatest_absolute_change_label": 0.78,
}


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic boxplot query id."""

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
    """Use a per-public-variant occurrence index for subvariant support cycling."""

    support_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return support_params
    if not _uses_uniform_query_id_cycle(params, query_id_probabilities=query_id_probabilities):
        return support_params
    support_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(_SUPPORTED_QUERY_IDS))
    return support_params


def _resolve_median_reference_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the median-reference direction for the merged boxplot variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_MEDIAN_REFERENCE_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="median_reference_direction",
        weights_key="median_reference_direction_weights",
        balance_flag_key="balanced_median_reference_direction_sampling",
        axis_namespace="median_reference_direction",
    )


def _resolve_extremum_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve largest/smallest for the merged IQR-extremum variant."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_EXTREMUM_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
        balance_flag_key="balanced_extremum_direction_sampling",
        axis_namespace="iqr_extremum_direction",
    )


def _internal_boxplot_variant(
    query_id: str,
    *,
    median_reference_direction: str | None,
    extremum_direction: str | None,
) -> str:
    """Map the public boxplot variant plus query parameter to the construction variant."""

    if str(query_id) == "median_reference_label":
        if str(median_reference_direction) == "above_reference_q3":
            return "median_above_reference_q3"
        if str(median_reference_direction) == "below_reference_q1":
            return "median_below_reference_q1"
        raise ValueError(f"unsupported median_reference_direction: {median_reference_direction}")
    if str(query_id) == "iqr_extremum_label":
        if str(extremum_direction) == "largest":
            return "largest_iqr"
        if str(extremum_direction) == "smallest":
            return "smallest_iqr"
        raise ValueError(f"unsupported extremum_direction: {extremum_direction}")
    raise ValueError(f"unsupported boxplot query_id: {query_id}")


def _median_reference_prompt_slots(median_reference_direction: str | None) -> Dict[str, str]:
    """Return prompt slots for the median-reference direction."""

    if median_reference_direction is None:
        return {
            "median_reference_direction_word": "",
            "reference_quartile_name": "",
            "median_reference_gap_phrase": "",
        }
    if str(median_reference_direction) == "above_reference_q3":
        return {
            "median_reference_direction_word": "above",
            "reference_quartile_name": "upper quartile",
            "median_reference_gap_phrase": "between its median and the reference upper quartile",
        }
    if str(median_reference_direction) == "below_reference_q1":
        return {
            "median_reference_direction_word": "below",
            "reference_quartile_name": "lower quartile",
            "median_reference_gap_phrase": "between the reference lower quartile and its median",
        }
    raise ValueError(f"unsupported median_reference_direction: {median_reference_direction}")


def _iqr_extremum_prompt_slots(extremum_direction: str | None) -> Dict[str, str]:
    """Return prompt slots for the IQR extremum direction."""

    if extremum_direction is None:
        return {"extremum_direction": "", "iqr_width_phrase": ""}
    if str(extremum_direction) == "largest":
        return {"extremum_direction": "largest", "iqr_width_phrase": "widest"}
    if str(extremum_direction) == "smallest":
        return {"extremum_direction": "smallest", "iqr_width_phrase": "narrowest"}
    raise ValueError(f"unsupported extremum_direction: {extremum_direction}")


def _resolve_paired_shift_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the paired before/after median-shift query."""

    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_PAIRED_SHIFT_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_PAIRED_SHIFT_QUERY_IDS,
        task_id=PAIRED_MEDIAN_SHIFT_TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_median_rank_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve which ranked medians are compared."""

    resolved_params = dict(params)
    query_id = resolved_params.get("query_id")
    if resolved_params.get("query_id") is None and query_id is not None:
        query_id_text = str(query_id)
        if query_id_text in set(_SUPPORTED_MEDIAN_RANK_QUERY_IDS):
            resolved_params["query_id"] = query_id_text
        elif query_id_text == "median_rank_difference_value":
            resolved_params["query_id"] = "median_top_third_difference_value"
    return resolve_chart_axis_variant(
        params=resolved_params,
        gen_defaults=_MEDIAN_RANK_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_MEDIAN_RANK_QUERY_IDS,
        task_id=MEDIAN_RANK_DIFFERENCE_TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _median_rank_params_for_query(params: Mapping[str, Any], *, query_id: str) -> Dict[str, Any]:
    """Return generation params for one median-rank comparison query."""

    resolved = dict(params)
    resolved["median_rank_upper_rank"] = 1
    if str(query_id) == "median_top_second_difference_value":
        resolved["median_rank_lower_rank"] = 2
    elif str(query_id) == "median_top_third_difference_value":
        resolved["median_rank_lower_rank"] = 3
    elif str(query_id) == "median_top_bottom_difference_value":
        resolved["median_rank_lower_rank"] = "lowest"
    else:
        raise ValueError(f"unsupported median-rank query id: {query_id}")
    return resolved


def _render_boxplot_public_output(
    *,
    task_id: str,
    domain: str,
    task_group: str,
    instance_seed: int,
    effective_params: Mapping[str, Any],
    mark_style: Mapping[str, Any],
    boxplots: Sequence[Any],
    answer_gt: TypedValue,
    evidence_labels: Sequence[str],
    trace_extras: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    prompt_defaults: Mapping[str, Any],
    prompt_task_key: str,
    render_defaults: Mapping[str, Any],
    complexity_weights: Mapping[str, float],
    reasoning_load: float,
    paired_boxplots: Tuple[Sequence[Any], Sequence[Any]] | None = None,
    slot_overrides: Mapping[str, Any] | None = None,
) -> TaskOutput:
    """Render a public boxplot task with default query_id and explicit query_id."""

    render_params = resolve_chart_render_params_for_task(
        {**dict(effective_params), **dict(mark_style)},
        render_defaults=render_defaults,
        defaults=_RENDER_DEFAULTS_FALLBACK,
        instance_seed=int(instance_seed),
    )
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=dict(effective_params),
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    if paired_boxplots is None:
        rendered_scene = render_boxplot_scene(
            background,
            boxplots=boxplots,
            render_params=render_params,
        )
    else:
        before_boxplots, after_boxplots = paired_boxplots
        rendered_scene = render_paired_boxplot_scene(
            background,
            before_boxplots=before_boxplots,
            after_boxplots=after_boxplots,
            render_params=render_params,
            before_title=str(trace_extras.get("paired_panels", {}).get("before", "Before")),
            after_title=str(trace_extras.get("paired_panels", {}).get("after", "After")),
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=dict(effective_params),
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    prompt_selection = render_task_prompt_variants(
        domain=domain,
        task_group=task_group,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_task_key),
        query_key=str(query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "evidence_hint": str(prompt_defaults["evidence_hint"]),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "json_example": str(prompt_defaults["json_example"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            **dict(slot_overrides or {}),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    evidence_projection = projected_mark_evidence(rendered_scene, [str(label) for label in evidence_labels])
    evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
    evidence_gt = TypedValue(type="point_set", value=list(evidence_points))
    label_centers = {
        str(mark["label"]): list(mark["label_center_px"])
        for mark in rendered_scene.mark_traces
    }
    visual_scan_count = int(trace_extras.get("rendered_boxplot_count", trace_extras.get("category_count", 1)))
    visual_scan_range = list(
        trace_extras.get(
            "rendered_boxplot_count_range",
            trace_extras.get("category_count_range", [max(1, visual_scan_count), max(1, visual_scan_count)]),
        )
    )
    trace_params = {
        "query_id": str(query_id),
        "query_id_probabilities": dict(query_id_probabilities),
        **dict(trace_extras),
    }
    trace_payload = {
        "scene_ir": {
            "scene_kind": "chart_boxplot_distribution",
            "domain": str(domain),
            "scene_id": "boxplot",
            "task_id": str(task_id),
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": dict(trace_params),
        },
        "query_spec": {
            "domain": str(domain),
            "scene_id": "boxplot",
            "task_id": str(task_id),
            "query_id": str(query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(trace_params),
        },
        "render_spec": {
            "domain": str(domain),
            "scene_id": "boxplot",
            "task_id": str(task_id),
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
            "domain": str(domain),
            "scene_id": "boxplot",
            "task_id": str(task_id),
            **dict(trace_params),
            "question_format": "numeric_open" if answer_gt.type == "integer" else "label_open",
            "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
            "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
            "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
            **{
                str(key): value
                for key, value in mark_style.items()
                if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
            },
        },
        "witness_symbolic": {
            "type": str(answer_gt.type),
            "value": answer_gt.value,
        },
        "projected_evidence": {
            "point_set": list(evidence_points),
            **dict(evidence_projection),
        },
    }

    complexity = build_chart_complexity(
        weights=complexity_weights,
        components={
            "visual_scan": normalize_int_with_bounds(
                int(visual_scan_count),
                visual_scan_range,
            ),
            "reasoning_load": float(reasoning_load),
            "scene_variant_load": 0.65,
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
        scene_id="boxplot",
        query_id=str(query_id),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


class ChartsDistributionBoxplotLabelTask:
    """Return the label of the boxplot matching one distribution query."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "distribution"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        base_params = dict(params)
        query_id, query_id_probabilities = _resolve_query_id(base_params, instance_seed=int(instance_seed))
        support_params = _support_params_for_query_id_cycle(
            base_params,
            query_id_probabilities=query_id_probabilities,
        )
        effective_params = apply_query_id_overrides(
            support_params,
            query_id=str(query_id),
            default_params=_GEN_DEFAULTS,
        )
        median_reference_direction = None
        median_reference_direction_probabilities: Dict[str, float] = {}
        extremum_direction = None
        extremum_direction_probabilities: Dict[str, float] = {}
        if str(query_id) == "median_reference_label":
            median_reference_direction, median_reference_direction_probabilities = _resolve_median_reference_direction(
                effective_params,
                instance_seed=int(instance_seed),
            )
        elif str(query_id) == "iqr_extremum_label":
            extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
                effective_params,
                instance_seed=int(instance_seed),
            )
        boxplot_variant = _internal_boxplot_variant(
            str(query_id),
            median_reference_direction=median_reference_direction,
            extremum_direction=extremum_direction,
        )
        mark_style = resolve_chart_mark_colors(
            effective_params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_RENDER_DEFAULTS_FALLBACK,
            instance_seed=int(instance_seed),
            scene_variant=SCENE_VARIANT,
            mark_count=1,
        )
        boxplots, answer_label, evidence_value, trace_extras = build_boxplot_dataset_for_variant(
            query_id=str(boxplot_variant),
            params=effective_params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
            mark_style=mark_style,
        )
        render_params = resolve_chart_render_params_for_task(
            {**dict(effective_params), **mark_style},
            render_defaults=_RENDER_DEFAULTS,
            defaults=_RENDER_DEFAULTS_FALLBACK,
            instance_seed=int(instance_seed),
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=effective_params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_boxplot_scene(
            background,
            boxplots=boxplots,
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
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_boxplot",
                "evidence_hint_median_reference_label",
                "evidence_hint_iqr_extremum_label",
                "json_example_median_reference_label",
                "json_example_iqr_extremum_label",
                "json_example_answer_only_median_reference_label",
                "json_example_answer_only_iqr_extremum_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        trace_extras["median_reference_direction"] = str(median_reference_direction or "")
        trace_extras["extremum_direction"] = str(extremum_direction or "")
        median_slots = _median_reference_prompt_slots(median_reference_direction)
        iqr_slots = _iqr_extremum_prompt_slots(extremum_direction)
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_boxplot"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(query_id)}"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults[f"json_example_{str(query_id)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
                "reference_label": str(trace_extras.get("reference_label", "")),
                **dict(median_slots),
                **dict(iqr_slots),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="option_letter", value=str(answer_label))
        projected_labels = (
            [str(trace_extras["reference_label"]), str(answer_label)]
            if "reference_label" in trace_extras
            else [str(answer_label)]
        )
        evidence_projection = projected_mark_evidence(rendered_scene, projected_labels)
        evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
        evidence_gt = TypedValue(type="point_set", value=list(evidence_points))
        label_centers = {
            str(mark["label"]): list(mark["label_center_px"])
            for mark in rendered_scene.mark_traces
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_boxplot_distribution",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": SCENE_VARIANT,
                    "answer_label": str(answer_label),
                    "evidence_value": int(evidence_value),
                    **(
                        {"median_reference_direction": str(median_reference_direction)}
                        if median_reference_direction is not None
                        else {}
                    ),
                    **(
                        {"extremum_direction": str(extremum_direction)}
                        if extremum_direction is not None
                        else {}
                    ),
                    **(
                        {"median_reference_direction_probabilities": dict(median_reference_direction_probabilities)}
                        if median_reference_direction_probabilities
                        else {}
                    ),
                    **(
                        {"extremum_direction_probabilities": dict(extremum_direction_probabilities)}
                        if extremum_direction_probabilities
                        else {}
                    ),
                    **(
                        {
                            "reference_label": str(trace_extras["reference_label"]),
                            "reference_q3": int(trace_extras["reference_q3"]),
                        }
                        if "reference_q3" in trace_extras
                        else {}
                    ),
                    **(
                        {
                            "reference_label": str(trace_extras["reference_label"]),
                            "reference_q1": int(trace_extras["reference_q1"]),
                        }
                        if "reference_q1" in trace_extras
                        else {}
                    ),
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
                        {"median_reference_direction": str(median_reference_direction)}
                        if median_reference_direction is not None
                        else {}
                    ),
                    **(
                        {"extremum_direction": str(extremum_direction)}
                        if extremum_direction is not None
                        else {}
                    ),
                    **(
                        {"median_reference_direction_probabilities": dict(median_reference_direction_probabilities)}
                        if median_reference_direction_probabilities
                        else {}
                    ),
                    **(
                        {"extremum_direction_probabilities": dict(extremum_direction_probabilities)}
                        if extremum_direction_probabilities
                        else {}
                    ),
                    "category_count": int(trace_extras["category_count"]),
                    "category_count_range": list(trace_extras["category_count_range"]),
                    "value_range": list(trace_extras["value_range"]),
                    **(
                        {
                            "reference_label": str(trace_extras["reference_label"]),
                            "reference_q3": int(trace_extras["reference_q3"]),
                        }
                        if "reference_q3" in trace_extras
                        else {}
                    ),
                    **(
                        {
                            "reference_label": str(trace_extras["reference_label"]),
                            "reference_q1": int(trace_extras["reference_q1"]),
                        }
                        if "reference_q1" in trace_extras
                        else {}
                    ),
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
                "answer_label": str(answer_label),
                "evidence_value": int(evidence_value),
                "labels": [str(mark["label"]) for mark in rendered_scene.mark_traces],
                "category_count": int(trace_extras["category_count"]),
                "category_count_range": list(trace_extras["category_count_range"]),
                "value_range": list(trace_extras["value_range"]),
                "quartiles_by_label": dict(trace_extras["quartiles_by_label"]),
                "query_id_probabilities": dict(query_id_probabilities),
                **(
                    {"median_reference_direction": str(median_reference_direction)}
                    if median_reference_direction is not None
                    else {}
                ),
                **(
                    {"extremum_direction": str(extremum_direction)}
                    if extremum_direction is not None
                    else {}
                ),
                **(
                    {"median_reference_direction_probabilities": dict(median_reference_direction_probabilities)}
                    if median_reference_direction_probabilities
                    else {}
                ),
                **(
                    {"extremum_direction_probabilities": dict(extremum_direction_probabilities)}
                    if extremum_direction_probabilities
                    else {}
                ),
                **(
                    {
                        "reference_label": str(trace_extras["reference_label"]),
                        "reference_q3": int(trace_extras["reference_q3"]),
                        "winner_margin": int(trace_extras["winner_margin"]),
                    }
                    if "reference_q3" in trace_extras
                    else {}
                ),
                **(
                    {
                        "reference_label": str(trace_extras["reference_label"]),
                        "reference_q1": int(trace_extras["reference_q1"]),
                        "winner_margin": int(trace_extras["winner_margin"]),
                    }
                    if "reference_q1" in trace_extras
                    else {}
                ),
                "question_format": "label_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                **{
                    str(key): value
                    for key, value in mark_style.items()
                    if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                },
            },
            "witness_symbolic": {
                "type": "integer",
                "value": int(evidence_value),
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
                    int(trace_extras["category_count"]),
                    trace_extras["category_count_range"],
                ),
                "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(query_id)]),
                "scene_variant_load": 0.65,
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
class ChartsDistributionBoxplotSummaryLabelTask(
    MergedChartQueryVariantTaskMixin,
    ChartsDistributionBoxplotLabelTask,
):
    """Return a box label from one sampled boxplot summary query."""

    task_id = "task_charts__boxplot__summary_statistic_label"
    allowed_query_ids = ("median_reference_label", "iqr_extremum_label")


@register_task
class ChartsDistributionBoxplotMedianRankDifferenceValueTask:
    """Return the numeric difference between two ranked boxplot medians."""

    task_id = MEDIAN_RANK_DIFFERENCE_TASK_ID
    domain = "charts"
    task_group = "distribution"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        base_params = dict(params)
        query_id, query_id_probabilities = _resolve_median_rank_query_id(
            base_params,
            instance_seed=int(instance_seed),
        )
        effective_params = _median_rank_params_for_query(base_params, query_id=str(query_id))
        supported_aliases = set(_SUPPORTED_MEDIAN_RANK_QUERY_IDS) | {"", "default", "median_rank_difference_value"}
        for explicit_key in ("query_id", "query_id", "query_id"):
            explicit_value = effective_params.get(str(explicit_key))
            if explicit_value is not None and str(explicit_value) not in supported_aliases:
                raise ValueError(f"unsupported {explicit_key} for {self.task_id}: {explicit_value}")
        mark_style = resolve_chart_mark_colors(
            effective_params,
            render_defaults=_MEDIAN_RANK_RENDER_DEFAULTS,
            defaults=_RENDER_DEFAULTS_FALLBACK,
            instance_seed=int(instance_seed),
            scene_variant=SCENE_VARIANT,
            mark_count=1,
        )
        boxplots, answer, evidence_labels, trace_extras = build_boxplot_median_rank_difference_dataset(
            params=effective_params,
            instance_seed=int(instance_seed),
            gen_defaults=_MEDIAN_RANK_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
            mark_style=mark_style,
        )
        prompt_defaults_raw = required_group_defaults(
            _MEDIAN_RANK_PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_boxplot",
                "answer_hint",
                "evidence_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_defaults = {
            **dict(prompt_defaults_raw),
            "object_description": str(prompt_defaults_raw["object_description_boxplot"]),
        }
        return _render_boxplot_public_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            instance_seed=int(instance_seed),
            effective_params=effective_params,
            mark_style=mark_style,
            boxplots=boxplots,
            answer_gt=TypedValue(type="integer", value=int(answer)),
            evidence_labels=evidence_labels,
            trace_extras=trace_extras,
            query_id=str(query_id),
            query_id_probabilities=dict(query_id_probabilities),
            prompt_defaults=prompt_defaults,
            prompt_task_key=str(prompt_defaults["task_key"]),
            render_defaults=_MEDIAN_RANK_RENDER_DEFAULTS,
            complexity_weights=_MEDIAN_RANK_COMPLEXITY_WEIGHTS,
            reasoning_load=0.74,
        )


@register_task
class ChartsDistributionBoxplotPairedMedianShiftLabelTask:
    """Return the label with the requested paired median shift."""

    task_id = PAIRED_MEDIAN_SHIFT_TASK_ID
    domain = "charts"
    task_group = "distribution"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        base_params = dict(params)
        query_id, query_id_probabilities = _resolve_paired_shift_query_id(
            base_params,
            instance_seed=int(instance_seed),
        )
        effective_params = apply_query_id_overrides(
            base_params,
            query_id=str(query_id),
            default_params=_PAIRED_SHIFT_GEN_DEFAULTS,
        )
        mark_style = resolve_chart_mark_colors(
            effective_params,
            render_defaults=_PAIRED_SHIFT_RENDER_DEFAULTS,
            defaults=_RENDER_DEFAULTS_FALLBACK,
            instance_seed=int(instance_seed),
            scene_variant=SCENE_VARIANT,
            mark_count=1,
        )
        before_boxplots, after_boxplots, answer_label, evidence_labels, trace_extras = build_boxplot_paired_median_shift_dataset(
            query_id=str(query_id),
            params=effective_params,
            instance_seed=int(instance_seed),
            gen_defaults=_PAIRED_SHIFT_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
            mark_style=mark_style,
        )
        boxplots = [*before_boxplots, *after_boxplots]
        prompt_defaults_raw = required_group_defaults(
            _PAIRED_SHIFT_PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_paired_boxplot",
                "answer_hint",
                "evidence_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_defaults = {
            **dict(prompt_defaults_raw),
            "object_description": str(prompt_defaults_raw["object_description_paired_boxplot"]),
        }
        return _render_boxplot_public_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            instance_seed=int(instance_seed),
            effective_params=effective_params,
            mark_style=mark_style,
            boxplots=boxplots,
            paired_boxplots=(before_boxplots, after_boxplots),
            answer_gt=TypedValue(type="option_letter", value=str(answer_label)),
            evidence_labels=evidence_labels,
            trace_extras=trace_extras,
            query_id=str(query_id),
            query_id_probabilities=dict(query_id_probabilities),
            prompt_defaults=prompt_defaults,
            prompt_task_key=str(prompt_defaults["task_key"]),
            render_defaults=_PAIRED_SHIFT_RENDER_DEFAULTS,
            complexity_weights=_PAIRED_SHIFT_COMPLEXITY_WEIGHTS,
            reasoning_load=float(_PAIRED_SHIFT_REASONING_LOAD_BY_VARIANT[str(query_id)]),
        )


__all__ = [
    "ChartsDistributionBoxplotLabelTask",
    "ChartsDistributionBoxplotMedianRankDifferenceValueTask",
    "ChartsDistributionBoxplotPairedMedianShiftLabelTask",
    "ChartsDistributionBoxplotSummaryLabelTask",
]
