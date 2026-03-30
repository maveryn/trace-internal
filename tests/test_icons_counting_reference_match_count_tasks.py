"""Behavior tests for consolidated icon reference-match counting."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.icons.counting.reference_match_count import IconsCountingReferenceMatchCountTask
from trace.tasks import TASK_REGISTRY


EXPECTED_ICONS_TASKS = {
    "task_icons_counting_reference_match_count",
    "task_icons_counting_singleton_type",
    "task_icons_counting_size_relation",
    "task_icons_pattern_structured_violation",
    "task_icons_relation_between_two_anchors_count",
    "task_icons_relation_mirror_symmetry",
    "task_icons_relation_occlusion_order",
    "task_icons_relation_relative_position_type",
    "task_icons_sequence_missing_count",
    "task_icons_transformation_pair_count",
}


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


@pytest.mark.parametrize(
    ("task_variant", "legacy_task_id"),
    (
        ("match_type", "task_icons_counting_type"),
        ("match_color", "task_icons_counting_color"),
        ("match_orientation", "task_icons_counting_orientation"),
        ("match_attribute_binding", "task_icons_counting_attribute_binding"),
    ),
)
def test_icons_counting_reference_match_count_tracks_consolidated_trace(
    task_variant: str,
    legacy_task_id: str,
) -> None:
    task = IconsCountingReferenceMatchCountTask()
    out = task.generate(
        24010,
        params={"task_variant": task_variant, "object_count": 8, "target_count": 3},
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_entities = [entity for entity in trace["scene_ir"]["entities"] if str(entity["panel"]) == "scene"]
    reference = trace["render_map"]["anchors"]["reference_icon"]

    assert trace["scene_ir"]["scene_kind"] == "icons_reference_match_count"
    assert execution["legacy_task_id"] == legacy_task_id
    assert execution["legacy_task_variant"]
    assert execution["scene_variant"] == "reference_scene"
    assert execution["task_variant"] == task_variant
    assert trace["query_spec"]["template_id"] == "icons_counting_v1"
    assert trace["query_spec"]["params"]["legacy_task_id"] == legacy_task_id
    assert trace["query_spec"]["params"]["scene_variant"] == "reference_scene"
    assert trace["query_spec"]["params"]["task_variant"] == task_variant
    assert out.task_variant == task_variant
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 3
    assert execution["task_variant_probabilities"] == trace["query_spec"]["params"]["task_variant_probabilities"]

    matching_indices = {int(value) for value in execution["matching_scene_indices"]}
    assert len(matching_indices) == 3
    assert len(scene_entities) == 8
    if task_variant == "match_type":
        reference_icon_id = str(execution["reference_icon_id"])
        for index, entity in enumerate(scene_entities):
            assert bool(entity["is_match"]) == (int(index) in matching_indices)
            if int(index) in matching_indices:
                assert str(entity["icon_id"]) == reference_icon_id
    elif task_variant == "match_color":
        reference_icon_id = str(execution["reference_icon_id"])
        reference_tint = tuple(int(channel) for channel in execution["reference_tint_rgb"])
        assert all(str(entity["icon_id"]) == reference_icon_id for entity in scene_entities)
        for index, entity in enumerate(scene_entities):
            entity_tint = tuple(int(channel) for channel in entity["tint_rgb"])
            assert bool(entity["is_match"]) == (int(index) in matching_indices)
            if int(index) in matching_indices:
                assert entity_tint == reference_tint
            else:
                assert entity_tint != reference_tint
    elif task_variant == "match_orientation":
        base_icon_id = str(execution["base_icon_id"])
        reference_rotation = int(execution["reference_rotation_degrees"])
        assert str(reference["icon_id"]) == base_icon_id
        for index, entity in enumerate(scene_entities):
            assert str(entity["icon_id"]) == base_icon_id
            assert bool(entity["is_match"]) == (int(index) in matching_indices)
            if int(index) in matching_indices:
                assert int(entity["rotation_degrees"]) == reference_rotation
    else:
        reference_icon_id = str(execution["reference_icon_id"])
        reference_tint = tuple(int(channel) for channel in execution["reference_tint_rgb"])
        reference_rotation = int(execution["reference_rotation_degrees"])
        for index, entity in enumerate(scene_entities):
            assert bool(entity["is_match"]) == (int(index) in matching_indices)
            if int(index) in matching_indices:
                assert str(entity["icon_id"]) == reference_icon_id
                assert tuple(int(channel) for channel in entity["tint_rgb"]) == reference_tint
                assert int(entity["rotation_degrees"]) == reference_rotation


def test_icons_counting_reference_match_count_prompt_example_matches_contract() -> None:
    task = IconsCountingReferenceMatchCountTask()
    out = task.generate(24011, params={"task_variant": "match_type", "object_count": 8, "target_count": 3}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 2}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert len(answer_and_evidence["evidence"]) == 2
    assert answer_and_evidence["answer"] == 2


def test_icons_counting_reference_match_count_balances_variants_by_default() -> None:
    task = IconsCountingReferenceMatchCountTask()
    counts: Counter[str] = Counter()
    for index in range(40):
        out = task.generate(
            hash64(24012, "icons_counting_reference_match_count", index),
            params={"_sampling_index": index},
            max_attempts=200,
        )
        counts[str(out.task_variant)] += 1
    assert set(counts.keys()) == {
        "match_type",
        "match_color",
        "match_orientation",
        "match_attribute_binding",
    }
    assert max(counts.values()) - min(counts.values()) <= 1


def test_icons_counting_reference_match_count_binding_is_harder_than_type_for_same_counts() -> None:
    task = IconsCountingReferenceMatchCountTask()
    type_out = task.generate(
        24016,
        params={"task_variant": "match_type", "object_count": 9, "target_count": 3},
        max_attempts=200,
    )
    binding_out = task.generate(
        24016,
        params={"task_variant": "match_attribute_binding", "object_count": 9, "target_count": 3},
        max_attempts=200,
    )
    assert float(binding_out.complexity.complexity_score) > float(type_out.complexity.complexity_score)


def test_icons_registry_contains_only_ten_active_icons_tasks() -> None:
    active_icons = {task_id for task_id in TASK_REGISTRY if task_id.startswith("task_icons_")}
    assert active_icons == EXPECTED_ICONS_TASKS
