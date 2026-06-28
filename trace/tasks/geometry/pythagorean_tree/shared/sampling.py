"""Sampling primitives for Pythagorean tree cases."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.tasks.geometry.shared.pythagorean import (
    IntegerRightTriangle,
    integer_right_triangles,
    validate_integer_right_triangle,
)
from trace.core.sampling import uniform_choice
from trace.core.seed import spawn_rng
from trace.tasks.shared.fixed_query import geometry_selected_probability_map

from .state import PythagoreanTreeTriple

TARGET_SQUARE_ROLES: tuple[str, ...] = ("leg_square_1", "leg_square_2", "hypotenuse_square")


def _default_tree_triples() -> tuple[PythagoreanTreeTriple, ...]:
    """Return attached-square cases with distinct leg and hypotenuse answers."""

    triples: list[PythagoreanTreeTriple] = []
    used_legs: set[int] = set()
    used_hypotenuses: set[int] = set()
    for triangle in integer_right_triangles(
        min_leg=3,
        max_leg=55,
        max_hypotenuse=65,
    ):
        leg_a = int(triangle.leg_a)
        leg_b = int(triangle.leg_b)
        hypotenuse = int(triangle.hypotenuse)
        if leg_a in used_legs or leg_b in used_legs:
            continue
        if hypotenuse in used_hypotenuses:
            continue
        triples.append(PythagoreanTreeTriple(leg_a, leg_b, hypotenuse))
        used_legs.update((leg_a, leg_b))
        used_hypotenuses.add(hypotenuse)
    if len(triples) < 10:
        raise RuntimeError("pythagorean tree triple pool is unexpectedly small")
    return tuple(triples)


TREE_TRIPLES: tuple[PythagoreanTreeTriple, ...] = _default_tree_triples()


def triple_key(triple: PythagoreanTreeTriple) -> str:
    """Return a compact stable key for one integer right triangle."""

    return f"{int(triple.leg_a)}-{int(triple.leg_b)}-{int(triple.hypotenuse)}"


def coerce_explicit_triple(value: Any) -> PythagoreanTreeTriple:
    """Validate a caller-provided three-item integer right-triangle override."""

    if not isinstance(value, Sequence) or len(value) != 3:
        raise ValueError("triple must be a three-item sequence")
    leg_a, leg_b, hypotenuse = [int(item) for item in value]
    validate_integer_right_triangle(
        IntegerRightTriangle(
            leg_a=int(leg_a),
            leg_b=int(leg_b),
            hypotenuse=int(hypotenuse),
        )
    )
    return PythagoreanTreeTriple(int(leg_a), int(leg_b), int(hypotenuse))


def select_tree_triple(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[PythagoreanTreeTriple, dict[str, float]]:
    """Select or validate the integer right-triangle case."""

    explicit = params.get("triple")
    if explicit is not None:
        triple = coerce_explicit_triple(explicit)
        return triple, {triple_key(triple): 1.0}
    rng = spawn_rng(int(instance_seed), str(namespace))
    triple = uniform_choice(rng, TREE_TRIPLES)
    return triple, {triple_key(item): 1.0 / float(len(TREE_TRIPLES)) for item in TREE_TRIPLES}


def select_target_square_role(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> tuple[str, dict[str, float]]:
    """Select which attached square is the unknown area target."""

    explicit = params.get("target_role")
    if explicit is not None:
        role = str(explicit)
        if role not in TARGET_SQUARE_ROLES:
            raise ValueError(f"unsupported pythagorean tree target_role: {role}")
        return role, geometry_selected_probability_map(
            TARGET_SQUARE_ROLES,
            role,
            key_fn=str,
            is_selected=lambda value, selected: str(value) == str(selected),
        )
    rng = spawn_rng(int(instance_seed), str(namespace))
    role = str(uniform_choice(rng, TARGET_SQUARE_ROLES))
    return role, {item: 1.0 / float(len(TARGET_SQUARE_ROLES)) for item in TARGET_SQUARE_ROLES}


__all__ = [
    "TARGET_SQUARE_ROLES",
    "TREE_TRIPLES",
    "coerce_explicit_triple",
    "select_target_square_role",
    "select_tree_triple",
    "triple_key",
]
