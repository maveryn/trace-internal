"""Contract tests for toggle-grid puzzle tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.logic.toggle_grid import (
    REPAIR_QUERY_ID,
    RESULT_QUERY_ID,
    SCENE_ID,
    TOGGLE_REPAIR_TASK_ID,
    TOGGLE_RESULT_TASK_ID,
    PuzzlesLogicToggleRepairSwitchLabelTask,
    PuzzlesLogicToggleResultLabelTask,
)


def _assert_bbox_in_image(bbox: list[float], image_size: tuple[int, int]) -> None:
    assert len(bbox) == 4
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= image_size[0]
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= image_size[1]


def _toggle_once(state: list[list[int]], row: int, col: int) -> list[list[int]]:
    out = [list(values) for values in state]
    for rr, cc in ((row, col), (row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
        if 0 <= rr < len(out) and 0 <= cc < len(out[0]):
            out[rr][cc] = 1 - int(out[rr][cc])
    return out


def _apply_toggles(state: list[list[int]], cells: list[list[int]]) -> list[list[int]]:
    out = [list(values) for values in state]
    for row, col in cells:
        out = _toggle_once(out, int(row), int(col))
    return out


def test_toggle_grid_tasks_are_registered() -> None:
    assert TASK_REGISTRY[TOGGLE_RESULT_TASK_ID] is PuzzlesLogicToggleResultLabelTask
    assert TASK_REGISTRY[TOGGLE_REPAIR_TASK_ID] is PuzzlesLogicToggleRepairSwitchLabelTask

    for task_cls in (PuzzlesLogicToggleResultLabelTask, PuzzlesLogicToggleRepairSwitchLabelTask):
        task = task_cls()
        assert task.domain == "puzzles"
        assert task.scene_id == "logic"


def test_toggle_result_contract() -> None:
    out = PuzzlesLogicToggleResultLabelTask().generate(2026053001, params={}, max_attempts=50)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == RESULT_QUERY_ID
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"start_grid", "selected_option"}
    assert trace["projected_annotation"]["type"] == "keyed_bbox_map"
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_keyed_bbox_map"] == out.annotation_gt.value
    assert execution["annotation_role_item_ids"] == {
        "start_grid": "start_grid_bbox_px",
        "selected_option": f"option_{execution['answer_value']}",
    }
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]

    recomputed = _apply_toggles(execution["start_state"], execution["pressed_cells"])
    assert recomputed == execution["target_state"]
    correct = next(option for option in execution["option_specs"] if option["option_label"] == execution["answer_value"])
    assert correct["state"] == execution["target_state"]
    assert str(out.answer_gt.value) == str(execution["answer_value"])
    assert out.annotation_gt.value["start_grid"] == trace["render_map"]["start_grid_bbox_px"]
    assert out.annotation_gt.value["selected_option"] == trace["render_map"]["option_panel_bboxes_px"][f"option_{execution['answer_value']}"]
    for bbox in out.annotation_gt.value.values():
        _assert_bbox_in_image(bbox, out.image.size)


def test_toggle_repair_contract() -> None:
    out = PuzzlesLogicToggleRepairSwitchLabelTask().generate(2026053002, params={}, max_attempts=50)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == REPAIR_QUERY_ID
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"start_grid", "target_grid", "selected_switch"}
    assert trace["projected_annotation"]["type"] == "keyed_bbox_map"
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_keyed_bbox_map"] == out.annotation_gt.value
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]

    correct = next(option for option in execution["candidate_switch_specs"] if option["option_label"] == execution["answer_value"])
    recomputed = _toggle_once(execution["start_state"], int(correct["row"]), int(correct["col"]))
    assert recomputed == execution["target_state"]
    assert str(out.answer_gt.value) == str(execution["answer_value"])
    assert execution["annotation_role_item_ids"] == {
        "start_grid": "start_grid_bbox_px",
        "target_grid": "target_grid_bbox_px",
        "selected_switch": f"cell_{correct['row']}_{correct['col']}",
    }
    assert out.annotation_gt.value["start_grid"] == trace["render_map"]["start_grid_bbox_px"]
    assert out.annotation_gt.value["target_grid"] == trace["render_map"]["target_grid_bbox_px"]
    assert out.annotation_gt.value["selected_switch"] == trace["render_map"]["start_cell_bboxes_px"][f"cell_{correct['row']}_{correct['col']}"]
    for bbox in out.annotation_gt.value.values():
        _assert_bbox_in_image(bbox, out.image.size)
