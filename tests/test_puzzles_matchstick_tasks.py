"""Behavior tests for matchstick puzzle tasks."""

from __future__ import annotations

from trace.tasks.puzzles.logic.matchstick_arrangement import (
    ENDPOINT_QUERY_IDS,
    NUMBER_QUERY_IDS,
    SCENE_VARIANTS,
    PuzzlesLogicMatchstickLooseEndpointExtremumLabelTask,
    PuzzlesLogicMatchstickNumberTransformLabelTask,
)
from tests.helpers import extract_prompt_json_example


def test_matchstick_number_transform_uses_keyed_source_and_option_evidence() -> None:
    task = PuzzlesLogicMatchstickNumberTransformLabelTask()

    for index, (query_id, scene_variant) in enumerate(zip(NUMBER_QUERY_IDS * 3, SCENE_VARIANTS)):
        out = task.generate(
            31000 + index,
            params={"query_id": query_id, "scene_variant": scene_variant},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        evidence = {
            str(key): [float(value) for value in bbox]
            for key, bbox in out.evidence_gt.value.items()
        }

        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "keyed_bbox_map"
        assert set(evidence) == {"source_number", "selected_option"}
        assert trace["projected_evidence"]["type"] == "keyed_bbox_map"
        assert trace["projected_evidence"]["keyed_bbox_map"] == evidence
        assert trace["projected_evidence"]["pixel_keyed_bbox_map"] == evidence
        assert execution["evidence_role_item_ids"] == {
            "source_number": "source_panel",
            "selected_option": f"option_{out.answer_gt.value}",
        }
        assert execution["supporting_item_ids"] == [
            "source_panel",
            f"option_{out.answer_gt.value}",
        ]
        assert evidence["source_number"] == [
            float(value) for value in render_map["item_bboxes_px"]["source_panel"]
        ]
        assert evidence["selected_option"] == [
            float(value) for value in render_map["item_bboxes_px"][f"option_{out.answer_gt.value}"]
        ]
        assert render_map["evidence_source"] == "keyed_item_bboxes_px"
        assert render["text_style"]["font"]["source"] == "global_font_pool"
        assert render["text_style"]["font"]["font_family"]


def test_matchstick_endpoint_extremum_keeps_single_selected_option_evidence() -> None:
    task = PuzzlesLogicMatchstickLooseEndpointExtremumLabelTask()

    for index, query_id in enumerate(ENDPOINT_QUERY_IDS):
        out = task.generate(
            31100 + index,
            params={"query_id": query_id, "scene_variant": SCENE_VARIANTS[index]},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        evidence = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "bbox_set"
        assert len(evidence) == 1
        assert trace["projected_evidence"]["type"] == "bbox_set"
        assert trace["projected_evidence"]["bbox_set"] == evidence
        assert trace["projected_evidence"]["pixel_bbox_set"] == evidence
        assert execution["supporting_item_ids"] == [f"option_{out.answer_gt.value}"]
        assert evidence[0] == [
            float(value) for value in render_map["item_bboxes_px"][f"option_{out.answer_gt.value}"]
        ]
        assert render_map["evidence_source"] == "item_bboxes_px"
        assert render["text_style"]["font"]["source"] == "global_font_pool"
        assert render["text_style"]["font"]["font_family"]


def test_matchstick_number_transform_prompt_example_uses_keyed_evidence() -> None:
    out = PuzzlesLogicMatchstickNumberTransformLabelTask().generate(
        31200,
        params={"query_id": "add_one_stick"},
        max_attempts=10,
    )

    answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert set(answer_and_evidence["evidence"]) == {"source_number", "selected_option"}
    assert answer_and_evidence["answer"] == "B"
