"""Contracts for pipe-flow puzzle tasks."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import hash64
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.pipe_flow.pipe_flow_repair_tile_label import (
    SCENE_ID,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    PuzzlesPipeFlowRepairTileLabelTask,
)


def test_pipe_flow_task_is_registered() -> None:
    assert TASK_ID in TASK_REGISTRY
    taxonomy = resolve_task_taxonomy(TASK_ID)
    assert taxonomy.domain == "puzzles"
    assert taxonomy.scene_id == SCENE_ID
    assert taxonomy.source_domain == "puzzles"
    assert taxonomy.source_scene_id == ""
    assert SUPPORTED_QUERY_IDS == (SINGLE_QUERY_ID,)


def test_pipe_flow_repair_tile_contract() -> None:
    task = PuzzlesPipeFlowRepairTileLabelTask()
    out = task.generate(
        int(hash64(20260521, TASK_ID, 0)),
        params={
            "query_id": SINGLE_QUERY_ID,
            "grid_size_variant": "9x9",
            "scene_variant": "water_pipe",
            "answer_label": "C",
        },
        max_attempts=80,
    )

    assert out.scene_id == SCENE_ID
    assert out.query_id == SINGLE_QUERY_ID
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "C"
    assert out.annotation_gt.type == "bbox_map"
    assert set(out.annotation_gt.value) == {"selected_option", "missing_gap"}
    assert "annotation" in out.prompt_variants["answer_and_annotation"].lower()
    assert "selected_option" in out.prompt_variants["answer_and_annotation"]
    assert "missing_gap" in out.prompt_variants["answer_and_annotation"]

    trace = out.trace_payload["execution_trace"]
    assert trace["question_format"] == "pipe_flow_repair_tile_label"
    assert trace["query_id"] == SINGLE_QUERY_ID
    assert trace["internal_question_format"] == "pipe_flow_repair_tile_label"
    assert trace["answer_label"] == "C"
    assert trace["query_id_probabilities"] == {SINGLE_QUERY_ID: 1.0}
    assert trace["answer_label_probabilities"] == {
        label: (1.0 if label == "C" else 0.0)
        for label in "ABCD"
    }
    correct_options = [option for option in trace["option_specs"] if option["is_correct"]]
    assert len(correct_options) == 1
    assert correct_options[0]["label"] == "C"
    assert correct_options[0]["rotation_allowed"] is True
    assert correct_options[0]["connects_after_rotation_turns"]
    assert all(
        not option["connects_after_rotation_turns"]
        for option in trace["option_specs"]
        if not option["is_correct"]
    )
    assert trace["rotation_allowed"] is True
    assert trace["candidate_count"] == 4
    assert len(trace["missing_cells"]) == 4
    assert trace["branch_cells"]
    assert trace["branch_terminal_cells"]
    assert all(
        row in {0, trace["rows"] - 1} or col in {0, trace["cols"] - 1}
        for row, col in trace["branch_terminal_cells"]
    )

    correct_bbox = out.trace_payload["render_map"]["item_bboxes_px"][
        trace["correct_option_panel_id"]
    ]
    missing_bbox = out.trace_payload["render_map"]["item_bboxes_px"][
        trace["missing_region_id"]
    ]
    assert out.annotation_gt.value == {
        "selected_option": [float(value) for value in correct_bbox],
        "missing_gap": [float(value) for value in missing_bbox],
    }
    assert out.trace_payload["projected_annotation"]["bbox_map"] == out.annotation_gt.value


def test_pipe_flow_repair_tile_is_deterministic() -> None:
    task = PuzzlesPipeFlowRepairTileLabelTask()
    seed = int(hash64(20260521, TASK_ID, 1))
    params = {
        "grid_size_variant": "6x6",
        "scene_variant": "circuit_trace",
        "answer_label": "D",
    }
    left = task.generate(seed, params=params, max_attempts=80)
    right = task.generate(seed, params=params, max_attempts=80)

    assert left.prompt == right.prompt
    assert left.answer_gt == right.answer_gt
    assert left.annotation_gt == right.annotation_gt
    assert left.trace_payload["execution_trace"] == right.trace_payload["execution_trace"]
    assert left.image.tobytes() == right.image.tobytes()
