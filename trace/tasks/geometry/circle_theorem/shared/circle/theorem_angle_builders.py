"""Angle-theorem scene payload builders for circle-theorem value tasks."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Tuple

from .theorem_common import (
    _ResolvedQuery,
    _EXTERNAL_SECANT_ANGLE_SUPPORT,
    _CYCLIC_QUADRILATERAL_ANGLE_SUPPORT,
    _sample_point_label_map,
    _visible_segment,
    _visible_angle,
    _visible_arc,
    _line_intersection,
    _angle_degrees_at,
)
from .theorem_geometry import (
    _add_points,
    _circle_point,
    _extend_ray,
    _mirror_point_x,
    _rotated_tangent_unit,
    _sample_external_point_side,
    _split_cyclic_arc_sum,
)

def _build_intersecting_chords_arc_scene(
    rng, *, query: _ResolvedQuery
) -> Dict[str, Any]:
    target_arc = int(query.target_answer)
    if int(target_arc) % 10 != 0 or not (40 <= int(target_arc) <= 180):
        raise ValueError(
            f"unsupported target answer for intersecting-chords arc theorem: {query.target_answer}"
        )
    label_map = _sample_point_label_map(rng, ("O", "A", "B", "C", "D", "E"))
    known_arc_candidates = [
        value
        for value in range(40, 171, 10)
        if 35 <= int(360 - int(target_arc) - int(value) - 55)
    ]
    if not known_arc_candidates:
        raise ValueError(f"no feasible known arc for target arc: {query.target_answer}")
    known_arc = int(rng.choice(known_arc_candidates))
    gap_bc_candidates = [
        value
        for value in range(45, 131, 5)
        if int(360 - int(known_arc) - int(target_arc) - int(value)) >= 45
    ]
    if not gap_bc_candidates:
        raise ValueError(f"no feasible arc gap for target arc: {query.target_answer}")
    arc_bc = int(rng.choice(gap_bc_candidates))
    arc_da = int(360 - int(known_arc) - int(target_arc) - int(arc_bc))
    angle_value = int((int(known_arc) + int(target_arc)) // 2)
    radius = float(rng.choice((10, 11, 12, 13, 14)))
    rotation = float(rng.choice((35, 50, 65, 80, 95, 110, 125)))
    center = (0.0, 0.0)
    angles = {
        "A": float(rotation),
        "B": float(rotation + known_arc),
        "C": float(rotation + known_arc + arc_bc),
        "D": float(rotation + known_arc + arc_bc + target_arc),
    }
    canonical_point_model = {
        "O": center,
        "A": _circle_point(radius, angles["A"]),
        "B": _circle_point(radius, angles["B"]),
        "C": _circle_point(radius, angles["C"]),
        "D": _circle_point(radius, angles["D"]),
    }
    canonical_point_model["E"] = _line_intersection(
        canonical_point_model["A"],
        canonical_point_model["C"],
        canonical_point_model["B"],
        canonical_point_model["D"],
    )
    observed_angle = _angle_degrees_at(
        canonical_point_model["E"],
        canonical_point_model["A"],
        canonical_point_model["B"],
    )
    if abs(int(observed_angle) - int(angle_value)) > 1:
        raise ValueError("sampled intersecting-chords angle does not match arc theorem")
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    first_chord = _visible_segment(label_map, "A", "C")
    second_chord = _visible_segment(label_map, "B", "D")
    angle_name = _visible_angle(label_map, "A", "E", "B")
    known_arc_name = _visible_arc(label_map, "A", "B")
    answer_arc_name = _visible_arc(label_map, "C", "D")
    distractor_arc_name = _visible_arc(label_map, "B", "C")
    angle_token = f"{angle_name}={int(angle_value)}"
    known_arc_token = f"{known_arc_name}={int(known_arc)}"
    distractor_token = f"{distractor_arc_name}={int(arc_bc)}"
    query_arc_token = f"{answer_arc_name}=?"
    theorem_trace = {
        "theorem": "intersecting_chords_angle",
        "label_map": dict(label_map),
        "angle_AEB": int(angle_value),
        "arc_AB": int(known_arc),
        "arc_BC": int(arc_bc),
        "arc_CD": int(target_arc),
        "arc_DA": int(arc_da),
        "canonical_answer_segment": "arcCD",
        "answer_segment": str(answer_arc_name),
        "answer_value": int(target_arc),
        "arc_sum_for_angle": int(known_arc + target_arc),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "AC": (label_map["A"], label_map["C"]),
            "BD": (label_map["B"], label_map["D"]),
        },
        "measurement_specs": tuple(),
        "angle_marker_specs": (
            {
                "token": angle_token,
                "vertex": label_map["E"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 42.0,
            },
        ),
        "circle_arc_specs": (
            {"token": known_arc_token, "start": label_map["A"], "end": label_map["B"]},
            {"token": distractor_token, "start": label_map["B"], "end": label_map["C"]},
            {"token": query_arc_token, "start": label_map["C"], "end": label_map["D"]},
        ),
        "support_measurement_tokens": (angle_token, known_arc_token),
        "annotation_point_labels": (
            label_map["A"],
            label_map["E"],
            label_map["B"],
            label_map["C"],
            label_map["D"],
        ),
        "annotation_values": {
            str(angle_name): int(angle_value),
            str(known_arc_name): int(known_arc),
            str(distractor_arc_name): int(arc_bc),
            str(answer_arc_name): int(target_arc),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "first_chord_segment": str(first_chord),
            "second_chord_segment": str(second_chord),
            "intersection_label": str(label_map["E"]),
            "known_arc": str(known_arc_name),
            "answer_arc": str(answer_arc_name),
            "answer_segment": str(answer_arc_name),
        },
    }

def _build_multi_step_angle_scene(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    target_angle = int(query.target_answer)
    if int(target_angle) % 5 != 0 or not (45 <= int(target_angle) <= 135):
        raise ValueError(
            f"unsupported target answer for multi-step circle angle theorem: {query.target_answer}"
        )
    label_map = _sample_point_label_map(rng, ("O", "A", "B", "C", "D", "E"))
    arc_sum = int(2 * int(target_angle))
    known_arc_candidates = [
        value for value in range(40, 171, 10) if 40 <= int(arc_sum - int(value)) <= 170
    ]
    if not known_arc_candidates:
        raise ValueError(
            f"no feasible known arcs for target angle: {query.target_answer}"
        )
    first_arc = int(rng.choice(known_arc_candidates))
    opposite_arc = int(arc_sum - int(first_arc))
    remaining_arc = int(360 - int(first_arc) - int(opposite_arc))
    if int(remaining_arc) < 90:
        raise ValueError(
            f"no feasible remaining arcs for target angle: {query.target_answer}"
        )
    gap_bc_candidates = [
        value
        for value in range(45, int(remaining_arc) - 44, 5)
        if int(remaining_arc - int(value)) >= 45
    ]
    if not gap_bc_candidates:
        raise ValueError(f"no feasible arc gap for target angle: {query.target_answer}")
    arc_bc = int(rng.choice(gap_bc_candidates))
    arc_da = int(remaining_arc - int(arc_bc))
    radius = float(rng.choice((10, 11, 12, 13, 14)))
    rotation = float(rng.choice((30, 45, 60, 75, 90, 105, 120)))
    center = (0.0, 0.0)
    angles = {
        "A": float(rotation),
        "B": float(rotation + first_arc),
        "C": float(rotation + first_arc + arc_bc),
        "D": float(rotation + first_arc + arc_bc + opposite_arc),
    }
    canonical_point_model = {
        "O": center,
        "A": _circle_point(radius, angles["A"]),
        "B": _circle_point(radius, angles["B"]),
        "C": _circle_point(radius, angles["C"]),
        "D": _circle_point(radius, angles["D"]),
    }
    canonical_point_model["E"] = _line_intersection(
        canonical_point_model["A"],
        canonical_point_model["C"],
        canonical_point_model["B"],
        canonical_point_model["D"],
    )
    observed_angle = _angle_degrees_at(
        canonical_point_model["E"],
        canonical_point_model["A"],
        canonical_point_model["B"],
    )
    if abs(int(observed_angle) - int(target_angle)) > 1:
        raise ValueError(
            "sampled multi-step angle does not match intersecting-chords theorem"
        )
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    first_chord = _visible_segment(label_map, "A", "C")
    second_chord = _visible_segment(label_map, "B", "D")
    angle_name = _visible_angle(label_map, "A", "E", "B")
    first_arc_name = _visible_arc(label_map, "A", "B")
    opposite_arc_name = _visible_arc(label_map, "C", "D")
    distractor_arc_name = _visible_arc(label_map, "B", "C")
    answer_angle_token = f"{angle_name}=?"
    first_arc_token = f"{first_arc_name}={int(first_arc)}"
    opposite_arc_token = f"{opposite_arc_name}={int(opposite_arc)}"
    distractor_token = f"{distractor_arc_name}={int(arc_bc)}"
    theorem_trace = {
        "theorem": "intersecting_chords_angle_from_arcs",
        "label_map": dict(label_map),
        "angle_AEB": int(target_angle),
        "arc_AB": int(first_arc),
        "arc_BC": int(arc_bc),
        "arc_CD": int(opposite_arc),
        "arc_DA": int(arc_da),
        "canonical_answer_segment": "angleAEB",
        "answer_segment": str(angle_name),
        "answer_value": int(target_angle),
        "arc_sum_for_angle": int(first_arc + opposite_arc),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "AC": (label_map["A"], label_map["C"]),
            "BD": (label_map["B"], label_map["D"]),
        },
        "measurement_specs": tuple(),
        "angle_marker_specs": (
            {
                "token": answer_angle_token,
                "vertex": label_map["E"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 42.0,
            },
        ),
        "circle_arc_specs": (
            {"token": first_arc_token, "start": label_map["A"], "end": label_map["B"]},
            {"token": distractor_token, "start": label_map["B"], "end": label_map["C"]},
            {
                "token": opposite_arc_token,
                "start": label_map["C"],
                "end": label_map["D"],
            },
        ),
        "support_measurement_tokens": (first_arc_token, opposite_arc_token),
        "annotation_point_labels": (
            label_map["A"],
            label_map["B"],
            label_map["C"],
            label_map["D"],
            label_map["E"],
        ),
        "annotation_values": {
            str(angle_name): int(target_angle),
            str(first_arc_name): int(first_arc),
            str(distractor_arc_name): int(arc_bc),
            str(opposite_arc_name): int(opposite_arc),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "first_chord_segment": str(first_chord),
            "second_chord_segment": str(second_chord),
            "intersection_label": str(label_map["E"]),
            "answer_angle": str(angle_name),
            "answer_segment": str(angle_name),
        },
    }

def _build_inscribed_angle_scene(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    query_id = str(query.query_id)
    if query_id == "central_angle_from_inscribed":
        central_angle = int(query.target_answer)
        if int(central_angle) % 10 != 0 or not (40 <= int(central_angle) <= 160):
            raise ValueError(f"unsupported central angle answer: {query.target_answer}")
        inscribed_angle = int(central_angle // 2)
        answer_kind = "central"
    elif query_id in {"inscribed_angle_from_central", "inscribed_angle_from_arc"}:
        inscribed_angle = int(query.target_answer)
        if int(inscribed_angle) % 5 != 0 or not (20 <= int(inscribed_angle) <= 80):
            raise ValueError(
                f"unsupported inscribed angle answer: {query.target_answer}"
            )
        central_angle = int(2 * int(inscribed_angle))
        answer_kind = "inscribed"
    else:
        raise ValueError(f"unsupported inscribed-angle query: {query_id}")

    radius = float(rng.choice((10, 11, 12, 13, 14)))
    rotation = float(rng.choice((20, 35, 50, 65, 80, 95, 110, 125, 140)))
    c_offset = float(rng.choice((-35, -25, -15, 15, 25, 35)))
    angles = {
        "A": float(rotation - (0.5 * central_angle)),
        "B": float(rotation + (0.5 * central_angle)),
        "C": float(rotation + 180.0 + c_offset),
    }
    center = (0.0, 0.0)
    canonical_point_model = {
        "O": center,
        "A": _circle_point(radius, angles["A"]),
        "B": _circle_point(radius, angles["B"]),
        "C": _circle_point(radius, angles["C"]),
    }
    observed_inscribed = _angle_degrees_at(
        canonical_point_model["C"],
        canonical_point_model["A"],
        canonical_point_model["B"],
    )
    observed_central = _angle_degrees_at(
        canonical_point_model["O"],
        canonical_point_model["A"],
        canonical_point_model["B"],
    )
    if abs(int(observed_inscribed) - int(inscribed_angle)) > 1:
        raise ValueError("sampled inscribed angle does not match intercepted arc")
    if abs(int(observed_central) - int(central_angle)) > 1:
        raise ValueError("sampled central angle does not match intercepted arc")

    label_map = _sample_point_label_map(rng, ("O", "A", "B", "C"))
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    central_angle_name = _visible_angle(label_map, "A", "O", "B")
    inscribed_angle_name = _visible_angle(label_map, "A", "C", "B")
    intercepted_arc_name = _visible_arc(label_map, "A", "B")
    distractor_arc_name = _visible_arc(label_map, "B", "C")
    raw_distractor_arc = float((angles["C"] - angles["B"]) % 360.0)
    distractor_arc = int(
        round(min(raw_distractor_arc, 360.0 - raw_distractor_arc) / 5.0) * 5
    )

    token_by_kind = {
        "central": f"{central_angle_name}={int(central_angle)}",
        "inscribed": f"{inscribed_angle_name}={int(inscribed_angle)}",
        "arc": f"{intercepted_arc_name}={int(central_angle)}",
    }
    if query_id == "inscribed_angle_from_central":
        support_measurement_tokens = (token_by_kind["central"],)
        annotation_point_labels = (
            label_map["A"],
            label_map["O"],
            label_map["B"],
            label_map["C"],
        )
        angle_marker_specs = (
            {
                "token": token_by_kind["central"],
                "vertex": label_map["O"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 48.0,
            },
            {
                "token": f"{inscribed_angle_name}=?",
                "vertex": label_map["C"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 42.0,
            },
        )
        circle_arc_specs = (
            {
                "token": f"{distractor_arc_name}={int(distractor_arc)}",
                "start": label_map["B"],
                "end": label_map["C"],
            },
        )
    elif query_id == "central_angle_from_inscribed":
        support_measurement_tokens = (token_by_kind["inscribed"],)
        annotation_point_labels = (
            label_map["A"],
            label_map["C"],
            label_map["B"],
            label_map["O"],
        )
        angle_marker_specs = (
            {
                "token": f"{central_angle_name}=?",
                "vertex": label_map["O"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 48.0,
            },
            {
                "token": token_by_kind["inscribed"],
                "vertex": label_map["C"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 42.0,
            },
        )
        circle_arc_specs = (
            {
                "token": f"{distractor_arc_name}={int(distractor_arc)}",
                "start": label_map["B"],
                "end": label_map["C"],
            },
        )
    else:
        support_measurement_tokens = (token_by_kind["arc"],)
        annotation_point_labels = (
            label_map["A"],
            label_map["B"],
            label_map["C"],
        )
        angle_marker_specs = (
            {
                "token": f"{inscribed_angle_name}=?",
                "vertex": label_map["C"],
                "arm0": label_map["A"],
                "arm1": label_map["B"],
                "radius_px": 42.0,
            },
        )
        circle_arc_specs = (
            {
                "token": token_by_kind["arc"],
                "start": label_map["A"],
                "end": label_map["B"],
            },
            {
                "token": f"{distractor_arc_name}={int(distractor_arc)}",
                "start": label_map["B"],
                "end": label_map["C"],
            },
        )

    answer_name = (
        central_angle_name if answer_kind == "central" else inscribed_angle_name
    )
    answer_value = int(central_angle if answer_kind == "central" else inscribed_angle)
    distractor_token = f"{distractor_arc_name}={int(distractor_arc)}"
    theorem_trace = {
        "theorem": "inscribed_angle",
        "label_map": dict(label_map),
        "central_angle_AOB": int(central_angle),
        "inscribed_angle_ACB": int(inscribed_angle),
        "arc_AB": int(central_angle),
        "arc_BC": int(distractor_arc),
        "canonical_answer_segment": (
            "angleAOB" if answer_kind == "central" else "angleACB"
        ),
        "answer_segment": str(answer_name),
        "answer_value": int(answer_value),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "OA": (label_map["O"], label_map["A"]),
            "OB": (label_map["O"], label_map["B"]),
            "CA": (label_map["C"], label_map["A"]),
            "CB": (label_map["C"], label_map["B"]),
        },
        "measurement_specs": tuple(),
        "angle_marker_specs": angle_marker_specs,
        "circle_arc_specs": circle_arc_specs,
        "support_measurement_tokens": support_measurement_tokens,
        "annotation_point_labels": annotation_point_labels,
        "annotation_values": {
            str(central_angle_name): int(central_angle),
            str(inscribed_angle_name): int(inscribed_angle),
            str(intercepted_arc_name): int(central_angle),
            str(distractor_arc_name): int(distractor_arc),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "central_angle": str(central_angle_name),
            "inscribed_angle": str(inscribed_angle_name),
            "intercepted_arc": str(intercepted_arc_name),
            "answer_angle": str(answer_name),
            "answer_segment": str(answer_name),
        },
    }

def _build_tangent_chord_angle_scene(rng, *, query: _ResolvedQuery) -> Dict[str, Any]:
    query_id = str(query.query_id)
    tangent_chord_angle = int(query.target_answer)
    if int(tangent_chord_angle) % 5 != 0 or not (25 <= int(tangent_chord_angle) <= 75):
        raise ValueError(
            f"unsupported tangent-chord angle answer: {query.target_answer}"
        )
    if query_id not in {
        "tangent_chord_angle_from_arc",
        "tangent_chord_angle_from_inscribed",
    }:
        raise ValueError(f"unsupported tangent-chord query: {query_id}")

    central_angle = int(2 * int(tangent_chord_angle))
    radius = float(rng.choice((10, 11, 12, 13, 14)))
    rotation = float(rng.choice((10, 25, 40, 55, 70, 85, 100, 115, 130)))
    tangent_unit = _rotated_tangent_unit(rotation)
    point_t = _circle_point(radius, rotation)
    point_a = _circle_point(radius, rotation + central_angle)
    arc_ab = int(rng.choice((105, 120, 135, 150)))
    point_b = _circle_point(radius, rotation + central_angle + float(arc_ab))
    point_p = _add_points(point_t, tangent_unit, scale=float(radius * 1.05))
    center = (0.0, 0.0)
    canonical_point_model = {
        "O": center,
        "P": point_p,
        "T": point_t,
        "A": point_a,
        "B": point_b,
    }
    observed_tangent_angle = _angle_degrees_at(
        canonical_point_model["T"],
        canonical_point_model["P"],
        canonical_point_model["A"],
    )
    observed_inscribed = _angle_degrees_at(
        canonical_point_model["B"],
        canonical_point_model["T"],
        canonical_point_model["A"],
    )
    if abs(int(observed_tangent_angle) - int(tangent_chord_angle)) > 1:
        raise ValueError("sampled tangent-chord angle does not match intercepted arc")
    if abs(int(observed_inscribed) - int(tangent_chord_angle)) > 1:
        raise ValueError("sampled inscribed angle does not match tangent-chord angle")

    label_map = _sample_point_label_map(rng, ("O", "P", "T", "A", "B"))
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    tangent_chord_angle_name = _visible_angle(label_map, "P", "T", "A")
    inscribed_angle_name = _visible_angle(label_map, "T", "B", "A")
    intercepted_arc_name = _visible_arc(label_map, "T", "A")
    distractor_arc_name = _visible_arc(label_map, "A", "B")
    distractor_arc = int(arc_ab)
    answer_token = f"{tangent_chord_angle_name}=?"
    arc_token = f"{intercepted_arc_name}={int(central_angle)}"
    inscribed_token = f"{inscribed_angle_name}={int(tangent_chord_angle)}"
    distractor_token = f"{distractor_arc_name}={int(distractor_arc)}"
    if query_id == "tangent_chord_angle_from_arc":
        support_measurement_tokens = (arc_token,)
        annotation_point_labels = (
            label_map["P"],
            label_map["T"],
            label_map["A"],
        )
        extra_angle_token: str | None = None
    else:
        support_measurement_tokens = (inscribed_token,)
        annotation_point_labels = (
            label_map["P"],
            label_map["T"],
            label_map["A"],
            label_map["B"],
        )
        extra_angle_token = inscribed_token

    angle_marker_specs: Tuple[Mapping[str, Any], ...]
    if extra_angle_token is None:
        angle_marker_specs = (
            {
                "token": answer_token,
                "vertex": label_map["T"],
                "arm0": label_map["P"],
                "arm1": label_map["A"],
                "radius_px": 42.0,
            },
        )
    else:
        angle_marker_specs = (
            {
                "token": answer_token,
                "vertex": label_map["T"],
                "arm0": label_map["P"],
                "arm1": label_map["A"],
                "radius_px": 42.0,
            },
            {
                "token": extra_angle_token,
                "vertex": label_map["B"],
                "arm0": label_map["T"],
                "arm1": label_map["A"],
                "radius_px": 38.0,
            },
        )

    circle_arc_specs = (
        {
            "token": (
                arc_token if query_id == "tangent_chord_angle_from_arc" else None
            ),
            "start": label_map["T"],
            "end": label_map["A"],
        },
        {"token": distractor_token, "start": label_map["A"], "end": label_map["B"]},
    )
    theorem_trace = {
        "theorem": "tangent_chord_angle",
        "label_map": dict(label_map),
        "angle_PTA": int(tangent_chord_angle),
        "angle_TBA": int(tangent_chord_angle),
        "arc_TA": int(central_angle),
        "arc_AB": int(distractor_arc),
        "canonical_answer_segment": "anglePTA",
        "answer_segment": str(tangent_chord_angle_name),
        "answer_value": int(tangent_chord_angle),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "PT": (label_map["P"], label_map["T"]),
            "TA": (label_map["T"], label_map["A"]),
            "OT": (label_map["O"], label_map["T"]),
            "BT": (label_map["B"], label_map["T"]),
            "BA": (label_map["B"], label_map["A"]),
        },
        "measurement_specs": tuple(),
        "angle_marker_specs": angle_marker_specs,
        "circle_arc_specs": circle_arc_specs,
        "support_measurement_tokens": support_measurement_tokens,
        "annotation_point_labels": annotation_point_labels,
        "annotation_values": {
            str(tangent_chord_angle_name): int(tangent_chord_angle),
            str(inscribed_angle_name): int(tangent_chord_angle),
            str(intercepted_arc_name): int(central_angle),
            str(distractor_arc_name): int(distractor_arc),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "tangent_chord_angle": str(tangent_chord_angle_name),
            "inscribed_angle": str(inscribed_angle_name),
            "intercepted_arc": str(intercepted_arc_name),
            "answer_angle": str(tangent_chord_angle_name),
            "answer_segment": str(tangent_chord_angle_name),
        },
    }

def _build_external_secant_angle_scene(
    rng, *, query: _ResolvedQuery
) -> Dict[str, Any]:
    target_angle = int(query.target_answer)
    if int(target_angle) not in _EXTERNAL_SECANT_ANGLE_SUPPORT:
        raise ValueError(
            f"unsupported target answer for external secant angle theorem: {query.target_answer}"
        )
    beta_candidates = [
        value
        for value in range(10, 61, 5)
        if int(value + target_angle) <= 85
        and int(180 - (value + target_angle) - value) >= 35
    ]
    if not beta_candidates:
        raise ValueError(
            f"no feasible intercepted arcs for external secant angle: {query.target_answer}"
        )
    beta = int(rng.choice(beta_candidates))
    alpha = int(beta + target_angle)
    near_arc = int(2 * beta)
    far_arc = int(2 * alpha)
    distractor_arc = int(180 - alpha - beta)
    radius = float(rng.choice((10, 11, 12, 13, 14)))
    rotation = float(rng.choice((-15, -8, 0, 8, 15)))
    center = (0.0, 0.0)
    angles = {
        "A": float(180 - alpha + rotation),
        "B": float(beta + rotation),
        "C": float(180 + alpha + rotation),
        "D": float(360 - beta + rotation),
    }
    canonical_point_model = {
        "O": center,
        "A": _circle_point(radius, angles["A"]),
        "B": _circle_point(radius, angles["B"]),
        "C": _circle_point(radius, angles["C"]),
        "D": _circle_point(radius, angles["D"]),
    }
    canonical_point_model["P"] = _line_intersection(
        canonical_point_model["A"],
        canonical_point_model["B"],
        canonical_point_model["C"],
        canonical_point_model["D"],
    )
    observed_angle = _angle_degrees_at(
        canonical_point_model["P"],
        canonical_point_model["B"],
        canonical_point_model["D"],
    )
    if abs(int(observed_angle) - int(target_angle)) > 1:
        raise ValueError("sampled external secant angle does not match arc theorem")
    if (
        math.hypot(
            float(canonical_point_model["P"][0]) - float(center[0]),
            float(canonical_point_model["P"][1]) - float(center[1]),
        )
        <= float(radius) * 1.03
    ):
        raise ValueError("sampled external secant point is not outside the circle")

    external_point_side = _sample_external_point_side(rng)
    if str(external_point_side) == "left":
        canonical_point_model = {
            str(label): _mirror_point_x(point)
            for label, point in canonical_point_model.items()
        }
        center = _mirror_point_x(center)
    elif str(external_point_side) != "right":
        raise ValueError(f"unsupported external point side: {external_point_side!r}")

    label_map = _sample_point_label_map(rng, ("O", "P", "A", "B", "C", "D"))
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    answer_angle_name = _visible_angle(label_map, "B", "P", "D")
    far_arc_name = _visible_arc(label_map, "A", "C")
    near_arc_name = _visible_arc(label_map, "B", "D")
    distractor_arc_name = _visible_arc(label_map, "A", "B")
    answer_token = f"{answer_angle_name}=?"
    far_arc_token = f"{far_arc_name}={int(far_arc)}"
    near_arc_token = f"{near_arc_name}={int(near_arc)}"
    distractor_token = f"{distractor_arc_name}={int(distractor_arc)}"
    theorem_trace = {
        "theorem": "external_secant_angle_from_arcs",
        "label_map": dict(label_map),
        "angle_BPD": int(target_angle),
        "arc_AC": int(far_arc),
        "arc_BD": int(near_arc),
        "arc_AB": int(distractor_arc),
        "canonical_answer_segment": "angleBPD",
        "answer_segment": str(answer_angle_name),
        "answer_value": int(target_angle),
        "far_intercepted_arc_measure": int(far_arc),
        "near_intercepted_arc_measure": int(near_arc),
        "arc_difference_for_angle": int(far_arc - near_arc),
        "external_point_side": str(external_point_side),
        "distractor_tokens": [str(distractor_token)],
    }
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": {
            "first_secant": (label_map["P"], label_map["A"]),
            "second_secant": (label_map["P"], label_map["C"]),
        },
        "measurement_specs": tuple(),
        "angle_marker_specs": (
            {
                "token": answer_token,
                "vertex": label_map["P"],
                "arm0": label_map["B"],
                "arm1": label_map["D"],
                "radius_px": 42.0,
            },
        ),
        "circle_arc_specs": (
            {"token": far_arc_token, "start": label_map["A"], "end": label_map["C"]},
            {"token": near_arc_token, "start": label_map["B"], "end": label_map["D"]},
            {
                "token": distractor_token,
                "start": label_map["A"],
                "end": label_map["B"],
            },
        ),
        "support_measurement_tokens": (far_arc_token, near_arc_token),
        "annotation_point_labels": (
            label_map["P"],
            label_map["B"],
            label_map["A"],
            label_map["D"],
            label_map["C"],
        ),
        "annotation_values": {
            str(answer_angle_name): int(target_angle),
            str(far_arc_name): int(far_arc),
            str(near_arc_name): int(near_arc),
            str(distractor_arc_name): int(distractor_arc),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "external_point": str(label_map["P"]),
            "near_point": str(label_map["B"]),
            "far_point": str(label_map["A"]),
            "near_point_alt": str(label_map["D"]),
            "far_point_alt": str(label_map["C"]),
            "near_arc": str(near_arc_name),
            "far_arc": str(far_arc_name),
            "answer_angle": str(answer_angle_name),
            "answer_segment": str(answer_angle_name),
        },
    }

def _build_cyclic_quadrilateral_angle_scene(
    rng, *, query: _ResolvedQuery
) -> Dict[str, Any]:
    target_angle = int(query.target_answer)
    if int(target_angle) not in _CYCLIC_QUADRILATERAL_ANGLE_SUPPORT:
        raise ValueError(
            f"unsupported target answer for cyclic quadrilateral angle theorem: {query.target_answer}"
        )
    query_id = str(query.query_id)
    if query_id not in {
        "opposite_angle_supplement",
        "exterior_angle_from_opposite_interior",
    }:
        raise ValueError(f"unsupported cyclic quadrilateral query: {query.query_id}")

    target_vertex = str(rng.choice(("B", "D")))
    if query_id == "opposite_angle_supplement":
        angle_b = int(target_angle if target_vertex == "B" else 180 - target_angle)
        known_vertex = "D" if target_vertex == "B" else "B"
        target_canonical_angle = "ABC" if target_vertex == "B" else "CDA"
        known_canonical_angle = "CDA" if target_vertex == "B" else "ABC"
        exterior_point = None
    else:
        exterior_vertex = target_vertex
        if exterior_vertex == "D":
            angle_b = int(target_angle)
            known_vertex = "B"
            target_canonical_angle = "ADE"
            known_canonical_angle = "ABC"
        else:
            angle_b = int(180 - target_angle)
            known_vertex = "D"
            target_canonical_angle = "EBC"
            known_canonical_angle = "CDA"
        exterior_point = "E"

    arc_cd_plus_da = int(2 * angle_b)
    arc_ab_plus_bc = int(360 - arc_cd_plus_da)
    arc_ab, arc_bc = _split_cyclic_arc_sum(rng, arc_ab_plus_bc)
    arc_cd, arc_da = _split_cyclic_arc_sum(rng, arc_cd_plus_da)
    radius = float(rng.choice((10, 11, 12, 13, 14)))
    rotation = float(rng.choice((12, 28, 44, 60, 76, 92, 108)))
    center = (0.0, 0.0)
    angles = {
        "A": float(rotation),
        "B": float(rotation + arc_ab),
        "C": float(rotation + arc_ab + arc_bc),
        "D": float(rotation + arc_ab + arc_bc + arc_cd),
    }
    canonical_point_model = {
        "O": center,
        "A": _circle_point(radius, angles["A"]),
        "B": _circle_point(radius, angles["B"]),
        "C": _circle_point(radius, angles["C"]),
        "D": _circle_point(radius, angles["D"]),
    }
    if exterior_point == "E":
        extension_length = float(radius) * float(rng.choice((0.34, 0.42, 0.50)))
        if target_canonical_angle == "ADE":
            canonical_point_model["E"] = _extend_ray(
                canonical_point_model["C"],
                canonical_point_model["D"],
                distance=extension_length,
            )
        else:
            canonical_point_model["E"] = _extend_ray(
                canonical_point_model["A"],
                canonical_point_model["B"],
                distance=extension_length,
            )

    angle_abc = _angle_degrees_at(
        canonical_point_model["B"],
        canonical_point_model["A"],
        canonical_point_model["C"],
    )
    angle_cda = _angle_degrees_at(
        canonical_point_model["D"],
        canonical_point_model["C"],
        canonical_point_model["A"],
    )
    if abs(int(angle_abc) + int(angle_cda) - 180) > 1:
        raise ValueError("sampled cyclic quadrilateral angles are not supplementary")
    angle_by_canonical = {
        "ABC": int(angle_abc),
        "CDA": int(angle_cda),
        "DAB": _angle_degrees_at(
            canonical_point_model["A"],
            canonical_point_model["D"],
            canonical_point_model["B"],
        ),
        "BCD": _angle_degrees_at(
            canonical_point_model["C"],
            canonical_point_model["B"],
            canonical_point_model["D"],
        ),
    }
    if query_id == "exterior_angle_from_opposite_interior":
        if target_canonical_angle == "ADE":
            angle_by_canonical["ADE"] = _angle_degrees_at(
                canonical_point_model["D"],
                canonical_point_model["A"],
                canonical_point_model["E"],
            )
        else:
            angle_by_canonical["EBC"] = _angle_degrees_at(
                canonical_point_model["B"],
                canonical_point_model["E"],
                canonical_point_model["C"],
            )
    if abs(int(angle_by_canonical[target_canonical_angle]) - int(target_angle)) > 1:
        raise ValueError("sampled cyclic quadrilateral target angle does not match")

    labels = ("O", "A", "B", "C", "D", "E") if exterior_point else ("O", "A", "B", "C", "D")
    label_map = _sample_point_label_map(rng, labels)
    point_model = {
        label_map[key]: value for key, value in canonical_point_model.items()
    }
    visible_angle_by_canonical = {
        "ABC": _visible_angle(label_map, "A", "B", "C"),
        "CDA": _visible_angle(label_map, "C", "D", "A"),
        "DAB": _visible_angle(label_map, "D", "A", "B"),
        "BCD": _visible_angle(label_map, "B", "C", "D"),
    }
    if exterior_point:
        visible_angle_by_canonical["ADE"] = _visible_angle(label_map, "A", "D", "E")
        visible_angle_by_canonical["EBC"] = _visible_angle(label_map, "E", "B", "C")
    answer_angle_name = str(visible_angle_by_canonical[target_canonical_angle])
    known_angle_name = str(visible_angle_by_canonical[known_canonical_angle])
    distractor_canonical_angle = "DAB" if target_canonical_angle != "DAB" else "BCD"
    distractor_angle_name = str(visible_angle_by_canonical[distractor_canonical_angle])
    answer_token = f"{answer_angle_name}=?"
    known_token = f"{known_angle_name}={int(angle_by_canonical[known_canonical_angle])}"
    distractor_token = (
        f"{distractor_angle_name}={int(angle_by_canonical[distractor_canonical_angle])}"
    )
    angle_marker_specs = (
        {
            "token": known_token,
            "vertex": label_map[known_canonical_angle[1]],
            "arm0": label_map[known_canonical_angle[0]],
            "arm1": label_map[known_canonical_angle[2]],
            "radius_px": 42.0,
        },
        {
            "token": answer_token,
            "vertex": label_map[target_canonical_angle[1]],
            "arm0": label_map[target_canonical_angle[0]],
            "arm1": label_map[target_canonical_angle[2]],
            "radius_px": 42.0,
        },
        {
            "token": distractor_token,
            "vertex": label_map[distractor_canonical_angle[1]],
            "arm0": label_map[distractor_canonical_angle[0]],
            "arm1": label_map[distractor_canonical_angle[2]],
            "radius_px": 34.0,
        },
    )
    segments = {
        "AB": (label_map["A"], label_map["B"]),
        "BC": (label_map["B"], label_map["C"]),
        "CD": (label_map["C"], label_map["D"]),
        "DA": (label_map["D"], label_map["A"]),
    }
    if exterior_point:
        if target_canonical_angle == "ADE":
            segments["DE"] = (label_map["D"], label_map["E"])
        else:
            segments["BE"] = (label_map["B"], label_map["E"])
    annotation_point_labels = (
        (label_map["A"], label_map["B"], label_map["C"], label_map["D"], label_map["E"])
        if exterior_point
        else (label_map["A"], label_map["B"], label_map["C"], label_map["D"])
    )
    theorem_trace = {
        "theorem": "cyclic_quadrilateral_angle",
        "label_map": dict(label_map),
        "angle_ABC": int(angle_by_canonical["ABC"]),
        "angle_CDA": int(angle_by_canonical["CDA"]),
        "angle_DAB": int(angle_by_canonical["DAB"]),
        "angle_BCD": int(angle_by_canonical["BCD"]),
        "target_vertex": str(target_vertex),
        "known_vertex": str(known_vertex),
        "canonical_known_angle": str("angle" + known_canonical_angle),
        "known_angle": str(known_angle_name),
        "canonical_answer_segment": str("angle" + target_canonical_angle),
        "answer_segment": str(answer_angle_name),
        "answer_value": int(target_angle),
        "opposite_angle_sum": 180,
        "distractor_tokens": [str(distractor_token)],
    }
    if exterior_point:
        theorem_trace["exterior_vertex"] = str(target_vertex)
        theorem_trace[f"angle_{target_canonical_angle}"] = int(
            angle_by_canonical[target_canonical_angle]
        )
        theorem_trace["extension_point"] = str(label_map["E"])
    return {
        "point_model": point_model,
        "circle_center": center,
        "circle_radius": float(radius),
        "segments": segments,
        "measurement_specs": tuple(),
        "angle_marker_specs": angle_marker_specs,
        "circle_arc_specs": tuple(),
        "support_measurement_tokens": (known_token,),
        "annotation_point_labels": annotation_point_labels,
        "annotation_values": {
            str(answer_angle_name): int(target_angle),
            str(known_angle_name): int(angle_by_canonical[known_canonical_angle]),
            str(distractor_angle_name): int(angle_by_canonical[distractor_canonical_angle]),
        },
        "theorem_trace": theorem_trace,
        "prompt_slots": {
            "known_angle": str(known_angle_name),
            "answer_angle": str(answer_angle_name),
            "extension_point": "" if not exterior_point else str(label_map["E"]),
            "answer_segment": str(answer_angle_name),
        },
    }

__all__ = [
    '_build_intersecting_chords_arc_scene',
    '_build_multi_step_angle_scene',
    '_build_inscribed_angle_scene',
    '_build_tangent_chord_angle_scene',
    '_build_external_secant_angle_scene',
    '_build_cyclic_quadrilateral_angle_scene',
]
