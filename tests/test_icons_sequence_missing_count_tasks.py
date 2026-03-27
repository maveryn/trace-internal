"""Behavior tests for icon sequence missing-count task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.icons.sequence.missing_count import IconsSequenceMissingCountTask


def _overlap_fraction_smaller(left: list[int], right: list[int]) -> float:
    ix0 = max(int(left[0]), int(right[0]))
    iy0 = max(int(left[1]), int(right[1]))
    ix1 = min(int(left[2]), int(right[2]))
    iy1 = min(int(left[3]), int(right[3]))
    inter = max(0, ix1 - ix0) * max(0, iy1 - iy0)
    if inter <= 0:
        return 0.0
    left_area = max(1, int(left[2]) - int(left[0])) * max(1, int(left[3]) - int(left[1]))
    right_area = max(1, int(right[2]) - int(right[0])) * max(1, int(right[3]) - int(right[1]))
    return float(inter) / float(min(left_area, right_area))


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_icons_sequence_missing_count_contract_matches_scene() -> None:
    task = IconsSequenceMissingCountTask()
    out = task.generate(
        15110,
        params={"sequence_length": 5, "missing_cell_index": 2, "target_count": 4, "step_delta": 1},
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    entities = trace["scene_ir"]["entities"]
    reference_entities = [entity for entity in entities if str(entity["entity_kind"]) == "reference_icon"]
    cell_entities = [entity for entity in entities if str(entity["entity_kind"]) == "sequence_cell"]
    icon_entities = [entity for entity in entities if str(entity["entity_kind"]) == "scene_icon"]

    assert len(reference_entities) == 1
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 4
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert trace["scene_ir"]["scene_kind"] == "icons_reference_sequence_missing_count"
    assert execution["question_format"] == "infer_missing_sequence_count"
    assert execution["task_variant"] == "arithmetic_progression"
    assert int(execution["sequence_length"]) == 5
    assert int(execution["missing_cell_index"]) == 2
    assert int(execution["step_delta"]) == 1
    assert execution["full_sequence_counts"] == [2, 3, 4, 5, 6]
    assert len(cell_entities) == 5
    assert len(icon_entities) == 16

    reference_entity = reference_entities[0]
    assert 0 <= int(reference_entity["rotation_degrees"]) < 360
    reference_color = tuple(int(channel) for channel in reference_entity["tint_rgb"])
    scene_icons_by_cell: dict[int, list[dict]] = {}
    for entity in icon_entities:
        scene_icons_by_cell.setdefault(int(entity["cell_index"]), []).append(entity)
        assert str(entity["icon_id"]) == str(reference_entity["icon_id"])
        assert tuple(int(channel) for channel in entity["tint_rgb"]) == reference_color
        assert int(entity["nominal_size_px"]) >= 24
        assert int(entity["nominal_size_px"]) <= 40
        assert int(entity["rotation_degrees"]) in {0, 90, 180, 270}
        assert isinstance(entity["noise_edits"], list)

    missing_boxes = out.evidence_gt.value
    assert missing_boxes == trace["projected_evidence"]["bbox_set"]
    missing_cell = [entity for entity in cell_entities if bool(entity["is_missing"])]
    assert len(missing_cell) == 1
    assert missing_boxes[0] == missing_cell[0]["cell_bbox_xyxy"]
    assert int(missing_cell[0]["cell_index"]) == 2
    assert int(missing_cell[0]["target_icon_count"]) == 4
    assert int(missing_cell[0]["rendered_icon_count"]) == 0

    expected_visible_counts = {0: 2, 1: 3, 3: 5, 4: 6}
    for cell in cell_entities:
        cell_index = int(cell["cell_index"])
        if bool(cell["is_missing"]):
            continue
        rendered_icons = scene_icons_by_cell.get(cell_index, [])
        assert len(rendered_icons) == int(cell["target_icon_count"])
        assert len(rendered_icons) == expected_visible_counts[cell_index]
        for left_index, left in enumerate(rendered_icons):
            for right in rendered_icons[left_index + 1 :]:
                assert _overlap_fraction_smaller(left["bbox_xyxy"], right["bbox_xyxy"]) <= 0.20 + 1e-6


def test_icons_sequence_missing_count_supports_end_missing_cell_and_zero_answer() -> None:
    task = IconsSequenceMissingCountTask()
    out = task.generate(
        15111,
        params={"sequence_length": 4, "missing_cell_index": 3, "target_count": 0, "step_delta": -1},
        max_attempts=200,
    )
    execution = out.trace_payload["execution_trace"]
    assert int(out.answer_gt.value) == 0
    assert len(out.evidence_gt.value) == 1
    assert int(execution["missing_cell_index"]) == 3
    assert execution["full_sequence_counts"] == [3, 2, 1, 0]


def test_icons_sequence_missing_count_prompt_example_matches_contract() -> None:
    task = IconsSequenceMissingCountTask()
    out = task.generate(
        15112,
        params={"sequence_length": 6, "missing_cell_index": 5, "target_count": 7, "step_delta": 1},
        max_attempts=200,
    )
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 5}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert len(answer_and_evidence["evidence"]) == 1
    assert answer_and_evidence["answer"] == 5


def test_icons_sequence_missing_count_balanced_sampling_defaults() -> None:
    task = IconsSequenceMissingCountTask()
    target_counts: Counter[int] = Counter()
    sequence_lengths: Counter[int] = Counter()
    end_missing_count = 0
    for index in range(66):
        out = task.generate(
            hash64(15113, "icons_sequence_missing_count", index),
            params={"_sampling_index": index},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        target_count = int(execution["target_count"])
        sequence_length = int(execution["sequence_length"])
        missing_cell_index = int(execution["missing_cell_index"])
        target_counts[target_count] += 1
        sequence_lengths[sequence_length] += 1
        assert 0 <= target_count <= 10
        assert 4 <= sequence_length <= 6
        assert 0 <= missing_cell_index < sequence_length
        if missing_cell_index in {0, sequence_length - 1}:
            end_missing_count += 1
    assert set(target_counts.keys()) == set(range(0, 11))
    assert max(target_counts.values()) - min(target_counts.values()) <= 1
    assert sequence_lengths == Counter({4: 22, 5: 22, 6: 22})
    assert end_missing_count > 0
