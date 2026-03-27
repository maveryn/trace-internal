"""Behavior tests for icon counting orientation task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.icons.counting.orientation import IconsCountingOrientationTask


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


def test_icons_counting_orientation_contract_matches_scene() -> None:
    task = IconsCountingOrientationTask()
    out = task.generate(
        14030,
        params={"object_count": 8, "target_count": 3, "pool_manifest": "non_symmetry.txt"},
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_entities = [
        entity for entity in trace["scene_ir"]["entities"] if str(entity["panel"]) == "scene"
    ]
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 3
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 3
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert trace["scene_ir"]["scene_kind"] == "icons_reference_counting_orientation"
    assert execution["question_format"] == "count_matching_scene_icons_by_reference"
    assert int(execution["object_count"]) == 8
    assert int(execution["target_count"]) == 3
    assert int(execution["distractor_count"]) == 5
    sampled_palette = [tuple(int(channel) for channel in color) for color in trace["render_spec"]["style"]["sampled_palette_rgb"]]
    assert 8 <= len(sampled_palette) <= 12
    assert list(trace["render_spec"]["style"]["icon_noise_edit_count_range"]) == [0, 2]
    assert float(trace["render_spec"]["style"]["scene_max_overlap_fraction"]) == 0.10

    base_icon_id = str(execution["base_icon_id"])
    reference_rotation = int(execution["reference_rotation_degrees"])
    scene_rotations = [int(value) for value in execution["scene_rotations_degrees"]]
    matching_indices = {int(value) for value in execution["matching_scene_indices"]}
    assert len(scene_entities) == 8
    reference_tint = tuple(int(channel) for channel in trace["render_map"]["anchors"]["reference_icon"]["tint_rgb"])
    assert reference_tint in sampled_palette
    assert isinstance(trace["render_map"]["anchors"]["reference_icon"]["noise_edits"], list)
    for index, entity in enumerate(scene_entities):
        assert str(entity["icon_id"]) == base_icon_id
        is_match = bool(entity["is_match"])
        assert is_match == (int(index) in matching_indices)
        assert tuple(int(channel) for channel in entity["tint_rgb"]) in sampled_palette
        assert isinstance(entity["noise_edits"], list)
        if is_match:
            assert scene_rotations[index] == reference_rotation
        else:
            assert scene_rotations[index] != reference_rotation
    for left_index, left in enumerate(scene_entities):
        for right in scene_entities[left_index + 1 :]:
            assert _overlap_fraction_smaller(left["bbox_xyxy"], right["bbox_xyxy"]) <= 0.10 + 1e-6


def test_icons_counting_orientation_supports_zero_matches() -> None:
    task = IconsCountingOrientationTask()
    out = task.generate(
        14033,
        params={"object_count": 7, "target_count": 0, "pool_manifest": "non_symmetry.txt"},
        max_attempts=200,
    )
    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []


def test_icons_counting_orientation_prompt_example_matches_contract() -> None:
    task = IconsCountingOrientationTask()
    out = task.generate(14031, params={"object_count": 8, "target_count": 3}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 3}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert len(answer_and_evidence["evidence"]) == 3
    assert answer_and_evidence["answer"] == 3


def test_icons_counting_orientation_balanced_sampling_defaults() -> None:
    task = IconsCountingOrientationTask()
    object_counts: Counter[int] = Counter()
    target_counts: Counter[int] = Counter()
    distractor_counts: Counter[int] = Counter()
    for index in range(60):
        out = task.generate(
            hash64(14032, "icons_counting_orientation", index),
            params={"_sampling_index": index},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        object_count = int(execution["object_count"])
        target_count = int(execution["target_count"])
        distractor_count = int(execution["distractor_count"])
        object_counts[object_count] += 1
        target_counts[target_count] += 1
        distractor_counts[distractor_count] += 1
        assert 0 <= target_count <= 10
        assert 1 <= distractor_count <= 10
        assert int(object_count) == int(target_count) + int(distractor_count)
    assert min(object_counts.keys()) >= 1
    assert max(object_counts.keys()) <= 20
    assert set(target_counts.keys()) == set(range(0, 11))
    assert set(distractor_counts.keys()) == set(range(1, 11))
    assert max(target_counts.values()) - min(target_counts.values()) <= 1
    assert max(distractor_counts.values()) - min(distractor_counts.values()) <= 1
