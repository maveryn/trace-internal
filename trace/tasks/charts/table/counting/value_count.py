"""Table counting task that counts rows matching one supported table predicate."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from trace.core.task_group_config import get_task_group_defaults
from trace.core.types import TaskComplexity, TypedValue
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.charts.shared.fixed_query_task import MergedChartQueryVariantTaskMixin
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from trace.tasks.charts.table.shared.table_common import (
    SUPPORTED_TABLE_SCENE_VARIANTS,
    TableDefaults,
    build_counting_value_dataset_for_variant,
    projected_table_bbox_evidence,
    resolve_table_axis_variant,
    resolve_table_render_params,
    table_render_style_spec,
    table_value_cell_id,
)
from trace.tasks.charts.table.shared.table_scene import render_table_scene
from trace.tasks.charts.table.shared.visual_defaults import load_table_background_defaults, load_table_noise_defaults


TASK_ID = "task_charts__table__value_predicate_count"
_SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "threshold_count",
    "in_interval",
    "categorical_value_count",
)
_SOURCE_THRESHOLD_VARIANTS: Tuple[str, ...] = ("above_threshold", "below_threshold")
_SUPPORTED_COMPARISONS: Tuple[str, ...] = ("greater_than", "less_than")

_DEFAULTS = TableDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "table_counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_table_background_defaults(task_group="counting")
POST_IMAGE_NOISE_DEFAULTS = load_table_noise_defaults(task_group="counting", apply_prob=0.0)


def _resolve_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic table-counting variant."""

    explicit_variant = params.get("query_variant")
    if explicit_variant is not None and str(explicit_variant).strip().lower() in set(_SOURCE_THRESHOLD_VARIANTS):
        return "threshold_count", {
            str(value): (1.0 if str(value) == "threshold_count" else 0.0)
            for value in _SUPPORTED_QUERY_VARIANTS
        }
    return resolve_table_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_QUERY_VARIANTS,
        task_id=TASK_ID,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


def _resolve_comparison(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str | None, Dict[str, float]]:
    """Resolve threshold comparator for the merged threshold-count variant."""

    explicit_variant = params.get("query_variant")
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
            raise ValueError("query_variant threshold alias conflicts with explicit comparison")
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


class TablesCountingValueCountTask:
    """Count table rows whose queried values satisfy one supported counting predicate."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "table_counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_variant, query_variant_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
        comparison = None
        comparison_probabilities: Dict[str, float] = {}
        if str(query_variant) == "threshold_count":
            comparison, comparison_probabilities = _resolve_comparison(params, instance_seed=int(instance_seed))
        internal_query_variant = (
            _internal_threshold_variant(str(comparison))
            if str(query_variant) == "threshold_count"
            else str(query_variant)
        )
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = build_counting_value_dataset_for_variant(
            query_variant=str(internal_query_variant),
            params=params,
            instance_seed=int(instance_seed),
            gen_defaults=_GEN_DEFAULTS,
            defaults=_DEFAULTS,
            task_id=self.task_id,
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
                "evidence_hint_threshold_count",
                "evidence_hint_in_interval",
                "evidence_hint_categorical_value_count",
                "json_example_threshold_count",
                "json_example_in_interval",
                "json_example_categorical_value_count",
                "json_example_answer_only_threshold_count",
                "json_example_answer_only_in_interval",
                "json_example_answer_only_categorical_value_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(query_variant)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_variant)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_variant)}"])
        variant_slots = {"query_column": str(dataset["query_column"])}
        if str(query_variant) == "threshold_count":
            variant_slots["threshold_value"] = int(dataset["threshold_value"])
            variant_slots["comparison_phrase"] = _comparison_phrase(comparison)
        elif str(query_variant) == "in_interval":
            variant_slots["interval_min"] = int(dataset["interval_min"])
            variant_slots["interval_max"] = int(dataset["interval_max"])
        else:
            variant_slots["target_category"] = str(dataset["target_category"])

        prompt_selection = render_task_prompt_variants(
            domain=str(getattr(self, "prompt_domain", self.domain)),
            task_group=str(getattr(self, "prompt_task_group", self.task_group)),
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
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
        evidence_projection = projected_table_bbox_evidence(rendered_scene, supporting_cell_ids)
        evidence_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in evidence_projection["bbox_set"]
        ]
        answer_value = int(dataset["answer_value"])
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        values_by_row = {
            str(row_label): {
                str(header): _trace_cell_value(value)
                for header, value in row_values.items()
            }
            for row_label, row_values in dataset["values_by_row"].items()
        }
        variant_relation_fields: Dict[str, Any]
        if str(query_variant) == "threshold_count":
            variant_relation_fields = {
                "threshold_value": int(dataset["threshold_value"]),
                "comparison": str(comparison),
            }
        elif str(query_variant) == "in_interval":
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
                    "query_variant": str(query_variant),
                    "internal_query_variant": str(internal_query_variant),
                    "scene_variant": str(scene_variant),
                    "answer_value": int(answer_value),
                    "supporting_cell_ids": [str(cell_id) for cell_id in supporting_cell_ids],
                    "query_column": str(dataset["query_column"]),
                    **dict(variant_relation_fields),
                },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query_variant),
                    "internal_query_variant": str(internal_query_variant),
                    "scene_variant": str(scene_variant),
                    "query_column": str(dataset["query_column"]),
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    **(
                        {"comparison": str(comparison), "comparison_probabilities": dict(comparison_probabilities)}
                        if str(query_variant) == "threshold_count"
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
                "query_variant": str(query_variant),
                "internal_query_variant": str(internal_query_variant),
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
                "query_variant_probabilities": dict(query_variant_probabilities),
                **(
                    {"comparison": str(comparison), "comparison_probabilities": dict(comparison_probabilities)}
                    if str(query_variant) == "threshold_count"
                    else {}
                ),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "supporting_cell_ids": [str(cell_id) for cell_id in supporting_cell_ids],
                "query_column": str(dataset["query_column"]),
                "query_column_index": int(dataset["query_column_index"]),
                "question_format": "categorical_filter_count"
                if str(query_variant) == "categorical_value_count"
                else "column_filter_count",
                **dict(variant_relation_fields),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }

        variant_bonus = (
            0.05
            if str(query_variant) == "categorical_value_count"
            else 0.04
            if str(query_variant) == "in_interval"
            else 0.01
        )
        complexity = TaskComplexity(
            complexity_score=float(
                0.14
                + (0.025 * int(dataset["row_count"]))
                + (0.015 * int(dataset["numeric_column_count"]))
                + float(variant_bonus)
            ),
            complexity_components={
                "query_variant": str(query_variant),
                "scene_variant": str(scene_variant),
                "row_count": int(dataset["row_count"]),
                "numeric_column_count": int(dataset["numeric_column_count"]),
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
            query_variant=str(query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsTableValuePredicateCountTask(MergedChartQueryVariantTaskMixin, TablesCountingValueCountTask):
    """Count table rows matching one sampled value predicate."""

    task_id = "task_charts__table__value_predicate_count"
    domain = "charts"
    task_group = "table_counting"
    prompt_domain = "charts"
    prompt_task_group = "table_counting"
    allowed_query_variants = ("threshold_count", "in_interval", "categorical_value_count")


__all__ = [
    "ChartsTableValuePredicateCountTask",
    "TablesCountingValueCountTask",
]
