"""Behavior tests for chart map-region tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.region_map.adjacent_category_count import (
    QUERY_ID as ADJACENT_CATEGORY_QUERY_ID,
    ChartsMapAdjacentCategoryCountTask,
)
from trace.tasks.charts.region_map.adjacent_numeric_threshold_count import (
    QUERY_ID as ADJACENT_NUMERIC_THRESHOLD_QUERY_ID,
    ChartsMapAdjacentNumericThresholdCountTask,
)
from trace.tasks.charts.region_map.adjacent_same_category_count import (
    QUERY_ID as ADJACENT_SAME_CATEGORY_QUERY_ID,
    ChartsMapAdjacentSameCategoryCountTask,
)
from trace.tasks.charts.region_map.categorical_region_count import (
    QUERY_ID as CATEGORICAL_REGION_QUERY_ID,
    ChartsMapCategoricalRegionCountTask,
)
from trace.tasks.charts.region_map.continent_category_region_count import (
    QUERY_ID as CONTINENT_CATEGORY_REGION_QUERY_ID,
    ChartsMapContinentCategoryRegionCountTask,
)
from trace.tasks.charts.region_map.continent_region_count import (
    QUERY_ID as CONTINENT_REGION_QUERY_ID,
    ChartsMapContinentRegionCountTask,
)
from trace.tasks.charts.region_map.continent_threshold_region_count import (
    QUERY_ID as CONTINENT_THRESHOLD_REGION_QUERY_ID,
    ChartsMapContinentThresholdRegionCountTask,
)
from trace.tasks.charts.region_map.group_filtered_region_value import (
    ChartsMapGroupFilteredRegionValueTask,
)
from trace.tasks.charts.region_map.named_region_set_total_value import (
    ChartsMapNamedRegionSetTotalValueTask,
)
from trace.tasks.charts.region_map.numeric_interval_region_count import (
    QUERY_ID as NUMERIC_INTERVAL_REGION_QUERY_ID,
    ChartsMapNumericIntervalRegionCountTask,
)
from trace.tasks.charts.region_map.numeric_threshold_region_count import (
    QUERY_ID as NUMERIC_THRESHOLD_REGION_QUERY_ID,
    ChartsMapNumericThresholdRegionCountTask,
)
from trace.tasks.charts.marker_map.marker_region_extremum_label import (
    LARGEST_QUERY_ID as MARKER_MAP_LARGEST_QUERY_ID,
    SMALLEST_QUERY_ID as MARKER_MAP_SMALLEST_QUERY_ID,
    ChartsMarkerMapMarkerRegionExtremumLabelTask,
)
from trace.tasks.charts.marker_map.marker_region_threshold_count import (
    GREATER_THAN_QUERY_ID as MARKER_MAP_GREATER_THAN_QUERY_ID,
    LESS_THAN_QUERY_ID as MARKER_MAP_LESS_THAN_QUERY_ID,
    ChartsMarkerMapMarkerRegionThresholdCountTask,
)


REGION_VALUE_TASKS = {
    "numeric_threshold_region_count": ChartsMapNumericThresholdRegionCountTask,
    "numeric_interval_region_count": ChartsMapNumericIntervalRegionCountTask,
    "categorical_region_count": ChartsMapCategoricalRegionCountTask,
}
SUPPORTED_REGION_VALUE_QUERY_IDS = (
    NUMERIC_THRESHOLD_REGION_QUERY_ID,
    NUMERIC_INTERVAL_REGION_QUERY_ID,
    CATEGORICAL_REGION_QUERY_ID,
)
WORLD_FILTERED_TASKS = {
    "continent_region_count": ChartsMapContinentRegionCountTask,
    "continent_category_region_count": ChartsMapContinentCategoryRegionCountTask,
    "continent_threshold_region_count": ChartsMapContinentThresholdRegionCountTask,
}
SUPPORTED_WORLD_FILTERED_QUERY_IDS = (
    CONTINENT_REGION_QUERY_ID,
    CONTINENT_CATEGORY_REGION_QUERY_ID,
    CONTINENT_THRESHOLD_REGION_QUERY_ID,
)
ADJACENT_TASKS = {
    "adjacent_same_category_count": ChartsMapAdjacentSameCategoryCountTask,
    "adjacent_category_count": ChartsMapAdjacentCategoryCountTask,
    "adjacent_numeric_threshold_count": ChartsMapAdjacentNumericThresholdCountTask,
}
SUPPORTED_ADJACENT_QUERY_IDS = (
    ADJACENT_SAME_CATEGORY_QUERY_ID,
    ADJACENT_CATEGORY_QUERY_ID,
    ADJACENT_NUMERIC_THRESHOLD_QUERY_ID,
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
    assert out.annotation_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert str(execution["scene_variant"]) in {"synthetic_region_map", "geographic_region_map"}
    assert str(execution["question_format"]) == "map_region_count"
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert trace["projected_annotation"]["type"] == "bbox_set"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_bbox_set"] == out.annotation_gt.value
    assert len(trace["projected_annotation"]["region_ids"]) == int(out.answer_gt.value)
    assert "background_style" in render
    assert str(render["font_assets"]["font_asset_version"])
    assert str(render["font_assets"]["chart_font_family"])
    assert "choropleth" not in out.prompt.lower()
    for bbox in out.annotation_gt.value:
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
    task = REGION_VALUE_TASKS[str(query_id)]()
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
    task = ChartsMapCategoricalRegionCountTask()
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
    for region_id in trace["projected_annotation"]["region_ids"]:
        assert str(_regions_by_id(execution)[str(region_id)]["category"]) == target_category


@pytest.mark.parametrize("query_id", SUPPORTED_WORLD_FILTERED_QUERY_IDS)
def test_chart_map_continent_filtered_count_uses_world_map_filter(query_id: str) -> None:
    task = WORLD_FILTERED_TASKS[str(query_id)]()
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
    annotation_ids = [str(region_id) for region_id in trace["projected_annotation"]["region_ids"]]
    assert all(str(regions_by_id[region_id]["continent"]) == continent for region_id in annotation_ids)

    if str(query_id) == "continent_category_region_count":
        target_category = str(qparams["category_label"])
        assert all(str(regions_by_id[region_id]["category"]) == target_category for region_id in annotation_ids)
    elif str(query_id) == "continent_threshold_region_count":
        target_bins = {int(value) for value in qparams["target_bin_indices"]}
        assert all(int(regions_by_id[region_id]["bin_index"]) in target_bins for region_id in annotation_ids)


def test_chart_map_named_region_set_total_value_sums_visible_labeled_regions() -> None:
    task = ChartsMapNamedRegionSetTotalValueTask()
    out = task.generate(67350, params={"scene_variant": "synthetic_region_map"}, max_attempts=10)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    qparams = trace["query_spec"]["params"]
    regions_by_id = _regions_by_id(execution)
    annotation_ids = [str(region_id) for region_id in trace["projected_annotation"]["region_ids"]]

    assert out.query_id == "named_region_set_total_value"
    assert out.scene_id == "region_map"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert str(execution["question_format"]) == "map_region_value"
    assert str(qparams["region_set_label_list"])
    assert annotation_ids == [str(region_id) for region_id in qparams["region_set_region_ids"]]
    assert int(out.answer_gt.value) == sum(int(regions_by_id[region_id]["region_value"]) for region_id in annotation_ids)
    assert all(str(regions_by_id[region_id]["region_label"]) for region_id in annotation_ids)
    assert any(str(entity.get("entity_type")) == "map_region_value_label" for entity in trace["scene_ir"]["entities"])


def test_chart_map_group_filtered_region_value_uses_geographic_group_and_threshold() -> None:
    task = ChartsMapGroupFilteredRegionValueTask()
    out = task.generate(67375, params={}, max_attempts=10)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    qparams = trace["query_spec"]["params"]
    regions_by_id = _regions_by_id(execution)
    annotation_ids = [str(region_id) for region_id in trace["projected_annotation"]["region_ids"]]

    assert out.query_id == "group_filtered_region_value"
    assert out.scene_id == "region_map"
    assert str(execution["scene_variant"]) == "geographic_region_map"
    assert str(execution["geographic_map_variant"]) == "world_countries"
    assert str(execution["question_format"]) == "map_region_value"
    assert int(out.answer_gt.value) == sum(int(regions_by_id[region_id]["region_value"]) for region_id in annotation_ids)

    continent = str(qparams["continent_label"])
    target_bins = {int(value) for value in qparams["target_bin_indices"]}
    assert continent in {"Africa", "Asia", "Europe", "North America", "South America"}
    assert all(str(regions_by_id[region_id]["continent"]) == continent for region_id in annotation_ids)
    assert all(int(regions_by_id[region_id]["bin_index"]) in target_bins for region_id in annotation_ids)
    for region_id in qparams["same_group_distractor_region_ids"]:
        if str(region_id) in regions_by_id:
            assert str(regions_by_id[str(region_id)]["continent"]) == continent
            assert int(regions_by_id[str(region_id)]["bin_index"]) not in target_bins


@pytest.mark.parametrize("query_id", SUPPORTED_ADJACENT_QUERY_IDS)
def test_chart_map_adjacent_condition_count_uses_highlighted_reference(query_id: str) -> None:
    task = ADJACENT_TASKS[str(query_id)]()
    out = task.generate(
        67400 + SUPPORTED_ADJACENT_QUERY_IDS.index(query_id),
        params={"query_id": query_id, "scene_variant": "geographic_region_map"},
        max_attempts=10,
    )
    _assert_common_output(out)
    trace = out.trace_payload
    execution = trace["execution_trace"]
    qparams = trace["query_spec"]["params"]
    regions_by_id = _regions_by_id(execution)

    assert out.query_id == query_id
    assert str(execution["scene_variant"]) == "synthetic_region_map"
    reference_region_id = str(qparams["reference_region_id"])
    assert bool(regions_by_id[reference_region_id]["is_reference_region"])
    assert reference_region_id not in set(trace["projected_annotation"]["region_ids"])
    assert set(trace["projected_annotation"]["region_ids"]).issubset(set(qparams["adjacent_neighbor_region_ids"]))

    annotation_ids = [str(region_id) for region_id in trace["projected_annotation"]["region_ids"]]
    if query_id == "adjacent_same_category_count":
        reference_category = str(regions_by_id[reference_region_id]["category"])
        assert all(str(regions_by_id[region_id]["category"]) == reference_category for region_id in annotation_ids)
    elif query_id == "adjacent_category_count":
        target_category = str(qparams["category_label"])
        assert all(str(regions_by_id[region_id]["category"]) == target_category for region_id in annotation_ids)
    else:
        target_bins = {int(value) for value in qparams["target_bin_indices"]}
        assert all(int(regions_by_id[region_id]["bin_index"]) in target_bins for region_id in annotation_ids)


def test_chart_map_tasks_prompt_examples_match_contract() -> None:
    expected = [
        (ChartsMapNumericIntervalRegionCountTask, "numeric_interval_region_count", 4),
        (ChartsMapCategoricalRegionCountTask, "categorical_region_count", 3),
        (ChartsMapNamedRegionSetTotalValueTask, "named_region_set_total_value", 126),
        (ChartsMapAdjacentSameCategoryCountTask, "adjacent_same_category_count", 2),
    ]
    for index, (task_cls, query_id, answer) in enumerate(expected, start=67500):
        out = task_cls().generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation["answer"] == answer
        assert answer_only == {"answer": answer}
        assert isinstance(answer_and_annotation["annotation"], list)


def test_chart_map_task_sampling_covers_map_scene_types() -> None:
    scenes: Counter[str] = Counter()
    map_variants: Counter[str] = Counter()
    query_ids: Counter[str] = Counter()
    for index in range(24):
        query_id = SUPPORTED_REGION_VALUE_QUERY_IDS[int(index) % len(SUPPORTED_REGION_VALUE_QUERY_IDS)]
        task = REGION_VALUE_TASKS[str(query_id)]()
        out = task.generate(hash64(67600, "charts_map", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        scenes[str(execution["scene_variant"])] += 1
        query_ids[str(out.query_id)] += 1
        if str(execution["scene_variant"]) == "geographic_region_map":
            map_variants[str(execution["geographic_map_variant"])] += 1
    assert set(scenes.keys()) == {"synthetic_region_map", "geographic_region_map"}
    assert set(query_ids.keys()) == set(SUPPORTED_REGION_VALUE_QUERY_IDS)
    assert set(map_variants.keys()).issubset({"world_countries", "usa_states", "eu_countries", "china_provinces"})


@pytest.mark.parametrize(
    ("task_cls", "expected_query_id", "expected_answer_type", "expected_annotation_type"),
    [
        (ChartsMarkerMapMarkerRegionThresholdCountTask, MARKER_MAP_GREATER_THAN_QUERY_ID, "integer", "bbox_set"),
        (ChartsMarkerMapMarkerRegionThresholdCountTask, MARKER_MAP_LESS_THAN_QUERY_ID, "integer", "bbox_set"),
        (ChartsMarkerMapMarkerRegionExtremumLabelTask, MARKER_MAP_LARGEST_QUERY_ID, "string", "bbox"),
        (ChartsMarkerMapMarkerRegionExtremumLabelTask, MARKER_MAP_SMALLEST_QUERY_ID, "string", "bbox"),
    ],
)
def test_chart_map_marker_tasks_use_marker_bubble_annotation(
    task_cls,
    expected_query_id: str,
    expected_answer_type: str,
    expected_annotation_type: str,
) -> None:
    task = task_cls()
    render_variant = "proportional_bubble"
    out = task.generate(
        hash64(67700, f"{expected_query_id}.{render_variant}"),
        params={"query_id": expected_query_id, "scene_variant": "synthetic_region_map"},
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    projected = trace["projected_annotation"]

    assert out.query_id == expected_query_id
    assert out.scene_id == "marker_map"
    assert out.answer_gt.type == expected_answer_type
    assert out.annotation_gt.type == expected_annotation_type
    assert str(execution["question_format"]) == "map_marker_query"
    assert str(execution["query_id"]) == expected_query_id
    assert str(trace["query_spec"]["params"]["marker_render_variant"]) == render_variant
    assert str(render["marker_render"]["marker_render_variant"]) == render_variant
    assert str(render["font_assets"]["font_asset_version"])
    assert str(render["font_assets"]["chart_font_family"])
    assert projected["type"] == expected_annotation_type
    assert projected["marker_bboxes_by_region"]
    if expected_annotation_type == "bbox_set":
        assert projected["bbox_set"] == out.annotation_gt.value
        assert len(out.annotation_gt.value) == len(projected["region_ids"])
        assert out.annotation_gt.value == [projected["bbox_map"][str(region_id)] for region_id in projected["region_ids"]]
        assert len(out.annotation_gt.value) >= 1
        bboxes_to_check = out.annotation_gt.value
    else:
        assert projected["bbox"] == out.annotation_gt.value
        assert len(projected["region_ids"]) == 1
        assert out.annotation_gt.value == projected["bbox_map"][str(projected["region_id"])]
        bboxes_to_check = [out.annotation_gt.value]
    assert "marker" in out.prompt.lower()
    assert "choropleth" not in out.prompt.lower()
    marker_label_entities = [
        entity for entity in trace["scene_ir"]["entities"] if str(entity.get("entity_type")) == "map_marker_label"
    ]
    for bbox in bboxes_to_check:
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
