"""Scene-local top-down RPG house renderer."""

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
from trace.tasks.illustrations.shared.option_rendering import draw_label_badge
from trace.tasks.illustrations.shared.pixel_world_objects import CANONICAL_TILE_PX

from .state import BBox, RpgHouseDoor, RpgHouseEntity, RpgHouseRoom, RpgHouseScene, TileBox


SCENE_ID = "rpg_house"
RENDERER_ID = "rpg_house_top_down_v0"
DEFAULT_TILE_PX = 48
DEFAULT_CANVAS_WIDTH = 960
DEFAULT_CANVAS_HEIGHT = 720
ROOM_IDS: tuple[str, ...] = ("bedroom", "kitchen", "storage", "study", "parlor")
HALL_ROOM_ID = "hall"
PASSABLE_DOOR_STATES: frozenset[str] = frozenset({"open"})

ROOM_PUBLIC_NAMES: Mapping[str, str] = {
    "bedroom": "bedroom",
    "kitchen": "kitchen",
    "storage": "storage room",
    "study": "study",
    "parlor": "parlor",
    "hall": "hallway",
}

RGB = tuple[int, int, int]

THEMES: Mapping[str, Mapping[str, Any]] = {
    "warm_cottage": {
        "background_rgb": (57, 47, 39),
        "wall_rgb": (111, 72, 45),
        "wall_dark_rgb": (57, 39, 31),
        "door_rgb": (124, 73, 41),
        "floor_rgbs": {
            "bedroom": (171, 128, 82),
            "kitchen": (154, 121, 84),
            "storage": (135, 106, 76),
            "study": (146, 112, 73),
            "parlor": (174, 134, 86),
            "hall": (158, 112, 67),
        },
        "wood_rgb": (132, 78, 42),
        "rug_rgb": (150, 67, 82),
    },
    "blue_inn": {
        "background_rgb": (45, 51, 61),
        "wall_rgb": (96, 105, 123),
        "wall_dark_rgb": (46, 52, 64),
        "door_rgb": (111, 73, 48),
        "floor_rgbs": {
            "bedroom": (146, 115, 78),
            "kitchen": (126, 120, 108),
            "storage": (119, 101, 78),
            "study": (130, 101, 73),
            "parlor": (154, 118, 76),
            "hall": (132, 103, 69),
        },
        "wood_rgb": (118, 75, 45),
        "rug_rgb": (74, 126, 153),
    },
    "stone_house": {
        "background_rgb": (49, 48, 45),
        "wall_rgb": (117, 111, 101),
        "wall_dark_rgb": (55, 54, 50),
        "door_rgb": (115, 75, 45),
        "floor_rgbs": {
            "bedroom": (133, 119, 95),
            "kitchen": (119, 117, 105),
            "storage": (107, 103, 93),
            "study": (124, 106, 82),
            "parlor": (138, 120, 92),
            "hall": (122, 111, 93),
        },
        "wood_rgb": (122, 75, 44),
        "rug_rgb": (126, 76, 112),
    },
}


@dataclass(frozen=True)
class RpgHouseLayout:
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
class _RoomSpec:
    room_id: str
    public_name: str
    tile_xywh: TileBox
    floor_rgb: RGB


@dataclass(frozen=True)
class _DoorSpec:
    door_id: str
    room_a_id: str
    room_b_id: str
    state: str
    orientation: str
    tile_xy: tuple[int, int]


@dataclass(frozen=True)
class _EntitySpec:
    entity_id: str
    object_type: str
    public_name: str
    room_id: str
    tile_xywh: TileBox
    layer: str
    visual: Mapping[str, Any] | None = None


def render_rpg_house_scene(
    seed: int,
    *,
    width: int = DEFAULT_CANVAS_WIDTH,
    height: int = DEFAULT_CANVAS_HEIGHT,
    tile_px: int = DEFAULT_TILE_PX,
    start_room_id: str | None = None,
    room_labels: Mapping[str, str] | None = None,
    door_states: Mapping[str, str] | None = None,
    label_font_family: str | None = None,
    label_font_trace: Mapping[str, Any] | None = None,
    render_metadata: Mapping[str, Any] | None = None,
) -> RpgHouseScene:
    """Render one top-down RPG house layout."""

    rng = random.Random(int(seed))
    layout = _sample_layout(width=int(width), height=int(height), tile_px=int(tile_px))
    theme_id = str(_choose(rng, tuple(THEMES)))
    theme = THEMES[theme_id]
    room_specs, door_specs = _make_layout_specs(layout, theme=theme, door_states=door_states or {})
    entity_specs = _make_entity_specs(layout, theme_id=theme_id)
    canvas, draw = _render_base(layout, room_specs=room_specs, door_specs=door_specs, theme=theme)
    entities = _render_entities(draw, entity_specs=entity_specs, layout=layout, theme=theme, theme_id=theme_id)

    scaled = canvas.resize((layout.display_grid_width_px, layout.display_grid_height_px), Image.Resampling.NEAREST)
    final = Image.new("RGB", (int(width), int(height)), _shade(theme["background_rgb"], -8))
    final.paste(scaled.convert("RGB"), layout.display_offset_xy)
    final_draw = ImageDraw.Draw(final)
    room_labels = {str(key): str(value) for key, value in dict(room_labels or {}).items()}
    rooms = tuple(
        RpgHouseRoom(
            room_id=spec.room_id,
            public_name=spec.public_name,
            label=room_labels.get(spec.room_id),
            tile_xywh=spec.tile_xywh,
            bbox_xyxy=_tile_bbox(layout, spec.tile_xywh),
            metadata={"floor_rgb": list(spec.floor_rgb)},
        )
        for spec in room_specs
    )
    doors = tuple(_make_door(spec, layout) for spec in door_specs)
    _draw_final_room_marks(
        final_draw,
        rooms=rooms,
        start_room_id=start_room_id,
        label_font_family=label_font_family,
    )
    trace = {
        "renderer_id": RENDERER_ID,
        "renderer_style": RENDERER_STYLE_TOP_DOWN_PIXEL_RPG,
        "theme_id": theme_id,
        "width": int(width),
        "height": int(height),
        "grid_cols": int(layout.cols),
        "grid_rows": int(layout.rows),
        "tile_px": int(layout.tile_px),
        "room_ids": [room.room_id for room in rooms],
        "candidate_room_labels": dict(room_labels),
        "start_room_id": None if start_room_id is None else str(start_room_id),
        "doors": [door.as_dict() for door in doors],
        "room_graph": room_graph(doors),
        "label_font": dict(label_font_trace or {}),
        **dict(render_metadata or {}),
    }
    return RpgHouseScene(
        image=final,
        rooms=rooms,
        doors=doors,
        entities=tuple(sorted(entities, key=lambda entity: (entity.layer, entity.room_id, entity.entity_id))),
        trace=trace,
    )


def draw_rpg_house_debug_overlay(scene: RpgHouseScene) -> Image.Image:
    """Return an overlay image with room, door, and fixture bboxes."""

    image = scene.image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for room in scene.rooms:
        draw.rectangle(room.bbox_xyxy, outline=(42, 111, 210, 220), width=3)
    for door in scene.doors:
        color = (38, 152, 91, 235) if door.state == "open" else (214, 67, 59, 235)
        draw.rectangle(door.bbox_xyxy, outline=color, width=3)
    for entity in scene.entities:
        draw.rectangle(entity.bbox_xyxy, outline=(239, 173, 42, 220), width=2)
    return Image.alpha_composite(image, overlay).convert("RGB")


def room_graph(doors: Sequence[RpgHouseDoor]) -> dict[str, list[dict[str, str]]]:
    """Return an adjacency map with door states."""

    graph: dict[str, list[dict[str, str]]] = {}
    for door in doors:
        graph.setdefault(str(door.room_a_id), []).append(
            {"room_id": str(door.room_b_id), "door_id": str(door.door_id), "state": str(door.state)}
        )
        graph.setdefault(str(door.room_b_id), []).append(
            {"room_id": str(door.room_a_id), "door_id": str(door.door_id), "state": str(door.state)}
        )
    return {key: sorted(values, key=lambda item: (item["room_id"], item["door_id"])) for key, values in graph.items()}


def reachable_room_ids(doors: Sequence[RpgHouseDoor], *, start_room_id: str) -> tuple[str, ...]:
    """Return rooms reachable through open doors from ``start_room_id``."""

    graph = room_graph(doors)
    seen = {str(start_room_id)}
    queue = [str(start_room_id)]
    while queue:
        room_id = queue.pop(0)
        for edge in graph.get(room_id, []):
            if str(edge["state"]) not in PASSABLE_DOOR_STATES:
                continue
            other = str(edge["room_id"])
            if other in seen:
                continue
            seen.add(other)
            queue.append(other)
    return tuple(sorted(seen))


def _sample_layout(*, width: int, height: int, tile_px: int) -> RpgHouseLayout:
    resolved_tile_px = max(40, min(56, int(tile_px)))
    cols = max(14, int(width) // resolved_tile_px)
    rows = max(12, int(height) // resolved_tile_px)
    grid_w = int(cols) * resolved_tile_px
    grid_h = int(rows) * resolved_tile_px
    if grid_w > int(width) or grid_h > int(height):
        raise ValueError(f"RPG house grid {cols}x{rows} does not fit in {width}x{height}")
    return RpgHouseLayout(
        cols=int(cols),
        rows=int(rows),
        tile_px=int(resolved_tile_px),
        width_px=int(width),
        height_px=int(height),
        display_offset_xy=((int(width) - grid_w) // 2, (int(height) - grid_h) // 2),
    )


def _make_layout_specs(
    layout: RpgHouseLayout,
    *,
    theme: Mapping[str, Any],
    door_states: Mapping[str, str],
) -> tuple[list[_RoomSpec], list[_DoorSpec]]:
    """Build the fixed room graph around a central hallway."""

    usable_w = int(layout.cols) - 2
    usable_h = int(layout.rows) - 2
    hall_w = max(3, min(5, usable_w // 4))
    left_w = max(4, (usable_w - hall_w) // 2)
    right_w = max(4, usable_w - hall_w - left_w)
    top_h = max(3, usable_h // 3)
    mid_h = max(3, usable_h // 3)
    bottom_h = max(3, usable_h - top_h - mid_h)
    x_left = 1
    x_hall = x_left + left_w
    x_right = x_hall + hall_w
    y_top = 1
    y_mid = y_top + top_h
    y_bottom = y_mid + mid_h
    floors = theme["floor_rgbs"]
    rooms = [
        _RoomSpec("bedroom", ROOM_PUBLIC_NAMES["bedroom"], (x_left, y_top, left_w, top_h), floors["bedroom"]),
        _RoomSpec("kitchen", ROOM_PUBLIC_NAMES["kitchen"], (x_left, y_mid, left_w, mid_h), floors["kitchen"]),
        _RoomSpec("storage", ROOM_PUBLIC_NAMES["storage"], (x_left, y_bottom, left_w, bottom_h), floors["storage"]),
        _RoomSpec("hall", ROOM_PUBLIC_NAMES["hall"], (x_hall, y_top, hall_w, usable_h), floors["hall"]),
        _RoomSpec("study", ROOM_PUBLIC_NAMES["study"], (x_right, y_top, right_w, top_h), floors["study"]),
        _RoomSpec("parlor", ROOM_PUBLIC_NAMES["parlor"], (x_right, y_mid, right_w, mid_h + bottom_h), floors["parlor"]),
    ]
    base_doors = [
        ("bedroom_hall", "bedroom", "hall", "vertical", (x_hall, y_top + top_h // 2)),
        ("kitchen_hall", "kitchen", "hall", "vertical", (x_hall, y_mid + mid_h // 2)),
        ("storage_hall", "storage", "hall", "vertical", (x_hall, y_bottom + bottom_h // 2)),
        ("study_hall", "study", "hall", "vertical", (x_right, y_top + top_h // 2)),
        ("parlor_hall", "parlor", "hall", "vertical", (x_right, y_mid + (mid_h + bottom_h) // 2)),
    ]
    doors = [
        _DoorSpec(
            door_id=door_id,
            room_a_id=room_a,
            room_b_id=room_b,
            state=str(door_states.get(door_id, "closed")),
            orientation=orientation,
            tile_xy=tile_xy,
        )
        for door_id, room_a, room_b, orientation, tile_xy in base_doors
    ]
    return rooms, doors


def _make_entity_specs(layout: RpgHouseLayout, *, theme_id: str) -> list[_EntitySpec]:
    room_specs, _doors = _make_layout_specs(layout, theme=THEMES[theme_id], door_states={})
    by_id = {room.room_id: room.tile_xywh for room in room_specs}
    wood = THEMES[theme_id]["wood_rgb"]
    rug = THEMES[theme_id]["rug_rgb"]
    entities: list[_EntitySpec] = []

    def add(entity_id: str, object_type: str, public_name: str, room_id: str, box: TileBox, **visual: Any) -> None:
        entities.append(_EntitySpec(entity_id, object_type, public_name, room_id, box, "fixture", visual))

    bx, by, bw, bh = by_id["bedroom"]
    add("bed_00", "bed", "bed", "bedroom", (bx + 1, by + 1, max(3, bw - 2), min(2, max(1, bh - 2))), bed_size="single", wood_rgb=wood, blanket_rgb=(96, 132, 174))
    add("rug_bedroom", "rug", "rug", "bedroom", (bx + 1, max(by + 2, by + bh - 2), max(2, bw - 2), 1), cloth_rgb=rug)
    kx, ky, kw, kh = by_id["kitchen"]
    add("counter_00", "counter", "counter", "kitchen", (kx + 1, ky + 1, max(3, kw - 2), 1), wood_rgb=wood, top_rgb=_shade(wood, 46))
    add("fireplace_00", "fireplace", "hearth", "kitchen", (kx + 1, max(ky + 2, ky + kh - 2), max(2, kw - 2), 1), fire_state="lit")
    sx, sy, sw, sh = by_id["storage"]
    add("shelf_storage", "shelf", "shelf", "storage", (sx + 1, sy + 1, max(3, sw - 2), 1), wood_rgb=wood, goods_type="mixed")
    add("chest_00", "chest", "chest", "storage", (sx + 1, max(sy + 2, sy + sh - 2), max(2, min(3, sw - 2)), 1), wood_rgb=wood)
    tx, ty, tw, th = by_id["study"]
    add("shelf_study", "shelf", "shelf", "study", (tx + 1, ty + 1, max(3, tw - 2), 1), wood_rgb=wood, goods_type="books")
    add("table_study", "table", "table", "study", (tx + 1, max(ty + 2, ty + th - 3), max(2, tw - 2), 2), table_shape="long", wood_rgb=wood)
    px, py, pw, ph = by_id["parlor"]
    add("rug_parlor", "rug", "rug", "parlor", (px + 1, py + 1, max(3, pw - 2), max(2, ph - 2)), cloth_rgb=rug)
    add("table_parlor", "table", "table", "parlor", (px + 1, py + max(1, ph // 2), max(3, pw - 2), 2), table_shape="long", wood_rgb=wood)
    hx, hy, hw, hh = by_id["hall"]
    add("stairs_00", "stairs", "stairs", "hall", (hx + 1, hy + hh - 3, max(2, hw - 2), 2), stone_rgb=(122, 119, 109), stair_direction="down")
    return entities


def _render_base(
    layout: RpgHouseLayout,
    *,
    room_specs: Sequence[_RoomSpec],
    door_specs: Sequence[_DoorSpec],
    theme: Mapping[str, Any],
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (layout.canonical_width_px, layout.canonical_height_px), _rgba(theme["background_rgb"]))
    draw = ImageDraw.Draw(image)
    wall = theme["wall_rgb"]
    wall_dark = theme["wall_dark_rgb"]
    for room in room_specs:
        x0, y0, x1, y1 = _canonical_rect(room.tile_xywh)
        draw.rectangle((x0, y0, x1, y1), fill=_rgba(room.floor_rgb), outline=_rgba(wall_dark), width=2)
        draw.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), outline=_rgba(wall), width=1)
        _draw_floor_lines(draw, room.tile_xywh, room.floor_rgb)
    for door in door_specs:
        _draw_door(draw, door, theme=theme)
    return image, draw


def _draw_floor_lines(draw: ImageDraw.ImageDraw, tile_xywh: TileBox, floor_rgb: RGB) -> None:
    x, y, w, h = tile_xywh
    for yy in range(int(y), int(y) + int(h)):
        py = yy * CANONICAL_TILE_PX + CANONICAL_TILE_PX // 2
        draw.line(
            (int(x) * CANONICAL_TILE_PX + 2, py, (int(x) + int(w)) * CANONICAL_TILE_PX - 3, py),
            fill=_rgba(_shade(floor_rgb, -20), 105),
        )


def _draw_door(draw: ImageDraw.ImageDraw, door: _DoorSpec, *, theme: Mapping[str, Any]) -> None:
    x, y = door.tile_xy
    px = int(x) * CANONICAL_TILE_PX
    py = int(y) * CANONICAL_TILE_PX
    if door.orientation != "vertical":
        raise ValueError(f"unsupported RPG house door orientation: {door.orientation}")
    gap = (px - 2, py + 2, px + 2, py + CANONICAL_TILE_PX - 3)
    if door.state == "open":
        draw.rectangle(gap, fill=_rgba(_shade(theme["floor_rgbs"]["hall"], 8)))
        draw.line((px - 2, py + 2, px + 2, py + 2), fill=_rgba(theme["wall_dark_rgb"]))
        draw.line((px - 2, py + CANONICAL_TILE_PX - 3, px + 2, py + CANONICAL_TILE_PX - 3), fill=_rgba(theme["wall_dark_rgb"]))
        return
    draw.rectangle((px - 2, py + 1, px + 2, py + CANONICAL_TILE_PX - 2), fill=_rgba(theme["door_rgb"]), outline=_rgba(_shade(theme["door_rgb"], -42)))
    draw.point((px + 1, py + CANONICAL_TILE_PX // 2), fill=_rgba((230, 188, 82)))


def _render_entities(
    draw: ImageDraw.ImageDraw,
    *,
    entity_specs: Sequence[_EntitySpec],
    layout: RpgHouseLayout,
    theme: Mapping[str, Any],
    theme_id: str,
) -> list[RpgHouseEntity]:
    """Draw large context fixtures and serialize their final bboxes."""

    entities: list[RpgHouseEntity] = []
    for spec in entity_specs:
        bbox = _tile_bbox(layout, spec.tile_xywh)
        visual = {"theme_id": theme_id, "renderer_style": RENDERER_STYLE_TOP_DOWN_PIXEL_RPG}
        visual.update(dict(spec.visual or {}))
        rendered = render_illustration_object(
            IllustrationObjectSpec(
                object_id=spec.entity_id,
                object_type=spec.object_type,
                public_name=spec.public_name,
                bbox_xyxy=bbox,
                tile_xywh=spec.tile_xywh,
                renderer_id=RENDERER_ID,
                renderer_variant_id=f"top_down:{theme_id}",
                semantic_attributes={"room_id": spec.room_id, "layout_context": True},
                visual_attributes=visual,
                role="context",
                source_entity_type="rpg_house_entity",
            ),
            RenderContext(renderer_style=RENDERER_STYLE_TOP_DOWN_PIXEL_RPG, draw=draw),
        )
        point = ((bbox[0] + bbox[2]) * 0.5, (bbox[1] + bbox[3]) * 0.5)
        entities.append(
            RpgHouseEntity(
                entity_id=spec.entity_id,
                public_name=spec.public_name,
                object_type=spec.object_type,
                room_id=spec.room_id,
                tile_xywh=spec.tile_xywh,
                bbox_xyxy=bbox,
                point_xy=point,
                layer=spec.layer,
                metadata={"visual_attributes": visual, "object_record": rendered.object_record},
            )
        )
    return entities


def _draw_final_room_marks(
    draw: ImageDraw.ImageDraw,
    *,
    rooms: Sequence[RpgHouseRoom],
    start_room_id: str | None,
    label_font_family: str | None,
) -> None:
    for room in rooms:
        if str(room.room_id) == str(start_room_id):
            x0, y0, x1, y1 = [float(value) for value in room.bbox_xyxy]
            inset = 5
            draw.rectangle((x0 + inset, y0 + inset, x1 - inset, y1 - inset), outline=(218, 45, 48), width=6)
    for room in rooms:
        if not room.label:
            continue
        x0, y0, _x1, _y1 = [float(value) for value in room.bbox_xyxy]
        draw_label_badge(
            draw,
            str(room.label),
            (x0 + 12, y0 + 12, x0 + 48, y0 + 48),
            font_family=label_font_family,
            fill=(255, 255, 245),
            outline=(32, 40, 54),
            text_fill=(24, 31, 43),
        )


def _make_door(spec: _DoorSpec, layout: RpgHouseLayout) -> RpgHouseDoor:
    return RpgHouseDoor(
        door_id=spec.door_id,
        room_a_id=spec.room_a_id,
        room_b_id=spec.room_b_id,
        state=spec.state,
        orientation=spec.orientation,
        tile_xy=spec.tile_xy,
        bbox_xyxy=_door_bbox(layout, spec),
        metadata={"passable": spec.state in PASSABLE_DOOR_STATES},
    )


def _tile_bbox(layout: RpgHouseLayout, tile_xywh: TileBox) -> BBox:
    x, y, w, h = tile_xywh
    ox, oy = layout.display_offset_xy
    return (
        float(ox + int(x) * int(layout.tile_px)),
        float(oy + int(y) * int(layout.tile_px)),
        float(ox + (int(x) + int(w)) * int(layout.tile_px)),
        float(oy + (int(y) + int(h)) * int(layout.tile_px)),
    )


def _door_bbox(layout: RpgHouseLayout, spec: _DoorSpec) -> BBox:
    x, y = spec.tile_xy
    ox, oy = layout.display_offset_xy
    px = ox + int(x) * int(layout.tile_px)
    py = oy + int(y) * int(layout.tile_px)
    if spec.orientation == "vertical":
        return (
            float(px - max(3, layout.tile_px // 12)),
            float(py + max(3, layout.tile_px // 12)),
            float(px + max(3, layout.tile_px // 12)),
            float(py + layout.tile_px - max(3, layout.tile_px // 12)),
        )
    raise ValueError(f"unsupported RPG house door orientation: {spec.orientation}")


def _canonical_rect(tile_xywh: TileBox) -> tuple[int, int, int, int]:
    x, y, w, h = tile_xywh
    return (
        int(x) * CANONICAL_TILE_PX,
        int(y) * CANONICAL_TILE_PX,
        (int(x) + int(w)) * CANONICAL_TILE_PX - 1,
        (int(y) + int(h)) * CANONICAL_TILE_PX - 1,
    )


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
    "HALL_ROOM_ID",
    "PASSABLE_DOOR_STATES",
    "RENDERER_ID",
    "ROOM_IDS",
    "ROOM_PUBLIC_NAMES",
    "SCENE_ID",
    "draw_rpg_house_debug_overlay",
    "reachable_room_ids",
    "render_rpg_house_scene",
    "room_graph",
]
