"""Contract tests for symbolic Braille notation tasks."""

from __future__ import annotations

from trace.core.prompts import load_prompt_bundle
from trace.core.prompts.schema import REQUIRED_PROMPT_VARIANTS
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.registry import TASK_REGISTRY
from trace.tasks.symbolic.notation.braille import (
    MATCHING_PATTERN_QUERY_ID,
    MATCHING_PATTERN_TASK_ID,
    RAISED_DOT_COUNT_QUERY_ID,
    RAISED_DOT_COUNT_TASK_ID,
    SCENE_ID,
    SymbolicBrailleMatchingPatternLabelTask,
    SymbolicBrailleRaisedDotCountTask,
)


def test_braille_tasks_are_registered_and_taxonomized() -> None:
    assert TASK_REGISTRY[RAISED_DOT_COUNT_TASK_ID] is SymbolicBrailleRaisedDotCountTask
    assert TASK_REGISTRY[MATCHING_PATTERN_TASK_ID] is SymbolicBrailleMatchingPatternLabelTask
    for task_id in (RAISED_DOT_COUNT_TASK_ID, MATCHING_PATTERN_TASK_ID):
        task = TASK_REGISTRY[task_id]()
        taxonomy = resolve_task_taxonomy(task_id)
        assert task.domain == "symbolic"
        assert task.scene_id == "notation"
        assert taxonomy.domain == "symbolic"
        assert taxonomy.scene_id == SCENE_ID
        assert taxonomy.source_scene_id == "notation"


def test_braille_raised_dot_count_contract() -> None:
    out = SymbolicBrailleRaisedDotCountTask().generate(
        2026060501,
        params={"answer_value": 4, "scene_variant": "clean_card"},
        max_attempts=12,
    )
    trace = out.trace_payload
    target_cell_id = trace["execution_trace"]["braille_metadata"]["target_cell_id"]
    target_positions = trace["execution_trace"]["braille_metadata"]["target_raised_positions"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == RAISED_DOT_COUNT_QUERY_ID
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 4
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == len(target_positions) == 4
    assert trace["render_map"]["annotation_source"] == "dot_centers_px"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["execution_trace"]["annotation_item_ids"] == [target_cell_id]
    assert trace["execution_trace"]["answer_value"] == out.answer_gt.value

    width, height = out.image.size
    for point in out.annotation_gt.value:
        assert len(point) == 2
        assert 0 <= float(point[0]) <= width
        assert 0 <= float(point[1]) <= height


def test_braille_matching_pattern_contract() -> None:
    out = SymbolicBrailleMatchingPatternLabelTask().generate(
        2026060502,
        params={"correct_label": "C", "scene_variant": "notebook_card"},
        max_attempts=12,
    )
    trace = out.trace_payload
    option_patterns = trace["execution_trace"]["braille_metadata"]["option_patterns"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == MATCHING_PATTERN_QUERY_ID
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == "C"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert sorted(out.annotation_gt.value.keys()) == ["reference_cell", "selected_option"]
    assert len(option_patterns) == 6
    assert option_patterns["C"] == trace["execution_trace"]["braille_metadata"]["reference_pattern"]
    assert all(label in option_patterns for label in ("A", "B", "C", "D", "E", "F"))
    assert trace["render_map"]["annotation_source"] == "item_bboxes_px"
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert trace["execution_trace"]["answer_value"] == out.answer_gt.value

    width, height = out.image.size
    for bbox in out.annotation_gt.value.values():
        assert len(bbox) == 4
        assert 0 <= float(bbox[0]) < float(bbox[2]) <= width
        assert 0 <= float(bbox[1]) < float(bbox[3]) <= height


def test_braille_generation_is_deterministic() -> None:
    params = {"scene_variant": "exam_scan", "answer_value": 3}
    out_a = SymbolicBrailleRaisedDotCountTask().generate(2026060599, params=params, max_attempts=12)
    out_b = SymbolicBrailleRaisedDotCountTask().generate(2026060599, params=params, max_attempts=12)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_symbolic_notation_prompt_bundle_supports_braille_queries() -> None:
    bundle = load_prompt_bundle("symbolic", "notation", "symbolic_v0")
    assert "braille_cell" in bundle.scene_templates
    assert len(bundle.task_templates["braille_raised_dot_count"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["braille_matching_pattern_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates[RAISED_DOT_COUNT_QUERY_ID]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates[MATCHING_PATTERN_QUERY_ID]) == REQUIRED_PROMPT_VARIANTS
    assert list(bundle.required_slots_by_key["scene:braille_cell"]) == ["object_description"]
    assert list(bundle.required_slots_by_key[f"query:{RAISED_DOT_COUNT_QUERY_ID}"]) == []
    assert list(bundle.required_slots_by_key[f"query:{MATCHING_PATTERN_QUERY_ID}"]) == []
