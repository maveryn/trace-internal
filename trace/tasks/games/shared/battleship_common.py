"""Shared Battleship-grid helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Sequence, Tuple


Coord = Tuple[int, int]
SUPPORTED_BATTLESHIP_SHIP_STATUS_QUERY_IDS: Tuple[str, ...] = (
    "sunk_ship_count",
    "partial_ship_count",
)
SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS: Tuple[str, ...] = (
    "named_ship_hit_cell_count",
    "named_ship_unhit_cell_count",
)
SUPPORTED_BATTLESHIP_LAST_CELL_QUERY_IDS: Tuple[str, ...] = (
    "last_ship_cell_label",
)
SUPPORTED_BATTLESHIP_QUERY_IDS: Tuple[str, ...] = (
    *SUPPORTED_BATTLESHIP_SHIP_STATUS_QUERY_IDS,
    *SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS,
    *SUPPORTED_BATTLESHIP_LAST_CELL_QUERY_IDS,
)
SUPPORTED_BATTLESHIP_SCENE_VARIANTS: Tuple[str, ...] = ("standard_fleet",)
SUPPORTED_BATTLESHIP_TARGET_SHIP_IDS: Tuple[str, ...] = (
    "line5",
    "line4",
    "line3",
    "square4",
    "elbow3",
)


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
class BattleshipCandidateOption:
    """One labeled candidate cell in a Battleship option-label task."""

    label: str
    coord: Coord
    is_answer: bool


@dataclass(frozen=True)
class BattleshipSample:
    """Generated Battleship tracking-grid state."""

    board_size: int
    query_id: str
    scene_variant: str
    answer: int | str
    ship_placements: Tuple[BattleshipShipPlacement, ...]
    hit_coords: Tuple[Coord, ...]
    miss_coords: Tuple[Coord, ...]
    annotation_coords: Tuple[Coord, ...]
    annotation_ship_ids: Tuple[str, ...]
    target_answer: int
    sunk_ship_count: int
    partial_ship_count: int
    untouched_ship_count: int
    construction_mode: str
    target_ship_id: str = ""
    target_ship_display_name: str = ""
    target_ship_shape_id: str = ""
    target_cell_status: str = ""
    target_missing_coord: Coord | None = None
    candidate_options: Tuple[BattleshipCandidateOption, ...] = tuple()


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
    if str(sample.query_id) == "sunk_ship_count":
        expected_answer = int(sample.sunk_ship_count)
        expected_annotation_coords = {coord for ship in sunk_ships for coord in ship.hit_coords}
        expected_annotation_ship_ids = {str(ship.ship_id) for ship in sunk_ships}
    elif str(sample.query_id) == "partial_ship_count":
        expected_answer = int(sample.partial_ship_count)
        expected_annotation_coords = {coord for ship in partial_ships for coord in ship.hit_coords}
        expected_annotation_ship_ids = {str(ship.ship_id) for ship in partial_ships}
    elif str(sample.query_id) in SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS:
        target_ships = [ship for ship in sample.ship_placements if str(ship.ship_id) == str(sample.target_ship_id)]
        if len(target_ships) != 1:
            raise ValueError("Battleship cell-status query must name one target ship")
        target_ship = target_ships[0]
        if str(sample.target_ship_display_name) != str(target_ship.display_name):
            raise ValueError("Battleship target ship display name must match placement")
        if str(sample.target_ship_shape_id) != str(target_ship.shape_id):
            raise ValueError("Battleship target ship shape id must match placement")
        hit_set_for_ship = set(target_ship.hit_coords)
        if str(sample.query_id) == "named_ship_hit_cell_count":
            expected_annotation_coords = set(target_ship.hit_coords)
            expected_answer = len(expected_annotation_coords)
            expected_status = "hit"
        else:
            expected_annotation_coords = set(target_ship.coords) - hit_set_for_ship
            expected_answer = len(expected_annotation_coords)
            expected_status = "unhit"
        expected_annotation_ship_ids = {str(target_ship.ship_id)}
        if str(sample.target_cell_status) != str(expected_status):
            raise ValueError("Battleship target cell status must match active query")
    elif str(sample.query_id) in SUPPORTED_BATTLESHIP_LAST_CELL_QUERY_IDS:
        target_ships = [ship for ship in sample.ship_placements if str(ship.ship_id) == str(sample.target_ship_id)]
        if len(target_ships) != 1:
            raise ValueError("Battleship last-cell query must name one target ship")
        target_ship = target_ships[0]
        if str(sample.target_ship_display_name) != str(target_ship.display_name):
            raise ValueError("Battleship target ship display name must match placement")
        if str(sample.target_ship_shape_id) != str(target_ship.shape_id):
            raise ValueError("Battleship target ship shape id must match placement")
        if sample.target_missing_coord is None:
            raise ValueError("Battleship last-cell query must record one target missing coord")
        missing_coord = (int(sample.target_missing_coord[0]), int(sample.target_missing_coord[1]))
        target_coords = set(target_ship.coords)
        if missing_coord not in target_coords:
            raise ValueError("Battleship missing coord must belong to target ship")
        if set(target_ship.hit_coords) != target_coords - {missing_coord}:
            raise ValueError("Battleship last-cell target must have exactly one unhit cell")
        for ship in sample.ship_placements:
            if str(ship.ship_id) != str(target_ship.ship_id) and not bool(ship.is_sunk):
                raise ValueError("Battleship last-cell query requires every non-target ship to be sunk")
        if len(sample.candidate_options) not in {4, 5, 6}:
            raise ValueError("Battleship last-cell query requires 4, 5, or 6 candidate options")
        labels = [str(option.label) for option in sample.candidate_options]
        expected_labels = ["A", "B", "C", "D", "E", "F"][: len(labels)]
        if labels != expected_labels:
            raise ValueError("Battleship last-cell candidate labels must be ordered A-prefix labels")
        candidate_coords = [(int(option.coord[0]), int(option.coord[1])) for option in sample.candidate_options]
        if len(candidate_coords) != len(set(candidate_coords)):
            raise ValueError("Battleship last-cell candidate coords must be unique")
        answer_options = [option for option in sample.candidate_options if bool(option.is_answer)]
        if len(answer_options) != 1:
            raise ValueError("Battleship last-cell query must have exactly one answer option")
        answer_option = answer_options[0]
        if str(sample.answer) != str(answer_option.label):
            raise ValueError("Battleship last-cell answer must be the answer option label")
        if (int(answer_option.coord[0]), int(answer_option.coord[1])) != missing_coord:
            raise ValueError("Battleship last-cell answer option must mark the missing coord")
        target_hits = set(target_ship.hit_coords)
        valid_candidate_labels = []
        for option in sample.candidate_options:
            completed = target_hits | {(int(option.coord[0]), int(option.coord[1]))}
            if str(target_ship.shape_id) in matching_fleet_shape_ids(tuple(completed)):
                valid_candidate_labels.append(str(option.label))
        if valid_candidate_labels != [str(answer_option.label)]:
            raise ValueError("Battleship last-cell candidate set must have exactly one shape-valid answer")
        expected_answer = str(answer_option.label)
        expected_annotation_coords = {missing_coord}
        expected_annotation_ship_ids = {str(target_ship.ship_id)}
    else:
        raise ValueError(f"unsupported Battleship query_id: {sample.query_id}")
    if str(sample.query_id) in SUPPORTED_BATTLESHIP_LAST_CELL_QUERY_IDS:
        if str(sample.answer) != str(expected_answer):
            raise ValueError("Battleship answer does not match active query label")
    elif int(sample.answer) != int(expected_answer):
        raise ValueError("Battleship answer does not match active query count")
    annotation_set = set(sample.annotation_coords)
    if annotation_set != expected_annotation_coords:
        raise ValueError("Battleship annotation coordinates do not match active query ships")
    annotation_ship_ids = set(str(ship_id) for ship_id in sample.annotation_ship_ids)
    if annotation_ship_ids != expected_annotation_ship_ids:
        raise ValueError("Battleship annotation ship ids do not match active query ships")


__all__ = [
    "BattleshipSample",
    "BattleshipCandidateOption",
    "BattleshipShipPlacement",
    "Coord",
    "FLEET_SHAPES",
    "FleetShapeSpec",
    "SUPPORTED_BATTLESHIP_CELL_STATUS_QUERY_IDS",
    "SUPPORTED_BATTLESHIP_LAST_CELL_QUERY_IDS",
    "SUPPORTED_BATTLESHIP_QUERY_IDS",
    "SUPPORTED_BATTLESHIP_SCENE_VARIANTS",
    "SUPPORTED_BATTLESHIP_SHIP_STATUS_QUERY_IDS",
    "SUPPORTED_BATTLESHIP_TARGET_SHIP_IDS",
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
