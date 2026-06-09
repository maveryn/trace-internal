"""Shared rules and symbolic helpers for Sixteen Soldiers scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Tuple


EMPTY = 0
RED = 1
BLUE = 2
Coord = Tuple[int, int]
PointId = str
Board = Tuple[Tuple[PointId, int], ...]

SUPPORTED_SIXTEEN_SOLDIERS_QUERY_IDS: Tuple[str, ...] = (
    "marked_piece_destination_count",
    "marked_piece_capture_count",
)
SUPPORTED_SIXTEEN_SOLDIERS_SCENE_VARIANTS: Tuple[str, ...] = (
    "balanced_midgame",
    "center_crossroads_midgame",
    "triangle_wing_midgame",
)
SUPPORTED_SIXTEEN_SOLDIERS_STYLE_VARIANTS: Tuple[str, ...] = (
    "ground_court",
    "ink_court",
    "cloth_board",
    "slate_court",
    "sand_court",
)


@dataclass(frozen=True)
class JumpSpec:
    """One directed jump line: origin -> adjacent opponent -> empty landing."""

    origin_id: PointId
    middle_id: PointId
    landing_id: PointId


@dataclass(frozen=True)
class SixteenSoldiersSample:
    """One symbolic Sixteen Soldiers board plus query witnesses."""

    query_id: str
    scene_variant: str
    style_variant: str
    board: Board
    answer: int
    target_answer: int
    annotation_point_ids: Tuple[PointId, ...]
    target_color: int
    marked_point_id: PointId
    construction_mode: str


def _valid_point_coords() -> Tuple[Coord, ...]:
    """Return the canonical 37-point Sixteen Soldiers board coordinates."""

    coords: list[Coord] = []
    coords.extend(((0, 0), (0, 2), (0, 4)))
    coords.extend(((1, 1), (1, 2), (1, 3)))
    for row in range(2, 7):
        coords.extend((row, col) for col in range(5))
    coords.extend(((7, 1), (7, 2), (7, 3)))
    coords.extend(((8, 0), (8, 2), (8, 4)))
    return tuple(coords)


POINT_COORDS: Tuple[Coord, ...] = _valid_point_coords()
COORD_TO_POINT_ID: dict[Coord, PointId] = {coord: f"point_r{coord[0]}_c{coord[1]}" for coord in POINT_COORDS}
POINT_ID_TO_COORD: dict[PointId, Coord] = {point_id: coord for coord, point_id in COORD_TO_POINT_ID.items()}


def _point_sort_key(point_id: PointId) -> Tuple[int, int]:
    """Return row-major ordering key for one point id."""

    coord = POINT_ID_TO_COORD[str(point_id)]
    return (int(coord[0]), int(coord[1]))


def _edge_key(a: Coord, b: Coord) -> Tuple[PointId, PointId]:
    """Return one sorted undirected edge key."""

    pa = COORD_TO_POINT_ID[a]
    pb = COORD_TO_POINT_ID[b]
    return tuple(sorted((pa, pb), key=_point_sort_key))  # type: ignore[return-value]


def _build_edges() -> Tuple[Tuple[PointId, PointId], ...]:
    """Build the fixed alquerque-plus-two-triangles graph."""

    edges: set[Tuple[PointId, PointId]] = set()

    def add(a: Coord, b: Coord) -> None:
        if a not in COORD_TO_POINT_ID or b not in COORD_TO_POINT_ID:
            raise ValueError(f"invalid Sixteen Soldiers edge: {a!r}->{b!r}")
        edges.add(_edge_key(a, b))

    # Central 5 by 5 alquerque board.
    for row in range(2, 7):
        for col in range(4):
            add((row, col), (row, col + 1))
    for row in range(2, 6):
        for col in range(5):
            add((row, col), (row + 1, col))
    for row in range(2, 6):
        for col in range(5):
            if (row + col) % 2 != 0:
                continue
            for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
                candidate = (row + dr, col + dc)
                if 2 <= candidate[0] <= 6 and 0 <= candidate[1] <= 4:
                    add((row, col), candidate)

    # Top triangular extension.
    for edge in (
        ((0, 0), (0, 2)),
        ((0, 2), (0, 4)),
        ((1, 1), (1, 2)),
        ((1, 2), (1, 3)),
        ((0, 2), (1, 2)),
        ((1, 2), (2, 2)),
        ((0, 0), (1, 1)),
        ((1, 1), (2, 2)),
        ((0, 4), (1, 3)),
        ((1, 3), (2, 2)),
    ):
        add(*edge)

    # Bottom triangular extension.
    for edge in (
        ((8, 0), (8, 2)),
        ((8, 2), (8, 4)),
        ((7, 1), (7, 2)),
        ((7, 2), (7, 3)),
        ((6, 2), (7, 2)),
        ((7, 2), (8, 2)),
        ((6, 2), (7, 1)),
        ((7, 1), (8, 0)),
        ((6, 2), (7, 3)),
        ((7, 3), (8, 4)),
    ):
        add(*edge)

    return tuple(sorted(edges, key=lambda edge: (_point_sort_key(edge[0]), _point_sort_key(edge[1]))))


EDGES: Tuple[Tuple[PointId, PointId], ...] = _build_edges()


def _build_neighbors() -> dict[PointId, Tuple[PointId, ...]]:
    """Return sorted neighbors for every point."""

    neighbors: dict[PointId, set[PointId]] = {point_id: set() for point_id in POINT_ID_TO_COORD}
    for a, b in EDGES:
        neighbors[a].add(b)
        neighbors[b].add(a)
    return {
        point_id: tuple(sorted(values, key=_point_sort_key))
        for point_id, values in sorted(neighbors.items(), key=lambda item: _point_sort_key(item[0]))
    }


NEIGHBORS: dict[PointId, Tuple[PointId, ...]] = _build_neighbors()


def _build_jump_specs() -> Tuple[JumpSpec, ...]:
    """Return all directed two-edge straight-line jump specs."""

    edge_set = {frozenset((a, b)) for a, b in EDGES}
    specs: list[JumpSpec] = []
    for origin_id in POINT_ID_TO_COORD:
        row0, col0 = POINT_ID_TO_COORD[origin_id]
        for middle_id in NEIGHBORS[origin_id]:
            row1, col1 = POINT_ID_TO_COORD[middle_id]
            landing_coord = (int(row1 + (row1 - row0)), int(col1 + (col1 - col0)))
            landing_id = COORD_TO_POINT_ID.get(landing_coord)
            if landing_id is None:
                continue
            if frozenset((middle_id, landing_id)) not in edge_set:
                continue
            specs.append(
                JumpSpec(
                    origin_id=str(origin_id),
                    middle_id=str(middle_id),
                    landing_id=str(landing_id),
                )
            )
    return tuple(
        sorted(
            specs,
            key=lambda spec: (
                _point_sort_key(spec.origin_id),
                _point_sort_key(spec.middle_id),
                _point_sort_key(spec.landing_id),
            ),
        )
    )


JUMP_SPECS: Tuple[JumpSpec, ...] = _build_jump_specs()


def all_point_ids() -> Tuple[PointId, ...]:
    """Return all board point ids in visual row-major order."""

    return tuple(COORD_TO_POINT_ID[coord] for coord in POINT_COORDS)


def point_id_from_coord(coord: Coord) -> PointId:
    """Return a stable trace id for one board point."""

    return COORD_TO_POINT_ID[(int(coord[0]), int(coord[1]))]


def point_coord(point_id: PointId) -> Coord:
    """Return symbolic coordinates for one point id."""

    return POINT_ID_TO_COORD[str(point_id)]


def piece_to_entity_id(point_id: PointId) -> str:
    """Return a stable trace id for one piece occupying a point."""

    return f"piece_{str(point_id)}"


def player_name(value: int) -> str:
    """Return prompt-facing player color name."""

    return "red" if int(value) == int(RED) else "blue"


def opponent(value: int) -> int:
    """Return the opposite player value."""

    return BLUE if int(value) == int(RED) else RED


def freeze_board(values: Mapping[PointId, int]) -> Board:
    """Freeze a point-value mapping into the canonical board representation."""

    missing = set(all_point_ids()) - {str(key) for key in values}
    extra = {str(key) for key in values} - set(all_point_ids())
    if missing:
        raise ValueError(f"Sixteen Soldiers board is missing points: {sorted(missing)!r}")
    if extra:
        raise ValueError(f"Sixteen Soldiers board has invalid points: {sorted(extra)!r}")
    frozen: list[Tuple[PointId, int]] = []
    for point_id in all_point_ids():
        value = int(values[str(point_id)])
        if value not in {EMPTY, RED, BLUE}:
            raise ValueError(f"unsupported Sixteen Soldiers point value: {value!r}")
        frozen.append((str(point_id), int(value)))
    return tuple(frozen)


def board_to_dict(board: Board) -> dict[PointId, int]:
    """Return a mutable dictionary for a frozen board."""

    return {str(point_id): int(value) for point_id, value in freeze_board(dict(board))}


def legal_destinations(board: Board, point_id: PointId) -> Tuple[PointId, ...]:
    """Return empty neighboring points connected by a drawn line."""

    values = board_to_dict(board)
    origin_id = str(point_id)
    if values[origin_id] == EMPTY:
        return tuple()
    return tuple(
        neighbor_id
        for neighbor_id in NEIGHBORS[origin_id]
        if values[str(neighbor_id)] == EMPTY
    )


def jump_specs_from(point_id: PointId) -> Tuple[JumpSpec, ...]:
    """Return directed jump specs whose origin is one point."""

    origin_id = str(point_id)
    return tuple(spec for spec in JUMP_SPECS if spec.origin_id == origin_id)


def capturable_opponent_points(board: Board, point_id: PointId) -> Tuple[PointId, ...]:
    """Return opponent pieces immediately capturable by one occupied point."""

    values = board_to_dict(board)
    origin_id = str(point_id)
    origin_value = int(values[origin_id])
    if origin_value == EMPTY:
        return tuple()
    opponent_value = opponent(origin_value)
    out: set[PointId] = set()
    for spec in jump_specs_from(origin_id):
        if int(values[spec.middle_id]) != int(opponent_value):
            continue
        if int(values[spec.landing_id]) != EMPTY:
            continue
        out.add(str(spec.middle_id))
    return tuple(sorted(out, key=_point_sort_key))


def capture_lines(board: Board, point_id: PointId) -> Tuple[dict[str, PointId], ...]:
    """Return full capture witnesses for trace metadata."""

    values = board_to_dict(board)
    origin_id = str(point_id)
    origin_value = int(values[origin_id])
    if origin_value == EMPTY:
        return tuple()
    opponent_value = opponent(origin_value)
    out: list[dict[str, PointId]] = []
    seen: set[Tuple[PointId, PointId]] = set()
    for spec in jump_specs_from(origin_id):
        if int(values[spec.middle_id]) != int(opponent_value):
            continue
        if int(values[spec.landing_id]) != EMPTY:
            continue
        key = (str(spec.middle_id), str(spec.landing_id))
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "opponent_piece_point_id": str(spec.middle_id),
                "landing_point_id": str(spec.landing_id),
            }
        )
    return tuple(sorted(out, key=lambda item: (_point_sort_key(item["opponent_piece_point_id"]), _point_sort_key(item["landing_point_id"]))))


def board_piece_count(board: Board, player: int) -> int:
    """Count pieces for one player."""

    return sum(1 for _point_id, value in freeze_board(dict(board)) if int(value) == int(player))


def validate_sixteen_soldiers_sample(sample: SixteenSoldiersSample) -> None:
    """Validate answer/annotation consistency for one sampled scene."""

    board = freeze_board(dict(sample.board))
    values = board_to_dict(board)
    if str(sample.marked_point_id) not in values:
        raise ValueError("marked point id is not on the Sixteen Soldiers board")
    if int(values[str(sample.marked_point_id)]) not in {RED, BLUE}:
        raise ValueError("marked point must contain a piece")
    if str(sample.query_id) == "marked_piece_destination_count":
        expected = tuple(sorted(legal_destinations(board, sample.marked_point_id), key=_point_sort_key))
    elif str(sample.query_id) == "marked_piece_capture_count":
        expected = tuple(sorted(capturable_opponent_points(board, sample.marked_point_id), key=_point_sort_key))
    else:
        raise ValueError(f"unsupported Sixteen Soldiers query_id={sample.query_id!r}")
    if tuple(sorted(sample.annotation_point_ids, key=_point_sort_key)) != expected:
        raise ValueError("Sixteen Soldiers annotation points do not match board rules")
    if int(sample.answer) != len(expected):
        raise ValueError("Sixteen Soldiers answer does not match annotation count")


def visible_board_trace(board: Board) -> list[dict[str, Any]]:
    """Return compact symbolic board rows for trace/debugging."""

    values = board_to_dict(board)
    rows: list[dict[str, Any]] = []
    for row in range(9):
        row_points = [coord for coord in POINT_COORDS if int(coord[0]) == int(row)]
        if not row_points:
            continue
        rows.append(
            {
                "row": int(row),
                "points": [
                    {
                        "coord": [int(coord[0]), int(coord[1])],
                        "point_id": point_id_from_coord(coord),
                        "state": "empty"
                        if int(values[point_id_from_coord(coord)]) == EMPTY
                        else "red"
                        if int(values[point_id_from_coord(coord)]) == RED
                        else "blue",
                    }
                    for coord in row_points
                ],
            }
        )
    return rows


__all__ = [
    "BLUE",
    "Board",
    "COORD_TO_POINT_ID",
    "Coord",
    "EDGES",
    "EMPTY",
    "JUMP_SPECS",
    "JumpSpec",
    "NEIGHBORS",
    "POINT_COORDS",
    "POINT_ID_TO_COORD",
    "PointId",
    "RED",
    "SUPPORTED_SIXTEEN_SOLDIERS_QUERY_IDS",
    "SUPPORTED_SIXTEEN_SOLDIERS_SCENE_VARIANTS",
    "SUPPORTED_SIXTEEN_SOLDIERS_STYLE_VARIANTS",
    "SixteenSoldiersSample",
    "all_point_ids",
    "board_piece_count",
    "board_to_dict",
    "capturable_opponent_points",
    "capture_lines",
    "freeze_board",
    "jump_specs_from",
    "legal_destinations",
    "opponent",
    "piece_to_entity_id",
    "player_name",
    "point_coord",
    "point_id_from_coord",
    "validate_sixteen_soldiers_sample",
    "visible_board_trace",
]
