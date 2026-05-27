"""Shared Battleship-grid helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple


Coord = Tuple[int, int]
SUPPORTED_BATTLESHIP_QUERY_VARIANTS: Tuple[str, ...] = ("sunk_ship_count", "partial_ship_count")
SUPPORTED_BATTLESHIP_SCENE_VARIANTS: Tuple[str, ...] = ("standard_fleet",)


@dataclass(frozen=True)
class FleetShapeSpec:
    """One visible fleet shape and its canonical cell offsets."""

    shape_id: str
    display_name: str
    offsets: Tuple[Coord, ...]


@dataclass(frozen=True)
class BattleshipShipPlacement:
    """One placed fleet ship on the Battleship grid."""

    ship_id: str
    shape_id: str
    display_name: str
    coords: Tuple[Coord, ...]
    hit_coords: Tuple[Coord, ...]
    is_sunk: bool


@dataclass(frozen=True)
class BattleshipSample:
    """Generated Battleship tracking-grid state."""

    board_size: int
    query_variant: str
    scene_variant: str
    answer: int
    ship_placements: Tuple[BattleshipShipPlacement, ...]
    hit_coords: Tuple[Coord, ...]
    miss_coords: Tuple[Coord, ...]
    evidence_coords: Tuple[Coord, ...]
    target_answer: int
    sunk_ship_count: int
    partial_ship_count: int
    untouched_ship_count: int
    construction_mode: str


FLEET_SHAPES: Tuple[FleetShapeSpec, ...] = (
    FleetShapeSpec(
        shape_id="line5",
        display_name="Line 5",
        offsets=((0, 0), (0, 1), (0, 2), (0, 3), (0, 4)),
    ),
    FleetShapeSpec(
        shape_id="line4",
        display_name="Line 4",
        offsets=((0, 0), (0, 1), (0, 2), (0, 3)),
    ),
    FleetShapeSpec(
        shape_id="line3",
        display_name="Line 3",
        offsets=((0, 0), (0, 1), (0, 2)),
    ),
    FleetShapeSpec(
        shape_id="line2",
        display_name="Line 2",
        offsets=((0, 0), (0, 1)),
    ),
    FleetShapeSpec(
        shape_id="square4",
        display_name="Square 2x2",
        offsets=((0, 0), (0, 1), (1, 0), (1, 1)),
    ),
    FleetShapeSpec(
        shape_id="elbow3",
        display_name="L 3",
        offsets=((0, 0), (1, 0), (1, 1)),
    ),
)


def coord_to_cell_id(coord: Coord) -> str:
    """Return the stable render/entity id for one Battleship board cell."""

    row, col = coord
    return f"r{int(row)}_c{int(col)}"


def all_coords(size: int) -> Tuple[Coord, ...]:
    """Return all board coordinates in row-major order."""

    return tuple((row, col) for row in range(int(size)) for col in range(int(size)))


def sorted_coords(coords: Iterable[Coord]) -> Tuple[Coord, ...]:
    """Return canonical sorted coordinates."""

    return tuple(sorted((int(row), int(col)) for row, col in coords))


def normalize_offsets(coords: Iterable[Coord]) -> Tuple[Coord, ...]:
    """Normalize a set of shape cells to top-left origin."""

    items = [(int(row), int(col)) for row, col in coords]
    if not items:
        return tuple()
    min_row = min(row for row, _col in items)
    min_col = min(col for _row, col in items)
    return tuple(sorted((row - min_row, col - min_col) for row, col in items))


def shape_orientations(offsets: Sequence[Coord]) -> Tuple[Tuple[Coord, ...], ...]:
    """Return unique right-angle rotations for one fleet shape."""

    base = normalize_offsets(offsets)
    orientations = set()
    current = tuple(base)
    for _ in range(4):
        normalized = normalize_offsets(current)
        orientations.add(normalized)
        current = tuple((col, -row) for row, col in normalized)
    return tuple(sorted(orientations))


def fleet_shape_by_id() -> Dict[str, FleetShapeSpec]:
    """Return fleet shapes keyed by stable id."""

    return {shape.shape_id: shape for shape in FLEET_SHAPES}


def fleet_orientation_lookup() -> Dict[Tuple[Coord, ...], Tuple[str, ...]]:
    """Return normalized shape offsets mapped to matching fleet shape ids."""

    lookup: Dict[Tuple[Coord, ...], list[str]] = {}
    for shape in FLEET_SHAPES:
        for oriented in shape_orientations(shape.offsets):
            lookup.setdefault(oriented, []).append(str(shape.shape_id))
    return {key: tuple(values) for key, values in lookup.items()}


def matching_fleet_shape_ids(coords: Sequence[Coord]) -> Tuple[str, ...]:
    """Return fleet shape ids whose geometry exactly matches the given cells."""

    return fleet_orientation_lookup().get(normalize_offsets(coords), tuple())


def validate_battleship_sample(sample: BattleshipSample) -> None:
    """Validate that the generated answer is unique and geometry-grounded."""

    ship_ids = [ship.ship_id for ship in sample.ship_placements]
    if len(ship_ids) != len(set(ship_ids)):
        raise ValueError("Battleship ship ids must be unique")
    if len(sample.ship_placements) != len(FLEET_SHAPES):
        raise ValueError("Battleship sample must place every fleet ship exactly once")
    expected_shape_ids = {shape.shape_id for shape in FLEET_SHAPES}
    placed_shape_ids = {ship.shape_id for ship in sample.ship_placements}
    if placed_shape_ids != expected_shape_ids:
        raise ValueError("Battleship placed fleet shape ids must match the fleet exactly")

    ship_cells: set[Coord] = set()
    for ship in sample.ship_placements:
        if set(ship.coords) & ship_cells:
            raise ValueError("Battleship ships cannot overlap")
        ship_cells.update(ship.coords)
        if str(ship.shape_id) not in matching_fleet_shape_ids(ship.coords):
            raise ValueError("Battleship ship placement geometry does not match its declared shape")
        hit_subset = set(ship.hit_coords)
        if not hit_subset <= set(ship.coords):
            raise ValueError("Battleship ship hits must be a subset of that ship's cells")
        if bool(ship.is_sunk) != (hit_subset == set(ship.coords)):
            raise ValueError("Battleship sunk flag must mean every ship cell is hit")

    hit_set = set(sample.hit_coords)
    if len(hit_set) != len(sample.hit_coords):
        raise ValueError("Battleship hit coordinates must be unique")
    if not hit_set <= ship_cells:
        raise ValueError("Battleship hits must occur only on placed ship cells")
    if set(sample.miss_coords) & hit_set:
        raise ValueError("Battleship miss coordinates cannot overlap hit coordinates")
    if set(sample.miss_coords) & ship_cells:
        raise ValueError("Battleship misses must occur only on water cells")

    sunk_ships = [ship for ship in sample.ship_placements if bool(ship.is_sunk)]
    partial_ships = [
        ship
        for ship in sample.ship_placements
        if bool(ship.hit_coords) and not bool(ship.is_sunk)
    ]
    untouched_ships = [ship for ship in sample.ship_placements if not bool(ship.hit_coords)]
    if len(sunk_ships) != int(sample.sunk_ship_count):
        raise ValueError("Battleship sunk_ship_count does not equal sunk ships")
    if len(partial_ships) != int(sample.partial_ship_count):
        raise ValueError("Battleship partial_ship_count does not equal partially hit ships")
    if len(untouched_ships) != int(sample.untouched_ship_count):
        raise ValueError("Battleship untouched_ship_count does not equal untouched ships")
    if str(sample.query_variant) == "sunk_ship_count":
        expected_answer = int(sample.sunk_ship_count)
        expected_evidence = {coord for ship in sunk_ships for coord in ship.coords}
    elif str(sample.query_variant) == "partial_ship_count":
        expected_answer = int(sample.partial_ship_count)
        expected_evidence = {coord for ship in partial_ships for coord in ship.coords}
    else:
        raise ValueError(f"unsupported Battleship query_variant: {sample.query_variant}")
    if int(sample.answer) != int(expected_answer):
        raise ValueError("Battleship answer does not match active query count")
    evidence_set = set(sample.evidence_coords)
    if evidence_set != expected_evidence:
        raise ValueError("Battleship evidence coordinates do not match active query ships")


__all__ = [
    "BattleshipSample",
    "BattleshipShipPlacement",
    "Coord",
    "FLEET_SHAPES",
    "FleetShapeSpec",
    "SUPPORTED_BATTLESHIP_QUERY_VARIANTS",
    "SUPPORTED_BATTLESHIP_SCENE_VARIANTS",
    "all_coords",
    "coord_to_cell_id",
    "fleet_orientation_lookup",
    "fleet_shape_by_id",
    "matching_fleet_shape_ids",
    "normalize_offsets",
    "shape_orientations",
    "sorted_coords",
    "validate_battleship_sample",
]
