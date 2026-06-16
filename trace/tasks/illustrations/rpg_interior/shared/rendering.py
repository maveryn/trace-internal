"""Scene-local top-down pixel RPG interior renderer."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from trace.tasks.illustrations.shared.object_rendering import (
    IllustrationObjectSpec,
    RenderContext,
    render_illustration_object,
)
from trace.tasks.illustrations.shared.object_variants import RENDERER_STYLE_TOP_DOWN_PIXEL_RPG
from trace.tasks.illustrations.shared.pixel_world_objects import CANONICAL_TILE_PX

from .state import BBox, RpgInteriorEntity, RpgInteriorRegion, RpgInteriorScene, TileBox


SCENE_ID = "rpg_interior"
RENDERER_ID = "rpg_interior_top_down_v0"
DEFAULT_TILE_PX = 48
DEFAULT_CANVAS_WIDTH = 960
DEFAULT_CANVAS_HEIGHT = 720
INTERIOR_TYPES: tuple[str, ...] = ("shop", "home", "inn")
ZONE_IDS: tuple[str, ...] = ("counter", "table", "shelf", "storage_corner")

TARGET_OBJECT_PUBLIC_NAMES: Mapping[str, str] = {
    "bottle": "bottle",
    "bowl": "bowl",
    "candle": "candle",
    "mug": "mug",
    "plate": "plate",
    "pot": "pot",
}
TARGET_OBJECT_PLURALS: Mapping[str, str] = {
    "bottle": "bottles",
    "bowl": "bowls",
    "candle": "candles",
    "mug": "mugs",
    "plate": "plates",
    "pot": "pots",
}
TARGET_OBJECT_TYPES: tuple[str, ...] = tuple(TARGET_OBJECT_PUBLIC_NAMES)


RGB = tuple[int, int, int]


THEMES: Mapping[str, Mapping[str, Any]] = {
    "warm_shop": {
        "wall_rgb": (170, 119, 72),
        "wall_dark_rgb": (88, 59, 39),
        "floor_rgb": (185, 128, 70),
        "floor_alt_rgb": (170, 111, 61),
        "trim_rgb": (84, 54, 35),
        "wood_rgb": (135, 80, 43),
        "rug_rgb": (155, 62, 73),
    },
    "blue_home": {
        "wall_rgb": (142, 152, 171),
        "wall_dark_rgb": (74, 80, 98),
        "floor_rgb": (156, 118, 75),
        "floor_alt_rgb": (142, 102, 63),
        "trim_rgb": (65, 67, 82),
        "wood_rgb": (121, 75, 45),
        "rug_rgb": (71, 129, 151),
    },
    "stone_inn": {
        "wall_rgb": (145, 132, 112),
        "wall_dark_rgb": (74, 68, 62),
        "floor_rgb": (130, 128, 116),
        "floor_alt_rgb": (116, 116, 106),
        "trim_rgb": (58, 56, 52),
        "wood_rgb": (128, 76, 43),
        "rug_rgb": (132, 78, 111),
    },
}


@dataclass(frozen=True)
class RpgInteriorLayout:
    """Tile grid and display geometry."""

    cols: int
    rows: int
    tile_px: int
    width_px: int
    height_px: int
    display_offset_xy: tuple[int, int]

    @property
    def canonical_width_px(self) -> int:
        return int(self.cols) * CANONICAL_TILE_PX

    @property
    def canonical_height_px(self) -> int:
        return int(self.rows) * CANONICAL_TILE_PX

    @property
    def display_grid_width_px(self) -> int:
        return int(self.cols) * int(self.tile_px)

    @property
    def display_grid_height_px(self) -> int:
        return int(self.rows) * int(self.tile_px)


@dataclass(frozen=True)
class _EntitySpec:
    entity_id: str
    object_type: str
    public_name: str
    category: str
    zone_id: str
    tile_xywh: TileBox
    layer: str
    countable: bool = False
    semantic: Mapping[str, Any] | None = None
    visual: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class _RegionSpec:
    region_id: str
    public_name: str
    relation_phrase: str
    region_type: str
    tile_xywh: TileBox
    metadata: Mapping[str, Any]


def render_rpg_interior_scene(
    seed: int,
    *,
    width: int = DEFAULT_CANVAS_WIDTH,
    height: int = DEFAULT_CANVAS_HEIGHT,
    tile_px: int = DEFAULT_TILE_PX,
    interior_type: str = "auto",
    required_zone_object_counts: Mapping[str, Mapping[str, int]] | None = None,
    distractor_count_min: int = 7,
    distractor_count_max: int = 13,
    render_metadata: Mapping[str, Any] | None = None,
) -> RpgInteriorScene:
    """Render one top-down RPG interior scene."""

    rng = random.Random(int(seed))
    layout = _sample_layout(width=int(width), height=int(height), tile_px=int(tile_px))
    requested_counts = _normalize_required_counts(required_zone_object_counts or {})
    resolved_type = _resolve_interior_type(rng, interior_type)
    theme_id = _theme_for_type(rng, resolved_type)
    floor_pattern = str(_choose(rng, ("plank", "checker", "stone")))
    theme = THEMES[theme_id]
    canvas, draw = _render_base(layout, theme=theme, floor_pattern=floor_pattern)
    region_specs, entity_specs, zone_cells = _make_plan(
        rng,
        layout=layout,
        interior_type=resolved_type,
        theme_id=theme_id,
        requested_counts=requested_counts,
        distractor_count_min=int(distractor_count_min),
        distractor_count_max=int(distractor_count_max),
    )

    regions = tuple(_make_region(spec, layout) for spec in region_specs)
    entities: list[RpgInteriorEntity] = []
    for spec in sorted(entity_specs, key=_entity_sort_key):
        bbox = _tile_bbox(layout, spec.tile_xywh)
        semantic = {
            "zone_id": str(spec.zone_id),
            "zone_public_name": _zone_public_name(regions, spec.zone_id),
            "countable": bool(spec.countable),
            "interior_type": str(resolved_type),
        }
        semantic.update(dict(spec.semantic or {}))
        visual = {"theme_id": theme_id, "renderer_style": RENDERER_STYLE_TOP_DOWN_PIXEL_RPG}
        visual.update(dict(spec.visual or {}))
        rendered = render_illustration_object(
            IllustrationObjectSpec(
                object_id=str(spec.entity_id),
                object_type=str(spec.object_type),
                public_name=str(spec.public_name),
                bbox_xyxy=bbox,
                tile_xywh=spec.tile_xywh,
                renderer_id=RENDERER_ID,
                renderer_variant_id=f"top_down:{theme_id}",
                semantic_attributes=semantic,
                visual_attributes=visual,
                role="foreground" if spec.countable else "context",
                source_entity_type="rpg_interior_entity",
            ),
            RenderContext(renderer_style=RENDERER_STYLE_TOP_DOWN_PIXEL_RPG, draw=draw),
        )
        point = ((bbox[0] + bbox[2]) * 0.5, (bbox[1] + bbox[3]) * 0.5)
        entities.append(
            RpgInteriorEntity(
                entity_id=str(spec.entity_id),
                public_name=str(spec.public_name),
                object_type=str(spec.object_type),
                category=str(spec.category),
                zone_id=str(spec.zone_id),
                tile_xywh=spec.tile_xywh,
                bbox_xyxy=bbox,
                point_xy=point,
                layer=str(spec.layer),
                countable=bool(spec.countable),
                metadata={
                    "semantic_attributes": semantic,
                    "visual_attributes": visual,
                    "object_record": rendered.object_record,
                },
            )
        )

    scaled = canvas.resize((layout.display_grid_width_px, layout.display_grid_height_px), Image.Resampling.NEAREST)
    final = Image.new("RGB", (int(width), int(height)), _shade(theme["wall_dark_rgb"], -18))
    final.paste(scaled.convert("RGB"), layout.display_offset_xy)

    trace = {
        "scene_id": SCENE_ID,
        "renderer_id": RENDERER_ID,
        "renderer_style": RENDERER_STYLE_TOP_DOWN_PIXEL_RPG,
        "seed": int(seed),
        "width": int(width),
        "height": int(height),
        "grid_cols": int(layout.cols),
        "grid_rows": int(layout.rows),
        "tile_px": int(layout.tile_px),
        "display_offset_xy": [int(value) for value in layout.display_offset_xy],
        "theme_id": str(theme_id),
        "interior_type": str(resolved_type),
        "floor_pattern": str(floor_pattern),
        "required_zone_object_counts": {
            str(zone_id): {str(obj): int(count) for obj, count in values.items()}
            for zone_id, values in requested_counts.items()
        },
        "zone_cells": {
            str(zone_id): [[int(x), int(y)] for x, y in cells]
            for zone_id, cells in zone_cells.items()
        },
        "entity_count": len(entities),
        "region_count": len(regions),
        "category_counts": _counts(entity.category for entity in entities),
        "public_name_counts": _counts(entity.public_name for entity in entities),
        "object_type_counts": _counts(entity.object_type for entity in entities),
        "regions": [region.as_dict() for region in regions],
        "entities": [entity.as_dict() for entity in entities],
        "uses_external_sprites": False,
        **dict(render_metadata or {}),
    }
    return RpgInteriorScene(image=final, entities=tuple(entities), regions=regions, trace=trace)


def draw_rpg_interior_debug_overlay(scene: RpgInteriorScene) -> Image.Image:
    """Return a debug overlay with region boxes and entity boxes."""

    image = scene.image.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    for region in scene.regions:
        draw.rectangle(region.bbox_xyxy, outline=(55, 118, 210, 220), width=2)
        draw.text((region.bbox_xyxy[0] + 2, region.bbox_xyxy[1] + 2), region.region_id, fill=(35, 75, 170, 235))
    for entity in scene.entities:
        color = (224, 62, 62, 235) if entity.countable else (72, 150, 86, 210)
        draw.rectangle(entity.bbox_xyxy, outline=color, width=2)
        draw.text((entity.bbox_xyxy[0] + 2, entity.bbox_xyxy[1] + 2), entity.entity_id, fill=color)
    return image.convert("RGB")


def _sample_layout(*, width: int, height: int, tile_px: int) -> RpgInteriorLayout:
    resolved_tile_px = max(32, min(48, int(tile_px)))
    cols = max(16, int(width) // resolved_tile_px - 2)
    rows = max(12, int(height) // resolved_tile_px - 2)
    grid_w = int(cols) * resolved_tile_px
    grid_h = int(rows) * resolved_tile_px
    if grid_w > int(width) or grid_h > int(height):
        raise ValueError(f"RPG interior grid {cols}x{rows} does not fit in {width}x{height}")
    return RpgInteriorLayout(
        cols=int(cols),
        rows=int(rows),
        tile_px=int(resolved_tile_px),
        width_px=int(width),
        height_px=int(height),
        display_offset_xy=((int(width) - grid_w) // 2, (int(height) - grid_h) // 2),
    )


def _render_base(
    layout: RpgInteriorLayout,
    *,
    theme: Mapping[str, Any],
    floor_pattern: str,
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (layout.canonical_width_px, layout.canonical_height_px), _rgba(theme["wall_dark_rgb"]))
    draw = ImageDraw.Draw(image, "RGBA")
    door_left = layout.cols // 2 - 1
    door_right = layout.cols // 2
    for y in range(layout.rows):
        for x in range(layout.cols):
            is_wall = x == 0 or x == layout.cols - 1 or y == 0 or (y == layout.rows - 1 and x not in {door_left, door_right})
            fill = theme["wall_rgb"] if is_wall else _floor_tile_rgb(theme, floor_pattern, x=x, y=y)
            outline = theme["wall_dark_rgb"] if is_wall else _shade(fill, -30)
            px = x * CANONICAL_TILE_PX
            py = y * CANONICAL_TILE_PX
            draw.rectangle((px, py, px + 15, py + 15), fill=_rgba(fill), outline=_rgba(outline, 170))
            if not is_wall and floor_pattern == "plank":
                draw.line((px + 1, py + 8, px + 14, py + 8), fill=_rgba(_shade(fill, -24), 150))
            elif not is_wall and floor_pattern == "stone" and (x + y) % 2 == 0:
                draw.line((px + 3, py + 4, px + 12, py + 3), fill=_rgba(_shade(fill, 20), 130))
    trim = theme["trim_rgb"]
    draw.rectangle((0, CANONICAL_TILE_PX - 2, layout.canonical_width_px - 1, CANONICAL_TILE_PX + 1), fill=_rgba(trim))
    draw.rectangle((CANONICAL_TILE_PX - 2, CANONICAL_TILE_PX, CANONICAL_TILE_PX + 1, layout.canonical_height_px - 1), fill=_rgba(trim))
    draw.rectangle(((layout.cols - 1) * CANONICAL_TILE_PX - 1, CANONICAL_TILE_PX, (layout.cols - 1) * CANONICAL_TILE_PX + 1, layout.canonical_height_px - 1), fill=_rgba(trim))
    ex = door_left * CANONICAL_TILE_PX
    ey = (layout.rows - 1) * CANONICAL_TILE_PX
    draw.rectangle((ex, ey + 3, ex + 31, ey + 15), fill=_rgba((57, 45, 38)), outline=_rgba((32, 26, 23)))
    for x in (2, max(3, layout.cols - 5)):
        px = x * CANONICAL_TILE_PX + 2
        draw.rectangle((px, 3, px + 23, 12), fill=_rgba((92, 145, 168)), outline=_rgba(trim))
        draw.line((px + 11, 3, px + 11, 12), fill=_rgba((220, 238, 232), 210))
        draw.line((px, 7, px + 23, 7), fill=_rgba((64, 105, 129), 210))
    return image, draw


def _make_plan(
    rng: random.Random,
    *,
    layout: RpgInteriorLayout,
    interior_type: str,
    theme_id: str,
    requested_counts: Mapping[str, Mapping[str, int]],
    distractor_count_min: int,
    distractor_count_max: int,
) -> tuple[list[_RegionSpec], list[_EntitySpec], dict[str, list[tuple[int, int]]]]:
    """Build one room layout with requested countable props placed before neutral distractors."""

    c = layout.cols // 2
    table_y = max(5, min(layout.rows - 6, layout.rows // 2))
    storage_y = layout.rows - 5
    regions = [
        _RegionSpec("counter", "counter", "on", "support_zone", (c - 3, 2, 6, 1), {"surface": True}),
        _RegionSpec("shelf", "shelf", "on", "support_zone", (2, 1, 5, 1), {"surface": True}),
        _RegionSpec("table", "table", "on", "support_zone", (c - 2, table_y, 4, 2), {"surface": True}),
        _RegionSpec("storage_corner", "storage corner", "in", "floor_zone", (1, storage_y, 6, 3), {"surface": False}),
    ]
    zone_cells = {
        "counter": _cells_for_box((c - 3, 2, 6, 1)),
        "shelf": _cells_for_box((2, 1, 5, 1)),
        "table": _cells_for_box((c - 2, table_y, 4, 2)),
        "storage_corner": _cells_for_box((1, storage_y, 6, 2)),
    }
    wood = THEMES[theme_id]["wood_rgb"]
    entities: list[_EntitySpec] = [
        _EntitySpec("rug_00", "rug", "rug", "fixture", "table", (c - 3, table_y - 1, 6, 4), "floor_fixture", visual={"cloth_rgb": THEMES[theme_id]["rug_rgb"], "trim_rgb": (226, 188, 96)}),
        _EntitySpec("counter_00", "counter", "counter", "fixture", "counter", (c - 3, 2, 6, 1), "fixture", visual={"wood_rgb": wood, "top_rgb": _shade(wood, 44)}),
        _EntitySpec("shelf_00", "shelf", "shelf", "fixture", "shelf", (2, 1, 5, 1), "fixture", visual={"wood_rgb": _shade(wood, -8), "goods_type": "books"}),
        _EntitySpec("table_00", "table", "table", "fixture", "table", (c - 2, table_y, 4, 2), "fixture", visual={"wood_rgb": wood, "table_shape": "long"}),
        _EntitySpec("crate_00", "crate", "crate", "container", "storage_corner", (1, storage_y + 2, 1, 1), "fixture"),
        _EntitySpec("barrel_00", "barrel", "barrel", "container", "storage_corner", (2, storage_y + 2, 1, 1), "fixture"),
        _EntitySpec("chest_00", "chest", "chest", "container", "storage_corner", (3, storage_y + 2, 2, 1), "fixture", visual={"wood_rgb": _shade(wood, -6)}),
    ]
    if interior_type in {"home", "inn"}:
        entities.append(_EntitySpec("bed_00", "bed", "bed", "fixture", "bed_area", (layout.cols - 5, layout.rows - 6, 3, 2), "fixture", visual={"bed_size": "single", "wood_rgb": wood, "blanket_rgb": _choose(rng, ((86, 128, 174), (157, 76, 88), (78, 138, 96)))}))
    if interior_type in {"shop", "inn"}:
        entities.append(_EntitySpec("stool_00", "stool", "stool", "fixture", "counter", (c + 3, 2, 1, 1), "fixture", visual={"wood_rgb": wood, "cushion_rgb": (147, 84, 62)}))
    if interior_type == "home":
        entities.append(_EntitySpec("fireplace_00", "fireplace", "fireplace", "fixture", "wall", (layout.cols - 4, 1, 2, 1), "fixture", visual={"fire_state": "lit"}))

    occupied: set[tuple[int, int]] = set()
    for zone_id, object_counts in requested_counts.items():
        available = list(zone_cells[str(zone_id)])
        rng.shuffle(available)
        for object_type, count in object_counts.items():
            for _ in range(int(count)):
                if not available:
                    raise ValueError(f"not enough open cells in RPG interior zone {zone_id}")
                x, y = available.pop()
                occupied.add((x, y))
                entities.append(_small_prop_spec(rng, len(entities), object_type, str(zone_id), (x, y, 1, 1), countable=True))

    distractor_total = rng.randint(int(distractor_count_min), int(distractor_count_max))
    zone_order = list(zone_cells)
    object_pool = list(TARGET_OBJECT_TYPES)
    for _ in range(distractor_total):
        rng.shuffle(zone_order)
        placed = False
        for zone_id in zone_order:
            cells = [cell for cell in zone_cells[zone_id] if cell not in occupied]
            if not cells:
                continue
            object_type = str(_choose(rng, object_pool))
            x, y = _choose(rng, cells)
            occupied.add((x, y))
            entities.append(_small_prop_spec(rng, len(entities), object_type, zone_id, (x, y, 1, 1), countable=True))
            placed = True
            break
        if not placed:
            break

    return regions, entities, zone_cells


def _small_prop_spec(
    rng: random.Random,
    index: int,
    object_type: str,
    zone_id: str,
    tile_xywh: TileBox,
    *,
    countable: bool,
) -> _EntitySpec:
    return _EntitySpec(
        entity_id=f"prop_{int(index):02d}",
        object_type=str(object_type),
        public_name=str(TARGET_OBJECT_PUBLIC_NAMES[str(object_type)]),
        category="prop",
        zone_id=str(zone_id),
        tile_xywh=tile_xywh,
        layer="prop",
        countable=bool(countable),
        visual=_small_prop_visual(rng, object_type),
        semantic={"queryable_object": True},
    )


def _small_prop_visual(rng: random.Random, object_type: str) -> dict[str, Any]:
    if object_type == "bottle":
        return {"glass_rgb": _choose(rng, ((54, 133, 94), (55, 128, 160), (142, 76, 164), (203, 130, 54)))}
    if object_type == "bowl":
        return {"ceramic_rgb": _choose(rng, ((210, 190, 148), (196, 132, 94), (143, 169, 185))), "contents_rgb": _choose(rng, ((190, 119, 62), (94, 145, 78), (208, 169, 70)))}
    if object_type == "candle":
        return {"wax_rgb": _choose(rng, ((238, 222, 171), (230, 204, 132), (205, 218, 232))), "flame_state": "lit"}
    if object_type == "mug":
        return {"ceramic_rgb": _choose(rng, ((218, 205, 165), (93, 143, 178), (178, 91, 95))), "drink_rgb": (125, 77, 42)}
    if object_type == "plate":
        return {"ceramic_rgb": _choose(rng, ((224, 218, 198), (194, 218, 224), (229, 205, 188))), "food_rgb": _choose(rng, ((190, 119, 62), (92, 150, 75), (215, 171, 72), None))}
    if object_type == "pot":
        return {"clay_rgb": _choose(rng, ((174, 94, 58), (145, 91, 65), (105, 113, 126)))}
    return {}


def _make_region(spec: _RegionSpec, layout: RpgInteriorLayout) -> RpgInteriorRegion:
    return RpgInteriorRegion(
        region_id=str(spec.region_id),
        public_name=str(spec.public_name),
        relation_phrase=str(spec.relation_phrase),
        region_type=str(spec.region_type),
        tile_xywh=spec.tile_xywh,
        bbox_xyxy=_tile_bbox(layout, spec.tile_xywh),
        metadata=dict(spec.metadata),
    )


def _tile_bbox(layout: RpgInteriorLayout, tile_xywh: TileBox) -> BBox:
    x, y, w, h = tile_xywh
    ox, oy = layout.display_offset_xy
    return (
        float(ox + int(x) * int(layout.tile_px)),
        float(oy + int(y) * int(layout.tile_px)),
        float(ox + (int(x) + int(w)) * int(layout.tile_px)),
        float(oy + (int(y) + int(h)) * int(layout.tile_px)),
    )


def _cells_for_box(tile_xywh: TileBox) -> list[tuple[int, int]]:
    x, y, w, h = tile_xywh
    return [(xx, yy) for yy in range(int(y), int(y) + int(h)) for xx in range(int(x), int(x) + int(w))]


def _entity_sort_key(spec: _EntitySpec) -> tuple[int, int, str]:
    layer_order = {"floor_fixture": 0, "fixture": 1, "prop": 2, "actor": 3}
    return (layer_order.get(str(spec.layer), 9), int(spec.tile_xywh[1]), str(spec.entity_id))


def _normalize_required_counts(raw: Mapping[str, Mapping[str, int]]) -> dict[str, dict[str, int]]:
    normalized: dict[str, dict[str, int]] = {}
    for zone_id, object_counts in raw.items():
        if str(zone_id) not in set(ZONE_IDS):
            raise ValueError(f"unsupported RPG interior zone: {zone_id}")
        normalized[str(zone_id)] = {}
        for object_type, count in object_counts.items():
            if str(object_type) not in set(TARGET_OBJECT_TYPES):
                raise ValueError(f"unsupported RPG interior object type: {object_type}")
            normalized[str(zone_id)][str(object_type)] = int(count)
    return normalized


def _resolve_interior_type(rng: random.Random, value: str) -> str:
    text = str(value).strip().lower()
    if text in {"", "auto"}:
        return str(_choose(rng, INTERIOR_TYPES))
    if text not in set(INTERIOR_TYPES):
        raise ValueError(f"interior_type must be one of {INTERIOR_TYPES} or auto")
    return text


def _theme_for_type(rng: random.Random, interior_type: str) -> str:
    if interior_type == "shop":
        return str(_choose(rng, ("warm_shop", "stone_inn")))
    if interior_type == "home":
        return str(_choose(rng, ("blue_home", "warm_shop")))
    return str(_choose(rng, ("stone_inn", "warm_shop")))


def _zone_public_name(regions: Sequence[RpgInteriorRegion], zone_id: str) -> str:
    for region in regions:
        if region.region_id == str(zone_id):
            return str(region.public_name)
    return str(zone_id).replace("_", " ")


def _floor_tile_rgb(theme: Mapping[str, Any], floor_pattern: str, *, x: int, y: int) -> RGB:
    base = theme["floor_rgb"]
    alt = theme["floor_alt_rgb"]
    if floor_pattern == "checker":
        return alt if (int(x) + int(y)) % 2 else base
    if floor_pattern == "stone":
        return _shade(base, -9 if (int(x) * 3 + int(y) * 5) % 4 == 0 else 10)
    return _shade(base, -10 if int(y) % 2 else 8)


def _counts(values: Sequence[str] | Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _choose(rng: random.Random, values: Sequence[Any]) -> Any:
    if not values:
        raise ValueError("cannot choose from an empty sequence")
    return values[int(rng.randrange(len(values)))]


def _rgba(color: Any, alpha: int = 255) -> tuple[int, int, int, int]:
    r, g, b = tuple(int(v) for v in color)
    return (r, g, b, int(alpha))


def _shade(color: Any, delta: int) -> RGB:
    return tuple(max(0, min(255, int(channel) + int(delta))) for channel in color)  # type: ignore[return-value]


__all__ = [
    "DEFAULT_CANVAS_HEIGHT",
    "DEFAULT_CANVAS_WIDTH",
    "DEFAULT_TILE_PX",
    "INTERIOR_TYPES",
    "RENDERER_ID",
    "SCENE_ID",
    "TARGET_OBJECT_PLURALS",
    "TARGET_OBJECT_PUBLIC_NAMES",
    "TARGET_OBJECT_TYPES",
    "ZONE_IDS",
    "draw_rpg_interior_debug_overlay",
    "render_rpg_interior_scene",
]
