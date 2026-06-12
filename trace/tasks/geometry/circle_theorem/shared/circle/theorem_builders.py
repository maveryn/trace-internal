"""Facade for circle-theorem query sampling and scene construction."""

from __future__ import annotations

from typing import Any, Dict

from .theorem_common import _ResolvedQuery
from .theorem_angle_builders import (
    _build_cyclic_quadrilateral_angle_scene,
    _build_external_secant_angle_scene,
    _build_inscribed_angle_scene,
    _build_intersecting_chords_arc_scene,
    _build_multi_step_angle_scene,
    _build_tangent_chord_angle_scene,
)
from .theorem_geometry import (
    _add_points,
    _circle_point,
    _rotated_tangent_unit,
)
from .theorem_length_builders import (
    _build_diameter_perpendicular_chord_scene,
    _build_secant_secant_scene,
    _build_secant_secant_variable_scene,
    _build_tangent_secant_scene,
)
from .theorem_sampling import (
    _candidate_diameter_chord_values,
    _candidate_secant_secant_values,
    _candidate_secant_secant_variable_values,
    _candidate_tangent_secant_values,
    _feasible_secant_secant_variable_target_kinds,
    _feasible_tangent_secant_target_kinds,
    _hard_tangent_secant_triple,
    _resolve_query,
)


def _build_scene_payload(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    if str(query.query_id) == "diameter_perpendicular_chord_length":
        return _build_diameter_perpendicular_chord_scene(rng, query=query)
    if str(query.query_id) == "secant_secant_variable_segment_length":
        return _build_secant_secant_variable_scene(rng, query=query)
    if str(query.query_id) == "tangent_secant_length":
        return _build_tangent_secant_scene(rng, query=query)
    if str(query.query_id) == "secant_secant_length":
        return _build_secant_secant_scene(rng, query=query)
    if str(query.query_id) == "intersecting_chords_arc_measure":
        return _build_intersecting_chords_arc_scene(rng, query=query)
    if str(query.query_id) == "multi_step_angle_value":
        return _build_multi_step_angle_scene(rng, query=query)
    if str(query.query_id) in {
        "inscribed_angle_from_central",
        "central_angle_from_inscribed",
        "inscribed_angle_from_arc",
    }:
        return _build_inscribed_angle_scene(rng, query=query)
    if str(query.query_id) in {
        "tangent_chord_angle_from_arc",
        "tangent_chord_angle_from_inscribed",
    }:
        return _build_tangent_chord_angle_scene(rng, query=query)
    if str(query.query_id) == "external_two_secants_angle_from_arcs":
        return _build_external_secant_angle_scene(rng, query=query)
    if str(query.query_id) in {
        "opposite_angle_supplement",
        "exterior_angle_from_opposite_interior",
    }:
        return _build_cyclic_quadrilateral_angle_scene(rng, query=query)
    raise ValueError(f"unsupported query_id: {query.query_id}")


__all__ = [
    '_candidate_diameter_chord_values',
    '_hard_tangent_secant_triple',
    '_candidate_tangent_secant_values',
    '_feasible_tangent_secant_target_kinds',
    '_candidate_secant_secant_values',
    '_candidate_secant_secant_variable_values',
    '_feasible_secant_secant_variable_target_kinds',
    '_resolve_query',
    '_build_diameter_perpendicular_chord_scene',
    '_build_tangent_secant_scene',
    '_build_secant_secant_scene',
    '_build_secant_secant_variable_scene',
    '_circle_point',
    '_rotated_tangent_unit',
    '_add_points',
    '_build_intersecting_chords_arc_scene',
    '_build_multi_step_angle_scene',
    '_build_inscribed_angle_scene',
    '_build_tangent_chord_angle_scene',
    '_build_external_secant_angle_scene',
    '_build_cyclic_quadrilateral_angle_scene',
    '_build_scene_payload',
]
