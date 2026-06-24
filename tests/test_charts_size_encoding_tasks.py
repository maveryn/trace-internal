"""Behavior tests for chart size-encoding tasks."""

from __future__ import annotations

from collections import Counter
from typing import Any

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.query_ids import SINGLE_QUERY_ID
from trace.core.seed import hash64
from trace.tasks.charts.size_encoding.category_total_extremum_label import (
    ChartsSizeEncodingCategoryTotalExtremumLabelTask,
)
from trace.tasks.charts.size_encoding.filtered_item_extremum_label import (
    ChartsSizeEncodingFilteredItemExtremumLabelTask,
)
from trace.tasks.charts.size_encoding.reference_size_neighbor_label import (
    ChartsSizeEncodingReferenceSizeNeighborLabelTask,
)
from trace.tasks.charts.size_encoding.shared.state import SUPPORTED_SCENE_VARIANTS


TASK_CASES = (
    (
        ChartsSizeEncodingFilteredItemExtremumLabelTask,
        ("largest_size_item_in_category_label", "smallest_size_item_in_category_label"),
        "bbox",
    ),
    (
        ChartsSizeEncodingReferenceSizeNeighborLabelTask,
        (SINGLE_QUERY_ID,),
        "bbox_map",
    ),
    (
        ChartsSizeEncodingCategoryTotalExtremumLabelTask,
        ("largest_category_total_label", "smallest_category_total_label"),
        "bbox_set",
    ),
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict[str, Any], query_params: dict[str, Any]) -> str:
    values_by_label = {str(label): int(value) for label, value in execution["values_by_label"].items()}
    category_by_label = {str(label): str(value) for label, value in execution["category_by_label"].items()}
    question_format = str(execution["question_format"])
    assert question_format == "size_encoded_label_comparison"

    if str(query_params["query_id"]) in {"largest_size_item_in_category_label", "smallest_size_item_in_category_label"}:
        category = str(query_params["category_label"])
        candidates = [label for label, value in category_by_label.items() if value == category]
        reverse = str(execution["extremum_direction"]) == "largest"
        return str(sorted(candidates, key=lambda label: (values_by_label[label], label), reverse=reverse)[0])

    if str(query_params["query_id"]) == SINGLE_QUERY_ID:
        category = str(query_params["category_label"])
        reference = str(query_params["reference_label"])
        reference_value = values_by_label[reference]
        candidates = [label for label, value in category_by_label.items() if value == category and label != reference]
        return str(sorted(candidates, key=lambda label: (abs(values_by_label[label] - reference_value), label))[0])

    if str(query_params["query_id"]) in {"largest_category_total_label", "smallest_category_total_label"}:
        totals = {str(label): int(value) for label, value in execution["category_totals"].items()}
        reverse = str(execution["extremum_direction"]) == "largest"
        return str(sorted(totals, key=lambda label: (totals[label], label), reverse=reverse)[0])

    raise AssertionError(f"unsupported branch: {query_params['query_id']}")


@pytest.mark.parametrize(("task_cls", "branches", "annotation_type"), TASK_CASES)
def test_chart_size_encoding_tasks_match_contract(task_cls: type, branches: tuple[str, ...], annotation_type: str) -> None:
    task = task_cls()
    for branch_index, branch in enumerate(branches):
        out = task.generate(78300 + branch_index, params={"query_id": branch}, max_attempts=160)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        query_params = trace["query_spec"]["params"]

        assert out.query_id == branch
        assert out.answer_gt.type == "string"
        assert out.annotation_gt.type == annotation_type
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
        assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 3 <= int(execution["category_count"]) <= 5
        assert 1 <= int(execution["panel_count"]) <= 4
        assert int(execution["item_count"]) == len(execution["values_by_label"])

        expected_answer = _expected_answer(execution, query_params)
        assert str(out.answer_gt.value) == expected_answer
        assert str(execution["answer_label"]) == expected_answer
        assert trace["projected_annotation"]["type"] == annotation_type

        annotation_item_ids = [str(item_id) for item_id in trace["projected_annotation"]["annotation_item_ids"]]
        expected_item_boxes = [render_map["item_bboxes_px"][item_id] for item_id in annotation_item_ids]
        if annotation_type == "bbox":
            assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
            assert out.annotation_gt.value == expected_item_boxes[0]
            annotation_boxes = [list(out.annotation_gt.value)]
            assert len(annotation_item_ids) == 1
            assert 16 <= int(execution["winner_gap"]) <= 24
            assert int(execution["outside_extreme_count"]) >= 2
        elif annotation_type == "bbox_map":
            assert trace["projected_annotation"]["bbox_map"] == out.annotation_gt.value
            assert trace["projected_annotation"]["pixel_bbox_map"] == out.annotation_gt.value
            assert set(out.annotation_gt.value) == {"reference_item", "answer_item"}
            assert out.annotation_gt.value == {"reference_item": expected_item_boxes[0], "answer_item": expected_item_boxes[1]}
            annotation_boxes = [list(bbox) for bbox in out.annotation_gt.value.values()]
            assert len(out.annotation_gt.value) == 2
            assert execution["annotation_labels"][0] == query_params["reference_label"]
        else:
            assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
            assert out.annotation_gt.value == expected_item_boxes
            annotation_boxes = [list(bbox) for bbox in out.annotation_gt.value]
            assert str(out.answer_gt.value) in execution["categories"]
            assert len(out.annotation_gt.value) >= 2

        assert str(render["font_assets"]["font_asset_version"])
        assert str(render["font_assets"]["chart_font_family"])
        for bbox in annotation_boxes:
            _assert_bbox_inside_canvas([float(value) for value in bbox], width=int(render["canvas_width"]), height=int(render["canvas_height"]))


def test_chart_size_encoding_prompt_examples_match_contract() -> None:
    for task_cls, branches, annotation_type in TASK_CASES:
        task = task_cls()
        for index, branch in enumerate(branches, start=78400):
            out = task.generate(index, params={"query_id": branch}, max_attempts=160)
            answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
            answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
            assert isinstance(answer_and_annotation["answer"], str)
            if annotation_type == "bbox_map":
                assert isinstance(answer_and_annotation["annotation"], dict)
                assert set(answer_and_annotation["annotation"]) == {"reference_item", "answer_item"}
            elif annotation_type == "bbox":
                assert isinstance(answer_and_annotation["annotation"], list)
                assert len(answer_and_annotation["annotation"]) == 4
            else:
                assert isinstance(answer_and_annotation["annotation"], list)
                assert all(isinstance(value, list) for value in answer_and_annotation["annotation"])
            assert isinstance(answer_only["answer"], str)


def test_chart_size_encoding_sampling_covers_scene_variants_and_branches() -> None:
    variants: Counter[str] = Counter()
    scenes: Counter[str] = Counter()
    for task_cls, branches, _annotation_type in TASK_CASES:
        task = task_cls()
        for index, branch in enumerate(branches):
            out = task.generate(hash64(78500, task.task_id, index), params={"query_id": branch}, max_attempts=300)
            execution = out.trace_payload["execution_trace"]
            variants[str(out.query_id)] += 1
            scenes[str(execution["scene_variant"])] += 1
    assert set(variants) == {
        "largest_size_item_in_category_label",
        "smallest_size_item_in_category_label",
        SINGLE_QUERY_ID,
        "largest_category_total_label",
        "smallest_category_total_label",
    }
    assert set(scenes).issubset(set(SUPPORTED_SCENE_VARIANTS))
    assert len(scenes) >= 2


def test_chart_size_encoding_is_deterministic() -> None:
    task = ChartsSizeEncodingReferenceSizeNeighborLabelTask()
    params = {"query_id": SINGLE_QUERY_ID, "scene_variant": "packed_bubble_cloud"}
    out_a = task.generate(78600, params=params, max_attempts=160)
    out_b = task.generate(78600, params=params, max_attempts=160)
    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
