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


def test_matchstick_number_transform_uses_keyed_source_and_option_annotation() -> None:
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
        annotation = {
            str(key): [float(value) for value in bbox]
            for key, bbox in out.annotation_gt.value.items()
        }

        assert out.answer_gt.type == "option_letter"
        assert out.annotation_gt.type == "keyed_bbox_map"
        assert set(annotation) == {"source_number", "selected_option"}
        assert trace["projected_annotation"]["type"] == "keyed_bbox_map"
        assert trace["projected_annotation"]["keyed_bbox_map"] == annotation
        assert trace["projected_annotation"]["pixel_keyed_bbox_map"] == annotation
        assert execution["annotation_role_item_ids"] == {
            "source_number": "source_panel",
            "selected_option": f"option_{out.answer_gt.value}",
        }
        assert execution["supporting_item_ids"] == [
            "source_panel",
            f"option_{out.answer_gt.value}",
        ]
        assert annotation["source_number"] == [
            float(value) for value in render_map["item_bboxes_px"]["source_panel"]
        ]
        assert annotation["selected_option"] == [
            float(value) for value in render_map["item_bboxes_px"][f"option_{out.answer_gt.value}"]
        ]
        assert render_map["annotation_source"] == "keyed_item_bboxes_px"
        assert render["text_style"]["font"]["source"] == "global_font_pool"
        assert render["text_style"]["font"]["font_family"]


def test_matchstick_endpoint_extremum_keeps_single_selected_option_annotation() -> None:
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
        annotation = [[float(value) for value in bbox] for bbox in out.annotation_gt.value]

        assert out.answer_gt.type == "option_letter"
        assert out.annotation_gt.type == "bbox_set"
        assert len(annotation) == 1
        assert trace["projected_annotation"]["type"] == "bbox_set"
        assert trace["projected_annotation"]["bbox_set"] == annotation
        assert trace["projected_annotation"]["pixel_bbox_set"] == annotation
        assert execution["supporting_item_ids"] == [f"option_{out.answer_gt.value}"]
        assert annotation[0] == [
            float(value) for value in render_map["item_bboxes_px"][f"option_{out.answer_gt.value}"]
        ]
        assert render_map["annotation_source"] == "item_bboxes_px"
        assert render["text_style"]["font"]["source"] == "global_font_pool"
        assert render["text_style"]["font"]["font_family"]


def test_matchstick_number_transform_prompt_example_uses_keyed_annotation() -> None:
    out = PuzzlesLogicMatchstickNumberTransformLabelTask().generate(
        31200,
        params={"query_id": "add_one_stick"},
        max_attempts=10,
    )

    answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    assert set(answer_and_annotation["annotation"]) == {"source_number", "selected_option"}
    assert answer_and_annotation["answer"] == "B"
