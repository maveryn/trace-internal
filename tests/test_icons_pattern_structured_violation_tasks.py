"""Behavior tests for public icon pattern-violation tasks."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.icons.pattern.sequence_rotation_violation import IconsPatternSequenceRotationViolationTask
from trace.tasks.icons.pattern_grid.attribute_pattern_violation_index import IconsPatternGridAttributePatternViolationTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _plausible_row_violation_indices(rotations: list[int]) -> tuple[bool, set[int]]:
    exact_match = False
    plausible: set[int] = set()
    for start in (0, 90, 180, 270):
        for step in (90, 180, 270):
            expected = [int((start + (index * step)) % 360) for index in range(len(rotations))]
            mismatches = [index for index, (left, right) in enumerate(zip(rotations, expected)) if int(left) != int(right)]
            if not mismatches:
                exact_match = True
            elif len(mismatches) == 1:
                plausible.add(int(mismatches[0]))
    return exact_match, plausible


def _plausible_grid_size_indices(levels: list[int], *, grid_rows: int, grid_cols: int) -> tuple[bool, set[int]]:
    exact_match = False
    plausible: set[int] = set()
    allowed_levels = {1, 2, 3, 4, 5}
    for base in (1, 2, 3, 4, 5):
        for row_step in (-1, 0, 1):
            for col_step in (-1, 0, 1):
                if row_step == 0 and col_step == 0:
                    continue
                expected = [
                    int(base + ((index // grid_cols) * row_step) + ((index % grid_cols) * col_step))
                    for index in range(len(levels))
                ]
                if any(int(level) not in allowed_levels for level in expected):
                    continue
                mismatches = [index for index, (left, right) in enumerate(zip(levels, expected)) if int(left) != int(right)]
                if not mismatches:
                    exact_match = True
                elif len(mismatches) == 1:
                    plausible.add(int(mismatches[0]))
    return exact_match, plausible


def _uniform_color_violation_indices(levels: list[int], *, grid_rows: int, grid_cols: int, group_axis: str) -> set[int]:
    plausible: set[int] = set()
    if group_axis == "row":
        for row in range(grid_rows):
            row_indices = [row * grid_cols + col for col in range(grid_cols)]
            counts = Counter(int(levels[index]) for index in row_indices)
            common_level, common_count = counts.most_common(1)[0]
            if common_count == grid_cols - 1:
                plausible.update(index for index in row_indices if int(levels[index]) != int(common_level))
    elif group_axis == "column":
        for col in range(grid_cols):
            col_indices = [row * grid_cols + col for row in range(grid_rows)]
            counts = Counter(int(levels[index]) for index in col_indices)
            common_level, common_count = counts.most_common(1)[0]
            if common_count == grid_rows - 1:
                plausible.update(index for index in col_indices if int(levels[index]) != int(common_level))
    else:
        raise ValueError(group_axis)
    return plausible


def test_icons_pattern_structured_violation_row_rotation_contract_matches_scene() -> None:
    task = IconsPatternSequenceRotationViolationTask()
    out = task.generate(
        24110,
        params={
            "sequence_length": 10,
            "violation_cell_index": 3,
            "start_rotation_degrees": 0,
            "step_delta_degrees": 180,
        },
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    assert out.query_id == "row_rotation_violation"
    assert trace["scene_ir"]["scene_kind"] == "icons_pattern_sequence_rotation_violation"
    assert trace["scene_ir"]["scene_id"] == "sequence_strip"
    assert trace["query_spec"]["query_id"] == "row_rotation_violation"
    assert "source_task_id" not in execution
    assert "source_query_id" not in execution
    assert execution["scene_variant"] == "sequence_row"
    assert execution["query_id"] == "row_rotation_violation"
    assert trace["query_spec"]["template_id"] == "icons_pattern_v0"
    assert int(out.answer_gt.value) == 4
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 1
    assert trace["projected_annotation"]["type"] == "bbox_set"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_bbox_set"] == out.annotation_gt.value
    assert len(trace["projected_annotation"]["pixel_point_set"]) == 1
    drawn_text_roles = {
        str(record.get("role"))
        for record in trace["render_spec"]["drawn_text"]["text_legibility"]["records"]
    }
    assert "icon_cell_label_text" in drawn_text_roles
    exact_match, plausible_indices = _plausible_row_violation_indices(list(execution["observed_sequence_rotations_degrees"]))
    assert exact_match is False
    assert plausible_indices == {3}


def test_icons_pattern_structured_violation_grid_size_contract_matches_scene() -> None:
    task = IconsPatternGridAttributePatternViolationTask()
    out = task.generate(
        24112,
        params={
            "query_id": "grid_size_violation",
            "answer_index": 5,
            "base_size_level": 3,
            "row_step_levels": 1,
            "col_step_levels": -1,
            "violation_size_level": 1,
            "shared_rotation_degrees": 180,
        },
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    assert out.query_id == "grid_size_violation"
    assert trace["scene_ir"]["scene_kind"] == "icons_pattern_grid_size_violation"
    assert trace["scene_ir"]["scene_id"] == "pattern_grid"
    assert trace["query_spec"]["query_id"] == "grid_size_violation"
    assert "source_task_id" not in execution
    assert "source_query_id" not in execution
    assert execution["scene_variant"] == "numbered_grid"
    assert execution["query_id"] == "grid_size_violation"
    assert int(out.answer_gt.value) == 5
    assert out.annotation_gt.type == "bbox"
    assert trace["projected_annotation"]["type"] == "bbox"
    assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
    style = trace["render_spec"]["style"]
    assert int(style["text_legibility"]["failure_count"]) == 0
    assert {
        str(record["role"])
        for record in style["text_legibility"]["records"]
    } >= {"icon_panel_header_text", "icon_cell_label_text"}
    exact_match, plausible_indices = _plausible_grid_size_indices(
        list(execution["observed_grid_size_levels"]),
        grid_rows=int(execution["grid_rows"]),
        grid_cols=int(execution["grid_cols"]),
    )
    assert exact_match is False
    assert plausible_indices == {4}


@pytest.mark.parametrize(
    ("query_id", "group_axis", "expected_scene_kind", "expected_question_format"),
    (
        (
            "grid_row_color_violation",
            "row",
            "icons_pattern_grid_row_color_violation",
            "identify_grid_row_color_violation",
        ),
        (
            "grid_column_color_violation",
            "column",
            "icons_pattern_grid_column_color_violation",
            "identify_grid_column_color_violation",
        ),
    ),
)
def test_icons_pattern_grid_color_violation_contract_matches_scene(
    query_id: str,
    group_axis: str,
    expected_scene_kind: str,
    expected_question_format: str,
) -> None:
    task = IconsPatternGridAttributePatternViolationTask()
    out = task.generate(
        24115,
        params={
            "query_id": query_id,
            "answer_index": 5,
            f"{group_axis}_color_levels": [1, 2, 3],
            "violation_color_level": 0,
            "shared_rotation_degrees": 180,
        },
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    assert out.query_id == query_id
    assert trace["scene_ir"]["scene_kind"] == expected_scene_kind
    assert trace["scene_ir"]["scene_id"] == "pattern_grid"
    assert trace["query_spec"]["query_id"] == query_id
    assert execution["scene_variant"] == "numbered_grid"
    assert execution["query_id"] == query_id
    assert execution["question_format"] == expected_question_format
    assert execution["pattern_rule"] == f"{group_axis}_uniform_color"
    assert execution["color_group_axis"] == group_axis
    assert int(out.answer_gt.value) == 5
    assert out.annotation_gt.type == "bbox"
    assert trace["projected_annotation"]["type"] == "bbox"
    assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
    style = trace["render_spec"]["style"]
    assert int(style["text_legibility"]["failure_count"]) == 0
    assert {
        str(record["role"])
        for record in style["text_legibility"]["records"]
    } >= {"icon_panel_header_text", "icon_cell_label_text"}
    plausible_indices = _uniform_color_violation_indices(
        list(execution["observed_grid_color_levels"]),
        grid_rows=int(execution["grid_rows"]),
        grid_cols=int(execution["grid_cols"]),
        group_axis=group_axis,
    )
    assert plausible_indices == {4}


def test_icons_pattern_structured_violation_prompt_example_matches_contract() -> None:
    task = IconsPatternGridAttributePatternViolationTask()
    out = task.generate(24113, params={"query_id": "grid_size_violation", "answer_index": 5}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_annotation = _extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    assert answer_only == {"answer": 5}
    assert list(answer_and_annotation.keys()) == ["annotation", "answer"]
    assert isinstance(answer_and_annotation["annotation"], list)
    assert len(answer_and_annotation["annotation"]) == 4
    assert answer_and_annotation["answer"] == 5


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_answers"),
    (
        (IconsPatternSequenceRotationViolationTask, {}, set(range(2, 7))),
        (IconsPatternGridAttributePatternViolationTask, {"query_id": "grid_size_violation"}, set(range(1, 10))),
        (IconsPatternGridAttributePatternViolationTask, {"query_id": "grid_row_color_violation"}, set(range(1, 10))),
        (IconsPatternGridAttributePatternViolationTask, {"query_id": "grid_column_color_violation"}, set(range(1, 10))),
    ),
)
def test_icons_pattern_violation_balances_answers_by_default(task_cls, params: dict, expected_answers: set[int]) -> None:
    task = task_cls()
    counts: Counter[int] = Counter()
    for index in range(90):
        out = task.generate(
            hash64(24114, task.task_id, index),
            params=dict(params),
            max_attempts=200,
        )
        assert out.query_id
        counts[int(out.answer_gt.value)] += 1
    assert set(counts.keys()) == expected_answers
