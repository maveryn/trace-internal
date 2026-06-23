"""Behavior tests for faceted scatter-density chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.scene_config import get_scene_defaults
from trace.tasks import create_task
from trace.tasks.charts.scatter_facet_grid.region_density_extremum_label import (
    SUPPORTED_QUERY_IDS,
    ChartsScatterFacetGridRegionDensityExtremumLabelTask,
)
from trace.tasks.charts.scatter_facet_grid.shared.state import SUPPORTED_LAYOUTS


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _bbox_contains(outer: list[float], inner: list[float]) -> bool:
    return (
        float(outer[0]) <= float(inner[0])
        and float(outer[1]) <= float(inner[1])
        and float(outer[2]) >= float(inner[2])
        and float(outer[3]) >= float(inner[3])
    )


def _expected_answer(execution: dict) -> str:
    densities = {str(label): float(value) for label, value in execution["density_by_panel_label"].items()}
    return max(sorted(densities), key=lambda label: (densities[label], label))


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_chart_scatter_facet_grid_queries_match_contract(query_id: str) -> None:
    task = ChartsScatterFacetGridRegionDensityExtremumLabelTask()
    out = task.generate(
        hash64(20260606, "scatter_facet_grid_contract", SUPPORTED_QUERY_IDS.index(query_id)),
        params={"query_id": query_id},
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]
    width, height = int(render["canvas_width"]), int(render["canvas_height"])

    assert out.scene_id == "scatter_facet_grid"
    assert out.query_id == query_id
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "bbox"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert str(execution["question_format"]) == "scatter_facet_grid_query"
    assert out.image.size == (width, height)
    assert str(render["font_asset_version"])
    assert str(render["chart_font_family"])
    assert str(render["font_assets"]["chart_font_family"]) == str(render["chart_font_family"])

    assert 6 <= int(execution["panel_count"]) <= 12
    assert str(execution["layout_id"]) in SUPPORTED_LAYOUTS
    assert int(execution["layout_rows"]) * int(execution["layout_cols"]) >= int(execution["panel_count"])
    assert len(execution["panel_labels"]) == int(execution["panel_count"])
    assert len(set(execution["panel_labels"])) == int(execution["panel_count"])
    assert str(execution["target_region"]) in {"upper_right", "upper_left", "lower_right", "lower_left"}
    assert set(render_map["panel_bboxes_px"]) == set(execution["panel_labels"])
    assert set(render_map["target_region_bboxes_px"]) == set(execution["panel_labels"])
    assert set(render_map["density_region_bboxes_px"]) == set(execution["panel_labels"])

    expected = _expected_answer(execution)
    assert str(out.answer_gt.value) == expected
    assert str(execution["answer"]) == expected
    assert trace["projected_annotation"]["type"] == "bbox"
    assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_bbox"] == out.annotation_gt.value
    assert trace["projected_annotation"]["answer_panel_label"] == expected
    assert 0.10 <= float(execution["density_winner_relative_gap"]) <= 0.35

    annotation_bbox = list(out.annotation_gt.value)
    _assert_bbox_inside_canvas(annotation_bbox, width=width, height=height)
    assert annotation_bbox == render_map["density_region_bboxes_px"][expected]
    assert _bbox_contains(render_map["panel_bboxes_px"][expected], annotation_bbox)
    assert _bbox_contains(render_map["target_region_bboxes_px"][expected], annotation_bbox)
    assert len(trace["projected_annotation"]["annotation_point_ids"]) >= 18


def test_chart_scatter_facet_grid_prompt_examples_match_contract() -> None:
    task = ChartsScatterFacetGridRegionDensityExtremumLabelTask()
    for index, query_id in enumerate(SUPPORTED_QUERY_IDS):
        out = task.generate(
            hash64(20260606, "scatter_facet_grid_prompt", index),
            params={"query_id": query_id},
            max_attempts=80,
        )
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        assert set(answer_only) == {"answer"}
        assert isinstance(answer_only["answer"], str)
        assert set(answer_and_annotation) == {"annotation", "answer"}
        assert isinstance(answer_and_annotation["answer"], str)
        assert isinstance(answer_and_annotation["annotation"], list)
        assert len(answer_and_annotation["annotation"]) == 4


def test_chart_scatter_facet_grid_balanced_sampling_covers_queries_and_layouts() -> None:
    task = ChartsScatterFacetGridRegionDensityExtremumLabelTask()
    queries: Counter[str] = Counter()
    layouts: Counter[str] = Counter()
    regions: Counter[str] = Counter()
    counts: Counter[int] = Counter()
    for index in range(36):
        out = task.generate(
            hash64(20260606, "scatter_facet_grid_balanced", index),
            params={"_sample_cursor": index},
            max_attempts=80,
        )
        execution = out.trace_payload["execution_trace"]
        queries[str(out.query_id)] += 1
        layouts[str(execution["layout_id"])] += 1
        regions[str(execution["target_region"])] += 1
        counts[int(execution["panel_count"])] += 1

    assert set(queries) == set(SUPPORTED_QUERY_IDS)
    assert set(regions) == {"upper_right", "upper_left", "lower_right", "lower_left"}
    assert set(layouts).issubset(set(SUPPORTED_LAYOUTS))
    assert len(layouts) >= 2
    assert min(counts) >= 6
    assert max(counts) <= 12


def test_chart_scatter_facet_grid_is_deterministic() -> None:
    task = ChartsScatterFacetGridRegionDensityExtremumLabelTask()
    seed = hash64(20260606, "scatter_facet_grid_deterministic")
    first = task.generate(seed, params={}, max_attempts=80)
    second = task.generate(seed, params={}, max_attempts=80)
    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
    assert first.image.tobytes() == second.image.tobytes()


def test_chart_scatter_facet_grid_registered_and_group_config_loaded() -> None:
    task = create_task("task_charts__scatter_facet_grid__region_density_extremum_label")
    assert task.task_id == "task_charts__scatter_facet_grid__region_density_extremum_label"
    out = task.generate(hash64(20260606, "scatter_facet_grid_registered"), params={}, max_attempts=80)
    assert out.scene_id == "scatter_facet_grid"
    assert out.query_id in SUPPORTED_QUERY_IDS

    cfg = get_scene_defaults("charts", "scatter_facet_grid")
    generation = cfg["generation"]["shared"]
    assert int(generation["facet_panel_count_min"]) == 6
    assert int(generation["facet_panel_count_max"]) == 12
    prompt = cfg["prompt"]["shared"]
    assert str(prompt["bundle_id"]) == "charts_scatter_facet_grid_v1"
