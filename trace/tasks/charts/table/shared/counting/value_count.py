"""Table counting task that counts rows matching one supported table predicate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import required_group_defaults, split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.text_rendering import temporary_default_font_family
from trace.tasks.charts.table.shared.table_common import (
    SUPPORTED_TABLE_SCENE_VARIANTS,
    TableDefaults,
    build_counting_value_dataset_for_variant,
    projected_table_bbox_annotation,
    resolve_table_axis_variant,
    resolve_table_render_params,
    table_render_style_spec,
    table_value_cell_id,
)
from trace.tasks.charts.table.shared.table_scene import render_table_scene
from trace.tasks.charts.table.shared.visual_defaults import (
    load_table_background_defaults,
    load_table_noise_defaults,
    sample_table_font_family,
    table_font_asset_metadata,
)


TASK_ID = "charts_table_value_predicate_count_base"
_SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "threshold_count",
    "in_interval",
    "categorical_value_count",
)
_SOURCE_THRESHOLD_VARIANTS: Tuple[str, ...] = ("above_threshold", "below_threshold")
_SUPPORTED_COMPARISONS: Tuple[str, ...] = ("greater_than", "less_than")

_DEFAULTS = TableDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("charts", "table")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_table_background_defaults(scene_id="table")
POST_IMAGE_NOISE_DEFAULTS = load_table_noise_defaults(scene_id="table", apply_prob=0.0)


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic table-counting variant."""

    explicit_variant = params.get("query_id")
    if explicit_variant is not None and str(explicit_variant).strip().lower() in set(_SOURCE_THRESHOLD_VARIANTS):
        return "threshold_count", {
            str(value): (1.0 if str(value) == "threshold_count" else 0.0)
            for value in _SUPPORTED_QUERY_IDS
        }
    return resolve_table_axis_variant(
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


def _resolve_comparison(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str | None, Dict[str, float]]:
    """Resolve threshold comparator for the merged threshold-count variant."""

    explicit_variant = params.get("query_id")
    source_comparison = None
    if explicit_variant is not None:
        normalized_variant = str(explicit_variant).strip().lower()
        if normalized_variant == "above_threshold":
            source_comparison = "greater_than"
        elif normalized_variant == "below_threshold":
            source_comparison = "less_than"
    explicit_comparison = params.get("comparison")
    if explicit_comparison is not None:
        comparison = str(explicit_comparison).strip().lower()
        if comparison not in set(_SUPPORTED_COMPARISONS):
            raise ValueError(f"unsupported table counting comparison: {explicit_comparison}")
        if source_comparison is not None and str(source_comparison) != str(comparison):
            raise ValueError("query_id threshold alias conflicts with explicit comparison")
        return str(comparison), {
            str(value): (1.0 if str(value) == str(comparison) else 0.0)
            for value in _SUPPORTED_COMPARISONS
        }
    if source_comparison is not None:
        return str(source_comparison), {
            str(value): (1.0 if str(value) == str(source_comparison) else 0.0)
            for value in _SUPPORTED_COMPARISONS
        }
    comparison, probabilities = resolve_table_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_COMPARISONS,
        task_id=TASK_ID,
        explicit_key="comparison",
        weights_key="comparison_weights",
        balance_flag_key="balanced_comparison_sampling",
        axis_namespace="comparison",
    )
    return str(comparison), dict(probabilities)


def _internal_threshold_variant(comparison: str) -> str:
    """Map public comparator to the construction variant."""

    if str(comparison) == "greater_than":
        return "above_threshold"
    if str(comparison) == "less_than":
        return "below_threshold"
    raise ValueError(f"unsupported table counting comparison: {comparison}")


def _comparison_phrase(comparison: str | None) -> str:
    """Return prompt wording for the threshold comparator."""

    if str(comparison) == "greater_than":
        return "greater than"
    if str(comparison) == "less_than":
        return "less than"
    return ""


def _trace_cell_value(value: Any) -> Any:
    """Return a JSON-safe value while preserving numeric cells as integers."""

    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return int(value)
    return str(value)


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the visual table scene variant."""

    return resolve_table_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_TABLE_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )

@dataclass(frozen=True)
class TableCountingTaskComponents:
    prompt: str
    prompt_variants: Dict[str, str]
    answer_type: str
    answer_value: Any
    annotation_type: str
    annotation_value: Any
    image: Any
    query_id: str
    trace_payload: Dict[str, Any]

def build_table_counting_task_components(
    *,
    task_id: str,
    scene_id: str,
    prompt_domain: str,
    selected_query_id: str,
    query_id_probabilities: Mapping[str, float],
    instance_seed: int,
    params: Mapping[str, Any],
) -> TableCountingTaskComponents:
    params = dict(params)
    query_id = str(selected_query_id)
    comparison = None
    comparison_probabilities: Dict[str, float] = {}
    if str(query_id) == "threshold_count":
        comparison, comparison_probabilities = _resolve_comparison(params, instance_seed=int(instance_seed))
    internal_query_id = (
        _internal_threshold_variant(str(comparison))
        if str(query_id) == "threshold_count"
        else str(query_id)
    )
    scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
    dataset = build_counting_value_dataset_for_variant(
        query_id=str(internal_query_id),
        params=params,
        instance_seed=int(instance_seed),
        gen_defaults=_GEN_DEFAULTS,
        defaults=_DEFAULTS,
        task_id=task_id,
    )

    render_params = resolve_table_render_params(
        params,
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
    table_font_family = sample_table_font_family(
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.table_font",
        params=params,
    )
    with temporary_default_font_family(str(table_font_family)):
        rendered_scene = render_table_scene(
            background,
            scene_variant=str(scene_variant),
            row_labels=list(dataset["row_labels"]),
            column_headers=list(dataset["column_headers"]),
            values_by_row=dict(dataset["values_by_row"]),
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
            "object_description_spreadsheet",
            "object_description_zebra",
            "object_description_ledger",
            "object_description_card_table",
            "annotation_hint_threshold_count",
            "annotation_hint_in_interval",
            "annotation_hint_categorical_value_count",
            "json_example_threshold_count",
            "json_example_in_interval",
            "json_example_categorical_value_count",
            "json_example_answer_only_threshold_count",
            "json_example_answer_only_in_interval",
            "json_example_answer_only_categorical_value_count",
        ),
        context=f"prompt defaults for {task_id}",
    )
    object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
    annotation_hint = str(prompt_defaults[f"annotation_hint_{str(query_id)}"])
    json_example = str(prompt_defaults[f"json_example_{str(query_id)}"])
    json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_id)}"])
    variant_slots = {"query_column": str(dataset["query_column"])}
    if str(query_id) == "threshold_count":
        variant_slots["threshold_value"] = str(int(dataset["threshold_value"]))
        variant_slots["comparison_phrase"] = _comparison_phrase(comparison)
    elif str(query_id) == "in_interval":
        variant_slots["interval_min"] = str(int(dataset["interval_min"]))
        variant_slots["interval_max"] = str(int(dataset["interval_max"]))
    else:
        variant_slots["target_category"] = str(dataset["target_category"])

    prompt_selection = render_scene_prompt_variants(
        domain=str(prompt_domain),
        scene_id=scene_id,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "object_description": str(object_description),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(annotation_hint),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            **variant_slots,
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    supporting_cell_ids = [
        table_value_cell_id(
            data_row_index=int(row_index),
            numeric_column_index=int(dataset["query_column_index"]),
        )
        for row_index in dataset["matching_row_indices"]
    ]
    annotation_projection = projected_table_bbox_annotation(rendered_scene, supporting_cell_ids)
    annotation_bboxes = [
        [round(float(value), 3) for value in bbox]
        for bbox in annotation_projection["bbox_set"]
    ]
    answer_value = int(dataset["answer_value"])
    answer_type = "integer"
    answer_gt_value = int(answer_value)
    annotation_type = "bbox_set"
    annotation_value = list(annotation_bboxes)

    values_by_row = {
        str(row_label): {
            str(header): _trace_cell_value(value)
            for header, value in row_values.items()
        }
        for row_label, row_values in dataset["values_by_row"].items()
    }
    variant_relation_fields: Dict[str, Any]
    if str(query_id) == "threshold_count":
        variant_relation_fields = {
            "threshold_value": int(dataset["threshold_value"]),
            "comparison": str(comparison),
        }
    elif str(query_id) == "in_interval":
        variant_relation_fields = {
            "interval_min": int(dataset["interval_min"]),
            "interval_max": int(dataset["interval_max"]),
        }
    else:
        variant_relation_fields = {
            "category_column": str(dataset["category_column"]),
            "target_category": str(dataset["target_category"]),
        }
    cell_bbox_map = {
        str(cell_trace["cell_id"]): list(cell_trace["bbox_px"])
        for cell_trace in rendered_scene.cell_traces
    }
    trace_payload = {
        "scene_ir": {
            "scene_kind": f"table_{str(scene_variant)}_counting",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "query_id": str(query_id),
                "internal_query_id": str(internal_query_id),
                "scene_variant": str(scene_variant),
                "answer_value": int(answer_value),
                "supporting_cell_ids": [str(cell_id) for cell_id in supporting_cell_ids],
                "query_column": str(dataset["query_column"]),
                **dict(variant_relation_fields),
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
                "query_column": str(dataset["query_column"]),
                "query_id_probabilities": dict(query_id_probabilities),
                **(
                    {"comparison": str(comparison), "comparison_probabilities": dict(comparison_probabilities)}
                    if str(query_id) == "threshold_count"
                    else {}
                ),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "row_count": int(dataset["row_count"]),
                "numeric_column_count": int(dataset["numeric_column_count"]),
                "column_count": int(dataset.get("column_count", len(dataset["column_headers"]))),
                **dict(variant_relation_fields),
            },
        },
        "render_spec": {
            "canvas_width": int(render_params.canvas_width),
            "canvas_height": int(render_params.canvas_height),
            "coord_space": "pixel",
            "scene_variant": str(scene_variant),
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "font_assets": table_font_asset_metadata(str(table_font_family)),
            "table_bbox_px": list(rendered_scene.table_bbox_px),
            "table_style": table_render_style_spec(render_params),
            "text_style": {
                "label_font_size_px": int(render_params.label_font_size_px),
                "value_font_size_px": int(render_params.value_font_size_px),
            },
            "grid_style": {
                "border_width_px": int(render_params.border_width_px),
                "grid_width_px": int(render_params.grid_width_px),
            },
        },
        "render_map": {
            "image_id": "img0",
            "table_bbox_px": list(rendered_scene.table_bbox_px),
            "row_region_bboxes_px": dict(rendered_scene.row_region_bboxes),
            "column_region_bboxes_px": dict(rendered_scene.column_region_bboxes),
            "row_label_bboxes_px": dict(rendered_scene.row_label_bboxes),
            "header_bboxes_px": dict(rendered_scene.header_bboxes),
            "cell_bboxes_px": dict(cell_bbox_map),
        },
        "execution_trace": {
            "query_id": str(query_id),
            "internal_query_id": str(internal_query_id),
            "scene_variant": str(scene_variant),
            "answer_value": int(answer_value),
            "row_labels": [str(label) for label in dataset["row_labels"]],
            "column_headers": [str(header) for header in dataset["column_headers"]],
            "values_by_row": dict(values_by_row),
            "row_count": int(dataset["row_count"]),
            "numeric_column_count": int(dataset["numeric_column_count"]),
            "column_count": int(dataset.get("column_count", len(dataset["column_headers"]))),
            "row_count_range": list(dataset["row_count_range"]),
            "numeric_column_count_range": list(dataset["numeric_column_count_range"]),
            "value_range": list(dataset["value_range"]),
            "matching_row_indices": [int(row_index) for row_index in dataset["matching_row_indices"]],
            "matching_row_labels": [str(label) for label in dataset["matching_row_labels"]],
            "query_id_probabilities": dict(query_id_probabilities),
            **(
                {"comparison": str(comparison), "comparison_probabilities": dict(comparison_probabilities)}
                if str(query_id) == "threshold_count"
                else {}
            ),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "supporting_cell_ids": [str(cell_id) for cell_id in supporting_cell_ids],
            "query_column": str(dataset["query_column"]),
            "query_column_index": int(dataset["query_column_index"]),
            "question_format": "categorical_filter_count"
            if str(query_id) == "categorical_value_count"
            else "column_filter_count",
            **dict(variant_relation_fields),
        },
        "witness_symbolic": {
            "type": "bbox_set",
            "value": list(annotation_bboxes),
        },
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": list(annotation_bboxes),
        },
    }

    variant_bonus = (
        0.05
        if str(query_id) == "categorical_value_count"
        else 0.04
        if str(query_id) == "in_interval"
        else 0.01
    )
    return TableCountingTaskComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type=str(answer_type),
        answer_value=answer_gt_value,
        annotation_type=str(annotation_type),
        annotation_value=list(annotation_value),
        image=image,
        query_id=str(query_id),
        trace_payload=dict(trace_payload),
    )


__all__ = ["TableCountingTaskComponents", "build_table_counting_task_components"]
