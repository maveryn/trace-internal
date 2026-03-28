"""Behavior tests for icon singleton-type counting task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.icons.counting.singleton_type import IconsCountingSingletonTypeTask


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


def test_icons_counting_singleton_type_contract_matches_scene() -> None:
    task = IconsCountingSingletonTypeTask()
    out = task.generate(
        18310,
        params={"object_count": 9, "target_count": 3},
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_entities = trace["scene_ir"]["entities"]
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 3
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 3
    assert out.evidence_gt.value == sorted(out.evidence_gt.value, key=lambda box: (box[1], box[0], box[3], box[2]))
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
    assert trace["scene_ir"]["scene_kind"] == "icons_singleton_type_counting"
    assert execution["question_format"] == "count_singleton_type_icons"
    assert execution["scene_variant"] == "single_panel_scene"
    assert int(execution["object_count"]) == 9
    assert int(execution["target_count"]) == 3
    assert int(execution["repeated_type_count"]) >= 1
    assert int(execution["distinct_type_count"]) >= 4
    assert len(scene_entities) == 9
    assert "reference_panel_xyxy" not in trace["render_spec"]["panel_geometry"]
    sampled_palette = [tuple(int(channel) for channel in color) for color in trace["render_spec"]["style"]["sampled_palette_rgb"]]
    assert 8 <= len(sampled_palette) <= 12
    assert list(trace["render_spec"]["style"]["icon_noise_edit_count_range"]) == [0, 2]
    assert float(trace["render_spec"]["style"]["scene_max_overlap_fraction"]) == 0.10
    assert 0.0 <= float(out.complexity.complexity_score) <= 1.0
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "semantic_match",
        "ambiguity",
        "clutter",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())

    singleton_indices = {int(value) for value in execution["singleton_indices"]}
    type_frequencies = {str(key): int(value) for key, value in execution["type_frequencies"].items()}
    assert len(singleton_indices) == 3
    assert sum(1 for value in execution["scene_icon_ids"] if type_frequencies[str(value)] == 1) == 3
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    evidence_boxes = {tuple(int(value) for value in box) for box in out.evidence_gt.value}
    for index, entity in enumerate(scene_entities):
        icon_id = str(entity["icon_id"])
        assert int(entity["type_frequency"]) == int(type_frequencies[icon_id])
        assert bool(entity["is_singleton_type"]) == (int(index) in singleton_indices)
        assert tuple(int(channel) for channel in entity["tint_rgb"]) in sampled_palette
        assert int(entity["rotation_degrees"]) in {0, 90, 180, 270}
        assert isinstance(entity["noise_edits"], list)
        if bool(entity["is_singleton_type"]):
            assert tuple(int(value) for value in entity["bbox_xyxy"]) in evidence_boxes
            assert int(type_frequencies[icon_id]) == 1
        else:
            assert int(type_frequencies[icon_id]) >= 2
    for left_index, left in enumerate(scene_entities):
        for right in scene_entities[left_index + 1 :]:
            assert _overlap_fraction_smaller(left["bbox_xyxy"], right["bbox_xyxy"]) <= 0.10 + 1e-6


def test_icons_counting_singleton_type_supports_zero_singletons() -> None:
    task = IconsCountingSingletonTypeTask()
    out = task.generate(
        18311,
        params={"object_count": 8, "target_count": 0},
        max_attempts=200,
    )
    execution = out.trace_payload["execution_trace"]
    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []
    assert execution["singleton_indices"] == []


def test_icons_counting_singleton_type_prompt_example_matches_contract() -> None:
    task = IconsCountingSingletonTypeTask()
    out = task.generate(18312, params={"object_count": 9, "target_count": 2}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 2}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert len(answer_and_evidence["evidence"]) == 2
    assert answer_and_evidence["answer"] == 2


def test_icons_counting_singleton_type_balanced_sampling_defaults() -> None:
    task = IconsCountingSingletonTypeTask()
    object_counts: Counter[int] = Counter()
    target_counts: Counter[int] = Counter()
    for index in range(60):
        out = task.generate(
            hash64(18313, "icons_counting_singleton_type", index),
            params={"_sampling_index": index},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        object_count = int(execution["object_count"])
        target_count = int(execution["target_count"])
        object_counts[object_count] += 1
        target_counts[target_count] += 1
        assert 6 <= object_count <= 15
        assert 0 <= target_count <= 5
    assert set(target_counts.keys()) == set(range(0, 6))
    assert max(target_counts.values()) - min(target_counts.values()) <= 1
    assert min(object_counts.keys()) >= 6
    assert max(object_counts.keys()) <= 15
