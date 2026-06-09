"""Task-output assembly for part-whole composition chart tasks."""

from __future__ import annotations

from typing import Any, Dict

from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import group_default, required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.complexity import build_chart_complexity, normalize_int_with_bounds
from .share_arithmetic_common import (
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
    TASK_ID,
    _COMPLEXITY_WEIGHTS,
    _DEFAULTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _RENDER_DEFAULTS,
    _SCENE_VARIANT_LOADS,
    _chart_order_phrase,
    _format_quoted,
    _params_for_scene_axis,
    _public_task_param_overrides,
    _resolve_query_id,
    _resolve_scene_variant,
    _scene_variants_for_task,
)
from .share_arithmetic_dataset import _build_dataset, _annotation_value_for_label, _public_annotation_key
from .share_arithmetic_rendering import _render_share_chart

class ChartsCompositionShareArithmeticValueTask:
    """Return an integer share-arithmetic value from one composition chart."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "composition"

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
        scene_params = _params_for_scene_axis(params)
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            scene_params,
            instance_seed=int(instance_seed),
            supported_variants=_scene_variants_for_task(str(query_id)),
        )
        dataset = _build_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))

        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
        background, background_meta = make_background_canvas(
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = _render_share_chart(
            base_image=background,
            dataset=dataset,
            scene_variant=str(scene_variant),
            params=params,
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
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_pie",
                "object_description_donut",
                "object_description_stacked_bar",
                "object_description_stacked_horizontal_bar",
                "annotation_hint_contiguous_chart_order_sum",
                "annotation_hint_positional_segment_share_sum",
                "annotation_hint_chart_order_share_to_count",
                "annotation_hint_chart_order_remaining_count",
                "annotation_hint_subset_denominator_share_value",
                "annotation_hint_sector_share_to_angle",
                "annotation_hint_chart_order_adjacent_transfer_gap",
                "json_example_contiguous_chart_order_sum",
                "json_example_positional_segment_share_sum",
                "json_example_chart_order_share_to_count",
                "json_example_chart_order_remaining_count",
                "json_example_subset_denominator_share_value",
                "json_example_sector_share_to_angle",
                "json_example_chart_order_adjacent_transfer_gap",
                "json_example_answer_only_contiguous_chart_order_sum",
                "json_example_answer_only_positional_segment_share_sum",
                "json_example_answer_only_chart_order_share_to_count",
                "json_example_answer_only_chart_order_remaining_count",
                "json_example_answer_only_subset_denominator_share_value",
                "json_example_answer_only_sector_share_to_angle",
                "json_example_answer_only_chart_order_adjacent_transfer_gap",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        extras = dict(dataset.trace_extras)
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        annotation_hint = str(prompt_defaults[f"annotation_hint_{str(query_id)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_id)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "category_list": _format_quoted([str(label) for label in extras.get("category_list", [])]),
                "rank_position_list_text": str(extras.get("rank_position_list_text", "")),
                "lower_reference_category": str(extras.get("lower_reference_category", "")),
                "upper_reference_category": str(extras.get("upper_reference_category", "")),
                "start_category": str(extras.get("start_category", "")),
                "end_category": str(extras.get("end_category", "")),
                "subset_category_list_text": str(extras.get("subset_category_list_text", "")),
                "source_category": str(extras.get("source_category", "")),
                "target_category": str(extras.get("target_category", "")),
                "transfer_delta": str(extras.get("transfer_delta", "")),
                "source_rank_text": str(extras.get("source_rank_text", "")),
                "target_rank_text": str(extras.get("target_rank_text", "")),
                "source_threshold": str(extras.get("source_threshold", "")),
                "target_threshold": str(extras.get("target_threshold", "")),
                "source_order_direction": str(extras.get("source_order_direction", "")),
                "target_order_direction": str(extras.get("target_order_direction", "")),
                "source_extremum_text": str(extras.get("source_extremum_text", "")),
                "target_extremum_text": str(extras.get("target_extremum_text", "")),
                "positional_instruction": str(extras.get("positional_instruction", "")),
                "group_size": str(extras.get("group_size", "")),
                "known_count_category": str(extras.get("known_count_category", "")),
                "threshold_value": str(extras.get("threshold_value", "")),
                "comparison_start_category": str(extras.get("comparison_start_category", "")),
                "chart_order_phrase": str(extras.get("chart_order_direction", _chart_order_phrase(str(scene_variant)))),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        values_by_label = {str(category.label): int(category.value) for category in dataset.categories}
        annotation_values = [
            _annotation_value_for_label(str(label), extras=extras, values_by_label=values_by_label)
            for label in dataset.annotation_labels
        ]
        annotation_bboxes = [
            list(rendered_scene.annotation_bbox_by_label[str(label)])
            for label in dataset.annotation_labels
            if str(label) in rendered_scene.annotation_bbox_by_label
        ]
        annotation_points = [
            list(rendered_scene.annotation_point_by_label[str(label)])
            for label in dataset.annotation_labels
            if str(label) in rendered_scene.annotation_point_by_label
        ]
        annotation_keyed_points = {
            _public_annotation_key(str(label)): list(rendered_scene.annotation_point_by_label[str(label)])
            for label in dataset.annotation_labels
            if str(label) in rendered_scene.annotation_point_by_label
        }
        annotation_keys = [_public_annotation_key(str(label)) for label in dataset.annotation_labels]
        answer_gt = TypedValue(type="integer", value=int(dataset.answer_value))
        annotation_gt = TypedValue(type="keyed_point_map", value=dict(annotation_keyed_points))
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "scene_kind": f"chart_{str(scene_variant)}_composition_share_arithmetic",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "category_labels": [str(category.label) for category in dataset.categories],
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
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "category_count": int(extras["category_count"]),
                    "annotation_labels": [str(label) for label in dataset.annotation_labels],
                    "annotation_keys": [str(key) for key in annotation_keys],
                },
            },
            "render_spec": {
                "canvas_width": int(canvas_width),
                "canvas_height": int(canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "layout_jitter": dict(rendered_scene.layout_jitter_meta),
                "table_position": str(rendered_scene.layout_jitter_meta.get("table_position", "right")),
                "table_columns": int(rendered_scene.layout_jitter_meta.get("table_columns", 1)),
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "table_bbox_px": list(rendered_scene.table_bbox_px),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered_scene.plot_bbox_px),
                "table_bbox_px": list(rendered_scene.table_bbox_px),
                "chart_traces": [dict(trace) for trace in rendered_scene.chart_traces],
                "category_traces": [dict(trace) for trace in rendered_scene.category_traces],
                "annotation_bbox_by_label": {
                    str(label): list(bbox)
                    for label, bbox in rendered_scene.annotation_bbox_by_label.items()
                },
                "annotation_point_by_label": {
                    str(label): list(point)
                    for label, point in rendered_scene.annotation_point_by_label.items()
                },
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "answer_value": int(dataset.answer_value),
                "category_count": int(extras["category_count"]),
                "category_count_range": list(extras["category_count_range"]),
                "category_values": {str(label): int(value) for label, value in values_by_label.items()},
                "categories": [
                    {
                        "label": str(category.label),
                        "value": int(category.value),
                        "fill_rgb": [int(channel) for channel in category.color_rgb],
                    }
                    for category in dataset.categories
                ],
                "annotation_labels": [str(label) for label in dataset.annotation_labels],
                "annotation_keys": [str(key) for key in annotation_keys],
                "annotation_values": [int(value) for value in annotation_values],
                "question_format": "numeric_open",
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                **dict(extras),
            },
            "witness_symbolic": {
                "type": "composition_share_arithmetic",
                "query_id": str(query_id),
                "answer_value": int(dataset.answer_value),
                "annotation_values": [int(value) for value in annotation_values],
                "calculation": dict(extras),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_keyed_points),
                "pixel_keyed_point_map": dict(annotation_keyed_points),
                "point_set": list(annotation_points),
                "pixel_point_set": list(annotation_points),
                "bbox_set": list(annotation_bboxes),
                "annotation_labels": [str(label) for label in dataset.annotation_labels],
                "annotation_keys": [str(key) for key in annotation_keys],
            },
        }
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(extras["category_count"]), extras["category_count_range"]),
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
