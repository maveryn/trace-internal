from __future__ import annotations

from pathlib import Path
import sys
import types


def _install_trace_tasks_namespace() -> None:
    if "trace.tasks" in sys.modules:
        return
    repo_root = Path(__file__).resolve().parents[1]
    tasks_module = types.ModuleType("trace.tasks")
    tasks_module.__path__ = [str(repo_root / "trace" / "tasks")]  # type: ignore[attr-defined]
    sys.modules["trace.tasks"] = tasks_module


_install_trace_tasks_namespace()

from trace.tasks.illustrations.shared.object_variants import (  # noqa: E402
    RENDERER_STYLE_ISOMETRIC_PIXEL_RPG,
    RENDERER_STYLE_TOP_DOWN_PIXEL_RPG,
)
from trace.tasks.illustrations.shared.pixel_rpg_interior_rendering import (  # noqa: E402
    RENDERER_ID,
    SCENE_ID,
    draw_pixel_rpg_general_store_debug_overlay,
    render_pixel_rpg_general_store,
)


def test_general_store_rendering_is_deterministic_per_projection() -> None:
    for projection in ("top_down", "isometric"):
        first = render_pixel_rpg_general_store(20260608, projection=projection)
        second = render_pixel_rpg_general_store(20260608, projection=projection)

        assert first.image.size == (960, 720)
        assert first.image.tobytes() == second.image.tobytes()
        assert first.trace == second.trace
        assert first.trace["scene_id"] == SCENE_ID
        assert first.trace["renderer_id"] == RENDERER_ID


def test_general_store_has_required_zones_and_shop_objects() -> None:
    scene = render_pixel_rpg_general_store(17, projection="top_down")
    region_ids = {region.region_id for region in scene.regions}
    object_counts = scene.trace["object_type_counts"]

    assert {
        "entrance",
        "counter_zone",
        "back_wall",
        "left_wall",
        "right_wall",
        "center_aisle",
        "storage_corner",
    }.issubset(region_ids)
    assert object_counts["counter"] == 1
    assert object_counts["person"] == 1
    assert object_counts["shelf"] >= 2
    assert object_counts["produce_bin"] == 1
    assert object_counts["crate"] >= 2
    assert object_counts["barrel"] == 1
    assert object_counts["notice_board"] == 1
    assert object_counts["jar"] >= 1
    assert object_counts["pot"] >= 1
    assert object_counts["basket"] >= 1


def test_general_store_top_down_and_isometric_share_logical_layout() -> None:
    top_down = render_pixel_rpg_general_store(42, projection="top_down")
    isometric = render_pixel_rpg_general_store(42, projection="isometric")

    top_entities = {entity.entity_id: entity for entity in top_down.entities}
    iso_entities = {entity.entity_id: entity for entity in isometric.entities}
    assert set(top_entities) == set(iso_entities)
    for entity_id, entity in top_entities.items():
        assert entity.tile_xywh == iso_entities[entity_id].tile_xywh
        assert entity.object_type == iso_entities[entity_id].object_type
    assert [region.region_id for region in top_down.regions] == [region.region_id for region in isometric.regions]
    assert top_down.trace["object_type_counts"] == isometric.trace["object_type_counts"]


def test_general_store_entity_records_and_bboxes_are_valid_for_both_projections() -> None:
    expected_styles = {
        "top_down": RENDERER_STYLE_TOP_DOWN_PIXEL_RPG,
        "isometric": RENDERER_STYLE_ISOMETRIC_PIXEL_RPG,
    }
    for projection, renderer_style in expected_styles.items():
        scene = render_pixel_rpg_general_store(99, projection=projection)
        assert scene.trace["renderer_style"] == renderer_style
        assert draw_pixel_rpg_general_store_debug_overlay(scene).size == scene.image.size
        for entity in scene.entities:
            x0, y0, x1, y1 = entity.bbox_xyxy
            assert 0 <= x0 < x1 <= scene.image.width, entity.entity_id
            assert 0 <= y0 < y1 <= scene.image.height, entity.entity_id
            record = entity.metadata["object_record"]
            assert record["object_id"] == entity.entity_id
            assert record["object_type"] == entity.object_type
            assert record["visual_attributes"]["renderer_style"] == renderer_style
            assert record["visual_attributes"]["shadow_policy"] == "none"


def test_general_store_samples_visual_variation_across_seeds() -> None:
    themes = set()
    floors = set()
    shelf_goods = set()
    produce_goods = set()
    for seed in range(30, 48):
        trace = render_pixel_rpg_general_store(seed, projection="top_down").trace
        themes.add(trace["theme_id"])
        floors.add(trace["floor_pattern"])
        shelf_goods.update(trace["shelf_goods"])
        produce_goods.add(trace["produce_goods"])

    assert len(themes) >= 3
    assert len(floors) >= 2
    assert len(shelf_goods) >= 3
    assert len(produce_goods) >= 2
