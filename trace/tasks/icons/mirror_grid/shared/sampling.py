"""Sampling helpers for mirror-grid icon scenes."""

from __future__ import annotations

from typing import Sequence, Tuple

from ....shared.labeling import LABEL_POOL_A_L


SYMMETRY_KINDS: Tuple[str, ...] = (
    "vertical",
    "horizontal",
    "diagonal_main",
    "diagonal_anti",
    "both_axes",
)
NONSYMMETRIC_KIND = "none"


def fixed_grid_labels(object_count: int) -> Tuple[str, ...]:
    """Return fixed row-major labels for the visible scene cells."""

    if int(object_count) <= 0 or int(object_count) > len(LABEL_POOL_A_L):
        raise ValueError("mirror-grid object_count is outside the label support")
    return tuple(str(value) for value in LABEL_POOL_A_L[: int(object_count)])


def sample_matching_indices(rng, *, object_count: int, target_count: int) -> Tuple[int, ...]:
    """Sample the scene-cell indices that satisfy the target predicate."""

    if int(target_count) < 0 or int(target_count) > int(object_count):
        raise ValueError("target_count must be within the object_count range")
    return tuple(sorted(int(index) for index in rng.sample(list(range(int(object_count))), int(target_count))))


def sample_distractor_symmetry_kinds(
    rng,
    *,
    reference_symmetry_kind: str,
    distractor_count: int,
) -> Tuple[str, ...]:
    """Sample exact-other or nonsymmetric distractor cell kinds."""

    reference_kind = str(reference_symmetry_kind)
    if reference_kind not in set(SYMMETRY_KINDS):
        raise ValueError(f"unsupported reference symmetry kind: {reference_kind}")
    other_symmetries = [str(value) for value in SYMMETRY_KINDS if str(value) != reference_kind]
    variants: list[str] = []
    if int(distractor_count) >= 1:
        variants.append(str(rng.choice(other_symmetries)))
    if int(distractor_count) >= 2:
        variants.append(NONSYMMETRIC_KIND)
    while len(variants) < int(distractor_count):
        variants.append(str(rng.choice(tuple(other_symmetries) + (NONSYMMETRIC_KIND,))))
    rng.shuffle(variants)
    return tuple(str(value) for value in variants)


__all__ = [
    "NONSYMMETRIC_KIND",
    "SYMMETRY_KINDS",
    "fixed_grid_labels",
    "sample_distractor_symmetry_kinds",
    "sample_matching_indices",
]
