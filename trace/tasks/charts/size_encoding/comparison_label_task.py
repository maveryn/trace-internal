"""Task assembly for size-encoded chart comparison tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ....core.types import TypedValue
from ...base import TaskOutput
from ...shared.config_defaults import required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import temporary_default_font_family
from ..shared.complexity import build_chart_complexity, clamp_unit_interval, normalize_int_with_bounds
from ..shared.visual_defaults import chart_font_asset_metadata, sample_chart_font_family
from .comparison_label_common import (
    _COMPLEXITY_WEIGHTS,
    _GEN_DEFAULTS,
    _PROMPT_DEFAULTS,
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_VARIANT_LOADS,
    TASK_ID,
    _Dataset,
    _Rendered,
    _resolve_extremum_direction,
    _resolve_int,
    _resolve_query_id,
    _resolve_scene_variant,
)
from .comparison_label_rendering import _render_dataset
from .comparison_label_sampling import _build_dataset

def _annotation_bboxes(dataset: _Dataset, rendered: _Rendered) -> List[List[float]]:
    boxes: List[List[float]] = []
    for panel_label in dataset.query.annotation_panel_labels:
        bbox = rendered.panel_title_bboxes.get(str(panel_label))
        if bbox is not None:
            boxes.append(list(bbox))
    for category_label in dataset.query.annotation_category_labels:
        if dataset.query.query_id != "category_total_extremum_label":
            bbox = rendered.category_legend_bboxes.get(str(category_label))
            if bbox is not None:
                boxes.append(list(bbox))
    for item_id in dataset.query.annotation_item_ids:
        bbox = rendered.item_bboxes.get(str(item_id))
        if bbox is not None:
            boxes.append(list(bbox))
    return boxes

def _annotation_for_query(
    dataset: _Dataset,
    rendered: _Rendered,
) -> Tuple[str, List[List[float]] | Dict[str, List[float]], Dict[str, Any]]:
    """Return public annotation payload and projection metadata for one query."""

    bbox_set = _annotation_bboxes(dataset, rendered)
    if str(dataset.query.query_id) != "reference_size_neighbor_label":
        return (
            "bbox_set",
            [list(bbox) for bbox in bbox_set],
            {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in bbox_set],
            },
        )

    item_ids = [str(item_id) for item_id in dataset.query.annotation_item_ids]
    if len(item_ids) < 2:
        raise RuntimeError("reference_size_neighbor_label requires reference and answer annotation items")
    reference_bbox = rendered.item_bboxes.get(item_ids[0])
    answer_bbox = rendered.item_bboxes.get(item_ids[1])
    if reference_bbox is None or answer_bbox is None:
        raise RuntimeError("missing reference-neighbor annotation item bbox")
    keyed = {
        "reference_item": list(reference_bbox),
        "answer_item": list(answer_bbox),
    }
    return (
        "keyed_bbox_map",
        dict(keyed),
        {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(keyed),
            "pixel_keyed_bbox_map": dict(keyed),
            "bbox_set": list(keyed.values()),
        },
    )

class ChartsSizeEncodingComparisonLabelTask:
    """Answer comparative label queries on size-encoded charts."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "size_encoding"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            query_id=str(query_id),
            instance_seed=int(instance_seed),
        )
        extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
            params,
            instance_seed=int(instance_seed),
        )

        last_error: Exception | None = None
        dataset: _Dataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset(
                    query_id=str(query_id),
                    scene_variant=str(scene_variant),
                    extremum_direction=str(extremum_direction),
                    params=params,
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt_index),
                )
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_dataset(
                dataset,
                scene_variant=str(scene_variant),
                params=params,
                instance_seed=int(instance_seed),
            )
        annotation_type, annotation_value, projected_annotation = _annotation_for_query(dataset, rendered)
        annotation_boxes = [list(bbox) for bbox in projected_annotation.get("bbox_set", [])]
        if not annotation_boxes:
            raise RuntimeError(f"{self.task_id} produced empty annotation")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_rect_word_cloud",
                "object_description_circle_word_cloud",
                "object_description_packed_bubble_cloud",
                "object_description_small_multiple_bubble_cloud",
                "annotation_hint_filtered_item_extremum_label",
                "annotation_hint_reference_size_neighbor_label",
                "annotation_hint_category_total_extremum_label",
                "json_example_filtered_item_extremum_label",
                "json_example_reference_size_neighbor_label",
                "json_example_category_total_extremum_label",
                "json_example_answer_only_filtered_item_extremum_label",
                "json_example_answer_only_reference_size_neighbor_label",
                "json_example_answer_only_category_total_extremum_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(scene_variant)}"]),
                "category_label": str(dataset.query.category_label),
                "panel_label": str(dataset.query.panel_label),
                "reference_label": str(dataset.query.reference_label),
                "extremum_phrase": "largest" if str(extremum_direction) == "largest" else "smallest",
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(query_id)}"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults[f"json_example_{str(query_id)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        items_by_id = {str(item.item_id): item for item in dataset.items}
        values_by_label = {str(item.label): int(item.value) for item in dataset.items}
        category_by_label = {str(item.label): str(item.category) for item in dataset.items}
        panel_by_label = {str(item.label): str(item.panel) for item in dataset.items}
        annotation_labels = [str(items_by_id[item_id].label) for item_id in dataset.query.annotation_item_ids if item_id in items_by_id]
        annotation_gt = TypedValue(type=str(annotation_type), value=annotation_value)
        answer_gt = TypedValue(type="string", value=str(dataset.query.answer))

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_size_encoding_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "extremum_direction": str(extremum_direction),
                    "answer_label": str(dataset.query.answer),
                    "annotation_labels": list(annotation_labels),
                    "category_label": str(dataset.query.category_label),
                    "panel_label": str(dataset.query.panel_label),
                    "reference_label": str(dataset.query.reference_label),
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
                    "extremum_direction": str(extremum_direction),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "extremum_direction_probabilities": dict(extremum_direction_probabilities),
                    "item_count": int(len(dataset.items)),
                    "category_count": int(len(dataset.categories)),
                    "panel_count": int(len(dataset.panels)),
                    "category_label": str(dataset.query.category_label),
                    "panel_label": str(dataset.query.panel_label),
                    "reference_label": str(dataset.query.reference_label),
                    "question_format": "size_encoded_label_comparison",
                },
            },
            "render_spec": {
                "canvas_width": _resolve_int(params, "canvas_width", 1320),
                "canvas_height": _resolve_int(params, "canvas_height", 900),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                **dict(rendered.render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "item_bboxes_px": dict(rendered.item_bboxes),
                "panel_title_bboxes_px": dict(rendered.panel_title_bboxes),
                "category_legend_bboxes_px": dict(rendered.category_legend_bboxes),
            },
            "execution_trace": {
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "extremum_direction": str(extremum_direction),
                "answer_label": str(dataset.query.answer),
                "answer_value_hidden": int(values_by_label[str(dataset.query.answer)])
                if str(dataset.query.answer) in values_by_label
                else None,
                "annotation_labels": list(annotation_labels),
                "item_count": int(len(dataset.items)),
                "category_count": int(len(dataset.categories)),
                "panel_count": int(len(dataset.panels)),
                "categories": list(dataset.categories),
                "panels": list(dataset.panels),
                "values_by_label": dict(values_by_label),
                "category_by_label": dict(category_by_label),
                "panel_by_label": dict(panel_by_label),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "extremum_direction_probabilities": dict(extremum_direction_probabilities),
                "question_format": "size_encoded_label_comparison",
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "object_set",
                "labels": list(annotation_labels),
                "answer": str(dataset.query.answer),
            },
            "projected_annotation": {
                **dict(projected_annotation),
                "annotation_item_ids": list(dataset.query.annotation_item_ids),
                "annotation_panel_labels": list(dataset.query.annotation_panel_labels),
                "annotation_category_labels": list(dataset.query.annotation_category_labels),
            },
        }

        single_item_min = _resolve_int(params, "item_count_min", 18)
        panel_max = _resolve_int(params, "panel_count_max", 4)
        panel_item_max = _resolve_int(params, "panel_item_count_max", 10)
        visual_scan_max = max(int(single_item_min) + 1, int(panel_max) * int(panel_item_max))
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(len(dataset.items)), [int(single_item_min), int(visual_scan_max)]),
                "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(query_id)]),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )
        if str(query_id) == "category_total_extremum_label":
            complexity = build_chart_complexity(
                weights=_COMPLEXITY_WEIGHTS,
                components={
                    "visual_scan": normalize_int_with_bounds(int(len(dataset.items)), [int(single_item_min), int(visual_scan_max)]),
                    "reasoning_load": clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(query_id)]) + (0.04 * max(0, len(annotation_boxes) - 4))),
                    "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
                },
            )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id="size_encoding",
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
