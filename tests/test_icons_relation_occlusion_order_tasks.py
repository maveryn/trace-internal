"""Behavior tests for icon relation occlusion-order task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.icons.relation.occlusion_order import IconsRelationOcclusionOrderTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_icons_relation_occlusion_order_contract_matches_scene() -> None:
    task = IconsRelationOcclusionOrderTask()
    out = task.generate(14710, params={"object_count": 8, "target_count": 3}, max_attempts=200)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_entities = [entity for entity in trace["scene_ir"]["entities"] if str(entity.get("panel")) == "scene"]
    reference_entities = [entity for entity in trace["scene_ir"]["entities"] if str(entity.get("panel")) == "reference"]
    assert len(reference_entities) == 1
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 3
    assert out.evidence_gt.type == "label_set"
    assert out.evidence_gt.value == sorted(out.evidence_gt.value)
    assert len(out.evidence_gt.value) == 3
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
    assert trace["scene_ir"]["scene_kind"] == "icons_reference_grid_occlusion_order_count"
    assert execution["question_format"] == "count_scene_cells_matching_reference_occlusion_order"
    assert execution["task_variant"] == "same_front_to_back_order"
    assert int(execution["object_count"]) == 8
    assert int(execution["target_count"]) == 3
    assert int(execution["distractor_count"]) == 5
    assert 0.0 <= float(out.complexity.complexity_score) <= 1.0
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "spatial_reasoning",
        "ambiguity",
        "clutter",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())

    reference_pair = reference_entities[0]
    reference_order_id = str(execution["reference_order_id"])
    assert str(reference_pair["order_id"]) == reference_order_id
    assert len(scene_entities) == 8
    assert len({str(entity["label"]) for entity in scene_entities}) == 8
    matching_labels = set(str(value) for value in execution["matching_cell_labels"])
    assert matching_labels == set(str(value) for value in out.evidence_gt.value)

    sampled_palette = [tuple(int(channel) for channel in color) for color in trace["render_spec"]["style"]["sampled_palette_rgb"]]
    assert len(sampled_palette) >= 2
    overlap_min, overlap_max = trace["render_spec"]["style"]["overlap_ratio_range"]
    for entity in scene_entities:
        assert str(entity["icon_a_id"]) == str(execution["icon_a_id"])
        assert str(entity["icon_b_id"]) == str(execution["icon_b_id"])
        assert overlap_min <= float(entity["overlap_ratio"]) <= overlap_max
        assert tuple(int(channel) for channel in entity["icon_a_tint_rgb"]) in sampled_palette
        assert tuple(int(channel) for channel in entity["icon_b_tint_rgb"]) in sampled_palette
        assert tuple(int(channel) for channel in entity["icon_a_tint_rgb"]) != tuple(
            int(channel) for channel in entity["icon_b_tint_rgb"]
        )
        is_match = bool(entity["is_match"])
        assert is_match == (str(entity["label"]) in matching_labels)
        if is_match:
            assert str(entity["order_id"]) == reference_order_id
        else:
            assert str(entity["order_id"]) != reference_order_id


def test_icons_relation_occlusion_order_supports_zero_matches() -> None:
    task = IconsRelationOcclusionOrderTask()
    out = task.generate(14711, params={"target_count": 0, "distractor_count": 6}, max_attempts=200)
    assert int(out.answer_gt.value) == 0
    assert out.evidence_gt.value == []


def test_icons_relation_occlusion_order_prompt_example_matches_contract() -> None:
    task = IconsRelationOcclusionOrderTask()
    out = task.generate(14712, params={"object_count": 8, "target_count": 3}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 3}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert answer_and_evidence["evidence"] == ["B", "E", "G"]
    assert answer_and_evidence["answer"] == 3


def test_icons_relation_occlusion_order_balanced_sampling_defaults() -> None:
    task = IconsRelationOcclusionOrderTask()
    object_counts: Counter[int] = Counter()
    target_counts: Counter[int] = Counter()
    distractor_counts: Counter[int] = Counter()
    for index in range(42):
        out = task.generate(
            hash64(14713, "icons_relation_occlusion_order", index),
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
        assert 0 <= target_count <= 6
        assert 1 <= distractor_count <= 6
        assert 2 <= object_count <= 12
        assert object_count == target_count + distractor_count
    assert set(target_counts.keys()) == set(range(0, 7))
    assert set(distractor_counts.keys()) == set(range(1, 7))
    assert max(target_counts.values()) - min(target_counts.values()) <= 1
    assert max(distractor_counts.values()) - min(distractor_counts.values()) <= 2
