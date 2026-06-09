"""Base annotated-series chart task implementation."""

from __future__ import annotations

from typing import Any, Dict

from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import required_group_defaults
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import temporary_default_font_family
from ...shared.visual_style.context_layer import context_text_layer_metadata
from ..shared.chart_scene import render_labeled_chart_scene, value_axis_render_metadata
from ..shared.complexity import build_chart_complexity, clamp_unit_interval, normalize_int_with_bounds
from ..shared.labeled_chart_common import build_chart_mark_specs, resolve_chart_mark_colors, resolve_chart_render_params_for_task
from ..shared.information_style import prepare_chart_information_scene
from .event_window_common import (
    POST_IMAGE_NOISE_DEFAULTS,
    SCENE_ID,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    _COMPLEXITY_WEIGHTS,
    _DEFAULTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOADS,
    _RENDER_DEFAULTS,
    _SCENE_VARIANT_LOADS,
    _gen_int,
    _render_default_value,
)
from .event_window_context import _apply_context_margin_overrides, _draw_context_layer, _resolve_context_layout
from .event_window_rendering import _apply_annotation
from .event_window_sampling import _build_dataset

def _prompt_object_description(scene_variant: str, prompt_defaults: Mapping[str, Any]) -> str:
    key = f"object_description_{str(scene_variant)}"
    return str(prompt_defaults[key])


class ChartsAnnotatedSeriesBaseTask:
    """Shared implementation for annotated single-series chart public tasks."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "annotated_series"
    query_id = ""
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id = str(params.get("query_id", self.query_id) or self.query_id)
        if query_id not in set(SUPPORTED_QUERY_IDS):
            raise ValueError(f"unsupported annotated_series query id: {query_id}")
        if self.query_id and query_id != self.query_id:
            raise ValueError(f"{self.task_id} only supports query_id={self.query_id}")

        dataset = _build_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))
        mark_style = resolve_chart_mark_colors(
            params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
            scene_variant=str(dataset.scene_variant),
            mark_count=len(dataset.labels),
        )
        marks = build_chart_mark_specs(
            labels=dataset.labels,
            values=dataset.values,
            scene_variant=str(dataset.scene_variant),
            mark_style=mark_style,
        )
        context_layout = _resolve_context_layout(
            params=params,
            instance_seed=int(instance_seed),
            canvas_width=int(_render_default_value(params, "canvas_width", _DEFAULTS.canvas_width)),
            canvas_height=int(_render_default_value(params, "canvas_height", _DEFAULTS.canvas_height)),
        )
        render_input_params = _apply_context_margin_overrides(
            {**dict(params), **mark_style},
            context_layout=context_layout,
        )
        render_params = resolve_chart_render_params_for_task(
            render_input_params,
            render_defaults=_RENDER_DEFAULTS,
            defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        render_params, background, background_meta, information_style_meta = prepare_chart_information_scene(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            task_group=self.task_group,
            render_params=render_params,
        )
        chart_font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
        annotation_font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.annotation_font",
            params=params,
            explicit_key="annotation_font_family",
            weights_key="annotation_font_family_weights",
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered_scene = render_labeled_chart_scene(
                background,
                scene_variant=str(dataset.scene_variant),
                marks=marks,
                render_params=render_params,
                instance_seed=int(instance_seed),
            )
        with temporary_default_font_family(str(annotation_font_family)):
            annotation = _apply_annotation(
                image=rendered_scene.image,
                rendered_scene=rendered_scene,
                dataset=dataset,
                params=params,
                instance_seed=int(instance_seed),
            )
        context_elements = _draw_context_layer(
            annotation.image,
            context_layout=context_layout,
            information_style_meta=information_style_meta,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            annotation.image,
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
                "answer_hint_label",
                "answer_hint_count",
                "answer_hint_value",
                "object_description_line",
                "object_description_bar",
                "object_description_area",
                "object_description_dot_plot",
                "object_description_lollipop",
                "annotation_hint_event_window_extremum_label",
                "annotation_hint_event_window_threshold_count",
                "annotation_hint_callout_endpoint_change_value",
                "json_example_event_window_extremum_label",
                "json_example_event_window_threshold_count",
                "json_example_callout_endpoint_change_value",
                "json_example_answer_only_event_window_extremum_label",
                "json_example_answer_only_event_window_threshold_count",
                "json_example_answer_only_callout_endpoint_change_value",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_hint = (
            prompt_defaults["answer_hint_label"]
            if dataset.answer_type == "string"
            else prompt_defaults["answer_hint_count"]
            if str(dataset.query_id) == "event_window_threshold_count"
            else prompt_defaults["answer_hint_value"]
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(dataset.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": _prompt_object_description(str(dataset.scene_variant), prompt_defaults),
                "extremum_direction": str(dataset.query_params.get("extremum_direction", "")),
                "threshold_comparison_phrase": str(dataset.query_params.get("threshold_comparison_phrase", "")),
                "threshold": str(dataset.query_params.get("threshold", "")),
                "endpoint_label": str(dataset.query_params.get("endpoint_label", "")),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{dataset.query_id}"]),
                "answer_hint": str(answer_hint),
                "json_example": str(prompt_defaults[f"json_example_{dataset.query_id}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{dataset.query_id}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        label_centers = {
            str(mark["label"]): list(mark["label_center_px"])
            for mark in rendered_scene.mark_traces
        }
        values_by_label = {
            str(mark["label"]): int(mark["value"])
            for mark in rendered_scene.mark_traces
        }
        mark_bbox_by_label = {
            str(mark["label"]): list(mark["mark_bbox_px"])
            for mark in rendered_scene.mark_traces
        }
        mark_center_by_label = {
            str(mark["label"]): list(mark["mark_center_px"])
            for mark in rendered_scene.mark_traces
        }
        answer_gt = TypedValue(type=str(dataset.answer_type), value=dataset.answer_value)
        annotation_points = [list(item) for item in annotation.point_set]
        if str(dataset.query_id) == "callout_endpoint_change_value":
            keyed_points = {
                "callout_mark": list(annotation_points[0]),
                "endpoint_mark": list(annotation_points[1]),
            }
            annotation_gt = TypedValue(type="keyed_point_map", value=dict(keyed_points))
            witness_symbolic = {
                "type": "object_key_map",
                "keys": {
                    "callout_mark": str(dataset.query_params["anchor_label"]),
                    "endpoint_mark": str(dataset.query_params["endpoint_label"]),
                },
            }
            projected_annotation = {
                "type": "keyed_point_map",
                "keyed_point_map": dict(keyed_points),
                "pixel_keyed_point_map": dict(keyed_points),
            }
        else:
            annotation_gt = TypedValue(type="point_set", value=annotation_points)
            witness_symbolic = {
                "type": "point_set",
                "count": len(annotation_points),
            }
            projected_annotation = {
                "type": "point_set",
                "point_set": list(annotation_points),
                "pixel_point_set": list(annotation_points),
            }
        context_element_traces = [element.to_trace() for element in context_elements]
        context_entities = [
            {
                "entity_id": str(element["context_id"]),
                "entity_type": "non_answer_context_text",
                "attrs": dict(element),
            }
            for element in context_element_traces
        ]

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_{str(dataset.scene_variant)}_annotated_series",
                "entities": [dict(entity) for entity in rendered_scene.entities]
                + [dict(entity) for entity in annotation.entities]
                + [dict(entity) for entity in context_entities],
                "relations": {
                    "query_id": str(dataset.query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "annotation_kind": "callout" if str(dataset.query_id) == "callout_endpoint_change_value" else "event_window",
                    "annotation_labels": [str(label) for label in dataset.annotation_labels],
                    "window_labels": [str(label) for label in dataset.window_labels],
                    **dict(dataset.query_params),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(dataset.query_id),
                    "query_id_probabilities": dict(dataset.query_id_probabilities),
                    "scene_variant": str(dataset.scene_variant),
                    "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
                    "mark_count": int(len(dataset.labels)),
                    "mark_count_range": [
                        _gen_int(params, "mark_count_min", _DEFAULTS.mark_count_min),
                        _gen_int(params, "mark_count_max", _DEFAULTS.mark_count_max),
                    ],
                    **dict(dataset.query_params),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "scene_variant": str(dataset.scene_variant),
                "information_scene_style": dict(information_style_meta),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "layout_jitter": dict(render_params.layout_jitter_meta or {}),
                "context_text_layer": context_text_layer_metadata(
                    context_elements,
                    enabled=bool(context_layout.get("enabled", False)),
                    layout_mode=f"{context_layout.get('layout_mode', context_layout.get('mode', 'clean'))}:{context_layout.get('placement', 'none')}",
                    layout_spec={str(key): value for key, value in dict(context_layout).items() if str(key) != "context_params"},
                ),
                "text_style": {
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "tick_font_size_px": int(render_params.tick_font_size_px),
                    "label_stroke_width_px": int(render_params.label_stroke_width_px),
                    "font_asset_version": str(font_asset_version()),
                    "chart_font_family": str(chart_font_family),
                    "annotation_font_family": str(annotation_font_family),
                    "chart_font_exclude_tags": [],
                    "annotation_font_exclude_tags": [],
                    "context_font_exclude_tags": ["mono", "display", "script", "handwriting"],
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
                "annotation_bboxes": dict(annotation.annotation_bboxes),
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "y_axis_max": int(rendered_scene.y_axis_max),
                "y_ticks": [int(value) for value in rendered_scene.y_ticks],
                **value_axis_render_metadata(rendered_scene),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "label_centers_px": dict(label_centers),
                "mark_bbox_by_label": dict(mark_bbox_by_label),
                "mark_center_by_label": dict(mark_center_by_label),
                "annotation_bboxes": dict(annotation.annotation_bboxes),
            },
            "execution_trace": {
                "query_id": str(dataset.query_id),
                "scene_variant": str(dataset.scene_variant),
                "answer_value": dataset.answer_value,
                "annotation_labels": [str(label) for label in dataset.annotation_labels],
                "labels": [str(label) for label in dataset.labels],
                "values": [int(value) for value in dataset.values],
                "values_by_label": dict(values_by_label),
                "window_labels": [str(label) for label in dataset.window_labels],
                "mark_count": int(len(dataset.labels)),
                "mark_count_range": [
                    _gen_int(params, "mark_count_min", _DEFAULTS.mark_count_min),
                    _gen_int(params, "mark_count_max", _DEFAULTS.mark_count_max),
                ],
                "query_id_probabilities": dict(dataset.query_id_probabilities),
                "scene_variant_probabilities": dict(dataset.scene_variant_probabilities),
                "question_format": "string_open" if dataset.answer_type == "string" else "numeric_open",
                "mark_color_sampling_policy": str(mark_style["sampling_policy"]),
                "mark_fill_rgb": list(mark_style["mark_fill_rgb"]),
                "mark_outline_rgb": list(mark_style["mark_outline_rgb"]),
                **{
                    str(key): value
                    for key, value in mark_style.items()
                    if key not in {"sampling_policy", "mark_fill_rgb", "mark_outline_rgb"}
                },
                **dict(dataset.query_params),
            },
            "witness_symbolic": dict(witness_symbolic),
            "projected_annotation": dict(projected_annotation),
        }

        mark_count_bounds = [
            _gen_int(params, "mark_count_min", _DEFAULTS.mark_count_min),
            _gen_int(params, "mark_count_max", _DEFAULTS.mark_count_max),
        ]
        window_bounds = [
            _gen_int(params, "window_size_min", 3),
            _gen_int(params, "window_size_max", 6),
        ]
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(len(dataset.labels)), mark_count_bounds),
                "reasoning_load": float(_REASONING_LOADS[str(dataset.query_id)]),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(dataset.scene_variant)]),
                "annotation_scope": (
                    normalize_int_with_bounds(int(len(dataset.window_labels)), window_bounds)
                    if dataset.window_labels
                    else clamp_unit_interval(
                        abs(int(dataset.query_params.get("anchor_index", 0)) - int(dataset.query_params.get("endpoint_index", 0))) / max(1.0, float(len(dataset.labels) - 1))
                    )
                ),
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
            scene_id=SCENE_ID,
            query_id=str(dataset.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
