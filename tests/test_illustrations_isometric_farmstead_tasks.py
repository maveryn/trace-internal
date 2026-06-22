from __future__ import annotations

from trace.tasks.registry import TASK_REGISTRY, create_task
from trace.tasks.illustrations.isometric_farmstead.shared.rendering import (
    SCENE_ID,
    SUPPORTED_LEVELS,
    render_isometric_farmstead_scene,
)
from trace.tasks.illustrations.isometric_farmstead.terrain_elevation_extremum_label import (
    SUPPORTED_QUERY_IDS,
    TASK_ID,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= float(width)
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= float(height)


def test_isometric_farmstead_renderer_is_deterministic_and_profile_safe() -> None:
    for width, height, profile in ((1200, 800, "landscape"), (960, 960, "square"), (800, 1200, "portrait")):
        first = render_isometric_farmstead_scene(
            2026062301,
            width=width,
            height=height,
            canvas_profile=profile,
            canvas_profile_probabilities={profile: 1.0},
        )
        second = render_isometric_farmstead_scene(
            2026062301,
            width=width,
            height=height,
            canvas_profile=profile,
            canvas_profile_probabilities={profile: 1.0},
        )
        assert first.image.size == (width, height)
        assert first.image.tobytes() == second.image.tobytes()
        assert first.trace["renderer_id"] == "isometric_farmstead_v0"
        assert first.trace["projection"]["type"] == "2:1_isometric"
        assert first.trace["levels"] == list(SUPPORTED_LEVELS)
        assert set(first.trace["level_tile_counts"]) == {"0", "1", "2", "3"}
        assert all(int(first.trace["level_tile_counts"][str(level)]) > 0 for level in SUPPORTED_LEVELS)
        assert {transition.lower_level for transition in first.transitions} == {0, 1, 2}
        assert {transition.upper_level for transition in first.transitions} == {1, 2, 3}
        assert first.trace["eligible_tile_ids"]
        for tile in first.tiles:
            _assert_bbox_inside_canvas(list(tile.bbox_xyxy), width=width, height=height)
        for transition in first.transitions:
            _assert_bbox_inside_canvas(list(transition.bbox_xyxy), width=width, height=height)
        for entity in first.entities:
            _assert_bbox_inside_canvas(list(entity.bbox_xyxy), width=width, height=height)


def test_isometric_farmstead_elevation_task_contract() -> None:
    task = create_task(TASK_ID)
    cases = (
        ("highest_terrain_tile", "landscape", 2026062311),
        ("lowest_terrain_tile", "square", 2026062312),
        ("highest_terrain_tile", "portrait", 2026062313),
        ("lowest_terrain_tile", "portrait", 2026062314),
    )
    for query_id, profile, seed in cases:
        out = task.generate(
            seed,
            params={"query_id": query_id, "canvas_profile": profile, "candidate_count": 6},
            max_attempts=30,
        )
        assert out.scene_id == SCENE_ID
        assert out.query_id == query_id
        assert out.answer_gt.type == "option_letter"
        assert out.answer_gt.value in {"A", "B", "C", "D", "E", "F"}
        assert out.annotation_gt.type == "bbox"
        width, height = out.image.size
        _assert_bbox_inside_canvas(list(out.annotation_gt.value), width=width, height=height)
        assert "ground tile" in out.prompt or "terrain tile" in out.prompt

        trace = out.trace_payload
        assert trace["query_spec"]["query_id"] == query_id
        assert trace["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "illustrations_isometric_farmstead_v0"
        assert trace["query_spec"]["prompt_variant"]["prompt_scene_id"] == SCENE_ID
        assert trace["projected_annotation"]["type"] == "bbox"
        assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
        assert trace["projected_annotation"]["pixel_bbox"] == out.annotation_gt.value
        assert trace["render_map"]["selected_label"] == out.answer_gt.value
        assert trace["render_map"]["selected_tile_bbox_px"] == out.annotation_gt.value
        assert len(trace["render_map"]["candidate_tile_ids_by_label"]) == 6
        levels = trace["render_map"]["candidate_levels_by_label"]
        selected_level = int(levels[str(out.answer_gt.value)])
        if query_id == "highest_terrain_tile":
            assert selected_level == max(int(value) for value in levels.values())
            assert sum(1 for value in levels.values() if int(value) == selected_level) == 1
        else:
            assert selected_level == min(int(value) for value in levels.values())
            assert sum(1 for value in levels.values() if int(value) == selected_level) == 1


def test_isometric_farmstead_elevation_task_registered() -> None:
    assert TASK_ID in TASK_REGISTRY
    task_cls = TASK_REGISTRY[TASK_ID]
    assert tuple(task_cls.supported_query_ids) == tuple(SUPPORTED_QUERY_IDS)
