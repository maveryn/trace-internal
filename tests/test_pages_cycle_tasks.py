"""Behavior tests for pages cycle tasks."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from trace.core.seed import hash64
from trace.tasks.pages.cycle.offset_stage_label import PagesCycleOffsetStageLabelTask
from tests.helpers import extract_prompt_json_example


def _bboxes_overlap(left, right) -> bool:
    return not (
        float(left[2]) <= float(right[0])
        or float(left[0]) >= float(right[2])
        or float(left[3]) <= float(right[1])
        or float(left[1]) >= float(right[3])
    )


def test_pages_cycle_prompt_bundle_does_not_name_direction() -> None:
    bundle_path = Path("prompts/pages/cycle/pages_cycle_v0.json")
    bundle_text = bundle_path.read_text(encoding="utf-8")
    bundle = json.loads(bundle_text)

    assert "clockwise" not in bundle_text.lower()
    assert "counterclockwise" not in bundle_text.lower()
    assert bundle["scene_templates"]["cycle_diagram"]


def test_pages_cycle_offset_stage_label_contract_matches_answer_stage_bbox() -> None:
    task = PagesCycleOffsetStageLabelTask()
    query_relationships = ("after", "before")
    cycle_directions = ("clockwise", "counterclockwise")

    for relationship_index, query_relationship in enumerate(query_relationships):
        for direction_index, cycle_direction in enumerate(cycle_directions):
            seed = 61400 + (10 * relationship_index) + direction_index
            out = task.generate(
                seed,
                params={
                    "query_id": "offset_stage_label",
                    "query_relationship": query_relationship,
                    "scene_variant": "cycle_ring",
                    "cycle_direction": cycle_direction,
                },
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            annotation_bboxes = [[float(value) for value in bbox] for bbox in out.annotation_gt.value]

            assert out.answer_gt.type == "string"
            assert out.annotation_gt.type == "bbox_set"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
            assert str(out.query_id) == f"{query_relationship}_offset_stage_label"
            assert str(execution["query_id"]) == f"{query_relationship}_offset_stage_label"
            assert str(execution["query_relationship"]) == str(query_relationship)
            assert str(execution["scene_variant"]) == "cycle_ring"
            assert str(execution["question_format"]) == "cycle_offset_stage_label"
            assert str(execution["view_family"]) == "cycle_diagram"
            assert str(execution["direction"]) == str(cycle_direction)
            assert "clockwise" not in out.prompt.lower()
            assert "Clockwise" not in {str(entity.get("text", "")) for entity in trace["scene_ir"]["entities"]}
            assert "direction_badge_bbox_px" not in render_map
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert len(annotation_bboxes) == 1
            assert trace["projected_annotation"]["bbox_set"] == annotation_bboxes
            assert str(out.answer_gt.value) == str(execution["answer_stage_label"])

            expected_bbox = [
                float(value)
                for value in render_map["stage_bboxes_px"][str(execution["answer_stage_bbox_id"])]
            ]
            assert annotation_bboxes == [expected_bbox]
            assert [str(item) for item in execution["supporting_stage_bbox_ids"]] == [str(execution["answer_stage_bbox_id"])]
            assert len(execution["stage_specs"]) == int(execution["stage_count"])
            assert len(render_map["stage_bboxes_px"]) == int(execution["stage_count"])
            assert len(render_map["edge_bboxes_px"]) == int(execution["stage_count"])


def test_pages_cycle_prompt_examples_match_variant_contract() -> None:
    task = PagesCycleOffsetStageLabelTask()
    expected_answer_and_annotation = {"annotation": [[747, 242, 869, 300]], "answer": "Mina"}
    expected_answer_only = {"answer": "Mina"}

    for index, query_relationship in enumerate(("after", "before"), start=61460):
        out = task.generate(
            index,
            params={"query_id": "offset_stage_label", "query_relationship": query_relationship},
            max_attempts=10,
        )
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation == expected_answer_and_annotation
        assert answer_only == expected_answer_only


def test_pages_cycle_uses_paragraph_context_side_notes() -> None:
    task = PagesCycleOffsetStageLabelTask()
    out = task.generate(61400, params={}, max_attempts=10)
    trace = out.trace_payload
    context_layer = trace["render_spec"]["context_text_layer"]
    context_elements = [dict(element) for element in context_layer["elements"]]
    panel_bbox = trace["render_map"]["panel_bbox_px"]

    assert context_layer["layout_spec"]["density"] == "two_side_notes"
    assert int(context_layer["layout_spec"]["side_notes_added"]) == 2
    assert any(str(element["role"]) == "side_note_body" for element in context_elements)
    assert any(
        str(element["role"]) == "side_note_body"
        and str(element["manifest_path"]) == "paragraphs/context_template_blocks.txt"
        for element in context_elements
    )
    assert all(not _bboxes_overlap(element["bbox_xyxy"], panel_bbox) for element in context_elements)
    assert "context_text_bboxes_px" in trace["render_map"]


def test_pages_cycle_offset_stage_label_is_deterministic() -> None:
    task = PagesCycleOffsetStageLabelTask()
    params = {"query_id": "offset_stage_label", "query_relationship": "before", "scene_variant": "cycle_ring"}
    out_a = task.generate(61510, params=params, max_attempts=10)
    out_b = task.generate(61510, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_pages_cycle_balanced_sampling_defaults_cover_variants() -> None:
    task = PagesCycleOffsetStageLabelTask()
    query_ids: Counter[str] = Counter()
    query_relationships: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    cycle_directions: Counter[str] = Counter()
    relationship_direction_pairs: Counter[tuple[str, str]] = Counter()

    for index in range(48):
        out = task.generate(hash64(61540, "pages_cycle", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        query_ids[str(execution["query_id"])] += 1
        query_relationships[str(execution["query_relationship"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        cycle_directions[str(execution["direction"])] += 1
        relationship_direction_pairs[(str(execution["query_relationship"]), str(execution["direction"]))] += 1

    assert set(query_ids.keys()) == {"after_offset_stage_label", "before_offset_stage_label"}
    assert set(query_relationships.keys()) == {"after", "before"}
    assert set(scene_variants.keys()) == {"cycle_ring"}
    assert set(cycle_directions.keys()) == {"clockwise", "counterclockwise"}
    assert set(relationship_direction_pairs.keys()) == {
        ("after", "clockwise"),
        ("after", "counterclockwise"),
        ("before", "clockwise"),
        ("before", "counterclockwise"),
    }


def test_pages_cycle_uses_short_names_and_respects_stage_and_step_ranges() -> None:
    task = PagesCycleOffsetStageLabelTask()
    out = task.generate(
        61590,
        params={"query_id": "offset_stage_label", "query_relationship": "after", "scene_variant": "cycle_ring"},
        max_attempts=10,
    )
    execution = out.trace_payload["execution_trace"]
    stage_count = int(execution["stage_count"])
    step_count = int(execution["step_count"])

    assert 5 <= stage_count <= 12
    assert 2 <= step_count <= stage_count - 1
    for stage_spec in execution["stage_specs"]:
        label = str(stage_spec["stage_label"])
        assert " " not in label
        assert 2 <= len(label) <= 8

    query_index = int(execution["query_stage_index"])
    answer_index = int(execution["answer_stage_index"])
    direction_delta = 1 if str(execution["direction"]) == "clockwise" else -1
    assert answer_index == (query_index + (direction_delta * step_count)) % stage_count


def test_pages_cycle_before_relationship_is_harder_than_after_relationship() -> None:
    task = PagesCycleOffsetStageLabelTask()
    after = task.generate(
        61620,
        params={"query_id": "offset_stage_label", "query_relationship": "after", "scene_variant": "cycle_ring"},
        max_attempts=10,
    )
    before = task.generate(
        61620,
        params={"query_id": "offset_stage_label", "query_relationship": "before", "scene_variant": "cycle_ring"},
        max_attempts=10,
    )

    assert float(before.complexity.complexity_components["reasoning_load"]) > float(
        after.complexity.complexity_components["reasoning_load"]
    )


def test_pages_cycle_source_before_after_query_id_aliases_query_relationship() -> None:
    task = PagesCycleOffsetStageLabelTask()
    out = task.generate(61650, params={"query_id": "before_k_steps", "scene_variant": "cycle_ring"}, max_attempts=10)
    execution = out.trace_payload["execution_trace"]

    assert str(out.query_id) == "before_offset_stage_label"
    assert str(execution["query_id"]) == "before_offset_stage_label"
    assert str(execution["query_relationship"]) == "before"
