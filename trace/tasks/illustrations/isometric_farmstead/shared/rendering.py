"""Renderer for the isometric farmstead scene package."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from trace.tasks.illustrations.shared.pixel_world_objects import draw_pixel_animal, draw_pixel_tree
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
ACTIVE_MAX_LEVEL_SUPPORT: tuple[int, ...] = (1, 2)
DEFAULT_CANDIDATE_LABELS: tuple[str, ...] = ("A", "B", "C", "D")
LAYOUT_FAMILIES: tuple[str, ...] = (
    "concentric_terrace",
    "side_plateau",
    "corner_plateau",
    "split_field",
)
FARM_PATCH_TERRAINS: tuple[str, ...] = ("crop", "soil", "flower", "pasture")
TREE_STYLES: tuple[str, ...] = ("oak", "pine", "maple", "fruit_tree")
ANIMAL_TYPES: tuple[str, ...] = ("chicken", "pig", "sheep", "cow")

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
        return (11, 15)
    if int(width) > int(height) * 1.15:
        return (15, 12)
    return (13, 13)


def _inside(col: int, row: int, rect: TileRect) -> bool:
    x, y, w, h = rect
    return int(x) <= int(col) < int(x + w) and int(y) <= int(row) < int(y + h)


def _inset_rect(rect: TileRect, *, dx: int, dy: int, min_w: int, min_h: int) -> TileRect:
    x, y, w, h = rect
    next_w = max(int(min_w), int(w) - 2 * int(dx))
    next_h = max(int(min_h), int(h) - 2 * int(dy))
    return (int(x) + max(0, (int(w) - next_w) // 2), int(y) + max(0, (int(h) - next_h) // 2), next_w, next_h)


def _rect_cells(rect: TileRect) -> list[tuple[int, int]]:
    x, y, w, h = rect
    return [(int(col), int(row)) for row in range(int(y), int(y + h)) for col in range(int(x), int(x + w))]


def _blank_level_grid(*, cols: int, rows: int) -> dict[tuple[int, int], int]:
    return {(int(col), int(row)): 0 for row in range(int(rows)) for col in range(int(cols))}


def _apply_rect(grid: dict[tuple[int, int], int], rect: TileRect, *, level: int, cols: int, rows: int) -> None:
    for col, row in _rect_cells(rect):
        if 0 <= int(col) < int(cols) and 0 <= int(row) < int(rows):
            grid[(int(col), int(row))] = max(int(grid.get((int(col), int(row)), 0)), int(level))


def _sample_active_max_level(rng: random.Random) -> int:
    return int(rng.choice((1, 2, 2)))


def _sample_layout_family(rng: random.Random) -> str:
    return str(rng.choice(LAYOUT_FAMILIES))


def _make_concentric_rects(rng: random.Random, *, cols: int, rows: int, active_max_level: int) -> dict[int, list[TileRect]]:
    pad_x = max(1, int(cols) // 6)
    pad_y = max(1, int(rows) // 6)
    w1 = max(8, int(cols) - 2 * pad_x)
    h1 = max(8, int(rows) - 2 * pad_y)
    x1 = _clamp(pad_x + rng.choice((-1, 0, 1)), 1, int(cols) - w1 - 1)
    y1 = _clamp(pad_y + rng.choice((-1, 0, 1)), 1, int(rows) - h1 - 1)
    rects: dict[int, list[TileRect]] = {1: [(x1, y1, w1, h1)]}
    current = rects[1][0]
    for level in range(2, int(active_max_level) + 1):
        current = _inset_rect(current, dx=rng.choice((1, 2)), dy=rng.choice((1, 2)), min_w=3, min_h=3)
        rects[int(level)] = [current]
    return rects


def _make_side_rects(rng: random.Random, *, cols: int, rows: int, active_max_level: int) -> dict[int, list[TileRect]]:
    side = rng.choice(("north", "south", "west", "east"))
    if side in {"west", "east"}:
        w = rng.randint(max(5, cols // 3), max(6, cols // 2))
        h = rng.randint(max(7, rows // 2), max(8, rows - 2))
        x = 1 if side == "west" else max(1, cols - w - 1)
        y = rng.randint(1, max(1, rows - h - 1))
    else:
        w = rng.randint(max(8, cols // 2), max(9, cols - 2))
        h = rng.randint(max(5, rows // 3), max(6, rows // 2))
        x = rng.randint(1, max(1, cols - w - 1))
        y = 1 if side == "north" else max(1, rows - h - 1)
    rects: dict[int, list[TileRect]] = {1: [(x, y, w, h)]}
    current = rects[1][0]
    for level in range(2, int(active_max_level) + 1):
        current = _inset_rect(current, dx=1, dy=1, min_w=3, min_h=3)
        cx, cy, cw, ch = current
        if side == "west":
            current = (max(1, cx - 1), cy, cw, ch)
        elif side == "east":
            current = (min(cols - cw - 1, cx + 1), cy, cw, ch)
        elif side == "north":
            current = (cx, max(1, cy - 1), cw, ch)
        else:
            current = (cx, min(rows - ch - 1, cy + 1), cw, ch)
        rects[int(level)] = [current]
    return rects


def _make_corner_rects(rng: random.Random, *, cols: int, rows: int, active_max_level: int) -> dict[int, list[TileRect]]:
    corner = rng.choice(("nw", "ne", "sw", "se"))
    w = rng.randint(max(6, cols // 3), max(7, cols // 2))
    h = rng.randint(max(6, rows // 3), max(7, rows // 2))
    x = 1 if "w" in corner else max(1, cols - w - 1)
    y = 1 if "n" in corner else max(1, rows - h - 1)
    rects: dict[int, list[TileRect]] = {1: [(x, y, w, h)]}
    current = rects[1][0]
    for level in range(2, int(active_max_level) + 1):
        current = _inset_rect(current, dx=1, dy=1, min_w=3, min_h=3)
        cx, cy, cw, ch = current
        if "w" in corner:
            cx = max(1, cx - 1)
        else:
            cx = min(cols - cw - 1, cx + 1)
        if "n" in corner:
            cy = max(1, cy - 1)
        else:
            cy = min(rows - ch - 1, cy + 1)
        current = (cx, cy, cw, ch)
        rects[int(level)] = [current]
    return rects


def _make_split_rects(rng: random.Random, *, cols: int, rows: int, active_max_level: int) -> dict[int, list[TileRect]]:
    w = max(4, cols // 3)
    h = max(4, rows // 3)
    left = (rng.randint(1, 2), rng.randint(1, max(1, rows - h - 2)), w, h)
    right = (max(1, cols - w - rng.randint(2, 3)), rng.randint(1, max(1, rows - h - 2)), w, h)
    rects: dict[int, list[TileRect]] = {1: [left, right]}
    current = rng.choice((left, right))
    for level in range(2, int(active_max_level) + 1):
        current = _inset_rect(current, dx=1, dy=1, min_w=3, min_h=3)
        rects[int(level)] = [current]
    return rects


def _make_level_grid(
    rng: random.Random,
    *,
    cols: int,
    rows: int,
    active_max_level: int,
    layout_family: str,
) -> tuple[dict[tuple[int, int], int], dict[int, list[TileRect]]]:
    if str(layout_family) == "side_plateau":
        rects = _make_side_rects(rng, cols=int(cols), rows=int(rows), active_max_level=int(active_max_level))
    elif str(layout_family) == "corner_plateau":
        rects = _make_corner_rects(rng, cols=int(cols), rows=int(rows), active_max_level=int(active_max_level))
    elif str(layout_family) == "split_field":
        rects = _make_split_rects(rng, cols=int(cols), rows=int(rows), active_max_level=int(active_max_level))
    else:
        rects = _make_concentric_rects(rng, cols=int(cols), rows=int(rows), active_max_level=int(active_max_level))
    grid = _blank_level_grid(cols=int(cols), rows=int(rows))
    for level in range(1, int(active_max_level) + 1):
        for rect in rects.get(int(level), []):
            _apply_rect(grid, rect, level=int(level), cols=int(cols), rows=int(rows))
    return grid, rects


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


def _sample_farm_patches(
    rng: random.Random,
    *,
    cols: int,
    rows: int,
    active_levels: Sequence[int],
    level_grid: Mapping[tuple[int, int], int],
    blocked_tile_ids: set[str],
) -> tuple[list[dict[str, Any]], dict[tuple[int, int], str], set[str]]:
    """Place at most one connected farm terrain patch per active level without consuming candidate support."""

    patches: list[dict[str, Any]] = []
    terrain_by_cell: dict[tuple[int, int], str] = {}
    occupied: set[str] = set()
    patch_sizes = ((2, 2), (2, 3), (3, 2), (3, 3))
    for level in active_levels:
        if rng.random() > 0.68:
            continue
        level_tile_total = sum(1 for value in level_grid.values() if int(value) == int(level))
        candidates: list[tuple[TileRect, tuple[str, ...]]] = []
        sizes = list(patch_sizes)
        rng.shuffle(sizes)
        for w, h in sizes:
            for y in range(1, max(1, int(rows) - int(h))):
                for x in range(1, max(1, int(cols) - int(w))):
                    rect = (int(x), int(y), int(w), int(h))
                    cells = _rect_cells(rect)
                    tile_ids = tuple(_tile_id(col, row) for col, row in cells)
                    if any(tile_id in blocked_tile_ids or tile_id in occupied for tile_id in tile_ids):
                        continue
                    if int(level_tile_total) - len(tile_ids) < 5:
                        continue
                    if all(int(level_grid[(col, row)]) == int(level) for col, row in cells):
                        candidates.append((rect, tile_ids))
        if not candidates:
            continue
        rect, tile_ids = rng.choice(candidates)
        terrain = str(rng.choice(FARM_PATCH_TERRAINS))
        patch_id = f"farm_patch_{len(patches):02d}"
        patches.append(
            {
                "patch_id": patch_id,
                "level": int(level),
                "terrain": terrain,
                "rect": [int(value) for value in rect],
                "tile_ids": list(tile_ids),
            }
        )
        occupied.update(tile_ids)
        for col, row in _rect_cells(rect):
            terrain_by_cell[(int(col), int(row))] = terrain
    if not patches:
        forced_levels = list(active_levels)
        rng.shuffle(forced_levels)
        for level in forced_levels:
            candidates = []
            level_tile_total = sum(1 for value in level_grid.values() if int(value) == int(level))
            for y in range(1, max(1, int(rows) - 2)):
                for x in range(1, max(1, int(cols) - 2)):
                    rect = (int(x), int(y), 2, 2)
                    cells = _rect_cells(rect)
                    tile_ids = tuple(_tile_id(col, row) for col, row in cells)
                    if any(tile_id in blocked_tile_ids for tile_id in tile_ids):
                        continue
                    if int(level_tile_total) - len(tile_ids) < 5:
                        continue
                    if all(int(level_grid[(col, row)]) == int(level) for col, row in cells):
                        candidates.append((rect, tile_ids))
            if not candidates:
                continue
            rect, tile_ids = rng.choice(candidates)
            terrain = str(rng.choice(FARM_PATCH_TERRAINS))
            patches.append(
                {
                    "patch_id": "farm_patch_00",
                    "level": int(level),
                    "terrain": terrain,
                    "rect": [int(value) for value in rect],
                    "tile_ids": list(tile_ids),
                }
            )
            occupied.update(tile_ids)
            for col, row in _rect_cells(rect):
                terrain_by_cell[(int(col), int(row))] = terrain
            break
    return patches, terrain_by_cell, occupied


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
    elif terrain == "pasture":
        fill = (103, 171, 92)
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
    elif tile.terrain == "pasture":
        for dx in (-0.18, 0.08, 0.21):
            px = int(round(cx + dx * layout.tile_w))
            draw.line((px, int(cy + 1), px + 5, int(cy - 5)), fill=(50, 128, 58), width=2)


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


def _transition_specs(
    rng: random.Random,
    *,
    level_grid: Mapping[tuple[int, int], int],
    active_levels: Sequence[int],
) -> list[tuple[str, str, tuple[int, int], tuple[int, int], int, int, str]]:
    specs: list[tuple[str, str, tuple[int, int], tuple[int, int], int, int, str]] = []
    for level in [value for value in active_levels if int(value) > 0]:
        candidates: list[tuple[str, tuple[int, int], tuple[int, int]]] = []
        for (col, row), tile_level in level_grid.items():
            if int(tile_level) != int(level):
                continue
            for side, lower in (("south", (int(col), int(row) + 1)), ("east", (int(col) + 1, int(row)))):
                if int(level_grid.get(lower, -1)) == int(level) - 1:
                    candidates.append((side, lower, (int(col), int(row))))
        if not candidates:
            continue
        side, lower, upper = rng.choice(candidates)
        kind = "ramp" if level % 2 else "stair"
        specs.append((f"transition_{level - 1}_{level}", kind, lower, upper, level - 1, level, str(side)))
    return specs


def _draw_transition(draw: ImageDraw.ImageDraw, layout: IsoLayout, spec: tuple[str, str, tuple[int, int], tuple[int, int], int, int, str]) -> IsoFarmsteadTransition:
    """Draw one ramp/stair over a sampled level boundary and record its blocking footprint."""

    transition_id, kind, lower_xy, upper_xy, lower_level, upper_level, side = spec
    lower_top, _, _, lower_left = _tile_vertices(layout, lower_xy[0], lower_xy[1], lower_level)
    _, lower_right, _, _ = _tile_vertices(layout, lower_xy[0], lower_xy[1], lower_level)
    _, upper_right, upper_bottom, upper_left = _tile_vertices(layout, upper_xy[0], upper_xy[1], upper_level)
    if str(side) == "east":
        polygon: IsoPolygon = (upper_right, upper_bottom, lower_left, lower_top)
        line_pairs = ((upper_right, lower_top), (upper_bottom, lower_left))
    else:
        polygon = (upper_left, upper_bottom, lower_right, lower_top)
        line_pairs = ((upper_left, lower_top), (upper_bottom, lower_right))
    points = [(int(round(x)), int(round(y))) for x, y in polygon]
    if kind == "ramp":
        draw.polygon(points, fill=(191, 145, 86), outline=(96, 70, 45))
        draw.line(line_pairs[0], fill=(100, 71, 45), width=2)
        draw.line(line_pairs[1], fill=(141, 100, 58), width=2)
        for t in (0.33, 0.66):
            lx = line_pairs[0][0][0] + (line_pairs[0][1][0] - line_pairs[0][0][0]) * t
            ly = line_pairs[0][0][1] + (line_pairs[0][1][1] - line_pairs[0][0][1]) * t
            rx = line_pairs[1][0][0] + (line_pairs[1][1][0] - line_pairs[1][0][0]) * t
            ry = line_pairs[1][0][1] + (line_pairs[1][1][1] - line_pairs[1][0][1]) * t
            draw.line((int(lx), int(ly), int(rx), int(ry)), fill=(214, 164, 97), width=2)
    else:
        draw.polygon(points, fill=(128, 118, 96), outline=(79, 72, 59))
        for index in range(5):
            t = index / 5.0
            lx = line_pairs[0][0][0] + (line_pairs[0][1][0] - line_pairs[0][0][0]) * t
            ly = line_pairs[0][0][1] + (line_pairs[0][1][1] - line_pairs[0][0][1]) * t
            rx = line_pairs[1][0][0] + (line_pairs[1][1][0] - line_pairs[1][0][0]) * t
            ry = line_pairs[1][0][1] + (line_pairs[1][1][1] - line_pairs[1][0][1]) * t
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


def _bbox_inside_canvas(bbox: Sequence[float], *, width: int, height: int) -> bool:
    return 0 <= float(bbox[0]) < float(bbox[2]) <= float(width) and 0 <= float(bbox[1]) < float(bbox[3]) <= float(height)


def _object_sprite_bbox(layout: IsoLayout, tile: IsoFarmsteadTile, *, object_type: str, subtype: str) -> BBox:
    cx, cy = tile.center_xy
    if str(object_type) == "tree":
        width = float(layout.tile_w) * 0.62
        height = float(layout.tile_w) * 1.18
        return (cx - width * 0.5, cy - height + float(layout.tile_h) * 0.28, cx + width * 0.5, cy + float(layout.tile_h) * 0.28)
    if str(subtype) == "cow":
        width = float(layout.tile_w) * 0.96
        height = float(layout.tile_w) * 0.52
    elif str(subtype) == "chicken":
        width = float(layout.tile_w) * 0.46
        height = float(layout.tile_w) * 0.42
    else:
        width = float(layout.tile_w) * 0.6
        height = float(layout.tile_w) * 0.46
    return (cx - width * 0.5, cy - height * 0.72, cx + width * 0.5, cy + height * 0.28)


def _paste_sprite(image: Image.Image, bbox: Sequence[float], sprite: Image.Image) -> None:
    x0, y0, x1, y1 = [int(round(float(value))) for value in bbox]
    if x1 <= x0 or y1 <= y0:
        return
    scaled = sprite.resize((x1 - x0, y1 - y0), Image.Resampling.NEAREST)
    image.paste(scaled, (x0, y0), scaled)


def _tree_sprite(style: str) -> Image.Image:
    sprite = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    sprite_draw = ImageDraw.Draw(sprite, "RGBA")
    leaf_by_style = {
        "oak": (44, 138, 76),
        "pine": (42, 118, 83),
        "maple": (176, 96, 58),
        "fruit_tree": (57, 142, 78),
    }
    draw_pixel_tree(
        sprite_draw,
        (0, 0, 1, 2),
        style=str(style),
        leaf_rgb=leaf_by_style.get(str(style), (44, 138, 76)),
        fruit_rgb=(220, 68, 61),
    )
    return sprite


def _animal_sprite(animal_type: str, *, facing: str) -> Image.Image:
    tile_width = 2 if str(animal_type) == "cow" else 1
    sprite = Image.new("RGBA", (16 * tile_width, 16), (0, 0, 0, 0))
    sprite_draw = ImageDraw.Draw(sprite, "RGBA")
    draw_pixel_animal(sprite_draw, (0, 0, tile_width, 1), animal_type=str(animal_type), facing=str(facing))
    return sprite


def _patches_with_bboxes(patches: Sequence[Mapping[str, Any]], tiles_by_id: Mapping[str, IsoFarmsteadTile]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for patch in patches:
        tile_ids = [str(value) for value in patch.get("tile_ids", []) if str(value) in tiles_by_id]
        if not tile_ids:
            continue
        bbox = _bbox_union([tiles_by_id[tile_id].bbox_xyxy for tile_id in tile_ids])
        resolved.append({**dict(patch), "bbox": [round(float(value), 3) for value in bbox]})
    return resolved


def _draw_context_entities(
    image: Image.Image,
    layout: IsoLayout,
    tiles: Sequence[IsoFarmsteadTile],
    rng: random.Random,
    *,
    transition_tile_ids: set[str],
    farm_patch_tile_ids: set[str],
) -> tuple[list[IsoFarmsteadEntity], set[str]]:
    """Draw reusable farm context objects and return occupied terrain tile ids."""

    entities: list[IsoFarmsteadEntity] = []
    occupied: set[str] = set()
    blocked = set(transition_tile_ids)
    width, height = image.size
    tiles_by_id = {str(tile.tile_id): tile for tile in tiles}
    edge_tiles = [
        tile
        for tile in tiles
        if str(tile.tile_id) not in blocked
        and str(tile.tile_id) not in farm_patch_tile_ids
        and str(tile.terrain) == "grass"
        and (tile.col <= 2 or tile.row <= 2 or tile.col >= layout.cols - 3 or tile.row >= layout.rows - 3)
    ]
    fallback_tree_tiles = [
        tile
        for tile in tiles
        if str(tile.tile_id) not in blocked and str(tile.tile_id) not in farm_patch_tile_ids and str(tile.terrain) == "grass"
    ]
    tree_candidates = edge_tiles or fallback_tree_tiles
    rng.shuffle(tree_candidates)
    drawable: list[tuple[float, str, str, str, IsoFarmsteadTile, BBox]] = []
    tree_count = min(len(tree_candidates), rng.randint(3, 8))
    for index, tile in enumerate(tree_candidates[:tree_count]):
        style = str(rng.choice(TREE_STYLES))
        bbox = _object_sprite_bbox(layout, tile, object_type="tree", subtype=style)
        if not _bbox_inside_canvas(bbox, width=width, height=height):
            continue
        occupied.add(str(tile.tile_id))
        drawable.append((float(bbox[3]), f"tree_{index:02d}", "tree", style, tile, bbox))

    animal_candidates = [
        tile
        for tile in tiles
        if str(tile.tile_id) not in blocked
        and str(tile.tile_id) not in occupied
        and str(tile.terrain) in {"grass", "pasture"}
    ]
    rng.shuffle(animal_candidates)
    animal_count = min(len(animal_candidates), rng.randint(3, 7))
    animal_index = 0
    for tile in animal_candidates:
        if animal_index >= animal_count:
            break
        animal_type = str(rng.choice(ANIMAL_TYPES))
        bbox = _object_sprite_bbox(layout, tile, object_type="animal", subtype=animal_type)
        if not _bbox_inside_canvas(bbox, width=width, height=height):
            continue
        occupied.add(str(tile.tile_id))
        drawable.append((float(bbox[3]), f"animal_{animal_index:02d}", "domestic_animal", animal_type, tile, bbox))
        animal_index += 1

    for _, entity_id, object_type, subtype, tile, bbox in sorted(drawable, key=lambda item: item[0]):
        if object_type == "tree":
            _paste_sprite(image, bbox, _tree_sprite(subtype))
            public_name = f"{subtype.replace('_', ' ')}"
            metadata = {"base_level": int(tile.level), "tree_style": subtype}
        else:
            facing = str(rng.choice(("left", "right")))
            _paste_sprite(image, bbox, _animal_sprite(subtype, facing=facing))
            public_name = subtype
            metadata = {"base_level": int(tile.level), "animal_type": subtype, "facing": facing}
        _add_entity(
            entities,
            entity_id=entity_id,
            public_name=public_name,
            object_type=object_type,
            tile_ids=[str(tile.tile_id)],
            level=int(tile.level),
            bbox=bbox,
            role="context",
            metadata=metadata,
        )
    return entities, occupied


def _build_tiles(
    layout: IsoLayout,
    level_grid: Mapping[tuple[int, int], int],
    farm_terrain_by_cell: Mapping[tuple[int, int], str],
) -> tuple[IsoFarmsteadTile, ...]:
    tiles: list[IsoFarmsteadTile] = []
    for row in range(layout.rows):
        for col in range(layout.cols):
            level = int(level_grid[(col, row)])
            terrain = str(farm_terrain_by_cell.get((int(col), int(row)), "grass"))
            polygon = _tile_vertices(layout, col, row, level)
            center = _project(layout, col, row, level)
            metadata: dict[str, Any] = {"candidate_allowed": terrain == "grass"}
            if terrain != "grass":
                metadata["farm_patch_terrain"] = terrain
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
                    metadata=metadata,
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
    """Render a deterministic isometric farmstead with variable terrain levels."""

    rng = random.Random(int(seed))
    cols, rows = _profile_grid(int(width), int(height))
    active_max_level = _sample_active_max_level(rng)
    layout_family = _sample_layout_family(rng)
    active_levels = tuple(range(0, int(active_max_level) + 1))
    level_grid, level_shapes = _make_level_grid(
        rng,
        cols=cols,
        rows=rows,
        active_max_level=int(active_max_level),
        layout_family=str(layout_family),
    )
    transition_specs = _transition_specs(rng, level_grid=level_grid, active_levels=active_levels)
    transition_tile_ids = {_tile_id(spec[2][0], spec[2][1]) for spec in transition_specs} | {
        _tile_id(spec[3][0], spec[3][1]) for spec in transition_specs
    }
    farm_patches, farm_terrain_by_cell, farm_patch_tile_ids = _sample_farm_patches(
        rng,
        cols=cols,
        rows=rows,
        active_levels=active_levels,
        level_grid=level_grid,
        blocked_tile_ids=set(transition_tile_ids),
    )
    layout = _layout_for_scene(width=int(width), height=int(height), cols=cols, rows=rows, level_grid=level_grid)
    tile_rng = random.Random(int(seed) + 17011)
    tiles = _build_tiles(layout, level_grid, farm_terrain_by_cell)
    tiles_by_id = {str(tile.tile_id): tile for tile in tiles}
    farm_patches_with_bboxes = _patches_with_bboxes(farm_patches, tiles_by_id)
    image = Image.new("RGB", (int(width), int(height)), (207, 220, 190))
    draw = ImageDraw.Draw(image, "RGBA")

    for tile in tiles:
        _draw_tile_top(draw, layout, tile, tile_rng)
    open_edges = {(spec[3][0], spec[3][1], spec[6]) for spec in transition_specs}
    face_records = _draw_level_faces(draw, layout, level_grid, open_edges=open_edges)
    transitions = tuple(_draw_transition(draw, layout, spec) for spec in transition_specs)
    entities, occupied_tile_ids = _draw_context_entities(
        image,
        layout,
        tiles,
        rng,
        transition_tile_ids=set(transition_tile_ids),
        farm_patch_tile_ids=set(farm_patch_tile_ids),
    )

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
    excluded_tile_ids = set(transition_tile_ids) | set(occupied_tile_ids) | set(farm_patch_tile_ids)
    trace = {
        "renderer_id": RENDERER_ID,
        "renderer_style": RENDERER_STYLE,
        "theme_id": "isometric_farmstead_elevation",
        "seed": int(seed),
        "canvas_profile": str(canvas_profile),
        "canvas_profile_probabilities": dict(canvas_profile_probabilities or {}),
        "canvas_size_px": [int(width), int(height)],
        "grid_cols": int(cols),
        "grid_rows": int(rows),
        "supported_levels": list(SUPPORTED_LEVELS),
        "levels": list(active_levels),
        "active_max_level": int(active_max_level),
        "layout_family": str(layout_family),
        "level_tile_counts": {
            str(level): sum(1 for value in level_grid.values() if int(value) == int(level))
            for level in active_levels
        },
        "projection": {
            "type": "2:1_isometric",
            "tile_size_px": [round(float(layout.tile_w), 3), round(float(layout.tile_h), 3)],
            "level_step_px": round(float(layout.level_px), 3),
            "origin_xy": [round(float(value), 3) for value in layout.origin_xy],
        },
        "level_shapes": {
            str(level): [[int(value) for value in rect] for rect in rects]
            for level, rects in sorted(level_shapes.items())
        },
        "farm_patches": farm_patches_with_bboxes,
        "farm_patch_tile_ids": sorted(farm_patch_tile_ids),
        "transition_tile_ids": sorted(transition_tile_ids),
        "occupied_tile_ids": sorted(occupied_tile_ids),
        "eligible_tile_ids": [
            str(tile.tile_id)
            for tile in tiles
            if str(tile.tile_id) not in excluded_tile_ids and bool(tile.metadata.get("candidate_allowed", False))
        ],
        "tile_count": len(tiles),
        "entity_count": len(entities),
        "context_object_counts": {
            "tree": sum(1 for entity in entities if entity.object_type == "tree"),
            "domestic_animal": sum(1 for entity in entities if entity.object_type == "domestic_animal"),
        },
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
