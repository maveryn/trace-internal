"""Behavior tests for icon 2D size-pattern violation task."""

from __future__ import annotations

import json
from collections import Counter
from statistics import mean

from trace.core.seed import hash64
from trace.tasks.icons.pattern.grid_size_violation import IconsPatternGridSizeViolationTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _plausible_violation_indices(levels: list[int], *, grid_rows: int, grid_cols: int) -> tuple[bool, set[int]]:
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


def test_icons_pattern_grid_size_violation_contract_matches_scene() -> None:
    task = IconsPatternGridSizeViolationTask()
    out = task.generate(
        18210,
        params={
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
    entities = trace["scene_ir"]["entities"]
    cell_entities = [entity for entity in entities if str(entity["entity_kind"]) == "pattern_cell"]
    icon_entities = [entity for entity in entities if str(entity["entity_kind"]) == "scene_icon"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 5
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert trace["scene_ir"]["scene_kind"] == "icons_pattern_grid_size_violation"
    assert execution["question_format"] == "identify_grid_size_violation"
    assert execution["task_variant"] == "row_col_size_grid_violation"
    assert execution["size_levels"] == [1, 2, 3, 4, 5]
    assert execution["expected_grid_size_levels"] == [3, 2, 1, 4, 3, 2, 5, 4, 3]
    assert execution["observed_grid_size_levels"] == [3, 2, 1, 4, 1, 2, 5, 4, 3]
    assert int(execution["grid_rows"]) == 3
    assert int(execution["grid_cols"]) == 3
    assert int(execution["answer_index"]) == 5
    assert int(execution["violation_cell_index"]) == 4
    assert int(execution["base_size_level"]) == 3
    assert int(execution["row_step_levels"]) == 1
    assert int(execution["col_step_levels"]) == -1
    assert int(execution["violation_size_level"]) == 1
    assert int(execution["shared_rotation_degrees"]) == 180
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
    assert 116 <= int(execution["cell_box_width_px"]) <= 152
    assert 116 <= int(execution["cell_box_height_px"]) <= 152

    row_counts = Counter(int(entity["grid_row"]) for entity in cell_entities)
    col_counts = Counter(int(entity["grid_col"]) for entity in cell_entities)
    assert row_counts == {0: 3, 1: 3, 2: 3}
    assert col_counts == {0: 3, 1: 3, 2: 3}
    row_centers = {
        int(row): mean(
            [(float(entity["cell_bbox_xyxy"][1]) + float(entity["cell_bbox_xyxy"][3])) * 0.5 for entity in cell_entities if int(entity["grid_row"]) == row]
        )
        for row in row_counts
    }
    col_centers = {
        int(col): mean(
            [(float(entity["cell_bbox_xyxy"][0]) + float(entity["cell_bbox_xyxy"][2])) * 0.5 for entity in cell_entities if int(entity["grid_col"]) == col]
        )
        for col in col_counts
    }
    assert row_centers[0] < row_centers[1] < row_centers[2]
    assert col_centers[0] < col_centers[1] < col_centers[2]

    exact_match, plausible_indices = _plausible_violation_indices(
        list(execution["observed_grid_size_levels"]),
        grid_rows=int(execution["grid_rows"]),
        grid_cols=int(execution["grid_cols"]),
    )
    assert exact_match is False
    assert plausible_indices == {4}

    size_level_map = {int(key): int(value) for key, value in execution["size_level_nominal_sizes_px"].items()}
    assert sorted(size_level_map.keys()) == [1, 2, 3, 4, 5]
    ordered_sizes = [size_level_map[index] for index in range(1, 6)]
    assert ordered_sizes == sorted(ordered_sizes)
    assert {ordered_sizes[index + 1] - ordered_sizes[index] for index in range(4)} == {8}
    assert ordered_sizes[0] >= 34
    assert ordered_sizes[-1] <= 82

    scene_colors = {tuple(int(channel) for channel in entity["tint_rgb"]) for entity in icon_entities}
    assert len(scene_colors) == 1
    for index, entity in enumerate(icon_entities):
        assert str(entity["icon_id"]) == str(execution["pattern_icon_id"])
        assert int(entity["rotation_degrees"]) == 180
        assert int(entity["nominal_size_px"]) == int(execution["observed_grid_nominal_sizes_px"][index])
        assert isinstance(entity["noise_edits"], list)
        assert str(entity["cell_label_text"]).isdigit()
        assert int(entity["cell_index"]) == index

    violating_boxes = out.evidence_gt.value
    assert violating_boxes == trace["projected_evidence"]["bbox_set"]
    violating_cells = [entity for entity in cell_entities if bool(entity["is_violation"])]
    assert len(violating_cells) == 1
    assert violating_boxes[0] == violating_cells[0]["cell_bbox_xyxy"]
    assert str(violating_cells[0]["cell_label_text"]) == "5"
    assert int(violating_cells[0]["expected_size_level"]) == 3
    assert int(violating_cells[0]["observed_size_level"]) == 1
    assert int(violating_cells[0]["expected_nominal_size_px"]) == int(size_level_map[3])
    assert int(violating_cells[0]["observed_nominal_size_px"]) == int(size_level_map[1])


def test_icons_pattern_grid_size_violation_prompt_example_matches_contract() -> None:
    task = IconsPatternGridSizeViolationTask()
    out = task.generate(
        18211,
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


def test_icons_pattern_grid_size_violation_balanced_answer_support_defaults() -> None:
    task = IconsPatternGridSizeViolationTask()
    answer_counts: Counter[int] = Counter()
    corner_violations = 0
    center_violations = 0
    for index in range(90):
        out = task.generate(
            hash64(18212, "icons_pattern_grid_size_violation", index),
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
