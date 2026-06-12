"""Task assembly for single-series trend chart tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from .....core.visual.noise import apply_post_image_noise
from ....shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ....shared.text_rendering import temporary_default_font_family
from ...shared.chart_scene import render_labeled_chart_scene, value_axis_render_metadata
from ...shared.labeled_chart_common import (
    build_chart_mark_specs,
    build_trend_interval_change_dataset_for_variant,
    build_trend_structure_dataset_for_variant,
    build_trend_threshold_crossing_dataset_for_variant,
    projected_mark_annotation,
    resolve_chart_mark_colors,
    resolve_chart_render_params_for_task,
)
from ...shared.information_style import prepare_chart_information_scene
from ...shared.unanswerable import UNANSWERABLE_ANSWER, absence_proof, should_use_unanswerable_branch
from ...shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from .value_common import (
    _BRANCH_GENERATION_KEYS,
    _DEFAULTS,
    _ENDPOINT_CHANGE_REASONING_LOADS,
    _GEN_DEFAULTS,
    _INTERVAL_RATE_REASONING_LOAD,
    _PROMPT_DEFAULTS,
    _RENDER_DEFAULTS,
    _SCENE_VARIANT_LOADS,
    _STRUCTURE_REASONING_LOADS,
    _SUPPORTED_SCENE_VARIANTS,
    _SUPPORTED_THRESHOLD_SCENE_VARIANTS,
    _TASK_GROUP_DEFAULTS,
    _THRESHOLD_REASONING_LOADS,
    POST_IMAGE_NOISE_DEFAULTS,
    TASK_ID,
    _branch_generation_params,
    _build_threshold_mark_specs,
    _crossing_mode_prompt_slots,
    _crossing_prompt_slots,
    _endpoint_change_prompt_slots,
    _internal_crossing_variant,
    _internal_interval_variant,
    _internal_structure_variant,
    _resolve_crossing_direction,
    _resolve_crossing_mode,
    _resolve_endpoint_change_kind,
    _resolve_query_id,
    _resolve_scene_variant,
    _resolve_streak_direction,
    _resolve_turning_point_type,
    _streak_prompt_slots,
    _support_params_for_query_id_cycle,
    _threshold_generation_params,
    _threshold_mode_support_params,
    _threshold_support_params,
    _turning_point_prompt_slots,
)


@dataclass(frozen=True)
class TrendValueTaskComponents:
    prompt: str
    prompt_variants: Dict[str, str]
    answer_type: str
    answer_value: int | str
    annotation_type: str
    annotation_value: Any
    image: Any
    query_id: str
    trace_payload: Dict[str, Any]

def build_trend_value_task_components(
    *,
    task_id: str,
    instance_seed: int,
    params: Dict[str, Any],
    selected_query_id: str,
    query_id_probabilities: Mapping[str, float],
    supports_unanswerable: bool = False,
) -> TrendValueTaskComponents:
        shared_gen_defaults, _, _ = split_scene_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        )
        task_gen_defaults, _, _ = split_scene_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
            task_id=str(task_id),
        )
        task_override_params = {
            str(key): value
            for key, value in task_gen_defaults.items()
            if shared_gen_defaults.get(str(key)) != value
        }
        effective_params = dict(task_override_params)
        effective_params.update(dict(params))
        if "query_id_weights" in task_override_params:
            raw_weights = params.get("query_id_weights")
            override_weights = task_override_params["query_id_weights"]
            override_keys = set(str(key) for key in override_weights) if isinstance(override_weights, Mapping) else set()
            raw_keys = set(str(key) for key in raw_weights) if isinstance(raw_weights, Mapping) else set()
            raw_is_uniform_allowed = (
                isinstance(raw_weights, Mapping)
                and raw_keys == override_keys
                and all(float(value) == 1.0 for value in raw_weights.values())
            )
            if raw_is_uniform_allowed:
                effective_params["query_id_weights"] = task_override_params["query_id_weights"]
        params = {
            **effective_params,
            "_enable_unanswerable": bool(supports_unanswerable),
        }
        query_id = str(selected_query_id)
        query_id_probabilities = dict(query_id_probabilities)
        support_params = _support_params_for_query_id_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
        )
        turning_point_type = None
        turning_point_type_probabilities: Dict[str, float] = {}
        streak_direction = None
        streak_direction_probabilities: Dict[str, float] = {}
        endpoint_change_kind = None
        endpoint_change_kind_probabilities: Dict[str, float] = {}
        crossing_mode = None
        crossing_mode_probabilities: Dict[str, float] = {}
        crossing_direction = None
        crossing_direction_probabilities: Dict[str, float] = {}
        threshold_reference: Dict[str, Any] = {}

        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            support_params,
            query_id=str(query_id),
            instance_seed=int(instance_seed),
        )

        labels = [str(label) for label in trace_extras["labels"]]
        projected_labels = [str(label) for label in trace_extras.get("projected_labels", [])]
        mark_style = resolve_chart_mark_colors(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
            scene_variant=str(scene_variant),
            mark_count=len(labels),
        )
        if str(query_id) == "threshold_crossing":
            marks = _build_threshold_mark_specs(
                labels=tuple(labels),
                values=tuple(int(value) for value in values),
                scene_variant=str(scene_variant),
                mark_style=mark_style,
                future_labels=tuple(projected_labels),
            )
        else:
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
            render_params=render_params,
        )
        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.chart_font",
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
                "task_key",
                "threshold_task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "answer_hint_crossing_label",
                "object_description_area",
                "object_description_bar",
                "object_description_horizontal_bar",
                "object_description_line",
                "object_description_dot_plot",
                "object_description_lollipop",
                "annotation_hint_turning_point_count",
                "annotation_hint_longest_monotone_streak",
                "annotation_hint_endpoint_change_value",
                "annotation_hint_interval_rate_value",
                "annotation_hint_first_crosses_above_threshold",
                "annotation_hint_first_crosses_below_threshold",
                "annotation_hint_linear_projection_crosses_above",
                "annotation_hint_linear_projection_crosses_below",
                "json_example_turning_point_count",
                "json_example_longest_monotone_streak",
                "json_example_endpoint_change_value",
                "json_example_interval_rate_value",
                "json_example_first_crosses_above_threshold",
                "json_example_first_crosses_below_threshold",
                "json_example_linear_projection_crosses_above",
                "json_example_linear_projection_crosses_below",
                "json_example_answer_only_turning_point_count",
                "json_example_answer_only_longest_monotone_streak",
                "json_example_answer_only_endpoint_change_value",
                "json_example_answer_only_interval_rate_value",
                "json_example_answer_only_first_crosses_above_threshold",
                "json_example_answer_only_first_crosses_below_threshold",
                "json_example_answer_only_linear_projection_crosses_above",
                "json_example_answer_only_linear_projection_crosses_below",
                "unanswerable_instruction",
            ),
            context=f"prompt defaults for {task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        prompt_task_key = (
            str(prompt_defaults["threshold_task_key"])
            if str(query_id) == "threshold_crossing"
            else str(prompt_defaults["task_key"])
        )
        prompt_answer_hint = (
            str(prompt_defaults["answer_hint_crossing_label"])
            if str(query_id) == "threshold_crossing"
            else str(prompt_defaults["answer_hint"])
        )
        prompt_annotation_key = str(internal_query_id) if str(query_id) == "threshold_crossing" else str(query_id)
        annotation_hint = str(prompt_defaults[f"annotation_hint_{str(prompt_annotation_key)}"])
        json_example = str(prompt_defaults[f"json_example_{str(prompt_annotation_key)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(prompt_annotation_key)}"])
        turning_point_slots = _turning_point_prompt_slots(turning_point_type)
        streak_slots = _streak_prompt_slots(streak_direction)
        endpoint_change_slots = _endpoint_change_prompt_slots(endpoint_change_kind)
        crossing_slots = _crossing_prompt_slots(crossing_direction)
        crossing_mode_slots = _crossing_mode_prompt_slots(crossing_mode)

        prompt_selection = render_scene_prompt_variants(
            domain="charts",
            scene_id="single_series",
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_task_key),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "object_description": str(object_description),
                "start_label": str(trace_extras.get("start_label", "")),
                "end_label": str(trace_extras.get("end_label", "")),
                "threshold": str(trace_extras.get("threshold", "")),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "unanswerable_instruction": (
                    str(prompt_defaults["unanswerable_instruction"])
                    if bool(supports_unanswerable)
                    else ""
                ),
                **dict(turning_point_slots),
                **dict(streak_slots),
                **dict(endpoint_change_slots),
                **dict(crossing_slots),
                **dict(crossing_mode_slots),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        if str(answer_type) == "integer":
            answer_output_type = "integer"
            answer_output_value: int | str = int(answer_value)
            answer_value_for_trace: int | str = int(answer_value)
            question_format = "numeric_open"
        else:
            answer_output_type = "string" if str(answer_type) == "string" else "option_letter"
            answer_output_value = str(answer_value)
            answer_value_for_trace = str(answer_value)
            question_format = "label_open"
        label_centers = {
            str(mark["label"]): list(mark["label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        values_by_label = {
            str(mark["label"]): int(mark["value"])
            for mark in rendered_scene.mark_traces
        }
        annotation_projection = projected_mark_annotation(rendered_scene, ordered_annotation_labels)
        annotation_points = [list(point) for point in annotation_projection["pixel_point_set"]]
        keyed_annotation_points: Dict[str, list[float]] = {}
        if str(annotation_kind) == "keyed_point_map":
            point_map = {
                str(label): list(point)
                for label, point in annotation_projection.get("pixel_point_map", {}).items()
            }
            keyed_annotation_points = {
                "start_mark": list(point_map[str(trace_extras["start_label"])]),
                "end_mark": list(point_map[str(trace_extras["end_label"])]),
            }
            annotation_output_type = "keyed_point_map"
            annotation_output_value: Any = dict(keyed_annotation_points)
        else:
            annotation_output_type = str(annotation_kind)
            annotation_output_value = list(annotation_points)

        optional_structure_params = {
            **(
                {"turning_point_type": str(turning_point_type)}
                if turning_point_type is not None
                else {}
            ),
            **(
                {"streak_direction": str(streak_direction)}
                if streak_direction is not None
                else {}
            ),
            **(
                {"turning_point_type_probabilities": dict(turning_point_type_probabilities)}
                if turning_point_type_probabilities
                else {}
            ),
            **(
                {"streak_direction_probabilities": dict(streak_direction_probabilities)}
                if streak_direction_probabilities
                else {}
            ),
        }
        optional_interval_params = {
            **(
                {"endpoint_change_kind": str(endpoint_change_kind)}
                if endpoint_change_kind is not None
                else {}
            ),
            **(
                {"endpoint_change_kind_probabilities": dict(endpoint_change_kind_probabilities)}
                if endpoint_change_kind_probabilities
                else {}
            ),
            **(
                {
                    "start_label": str(trace_extras["start_label"]),
                    "end_label": str(trace_extras["end_label"]),
                    "interval_gap": int(trace_extras["interval_gap"]),
                }
                if "start_label" in trace_extras
                else {}
            ),
        }
        optional_crossing_params = {
            **(
                {"crossing_mode": str(crossing_mode)}
                if crossing_mode is not None
                else {}
            ),
            **(
                {"crossing_mode_probabilities": dict(crossing_mode_probabilities)}
                if crossing_mode_probabilities
                else {}
            ),
            **(
                {"crossing_direction": str(crossing_direction)}
                if crossing_direction is not None
                else {}
            ),
            **(
                {"crossing_direction_probabilities": dict(crossing_direction_probabilities)}
                if crossing_direction_probabilities
                else {}
            ),
            **(
                {
                    "answer_label": str(answer_value),
                    "answer_index": int(trace_extras.get("answer_index", -1)),
                    "threshold": int(trace_extras["threshold"]),
                    "comparison": str(trace_extras["comparison"]),
                    "answerability": str(trace_extras.get("answerability", "answerable")),
                    **(
                        {"absence_proof": dict(trace_extras["absence_proof"])}
                        if str(trace_extras.get("answerability")) == "unanswerable"
                        else {}
                    ),
                }
                if str(query_id) == "threshold_crossing"
                else {}
            ),
        }
        target_answer_params = (
            {}
            if str(answer_type) in {"option_letter", "string"}
            else {
                "target_answer": int(trace_extras.get("target_answer", answer_value)),
                **(
                    {"target_answer_range": list(trace_extras["target_answer_range"])}
                    if "target_answer_range" in trace_extras
                    else {}
                ),
            }
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_trend_value",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "internal_query_id": str(internal_query_id),
                    "scene_variant": str(scene_variant),
                    "annotation_labels": list(annotation_labels),
                    "ordered_annotation_labels": list(ordered_annotation_labels),
                    **dict(optional_structure_params),
                    **dict(optional_interval_params),
                    **dict(optional_crossing_params),
                    **{
                        str(key): value
                        for key, value in trace_extras.items()
                        if key
                        in {
                            "annotation_point_indices",
                            "step_signs",
                            "step_directions",
                            "turning_kind",
                            "streak_direction",
                            "start_label",
                            "end_label",
                            "start_value",
                            "end_value",
                            "delta",
                            "interval_gap",
                            "observed_labels",
                            "projected_labels",
                            "crossing_index",
                            "crossing_label",
                            "pre_crossing_label",
                        }
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
                    "internal_query_id": str(internal_query_id),
                    "scene_variant": str(scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "mark_count": int(trace_extras["mark_count"]),
                    **dict(optional_structure_params),
                    **dict(optional_interval_params),
                    **dict(optional_crossing_params),
                    **dict(target_answer_params),
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
                **(
                    {"threshold_reference": dict(threshold_reference)}
                    if threshold_reference
                    else {}
                ),
                **value_axis_render_metadata(rendered_scene),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "label_centers_px": dict(label_centers),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "internal_query_id": str(internal_query_id),
                "scene_variant": str(scene_variant),
                "answer_value": answer_value_for_trace,
                "annotation_labels": list(annotation_labels),
                "ordered_annotation_labels": list(ordered_annotation_labels),
                "labels": [str(label) for label in labels],
                "values": [int(value) for value in values],
                "values_by_label": dict(values_by_label),
                "mark_count": int(trace_extras["mark_count"]),
                "mark_count_range": list(trace_extras["mark_count_range"]),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": str(question_format),
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                **dict(optional_structure_params),
                **dict(optional_interval_params),
                **dict(optional_crossing_params),
                **dict(target_answer_params),
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
                        "annotation_labels",
                        "ordered_annotation_labels",
                    }
                },
            },
            "witness_symbolic": {
                "type": "object_set",
                "labels": list(annotation_labels),
                "ordered_labels": list(ordered_annotation_labels),
                "answerability": str(trace_extras.get("answerability", "answerable")),
                **(
                    {"absence_proof": dict(trace_extras["absence_proof"])}
                    if str(trace_extras.get("answerability")) == "unanswerable"
                    else {}
                ),
            },
            "projected_annotation": (
                {
                    "type": "keyed_point_map",
                    "keyed_point_map": dict(keyed_annotation_points),
                    "pixel_keyed_point_map": dict(keyed_annotation_points),
                    "point_set": list(keyed_annotation_points.values()),
                    **dict(annotation_projection),
                }
                if str(annotation_kind) == "keyed_point_map"
                else {
                    "type": "point_set",
                    "point_set": list(annotation_points),
                    **dict(annotation_projection),
                }
            ),
        }


        return TrendValueTaskComponents(
            prompt=str(prompt_artifacts.prompt),
            answer_type=str(answer_output_type),
            answer_value=answer_output_value,
            annotation_type=str(annotation_output_type),
            annotation_value=annotation_output_value,
            image=image,
            trace_payload=trace_payload,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
