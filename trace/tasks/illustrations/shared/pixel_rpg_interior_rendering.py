"""Procedural pixel RPG interior renderer prototypes.

This module is intentionally not a public task. It is a renderer prototype for
reviewing whether classic RPG-like interiors can support future illustration
tasks over rooms, zones, shelves, counters, people, and portable props.
"""

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
from trace.tasks.illustrations.shared.object_variants import (
    RENDERER_STYLE_ISOMETRIC_PIXEL_RPG,
    RENDERER_STYLE_TOP_DOWN_PIXEL_RPG,
)
from trace.tasks.illustrations.shared.pixel_world_objects import CANONICAL_TILE_PX


BBox = tuple[float, float, float, float]
IsoPoint = tuple[float, float]
IsoPolygon = tuple[IsoPoint, ...]
RGB = tuple[int, int, int]
TileBox = tuple[int, int, int, int]

SCENE_ID = "pixel_rpg_general_store"
RENDERER_ID = "pixel_rpg_general_store_v0"
DEFAULT_DISPLAY_TILE_PX = 32
DEFAULT_SCALE = 2
CANONICAL_ISO_TILE_W_PX = 32
CANONICAL_ISO_TILE_H_PX = 16

REFERENCE_SOURCES = {
    "kenney_roguelike_rpg_pack": {
        "name": "Kenney Roguelike/RPG pack",
        "url": "https://kenney.nl/assets/roguelike-rpg-pack",
        "notes": "CC0 pixel RPG pack used as visual reference only; no sprites are loaded.",
    },
    "kenney_rpg_urban_pack": {
        "name": "Kenney RPG Urban Pack",
        "url": "https://kenney.nl/assets/rpg-urban-pack",
        "notes": "CC0 RPG prop pack used as visual reference only; no sprites are loaded.",
    },
}


@dataclass(frozen=True)
class PixelRpgInteriorLayout:
    """Grid, projection, and display geometry for one RPG interior."""

    cols: int
    rows: int
    projection: str
    tile_px: int
    width_px: int
    height_px: int
    scale: int
    origin_xy: tuple[int, int]
    display_offset_xy: tuple[int, int]

    @property
    def canonical_width_px(self) -> int:
        if self.projection == "isometric":
            return max(1, int(self.width_px) // max(1, int(self.scale)))
        return int(self.cols) * CANONICAL_TILE_PX

    @property
    def canonical_height_px(self) -> int:
        if self.projection == "isometric":
            return max(1, int(self.height_px) // max(1, int(self.scale)))
        return int(self.rows) * CANONICAL_TILE_PX

    @property
    def display_grid_width_px(self) -> int:
        return int(self.cols) * int(self.tile_px)

    @property
    def display_grid_height_px(self) -> int:
        return int(self.rows) * int(self.tile_px)


@dataclass(frozen=True)
class PixelRpgInteriorRegion:
    """One semantic zone in an RPG interior."""

    region_id: str
    public_name: str
    region_type: str
    tile_xywh: TileBox
    bbox_xyxy: BBox
    polygon_xy: IsoPolygon
    metadata: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "region_id": str(self.region_id),
            "public_name": str(self.public_name),
            "region_type": str(self.region_type),
            "tile_xywh": [int(v) for v in self.tile_xywh],
            "bbox": [round(float(v), 3) for v in self.bbox_xyxy],
            "polygon": [[round(float(x), 3), round(float(y), 3)] for x, y in self.polygon_xy],
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class PixelRpgInteriorEntity:
    """One semantic entity in the generated RPG interior."""

    entity_id: str
    public_name: str
    object_type: str
    category: str
    tile_xywh: TileBox
    bbox_xyxy: BBox
    footprint_polygon_xy: IsoPolygon
    anchor_screen_xy: IsoPoint
    layer: str
    metadata: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        metadata = {str(key): value for key, value in self.metadata.items() if str(key) != "object_record"}
        payload = {
            "entity_id": str(self.entity_id),
            "public_name": str(self.public_name),
            "object_type": str(self.object_type),
            "category": str(self.category),
            "tile_xywh": [int(v) for v in self.tile_xywh],
            "bbox": [round(float(v), 3) for v in self.bbox_xyxy],
            "footprint_polygon": [[round(float(x), 3), round(float(y), 3)] for x, y in self.footprint_polygon_xy],
            "anchor_screen_xy": [round(float(v), 3) for v in self.anchor_screen_xy],
            "center_tile_xy": [
                round(float(self.tile_xywh[0]) + (float(self.tile_xywh[2]) - 1.0) * 0.5, 3),
                round(float(self.tile_xywh[1]) + (float(self.tile_xywh[3]) - 1.0) * 0.5, 3),
            ],
            "layer": str(self.layer),
            "metadata": metadata,
        }
        if "object_record" in self.metadata:
            payload["object_record"] = self.metadata["object_record"]
        return payload


@dataclass(frozen=True)
class PixelRpgInteriorScene:
    """Rendered RPG interior scene plus trace metadata."""

    image: Image.Image
    entities: tuple[PixelRpgInteriorEntity, ...]
    regions: tuple[PixelRpgInteriorRegion, ...]
    trace: Mapping[str, Any]


THEMES: Mapping[str, Mapping[str, Any]] = {
    "warm_wood": {
        "wall_rgb": (177, 128, 78),
        "wall_dark_rgb": (111, 74, 44),
        "floor_rgb": (188, 132, 72),
        "floor_alt_rgb": (174, 115, 62),
        "trim_rgb": (92, 59, 37),
        "counter_rgb": (142, 82, 45),
        "rug_rgb": (164, 66, 73),
    },
    "bright_market": {
        "wall_rgb": (209, 178, 116),
        "wall_dark_rgb": (132, 96, 58),
        "floor_rgb": (196, 155, 95),
        "floor_alt_rgb": (184, 141, 82),
        "trim_rgb": (108, 74, 45),
        "counter_rgb": (158, 94, 48),
        "rug_rgb": (73, 132, 155),
    },
    "stone_floor": {
        "wall_rgb": (159, 138, 112),
        "wall_dark_rgb": (88, 78, 72),
        "floor_rgb": (137, 139, 128),
        "floor_alt_rgb": (121, 126, 118),
        "trim_rgb": (70, 67, 62),
        "counter_rgb": (133, 83, 47),
        "rug_rgb": (154, 72, 101),
    },
    "rustic_shop": {
        "wall_rgb": (154, 110, 69),
        "wall_dark_rgb": (84, 58, 39),
        "floor_rgb": (152, 102, 56),
        "floor_alt_rgb": (136, 89, 50),
        "trim_rgb": (72, 47, 32),
        "counter_rgb": (118, 72, 44),
        "rug_rgb": (79, 135, 83),
    },
}


def render_pixel_rpg_general_store(
    seed: int,
    *,
    width: int = 960,
    height: int = 720,
    projection: str = "top_down",
    tile_px: int = DEFAULT_DISPLAY_TILE_PX,
    grid_cols: int | None = None,
    grid_rows: int | None = None,
) -> PixelRpgInteriorScene:
    """Render one deterministic procedural RPG general-store interior."""

    resolved_projection = _normalize_projection(projection)
    rng = random.Random(int(seed))
    layout = _sample_layout(
        rng,
        width=int(width),
        height=int(height),
        projection=resolved_projection,
        tile_px=int(tile_px),
        grid_cols=grid_cols,
        grid_rows=grid_rows,
    )
    theme_id = str(_choose(rng, tuple(THEMES)))
    theme = THEMES[theme_id]
    floor_pattern = str(_choose(rng, ("plank", "checker", "stone")))
    shelf_goods = [str(_choose(rng, ("jars", "produce", "books", "mixed"))) for _ in range(2)]
    produce_goods = str(_choose(rng, ("fruit", "vegetable", "grain")))
    plan = _make_general_store_plan(
        rng,
        layout=layout,
        theme_id=theme_id,
        shelf_goods=shelf_goods,
        produce_goods=produce_goods,
    )

    if layout.projection == "top_down":
        canvas, draw, project_tile_center = _render_top_down_base(layout, theme=theme, floor_pattern=floor_pattern)
        renderer_style = RENDERER_STYLE_TOP_DOWN_PIXEL_RPG
    else:
        canvas, draw, project_tile_center = _render_isometric_base(layout, theme=theme, floor_pattern=floor_pattern)
        renderer_style = RENDERER_STYLE_ISOMETRIC_PIXEL_RPG

    regions = tuple(
        _make_region(region_id, public_name, region_type, tile_xywh, layout, metadata)
        for region_id, public_name, region_type, tile_xywh, metadata in plan["regions"]
    )

    entities: list[PixelRpgInteriorEntity] = []
    for spec_data in sorted(plan["entities"], key=lambda item: _entity_sort_key(item, layout)):
        tile_xywh = tuple(int(v) for v in spec_data["tile_xywh"])  # type: ignore[assignment]
        bbox_xyxy = _entity_bbox(tile_xywh, str(spec_data["object_type"]), layout)
        footprint_polygon = _footprint_polygon_display(layout, tile_xywh)
        anchor_screen_xy = _anchor_screen_xy(layout, tile_xywh)
        visual = dict(spec_data.get("visual_attributes", {}))
        visual.setdefault("theme_id", theme_id)
        semantic = dict(spec_data.get("semantic_attributes", {}))
        spec = IllustrationObjectSpec(
            object_id=str(spec_data["entity_id"]),
            object_type=str(spec_data["object_type"]),
            public_name=str(spec_data["public_name"]),
            bbox_xyxy=bbox_xyxy,
            tile_xywh=tile_xywh,
            variant_id=str(spec_data.get("variant_id", "")),
            renderer_id=RENDERER_ID,
            renderer_variant_id=f"{layout.projection}:{theme_id}",
            semantic_attributes=semantic,
            visual_attributes=visual,
            role=str(spec_data.get("role", "foreground")),
            source_entity_type="pixel_rpg_general_store_entity",
        )
        if layout.projection == "top_down":
            rendered = render_illustration_object(spec, RenderContext(renderer_style=renderer_style, draw=draw))
        else:
            rendered = render_illustration_object(
                spec,
                RenderContext(
                    renderer_style=renderer_style,
                    image=canvas,
                    project_tile_center=project_tile_center,
                ),
            )
        metadata = {
            "zone_id": str(semantic.get("zone_id", "")),
            "required": bool(spec_data.get("required", False)),
            "logical_role": str(spec_data.get("logical_role", "")),
            "visual_attributes": visual,
            "semantic_attributes": semantic,
            "object_record": rendered.object_record,
        }
        entities.append(
            PixelRpgInteriorEntity(
                entity_id=str(spec_data["entity_id"]),
                public_name=str(spec_data["public_name"]),
                object_type=str(spec_data["object_type"]),
                category=str(spec_data["category"]),
                tile_xywh=tile_xywh,
                bbox_xyxy=bbox_xyxy,
                footprint_polygon_xy=footprint_polygon,
                anchor_screen_xy=anchor_screen_xy,
                layer=str(spec_data["layer"]),
                metadata=metadata,
            )
        )

    if layout.projection == "top_down":
        rendered_grid = canvas.resize((layout.display_grid_width_px, layout.display_grid_height_px), Image.Resampling.NEAREST)
        final = Image.new("RGB", (int(width), int(height)), _shade(theme["floor_rgb"], -54))
        final.paste(rendered_grid.convert("RGB"), layout.display_offset_xy)
    else:
        final = canvas.resize((int(width), int(height)), Image.Resampling.NEAREST).convert("RGB")

    category_counts = _counts(entity.category for entity in entities)
    public_name_counts = _counts(entity.public_name for entity in entities)
    object_type_counts = _counts(entity.object_type for entity in entities)
    trace = {
        "scene_id": SCENE_ID,
        "renderer_id": RENDERER_ID,
        "renderer_style": renderer_style,
        "projection": layout.projection,
        "seed": int(seed),
        "width": int(width),
        "height": int(height),
        "grid_cols": int(layout.cols),
        "grid_rows": int(layout.rows),
        "tile_px": int(layout.tile_px),
        "scale": int(layout.scale),
        "origin_xy": [int(v) for v in layout.origin_xy],
        "display_offset_xy": [int(v) for v in layout.display_offset_xy],
        "theme_id": theme_id,
        "floor_pattern": floor_pattern,
        "shelf_goods": list(shelf_goods),
        "produce_goods": produce_goods,
        "region_count": len(regions),
        "entity_count": len(entities),
        "category_counts": category_counts,
        "public_name_counts": public_name_counts,
        "object_type_counts": object_type_counts,
        "required_object_types": [
            "counter",
            "person",
            "shelf",
            "produce_bin",
            "crate",
            "barrel",
            "jar",
            "pot",
            "basket",
            "notice_board",
        ],
        "uses_external_sprites": False,
        "reference_sources": dict(REFERENCE_SOURCES),
        "regions": [region.as_dict() for region in regions],
        "entities": [entity.as_dict() for entity in entities],
    }
    return PixelRpgInteriorScene(image=final, entities=tuple(entities), regions=regions, trace=trace)


def draw_pixel_rpg_general_store_debug_overlay(scene: PixelRpgInteriorScene) -> Image.Image:
    """Return a debug overlay with region polygons and entity bboxes."""

    image = scene.image.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    for region in scene.regions:
        if region.polygon_xy:
            points = [(float(x), float(y)) for x, y in region.polygon_xy]
            draw.polygon(points, outline=(60, 120, 220, 210))
        else:
            draw.rectangle(region.bbox_xyxy, outline=(60, 120, 220, 210), width=2)
        x0, y0, _, _ = region.bbox_xyxy
        draw.text((x0 + 2, y0 + 2), region.region_id, fill=(40, 80, 160, 230))
    for entity in scene.entities:
        color = (216, 58, 58, 230) if entity.metadata.get("required") else (72, 154, 82, 220)
        draw.rectangle(entity.bbox_xyxy, outline=color, width=2)
        draw.text((entity.bbox_xyxy[0] + 2, entity.bbox_xyxy[1] + 2), entity.entity_id, fill=color)
    return image.convert("RGB")


def _sample_layout(
    rng: random.Random,
    *,
    width: int,
    height: int,
    projection: str,
    tile_px: int,
    grid_cols: int | None,
    grid_rows: int | None,
) -> PixelRpgInteriorLayout:
    if grid_cols is None or grid_rows is None:
        cols, rows = _choose(rng, ((14, 10), (16, 11)))
        cols = int(grid_cols) if grid_cols is not None else int(cols)
        rows = int(grid_rows) if grid_rows is not None else int(rows)
    else:
        cols = int(grid_cols)
        rows = int(grid_rows)
    if cols < 14 or rows < 10:
        raise ValueError("general-store interior grid must be at least 14x10")
    if cols > 16 or rows > 11:
        raise ValueError("general-store interior prototype supports grids up to 16x11")

    resolved_tile_px = max(24, min(40, int(tile_px)))
    if projection == "top_down":
        grid_w = cols * resolved_tile_px
        grid_h = rows * resolved_tile_px
        if grid_w > int(width) or grid_h > int(height):
            raise ValueError(f"top-down general store grid {cols}x{rows} does not fit in {width}x{height}")
        return PixelRpgInteriorLayout(
            cols=cols,
            rows=rows,
            projection=projection,
            tile_px=resolved_tile_px,
            width_px=int(width),
            height_px=int(height),
            scale=1,
            origin_xy=(0, 0),
            display_offset_xy=((int(width) - grid_w) // 2, (int(height) - grid_h) // 2),
        )

    scale = max(1, int(round(float(resolved_tile_px) / 16.0)))
    canonical_w = max(1, int(width) // scale)
    canonical_h = max(1, int(height) // scale)
    x_min = -((rows - 1) * 16) - 24
    x_max = ((cols - 1) * 16) + 24
    y_min = -56
    y_max = ((cols + rows - 2) * 8) + 36
    origin_x = int(round((canonical_w - (x_min + x_max)) * 0.5))
    origin_y = int(round((canonical_h - (y_max - y_min)) * 0.5 - y_min))
    return PixelRpgInteriorLayout(
        cols=cols,
        rows=rows,
        projection=projection,
        tile_px=resolved_tile_px,
        width_px=int(width),
        height_px=int(height),
        scale=scale,
        origin_xy=(origin_x, origin_y),
        display_offset_xy=(0, 0),
    )


def _make_general_store_plan(
    rng: random.Random,
    *,
    layout: PixelRpgInteriorLayout,
    theme_id: str,
    shelf_goods: Sequence[str],
    produce_goods: str,
) -> dict[str, Any]:
    cols = layout.cols
    rows = layout.rows
    c = cols // 2
    regions = [
        ("entrance", "entrance", "entry", (c - 1, rows - 1, 2, 1), {"open_to_room": True}),
        ("counter_zone", "counter zone", "service", (c - 2, 1, 5, 3), {"contains_vendor": True}),
        ("back_wall", "back wall", "wall", (1, 0, cols - 2, 2), {}),
        ("left_wall", "left wall", "wall", (0, 1, 2, rows - 2), {}),
        ("right_wall", "right wall", "wall", (cols - 2, 1, 2, rows - 2), {}),
        ("center_aisle", "center aisle", "walkway", (4, 4, cols - 8, rows - 5), {"kept_clear": True}),
        ("storage_corner", "storage corner", "storage", (1, rows - 3, 4, 2), {}),
    ]
    counter_rgb = THEMES[theme_id]["counter_rgb"]
    shelf_rgb = _shade(counter_rgb, -8)
    rug_rgb = THEMES[theme_id]["rug_rgb"]
    entities: list[dict[str, Any]] = []

    def add(
        entity_id: str,
        object_type: str,
        public_name: str,
        category: str,
        tile_xywh: TileBox,
        layer: str,
        zone_id: str,
        *,
        required: bool = False,
        logical_role: str = "",
        variant_id: str = "",
        semantic: Mapping[str, Any] | None = None,
        visual: Mapping[str, Any] | None = None,
    ) -> None:
        semantic_attrs = {"zone_id": str(zone_id)}
        semantic_attrs.update(dict(semantic or {}))
        visual_attrs = {"theme_id": theme_id}
        visual_attrs.update(dict(visual or {}))
        entities.append(
            {
                "entity_id": str(entity_id),
                "object_type": str(object_type),
                "public_name": str(public_name),
                "category": str(category),
                "tile_xywh": tuple(int(v) for v in tile_xywh),
                "layer": str(layer),
                "required": bool(required),
                "logical_role": str(logical_role),
                "variant_id": str(variant_id),
                "semantic_attributes": semantic_attrs,
                "visual_attributes": visual_attrs,
            }
        )

    add(
        "rug_00",
        "rug",
        "rug",
        "fixture",
        (c - 2, min(rows - 4, 5), 3, 2),
        "floor_fixture",
        "center_aisle",
        visual={"cloth_rgb": rug_rgb, "trim_rgb": (230, 190, 96)},
    )
    add(
        "counter_00",
        "counter",
        "counter",
        "fixture",
        (c - 1, 2, 3, 1),
        "fixture",
        "counter_zone",
        required=True,
        logical_role="service_counter",
        visual={"wood_rgb": counter_rgb, "top_rgb": _shade(counter_rgb, 42)},
    )
    add(
        "vendor_00",
        "person",
        "person",
        "person",
        (c, 1, 1, 1),
        "actor",
        "counter_zone",
        required=True,
        logical_role="vendor",
        variant_id="vendor",
        semantic={"activity": "vendor", "activity_label": "vendor"},
        visual={
            "person_variant_id": "vendor",
            "gender_id": "female" if rng.random() < 0.5 else "male",
            "facing": "down" if layout.projection == "top_down" else "right",
            "shirt_rgb": _choose(rng, ((70, 123, 178), (183, 76, 88), (72, 143, 92))),
            "pants_rgb": (63, 65, 82),
            "hair_rgb": _choose(rng, ((78, 48, 31), (110, 72, 42), (45, 39, 34))),
            "skin_rgb": _choose(rng, ((232, 177, 111), (196, 128, 82), (238, 196, 139))),
        },
    )
    add(
        "shelf_00",
        "shelf",
        "shelf",
        "fixture",
        (2, 1, 3, 1),
        "fixture",
        "back_wall",
        required=True,
        logical_role="back_left_shelf",
        visual={"wood_rgb": shelf_rgb, "goods_type": shelf_goods[0]},
    )
    add(
        "shelf_01",
        "shelf",
        "shelf",
        "fixture",
        (cols - 5, 1, 3, 1),
        "fixture",
        "back_wall",
        required=True,
        logical_role="back_right_shelf",
        visual={"wood_rgb": shelf_rgb, "goods_type": shelf_goods[1]},
    )
    add(
        "produce_bin_00",
        "produce_bin",
        "produce bin",
        "fixture",
        (cols - 5, 4, 2, 1),
        "fixture",
        "right_wall",
        required=True,
        logical_role="produce_display",
        visual={"wood_rgb": _shade(counter_rgb, -4), "goods_type": produce_goods},
    )
    add("crate_00", "crate", "crate", "container", (1, rows - 3, 1, 1), "prop", "storage_corner", required=True)
    add("barrel_00", "barrel", "barrel", "container", (2, rows - 3, 1, 1), "prop", "storage_corner", required=True)
    add("crate_01", "crate", "crate", "container", (1, rows - 2, 1, 1), "prop", "storage_corner")
    add("sack_00", "sack", "sack", "container", (3, rows - 3, 1, 1), "prop", "storage_corner")
    add("jar_00", "jar", "jar", "container", (4, 3, 1, 1), "prop", "left_wall", required=True)
    add("pot_00", "pot", "pot", "container", (3, 4, 1, 1), "prop", "left_wall", required=True)
    add("basket_00", "basket", "basket", "container", (4, 4, 1, 1), "prop", "left_wall", required=True)
    add(
        "notice_board_00",
        "notice_board",
        "notice board",
        "fixture",
        (cols - 3, 2, 2, 1),
        "fixture",
        "right_wall",
        required=True,
        logical_role="price_notice",
    )

    if rng.random() < 0.7:
        add("chest_00", "chest", "chest", "container", (cols - 4, rows - 3, 2, 1), "prop", "right_wall")
    if rng.random() < 0.55:
        add("basket_01", "basket", "basket", "container", (cols - 4, rows - 2, 1, 1), "prop", "right_wall")
    if rng.random() < 0.5:
        add("jar_01", "jar", "jar", "container", (5, 2, 1, 1), "prop", "back_wall")
    if rng.random() < 0.45:
        add("sack_01", "sack", "sack", "container", (2, rows - 2, 1, 1), "prop", "storage_corner")

    return {"regions": regions, "entities": entities}


def _render_top_down_base(
    layout: PixelRpgInteriorLayout,
    *,
    theme: Mapping[str, Any],
    floor_pattern: str,
) -> tuple[Image.Image, ImageDraw.ImageDraw, Any]:
    image = Image.new("RGBA", (layout.canonical_width_px, layout.canonical_height_px), _rgba(theme["wall_dark_rgb"]))
    draw = ImageDraw.Draw(image, "RGBA")
    for y in range(layout.rows):
        for x in range(layout.cols):
            if x == 0 or x == layout.cols - 1 or y == 0:
                fill = theme["wall_rgb"]
                outline = theme["wall_dark_rgb"]
            elif y == layout.rows - 1 and x not in {layout.cols // 2 - 1, layout.cols // 2}:
                fill = theme["wall_dark_rgb"]
                outline = _shade(theme["wall_dark_rgb"], -20)
            else:
                fill = _floor_tile_rgb(theme, floor_pattern, x=x, y=y)
                outline = _shade(fill, -28)
            px = x * CANONICAL_TILE_PX
            py = y * CANONICAL_TILE_PX
            draw.rectangle((px, py, px + 15, py + 15), fill=_rgba(fill), outline=_rgba(outline, 150))
            if floor_pattern == "plank" and not (x == 0 or x == layout.cols - 1 or y == 0):
                draw.line((px + 1, py + 8, px + 14, py + 8), fill=_rgba(_shade(fill, -22), 160))
            elif floor_pattern == "stone" and not (x == 0 or x == layout.cols - 1 or y == 0):
                draw.line((px + 2, py + 3, px + 12, py + 2), fill=_rgba(_shade(fill, 20), 130))
                draw.line((px + 4, py + 12, px + 14, py + 11), fill=_rgba(_shade(fill, -28), 130))
    trim = theme["trim_rgb"]
    draw.rectangle((0, CANONICAL_TILE_PX - 2, layout.canonical_width_px - 1, CANONICAL_TILE_PX + 1), fill=_rgba(trim))
    draw.rectangle((CANONICAL_TILE_PX - 2, CANONICAL_TILE_PX, CANONICAL_TILE_PX + 1, layout.canonical_height_px - 1), fill=_rgba(trim))
    draw.rectangle(((layout.cols - 1) * 16 - 1, CANONICAL_TILE_PX, (layout.cols - 1) * 16 + 1, layout.canonical_height_px - 1), fill=_rgba(trim))
    ex = (layout.cols // 2 - 1) * 16
    ey = (layout.rows - 1) * 16
    draw.rectangle((ex, ey + 3, ex + 31, ey + 15), fill=_rgba((57, 45, 38)), outline=_rgba((32, 26, 23)))
    _draw_top_down_wall_fixtures(draw, layout, theme=theme)

    def project_tile_center(tile_xywh: TileBox, level: int) -> tuple[float, float]:
        x, y, w, h = tile_xywh
        return (
            float((x + (w - 1) * 0.5) * CANONICAL_TILE_PX + CANONICAL_TILE_PX * 0.5),
            float((y + (h - 1) * 0.5) * CANONICAL_TILE_PX + CANONICAL_TILE_PX * 0.5 - int(level) * 12),
        )

    return image, draw, project_tile_center


def _render_isometric_base(
    layout: PixelRpgInteriorLayout,
    *,
    theme: Mapping[str, Any],
    floor_pattern: str,
) -> tuple[Image.Image, ImageDraw.ImageDraw, Any]:
    image = Image.new("RGBA", (layout.canonical_width_px, layout.canonical_height_px), _rgba(_shade(theme["floor_rgb"], -58)))
    draw = ImageDraw.Draw(image, "RGBA")

    def project_tile_center(tile_xywh: TileBox, level: int) -> tuple[float, float]:
        x, y, w, h = tile_xywh
        center_x = float(x) + (float(w) - 1.0) * 0.5
        center_y = float(y) + (float(h) - 1.0) * 0.5
        return _project_c(layout, center_x, center_y, int(level))

    _draw_isometric_walls(draw, layout, theme=theme)
    for y in range(layout.rows):
        for x in range(layout.cols):
            cx, cy = _project_c(layout, float(x), float(y), 0)
            fill = _floor_tile_rgb(theme, floor_pattern, x=x, y=y)
            diamond = [(cx, cy - 8), (cx + 16, cy), (cx, cy + 8), (cx - 16, cy)]
            draw.polygon(diamond, fill=_rgba(fill), outline=_rgba(_shade(fill, -34), 210))
            if floor_pattern == "plank":
                draw.line((cx - 8, cy, cx, cy + 4, cx + 8, cy), fill=_rgba(_shade(fill, -25), 160))
            elif floor_pattern == "stone" and (x + y) % 2 == 0:
                draw.line((cx - 5, cy - 2, cx + 5, cy + 2), fill=_rgba(_shade(fill, 24), 130))
    _draw_isometric_wall_fixtures(draw, layout, theme=theme)
    return image, draw, project_tile_center


def _draw_top_down_wall_fixtures(draw: ImageDraw.ImageDraw, layout: PixelRpgInteriorLayout, *, theme: Mapping[str, Any]) -> None:
    trim = theme["trim_rgb"]
    glass = (91, 144, 166)
    for x in (2, layout.cols - 4):
        px = x * 16 + 2
        draw.rectangle((px, 3, px + 19, 12), fill=_rgba(glass), outline=_rgba(trim))
        draw.line((px + 9, 3, px + 9, 12), fill=_rgba((218, 236, 230), 210))
        draw.line((px, 7, px + 19, 7), fill=_rgba((64, 105, 129), 210))
    for x in (1, layout.cols - 2):
        px = x * 16 + 5
        draw.rectangle((px, 20, px + 5, 29), fill=_rgba((105, 72, 45)), outline=_rgba((58, 41, 31)))
        draw.point((px + 2, 22), fill=_rgba((244, 202, 90)))


def _draw_isometric_walls(draw: ImageDraw.ImageDraw, layout: PixelRpgInteriorLayout, *, theme: Mapping[str, Any]) -> None:
    wall = theme["wall_rgb"]
    wall_dark = theme["wall_dark_rgb"]
    trim = theme["trim_rgb"]
    wall_h = 28
    for x in range(layout.cols):
        cx, cy = _project_c(layout, float(x), 0.0, 0)
        edge = [(cx - 16, cy), (cx, cy - 8), (cx + 16, cy), (cx, cy + 8)]
        face = [(edge[0][0], edge[0][1] - wall_h), (edge[1][0], edge[1][1] - wall_h), edge[1], edge[0]]
        draw.polygon(face, fill=_rgba(wall), outline=_rgba(wall_dark))
        draw.line((edge[0][0], edge[0][1], edge[1][0], edge[1][1]), fill=_rgba(trim))
    for y in range(1, layout.rows):
        for side_x, shade_delta in ((0, -14), (layout.cols - 1, -26)):
            cx, cy = _project_c(layout, float(side_x), float(y), 0)
            edge = [(cx - 16, cy), (cx, cy + 8)] if side_x == 0 else [(cx + 16, cy), (cx, cy + 8)]
            face = [(edge[0][0], edge[0][1] - wall_h), (edge[1][0], edge[1][1] - wall_h), edge[1], edge[0]]
            draw.polygon(face, fill=_rgba(_shade(wall, shade_delta)), outline=_rgba(wall_dark))
            draw.line((edge[0][0], edge[0][1], edge[1][0], edge[1][1]), fill=_rgba(trim))


def _draw_isometric_wall_fixtures(draw: ImageDraw.ImageDraw, layout: PixelRpgInteriorLayout, *, theme: Mapping[str, Any]) -> None:
    trim = theme["trim_rgb"]
    for x in (2, layout.cols - 4):
        cx, cy = _project_c(layout, float(x), 0.0, 0)
        y0 = cy - 34
        draw.polygon([(cx - 10, y0), (cx, y0 - 5), (cx + 12, y0), (cx + 2, y0 + 5)], fill=_rgba((90, 143, 166)), outline=_rgba(trim))
        draw.line((cx, y0 - 4, cx + 1, y0 + 4), fill=_rgba((218, 236, 230), 210))


def _make_region(
    region_id: str,
    public_name: str,
    region_type: str,
    tile_xywh: TileBox,
    layout: PixelRpgInteriorLayout,
    metadata: Mapping[str, Any],
) -> PixelRpgInteriorRegion:
    polygon = _footprint_polygon_display(layout, tile_xywh)
    bbox = _bbox_from_points(polygon) if layout.projection == "isometric" else _top_down_tile_bbox(layout, tile_xywh)
    return PixelRpgInteriorRegion(
        region_id=str(region_id),
        public_name=str(public_name),
        region_type=str(region_type),
        tile_xywh=tile_xywh,
        bbox_xyxy=bbox,
        polygon_xy=polygon if layout.projection == "isometric" else tuple(),
        metadata=dict(metadata),
    )


def _top_down_tile_bbox(layout: PixelRpgInteriorLayout, tile_xywh: TileBox) -> BBox:
    x, y, w, h = tile_xywh
    ox, oy = layout.display_offset_xy
    return (
        float(ox + x * layout.tile_px),
        float(oy + y * layout.tile_px),
        float(ox + (x + w) * layout.tile_px),
        float(oy + (y + h) * layout.tile_px),
    )


def _entity_bbox(tile_xywh: TileBox, object_type: str, layout: PixelRpgInteriorLayout) -> BBox:
    if layout.projection == "top_down":
        return _top_down_tile_bbox(layout, tile_xywh)
    polygon = _footprint_polygon_display(layout, tile_xywh)
    x0, y0, x1, y1 = _bbox_from_points(polygon)
    top_extra = {
        "person": 34,
        "shelf": 28,
        "counter": 22,
        "produce_bin": 18,
        "notice_board": 24,
        "chest": 16,
        "barrel": 16,
        "crate": 14,
        "sack": 14,
        "jar": 14,
        "pot": 14,
        "basket": 12,
    }.get(str(object_type), 12)
    bottom_extra = 16
    scale = float(layout.scale)
    return _clamp_bbox(
        (x0, y0 - top_extra * scale, x1, y1 + bottom_extra * scale),
        width=layout.width_px,
        height=layout.height_px,
    )


def _footprint_polygon_display(layout: PixelRpgInteriorLayout, tile_xywh: TileBox) -> IsoPolygon:
    if layout.projection == "top_down":
        x0, y0, x1, y1 = _top_down_tile_bbox(layout, tile_xywh)
        return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    x, y, w, h = tile_xywh
    corners = (
        (float(x) - 0.5, float(y) - 0.5),
        (float(x + w) - 0.5, float(y) - 0.5),
        (float(x + w) - 0.5, float(y + h) - 0.5),
        (float(x) - 0.5, float(y + h) - 0.5),
    )
    return tuple(_to_display(layout, _project_c(layout, col, row, 0)) for col, row in corners)


def _anchor_screen_xy(layout: PixelRpgInteriorLayout, tile_xywh: TileBox) -> IsoPoint:
    if layout.projection == "top_down":
        x0, y0, x1, y1 = _top_down_tile_bbox(layout, tile_xywh)
        return ((x0 + x1) * 0.5, (y0 + y1) * 0.5)
    x, y, w, h = tile_xywh
    point = _project_c(layout, float(x) + (float(w) - 1.0) * 0.5, float(y) + (float(h) - 1.0) * 0.5, 0)
    return _to_display(layout, point)


def _project_c(layout: PixelRpgInteriorLayout, col: float, row: float, level: int) -> IsoPoint:
    ox, oy = layout.origin_xy
    return (
        float(ox) + (float(col) - float(row)) * (CANONICAL_ISO_TILE_W_PX * 0.5),
        float(oy) + (float(col) + float(row)) * (CANONICAL_ISO_TILE_H_PX * 0.5) - float(level) * 12.0,
    )


def _to_display(layout: PixelRpgInteriorLayout, point: IsoPoint) -> IsoPoint:
    return (float(point[0]) * float(layout.scale), float(point[1]) * float(layout.scale))


def _bbox_from_points(points: Sequence[IsoPoint]) -> BBox:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _clamp_bbox(bbox: BBox, *, width: int, height: int) -> BBox:
    x0, y0, x1, y1 = bbox
    return (
        max(0.0, min(float(width), float(x0))),
        max(0.0, min(float(height), float(y0))),
        max(0.0, min(float(width), float(x1))),
        max(0.0, min(float(height), float(y1))),
    )


def _entity_sort_key(item: Mapping[str, Any], layout: PixelRpgInteriorLayout) -> tuple[float, float, str]:
    layer_order = {"floor_fixture": 0, "fixture": 1, "prop": 2, "actor": 3}
    x, y, w, h = tuple(int(v) for v in item["tile_xywh"])
    if layout.projection == "isometric":
        return (float(layer_order.get(str(item["layer"]), 9)), float(x + y + w + h), str(item["entity_id"]))
    return (float(layer_order.get(str(item["layer"]), 9)), float(y), str(item["entity_id"]))


def _floor_tile_rgb(theme: Mapping[str, Any], floor_pattern: str, *, x: int, y: int) -> RGB:
    base = theme["floor_rgb"]
    alt = theme["floor_alt_rgb"]
    if floor_pattern == "checker":
        return alt if (int(x) + int(y)) % 2 else base
    if floor_pattern == "stone":
        return _shade(base, -8 if (int(x) * 3 + int(y) * 5) % 4 == 0 else 10)
    return _shade(base, -10 if int(y) % 2 else 8)


def _choose(rng: random.Random, values: Sequence[Any]) -> Any:
    if not values:
        raise ValueError("cannot choose from an empty sequence")
    return values[int(rng.randrange(len(values)))]


def _counts(values: Sequence[str] | Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _normalize_projection(projection: str) -> str:
    value = str(projection).strip().lower()
    aliases = {
        "topdown": "top_down",
        "top_down_pixel_rpg": "top_down",
        "isometric_pixel_rpg": "isometric",
        "iso": "isometric",
    }
    value = aliases.get(value, value)
    if value not in {"top_down", "isometric"}:
        raise ValueError("projection must be 'top_down' or 'isometric'")
    return value


def _rgba(color: Any, alpha: int = 255) -> tuple[int, int, int, int]:
    r, g, b = tuple(int(v) for v in color)
    return (r, g, b, int(alpha))


def _shade(color: Any, delta: int) -> RGB:
    return tuple(max(0, min(255, int(channel) + int(delta))) for channel in color)  # type: ignore[return-value]


__all__ = [
    "PixelRpgInteriorEntity",
    "PixelRpgInteriorLayout",
    "PixelRpgInteriorRegion",
    "PixelRpgInteriorScene",
    "REFERENCE_SOURCES",
    "RENDERER_ID",
    "SCENE_ID",
    "draw_pixel_rpg_general_store_debug_overlay",
    "render_pixel_rpg_general_store",
]
