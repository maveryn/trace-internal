"""Contract tests for the geometry circle-theorem value task."""

from __future__ import annotations

import math

import pytest

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.geometry.circle.theorem_value import (
    GeometryCircleCyclicQuadrilateralAngleValueTask,
    GeometryCircleExternalSecantAngleValueTask,
    GeometryCircleTheoremValueTask,
)
from trace.tasks.geometry.circle.chord_length import (
    GeometryCircleChordLengthFromRadiusAngleValueTask,
)
from trace.tasks.geometry.circle.tangent_radius import (
    GeometryCircleTangentRadiusRightTriangleLengthValueTask,
)
from trace.tasks.shared.config_defaults import (
    split_generation_rendering_prompt_defaults,
)


def _point_in_bbox(point: list[float] | tuple[float, float], bbox: list[float]) -> bool:
    return bool(
        float(bbox[0]) <= float(point[0]) <= float(bbox[2])
        and float(bbox[1]) <= float(point[1]) <= float(bbox[3])
    )


def _orientation(
    a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]
) -> float:
    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def _segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    return bool(
        (_orientation(a, b, c) * _orientation(a, b, d) < 0.0)
        and (_orientation(c, d, a) * _orientation(c, d, b) < 0.0)
    )


def _segment_crosses_bbox(
    a: tuple[float, float], b: tuple[float, float], bbox: list[float]
) -> bool:
    x0, y0, x1, y1 = (float(value) for value in bbox)
    if _point_in_bbox(a, bbox) or _point_in_bbox(b, bbox):
        return True
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return any(
        _segments_intersect(a, b, c, d)
        for c, d in zip(corners, corners[1:] + corners[:1])
    )


def _circle_crosses_bbox(center: list[float], radius: float, bbox: list[float]) -> bool:
    x0, y0, x1, y1 = (float(value) for value in bbox)
    cx, cy = float(center[0]), float(center[1])
    closest = (min(max(cx, x0), x1), min(max(cy, y0), y1))
    nearest = math.hypot(float(closest[0]) - cx, float(closest[1]) - cy)
    farthest = max(
        math.hypot(float(x) - cx, float(y) - cy) for x in (x0, x1) for y in (y0, y1)
    )
    return bool(float(nearest) <= float(radius) <= float(farthest))


@pytest.mark.parametrize(
    "query_id,expected_keys",
    (
        (
            "chord_length_from_radius_and_central_angle",
            ("center", "chord_endpoint_1", "chord_endpoint_2"),
        ),
        (
            "chord_length_from_radius_and_inscribed_angle",
            (
                "center",
                "chord_endpoint_1",
                "chord_endpoint_2",
                "inscribed_angle_vertex",
            ),
        ),
    ),
)
def test_circle_chord_length_from_radius_angle_contract(
    query_id: str, expected_keys: tuple[str, ...]
) -> None:
    out = GeometryCircleChordLengthFromRadiusAngleValueTask().generate(
        29031,
        params={"query_id": query_id, "radius_value": 10, "angle_degrees": 60},
        max_attempts=40,
    )

    execution = out.trace_payload["execution_trace"]
    expected_central = 60 if query_id.endswith("central_angle") else 120
    expected_answer = round(
        2.0
        * float(execution["radius_value"])
        * math.sin(math.radians(float(expected_central) / 2.0)),
        1,
    )
    assert out.answer_gt.type == "number"
    assert float(out.answer_gt.value) == pytest.approx(expected_answer)
    assert execution["answer_type"] == "number"
    assert execution["answer_rounding"] == "nearest_tenth"
    assert execution["central_angle_degrees"] == expected_central
    assert execution["answer_value"] == pytest.approx(expected_answer)
    assert out.annotation_gt.type == "keyed_point_map"
    assert tuple(out.annotation_gt.value) == tuple(expected_keys)
    assert set(out.annotation_gt.value) == set(execution["annotation_roles"])
    assert out.trace_payload["projected_annotation"]["type"] == "keyed_point_map"
    assert (
        out.trace_payload["projected_annotation"]["keyed_point_map"]
        == out.annotation_gt.value
    )
    assert "role keys" in out.prompt
    for key in expected_keys:
        assert f'"{key}"' in out.prompt
    assert "task_variant" not in str(out.trace_payload)


@pytest.mark.parametrize(
    (
        "params",
        "expected_answer",
        "expected_canonical_segment",
        "expected_angle",
    ),
    (
        (
            {
                "query_id": "tangent_length_from_radius_and_external_distance",
                "radius_value": 5,
                "external_distance": 13,
            },
            12.0,
            "PT",
            None,
        ),
        (
            {
                "query_id": "radius_from_external_distance_and_angle",
                "external_distance": 10,
                "angle_degrees": 30,
            },
            5.0,
            "OT",
            30,
        ),
    ),
)
def test_circle_tangent_radius_right_triangle_length_contract(
    params: dict[str, object],
    expected_answer: float,
    expected_canonical_segment: str,
    expected_angle: int | None,
) -> None:
    out = GeometryCircleTangentRadiusRightTriangleLengthValueTask().generate(
        29137,
        params=params,
        max_attempts=40,
    )
    execution = out.trace_payload["execution_trace"]
    point_model = out.trace_payload["render_map"]["point_model"]
    label_map = execution["label_map"]
    ox, oy = point_model[label_map["O"]]
    tx, ty = point_model[label_map["T"]]
    px, py = point_model[label_map["P"]]

    radius = math.hypot(float(tx) - float(ox), float(ty) - float(oy))
    tangent = math.hypot(float(px) - float(tx), float(py) - float(ty))
    external = math.hypot(float(px) - float(ox), float(py) - float(oy))
    dot_product = ((float(ox) - float(tx)) * (float(px) - float(tx))) + (
        (float(oy) - float(ty)) * (float(py) - float(ty))
    )

    assert out.answer_gt.type == "number"
    assert float(out.answer_gt.value) == pytest.approx(expected_answer)
    assert execution["answer_type"] == "number"
    assert execution["answer_rounding"] == "nearest_tenth"
    assert execution["canonical_answer_segment"] == expected_canonical_segment
    assert execution["answer_value"] == pytest.approx(expected_answer)
    assert execution["angle_degrees"] == expected_angle
    assert radius == pytest.approx(float(execution["radius_value"]))
    assert tangent == pytest.approx(float(execution["tangent_length"]))
    assert external == pytest.approx(float(execution["external_distance"]))
    assert dot_product == pytest.approx(0.0, abs=1e-7)
    assert (radius * radius) + (tangent * tangent) == pytest.approx(
        external * external
    )
    assert out.annotation_gt.type == "keyed_point_map"
    assert tuple(out.annotation_gt.value) == (
        "center",
        "tangent_point",
        "external_point",
    )
    assert set(out.annotation_gt.value) == set(execution["annotation_roles"])
    assert out.trace_payload["projected_annotation"]["type"] == "keyed_point_map"
    assert (
        out.trace_payload["projected_annotation"]["keyed_point_map"]
        == out.annotation_gt.value
    )
    assert "role keys" in out.prompt
    for key in ("center", "tangent_point", "external_point"):
        assert f'"{key}"' in out.prompt
    assert "task_variant" not in str(out.trace_payload)


@pytest.mark.parametrize(
    (
        "params",
        "expected_answer",
        "expected_annotation_count",
        "expected_canonical_segment",
    ),
    (
        (
            {"query_id": "diameter_perpendicular_chord_length", "target_answer": 8},
            8,
            5,
            "BE",
        ),
        (
            {
                "query_id": "secant_secant_variable_segment_length",
                "target_answer": 24,
                "secant_secant_variable_target_kind": "inside_first",
            },
            24,
            5,
            "AB",
        ),
        (
            {
                "query_id": "tangent_secant_length",
                "target_answer": 24,
                "tangent_secant_target_kind": "outside",
            },
            24,
            4,
            "PA",
        ),
        (
            {"query_id": "secant_secant_length", "target_answer": 10},
            10,
            5,
            "PA",
        ),
        (
            {"query_id": "intersecting_chords_arc_measure", "target_answer": 120},
            120,
            5,
            "arcCD",
        ),
        (
            {"query_id": "multi_step_angle_value", "target_answer": 85},
            85,
            5,
            "angleAEB",
        ),
        (
            {"query_id": "inscribed_angle_from_central", "target_answer": 35},
            35,
            4,
            "angleACB",
        ),
        (
            {"query_id": "central_angle_from_inscribed", "target_answer": 70},
            70,
            4,
            "angleAOB",
        ),
        (
            {"query_id": "inscribed_angle_from_arc", "target_answer": 35},
            35,
            3,
            "angleACB",
        ),
        (
            {"query_id": "tangent_chord_angle_from_arc", "target_answer": 45},
            45,
            3,
            "anglePTA",
        ),
        (
            {"query_id": "tangent_chord_angle_from_inscribed", "target_answer": 45},
            45,
            4,
            "anglePTA",
        ),
        (
            {"query_id": "external_two_secants_angle_from_arcs", "target_answer": 50},
            50,
            5,
            "angleBPD",
        ),
        (
            {"query_id": "opposite_angle_supplement", "target_answer": 75},
            75,
            4,
            "angleABC",
        ),
        (
            {"query_id": "exterior_angle_from_opposite_interior", "target_answer": 75},
            75,
            5,
            "angleEBC",
        ),
    ),
)
def test_geometry_circle_theorem_value_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_annotation_count: int,
    expected_canonical_segment: str,
) -> None:
    out = GeometryCircleTheoremValueTask().generate(
        23401, params=params, max_attempts=40
    )

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.annotation_gt.type == "keyed_point_map"
    assert len(out.annotation_gt.value) == int(expected_annotation_count)
    assert (
        out.trace_payload["execution_trace"]["canonical_answer_segment"]
        == expected_canonical_segment
    )
    assert out.trace_payload["execution_trace"]["target_answer"] == int(expected_answer)
    assert (
        out.trace_payload["query_spec"]["params"]["query_id"]
        == params["query_id"]
    )
    assert len(out.trace_payload["execution_trace"]["distractor_tokens"]) >= 1
    support_measurement_tokens = set(
        out.trace_payload["witness_symbolic"]["support_measurement_tokens"]
    )
    annotation_point_labels = set(
        out.trace_payload["witness_symbolic"]["annotation_point_labels"]
    )
    assert not (
        set(out.trace_payload["execution_trace"]["distractor_tokens"])
        & support_measurement_tokens
    )
    assert set(out.annotation_gt.value) == annotation_point_labels
    assert annotation_point_labels <= set(out.trace_payload["render_map"]["point_pixels"])
    assert "exactly these visible point-label keys" in out.prompt
    for label in annotation_point_labels:
        assert f'"{label}"' in out.prompt
    all_tokens = set(out.trace_payload["render_map"]["measurement_token_bboxes"])
    assert not any(str(token).startswith("angle") for token in all_tokens)
    assert any(str(token).startswith("∠") for token in all_tokens)
    for token in out.trace_payload["execution_trace"]["distractor_tokens"]:
        assert token in out.trace_payload["render_map"]["measurement_token_bboxes"]

    projected = out.trace_payload["projected_annotation"]
    assert projected["type"] == "keyed_point_map"
    assert projected["keyed_point_map"] == out.annotation_gt.value
    assert projected["pixel_keyed_point_map"] == out.annotation_gt.value
    assert len(projected["point_set"]) == int(expected_annotation_count)
    assert all(
        isinstance(point, list) and len(point) == 2 for point in projected["point_set"]
    )
    assert all(
        isinstance(point, list) and len(point) == 2
        for point in out.annotation_gt.value.values()
    )
    assert all("=" in str(token) for token in support_measurement_tokens)


def test_geometry_circle_theorem_value_is_deterministic() -> None:
    params = {
        "query_id": "secant_secant_variable_segment_length",
        "target_answer": 24,
        "secant_secant_variable_target_kind": "inside_first",
    }
    task = GeometryCircleTheoremValueTask()

    out_a = task.generate(23411, params=params, max_attempts=40)
    out_b = task.generate(23411, params=params, max_attempts=40)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_geometry_circle_theorem_reserves_visible_o_for_center() -> None:
    task = GeometryCircleTheoremValueTask()
    variants = (
        "diameter_perpendicular_chord_length",
        "secant_secant_variable_segment_length",
        "tangent_secant_length",
        "secant_secant_length",
        "intersecting_chords_arc_measure",
        "multi_step_angle_value",
        "inscribed_angle_from_central",
        "central_angle_from_inscribed",
        "inscribed_angle_from_arc",
        "tangent_chord_angle_from_arc",
        "tangent_chord_angle_from_inscribed",
        "external_two_secants_angle_from_arcs",
        "opposite_angle_supplement",
        "exterior_angle_from_opposite_interior",
    )

    for seed in range(23450, 23460):
        for query_id in variants:
            out = task.generate(
                seed, params={"query_id": query_id}, max_attempts=100
            )
            label_map = out.trace_payload["execution_trace"]["label_map"]

            assert label_map["O"] == "O"
            assert all(
                visible != "O"
                for canonical, visible in label_map.items()
                if canonical != "O"
            )


def test_geometry_circle_theorem_value_rejects_unsupported_variant() -> None:
    with pytest.raises(ValueError):
        GeometryCircleTheoremValueTask().generate(
            23421,
            params={"query_id": "inscribed_angle_measure", "target_answer": 8},
            max_attempts=20,
        )


def test_tangent_secant_variant_places_tangent_point_on_circle() -> None:
    out = GeometryCircleTheoremValueTask().generate(
        23431,
        params={
            "query_id": "tangent_secant_length",
            "target_answer": 24,
            "tangent_secant_target_kind": "outside",
        },
        max_attempts=40,
    )
    point_model = out.trace_payload["render_map"]["point_model"]
    trace = out.trace_payload["execution_trace"]
    label_map = trace["label_map"]

    px, py = point_model[label_map["P"]]
    tx, ty = point_model[label_map["T"]]
    ox, oy = point_model[label_map["O"]]
    radius = float(out.trace_payload["render_map"]["circle_radius_model"])

    assert math.isclose(
        math.hypot(float(tx) - float(ox), float(ty) - float(oy)), radius, abs_tol=1e-7
    )
    assert math.isclose(
        math.hypot(float(tx) - float(px), float(ty) - float(py)),
        float(trace["PT"]),
        abs_tol=1e-7,
    )
    assert int(trace["PA"]) == int(out.answer_gt.value)
    tangent_vector = (float(tx) - float(px), float(ty) - float(py))
    radius_vector = (float(tx) - float(ox), float(ty) - float(oy))
    dot_product = (tangent_vector[0] * radius_vector[0]) + (
        tangent_vector[1] * radius_vector[1]
    )
    assert math.isclose(dot_product, 0.0, abs_tol=1e-7)


@pytest.mark.parametrize(
    ("target_kind", "target_answer", "canonical_answer_segment"),
    (
        ("outside", 24, "PA"),
        ("inside", 30, "AB"),
        ("tangent", 60, "PT"),
    ),
)
def test_tangent_secant_variant_supports_multiple_missing_segments(
    target_kind: str,
    target_answer: int,
    canonical_answer_segment: str,
) -> None:
    out = GeometryCircleTheoremValueTask().generate(
        23435,
        params={
            "query_id": "tangent_secant_length",
            "target_answer": target_answer,
            "tangent_secant_target_kind": target_kind,
        },
        max_attempts=40,
    )
    trace = out.trace_payload["execution_trace"]

    assert trace["target_kind"] == target_kind
    assert trace["canonical_answer_segment"] == canonical_answer_segment
    assert int(out.answer_gt.value) == int(target_answer)
    assert int(trace["PT"]) * int(trace["PT"]) == int(trace["PA"]) * int(trace["PB"])
    assert int(trace["PB"]) == int(trace["PA"]) + int(trace["AB"])


def test_secant_secant_variant_places_intersections_on_circle_and_preserves_power() -> (
    None
):
    out = GeometryCircleTheoremValueTask().generate(
        23441,
        params={"query_id": "secant_secant_length", "target_answer": 10},
        max_attempts=40,
    )
    point_model = out.trace_payload["render_map"]["point_model"]
    trace = out.trace_payload["execution_trace"]
    label_map = trace["label_map"]
    ox, oy = point_model[label_map["O"]]
    radius = float(out.trace_payload["render_map"]["circle_radius_model"])

    for label in ("A", "B", "C", "D"):
        x, y = point_model[label_map[label]]
        assert math.isclose(
            math.hypot(float(x) - float(ox), float(y) - float(oy)), radius, abs_tol=1e-7
        )
    assert int(trace["PA"]) * int(trace["PB"]) == int(trace["PC"]) * int(trace["PD"])
    assert int(trace["PA"]) == int(out.answer_gt.value)


@pytest.mark.parametrize(
    ("target_kind", "target_answer", "canonical_answer_segment"),
    (
        ("outside_first", 10, "PA"),
        ("inside_first", 24, "AB"),
        ("outside_second", 12, "PC"),
        ("inside_second", 20, "CD"),
    ),
)
def test_secant_secant_variable_variant_supports_multiple_missing_segments(
    target_kind: str,
    target_answer: int,
    canonical_answer_segment: str,
) -> None:
    out = GeometryCircleTheoremValueTask().generate(
        23445,
        params={
            "query_id": "secant_secant_variable_segment_length",
            "target_answer": target_answer,
            "secant_secant_variable_target_kind": target_kind,
        },
        max_attempts=40,
    )
    trace = out.trace_payload["execution_trace"]

    assert trace["theorem"] == "secant_secant_variable"
    assert trace["target_kind"] == target_kind
    assert trace["canonical_answer_segment"] == canonical_answer_segment
    assert int(out.answer_gt.value) == int(target_answer)
    assert int(trace["PA"]) * int(trace["PB"]) == int(trace["PC"]) * int(trace["PD"])
    assert int(trace["PB"]) == int(trace["PA"]) + int(trace["AB"])
    assert int(trace["PD"]) == int(trace["PC"]) + int(trace["CD"])
    assert len(out.annotation_gt.value) == 5

@pytest.mark.parametrize(
    "query_id",
    (
        "tangent_secant_length",
        "secant_secant_length",
        "secant_secant_variable_segment_length",
        "external_two_secants_angle_from_arcs",
    ),
)
def test_secant_theorem_variants_sample_external_point_on_both_sides(
    query_id: str,
) -> None:
    task = GeometryCircleTheoremValueTask()
    observed_sides: set[str] = set()

    for seed in range(23480, 23490):
        out = task.generate(seed, params={"query_id": query_id}, max_attempts=100)
        trace = out.trace_payload["execution_trace"]
        label_map = trace["label_map"]
        point_model = out.trace_payload["render_map"]["point_model"]
        external_x = float(point_model[label_map["P"]][0])
        center_x = float(point_model[label_map["O"]][0])
        side = str(trace["external_point_side"])

        observed_sides.add(side)
        if side == "left":
            assert external_x < center_x
        elif side == "right":
            assert external_x > center_x
        else:
            raise AssertionError(f"unsupported side: {side!r}")

    assert observed_sides == {"left", "right"}


def test_intersecting_chords_arc_variant_uses_angle_arc_relationship() -> None:
    out = GeometryCircleTheoremValueTask().generate(
        23451,
        params={
            "query_id": "intersecting_chords_arc_measure",
            "target_answer": 120,
        },
        max_attempts=40,
    )
    trace = out.trace_payload["execution_trace"]

    assert int(trace["angle_AEB"]) * 2 == int(trace["arc_AB"]) + int(trace["arc_CD"])
    assert int(trace["arc_CD"]) == int(out.answer_gt.value)
    assert "arc " in out.prompt
    assert "arcCD" not in out.prompt
    assert len(out.annotation_gt.value) == 5
    assert len(out.trace_payload["projected_annotation"]["pixel_keyed_point_map"]) == 5


def test_multi_step_angle_variant_uses_intersecting_chord_arc_sum() -> None:
    out = GeometryCircleTheoremValueTask().generate(
        23453,
        params={"query_id": "multi_step_angle_value", "target_answer": 85},
        max_attempts=40,
    )
    trace = out.trace_payload["execution_trace"]

    assert int(trace["angle_AEB"]) * 2 == int(trace["arc_AB"]) + int(trace["arc_CD"])
    assert int(trace["angle_AEB"]) == int(out.answer_gt.value)
    assert "∠" in out.prompt
    assert "angleAEB" not in out.prompt
    assert len(out.annotation_gt.value) == 5
    assert len(out.trace_payload["projected_annotation"]["pixel_keyed_point_map"]) == 5


def test_external_secant_angle_variant_uses_arc_difference() -> None:
    out = GeometryCircleExternalSecantAngleValueTask().generate(
        23454,
        params={"target_answer": 50},
        max_attempts=60,
    )
    trace = out.trace_payload["execution_trace"]

    assert trace["theorem"] == "external_secant_angle_from_arcs"
    assert int(trace["angle_BPD"]) == int(out.answer_gt.value)
    assert (
        int(trace["far_intercepted_arc_measure"])
        - int(trace["near_intercepted_arc_measure"])
    ) == 2 * int(out.answer_gt.value)
    assert "∠" in out.prompt
    assert "angleBPD" not in out.prompt
    assert "arc " in out.prompt
    assert len(out.annotation_gt.value) == 5
    assert set(out.annotation_gt.value) == set(
        out.trace_payload["witness_symbolic"]["annotation_point_labels"]
    )


def test_cyclic_quadrilateral_opposite_angle_variant_uses_supplement() -> None:
    out = GeometryCircleCyclicQuadrilateralAngleValueTask().generate(
        23458,
        params={"query_id": "opposite_angle_supplement", "target_answer": 75},
        max_attempts=60,
    )
    trace = out.trace_payload["execution_trace"]

    assert trace["theorem"] == "cyclic_quadrilateral_angle"
    assert int(trace["angle_ABC"]) + int(trace["angle_CDA"]) == 180
    assert int(trace["answer_value"]) == int(out.answer_gt.value)
    assert int(out.answer_gt.value) == 75
    assert "∠" in out.prompt
    assert "angleABC" not in out.prompt
    assert "angleCDA" not in out.prompt
    assert len(out.annotation_gt.value) == 4
    assert set(out.annotation_gt.value) == set(
        out.trace_payload["witness_symbolic"]["annotation_point_labels"]
    )


def test_cyclic_quadrilateral_exterior_angle_variant_matches_opposite_angle() -> None:
    out = GeometryCircleCyclicQuadrilateralAngleValueTask().generate(
        23459,
        params={
            "query_id": "exterior_angle_from_opposite_interior",
            "target_answer": 75,
        },
        max_attempts=60,
    )
    trace = out.trace_payload["execution_trace"]

    assert trace["theorem"] == "cyclic_quadrilateral_angle"
    assert int(trace["angle_ABC"]) + int(trace["angle_CDA"]) == 180
    assert int(trace["answer_value"]) == int(out.answer_gt.value)
    assert int(out.answer_gt.value) == 75
    assert str(trace["extension_point"]) in out.annotation_gt.value
    assert str(trace["known_angle"]) in out.prompt
    assert "∠" in out.prompt
    assert "angleADE" not in out.prompt
    assert "angleEBC" not in out.prompt
    assert len(out.annotation_gt.value) == 5


@pytest.mark.parametrize(
    ("query_id", "target_answer"),
    (
        ("inscribed_angle_from_central", 35),
        ("central_angle_from_inscribed", 70),
        ("inscribed_angle_from_arc", 35),
    ),
)
def test_inscribed_angle_variants_use_half_arc_relationship(
    query_id: str, target_answer: int
) -> None:
    out = GeometryCircleTheoremValueTask().generate(
        23455,
        params={"query_id": query_id, "target_answer": target_answer},
        max_attempts=40,
    )
    trace = out.trace_payload["execution_trace"]

    assert int(trace["central_angle_AOB"]) == int(trace["arc_AB"])
    assert int(trace["central_angle_AOB"]) == 2 * int(trace["inscribed_angle_ACB"])
    assert int(out.answer_gt.value) == int(target_answer)
    assert "∠" in out.prompt
    assert "angleAOB" not in out.prompt
    assert "angleACB" not in out.prompt
    expected_count = 3 if query_id == "inscribed_angle_from_arc" else 4
    assert len(out.annotation_gt.value) == expected_count


@pytest.mark.parametrize(
    "query_id",
    ("tangent_chord_angle_from_arc", "tangent_chord_angle_from_inscribed"),
)
def test_tangent_chord_angle_variants_use_matching_angle_or_arc(
    query_id: str,
) -> None:
    out = GeometryCircleTheoremValueTask().generate(
        23457,
        params={"query_id": query_id, "target_answer": 45},
        max_attempts=40,
    )
    trace = out.trace_payload["execution_trace"]

    assert int(trace["arc_TA"]) == 2 * int(trace["angle_PTA"])
    assert int(trace["angle_TBA"]) == int(trace["angle_PTA"])
    assert int(trace["angle_PTA"]) == int(out.answer_gt.value)
    assert "∠" in out.prompt
    assert "anglePTA" not in out.prompt
    expected_count = 3 if query_id == "tangent_chord_angle_from_arc" else 4
    assert len(out.annotation_gt.value) == expected_count


def test_circle_theorem_rendered_label_boxes_avoid_lines_and_circle() -> None:
    task = GeometryCircleTheoremValueTask()
    variants = (
        "diameter_perpendicular_chord_length",
        "secant_secant_variable_segment_length",
        "tangent_secant_length",
        "secant_secant_length",
        "intersecting_chords_arc_measure",
        "multi_step_angle_value",
        "inscribed_angle_from_central",
        "central_angle_from_inscribed",
        "inscribed_angle_from_arc",
        "tangent_chord_angle_from_arc",
        "tangent_chord_angle_from_inscribed",
        "external_two_secants_angle_from_arcs",
        "opposite_angle_supplement",
        "exterior_angle_from_opposite_interior",
    )

    for seed in (50000, 50001):
        for query_id in variants:
            out = task.generate(
                seed, params={"query_id": query_id}, max_attempts=100
            )
            render_map = out.trace_payload["render_map"]
            segments = [
                (
                    tuple(float(coord) for coord in endpoints[0]),
                    tuple(float(coord) for coord in endpoints[1]),
                )
                for endpoints in render_map["segment_pixels"].values()
            ]
            label_boxes = dict(render_map["measurement_token_bboxes"])
            label_boxes.update(
                {
                    f"point:{key}": value
                    for key, value in render_map["point_label_bboxes"].items()
                }
            )
            for label, bbox in label_boxes.items():
                assert not any(
                    _segment_crosses_bbox(a, b, bbox) for a, b in segments
                ), (query_id, seed, label, bbox)
                assert not _circle_crosses_bbox(
                    render_map["circle_center_pixel"],
                    float(render_map["circle_radius_px"]),
                    bbox,
                ), (query_id, seed, label, bbox)


def test_geometry_circle_task_group_config_exposes_variants_and_prompts() -> None:
    cfg = get_task_group_defaults("geometry", "circle")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="geometry_circle_theorem_value_base",
    )

    assert bool(generation["balanced_query_id_sampling"]) is True
    assert bool(generation["balanced_answer_sampling"]) is True
    assert set(generation["query_id_weights"].keys()) == {
        "diameter_perpendicular_chord_length",
        "secant_secant_variable_segment_length",
        "tangent_secant_length",
        "secant_secant_length",
        "intersecting_chords_arc_measure",
        "multi_step_angle_value",
        "inscribed_angle_from_central",
        "central_angle_from_inscribed",
        "inscribed_angle_from_arc",
        "tangent_chord_angle_from_arc",
        "tangent_chord_angle_from_inscribed",
        "external_two_secants_angle_from_arcs",
        "opposite_angle_supplement",
        "exterior_angle_from_opposite_interior",
    }
    assert list(
        generation["secant_secant_variable_segment_length_answer_support"]
    ) == list(range(4, 61))
    assert min(generation["tangent_secant_length_answer_support"]) >= 11
    assert max(generation["tangent_secant_length_answer_support"]) == 100
    assert list(generation["intersecting_chords_arc_measure_answer_support"]) == [
        40,
        50,
        60,
        70,
        80,
        90,
        100,
        110,
        120,
        130,
        140,
        150,
        160,
        170,
        180,
    ]
    assert list(generation["multi_step_angle_value_answer_support"]) == [
        45,
        50,
        55,
        60,
        65,
        70,
        75,
        80,
        85,
        90,
        95,
        100,
        105,
        110,
        115,
        120,
        125,
        130,
        135,
    ]
    assert list(generation["inscribed_angle_from_central_answer_support"]) == [
        20,
        25,
        30,
        35,
        40,
        45,
        50,
        55,
        60,
        65,
        70,
        75,
        80,
    ]
    assert list(generation["central_angle_from_inscribed_answer_support"]) == [
        40,
        50,
        60,
        70,
        80,
        90,
        100,
        110,
        120,
        130,
        140,
        150,
        160,
    ]
    assert list(generation["tangent_chord_angle_from_arc_answer_support"]) == [
        25,
        30,
        35,
        40,
        45,
        50,
        55,
        60,
        65,
        70,
        75,
    ]
    assert list(generation["external_two_secants_angle_from_arcs_answer_support"]) == [
        20,
        25,
        30,
        35,
        40,
        45,
        50,
        55,
        60,
        65,
        70,
        75,
    ]
    assert list(generation["opposite_angle_supplement_answer_support"]) == list(
        range(45, 136, 5)
    )
    assert list(generation["exterior_angle_from_opposite_interior_answer_support"]) == list(
        range(45, 136, 5)
    )
    assert int(rendering["line_width"]) > 0
    assert str(prompt["bundle_id"]) == "geometry_circle_theorem_v0"

    chord_generation, _, chord_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_geometry__circle_theorem__chord_length_from_radius_angle_value",
    )
    assert set(chord_generation["query_id_weights"].keys()) == {
        "chord_length_from_radius_and_central_angle",
        "chord_length_from_radius_and_inscribed_angle",
    }
    assert list(chord_generation["radius_support"]) == list(range(6, 17))
    assert list(chord_generation["central_angle_support"]) == [60, 90, 120, 150]
    assert list(chord_generation["inscribed_angle_support"]) == [30, 45, 60, 75]
    assert str(chord_prompt["answer_hint_number"]).strip()
    assert str(chord_prompt["annotation_hint_chord_length_points"]).strip()

    tangent_radius_generation, _, tangent_radius_prompt = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_geometry__circle_theorem__tangent_radius_right_triangle_length_value",
        )
    )
    assert set(tangent_radius_generation["query_id_weights"].keys()) == {
        "radius_from_external_distance_and_angle",
        "tangent_length_from_radius_and_external_distance",
    }
    assert list(
        tangent_radius_generation["tangent_radius_external_distance_support"]
    ) == [8, 10, 12, 14, 16, 18, 20]
    assert list(tangent_radius_generation["tangent_radius_angle_support"]) == [
        30,
        45,
        60,
    ]
    assert str(tangent_radius_prompt["answer_hint_tangent_radius_number"]).strip()
    assert str(tangent_radius_prompt["annotation_hint_tangent_radius_points"]).strip()
