"""Length-theorem scene payload builders for circle-theorem value tasks."""

from __future__ import annotations

import math
from typing import Any, Dict

from .theorem_common import (
    Point,
    _ResolvedQuery,
    _CENTER_LABEL,
    _sample_point_label_map,
    _visible_segment,
    _visible_angle,
    _line_intersection,
    _angle_degrees_at,
)
from .theorem_geometry import (
    _add_points,
    _apply_external_point_side,
    _mirror_point_x,
    _rotated_tangent_unit,
    _sample_external_point_side,
)
from .theorem_sampling import (
    _candidate_diameter_chord_values,
    _candidate_tangent_secant_values,
    _candidate_secant_secant_values,
    _candidate_secant_secant_variable_values,
)

def _build_diameter_perpendicular_chord_scene(
    rng, *, query: _ResolvedQuery
) -> Dict[str, Any]:
    candidates = _candidate_diameter_chord_values(int(query.target_answer))
    if not candidates:
        raise ValueError(
            f"unsupported target answer for diameter chord theorem: {query.target_answer}"
        )
    spec = dict(candidates[int(rng.randrange(len(candidates)))])
    label_map = _sample_point_label_map(rng, ("O", "B", "D", "E", "A", "C"))
    radius = float(spec["radius"])
    offset = float(spec["offset"])
    half_chord = float(spec["half_chord"])
    canonical_point_model = {
        "O": (0.0, 0.0),
        "B": (0.0, -radius),
        "D": (0.0, radius),
        "E": (0.0, -offset),
        "A": (-half_chord, -offset),
        "C": (half_chord, -offset),
    }
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    diameter_segment = _visible_segment(label_map, "D", "B")
    chord_segment = _visible_segment(label_map, "A", "C")
    answer_segment = _visible_segment(label_map, "B", "E")
    angle_token = f"{_visible_angle(label_map, 'D', 'E', 'C')}=90"
    diameter_token = f"{diameter_segment}={int(spec['diameter'])}"
    chord_token = f"{chord_segment}={int(spec['chord'])}"
    theorem_trace = {
        "theorem": "diameter_perpendicular_chord",
        "label_map": dict(label_map),
        "radius": int(spec["radius"]),
        "center_to_chord_distance": int(spec["offset"]),
        "half_chord_length": int(spec["half_chord"]),
        "diameter_length": int(spec["diameter"]),
        "chord_length": int(spec["chord"]),
        "canonical_answer_segment": "BE",
        "answer_segment": str(answer_segment),
        "answer_value": int(spec["answer"]),
        "distractor_tokens": [str(angle_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": (0.0, 0.0),
        "circle_radius": radius,
        "segments": {
            "DB": (label_map["D"], label_map["B"]),
            "AC": (label_map["A"], label_map["C"]),
            "BE": (label_map["B"], label_map["E"]),
            "DE": (label_map["D"], label_map["E"]),
        },
        "measurement_specs": (
            (diameter_token, "DB", -1.0),
            (chord_token, "AC", -1.0),
            (f"{answer_segment}=?", "BE", 1.0),
        ),
        "angle_marker_specs": (
            {
                "token": angle_token,
                "vertex": label_map["E"],
                "arm0": label_map["D"],
                "arm1": label_map["C"],
                "radius_px": 34.0,
            },
        ),
        "support_measurement_tokens": (diameter_token, chord_token),
        "annotation_point_labels": (
            label_map["D"],
            label_map["B"],
            label_map["A"],
            label_map["C"],
            label_map["E"],
        ),
        "annotation_values": {
            str(diameter_segment): int(spec["diameter"]),
            str(chord_segment): int(spec["chord"]),
            str(answer_segment): int(spec["answer"]),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "diameter_segment": str(diameter_segment),
            "chord_segment": str(chord_segment),
            "intersection_label": str(label_map["E"]),
            "answer_segment": str(answer_segment),
        },
    }

def _build_tangent_secant_scene(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    candidates = _candidate_tangent_secant_values(
        int(query.target_answer),
        target_kind=query.tangent_secant_target_kind,
    )
    if not candidates:
        raise ValueError(
            f"unsupported target answer for tangent secant theorem: {query.target_answer}"
        )
    spec = dict(candidates[int(rng.randrange(len(candidates)))])
    label_map = _sample_point_label_map(rng, ("P", "A", "B", "T", "O"))
    outside = float(spec["PA"])
    internal = float(spec["AB"])
    tangent = float(spec["PT"])
    target_kind = str(spec["target_kind"])
    radius = internal / 2.0
    center_x = outside + radius
    center = (center_x, 0.0)
    tangent_x = ((center_x * center_x) - (radius * radius)) / center_x
    tangent_y = (radius * tangent) / center_x
    if abs(math.hypot(tangent_x - center_x, tangent_y) - radius) > 1e-7:
        raise ValueError("sampled tangent point is not on the circle")
    if abs((tangent_x * (tangent_x - center_x)) + (tangent_y * tangent_y)) > 1e-7:
        raise ValueError("sampled tangent point is not perpendicular to the radius")
    canonical_point_model = {
        "P": (0.0, 0.0),
        "A": (outside, 0.0),
        "B": (outside + internal, 0.0),
        "T": (float(tangent_x), float(tangent_y)),
        "O": center,
    }
    external_point_side = _sample_external_point_side(rng)
    canonical_point_model, center = _apply_external_point_side(
        canonical_point_model,
        center,
        side=external_point_side,
    )
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    tangent_segment = _visible_segment(label_map, "P", "T")
    outside_segment = _visible_segment(label_map, "P", "A")
    inside_segment = _visible_segment(label_map, "A", "B")
    full_secant_segment = _visible_segment(label_map, "P", "B")
    answer_segment_by_kind = {
        "outside": outside_segment,
        "inside": inside_segment,
        "tangent": tangent_segment,
    }
    answer_segment = str(answer_segment_by_kind[str(target_kind)])
    canonical_answer_segment = str(spec["canonical_answer_segment"])
    known_token_by_segment = {
        "PT": f"{tangent_segment}={int(tangent)}",
        "PA": f"{outside_segment}={int(outside)}",
        "AB": f"{inside_segment}={int(internal)}",
    }
    known_segment_ids_by_kind = {
        "outside": ("PT", "AB"),
        "inside": ("PT", "PA"),
        "tangent": ("PA", "AB"),
    }
    known_segment_ids = known_segment_ids_by_kind[str(target_kind)]
    tokens = tuple(
        str(known_token_by_segment[str(segment_id)]) for segment_id in known_segment_ids
    )
    measurement_specs_by_kind = {
        "outside": (
            (known_token_by_segment["PT"], "PT", -1.0),
            (f"{outside_segment}=?", "PA", 1.0),
            (known_token_by_segment["AB"], "AB", 1.0),
        ),
        "inside": (
            (known_token_by_segment["PT"], "PT", -1.0),
            (known_token_by_segment["PA"], "PA", 1.0),
            (f"{inside_segment}=?", "AB", 1.0),
        ),
        "tangent": (
            (f"{tangent_segment}=?", "PT", -1.0),
            (known_token_by_segment["PA"], "PA", 1.0),
            (known_token_by_segment["AB"], "AB", 1.0),
        ),
    }
    distractor_angle = _visible_angle(label_map, "T", "P", "A")
    distractor_angle_value = _angle_degrees_at(
        canonical_point_model["P"],
        canonical_point_model["T"],
        canonical_point_model["A"],
    )
    distractor_token = f"{distractor_angle}={int(distractor_angle_value)}"
    theorem_trace = {
        "theorem": "tangent_secant",
        "label_map": dict(label_map),
        "target_kind": str(target_kind),
        "PT": int(tangent),
        "PA": int(outside),
        "AB": int(internal),
        "PB": int(outside + internal),
        "canonical_answer_segment": str(canonical_answer_segment),
        "answer_segment": str(answer_segment),
        "answer_value": int(spec["answer"]),
        "power_PT_squared": int(tangent * tangent),
        "power_PA_times_PB": int(outside * (outside + internal)),
        "distractor_tokens": [str(distractor_token)],
        "external_point_side": str(external_point_side),
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "PT": (label_map["P"], label_map["T"]),
            "PAB": (label_map["P"], label_map["B"]),
            "PA": (label_map["P"], label_map["A"]),
            "AB": (label_map["A"], label_map["B"]),
            "OB": (label_map["O"], label_map["B"]),
        },
        "measurement_specs": measurement_specs_by_kind[str(target_kind)],
        "angle_marker_specs": (
            {
                "token": distractor_token,
                "vertex": label_map["P"],
                "arm0": label_map["T"],
                "arm1": label_map["A"],
                "radius_px": 36.0,
            },
        ),
        "support_measurement_tokens": tokens,
        "annotation_point_labels": (
            label_map["P"],
            label_map["T"],
            label_map["A"],
            label_map["B"],
        ),
        "annotation_values": {
            str(tangent_segment): int(tangent),
            str(outside_segment): int(outside),
            str(inside_segment): int(internal),
            str(full_secant_segment): int(outside + internal),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "external_point": str(label_map["P"]),
            "tangent_point": str(label_map["T"]),
            "near_point": str(label_map["A"]),
            "far_point": str(label_map["B"]),
            "tangent_segment": str(tangent_segment),
            "inside_segment": str(inside_segment),
            "answer_segment": str(answer_segment),
        },
    }

def _build_secant_secant_scene(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    candidates = _candidate_secant_secant_values(int(query.target_answer))
    if not candidates:
        raise ValueError(
            f"unsupported target answer for secant secant theorem: {query.target_answer}"
        )
    spec = dict(candidates[int(rng.randrange(len(candidates)))])
    label_map = _sample_point_label_map(rng, ("P", "A", "B", "C", "D", "O"))
    pa = float(spec["PA"])
    ab = float(spec["AB"])
    pc = float(spec["PC"])
    cd = float(spec["CD"])
    pd = float(spec["PD"])
    radius = ab / 2.0
    center_x = pa + radius
    center = (center_x, 0.0)
    cos_theta = float(pc + pd) / float(2.0 * center_x)
    sin_theta = math.sqrt(max(0.0, 1.0 - (cos_theta * cos_theta)))
    u2 = (float(cos_theta), float(sin_theta))
    canonical_point_model = {
        "P": (0.0, 0.0),
        "A": (pa, 0.0),
        "B": (pa + ab, 0.0),
        "C": (pc * u2[0], pc * u2[1]),
        "D": (pd * u2[0], pd * u2[1]),
        "O": center,
    }
    external_point_side = _sample_external_point_side(rng)
    canonical_point_model, center = _apply_external_point_side(
        canonical_point_model,
        center,
        side=external_point_side,
    )
    for label in ("A", "B", "C", "D"):
        distance = math.hypot(
            canonical_point_model[label][0] - center[0],
            canonical_point_model[label][1] - center[1],
        )
        if abs(float(distance) - float(radius)) > 1e-6:
            raise ValueError("sampled secant point is not on the circle")
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    outside_segment = _visible_segment(label_map, "P", "A")
    inside_segment = _visible_segment(label_map, "A", "B")
    full_first_secant = _visible_segment(label_map, "P", "B")
    outside_second_segment = _visible_segment(label_map, "P", "C")
    inside_second_segment = _visible_segment(label_map, "C", "D")
    full_second_secant = _visible_segment(label_map, "P", "D")
    distractor_angle = _visible_angle(label_map, "A", "P", "C")
    distractor_angle_value = _angle_degrees_at(
        canonical_point_model["P"],
        canonical_point_model["A"],
        canonical_point_model["C"],
    )
    tokens = (
        f"{inside_segment}={int(ab)}",
        f"{outside_second_segment}={int(pc)}",
        f"{inside_second_segment}={int(cd)}",
    )
    distractor_token = f"{distractor_angle}={int(distractor_angle_value)}"
    theorem_trace = {
        "theorem": "secant_secant",
        "label_map": dict(label_map),
        "PA": int(pa),
        "AB": int(ab),
        "PB": int(pa + ab),
        "PC": int(pc),
        "CD": int(cd),
        "PD": int(pd),
        "canonical_answer_segment": "PA",
        "answer_segment": str(outside_segment),
        "answer_value": int(pa),
        "power_PA_times_PB": int(pa * (pa + ab)),
        "power_PC_times_PD": int(pc * pd),
        "distractor_tokens": [str(distractor_token)],
        "external_point_side": str(external_point_side),
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "PAB": (label_map["P"], label_map["B"]),
            "PCD": (label_map["P"], label_map["D"]),
            "PA": (label_map["P"], label_map["A"]),
            "AB": (label_map["A"], label_map["B"]),
            "PC": (label_map["P"], label_map["C"]),
            "CD": (label_map["C"], label_map["D"]),
        },
        "measurement_specs": (
            (f"{outside_segment}=?", "PA", 1.0),
            (tokens[0], "AB", 1.0),
            (tokens[1], "PC", -1.0),
            (tokens[2], "CD", 1.0),
        ),
        "angle_marker_specs": (
            {
                "token": distractor_token,
                "vertex": label_map["P"],
                "arm0": label_map["A"],
                "arm1": label_map["C"],
                "radius_px": 38.0,
            },
        ),
        "support_measurement_tokens": tokens,
        "annotation_point_labels": (
            label_map["P"],
            label_map["A"],
            label_map["B"],
            label_map["C"],
            label_map["D"],
        ),
        "annotation_values": {
            str(outside_segment): int(pa),
            str(inside_segment): int(ab),
            str(full_first_secant): int(pa + ab),
            str(outside_second_segment): int(pc),
            str(inside_second_segment): int(cd),
            str(full_second_secant): int(pd),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "external_point": str(label_map["P"]),
            "near_point": str(label_map["A"]),
            "far_point": str(label_map["B"]),
            "near_point_alt": str(label_map["C"]),
            "far_point_alt": str(label_map["D"]),
            "inside_segment": str(inside_segment),
            "outside_second_segment": str(outside_second_segment),
            "inside_second_segment": str(inside_second_segment),
            "answer_segment": str(outside_segment),
        },
    }

def _build_secant_secant_variable_scene(
    rng, *, query: _ResolvedQuery
) -> Dict[str, Any]:
    candidates = _candidate_secant_secant_variable_values(
        int(query.target_answer),
        target_kind=query.secant_secant_variable_target_kind,
    )
    if not candidates:
        raise ValueError(
            f"unsupported target answer for variable secant secant theorem: {query.target_answer}"
        )
    spec = dict(candidates[int(rng.randrange(len(candidates)))])
    label_map = _sample_point_label_map(rng, ("P", "A", "B", "C", "D", "O"))
    pa = float(spec["PA"])
    ab = float(spec["AB"])
    pc = float(spec["PC"])
    cd = float(spec["CD"])
    pd = float(spec["PD"])
    target_kind = str(spec["target_kind"])
    canonical_answer_segment = str(spec["canonical_answer_segment"])
    radius = ab / 2.0
    center_x = pa + radius
    center = (center_x, 0.0)
    cos_theta = float(pc + pd) / float(2.0 * center_x)
    sin_theta = math.sqrt(max(0.0, 1.0 - (cos_theta * cos_theta)))
    u2 = (float(cos_theta), float(sin_theta))
    canonical_point_model = {
        "P": (0.0, 0.0),
        "A": (pa, 0.0),
        "B": (pa + ab, 0.0),
        "C": (pc * u2[0], pc * u2[1]),
        "D": (pd * u2[0], pd * u2[1]),
        "O": center,
    }
    external_point_side = _sample_external_point_side(rng)
    canonical_point_model, center = _apply_external_point_side(
        canonical_point_model,
        center,
        side=external_point_side,
    )
    for label in ("A", "B", "C", "D"):
        distance = math.hypot(
            canonical_point_model[label][0] - center[0],
            canonical_point_model[label][1] - center[1],
        )
        if abs(float(distance) - float(radius)) > 1e-6:
            raise ValueError("sampled secant point is not on the circle")
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    visible_by_canonical = {
        "PA": _visible_segment(label_map, "P", "A"),
        "AB": _visible_segment(label_map, "A", "B"),
        "PB": _visible_segment(label_map, "P", "B"),
        "PC": _visible_segment(label_map, "P", "C"),
        "CD": _visible_segment(label_map, "C", "D"),
        "PD": _visible_segment(label_map, "P", "D"),
    }
    value_by_canonical = {
        "PA": int(pa),
        "AB": int(ab),
        "PB": int(pa + ab),
        "PC": int(pc),
        "CD": int(cd),
        "PD": int(pd),
    }
    token_by_canonical = {
        canonical: f"{visible_by_canonical[canonical]}={value_by_canonical[canonical]}"
        for canonical in ("PA", "AB", "PC", "CD")
    }
    measurement_token_by_canonical = dict(token_by_canonical)
    measurement_token_by_canonical[str(canonical_answer_segment)] = (
        f"{visible_by_canonical[str(canonical_answer_segment)]}=?"
    )
    tokens = tuple(
        str(token_by_canonical[canonical])
        for canonical in ("PA", "AB", "PC", "CD")
        if str(canonical) != str(canonical_answer_segment)
    )
    distractor_angle = _visible_angle(label_map, "A", "P", "C")
    distractor_angle_value = _angle_degrees_at(
        canonical_point_model["P"],
        canonical_point_model["A"],
        canonical_point_model["C"],
    )
    distractor_token = f"{distractor_angle}={int(distractor_angle_value)}"
    theorem_trace = {
        "theorem": "secant_secant_variable",
        "label_map": dict(label_map),
        "target_kind": str(target_kind),
        "PA": int(pa),
        "AB": int(ab),
        "PB": int(pa + ab),
        "PC": int(pc),
        "CD": int(cd),
        "PD": int(pd),
        "canonical_answer_segment": str(canonical_answer_segment),
        "answer_segment": str(visible_by_canonical[str(canonical_answer_segment)]),
        "answer_value": int(spec["answer"]),
        "power_PA_times_PB": int(pa * (pa + ab)),
        "power_PC_times_PD": int(pc * pd),
        "distractor_tokens": [str(distractor_token)],
        "external_point_side": str(external_point_side),
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "PAB": (label_map["P"], label_map["B"]),
            "PCD": (label_map["P"], label_map["D"]),
            "PA": (label_map["P"], label_map["A"]),
            "AB": (label_map["A"], label_map["B"]),
            "PC": (label_map["P"], label_map["C"]),
            "CD": (label_map["C"], label_map["D"]),
        },
        "measurement_specs": (
            (measurement_token_by_canonical["PA"], "PA", 1.0),
            (measurement_token_by_canonical["AB"], "AB", 1.0),
            (measurement_token_by_canonical["PC"], "PC", -1.0),
            (measurement_token_by_canonical["CD"], "CD", 1.0),
        ),
        "angle_marker_specs": (
            {
                "token": distractor_token,
                "vertex": label_map["P"],
                "arm0": label_map["A"],
                "arm1": label_map["C"],
                "radius_px": 38.0,
            },
        ),
        "support_measurement_tokens": tokens,
        "annotation_point_labels": (
            label_map["P"],
            label_map["A"],
            label_map["B"],
            label_map["C"],
            label_map["D"],
        ),
        "annotation_values": {
            str(visible_by_canonical[key]): int(value)
            for key, value in value_by_canonical.items()
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "external_point": str(label_map["P"]),
            "near_point": str(label_map["A"]),
            "far_point": str(label_map["B"]),
            "near_point_alt": str(label_map["C"]),
            "far_point_alt": str(label_map["D"]),
            "inside_segment": str(visible_by_canonical["AB"]),
            "outside_second_segment": str(visible_by_canonical["PC"]),
            "inside_second_segment": str(visible_by_canonical["CD"]),
            "answer_segment": str(visible_by_canonical[str(canonical_answer_segment)]),
        },
    }

__all__ = [
    '_build_diameter_perpendicular_chord_scene',
    '_build_tangent_secant_scene',
    '_build_secant_secant_scene',
    '_build_secant_secant_variable_scene',
]
