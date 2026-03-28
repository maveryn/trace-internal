"""Behavior tests for icon sequence rotation-violation task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.icons.sequence.rotation_violation import IconsSequenceRotationViolationTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _plausible_violation_indices(rotations: list[int]) -> tuple[bool, set[int]]:
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


def test_icons_sequence_rotation_violation_contract_matches_scene() -> None:
    task = IconsSequenceRotationViolationTask()
    out = task.generate(
        16110,
        params={
            "sequence_length": 6,
            "violation_cell_index": 3,
            "start_rotation_degrees": 0,
            "step_delta_degrees": 90,
        },
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    entities = trace["scene_ir"]["entities"]
    cell_entities = [entity for entity in entities if str(entity["entity_kind"]) == "sequence_cell"]
    icon_entities = [entity for entity in entities if str(entity["entity_kind"]) == "scene_icon"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 4
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert trace["scene_ir"]["scene_kind"] == "icons_sequence_rotation_violation"
    assert execution["question_format"] == "identify_rotation_sequence_violation"
    assert execution["task_variant"] == "constant_rotation_step_violation"
    assert execution["expected_sequence_rotations_degrees"] == [0, 90, 180, 270, 0, 90]
    assert int(execution["sequence_length"]) == 6
    assert int(execution["answer_index"]) == 4
    assert int(execution["violation_cell_index"]) == 3
    assert int(execution["start_rotation_degrees"]) == 0
    assert int(execution["step_delta_degrees"]) == 90
    assert 0.0 <= float(out.complexity.complexity_score) <= 1.0
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "rule_inference",
        "ambiguity",
        "clutter",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
    assert len(cell_entities) == 6
    assert len(icon_entities) == 6
    assert 96 <= int(execution["cell_box_width_px"]) <= 136
    assert 96 <= int(execution["cell_box_height_px"]) <= 136

    expected_rotations = list(execution["expected_sequence_rotations_degrees"])
    observed_rotations = list(execution["observed_sequence_rotations_degrees"])
    assert len(observed_rotations) == 6
    mismatch_indices = [index for index, (left, right) in enumerate(zip(observed_rotations, expected_rotations)) if int(left) != int(right)]
    assert mismatch_indices == [3]
    exact_match, plausible_indices = _plausible_violation_indices(observed_rotations)
    assert exact_match is False
    assert plausible_indices == {3}

    scene_colors = {tuple(int(channel) for channel in entity["tint_rgb"]) for entity in icon_entities}
    assert len(scene_colors) == 1
    for entity in icon_entities:
        assert str(entity["icon_id"]) == str(execution["sequence_icon_id"])
        assert int(entity["nominal_size_px"]) >= 48
        assert int(entity["nominal_size_px"]) <= 72
        assert int(entity["rotation_degrees"]) in {0, 90, 180, 270}
        assert isinstance(entity["noise_edits"], list)
        assert str(entity["cell_label_text"]).isdigit()

    violating_boxes = out.evidence_gt.value
    assert violating_boxes == trace["projected_evidence"]["bbox_set"]
    violating_cells = [entity for entity in cell_entities if bool(entity["is_violation"])]
    assert len(violating_cells) == 1
    assert violating_boxes[0] == violating_cells[0]["cell_bbox_xyxy"]
    assert str(violating_cells[0]["cell_label_text"]) == "4"
    assert int(violating_cells[0]["expected_rotation_degrees"]) == 270
    assert int(violating_cells[0]["observed_rotation_degrees"]) != 270


def test_icons_sequence_rotation_violation_prompt_example_matches_contract() -> None:
    task = IconsSequenceRotationViolationTask()
    out = task.generate(
        16111,
        params={"sequence_length": 5, "violation_cell_index": 3},
        max_attempts=200,
    )
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 4}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert len(answer_and_evidence["evidence"]) == 1
    assert answer_and_evidence["answer"] == 4


def test_icons_sequence_rotation_violation_balanced_answer_support_defaults() -> None:
    task = IconsSequenceRotationViolationTask()
    answer_counts: Counter[int] = Counter()
    sequence_lengths: Counter[int] = Counter()
    end_violations = 0
    for index in range(84):
        out = task.generate(
            hash64(16112, "icons_sequence_rotation_violation", index),
            params={"_sampling_index": index},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        answer_index = int(execution["answer_index"])
        sequence_length = int(execution["sequence_length"])
        violation_cell_index = int(execution["violation_cell_index"])
        answer_counts[answer_index] += 1
        sequence_lengths[sequence_length] += 1
        assert 1 <= answer_index <= 7
        assert 5 <= sequence_length <= 7
        assert 0 <= violation_cell_index < sequence_length
        if violation_cell_index in {0, sequence_length - 1}:
            end_violations += 1
    assert set(answer_counts.keys()) == set(range(1, 8))
    assert max(answer_counts.values()) - min(answer_counts.values()) <= 1
    assert set(sequence_lengths.keys()) == {5, 6, 7}
    assert end_violations > 0
