"""Contract tests for toggle-grid puzzle scene-package tasks."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.puzzles.toggle_grid.shared.rules import apply_toggles, toggle_once
from trace.tasks.puzzles.toggle_grid.shared.state import SCENE_ID
from trace.tasks.puzzles.toggle_grid.toggle_repair_switch_label import (
    PuzzlesToggleGridToggleRepairSwitchLabelTask,
)
from trace.tasks.puzzles.toggle_grid.toggle_result_label import (
    PuzzlesToggleGridToggleResultLabelTask,
)

RESULT_TASK_ID = "task_puzzles__toggle_grid__toggle_result_label"
REPAIR_TASK_ID = "task_puzzles__toggle_grid__toggle_repair_switch_label"


def _assert_bbox_in_image(bbox: list[float], image_size: tuple[int, int]) -> None:
    """Assert one scalar bbox lies inside the rendered image."""

    assert len(bbox) == 4
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= image_size[0]
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= image_size[1]


def test_toggle_grid_tasks_are_registered() -> None:
    """The public ids route to one task file each."""

    assert TASK_REGISTRY[RESULT_TASK_ID] is PuzzlesToggleGridToggleResultLabelTask
    assert TASK_REGISTRY[REPAIR_TASK_ID] is PuzzlesToggleGridToggleRepairSwitchLabelTask

    for task_id in (RESULT_TASK_ID, REPAIR_TASK_ID):
        task = create_task(task_id)
        assert task.domain == "puzzles"
        assert task.supported_query_ids == (SINGLE_QUERY_ID,)
        assert not hasattr(task, "scene_id")


def test_toggle_result_contract() -> None:
    """Result task answer is the option matching sequential toggle simulation."""

    out = create_task(RESULT_TASK_ID).generate(2026053001, params={}, max_attempts=64)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == SINGLE_QUERY_ID
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "bbox"
    assert trace["projected_annotation"]["type"] == "bbox"
    assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]

    recomputed = apply_toggles(
        tuple(tuple(int(value) for value in row) for row in execution["start_state"]),
        tuple(tuple(int(value) for value in cell) for cell in execution["pressed_cells"]),
    )
    assert [list(row) for row in recomputed] == execution["target_state"]
    correct = next(
        option
        for option in execution["result_options"]
        if option["option_label"] == execution["answer_value"]
    )
    assert correct["state"] == execution["target_state"]
    assert bool(correct["is_correct"])
    assert str(out.answer_gt.value) == str(execution["answer_value"])
    selected_bbox = trace["render_map"]["option_panel_bboxes_px"][
        f"option_{execution['answer_value']}"
    ]
    assert out.annotation_gt.value == selected_bbox
    _assert_bbox_in_image(out.annotation_gt.value, out.image.size)


def test_toggle_repair_contract() -> None:
    """Repair task answer is the switch whose one press reaches the target grid."""

    out = create_task(REPAIR_TASK_ID).generate(2026053002, params={}, max_attempts=64)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == SINGLE_QUERY_ID
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "bbox"
    assert trace["projected_annotation"]["type"] == "bbox"
    assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]

    correct = next(
        option
        for option in execution["switch_options"]
        if option["option_label"] == execution["answer_value"]
    )
    recomputed = toggle_once(
        tuple(tuple(int(value) for value in row) for row in execution["start_state"]),
        (int(correct["row"]), int(correct["col"])),
    )
    assert [list(row) for row in recomputed] == execution["target_state"]
    assert bool(correct["is_correct"])
    assert str(out.answer_gt.value) == str(execution["answer_value"])
    selected_bbox = trace["render_map"]["start_cell_bboxes_px"][
        f"cell_{correct['row']}_{correct['col']}"
    ]
    assert out.annotation_gt.value == selected_bbox
    _assert_bbox_in_image(out.annotation_gt.value, out.image.size)
