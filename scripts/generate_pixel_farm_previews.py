#!/usr/bin/env python3
"""Generate procedural pixel-farm prototype scenes and object sheets for review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import types
from typing import Callable, Sequence

from PIL import Image, ImageDraw


def _install_trace_tasks_namespace() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    trace_module = sys.modules.get("trace")
    if trace_module is None or not hasattr(trace_module, "__path__"):
        trace_module = types.ModuleType("trace")
        trace_module.__path__ = [str(repo_root / "trace")]  # type: ignore[attr-defined]
        sys.modules["trace"] = trace_module
    if "trace.tasks" in sys.modules:
        return
    tasks_module = types.ModuleType("trace.tasks")
    tasks_module.__path__ = [str(repo_root / "trace" / "tasks")]  # type: ignore[attr-defined]
    sys.modules["trace.tasks"] = tasks_module
    setattr(trace_module, "tasks", tasks_module)


_install_trace_tasks_namespace()

from trace.tasks.illustrations.shared.pixel_farm_rendering import (  # noqa: E402
    draw_pixel_farm_debug_overlay,
    render_pixel_farm_map,
)
from trace.tasks.illustrations.shared.object_rendering import (  # noqa: E402
    PIXEL_RPG_SHARED_OBJECT_TYPES,
    IllustrationObjectSpec,
    RenderContext,
    render_illustration_object,
)
from trace.tasks.illustrations.shared.object_variants import (  # noqa: E402
    RENDERER_STYLE_ISOMETRIC_PIXEL_RPG,
    RENDERER_STYLE_TOP_DOWN_PIXEL_RPG,
)
from trace.tasks.illustrations.shared.pixel_world_objects import (  # noqa: E402
    CANONICAL_TILE_PX,
    PIXEL_CROP_STYLES,
    PIXEL_DOMESTIC_ANIMALS,
    PIXEL_PERSON_VARIANTS,
    PIXEL_TREE_STYLES,
    PIXEL_VEGETABLE_STYLES,
    draw_pixel_animal,
    draw_pixel_autumn_overlay,
    draw_pixel_barrel,
    draw_pixel_bench,
    draw_pixel_boulder,
    draw_pixel_castle,
    draw_pixel_cave_entrance,
    draw_pixel_church,
    draw_pixel_crystal_cluster,
    draw_pixel_crop_row,
    draw_pixel_cart,
    draw_pixel_flower_patch,
    draw_pixel_gazebo,
    draw_pixel_hay_bale,
    draw_pixel_lamp_post,
    draw_pixel_ladder,
    draw_pixel_market_stall,
    draw_pixel_mine_cart,
    draw_pixel_notice_board,
    draw_pixel_ore_vein,
    draw_pixel_person,
    draw_pixel_pond,
    draw_pixel_rail_track,
    draw_pixel_scarecrow,
    draw_pixel_stairs,
    draw_pixel_stalagmite,
    draw_pixel_statue,
    draw_pixel_torch,
    draw_pixel_tree,
    draw_pixel_vegetable_patch,
    draw_pixel_well,
    draw_pixel_windmill,
    draw_pixel_woodpile,
    draw_pixel_wood_support,
    draw_pixel_wagon,
    draw_pixel_winter_overlay,
)


DEFAULT_OUT_DIR = Path("review/task-reviews/assets/illustrations/pixel_farm_map")
DEFAULT_OBJECT_OUT_DIR = Path("review/task-reviews/assets/illustrations/pixel_world_objects")
REFERENCE_SOURCES = {
    "kenney_tiny_town": {
        "name": "Kenney Tiny Town",
        "url": "https://kenney.nl/assets/tiny-town",
        "notes": "CC0 pixel town pack used as visual reference only.",
    },
    "kenney_roguelike_rpg": {
        "name": "Kenney Roguelike/RPG pack",
        "url": "https://kenney.nl/assets/roguelike-rpg-pack",
        "notes": "CC0 pixel RPG pack used as visual reference only.",
    },
    "kenney_rpg_urban_pack": {
        "name": "Kenney RPG Urban Pack",
        "url": "https://opengameart.org/content/rpg-urban-pack",
        "notes": "CC0 pixel urban prop pack used as visual reference only.",
    },
    "kenney_tiny_dungeon": {
        "name": "Kenney Tiny Dungeon",
        "url": "https://kenney.nl/assets/tiny-dungeon",
        "notes": "CC0 dungeon pack used as visual reference only.",
    },
    "kenney_micro_roguelike": {
        "name": "Kenney Micro Roguelike",
        "url": "https://www.kenney.nl/assets/micro-roguelike",
        "notes": "CC0 roguelike pack used as visual reference only.",
    },
    "opengameart_16x16_rpg_tileset": {
        "name": "OpenGameArt 16x16 RPG Tileset",
        "url": "https://opengameart.org/content/16x16-rpg-tileset",
        "notes": "Pixel RPG tileset used as visual reference only.",
    },
    "opengameart_cave_tileset": {
        "name": "OpenGameArt Cave Tileset",
        "url": "https://opengameart.org/content/cave-tileset",
        "notes": "Cave tileset used as visual reference only.",
    },
    "opengameart_puny_dungeon": {
        "name": "OpenGameArt 16x16 Puny Dungeon Tileset",
        "url": "https://opengameart.org/content/16x16-puny-dungeon-tileset",
        "notes": "Dungeon tileset used as visual reference only.",
    },
}
REFERENCE_SOURCE_IDS_BY_LABEL = {
    "boulder": ["kenney_tiny_dungeon", "opengameart_cave_tileset"],
    "cave entrance": ["opengameart_cave_tileset", "opengameart_16x16_rpg_tileset"],
    "crystal cluster": ["kenney_micro_roguelike", "opengameart_cave_tileset"],
    "ladder": ["kenney_tiny_dungeon", "opengameart_puny_dungeon"],
    "market stall": ["kenney_tiny_town", "kenney_roguelike_rpg"],
    "mine cart": ["kenney_tiny_dungeon", "opengameart_cave_tileset"],
    "ore vein": ["kenney_tiny_dungeon", "opengameart_cave_tileset"],
    "wagon": ["kenney_rpg_urban_pack", "kenney_roguelike_rpg"],
    "rail track": ["kenney_tiny_dungeon", "opengameart_cave_tileset"],
    "stairs": ["kenney_tiny_dungeon", "opengameart_puny_dungeon"],
    "stalagmite": ["opengameart_cave_tileset", "opengameart_16x16_rpg_tileset"],
    "statue": ["kenney_tiny_town", "kenney_roguelike_rpg"],
    "torch": ["kenney_tiny_dungeon", "kenney_micro_roguelike"],
    "gazebo": ["kenney_tiny_town", "kenney_roguelike_rpg"],
    "woodpile": ["kenney_roguelike_rpg", "kenney_tiny_town"],
    "wood support": ["kenney_tiny_dungeon", "opengameart_cave_tileset"],
    "pond": ["kenney_tiny_town"],
}
SHARED_OBJECT_TEMPLATE_FOOTPRINTS: dict[str, tuple[int, int]] = {
    "barn": (4, 3),
    "boulder": (1, 1),
    "cart": (2, 1),
    "castle": (5, 4),
    "cave_entrance": (4, 3),
    "chicken_coop": (2, 2),
    "church": (4, 4),
    "coop": (2, 2),
    "crystal_cluster": (1, 1),
    "dead_tree": (1, 2),
    "domestic_animal": (2, 1),
    "gazebo": (3, 3),
    "house": (4, 3),
    "inn": (4, 3),
    "ladder": (1, 1),
    "lamp_post": (1, 2),
    "market_stall": (3, 2),
    "mine_cart": (2, 1),
    "notice_board": (2, 1),
    "ore_vein": (1, 1),
    "pond": (3, 2),
    "rail_track": (1, 1),
    "scarecrow": (1, 2),
    "shop": (4, 3),
    "stairs": (2, 2),
    "stalagmite": (1, 1),
    "statue": (2, 2),
    "tower": (3, 4),
    "torch": (1, 1),
    "tree": (1, 2),
    "trough": (2, 1),
    "vegetable_patch": (1, 1),
    "wagon": (3, 2),
    "well": (2, 2),
    "windmill": (3, 4),
    "woodpile": (2, 1),
    "wood_support": (2, 2),
}
SHARED_OBJECT_TEMPLATE_CATEGORIES: dict[str, str] = {
    "barn": "building",
    "boulder": "obstacle",
    "castle": "landmark",
    "cave_entrance": "terrain_feature",
    "chicken_coop": "building",
    "church": "landmark",
    "coop": "building",
    "crystal_cluster": "resource",
    "crop_row": "plant",
    "dead_tree": "plant",
    "domestic_animal": "animal",
    "flower": "plant",
    "gazebo": "landmark",
    "grave_marker": "grave_marker",
    "hay_bale": "farm_fixture",
    "house": "building",
    "inn": "building",
    "ladder": "route_feature",
    "market_stall": "landmark",
    "mine_cart": "vehicle",
    "ore_vein": "resource",
    "person": "person",
    "pond": "landmark",
    "rail_track": "route_feature",
    "scarecrow": "farm_fixture",
    "shop": "building",
    "stairs": "route_feature",
    "stalagmite": "obstacle",
    "statue": "landmark",
    "tower": "building",
    "torch": "fixture",
    "tree": "tree",
    "trough": "farm_fixture",
    "vegetable_patch": "vegetable",
    "well": "landmark",
    "windmill": "landmark",
    "wood_support": "structure",
}
SHARED_OBJECT_TEMPLATE_LABELS: dict[str, str] = {
    "cave_entrance": "cave entrance",
    "cemetery_gate": "cemetery gate",
    "chicken_coop": "chicken coop",
    "crystal_cluster": "crystal cluster",
    "crop_row": "crop row",
    "dead_tree": "dead tree",
    "domestic_animal": "cow",
    "farm_gate": "farm gate",
    "grave_marker": "grave marker",
    "hay_bale": "hay bale",
    "iron_fence": "iron fence",
    "lamp_post": "lamp post",
    "market_stall": "market stall",
    "mine_cart": "mine cart",
    "notice_board": "notice board",
    "ore_vein": "ore vein",
    "rail_track": "rail track",
    "vegetable_patch": "vegetable patch",
    "wood_support": "wood support",
}


def _fit(image: Image.Image, *, max_w: int, max_h: int) -> Image.Image:
    fitted = image.copy()
    fitted.thumbnail((int(max_w), int(max_h)), Image.Resampling.NEAREST)
    return fitted


def _make_contact_sheet(image_paths: Sequence[Path], output_path: Path, *, columns: int = 3) -> None:
    thumbs: list[Image.Image] = []
    for path in image_paths:
        thumbs.append(_fit(Image.open(path).convert("RGB"), max_w=360, max_h=270))
    if not thumbs:
        return
    tile_w = 380
    tile_h = 306
    rows = (len(thumbs) + int(columns) - 1) // int(columns)
    sheet = Image.new("RGB", (int(columns) * tile_w, rows * tile_h), (238, 238, 222))
    draw = ImageDraw.Draw(sheet)
    for index, thumb in enumerate(thumbs):
        row, col = divmod(index, int(columns))
        x = col * tile_w
        y = row * tile_h
        draw.rectangle((x + 8, y + 8, x + tile_w - 8, y + tile_h - 8), fill=(255, 255, 238), outline=(190, 190, 174))
        sheet.paste(thumb, (x + (tile_w - thumb.width) // 2, y + 16))
        draw.text((x + 16, y + tile_h - 26), f"pixel farm {index:02d}", fill=(45, 48, 54))
    sheet.save(output_path)


def _template_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (4 * CANONICAL_TILE_PX, 4 * CANONICAL_TILE_PX), (98, 168, 91))
    draw = ImageDraw.Draw(image)
    for x in range(0, image.width, CANONICAL_TILE_PX):
        draw.line((x, 0, x, image.height), fill=(82, 144, 78))
    for y in range(0, image.height, CANONICAL_TILE_PX):
        draw.line((0, y, image.width, y), fill=(82, 144, 78))
    return image, draw


def _winter_template_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (4 * CANONICAL_TILE_PX, 4 * CANONICAL_TILE_PX), (218, 230, 231))
    draw = ImageDraw.Draw(image)
    for x in range(0, image.width, CANONICAL_TILE_PX):
        draw.line((x, 0, x, image.height), fill=(190, 211, 218))
    for y in range(0, image.height, CANONICAL_TILE_PX):
        draw.line((0, y, image.width, y), fill=(190, 211, 218))
    return image, draw


def _autumn_template_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (4 * CANONICAL_TILE_PX, 4 * CANONICAL_TILE_PX), (112, 151, 79))
    draw = ImageDraw.Draw(image)
    for x in range(0, image.width, CANONICAL_TILE_PX):
        draw.line((x, 0, x, image.height), fill=(92, 129, 71))
    for y in range(0, image.height, CANONICAL_TILE_PX):
        draw.line((0, y, image.width, y), fill=(92, 129, 71))
    return image, draw


def _render_template(draw_fn: Callable[[ImageDraw.ImageDraw], None]) -> Image.Image:
    image, draw = _template_canvas()
    draw_fn(draw)
    return image.resize((128, 128), Image.Resampling.NEAREST)


def _render_winter_template(draw_fn: Callable[[ImageDraw.ImageDraw], None]) -> Image.Image:
    image, draw = _winter_template_canvas()
    draw_fn(draw)
    return image.resize((128, 128), Image.Resampling.NEAREST)


def _render_autumn_template(draw_fn: Callable[[ImageDraw.ImageDraw], None]) -> Image.Image:
    image, draw = _autumn_template_canvas()
    draw_fn(draw)
    return image.resize((128, 128), Image.Resampling.NEAREST)


def _make_side_by_side(left: Image.Image, right: Image.Image) -> Image.Image:
    image = Image.new("RGB", (left.width * 2 + 8, left.height), (237, 237, 224))
    image.paste(left, (0, 0))
    image.paste(right, (left.width + 8, 0))
    return image


def _shared_object_template_attributes(object_type: str) -> tuple[dict, dict]:
    semantic: dict = {}
    visual: dict = {}
    if object_type == "domestic_animal":
        semantic["animal_type"] = "cow"
        visual.update({"animal_type": "cow", "facing": "right"})
    elif object_type == "tree":
        visual.update({"tree_style": "fruit_tree"})
    elif object_type == "person":
        visual.update({"person_variant_id": "farmer", "facing": "down"})
    elif object_type == "crop_row":
        visual.update({"crop_style": "wheat"})
    elif object_type == "vegetable_patch":
        visual.update({"vegetable_style": "carrot"})
    elif object_type == "grave_marker":
        visual.update({"marker_style": "rounded"})
    elif object_type == "pond":
        visual.update({"pond_shape": "kidney"})
    elif object_type in {"bench", "bridge", "cemetery_gate", "farm_gate", "fence", "iron_fence"}:
        visual.update({"orientation": "horizontal"})
    elif object_type == "ladder":
        visual.update({"orientation": "vertical"})
    elif object_type in {"cart", "wagon"}:
        visual.update({"facing": "right"})
    elif object_type == "mine_cart":
        visual.update({"orientation": "horizontal"})
    elif object_type == "market_stall":
        visual.update({"goods_type": "fruit"})
    elif object_type == "rail_track":
        visual.update({"track_shape": "horizontal"})
    elif object_type == "stairs":
        visual.update({"stair_direction": "down"})
    elif object_type == "windmill":
        visual.update({"blade_pose": "plus"})
    elif object_type == "woodpile":
        visual.update({"stack_variant": "low"})
    return semantic, visual


def _shared_object_template_spec(object_type: str, *, tile_xywh: tuple[int, int, int, int]) -> IllustrationObjectSpec:
    label = SHARED_OBJECT_TEMPLATE_LABELS.get(object_type, object_type.replace("_", " "))
    semantic, visual = _shared_object_template_attributes(object_type)
    return IllustrationObjectSpec(
        object_id=f"template_{object_type}",
        object_type=str(object_type),
        public_name=str(label),
        tile_xywh=tile_xywh,
        semantic_attributes=semantic,
        visual_attributes=visual,
        source_entity_type="pixel_world_object_resource_template",
    )


def _render_shared_top_down_template(object_type: str) -> Image.Image:
    w, h = SHARED_OBJECT_TEMPLATE_FOOTPRINTS.get(object_type, (1, 1))
    size_tiles = max(6, int(w) + 2, int(h) + 2)
    tile_x = max(0, (size_tiles - int(w)) // 2)
    tile_y = max(0, (size_tiles - int(h)) // 2)
    image = Image.new("RGBA", (size_tiles * CANONICAL_TILE_PX, size_tiles * CANONICAL_TILE_PX), (98, 168, 91, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    for x in range(0, image.width, CANONICAL_TILE_PX):
        draw.line((x, 0, x, image.height), fill=(82, 144, 78, 255))
    for y in range(0, image.height, CANONICAL_TILE_PX):
        draw.line((0, y, image.width, y), fill=(82, 144, 78, 255))
    render_illustration_object(
        _shared_object_template_spec(object_type, tile_xywh=(tile_x, tile_y, int(w), int(h))),
        RenderContext(renderer_style=RENDERER_STYLE_TOP_DOWN_PIXEL_RPG, draw=draw),
    )
    return image.convert("RGB").resize((128, 128), Image.Resampling.NEAREST)


def _render_shared_isometric_template(object_type: str) -> Image.Image:
    w, h = SHARED_OBJECT_TEMPLATE_FOOTPRINTS.get(object_type, (1, 1))
    image = Image.new("RGBA", (176, 152), (237, 237, 224, 255))
    draw = ImageDraw.Draw(image, "RGBA")

    def project_tile_center(tile_xywh: tuple[int, int, int, int], level: int) -> tuple[float, float]:
        x, y, width, height = tile_xywh
        center_x = x + (width - 1) * 0.5
        center_y = y + (height - 1) * 0.5
        return (88.0 + (center_x - center_y) * 16.0, 96.0 + (center_x + center_y) * 8.0 - level * 12.0)

    for ty in range(int(h)):
        for tx in range(int(w)):
            cx, cy = project_tile_center((tx, ty, 1, 1), 0)
            draw.polygon(
                [(cx, cy - 8), (cx + 16, cy), (cx, cy + 8), (cx - 16, cy)],
                fill=(105, 174, 92, 255),
                outline=(76, 136, 76, 255),
            )
    render_illustration_object(
        _shared_object_template_spec(object_type, tile_xywh=(0, 0, int(w), int(h))),
        RenderContext(
            renderer_style=RENDERER_STYLE_ISOMETRIC_PIXEL_RPG,
            image=image,
            project_tile_center=project_tile_center,
        ),
    )
    fitted = _fit(image.convert("RGB"), max_w=128, max_h=128)
    output = Image.new("RGB", (128, 128), (237, 237, 224))
    output.paste(fitted, ((128 - fitted.width) // 2, (128 - fitted.height) // 2))
    return output


def generate_shared_renderer_object_template_sheet(*, out_dir: Path) -> list[dict[str, str]]:
    entries: list[tuple[str, str, str, Image.Image]] = []
    for object_type in PIXEL_RPG_SHARED_OBJECT_TYPES:
        category = SHARED_OBJECT_TEMPLATE_CATEGORIES.get(object_type, "object")
        label = SHARED_OBJECT_TEMPLATE_LABELS.get(object_type, object_type.replace("_", " "))
        entries.append(
            (
                str(object_type),
                str(category),
                str(label),
                _make_side_by_side(
                    _render_shared_top_down_template(str(object_type)),
                    _render_shared_isometric_template(str(object_type)),
                ),
            )
        )

    cell_w = 328
    cell_h = 176
    columns = 2
    rows = (len(entries) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (237, 237, 224))
    draw = ImageDraw.Draw(sheet)
    for index, (object_type, category, label, image) in enumerate(entries):
        row, col = divmod(index, columns)
        x = col * cell_w
        y = row * cell_h
        draw.rectangle((x + 8, y + 8, x + cell_w - 8, y + cell_h - 8), fill=(255, 255, 240), outline=(188, 188, 170))
        sheet.paste(image, (x + (cell_w - image.width) // 2, y + 16))
        draw.text((x + 14, y + 150), f"{category}: {label}", fill=(40, 44, 48))
        draw.text((x + 14, y + 136), "top-down | isometric", fill=(84, 88, 92))
    sheet.save(out_dir / "object_topdown_isometric_templates.png")
    return [
        {
            "object_type": object_type,
            "category": category,
            "label": label,
        }
        for object_type, category, label, _ in entries
    ]


def generate_object_template_sheet(*, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, str, Image.Image]] = []

    for style in PIXEL_TREE_STYLES:
        entries.append(
            (
                "tree",
                str(style),
                _render_template(lambda draw, style=style: draw_pixel_tree(draw, (1, 1, 1, 2), style=str(style))),
            )
        )
    for person_variant in PIXEL_PERSON_VARIANTS:
        for gender_id in ("male", "female"):
            entries.append(
                (
                    "person",
                    f"{person_variant} {gender_id}",
                    _render_template(
                        lambda draw, person_variant=person_variant, gender_id=gender_id: draw_pixel_person(
                            draw,
                            (1, 2, 1, 1),
                            person_variant_id=str(person_variant),
                            gender_id=str(gender_id),
                            facing="down",
                        )
                    ),
                )
            )
    entries.extend(
        [
            ("landmark", "castle", _render_template(lambda draw: draw_pixel_castle(draw, (0, 0, 4, 4)))),
            ("landmark", "church", _render_template(lambda draw: draw_pixel_church(draw, (0, 0, 4, 4)))),
            ("landmark", "windmill", _render_template(lambda draw: draw_pixel_windmill(draw, (0, 0, 3, 4)))),
            ("landmark", "well", _render_template(lambda draw: draw_pixel_well(draw, (1, 1, 2, 2)))),
            ("object", "barrel", _render_template(lambda draw: draw_pixel_barrel(draw, (1, 2, 1, 1)))),
            ("object", "bench", _render_template(lambda draw: draw_pixel_bench(draw, (1, 2, 2, 1), orientation="horizontal"))),
            ("landmark", "lamp post", _render_template(lambda draw: draw_pixel_lamp_post(draw, (1, 1, 1, 2)))),
            ("landmark", "notice board", _render_template(lambda draw: draw_pixel_notice_board(draw, (1, 2, 2, 1)))),
            ("object", "cart", _render_template(lambda draw: draw_pixel_cart(draw, (1, 2, 2, 1), facing="right"))),
            (
                "landmark",
                "market stall",
                _render_template(lambda draw: draw_pixel_market_stall(draw, (0, 1, 3, 2), goods_type="fruit")),
            ),
            (
                "object",
                "wagon",
                _render_template(lambda draw: draw_pixel_wagon(draw, (0, 1, 3, 2), facing="right", cover_rgb=(214, 192, 138))),
            ),
            ("landmark", "statue", _render_template(lambda draw: draw_pixel_statue(draw, (1, 1, 2, 2)))),
            ("landmark", "gazebo", _render_template(lambda draw: draw_pixel_gazebo(draw, (0, 0, 3, 3)))),
            ("object", "woodpile", _render_template(lambda draw: draw_pixel_woodpile(draw, (1, 2, 2, 1)))),
            ("landmark", "pond", _render_template(lambda draw: draw_pixel_pond(draw, (0, 1, 4, 3), shape="kidney"))),
            ("plant", "flower", _render_template(lambda draw: draw_pixel_flower_patch(draw, (1, 2, 1, 1)))),
            ("farm_fixture", "hay bale", _render_template(lambda draw: draw_pixel_hay_bale(draw, (1, 2, 1, 1)))),
            ("farm_fixture", "scarecrow", _render_template(lambda draw: draw_pixel_scarecrow(draw, (1, 1, 1, 2)))),
            ("terrain_feature", "cave entrance", _render_template(lambda draw: draw_pixel_cave_entrance(draw, (0, 0, 4, 3)))),
            ("obstacle", "boulder", _render_template(lambda draw: draw_pixel_boulder(draw, (1, 2, 1, 1)))),
            ("resource", "ore vein", _render_template(lambda draw: draw_pixel_ore_vein(draw, (1, 2, 1, 1)))),
            ("resource", "crystal cluster", _render_template(lambda draw: draw_pixel_crystal_cluster(draw, (1, 2, 1, 1)))),
            ("obstacle", "stalagmite", _render_template(lambda draw: draw_pixel_stalagmite(draw, (1, 2, 1, 1)))),
            ("fixture", "torch", _render_template(lambda draw: draw_pixel_torch(draw, (1, 2, 1, 1)))),
            ("route_feature", "ladder", _render_template(lambda draw: draw_pixel_ladder(draw, (1, 2, 1, 1), orientation="vertical"))),
            ("vehicle", "mine cart", _render_template(lambda draw: draw_pixel_mine_cart(draw, (1, 2, 2, 1), orientation="horizontal"))),
            ("route_feature", "rail track", _render_template(lambda draw: draw_pixel_rail_track(draw, (1, 2, 1, 1), track_shape="horizontal"))),
            ("structure", "wood support", _render_template(lambda draw: draw_pixel_wood_support(draw, (1, 1, 2, 2)))),
            ("route_feature", "stairs", _render_template(lambda draw: draw_pixel_stairs(draw, (1, 1, 2, 2), stair_direction="down"))),
        ]
    )
    for style in PIXEL_CROP_STYLES:
        entries.append(
            (
                "plant",
                f"crop row: {style}",
                _render_template(lambda draw, style=style: draw_pixel_crop_row(draw, (0, 2, 4, 1), style=str(style))),
            )
        )
    for style in PIXEL_VEGETABLE_STYLES:
        entries.append(
            (
                "vegetable",
                f"vegetable patch: {style}",
                _render_template(
                    lambda draw, style=style: draw_pixel_vegetable_patch(draw, (1, 2, 1, 1), style=str(style))
                ),
            )
        )
    for animal_type in PIXEL_DOMESTIC_ANIMALS:
        tile_xywh = (1, 2, 2, 1) if animal_type == "cow" else (1, 2, 1, 1)
        entries.append(
            (
                "animal",
                str(animal_type),
                _render_template(
                    lambda draw, animal_type=animal_type, tile_xywh=tile_xywh: draw_pixel_animal(
                        draw,
                        tile_xywh,
                        animal_type=str(animal_type),
                        facing="right",
                    )
                ),
            )
        )

    cell_w = 172
    cell_h = 176
    columns = 4
    rows = (len(entries) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (237, 237, 224))
    draw = ImageDraw.Draw(sheet)
    for index, (category, label, image) in enumerate(entries):
        row, col = divmod(index, columns)
        x = col * cell_w
        y = row * cell_h
        draw.rectangle((x + 8, y + 8, x + cell_w - 8, y + cell_h - 8), fill=(255, 255, 240), outline=(188, 188, 170))
        sheet.paste(image, (x + (cell_w - image.width) // 2, y + 16))
        draw.text((x + 14, y + 150), f"{category}: {label}", fill=(40, 44, 48))
    output_path = out_dir / "object_templates.png"
    sheet.save(output_path)
    generate_autumn_object_template_sheet(out_dir=out_dir)
    generate_winter_object_template_sheet(out_dir=out_dir)
    shared_renderer_entries = generate_shared_renderer_object_template_sheet(out_dir=out_dir)
    manifest = {
        "asset_id": "pixel_world_object_templates_v0",
        "uses_external_sprites": False,
        "reference_sources": REFERENCE_SOURCES,
        "categories": sorted({category for category, _, _ in entries}),
        "entries": [
            {
                "category": category,
                "label": label,
                "reference_source_ids": REFERENCE_SOURCE_IDS_BY_LABEL.get(label, []),
            }
            for category, label, _ in entries
        ],
        "image": str(output_path),
        "autumn_theme_image": str(out_dir / "object_autumn_templates.png"),
        "winter_theme_image": str(out_dir / "object_winter_templates.png"),
        "topdown_isometric_image": str(out_dir / "object_topdown_isometric_templates.png"),
        "shared_renderer_entries": shared_renderer_entries,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# Pixel World Object Templates",
                "",
                "Reusable procedural pixel-world object templates used by renderer prototypes.",
                "",
                "- `object_templates.png`: inspection sheet for reusable trees, landmarks, village props, farm fixtures, plants, and domestic animals.",
                "- `object_autumn_templates.png`: temperate/autumn comparison sheet for the first autumn-enabled pixel village objects.",
                "- `object_winter_templates.png`: temperate/winter comparison sheet for the first winter-enabled pixel village objects.",
                "- `object_topdown_isometric_templates.png`: shared-renderer top-down/isometric comparison sheet for all current portable pixel RPG objects.",
                "- `manifest.json`: category and label inventory.",
                "",
                "The sheet is procedural and uses no external sprite pixels.",
                "Reference source ids indicate visual inspiration only.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def generate_autumn_object_template_sheet(*, out_dir: Path) -> None:
    leaf_kwargs = {
        "leaf_rgb": (177, 126, 55),
        "shadow_rgb": (104, 82, 47),
        "accent_rgb": (154, 78, 51),
        "coverage": 0.28,
        "style": "scattered",
    }
    entries: list[tuple[str, str, Image.Image]] = [
        (
            "tree",
            "oak",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_tree(draw, (1, 1, 1, 2), style="oak")),
                _render_autumn_template(
                    lambda draw: (
                        draw_pixel_tree(draw, (1, 1, 1, 2), style="oak", leaf_rgb=(155, 126, 60)),
                        draw_pixel_autumn_overlay(draw, (1, 1, 1, 2), target="oak", **leaf_kwargs),
                    )
                ),
            ),
        ),
        (
            "plant",
            "flower patch",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_flower_patch(draw, (1, 2, 1, 1))),
                _render_autumn_template(
                    lambda draw: draw_pixel_flower_patch(
                        draw,
                        (1, 2, 1, 1),
                        flower_rgb=(174, 119, 63),
                        leaf_rgb=(82, 96, 55),
                    )
                ),
            ),
        ),
        (
            "plant",
            "crop row",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_crop_row(draw, (0, 2, 4, 1), style="wheat")),
                _render_autumn_template(
                    lambda draw: draw_pixel_crop_row(
                        draw,
                        (0, 2, 4, 1),
                        style="wheat",
                        crop_rgb=(179, 136, 58),
                        soil_rgb=(119, 79, 49),
                    )
                ),
            ),
        ),
        (
            "object",
            "bench",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_bench(draw, (1, 2, 2, 1), orientation="horizontal")),
                _render_autumn_template(
                    lambda draw: (
                        draw_pixel_bench(draw, (1, 2, 2, 1), orientation="horizontal"),
                        draw_pixel_autumn_overlay(draw, (1, 2, 2, 1), target="bench", **leaf_kwargs),
                    )
                ),
            ),
        ),
        (
            "landmark",
            "market stall",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_market_stall(draw, (0, 1, 3, 2), goods_type="fruit")),
                _render_autumn_template(
                    lambda draw: (
                        draw_pixel_market_stall(draw, (0, 1, 3, 2), goods_type="fruit"),
                        draw_pixel_autumn_overlay(draw, (0, 1, 3, 2), target="market_stall", **leaf_kwargs),
                    )
                ),
            ),
        ),
        (
            "object",
            "wagon",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_wagon(draw, (0, 1, 3, 2), facing="right", cover_rgb=(214, 192, 138))),
                _render_autumn_template(
                    lambda draw: (
                        draw_pixel_wagon(draw, (0, 1, 3, 2), facing="right", cover_rgb=(214, 192, 138)),
                        draw_pixel_autumn_overlay(draw, (0, 1, 3, 2), target="wagon", **leaf_kwargs),
                    )
                ),
            ),
        ),
        (
            "landmark",
            "gazebo",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_gazebo(draw, (0, 0, 3, 3))),
                _render_autumn_template(
                    lambda draw: (
                        draw_pixel_gazebo(draw, (0, 0, 3, 3)),
                        draw_pixel_autumn_overlay(draw, (0, 0, 3, 3), target="gazebo", **leaf_kwargs),
                    )
                ),
            ),
        ),
        (
            "landmark",
            "pond",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_pond(draw, (0, 1, 4, 3), shape="kidney")),
                _render_autumn_template(
                    lambda draw: (
                        draw_pixel_pond(draw, (0, 1, 4, 3), shape="kidney", water_rgb=(49, 122, 180), rim_rgb=(97, 130, 78)),
                        draw_pixel_autumn_overlay(draw, (0, 1, 4, 3), target="pond", **leaf_kwargs),
                    )
                ),
            ),
        ),
    ]
    cell_w = 300
    cell_h = 176
    columns = 2
    rows = (len(entries) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (237, 237, 224))
    draw = ImageDraw.Draw(sheet)
    for index, (category, label, image) in enumerate(entries):
        row, col = divmod(index, columns)
        x = col * cell_w
        y = row * cell_h
        draw.rectangle((x + 8, y + 8, x + cell_w - 8, y + cell_h - 8), fill=(255, 255, 240), outline=(188, 188, 170))
        sheet.paste(image, (x + (cell_w - image.width) // 2, y + 16))
        draw.text((x + 14, y + 150), f"{category}: {label}", fill=(40, 44, 48))
    sheet.save(out_dir / "object_autumn_templates.png")


def generate_winter_object_template_sheet(*, out_dir: Path) -> None:
    snow_kwargs = {
        "snow_rgb": (240, 247, 249),
        "shadow_rgb": (176, 204, 218),
        "coverage": 0.62,
        "style": "patchy",
    }
    entries: list[tuple[str, str, Image.Image]] = [
        (
            "tree",
            "oak",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_tree(draw, (1, 1, 1, 2), style="oak")),
                _render_winter_template(
                    lambda draw: (
                        draw_pixel_tree(draw, (1, 1, 1, 2), style="oak"),
                        draw_pixel_winter_overlay(draw, (1, 1, 1, 2), target="oak", **snow_kwargs),
                    )
                ),
            ),
        ),
        (
            "object",
            "bench",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_bench(draw, (1, 2, 2, 1), orientation="horizontal")),
                _render_winter_template(
                    lambda draw: (
                        draw_pixel_bench(draw, (1, 2, 2, 1), orientation="horizontal"),
                        draw_pixel_winter_overlay(draw, (1, 2, 2, 1), target="bench", **snow_kwargs),
                    )
                ),
            ),
        ),
        (
            "landmark",
            "lamp post",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_lamp_post(draw, (1, 1, 1, 2))),
                _render_winter_template(
                    lambda draw: (
                        draw_pixel_lamp_post(draw, (1, 1, 1, 2)),
                        draw_pixel_winter_overlay(draw, (1, 1, 1, 2), target="lamp_post", **snow_kwargs),
                    )
                ),
            ),
        ),
        (
            "landmark",
            "market stall",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_market_stall(draw, (0, 1, 3, 2), goods_type="fruit")),
                _render_winter_template(
                    lambda draw: (
                        draw_pixel_market_stall(draw, (0, 1, 3, 2), goods_type="fruit"),
                        draw_pixel_winter_overlay(draw, (0, 1, 3, 2), target="market_stall", **snow_kwargs),
                    )
                ),
            ),
        ),
        (
            "object",
            "wagon",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_wagon(draw, (0, 1, 3, 2), facing="right", cover_rgb=(214, 192, 138))),
                _render_winter_template(
                    lambda draw: (
                        draw_pixel_wagon(draw, (0, 1, 3, 2), facing="right", cover_rgb=(214, 192, 138)),
                        draw_pixel_winter_overlay(draw, (0, 1, 3, 2), target="wagon", **snow_kwargs),
                    )
                ),
            ),
        ),
        (
            "landmark",
            "gazebo",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_gazebo(draw, (0, 0, 3, 3))),
                _render_winter_template(
                    lambda draw: (
                        draw_pixel_gazebo(draw, (0, 0, 3, 3)),
                        draw_pixel_winter_overlay(draw, (0, 0, 3, 3), target="gazebo", **snow_kwargs),
                    )
                ),
            ),
        ),
        (
            "landmark",
            "pond",
            _make_side_by_side(
                _render_template(lambda draw: draw_pixel_pond(draw, (0, 1, 4, 3), shape="kidney")),
                _render_winter_template(
                    lambda draw: (
                        draw_pixel_pond(draw, (0, 1, 4, 3), shape="kidney", water_rgb=(73, 141, 178), rim_rgb=(151, 171, 160)),
                        draw_pixel_winter_overlay(draw, (0, 1, 4, 3), target="pond", **snow_kwargs),
                    )
                ),
            ),
        ),
    ]
    cell_w = 300
    cell_h = 176
    columns = 2
    rows = (len(entries) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * cell_h), (237, 237, 224))
    draw = ImageDraw.Draw(sheet)
    for index, (category, label, image) in enumerate(entries):
        row, col = divmod(index, columns)
        x = col * cell_w
        y = row * cell_h
        draw.rectangle((x + 8, y + 8, x + cell_w - 8, y + cell_h - 8), fill=(255, 255, 240), outline=(188, 188, 170))
        sheet.paste(image, (x + (cell_w - image.width) // 2, y + 16))
        draw.text((x + 14, y + 150), f"{category}: {label}", fill=(40, 44, 48))
    sheet.save(out_dir / "object_winter_templates.png")


def generate_previews(*, out_dir: Path, object_out_dir: Path, count: int, seed: int, width: int, height: int) -> None:
    images_dir = out_dir / "images"
    overlays_dir = out_dir / "overlays"
    data_dir = out_dir / "data"
    for directory in (images_dir, overlays_dir, data_dir):
        directory.mkdir(parents=True, exist_ok=True)

    image_paths: list[Path] = []
    overlay_paths: list[Path] = []
    records: list[dict] = []
    for index in range(int(count)):
        scene_seed = int(seed) + index
        scene = render_pixel_farm_map(scene_seed, width=int(width), height=int(height))
        image_path = images_dir / f"{index:04d}.png"
        overlay_path = overlays_dir / f"{index:04d}_overlay.png"
        data_path = data_dir / f"{index:04d}.json"
        scene.image.save(image_path)
        draw_pixel_farm_debug_overlay(scene).save(overlay_path)
        data_path.write_text(json.dumps(scene.trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        image_paths.append(image_path)
        overlay_paths.append(overlay_path)
        records.append(
            {
                "index": int(index),
                "seed": int(scene_seed),
                "image": str(image_path),
                "overlay": str(overlay_path),
                "data": str(data_path),
                "grid_cols": int(scene.trace["grid_cols"]),
                "grid_rows": int(scene.trace["grid_rows"]),
                "tile_px": int(scene.trace["tile_px"]),
                "map_size_px": list(scene.trace["map_size_px"]),
                "entity_count": int(scene.trace["entity_count"]),
                "animal_count": int(scene.trace["animal_count"]),
                "inside_pen_animal_count": int(scene.trace["inside_pen_animal_count"]),
                "outside_pen_animal_count": int(scene.trace["outside_pen_animal_count"]),
                "category_counts": dict(scene.trace["category_counts"]),
                "public_name_counts": dict(scene.trace["public_name_counts"]),
            }
        )
    _make_contact_sheet(image_paths, out_dir / "scene_contact_sheet.png")
    _make_contact_sheet(overlay_paths, out_dir / "overlay_contact_sheet.png")
    manifest = {
        "renderer_id": "pixel_farm_map_v0",
        "count": int(count),
        "base_seed": int(seed),
        "width": int(width),
        "height": int(height),
        "records": records,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme = [
        "# Pixel Farm Map Prototype",
        "",
        "Generated review scenes for a procedural old-school pixel RPG farm renderer.",
        "",
        "- `images/`: original scene renders",
        "- `overlays/`: debug renders with metadata bboxes, pen regions, and public names",
        "- `data/`: per-scene trace metadata",
        "- `scene_contact_sheet.png`: original scene overview",
        "- `overlay_contact_sheet.png`: bbox/debug overview",
        "",
        "The renderer uses no external sprites. Kenney and OpenGameArt animal packs are visual references only.",
        "Each scene samples its own grid dimensions and renders logical tiles at 32px by default.",
        "Pen regions and each animal's `inside_pen` / `region_id` metadata are recorded for future region-count tasks.",
        "No public TRACE task is registered for this prototype yet.",
    ]
    (out_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    generate_object_template_sheet(out_dir=object_out_dir)
    print(f"[done] wrote {count} pixel-farm previews to {out_dir}")
    print(f"[done] wrote pixel-world object templates to {object_out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--object-out-dir", type=Path, default=DEFAULT_OBJECT_OUT_DIR)
    parser.add_argument("--count", type=int, default=18)
    parser.add_argument("--seed", type=int, default=20260604)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()
    generate_previews(
        out_dir=args.out_dir,
        object_out_dir=args.object_out_dir,
        count=args.count,
        seed=args.seed,
        width=args.width,
        height=args.height,
    )


if __name__ == "__main__":
    main()
