"""Behavior tests for synthetic 3D chart panel tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks import create_task
from trace.tasks.charts.three_d.panel_query import (
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_QUERY_IDS,
    ChartsThreeDPanelQueryTask,
)


PUBLIC_TASK_IDS = {
    "reference_nearest_label": "task_charts__surface_3d__reference_nearest_label",
    "surface_extremum_label": "task_charts__surface_3d__surface_extremum_label",
    "series_trend_label": "task_charts__surface_3d__series_trend_label",
    "panel_variation_label": "task_charts__surface_3d__panel_variation_label",
}


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict) -> int | str:
    variant = str(execution["query_id"])

    if variant == "reference_nearest_label":
        target = float(execution["target_axis_value"])
        return min(
            (str(point["label"]) for point in execution["points"]),
            key=lambda label: (
                abs(
                    next(float(point["y_value"]) for point in execution["points"] if str(point["label"]) == label)
                    - target
                ),
                label,
            ),
        )

    if variant == "surface_extremum_label":
        row_values = {str(label): int(value) for label, value in execution["row_values_by_x"].items()}
        reverse = str(execution["extremum_direction"]) == "highest"
        return sorted(row_values, key=lambda label: (row_values[label], label), reverse=reverse)[0]

    if variant == "series_trend_label":
        deltas = {str(label): int(value) for label, value in execution["deltas_by_series"].items()}
        reverse = str(execution["trend_direction"]) == "increase"
        return sorted(deltas, key=lambda label: (deltas[label], label), reverse=reverse)[0]

    if variant == "panel_variation_label":
        ranges = {str(label): int(value) for label, value in execution["ranges_by_panel"].items()}
        return sorted(ranges, key=lambda label: (ranges[label], label), reverse=True)[0]

    raise AssertionError(f"unsupported variant: {variant}")


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_chart_three_d_base_variants_match_contract(query_id: str) -> None:
    task = ChartsThreeDPanelQueryTask()
    out = task.generate(
        98200 + SUPPORTED_QUERY_IDS.index(query_id),
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
    assert str(execution["question_format"]) == "surface_3d_query"
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))

    expected = _expected_answer(execution)
    assert out.answer_gt.value == expected
    assert execution["answer"] == expected
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

    for bbox in out.evidence_gt.value:
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )

    expected_boxes = []
    expected_boxes.extend(render_map["point_bboxes_px"][point_id] for point_id in trace["projected_evidence"]["point_ids"])
    expected_boxes.extend(render_map["surface_cell_bboxes_px"][cell_id] for cell_id in trace["projected_evidence"]["surface_cell_ids"])
    expected_boxes.extend(render_map["panel_bboxes_px"][label] for label in trace["projected_evidence"]["panel_labels"])
    assert out.evidence_gt.value == expected_boxes

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values())


@pytest.mark.parametrize("query_id,task_id", sorted(PUBLIC_TASK_IDS.items()))
def test_chart_three_d_public_tasks_rewrite_query_id(query_id: str, task_id: str) -> None:
    out = create_task(task_id).generate(98300 + SUPPORTED_QUERY_IDS.index(query_id), params={}, max_attempts=80)
    trace = out.trace_payload

    assert out.query_id == "default"
    assert out.query_id == query_id
    assert trace["query_spec"]["query_id"] == "default"
    assert trace["query_spec"]["query_id"] == query_id
    assert trace["execution_trace"]["query_id"] == "default"
    assert trace["execution_trace"]["query_id"] == query_id
    assert trace["scene_ir"]["relations"]["query_id"] == "default"
    assert trace["scene_ir"]["relations"]["query_id"] == query_id


def test_chart_three_d_prompt_examples_match_contract() -> None:
    task = ChartsThreeDPanelQueryTask()
    for index, query_id in enumerate(SUPPORTED_QUERY_IDS, start=98400):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=80)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert "Read this visual" not in out.prompt
        assert "Shown is" not in out.prompt
        assert isinstance(answer_and_evidence["evidence"], list)
        assert isinstance(answer_only["answer"], int | str)
        assert isinstance(answer_and_evidence["answer"], str)


def test_chart_three_d_balanced_sampling_covers_queries_and_sizes() -> None:
    task = ChartsThreeDPanelQueryTask()
    variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    surface_x_counts: Counter[int] = Counter()
    panel_counts: Counter[int] = Counter()

    for index in range(100):
        out = task.generate(hash64(98500, "charts_three_d", index), params={}, max_attempts=300)
        execution = out.trace_payload["execution_trace"]
        variant = str(execution["query_id"])
        variants[variant] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        if variant == "surface_extremum_label":
            surface_x_counts[int(execution["x_count"])] += 1
        if variant == "panel_variation_label":
            panel_counts[int(execution["panel_count"])] += 1

    assert set(variants) == set(SUPPORTED_QUERY_IDS)
    assert set(scene_variants).issubset(set(SUPPORTED_SCENE_VARIANTS))
    assert min(surface_x_counts) >= 5
    assert max(surface_x_counts) <= 7
    assert min(panel_counts) >= 4
    assert max(panel_counts) <= 6


def test_chart_three_d_config_is_loaded() -> None:
    defaults = get_task_group_defaults("charts", "three_d")
    assert defaults["prompt"]["shared"]["bundle_id"] == "charts_three_d_v0"
    assert defaults["generation"]["shared"]["balanced_query_id_sampling"] is True
