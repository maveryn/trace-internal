"""Regression tests for survey-traverse geometry tasks."""

from __future__ import annotations

import json

import pytest

from trace.core.taxonomy import lookup_task_taxonomy
from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.geometry.survey_traverse.bearing_angle_value import GeometrySurveyTraverseBearingAngleValueTask
from trace.tasks.geometry.survey_traverse.shared.measurement.survey_traverse_common import (
    AREA_QUERY_IDS,
    ELEVATION_QUERY_IDS,
    QUERY_IDS,
    SCENE_ID,
    TASK_ID,
    TASK_ID_BEARING_ANGLE,
    TASK_ID_STATION_ELEVATION,
    TASK_ID_TRAVERSE_AREA,
)
from trace.tasks.geometry.survey_traverse.station_elevation_value import GeometrySurveyTraverseStationElevationValueTask
from trace.tasks.geometry.survey_traverse.traverse_area_value import GeometrySurveyTraverseTraverseAreaValueTask


def _generate(seed: int, *, task_id: str = TASK_ID_BEARING_ANGLE, **params):
    task = create_task(task_id)
    return task.generate(seed, params=dict(params), max_attempts=20)


def test_survey_traverse_bearing_angle_registered_public_task() -> None:
    assert TASK_ID == TASK_ID_BEARING_ANGLE
    assert TASK_ID_BEARING_ANGLE in TASK_REGISTRY
    assert TASK_ID_STATION_ELEVATION in TASK_REGISTRY
    assert TASK_ID_TRAVERSE_AREA in TASK_REGISTRY
    assert TASK_REGISTRY[TASK_ID_BEARING_ANGLE] is GeometrySurveyTraverseBearingAngleValueTask
    assert TASK_REGISTRY[TASK_ID_STATION_ELEVATION] is GeometrySurveyTraverseStationElevationValueTask
    assert TASK_REGISTRY[TASK_ID_TRAVERSE_AREA] is GeometrySurveyTraverseTraverseAreaValueTask
    bearing_taxonomy = lookup_task_taxonomy(TASK_ID_BEARING_ANGLE)
    assert bearing_taxonomy is not None
    assert bearing_taxonomy.domain == "geometry"
    assert bearing_taxonomy.scene_id == SCENE_ID
    elevation_taxonomy = lookup_task_taxonomy(TASK_ID_STATION_ELEVATION)
    assert elevation_taxonomy is not None
    assert elevation_taxonomy.domain == "geometry"
    assert elevation_taxonomy.scene_id == SCENE_ID
    area_taxonomy = lookup_task_taxonomy(TASK_ID_TRAVERSE_AREA)
    assert area_taxonomy is not None
    assert area_taxonomy.domain == "geometry"
    assert area_taxonomy.scene_id == SCENE_ID


def test_back_bearing_contract_and_formula() -> None:
    out = _generate(
        20260611,
        query_id="bearing_from_back_bearing",
        target_bearing=50,
        station_labels=("A", "B", "C"),
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == "bearing_from_back_bearing"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 50
    assert execution["known_back_bearing"] == 230
    assert execution["target_forward_bearing"] == 50

    assert out.annotation_gt.type == "keyed_point_map"
    assert set(out.annotation_gt.value) == {
        "station_a",
        "station_b",
        "reference_north",
        "target_direction",
    }
    _assert_point_map_inside_image(out.annotation_gt.value, out.image.size)
    assert "task_variant" not in json.dumps(trace)


def test_closed_traverse_contract_and_formula() -> None:
    out = _generate(
        20260612,
        query_id="closed_traverse_missing_bearing",
        base_bearing=100,
        turn_angle=45,
        turn_direction="right",
        station_labels=("A", "B", "C"),
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == "closed_traverse_missing_bearing"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 145
    assert execution["known_bearing"] == 100
    assert execution["turn_angle"] == 45
    assert execution["turn_direction"] == "right"
    assert execution["target_bearing"] == 145

    assert out.annotation_gt.type == "keyed_point_map"
    assert set(out.annotation_gt.value) == {
        "station_a",
        "station_b",
        "reference_north",
        "target_direction",
        "turn_vertex",
    }
    assert out.annotation_gt.value["station_b"] == out.annotation_gt.value["turn_vertex"]
    _assert_point_map_inside_image(out.annotation_gt.value, out.image.size)
    assert "task_variant" not in json.dumps(trace)


def test_leveling_station_elevation_contract_and_formula() -> None:
    out = _generate(
        20260614,
        task_id=TASK_ID_STATION_ELEVATION,
        query_id="leveling_station_elevation",
        elevation_case=(120, 4, 7),
        station_labels=("A", "B", "C"),
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == "leveling_station_elevation"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 117
    assert execution["reference_elevation"] == 120
    assert execution["backsight"] == 4
    assert execution["foresight"] == 7
    assert execution["height_of_instrument"] == 124
    assert execution["target_elevation"] == 117
    assert execution["formula_family"] == "survey_leveling_station_elevation"

    assert out.annotation_gt.type == "keyed_point_map"
    assert tuple(out.annotation_gt.value) == (
        "reference_station",
        "target_station",
        "measurement_line",
        "field_note_region",
    )
    assert trace["projected_annotation"]["keyed_point_map"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_keyed_point_map"] == out.annotation_gt.value
    _assert_point_map_inside_image(out.annotation_gt.value, out.image.size)
    assert "task_variant" not in json.dumps(trace)


def test_slope_distance_elevation_change_contract_and_formula() -> None:
    out = _generate(
        20260615,
        task_id=TASK_ID_STATION_ELEVATION,
        query_id="slope_distance_elevation_change",
        elevation_case=(120, 60, -3),
        station_labels=("A", "B", "C"),
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == "slope_distance_elevation_change"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 111
    assert execution["reference_elevation"] == 120
    assert execution["slope_distance"] == 60
    assert execution["rise_per_20"] == -3
    assert execution["total_rise"] == -9
    assert execution["target_elevation"] == 111
    assert execution["formula_family"] == "survey_slope_distance_elevation_change"

    assert out.annotation_gt.type == "keyed_point_map"
    assert tuple(out.annotation_gt.value) == (
        "reference_station",
        "target_station",
        "measurement_line",
        "field_note_region",
    )
    assert trace["render_spec"]["prompt"]["prompt_variant"]["prompt_bundle_id"] == "geometry_survey_traverse_v0"
    _assert_point_map_inside_image(out.annotation_gt.value, out.image.size)
    assert "task_variant" not in json.dumps(trace)


def test_coordinate_traverse_area_contract_and_formula() -> None:
    out = _generate(
        20260617,
        task_id=TASK_ID_TRAVERSE_AREA,
        query_id="coordinate_traverse_area",
        area_case=(0, 0, 6, 0, 7, 4, 0, 6),
        station_labels=("A", "B", "C"),
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == "coordinate_traverse_area"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 33
    assert execution["formula_family"] == "survey_coordinate_traverse_area"
    assert execution["coordinate_points"] == [[0, 0], [6, 0], [7, 4], [0, 6]]
    assert execution["answer"] == 33

    assert out.annotation_gt.type == "keyed_bbox_map"
    assert tuple(out.annotation_gt.value) == (
        "traverse_region",
        "field_note_region",
        "area_reference_region",
    )
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_keyed_bbox_map"] == out.annotation_gt.value
    _assert_bbox_map_inside_image(out.annotation_gt.value, out.image.size)
    assert "task_variant" not in json.dumps(trace)


def test_offset_trapezoid_area_contract_and_formula() -> None:
    out = _generate(
        20260618,
        task_id=TASK_ID_TRAVERSE_AREA,
        query_id="offset_trapezoid_area",
        area_case=(20, 40, 60, 3, 5, 4, 2),
        station_labels=("A", "B", "C"),
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.scene_id == SCENE_ID
    assert out.query_id == "offset_trapezoid_area"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 230
    assert execution["formula_family"] == "survey_offset_trapezoid_area"
    assert execution["chainages"] == [0, 20, 40, 60]
    assert execution["offsets"] == [3, 5, 4, 2]
    assert execution["answer"] == 230

    assert out.annotation_gt.type == "keyed_bbox_map"
    assert tuple(out.annotation_gt.value) == (
        "traverse_region",
        "field_note_region",
        "area_reference_region",
    )
    assert trace["render_spec"]["prompt"]["prompt_variant"]["prompt_bundle_id"] == "geometry_survey_traverse_v0"
    _assert_bbox_map_inside_image(out.annotation_gt.value, out.image.size)
    assert "task_variant" not in json.dumps(trace)


@pytest.mark.parametrize("query_id", QUERY_IDS)
def test_survey_traverse_bearing_generation_is_deterministic(query_id: str) -> None:
    params = {"query_id": query_id}
    first = _generate(20260613, **params)
    second = _generate(20260613, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
    assert first.image.tobytes() == second.image.tobytes()


@pytest.mark.parametrize("query_id", ELEVATION_QUERY_IDS)
def test_survey_traverse_station_elevation_generation_is_deterministic(query_id: str) -> None:
    params = {"query_id": query_id}
    first = _generate(20260616, task_id=TASK_ID_STATION_ELEVATION, **params)
    second = _generate(20260616, task_id=TASK_ID_STATION_ELEVATION, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
    assert first.image.tobytes() == second.image.tobytes()


@pytest.mark.parametrize("query_id", AREA_QUERY_IDS)
def test_survey_traverse_area_generation_is_deterministic(query_id: str) -> None:
    params = {"query_id": query_id}
    first = _generate(20260619, task_id=TASK_ID_TRAVERSE_AREA, **params)
    second = _generate(20260619, task_id=TASK_ID_TRAVERSE_AREA, **params)

    assert first.prompt == second.prompt
    assert first.answer_gt == second.answer_gt
    assert first.annotation_gt == second.annotation_gt
    assert first.trace_payload["execution_trace"] == second.trace_payload["execution_trace"]
    assert first.image.tobytes() == second.image.tobytes()


def test_survey_traverse_bearing_rejects_invalid_params() -> None:
    task = create_task(TASK_ID_BEARING_ANGLE)
    with pytest.raises(ValueError):
        task.generate(1, params={"query_id": "bad_query"}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(1, params={"query_id": "bearing_from_back_bearing", "target_bearing": 17}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(
            1,
            params={"query_id": "closed_traverse_missing_bearing", "turn_direction": "clockwise"},
            max_attempts=1,
        )
    with pytest.raises(ValueError):
        task.generate(1, params={"station_labels": ("A", "A", "B")}, max_attempts=1)


def test_survey_traverse_station_elevation_rejects_invalid_params() -> None:
    task = create_task(TASK_ID_STATION_ELEVATION)
    with pytest.raises(ValueError):
        task.generate(1, params={"query_id": "bad_query"}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(
            1,
            params={"query_id": "leveling_station_elevation", "elevation_case": (1, 2, 3)},
            max_attempts=1,
        )
    with pytest.raises(ValueError):
        task.generate(
            1,
            params={"query_id": "slope_distance_elevation_change", "elevation_case": "100,80,2"},
            max_attempts=1,
        )


def test_survey_traverse_area_rejects_invalid_params() -> None:
    task = create_task(TASK_ID_TRAVERSE_AREA)
    with pytest.raises(ValueError):
        task.generate(1, params={"query_id": "bad_query"}, max_attempts=1)
    with pytest.raises(ValueError):
        task.generate(
            1,
            params={"query_id": "coordinate_traverse_area", "area_case": (1, 2, 3, 4)},
            max_attempts=1,
        )
    with pytest.raises(ValueError):
        task.generate(
            1,
            params={"query_id": "offset_trapezoid_area", "area_case": "20,40,60,3,5,4,2"},
            max_attempts=1,
        )


def _assert_point_map_inside_image(annotation: dict[str, list[float]], image_size: tuple[int, int]) -> None:
    width, height = image_size
    for point in annotation.values():
        assert isinstance(point, list)
        assert len(point) == 2
        x, y = [float(value) for value in point]
        assert 0.0 <= x <= float(width)
        assert 0.0 <= y <= float(height)


def _assert_bbox_map_inside_image(annotation: dict[str, list[float]], image_size: tuple[int, int]) -> None:
    width, height = image_size
    for bbox in annotation.values():
        assert isinstance(bbox, list)
        assert len(bbox) == 4
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 < x1 <= float(width)
        assert 0.0 <= y0 < y1 <= float(height)
