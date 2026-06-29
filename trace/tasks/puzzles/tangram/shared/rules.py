"""Tangram scene rules and validation helpers."""

from __future__ import annotations

from itertools import combinations

from .spatial_primitives import BASE_PIECES, CONTACTS


def edge_touching_piece_ids(marked_piece_ids: tuple[str, ...]) -> tuple[str, ...]:
    """Return unmarked pieces that edge-touch any marked piece."""

    marked = {str(piece_id) for piece_id in marked_piece_ids}
    touching: set[str] = set()
    for piece_id in marked:
        touching.update(str(item) for item in CONTACTS.get(str(piece_id), ()))
    return tuple(sorted(touching.difference(marked)))


def contact_mark_candidates() -> (
    dict[int, list[tuple[tuple[str, ...], tuple[str, ...]]]]
):
    """Group feasible marked-piece sets by counted marked-plus-touching total."""

    piece_ids = tuple(str(piece.piece_id) for piece in BASE_PIECES)
    grouped: dict[int, list[tuple[tuple[str, ...], tuple[str, ...]]]] = {}
    for marked_count in (1, 2):
        marked_sets = combinations(piece_ids, marked_count)
        for marked in marked_sets:
            touching = edge_touching_piece_ids(tuple(marked))
            grouped.setdefault(len(marked) + len(touching), []).append(
                (
                    tuple(str(item) for item in marked),
                    tuple(str(item) for item in touching),
                )
            )
    return grouped


def require_unique_correct_option(option_specs: tuple) -> None:
    """Validate that exactly one option is marked correct."""

    correct = [option for option in option_specs if bool(option.is_correct)]
    if len(correct) != 1:
        raise ValueError("Tangram missing-piece task must have exactly one answer")


__all__ = [
    "contact_mark_candidates",
    "edge_touching_piece_ids",
    "require_unique_correct_option",
]
