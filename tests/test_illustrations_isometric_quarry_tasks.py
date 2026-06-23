from __future__ import annotations

from trace.tasks.registry import TASK_REGISTRY, create_task
from trace.tasks.illustrations.isometric_quarry.shared.rendering import (
    SCENE_ID,
    SUPPORTED_LEVELS,
    render_isometric_quarry_scene,
)
from trace.tasks.illustrations.isometric_quarry.terrain_elevation_extremum_label import (
    SUPPORTED_QUERY_IDS as ELEVATION_QUERY_IDS,
    TASK_ID as ELEVATION_TASK_ID,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= float(width)
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= float(height)


def _assert_no_one_tile_terrace_border_gap(trace: dict) -> None:
    cols = int(trace["grid_cols"])
    rows = int(trace["grid_rows"])
    for rects in trace["level_shapes"].values():
        for x, y, w, h in rects:
            assert int(x) != 1
            assert int(y) != 1
            assert int(cols) - (int(x) + int(w)) != 1
            assert int(rows) - (int(y) + int(h)) != 1


def _assert_no_entity_on_unsafe_tile(scene: object) -> None:
    unsafe_ids = set(str(value) for value in scene.trace["object_unsafe_low_adjacent_higher_tile_ids"])
    for entity in scene.entities:
        assert not unsafe_ids.intersection(str(tile_id) for tile_id in entity.tile_ids)


def test_isometric_quarry_renderer_is_deterministic_and_profile_safe() -> None:
    for width, height, profile, expected_grid in (
        (1200, 800, "landscape", (16, 12)),
        (960, 960, "square", (14, 14)),
    ):
        first = render_isometric_quarry_scene(
            2026062401,
            width=width,
            height=height,
            canvas_profile=profile,
            canvas_profile_probabilities={profile: 1.0},
        )
        second = render_isometric_quarry_scene(
            2026062401,
            width=width,
            height=height,
            canvas_profile=profile,
            canvas_profile_probabilities={profile: 1.0},
        )
        assert first.image.size == (width, height)
        assert first.image.tobytes() == second.image.tobytes()
        assert first.trace["renderer_id"] == "isometric_quarry_v0"
        assert first.trace["renderer_style"] == "isometric_pixel_quarry"
        assert first.trace["projection"]["type"] == "2:1_isometric"
        assert (int(first.trace["grid_cols"]), int(first.trace["grid_rows"])) == expected_grid
        assert first.trace["supported_levels"] == list(SUPPORTED_LEVELS)
        active_levels = [int(level) for level in first.trace["levels"]]
        assert active_levels[0] == 0
        assert 1 <= int(first.trace["active_max_level"]) <= 2
        assert active_levels == list(range(0, int(first.trace["active_max_level"]) + 1))
        assert first.trace["layout_family"] not in {"diagonal_ridge", "stepped_hillside"}
        _assert_no_one_tile_terrace_border_gap(first.trace)
        _assert_no_entity_on_unsafe_tile(first)
        assert first.trace["quarry_patches"]
        assert first.trace["context_object_counts"]["quarry_object"] >= 4
        assert first.trace["transition_tile_ids"] == []
        assert first.transitions == ()
        assert first.trace["eligible_tile_ids"]
        assert {str(tile.terrain) for tile in first.tiles}.issuperset({"rock"})
        assert all(str(entity.object_type) == "quarry_object" for entity in first.entities)
        for tile in first.tiles:
            _assert_bbox_inside_canvas(list(tile.bbox_xyxy), width=width, height=height)
        for entity in first.entities:
            _assert_bbox_inside_canvas(list(entity.bbox_xyxy), width=width, height=height)


def test_isometric_quarry_elevation_task_contract() -> None:
    task = create_task(ELEVATION_TASK_ID)
    cases = (
        ("highest_terrain_tile", "landscape", 2026062411),
        ("lowest_terrain_tile", "square", 2026062412),
        ("highest_terrain_tile", "landscape", 2026062413),
        ("lowest_terrain_tile", "square", 2026062414),
    )
    for query_id, profile, seed in cases:
        out = task.generate(
            seed,
            params={"query_id": query_id, "canvas_profile": profile, "candidate_count": 4},
            max_attempts=40,
        )
        assert out.scene_id == SCENE_ID
        assert out.query_id == query_id
        assert out.answer_gt.type == "option_letter"
        assert out.answer_gt.value in {"A", "B", "C", "D"}
        assert out.annotation_gt.type == "bbox"
        width, height = out.image.size
        _assert_bbox_inside_canvas(list(out.annotation_gt.value), width=width, height=height)
        assert "quarry" in out.prompt
        assert "ground tile" in out.prompt or "terrain tile" in out.prompt

        trace = out.trace_payload
        assert trace["query_spec"]["query_id"] == query_id
        assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_isometric_quarry_v0"
        assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == SCENE_ID
        assert trace["projected_annotation"]["type"] == "bbox"
        assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
        assert trace["projected_annotation"]["pixel_bbox"] == out.annotation_gt.value
        assert trace["render_map"]["selected_label"] == out.answer_gt.value
        assert trace["render_map"]["selected_tile_bbox_px"] == out.annotation_gt.value
        assert len(trace["render_map"]["candidate_tile_ids_by_label"]) == 4
        levels = trace["render_map"]["candidate_levels_by_label"]
        selected_level = int(levels[str(out.answer_gt.value)])
        if query_id == "highest_terrain_tile":
            assert selected_level == max(int(value) for value in levels.values())
            assert sum(1 for value in levels.values() if int(value) == selected_level) == 1
        else:
            assert selected_level == min(int(value) for value in levels.values())
            assert sum(1 for value in levels.values() if int(value) == selected_level) == 1


def test_isometric_quarry_task_registered() -> None:
    assert ELEVATION_TASK_ID in TASK_REGISTRY
    elevation_task_cls = TASK_REGISTRY[ELEVATION_TASK_ID]
    assert tuple(elevation_task_cls.supported_query_ids) == tuple(ELEVATION_QUERY_IDS)
