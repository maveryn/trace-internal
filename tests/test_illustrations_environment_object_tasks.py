"""Tests for illustration environment-object tasks."""

from __future__ import annotations

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.illustrations.environment.shared.rendering import (
    BRIDGE_STYLE_IDS,
    BUILDING_STYLE_IDS,
    RIVER_STYLE_IDS,
    ROAD_STYLE_IDS,
)


def test_feature_side_object_count_contracts() -> None:
    scenarios = (
        ("park_road", "road", "above"),
        ("river_meadow", "river", "below"),
        ("road_and_river", "road", "below"),
        ("road_and_river", "river", "above"),
        ("canal_city", "river", "below"),
        ("skyline_street", "road", "above"),
    )
    for index, (theme_id, feature_type, relation) in enumerate(scenarios):
        out = create_task("task_illustrations__environment__feature_side_object_count").generate(
            hash64(2026052101, f"{theme_id}:{feature_type}:{relation}", index),
            params={
                "theme_id": theme_id,
                "feature_type": feature_type,
                "relation": relation,
                "object_count": 14,
                "target_count_min": 1,
            },
            max_attempts=300,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render_map = trace["render_map"]
        assert out.scene_id == "environment"
        assert out.query_id == "single"
        assert execution["theme_id"] == theme_id
        assert execution["feature_type"] == feature_type
        assert execution["relation"] == relation
        layout = trace["render_spec"]["style"]["layout"]
        assert layout["road_style_id"] in ROAD_STYLE_IDS
        assert layout["river_style_id"] in RIVER_STYLE_IDS
        assert layout["bridge_style_id"] in BRIDGE_STYLE_IDS
        target_feature = next(
            entity
            for entity in trace["scene_ir"]["entities"]
            if entity["entity_type"] == "environment_feature" and entity["entity_id"] == execution["feature_id"]
        )
        if feature_type == "road":
            assert target_feature["attributes"]["road_style_id"] in ROAD_STYLE_IDS
        else:
            assert target_feature["attributes"]["river_style_id"] in RIVER_STYLE_IDS
        assert int(out.answer_gt.value) == len(execution["counted_object_ids"])
        assert len(out.annotation_gt.value) == int(out.answer_gt.value)
        assert execution["feature_id"] in render_map["feature_bboxes_px"]
        assert execution["feature_id"] in render_map["feature_paths_px"]
        assert render_map["counted_object_ids"] == execution["counted_object_ids"]
        expected = [render_map["object_bboxes_px"][object_id] for object_id in execution["counted_object_ids"]]
        assert sorted(out.annotation_gt.value) == sorted(expected)
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value


def test_on_feature_object_count_contract() -> None:
    out = create_task("task_illustrations__environment__on_feature_object_count").generate(
        hash64(2026052302, "on-feature", 0),
        params={"theme_id": "road_and_river", "feature_type": "river", "object_count": 14},
        max_attempts=400,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render_map = trace["render_map"]
    assert out.scene_id == "environment"
    assert out.query_id == "single"
    assert execution["feature_type"] == "river"
    feature_types = {entity["feature_type"] for entity in trace["scene_ir"]["entities"] if entity["entity_type"] == "environment_feature"}
    assert "bridge" not in feature_types
    assert "crosswalk" not in feature_types
    assert int(out.answer_gt.value) == len(execution["counted_object_ids"])
    assert all(execution["object_zones"][object_id] == "river" for object_id in execution["counted_object_ids"])
    expected = [render_map["object_bboxes_px"][object_id] for object_id in execution["counted_object_ids"]]
    assert sorted(out.annotation_gt.value) == sorted(expected)


def test_crossing_feature_count_contract() -> None:
    out = create_task("task_illustrations__environment__crossing_feature_count").generate(
        hash64(2026052302, "crossing-feature", 0),
        params={"crossing_type": "bridge", "theme_id": "canal_city", "object_count": 12},
        max_attempts=300,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render_map = trace["render_map"]
    assert out.scene_id == "environment"
    assert out.query_id == "single"
    assert execution["crossing_type"] == "bridge"
    bridge_features = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if entity["entity_type"] == "environment_feature" and entity["entity_id"] in set(execution["counted_feature_ids"])
    ]
    assert bridge_features
    assert all(feature["attributes"]["bridge_style_id"] in BRIDGE_STYLE_IDS for feature in bridge_features)
    assert int(out.answer_gt.value) == len(execution["counted_feature_ids"])
    expected = [render_map["feature_bboxes_px"][feature_id] for feature_id in execution["counted_feature_ids"]]
    assert sorted(out.annotation_gt.value) == sorted(expected)


def test_building_window_count_contract() -> None:
    out = create_task("task_illustrations__environment__lit_window_count").generate(
        hash64(2026052302, "building-window", 0),
        params={"theme_id": "skyline_street", "target_count": 6, "object_count": 10},
        max_attempts=300,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render_map = trace["render_map"]
    assert out.scene_id == "environment"
    assert out.query_id == "single"
    assert execution["window_mode"] == "lit"
    assert int(out.answer_gt.value) == 6
    assert int(out.answer_gt.value) == len(execution["counted_window_ids"])
    buildings = [entity for entity in trace["scene_ir"]["entities"] if entity["entity_type"] == "environment_building"]
    assert buildings
    assert all(building["attributes"]["building_style_id"] in BUILDING_STYLE_IDS for building in buildings)
    expected = [render_map["window_bboxes_px"][window_id] for window_id in execution["counted_window_ids"]]
    assert sorted(out.annotation_gt.value) == sorted(expected)
