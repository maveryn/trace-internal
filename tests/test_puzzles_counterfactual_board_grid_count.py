"""Contract tests for counterfactual board-grid counting."""

from __future__ import annotations

import pytest

from trace.core.seed import hash64
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.counterfactual.board_grid_count import (
    BOARD_DIMENSION_COUNT_TASK_ID,
    BOARD_LINE_COUNT_TASK_ID,
    SCENE_ID,
    PuzzlesCounterfactualBoardDimensionCountTask,
    PuzzlesCounterfactualBoardLineCountTask,
)


def _assert_bbox_in_image(bbox: list[float], image_size: tuple[int, int]) -> None:
    assert len(bbox) == 4
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= image_size[0]
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= image_size[1]


def test_counterfactual_board_grid_count_task_is_registered() -> None:
    for task_id in (BOARD_DIMENSION_COUNT_TASK_ID, BOARD_LINE_COUNT_TASK_ID):
        assert task_id in TASK_REGISTRY
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "puzzles"
        assert taxonomy.scene_id == SCENE_ID
        assert taxonomy.source_task_group == "counterfactual"


def _task_for_query(query_id: object):
    if str(query_id) in {"row_count", "column_count"}:
        return PuzzlesCounterfactualBoardDimensionCountTask(), BOARD_DIMENSION_COUNT_TASK_ID
    return PuzzlesCounterfactualBoardLineCountTask(), BOARD_LINE_COUNT_TASK_ID


@pytest.mark.parametrize(
    ("seed_suffix", "params"),
    [
        (
            0,
            {
                "board_style": "chess_checkers",
                "query_id": "row_count",
                "visible_rows": 6,
                "visible_columns": 8,
            },
        ),
        (
            1,
            {
                "board_style": "sudoku",
                "query_id": "column_count",
                "visible_rows": 9,
                "visible_columns": 10,
            },
        ),
        (
            2,
            {
                "board_style": "xiangqi",
                "query_id": "horizontal_line_count",
                "visible_rows": 11,
                "visible_columns": 9,
            },
        ),
        (
            3,
            {
                "board_style": "xiangqi",
                "query_id": "vertical_line_count",
                "visible_rows": 10,
                "visible_columns": 8,
            },
        ),
    ],
)
def test_counterfactual_board_grid_count_annotation_tracks_counted_units(
    seed_suffix: int,
    params: dict[str, object],
) -> None:
    task, task_id = _task_for_query(params["query_id"])
    out = task.generate(
        int(hash64(20260529, task_id, seed_suffix)),
        params=params,
        max_attempts=20,
    )

    assert out.scene_id == SCENE_ID
    assert out.query_id == params["query_id"]
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == int(out.answer_gt.value)

    trace = out.trace_payload
    execution = trace["execution_trace"]
    expected_bboxes = [[float(value) for value in bbox] for bbox in execution["counted_element_bboxes_px"]]
    assert out.annotation_gt.value == expected_bboxes
    assert trace["render_map"]["annotation_source"] == "counted_element_bboxes_px"
    assert execution["supporting_item_ids"] == execution["counted_element_ids"]
    assert trace["projected_annotation"]["type"] == "bbox_set"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert trace["witness_symbolic"]["value"] == out.annotation_gt.value

    for bbox in out.annotation_gt.value:
        _assert_bbox_in_image(bbox, out.image.size)

    noise = trace["render_spec"]["post_image_noise"]
    assert noise["enabled"] is True
    assert float(noise["apply_prob"]) == pytest.approx(0.5)
    assert set(noise["edit_types"]) == {"blur", "downsample", "jpeg", "noise"}
    assert noise["edit_count_range"] == [1, 1]

    font = trace["render_spec"]["label_style"]["font"]
    assert font["source"] == "global_font_pool"
    assert font["font_family"]
    assert font["font_asset_version"]


def test_counterfactual_board_grid_count_prompt_is_neutral_about_size_change() -> None:
    out = PuzzlesCounterfactualBoardDimensionCountTask().generate(
        int(hash64(20260529, BOARD_DIMENSION_COUNT_TASK_ID, 50)),
        params={
            "board_style": "chess_checkers",
            "query_id": "column_count",
            "visible_rows": 7,
            "visible_columns": 9,
        },
        max_attempts=20,
    )

    prompt = out.prompt.lower()
    assert "usual pattern" not in prompt
    assert "visible size" not in prompt
    assert "may differ" not in prompt
    assert "familiar" not in prompt
    assert "counterfactual" not in prompt


def test_counterfactual_board_grid_count_is_deterministic() -> None:
    task = PuzzlesCounterfactualBoardDimensionCountTask()
    seed = int(hash64(20260529, BOARD_DIMENSION_COUNT_TASK_ID, 99))
    params = {
        "board_style": "sudoku",
        "query_id": "row_count",
        "visible_rows": 10,
        "visible_columns": 9,
    }

    left = task.generate(seed, params=params, max_attempts=20)
    right = task.generate(seed, params=params, max_attempts=20)

    assert left.prompt == right.prompt
    assert left.answer_gt == right.answer_gt
    assert left.annotation_gt == right.annotation_gt
    assert left.trace_payload["execution_trace"] == right.trace_payload["execution_trace"]
    assert left.trace_payload["render_spec"]["label_style"] == right.trace_payload["render_spec"]["label_style"]
    assert left.image.tobytes() == right.image.tobytes()
