"""Behavior tests for chart size-encoding comparison tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.size_encoding.comparison_label import (
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_QUERY_VARIANTS,
    ChartsSizeEncodingComparisonLabelTask,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict, query_params: dict) -> str:
    values_by_label = {str(label): int(value) for label, value in execution["values_by_label"].items()}
    category_by_label = {str(label): str(value) for label, value in execution["category_by_label"].items()}
    variant = str(execution["query_variant"])

    if variant == "filtered_item_extremum_label":
        category = str(query_params["category_label"])
        candidates = [label for label, value in category_by_label.items() if value == category]
        reverse = str(execution["extremum_direction"]) == "largest"
        return str(sorted(candidates, key=lambda label: (values_by_label[label], label), reverse=reverse)[0])

    if variant == "reference_size_neighbor_label":
        category = str(query_params["category_label"])
        reference = str(query_params["reference_label"])
        reference_value = values_by_label[reference]
        candidates = [
            label
            for label, value in category_by_label.items()
            if value == category and label != reference
        ]
        return str(sorted(candidates, key=lambda label: (abs(values_by_label[label] - reference_value), label))[0])

    if variant == "category_total_extremum_label":
        totals = {str(label): int(value) for label, value in execution["category_totals"].items()}
        reverse = str(execution["extremum_direction"]) == "largest"
        return str(sorted(totals, key=lambda label: (totals[label], label), reverse=reverse)[0])

    raise AssertionError(f"unsupported variant: {variant}")


@pytest.mark.parametrize("query_variant", SUPPORTED_QUERY_VARIANTS)
def test_chart_size_encoding_variants_match_contract(query_variant: str) -> None:
    task = ChartsSizeEncodingComparisonLabelTask()
    out = task.generate(
        78300 + SUPPORTED_QUERY_VARIANTS.index(query_variant),
        params={"query_variant": query_variant},
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]
    query_params = trace["query_spec"]["params"]

    assert out.query_variant == query_variant
    assert out.answer_gt.type == "string"
    assert out.evidence_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(execution["question_format"]) == "size_encoded_label_comparison"
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 3 <= int(execution["category_count"]) <= 5
    assert 1 <= int(execution["panel_count"]) <= 4
    assert int(execution["item_count"]) == len(execution["values_by_label"])

    expected_answer = _expected_answer(execution, query_params)
    assert str(out.answer_gt.value) == expected_answer
    assert str(execution["answer_label"]) == expected_answer
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

    for bbox in out.evidence_gt.value:
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )

    evidence_item_ids = [str(item_id) for item_id in trace["projected_evidence"]["evidence_item_ids"]]
    expected_item_boxes = [render_map["item_bboxes_px"][item_id] for item_id in evidence_item_ids]
    assert out.evidence_gt.value == expected_item_boxes

    if query_variant == "category_total_extremum_label":
        assert str(out.answer_gt.value) in execution["categories"]
        assert len(out.evidence_gt.value) >= 2
    elif query_variant == "reference_size_neighbor_label":
        assert len(out.evidence_gt.value) == 2
        assert execution["evidence_labels"][0] == query_params["reference_label"]
    else:
        assert len(out.evidence_gt.value) == 1
        assert 16 <= int(execution["winner_gap"]) <= 24
        assert int(execution["outside_extreme_count"]) >= 2

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values())


def test_chart_size_encoding_prompt_examples_match_contract() -> None:
    task = ChartsSizeEncodingComparisonLabelTask()
    for index, query_variant in enumerate(SUPPORTED_QUERY_VARIANTS, start=78400):
        out = task.generate(index, params={"query_variant": query_variant}, max_attempts=80)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert isinstance(answer_and_evidence["answer"], str)
        assert isinstance(answer_and_evidence["evidence"], list)
        assert isinstance(answer_only["answer"], str)


def test_chart_size_encoding_balanced_sampling_covers_axes() -> None:
    task = ChartsSizeEncodingComparisonLabelTask()
    variants: Counter[str] = Counter()
    scenes: Counter[str] = Counter()
    directions: Counter[str] = Counter()

    for index in range(40):
        out = task.generate(hash64(78500, "charts_size_encoding", index), params={}, max_attempts=300)
        execution = out.trace_payload["execution_trace"]
        variants[str(execution["query_variant"])] += 1
        scenes[str(execution["scene_variant"])] += 1
        directions[str(execution["extremum_direction"])] += 1

    assert set(variants) == set(SUPPORTED_QUERY_VARIANTS)
    assert set(scenes) == set(SUPPORTED_SCENE_VARIANTS)
    assert set(directions) >= {"largest", "smallest"}


def test_chart_size_encoding_is_deterministic() -> None:
    task = ChartsSizeEncodingComparisonLabelTask()
    params = {"query_variant": "reference_size_neighbor_label", "scene_variant": "packed_bubble_cloud"}
    out_a = task.generate(78600, params=params, max_attempts=80)
    out_b = task.generate(78600, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()
