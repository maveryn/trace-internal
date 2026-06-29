"""Construction pools for triangle-relations analytical diagrams."""

from __future__ import annotations

import math
from typing import Any, Callable, Iterable, Mapping

from trace.tasks.geometry.shared.measurement_rendering import fmt_measure, round1
from trace.tasks.geometry.shared.vector2d import mid

from .state import AngleLabel, RightAngleMark, SegmentLabel, TickGroup, TriangleRelationsCase

DEGREE_SYMBOL = chr(176)


def _case(
    *,
    case_kind: str,
    answer: int | float,
    answer_type: str,
    formula_family: str,
    formula_text: str,
    reasoning_steps: int,
    vertices: Mapping[str, tuple[float, float]],
    edges: Iterable[tuple[str, str]],
    polygons: Iterable[tuple[str, ...]],
    segment_labels: Iterable[SegmentLabel],
    target_segment: tuple[str, str] | None = None,
    target_point: str | None = None,
    point_annotation_labels: Iterable[str] = (),
    angle_labels: Iterable[AngleLabel] = (),
    right_angles: Iterable[RightAngleMark] = (),
    tick_groups: Iterable[TickGroup] = (),
    filled_polygons: Iterable[tuple[str, ...]] = (),
    trace_values: Mapping[str, Any] | None = None,
    answer_rounding: str = "integer",
) -> TriangleRelationsCase:
    """Normalize one resolved construction into the scene state dataclass."""

    return TriangleRelationsCase(
        case_kind=str(case_kind),
        answer=int(answer) if str(answer_type) == "integer" else float(round1(float(answer))),
        answer_type=str(answer_type),
        answer_rounding=str(answer_rounding),
        formula_family=str(formula_family),
        formula_text=str(formula_text),
        reasoning_steps=int(reasoning_steps),
        vertices={str(key): (float(value[0]), float(value[1])) for key, value in vertices.items()},
        edges=tuple((str(a), str(b)) for a, b in edges),
        polygons=tuple(tuple(str(label) for label in polygon) for polygon in polygons),
        segment_labels=tuple(segment_labels),
        target_segment=target_segment,
        target_point=target_point,
        point_annotation_labels=tuple(str(label) for label in point_annotation_labels),
        angle_labels=tuple(angle_labels),
        right_angles=tuple(right_angles),
        tick_groups=tuple(tick_groups),
        filled_polygons=tuple(tuple(str(label) for label in polygon) for polygon in filled_polygons),
        trace_values=dict(trace_values or {}),
    )


def _triangle_scale_points(split_ratio: float) -> dict[str, tuple[float, float]]:
    a, b, c = (360.0, 110.0), (135.0, 430.0), (605.0, 430.0)
    d = (a[0] + (b[0] - a[0]) * split_ratio, a[1] + (b[1] - a[1]) * split_ratio)
    e = (a[0] + (c[0] - a[0]) * split_ratio, a[1] + (c[1] - a[1]) * split_ratio)
    return {"A": a, "B": b, "C": c, "D": d, "E": e}


def _nested_triangle_case(
    *,
    case_kind: str,
    answer: int,
    labels: tuple[SegmentLabel, ...],
    target_segment: tuple[str, str],
    split_ratio: float,
    formula_family: str,
    formula_text: str,
    trace_values: Mapping[str, Any],
) -> TriangleRelationsCase:
    return _case(
        case_kind=case_kind,
        answer=int(answer),
        answer_type="integer",
        formula_family=formula_family,
        formula_text=formula_text,
        reasoning_steps=3,
        vertices=_triangle_scale_points(float(split_ratio)),
        edges=(("A", "B"), ("A", "C"), ("B", "C"), ("D", "E")),
        polygons=(("A", "B", "C"),),
        segment_labels=labels,
        target_segment=target_segment,
        tick_groups=(TickGroup((("D", "E"), ("B", "C")), kind="parallel"),),
        trace_values=trace_values,
    )


def similar_side_cases() -> tuple[TriangleRelationsCase, ...]:
    cases: list[TriangleRelationsCase] = []
    for ad in range(2, 9):
        for db in range(2, 10):
            for ae in range(2, 18):
                if (ae * db) % ad != 0:
                    continue
                ec = (ae * db) // ad
                if not 2 <= ec <= 42:
                    continue
                ratio = ad / float(ad + db)
                cases.append(
                    _nested_triangle_case(
                        case_kind="nested_similarity_side",
                        answer=ec,
                        labels=(
                            SegmentLabel(("A", "D"), str(ad), -30.0, "AD"),
                            SegmentLabel(("D", "B"), str(db), -30.0, "DB"),
                            SegmentLabel(("A", "E"), str(ae), 30.0, "AE"),
                            SegmentLabel(("E", "C"), "EC=?", 30.0, "EC"),
                        ),
                        target_segment=("E", "C"),
                        split_ratio=ratio,
                        formula_family="similar_triangles_side_transfer",
                        formula_text="EC = AE * DB / AD",
                        trace_values={"AD": ad, "DB": db, "AE": ae, "EC": ec},
                    )
                )
    return tuple(cases[:180])


def parallel_section_cross_cases() -> tuple[TriangleRelationsCase, ...]:
    cases: list[TriangleRelationsCase] = []
    for ad in range(2, 10):
        for db in range(2, 11):
            ab = ad + db
            for bc in range(10, 80):
                if (bc * ad) % ab != 0:
                    continue
                de = (bc * ad) // ab
                if not 3 <= de <= 45:
                    continue
                cases.append(
                    _nested_triangle_case(
                        case_kind="parallel_cross_section",
                        answer=de,
                        labels=(
                            SegmentLabel(("A", "D"), str(ad), -30.0, "AD"),
                            SegmentLabel(("D", "B"), str(db), -30.0, "DB"),
                            SegmentLabel(("B", "C"), str(bc), 34.0, "BC"),
                            SegmentLabel(("D", "E"), "DE=?", -30.0, "DE"),
                        ),
                        target_segment=("D", "E"),
                        split_ratio=ad / float(ab),
                        formula_family="parallel_section_scale",
                        formula_text="DE = BC * AD / (AD + DB)",
                        trace_values={"AD": ad, "DB": db, "AB": ab, "BC": bc, "DE": de},
                    )
                )
    return tuple(cases[:180])


def parallel_section_base_cases() -> tuple[TriangleRelationsCase, ...]:
    cases: list[TriangleRelationsCase] = []
    for ad in range(2, 10):
        for db in range(2, 11):
            ab = ad + db
            for de in range(3, 46):
                if (de * ab) % ad != 0:
                    continue
                bc = (de * ab) // ad
                if not 10 <= bc <= 90:
                    continue
                cases.append(
                    _nested_triangle_case(
                        case_kind="parallel_base_scale",
                        answer=bc,
                        labels=(
                            SegmentLabel(("A", "D"), str(ad), -30.0, "AD"),
                            SegmentLabel(("D", "B"), str(db), -30.0, "DB"),
                            SegmentLabel(("D", "E"), str(de), -30.0, "DE"),
                            SegmentLabel(("B", "C"), "BC=?", 34.0, "BC"),
                        ),
                        target_segment=("B", "C"),
                        split_ratio=ad / float(ab),
                        formula_family="parallel_section_scale",
                        formula_text="BC = DE * (AD + DB) / AD",
                        trace_values={"AD": ad, "DB": db, "AB": ab, "DE": de, "BC": bc},
                    )
                )
    return tuple(cases[:180])


def chained_rectangle_diagonal_cases() -> tuple[TriangleRelationsCase, ...]:
    """Build two-step Pythagorean cases over one split rectangle diagram."""

    rows = (
        (5, 12, 13, 4, 15),
        (5, 12, 13, 11, 20),
        (8, 15, 17, 12, 25),
        (7, 24, 25, 3, 26),
        (15, 20, 25, 6, 29),
        (20, 21, 29, 8, 35),
        (9, 40, 41, 31, 50),
        (12, 35, 37, 4, 52),
    )
    cases: list[TriangleRelationsCase] = []
    for left_w, height, left_diag, right_w, target_diag in rows:
        total_w = left_w + right_w
        scale = min(24.0, 440.0 / total_w, 280.0 / height)
        a = (150.0, 420.0)
        e = (a[0] + left_w * scale, a[1])
        b = (a[0] + total_w * scale, a[1])
        d = (a[0], a[1] - height * scale)
        f = (e[0], d[1])
        c = (b[0], d[1])
        cases.append(
            _case(
                case_kind="split_rectangle_diagonal",
                answer=target_diag,
                answer_type="integer",
                formula_family="two_step_pythagorean_length",
                formula_text="height from left diagonal, then target diagonal from total width",
                reasoning_steps=4,
                vertices={"A": a, "B": b, "C": c, "D": d, "E": e, "F": f},
                edges=(("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"), ("E", "F"), ("D", "E"), ("D", "B")),
                polygons=(("A", "B", "C", "D"),),
                segment_labels=(
                    SegmentLabel(("A", "E"), str(left_w), 28.0, "AE"),
                    SegmentLabel(("E", "B"), str(right_w), 28.0, "EB"),
                    SegmentLabel(("D", "E"), str(left_diag), -30.0, "DE"),
                    SegmentLabel(("D", "B"), "DB=?", -30.0, "DB"),
                ),
                target_segment=("D", "B"),
                right_angles=(RightAngleMark("A", "B", "D"),),
                filled_polygons=(("A", "B", "C", "D"),),
                trace_values={
                    "AE": left_w,
                    "EB": right_w,
                    "DE": left_diag,
                    "derived_AD": height,
                    "AB": total_w,
                    "DB": target_diag,
                },
            )
        )
    return tuple(cases)


def rectangle_triangle_shared_height_cases() -> tuple[TriangleRelationsCase, ...]:
    """Build cases where a rectangle diagonal exposes the adjacent triangle height."""

    rows = (
        (5, 12, 13, 9, 15),
        (8, 15, 17, 20, 25),
        (7, 24, 25, 10, 26),
        (15, 20, 25, 21, 29),
        (20, 21, 29, 28, 35),
        (12, 35, 37, 12, 37),
    )
    cases: list[TriangleRelationsCase] = []
    for rect_w, height, rect_diag, base, hyp in rows:
        scale = min(22.0, 220.0 / rect_w, 260.0 / base, 275.0 / height)
        b = (335.0, 420.0)
        a = (b[0] - rect_w * scale, b[1])
        c = (b[0] + base * scale, b[1])
        d = (b[0], b[1] - height * scale)
        e = (a[0], d[1])
        cases.append(
            _case(
                case_kind="rectangle_triangle_shared_height",
                answer=hyp,
                answer_type="integer",
                formula_family="two_step_pythagorean_length",
                formula_text="shared height from rectangle diagonal, then triangle hypotenuse",
                reasoning_steps=4,
                vertices={"A": a, "B": b, "C": c, "D": d, "E": e},
                edges=(("A", "B"), ("B", "D"), ("D", "E"), ("E", "A"), ("B", "C"), ("C", "D"), ("A", "D")),
                polygons=(("A", "B", "D", "E"), ("B", "C", "D")),
                segment_labels=(
                    SegmentLabel(("A", "B"), str(rect_w), 28.0, "AB"),
                    SegmentLabel(("A", "D"), str(rect_diag), -30.0, "AD"),
                    SegmentLabel(("B", "C"), str(base), 28.0, "BC"),
                    SegmentLabel(("C", "D"), "CD=?", -32.0, "CD"),
                ),
                target_segment=("C", "D"),
                right_angles=(RightAngleMark("B", "A", "D"),),
                filled_polygons=(("A", "B", "D", "E"), ("B", "C", "D")),
                trace_values={"AB": rect_w, "AD": rect_diag, "BD": height, "BC": base, "CD": hyp},
            )
        )
    return tuple(cases)


def _bisector_points(ab: int, ac: int, bd: int, dc: int) -> dict[str, tuple[float, float]]:
    bc = bd + dc
    scale = min(28.0, 430.0 / bc, 310.0 / max(ab, ac))
    base_width = bc * scale
    x_from_b = (((ab * ab) + (bc * bc) - (ac * ac)) / (2.0 * bc)) * scale
    height = math.sqrt(max(64.0, (ab * scale) ** 2 - x_from_b**2))
    left = 360.0 - base_width / 2.0
    base_y = 430.0
    return {
        "A": (left + x_from_b, base_y - height),
        "B": (left, base_y),
        "C": (left + base_width, base_y),
        "D": (left + bd * scale, base_y),
    }


def _bisector_case(
    *,
    case_kind: str,
    answer: int,
    ab: int,
    ac: int,
    bd: int,
    dc: int,
    labels: tuple[SegmentLabel, ...],
    target: tuple[str, str],
    trace_values: Mapping[str, Any],
) -> TriangleRelationsCase:
    return _case(
        case_kind=case_kind,
        answer=answer,
        answer_type="integer",
        formula_family="angle_bisector_theorem",
        formula_text="AB / AC = BD / DC",
        reasoning_steps=3,
        vertices=_bisector_points(ab, ac, bd, dc),
        edges=(("A", "B"), ("A", "C"), ("B", "C"), ("A", "D")),
        polygons=(("A", "B", "C"),),
        segment_labels=labels,
        target_segment=target,
        angle_labels=(AngleLabel("A", "B", "D", "", 34.0), AngleLabel("A", "D", "C", "", 44.0)),
        tick_groups=(TickGroup((("A", "B"), ("A", "C")), count=0, kind="angle_bisector"),),
        trace_values=trace_values,
    )


def angle_bisector_split_cases() -> tuple[TriangleRelationsCase, ...]:
    rows = ((6, 9, 4), (8, 12, 6), (10, 15, 8), (9, 12, 6), (12, 18, 10), (15, 20, 12), (7, 14, 5), (10, 25, 6))
    cases: list[TriangleRelationsCase] = []
    for ab, ac, bd in rows:
        dc = bd * ac // ab
        cases.append(
            _bisector_case(
                case_kind="bisector_split",
                answer=dc,
                ab=ab,
                ac=ac,
                bd=bd,
                dc=dc,
                labels=(
                    SegmentLabel(("A", "B"), str(ab), -32.0, "AB"),
                    SegmentLabel(("A", "C"), str(ac), 32.0, "AC"),
                    SegmentLabel(("B", "D"), str(bd), 28.0, "BD"),
                    SegmentLabel(("D", "C"), "DC=?", 28.0, "DC"),
                ),
                target=("D", "C"),
                trace_values={"AB": ab, "AC": ac, "BD": bd, "DC": dc},
            )
        )
    return tuple(cases)


def angle_bisector_base_cases() -> tuple[TriangleRelationsCase, ...]:
    cases: list[TriangleRelationsCase] = []
    for split_case in angle_bisector_split_cases():
        ab = int(split_case.trace_values["AB"])
        ac = int(split_case.trace_values["AC"])
        bd = int(split_case.trace_values["BD"])
        dc = int(split_case.trace_values["DC"])
        bc = bd + dc
        cases.append(
            _bisector_case(
                case_kind="bisector_base",
                answer=bc,
                ab=ab,
                ac=ac,
                bd=bd,
                dc=dc,
                labels=(
                    SegmentLabel(("A", "B"), str(ab), -32.0, "AB"),
                    SegmentLabel(("A", "C"), str(ac), 32.0, "AC"),
                    SegmentLabel(("B", "D"), str(bd), 28.0, "BD"),
                    SegmentLabel(("B", "C"), "BC=?", 44.0, "BC"),
                ),
                target=("B", "C"),
                trace_values={"AB": ab, "AC": ac, "BD": bd, "derived_DC": dc, "BC": bc},
            )
        )
    return tuple(cases)


def centroid_vertex_cases() -> tuple[TriangleRelationsCase, ...]:
    return tuple(_centroid_case(given=value, target_whole=False) for value in range(4, 19))


def centroid_whole_cases() -> tuple[TriangleRelationsCase, ...]:
    return tuple(_centroid_case(given=value, target_whole=True) for value in range(8, 39, 2))


def _centroid_case(*, given: int, target_whole: bool) -> TriangleRelationsCase:
    a, b, c = (360.0, 110.0), (140.0, 430.0), (590.0, 430.0)
    d = mid(b, c)
    g = (a[0] + (d[0] - a[0]) * (2.0 / 3.0), a[1] + (d[1] - a[1]) * (2.0 / 3.0))
    if target_whole:
        answer = (3 * given) // 2
        labels = (SegmentLabel(("A", "G"), str(given), -30.0, "AG"), SegmentLabel(("A", "D"), "AD=?", 30.0, "AD"))
        target = ("A", "D")
        values = {"AG": given, "GD": given // 2, "AD": answer}
        kind = "centroid_whole_median"
    else:
        answer = 2 * given
        labels = (SegmentLabel(("G", "D"), str(given), 30.0, "GD"), SegmentLabel(("A", "G"), "AG=?", -30.0, "AG"))
        target = ("A", "G")
        values = {"GD": given, "AG": answer, "AD": answer + given}
        kind = "centroid_vertex_segment"
    return _case(
        case_kind=kind,
        answer=answer,
        answer_type="integer",
        formula_family="centroid_median_ratio",
        formula_text="AG:GD = 2:1 and AD = AG + GD",
        reasoning_steps=2,
        vertices={"A": a, "B": b, "C": c, "D": d, "G": g},
        edges=(("A", "B"), ("A", "C"), ("B", "C"), ("A", "D")),
        polygons=(("A", "B", "C"),),
        segment_labels=labels,
        target_segment=target,
        tick_groups=(TickGroup((("B", "D"), ("D", "C")), count=1),),
        trace_values={"D_midpoint_of_BC": True, "G_is_centroid": True, **values},
    )


def _right_triangle_case(
    *,
    case_kind: str,
    adjacent: float,
    opposite: float,
    hypotenuse: float,
    theta: float,
    visible_sides: tuple[str, ...],
    target_side: str | None,
    formula_family: str,
    formula_text: str,
    answer: float,
    context: str = "triangle",
) -> TriangleRelationsCase:
    """Construct one right-triangle trigonometry diagram with one target witness."""

    scale = min(420.0 / max(adjacent, 1.0), 270.0 / max(opposite, 1.0))
    a = (140.0, 430.0)
    c = (140.0 + adjacent * scale, 430.0)
    b = (c[0], 430.0 - opposite * scale)
    side_segments = {"adjacent": ("A", "C"), "opposite": ("C", "B"), "hypotenuse": ("A", "B")}
    side_names = {"adjacent": "ground", "opposite": "height", "hypotenuse": "slope"}
    labels: list[SegmentLabel] = []
    for side in visible_sides:
        value = {"adjacent": adjacent, "opposite": opposite, "hypotenuse": hypotenuse}[side]
        labels.append(SegmentLabel(side_segments[side], f"{side_names[side]}={fmt_measure(value)}", 32.0, side))
    if target_side is not None:
        labels.append(SegmentLabel(side_segments[target_side], f"{side_names[target_side]}=?", -34.0, target_side))
    angle_text = "?" if target_side is None else f"θ={fmt_measure(theta)}°"
    answer_type = "number"
    rounding = "nearest_tenth"
    annotation_mode = "segment" if target_side is not None else "point"
    trace_values = {
        "adjacent": round1(adjacent),
        "opposite": round1(opposite),
        "hypotenuse": round1(hypotenuse),
        "theta_degrees": round1(theta),
        "visible_sides": list(visible_sides),
        "target_side": target_side,
        "context_style": context,
        "annotation_mode": annotation_mode,
    }
    return _case(
        case_kind=case_kind,
        answer=answer,
        answer_type=answer_type,
        answer_rounding=rounding,
        formula_family=formula_family,
        formula_text=formula_text,
        reasoning_steps=1,
        vertices={"A": a, "B": b, "C": c},
        edges=(("A", "C"), ("C", "B"), ("A", "B")),
        polygons=(("A", "B", "C"),),
        segment_labels=tuple(labels),
        target_segment=side_segments[target_side] if target_side is not None else None,
        target_point="A" if target_side is None else None,
        angle_labels=(AngleLabel("A", "B", "C", angle_text, 54.0, "theta"),),
        right_angles=(RightAngleMark("C", "A", "B"),),
        filled_polygons=(("A", "B", "C"),),
        trace_values=trace_values,
    )


def _missing_side_cases(kind: str, builder: Callable[[float, float], tuple[float, float, float, float, tuple[str, ...], str, str, str]]) -> tuple[TriangleRelationsCase, ...]:
    cases: list[TriangleRelationsCase] = []
    for theta in (25, 30, 35, 40, 45, 50, 55, 60, 65):
        for known in (8, 10, 12, 14, 16, 18, 20, 24, 28):
            adjacent, opposite, hypotenuse, answer, visible, target, family, formula = builder(float(theta), float(known))
            cases.append(
                _right_triangle_case(
                    case_kind=kind,
                    adjacent=adjacent,
                    opposite=opposite,
                    hypotenuse=hypotenuse,
                    theta=float(theta),
                    visible_sides=visible,
                    target_side=target,
                    formula_family=family,
                    formula_text=formula,
                    answer=round1(answer),
                )
            )
    return tuple(cases)


def height_from_angle_ground_cases() -> tuple[TriangleRelationsCase, ...]:
    return _missing_side_cases("height_from_tangent", lambda theta, known: (known, known * math.tan(math.radians(theta)), math.hypot(known, known * math.tan(math.radians(theta))), known * math.tan(math.radians(theta)), ("adjacent",), "opposite", "right_triangle_tangent", "height = ground * tan(theta)"))


def ground_from_angle_height_cases() -> tuple[TriangleRelationsCase, ...]:
    return _missing_side_cases("ground_from_tangent", lambda theta, known: (known / math.tan(math.radians(theta)), known, math.hypot(known / math.tan(math.radians(theta)), known), known / math.tan(math.radians(theta)), ("opposite",), "adjacent", "right_triangle_tangent", "ground = height / tan(theta)"))


def hypotenuse_from_angle_height_cases() -> tuple[TriangleRelationsCase, ...]:
    return _missing_side_cases("hypotenuse_from_sine", lambda theta, known: (known / math.tan(math.radians(theta)), known, known / math.sin(math.radians(theta)), known / math.sin(math.radians(theta)), ("opposite",), "hypotenuse", "right_triangle_sine", "hypotenuse = height / sin(theta)"))


def height_from_angle_hypotenuse_cases() -> tuple[TriangleRelationsCase, ...]:
    return _missing_side_cases("height_from_sine", lambda theta, known: (known * math.cos(math.radians(theta)), known * math.sin(math.radians(theta)), known, known * math.sin(math.radians(theta)), ("hypotenuse",), "opposite", "right_triangle_sine", "height = hypotenuse * sin(theta)"))


def ground_from_angle_hypotenuse_cases() -> tuple[TriangleRelationsCase, ...]:
    return _missing_side_cases("ground_from_cosine", lambda theta, known: (known * math.cos(math.radians(theta)), known * math.sin(math.radians(theta)), known, known * math.cos(math.radians(theta)), ("hypotenuse",), "adjacent", "right_triangle_cosine", "ground = hypotenuse * cos(theta)"))


def angle_from_opposite_adjacent_cases() -> tuple[TriangleRelationsCase, ...]:
    return _angle_cases("angle_from_tangent", ("opposite", "adjacent"), "theta = arctan(height / ground)")


def angle_from_opposite_hypotenuse_cases() -> tuple[TriangleRelationsCase, ...]:
    return _angle_cases("angle_from_sine", ("opposite", "hypotenuse"), "theta = arcsin(height / hypotenuse)")


def angle_from_adjacent_hypotenuse_cases() -> tuple[TriangleRelationsCase, ...]:
    return _angle_cases("angle_from_cosine", ("adjacent", "hypotenuse"), "theta = arccos(ground / hypotenuse)")


def angle_of_elevation_cases() -> tuple[TriangleRelationsCase, ...]:
    return _angle_cases("angle_of_elevation", ("opposite", "adjacent"), "theta = arctan(height / distance)", context="flagpole")


def _angle_cases(family: str, visible: tuple[str, ...], formula: str, *, context: str = "triangle") -> tuple[TriangleRelationsCase, ...]:
    triples = (
        (11, 60, 61),
        (60, 11, 61),
        (12, 5, 13),
        (20, 21, 29),
        (80, 39, 89),
        (9, 40, 41),
        (15, 8, 17),
        (21, 20, 29),
        (56, 33, 65),
        (63, 16, 65),
        (48, 55, 73),
        (65, 72, 97),
        (85, 132, 157),
    )
    return tuple(
        _right_triangle_case(
            case_kind=family,
            adjacent=float(adjacent),
            opposite=float(opposite),
            hypotenuse=float(hypotenuse),
            theta=math.degrees(math.atan2(float(opposite), float(adjacent))),
            visible_sides=visible,
            target_side=None,
            formula_family=family,
            formula_text=formula,
            answer=round1(math.degrees(math.atan2(float(opposite), float(adjacent)))),
            context=context,
        )
        for adjacent, opposite, hypotenuse in triples
    )


def angle_bisector_variable_cases() -> tuple[TriangleRelationsCase, ...]:
    """Build angle-bisector equation cases while keeping A/B/C/D witnesses stable."""

    rows = (
        ("split_ratio_variable", 12, 18, 8, "x+4", 8),
        ("split_ratio_variable", 10, 15, 6, "x+3", 6),
        ("split_ratio_variable", 14, 21, 10, "x+5", 10),
        ("split_ratio_variable", 9, 12, 8, "x+15", 12),
        ("adjacent_ratio_variable", "x+3", 16, 5, 8, 7),
        ("adjacent_ratio_variable", "x+4", 18, 6, 9, 8),
        ("adjacent_ratio_variable", "x+2", 21, 4, 7, 10),
        ("adjacent_ratio_variable", "x+5", 20, 7, 10, 9),
    )
    cases: list[TriangleRelationsCase] = []
    for row in rows:
        family = str(row[0])
        if family == "split_ratio_variable":
            ab, ac, bd, dc_label, answer = row[1:]
            dc = int(str(dc_label).split("+")[1]) + int(answer)
            labels = (
                SegmentLabel(("A", "B"), str(ab), -32.0, "AB"),
                SegmentLabel(("A", "C"), str(ac), 32.0, "AC"),
                SegmentLabel(("B", "D"), str(bd), 28.0, "BD"),
                SegmentLabel(("D", "C"), str(dc_label), 28.0, "DC"),
            )
            trace = {"AB": ab, "AC": ac, "BD": bd, "DC_expression": dc_label, "x": answer}
        else:
            ab_label, ac, bd, dc, answer = row[1:]
            ab = int(str(ab_label).split("+")[1]) + int(answer)
            labels = (
                SegmentLabel(("A", "B"), str(ab_label), -32.0, "AB"),
                SegmentLabel(("A", "C"), str(ac), 32.0, "AC"),
                SegmentLabel(("B", "D"), str(bd), 28.0, "BD"),
                SegmentLabel(("D", "C"), str(dc), 28.0, "DC"),
            )
            trace = {"AB_expression": ab_label, "AC": ac, "BD": bd, "DC": dc, "x": answer}
        cases.append(
            _case(
                case_kind=family,
                answer=int(answer),
                answer_type="integer",
                formula_family="angle_bisector_theorem_variable",
                formula_text="AB / AC = BD / DC, solve for x",
                reasoning_steps=3,
                vertices=_bisector_points(int(ab), int(ac), int(bd), int(dc)),
                edges=(("A", "B"), ("A", "C"), ("B", "C"), ("A", "D")),
                polygons=(("A", "B", "C"),),
                segment_labels=labels,
                point_annotation_labels=("A", "B", "C", "D"),
                angle_labels=(AngleLabel("A", "B", "D", "", 34.0), AngleLabel("A", "D", "C", "", 44.0)),
                trace_values={**trace, "internal_case_family": family},
            )
        )
    return tuple(cases)


def split_triangle_angle_cases() -> tuple[TriangleRelationsCase, ...]:
    """Build split-triangle angle-chase cases under the triangle-relations scene."""

    rows = (
        ("single_cevian_triangle_angle_sum", 42, 72, 66),
        ("single_cevian_triangle_angle_sum", 55, 47, 78),
        ("single_cevian_triangle_angle_sum", 38, 84, 58),
        ("single_cevian_triangle_angle_sum", 63, 46, 71),
        ("single_cevian_triangle_angle_sum", 48, 69, 63),
        ("single_cevian_triangle_angle_sum", 36, 92, 52),
        ("single_cevian_triangle_angle_sum", 44, 62, 74),
        ("single_cevian_triangle_angle_sum", 50, 46, 84),
        ("single_cevian_triangle_angle_sum", 67, 58, 55),
        ("single_cevian_triangle_angle_sum", 39, 72, 69),
        ("shared_vertex_split_angle_sum", 51, 57, 72),
        ("shared_vertex_split_angle_sum", 44, 68, 68),
        ("shared_vertex_split_angle_sum", 62, 41, 77),
        ("shared_vertex_split_angle_sum", 35, 83, 62),
        ("shared_vertex_split_angle_sum", 58, 52, 70),
        ("two_step_adjacent_triangle_angle_sum", 51, 49, 33),
        ("two_step_adjacent_triangle_angle_sum", 42, 66, 38),
        ("two_step_adjacent_triangle_angle_sum", 55, 35, 47),
        ("two_step_adjacent_triangle_angle_sum", 48, 54, 39),
        ("two_step_adjacent_triangle_angle_sum", 60, 42, 36),
        ("two_step_adjacent_triangle_angle_sum", 46, 58, 26),
        ("two_step_adjacent_triangle_angle_sum", 38, 63, 23),
        ("two_step_adjacent_triangle_angle_sum", 44, 51, 21),
        ("two_step_adjacent_triangle_angle_sum", 57, 48, 38),
        ("two_step_adjacent_triangle_angle_sum", 49, 57, 29),
    )
    vertices = {
        "A": (150.0, 155.0),
        "B": (360.0, 160.0),
        "C": (610.0, 155.0),
        "D": (365.0, 430.0),
    }
    cases: list[TriangleRelationsCase] = []
    for family, angle_a, angle_b, angle_c in rows:
        labels: list[AngleLabel]
        if family == "two_step_adjacent_triangle_angle_sum":
            left_unknown = 180 - int(angle_a) - int(angle_b)
            straight_supplement = 180 - int(left_unknown)
            answer = 180 - int(straight_supplement) - int(angle_c)
            labels = [
                AngleLabel("A", "B", "D", f"{angle_a}{DEGREE_SYMBOL}", 48.0, "given_A"),
                AngleLabel("D", "A", "B", f"{angle_b}{DEGREE_SYMBOL}", 58.0, "given_D_left"),
                AngleLabel("C", "B", "D", f"{angle_c}{DEGREE_SYMBOL}", 48.0, "given_C"),
                AngleLabel("D", "B", "C", "?", 58.0, "target_angle"),
            ]
            trace = {
                "angle_a": int(angle_a),
                "angle_b": int(angle_b),
                "angle_c": int(angle_c),
                "left_triangle_missing_angle": int(left_unknown),
                "straight_angle_supplement": int(straight_supplement),
                "answer": int(answer),
            }
        elif family == "shared_vertex_split_angle_sum":
            answer = int(angle_c)
            labels = [
                AngleLabel("A", "B", "D", f"{angle_a}{DEGREE_SYMBOL}", 48.0, "given_A"),
                AngleLabel("D", "A", "B", f"{angle_b}{DEGREE_SYMBOL}", 58.0, "given_D"),
                AngleLabel("B", "A", "D", "?", 48.0, "target_angle"),
            ]
            trace = {"angle_a": int(angle_a), "angle_b": int(angle_b), "angle_c": int(angle_c), "answer": answer}
        else:
            answer = int(angle_c)
            labels = [
                AngleLabel("A", "B", "D", f"{angle_a}{DEGREE_SYMBOL}", 48.0, "given_A"),
                AngleLabel("B", "A", "D", f"{angle_b}{DEGREE_SYMBOL}", 48.0, "given_B"),
                AngleLabel("D", "A", "B", "?", 58.0, "target_angle"),
            ]
            trace = {"angle_a": int(angle_a), "angle_b": int(angle_b), "angle_c": int(angle_c), "answer": answer}
        cases.append(
            _case(
                case_kind=str(family),
                answer=int(answer),
                answer_type="integer",
                formula_family="split_triangle_angle_sum",
                formula_text="triangle angle sum and, when needed, straight-angle supplement",
                reasoning_steps=3 if str(family) == "two_step_adjacent_triangle_angle_sum" else 1,
                vertices=vertices,
                edges=(("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"), ("B", "D")),
                polygons=(("A", "B", "D"), ("B", "C", "D")),
                segment_labels=(),
                point_annotation_labels=("A", "B", "C", "D"),
                angle_labels=tuple(labels),
                filled_polygons=(("A", "B", "D"), ("B", "C", "D")),
                trace_values={**trace, "internal_construction_family": str(family)},
            )
        )
    return tuple(cases)


def split_triangle_trig_side_cases() -> tuple[TriangleRelationsCase, ...]:
    """Build split right-triangle trigonometry cases with a shared altitude."""

    def _num(value: float | int) -> str:
        return str(fmt_measure(float(value)))

    cases: list[TriangleRelationsCase] = []
    vertices = {
        "A": (365.0, 135.0),
        "B": (145.0, 430.0),
        "C": (625.0, 430.0),
        "D": (365.0, 430.0),
    }

    def add_case(
        *,
        family: str,
        answer: float,
        target: tuple[str, str],
        labels: tuple[SegmentLabel, ...],
        angles: tuple[AngleLabel, ...],
        trace: Mapping[str, Any],
        ticks: tuple[TickGroup, ...] = (),
    ) -> None:
        cases.append(
            _case(
                case_kind=str(family),
                answer=round1(float(answer)),
                answer_type="number",
                answer_rounding="nearest_tenth",
                formula_family="shared_altitude_right_triangle_trig",
                formula_text="use one right triangle to derive the shared altitude, then solve the target side",
                reasoning_steps=3,
                vertices=vertices,
                edges=(("A", "B"), ("B", "D"), ("D", "C"), ("C", "A"), ("A", "D")),
                polygons=(("A", "B", "D"), ("A", "D", "C")),
                segment_labels=labels,
                target_segment=target,
                point_annotation_labels=("A", "B", "C", "D"),
                angle_labels=angles,
                right_angles=(RightAngleMark("D", "A", "C"),),
                tick_groups=ticks,
                filled_polygons=(("A", "B", "D"), ("A", "D", "C")),
                trace_values={**dict(trace), "internal_construction_family": str(family), "answer": round1(float(answer))},
            )
        )

    for known_base in range(7, 26):
        for left_angle in range(32, 68, 3):
            for right_angle in range(35, 68, 4):
                if len([case for case in cases if case.case_kind == "shared_altitude_two_angles_side"]) >= 80:
                    break
                altitude = float(known_base) * math.tan(math.radians(float(left_angle)))
                answer = altitude / math.sin(math.radians(float(right_angle)))
                if not 6.0 <= answer <= 80.0:
                    continue
                add_case(
                    family="shared_altitude_two_angles_side",
                    answer=answer,
                    target=("A", "C"),
                    labels=(SegmentLabel(("B", "D"), _num(known_base), 32.0, "BD"), SegmentLabel(("A", "C"), "AC=?", 36.0, "AC")),
                    angles=(
                        AngleLabel("B", "A", "D", f"{left_angle}{DEGREE_SYMBOL}", 52.0, "angle_B"),
                        AngleLabel("C", "D", "A", f"{right_angle}{DEGREE_SYMBOL}", 52.0, "angle_C"),
                    ),
                    trace={
                        "known_segment": "BD",
                        "known_value": int(known_base),
                        "left_angle": int(left_angle),
                        "right_angle": int(right_angle),
                        "altitude": round(float(altitude), 4),
                        "target_side": "AC",
                    },
                )
            if len([case for case in cases if case.case_kind == "shared_altitude_two_angles_side"]) >= 80:
                break
        if len([case for case in cases if case.case_kind == "shared_altitude_two_angles_side"]) >= 80:
            break

    for known_side in range(10, 34):
        for left_angle in range(32, 69, 4):
            for right_angle in range(35, 69, 5):
                if len([case for case in cases if case.case_kind == "shared_altitude_side_then_hypotenuse"]) >= 80:
                    break
                altitude = float(known_side) * math.sin(math.radians(float(left_angle)))
                answer = altitude / math.sin(math.radians(float(right_angle)))
                if not 5.0 <= answer <= 70.0:
                    continue
                add_case(
                    family="shared_altitude_side_then_hypotenuse",
                    answer=answer,
                    target=("A", "C"),
                    labels=(SegmentLabel(("A", "B"), _num(known_side), -36.0, "AB"), SegmentLabel(("A", "C"), "AC=?", 36.0, "AC")),
                    angles=(
                        AngleLabel("B", "A", "D", f"{left_angle}{DEGREE_SYMBOL}", 52.0, "angle_B"),
                        AngleLabel("C", "D", "A", f"{right_angle}{DEGREE_SYMBOL}", 52.0, "angle_C"),
                    ),
                    trace={
                        "known_segment": "AB",
                        "known_value": int(known_side),
                        "left_angle": int(left_angle),
                        "right_angle": int(right_angle),
                        "altitude": round(float(altitude), 4),
                        "target_side": "AC",
                    },
                )
            if len([case for case in cases if case.case_kind == "shared_altitude_side_then_hypotenuse"]) >= 80:
                break
        if len([case for case in cases if case.case_kind == "shared_altitude_side_then_hypotenuse"]) >= 80:
            break

    for half_base in range(5, 28):
        for base_angle in range(34, 69, 3):
            if len([case for case in cases if case.case_kind == "isosceles_altitude_trig_side"]) >= 80:
                break
            answer = float(half_base) / math.cos(math.radians(float(base_angle)))
            if not 6.0 <= answer <= 75.0:
                continue
            add_case(
                family="isosceles_altitude_trig_side",
                answer=answer,
                target=("A", "B"),
                labels=(SegmentLabel(("B", "D"), _num(half_base), 32.0, "BD"), SegmentLabel(("A", "B"), "AB=?", -36.0, "AB")),
                angles=(AngleLabel("B", "A", "D", f"{base_angle}{DEGREE_SYMBOL}", 52.0, "angle_B"),),
                ticks=(TickGroup((("A", "B"), ("A", "C")), count=1), TickGroup((("B", "D"), ("D", "C")), count=2)),
                trace={
                    "known_segment": "BD",
                    "known_value": int(half_base),
                    "left_angle": int(base_angle),
                    "right_angle": int(base_angle),
                    "target_side": "AB",
                },
            )
        if len([case for case in cases if case.case_kind == "isosceles_altitude_trig_side"]) >= 80:
            break
    return tuple(cases)


def _right_triangle_altitude_cases(mode: str) -> tuple[TriangleRelationsCase, ...]:
    """Build right-triangle altitude theorem cases for one semantic mode."""

    rows = (
        (4, 9, 6, None, None),
        (9, 16, 12, 15, 20),
        (16, 25, 20, None, None),
        (25, 36, 30, None, None),
        (18, 32, 24, 30, 40),
        (12, 27, 18, None, None),
        (36, 64, 48, 60, 80),
        (8, 18, 12, None, None),
        (27, 48, 36, 45, 60),
        (48, 27, 36, 60, 45),
    )
    target_segments = {
        "altitude": ("A", "D"),
        "left_projection": ("B", "D"),
        "right_projection": ("D", "C"),
        "left_leg": ("A", "B"),
        "right_leg": ("A", "C"),
    }
    cases: list[TriangleRelationsCase] = []
    for left_projection, right_projection, altitude, left_leg, right_leg in rows:
        hypotenuse = int(left_projection) + int(right_projection)
        vertices = {
            "B": (130.0, 420.0),
            "D": (130.0 + 430.0 * (float(left_projection) / float(hypotenuse)), 420.0),
            "C": (560.0, 420.0),
            "A": (130.0 + 430.0 * (float(left_projection) / float(hypotenuse)), 170.0),
        }
        branch_cases: list[tuple[str, int, tuple[SegmentLabel, ...], Mapping[str, Any]]] = []
        if mode == "altitude_from_two_projections":
            branch_cases.append(
                (
                    "altitude",
                    int(altitude),
                    (
                        SegmentLabel(("B", "D"), str(left_projection), 30.0, "BD"),
                        SegmentLabel(("D", "C"), str(right_projection), 30.0, "DC"),
                        SegmentLabel(("A", "D"), "AD=?", -34.0, "AD"),
                    ),
                    {"relation": "altitude_geometric_mean_from_split_hypotenuse"},
                )
            )
        elif mode == "projection_from_altitude_and_projection":
            branch_cases.extend(
                (
                    (
                        "right_projection",
                        int(right_projection),
                        (
                            SegmentLabel(("B", "D"), str(left_projection), 30.0, "BD"),
                            SegmentLabel(("D", "C"), "DC=?", 30.0, "DC"),
                            SegmentLabel(("A", "D"), str(altitude), -34.0, "AD"),
                        ),
                        {"relation": "projection_from_altitude_and_other_projection"},
                    ),
                    (
                        "left_projection",
                        int(left_projection),
                        (
                            SegmentLabel(("B", "D"), "BD=?", 30.0, "BD"),
                            SegmentLabel(("D", "C"), str(right_projection), 30.0, "DC"),
                            SegmentLabel(("A", "D"), str(altitude), -34.0, "AD"),
                        ),
                        {"relation": "projection_from_altitude_and_other_projection"},
                    ),
                )
            )
        elif mode == "leg_projection_relation" and left_leg is not None and right_leg is not None:
            branch_cases.extend(
                (
                    (
                        "left_leg",
                        int(left_leg),
                        (
                            SegmentLabel(("B", "C"), str(hypotenuse), 48.0, "BC"),
                            SegmentLabel(("B", "D"), str(left_projection), 30.0, "BD"),
                            SegmentLabel(("A", "B"), "AB=?", -34.0, "AB"),
                        ),
                        {"relation": "leg_geometric_mean_from_hypotenuse_projection"},
                    ),
                    (
                        "right_leg",
                        int(right_leg),
                        (
                            SegmentLabel(("B", "C"), str(hypotenuse), 48.0, "BC"),
                            SegmentLabel(("D", "C"), str(right_projection), 30.0, "DC"),
                            SegmentLabel(("A", "C"), "AC=?", 34.0, "AC"),
                        ),
                        {"relation": "leg_geometric_mean_from_hypotenuse_projection"},
                    ),
                )
            )
        elif mode == "projection_leg_relation" and left_leg is not None and right_leg is not None:
            branch_cases.extend(
                (
                    (
                        "left_projection",
                        int(left_projection),
                        (
                            SegmentLabel(("B", "C"), str(hypotenuse), 48.0, "BC"),
                            SegmentLabel(("A", "B"), str(left_leg), -34.0, "AB"),
                            SegmentLabel(("B", "D"), "BD=?", 30.0, "BD"),
                        ),
                        {"relation": "projection_length_from_leg_hypotenuse"},
                    ),
                    (
                        "right_projection",
                        int(right_projection),
                        (
                            SegmentLabel(("B", "C"), str(hypotenuse), 48.0, "BC"),
                            SegmentLabel(("A", "C"), str(right_leg), 34.0, "AC"),
                            SegmentLabel(("D", "C"), "DC=?", 30.0, "DC"),
                        ),
                        {"relation": "projection_length_from_leg_hypotenuse"},
                    ),
                )
            )
        for target_role, answer, labels, relation_trace in branch_cases:
            cases.append(
                _case(
                    case_kind=f"right_triangle_altitude_{target_role}",
                    answer=int(answer),
                    answer_type="integer",
                    formula_family="right_triangle_altitude_projection",
                    formula_text="AD^2 = BD * DC and leg^2 = hypotenuse * adjacent_projection",
                    reasoning_steps=2,
                    vertices=vertices,
                    edges=(("A", "B"), ("A", "C"), ("B", "C"), ("A", "D")),
                    polygons=(("A", "B", "C"),),
                    segment_labels=labels,
                    target_segment=target_segments[str(target_role)],
                    point_annotation_labels=("A", "B", "C", "D"),
                    right_angles=(RightAngleMark("A", "B", "C"), RightAngleMark("D", "A", "C")),
                    filled_polygons=(("A", "B", "C"),),
                    trace_values={
                        "left_projection": int(left_projection),
                        "right_projection": int(right_projection),
                        "altitude": int(altitude),
                        "hypotenuse": int(hypotenuse),
                        "left_leg": None if left_leg is None else int(left_leg),
                        "right_leg": None if right_leg is None else int(right_leg),
                        "target_role": str(target_role),
                        "target_name": "".join(target_segments[str(target_role)]),
                        **dict(relation_trace),
                    },
                )
            )
    return tuple(cases)


def altitude_from_two_projections_cases() -> tuple[TriangleRelationsCase, ...]:
    """Build cases where the altitude is the geometric mean of two projections."""

    return _right_triangle_altitude_cases("altitude_from_two_projections")


def projection_from_altitude_cases() -> tuple[TriangleRelationsCase, ...]:
    """Build cases where one projection is unknown from altitude and the other projection."""

    return _right_triangle_altitude_cases("projection_from_altitude_and_projection")


def leg_from_projection_cases() -> tuple[TriangleRelationsCase, ...]:
    """Build cases where one leg is unknown from hypotenuse and adjacent projection."""

    return _right_triangle_altitude_cases("leg_projection_relation")


def projection_from_leg_cases() -> tuple[TriangleRelationsCase, ...]:
    """Build cases where one projection is unknown from a leg and the hypotenuse."""

    return _right_triangle_altitude_cases("projection_leg_relation")


def parallel_segment_expression_length_cases() -> tuple[TriangleRelationsCase, ...]:
    """Build target-length proportion cases for the triangle side-splitter scaffold."""

    cases: list[TriangleRelationsCase] = []
    for answer in range(6, 61):
        for variant_index in range(8):
            offset = 1 + (variant_index % 6)
            ratio = 2 + (variant_index % 2)
            left_top = 4 + (variant_index % 8)
            split_ratio = left_top / float(left_top + ratio * left_top)
            cases.append(
                _case(
                    case_kind="triangle_side_splitter_segment_length_expression",
                    answer=int(answer),
                    answer_type="number",
                    answer_rounding="integer",
                    formula_family="parallel_segment_ratio_target_length",
                    formula_text="AD / DB = AE / EC, solve x, then AE = x + offset",
                    reasoning_steps=3,
                    vertices=_triangle_scale_points(split_ratio),
                    edges=(("A", "B"), ("A", "C"), ("B", "C"), ("D", "E")),
                    polygons=(("A", "B", "C"),),
                    segment_labels=(
                        SegmentLabel(("A", "D"), str(left_top), -30.0, "AD"),
                        SegmentLabel(("D", "B"), str(ratio * left_top), -30.0, "DB"),
                        SegmentLabel(("A", "E"), f"x+{offset}", 30.0, "AE"),
                        SegmentLabel(("E", "C"), str(ratio * answer), 30.0, "EC"),
                    ),
                    target_segment=("A", "E"),
                    point_annotation_labels=("A", "B", "C", "D", "E"),
                    tick_groups=(TickGroup((("D", "E"), ("B", "C")), kind="parallel"),),
                    trace_values={
                        "construction_family": "triangle_side_splitter",
                        "answer_value": int(answer),
                        "expression_offset": int(offset),
                        "ratio": int(ratio),
                        "left_top_value": int(left_top),
                        "solved_variable_value": int(answer - offset),
                        "target_name": "AE",
                    },
                )
            )
    return tuple(cases)


def parallel_segment_variable_cases() -> tuple[TriangleRelationsCase, ...]:
    """Build variable-solving proportion cases for the triangle side-splitter scaffold."""

    cases: list[TriangleRelationsCase] = []
    for answer in range(3, 41):
        for variant_index in range(8):
            offset = 1 + (variant_index % 5)
            ratio = 2 + (variant_index % 2)
            left_top = 4 + (variant_index % 8)
            split_ratio = left_top / float(left_top + answer + offset)
            cases.append(
                _case(
                    case_kind="triangle_side_splitter_proportion_expression",
                    answer=int(answer),
                    answer_type="number",
                    answer_rounding="integer",
                    formula_family="parallel_segment_ratio_variable",
                    formula_text="AD / DB = AE / EC, solve for x",
                    reasoning_steps=3,
                    vertices=_triangle_scale_points(split_ratio),
                    edges=(("A", "B"), ("A", "C"), ("B", "C"), ("D", "E")),
                    polygons=(("A", "B", "C"),),
                    segment_labels=(
                        SegmentLabel(("A", "D"), str(left_top), -30.0, "AD"),
                        SegmentLabel(("D", "B"), f"x+{offset}", -30.0, "DB"),
                        SegmentLabel(("A", "E"), str(ratio * left_top), 30.0, "AE"),
                        SegmentLabel(("E", "C"), str(ratio * (answer + offset)), 30.0, "EC"),
                    ),
                    point_annotation_labels=("A", "B", "C", "D", "E"),
                    tick_groups=(TickGroup((("D", "E"), ("B", "C")), kind="parallel"),),
                    trace_values={
                        "construction_family": "triangle_side_splitter",
                        "answer_value": int(answer),
                        "expression_offset": int(offset),
                        "ratio": int(ratio),
                        "left_top_value": int(left_top),
                        "solved_variable_value": int(answer),
                        "target_name": "x",
                    },
                )
            )
    return tuple(cases)


def case_trace_values(case: TriangleRelationsCase) -> dict[str, Any]:
    """Return JSON-safe trace values for one resolved construction case."""

    return {
        "internal_case_kind": str(case.case_kind),
        "formula_family": str(case.formula_family),
        "formula": str(case.formula_text),
        "reasoning_steps": int(case.reasoning_steps),
        **dict(case.trace_values),
    }


__all__ = [
    "angle_bisector_base_cases",
    "angle_bisector_split_cases",
    "angle_bisector_variable_cases",
    "angle_from_adjacent_hypotenuse_cases",
    "angle_from_opposite_adjacent_cases",
    "angle_from_opposite_hypotenuse_cases",
    "angle_of_elevation_cases",
    "altitude_from_two_projections_cases",
    "case_trace_values",
    "centroid_vertex_cases",
    "centroid_whole_cases",
    "chained_rectangle_diagonal_cases",
    "ground_from_angle_height_cases",
    "ground_from_angle_hypotenuse_cases",
    "height_from_angle_ground_cases",
    "height_from_angle_hypotenuse_cases",
    "hypotenuse_from_angle_height_cases",
    "leg_from_projection_cases",
    "parallel_section_base_cases",
    "parallel_section_cross_cases",
    "parallel_segment_expression_length_cases",
    "parallel_segment_variable_cases",
    "rectangle_triangle_shared_height_cases",
    "projection_from_altitude_cases",
    "projection_from_leg_cases",
    "similar_side_cases",
    "split_triangle_angle_cases",
    "split_triangle_trig_side_cases",
]
