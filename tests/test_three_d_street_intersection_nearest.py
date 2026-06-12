"""Tests for the 3D street intersection nearest-object task."""

from __future__ import annotations

import pytest

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.street.intersection_nearest import (
    BUILDING_STYLES,
    MIN_NEAREST_DISTANCE_MARGIN,
    SCENE_ID,
    STREET_OBJECT_TYPES,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
)
from tests.three_d_option_panel_helpers import assert_option_panel_matches_candidates


@pytest.mark.parametrize(
    "scene_variant",
    ["downtown_intersection", "neighborhood_intersection", "transit_intersection"],
)
def test_street_intersection_nearest_answer_annotation_and_geometry(scene_variant: str) -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260522,
        params={
            "query_id": "closest_to_intersection",
            "scene_variant": scene_variant,
            "candidate_count": 6,
            "context_object_count": 10,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=220,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    entities = output.trace_payload["scene_ir"]["entities"]
    surface_entity = next(
        entity
        for entity in entities
        if str(entity["entity_id"]) == "street_intersection_surface"
    )
    candidates = list(trace["candidate_object_specs"])
    answer_label = str(trace["answer_label"])
    answer_spec = next(
        spec for spec in candidates if str(spec["point_label"]) == answer_label
    )
    expected_bbox = render_map["object_bboxes_px"][str(answer_spec["object_id"])]
    distances = {
        str(label): float(value)
        for label, value in trace["ground_distance_to_intersection_by_label"].items()
    }
    sorted_labels = sorted(distances, key=lambda label: (distances[label], label))

    assert output.scene_id == SCENE_ID
    assert output.query_id == "closest_to_intersection"
    assert output.answer_gt.type == "option_letter"
    assert output.answer_gt.value == answer_label
    assert output.annotation_gt.type == "bbox_set"
    assert output.annotation_gt.value == [expected_bbox]
    assert_option_panel_matches_candidates(
        output,
        candidates,
        answer_label=answer_label,
        answer_object_id=str(answer_spec["object_id"]),
        expected_image_size=(1180, 1088),
    )
    assert trace["target_object_ids"] == [str(answer_spec["object_id"])]
    assert trace["distance_order_near_to_far"] == sorted_labels
    assert sorted_labels[0] == answer_label
    assert float(trace["nearest_distance_margin"]) >= MIN_NEAREST_DISTANCE_MARGIN
    assert sorted(str(spec["point_label"]) for spec in candidates) == list("ABCDEF")
    assert len(candidates) == 6
    assert len(trace["context_object_specs"]) == 10
    building_styles = {
        str(spec["building_style"])
        for spec in trace["context_object_specs"]
        if str(spec["object_type"]) == "building"
    }
    assert len(building_styles) >= 3
    assert building_styles.issubset(set(BUILDING_STYLES))
    assert str(answer_spec["object_type"]) == str(trace["answer_object_type"])
    answer_entity = next(entity for entity in entities if str(entity["entity_id"]) == str(answer_spec["object_id"]))
    answer_record = answer_entity["attrs"]["object_record"]
    assert answer_record["object_id"] == str(answer_spec["object_id"])
    assert answer_record["object_type"] == str(answer_spec["object_type"])
    assert answer_record["visual_attributes"]["renderer_id"] == "street_object"
    assert answer_record["visual_attributes"]["renderer_style"] == "projected_3d"
    assert render_map["candidate_bboxes_px"][answer_label] == expected_bbox
    assert render_map["street_bbox_px"] == [0.0, 0.0, 1180.0, 920.0]
    assert surface_entity["attrs"]["render_full_bleed_surface"] is True
    assert surface_entity["attrs"]["floor_polygon_mode"] == "canvas_ray_polygon"
    assert "{object_description}" not in output.prompt
    assert "{answer_hint}" not in output.prompt


def test_street_intersection_nearest_registered() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == SCENE_ID
    assert taxonomy.source_scene_id == "street"
    assert SUPPORTED_QUERY_IDS == ("closest_to_intersection",)
    assert {
        "motorcycle",
        "fire_hydrant",
        "trash_bin",
        "mailbox",
        "construction_barrier",
        "road_barrel",
    }.issubset(set(STREET_OBJECT_TYPES))
