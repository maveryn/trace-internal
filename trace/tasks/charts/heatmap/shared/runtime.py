"""Runtime helpers for heatmap chart tasks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping

from trace.core.types import TypedValue
from trace.core.visual.background import make_background_canvas
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.charts.heatmap.shared.grid_common import (
    _REASONING_LOAD_BY_VARIANT,
    _SCENE_LOAD_BY_VARIANT,
    POST_IMAGE_BACKGROUND_DEFAULTS,
    POST_IMAGE_NOISE_DEFAULTS,
)
from trace.tasks.charts.heatmap.shared.grid_rendering import _render_heatmap, _resolve_render_params
from trace.tasks.shared.font_assets import font_asset_version


def render_dataset(
    dataset: Mapping[str, Any],
    *,
    params: Mapping[str, Any],
    instance_seed: int,
) -> tuple[Any, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    render_style_params = {**dict(params), "_render_style_seed": int(instance_seed)}
    render_params = _resolve_render_params(render_style_params)
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    rendered_scene = _render_heatmap(
        background,
        scene_title=str(dataset["scene_title"]),
        scene_variant=str(dataset["scene_variant"]),
        row_labels=list(dataset["row_labels"]),
        column_labels=list(dataset["column_labels"]),
        cells=list(dataset["cells"]),
        render_params=render_params,
        colorbar_ticks=tuple(int(value) for value in dataset.get("colorbar_ticks", ())),
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    rendered_scene = replace(rendered_scene, image=image)
    render_meta = {
        "scene_variant": str(dataset["scene_variant"]),
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "row_count": int(dataset["row_count"]),
        "column_count": int(dataset["column_count"]),
        "heat_bin_count": int(dataset["heat_bin_count"]),
        "colorbar_value_min": dataset.get("colorbar_value_min"),
        "colorbar_value_max": dataset.get("colorbar_value_max"),
        "colorbar_ticks": list(dataset.get("colorbar_ticks", [])),
        "cell_gap_px": int(render_params.cell_gap_px),
        "layout_jitter": dict(render_params.layout_jitter_meta),
        "font_assets": {
            "asset_version": font_asset_version(),
            "chart_font_family": str(render_params.font_family),
        },
        "post_image_noise": dict(post_noise_meta),
    }
    return rendered_scene, dict(render_meta), dict(background_meta), dict(post_noise_meta)


def answer_typed_value(dataset: Mapping[str, Any]) -> TypedValue:
    answer_type = str(dataset["answer_type"])
    value: int | str = int(dataset["answer_value"]) if answer_type == "integer" else str(dataset["answer_value"])
    return TypedValue(type=answer_type, value=value)


def annotation_payload(
    *,
    dataset: Mapping[str, Any],
    rendered: Any,
) -> tuple[str, list[list[float]], Dict[str, Any]]:
    annotation_cell_ids = [str(cell_id) for cell_id in dataset["annotation_cell_ids"]]
    annotation_bboxes = [list(rendered.cell_bbox_map[str(cell_id)]) for cell_id in annotation_cell_ids]
    projected_annotation = {
        "type": "bbox_set",
        "bbox_set": list(annotation_bboxes),
        "pixel_bbox_set": list(annotation_bboxes),
        "bbox_map": {str(cell_id): list(rendered.cell_bbox_map[str(cell_id)]) for cell_id in annotation_cell_ids},
        "cell_ids": list(annotation_cell_ids),
    }
    return "bbox_set", list(annotation_bboxes), dict(projected_annotation)


def build_trace_scaffold(
    *,
    dataset: Mapping[str, Any],
    rendered: Any,
    render_meta: Mapping[str, Any],
    background_meta: Mapping[str, Any],
    post_noise_meta: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
    annotation_value: list[list[float]],
    answer_value: int | str,
) -> Dict[str, Any]:
    annotation_cell_ids = [str(cell_id) for cell_id in dataset["annotation_cell_ids"]]
    prompt_key = str(dataset["prompt_key"])
    question_params = dict(dataset["question_params"])
    return {
        "scene_ir": {
            "scene_kind": "chart_heatmap",
            "entities": [dict(item) for item in rendered.entities],
            "relations": {
                "prompt_key": str(prompt_key),
                "scene_variant": str(dataset["scene_variant"]),
                "query_axis": str(dataset["query_axis"]),
                "answer_value": answer_value,
                "answer_row_index": int(dataset["answer_row_index"]),
                "answer_column_index": int(dataset["answer_column_index"]),
                "annotation_cell_ids": list(annotation_cell_ids),
                "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
                **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
            },
        },
        "render_spec": dict(render_meta),
        "render_map": {
            "panel_bbox_px": list(rendered.panel_bbox_px),
            "title_bbox_px": list(rendered.title_bbox_px),
            "grid_bbox_px": list(rendered.grid_bbox_px),
            "legend_bbox_px": list(rendered.legend_bbox_px),
            "cell_bboxes_px": dict(rendered.cell_bbox_map),
            "row_label_bboxes_px": dict(rendered.row_label_bbox_map),
            "column_label_bboxes_px": dict(rendered.column_label_bbox_map),
        },
        "execution_trace": {
            "prompt_key": str(prompt_key),
            "scene_variant": str(dataset["scene_variant"]),
            "question_format": "heatmap_query",
            "scene_title": str(dataset["scene_title"]),
            "row_count": int(dataset["row_count"]),
            "column_count": int(dataset["column_count"]),
            "row_labels": list(dataset["row_labels"]),
            "column_labels": list(dataset["column_labels"]),
            "heat_bin_count": int(dataset["heat_bin_count"]),
            "colorbar_value_min": dataset.get("colorbar_value_min"),
            "colorbar_value_max": dataset.get("colorbar_value_max"),
            "colorbar_ticks": list(dataset.get("colorbar_ticks", [])),
            "values": [[int(value) for value in row] for row in dataset["values"]],
            "cells": [dict(cell) for cell in dataset["cells"]],
            "cells_by_id": {str(key): dict(value) for key, value in dict(dataset["cells_by_id"]).items()},
            "answer_value": answer_value,
            "answer_type": str(dataset["answer_type"]),
            "answer_row_index": int(dataset["answer_row_index"]),
            "answer_column_index": int(dataset["answer_column_index"]),
            "annotation_cell_ids": list(annotation_cell_ids),
            "query_axis": str(dataset["query_axis"]),
            "condition_kind": str(dataset["condition_kind"]),
            "extremum_direction": str(dataset["extremum_direction"]),
            **dict(question_params),
            "annotation_semantics": str(prompt_key),
            "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
            **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
        },
        "witness_symbolic": {
            "type": "heatmap_witness",
            "candidate_cell_ids": list(annotation_cell_ids),
            "answer_value": answer_value,
            "answer_row_index": int(dataset["answer_row_index"]),
            "answer_column_index": int(dataset["answer_column_index"]),
            "answerability": "unanswerable" if bool(dataset["is_unanswerable"]) else "answerable",
            **({"absence_proof": dict(dataset["absence_proof"])} if bool(dataset["is_unanswerable"]) else {}),
        },
        "projected_annotation": dict(projected_annotation),
        "annotation_refs": [{"cell_id": str(cell_id), "bbox_px": list(box)} for cell_id, box in zip(annotation_cell_ids, annotation_value)],
        "background": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
    }




