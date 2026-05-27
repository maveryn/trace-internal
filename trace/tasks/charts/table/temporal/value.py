"""Table temporal task that reasons over year-ordered columns for queried rows."""

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
    build_temporal_value_dataset_for_variant,
    projected_table_bbox_evidence,
    resolve_table_axis_variant,
    resolve_table_render_params,
    table_render_style_spec,
)
from trace.tasks.charts.table.shared.table_scene import render_table_scene
from trace.tasks.charts.table.shared.visual_defaults import load_table_background_defaults, load_table_noise_defaults


TASK_ID = "task_charts__table__temporal_row_interval_difference_value"
_SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "absolute_difference_between_rows_over_year_interval",
    "sum_absolute_differences_between_rows_over_year_interval",
)

_DEFAULTS = TableDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "table_temporal")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_table_background_defaults(task_group="temporal")
POST_IMAGE_NOISE_DEFAULTS = load_table_noise_defaults(task_group="temporal", apply_prob=0.0)


def _resolve_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic temporal table variant."""

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


class ChartsTableTemporalValueTaskBase:
    """Return one temporal value derived from year-ordered columns for queried row data."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "table_temporal"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_variant, query_variant_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = build_temporal_value_dataset_for_variant(
            query_variant=str(query_variant),
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
                "evidence_hint_absolute_difference_between_rows_over_year_interval",
                "evidence_hint_sum_absolute_differences_between_rows_over_year_interval",
                "json_example_absolute_difference_between_rows_over_year_interval",
                "json_example_sum_absolute_differences_between_rows_over_year_interval",
                "json_example_answer_only_absolute_difference_between_rows_over_year_interval",
                "json_example_answer_only_sum_absolute_differences_between_rows_over_year_interval",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(query_variant)}"])
        json_example = str(prompt_defaults[f"json_example_{str(query_variant)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(query_variant)}"])

        prompt_slots = {
            "object_description": str(object_description),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "evidence_hint": str(evidence_hint),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            "query_row_label": str(dataset["query_row_label"]),
            "query_row_label_a": str(dataset["query_row_label_a"]),
            "query_row_label_b": str(dataset["query_row_label_b"]),
            "query_year_start": str(dataset["query_year_start"]),
            "query_year_end": str(dataset["query_year_end"]),
        }

        prompt_selection = render_task_prompt_variants(
            domain=str(getattr(self, "prompt_domain", self.domain)),
            task_group=str(getattr(self, "prompt_task_group", self.task_group)),
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=dict(prompt_slots),
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        query_cells = [dict(cell) for cell in dataset["query_cells"]]
        supporting_cell_ids = [str(cell["cell_id"]) for cell in query_cells]
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
                str(header): int(value)
                for header, value in row_values.items()
            }
            for row_label, row_values in dataset["values_by_row"].items()
        }
        cell_bbox_map = {
            str(cell_trace["cell_id"]): list(cell_trace["bbox_px"])
            for cell_trace in rendered_scene.cell_traces
        }
        evidence_order = "row_then_query_year_order"
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"table_{str(scene_variant)}_temporal",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "query_row_label": str(dataset["query_row_label"]),
                    "query_row_labels": list(dataset["query_row_labels"]),
                    "query_years": list(dataset["query_years"]),
                    "row_interval_sums": dict(dataset["row_interval_sums"]),
                    "paired_absolute_differences": list(dataset["paired_absolute_differences"]),
                    "answer_value": int(answer_value),
                    "supporting_cell_ids": [str(cell_id) for cell_id in supporting_cell_ids],
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
                    "scene_variant": str(scene_variant),
                    "query_row_label": str(dataset["query_row_label"]),
                    "query_row_labels": list(dataset["query_row_labels"]),
                    "query_years": list(dataset["query_years"]),
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "row_count": int(dataset["row_count"]),
                    "numeric_column_count": int(dataset["numeric_column_count"]),
                    "interval_length_range": list(dataset["interval_length_range"]),
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
                "row_label_width": {
                    "fraction": float(render_params.row_label_width_fraction),
                    "min_width_px": int(render_params.row_label_min_width_px),
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
                "scene_variant": str(scene_variant),
                "row_count": int(dataset["row_count"]),
                "numeric_column_count": int(dataset["numeric_column_count"]),
                "row_count_range": list(dataset["row_count_range"]),
                "numeric_column_count_range": list(dataset["numeric_column_count_range"]),
                "value_range": list(dataset["value_range"]),
                "row_labels": list(dataset["row_labels"]),
                "column_headers": list(dataset["column_headers"]),
                "values_by_row": dict(values_by_row),
                "query_row_label": str(dataset["query_row_label"]),
                "query_row_index": int(dataset["query_row_index"]),
                "query_row_label_a": str(dataset["query_row_label_a"]),
                "query_row_index_a": int(dataset["query_row_index_a"]),
                "query_row_label_b": str(dataset["query_row_label_b"]),
                "query_row_index_b": int(dataset["query_row_index_b"]),
                "query_row_labels": list(dataset["query_row_labels"]),
                "query_years": list(dataset["query_years"]),
                "query_year_start": str(dataset["query_year_start"]),
                "query_year_end": str(dataset["query_year_end"]),
                "interval_length_range": list(dataset["interval_length_range"]),
                "query_cells": [dict(cell) for cell in query_cells],
                "row_interval_sums": dict(dataset["row_interval_sums"]),
                "paired_absolute_differences": list(dataset["paired_absolute_differences"]),
                "supporting_cell_ids": [str(cell_id) for cell_id in supporting_cell_ids],
                "answer_value": int(answer_value),
            },
            "verifier_spec": {
                "answer_type": "integer",
                "evidence_type": "bbox_set",
                "evidence_order": str(evidence_order),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": dict(evidence_projection),
        }

        span_length = int(len(query_cells))
        complexity_score = float(0.24 + (0.02 * int(dataset["row_count"])) + (0.03 * int(dataset["numeric_column_count"])))
        variant_load = 0.86
        complexity = TaskComplexity(
            complexity_score=float(complexity_score),
            complexity_components={
                "rows": float(dataset["row_count"]),
                "numeric_columns": float(dataset["numeric_column_count"]),
                "query_span": float(span_length),
                "variant_load": float(variant_load),
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
class ChartsTableTemporalRowIntervalDifferenceValueTask(MergedChartQueryVariantTaskMixin, ChartsTableTemporalValueTaskBase):
    """Compute one sampled row-interval difference metric from a temporal table."""

    task_id = "task_charts__table__temporal_row_interval_difference_value"
    domain = "charts"
    task_group = "table_temporal"
    prompt_domain = "charts"
    prompt_task_group = "table_temporal"
    allowed_query_variants = (
        "absolute_difference_between_rows_over_year_interval",
        "sum_absolute_differences_between_rows_over_year_interval",
    )


__all__ = [
    "ChartsTableTemporalRowIntervalDifferenceValueTask",
    "ChartsTableTemporalValueTaskBase",
]
