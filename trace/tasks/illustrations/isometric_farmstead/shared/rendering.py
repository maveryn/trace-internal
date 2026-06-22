"""Renderer for the isometric farmstead scene package."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from trace.tasks.illustrations.shared.option_rendering import draw_label_badge

from .state import (
    BBox,
    IsoFarmsteadEntity,
    IsoFarmsteadScene,
    IsoFarmsteadTile,
    IsoFarmsteadTransition,
    IsoPoint,
    IsoPolygon,
)


SCENE_ID = "isometric_farmstead"
RENDERER_ID = "isometric_farmstead_v0"
RENDERER_STYLE = "isometric_pixel_farmstead"
SUPPORTED_LEVELS: tuple[int, ...] = (0, 1, 2, 3)
DEFAULT_CANDIDATE_LABELS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

RGB = tuple[int, int, int]
TileRect = tuple[int, int, int, int]


@dataclass(frozen=True)
class IsoLayout:
    """Resolved isometric grid geometry."""

    cols: int
    rows: int
    width: int
    height: int
    tile_w: float
    tile_h: float
    level_px: float
    origin_xy: IsoPoint


def _shade(color: RGB, delta: int) -> RGB:
    return tuple(max(0, min(255, int(channel) + int(delta))) for channel in color)


def _clamp(value: int, low: int, high: int) -> int:
    return max(int(low), min(int(high), int(value)))


def _point_bbox(points: Sequence[IsoPoint]) -> BBox:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_union(boxes: Sequence[Sequence[float]]) -> BBox:
    return (
        min(float(box[0]) for box in boxes),
        min(float(box[1]) for box in boxes),
        max(float(box[2]) for box in boxes),
        max(float(box[3]) for box in boxes),
    )


def _tile_id(col: int, row: int) -> str:
    return f"tile_{int(col):02d}_{int(row):02d}"


def _profile_grid(width: int, height: int) -> tuple[int, int]:
    if int(height) > int(width) * 1.15:
        return (9, 13)
    if int(width) > int(height) * 1.15:
        return (13, 11)
    return (11, 11)


def _inside(col: int, row: int, rect: TileRect) -> bool:
    x, y, w, h = rect
    return int(x) <= int(col) < int(x + w) and int(y) <= int(row) < int(y + h)


def _inset_rect(rect: TileRect, *, dx: int, dy: int, min_w: int, min_h: int) -> TileRect:
    x, y, w, h = rect
    next_w = max(int(min_w), int(w) - 2 * int(dx))
    next_h = max(int(min_h), int(h) - 2 * int(dy))
    return (int(x) + max(0, (int(w) - next_w) // 2), int(y) + max(0, (int(h) - next_h) // 2), next_w, next_h)


def _make_level_rects(rng: random.Random, *, cols: int, rows: int) -> dict[int, TileRect]:
    pad_x = max(1, int(cols) // 6)
    pad_y = max(1, int(rows) // 6)
    w1 = max(7, int(cols) - 2 * pad_x)
    h1 = max(7, int(rows) - 2 * pad_y)
    x1 = _clamp(pad_x + rng.choice((-1, 0, 1)), 1, int(cols) - w1 - 1)
    y1 = _clamp(pad_y + rng.choice((-1, 0, 1)), 1, int(rows) - h1 - 1)
    level1 = (x1, y1, w1, h1)
    level2 = _inset_rect(level1, dx=2, dy=2, min_w=4, min_h=4)
    level3 = _inset_rect(level2, dx=1, dy=1, min_w=3, min_h=3)
    return {1: level1, 2: level2, 3: level3}


def _make_level_grid(*, cols: int, rows: int, level_rects: Mapping[int, TileRect]) -> dict[tuple[int, int], int]:
    grid: dict[tuple[int, int], int] = {}
    for row in range(int(rows)):
        for col in range(int(cols)):
            level = 0
            for candidate_level in (1, 2, 3):
                if _inside(col, row, level_rects[int(candidate_level)]):
                    level = int(candidate_level)
            grid[(col, row)] = int(level)
    return grid


def _project(layout: IsoLayout, col: float, row: float, level: int) -> IsoPoint:
    ox, oy = layout.origin_xy
    return (
        float(ox + (float(col) - float(row)) * float(layout.tile_w) * 0.5),
        float(oy + (float(col) + float(row)) * float(layout.tile_h) * 0.5 - int(level) * float(layout.level_px)),
    )


def _tile_vertices(layout: IsoLayout, col: int, row: int, level: int) -> tuple[IsoPoint, IsoPoint, IsoPoint, IsoPoint]:
    cx, cy = _project(layout, int(col), int(row), int(level))
    return (
        (cx, cy - float(layout.tile_h) * 0.5),
        (cx + float(layout.tile_w) * 0.5, cy),
        (cx, cy + float(layout.tile_h) * 0.5),
        (cx - float(layout.tile_w) * 0.5, cy),
    )


def _layout_for_scene(*, width: int, height: int, cols: int, rows: int, level_grid: Mapping[tuple[int, int], int]) -> IsoLayout:
    tile_w_by_width = float(width) * 0.9 * 2.0 / float(max(1, int(cols) + int(rows)))
    tile_w_by_height = float(height) * 1.05 * 2.0 / float(max(1, int(cols) + int(rows)))
    tile_w = max(58.0, min(96.0, tile_w_by_width, tile_w_by_height))
    tile_h = tile_w * 0.5
    level_px = max(22.0, tile_h * 0.82)
    raw_layout = IsoLayout(cols=int(cols), rows=int(rows), width=int(width), height=int(height), tile_w=tile_w, tile_h=tile_h, level_px=level_px, origin_xy=(0.0, 0.0))
    boxes: list[BBox] = []
    for (col, row), level in level_grid.items():
        boxes.append(_point_bbox(_tile_vertices(raw_layout, int(col), int(row), int(level))))
    min_x, min_y, max_x, max_y = _bbox_union(boxes)
    min_y -= 120.0
    max_y += 24.0 + level_px
    origin_x = (float(width) - (max_x - min_x)) * 0.5 - min_x
    origin_y = (float(height) - (max_y - min_y)) * 0.5 - min_y
    return IsoLayout(cols=int(cols), rows=int(rows), width=int(width), height=int(height), tile_w=tile_w, tile_h=tile_h, level_px=level_px, origin_xy=(origin_x, origin_y))


def _terrain_for_tile(col: int, row: int, level: int, rng: random.Random) -> str:
    if int(level) == 0 and int(row) % 3 == 1 and int(col) % 2 == 0:
        return "crop"
    if int(level) == 1 and (int(row) + int(col)) % 6 == 0:
        return "soil"
    if int(level) == 2 and rng.random() < 0.08:
        return "flower"
    return "grass"


def _terrain_colors(terrain: str, level: int) -> tuple[RGB, RGB, RGB]:
    base_by_level = {
        0: (84, 151, 76),
        1: (100, 166, 82),
        2: (115, 179, 91),
        3: (129, 190, 97),
    }
    fill = base_by_level.get(int(level), base_by_level[0])
    if terrain == "crop":
        fill = (133, 92, 54)
    elif terrain == "soil":
        fill = (164, 116, 64)
    elif terrain == "flower":
        fill = (111, 172, 88)
    return fill, _shade(fill, -42), _shade(fill, 34)


def _draw_tile_top(draw: ImageDraw.ImageDraw, layout: IsoLayout, tile: IsoFarmsteadTile, rng: random.Random) -> None:
    points = [(int(round(x)), int(round(y))) for x, y in tile.polygon_xy]
    fill, dark, light = _terrain_colors(tile.terrain, tile.level)
    draw.polygon(points, fill=fill)
    top, right, bottom, left = tile.polygon_xy
    draw.line((top, right), fill=light, width=2)
    draw.line((right, bottom), fill=_shade(dark, 8), width=2)
    draw.line((bottom, left), fill=dark, width=2)
    draw.line((left, top), fill=_shade(dark, -4), width=2)
    cx, cy = tile.center_xy
    if tile.terrain == "crop":
        leaf = (63, 149, 62)
        for dx in (-0.17, 0.0, 0.17):
            px = int(round(cx + dx * layout.tile_w))
            draw.line((px, int(cy - 5), px, int(cy + 8)), fill=_shade(leaf, -35), width=2)
            draw.ellipse((px - 4, int(cy - 3), px + 3, int(cy + 5)), fill=leaf)
    elif tile.terrain == "soil":
        draw.line((int(cx - 10), int(cy + 2), int(cx + 10), int(cy - 2)), fill=(111, 72, 43), width=2)
    elif tile.terrain == "flower":
        blossom = rng.choice(((238, 87, 107), (239, 200, 73), (185, 105, 222)))
        for dx, dy in ((-7, -1), (3, 2), (9, -2)):
            draw.ellipse((int(cx + dx - 2), int(cy + dy - 2), int(cx + dx + 2), int(cy + dy + 2)), fill=blossom)


def _draw_level_faces(draw: ImageDraw.ImageDraw, layout: IsoLayout, level_grid: Mapping[tuple[int, int], int], *, open_edges: set[tuple[int, int, str]]) -> list[dict[str, Any]]:
    """Draw visible vertical faces wherever adjacent terrain levels drop."""

    records: list[dict[str, Any]] = []
    for row in range(layout.rows):
        for col in range(layout.cols):
            level = int(level_grid[(col, row)])
            if level <= 0:
                continue
            top, right, bottom, left = _tile_vertices(layout, col, row, level)
            for side, edge, neighbor in (
                ("east", (right, bottom), (col + 1, row)),
                ("south", (bottom, left), (col, row + 1)),
            ):
                if (col, row, side) in open_edges:
                    continue
                neighbor_level = int(level_grid.get(neighbor, 0))
                drop = max(0, level - neighbor_level) * float(layout.level_px)
                if drop <= 0:
                    continue
                p0, p1 = edge
                face = (p0, p1, (p1[0], p1[1] + drop), (p0[0], p0[1] + drop))
                fill = (118, 92, 60) if side == "east" else (138, 103, 63)
                draw.polygon([(int(round(x)), int(round(y))) for x, y in face], fill=fill)
                draw.line((p0, p1), fill=(202, 159, 91), width=2)
                for offset in range(8, int(drop), 8):
                    draw.line((int(p0[0]), int(p0[1] + offset), int(p1[0]), int(p1[1] + offset)), fill=_shade(fill, -18), width=1)
                records.append(
                    {
                        "tile_id": _tile_id(col, row),
                        "side": side,
                        "from_level": int(level),
                        "to_level": int(neighbor_level),
                        "drop_px": round(float(drop), 3),
                        "polygon": [[round(float(x), 3), round(float(y), 3)] for x, y in face],
                    }
                )
    return records


def _transition_specs(level_rects: Mapping[int, TileRect]) -> list[tuple[str, str, tuple[int, int], tuple[int, int], int, int, str]]:
    specs: list[tuple[str, str, tuple[int, int], tuple[int, int], int, int, str]] = []
    for level in (1, 2, 3):
        x, y, w, h = level_rects[int(level)]
        upper = (x + max(1, w // 2), y + h - 1)
        lower = (upper[0], upper[1] + 1)
        kind = "ramp" if level % 2 else "stair"
        specs.append((f"transition_{level - 1}_{level}", kind, lower, upper, level - 1, level, "south"))
    return specs


def _draw_transition(draw: ImageDraw.ImageDraw, layout: IsoLayout, spec: tuple[str, str, tuple[int, int], tuple[int, int], int, int, str]) -> IsoFarmsteadTransition:
    transition_id, kind, lower_xy, upper_xy, lower_level, upper_level, side = spec
    lower_top = _tile_vertices(layout, lower_xy[0], lower_xy[1], lower_level)[0]
    lower_right = _tile_vertices(layout, lower_xy[0], lower_xy[1], lower_level)[1]
    upper_left = _tile_vertices(layout, upper_xy[0], upper_xy[1], upper_level)[3]
    upper_bottom = _tile_vertices(layout, upper_xy[0], upper_xy[1], upper_level)[2]
    polygon: IsoPolygon = (upper_left, upper_bottom, lower_right, lower_top)
    points = [(int(round(x)), int(round(y))) for x, y in polygon]
    if kind == "ramp":
        draw.polygon(points, fill=(191, 145, 86), outline=(96, 70, 45))
        draw.line((upper_left, lower_top), fill=(100, 71, 45), width=2)
        draw.line((upper_bottom, lower_right), fill=(141, 100, 58), width=2)
        for t in (0.33, 0.66):
            lx = upper_left[0] + (lower_top[0] - upper_left[0]) * t
            ly = upper_left[1] + (lower_top[1] - upper_left[1]) * t
            rx = upper_bottom[0] + (lower_right[0] - upper_bottom[0]) * t
            ry = upper_bottom[1] + (lower_right[1] - upper_bottom[1]) * t
            draw.line((int(lx), int(ly), int(rx), int(ry)), fill=(214, 164, 97), width=2)
    else:
        draw.polygon(points, fill=(128, 118, 96), outline=(79, 72, 59))
        for index in range(5):
            t = index / 5.0
            lx = upper_left[0] + (lower_top[0] - upper_left[0]) * t
            ly = upper_left[1] + (lower_top[1] - upper_left[1]) * t
            rx = upper_bottom[0] + (lower_right[0] - upper_bottom[0]) * t
            ry = upper_bottom[1] + (lower_right[1] - upper_bottom[1]) * t
            draw.line((int(lx), int(ly), int(rx), int(ry)), fill=(220, 207, 170), width=2)
    return IsoFarmsteadTransition(
        transition_id=str(transition_id),
        transition_type=str(kind),
        lower_tile_id=_tile_id(lower_xy[0], lower_xy[1]),
        upper_tile_id=_tile_id(upper_xy[0], upper_xy[1]),
        lower_level=int(lower_level),
        upper_level=int(upper_level),
        polygon_xy=polygon,
        bbox_xyxy=_point_bbox(polygon),
        metadata={"open_edge_side": str(side)},
    )


def _add_entity(
    entities: list[IsoFarmsteadEntity],
    *,
    entity_id: str,
    public_name: str,
    object_type: str,
    tile_ids: Sequence[str],
    level: int,
    bbox: BBox,
    role: str,
    metadata: Mapping[str, Any],
) -> None:
    entities.append(
        IsoFarmsteadEntity(
            entity_id=str(entity_id),
            public_name=str(public_name),
            object_type=str(object_type),
            tile_ids=tuple(str(value) for value in tile_ids),
            level=int(level),
            bbox_xyxy=tuple(float(value) for value in bbox),
            point_xy=((float(bbox[0]) + float(bbox[2])) * 0.5, (float(bbox[1]) + float(bbox[3])) * 0.5),
            role=str(role),
            metadata=dict(metadata),
        )
    )


def _draw_context_entities(draw: ImageDraw.ImageDraw, layout: IsoLayout, level_grid: Mapping[tuple[int, int], int], level_rects: Mapping[int, TileRect]) -> tuple[list[IsoFarmsteadEntity], set[str]]:
    """Draw farm context objects and return occupied terrain tile ids."""

    entities: list[IsoFarmsteadEntity] = []
    occupied: set[str] = set()
    top_rect = level_rects[3]
    barn_col = top_rect[0] + max(0, top_rect[2] - 2)
    barn_row = top_rect[1]
    barn_tiles = [_tile_id(barn_col + dx, barn_row + dy) for dx in range(2) for dy in range(2)]
    occupied.update(barn_tiles)
    barn_base = [_tile_vertices(layout, barn_col + dx, barn_row + dy, 3)[2] for dx in range(2) for dy in range(2)]
    bx0, by0, bx1, by1 = _bbox_union([_point_bbox(barn_base)])
    barn_box = (bx0 - 28, by0 - 122, bx1 + 28, by1 + 6)
    draw.rectangle((barn_box[0] + 16, barn_box[1] + 42, barn_box[2] - 16, barn_box[3]), fill=(178, 67, 54), outline=(95, 48, 43), width=2)
    roof = [(barn_box[0] + 8, barn_box[1] + 48), ((barn_box[0] + barn_box[2]) * 0.5, barn_box[1] + 4), (barn_box[2] - 8, barn_box[1] + 48)]
    draw.polygon([(int(x), int(y)) for x, y in roof], fill=(115, 47, 45), outline=(73, 39, 42))
    draw.rectangle((barn_box[0] + 45, barn_box[3] - 42, barn_box[2] - 45, barn_box[3]), fill=(101, 57, 39), outline=(66, 39, 31), width=2)
    _add_entity(entities, entity_id="barn_00", public_name="barn", object_type="barn", tile_ids=barn_tiles, level=3, bbox=barn_box, role="context", metadata={"base_level": 3})

    tree_positions = [(1, 1), (layout.cols - 2, 1), (1, layout.rows - 2), (layout.cols - 2, layout.rows - 2)]
    for index, (col, row) in enumerate(tree_positions):
        level = int(level_grid[(col, row)])
        center = _project(layout, col, row, level)
        box = (center[0] - 22, center[1] - 66, center[0] + 22, center[1] + 8)
        occupied.add(_tile_id(col, row))
        draw.rectangle((center[0] - 5, center[1] - 25, center[0] + 5, center[1] + 8), fill=(108, 70, 42))
        draw.ellipse((box[0], box[1], box[2], box[1] + 48), fill=(47, 134, 75), outline=(32, 89, 54), width=2)
        _add_entity(entities, entity_id=f"tree_{index:02d}", public_name="tree", object_type="tree", tile_ids=[_tile_id(col, row)], level=level, bbox=box, role="context", metadata={"base_level": level})
    return entities, occupied


def _build_tiles(layout: IsoLayout, level_grid: Mapping[tuple[int, int], int], rng: random.Random) -> tuple[IsoFarmsteadTile, ...]:
    tiles: list[IsoFarmsteadTile] = []
    for row in range(layout.rows):
        for col in range(layout.cols):
            level = int(level_grid[(col, row)])
            terrain = _terrain_for_tile(col, row, level, rng)
            polygon = _tile_vertices(layout, col, row, level)
            center = _project(layout, col, row, level)
            tiles.append(
                IsoFarmsteadTile(
                    tile_id=_tile_id(col, row),
                    col=int(col),
                    row=int(row),
                    level=int(level),
                    terrain=str(terrain),
                    polygon_xy=polygon,
                    bbox_xyxy=_point_bbox(polygon),
                    center_xy=center,
                    metadata={"candidate_allowed": True},
                )
            )
    return tuple(sorted(tiles, key=lambda item: (item.row + item.col, item.col)))


def render_isometric_farmstead_scene(
    seed: int,
    *,
    width: int,
    height: int,
    canvas_profile: str = "",
    canvas_profile_probabilities: Mapping[str, float] | None = None,
    candidate_labels_by_tile_id: Mapping[str, str] | None = None,
    label_font_family: str | None = None,
) -> IsoFarmsteadScene:
    """Render a deterministic isometric farmstead with four terrain levels."""

    rng = random.Random(int(seed))
    cols, rows = _profile_grid(int(width), int(height))
    level_rects = _make_level_rects(rng, cols=cols, rows=rows)
    level_grid = _make_level_grid(cols=cols, rows=rows, level_rects=level_rects)
    layout = _layout_for_scene(width=int(width), height=int(height), cols=cols, rows=rows, level_grid=level_grid)
    tile_rng = random.Random(int(seed) + 17011)
    tiles = _build_tiles(layout, level_grid, tile_rng)
    image = Image.new("RGB", (int(width), int(height)), (207, 220, 190))
    draw = ImageDraw.Draw(image, "RGBA")

    for tile in tiles:
        _draw_tile_top(draw, layout, tile, tile_rng)
    transition_specs = _transition_specs(level_rects)
    open_edges = {(spec[3][0], spec[3][1], spec[6]) for spec in transition_specs}
    face_records = _draw_level_faces(draw, layout, level_grid, open_edges=open_edges)
    transitions = tuple(_draw_transition(draw, layout, spec) for spec in transition_specs)
    entities, occupied_tile_ids = _draw_context_entities(draw, layout, level_grid, level_rects)

    labels = dict(candidate_labels_by_tile_id or {})
    label_bboxes: dict[str, BBox] = {}
    for tile_id, label in sorted(labels.items()):
        tile = next((candidate for candidate in tiles if candidate.tile_id == str(tile_id)), None)
        if tile is None:
            continue
        cx, cy = tile.center_xy
        box = (cx - 18.0, cy - 15.0, cx + 18.0, cy + 13.0)
        draw_label_badge(
            draw,
            str(label),
            box,
            font_family=label_font_family,
            fill=(255, 255, 244),
            outline=(39, 46, 55),
            text_fill=(18, 24, 31),
            radius=5,
            width=2,
        )
        label_bboxes[str(tile_id)] = tuple(float(value) for value in box)

    transition_tile_ids = {transition.lower_tile_id for transition in transitions} | {transition.upper_tile_id for transition in transitions}
    trace = {
        "renderer_id": RENDERER_ID,
        "renderer_style": RENDERER_STYLE,
        "theme_id": "farm_terraces",
        "seed": int(seed),
        "canvas_profile": str(canvas_profile),
        "canvas_profile_probabilities": dict(canvas_profile_probabilities or {}),
        "canvas_size_px": [int(width), int(height)],
        "grid_cols": int(cols),
        "grid_rows": int(rows),
        "levels": list(SUPPORTED_LEVELS),
        "level_tile_counts": {
            str(level): sum(1 for value in level_grid.values() if int(value) == int(level))
            for level in SUPPORTED_LEVELS
        },
        "projection": {
            "type": "2:1_isometric",
            "tile_size_px": [round(float(layout.tile_w), 3), round(float(layout.tile_h), 3)],
            "level_step_px": round(float(layout.level_px), 3),
            "origin_xy": [round(float(value), 3) for value in layout.origin_xy],
        },
        "level_rects": {str(level): [int(value) for value in rect] for level, rect in sorted(level_rects.items())},
        "transition_tile_ids": sorted(transition_tile_ids),
        "occupied_tile_ids": sorted(occupied_tile_ids),
        "eligible_tile_ids": [
            str(tile.tile_id)
            for tile in tiles
            if str(tile.tile_id) not in transition_tile_ids and str(tile.tile_id) not in occupied_tile_ids
        ],
        "tile_count": len(tiles),
        "entity_count": len(entities),
        "retaining_wall_faces": face_records,
        "label_bboxes_by_tile_id": {key: [round(float(value), 3) for value in bbox] for key, bbox in label_bboxes.items()},
    }
    return IsoFarmsteadScene(
        image=image,
        tiles=tiles,
        entities=tuple(sorted(entities, key=lambda item: item.entity_id)),
        transitions=tuple(sorted(transitions, key=lambda item: item.transition_id)),
        label_bboxes_by_tile_id=label_bboxes,
        trace=trace,
    )


__all__ = [
    "DEFAULT_CANDIDATE_LABELS",
    "RENDERER_ID",
    "RENDERER_STYLE",
    "SCENE_ID",
    "SUPPORTED_LEVELS",
    "render_isometric_farmstead_scene",
]
