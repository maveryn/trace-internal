"""Scene-local top-down RPG dungeon renderer."""

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
from trace.tasks.illustrations.shared.rpg_tile_profiles import DEFAULT_RPG_TILE_PX

from .relations import reachable_entity_ids, reachable_tiles
from .state import (
    BBox,
    RpgDungeonBlocker,
    RpgDungeonChamber,
    RpgDungeonEntity,
    RpgDungeonScene,
    Tile,
    TileBox,
)


SCENE_ID = "rpg_dungeon"
RENDERER_ID = "rpg_dungeon_top_down_v0"
DEFAULT_TILE_PX = DEFAULT_RPG_TILE_PX
DEFAULT_CANVAS_WIDTH = 27 * DEFAULT_TILE_PX
DEFAULT_CANVAS_HEIGHT = 18 * DEFAULT_TILE_PX
MIN_REACHABLE_CHEST_COUNT = 0
MAX_REACHABLE_CHEST_COUNT = 5
TOTAL_CHEST_COUNT = 5

RGB = tuple[int, int, int]

THEMES: Mapping[str, Mapping[str, Any]] = {
    "blue_stone": {
        "background_rgb": (31, 34, 43),
        "floor_rgb": (79, 88, 102),
        "floor_alt_rgb": (88, 96, 111),
        "floor_line_rgb": (55, 62, 74),
        "wall_edge_rgb": (28, 30, 37),
        "wall_light_rgb": (118, 126, 139),
        "chest_wood_rgb": (142, 84, 42),
        "chest_metal_rgb": (210, 172, 72),
    },
    "green_ruin": {
        "background_rgb": (33, 40, 35),
        "floor_rgb": (75, 91, 78),
        "floor_alt_rgb": (86, 101, 84),
        "floor_line_rgb": (52, 65, 56),
        "wall_edge_rgb": (25, 32, 28),
        "wall_light_rgb": (112, 132, 111),
        "chest_wood_rgb": (130, 79, 43),
        "chest_metal_rgb": (196, 161, 68),
    },
    "red_crypt": {
        "background_rgb": (42, 32, 35),
        "floor_rgb": (94, 78, 80),
        "floor_alt_rgb": (106, 86, 86),
        "floor_line_rgb": (66, 49, 54),
        "wall_edge_rgb": (34, 25, 28),
        "wall_light_rgb": (138, 114, 112),
        "chest_wood_rgb": (116, 67, 42),
        "chest_metal_rgb": (216, 154, 79),
    },
}


@dataclass(frozen=True)
class RpgDungeonLayout:
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
class _ChamberSpec:
    chamber_id: str
    public_name: str
    tile_xywh: TileBox


@dataclass(frozen=True)
class _EntitySpec:
    entity_id: str
    object_type: str
    public_name: str
    chamber_id: str | None
    tile_xywh: TileBox
    role: str
    visual: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class _BlockerSpec:
    blocker_id: str
    edge_id: str
    blocker_type: str
    tile_xy: Tile
    orientation: str


@dataclass(frozen=True)
class _EdgeSpec:
    edge_id: str
    source_chamber_id: str
    target_chamber_id: str
    path: tuple[Tile, ...]


@dataclass(frozen=True)
class _LayoutSpec:
    chambers: tuple[_ChamberSpec, ...]
    edge_specs: tuple[_EdgeSpec, ...]
    floor_tiles: tuple[Tile, ...]
    corridor_tiles: tuple[Tile, ...]
    blocked_tiles: tuple[Tile, ...]
    blocked_edge_ids: tuple[str, ...]
    blocker_specs: tuple[_BlockerSpec, ...]
    entity_specs: tuple[_EntitySpec, ...]
    player_tile: Tile
    chest_tile_map: Mapping[str, Tile]
    reachable_chest_ids: tuple[str, ...]


def render_rpg_dungeon_scene(
    seed: int,
    *,
    width: int = DEFAULT_CANVAS_WIDTH,
    height: int = DEFAULT_CANVAS_HEIGHT,
    tile_px: int = DEFAULT_TILE_PX,
    reachable_chest_count: int | None = None,
    total_chest_count: int = TOTAL_CHEST_COUNT,
    render_metadata: Mapping[str, Any] | None = None,
) -> RpgDungeonScene:
    """Render one top-down RPG dungeon layout with reachable chest metadata."""

    rng = random.Random(int(seed))
    layout = _sample_layout(width=int(width), height=int(height), tile_px=int(tile_px))
    theme_id = str(_choose(rng, tuple(THEMES)))
    theme = THEMES[theme_id]
    target_count = _resolve_reachable_chest_count(rng, reachable_chest_count)
    if int(total_chest_count) != TOTAL_CHEST_COUNT:
        raise ValueError(f"rpg_dungeon currently renders exactly {TOTAL_CHEST_COUNT} chests")
    layout_spec = _make_valid_layout_spec(layout, rng=rng, target_count=target_count)

    canonical, draw = _render_base(layout, layout_spec=layout_spec, theme=theme, rng=rng)
    entities = _render_entities(
        draw,
        entity_specs=layout_spec.entity_specs,
        layout=layout,
        theme=theme,
        theme_id=theme_id,
    )
    blockers = _render_blockers(
        draw,
        blocker_specs=layout_spec.blocker_specs,
        layout=layout,
        theme=theme,
        theme_id=theme_id,
    )
    scaled = canonical.resize((layout.display_grid_width_px, layout.display_grid_height_px), Image.Resampling.NEAREST)
    final = Image.new("RGB", (int(width), int(height)), _shade(theme["background_rgb"], -4))
    final.paste(scaled.convert("RGB"), layout.display_offset_xy)
    chambers = tuple(
        RpgDungeonChamber(
            chamber_id=spec.chamber_id,
            public_name=spec.public_name,
            tile_xywh=spec.tile_xywh,
            bbox_xyxy=_tile_bbox(layout, spec.tile_xywh),
            metadata={"kind": "carved_chamber"},
        )
        for spec in layout_spec.chambers
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
        "reachable_chest_target": int(target_count),
        "reachable_chest_ids": [str(entity_id) for entity_id in layout_spec.reachable_chest_ids],
        "edge_ids": [str(edge.edge_id) for edge in layout_spec.edge_specs],
        "blocked_edge_ids": [str(edge_id) for edge_id in layout_spec.blocked_edge_ids],
        "player_tile": [int(value) for value in layout_spec.player_tile],
        "chest_tile_map": {
            str(entity_id): [int(tile[0]), int(tile[1])]
            for entity_id, tile in sorted(layout_spec.chest_tile_map.items())
        },
        **dict(render_metadata or {}),
    }
    return RpgDungeonScene(
        image=final,
        chambers=chambers,
        floor_tiles=layout_spec.floor_tiles,
        blocked_tiles=layout_spec.blocked_tiles,
        corridor_tiles=layout_spec.corridor_tiles,
        blockers=tuple(sorted(blockers, key=lambda blocker: blocker.blocker_id)),
        entities=tuple(sorted(entities, key=lambda entity: (entity.role, entity.entity_id))),
        player_entity_id="player_00",
        chest_entity_ids=tuple(sorted(layout_spec.chest_tile_map)),
        reachable_chest_ids=tuple(str(entity_id) for entity_id in layout_spec.reachable_chest_ids),
        trace=trace,
    )


def rpg_dungeon_profile_metadata(render_params: Mapping[str, Any]) -> dict[str, Any]:
    """Return render trace metadata for the selected shared canvas profile."""

    return {
        "canvas_profile": str(render_params.get("canvas_profile", "")),
        "canvas_profile_size": list(render_params.get("canvas_profile_size", [])),
        "canvas_profile_probabilities": dict(render_params.get("canvas_profile_probabilities", {})),
        "rpg_tile_profile": dict(render_params.get("rpg_tile_profile", {})),
    }


def render_rpg_dungeon_profile_scene(
    seed: int,
    *,
    render_params: Mapping[str, Any],
    tile_px: int,
    reachable_chest_count: int,
    render_metadata: Mapping[str, Any] | None = None,
) -> RpgDungeonScene:
    """Render an RPG dungeon using resolved canvas-profile parameters."""

    metadata = rpg_dungeon_profile_metadata(render_params)
    if render_metadata:
        metadata.update({str(key): value for key, value in render_metadata.items()})
    return render_rpg_dungeon_scene(
        int(seed),
        width=int(render_params["canvas_width"]),
        height=int(render_params["canvas_height"]),
        tile_px=int(tile_px),
        reachable_chest_count=int(reachable_chest_count),
        render_metadata=metadata,
    )


def draw_rpg_dungeon_debug_overlay(scene: RpgDungeonScene) -> Image.Image:
    """Return an overlay image with chamber, blocker, and entity bboxes."""

    image = scene.image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for chamber in scene.chambers:
        draw.rectangle(chamber.bbox_xyxy, outline=(42, 111, 210, 210), width=3)
    for blocker in scene.blockers:
        draw.rectangle(blocker.bbox_xyxy, outline=(214, 67, 59, 230), width=3)
    for entity in scene.entities:
        color = (38, 152, 91, 235) if entity.entity_id in set(scene.reachable_chest_ids) else (239, 173, 42, 220)
        if entity.entity_id == scene.player_entity_id:
            color = (88, 142, 246, 240)
        draw.rectangle(entity.bbox_xyxy, outline=color, width=2)
    return Image.alpha_composite(image, overlay).convert("RGB")


def _sample_layout(*, width: int, height: int, tile_px: int) -> RpgDungeonLayout:
    resolved_tile_px = max(40, min(56, int(tile_px)))
    cols = max(18, int(round(float(width) / float(resolved_tile_px))))
    rows = max(18, int(round(float(height) / float(resolved_tile_px))))
    grid_w = int(cols) * resolved_tile_px
    grid_h = int(rows) * resolved_tile_px
    return RpgDungeonLayout(
        cols=int(cols),
        rows=int(rows),
        tile_px=int(resolved_tile_px),
        width_px=int(width),
        height_px=int(height),
        display_offset_xy=((int(width) - grid_w) // 2, (int(height) - grid_h) // 2),
    )


def _resolve_reachable_chest_count(rng: random.Random, reachable_chest_count: int | None) -> int:
    if reachable_chest_count is None:
        return int(rng.randint(MIN_REACHABLE_CHEST_COUNT, MAX_REACHABLE_CHEST_COUNT))
    value = int(reachable_chest_count)
    if not MIN_REACHABLE_CHEST_COUNT <= value <= MAX_REACHABLE_CHEST_COUNT:
        raise ValueError(
            f"reachable_chest_count must be in [{MIN_REACHABLE_CHEST_COUNT}, {MAX_REACHABLE_CHEST_COUNT}], got {value}"
        )
    return value


def _make_valid_layout_spec(layout: RpgDungeonLayout, *, rng: random.Random, target_count: int) -> _LayoutSpec:
    for attempt in range(80):
        spec = _make_layout_spec(layout, rng=random.Random(rng.randrange(1 << 62) + int(attempt)), target_count=target_count)
        reachable_ids = _reachable_chests_for_spec(spec)
        if len(reachable_ids) == int(target_count):
            return _replace_reachable_ids(spec, reachable_ids)
    raise ValueError(f"could not construct RPG dungeon with {target_count} reachable chests")


def _make_layout_spec(layout: RpgDungeonLayout, *, rng: random.Random, target_count: int) -> _LayoutSpec:
    """Construct the carved graph while keeping target answer control explicit."""

    chamber_specs = _make_chamber_specs(layout, rng=rng)
    chamber_by_id = {spec.chamber_id: spec for spec in chamber_specs}
    start = chamber_by_id["start"]
    start_tile = _rect_center_tile(start.tile_xywh)
    chest_chambers = tuple(spec for spec in chamber_specs if spec.chamber_id != "start")
    chest_ids = tuple(f"chest_{index:02d}" for index in range(len(chest_chambers)))
    edge_specs = _make_edge_specs(chamber_by_id)

    floor: set[Tile] = set()
    for chamber in chamber_specs:
        floor.update(_rect_tiles(chamber.tile_xywh))
    corridor_tiles: set[Tile] = set()
    chamber_floor_tiles = set(floor)
    for edge in edge_specs:
        floor.update(edge.path)
        corridor_tiles.update(tile for tile in edge.path if tile not in chamber_floor_tiles)
    chest_tile_map: dict[str, Tile] = {}
    entity_specs: list[_EntitySpec] = [
        _player_spec(start_tile),
    ]
    for index, chamber in enumerate(chest_chambers):
        chest_id = chest_ids[index]
        chest_box = _centered_box(chamber.tile_xywh, width_tiles=2, height_tiles=1)
        chest_tile_map[chest_id] = _rect_center_tile(chest_box)
        entity_specs.append(
            _EntitySpec(
                entity_id=chest_id,
                object_type="chest",
                public_name="treasure chest",
                chamber_id=chamber.chamber_id,
                tile_xywh=chest_box,
                role="queryable",
                visual={
                    "wood_rgb": _choose(rng, ((126, 71, 39), (149, 84, 41), (116, 76, 48))),
                    "metal_rgb": _choose(rng, ((218, 171, 67), (198, 181, 96), (216, 142, 76))),
                },
            )
        )

    blockers, blocked_edge_ids, reachable_chest_ids = _select_blocked_edge_config(
        rng=rng,
        target_count=int(target_count),
        chamber_by_id=chamber_by_id,
        edge_specs=edge_specs,
        floor_tiles=floor,
        start_tile=start_tile,
        chest_tile_map=chest_tile_map,
    )
    blocked_tiles = tuple(sorted({blocker.tile_xy for blocker in blockers}, key=lambda tile: (tile[1], tile[0])))
    return _LayoutSpec(
        chambers=tuple(chamber_specs),
        edge_specs=tuple(edge_specs),
        floor_tiles=tuple(sorted(floor, key=lambda tile: (tile[1], tile[0]))),
        corridor_tiles=tuple(sorted(corridor_tiles, key=lambda tile: (tile[1], tile[0]))),
        blocked_tiles=blocked_tiles,
        blocked_edge_ids=tuple(sorted(blocked_edge_ids)),
        blocker_specs=tuple(blockers),
        entity_specs=tuple(entity_specs),
        player_tile=start_tile,
        chest_tile_map=chest_tile_map,
        reachable_chest_ids=tuple(str(entity_id) for entity_id in sorted(reachable_chest_ids)),
    )


def _replace_reachable_ids(spec: _LayoutSpec, reachable_ids: Sequence[str]) -> _LayoutSpec:
    return _LayoutSpec(
        chambers=spec.chambers,
        edge_specs=spec.edge_specs,
        floor_tiles=spec.floor_tiles,
        corridor_tiles=spec.corridor_tiles,
        blocked_tiles=spec.blocked_tiles,
        blocked_edge_ids=spec.blocked_edge_ids,
        blocker_specs=spec.blocker_specs,
        entity_specs=spec.entity_specs,
        player_tile=spec.player_tile,
        chest_tile_map=spec.chest_tile_map,
        reachable_chest_ids=tuple(sorted(str(entity_id) for entity_id in reachable_ids)),
    )


def _reachable_chests_for_spec(spec: _LayoutSpec) -> tuple[str, ...]:
    reached = reachable_tiles(spec.floor_tiles, blocked_tiles=spec.blocked_tiles, start_tile=spec.player_tile)
    return reachable_entity_ids(entity_tile_map=dict(spec.chest_tile_map), reachable_tile_set=reached)


def _make_chamber_specs(layout: RpgDungeonLayout, *, rng: random.Random) -> tuple[_ChamberSpec, ...]:
    room_w = 4
    room_h = 4
    start_x = int(layout.cols // 2) - 2
    start_y = int(layout.rows // 2) - 2
    jitter_top = int(rng.choice((0, 1)))
    jitter_bottom = int(rng.choice((0, 1)))
    top_y = 1 + jitter_top
    bottom_y = int(layout.rows) - room_h - 1 - jitter_bottom
    left_x = 1 + int(rng.choice((0, 1)))
    right_x = int(layout.cols) - room_w - 1 - int(rng.choice((0, 1)))
    middle_x = max(left_x + room_w + 2, min(right_x - room_w - 2, int(layout.cols // 2) - 2 + int(rng.choice((-1, 0, 1)))))
    return (
        _ChamberSpec("start", "starting chamber", (start_x, start_y, 4, 4)),
        _ChamberSpec("northwest_chamber", "northwest chest chamber", (left_x, top_y, room_w, room_h)),
        _ChamberSpec("north_chamber", "north chest chamber", (middle_x, top_y, room_w, room_h)),
        _ChamberSpec("northeast_chamber", "northeast chest chamber", (right_x, top_y, room_w, room_h)),
        _ChamberSpec("southwest_chamber", "southwest chest chamber", (left_x, bottom_y, room_w, room_h)),
        _ChamberSpec("southeast_chamber", "southeast chest chamber", (right_x, bottom_y, room_w, room_h)),
    )


def _branch_path(start_tile: Tile, target_tile: Tile, *, chamber_id: str) -> tuple[Tile, ...]:
    sx, sy = start_tile
    tx, ty = target_tile
    path: list[Tile] = []
    if chamber_id == "north_chamber":
        _append_vertical(path, sx, sy, ty)
        _append_horizontal(path, ty, sx, tx)
    else:
        _append_horizontal(path, sy, sx, tx)
        _append_vertical(path, tx, sy, ty)
    return tuple(dict.fromkeys(path))


def _make_edge_specs(chamber_by_id: Mapping[str, _ChamberSpec]) -> tuple[_EdgeSpec, ...]:
    """Return room-to-room graph edges used by reachability and blocker placement."""

    edge_pairs = (
        ("start", "northwest_chamber"),
        ("start", "north_chamber"),
        ("start", "northeast_chamber"),
        ("start", "southwest_chamber"),
        ("start", "southeast_chamber"),
        ("northwest_chamber", "north_chamber"),
        ("north_chamber", "northeast_chamber"),
        ("southwest_chamber", "southeast_chamber"),
    )
    edges: list[_EdgeSpec] = []
    for source_id, target_id in edge_pairs:
        source = chamber_by_id[source_id]
        target = chamber_by_id[target_id]
        source_tile = _rect_center_tile(source.tile_xywh)
        target_tile = _rect_center_tile(target.tile_xywh)
        if source_id == "start":
            path = _branch_path(source_tile, target_tile, chamber_id=target_id)
        else:
            path = _straight_path(source_tile, target_tile)
        edge_id = f"edge_{source_id}_{target_id}"
        edges.append(
            _EdgeSpec(
                edge_id=edge_id,
                source_chamber_id=source_id,
                target_chamber_id=target_id,
                path=path,
            )
        )
    return tuple(edges)


def _straight_path(source_tile: Tile, target_tile: Tile) -> tuple[Tile, ...]:
    sx, sy = source_tile
    tx, ty = target_tile
    path: list[Tile] = []
    if int(sy) == int(ty):
        _append_horizontal(path, sy, sx, tx)
    elif int(sx) == int(tx):
        _append_vertical(path, sx, sy, ty)
    else:
        _append_horizontal(path, sy, sx, tx)
        _append_vertical(path, tx, sy, ty)
    return tuple(dict.fromkeys(path))


def _append_horizontal(path: list[Tile], y: int, x0: int, x1: int) -> None:
    step = 1 if int(x1) >= int(x0) else -1
    for x in range(int(x0), int(x1) + step, step):
        path.append((int(x), int(y)))


def _append_vertical(path: list[Tile], x: int, y0: int, y1: int) -> None:
    step = 1 if int(y1) >= int(y0) else -1
    for y in range(int(y0), int(y1) + step, step):
        path.append((int(x), int(y)))


def _select_blocked_edge_config(
    *,
    rng: random.Random,
    target_count: int,
    chamber_by_id: Mapping[str, _ChamberSpec],
    edge_specs: Sequence[_EdgeSpec],
    floor_tiles: set[Tile],
    start_tile: Tile,
    chest_tile_map: Mapping[str, Tile],
) -> tuple[tuple[_BlockerSpec, ...], tuple[str, ...], tuple[str, ...]]:
    """Choose visible blockers whose tile graph yields exactly the requested count."""

    eligible_edges: list[tuple[_EdgeSpec, Tile, str]] = []
    for edge in edge_specs:
        blocker_tile = _blocker_tile_for_edge(edge, chamber_by_id=chamber_by_id)
        if blocker_tile is None:
            continue
        eligible_edges.append((edge, blocker_tile, _blocker_orientation(edge.path, blocker_tile)))

    matching_configs: list[tuple[tuple[tuple[_EdgeSpec, Tile, str], ...], tuple[str, ...]]] = []
    for mask in range(1 << len(eligible_edges)):
        blocked_tiles: set[Tile] = set()
        selected: list[tuple[_EdgeSpec, Tile, str]] = []
        duplicate_tile = False
        for index, edge_blocker in enumerate(eligible_edges):
            if not (mask & (1 << index)):
                continue
            edge, blocker_tile, _orientation = edge_blocker
            if blocker_tile in blocked_tiles:
                duplicate_tile = True
                break
            blocked_tiles.add(blocker_tile)
            selected.append((edge, blocker_tile, _orientation))
        if duplicate_tile:
            continue
        reached = reachable_tiles(floor_tiles, blocked_tiles=blocked_tiles, start_tile=start_tile)
        reachable_ids = reachable_entity_ids(entity_tile_map=dict(chest_tile_map), reachable_tile_set=reached)
        if len(reachable_ids) == int(target_count):
            matching_configs.append((tuple(selected), tuple(reachable_ids)))

    if not matching_configs:
        raise ValueError(f"no RPG dungeon blocker graph produced {target_count} reachable chests")

    min_blockers = min(len(selected) for selected, _reachable_ids in matching_configs)
    compact_configs = [
        config
        for config in matching_configs
        if len(config[0]) <= min_blockers + (0 if int(target_count) in {0, TOTAL_CHEST_COUNT} else 1)
    ]
    selected_edges, reachable_ids = _choose(rng, compact_configs)
    blocker_specs: list[_BlockerSpec] = []
    for index, (edge, blocker_tile, orientation) in enumerate(sorted(selected_edges, key=lambda item: item[0].edge_id)):
        blocker_specs.append(
            _BlockerSpec(
                blocker_id=f"blocker_{index:02d}",
                edge_id=str(edge.edge_id),
                blocker_type=_choose(rng, ("sealed_door", "sealed_door", "boulder")),
                tile_xy=blocker_tile,
                orientation=orientation,
            )
        )
    return (
        tuple(blocker_specs),
        tuple(str(blocker.edge_id) for blocker in blocker_specs),
        tuple(str(entity_id) for entity_id in reachable_ids),
    )


def _blocker_tile_for_edge(edge: _EdgeSpec, *, chamber_by_id: Mapping[str, _ChamberSpec]) -> Tile | None:
    source_tiles = set(_rect_tiles(chamber_by_id[edge.source_chamber_id].tile_xywh))
    target_tiles = set(_rect_tiles(chamber_by_id[edge.target_chamber_id].tile_xywh))
    candidates = [
        (index, tile)
        for index, tile in enumerate(edge.path)
        if tile not in source_tiles and tile not in target_tiles
    ]
    if not candidates:
        return None
    return candidates[len(candidates) // 2][1]


def _blocker_orientation(path: Sequence[Tile], tile: Tile) -> str:
    tiles = list(path)
    try:
        index = tiles.index(tile)
    except ValueError:
        return "horizontal"
    prev_tile = tiles[max(0, index - 1)]
    next_tile = tiles[min(len(tiles) - 1, index + 1)]
    if prev_tile[0] == next_tile[0]:
        return "horizontal"
    return "vertical"


def _player_spec(start_tile: Tile) -> _EntitySpec:
    return _EntitySpec(
        entity_id="player_00",
        object_type="person",
        public_name="player",
        chamber_id="start",
        tile_xywh=(int(start_tile[0]), int(start_tile[1]), 1, 1),
        role="reference",
        visual={
            "role": "player_marker",
            "person_variant_id": "soldier",
            "gender_id": "male",
            "facing": "down",
            "shirt_rgb": (63, 113, 197),
            "pants_rgb": (43, 58, 91),
            "hair_rgb": (61, 44, 34),
        },
    )


def _render_base(
    layout: RpgDungeonLayout,
    *,
    layout_spec: _LayoutSpec,
    theme: Mapping[str, Any],
    rng: random.Random,
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (layout.canonical_width_px, layout.canonical_height_px), _rgba(theme["background_rgb"]))
    draw = ImageDraw.Draw(image)
    _draw_background_stone(draw, layout, theme=theme, rng=rng)
    floor = set(layout_spec.floor_tiles)
    for tile in sorted(floor, key=lambda item: (item[1], item[0])):
        _draw_floor_tile(draw, tile, theme=theme)
    _draw_wall_edges(draw, floor_tiles=floor, theme=theme)
    return image, draw


def _draw_background_stone(
    draw: ImageDraw.ImageDraw,
    layout: RpgDungeonLayout,
    *,
    theme: Mapping[str, Any],
    rng: random.Random,
) -> None:
    bg = theme["background_rgb"]
    for y in range(0, layout.canonical_height_px, CANONICAL_TILE_PX):
        for x in range(0, layout.canonical_width_px, CANONICAL_TILE_PX):
            delta = int(rng.choice((-6, -3, 0, 3)))
            draw.rectangle(
                (x, y, x + CANONICAL_TILE_PX - 1, y + CANONICAL_TILE_PX - 1),
                fill=_rgba(_shade(bg, delta)),
            )
            if rng.random() < 0.18:
                draw.line((x + 2, y + 3, x + 12, y + 3), fill=_rgba(_shade(bg, 18), 80))


def _draw_floor_tile(draw: ImageDraw.ImageDraw, tile: Tile, *, theme: Mapping[str, Any]) -> None:
    x, y = tile
    x0 = int(x) * CANONICAL_TILE_PX
    y0 = int(y) * CANONICAL_TILE_PX
    fill = theme["floor_rgb"] if (int(x) + int(y)) % 2 == 0 else theme["floor_alt_rgb"]
    draw.rectangle((x0, y0, x0 + 15, y0 + 15), fill=_rgba(fill))
    draw.rectangle((x0, y0, x0 + 15, y0 + 15), outline=_rgba(theme["floor_line_rgb"], 95))
    if (int(x) * 17 + int(y) * 31) % 7 == 0:
        draw.line((x0 + 3, y0 + 9, x0 + 12, y0 + 11), fill=_rgba(_shade(fill, -32), 120))


def _draw_wall_edges(draw: ImageDraw.ImageDraw, *, floor_tiles: set[Tile], theme: Mapping[str, Any]) -> None:
    edge = theme["wall_edge_rgb"]
    light = theme["wall_light_rgb"]
    for x, y in floor_tiles:
        x0 = int(x) * CANONICAL_TILE_PX
        y0 = int(y) * CANONICAL_TILE_PX
        if (x, y - 1) not in floor_tiles:
            draw.rectangle((x0, y0 - 2, x0 + 15, y0 + 2), fill=_rgba(edge))
            draw.line((x0 + 1, y0 + 2, x0 + 14, y0 + 2), fill=_rgba(light, 120))
        if (x, y + 1) not in floor_tiles:
            draw.rectangle((x0, y0 + 13, x0 + 15, y0 + 17), fill=_rgba(edge))
        if (x - 1, y) not in floor_tiles:
            draw.rectangle((x0 - 2, y0, x0 + 2, y0 + 15), fill=_rgba(edge))
            draw.line((x0 + 2, y0 + 1, x0 + 2, y0 + 14), fill=_rgba(light, 95))
        if (x + 1, y) not in floor_tiles:
            draw.rectangle((x0 + 13, y0, x0 + 17, y0 + 15), fill=_rgba(edge))


def _render_entities(
    draw: ImageDraw.ImageDraw,
    *,
    entity_specs: Sequence[_EntitySpec],
    layout: RpgDungeonLayout,
    theme: Mapping[str, Any],
    theme_id: str,
) -> list[RpgDungeonEntity]:
    """Draw entities on canonical tiles while storing final pixel bboxes."""

    entities: list[RpgDungeonEntity] = []
    for spec in entity_specs:
        bbox = _tile_bbox(layout, spec.tile_xywh)
        visual = {"theme_id": theme_id, "renderer_style": RENDERER_STYLE_TOP_DOWN_PIXEL_RPG}
        if spec.object_type == "chest":
            visual.update({"wood_rgb": theme["chest_wood_rgb"], "metal_rgb": theme["chest_metal_rgb"]})
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
                semantic_attributes={
                    "chamber_id": spec.chamber_id,
                    "role": spec.role,
                    "layout_context": str(spec.role) == "context",
                },
                visual_attributes=visual,
                role=spec.role,
                source_entity_type="rpg_dungeon_entity",
            ),
            RenderContext(renderer_style=RENDERER_STYLE_TOP_DOWN_PIXEL_RPG, draw=draw),
        )
        point = ((bbox[0] + bbox[2]) * 0.5, (bbox[1] + bbox[3]) * 0.5)
        entities.append(
            RpgDungeonEntity(
                entity_id=spec.entity_id,
                public_name=spec.public_name,
                object_type=spec.object_type,
                chamber_id=spec.chamber_id,
                tile_xywh=spec.tile_xywh,
                bbox_xyxy=bbox,
                point_xy=point,
                role=spec.role,
                metadata={"visual_attributes": visual, "object_record": rendered.object_record},
            )
        )
    return entities


def _render_blockers(
    draw: ImageDraw.ImageDraw,
    *,
    blocker_specs: Sequence[_BlockerSpec],
    layout: RpgDungeonLayout,
    theme: Mapping[str, Any],
    theme_id: str,
) -> list[RpgDungeonBlocker]:
    """Draw impassable blockers and serialize their graph-blocking tiles."""

    blockers: list[RpgDungeonBlocker] = []
    for spec in blocker_specs:
        tile_xywh = (int(spec.tile_xy[0]), int(spec.tile_xy[1]), 1, 1)
        bbox = _tile_bbox(layout, tile_xywh)
        visual: dict[str, Any] = {
            "theme_id": theme_id,
            "renderer_style": RENDERER_STYLE_TOP_DOWN_PIXEL_RPG,
            "door_orientation": spec.orientation,
            "contrast": "high",
        }
        _draw_dungeon_blocker(draw, spec, theme=theme)
        point = ((bbox[0] + bbox[2]) * 0.5, (bbox[1] + bbox[3]) * 0.5)
        blockers.append(
            RpgDungeonBlocker(
                blocker_id=spec.blocker_id,
                blocker_type=spec.blocker_type,
                tile_xy=spec.tile_xy,
                tile_xywh=tile_xywh,
                bbox_xyxy=bbox,
                point_xy=point,
                metadata={
                    "passable": False,
                    "edge_id": spec.edge_id,
                    "orientation": spec.orientation,
                    "visual_attributes": visual,
                },
            )
        )
    return blockers


def _draw_dungeon_blocker(draw: ImageDraw.ImageDraw, spec: _BlockerSpec, *, theme: Mapping[str, Any]) -> None:
    if spec.blocker_type == "sealed_door":
        _draw_one_tile_sealed_door(draw, spec.tile_xy, orientation=spec.orientation)
    else:
        _draw_one_tile_boulder(draw, spec.tile_xy, floor_rgb=theme["floor_rgb"])


def _draw_one_tile_sealed_door(draw: ImageDraw.ImageDraw, tile: Tile, *, orientation: str) -> None:
    x, y = tile
    x0 = int(x) * CANONICAL_TILE_PX
    y0 = int(y) * CANONICAL_TILE_PX
    outline = (32, 35, 40)
    panel = (229, 221, 183)
    shade = (142, 126, 91)
    strap = (62, 75, 96)
    seal = (238, 183, 55)
    draw.rectangle((x0 + 2, y0 + 2, x0 + 13, y0 + 13), fill=_rgba((30, 31, 33), 70))
    if str(orientation) == "horizontal":
        draw.rounded_rectangle((x0 + 1, y0 + 4, x0 + 14, y0 + 11), radius=2, fill=_rgba(panel), outline=_rgba(outline), width=1)
        draw.line((x0 + 2, y0 + 6, x0 + 13, y0 + 6), fill=_rgba(shade))
        draw.line((x0 + 2, y0 + 9, x0 + 13, y0 + 9), fill=_rgba(shade))
        draw.rectangle((x0 + 6, y0 + 4, x0 + 9, y0 + 11), fill=_rgba(strap))
        draw.rectangle((x0 + 7, y0 + 6, x0 + 8, y0 + 8), fill=_rgba(seal))
    else:
        draw.rounded_rectangle((x0 + 4, y0 + 1, x0 + 11, y0 + 14), radius=2, fill=_rgba(panel), outline=_rgba(outline), width=1)
        draw.line((x0 + 6, y0 + 2, x0 + 6, y0 + 13), fill=_rgba(shade))
        draw.line((x0 + 9, y0 + 2, x0 + 9, y0 + 13), fill=_rgba(shade))
        draw.rectangle((x0 + 4, y0 + 6, x0 + 11, y0 + 9), fill=_rgba(strap))
        draw.rectangle((x0 + 7, y0 + 7, x0 + 8, y0 + 8), fill=_rgba(seal))


def _draw_one_tile_boulder(draw: ImageDraw.ImageDraw, tile: Tile, *, floor_rgb: Any) -> None:
    x, y = tile
    x0 = int(x) * CANONICAL_TILE_PX
    y0 = int(y) * CANONICAL_TILE_PX
    outline = (35, 39, 37)
    fill = (217, 223, 216)
    shadow = _shade(floor_rgb, -40)
    facet = (134, 146, 137)
    highlight = (242, 244, 238)
    draw.ellipse((x0 + 2, y0 + 4, x0 + 14, y0 + 14), fill=_rgba(shadow, 150))
    draw.polygon(
        (
            (x0 + 3, y0 + 5),
            (x0 + 6, y0 + 2),
            (x0 + 11, y0 + 3),
            (x0 + 14, y0 + 7),
            (x0 + 12, y0 + 13),
            (x0 + 5, y0 + 14),
            (x0 + 2, y0 + 10),
        ),
        fill=_rgba(fill),
        outline=_rgba(outline),
    )
    draw.line((x0 + 6, y0 + 3, x0 + 8, y0 + 8, x0 + 4, y0 + 11), fill=_rgba(facet))
    draw.line((x0 + 9, y0 + 4, x0 + 12, y0 + 8, x0 + 10, y0 + 12), fill=_rgba(facet))
    draw.line((x0 + 5, y0 + 5, x0 + 9, y0 + 4), fill=_rgba(highlight))


def _tile_bbox(layout: RpgDungeonLayout, tile_xywh: TileBox) -> BBox:
    x, y, w, h = tile_xywh
    ox, oy = layout.display_offset_xy
    return _clip_bbox(
        (
            float(ox + int(x) * int(layout.tile_px)),
            float(oy + int(y) * int(layout.tile_px)),
            float(ox + (int(x) + int(w)) * int(layout.tile_px)),
            float(oy + (int(y) + int(h)) * int(layout.tile_px)),
        ),
        width=int(layout.width_px),
        height=int(layout.height_px),
    )


def _clip_bbox(bbox: BBox, *, width: int, height: int) -> BBox:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    clipped = (
        max(0.0, min(float(width), x0)),
        max(0.0, min(float(height), y0)),
        max(0.0, min(float(width), x1)),
        max(0.0, min(float(height), y1)),
    )
    if clipped[0] >= clipped[2] or clipped[1] >= clipped[3]:
        raise ValueError(f"RPG dungeon bbox clipped outside the canvas: {bbox}")
    return clipped


def _rect_tiles(tile_xywh: TileBox) -> tuple[Tile, ...]:
    x, y, w, h = tile_xywh
    return tuple(
        (int(xx), int(yy))
        for yy in range(int(y), int(y) + int(h))
        for xx in range(int(x), int(x) + int(w))
    )


def _rect_center_tile(tile_xywh: TileBox) -> Tile:
    x, y, w, h = tile_xywh
    return (int(x) + int(w) // 2, int(y) + int(h) // 2)


def _centered_box(container: TileBox, *, width_tiles: int, height_tiles: int) -> TileBox:
    x, y, w, h = container
    box_w = min(int(width_tiles), max(1, int(w) - 2))
    box_h = min(int(height_tiles), max(1, int(h) - 2))
    return (
        int(x) + max(1, (int(w) - box_w) // 2),
        int(y) + max(1, (int(h) - box_h) // 2),
        int(box_w),
        int(box_h),
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
    "MAX_REACHABLE_CHEST_COUNT",
    "MIN_REACHABLE_CHEST_COUNT",
    "RENDERER_ID",
    "SCENE_ID",
    "THEMES",
    "TOTAL_CHEST_COUNT",
    "draw_rpg_dungeon_debug_overlay",
    "render_rpg_dungeon_profile_scene",
    "render_rpg_dungeon_scene",
    "rpg_dungeon_profile_metadata",
]
