"""Construction pools for triangle-relations analytical diagrams."""

from __future__ import annotations

import math
from typing import Any, Callable, Iterable, Mapping

from trace.tasks.geometry.shared.measurement_rendering import fmt_measure, round1
from trace.tasks.geometry.shared.vector2d import mid

from .state import AngleLabel, RightAngleMark, SegmentLabel, TickGroup, TriangleRelationsCase


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
    "case_trace_values",
    "centroid_vertex_cases",
    "centroid_whole_cases",
    "chained_rectangle_diagonal_cases",
    "ground_from_angle_height_cases",
    "ground_from_angle_hypotenuse_cases",
    "height_from_angle_ground_cases",
    "height_from_angle_hypotenuse_cases",
    "hypotenuse_from_angle_height_cases",
    "parallel_section_base_cases",
    "parallel_section_cross_cases",
    "rectangle_triangle_shared_height_cases",
    "similar_side_cases",
]
