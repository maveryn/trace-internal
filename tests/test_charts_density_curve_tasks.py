"""Behavior tests for smooth density-curve chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.charts.distribution.density_curve import (
    SUPPORTED_CURVE_LINE_STYLES,
    SUPPORTED_DENSITY_FAMILIES,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    ChartsDistributionDensityCurveDensityAtXExtremumLabelTask,
    ChartsDistributionDensityCurveIntervalMassExtremumLabelTask,
    ChartsDistributionDensityCurveMeanExtremumLabelTask,
    ChartsDistributionDensityCurveModeLocationExtremumLabelTask,
    ChartsDistributionDensityCurveTask,
)
from trace.tasks.registry import create_task, list_default_task_ids


TASK_CASES = (
    (
        ChartsDistributionDensityCurveMeanExtremumLabelTask,
        "highest_mean_label",
        "answer_mean_marker",
        "mean_marker_bboxes_px",
        "mean_x_by_label",
        "max",
        "keyed_bbox_map",
    ),
    (
        ChartsDistributionDensityCurveMeanExtremumLabelTask,
        "lowest_mean_label",
        "answer_mean_marker",
        "mean_marker_bboxes_px",
        "mean_x_by_label",
        "min",
        "keyed_bbox_map",
    ),
    (
        ChartsDistributionDensityCurveModeLocationExtremumLabelTask,
        "leftmost_mode_label",
        "answer_mode_marker",
        "mode_marker_bboxes_px",
        "mode_x_by_label",
        "min",
        "keyed_bbox_map",
    ),
    (
        ChartsDistributionDensityCurveModeLocationExtremumLabelTask,
        "rightmost_mode_label",
        "answer_mode_marker",
        "mode_marker_bboxes_px",
        "mode_x_by_label",
        "max",
        "keyed_bbox_map",
    ),
    (
        ChartsDistributionDensityCurveIntervalMassExtremumLabelTask,
        "greatest_interval_mass_label",
        "answer_interval_mass",
        "interval_mass_bboxes_px",
        "interval_mass_by_label",
        "max",
        "keyed_bbox_map",
    ),
    (
        ChartsDistributionDensityCurveIntervalMassExtremumLabelTask,
        "least_interval_mass_label",
        "answer_interval_mass",
        "interval_mass_bboxes_px",
        "interval_mass_by_label",
        "min",
        "keyed_bbox_map",
    ),
    (
        ChartsDistributionDensityCurveDensityAtXExtremumLabelTask,
        "highest_density_at_x_label",
        "answer_density_at_x",
        "density_at_x_points_px",
        "density_at_x_by_label",
        "max",
        "keyed_point_map",
    ),
    (
        ChartsDistributionDensityCurveDensityAtXExtremumLabelTask,
        "lowest_density_at_x_label",
        "answer_density_at_x",
        "density_at_x_points_px",
        "density_at_x_by_label",
        "min",
        "keyed_point_map",
    ),
)


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


def _assert_point_inside_canvas(point: list[float], *, width: int, height: int) -> None:
    assert len(point) == 2
    x_value, y_value = [float(value) for value in point]
    assert 0 <= x_value <= width
    assert 0 <= y_value <= height


def _bbox_contains_point(outer: list[float], point: list[float]) -> bool:
    return float(outer[0]) <= float(point[0]) <= float(outer[2]) and float(outer[1]) <= float(point[1]) <= float(outer[3])


def _expected_label(values_by_label: dict[str, float], mode: str) -> str:
    if str(mode) == "max":
        return max(sorted(values_by_label), key=lambda label: (float(values_by_label[label]), label))
    return min(sorted(values_by_label), key=lambda label: (float(values_by_label[label]), label))


@pytest.mark.parametrize(("task_cls", "query_id", "annotation_key", "render_map_key", "metric_key", "mode", "annotation_type"), TASK_CASES)
def test_charts_density_curve_tasks_match_contract(
    task_cls: type,
    query_id: str,
    annotation_key: str,
    render_map_key: str,
    metric_key: str,
    mode: str,
    annotation_type: str,
) -> None:
    out = task_cls().generate(
        hash64(20260606, "density_curve_contract", SUPPORTED_QUERY_IDS.index(query_id)),
        params={"query_id": query_id},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]
    width, height = int(render["canvas_width"]), int(render["canvas_height"])

    assert out.scene_id == "density_curve"
    assert out.query_id == query_id
    assert str(execution["query_id"]) == query_id
    assert str(execution["question_format"]) == "density_curve_label_selection"
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == annotation_type
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert out.image.size == (width, height)
    assert str(render["font_asset_version"])
    assert str(render["chart_font_family"])
    assert str(render["font_assets"]["chart_font_family"]) == str(render["chart_font_family"])

    assert 4 <= int(execution["curve_count"]) <= 7
    assert len(execution["labels"]) == int(execution["curve_count"])
    assert len(set(execution["labels"])) == int(execution["curve_count"])
    assert set(execution["families_by_label"].values()).issubset(set(SUPPORTED_DENSITY_FAMILIES))
    assert set(execution["line_style_by_label"].values()).issubset(set(SUPPORTED_CURVE_LINE_STYLES))
    assert 0.0 <= float(execution["interval_start"]) < float(execution["interval_end"]) <= 100.0
    assert float(execution["winner_gap"]) >= 0.0

    expected = _expected_label({str(label): float(value) for label, value in execution[metric_key].items()}, mode)
    assert str(out.answer_gt.value) == expected
    assert str(execution["answer"]) == expected
    assert trace["projected_annotation"]["type"] == annotation_type
    if annotation_type == "keyed_point_map":
        assert trace["projected_annotation"]["keyed_point_map"] == out.annotation_gt.value
    else:
        assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert set(out.annotation_gt.value) == {annotation_key}

    annotation_witness = list(out.annotation_gt.value[annotation_key])
    assert annotation_witness == render_map[render_map_key][expected]
    if annotation_type == "keyed_point_map":
        _assert_point_inside_canvas(annotation_witness, width=width, height=height)
        assert _bbox_contains_point(render_map["plot_bbox_px"], annotation_witness)
    else:
        _assert_bbox_inside_canvas(annotation_witness, width=width, height=height)
        if annotation_key == "answer_mean_marker":
            plot_bbox = render_map["plot_bbox_px"]
            assert float(plot_bbox[0]) <= float(annotation_witness[0]) < float(annotation_witness[2]) <= float(plot_bbox[2])
            assert float(annotation_witness[1]) >= float(plot_bbox[3])
        else:
            assert _bbox_contains(render_map["plot_bbox_px"], annotation_witness)

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"]) == {"visual_scan", "reasoning_load", "scene_variant_load"}


def test_charts_density_curve_prompt_examples_match_contract() -> None:
    for index, (_task_cls, query_id, annotation_key, _render_map_key, _metric_key, _mode, _annotation_type) in enumerate(TASK_CASES):
        out = ChartsDistributionDensityCurveTask().generate(
            hash64(20260606, "density_curve_prompt", index),
            params={"query_id": query_id},
            max_attempts=100,
        )
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert set(answer_only) == {"answer"}
        assert isinstance(answer_only["answer"], str)
        assert set(answer_and_annotation) == {"annotation", "answer"}
        assert isinstance(answer_and_annotation["answer"], str)
        assert set(answer_and_annotation["annotation"]) == {annotation_key}


def test_charts_density_curve_balanced_sampling_covers_branches_counts_and_families() -> None:
    task = ChartsDistributionDensityCurveTask()
    queries: Counter[str] = Counter()
    counts: Counter[int] = Counter()
    families: Counter[str] = Counter()
    for index in range(96):
        out = task.generate(
            hash64(20260606, "density_curve_balanced", index),
            params={"_sample_cursor": index},
            max_attempts=100,
        )
        execution = out.trace_payload["execution_trace"]
        queries[str(out.query_id)] += 1
        counts[int(execution["curve_count"])] += 1
        families.update(str(value) for value in execution["families_by_label"].values())

    assert set(queries) == set(SUPPORTED_QUERY_IDS)
    assert min(counts) >= 4
    assert max(counts) <= 7
    assert len(counts) >= 3
    assert set(families).issubset(set(SUPPORTED_DENSITY_FAMILIES))
    assert len(families) >= 5


def test_charts_density_curve_is_deterministic() -> None:
    task = ChartsDistributionDensityCurveTask()
    seed = hash64(20260606, "density_curve_deterministic")
    first = task.generate(seed, params={}, max_attempts=100)
    second = task.generate(seed, params={}, max_attempts=100)
    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
    assert first.image.tobytes() == second.image.tobytes()


def test_charts_density_curve_registered_and_group_config_loaded() -> None:
    expected_task_ids = {
        "task_charts__density_curve__density_at_x_extremum_label",
        "task_charts__density_curve__mean_extremum_label",
        "task_charts__density_curve__mode_location_extremum_label",
        "task_charts__density_curve__interval_mass_extremum_label",
    }
    default_task_ids = set(list_default_task_ids())
    assert expected_task_ids.issubset(default_task_ids)
    for task_id in expected_task_ids:
        out = create_task(task_id).generate(hash64(20260606, task_id), params={}, max_attempts=100)
        assert out.scene_id == "density_curve"
        assert out.query_id in SUPPORTED_QUERY_IDS

    cfg = get_task_group_defaults("charts", "distribution")
    generation = cfg["generation"]["task_overrides"][TASK_ID]
    assert int(generation["density_curve_count_min"]) == 4
    assert int(generation["density_curve_count_max"]) == 7
    prompt = cfg["prompt"]["task_overrides"][TASK_ID]
    assert str(prompt["scene_key"]) == "density_curve"
    assert str(prompt["task_key"]) == "density_curve_query"
