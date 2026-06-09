"""Tests for the synthetic 3D object-cluster count task."""

from __future__ import annotations

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.shared.object_inventory_preview import render_three_d_object_profile_preview
from trace.tasks.three_d.shared.object_resources import OBJECT_CLUSTER_EXTRA_SHAPE_TYPES, object_profiles
from trace.tasks.three_d.spatial.object_cluster_attribute_count import (
    COLOR_SAFE_CLUSTER_SHAPE_TYPES,
    PROMPT_COLOR_RGB,
    TASK_ID as MULTI_ATTRIBUTE_AND_TASK_ID,
)
from trace.tasks.three_d.spatial.object_cluster_instance_count import COUNTABLE_SHAPE_TYPES, TASK_ID
from trace.tasks.three_d.spatial.object_cluster_total_count import TASK_ID as TOTAL_OBJECT_COUNT_TASK_ID


COUNTQA_CLUSTER_ADDITIONS = {
    "mini_chair",
    "mini_table",
    "heater",
    "flower",
    "towel",
    "glass",
    "jar",
    "can",
    "lid",
    "tube",
    "clip",
    "socket",
    "chess_piece",
    "marker",
    "hanger",
    "light_bulb",
    "egg",
    "chili",
    "paint_brush",
    "paint_roller",
    "stick",
    "straw",
    "ticket",
    "marble",
    "bead",
    "dot",
    "bolt",
    "pillow",
    "cushion",
    "stool",
    "bucket",
    "tray",
    "coaster",
    "rose",
    "tomato",
    "peanut",
    "coffee_bean",
    "hook",
    "bracket",
    "tape_roll",
    "bag",
}


def test_object_cluster_total_object_count_answer_and_annotation() -> None:
    task = create_task(TOTAL_OBJECT_COUNT_TASK_ID)
    output = task.generate(
        20260606,
        params={
            "query_id": "total_object_count",
            "scene_variant": "shallow_tray",
            "object_count": 14,
            "primary_shape_type": "button",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=240,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    counted_object_ids = [str(object_id) for object_id in trace["counted_object_ids"]]
    object_specs = list(trace["object_specs"])

    assert output.scene_id == "object_cluster"
    assert output.query_id == "total_object_count"
    assert trace["cluster_composition_mode"] == "single_type_cluster"
    assert trace["object_count"] == 14
    assert trace["distractor_count"] == 0
    assert output.answer_gt.type == "integer"
    assert output.answer_gt.value == 14
    assert output.annotation_gt.type == "bbox_set"
    assert len(output.annotation_gt.value) == int(output.answer_gt.value)
    assert counted_object_ids == [str(spec["object_id"]) for spec in sorted(object_specs, key=lambda item: str(item["object_id"]))]
    assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in counted_object_ids]
    assert output.trace_payload["projected_annotation"]["bbox_set"] == output.annotation_gt.value
    assert all(str(spec["shape_type"]) == "button" for spec in object_specs)
    assert all(bool(spec.get("matches_query", False)) for spec in object_specs)
    assert all(bool(spec.get("is_countable_object", False)) for spec in object_specs)
    assert "button" not in output.prompt.lower()
    assert output.image.size == (1180, 900)


def test_object_cluster_instance_count_answer_and_annotation() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260601,
        params={
            "query_id": "type_count",
            "scene_variant": "tabletop_pile",
            "object_count": 22,
            "target_count": 6,
            "target_shape_type": "pencil",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=240,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    target_object_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    object_specs = list(trace["object_specs"])

    assert output.scene_id == "object_cluster"
    assert output.query_id == "type_count"
    assert trace["cluster_composition_mode"] == "mixed_type_cluster"
    assert output.answer_gt.type == "integer"
    assert output.answer_gt.value == 6
    assert output.annotation_gt.type == "bbox_set"
    assert len(output.annotation_gt.value) == int(output.answer_gt.value)
    assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_object_ids]
    assert trace["shape_counts"]["pencil"] == 6
    assert all(str(spec["shape_type"]) == "pencil" for spec in object_specs if str(spec["object_id"]) in set(target_object_ids))
    assert all(not bool(spec.get("is_answer_candidate", False)) for spec in object_specs)
    assert all(bool(spec.get("is_countable_object", False)) for spec in object_specs)
    assert trace["solver_trace"]["cluster_object_pool_size"] == len(COUNTABLE_SHAPE_TYPES)
    assert output.trace_payload["projected_annotation"]["bbox_set"] == output.annotation_gt.value
    assert output.image.size == (1180, 900)


def test_object_cluster_single_type_mode_counts_every_object() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260602,
        params={
            "query_id": "type_count",
            "scene_variant": "cluster_mat",
            "composition_mode": "single_type_cluster",
            "target_count": 12,
            "target_shape_type": "spoon",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=240,
    )

    trace = output.trace_payload["execution_trace"]
    object_specs = list(trace["object_specs"])

    assert trace["cluster_composition_mode"] == "single_type_cluster"
    assert trace["object_count"] == 12
    assert trace["target_count"] == 12
    assert trace["distractor_count"] == 0
    assert output.answer_gt.value == 12
    assert len(output.annotation_gt.value) == 12
    assert all(str(spec["shape_type"]) == "spoon" for spec in object_specs)
    assert all(bool(spec.get("matches_query", False)) for spec in object_specs)


def test_object_cluster_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_cluster"
    assert taxonomy.source_task_group == "spatial"


def test_object_cluster_total_object_count_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TOTAL_OBJECT_COUNT_TASK_ID)

    assert TOTAL_OBJECT_COUNT_TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_cluster"
    assert taxonomy.source_task_group == "spatial"


def test_object_cluster_countqa_additions_have_profiles_and_render() -> None:
    assert COUNTQA_CLUSTER_ADDITIONS.issubset(set(OBJECT_CLUSTER_EXTRA_SHAPE_TYPES))
    assert COUNTQA_CLUSTER_ADDITIONS.issubset(set(COUNTABLE_SHAPE_TYPES))
    profiles = {
        str(profile.object_type): profile
        for profile in object_profiles(source_scene="object_cluster", role="cluster_small_shape")
    }

    for shape_type in OBJECT_CLUSTER_EXTRA_SHAPE_TYPES:
        profile = profiles[str(shape_type)]
        assert profile.display_name
        assert profile.dimensions_xyz is not None
        preview = render_three_d_object_profile_preview(
            profile,
            canvas_width=320,
            canvas_height=250,
            instance_seed=20260604,
            crop_to_object=True,
        )
        x0, y0, x1, y1 = preview.object_bbox_px
        assert x1 - x0 > 8.0
        assert y1 - y0 > 8.0


def test_object_cluster_multi_attribute_and_count_answer_and_annotation() -> None:
    task = create_task(MULTI_ATTRIBUTE_AND_TASK_ID)
    output = task.generate(
        20260605,
        params={
            "query_id": "type_and_color_count",
            "scene_variant": "tabletop_pile",
            "object_count": 18,
            "target_count": 4,
            "target_shape_type": "button",
            "target_color_name": "red",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=300,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    target_object_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    object_specs = list(trace["object_specs"])
    expected_ids = [
        str(spec["object_id"])
        for spec in sorted(object_specs, key=lambda item: str(item["object_id"]))
        if str(spec["shape_type"]) == "button" and str(spec["color_name"]) == "red"
    ]

    assert output.scene_id == "object_cluster"
    assert output.query_id == "type_and_color_count"
    assert output.answer_gt.type == "integer"
    assert output.answer_gt.value == 4
    assert output.annotation_gt.type == "bbox_set"
    assert target_object_ids == expected_ids
    assert len(output.annotation_gt.value) == int(output.answer_gt.value)
    assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_object_ids]
    assert output.trace_payload["projected_annotation"]["bbox_set"] == output.annotation_gt.value
    assert trace["target_property_phrase"] == "red buttons"
    assert trace["property_counts"]["red_button"] == 4
    assert all("color_name" in spec and "prompt_color_name" in spec and "fill_rgb" in spec for spec in object_specs)
    assert all(spec["fill_rgb"] == list(PROMPT_COLOR_RGB[str(spec["color_name"])]) for spec in object_specs)
    assert any(str(spec["count_role"]) == "same_type_wrong_color" for spec in object_specs)
    assert any(str(spec["count_role"]) == "same_color_wrong_type" for spec in object_specs)
    assert all(bool(spec["matches_query"]) == (str(spec["shape_type"]) == "button" and str(spec["color_name"]) == "red") for spec in object_specs)
    assert output.image.size == (1180, 900)


def test_object_cluster_multi_attribute_and_count_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(MULTI_ATTRIBUTE_AND_TASK_ID)

    assert MULTI_ATTRIBUTE_AND_TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_cluster"
    assert taxonomy.source_task_group == "spatial"
    assert len(COLOR_SAFE_CLUSTER_SHAPE_TYPES) >= 12
    assert {
        "hanger",
        "paint_roller",
        "straw",
        "ticket",
        "marble",
        "bead",
        "dot",
        "pillow",
        "cushion",
        "stool",
        "bucket",
        "tray",
        "coaster",
        "hook",
        "bracket",
        "tape_roll",
        "bag",
    }.issubset(set(COLOR_SAFE_CLUSTER_SHAPE_TYPES))
