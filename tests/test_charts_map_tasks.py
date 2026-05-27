"""Behavior tests for chart map-region tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.map.choropleth_region_label import (
    SUPPORTED_ADJACENT_QUERY_IDS,
    SUPPORTED_MARKER_RENDER_VARIANTS,
    SUPPORTED_REGION_VALUE_QUERY_IDS,
    SUPPORTED_WORLD_FILTERED_QUERY_IDS,
    ChartsMapAdjacentConditionCountTask,
    ChartsMapBorderNeighborCountTask,
    ChartsMapContinentFilteredCountTask,
    ChartsMapLegendPredicateRegionCountTask,
    ChartsMapMarkerRegionExtremumLabelTask,
    ChartsMapMarkerRegionThresholdCountTask,
    _world_country_shared_border_lengths,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _regions_by_id(execution: dict) -> dict[str, dict]:
    return {str(key): dict(value) for key, value in execution["regions_by_id"].items()}


def _assert_common_output(out) -> None:
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(execution["scene_variant"]) in {"synthetic_region_map", "geographic_region_map"}
    assert str(execution["question_format"]) == "map_region_count"
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(trace["projected_evidence"]["region_ids"]) == int(out.answer_gt.value)
    assert "choropleth" not in out.prompt.lower()
    for bbox in out.evidence_gt.value:
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )


def _expected_bin_count(execution: dict) -> int:
    target_bins = {int(value) for value in execution["target_bin_indices"]}
    return sum(1 for region in _regions_by_id(execution).values() if int(region["bin_index"]) in target_bins)


@pytest.mark.parametrize("query_id", SUPPORTED_REGION_VALUE_QUERY_IDS)
def test_chart_map_region_value_count_supports_synthetic_and_geographic_maps(query_id: str) -> None:
    task = ChartsMapLegendPredicateRegionCountTask()
    for scene_index, scene_variant in enumerate(("synthetic_region_map", "geographic_region_map")):
        out = task.generate(
            67100 + scene_index + SUPPORTED_REGION_VALUE_QUERY_IDS.index(query_id),
            params={"query_id": query_id, "scene_variant": scene_variant},
            max_attempts=10,
        )
        _assert_common_output(out)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        assert out.query_id == query_id
        assert int(out.answer_gt.value) == _expected_bin_count(execution)
        assert len(execution["legend_bins"]) >= 3
        assert str(render["legend_position"]) in {"right", "top", "bottom"}
        if scene_variant == "synthetic_region_map":
            assert 4 <= int(execution["rows"]) <= 7
            assert 4 <= int(execution["cols"]) <= 7
            assert 14 <= int(execution["region_count"]) <= 22
        else:
            assert str(execution["map_asset_id"]).startswith("natural_earth_")
            assert str(render["map_source"]["license"]) == "public domain"


def test_chart_map_region_category_count_uses_shared_label_assets() -> None:
    task = ChartsMapLegendPredicateRegionCountTask()
    out = task.generate(
        67200,
        params={"query_id": "categorical_region_count", "scene_variant": "geographic_region_map"},
        max_attempts=10,
    )
    _assert_common_output(out)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    qparams = trace["query_spec"]["params"]

    assert out.query_id == "categorical_region_count"
    assert int(out.answer_gt.value) == _expected_bin_count(execution)
    assert "category_label" in qparams
    target_category = str(qparams["category_label"])
    for bin_spec in execution["legend_bins"]:
        assert bin_spec["lower"] is None
        assert bin_spec["upper"] is None
        assert str(bin_spec["category"])
        assert dict(bin_spec["label_source"])["label_source_kind"] == "shared_label_manifest"
    for region_id in trace["projected_evidence"]["region_ids"]:
        assert str(_regions_by_id(execution)[str(region_id)]["category"]) == target_category


@pytest.mark.parametrize("query_id", SUPPORTED_WORLD_FILTERED_QUERY_IDS)
def test_chart_map_continent_filtered_count_uses_world_map_filter(query_id: str) -> None:
    task = ChartsMapContinentFilteredCountTask()
    out = task.generate(
        67250 + SUPPORTED_WORLD_FILTERED_QUERY_IDS.index(query_id),
        params={"query_id": query_id},
        max_attempts=10,
    )
    _assert_common_output(out)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    qparams = trace["query_spec"]["params"]

    assert out.query_id == query_id
    assert str(execution["scene_variant"]) == "geographic_region_map"
    assert str(execution["geographic_map_variant"]) == "world_countries"
    assert str(execution["map_asset_id"]) == "natural_earth_admin0_world_110m_v0"
    assert 1 <= int(out.answer_gt.value) <= 6

    continent = str(qparams["continent_label"])
    assert continent in {"Africa", "Asia", "Europe", "North America", "South America"}
    regions_by_id = _regions_by_id(execution)
    evidence_ids = [str(region_id) for region_id in trace["projected_evidence"]["region_ids"]]
    assert all(str(regions_by_id[region_id]["continent"]) == continent for region_id in evidence_ids)

    if str(query_id) == "continent_category_region_count":
        target_category = str(qparams["category_label"])
        assert all(str(regions_by_id[region_id]["category"]) == target_category for region_id in evidence_ids)
    elif str(query_id) == "continent_threshold_region_count":
        target_bins = {int(value) for value in qparams["target_bin_indices"]}
        assert all(int(regions_by_id[region_id]["bin_index"]) in target_bins for region_id in evidence_ids)


def test_chart_map_border_neighbor_count_uses_visible_land_borders() -> None:
    task = ChartsMapBorderNeighborCountTask()
    out = task.generate(67300, params={}, max_attempts=10)
    _assert_common_output(out)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    qparams = trace["query_spec"]["params"]

    assert out.query_id == "border_neighbor_count"
    assert str(execution["geographic_map_variant"]) == "world_countries"
    assert str(render["legend_position"]) == "none"
    assert trace["render_map"]["legend_entry_bboxes_px"] == {}
    assert "REF" not in out.prompt

    regions_by_id = _regions_by_id(execution)
    reference_region_id = str(qparams["reference_region_id"])
    assert bool(regions_by_id[reference_region_id]["is_reference_region"])
    assert reference_region_id not in set(trace["projected_evidence"]["region_ids"])

    reference_asset_id = str(qparams["reference_asset_region_id"])
    border_lengths = _world_country_shared_border_lengths()
    min_border = float(qparams["border_min_shared_length_deg"])
    evidence_asset_ids = {
        str(regions_by_id[str(region_id)]["asset_region_id"])
        for region_id in trace["projected_evidence"]["region_ids"]
    }
    expected_neighbor_asset_ids = {str(value) for value in qparams["target_border_neighbor_asset_ids"]}
    assert evidence_asset_ids == expected_neighbor_asset_ids
    assert all(
        float(border_lengths[reference_asset_id][neighbor_asset_id]) >= min_border
        for neighbor_asset_id in evidence_asset_ids
    )


@pytest.mark.parametrize("query_id", SUPPORTED_ADJACENT_QUERY_IDS)
def test_chart_map_adjacent_condition_count_uses_highlighted_reference(query_id: str) -> None:
    task = ChartsMapAdjacentConditionCountTask()
    out = task.generate(
        67400 + SUPPORTED_ADJACENT_QUERY_IDS.index(query_id),
        params={"query_id": query_id, "scene_variant": "synthetic_region_map"},
        max_attempts=10,
    )
    _assert_common_output(out)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    qparams = trace["query_spec"]["params"]
    regions_by_id = _regions_by_id(execution)

    assert out.query_id == query_id
    reference_region_id = str(qparams["reference_region_id"])
    assert bool(regions_by_id[reference_region_id]["is_reference_region"])
    assert reference_region_id not in set(trace["projected_evidence"]["region_ids"])
    assert set(trace["projected_evidence"]["region_ids"]).issubset(set(qparams["adjacent_neighbor_region_ids"]))

    evidence_ids = [str(region_id) for region_id in trace["projected_evidence"]["region_ids"]]
    if query_id == "adjacent_same_category_count":
        reference_category = str(regions_by_id[reference_region_id]["category"])
        assert all(str(regions_by_id[region_id]["category"]) == reference_category for region_id in evidence_ids)
    elif query_id == "adjacent_category_count":
        target_category = str(qparams["category_label"])
        assert all(str(regions_by_id[region_id]["category"]) == target_category for region_id in evidence_ids)
    else:
        target_bins = {int(value) for value in qparams["target_bin_indices"]}
        assert all(int(regions_by_id[region_id]["bin_index"]) in target_bins for region_id in evidence_ids)


def test_chart_map_tasks_prompt_examples_match_contract() -> None:
    expected = [
        (ChartsMapLegendPredicateRegionCountTask, "numeric_interval_region_count", 4),
        (ChartsMapLegendPredicateRegionCountTask, "categorical_region_count", 3),
        (ChartsMapAdjacentConditionCountTask, "adjacent_same_category_count", 2),
    ]
    for index, (task_cls, query_id, answer) in enumerate(expected, start=67500):
        out = task_cls().generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence["answer"] == answer
        assert answer_only == {"answer": answer}
        assert isinstance(answer_and_evidence["evidence"], list)


def test_chart_map_task_sampling_covers_map_scene_types() -> None:
    task = ChartsMapLegendPredicateRegionCountTask()
    scenes: Counter[str] = Counter()
    map_variants: Counter[str] = Counter()
    query_ids: Counter[str] = Counter()
    for index in range(24):
        out = task.generate(hash64(67600, "charts_map", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        scenes[str(execution["scene_variant"])] += 1
        query_ids[str(out.query_id)] += 1
        if str(execution["scene_variant"]) == "geographic_region_map":
            map_variants[str(execution["geographic_map_variant"])] += 1
    assert set(scenes.keys()) == {"synthetic_region_map", "geographic_region_map"}
    assert set(query_ids.keys()) == set(SUPPORTED_REGION_VALUE_QUERY_IDS).union({"categorical_region_count"})
    assert set(map_variants.keys()).issubset({"world_countries", "usa_states", "eu_countries", "china_provinces"})


@pytest.mark.parametrize(
    ("task_cls", "expected_query_id", "expected_answer_type"),
    [
        (ChartsMapMarkerRegionThresholdCountTask, "marker_region_threshold_count", "integer"),
        (ChartsMapMarkerRegionExtremumLabelTask, "marker_region_extremum_label", "string"),
    ],
)
def test_chart_map_marker_tasks_use_marker_bubble_evidence(task_cls, expected_query_id: str, expected_answer_type: str) -> None:
    task = task_cls()
    for index, render_variant in enumerate(SUPPORTED_MARKER_RENDER_VARIANTS):
        out = task.generate(
            hash64(67700 + index, f"{expected_query_id}.{render_variant}", index),
            params={"marker_render_variant": render_variant, "scene_variant": "synthetic_region_map"},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        projected = trace["projected_evidence"]

        assert out.query_id == expected_query_id
        assert out.query_id == "default"
        assert out.scene_id == "marker_map"
        assert out.answer_gt.type == expected_answer_type
        assert out.evidence_gt.type == "bbox_set"
        assert str(execution["question_format"]) == "map_marker_query"
        assert str(execution["query_id"]) == "default"
        assert str(trace["query_spec"]["params"]["marker_render_variant"]) == render_variant
        assert str(render["marker_render"]["marker_render_variant"]) == render_variant
        assert projected["bbox_set"] == out.evidence_gt.value
        assert projected["marker_bboxes_by_region"]
        assert len(out.evidence_gt.value) >= 1
        assert "marker" in out.prompt.lower()
        assert "choropleth" not in out.prompt.lower()
        marker_label_entities = [
            entity for entity in trace["scene_ir"]["entities"] if str(entity.get("entity_type")) == "map_marker_label"
        ]
        for bbox in out.evidence_gt.value:
            _assert_bbox_inside_canvas(
                [float(value) for value in bbox],
                width=int(render["canvas_width"]),
                height=int(render["canvas_height"]),
            )
        if expected_answer_type == "integer":
            assert not marker_label_entities
            assert "labeled" not in out.prompt.lower()
            assert int(out.answer_gt.value) == len(projected["marker_bboxes_by_region"])
        else:
            assert marker_label_entities
            answer = str(out.answer_gt.value)
            region_id = str(trace["query_spec"]["params"]["answer_region_id"])
            assert str(execution["regions_by_id"][region_id]["marker_label"]) == answer
