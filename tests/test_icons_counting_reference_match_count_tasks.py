"""Behavior tests for split icon reference-match counting."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.icons.counting.reference_match_count import IconsReferenceCanvasAttributeMatchCountTask
from trace.tasks import TASK_REGISTRY


EXPECTED_ICONS_TASKS = {
    "task_icons__icon_field__type_frequency_count",
    "task_icons__reference_canvas__attribute_match_count",
    "task_icons__named_field__closer_to_reference_count",
    "task_icons__named_field__shape_attribute_boolean_count",
    "task_icons__named_field__shape_count",
    "task_icons__named_field__shape_counterfactual_count",
    "task_icons__named_field__shape_pair_total_count",
    "task_icons__named_field__shape_pair_difference_count",
    "task_icons__named_field__region_shape_count",
    "task_icons__venn_field__venn_region_shape_count",
    "task_icons__paired_canvas__panel_difference_count",
    "task_icons__paired_canvas__panel_exact_match_count",
    "task_icons__reference_canvas__size_relation_count",
    "task_icons__pattern_grid__color_pattern_violation_index",
    "task_icons__pattern_grid__size_pattern_violation_index",
    "task_icons__sequence_strip__rotation_sequence_violation_index",
    "task_icons__two_anchor__between_anchors_count",
    "task_icons__mirror_grid__mirror_symmetry_count",
    "task_icons__paired_canvas__original_attribute_label",
    "task_icons__named_field__reference_distance_rank_label",
    "task_icons__overlap_grid__occlusion_order_count",
    "task_icons__paired_canvas__panel_movement_direction_count",
    "task_icons__mirror_grid__reflection_match_label",
    "task_icons__reference_canvas__anchor_position_count",
    "task_icons__sequence_strip__missing_count_value",
    "task_icons__paired_canvas__panel_attribute_change_count",
    "task_icons__pair_grid__pair_attribute_rule_count",
    "task_icons__pair_grid__pair_geometric_transform_count",
}


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


@pytest.mark.parametrize(
    ("task_cls", "query_variant", "expected_scene_kind"),
    (
        (
            IconsReferenceCanvasAttributeMatchCountTask,
            "match_type",
            "icons_reference_attribute_match_count",
        ),
        (
            IconsReferenceCanvasAttributeMatchCountTask,
            "match_color",
            "icons_reference_attribute_match_count",
        ),
        (
            IconsReferenceCanvasAttributeMatchCountTask,
            "match_rotation",
            "icons_reference_attribute_match_count",
        ),
        (
            IconsReferenceCanvasAttributeMatchCountTask,
            "match_type_color_rotation",
            "icons_reference_attribute_match_count",
        ),
    ),
)
def test_icons_counting_attribute_match_count_tracks_consolidated_trace(
    task_cls,
    query_variant: str,
    expected_scene_kind: str,
) -> None:
    task = task_cls()
    out = task.generate(
        24010,
        params={"query_variant": query_variant, "object_count": 8, "target_count": 3},
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_entities = [entity for entity in trace["scene_ir"]["entities"] if str(entity["panel"]) == "scene"]
    reference = trace["render_map"]["anchors"]["reference_icon"]

    assert trace["scene_ir"]["scene_kind"] == expected_scene_kind
    assert "source_task_id" not in execution
    assert "source_query_variant" not in execution
    assert execution["scene_variant"] == "reference_scene"
    assert execution["query_variant"] == "default"
    assert execution["query_id"] == query_variant
    assert trace["query_spec"]["template_id"] == "icons_counting_v0"
    assert trace["query_spec"]["params"]["scene_variant"] == "reference_scene"
    assert trace["query_spec"]["params"]["query_variant"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == query_variant
    assert out.query_variant == "default"
    assert out.query_id == query_variant
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 3
    assert execution["query_variant_probabilities"] == trace["query_spec"]["params"]["query_variant_probabilities"]

    matching_indices = {int(value) for value in execution["matching_scene_indices"]}
    assert len(matching_indices) == 3
    assert len(scene_entities) == 8
    if query_variant == "match_type":
        reference_icon_id = str(execution["reference_icon_id"])
        for index, entity in enumerate(scene_entities):
            assert bool(entity["is_match"]) == (int(index) in matching_indices)
            if int(index) in matching_indices:
                assert str(entity["icon_id"]) == reference_icon_id
    elif query_variant == "match_color":
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
    elif query_variant == "match_rotation":
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


def test_icons_counting_attribute_match_count_prompt_example_matches_contract() -> None:
    task = IconsReferenceCanvasAttributeMatchCountTask()
    out = task.generate(24011, params={"query_variant": "match_type", "object_count": 8, "target_count": 3}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 2}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert len(answer_and_evidence["evidence"]) == 2
    assert answer_and_evidence["answer"] == 2


def test_icons_counting_single_attribute_match_count_balances_variants_by_default() -> None:
    task = IconsReferenceCanvasAttributeMatchCountTask()
    counts: Counter[str] = Counter()
    for index in range(30):
        out = task.generate(
            hash64(24012, "icons_reference_canvas_attribute_match_count", index),
            params={},
            max_attempts=200,
        )
        counts[str(out.query_id)] += 1
    assert set(counts.keys()) == {
        "match_type",
        "match_color",
        "match_rotation",
        "match_type_color_rotation",
    }
    assert sum(counts.values()) == 30


def test_icons_counting_multi_attribute_match_count_is_harder_than_type_for_same_counts() -> None:
    task = IconsReferenceCanvasAttributeMatchCountTask()
    type_out = task.generate(
        24016,
        params={"query_variant": "match_type", "object_count": 9, "target_count": 3},
        max_attempts=200,
    )
    binding_out = task.generate(
        24016,
        params={"query_variant": "match_type_color_rotation", "object_count": 9, "target_count": 3},
        max_attempts=200,
    )
    assert float(binding_out.complexity.complexity_score) > float(type_out.complexity.complexity_score)


def test_icons_registry_contains_only_active_icons_tasks() -> None:
    active_icons = {task_id for task_id in TASK_REGISTRY if task_id.startswith("task_icons__")}
    assert active_icons == EXPECTED_ICONS_TASKS
