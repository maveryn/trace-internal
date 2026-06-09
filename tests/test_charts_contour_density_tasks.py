"""Behavior tests for contour-density chart tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.charts.contour_density.field_query import (
    OPTION_LABELS,
    SUPPORTED_DENSITY_EXTREMA,
    SUPPORTED_DENSITY_THRESHOLD_DIRECTIONS,
    SUPPORTED_DISTANCE_EXTREMA,
    SUPPORTED_QUERY_IDS,
    SUPPORTED_REFERENCE_KINDS,
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_SPREAD_EXTREMA,
    ChartsContourDensityDensityExtremumRegionLabelTask,
    ChartsContourDensityDensityThresholdRegionCountTask,
    ChartsContourDensityNearestRegionOptionLabelTask,
    ChartsContourDensityReferenceDistanceExtremumLabelTask,
    ChartsContourDensitySpreadExtremumRegionLabelTask,
)
from trace.tasks.registry import create_task, list_default_task_ids


TASK_CASES = (
    (
        ChartsContourDensityNearestRegionOptionLabelTask,
        "nearest_region_option_label",
        "option_letter",
        "keyed_bbox_map",
        {"reference_point", "selected_option_region"},
    ),
    (
        ChartsContourDensityDensityExtremumRegionLabelTask,
        "density_extremum_region_label",
        "string",
        "keyed_bbox_map",
        {"answer_region"},
    ),
    (
        ChartsContourDensityReferenceDistanceExtremumLabelTask,
        "reference_distance_extremum_label",
        "string",
        "keyed_bbox_map",
        {"reference_mark", "answer_region"},
    ),
    (
        ChartsContourDensityDensityThresholdRegionCountTask,
        "density_threshold_region_count",
        "integer",
        "bbox_set",
        set(),
    ),
    (
        ChartsContourDensitySpreadExtremumRegionLabelTask,
        "spread_extremum_region_label",
        "string",
        "keyed_bbox_map",
        {"answer_region"},
    ),
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _expected_answer(execution: dict) -> str | int:
    query_id = str(execution["query_id"])
    if query_id == "nearest_region_option_label":
        distances = {str(label): float(value) for label, value in execution["distances_by_option"].items()}
        return min(distances, key=lambda label: (distances[label], label))
    if query_id == "density_extremum_region_label":
        densities = {str(label): float(value) for label, value in execution["density_by_region_label"].items()}
        if str(execution["density_extremum"]) == "highest":
            return max(densities, key=lambda label: (densities[label], label))
        return min(densities, key=lambda label: (densities[label], label))
    if query_id == "reference_distance_extremum_label":
        distances = {str(label): float(value) for label, value in execution["distances_by_region_label"].items()}
        if str(execution["distance_extremum"]) == "nearest":
            return min(distances, key=lambda label: (distances[label], label))
        return max(distances, key=lambda label: (distances[label], label))
    if query_id == "density_threshold_region_count":
        threshold = int(execution["density_threshold_level"])
        levels = {str(label): int(value) for label, value in execution["density_level_by_region_label"].items()}
        if str(execution["density_threshold_direction"]) == "at_least":
            return sum(1 for value in levels.values() if int(value) >= threshold)
        return sum(1 for value in levels.values() if int(value) < threshold)
    if query_id == "spread_extremum_region_label":
        spreads = {str(label): float(value) for label, value in execution["footprint_area_by_region_label"].items()}
        if str(execution["spread_extremum"]) == "widest":
            return max(spreads, key=lambda label: (spreads[label], label))
        return min(spreads, key=lambda label: (spreads[label], label))
    raise AssertionError(f"unsupported query id: {query_id}")


@pytest.mark.parametrize(("task_cls", "query_id", "answer_type", "annotation_type", "annotation_keys"), TASK_CASES)
def test_charts_contour_density_tasks_match_contract(
    task_cls: type,
    query_id: str,
    answer_type: str,
    annotation_type: str,
    annotation_keys: set[str],
) -> None:
    seed_index = SUPPORTED_QUERY_IDS.index(str(query_id))
    out = task_cls().generate(hash64(20260605, "contour_density", seed_index), params={}, max_attempts=120)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert task_cls.task_id in list_default_task_ids()
    assert out.scene_id == "contour_density"
    assert out.query_id == query_id
    assert str(execution["query_id"]) == query_id
    assert str(execution["question_format"]) == "contour_density_field_query"
    assert str(execution["scene_variant"]) in SUPPORTED_SCENE_VARIANTS
    assert out.answer_gt.type == answer_type
    assert out.annotation_gt.type == annotation_type
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["region_count"]) == len(execution["region_labels"])
    assert 5 <= int(execution["region_count"]) <= 7

    expected = _expected_answer(execution)
    assert out.answer_gt.value == expected
    assert execution["answer"] == expected
    if query_id == "nearest_region_option_label":
        assert str(out.answer_gt.value) in OPTION_LABELS
        assert int(execution["region_count"]) == len(OPTION_LABELS)
        assert set(trace["render_map"]["option_bboxes_px"].keys()) == set(OPTION_LABELS)

    if annotation_type == "bbox_set":
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
        assert len(out.annotation_gt.value) == int(out.answer_gt.value)
        assert len(execution["matching_region_labels"]) == int(out.answer_gt.value)
        for bbox in out.annotation_gt.value:
            _assert_bbox_inside_canvas(
                [float(value) for value in bbox],
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )
    else:
        assert set(out.annotation_gt.value.keys()) == annotation_keys
        assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
        for bbox in out.annotation_gt.value.values():
            _assert_bbox_inside_canvas(
                [float(value) for value in bbox],
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }


def test_charts_contour_density_prompt_examples_match_contract() -> None:
    for seed_index, (task_cls, _query_id, answer_type, annotation_type, annotation_keys) in enumerate(TASK_CASES):
        out = task_cls().generate(hash64(20260605, "contour_density_prompt", seed_index), params={}, max_attempts=120)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        if annotation_type == "bbox_set":
            assert isinstance(answer_and_annotation["annotation"], list)
            assert answer_and_annotation["annotation"]
        else:
            assert set(answer_and_annotation["annotation"].keys()) == annotation_keys
        assert set(answer_only.keys()) == {"answer"}
        if answer_type == "option_letter":
            assert answer_and_annotation["answer"] in OPTION_LABELS
            assert answer_only["answer"] in OPTION_LABELS
        elif answer_type == "integer":
            assert isinstance(answer_and_annotation["answer"], int)
            assert isinstance(answer_only["answer"], int)
        else:
            assert isinstance(answer_and_annotation["answer"], str)
            assert isinstance(answer_only["answer"], str)
            assert len(answer_and_annotation["answer"]) > 1


def test_charts_contour_density_balanced_sampling_covers_axes() -> None:
    scene_variants: Counter[str] = Counter()
    nearest_answers: Counter[str] = Counter()
    density_extrema: Counter[str] = Counter()
    distance_extrema: Counter[str] = Counter()
    reference_kinds: Counter[str] = Counter()
    threshold_directions: Counter[str] = Counter()
    threshold_counts: Counter[int] = Counter()
    spread_extrema: Counter[str] = Counter()

    for index in range(90):
        nearest = ChartsContourDensityNearestRegionOptionLabelTask().generate(
            hash64(20260605, "contour_density_nearest", index),
            params={},
            max_attempts=120,
        )
        scene_variants[str(nearest.trace_payload["execution_trace"]["scene_variant"])] += 1
        nearest_answers[str(nearest.answer_gt.value)] += 1

        density = ChartsContourDensityDensityExtremumRegionLabelTask().generate(
            hash64(20260605, "contour_density_density", index),
            params={},
            max_attempts=120,
        )
        scene_variants[str(density.trace_payload["execution_trace"]["scene_variant"])] += 1
        density_extrema[str(density.trace_payload["execution_trace"]["density_extremum"])] += 1

        distance = ChartsContourDensityReferenceDistanceExtremumLabelTask().generate(
            hash64(20260605, "contour_density_distance", index),
            params={},
            max_attempts=120,
        )
        scene_variants[str(distance.trace_payload["execution_trace"]["scene_variant"])] += 1
        distance_extrema[str(distance.trace_payload["execution_trace"]["distance_extremum"])] += 1
        reference_kinds[str(distance.trace_payload["execution_trace"]["reference_kind"])] += 1

        threshold = ChartsContourDensityDensityThresholdRegionCountTask().generate(
            hash64(20260605, "contour_density_threshold", index),
            params={},
            max_attempts=120,
        )
        scene_variants[str(threshold.trace_payload["execution_trace"]["scene_variant"])] += 1
        threshold_directions[str(threshold.trace_payload["execution_trace"]["density_threshold_direction"])] += 1
        threshold_counts[int(threshold.answer_gt.value)] += 1

        spread = ChartsContourDensitySpreadExtremumRegionLabelTask().generate(
            hash64(20260605, "contour_density_spread", index),
            params={},
            max_attempts=120,
        )
        scene_variants[str(spread.trace_payload["execution_trace"]["scene_variant"])] += 1
        spread_extrema[str(spread.trace_payload["execution_trace"]["spread_extremum"])] += 1

    assert set(scene_variants) == set(SUPPORTED_SCENE_VARIANTS)
    assert set(nearest_answers) == set(OPTION_LABELS)
    assert set(density_extrema) == set(SUPPORTED_DENSITY_EXTREMA)
    assert set(distance_extrema) == set(SUPPORTED_DISTANCE_EXTREMA)
    assert set(reference_kinds) == set(SUPPORTED_REFERENCE_KINDS)
    assert set(threshold_directions) == set(SUPPORTED_DENSITY_THRESHOLD_DIRECTIONS)
    assert set(threshold_counts).issubset({1, 2, 3, 4, 5})
    assert len(threshold_counts) >= 4
    assert set(spread_extrema) == set(SUPPORTED_SPREAD_EXTREMA)


def test_charts_contour_density_is_deterministic() -> None:
    params = {
        "scene_variant": "scatter_contour",
        "distance_extremum": "farthest",
        "reference_kind": "vertical_line",
    }
    out_a = ChartsContourDensityReferenceDistanceExtremumLabelTask().generate(202606051, params=params, max_attempts=120)
    out_b = ChartsContourDensityReferenceDistanceExtremumLabelTask().generate(202606051, params=params, max_attempts=120)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["render_map"] == out_b.trace_payload["render_map"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()


def test_charts_contour_density_registry_and_config_are_wired() -> None:
    for seed_index, (task_cls, query_id, _answer_type, _annotation_type, _annotation_keys) in enumerate(TASK_CASES):
        task = create_task(str(task_cls.task_id))
        assert isinstance(task, task_cls)
        out = task.generate(hash64(20260605, "contour_density_registry", seed_index), params={}, max_attempts=120)
        assert out.query_id == query_id

    defaults = get_task_group_defaults("charts", "contour_density")
    assert sorted(defaults["generation"]["shared"]["query_id_weights"].keys()) == sorted(SUPPORTED_QUERY_IDS)
    prompt = defaults["prompt"]["shared"]
    assert str(prompt["bundle_id"]) == "charts_contour_density_v0"
    assert str(prompt["scene_key"]) == "contour_density_scene"
    assert str(prompt["task_key"]) == "contour_density_query"
