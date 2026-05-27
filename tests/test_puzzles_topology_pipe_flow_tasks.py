"""Contracts for pipe-flow topology puzzle tasks."""

from __future__ import annotations

from trace.core.seed import hash64
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.topology.pipe_flow_grid import (
    QUERY_ID,
    SCENE_ID,
    TASK_ID,
    PuzzlesTopologyPipeFlowRepairTileLabelTask,
)


def test_pipe_flow_task_is_registered() -> None:
    assert TASK_ID in TASK_REGISTRY
    taxonomy = resolve_task_taxonomy(TASK_ID)
    assert taxonomy.domain == "puzzles"
    assert taxonomy.scene_id == SCENE_ID
    assert taxonomy.source_task_group == "topology"


def test_pipe_flow_repair_tile_contract() -> None:
    task = PuzzlesTopologyPipeFlowRepairTileLabelTask()
    out = task.generate(
        int(hash64(20260521, TASK_ID, 0)),
        params={"grid_size_variant": "9x9", "scene_variant": "water_pipe", "answer_label": "C"},
        max_attempts=80,
    )

    assert out.query_id == "default"
    assert out.scene_id == SCENE_ID
    assert out.query_id == QUERY_ID
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "C"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 2
    assert 'Format for the "evidence" field:' in out.prompt_variants["answer_and_evidence"]
    assert "[x0, y0, x1, y1]" in out.prompt_variants["answer_and_evidence"]

    trace = out.trace_payload["execution_trace"]
    assert trace["question_format"] == QUERY_ID
    assert trace["answer_label"] == "C"
    assert trace["query_id"] == QUERY_ID
    correct_options = [option for option in trace["option_specs"] if option["is_correct"]]
    assert len(correct_options) == 1
    assert correct_options[0]["label"] == "C"
    assert correct_options[0]["rotation_allowed"] is True
    assert correct_options[0]["connects_after_rotation_turns"]
    assert all(not option["connects_after_rotation_turns"] for option in trace["option_specs"] if not option["is_correct"])
    assert trace["rotation_allowed"] is True
    assert trace["candidate_count"] == 6
    assert len(trace["missing_cells"]) == 4
    assert trace["branch_cells"]
    assert trace["branch_terminal_cells"]
    assert all(
        row in {0, trace["rows"] - 1} or col in {0, trace["cols"] - 1}
        for row, col in trace["branch_terminal_cells"]
    )
    start_tile = next(tile for tile in trace["tiles"] if [tile["row_index"], tile["col_index"]] == trace["start_cell"])
    finish_tile = next(tile for tile in trace["tiles"] if [tile["row_index"], tile["col_index"]] == trace["destination_cell"])
    assert "W" not in start_tile["current_openings"]
    assert "E" not in finish_tile["current_openings"]

    correct_bbox = out.trace_payload["render_map"]["item_bboxes_px"][trace["correct_option_panel_id"]]
    missing_bbox = out.trace_payload["render_map"]["item_bboxes_px"][trace["missing_region_id"]]
    assert out.evidence_gt.value == [[float(value) for value in correct_bbox], [float(value) for value in missing_bbox]]


def test_pipe_flow_repair_tile_is_deterministic() -> None:
    task = PuzzlesTopologyPipeFlowRepairTileLabelTask()
    seed = int(hash64(20260521, TASK_ID, 1))
    params = {"grid_size_variant": "6x6", "scene_variant": "circuit_trace", "answer_label": "E"}
    left = task.generate(seed, params=params, max_attempts=80)
    right = task.generate(seed, params=params, max_attempts=80)

    assert left.prompt == right.prompt
    assert left.answer_gt == right.answer_gt
    assert left.evidence_gt == right.evidence_gt
    assert left.trace_payload["execution_trace"] == right.trace_payload["execution_trace"]
    assert left.image.tobytes() == right.image.tobytes()
