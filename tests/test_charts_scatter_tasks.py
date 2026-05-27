"""Behavior tests for scatter cluster chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks import create_task
from trace.tasks.charts.scatter.cluster_query import (
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_QUERY_IDS,
    ChartsScatterClusterQueryTask,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict) -> str:
    variant = str(execution["query_id"])
    labels = [str(label) for label in execution["cluster_labels"]]

    if variant == "cluster_trend_direction_label":
        slopes = {str(label): float(value) for label, value in execution["cluster_slopes"].items()}
        if str(execution["trend_direction"]) == "upward":
            return max(labels, key=lambda label: (slopes[label], label))
        return min(labels, key=lambda label: (slopes[label], label))

    if variant == "cluster_separation_extremum_label":
        distances = {
            str(label): float(value)
            for label, value in execution["centroid_distances_from_reference"].items()
        }
        candidate_labels = sorted(distances)
        if str(execution["separation_extremum"]) == "closest":
            return min(candidate_labels, key=lambda label: (distances[label], label))
        return max(candidate_labels, key=lambda label: (distances[label], label))

    if variant == "cluster_spread_extremum_label":
        metrics = {str(label): float(value) for label, value in execution["cluster_spread_metrics"].items()}
        if str(execution["spread_extremum"]) == "largest":
            return max(labels, key=lambda label: (metrics[label], label))
        return min(labels, key=lambda label: (metrics[label], label))

    raise AssertionError(f"unsupported variant: {variant}")


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_chart_scatter_cluster_variants_match_contract(query_id: str) -> None:
    task = ChartsScatterClusterQueryTask()
    out = task.generate(
        91300 + SUPPORTED_QUERY_IDS.index(query_id),
        params={"query_id": query_id},
        max_attempts=80,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]

    assert out.query_id == query_id
    assert out.answer_gt.type == "string"
    assert out.evidence_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(execution["question_format"]) == "scatter_cluster_query"
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 4 <= int(execution["cluster_count"]) <= 7
    assert 8 <= int(execution["points_per_cluster"]) <= 12
    assert int(execution["total_point_count"]) == int(execution["cluster_count"]) * int(execution["points_per_cluster"])
    assert len(execution["cluster_labels"]) == int(execution["cluster_count"])
    assert len(set(execution["cluster_labels"])) == int(execution["cluster_count"])
    assert set(execution["cluster_labels"]).isdisjoint({"A", "B", "C", "D", "E", "F"})

    expected_answer = _expected_answer(execution)
    assert str(out.answer_gt.value) == expected_answer
    assert str(execution["answer"]) == expected_answer
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

    for bbox in out.evidence_gt.value:
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )

    evidence_clusters = [str(label) for label in trace["projected_evidence"]["cluster_labels"]]
    expected_cluster_boxes = [render_map["cluster_bboxes_px"][label] for label in evidence_clusters]
    assert out.evidence_gt.value == expected_cluster_boxes

    if query_id == "cluster_separation_extremum_label":
        assert len(evidence_clusters) == 2
        assert len(out.evidence_gt.value) == 2
        assert evidence_clusters[0] == execution["reference_cluster_label"]
        assert evidence_clusters[1] == expected_answer
    else:
        assert len(out.evidence_gt.value) == 1
        assert evidence_clusters == [expected_answer]

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values())


def test_chart_scatter_prompt_examples_match_contract() -> None:
    task = ChartsScatterClusterQueryTask()
    for index, query_id in enumerate(SUPPORTED_QUERY_IDS, start=91400):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=80)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert isinstance(answer_and_evidence["answer"], str)
        assert isinstance(answer_and_evidence["evidence"], list)
        assert isinstance(answer_only["answer"], str)
        assert "from from" not in out.prompt
        assert "to to" not in out.prompt


def test_chart_scatter_balanced_sampling_covers_axes() -> None:
    task = ChartsScatterClusterQueryTask()
    variants: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    cluster_counts: Counter[int] = Counter()
    trend_directions: Counter[str] = Counter()
    separation_extrema: Counter[str] = Counter()
    spread_axes: Counter[str] = Counter()
    spread_extrema: Counter[str] = Counter()

    for index in range(90):
        out = task.generate(hash64(91500, "charts_scatter", index), params={}, max_attempts=300)
        execution = out.trace_payload["execution_trace"]
        variants[str(execution["query_id"])] += 1
        labels[str(execution["answer"])] += 1
        cluster_counts[int(execution["cluster_count"])] += 1
        if "trend_direction" in execution:
            trend_directions[str(execution["trend_direction"])] += 1
        if "separation_extremum" in execution:
            separation_extrema[str(execution["separation_extremum"])] += 1
        if "spread_axis" in execution:
            spread_axes[str(execution["spread_axis"])] += 1
        if "spread_extremum" in execution:
            spread_extrema[str(execution["spread_extremum"])] += 1

    assert set(variants) == set(SUPPORTED_QUERY_IDS)
    assert min(cluster_counts) >= 4
    assert max(cluster_counts) <= 7
    assert len(cluster_counts) >= 3
    assert len(labels) >= 8
    assert set(labels).isdisjoint({"A", "B", "C", "D", "E", "F"})
    assert set(trend_directions) == {"upward", "downward"}
    assert set(separation_extrema) == {"closest", "farthest"}
    assert set(spread_axes) == {"horizontal", "vertical", "overall"}
    assert set(spread_extrema) == {"largest", "smallest"}


def test_chart_scatter_is_deterministic() -> None:
    task = ChartsScatterClusterQueryTask()
    params = {"query_id": "cluster_spread_extremum_label", "spread_axis": "overall", "spread_extremum": "largest"}
    out_a = task.generate(91600, params=params, max_attempts=80)
    out_b = task.generate(91600, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()


def test_chart_scatter_registered_and_group_config_loaded() -> None:
    assert create_task("task_charts__scatter_cluster__cluster_trend_direction_label").task_id == "task_charts__scatter_cluster__cluster_trend_direction_label"

    cfg = get_task_group_defaults("charts", "scatter")
    assert isinstance(cfg.get("generation"), dict)
    assert isinstance(cfg.get("rendering"), dict)
    assert isinstance(cfg.get("prompt"), dict)

    generation = cfg["generation"]["shared"]
    assert int(generation["cluster_count_min"]) == 4
    assert int(generation["cluster_count_max"]) == 7
    assert sorted(generation["query_id_weights"].keys()) == sorted(SUPPORTED_QUERY_IDS)

    prompt = cfg["prompt"]["shared"]
    assert str(prompt["bundle_id"]) == "charts_scatter_v0"
    assert str(prompt["scene_key"]) == "scatter_cluster"
    assert str(prompt["task_key"]) == "scatter_cluster_query"
