"""Shared nine-men's-morris board construction for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Mapping, Sequence, Tuple


SUPPORTED_NINE_MENS_MORRIS_SCENE_VARIANTS: Tuple[str, ...] = ("single_board",)
SUPPORTED_NINE_MENS_MORRIS_QUERY_IDS: Tuple[str, ...] = (
    "all_pieces_in_mill_count",
    "white_mill_completion_point_count",
    "black_mill_completion_point_count",
)

_POSITION_LAYOUT: Tuple[Tuple[str, float, float], ...] = (
    ("a7", 0.10, 0.10),
    ("d7", 0.50, 0.10),
    ("g7", 0.90, 0.10),
    ("b6", 0.23, 0.23),
    ("d6", 0.50, 0.23),
    ("f6", 0.77, 0.23),
    ("c5", 0.36, 0.36),
    ("d5", 0.50, 0.36),
    ("e5", 0.64, 0.36),
    ("a4", 0.10, 0.50),
    ("b4", 0.23, 0.50),
    ("c4", 0.36, 0.50),
    ("e4", 0.64, 0.50),
    ("f4", 0.77, 0.50),
    ("g4", 0.90, 0.50),
    ("c3", 0.36, 0.64),
    ("d3", 0.50, 0.64),
    ("e3", 0.64, 0.64),
    ("b2", 0.23, 0.77),
    ("d2", 0.50, 0.77),
    ("f2", 0.77, 0.77),
    ("a1", 0.10, 0.90),
    ("d1", 0.50, 0.90),
    ("g1", 0.90, 0.90),
)

_MILL_POSITION_INDICES: Tuple[Tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (9, 10, 11),
    (12, 13, 14),
    (15, 16, 17),
    (18, 19, 20),
    (21, 22, 23),
    (0, 9, 21),
    (3, 10, 18),
    (6, 11, 15),
    (1, 4, 7),
    (16, 19, 22),
    (8, 12, 17),
    (5, 13, 20),
    (2, 14, 23),
)

_WHITE_SUPPORT: Tuple[int, ...] = (0, 3, 5, 6, 7, 8, 9)
_BLACK_SUPPORT: Tuple[int, ...] = (0, 3, 5, 6, 7, 8, 9)
_ALL_SUPPORT: Tuple[int, ...] = (0, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18)
_COMPLETION_SUPPORT: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)


@dataclass(frozen=True)
class NineMensMorrisPieceInstance:
    """One visible piece on the nine-men's-morris board."""

    piece_id: str
    node_index: int
    node_label: str
    color: str


@dataclass(frozen=True)
class NineMensMorrisBoardState:
    """One generated nine-men's-morris board and its mill-membership trace."""

    piece_specs: Tuple[NineMensMorrisPieceInstance, ...]
    white_piece_ids_in_mill: Tuple[str, ...]
    black_piece_ids_in_mill: Tuple[str, ...]
    all_piece_ids_in_mill: Tuple[str, ...]
    white_mill_ids: Tuple[str, ...]
    black_mill_ids: Tuple[str, ...]
    white_mill_completion_node_labels: Tuple[str, ...]
    black_mill_completion_node_labels: Tuple[str, ...]
    overlapping_piece_ids: Tuple[str, ...]
    target_answer: int


@dataclass(frozen=True)
class _OccupancyAnalysis:
    """Derived mill membership information for one board occupancy."""

    white_piece_ids_in_mill: Tuple[str, ...]
    black_piece_ids_in_mill: Tuple[str, ...]
    all_piece_ids_in_mill: Tuple[str, ...]
    white_mill_ids: Tuple[str, ...]
    black_mill_ids: Tuple[str, ...]
    white_mill_completion_node_labels: Tuple[str, ...]
    black_mill_completion_node_labels: Tuple[str, ...]
    mill_membership_count_by_piece_id: Dict[str, int]


def _piece_id(node_index: int, color: str) -> str:
    return f"{str(color)}_{_POSITION_LAYOUT[int(node_index)][0]}"


def _position_label(node_index: int) -> str:
    return str(_POSITION_LAYOUT[int(node_index)][0])


def _mill_id(mill_index: int) -> str:
    return f"mill_{int(mill_index)}"


def _opponent_color(color: str) -> str:
    """Return the opposite Morris piece color."""

    return "black" if str(color) == "white" else "white"


def _completion_node_labels(occupancy_by_node: Mapping[int, str], *, color: str) -> Tuple[str, ...]:
    """Return empty nodes where one piece of the color would complete a mill."""

    target_color = str(color)
    completion_nodes: set[int] = set()
    for node_index in range(len(_POSITION_LAYOUT)):
        if int(node_index) in occupancy_by_node:
            continue
        for positions in _MILL_POSITION_INDICES:
            if int(node_index) not in positions:
                continue
            other_positions = [int(position) for position in positions if int(position) != int(node_index)]
            if all(str(occupancy_by_node.get(int(position), "")) == target_color for position in other_positions):
                completion_nodes.add(int(node_index))
                break
    return tuple(_position_label(int(node_index)) for node_index in sorted(completion_nodes))


def _compute_mill_union_sets_by_size() -> Dict[int, Tuple[FrozenSet[int], ...]]:
    """Precompute unique unions of mill positions up to nine pieces."""

    union_sets: set[FrozenSet[int]] = {frozenset()}
    mill_count = len(_MILL_POSITION_INDICES)
    for mask in range(1, 1 << mill_count):
        union: set[int] = set()
        for mill_index, positions in enumerate(_MILL_POSITION_INDICES):
            if mask & (1 << mill_index):
                union.update(int(position) for position in positions)
        if len(union) <= 9:
            union_sets.add(frozenset(int(position) for position in union))
    by_size: Dict[int, List[FrozenSet[int]]] = {}
    for union in union_sets:
        by_size.setdefault(len(union), []).append(frozenset(int(position) for position in union))
    return {
        int(size): tuple(sorted(values, key=lambda item: tuple(int(position) for position in sorted(item))))
        for size, values in by_size.items()
    }


_UNION_SETS_BY_SIZE = _compute_mill_union_sets_by_size()


def _analyze_occupancy(occupancy_by_node: Mapping[int, str]) -> _OccupancyAnalysis:
    """Return mill membership derived from one node occupancy map."""

    white_piece_ids: set[str] = set()
    black_piece_ids: set[str] = set()
    white_mill_ids: List[str] = []
    black_mill_ids: List[str] = []
    membership_count_by_piece_id: Dict[str, int] = {}

    for mill_index, positions in enumerate(_MILL_POSITION_INDICES):
        colors = [str(occupancy_by_node[position]) for position in positions if position in occupancy_by_node]
        if len(colors) != 3:
            continue
        color = colors[0]
        if not color or any(other != color for other in colors[1:]):
            continue
        mill_id = _mill_id(mill_index)
        if color == "white":
            white_mill_ids.append(str(mill_id))
        else:
            black_mill_ids.append(str(mill_id))
        for node_index in positions:
            piece_id = _piece_id(node_index, color)
            membership_count_by_piece_id[str(piece_id)] = membership_count_by_piece_id.get(str(piece_id), 0) + 1
            if color == "white":
                white_piece_ids.add(str(piece_id))
            else:
                black_piece_ids.add(str(piece_id))

    all_piece_ids = sorted(white_piece_ids | black_piece_ids)
    return _OccupancyAnalysis(
        white_piece_ids_in_mill=tuple(sorted(white_piece_ids)),
        black_piece_ids_in_mill=tuple(sorted(black_piece_ids)),
        all_piece_ids_in_mill=tuple(str(piece_id) for piece_id in all_piece_ids),
        white_mill_ids=tuple(str(value) for value in sorted(white_mill_ids)),
        black_mill_ids=tuple(str(value) for value in sorted(black_mill_ids)),
        white_mill_completion_node_labels=_completion_node_labels(occupancy_by_node, color="white"),
        black_mill_completion_node_labels=_completion_node_labels(occupancy_by_node, color="black"),
        mill_membership_count_by_piece_id={str(key): int(value) for key, value in membership_count_by_piece_id.items()},
    )


def _eligible_union_sets(size: int, *, forbidden_nodes: FrozenSet[int]) -> Tuple[FrozenSet[int], ...]:
    """Return precomputed mill unions of one size that avoid the forbidden nodes."""

    eligible = [
        union
        for union in _UNION_SETS_BY_SIZE.get(int(size), ())
        if frozenset(int(position) for position in union).isdisjoint(forbidden_nodes)
    ]
    return tuple(eligible)


def _choose_one_union_set(rng, *, size: int, forbidden_nodes: FrozenSet[int]) -> FrozenSet[int] | None:
    """Sample one union set of the requested size that avoids the forbidden nodes."""

    eligible = _eligible_union_sets(int(size), forbidden_nodes=forbidden_nodes)
    if not eligible:
        return None
    return frozenset(eligible[int(rng.randrange(len(eligible)))])


def _normalize_query_id_and_color(query_id: str, player_color: str | None = None) -> Tuple[str, str | None]:
    """Return canonical query id plus optional color."""

    variant = str(query_id)
    if variant == "all_pieces_in_mill_count":
        color = None
    elif variant == "white_mill_completion_point_count":
        color = "white"
    elif variant == "black_mill_completion_point_count":
        color = "black"
    else:
        raise ValueError(f"unsupported nine-men's-morris query id: {query_id}")
    return str(variant), color


def _sample_mill_sets(
    rng,
    *,
    query_id: str,
    player_color: str | None = None,
    target_answer: int,
) -> Tuple[FrozenSet[int], FrozenSet[int]]:
    """Sample disjoint white/black mill unions for one query id and target answer."""

    target = int(target_answer)
    variant, color = _normalize_query_id_and_color(str(query_id), player_color=player_color)

    feasible_pairs: List[Tuple[int, int]] = []
    for white_size in _WHITE_SUPPORT:
        for black_size in _BLACK_SUPPORT:
            if int(white_size) + int(black_size) != int(target):
                continue
            if _eligible_union_sets(int(white_size), forbidden_nodes=frozenset()) and _eligible_union_sets(
                int(black_size), forbidden_nodes=frozenset()
            ):
                feasible_pairs.append((int(white_size), int(black_size)))
    rng.shuffle(feasible_pairs)
    for white_size, black_size in feasible_pairs:
        for _ in range(128):
            white_nodes = _choose_one_union_set(rng, size=int(white_size), forbidden_nodes=frozenset())
            if white_nodes is None:
                continue
            black_nodes = _choose_one_union_set(rng, size=int(black_size), forbidden_nodes=white_nodes)
            if black_nodes is not None:
                return frozenset(white_nodes), frozenset(black_nodes)
    raise RuntimeError(f"failed to sample disjoint mill sets for total target {target}")


def _try_add_fillers(
    rng,
    *,
    occupancy_by_node: Dict[int, str],
    expected_white_piece_ids_in_mill: FrozenSet[str],
    expected_black_piece_ids_in_mill: FrozenSet[str],
) -> None:
    """Add non-mill filler pieces without changing the counted mill witnesses."""

    for color in ("white", "black"):
        current_count = sum(1 for occupant in occupancy_by_node.values() if str(occupant) == str(color))
        remaining_capacity = max(0, 9 - int(current_count))
        desired_extra = int(rng.randint(0, min(2, remaining_capacity)))
        candidate_nodes = [node_index for node_index in range(len(_POSITION_LAYOUT)) if node_index not in occupancy_by_node]
        rng.shuffle(candidate_nodes)
        added = 0
        for node_index in candidate_nodes:
            if added >= int(desired_extra):
                break
            occupancy_by_node[int(node_index)] = str(color)
            analysis = _analyze_occupancy(occupancy_by_node)
            if frozenset(analysis.white_piece_ids_in_mill) == expected_white_piece_ids_in_mill and frozenset(
                analysis.black_piece_ids_in_mill
            ) == expected_black_piece_ids_in_mill:
                added += 1
            else:
                del occupancy_by_node[int(node_index)]


def _board_state_from_occupancy(
    occupancy_by_node: Mapping[int, str],
    *,
    target_answer: int,
) -> NineMensMorrisBoardState:
    """Build a public board-state payload from finalized occupancy."""

    final_analysis = _analyze_occupancy(occupancy_by_node)
    piece_specs: List[NineMensMorrisPieceInstance] = []
    for node_index in sorted(occupancy_by_node):
        color = str(occupancy_by_node[node_index])
        piece_specs.append(
            NineMensMorrisPieceInstance(
                piece_id=_piece_id(int(node_index), color),
                node_index=int(node_index),
                node_label=_position_label(int(node_index)),
                color=str(color),
            )
        )
    overlapping_piece_ids = [
        str(piece_id)
        for piece_id, count in final_analysis.mill_membership_count_by_piece_id.items()
        if int(count) >= 2
    ]
    return NineMensMorrisBoardState(
        piece_specs=tuple(piece_specs),
        white_piece_ids_in_mill=tuple(str(value) for value in final_analysis.white_piece_ids_in_mill),
        black_piece_ids_in_mill=tuple(str(value) for value in final_analysis.black_piece_ids_in_mill),
        all_piece_ids_in_mill=tuple(str(value) for value in final_analysis.all_piece_ids_in_mill),
        white_mill_ids=tuple(str(value) for value in final_analysis.white_mill_ids),
        black_mill_ids=tuple(str(value) for value in final_analysis.black_mill_ids),
        white_mill_completion_node_labels=tuple(str(value) for value in final_analysis.white_mill_completion_node_labels),
        black_mill_completion_node_labels=tuple(str(value) for value in final_analysis.black_mill_completion_node_labels),
        overlapping_piece_ids=tuple(sorted(overlapping_piece_ids)),
        target_answer=int(target_answer),
    )


def _sample_completion_occupancy(
    rng,
    *,
    color: str,
    target_answer: int,
) -> Dict[int, str]:
    """Sample one legal occupancy with an exact mill-completion count."""

    target = int(target_answer)
    target_color = str(color)
    other_color = _opponent_color(target_color)
    for _ in range(8192):
        target_count_min = 0 if int(target) == 0 else 2
        target_piece_count = int(rng.randint(int(target_count_min), 9))
        other_piece_count = int(rng.randint(0, 9))
        nodes = list(range(len(_POSITION_LAYOUT)))
        rng.shuffle(nodes)
        occupancy: Dict[int, str] = {}
        for node_index in nodes[:target_piece_count]:
            occupancy[int(node_index)] = target_color
        for node_index in nodes[target_piece_count : target_piece_count + other_piece_count]:
            occupancy[int(node_index)] = other_color
        analysis = _analyze_occupancy(occupancy)
        completion_labels = (
            analysis.white_mill_completion_node_labels
            if target_color == "white"
            else analysis.black_mill_completion_node_labels
        )
        if len(completion_labels) == int(target):
            return occupancy
    raise RuntimeError(f"failed to sample mill-completion board for {target_color} target {target}")


def build_nine_mens_morris_board_state(
    *,
    rng,
    query_id: str,
    target_answer: int,
    player_color: str | None = None,
) -> NineMensMorrisBoardState:
    """Build one visible nine-men's-morris board for the requested query/answer."""

    target = int(target_answer)
    variant, color = _normalize_query_id_and_color(str(query_id), player_color=player_color)
    if variant == "all_pieces_in_mill_count" and target not in _ALL_SUPPORT:
        raise ValueError(f"unsupported all-color target_answer: {target}")
    if variant in {"white_mill_completion_point_count", "black_mill_completion_point_count"}:
        if target not in _COMPLETION_SUPPORT:
            raise ValueError(f"unsupported mill-completion target_answer: {target}")
        occupancy_by_node = _sample_completion_occupancy(
            rng,
            color=str(color),
            target_answer=int(target),
        )
        return _board_state_from_occupancy(occupancy_by_node, target_answer=int(target))

    for _ in range(512):
        white_mill_nodes, black_mill_nodes = _sample_mill_sets(
            rng,
            query_id=variant,
            player_color=color,
            target_answer=int(target),
        )
        occupancy_by_node: Dict[int, str] = {int(node): "white" for node in white_mill_nodes}
        occupancy_by_node.update({int(node): "black" for node in black_mill_nodes})

        base_analysis = _analyze_occupancy(occupancy_by_node)
        expected_white_piece_ids_in_mill = frozenset(base_analysis.white_piece_ids_in_mill)
        expected_black_piece_ids_in_mill = frozenset(base_analysis.black_piece_ids_in_mill)
        _try_add_fillers(
            rng,
            occupancy_by_node=occupancy_by_node,
            expected_white_piece_ids_in_mill=expected_white_piece_ids_in_mill,
            expected_black_piece_ids_in_mill=expected_black_piece_ids_in_mill,
        )
        final_analysis = _analyze_occupancy(occupancy_by_node)

        white_count = len(final_analysis.white_piece_ids_in_mill)
        black_count = len(final_analysis.black_piece_ids_in_mill)
        all_count = len(final_analysis.all_piece_ids_in_mill)
        if variant == "all_pieces_in_mill_count" and int(all_count) != int(target):
            continue

        return _board_state_from_occupancy(occupancy_by_node, target_answer=int(target))

    raise RuntimeError(f"failed to build nine-men's-morris board for {variant} target {target}")


def annotation_piece_ids(
    board_state: NineMensMorrisBoardState,
    *,
    query_id: str,
    player_color: str | None = None,
) -> Tuple[str, ...]:
    """Return prompt-facing annotation piece ids for one query id."""

    variant, color = _normalize_query_id_and_color(str(query_id), player_color=player_color)
    if variant == "white_mill_completion_point_count":
        return tuple(str(label) for label in board_state.white_mill_completion_node_labels)
    if variant == "black_mill_completion_point_count":
        return tuple(str(label) for label in board_state.black_mill_completion_node_labels)
    return tuple(str(piece_id) for piece_id in board_state.all_piece_ids_in_mill)


def supported_targets_for_query(query_id: str, *, player_color: str | None = None) -> Tuple[int, ...]:
    """Return the feasible answer support for one query id."""

    variant, color = _normalize_query_id_and_color(str(query_id), player_color=player_color)
    if variant in {"white_mill_completion_point_count", "black_mill_completion_point_count"}:
        return _COMPLETION_SUPPORT
    return _ALL_SUPPORT


POSITION_LAYOUT = _POSITION_LAYOUT
MILL_POSITION_INDICES = _MILL_POSITION_INDICES


__all__ = [
    "MILL_POSITION_INDICES",
    "POSITION_LAYOUT",
    "NineMensMorrisBoardState",
    "NineMensMorrisPieceInstance",
    "SUPPORTED_NINE_MENS_MORRIS_QUERY_IDS",
    "SUPPORTED_NINE_MENS_MORRIS_SCENE_VARIANTS",
    "build_nine_mens_morris_board_state",
    "annotation_piece_ids",
    "supported_targets_for_query",
]
