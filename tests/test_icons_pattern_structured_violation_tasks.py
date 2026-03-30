"""Behavior tests for consolidated icon structured-violation task."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.icons.pattern.structured_violation import IconsPatternStructuredViolationTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _plausible_row_violation_indices(rotations: list[int]) -> tuple[bool, set[int]]:
    exact_match = False
    plausible: set[int] = set()
    for start in (0, 90, 180, 270):
        for step in (90, 270):
            expected = [int((start + (index * step)) % 360) for index in range(len(rotations))]
            mismatches = [index for index, (left, right) in enumerate(zip(rotations, expected)) if int(left) != int(right)]
            if not mismatches:
                exact_match = True
            elif len(mismatches) == 1:
                plausible.add(int(mismatches[0]))
    return exact_match, plausible


def _plausible_grid_rotation_indices(rotations: list[int], *, grid_rows: int, grid_cols: int) -> tuple[bool, set[int]]:
    exact_match = False
    plausible: set[int] = set()
    for base in (0, 90, 180, 270):
        for row_step in (90, 180, 270):
            for col_step in (90, 180, 270):
                expected = [
                    int((base + ((index // grid_cols) * row_step) + ((index % grid_cols) * col_step)) % 360)
                    for index in range(len(rotations))
                ]
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


def test_icons_pattern_structured_violation_row_rotation_contract_matches_scene() -> None:
    task = IconsPatternStructuredViolationTask()
    out = task.generate(
        24110,
        params={
            "task_variant": "row_rotation_violation",
            "sequence_length": 6,
            "violation_cell_index": 3,
            "start_rotation_degrees": 0,
            "step_delta_degrees": 90,
        },
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    assert trace["scene_ir"]["scene_kind"] == "icons_pattern_structured_violation"
    assert execution["legacy_task_id"] == "task_icons_sequence_rotation_violation"
    assert execution["scene_variant"] == "sequence_row"
    assert execution["task_variant"] == "row_rotation_violation"
    assert trace["query_spec"]["template_id"] == "icons_pattern_v1"
    assert int(out.answer_gt.value) == 4
    assert len(out.evidence_gt.value) == 1
    exact_match, plausible_indices = _plausible_row_violation_indices(list(execution["observed_sequence_rotations_degrees"]))
    assert exact_match is False
    assert plausible_indices == {3}


def test_icons_pattern_structured_violation_grid_rotation_contract_matches_scene() -> None:
    task = IconsPatternStructuredViolationTask()
    out = task.generate(
        24111,
        params={
            "task_variant": "grid_rotation_violation",
            "answer_index": 5,
            "base_rotation_degrees": 0,
            "row_step_degrees": 90,
            "col_step_degrees": 180,
            "violation_rotation_degrees": 90,
        },
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    assert trace["scene_ir"]["scene_kind"] == "icons_pattern_structured_violation"
    assert execution["legacy_task_id"] == "task_icons_pattern_grid_rotation_violation"
    assert execution["scene_variant"] == "numbered_grid"
    assert execution["task_variant"] == "grid_rotation_violation"
    assert int(out.answer_gt.value) == 5
    exact_match, plausible_indices = _plausible_grid_rotation_indices(
        list(execution["observed_grid_rotations_degrees"]),
        grid_rows=int(execution["grid_rows"]),
        grid_cols=int(execution["grid_cols"]),
    )
    assert exact_match is False
    assert plausible_indices == {4}


def test_icons_pattern_structured_violation_grid_size_contract_matches_scene() -> None:
    task = IconsPatternStructuredViolationTask()
    out = task.generate(
        24112,
        params={
            "task_variant": "grid_size_violation",
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
    assert trace["scene_ir"]["scene_kind"] == "icons_pattern_structured_violation"
    assert execution["legacy_task_id"] == "task_icons_pattern_grid_size_violation"
    assert execution["scene_variant"] == "numbered_grid"
    assert execution["task_variant"] == "grid_size_violation"
    assert int(out.answer_gt.value) == 5
    exact_match, plausible_indices = _plausible_grid_size_indices(
        list(execution["observed_grid_size_levels"]),
        grid_rows=int(execution["grid_rows"]),
        grid_cols=int(execution["grid_cols"]),
    )
    assert exact_match is False
    assert plausible_indices == {4}


def test_icons_pattern_structured_violation_prompt_example_matches_contract() -> None:
    task = IconsPatternStructuredViolationTask()
    out = task.generate(24113, params={"task_variant": "grid_rotation_violation", "answer_index": 5}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 5}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert len(answer_and_evidence["evidence"]) == 1
    assert answer_and_evidence["answer"] == 5


def test_icons_pattern_structured_violation_balances_variants_by_default() -> None:
    task = IconsPatternStructuredViolationTask()
    counts: Counter[str] = Counter()
    for index in range(90):
        out = task.generate(
            hash64(24114, "icons_pattern_structured_violation", index),
            params={"_sampling_index": index},
            max_attempts=200,
        )
        counts[str(out.task_variant)] += 1
    assert set(counts.keys()) == {
        "row_rotation_violation",
        "grid_rotation_violation",
        "grid_size_violation",
    }
    assert max(counts.values()) - min(counts.values()) <= 1
