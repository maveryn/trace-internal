from __future__ import annotations

from trace.tasks.registry import TASK_REGISTRY, create_task
from trace.tasks.illustrations.isometric_harbor.boat_side_count import (
    QUERY_TO_SIDE,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
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
        assert first.trace["projection"]["type"] == "2:1_isometric"
        assert (int(first.trace["grid_cols"]), int(first.trace["grid_rows"])) == expected_grid
        assert first.trace["boat_counts_by_side"] == {"left": 5, "right": 0}
        assert first.trace["context_object_counts"]["boat"] == 5
        assert dock_is_connected(first)
        assert {str(tile.terrain) for tile in first.tiles} == {"dock", "water"}
        for tile in first.tiles:
            _assert_bbox_inside_canvas(list(tile.bbox_xyxy), width=width, height=height)
        for entity in first.entities:
            _assert_bbox_inside_canvas(list(entity.bbox_xyxy), width=width, height=height)


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


def test_isometric_harbor_task_registered() -> None:
    task = create_task(TASK_ID)
    assert TASK_ID in TASK_REGISTRY
    assert task.domain == "illustrations"
    assert tuple(task.supported_query_ids) == SUPPORTED_QUERY_IDS
