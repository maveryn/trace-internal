"""Common trace scaffolding for matrix public tasks."""

from __future__ import annotations

from typing import Any, Dict, List

from .cell_common import _REASONING_LOAD_BY_VARIANT, _SCENE_LOAD_BY_VARIANT
from .runtime import MatrixRenderResult, font_assets_payload




def build_trace_payload(
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
    answer_value: Any,
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
        "render_spec": render_spec(
            dataset=dataset,
            rendered=rendered,
            scene_variant=scene_variant,
            palette_variant=palette_variant,
            header_layout=header_layout,
            grid_style=grid_style,
        ),
        "render_map": render_map(rendered=rendered),
        "execution_trace": execution_trace(
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


def render_spec(
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


def render_map(*, rendered: MatrixRenderResult) -> Dict[str, Any]:
    return {
        "panel_bbox_px": list(rendered.rendered_scene.panel_bbox_px),
        "title_bbox_px": list(rendered.rendered_scene.title_bbox_px),
        "matrix_bbox_px": list(rendered.rendered_scene.matrix_bbox_px),
        "legend_bbox_px": list(rendered.rendered_scene.legend_bbox_px),
        "cell_bboxes_px": dict(rendered.rendered_scene.cell_bbox_map),
        "row_label_bboxes_px": dict(rendered.rendered_scene.row_label_bbox_map),
        "column_label_bboxes_px": dict(rendered.rendered_scene.column_label_bbox_map),
    }


def execution_trace(
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


