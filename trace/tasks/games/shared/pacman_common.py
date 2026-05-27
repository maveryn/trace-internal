"""Shared Pac-Man maze helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence, Tuple


Coord = Tuple[int, int]

SUPPORTED_PACMAN_QUERY_IDS: Tuple[str, ...] = (
    "path_pellet_count",
    "next_item_label",
    "pellet_count_before_ghost",
)
SUPPORTED_PACMAN_SCENE_VARIANTS: Tuple[str, ...] = (
    "compact_maze",
    "wide_maze",
)
SUPPORTED_PACMAN_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "neon",
    "paper",
    "terminal",
    "pastel",
)
PACMAN_ITEM_LABELS: Tuple[str, ...] = tuple("ABCDEF")
PACMAN_ITEM_KINDS: Tuple[str, ...] = (
    "cherry",
    "strawberry",
    "orange",
    "bell",
    "melon",
    "key",
)
PACMAN_GHOST_COLOR_KEYS: Tuple[str, ...] = (
    "red",
    "pink",
    "cyan",
    "orange",
    "purple",
)


@dataclass(frozen=True)
class PacmanItem:
    """One labeled visible bonus item."""

    label: str
    item_id: str
    coord: Coord
    kind: str
    is_answer: bool = False


@dataclass(frozen=True)
class PacmanGhost:
    """One visible ghost in the maze."""

    ghost_id: str
    coord: Coord
    color_key: str
    is_stop_ghost: bool = False


@dataclass(frozen=True)
class PacmanSample:
    """Generated Pac-Man maze state and query answer."""

    row_count: int
    col_count: int
    query_id: str
    scene_variant: str
    style_variant: str
    open_cells: Tuple[Coord, ...]
    wall_cells: Tuple[Coord, ...]
    pacman_coord: Coord
    route_coords: Tuple[Coord, ...]
    pellets: Tuple[Coord, ...]
    items: Tuple[PacmanItem, ...]
    ghosts: Tuple[PacmanGhost, ...]
    answer: int | str
    target_answer: int | str
    evidence_entity_ids: Tuple[str, ...]
    construction_mode: str


def sorted_coords(coords: Iterable[Coord]) -> Tuple[Coord, ...]:
    """Return canonical row-major coordinates."""

    return tuple(sorted((int(row), int(col)) for row, col in coords))


def pellet_entity_id(coord: Coord) -> str:
    """Return the stable entity id for one normal pellet."""

    row, col = coord
    return f"pellet_r{int(row)}_c{int(col)}"


def item_entity_id(label: str) -> str:
    """Return the stable entity id for one labeled bonus item."""

    return f"item_{str(label)}"


def ghost_entity_id(name: int | str) -> str:
    """Return the stable entity id for one visible ghost."""

    if isinstance(name, int):
        return f"ghost_{int(name):02d}"
    text = str(name).strip()
    if text.startswith("ghost_"):
        return text
    return f"ghost_{text}"


def pacman_entity_id() -> str:
    """Return the stable entity id for the visible Pac-Man marker."""

    return "pacman"


def route_entity_id(index: int) -> str:
    """Return the stable entity id for one highlighted route cell."""

    return f"route_{int(index):02d}"


def all_grid_coords(rows: int, cols: int) -> Tuple[Coord, ...]:
    """Return all grid coordinates."""

    return tuple((row, col) for row in range(int(rows)) for col in range(int(cols)))


def grid_neighbors(coord: Coord, *, rows: int, cols: int) -> Tuple[Coord, ...]:
    """Return orthogonal in-bounds grid neighbors excluding the outer wall ring."""

    row, col = int(coord[0]), int(coord[1])
    candidates = (
        (row - 1, col),
        (row + 1, col),
        (row, col - 1),
        (row, col + 1),
    )
    return tuple(
        (int(next_row), int(next_col))
        for next_row, next_col in candidates
        if 1 <= int(next_row) < int(rows) - 1 and 1 <= int(next_col) < int(cols) - 1
    )


def coord_from_entity_id(entity_id: str) -> Coord:
    """Decode a pellet-like entity id into a coordinate."""

    text = str(entity_id)
    if "_r" not in text or "_c" not in text:
        raise ValueError(f"entity id does not encode a coordinate: {entity_id}")
    row_text, col_text = text.split("_r", 1)[1].split("_c", 1)
    return int(row_text), int(col_text)


def validate_pacman_sample(sample: PacmanSample) -> None:
    """Validate one generated Pac-Man sample contract."""

    query = str(sample.query_id)
    if query not in SUPPORTED_PACMAN_QUERY_IDS:
        raise ValueError(f"unsupported Pac-Man query_id: {query}")
    if str(sample.scene_variant) not in SUPPORTED_PACMAN_SCENE_VARIANTS:
        raise ValueError(f"unsupported Pac-Man scene_variant: {sample.scene_variant}")
    if str(sample.style_variant) not in SUPPORTED_PACMAN_STYLE_VARIANTS:
        raise ValueError(f"unsupported Pac-Man style_variant: {sample.style_variant}")
    open_cells = {tuple(coord) for coord in sample.open_cells}
    wall_cells = {tuple(coord) for coord in sample.wall_cells}
    if open_cells & wall_cells:
        raise ValueError("Pac-Man open and wall cells overlap")
    if tuple(sample.pacman_coord) not in open_cells:
        raise ValueError("Pac-Man coordinate must be an open cell")
    if not sample.route_coords or tuple(sample.route_coords[0]) != tuple(sample.pacman_coord):
        raise ValueError("Pac-Man route must start at Pac-Man")
    if any(tuple(coord) not in open_cells for coord in sample.route_coords):
        raise ValueError("Pac-Man route includes a non-open cell")
    pellet_set = {tuple(coord) for coord in sample.pellets}
    if len(pellet_set) != len(sample.pellets):
        raise ValueError("Pac-Man pellets must be unique")
    if any(coord not in open_cells for coord in pellet_set):
        raise ValueError("Pac-Man pellet must be on an open cell")
    item_labels = [str(item.label) for item in sample.items]
    if len(set(item_labels)) != len(item_labels):
        raise ValueError("Pac-Man item labels must be unique")
    item_coords = [tuple(item.coord) for item in sample.items]
    if len(set(item_coords)) != len(item_coords):
        raise ValueError("Pac-Man item coordinates must be unique")
    if any(coord not in open_cells for coord in item_coords):
        raise ValueError("Pac-Man item must be on an open cell")
    if any(coord in pellet_set for coord in item_coords):
        raise ValueError("Pac-Man items and pellets must not overlap")
    ghost_ids = [str(ghost.ghost_id) for ghost in sample.ghosts]
    if len(set(ghost_ids)) != len(ghost_ids):
        raise ValueError("Pac-Man ghost ids must be unique")
    ghost_coords = [tuple(ghost.coord) for ghost in sample.ghosts]
    if len(set(ghost_coords)) != len(ghost_coords):
        raise ValueError("Pac-Man ghost coordinates must be unique")
    if any(coord not in open_cells for coord in ghost_coords):
        raise ValueError("Pac-Man ghost must be on an open cell")
    if any(coord in pellet_set for coord in ghost_coords):
        raise ValueError("Pac-Man ghosts and pellets must not overlap")
    if any(coord in set(item_coords) for coord in ghost_coords):
        raise ValueError("Pac-Man ghosts and items must not overlap")
    if tuple(sample.pacman_coord) in set(ghost_coords):
        raise ValueError("Pac-Man ghost must not overlap Pac-Man")

    evidence_ids = tuple(str(entity_id) for entity_id in sample.evidence_entity_ids)
    if query == "next_item_label":
        if not isinstance(sample.answer, str):
            raise ValueError("next_item_label must have a string answer")
        matching = [item for item in sample.items if str(item.label) == str(sample.answer)]
        if len(matching) != 1:
            raise ValueError("next_item_label answer must name exactly one visible item")
        if evidence_ids != (item_entity_id(str(sample.answer)),):
            raise ValueError("next_item_label evidence must be the selected item")
    elif query == "pellet_count_before_ghost":
        if not isinstance(sample.answer, int):
            raise ValueError("pellet_count_before_ghost must have an integer answer")
        pellet_ids = tuple(entity_id for entity_id in evidence_ids if entity_id.startswith("pellet_r"))
        ghost_ids_in_evidence = tuple(entity_id for entity_id in evidence_ids if entity_id.startswith("ghost_"))
        if len(ghost_ids_in_evidence) != 1:
            raise ValueError("pellet_count_before_ghost evidence must include exactly one route ghost")
        if len(pellet_ids) != int(sample.answer):
            raise ValueError("pellet_count_before_ghost pellet evidence count must match the answer")
        stop_ghost_id = ghost_ids_in_evidence[0]
        stop_ghosts = [ghost for ghost in sample.ghosts if str(ghost.ghost_id) == stop_ghost_id and bool(ghost.is_stop_ghost)]
        if len(stop_ghosts) != 1:
            raise ValueError("pellet_count_before_ghost evidence ghost must be the stop ghost")
        route_order = {tuple(coord): index for index, coord in enumerate(sample.route_coords)}
        stop_coord = tuple(stop_ghosts[0].coord)
        if stop_coord not in route_order or route_order[stop_coord] == 0:
            raise ValueError("pellet_count_before_ghost stop ghost must lie after Pac-Man on the route")
        evidence_coords = {coord_from_entity_id(entity_id) for entity_id in pellet_ids}
        if not evidence_coords.issubset(pellet_set):
            raise ValueError("pellet_count_before_ghost pellet evidence must be visible pellets")
        if any(tuple(coord) not in route_order for coord in evidence_coords):
            raise ValueError("pellet_count_before_ghost pellet evidence must be on the highlighted route")
        stop_index = int(route_order[stop_coord])
        if any(int(route_order[coord]) >= stop_index for coord in evidence_coords):
            raise ValueError("pellet_count_before_ghost pellet evidence must come before the stop ghost")
        expected_coords = {
            tuple(coord)
            for coord in pellet_set
            if tuple(coord) in route_order and int(route_order[tuple(coord)]) < stop_index
        }
        if evidence_coords != expected_coords:
            raise ValueError("pellet_count_before_ghost evidence must cover all counted route pellets before the stop ghost")
    else:
        if not isinstance(sample.answer, int):
            raise ValueError(f"{query} must have an integer answer")
        if len(evidence_ids) != int(sample.answer):
            raise ValueError(f"{query} evidence count must match the answer")
        if any(not entity_id.startswith("pellet_r") for entity_id in evidence_ids):
            raise ValueError(f"{query} evidence must point to pellet entities")
        evidence_coords = {coord_from_entity_id(entity_id) for entity_id in evidence_ids}
        if not evidence_coords.issubset(pellet_set):
            raise ValueError(f"{query} evidence must be visible pellets")


def visible_pellet_trace(pellets: Sequence[Coord]) -> Tuple[Mapping[str, object], ...]:
    """Return row-major trace rows for visible pellets."""

    return tuple(
        {
            "coord": [int(coord[0]), int(coord[1])],
            "entity_id": pellet_entity_id(coord),
        }
        for coord in sorted_coords(pellets)
    )


def visible_ghost_trace(ghosts: Sequence[PacmanGhost]) -> Tuple[Mapping[str, object], ...]:
    """Return trace rows for visible ghosts."""

    return tuple(
        {
            "coord": [int(ghost.coord[0]), int(ghost.coord[1])],
            "entity_id": str(ghost.ghost_id),
            "color_key": str(ghost.color_key),
            "is_stop_ghost": bool(ghost.is_stop_ghost),
        }
        for ghost in ghosts
    )


__all__ = [
    "PACMAN_GHOST_COLOR_KEYS",
    "PACMAN_ITEM_KINDS",
    "PACMAN_ITEM_LABELS",
    "SUPPORTED_PACMAN_QUERY_IDS",
    "SUPPORTED_PACMAN_SCENE_VARIANTS",
    "SUPPORTED_PACMAN_STYLE_VARIANTS",
    "Coord",
    "PacmanGhost",
    "PacmanItem",
    "PacmanSample",
    "all_grid_coords",
    "coord_from_entity_id",
    "grid_neighbors",
    "ghost_entity_id",
    "item_entity_id",
    "pacman_entity_id",
    "pellet_entity_id",
    "route_entity_id",
    "sorted_coords",
    "validate_pacman_sample",
    "visible_ghost_trace",
    "visible_pellet_trace",
]
