"""Behavior tests for matchstick puzzle tasks."""

from __future__ import annotations

import json
import re

from trace.tasks.puzzles.matchstick.matchstick_number_transform_label import (
    PuzzlesMatchstickNumberTransformLabelTask,
    SUPPORTED_QUERY_IDS as NUMBER_QUERY_IDS,
)
from trace.tasks.puzzles.matchstick.shared.state import SCENE_VARIANTS


def _extract_answer_and_annotation_example(prompt: str) -> dict[str, object]:
    match = re.search(r'(\{"annotation".*\})\.?$', str(prompt))
    assert match is not None
    return json.loads(match.group(1).rstrip("."))


def test_matchstick_number_transform_uses_keyed_source_and_option_annotation() -> None:
    task = PuzzlesMatchstickNumberTransformLabelTask()

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
        assert out.annotation_gt.type == "bbox_map"
        assert set(annotation) == {"source_number", "selected_option"}
        assert trace["projected_annotation"]["type"] == "bbox_map"
        assert trace["projected_annotation"]["bbox_map"] == annotation
        assert trace["projected_annotation"]["pixel_bbox_map"] == annotation
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


def test_matchstick_number_transform_prompt_example_uses_keyed_annotation() -> None:
    out = PuzzlesMatchstickNumberTransformLabelTask().generate(
        31200,
        params={"query_id": "add_one_stick"},
        max_attempts=10,
    )

    answer_and_annotation = _extract_answer_and_annotation_example(
        out.prompt_variants["answer_and_annotation"]
    )
    assert set(answer_and_annotation["annotation"]) == {"source_number", "selected_option"}
    assert answer_and_annotation["answer"] == "B"
