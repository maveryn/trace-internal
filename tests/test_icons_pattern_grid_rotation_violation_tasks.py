"""Behavior tests for icon 2D rotation-pattern violation task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.icons.pattern.grid_rotation_violation import IconsPatternGridRotationViolationTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _plausible_violation_indices(rotations: list[int], *, grid_rows: int, grid_cols: int) -> tuple[bool, set[int]]:
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


def test_icons_pattern_grid_rotation_violation_contract_matches_scene() -> None:
    task = IconsPatternGridRotationViolationTask()
    out = task.generate(
        18110,
        params={
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
    entities = trace["scene_ir"]["entities"]
    cell_entities = [entity for entity in entities if str(entity["entity_kind"]) == "pattern_cell"]
    icon_entities = [entity for entity in entities if str(entity["entity_kind"]) == "scene_icon"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 5
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert trace["scene_ir"]["scene_kind"] == "icons_pattern_grid_rotation_violation"
    assert execution["question_format"] == "identify_grid_rotation_violation"
    assert execution["task_variant"] == "row_col_rotation_grid_violation"
    assert execution["expected_grid_rotations_degrees"] == [0, 180, 0, 90, 270, 90, 180, 0, 180]
    assert execution["observed_grid_rotations_degrees"] == [0, 180, 0, 90, 90, 90, 180, 0, 180]
    assert int(execution["grid_rows"]) == 3
    assert int(execution["grid_cols"]) == 3
    assert int(execution["answer_index"]) == 5
    assert int(execution["violation_cell_index"]) == 4
    assert int(execution["base_rotation_degrees"]) == 0
    assert int(execution["row_step_degrees"]) == 90
    assert int(execution["col_step_degrees"]) == 180
    assert 0.0 <= float(out.complexity.complexity_score) <= 1.0
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "rule_inference",
        "ambiguity",
        "clutter",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
    assert len(cell_entities) == 9
    assert len(icon_entities) == 9
    assert 104 <= int(execution["cell_box_width_px"]) <= 140
    assert 104 <= int(execution["cell_box_height_px"]) <= 140

    exact_match, plausible_indices = _plausible_violation_indices(
        list(execution["observed_grid_rotations_degrees"]),
        grid_rows=int(execution["grid_rows"]),
        grid_cols=int(execution["grid_cols"]),
    )
    assert exact_match is False
    assert plausible_indices == {4}

    scene_colors = {tuple(int(channel) for channel in entity["tint_rgb"]) for entity in icon_entities}
    assert len(scene_colors) == 1
    for index, entity in enumerate(icon_entities):
        assert str(entity["icon_id"]) == str(execution["pattern_icon_id"])
        assert int(entity["nominal_size_px"]) >= 16
        assert int(entity["rotation_degrees"]) in {0, 90, 180, 270}
        assert isinstance(entity["noise_edits"], list)
        assert str(entity["cell_label_text"]).isdigit()
        assert int(entity["cell_index"]) == index

    violating_boxes = out.evidence_gt.value
    assert violating_boxes == trace["projected_evidence"]["bbox_set"]
    violating_cells = [entity for entity in cell_entities if bool(entity["is_violation"])]
    assert len(violating_cells) == 1
    assert violating_boxes[0] == violating_cells[0]["cell_bbox_xyxy"]
    assert str(violating_cells[0]["cell_label_text"]) == "5"
    assert int(violating_cells[0]["expected_rotation_degrees"]) == 270
    assert int(violating_cells[0]["observed_rotation_degrees"]) == 90


def test_icons_pattern_grid_rotation_violation_prompt_example_matches_contract() -> None:
    task = IconsPatternGridRotationViolationTask()
    out = task.generate(
        18111,
        params={"answer_index": 5},
        max_attempts=200,
    )
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 5}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert len(answer_and_evidence["evidence"]) == 1
    assert answer_and_evidence["answer"] == 5


def test_icons_pattern_grid_rotation_violation_balanced_answer_support_defaults() -> None:
    task = IconsPatternGridRotationViolationTask()
    answer_counts: Counter[int] = Counter()
    corner_violations = 0
    center_violations = 0
    for index in range(90):
        out = task.generate(
            hash64(18112, "icons_pattern_grid_rotation_violation", index),
            params={"_sampling_index": index},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        answer_index = int(execution["answer_index"])
        violation_cell_index = int(execution["violation_cell_index"])
        answer_counts[answer_index] += 1
        assert 1 <= answer_index <= 9
        if violation_cell_index in {0, 2, 6, 8}:
            corner_violations += 1
        if violation_cell_index == 4:
            center_violations += 1
    assert set(answer_counts.keys()) == set(range(1, 10))
    assert max(answer_counts.values()) - min(answer_counts.values()) <= 1
    assert corner_violations > 0
    assert center_violations > 0
