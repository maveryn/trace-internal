"""Behavior tests for the icon reflection-match label task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.icons.relation.reflection_match_label import IconsRelationReflectionMatchLabelTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    return json.loads(str(prompt).split(marker, 1)[1].strip())


def test_icons_relation_reflection_match_contract_matches_scene() -> None:
    task = IconsRelationReflectionMatchLabelTask()
    out = task.generate(
        2026051921,
        params={"reflection_query": "diagonal_main_reflection_match", "answer_index": 2},
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_entities = [entity for entity in trace["scene_ir"]["entities"] if str(entity.get("panel")) == "scene"]
    reference_entities = [entity for entity in trace["scene_ir"]["entities"] if str(entity.get("panel")) == "reference"]

    assert len(reference_entities) == 1
    assert len(scene_entities) == 6
    assert out.answer_gt.type == "option_letter"
    assert isinstance(out.answer_gt.value, str)
    assert out.evidence_gt.type == "keyed_bbox_map"
    assert sorted(out.evidence_gt.value.keys()) == ["reference_cell", "selected_option"]
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert trace["scene_ir"]["scene_kind"] == "icons_reference_grid_reflection_match_label"
    assert execution["question_format"] == "select_scene_cell_matching_requested_reference_reflection"
    assert out.query_id == "diagonal_main_reflection_match"
    assert execution["query_id"] == "diagonal_main_reflection_match"
    assert execution["reflection_axis"] == "mirror_diagonal_main"
    assert int(execution["object_count"]) == 6

    reference_cell = reference_entities[0]
    assert str(reference_cell["reflection_axis"]) == "mirror_diagonal_main"
    assert bool(reference_cell["has_vertical_symmetry"]) is False
    assert bool(reference_cell["has_horizontal_symmetry"]) is False
    assert bool(reference_cell["has_diagonal_main_symmetry"]) is False
    assert bool(reference_cell["has_diagonal_anti_symmetry"]) is False
    assert reference_cell["placements"]

    answer_label = str(out.answer_gt.value)
    assert answer_label == str(execution["answer_label"])
    matching = [entity for entity in scene_entities if bool(entity["is_match"])]
    assert len(matching) == 1
    assert str(matching[0]["label"]) == answer_label
    assert bool(matching[0]["is_exact_requested_reflection"]) is True
    assert all(bool(entity["is_exact_requested_reflection"]) is bool(entity["is_match"]) for entity in scene_entities)

    evidence_by_label = {str(entity["label"]): list(entity["cell_bbox_xyxy"]) for entity in scene_entities}
    assert out.evidence_gt.value == {
        "reference_cell": list(reference_cell["cell_bbox_xyxy"]),
        "selected_option": evidence_by_label[answer_label],
    }
    assert trace["projected_evidence"]["type"] == "keyed_bbox_map"
    assert trace["projected_evidence"]["keyed_bbox_map"] == out.evidence_gt.value
    assert trace["witness_symbolic"]["matching_cell_labels"] == [answer_label]
    assert trace["render_spec"]["style"]["text_legibility"]["required_role_count"] >= 2
    assert trace["render_spec"]["style"]["text_legibility"]["failure_count"] == 0
    assert "cell_label_stroke_rgb" in trace["render_spec"]["style"]
    assert 0.0 <= float(out.complexity.complexity_score) <= 1.0


def test_icons_relation_reflection_match_prompt_example_matches_contract() -> None:
    task = IconsRelationReflectionMatchLabelTask()
    out = task.generate(
        2026051922,
        params={"reflection_query": "vertical_reflection_match", "answer_index": 1},
        max_attempts=200,
    )
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": "B"}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert sorted(answer_and_evidence["evidence"].keys()) == ["reference_cell", "selected_option"]
    assert answer_and_evidence["answer"] == "B"


def test_icons_relation_reflection_match_balanced_sampling_defaults() -> None:
    task = IconsRelationReflectionMatchLabelTask()
    query_counts: Counter[str] = Counter()
    answer_counts: Counter[str] = Counter()
    for index in range(24):
        out = task.generate(
            hash64(2026051923, "icons_relation_reflection_match", index),
            params={},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        assert str(out.query_id) == str(execution["query_id"])
        assert int(execution["object_count"]) == 6
        assert len([cell for cell in out.trace_payload["scene_ir"]["entities"] if cell.get("panel") == "scene"]) == 6
        query_counts[str(out.query_id)] += 1
        answer_counts[str(out.answer_gt.value)] += 1
    assert set(query_counts.keys()) == {
        "vertical_reflection_match",
        "horizontal_reflection_match",
        "diagonal_main_reflection_match",
        "diagonal_anti_reflection_match",
    }
    assert sum(query_counts.values()) == 24
    assert len(answer_counts) >= 4
