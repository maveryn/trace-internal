"""Select a row or column label from an extremal matrix cell."""

from __future__ import annotations

from typing import Any, Dict, List

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.output_metadata import default_task_versions
from .shared.cell_common import (
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    SCENE_ID,
    _decoupled_sampling_params,
    _resolve_extremum_direction,
    _resolve_grid_style,
    _resolve_header_layout,
    _resolve_palette_variant,
    _resolve_query_axis,
    _resolve_scene_variant,
)
from .shared.cell_sampling import construct_axis_extremum_dataset
from .shared.prompts import build_prompt_artifacts, dynamic_slots
from .shared.runtime import MatrixRenderResult, annotation_bboxes, font_assets_payload, render_matrix_scene


@register_task
class ChartsMatrixAxisExtremumLabelTask:
    """Return a matrix row/column label selected by a second-extremum cell query."""

    task_id = "task_charts__matrix__axis_extremum_label"
    domain = "charts"
    scene_id = SCENE_ID
    objective_contract = "axis_extremum_label"
    supported_query_ids = ("axis_extremum_label",)
    default_dataset_enabled = True
    supports_unanswerable = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                return self._generate_once(int(instance_seed) + int(attempt), params=params)
            except ValueError as exc:
                last_error = exc
                continue
        raise ValueError(f"could not construct unique-answer matrix axis-extremum task: {last_error}")

    def _generate_once(self, instance_seed: int, *, params: Dict[str, Any]) -> TaskOutput:
        scene_params = _decoupled_sampling_params(params, divisor=2, explicit_keys=("scene_variant", "scene_variant_weights"))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            scene_params,
            objective_contract=self.objective_contract,
            instance_seed=int(instance_seed),
        )
        palette_params = _decoupled_sampling_params(params, divisor=3, explicit_keys=("palette_variant", "palette_variant_weights"))
        palette_variant, palette_variant_probabilities = _resolve_palette_variant(palette_params, instance_seed=int(instance_seed))
        header_params = _decoupled_sampling_params(params, divisor=5, explicit_keys=("header_layout", "header_layout_weights"))
        header_layout, header_layout_probabilities = _resolve_header_layout(header_params, instance_seed=int(instance_seed))
        grid_params = _decoupled_sampling_params(params, divisor=7, explicit_keys=("grid_style", "grid_style_weights"))
        grid_style, grid_style_probabilities = _resolve_grid_style(grid_params, instance_seed=int(instance_seed))
        axis_params = _decoupled_sampling_params(params, divisor=11, explicit_keys=("query_axis", "query_axis_weights"))
        query_axis, query_axis_probabilities = _resolve_query_axis(axis_params, instance_seed=int(instance_seed))
        extremum_params = _decoupled_sampling_params(params, divisor=13, explicit_keys=("extremum_direction", "extremum_direction_weights"))
        extremum_direction, extremum_probabilities = _resolve_extremum_direction(
            extremum_params,
            instance_seed=int(instance_seed),
        )
        dataset = construct_axis_extremum_dataset(
            scene_variant=str(scene_variant),
            query_axis=str(query_axis),
            extremum_direction=str(extremum_direction),
            supports_unanswerable=bool(self.supports_unanswerable),
            params=params,
            instance_seed=int(instance_seed),
        )
        rendered = render_matrix_scene(
            dataset=dataset,
            scene_variant=str(scene_variant),
            palette_variant=str(palette_variant),
            header_layout=str(header_layout),
            grid_style=str(grid_style),
            params=params,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_artifacts(
            prompt_query_key=self.objective_contract,
            dynamic_slot_values=dynamic_slots(
                dataset,
                scene_variant=str(scene_variant),
                supports_unanswerable=bool(self.supports_unanswerable),
            ),
            instance_seed=int(instance_seed),
        )
        annotation_cell_ids = [str(cell_id) for cell_id in dataset["annotation_cell_ids"]]
        support_header_keys = [str(key) for key in dataset["annotation_header_keys"]]
        boxes, entries = annotation_bboxes(
            rendered_scene=rendered.rendered_scene,
            annotation_cell_ids=annotation_cell_ids,
        )
        answer_value = str(dataset["answer_value"])
        trace_payload = _build_trace_payload(
            objective_contract=self.objective_contract,
            dataset=dataset,
            rendered=rendered,
            prompt_artifacts=prompt_artifacts,
            scene_variant=str(scene_variant),
            palette_variant=str(palette_variant),
            header_layout=str(header_layout),
            grid_style=str(grid_style),
            probabilities={
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "palette_variant_probabilities": dict(palette_variant_probabilities),
                "header_layout_probabilities": dict(header_layout_probabilities),
                "grid_style_probabilities": dict(grid_style_probabilities),
                "query_axis_probabilities": dict(query_axis_probabilities),
                "extremum_direction_probabilities": dict(extremum_probabilities),
            },
            annotation_cell_ids=annotation_cell_ids,
            support_header_keys=support_header_keys,
            annotation_bboxes=boxes,
            annotation_entries=entries,
            answer_value=answer_value,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=TypedValue(type=str(dataset["answer_type"]), value=answer_value),
            annotation_gt=TypedValue(type="bbox_set", value=list(boxes)),
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=self.objective_contract,
        )




def _build_trace_payload(
    *,
    objective_contract: str,
    dataset: Dict[str, Any],
    rendered: MatrixRenderResult,
    prompt_artifacts,
    scene_variant: str,
    palette_variant: str,
    header_layout: str,
    grid_style: str,
    probabilities: Dict[str, Dict[str, float]],
    annotation_cell_ids: List[str],
    support_header_keys: List[str],
    annotation_bboxes: List[List[float]],
    annotation_entries: List[Dict[str, Any]],
    answer_value: str,
) -> Dict[str, Any]:
    query_params = {
        "query_id": str(objective_contract),
        "scene_variant": str(scene_variant),
        "palette_variant": str(palette_variant),
        "header_layout": str(header_layout),
        "grid_style": str(grid_style),
        "row_count": int(dataset["row_count"]),
        "column_count": int(dataset["column_count"]),
        **dict(probabilities),
        **dict(dataset["question_params"]),
    }
    return {
        "scene_ir": {
            "scene_kind": "chart_annotated_matrix",
            "entities": [dict(item) for item in rendered.rendered_scene.entities],
            "relations": {
                "query_id": str(objective_contract),
                "scene_variant": str(scene_variant),
                "answer_value": answer_value,
                "answer_row_index": int(dataset["answer_row_index"]),
                "answer_column_index": int(dataset["answer_column_index"]),
                "annotation_cell_ids": list(annotation_cell_ids),
                "support_header_keys": list(support_header_keys),
                "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
            },
        },
        "query_spec": {
            "query_id": str(objective_contract),
            "template_id": "charts_matrix_v1",
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": dict(query_params),
        },
        "render_spec": _render_spec(
            dataset=dataset,
            rendered=rendered,
            scene_variant=scene_variant,
            palette_variant=palette_variant,
            header_layout=header_layout,
            grid_style=grid_style,
        ),
        "render_map": _render_map(rendered=rendered),
        "execution_trace": _execution_trace(
            objective_contract=objective_contract,
            dataset=dataset,
            scene_variant=scene_variant,
            annotation_cell_ids=annotation_cell_ids,
            support_header_keys=support_header_keys,
        ),
        "witness_symbolic": {
            "type": "matrix_cell_witness",
            "candidate_cell_ids": list(annotation_cell_ids),
            "support_header_keys": list(support_header_keys),
            "answer_value": answer_value,
            "answer_row_index": int(dataset["answer_row_index"]),
            "answer_column_index": int(dataset["answer_column_index"]),
            "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
            **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
        },
        "projected_annotation": {
            "bbox_set": list(annotation_bboxes),
            "entries": [dict(entry) for entry in annotation_entries],
            "cell_ids": list(annotation_cell_ids),
        },
        "background": dict(rendered.background_meta),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


def _render_spec(
    *,
    dataset: Dict[str, Any],
    rendered: MatrixRenderResult,
    scene_variant: str,
    palette_variant: str,
    header_layout: str,
    grid_style: str,
) -> Dict[str, Any]:
    render_params = rendered.render_params
    return {
        "scene_variant": str(scene_variant),
        "palette_variant": str(palette_variant),
        "header_layout": str(header_layout),
        "grid_style": str(grid_style),
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "row_count": int(dataset["row_count"]),
        "column_count": int(dataset["column_count"]),
        "value_min": int(dataset["value_min"]),
        "value_max": int(dataset["value_max"]),
        "layout_jitter": dict(render_params.layout_jitter_meta),
        "font_assets": font_assets_payload(render_params),
        "post_image_noise": dict(rendered.post_noise_meta),
    }


def _render_map(*, rendered: MatrixRenderResult) -> Dict[str, Any]:
    return {
        "panel_bbox_px": list(rendered.rendered_scene.panel_bbox_px),
        "title_bbox_px": list(rendered.rendered_scene.title_bbox_px),
        "matrix_bbox_px": list(rendered.rendered_scene.matrix_bbox_px),
        "legend_bbox_px": list(rendered.rendered_scene.legend_bbox_px),
        "cell_bboxes_px": dict(rendered.rendered_scene.cell_bbox_map),
        "row_label_bboxes_px": dict(rendered.rendered_scene.row_label_bbox_map),
        "column_label_bboxes_px": dict(rendered.rendered_scene.column_label_bbox_map),
    }


def _execution_trace(
    *,
    objective_contract: str,
    dataset: Dict[str, Any],
    scene_variant: str,
    annotation_cell_ids: List[str],
    support_header_keys: List[str],
) -> Dict[str, Any]:
    return {
        "query_id": str(objective_contract),
        "scene_variant": str(scene_variant),
        "question_format": "matrix_cell_query",
        "scene_title": str(dataset["scene_title"]),
        "row_count": int(dataset["row_count"]),
        "column_count": int(dataset["column_count"]),
        "row_labels": list(dataset["row_labels"]),
        "column_labels": list(dataset["column_labels"]),
        "values": [[None if value is None else int(value) for value in row] for row in dataset["values"]],
        "cells": [dict(cell) for cell in dataset["cells"]],
        "cells_by_id": {str(key): dict(value) for key, value in dict(dataset["cells_by_id"]).items()},
        "answer_value": dataset["answer_value"],
        "answer_type": str(dataset["answer_type"]),
        "answer_row_index": int(dataset["answer_row_index"]),
        "answer_column_index": int(dataset["answer_column_index"]),
        "annotation_cell_ids": list(annotation_cell_ids),
        "support_header_keys": list(support_header_keys),
        "query_axis": str(dataset.get("query_axis", "")),
        "extremum_direction": str(dataset.get("extremum_direction", "")),
        "comparison": str(dataset.get("comparison", "")),
        "extremum_rank": int(dataset.get("extremum_rank", 0)),
        "scene_meta": dict(dataset["scene_meta"]),
        "annotation_semantics": str(objective_contract),
        "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
        **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
    }


__all__ = ["ChartsMatrixAxisExtremumLabelTask"]
