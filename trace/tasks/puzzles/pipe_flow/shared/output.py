"""Trace payload assembly for pipe-flow repair puzzles."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.puzzles.shared.unit_size_jitter import with_puzzle_unit_size_jitter

from .state import PipeFlowDataset, RenderParams, RenderedPipeFlowScene, SCENE_ID


def option_trace(dataset: PipeFlowDataset) -> list[dict[str, Any]]:
    """Serialize option pieces and rotation-solvability metadata."""

    return [
        {
            "option_id": str(option.option_id),
            "label": str(option.label),
            "is_correct": bool(option.is_correct),
            "rotation_allowed": True,
            "display_rotation_turns": int(option.display_rotation_turns),
            "connects_after_rotation_turns": [
                int(value) for value in option.connects_after_rotation_turns
            ],
            "local_openings": [
                {"row": int(row), "col": int(col), "openings": list(openings)}
                for row, col, openings in option.local_openings
            ],
        }
        for option in dataset.options
    ]


def tile_trace(dataset: PipeFlowDataset) -> list[dict[str, Any]]:
    """Serialize visible grid tiles and their current openings."""

    return [
        {
            "tile_id": str(tile.tile_id),
            "label": str(tile.label),
            "row_index": int(tile.row),
            "col_index": int(tile.col),
            "current_openings": list(tile.current_openings),
            "required_openings": list(tile.required_openings),
            "is_path": bool(tile.is_path),
            "is_branch": bool(tile.is_branch),
        }
        for tile in dataset.tiles
    ]


def build_trace_payload(
    *,
    dataset: PipeFlowDataset,
    rendered_scene: RenderedPipeFlowScene,
    render_params: RenderParams,
    prompt_meta: Mapping[str, Any],
    task_fields: Mapping[str, Any],
    background_meta: Mapping[str, Any],
    scene_style_meta: Mapping[str, Any],
    post_noise_meta: Mapping[str, Any],
    projected_annotation: Mapping[str, Any],
    question_format: str,
) -> dict[str, Any]:
    """Build the metadata trace that backs answer and annotation verification."""

    return {
        "scene_ir": {
            "scene_kind": SCENE_ID,
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "scene_id": SCENE_ID,
                "scene_variant": str(dataset.scene_variant),
                "answer_label": str(dataset.answer_label),
                "correct_option_panel_id": str(dataset.correct_option_panel_id),
                "missing_region_id": str(dataset.missing_region_id),
            },
        },
        "render_spec": {
            "scene_id": SCENE_ID,
            "canvas_width": int(render_params.canvas_width),
            "canvas_height": int(render_params.canvas_height),
            "coord_space": "pixel",
            "scene_variant": str(dataset.scene_variant),
            "background_style": dict(background_meta),
            "scene_style": dict(scene_style_meta),
            "post_image_noise": dict(post_noise_meta),
            "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
            "unit_size_jitter": dict(render_params.unit_size_jitter),
        },
        "render_map": with_puzzle_unit_size_jitter(
            {
                "image_id": "img0",
                "scene_bbox_px": [
                    round(float(value), 3) for value in rendered_scene.scene_bbox_px
                ],
                "tile_bboxes_px": {
                    str(key): [round(float(v), 3) for v in value]
                    for key, value in rendered_scene.tile_bbox_map.items()
                },
                "item_bboxes_px": {
                    str(key): [round(float(v), 3) for v in value]
                    for key, value in rendered_scene.item_bbox_map.items()
                },
                "annotation_source": "item_bboxes_px",
            },
            render_params.unit_size_jitter,
        ),
        "execution_trace": {
            **dict(task_fields),
            "question_format": str(question_format),
            "tiles": tile_trace(dataset),
            "option_specs": option_trace(dataset),
            "path_cells": [[int(r), int(c)] for r, c in dataset.path_cells],
            "branch_cells": [[int(r), int(c)] for r, c in dataset.branch_cells],
            "branch_terminal_cells": [
                [int(r), int(c)] for r, c in dataset.branch_terminal_cells
            ],
            "start_cell": [int(dataset.start_cell[0]), int(dataset.start_cell[1])],
            "destination_cell": [
                int(dataset.destination_cell[0]),
                int(dataset.destination_cell[1]),
            ],
            "missing_origin": [int(dataset.missing_origin[0]), int(dataset.missing_origin[1])],
            "missing_cells": [[int(r), int(c)] for r, c in dataset.missing_cells],
            "missing_region_id": str(dataset.missing_region_id),
            "correct_option_panel_id": str(dataset.correct_option_panel_id),
            "supporting_item_ids": [
                str(dataset.correct_option_panel_id),
                str(dataset.missing_region_id),
            ],
            "answer_value": str(dataset.answer_label),
        },
        "witness_symbolic": {
            "type": str(projected_annotation.get("type", "")),
            "value": projected_annotation.get("bbox_map", projected_annotation.get("value")),
        },
        "projected_annotation": dict(projected_annotation),
    }
