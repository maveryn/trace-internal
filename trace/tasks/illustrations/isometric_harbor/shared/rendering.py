"""Renderer for the isometric harbor illustration scene."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng

from .state import BBox, IsoHarborEntity, IsoHarborScene, IsoHarborTile


SCENE_ID = "isometric_harbor"
RENDERER_ID = "isometric_harbor_v1"
BACKGROUND_RGB = (207, 220, 190)
SUPPORTED_CANVAS_PROFILES: Mapping[str, tuple[int, int, int, int, float, float]] = {
    "landscape": (16, 12, 60, 30, 0.5, 0.17),
    "square": (14, 14, 58, 29, 0.5, 0.18),
}
BOAT_SIDE_VALUES: tuple[str, ...] = ("left", "right")
BOAT_COLOR_PALETTES: tuple[tuple[tuple[int, int, int], tuple[int, int, int]], ...] = (
    ((164, 67, 50), (244, 196, 84)),
    ((35, 91, 143), (236, 108, 70)),
    ((65, 126, 97), (238, 187, 86)),
    ((128, 78, 142), (229, 178, 91)),
)


def _shade(color: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(channel) + int(delta))) for channel in color)


def _clamp_bbox(bbox: Sequence[float], *, width: int, height: int) -> BBox:
    return (
        max(0.0, min(float(width), float(bbox[0]))),
        max(0.0, min(float(height), float(bbox[1]))),
        max(0.0, min(float(width), float(bbox[2]))),
        max(0.0, min(float(height), float(bbox[3]))),
    )


def _bbox_for_points(points: Sequence[Sequence[float]]) -> BBox:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _iso_center(
    col: int,
    row: int,
    *,
    tile_w: float,
    tile_h: float,
    origin_x: float,
    origin_y: float,
) -> tuple[float, float]:
    return (
        float(origin_x) + (float(col) - float(row)) * float(tile_w) / 2.0,
        float(origin_y) + (float(col) + float(row)) * float(tile_h) / 2.0,
    )


def _tile_polygon(cx: float, cy: float, *, tile_w: float, tile_h: float) -> tuple[tuple[float, float], ...]:
    return (
        (float(cx), float(cy) - float(tile_h) / 2.0),
        (float(cx) + float(tile_w) / 2.0, float(cy)),
        (float(cx), float(cy) + float(tile_h) / 2.0),
        (float(cx) - float(tile_w) / 2.0, float(cy)),
    )


def _profile_geometry(width: int, height: int, canvas_profile: str) -> tuple[int, int, float, float, float, float]:
    profile = str(canvas_profile or "")
    if profile not in SUPPORTED_CANVAS_PROFILES:
        profile = "landscape" if int(width) >= int(height) else "square"
    cols, rows, tile_w, tile_h, origin_x_ratio, origin_y_ratio = SUPPORTED_CANVAS_PROFILES[profile]
    return (
        int(cols),
        int(rows),
        float(tile_w),
        float(tile_h),
        float(width) * float(origin_x_ratio),
        float(height) * float(origin_y_ratio),
    )


def _dock_cells(cols: int, rows: int, rng: Any) -> tuple[set[tuple[int, int]], dict[str, Any]]:
    dock_width = 2
    jitter = int(rng.choice((-1, 0, 1))) if int(cols) >= 16 else int(rng.choice((-1, 0)))
    left_col = max(3, min(int(cols) - 5, int(cols) // 2 - 1 + jitter))
    row_start = 1
    row_end = int(rows) - 1
    cells: set[tuple[int, int]] = {
        (col, row)
        for col in range(left_col, left_col + dock_width)
        for row in range(row_start, row_end)
    }
    cap_row = int(row_start)
    for col in range(left_col - 1, left_col + dock_width + 1):
        if 0 <= int(col) < int(cols):
            cells.add((int(col), cap_row))
    return cells, {
        "left_col": int(left_col),
        "right_col": int(left_col + dock_width - 1),
        "row_start": int(row_start),
        "row_end_exclusive": int(row_end),
        "dock_width_tiles": int(dock_width),
    }


def _land_cells(cols: int, rows: int, dock_meta: Mapping[str, Any]) -> set[tuple[int, int]]:
    """Return shoreline terrain cells that anchor the dock to land."""

    shore_rows = range(0, min(int(rows), int(dock_meta["row_start"]) + 1))
    return {(int(col), int(row)) for row in shore_rows for col in range(int(cols))}


def _make_tiles(
    *,
    cols: int,
    rows: int,
    tile_w: float,
    tile_h: float,
    origin_x: float,
    origin_y: float,
    dock_cells: set[tuple[int, int]],
    land_cells: set[tuple[int, int]],
) -> tuple[IsoHarborTile, ...]:
    tiles: list[IsoHarborTile] = []
    for row in range(int(rows)):
        for col in range(int(cols)):
            cx, cy = _iso_center(col, row, tile_w=tile_w, tile_h=tile_h, origin_x=origin_x, origin_y=origin_y)
            polygon = _tile_polygon(cx, cy, tile_w=tile_w, tile_h=tile_h)
            cell = (int(col), int(row))
            if cell in dock_cells:
                terrain = "dock"
            elif cell in land_cells:
                terrain = "land"
            else:
                terrain = "water"
            tiles.append(
                IsoHarborTile(
                    tile_id=f"tile_{int(col):02d}_{int(row):02d}",
                    col=int(col),
                    row=int(row),
                    terrain=terrain,
                    walkable=str(terrain) == "dock",
                    polygon_xy=polygon,
                    bbox_xyxy=_bbox_for_points(polygon),
                    center_xy=(float(cx), float(cy)),
                    metadata={"candidate_allowed": str(terrain) == "dock"},
                )
            )
    return tuple(tiles)


def _draw_land_tile(draw: ImageDraw.ImageDraw, tile: IsoHarborTile, *, rng: Any) -> None:
    green_shift = int(rng.randrange(-7, 8))
    fill = (126 + green_shift, 176 + green_shift, 103 + green_shift)
    if int(tile.row) > 0:
        fill = (194 + green_shift, 170 + green_shift, 105 + green_shift)
    dark = _shade(fill, -42)
    light = _shade(fill, 32)
    points = [(int(round(x)), int(round(y))) for x, y in tile.polygon_xy]
    draw.polygon(points, fill=fill)
    top, right, bottom, left = tile.polygon_xy
    draw.line((top, right), fill=light, width=2)
    draw.line((right, bottom), fill=_shade(dark, 8), width=2)
    draw.line((bottom, left), fill=dark, width=2)
    draw.line((left, top), fill=_shade(dark, -4), width=2)
    cx, cy = tile.center_xy
    if int(tile.row) == 0:
        for dx in (-0.2, 0.08, 0.22):
            px = int(round(cx + dx * (tile.bbox_xyxy[2] - tile.bbox_xyxy[0])))
            draw.line((px, int(cy + 2), px + 5, int(cy - 5)), fill=(53, 126, 58), width=2)
    else:
        draw.arc((cx - 11, cy - 2, cx + 12, cy + 7), 190, 350, fill=(143, 118, 74), width=1)


def _draw_water_tile(draw: ImageDraw.ImageDraw, tile: IsoHarborTile, *, rng: Any) -> None:
    blue_shift = int(rng.randrange(-8, 9))
    fill = (42, 135 + blue_shift, 174 + blue_shift)
    outline = (35, 112, 154)
    draw.polygon(tile.polygon_xy, fill=fill, outline=outline)
    cx, cy = tile.center_xy
    wave = float(tile.bbox_xyxy[2] - tile.bbox_xyxy[0]) * 0.16
    draw.arc((cx - wave, cy - 3, cx + wave, cy + 7), 190, 350, fill=(120, 205, 220), width=1)


def _draw_dock_tile(draw: ImageDraw.ImageDraw, tile: IsoHarborTile) -> None:
    draw.polygon(tile.polygon_xy, fill=(163, 112, 66), outline=(92, 61, 36))
    left, top, right, bottom = tile.bbox_xyxy
    cx, cy = tile.center_xy
    draw.line([(left + 8, cy), (cx, bottom - 2), (right - 8, cy)], fill=(124, 80, 43), width=1)
    draw.line([(cx, top + 2), (cx, bottom - 2)], fill=(121, 77, 41), width=1)


def _draw_post(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float) -> BBox:
    w = float(scale) * 0.16
    h = float(scale) * 0.42
    bbox = (float(cx) - w, float(cy) - h, float(cx) + w, float(cy) + h * 0.25)
    draw.rectangle(bbox, fill=(91, 58, 33), outline=(49, 32, 21))
    draw.ellipse((bbox[0], bbox[1] - w * 0.45, bbox[2], bbox[1] + w * 0.45), fill=(123, 84, 45), outline=(49, 32, 21))
    return bbox


def _draw_crate(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float) -> BBox:
    w = float(scale) * 0.28
    h = float(scale) * 0.22
    bbox = (float(cx) - w, float(cy) - h, float(cx) + w, float(cy) + h)
    draw.rectangle(bbox, fill=(170, 114, 57), outline=(82, 51, 27), width=2)
    draw.line([(bbox[0], bbox[1]), (bbox[2], bbox[3])], fill=(95, 57, 30), width=1)
    draw.line([(bbox[0], bbox[3]), (bbox[2], bbox[1])], fill=(95, 57, 30), width=1)
    return bbox


def _draw_barrel(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float) -> BBox:
    w = float(scale) * 0.2
    h = float(scale) * 0.28
    bbox = (float(cx) - w, float(cy) - h, float(cx) + w, float(cy) + h)
    draw.ellipse((bbox[0], bbox[1], bbox[2], bbox[1] + h * 0.55), fill=(138, 89, 45), outline=(65, 42, 27))
    draw.rectangle((bbox[0], bbox[1] + h * 0.25, bbox[2], bbox[3] - h * 0.25), fill=(128, 80, 39), outline=(65, 42, 27))
    draw.ellipse((bbox[0], bbox[3] - h * 0.55, bbox[2], bbox[3]), fill=(103, 67, 36), outline=(65, 42, 27))
    draw.line([(bbox[0] + 2, cy), (bbox[2] - 2, cy)], fill=(51, 49, 43), width=1)
    return bbox


def _boat_polygon(cx: float, cy: float, w: float, h: float) -> tuple[tuple[float, float], ...]:
    return (
        (float(cx) - float(w) * 0.5, float(cy)),
        (float(cx) - float(w) * 0.32, float(cy) - float(h) * 0.5),
        (float(cx) + float(w) * 0.32, float(cy) - float(h) * 0.5),
        (float(cx) + float(w) * 0.5, float(cy)),
        (float(cx) + float(w) * 0.28, float(cy) + float(h) * 0.5),
        (float(cx) - float(w) * 0.28, float(cy) + float(h) * 0.5),
    )


def _draw_polygon_with_outline(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Sequence[float]],
    *,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    width: int,
) -> None:
    polygon = [(float(x), float(y)) for x, y in points]
    draw.polygon(polygon, fill=fill)
    draw.line([*polygon, polygon[0]], fill=outline, width=int(width))


def _draw_boat(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    *,
    scale: float,
    boat_type: str,
    side: str,
    hull_fill: tuple[int, int, int],
    trim: tuple[int, int, int],
) -> BBox:
    """Draw one countable boat hull; returned bbox tracks the boat body, not wake or rope."""

    w = float(scale) * (1.12 if str(boat_type) == "cargo_boat" else 0.96)
    h = float(scale) * (0.66 if str(boat_type) == "cargo_boat" else 0.56)
    draw.ellipse(
        (cx - w * 0.58, cy + h * 0.08, cx + w * 0.58, cy + h * 0.54),
        fill=(30, 96, 127),
    )
    wake_fill = (118, 202, 218)
    draw.arc((cx - w * 0.72, cy + h * 0.18, cx - w * 0.32, cy + h * 0.58), 210, 20, fill=wake_fill, width=1)
    draw.arc((cx + w * 0.32, cy + h * 0.18, cx + w * 0.72, cy + h * 0.58), 160, 330, fill=wake_fill, width=1)
    hull = _boat_polygon(cx, cy, w, h)
    _draw_polygon_with_outline(draw, hull, fill=hull_fill, outline=(33, 34, 32), width=3)
    inner = _boat_polygon(cx, cy, w * 0.68, h * 0.5)
    _draw_polygon_with_outline(draw, inner, fill=(220, 181, 118), outline=trim, width=2)
    draw.line((cx - w * 0.44, cy - h * 0.05, cx + w * 0.44, cy - h * 0.05), fill=_shade(trim, -24), width=2)
    draw.line((cx - w * 0.36, cy + h * 0.18, cx + w * 0.36, cy + h * 0.18), fill=_shade(trim, -32), width=2)
    if str(boat_type) == "cargo_boat":
        cabin_w = w * 0.24
        cabin_h = h * 0.34
        draw.rectangle(
            (cx - cabin_w, cy - cabin_h * 0.6, cx + cabin_w, cy + cabin_h * 0.35),
            fill=(226, 214, 178),
            outline=(64, 62, 56),
        )
        draw.rectangle(
            (cx - cabin_w * 0.55, cy - cabin_h * 0.32, cx - cabin_w * 0.08, cy + cabin_h * 0.02),
            fill=(72, 138, 166),
            outline=(39, 72, 87),
        )
        draw.rectangle(
            (cx + cabin_w * 0.08, cy - cabin_h * 0.32, cx + cabin_w * 0.55, cy + cabin_h * 0.02),
            fill=(72, 138, 166),
            outline=(39, 72, 87),
        )
        cargo_w = w * 0.15
        cargo_h = h * 0.2
        for ox, oy in ((-0.3, 0.12), (0.28, 0.16)):
            draw.rectangle(
                (cx + ox * w - cargo_w, cy + oy * h - cargo_h, cx + ox * w + cargo_w, cy + oy * h + cargo_h),
                fill=(174, 111, 54),
                outline=(76, 47, 26),
            )
    else:
        for offset in (-0.22, 0.0, 0.22):
            draw.line(
                [(cx + offset * w - w * 0.15, cy - h * 0.06), (cx + offset * w + w * 0.15, cy + h * 0.1)],
                fill=(92, 58, 34),
                width=3,
            )
        draw.line((cx - w * 0.43, cy + h * 0.31, cx + w * 0.42, cy - h * 0.29), fill=(96, 63, 38), width=2)
        draw.ellipse((cx + w * 0.4 - 3, cy - h * 0.3 - 2, cx + w * 0.4 + 6, cy - h * 0.3 + 4), fill=(146, 96, 53))
    line_end_x = cx + (w * 0.58 if str(side) == "left" else -w * 0.58)
    draw.line([(cx, cy - h * 0.04), (line_end_x, cy - h * 0.46)], fill=(231, 218, 178), width=2)
    bbox = _bbox_for_points(hull)
    pad = 4.0
    return (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)


def _add_entity(
    entities: list[IsoHarborEntity],
    *,
    entity_id: str,
    public_name: str,
    object_type: str,
    tile_ids: Sequence[str],
    bbox: Sequence[float],
    point: Sequence[float],
    role: str,
    metadata: Mapping[str, Any],
    canvas_size: tuple[int, int],
) -> None:
    width, height = canvas_size
    entities.append(
        IsoHarborEntity(
            entity_id=str(entity_id),
            public_name=str(public_name),
            object_type=str(object_type),
            tile_ids=tuple(str(value) for value in tile_ids),
            bbox_xyxy=_clamp_bbox(bbox, width=int(width), height=int(height)),
            point_xy=(round(float(point[0]), 3), round(float(point[1]), 3)),
            role=str(role),
            metadata=dict(metadata),
        )
    )


def _select_boat_rows(
    *,
    rng: Any,
    dock_meta: Mapping[str, Any],
    side: str,
    count: int,
) -> list[int]:
    rows = list(range(int(dock_meta["row_start"]) + 1, int(dock_meta["row_end_exclusive"]) - 1))
    rows = [row for index, row in enumerate(rows) if index % 2 == (0 if str(side) == "left" else 1)]
    if len(rows) < int(count):
        rows = list(range(int(dock_meta["row_start"]) + 1, int(dock_meta["row_end_exclusive"]) - 1))
    rng.shuffle(rows)
    return sorted(rows[: int(count)])


def _draw_context_objects(
    *,
    draw: ImageDraw.ImageDraw,
    rng: Any,
    tiles_by_cell: Mapping[tuple[int, int], IsoHarborTile],
    dock_cells: set[tuple[int, int]],
    dock_meta: Mapping[str, Any],
    entities: list[IsoHarborEntity],
    canvas_size: tuple[int, int],
    tile_w: float,
) -> None:
    """Place non-answer cargo props on dock tiles without changing boat-side counts."""

    usable = [
        cell
        for cell in sorted(dock_cells)
        if int(dock_meta["row_start"]) + 1 <= int(cell[1]) < int(dock_meta["row_end_exclusive"]) - 1
    ]
    rng.shuffle(usable)
    context_count = min(len(usable), int(rng.randrange(4, 8)))
    for index, cell in enumerate(usable[:context_count]):
        tile = tiles_by_cell[cell]
        cx, cy = tile.center_xy
        offset_x = float(rng.choice((-0.16, 0.16))) * float(tile_w)
        offset_y = float(rng.choice((-0.08, 0.06))) * float(tile_w)
        object_type = str(rng.choice(("crate", "barrel")))
        if object_type == "crate":
            bbox = _draw_crate(draw, cx + offset_x, cy + offset_y, tile_w)
            name = "crate"
        else:
            bbox = _draw_barrel(draw, cx + offset_x, cy + offset_y, tile_w)
            name = "barrel"
        _add_entity(
            entities,
            entity_id=f"{object_type}_{index:02d}",
            public_name=name,
            object_type=object_type,
            tile_ids=(tile.tile_id,),
            bbox=bbox,
            point=(cx + offset_x, cy + offset_y),
            role="context",
            metadata={"base_tile_id": str(tile.tile_id)},
            canvas_size=canvas_size,
        )


def _draw_dock_posts(
    *,
    draw: ImageDraw.ImageDraw,
    tiles_by_cell: Mapping[tuple[int, int], IsoHarborTile],
    dock_meta: Mapping[str, Any],
    entities: list[IsoHarborEntity],
    canvas_size: tuple[int, int],
    tile_w: float,
) -> None:
    rows = range(int(dock_meta["row_start"]) + 1, int(dock_meta["row_end_exclusive"]), 3)
    for index, row in enumerate(rows):
        for side, col in (("left", int(dock_meta["left_col"])), ("right", int(dock_meta["right_col"]))):
            tile = tiles_by_cell.get((int(col), int(row)))
            if tile is None:
                continue
            cx, cy = tile.center_xy
            x_offset = -0.42 * float(tile_w) if side == "left" else 0.42 * float(tile_w)
            bbox = _draw_post(draw, cx + x_offset, cy, tile_w)
            _add_entity(
                entities,
                entity_id=f"dock_post_{side}_{index:02d}",
                public_name="dock post",
                object_type="dock_post",
                tile_ids=(tile.tile_id,),
                bbox=bbox,
                point=(cx + x_offset, cy),
                role="context",
                metadata={"dock_side": side, "base_tile_id": str(tile.tile_id)},
                canvas_size=canvas_size,
            )


def _draw_boats(
    *,
    draw: ImageDraw.ImageDraw,
    rng: Any,
    tiles_by_cell: Mapping[tuple[int, int], IsoHarborTile],
    dock_meta: Mapping[str, Any],
    required_boat_counts_by_side: Mapping[str, int],
    entities: list[IsoHarborEntity],
    canvas_size: tuple[int, int],
    tile_w: float,
) -> dict[str, int]:
    """Draw exact side-bound boat counts and record each boat's dock-side binding."""

    counts = {side: int(required_boat_counts_by_side.get(side, rng.randrange(0, 4))) for side in BOAT_SIDE_VALUES}
    for side in BOAT_SIDE_VALUES:
        counts[side] = max(0, min(5, int(counts[side])))
    side_to_water_col = {
        "left": int(dock_meta["left_col"]) - 1,
        "right": int(dock_meta["right_col"]) + 1,
    }
    entity_index = 0
    for side in BOAT_SIDE_VALUES:
        rows = _select_boat_rows(rng=rng, dock_meta=dock_meta, side=side, count=int(counts[side]))
        for row in rows:
            water_tile = tiles_by_cell.get((int(side_to_water_col[side]), int(row)))
            dock_tile = tiles_by_cell.get((int(dock_meta["left_col" if side == "left" else "right_col"]), int(row)))
            if water_tile is None or dock_tile is None:
                continue
            cx, cy = water_tile.center_xy
            side_offset = 0.18 * float(tile_w) if side == "left" else -0.18 * float(tile_w)
            boat_type = str(rng.choice(("rowboat", "cargo_boat")))
            hull_fill, trim = rng.choice(BOAT_COLOR_PALETTES)
            bbox = _draw_boat(
                draw,
                cx + side_offset,
                cy,
                scale=tile_w,
                boat_type=boat_type,
                side=side,
                hull_fill=tuple(hull_fill),
                trim=tuple(trim),
            )
            _add_entity(
                entities,
                entity_id=f"boat_{entity_index:02d}",
                public_name="boat",
                object_type="boat",
                tile_ids=(water_tile.tile_id, dock_tile.tile_id),
                bbox=bbox,
                point=(cx + side_offset, cy),
                role="queryable",
                metadata={
                    "boat_type": boat_type,
                    "hull_rgb": [int(value) for value in hull_fill],
                    "trim_rgb": [int(value) for value in trim],
                    "dock_side": side,
                    "water_tile_id": str(water_tile.tile_id),
                    "dock_tile_id": str(dock_tile.tile_id),
                },
                canvas_size=canvas_size,
            )
            entity_index += 1
    return counts


def render_isometric_harbor_scene(
    instance_seed: int,
    *,
    width: int = 1200,
    height: int = 800,
    canvas_profile: str = "landscape",
    canvas_profile_probabilities: Mapping[str, float] | None = None,
    required_boat_counts_by_side: Mapping[str, int] | None = None,
) -> IsoHarborScene:
    """Render a deterministic full-bleed isometric harbor scene."""

    rng = spawn_rng(int(instance_seed), f"{SCENE_ID}:render")
    cols, rows, tile_w, tile_h, origin_x, origin_y = _profile_geometry(int(width), int(height), str(canvas_profile))
    dock_cells, dock_meta = _dock_cells(cols, rows, rng)
    land_cells = _land_cells(cols, rows, dock_meta)
    tiles = _make_tiles(
        cols=cols,
        rows=rows,
        tile_w=tile_w,
        tile_h=tile_h,
        origin_x=origin_x,
        origin_y=origin_y,
        dock_cells=dock_cells,
        land_cells=land_cells,
    )
    tiles_by_cell = {(int(tile.col), int(tile.row)): tile for tile in tiles}
    image = Image.new("RGB", (int(width), int(height)), BACKGROUND_RGB)
    draw = ImageDraw.Draw(image)
    for tile in tiles:
        if str(tile.terrain) == "water":
            _draw_water_tile(draw, tile, rng=rng)
        elif str(tile.terrain) == "land":
            _draw_land_tile(draw, tile, rng=rng)
    for tile in tiles:
        if str(tile.terrain) == "dock":
            _draw_dock_tile(draw, tile)

    entities: list[IsoHarborEntity] = []
    _draw_dock_posts(
        draw=draw,
        tiles_by_cell=tiles_by_cell,
        dock_meta=dock_meta,
        entities=entities,
        canvas_size=(int(width), int(height)),
        tile_w=tile_w,
    )
    _draw_context_objects(
        draw=draw,
        rng=rng,
        tiles_by_cell=tiles_by_cell,
        dock_cells=dock_cells,
        dock_meta=dock_meta,
        entities=entities,
        canvas_size=(int(width), int(height)),
        tile_w=tile_w,
    )
    side_counts = _draw_boats(
        draw=draw,
        rng=rng,
        tiles_by_cell=tiles_by_cell,
        dock_meta=dock_meta,
        required_boat_counts_by_side={str(key): int(value) for key, value in (required_boat_counts_by_side or {}).items()},
        entities=entities,
        canvas_size=(int(width), int(height)),
        tile_w=tile_w,
    )

    dock_tile_ids = [tile.tile_id for tile in tiles if str(tile.terrain) == "dock"]
    water_tile_ids = [tile.tile_id for tile in tiles if str(tile.terrain) == "water"]
    land_tile_ids = [tile.tile_id for tile in tiles if str(tile.terrain) == "land"]
    trace = {
        "renderer_id": RENDERER_ID,
        "renderer_style": "isometric_pixel_harbor",
        "theme_id": "isometric_harbor_shoreline_dock",
        "seed": int(instance_seed),
        "background_rgb": [int(value) for value in BACKGROUND_RGB],
        "canvas_profile": str(canvas_profile),
        "canvas_profile_probabilities": dict(canvas_profile_probabilities or {}),
        "canvas_size_px": [int(width), int(height)],
        "grid_cols": int(cols),
        "grid_rows": int(rows),
        "tile_count": len(tiles),
        "dock_tile_ids": dock_tile_ids,
        "water_tile_ids": water_tile_ids,
        "land_tile_ids": land_tile_ids,
        "terrain_tile_counts": {
            "dock": len(dock_tile_ids),
            "water": len(water_tile_ids),
            "land": len(land_tile_ids),
        },
        "dock_meta": dict(dock_meta),
        "boat_counts_by_side": {str(side): int(side_counts.get(side, 0)) for side in BOAT_SIDE_VALUES},
        "entity_count": len(entities),
        "context_object_counts": {
            "boat": sum(1 for entity in entities if entity.object_type == "boat"),
            "crate": sum(1 for entity in entities if entity.object_type == "crate"),
            "barrel": sum(1 for entity in entities if entity.object_type == "barrel"),
            "dock_post": sum(1 for entity in entities if entity.object_type == "dock_post"),
        },
        "projection": {
            "type": "2:1_isometric",
            "origin_xy": [round(float(origin_x), 3), round(float(origin_y), 3)],
            "tile_size_px": [round(float(tile_w), 3), round(float(tile_h), 3)],
        },
    }
    return IsoHarborScene(
        image=image,
        tiles=tuple(tiles),
        entities=tuple(sorted(entities, key=lambda entity: str(entity.entity_id))),
        trace=trace,
    )


__all__ = [
    "BOAT_SIDE_VALUES",
    "RENDERER_ID",
    "SCENE_ID",
    "SUPPORTED_CANVAS_PROFILES",
    "render_isometric_harbor_scene",
]
