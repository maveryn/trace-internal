"""Behavior tests for scientific multi-panel chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks import create_task
from trace.tasks.charts.scientific.multipanel_subplot_query import (
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_QUERY_IDS,
    ChartsScientificMultipanelSubplotQueryTask,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict) -> str | int:
    variant = str(execution["query_id"])

    if variant == "curve_at_x_extremum_label":
        values = {str(key): int(value) for key, value in execution["values_at_query_x"].items()}
        return max(values, key=lambda label: (values[label], label))

    if variant == "threshold_series_count":
        threshold = int(execution["threshold_value"])
        values = {str(key): int(value) for key, value in execution["values_at_query_x"].items()}
        return sum(1 for value in values.values() if int(value) > int(threshold))

    if variant == "cross_panel_delta_extremum_label":
        deltas = {str(key): int(value) for key, value in execution["deltas_by_panel"].items()}
        return max(deltas, key=lambda label: (deltas[label], label))

    if variant == "curve_intersection_count":
        return int(execution["intersection_count"])

    if variant == "earliest_maximum_panel_label":
        peak_x = {str(key): int(value) for key, value in execution["peak_x_by_panel"].items()}
        return min(peak_x, key=lambda label: (peak_x[label], label))

    raise AssertionError(f"unsupported variant: {variant}")


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_charts_scientific_variants_match_contract(query_id: str) -> None:
    task = ChartsScientificMultipanelSubplotQueryTask()
    out = task.generate(
        93100 + SUPPORTED_QUERY_IDS.index(query_id),
        params={"query_id": query_id},
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]

    assert out.query_id == query_id
    assert out.evidence_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(execution["question_format"]) == "curve_panels_subplot_query"
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 4 <= int(execution["panel_count"]) <= 8
    assert 3 <= int(execution["method_count"]) <= 6
    assert 4 <= int(len(execution["x_values"])) <= 10
    x_values = [int(value) for value in execution["x_values"]]
    assert x_values[0] == 0
    assert len({x_values[index + 1] - x_values[index] for index in range(len(x_values) - 1)}) == 1

    expected_answer = _expected_answer(execution)
    assert out.answer_gt.value == expected_answer
    assert execution["answer"] == expected_answer
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

    for bbox in out.evidence_gt.value:
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )

    expected_boxes = []
    for panel_label in trace["projected_evidence"]["panel_labels"]:
        expected_boxes.append(render_map["panel_bboxes_px"][str(panel_label)])
    for point_id in trace["projected_evidence"]["point_ids"]:
        expected_boxes.append(render_map["point_bboxes_px"][str(point_id)])
    for intersection_id in trace["projected_evidence"]["intersection_ids"]:
        expected_boxes.append(render_map["intersection_bboxes_px"][str(intersection_id)])
    assert out.evidence_gt.value == expected_boxes

    if query_id == "threshold_series_count":
        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == len(trace["projected_evidence"]["point_ids"])
    elif query_id == "curve_intersection_count":
        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == len(trace["projected_evidence"]["intersection_ids"])
    else:
        assert out.answer_gt.type == "string"

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values())


def test_charts_scientific_prompt_examples_match_contract() -> None:
    task = ChartsScientificMultipanelSubplotQueryTask()
    for index, query_id in enumerate(SUPPORTED_QUERY_IDS, start=93200):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=80)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert isinstance(answer_and_evidence["evidence"], list)
        if out.answer_gt.type == "integer":
            assert isinstance(answer_and_evidence["answer"], int)
            assert isinstance(answer_only["answer"], int)
        else:
            assert isinstance(answer_and_evidence["answer"], str)
            assert isinstance(answer_only["answer"], str)


def test_charts_scientific_balanced_sampling_covers_axes() -> None:
    task = ChartsScientificMultipanelSubplotQueryTask()
    variants: Counter[str] = Counter()
    curve_answers: Counter[str] = Counter()
    threshold_answers: Counter[int] = Counter()
    delta_answers: Counter[str] = Counter()
    intersection_answers: Counter[int] = Counter()
    earliest_answers: Counter[str] = Counter()

    for index in range(150):
        out = task.generate(hash64(93300, "charts_scientific", index), params={}, max_attempts=120)
        execution = out.trace_payload["execution_trace"]
        variant = str(execution["query_id"])
        variants[variant] += 1
        if variant == "curve_at_x_extremum_label":
            curve_answers[str(execution["answer"])] += 1
        elif variant == "threshold_series_count":
            threshold_answers[int(execution["answer"])] += 1
        elif variant == "cross_panel_delta_extremum_label":
            delta_answers[str(execution["answer"])] += 1
        elif variant == "curve_intersection_count":
            intersection_answers[int(execution["answer"])] += 1
        elif variant == "earliest_maximum_panel_label":
            earliest_answers[str(execution["answer"])] += 1

    assert set(variants) == set(SUPPORTED_QUERY_IDS)
    assert set(curve_answers) == {"M1", "M2", "M3", "M4", "M5", "M6"}
    assert set(threshold_answers).issubset({1, 2, 3, 4, 5, 6})
    assert {1, 2, 3, 4}.issubset(set(threshold_answers))
    assert {"A", "B", "C", "D"}.issubset(set(delta_answers))
    assert set(delta_answers).issubset(set("ABCDEFGH"))
    assert set(intersection_answers) == {0, 1, 2, 3, 4}
    assert {"A", "B", "C", "D"}.issubset(set(earliest_answers))
    assert set(earliest_answers).issubset(set("ABCDEFGH"))


def test_charts_scientific_intersection_count_review_distribution() -> None:
    task = create_task("task_charts__curve_panels__curve_intersection_count")
    answers: Counter[int] = Counter()

    for index in range(100):
        out = task.generate(
            hash64(20260507, task.task_id, index),
            params={},
            max_attempts=120,
        )
        answers[int(out.answer_gt.value)] += 1

    assert set(answers) == {0, 1, 2, 3, 4}
    assert max(answers.values()) <= 25


def test_charts_scientific_is_deterministic() -> None:
    task = ChartsScientificMultipanelSubplotQueryTask()
    params = {"query_id": "cross_panel_delta_extremum_label"}
    out_a = task.generate(93400, params=params, max_attempts=80)
    out_b = task.generate(93400, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()


def test_charts_scientific_registered_and_group_config_loaded() -> None:
    assert create_task("task_charts__curve_panels__curve_at_x_extremum_label").task_id == "task_charts__curve_panels__curve_at_x_extremum_label"

    cfg = get_task_group_defaults("charts", "scientific")
    assert isinstance(cfg.get("generation"), dict)
    assert isinstance(cfg.get("rendering"), dict)
    assert isinstance(cfg.get("prompt"), dict)

    generation = cfg["generation"]["shared"]
    assert int(generation["panel_count_min"]) == 4
    assert int(generation["method_count_min"]) == 3
    assert int(generation["method_count_max"]) == 6
    assert int(generation["x_tick_count_min"]) == 4
    assert int(generation["x_tick_count_max"]) == 10
    assert int(generation["x_step_min"]) == 5
    assert int(generation["x_step_max"]) == 20
    assert sorted(generation["query_id_weights"].keys()) == sorted(SUPPORTED_QUERY_IDS)

    prompt = cfg["prompt"]["shared"]
    assert str(prompt["bundle_id"]) == "charts_scientific_v0"
    assert str(prompt["scene_key"]) == "curve_panels_subplot"
    assert str(prompt["task_key"]) == "multipanel_subplot_query"


def test_scientific_curve_at_x_public_task_uses_calibrated_density() -> None:
    task = create_task("task_charts__curve_panels__curve_at_x_extremum_label")
    out = task.generate(2026052301, params={}, max_attempts=120)
    execution = out.trace_payload["execution_trace"]

    assert out.query_id == "default"
    assert out.query_id == "curve_at_x_extremum_label"
    assert 6 <= int(execution["panel_count"]) <= 8
    assert int(execution["method_count"]) == 6
    assert 8 <= len(execution["x_values"]) <= 10

    values = {str(key): int(value) for key, value in execution["values_at_query_x"].items()}
    answer = str(out.answer_gt.value)
    assert answer in values
    assert values[answer] == max(values.values())
    assert min(values[answer] - value for key, value in values.items() if str(key) != answer) >= 4
