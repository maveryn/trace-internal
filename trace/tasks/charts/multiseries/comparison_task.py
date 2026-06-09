"""Generation implementation for multiseries comparison tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import required_group_defaults
from ...shared.font_assets import font_asset_version
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import temporary_default_font_family
from ..shared.chart_scene import render_multiseries_chart_scene, value_axis_render_metadata
from ..shared.complexity import build_chart_complexity, normalize_int_with_bounds
from ..shared.labeled_chart_common import resolve_chart_render_params_for_task
from ..shared.multiseries_chart_common import (
    build_category_total_extremum_label_dataset,
    build_conditional_gap_value_dataset,
    build_delta_extremum_label_dataset,
    build_multiseries_mark_specs,
    build_pair_equality_label_dataset,
    build_pairwise_comparison_count_dataset,
    build_ratio_extremum_label_dataset,
    build_series_rank_at_category_label_dataset,
    projected_multiseries_mark_annotation,
    resolve_multiseries_chart_colors,
)
from .comparison_common import (
    TASK_ID,
    _CATEGORY_TOTAL_QUERY_ID,
    _CHANGE_QUERY_ID,
    _COMPLEXITY_WEIGHTS,
    _CONDITIONAL_AGGREGATE_QUERY_ID,
    _CONDITIONAL_AGGREGATE_REASONING_LOADS,
    _CONDITIONAL_EXTREMUM_QUERY_ID,
    _DEFAULTS,
    _EQUALITY_QUERY_ID,
    _GEN_DEFAULTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_MEASURE,
    _REASONING_LOAD_BY_VARIANT,
    _RENDER_DEFAULTS,
    _SCENE_VARIANT_LOADS,
    _SERIES_RANK_QUERY_ID,
    _SUPPORTED_CHANGE_DIRECTIONS,
    _SUPPORTED_CHANGE_MEASURES,
    _SUPPORTED_COMPARISONS,
    _SUPPORTED_CONDITIONAL_GAP_AGGREGATE_KINDS,
    _SUPPORTED_EXTREMUM_DIRECTIONS,
    _SUPPORTED_RATIO_MEASURES,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    _keyed_points_from_projection,
    _normalize_multiseries_visual_scan,
    _projected_keyed_point_annotation,
    _sample_chart_font_family,
)
from .comparison_prompting import (
    _change_measure_prompt_slots,
    _change_prompt_slots,
    _comparison_phrase,
    _conditional_gap_aggregate_prompt_slots,
    _extremum_prompt_slots,
    _ordinal,
    _ranked_phrase,
    _ratio_measure_prompt_slots,
)
from .comparison_sampling import (
    _balance_answer_label_for_indexed_probe,
    _conditional_gap_internal_query_id,
    _internal_extremum_variant,
    _internal_pairwise_variant,
    _params_for_variant_family,
    _resolve_change_direction,
    _resolve_change_measure,
    _resolve_comparison,
    _resolve_condition_comparison,
    _resolve_conditional_gap_aggregate_kind,
    _resolve_extremum_direction,
    _resolve_query_id,
    _resolve_ratio_measure,
    _resolve_scene_variant,
    _support_params_for_query_axis_cycle,
    _support_params_for_query_id_cycle,
    _variant_family,
)


class _ChartsMultiseriesComparisonQueryTaskBase:
    """Answer label, count, and aggregate comparison queries over multiseries charts."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "multiseries"

    def _generate_conditional_gap(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        query_id: str,
        query_params: Dict[str, Any],
        query_id_probabilities: Mapping[str, float],
    ) -> TaskOutput:
        conditional_gap_aggregate_kind = None
        conditional_gap_aggregate_kind_probabilities: Dict[str, float] = {}
        condition_query_params = dict(query_params)
        if str(query_id) == _CONDITIONAL_AGGREGATE_QUERY_ID:
            conditional_gap_aggregate_kind, conditional_gap_aggregate_kind_probabilities = (
                _resolve_conditional_gap_aggregate_kind(
                    query_params,
                    instance_seed=int(instance_seed),
                )
            )
            condition_query_params = _support_params_for_query_axis_cycle(
                query_params,
                probabilities=conditional_gap_aggregate_kind_probabilities,
                supported_values=_SUPPORTED_CONDITIONAL_GAP_AGGREGATE_KINDS,
                explicit_key="conditional_gap_aggregate_kind",
                weights_key="conditional_gap_aggregate_kind_weights",
                balance_flag_key="balanced_conditional_gap_aggregate_kind_sampling",
            )
        condition_comparison, condition_comparison_probabilities = _resolve_condition_comparison(
            condition_query_params,
            instance_seed=int(instance_seed),
        )
        extremum_query_params = _support_params_for_query_axis_cycle(
            condition_query_params,
            probabilities=condition_comparison_probabilities,
            supported_values=_SUPPORTED_COMPARISONS,
            explicit_key="condition_comparison",
            weights_key="condition_comparison_weights",
            balance_flag_key="balanced_condition_comparison_sampling",
        )
        # Condition and extremum mirrors are prompt/query axes. Keep construction
        # support cycling at the public variant occurrence level so mirror pairs
        # do not duplicate the same numeric answer in exact 100-sample probes.
        dataset_params = dict(query_params)
        extremum_direction = None
        extremum_direction_probabilities: Dict[str, float] = {}
        if str(query_id) == _CONDITIONAL_EXTREMUM_QUERY_ID:
            extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
                extremum_query_params,
                instance_seed=int(instance_seed),
            )
        internal_query_id = _conditional_gap_internal_query_id(
            str(query_id),
            conditional_gap_aggregate_kind,
        )

        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            query_id=str(query_id),
            instance_seed=int(instance_seed),
        )
        (
            values_by_category,
            answer_value,
            annotation_labels,
            annotation_series_by_category,
            trace_extras,
        ) = build_conditional_gap_value_dataset(
            query_id=str(internal_query_id),
            condition_comparison=str(condition_comparison),
            extremum_direction=extremum_direction,
            params=dataset_params,
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
            instance_seed=int(instance_seed),
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        chart_font_family = _sample_chart_font_family(int(instance_seed), params)
        with temporary_default_font_family(str(chart_font_family)):
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
                "scene_key",
                "task_key_conditional_gap",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_conditional_gap_value",
                "object_description_grouped_bar",
                "object_description_grouped_horizontal_bar",
                "object_description_multi_line",
                "object_description_grouped_lollipop",
                "annotation_hint_conditional_gap_value",
                "json_example_conditional_gap_value",
                "json_example_answer_only_conditional_gap_value",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key_conditional_gap"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "condition_left_series": str(trace_extras["condition_left_series_label"]),
                "condition_right_series": str(trace_extras["condition_right_series_label"]),
                "target_left_series": str(trace_extras["target_left_series_label"]),
                "target_right_series": str(trace_extras["target_right_series_label"]),
                "comparison_phrase": _comparison_phrase(str(condition_comparison)),
                **_conditional_gap_aggregate_prompt_slots(conditional_gap_aggregate_kind),
                "extremum_direction": str(extremum_direction or trace_extras.get("extremum_direction", "largest")),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_conditional_gap_value"]),
                "answer_hint": str(prompt_defaults["answer_hint_conditional_gap_value"]),
                "json_example": str(prompt_defaults["json_example_conditional_gap_value"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only_conditional_gap_value"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(answer_value))
        category_label_centers = {
            str(mark["category_label"]): list(mark["category_label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        annotation_projection = projected_multiseries_mark_annotation(
            rendered_scene,
            annotation_labels,
            annotation_series_by_category,
        )
        annotation_points = _keyed_points_from_projection(annotation_projection)
        annotation_gt = TypedValue(type="keyed_point_map", value=dict(annotation_points))

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_multiseries",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "internal_query_id": str(internal_query_id),
                    "scene_variant": str(scene_variant),
                    "variant_family": "conditional_gap",
                    "annotation_labels": list(annotation_labels),
                    "annotation_series_labels_by_category": dict(annotation_series_by_category),
                    "condition_comparison": str(condition_comparison),
                    "condition_comparison_probabilities": dict(condition_comparison_probabilities),
                    **(
                        {"conditional_gap_aggregate_kind": str(conditional_gap_aggregate_kind)}
                        if conditional_gap_aggregate_kind is not None
                        else {}
                    ),
                    **(
                        {
                            "conditional_gap_aggregate_kind_probabilities": dict(
                                conditional_gap_aggregate_kind_probabilities
                            )
                        }
                        if conditional_gap_aggregate_kind_probabilities
                        else {}
                    ),
                    **(
                        {"extremum_direction": str(extremum_direction)}
                        if extremum_direction is not None
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
                    "internal_query_id": str(internal_query_id),
                    "scene_variant": str(scene_variant),
                    "variant_family": "conditional_gap",
                    "query_id_probabilities": dict(query_id_probabilities),
                    **(
                        {"conditional_gap_aggregate_kind": str(conditional_gap_aggregate_kind)}
                        if conditional_gap_aggregate_kind is not None
                        else {}
                    ),
                    **(
                        {
                            "conditional_gap_aggregate_kind_probabilities": dict(
                                conditional_gap_aggregate_kind_probabilities
                            )
                        }
                        if conditional_gap_aggregate_kind_probabilities
                        else {}
                    ),
                    "condition_comparison": str(condition_comparison),
                    "condition_comparison_probabilities": dict(condition_comparison_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "series_count": int(trace_extras["series_count"]),
                    "series_count_range": list(trace_extras["series_count_range"]),
                    "category_count": int(trace_extras["category_count"]),
                    "category_count_range": list(trace_extras["category_count_range"]),
                    "filtered_category_count": int(trace_extras["filtered_category_count"]),
                    "filtered_category_count_range": list(trace_extras["filtered_category_count_range"]),
                    "target_gap_range": list(trace_extras["target_gap_range"]),
                    "answer_range": list(trace_extras["answer_range"]),
                    **(
                        {"extremum_direction": str(extremum_direction)}
                        if extremum_direction is not None
                        else {}
                    ),
                    **(
                        {"extremum_direction_probabilities": dict(extremum_direction_probabilities)}
                        if extremum_direction_probabilities
                        else {}
                    ),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "font_assets": {
                    "asset_version": font_asset_version(),
                    "chart_font_family": str(chart_font_family),
                },
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
                    **{str(key): value for key, value in mark_style.items()},
                },
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "y_axis_max": int(rendered_scene.y_axis_max),
                "y_ticks": [int(value) for value in rendered_scene.y_ticks],
                **value_axis_render_metadata(rendered_scene),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "legend_bbox_px": list(rendered_scene.legend_bbox_px),
                "legend_item_bboxes_px": {
                    str(label): list(bbox)
                    for label, bbox in rendered_scene.legend_item_bboxes_px.items()
                },
                "context_protected_bboxes_px": {
                    "plot": list(rendered_scene.plot_bbox_px),
                    **({"legend": list(rendered_scene.legend_bbox_px)} if rendered_scene.legend_bbox_px else {}),
                },
                "category_label_centers_px": dict(category_label_centers),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "internal_query_id": str(internal_query_id),
                "scene_variant": str(scene_variant),
                "variant_family": "conditional_gap",
                "answer_value": int(answer_value),
                "annotation_labels": list(annotation_labels),
                "annotation_series_labels_by_category": dict(annotation_series_by_category),
                "category_labels": list(category_labels),
                "series_labels": list(series_labels),
                "queried_series_labels": list(trace_extras["queried_series_labels"]),
                "condition_series_labels": list(trace_extras["condition_series_labels"]),
                "target_series_labels": list(trace_extras["target_series_labels"]),
                "condition_left_series_label": str(trace_extras["condition_left_series_label"]),
                "condition_right_series_label": str(trace_extras["condition_right_series_label"]),
                "target_left_series_label": str(trace_extras["target_left_series_label"]),
                "target_right_series_label": str(trace_extras["target_right_series_label"]),
                "condition_comparison": str(condition_comparison),
                "condition_comparison_probabilities": dict(condition_comparison_probabilities),
                **(
                    {"conditional_gap_aggregate_kind": str(conditional_gap_aggregate_kind)}
                    if conditional_gap_aggregate_kind is not None
                    else {}
                ),
                **(
                    {
                        "conditional_gap_aggregate_kind_probabilities": dict(
                            conditional_gap_aggregate_kind_probabilities
                        )
                    }
                    if conditional_gap_aggregate_kind_probabilities
                    else {}
                ),
                "series_count": int(trace_extras["series_count"]),
                "series_count_range": list(trace_extras["series_count_range"]),
                "category_count": int(trace_extras["category_count"]),
                "category_count_range": list(trace_extras["category_count_range"]),
                "filtered_category_count": int(trace_extras["filtered_category_count"]),
                "filtered_category_count_range": list(trace_extras["filtered_category_count_range"]),
                "filtered_category_labels": list(trace_extras["filtered_category_labels"]),
                "filtered_gap_values": list(trace_extras["filtered_gap_values"]),
                "target_gap_by_category": dict(trace_extras["target_gap_by_category"]),
                "condition_holds_by_category": dict(trace_extras["condition_holds_by_category"]),
                "target_gap_range": list(trace_extras["target_gap_range"]),
                "answer_range": list(trace_extras["answer_range"]),
                "value_range": list(trace_extras["value_range"]),
                "values_by_category": dict(trace_extras["values_by_category"]),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "numeric_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                **(
                    {"extremum_direction": str(extremum_direction)}
                    if extremum_direction is not None
                    else {}
                ),
                **(
                    {"extremum_direction_probabilities": dict(extremum_direction_probabilities)}
                    if extremum_direction_probabilities
                    else {}
                ),
                **{str(key): value for key, value in mark_style.items() if key != "sampling_policy"},
            },
            "witness_symbolic": {
                "type": "numeric_sequence",
                "value": [int(value) for value in trace_extras["filtered_gap_values"]],
                "filtered_category_labels": list(annotation_labels),
            },
            "projected_annotation": {
                **_projected_keyed_point_annotation(annotation_projection, annotation_points),
            },
        }

        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": _normalize_multiseries_visual_scan(trace_extras),
                "reasoning_load": float(
                    _CONDITIONAL_AGGREGATE_REASONING_LOADS[str(conditional_gap_aggregate_kind)]
                    if conditional_gap_aggregate_kind is not None
                    else _REASONING_LOAD_BY_VARIANT[str(query_id)]
                ),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        query_params = _support_params_for_query_id_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
        )
        family = _variant_family(str(query_id))
        if str(family) == "conditional_gap":
            return self._generate_conditional_gap(
                int(instance_seed),
                params=params,
                query_id=str(query_id),
                query_params=query_params,
                query_id_probabilities=query_id_probabilities,
            )

        change_measure = None
        change_measure_probabilities: Dict[str, float] = {}
        ratio_measure = None
        ratio_measure_probabilities: Dict[str, float] = {}
        change_direction = None
        change_direction_probabilities: Dict[str, float] = {}
        extremum_direction = None
        extremum_direction_probabilities: Dict[str, float] = {}
        comparison = None
        comparison_probabilities: Dict[str, float] = {}
        dataset_params = dict(query_params)
        if str(family) == "delta":
            change_measure, change_measure_probabilities = _resolve_change_measure(
                query_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = _support_params_for_query_axis_cycle(
                query_params,
                probabilities=change_measure_probabilities,
                supported_values=_SUPPORTED_CHANGE_MEASURES,
                explicit_key="change_measure",
                weights_key="change_measure_weights",
                balance_flag_key="balanced_change_measure_sampling",
            )
            if str(change_measure) == "directional_change":
                change_direction, change_direction_probabilities = _resolve_change_direction(
                    dataset_params,
                    instance_seed=int(instance_seed),
                )
                dataset_params = _support_params_for_query_axis_cycle(
                    dataset_params,
                    probabilities=change_direction_probabilities,
                    supported_values=_SUPPORTED_CHANGE_DIRECTIONS,
                    explicit_key="change_direction",
                    weights_key="change_direction_weights",
                    balance_flag_key="balanced_change_direction_sampling",
                )
            else:
                extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
                    dataset_params,
                    instance_seed=int(instance_seed),
                )
                dataset_params = _support_params_for_query_axis_cycle(
                    dataset_params,
                    probabilities=extremum_direction_probabilities,
                    supported_values=_SUPPORTED_EXTREMUM_DIRECTIONS,
                    explicit_key="extremum_direction",
                    weights_key="extremum_direction_weights",
                    balance_flag_key="balanced_extremum_direction_sampling",
                )
        elif str(family) == "ratio":
            ratio_measure, ratio_measure_probabilities = _resolve_ratio_measure(
                query_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = _support_params_for_query_axis_cycle(
                query_params,
                probabilities=ratio_measure_probabilities,
                supported_values=_SUPPORTED_RATIO_MEASURES,
                explicit_key="ratio_measure",
                weights_key="ratio_measure_weights",
                balance_flag_key="balanced_ratio_measure_sampling",
            )
            extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
                dataset_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = _support_params_for_query_axis_cycle(
                dataset_params,
                probabilities=extremum_direction_probabilities,
                supported_values=_SUPPORTED_EXTREMUM_DIRECTIONS,
                explicit_key="extremum_direction",
                weights_key="extremum_direction_weights",
                balance_flag_key="balanced_extremum_direction_sampling",
            )
        elif str(family) == "category_total":
            extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
                query_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = _support_params_for_query_axis_cycle(
                query_params,
                probabilities=extremum_direction_probabilities,
                supported_values=_SUPPORTED_EXTREMUM_DIRECTIONS,
                explicit_key="extremum_direction",
                weights_key="extremum_direction_weights",
                balance_flag_key="balanced_extremum_direction_sampling",
            )
        elif str(family) == "series_rank":
            extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
                query_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = _support_params_for_query_axis_cycle(
                query_params,
                probabilities=extremum_direction_probabilities,
                supported_values=_SUPPORTED_EXTREMUM_DIRECTIONS,
                explicit_key="extremum_direction",
                weights_key="extremum_direction_weights",
                balance_flag_key="balanced_extremum_direction_sampling",
            )
        elif str(family) == "equality":
            pass
        else:
            comparison, comparison_probabilities = _resolve_comparison(
                query_params,
                instance_seed=int(instance_seed),
            )
            dataset_params = _support_params_for_query_axis_cycle(
                query_params,
                probabilities=comparison_probabilities,
                supported_values=_SUPPORTED_COMPARISONS,
                explicit_key="comparison",
                weights_key="comparison_weights",
                balance_flag_key="balanced_comparison_sampling",
            )
        extremum_variant = ""
        pairwise_variant = ""
        if str(family) in {"delta", "ratio"}:
            extremum_variant = _internal_extremum_variant(
                str(query_id),
                change_measure=change_measure,
                ratio_measure=ratio_measure,
                change_direction=change_direction,
                extremum_direction=extremum_direction,
            )
        elif str(family) == "category_total":
            extremum_variant = str(_CATEGORY_TOTAL_QUERY_ID)
        elif str(family) == "series_rank":
            extremum_variant = str(_SERIES_RANK_QUERY_ID)
        elif str(family) == "equality":
            extremum_variant = str(_EQUALITY_QUERY_ID)
        else:
            pairwise_variant = _internal_pairwise_variant(str(comparison))
        family_params = _params_for_variant_family(dataset_params, family=str(family))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            query_id=str(query_id),
            instance_seed=int(instance_seed),
        )
        if str(family) == "delta":
            values_by_category, answer_label, annotation_values, trace_extras = build_delta_extremum_label_dataset(
                query_id=str(extremum_variant),
                params=family_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )
        elif str(family) == "ratio":
            values_by_category, answer_label, annotation_values, trace_extras = build_ratio_extremum_label_dataset(
                query_id=str(extremum_variant),
                params=family_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )
        elif str(family) == "category_total":
            values_by_category, answer_label, annotation_values, trace_extras = build_category_total_extremum_label_dataset(
                query_id=str(extremum_variant),
                extremum_direction=str(extremum_direction),
                params=family_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )
        elif str(family) == "series_rank":
            values_by_category, answer_label, annotation_values, trace_extras = build_series_rank_at_category_label_dataset(
                query_id=str(extremum_variant),
                extremum_direction=str(extremum_direction),
                params=family_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )
        elif str(family) == "equality":
            values_by_category, answer_label, annotation_values, trace_extras = build_pair_equality_label_dataset(
                query_id=str(extremum_variant),
                params=family_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )
        else:
            values_by_category, answer_value, annotation_labels, trace_extras = build_pairwise_comparison_count_dataset(
                query_id=str(pairwise_variant),
                params=family_params,
                instance_seed=int(instance_seed),
                gen_defaults=_GEN_DEFAULTS,
                defaults=_DEFAULTS,
                task_id=self.task_id,
            )
            answer_label = ""
            annotation_values = []
        if str(family) in {"delta", "ratio", "category_total", "equality"}:
            values_by_category, answer_label, trace_extras = _balance_answer_label_for_indexed_probe(
                query_id=str(query_id),
                params=dataset_params,
                instance_seed=int(instance_seed),
                values_by_category=values_by_category,
                answer_label=str(answer_label),
                trace_extras=trace_extras,
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
            instance_seed=int(instance_seed),
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        chart_font_family = _sample_chart_font_family(int(instance_seed), params)
        with temporary_default_font_family(str(chart_font_family)):
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
                "scene_key",
                "task_key_pairwise",
                "task_key_delta",
                "task_key_ratio",
                "task_key_category_total",
                "task_key_equality",
                "task_key_series_rank",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_count",
                "answer_hint_label",
                "object_description_grouped_bar",
                "object_description_grouped_horizontal_bar",
                "object_description_multi_line",
                "object_description_grouped_lollipop",
                "annotation_hint_series_comparison_count",
                "annotation_hint_ranked_directional_change",
                "annotation_hint_ranked_absolute_gap",
                "annotation_hint_ranked_series_share",
                "annotation_hint_ranked_pair_ratio",
                "annotation_hint_category_total_extremum",
                "annotation_hint_pair_equality",
                "annotation_hint_series_rank_at_category",
                "json_example_series_comparison_count",
                "json_example_ranked_directional_change",
                "json_example_ranked_absolute_gap",
                "json_example_ranked_series_share",
                "json_example_ranked_pair_ratio",
                "json_example_category_total_extremum",
                "json_example_pair_equality",
                "json_example_series_rank_at_category",
                "json_example_answer_only_series_comparison_count",
                "json_example_answer_only_ranked_directional_change",
                "json_example_answer_only_ranked_absolute_gap",
                "json_example_answer_only_ranked_series_share",
                "json_example_answer_only_ranked_pair_ratio",
                "json_example_answer_only_category_total_extremum",
                "json_example_answer_only_pair_equality",
                "json_example_answer_only_series_rank_at_category",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        if str(family) == "delta":
            prompt_metric_key = "ranked_directional_change" if str(change_measure) == "directional_change" else "ranked_absolute_gap"
            task_key = str(prompt_defaults["task_key_delta"])
            answer_hint = str(prompt_defaults["answer_hint_label"])
        elif str(family) == "ratio":
            prompt_metric_key = "ranked_series_share" if str(ratio_measure) == "series_share" else "ranked_pair_ratio"
            task_key = str(prompt_defaults["task_key_ratio"])
            answer_hint = str(prompt_defaults["answer_hint_label"])
        elif str(family) == "category_total":
            prompt_metric_key = "category_total_extremum"
            task_key = str(prompt_defaults["task_key_category_total"])
            answer_hint = str(prompt_defaults["answer_hint_label"])
        elif str(family) == "series_rank":
            prompt_metric_key = "series_rank_at_category"
            task_key = str(prompt_defaults["task_key_series_rank"])
            answer_hint = str(prompt_defaults["answer_hint_label"])
        elif str(family) == "equality":
            prompt_metric_key = "pair_equality"
            task_key = str(prompt_defaults["task_key_equality"])
            answer_hint = str(prompt_defaults["answer_hint_label"])
        else:
            prompt_metric_key = "series_comparison_count"
            task_key = str(prompt_defaults["task_key_pairwise"])
            answer_hint = str(prompt_defaults["answer_hint_count"])
        annotation_hint = str(prompt_defaults[f"annotation_hint_{str(prompt_metric_key)}"])
        json_example = str(prompt_defaults[f"json_example_{str(prompt_metric_key)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(prompt_metric_key)}"])

        if str(family) == "pairwise":
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(task_key),
                query_key=str(query_id),
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(object_description),
                    "left_series": str(trace_extras["left_series_label"]),
                    "right_series": str(trace_extras["right_series_label"]),
                    "comparison_phrase": _comparison_phrase(str(comparison)),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "annotation_hint": str(annotation_hint),
                    "answer_hint": str(answer_hint),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_gt = TypedValue(type="integer", value=int(answer_value))
            category_label_centers = {
                str(mark["category_label"]): list(mark["category_label_center_px"])
                for mark in rendered_scene.mark_traces
            }
            annotation_projection = projected_multiseries_mark_annotation(
                rendered_scene,
                annotation_labels,
                trace_extras["queried_series_labels"],
            )
            annotation_points = _keyed_points_from_projection(annotation_projection)
            annotation_gt = TypedValue(type="keyed_point_map", value=dict(annotation_points))
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"chart_{str(scene_variant)}_multiseries",
                    "entities": [dict(entity) for entity in rendered_scene.entities],
                    "relations": {
                        "query_id": str(query_id),
                        "scene_variant": str(scene_variant),
                        "variant_family": str(family),
                        "internal_query_id": str(pairwise_variant),
                        "annotation_labels": list(annotation_labels),
                        "queried_series_labels": list(trace_extras["queried_series_labels"]),
                        "comparison": str(trace_extras["comparison"]),
                        "comparison_probabilities": dict(comparison_probabilities),
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
                        "variant_family": str(family),
                        "internal_query_id": str(pairwise_variant),
                        "query_id_probabilities": dict(query_id_probabilities),
                        "comparison": str(comparison),
                        "comparison_probabilities": dict(comparison_probabilities),
                        "scene_variant_probabilities": dict(scene_variant_probabilities),
                        "target_answer": int(trace_extras["target_answer"]),
                        "target_answer_range": list(trace_extras["target_answer_range"]),
                        "series_count": int(trace_extras["series_count"]),
                        "series_count_range": list(trace_extras["series_count_range"]),
                        "category_count": int(trace_extras["category_count"]),
                        "category_count_range": list(trace_extras["category_count_range"]),
                        "queried_series_labels": list(trace_extras["queried_series_labels"]),
                    },
                },
                "render_spec": {
                    "canvas_width": int(render_params.canvas_width),
                    "canvas_height": int(render_params.canvas_height),
                    "coord_space": "pixel",
                    "scene_variant": str(scene_variant),
                    "background_style": dict(background_meta),
                    "post_image_noise": dict(post_noise_meta),
                    "font_assets": {
                        "asset_version": font_asset_version(),
                        "chart_font_family": str(chart_font_family),
                    },
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
                        **{str(key): value for key, value in mark_style.items()},
                    },
                    "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                    "y_axis_max": int(rendered_scene.y_axis_max),
                    "y_ticks": [int(value) for value in rendered_scene.y_ticks],
                    **value_axis_render_metadata(rendered_scene),
                },
                "render_map": {
                    "image_id": "img0",
                    "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                    "legend_bbox_px": list(rendered_scene.legend_bbox_px),
                    "legend_item_bboxes_px": {
                        str(label): list(bbox)
                        for label, bbox in rendered_scene.legend_item_bboxes_px.items()
                    },
                    "context_protected_bboxes_px": {
                        "plot": list(rendered_scene.plot_bbox_px),
                        **({"legend": list(rendered_scene.legend_bbox_px)} if rendered_scene.legend_bbox_px else {}),
                    },
                    "category_label_centers_px": dict(category_label_centers),
                },
                "execution_trace": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "variant_family": str(family),
                    "internal_query_id": str(pairwise_variant),
                    "answer_value": int(answer_value),
                    "annotation_labels": list(annotation_labels),
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
                    "query_id_probabilities": dict(query_id_probabilities),
                    "comparison": str(comparison),
                    "comparison_probabilities": dict(comparison_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "question_format": "numeric_open",
                    "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                    **{str(key): value for key, value in mark_style.items() if key != "sampling_policy"},
                },
                "witness_symbolic": {
                    "type": "object_set",
                    "labels": list(annotation_labels),
                },
                "projected_annotation": {
                    **_projected_keyed_point_annotation(annotation_projection, annotation_points),
                },
            }
            complexity = build_chart_complexity(
                weights=_COMPLEXITY_WEIGHTS,
                components={
                    "visual_scan": _normalize_multiseries_visual_scan(trace_extras),
                    "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(query_id)]),
                    "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
                },
            )
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                answer_gt=answer_gt,
                annotation_gt=annotation_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                query_id=str(query_id),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
            )

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(task_key),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "left_series": str(trace_extras.get("left_series_label", "")),
                "right_series": str(trace_extras.get("right_series_label", "")),
                "target_series": str(trace_extras.get("target_series_label", "")),
                "target_category": str(trace_extras.get("target_category_label", "")),
                "numerator_series": str(trace_extras.get("numerator_series_label", "")),
                "denominator_series": str(trace_extras.get("denominator_series_label", "")),
                "rank": int(trace_extras["answer_rank"]),
                "rank_ordinal": _ordinal(int(trace_extras["answer_rank"])),
                "ranked_largest": _ranked_phrase(int(trace_extras["answer_rank"]), "largest"),
                "ranked_greatest": _ranked_phrase(int(trace_extras["answer_rank"]), "greatest"),
                "ranked_smallest": _ranked_phrase(int(trace_extras["answer_rank"]), "smallest"),
                **_change_prompt_slots(change_direction),
                **_change_measure_prompt_slots(change_measure, change_direction),
                **_extremum_prompt_slots(extremum_direction, answer_rank=int(trace_extras["answer_rank"])),
                **_ratio_measure_prompt_slots(
                    ratio_measure,
                    target_series=str(trace_extras.get("target_series_label", "")),
                    numerator_series=str(trace_extras.get("numerator_series_label", "")),
                    denominator_series=str(trace_extras.get("denominator_series_label", "")),
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_type = "string"
        answer_gt = TypedValue(type=answer_type, value=str(answer_label))
        category_label_centers = {
            str(mark["category_label"]): list(mark["category_label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        annotation_series_labels = (
            list(series_labels)
            if str(trace_extras.get("calculation_scope", ""))
            in {"category_total_share", "category_total", "target_category_series_rank"}
            else [str(label) for label in trace_extras["queried_series_labels"]]
        )
        annotation_category_label = (
            str(trace_extras["target_category_label"])
            if str(family) == "series_rank"
            else str(answer_label)
        )
        annotation_projection = projected_multiseries_mark_annotation(
            rendered_scene,
            [str(annotation_category_label)],
            annotation_series_labels,
        )
        annotation_points = _keyed_points_from_projection(annotation_projection)
        annotation_gt = TypedValue(type="keyed_point_map", value=dict(annotation_points))

        optional_trace_keys = (
            "left_series_label",
            "right_series_label",
            "target_series_label",
            "numerator_series_label",
            "denominator_series_label",
            "score_percent_range",
            "category_total_range",
            "category_totals_by_category",
            "answer_score_percent",
            "denominator_values_by_category",
            "ratio_percent_by_category",
            "calculation_scope",
            "answer_equal_value",
            "equality_by_category",
            "direction",
            "change_measure",
            "change_direction",
            "ratio_measure",
            "extremum_direction",
            "target_category_label",
            "target_category_index",
            "answer_series_label",
            "ranked_series_labels",
            "values_by_series_at_target_category",
        )
        optional_trace = {
            str(key): trace_extras[key]
            for key in optional_trace_keys
            if key in trace_extras and trace_extras[key] is not None
        }
        if change_direction is not None:
            optional_trace["change_direction"] = str(change_direction)
        if change_measure is not None:
            optional_trace["change_measure"] = str(change_measure)
        if ratio_measure is not None:
            optional_trace["ratio_measure"] = str(ratio_measure)
        if extremum_direction is not None:
            optional_trace["extremum_direction"] = str(extremum_direction)
        if change_measure_probabilities:
            optional_trace["change_measure_probabilities"] = dict(change_measure_probabilities)
        if ratio_measure_probabilities:
            optional_trace["ratio_measure_probabilities"] = dict(ratio_measure_probabilities)
        if change_direction_probabilities:
            optional_trace["change_direction_probabilities"] = dict(change_direction_probabilities)
        if extremum_direction_probabilities:
            optional_trace["extremum_direction_probabilities"] = dict(extremum_direction_probabilities)

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_multiseries",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "variant_family": str(family),
                    "internal_query_id": str(extremum_variant),
                    "answer_label": str(answer_label),
                    "annotation_values": [int(value) for value in annotation_values],
                    "queried_series_labels": list(trace_extras["queried_series_labels"]),
                    "derived_metric": str(trace_extras["derived_metric"]),
                    "answer_rank": int(trace_extras["answer_rank"]),
                    **dict(optional_trace),
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
                    "variant_family": str(family),
                    "internal_query_id": str(extremum_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    **(
                        {"change_direction": str(change_direction)}
                        if change_direction is not None
                        else {}
                    ),
                    **(
                        {"extremum_direction": str(extremum_direction)}
                        if extremum_direction is not None
                        else {}
                    ),
                    **(
                        {"change_direction_probabilities": dict(change_direction_probabilities)}
                        if change_direction_probabilities
                        else {}
                    ),
                    **(
                        {"extremum_direction_probabilities": dict(extremum_direction_probabilities)}
                        if extremum_direction_probabilities
                        else {}
                    ),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "series_count": int(trace_extras["series_count"]),
                    "series_count_range": list(trace_extras["series_count_range"]),
                    "category_count": int(trace_extras["category_count"]),
                    "category_count_range": list(trace_extras["category_count_range"]),
                    "queried_series_labels": list(trace_extras["queried_series_labels"]),
                    "derived_metric": str(trace_extras["derived_metric"]),
                    "answer_rank": int(trace_extras["answer_rank"]),
                    "value_range": list(trace_extras["value_range"]),
                    **dict(optional_trace),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "font_assets": {
                    "asset_version": font_asset_version(),
                    "chart_font_family": str(chart_font_family),
                },
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
                    **{str(key): value for key, value in mark_style.items()},
                },
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "y_axis_max": int(rendered_scene.y_axis_max),
                "y_ticks": [int(value) for value in rendered_scene.y_ticks],
                **value_axis_render_metadata(rendered_scene),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "legend_bbox_px": list(rendered_scene.legend_bbox_px),
                "legend_item_bboxes_px": {
                    str(label): list(bbox)
                    for label, bbox in rendered_scene.legend_item_bboxes_px.items()
                },
                "context_protected_bboxes_px": {
                    "plot": list(rendered_scene.plot_bbox_px),
                    **({"legend": list(rendered_scene.legend_bbox_px)} if rendered_scene.legend_bbox_px else {}),
                },
                "category_label_centers_px": dict(category_label_centers),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "variant_family": str(family),
                "internal_query_id": str(extremum_variant),
                "answer_label": str(answer_label),
                "answer_score": int(trace_extras["answer_score"]),
                "answer_type": str(answer_type),
                "answer_rank": int(trace_extras["answer_rank"]),
                "annotation_values": [int(value) for value in annotation_values],
                "category_labels": list(category_labels),
                "series_labels": list(series_labels),
                "queried_series_labels": list(trace_extras["queried_series_labels"]),
                "series_count": int(trace_extras["series_count"]),
                "series_count_range": list(trace_extras["series_count_range"]),
                "category_count": int(trace_extras["category_count"]),
                "category_count_range": list(trace_extras["category_count_range"]),
                "value_range": list(trace_extras["value_range"]),
                "values_by_category": dict(trace_extras["values_by_category"]),
                "derived_values_by_category": dict(trace_extras["derived_values_by_category"]),
                "derived_metric": str(trace_extras["derived_metric"]),
                "rank_order": str(trace_extras["rank_order"]),
                "ranked_category_labels": list(trace_extras["ranked_category_labels"]),
                "query_id_probabilities": dict(query_id_probabilities),
                **(
                    {"change_direction": str(change_direction)}
                    if change_direction is not None
                    else {}
                ),
                **(
                    {"extremum_direction": str(extremum_direction)}
                    if extremum_direction is not None
                    else {}
                ),
                **(
                    {"change_direction_probabilities": dict(change_direction_probabilities)}
                    if change_direction_probabilities
                    else {}
                ),
                **(
                    {"extremum_direction_probabilities": dict(extremum_direction_probabilities)}
                    if extremum_direction_probabilities
                    else {}
                ),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "label_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                **dict(optional_trace),
                **{str(key): value for key, value in mark_style.items() if key != "sampling_policy"},
            },
            "witness_symbolic": {
                "type": "numeric_sequence",
                "value": [int(value) for value in annotation_values],
                "answer_label": str(answer_label),
            },
            "projected_annotation": {
                **_projected_keyed_point_annotation(annotation_projection, annotation_points),
            },
        }

        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": _normalize_multiseries_visual_scan(trace_extras),
                "reasoning_load": (
                    0.85
                    * float(
                        _REASONING_LOAD_BY_MEASURE.get(
                            str(change_measure or ratio_measure),
                            _REASONING_LOAD_BY_VARIANT[str(query_id)],
                        )
                    )
                    + 0.15
                    * normalize_int_with_bounds(
                        int(trace_extras["answer_rank"]),
                        (int(_GEN_DEFAULTS.get("rank_min", 1)), int(_GEN_DEFAULTS.get("rank_max", 3))),
                    )
                ),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
