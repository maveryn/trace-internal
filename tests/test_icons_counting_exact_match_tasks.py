"""Behavior tests for icon exact-match counting task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.icons.counting.exact_match import IconsCountingExactMatchTask


_HARD_DISTRACTOR_CATEGORIES = {
    "same_type_color",
    "same_type_orientation",
    "same_color_orientation",
}
_ALL_DISTRACTOR_CATEGORIES = _HARD_DISTRACTOR_CATEGORIES | {
    "same_type_only",
    "same_color_only",
    "same_orientation_only",
    "no_queried_attributes",
}


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


def test_icons_counting_exact_match_contract_matches_scene() -> None:
    task = IconsCountingExactMatchTask()
    out = task.generate(
        14110,
        params={"object_count": 9, "target_count": 3, "pool_manifest": "non_symmetry.txt"},
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
    assert isinstance(out.evidence_gt.value, list)
    assert len(out.evidence_gt.value) == 3
    assert out.evidence_gt.value == sorted(out.evidence_gt.value, key=lambda box: (box[1], box[0], box[3], box[2]))
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
    assert trace["scene_ir"]["scene_kind"] == "icons_reference_counting_exact_match"
    assert execution["question_format"] == "count_exact_reference_match_by_attributes"
    assert int(execution["object_count"]) == 9
    assert int(execution["target_count"]) == 3
    assert int(execution["distractor_count"]) == 6
    assert len(scene_entities) == 9
    sampled_palette = [tuple(int(channel) for channel in color) for color in trace["render_spec"]["style"]["sampled_palette_rgb"]]
    assert 4 <= len(sampled_palette) <= 6
    assert float(trace["render_spec"]["style"]["min_color_distance"]) == 60.0
    assert list(trace["render_spec"]["style"]["icon_noise_edit_count_range"]) == [0, 2]
    assert float(trace["render_spec"]["style"]["scene_max_overlap_fraction"]) == 0.10

    reference_icon_id = str(execution["reference_icon_id"])
    reference_tint = tuple(int(channel) for channel in execution["reference_tint_rgb"])
    reference_rotation = int(execution["reference_rotation_degrees"])
    matching_indices = {int(value) for value in execution["matching_scene_indices"]}
    assert len(matching_indices) == 3
    hard_distractor_categories = 0
    for index, entity in enumerate(scene_entities):
        is_match = bool(entity["is_match"])
        same_type = bool(entity["same_type_as_reference"])
        same_color = bool(entity["same_color_as_reference"])
        same_orientation = bool(entity["same_orientation_as_reference"])
        category = str(entity["attribute_match_category"])
        assert is_match == (int(index) in matching_indices)
        assert tuple(int(channel) for channel in entity["tint_rgb"]) in sampled_palette
        assert isinstance(entity["noise_edits"], list)
        assert str(entity["icon_id"]) == reference_icon_id if same_type else str(entity["icon_id"]) != reference_icon_id
        assert tuple(int(channel) for channel in entity["tint_rgb"]) == reference_tint if same_color else tuple(int(channel) for channel in entity["tint_rgb"]) != reference_tint
        assert int(entity["rotation_degrees"]) == reference_rotation if same_orientation else int(entity["rotation_degrees"]) != reference_rotation
        if is_match:
            assert category == "exact_match"
            assert same_type and same_color and same_orientation
        else:
            assert category in _ALL_DISTRACTOR_CATEGORIES
            assert not (same_type and same_color and same_orientation)
            if category in _HARD_DISTRACTOR_CATEGORIES:
                hard_distractor_categories += 1
    assert hard_distractor_categories >= 2
    for left_index, left in enumerate(scene_entities):
        for right in scene_entities[left_index + 1 :]:
            assert _overlap_fraction_smaller(left["bbox_xyxy"], right["bbox_xyxy"]) <= 0.10 + 1e-6


def test_icons_counting_exact_match_supports_zero_matches() -> None:
    task = IconsCountingExactMatchTask()
    out = task.generate(
        14113,
        params={"object_count": 7, "target_count": 0, "pool_manifest": "non_symmetry.txt"},
        max_attempts=200,
    )
    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []


def test_icons_counting_exact_match_prompt_example_matches_contract() -> None:
    task = IconsCountingExactMatchTask()
    out = task.generate(14111, params={"object_count": 8, "target_count": 3}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 2}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert len(answer_and_evidence["evidence"]) == 2
    assert answer_and_evidence["answer"] == 2


def test_icons_counting_exact_match_balanced_sampling_defaults() -> None:
    task = IconsCountingExactMatchTask()
    object_counts: Counter[int] = Counter()
    target_counts: Counter[int] = Counter()
    distractor_counts: Counter[int] = Counter()
    for index in range(60):
        out = task.generate(
            hash64(14112, "icons_counting_exact_match", index),
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
