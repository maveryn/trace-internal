"""Tests for shared task annotation artifact builders."""

from __future__ import annotations

from trace.tasks.shared.annotation_artifacts import (
    bbox_set_annotation_artifacts,
    point_pair_set_annotation_artifacts,
    point_set_annotation_artifacts,
)


def test_bbox_set_annotation_artifacts_round_and_project() -> None:
    artifacts = bbox_set_annotation_artifacts(
        [
            [1.1114, 2.2225, 3.3336, 4.4447],
            (5, 6, 7, 8),
        ]
    )

    assert artifacts.annotation_type == "bbox_set"
    assert artifacts.value == [[1.111, 2.223, 3.334, 4.445], [5.0, 6.0, 7.0, 8.0]]
    assert artifacts.annotation_gt.type == "bbox_set"
    assert artifacts.annotation_gt.value == artifacts.value
    assert artifacts.projected_annotation == {
        "type": "bbox_set",
        "bbox_set": artifacts.value,
        "pixel_bbox_set": artifacts.value,
    }


def test_point_set_annotation_artifacts_round_and_project() -> None:
    artifacts = point_set_annotation_artifacts(
        [
            [1.1114, 2.2225],
            (3, 4),
        ]
    )

    assert artifacts.annotation_type == "point_set"
    assert artifacts.value == [[1.111, 2.223], [3.0, 4.0]]
    assert artifacts.annotation_gt.type == "point_set"
    assert artifacts.annotation_gt.value == artifacts.value
    assert artifacts.projected_annotation == {
        "type": "point_set",
        "point_set": artifacts.value,
        "pixel_point_set": artifacts.value,
    }


def test_point_pair_set_annotation_artifacts_round_and_project() -> None:
    artifacts = point_pair_set_annotation_artifacts(
        [
            [[1.1114, 2.2225], [3.3336, 4.4447]],
            ((5, 6), (7, 8)),
        ]
    )

    assert artifacts.annotation_type == "point_pair_set"
    assert artifacts.value == [
        [[1.111, 2.223], [3.334, 4.445]],
        [[5.0, 6.0], [7.0, 8.0]],
    ]
    assert artifacts.annotation_gt.type == "point_pair_set"
    assert artifacts.annotation_gt.value == artifacts.value
    assert artifacts.projected_annotation == {
        "type": "point_pair_set",
        "point_pair_set": artifacts.value,
        "pixel_point_pair_set": artifacts.value,
    }


def test_annotation_artifacts_support_empty_sets() -> None:
    assert bbox_set_annotation_artifacts([]).value == []
    assert point_set_annotation_artifacts([]).value == []
    assert point_pair_set_annotation_artifacts([]).value == []
