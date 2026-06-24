from __future__ import annotations

from trace.tasks.registry import TASK_REGISTRY, create_task
from trace.tasks.illustrations.isometric_harbor.boat_side_count import (
    QUERY_TO_SIDE,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
)
from trace.tasks.illustrations.isometric_harbor.boat_mooring_status_count import (
    QUERY_TO_STATUS,
    SUPPORTED_QUERY_IDS as MOORING_SUPPORTED_QUERY_IDS,
    TASK_ID as MOORING_TASK_ID,
)
from trace.tasks.illustrations.isometric_harbor.shared.rendering import (
    RENDERER_ID,
    SCENE_ID,
    render_isometric_harbor_scene,
)
from trace.tasks.illustrations.isometric_harbor.shared.spatial_primitives import dock_is_connected


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= float(width)
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= float(height)


def test_isometric_harbor_renderer_is_deterministic_and_profile_safe() -> None:
    for width, height, profile, expected_grid in (
        (1200, 800, "landscape", (16, 12)),
        (960, 960, "square", (14, 14)),
    ):
        first = render_isometric_harbor_scene(
            2026062501,
            width=width,
            height=height,
            canvas_profile=profile,
            canvas_profile_probabilities={profile: 1.0},
            required_boat_counts_by_side={"left": 5, "right": 0},
        )
        second = render_isometric_harbor_scene(
            2026062501,
            width=width,
            height=height,
            canvas_profile=profile,
            canvas_profile_probabilities={profile: 1.0},
            required_boat_counts_by_side={"left": 5, "right": 0},
        )
        assert first.image.size == (width, height)
        assert first.image.tobytes() == second.image.tobytes()
        assert first.trace["renderer_id"] == RENDERER_ID
        assert first.trace["renderer_style"] == "isometric_pixel_harbor"
        assert first.trace["theme_id"] == "isometric_harbor_shoreline_dock"
        assert first.trace["background_rgb"] == [207, 220, 190]
        assert first.trace["projection"]["type"] == "2:1_isometric"
        assert (int(first.trace["grid_cols"]), int(first.trace["grid_rows"])) == expected_grid
        assert first.trace["boat_counts_by_side"] == {"left": 5, "right": 0}
        assert first.trace["boat_counts_by_mooring_status"] == {"moored": 5, "open_water": 0}
        assert first.trace["context_object_counts"]["boat"] == 5
        assert dock_is_connected(first)
        assert {str(tile.terrain) for tile in first.tiles} == {"dock", "land", "water"}
        assert first.trace["terrain_tile_counts"]["land"] > 0
        assert first.trace["terrain_tile_counts"]["water"] > first.trace["terrain_tile_counts"]["land"]
        assert first.trace["terrain_tile_counts"]["dock"] == len(first.trace["dock_tile_ids"])
        for tile in first.tiles:
            _assert_bbox_inside_canvas(list(tile.bbox_xyxy), width=width, height=height)
        for entity in first.entities:
            _assert_bbox_inside_canvas(list(entity.bbox_xyxy), width=width, height=height)


def test_isometric_harbor_renderer_supports_open_water_boats() -> None:
    scene = render_isometric_harbor_scene(
        2026062602,
        width=1200,
        height=800,
        canvas_profile="landscape",
        required_moored_boat_count=3,
        required_open_water_boat_count=5,
    )
    boats = [entity for entity in scene.entities if entity.object_type == "boat"]
    moored = [entity for entity in boats if entity.metadata.get("mooring_status") == "moored"]
    open_water = [entity for entity in boats if entity.metadata.get("mooring_status") == "open_water"]
    assert len(moored) == 3
    assert len(open_water) == 5
    assert scene.trace["boat_counts_by_mooring_status"] == {"moored": 3, "open_water": 5}
    assert {str(entity.metadata.get("orientation")) for entity in open_water}
    for entity in open_water:
        assert "dock_side" not in entity.metadata
        assert len(entity.tile_ids) == 1
        tile = next(tile for tile in scene.tiles if tile.tile_id == entity.tile_ids[0])
        assert tile.terrain == "water"
        _assert_bbox_inside_canvas(list(entity.bbox_xyxy), width=scene.image.size[0], height=scene.image.size[1])


def test_isometric_harbor_boat_side_count_contract() -> None:
    task = create_task(TASK_ID)
    cases = (
        ("left_side_boat_count", 0, "landscape", "image-left"),
        ("right_side_boat_count", 5, "square", "image-right"),
    )
    for query_id, target_count, profile, prompt_side in cases:
        out = task.generate(
            2026062511 + int(target_count),
            params={"query_id": query_id, "target_count": target_count, "canvas_profile": profile},
            max_attempts=4,
        )
        assert out.scene_id == SCENE_ID
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == int(target_count)
        assert out.annotation_gt.type == "bbox_set"
        assert len(out.annotation_gt.value) == int(target_count)
        assert prompt_side in out.prompt
        trace = out.trace_payload
        assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_isometric_harbor_v1"
        assert trace["query_spec"]["prompt_variant"]["prompt_schema_version"] == "v1"
        assert trace["query_spec"]["params"]["target_side"] == QUERY_TO_SIDE[query_id]
        assert trace["execution_trace"]["answer"] == int(target_count)
        assert trace["render_map"]["answer_count"] == int(target_count)
        assert trace["render_map"]["target_side"] == QUERY_TO_SIDE[query_id]
        assert len(trace["render_map"]["counted_entity_ids"]) == int(target_count)
        assert len(trace["projected_annotation"]["bbox_set"]) == int(target_count)
        if int(target_count) == 0:
            assert out.annotation_gt.value == []
        for bbox in out.annotation_gt.value:
            _assert_bbox_inside_canvas(list(bbox), width=out.image.size[0], height=out.image.size[1])


def test_isometric_harbor_boat_mooring_status_count_contract() -> None:
    task = create_task(MOORING_TASK_ID)
    cases = (
        ("moored_boat_count", 0, 3, "landscape", "tied along the main dock"),
        ("open_water_boat_count", 5, 2, "square", "open water"),
    )
    for query_id, target_count, other_count, profile, prompt_text in cases:
        out = task.generate(
            2026062711 + int(target_count),
            params={
                "query_id": query_id,
                "target_count": target_count,
                "other_count": other_count,
                "canvas_profile": profile,
            },
            max_attempts=4,
        )
        assert out.scene_id == SCENE_ID
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == int(target_count)
        assert out.annotation_gt.type == "bbox_set"
        assert len(out.annotation_gt.value) == int(target_count)
        assert prompt_text in out.prompt
        trace = out.trace_payload
        assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_isometric_harbor_v1"
        assert trace["query_spec"]["params"]["target_mooring_status"] == QUERY_TO_STATUS[query_id]
        assert trace["execution_trace"]["answer"] == int(target_count)
        assert trace["render_map"]["answer_count"] == int(target_count)
        assert trace["render_map"]["target_mooring_status"] == QUERY_TO_STATUS[query_id]
        assert len(trace["render_map"]["counted_entity_ids"]) == int(target_count)
        assert len(trace["projected_annotation"]["bbox_set"]) == int(target_count)
        for bbox in out.annotation_gt.value:
            _assert_bbox_inside_canvas(list(bbox), width=out.image.size[0], height=out.image.size[1])


def test_isometric_harbor_task_registered() -> None:
    task = create_task(TASK_ID)
    mooring_task = create_task(MOORING_TASK_ID)
    assert TASK_ID in TASK_REGISTRY
    assert MOORING_TASK_ID in TASK_REGISTRY
    assert task.domain == "illustrations"
    assert mooring_task.domain == "illustrations"
    assert tuple(task.supported_query_ids) == SUPPORTED_QUERY_IDS
    assert tuple(mooring_task.supported_query_ids) == MOORING_SUPPORTED_QUERY_IDS
