"""Table statistics task that aggregates one target column over a filtered row subset."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
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
from ..shared.table_common import (
    SUPPORTED_TABLE_SCENE_VARIANTS,
    TableDefaults,
    build_statistics_filtered_subset_dataset_for_variant,
    projected_table_bbox_evidence,
    render_table_filter_condition,
    resolve_table_axis_variant,
    resolve_table_render_params,
)
from ..shared.table_scene import render_table_scene
from ..shared.visual_defaults import load_table_background_defaults, load_table_noise_defaults


TASK_ID = "task_tables_statistics_filtered_subset_value"
_SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = ("filtered_column_sum", "filtered_column_mean")

_DEFAULTS = TableDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("tables", "statistics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_table_background_defaults(task_group="statistics")
POST_IMAGE_NOISE_DEFAULTS = load_table_noise_defaults(task_group="statistics", apply_prob=0.0)


def _resolve_task_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the semantic filtered-summary variant."""

    return resolve_table_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=_SUPPORTED_TASK_VARIANTS,
        task_id=TASK_ID,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
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

@register_task
class TablesStatisticsFilteredSubsetValueTask:
    """Aggregate one numeric column over the rows selected by another column filter."""

    task_id = TASK_ID
    domain = "tables"
    task_group = "statistics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        task_variant, task_variant_probabilities = _resolve_task_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = build_statistics_filtered_subset_dataset_for_variant(
            task_variant=str(task_variant),
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
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_spreadsheet",
                "object_description_zebra",
                "object_description_ledger",
                "object_description_card_table",
                "evidence_hint_filtered_column_sum",
                "evidence_hint_filtered_column_mean",
                "json_example_filtered_column_sum",
                "json_example_filtered_column_mean",
                "json_example_answer_only_filtered_column_sum",
                "json_example_answer_only_filtered_column_mean",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(scene_variant)}"])
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(task_variant)}"])
        json_example = str(prompt_defaults[f"json_example_{str(task_variant)}"])
        json_example_answer_only = str(prompt_defaults[f"json_example_answer_only_{str(task_variant)}"])
        filter_condition = render_table_filter_condition(dataset)

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "query_filter_column": str(dataset["filter_column"]),
                "query_target_column": str(dataset["target_column"]),
                "filter_condition": str(filter_condition),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        supporting_cell_ids = [str(cell_id) for cell_id in dataset["supporting_cell_ids"]]
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
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"table_{str(scene_variant)}_statistics",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "filter_variant": str(dataset["filter_variant"]),
                    "filter_column": str(dataset["filter_column"]),
                    "target_column": str(dataset["target_column"]),
                    "answer_value": int(answer_value),
                    "selected_row_labels": [str(label) for label in dataset["selected_row_labels"]],
                    "supporting_cell_ids": [str(cell_id) for cell_id in supporting_cell_ids],
                    **(
                        {"threshold_value": int(dataset["threshold_value"])}
                        if str(dataset["filter_variant"]) in {"above_threshold", "below_threshold"}
                        else {
                            "interval_min": int(dataset["interval_min"]),
                            "interval_max": int(dataset["interval_max"]),
                        }
                    ),
                },
            },
            "query_spec": {
                "task_variant": str(task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(task_variant),
                    "scene_variant": str(scene_variant),
                    "filter_variant": str(dataset["filter_variant"]),
                    "filter_column": str(dataset["filter_column"]),
                    "target_column": str(dataset["target_column"]),
                    "task_variant_probabilities": dict(task_variant_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "row_count": int(dataset["row_count"]),
                    "numeric_column_count": int(dataset["numeric_column_count"]),
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
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "filter_variant": str(dataset["filter_variant"]),
                "filter_column": str(dataset["filter_column"]),
                "filter_column_index": int(dataset["filter_column_index"]),
                "target_column": str(dataset["target_column"]),
                "target_column_index": int(dataset["target_column_index"]),
                "answer_value": int(answer_value),
                "row_labels": [str(label) for label in dataset["row_labels"]],
                "column_headers": [str(header) for header in dataset["column_headers"]],
                "values_by_row": dict(values_by_row),
                "row_count": int(dataset["row_count"]),
                "numeric_column_count": int(dataset["numeric_column_count"]),
                "row_count_range": list(dataset["row_count_range"]),
                "numeric_column_count_range": list(dataset["numeric_column_count_range"]),
                "value_range": list(dataset["value_range"]),
                "selected_row_indices": [int(row_index) for row_index in dataset["selected_row_indices"]],
                "selected_row_labels": [str(label) for label in dataset["selected_row_labels"]],
                "task_variant_probabilities": dict(task_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": "filtered_subset_value",
                "supporting_cell_ids": [str(cell_id) for cell_id in supporting_cell_ids],
                **(
                    {"threshold_value": int(dataset["threshold_value"])}
                    if str(dataset["filter_variant"]) in {"above_threshold", "below_threshold"}
                    else {
                        "interval_min": int(dataset["interval_min"]),
                        "interval_max": int(dataset["interval_max"]),
                    }
                ),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }

        filter_bonus = 0.03 if str(dataset["filter_variant"]) == "in_interval" else 0.01
        complexity = TaskComplexity(
            complexity_score=float(
                0.2
                + (0.025 * int(dataset["row_count"]))
                + (0.02 * int(dataset["numeric_column_count"]))
                + (0.05 if str(task_variant) == "filtered_column_mean" else 0.03)
                + float(filter_bonus)
            ),
            complexity_components={
                "task_variant": str(task_variant),
                "scene_variant": str(scene_variant),
                "filter_variant": str(dataset["filter_variant"]),
                "row_count": int(dataset["row_count"]),
                "numeric_column_count": int(dataset["numeric_column_count"]),
                "selected_row_count": int(len(dataset["selected_row_indices"])),
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
            task_variant=str(task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["TablesStatisticsFilteredSubsetValueTask"]
