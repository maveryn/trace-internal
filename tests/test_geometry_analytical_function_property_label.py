"""Contract tests for analytical 2D function-property label task."""

from __future__ import annotations

from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.geometry.analytical.function_property_label import (
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    GeometryAnalyticalFunctionPropertyLabelTask,
)


def _matching_labels(variant: str, relations_by_label: dict[str, dict], answer_label: str) -> list[str]:
    if variant == "function_status_label":
        return [label for label, relation in relations_by_label.items() if bool(relation["is_function"])]
    if variant == "one_to_one_status_label":
        return [
            label
            for label, relation in relations_by_label.items()
            if bool(relation["is_function"]) and bool(relation["is_one_to_one"])
        ]
    if variant == "y_axis_symmetry_label":
        return [label for label, relation in relations_by_label.items() if bool(relation["symmetric_about_y_axis"])]
    if variant == "x_axis_symmetry_label":
        return [label for label, relation in relations_by_label.items() if bool(relation["symmetric_about_x_axis"])]
    if variant == "origin_symmetry_label":
        return [label for label, relation in relations_by_label.items() if bool(relation["symmetric_about_origin"])]
    if variant == "domain_match_label":
        target = relations_by_label[str(answer_label)]["domain"]
        return [label for label, relation in relations_by_label.items() if relation["domain"] == target]
    if variant == "range_match_label":
        target = relations_by_label[str(answer_label)]["range"]
        return [label for label, relation in relations_by_label.items() if relation["range"] == target]
    if variant in {"monotonic_interval_increasing_label", "monotonic_interval_decreasing_label"}:
        increasing = variant == "monotonic_interval_increasing_label"
        labels: list[str] = []
        for label, relation in relations_by_label.items():
            points = [point for point in relation["points"] if -2.0 <= float(point[0]) <= 2.0]
            y_values = [float(point[1]) for point in sorted(points, key=lambda point: float(point[0]))]
            if len(y_values) >= 2 and all(
                (right > left if increasing else right < left)
                for left, right in zip(y_values, y_values[1:])
            ):
                labels.append(label)
        return labels
    if variant in {"sign_interval_positive_label", "sign_interval_negative_label"}:
        positive = variant == "sign_interval_positive_label"
        return [
            label
            for label, relation in relations_by_label.items()
            if relation["points"]
            and all((float(point[1]) > 0.0 if positive else float(point[1]) < 0.0) for point in relation["points"])
        ]
    raise AssertionError(f"unsupported variant in test: {variant}")


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_geometry_analytical_function_property_label_contract(query_id: str) -> None:
    task = GeometryAnalyticalFunctionPropertyLabelTask()
    out = task.generate(
        hash64(93210, TASK_ID, 3),
        params={"query_id": query_id, "winner_label": "C"},
        max_attempts=10,
    )

    assert out.query_id == query_id
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "C"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert out.trace_payload["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert out.trace_payload["query_spec"]["template_id"] == "geometry_analytical_function_property_v0"
    assert out.image.size == (1024, 720)

    relations = out.trace_payload["execution_trace"]["relations_by_label"]
    assert set(relations.keys()) == {"A", "B", "C", "D", "E", "F"}
    assert _matching_labels(query_id, relations, "C") == ["C"]


def test_geometry_analytical_function_property_label_balances_variants_and_answers() -> None:
    task = GeometryAnalyticalFunctionPropertyLabelTask()
    per_query_id_labels = {variant: Counter() for variant in SUPPORTED_QUERY_IDS}

    total = len(SUPPORTED_QUERY_IDS) * 30
    for index in range(total):
        out = task.generate(
            hash64(93220, TASK_ID, index),
            params={},
            max_attempts=10,
        )
        per_query_id_labels[str(out.query_id)][str(out.answer_gt.value)] += 1

    variant_counts = {variant: sum(counter.values()) for variant, counter in per_query_id_labels.items()}
    assert set(variant_counts) == set(SUPPORTED_QUERY_IDS)
    assert all(20 <= count <= 40 for count in variant_counts.values())
    for counts in per_query_id_labels.values():
        assert set(counts.keys()).issubset({"A", "B", "C", "D", "E", "F"})
        assert len(counts) >= 5
        assert max(counts.values()) <= 12


def test_geometry_analytical_function_property_label_randomizes_relation_geometry() -> None:
    task = GeometryAnalyticalFunctionPropertyLabelTask()
    observed_winner_points = set()
    observed_domains = set()

    for index in range(12):
        out = task.generate(
            hash64(93230, TASK_ID, index),
            params={"query_id": "one_to_one_status_label", "winner_label": "A"},
            max_attempts=10,
        )
        winner = out.trace_payload["execution_trace"]["winner_relation"]
        observed_winner_points.add(tuple(tuple(point) for point in winner["points"]))
        observed_domains.add(tuple(winner["domain"]))

    assert len(observed_winner_points) >= 6
    assert len(observed_domains) >= 4
