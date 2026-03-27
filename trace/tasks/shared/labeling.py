"""Cross-domain helpers for assigning deterministic scene labels."""

from __future__ import annotations

from typing import Sequence, Tuple


LABEL_POOL_A_L: Tuple[str, ...] = tuple("ABCDEFGHIJKL")


def assign_shuffled_labels(
    rng,
    *,
    object_count: int,
    label_pool: Sequence[str] = LABEL_POOL_A_L,
) -> Tuple[str, ...]:
    """Return one shuffled label subset for a multi-object scene.

    The helper intentionally keeps the pool compact (`A`..`L`) so labels stay
    legible in crowded review workbooks and prompts.
    """

    if int(object_count) > len(label_pool):
        raise ValueError("object_count exceeds available scene labels")
    labels = [str(label) for label in label_pool[: int(object_count)]]
    rng.shuffle(labels)
    return tuple(str(label) for label in labels)


__all__ = ["LABEL_POOL_A_L", "assign_shuffled_labels"]
