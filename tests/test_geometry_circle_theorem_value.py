"""Contract tests for the geometry circle-theorem value task."""

from __future__ import annotations

import math

import pytest

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.geometry.circle.theorem_value import GeometryCircleTheoremValueTask
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
    (
        "params",
        "expected_answer",
        "expected_evidence_count",
        "expected_canonical_segment",
    ),
    (
        (
            {"query_id": "diameter_perpendicular_chord_length", "target_answer": 8},
            8,
            2,
            "BE",
        ),
        (
            {
                "query_id": "secant_secant_variable_segment_length",
                "target_answer": 24,
                "secant_secant_variable_target_kind": "inside_first",
            },
            24,
            3,
            "AB",
        ),
        (
            {
                "query_id": "tangent_secant_length",
                "target_answer": 24,
                "tangent_secant_target_kind": "outside",
            },
            24,
            2,
            "PA",
        ),
        (
            {"query_id": "secant_secant_length", "target_answer": 10},
            10,
            3,
            "PA",
        ),
        (
            {"query_id": "intersecting_chords_arc_measure", "target_answer": 120},
            120,
            2,
            "arcCD",
        ),
        (
            {"query_id": "multi_step_angle_value", "target_answer": 85},
            85,
            2,
            "angleAEB",
        ),
        (
            {"query_id": "inscribed_angle_from_central", "target_answer": 35},
            35,
            1,
            "angleACB",
        ),
        (
            {"query_id": "central_angle_from_inscribed", "target_answer": 70},
            70,
            1,
            "angleAOB",
        ),
        (
            {"query_id": "inscribed_angle_from_arc", "target_answer": 35},
            35,
            1,
            "angleACB",
        ),
        (
            {"query_id": "tangent_chord_angle_from_arc", "target_answer": 45},
            45,
            1,
            "anglePTA",
        ),
        (
            {"query_id": "tangent_chord_angle_from_inscribed", "target_answer": 45},
            45,
            1,
            "anglePTA",
        ),
    ),
)
def test_geometry_circle_theorem_value_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_evidence_count: int,
    expected_canonical_segment: str,
) -> None:
    out = GeometryCircleTheoremValueTask().generate(
        23401, params=params, max_attempts=40
    )

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == int(expected_evidence_count)
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
    evidence_tokens = set(out.trace_payload["witness_symbolic"]["evidence_tokens"])
    assert not (
        set(out.trace_payload["execution_trace"]["distractor_tokens"]) & evidence_tokens
    )
    all_tokens = set(out.trace_payload["render_map"]["measurement_token_bboxes"])
    assert not any(str(token).startswith("angle") for token in all_tokens)
    assert any(str(token).startswith("∠") for token in all_tokens)
    for token in out.trace_payload["execution_trace"]["distractor_tokens"]:
        assert token in out.trace_payload["render_map"]["measurement_token_bboxes"]

    projected = out.trace_payload["projected_evidence"]
    assert projected["type"] == "bbox_set"
    assert projected["bbox_set"] == out.evidence_gt.value
    assert projected["pixel_bbox_set"] == out.evidence_gt.value
    assert len(projected["point_set"]) == int(expected_evidence_count)
    assert all(
        isinstance(point, list) and len(point) == 2 for point in projected["point_set"]
    )
    assert len(projected["pixel_bbox_set"]) == int(expected_evidence_count)
    assert all(
        isinstance(bbox, list) and len(bbox) == 4 for bbox in out.evidence_gt.value
    )
    assert all("=" in str(token) for token in evidence_tokens)


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
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
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
    assert len(out.evidence_gt.value) == 3


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
    assert len(out.evidence_gt.value) == 2
    assert len(out.trace_payload["projected_evidence"]["pixel_bbox_set"]) == 2


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
    assert len(out.evidence_gt.value) == 2
    assert len(out.trace_payload["projected_evidence"]["pixel_bbox_set"]) == 2


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
    assert len(out.evidence_gt.value) == 1


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
    assert len(out.evidence_gt.value) == 1


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
    assert int(rendering["line_width"]) > 0
    assert str(prompt["bundle_id"]) == "geometry_circle_theorem_v0"
