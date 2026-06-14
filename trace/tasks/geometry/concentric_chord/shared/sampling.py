"""Identity-free case sampling for concentric-chord diagrams."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .state import ConcentricChordCase

PYTHAGOREAN_CASES: tuple[ConcentricChordCase, ...] = (
    ConcentricChordCase(5, 3, 4),
    ConcentricChordCase(10, 6, 8),
    ConcentricChordCase(13, 5, 12),
    ConcentricChordCase(13, 12, 5),
    ConcentricChordCase(17, 8, 15),
    ConcentricChordCase(25, 7, 24),
    ConcentricChordCase(25, 15, 20),
    ConcentricChordCase(25, 24, 7),
    ConcentricChordCase(29, 20, 21),
    ConcentricChordCase(34, 16, 30),
    ConcentricChordCase(37, 12, 35),
    ConcentricChordCase(39, 15, 36),
    ConcentricChordCase(41, 9, 40),
    ConcentricChordCase(41, 40, 9),
)


def _validate_case(case: ConcentricChordCase) -> ConcentricChordCase:
    if int(case.outer_radius) ** 2 != int(case.inner_radius) ** 2 + int(case.half_chord) ** 2:
        raise ValueError("concentric chord case must satisfy R^2 = r^2 + (c/2)^2")
    return case


def select_concentric_chord_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[ConcentricChordCase, int]:
    """Select one case, honoring explicit review/debug measurement overrides."""

    explicit_case = params.get("case_index")
    if explicit_case is not None:
        index = int(explicit_case) % len(PYTHAGOREAN_CASES)
    else:
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
        index = int(selection_index) % len(PYTHAGOREAN_CASES)
    base_case = PYTHAGOREAN_CASES[int(index)]
    case = ConcentricChordCase(
        outer_radius=int(params.get("outer_radius", base_case.outer_radius)),
        inner_radius=int(params.get("inner_radius", base_case.inner_radius)),
        half_chord=int(params.get("half_chord", base_case.half_chord)),
    )
    return _validate_case(case), int(index)


__all__ = ["PYTHAGOREAN_CASES", "select_concentric_chord_case"]
