"""Tests for the synthetic 3D object-cluster count task."""

from __future__ import annotations

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import TASK_REGISTRY, ensure_scene_tasks_registered
from trace.tasks.shared.named_colors import available_named_colors
from trace.tasks.three_d.shared.object_inventory_preview import render_three_d_object_profile_preview
from trace.tasks.three_d.shared.object_resources import OBJECT_CLUSTER_EXTRA_SHAPE_TYPES, object_profiles
from trace.tasks.three_d.object_cluster.color_membership_count import TASK_ID as COLOR_MEMBERSHIP_COUNT_TASK_ID
from trace.tasks.three_d.object_cluster.count_arithmetic import TASK_ID as COUNT_ARITHMETIC_TASK_ID
from trace.tasks.three_d.object_cluster.multi_attribute_and_count import TASK_ID as MULTI_ATTRIBUTE_AND_TASK_ID
from trace.tasks.three_d.object_cluster.multi_attribute_exclusion_count import (
    TASK_ID as MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID,
)
from trace.tasks.three_d.object_cluster.multi_attribute_or_count import TASK_ID as MULTI_ATTRIBUTE_OR_COUNT_TASK_ID
from trace.tasks.three_d.object_cluster.shared.defaults import (
    COLOR_SAFE_CLUSTER_SHAPE_TYPES,
    COUNTABLE_SHAPE_TYPES,
    PROMPT_COLOR_RGB,
)
from trace.tasks.three_d.object_cluster.single_attribute_membership_count import TASK_ID
from trace.tasks.three_d.object_cluster.total_object_count import TASK_ID as TOTAL_OBJECT_COUNT_TASK_ID
from trace.tasks.three_d.object_cluster.type_frequency_count import TASK_ID as TYPE_FREQUENCY_COUNT_TASK_ID
from trace.tasks.three_d.object_cluster.type_union_count import TASK_ID as TYPE_UNION_COUNT_TASK_ID
from tests.three_d_canvas_helpers import assert_three_d_canvas_contract


COUNTQA_CLUSTER_ADDITIONS = {
    "mini_chair",
    "mini_table",
    "heater",
    "flower",
    "glass",
    "jar",
    "can",
    "lid",
    "tube",
    "clip",
    "socket",
    "chess_piece",
    "light_bulb",
    "egg",
    "chili",
    "paint_brush",
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
    "coffee_bean",
    "hook",
    "tape_roll",
    "bag",
}


def test_object_cluster_prompt_colors_use_canonical_palette() -> None:
    canonical = {
        str(name): (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        for name, rgb in available_named_colors()
    }

    assert dict(PROMPT_COLOR_RGB) == canonical


def test_object_cluster_total_object_count_answer_and_annotation() -> None:
    task = create_task(TOTAL_OBJECT_COUNT_TASK_ID)
    output = task.generate(
        20260606,
        params={
            "query_id": "single",
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
    assert output.query_id == "single"
    assert trace["internal_query_id"] == "total_object_count"
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
    assert_three_d_canvas_contract(output)


def test_object_cluster_instance_count_answer_and_annotation() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260601,
        params={
            "query_id": "single",
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
    assert output.query_id == "single"
    assert trace["internal_query_id"] == "type_count"
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
    assert_three_d_canvas_contract(output)


def test_object_cluster_single_type_mode_counts_every_object() -> None:
    task = create_task(TASK_ID)
    output = task.generate(
        20260602,
        params={
            "query_id": "single",
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
    ensure_scene_tasks_registered("three_d", "object_cluster")
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in TASK_REGISTRY
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_cluster"
    assert not taxonomy.source_scene_id


def test_object_cluster_total_object_count_registered_in_three_d_taxonomy() -> None:
    ensure_scene_tasks_registered("three_d", "object_cluster")
    taxonomy = resolve_task_taxonomy(TOTAL_OBJECT_COUNT_TASK_ID)

    assert TOTAL_OBJECT_COUNT_TASK_ID in TASK_REGISTRY
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_cluster"
    assert not taxonomy.source_scene_id


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
            "query_id": "single",
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
    assert output.query_id == "single"
    assert trace["internal_query_id"] == "type_and_color_count"
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
    assert_three_d_canvas_contract(output)


def test_object_cluster_multi_attribute_and_count_registered_in_three_d_taxonomy() -> None:
    ensure_scene_tasks_registered("three_d", "object_cluster")
    taxonomy = resolve_task_taxonomy(MULTI_ATTRIBUTE_AND_TASK_ID)

    assert MULTI_ATTRIBUTE_AND_TASK_ID in TASK_REGISTRY
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "object_cluster"
    assert not taxonomy.source_scene_id
    assert len(COLOR_SAFE_CLUSTER_SHAPE_TYPES) >= 12
    assert {
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
        "tape_roll",
        "bag",
    }.issubset(set(COLOR_SAFE_CLUSTER_SHAPE_TYPES))


def test_object_cluster_color_membership_count_answer_and_annotation() -> None:
    task = create_task(COLOR_MEMBERSHIP_COUNT_TASK_ID)
    output = task.generate(
        20260611,
        params={
            "query_id": "single",
            "scene_variant": "shallow_tray",
            "object_count": 18,
            "target_count": 5,
            "target_color_name": "blue",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=300,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    object_specs = list(trace["object_specs"])
    target_object_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    expected_ids = [
        str(spec["object_id"])
        for spec in sorted(object_specs, key=lambda item: str(item["object_id"]))
        if str(spec["color_name"]) == "blue"
    ]

    assert output.query_id == "single"
    assert trace["internal_query_id"] == "color_count"
    assert output.answer_gt.value == 5
    assert output.annotation_gt.type == "bbox_set"
    assert target_object_ids == expected_ids
    assert output.annotation_gt.value == [render_map["object_bboxes_px"][object_id] for object_id in target_object_ids]
    assert all(bool(spec["matches_query"]) == (str(spec["color_name"]) == "blue") for spec in object_specs)


def test_object_cluster_multi_attribute_or_count_counts_overlap_once() -> None:
    task = create_task(MULTI_ATTRIBUTE_OR_COUNT_TASK_ID)
    output = task.generate(
        20260612,
        params={
            "query_id": "single",
            "scene_variant": "tabletop_pile",
            "object_count": 20,
            "target_count": 6,
            "target_shape_type": "button",
            "target_color_name": "red",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=300,
    )

    trace = output.trace_payload["execution_trace"]
    object_specs = list(trace["object_specs"])
    target_object_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    expected_ids = [
        str(spec["object_id"])
        for spec in sorted(object_specs, key=lambda item: str(item["object_id"]))
        if str(spec["shape_type"]) == "button" or str(spec["color_name"]) == "red"
    ]

    assert output.query_id == "single"
    assert trace["internal_query_id"] == "type_or_color_count"
    assert output.answer_gt.value == len(expected_ids) == 6
    assert target_object_ids == expected_ids
    assert len(target_object_ids) == len(set(target_object_ids))
    assert any(str(spec["shape_type"]) == "button" and str(spec["color_name"]) == "red" for spec in object_specs)


def test_object_cluster_multi_attribute_exclusion_count_answer_and_annotation() -> None:
    task = create_task(MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID)
    output = task.generate(
        20260613,
        params={
            "query_id": "type_and_not_color_count",
            "scene_variant": "cluster_mat",
            "object_count": 19,
            "target_count": 5,
            "target_shape_type": "button",
            "target_color_name": "red",
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=300,
    )

    trace = output.trace_payload["execution_trace"]
    object_specs = list(trace["object_specs"])
    target_object_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    expected_ids = [
        str(spec["object_id"])
        for spec in sorted(object_specs, key=lambda item: str(item["object_id"]))
        if str(spec["shape_type"]) == "button" and str(spec["color_name"]) != "red"
    ]

    assert output.query_id == "type_and_not_color_count"
    assert output.answer_gt.value == 5
    assert target_object_ids == expected_ids
    assert output.annotation_gt.type == "bbox_set"
    assert any(str(spec["shape_type"]) == "button" and str(spec["color_name"]) == "red" for spec in object_specs)


def test_object_cluster_type_union_count_answer_and_annotation() -> None:
    task = create_task(TYPE_UNION_COUNT_TASK_ID)
    output = task.generate(
        20260614,
        params={
            "query_id": "single",
            "scene_variant": "tabletop_pile",
            "object_count": 20,
            "target_count": 7,
            "target_shape_types": ["button", "marble"],
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=300,
    )

    trace = output.trace_payload["execution_trace"]
    object_specs = list(trace["object_specs"])
    target_object_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    expected_ids = [
        str(spec["object_id"])
        for spec in sorted(object_specs, key=lambda item: str(item["object_id"]))
        if str(spec["shape_type"]) in {"button", "marble"}
    ]

    assert output.query_id == "single"
    assert trace["internal_query_id"] == "two_type_union_count"
    assert output.answer_gt.value == 7
    assert target_object_ids == expected_ids
    assert output.annotation_gt.type == "bbox_set"
    assert set(trace["target_shape_types"]) == {"button", "marble"}


def test_object_cluster_count_arithmetic_keyed_operand_annotation() -> None:
    task = create_task(COUNT_ARITHMETIC_TASK_ID)
    output = task.generate(
        20260615,
        params={
            "query_id": "two_type_difference_count",
            "scene_variant": "shallow_tray",
            "left_shape_type": "button",
            "right_shape_type": "marble",
            "left_operand_count": 6,
            "right_operand_count": 2,
            "object_count": 18,
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=300,
    )

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    role_object_ids = trace["role_object_ids"]
    left_ids = [str(object_id) for object_id in role_object_ids["left_operand"]]
    right_ids = [str(object_id) for object_id in role_object_ids["right_operand"]]

    assert output.query_id == "two_type_difference_count"
    assert output.answer_gt.value == 4
    assert output.annotation_gt.type == "keyed_bbox_set_map"
    assert set(output.annotation_gt.value) == {"left_operand", "right_operand"}
    assert len(output.annotation_gt.value["left_operand"]) == 6
    assert len(output.annotation_gt.value["right_operand"]) == 2
    assert output.annotation_gt.value["left_operand"] == [render_map["object_bboxes_px"][object_id] for object_id in left_ids]
    assert output.annotation_gt.value["right_operand"] == [render_map["object_bboxes_px"][object_id] for object_id in right_ids]
    assert output.trace_payload["projected_annotation"]["keyed_bbox_set_map"] == output.annotation_gt.value


def test_object_cluster_type_frequency_singleton_count_answer_and_annotation() -> None:
    task = create_task(TYPE_FREQUENCY_COUNT_TASK_ID)
    output = task.generate(
        20260616,
        params={
            "query_id": "singleton_type_count",
            "scene_variant": "cluster_mat",
            "object_count": 18,
            "target_count": 4,
            "target_shape_types": ["button", "marble", "bead", "ticket"],
            "post_image_noise_apply_prob": 0.0,
        },
        max_attempts=300,
    )

    trace = output.trace_payload["execution_trace"]
    object_specs = list(trace["object_specs"])
    target_object_ids = [str(object_id) for object_id in trace["target_object_ids"]]
    shape_counts = trace["shape_counts"]
    expected_ids = [
        str(spec["object_id"])
        for spec in sorted(object_specs, key=lambda item: str(item["object_id"]))
        if int(shape_counts[str(spec["shape_type"])]) == 1
    ]

    assert output.query_id == "singleton_type_count"
    assert output.answer_gt.value == 4
    assert target_object_ids == expected_ids
    assert output.annotation_gt.type == "bbox_set"
    assert len(output.annotation_gt.value) == 4


def test_object_cluster_first_wave_tasks_registered_in_three_d_taxonomy() -> None:
    ensure_scene_tasks_registered("three_d", "object_cluster")
    for task_id in (
        COLOR_MEMBERSHIP_COUNT_TASK_ID,
        MULTI_ATTRIBUTE_OR_COUNT_TASK_ID,
        MULTI_ATTRIBUTE_EXCLUSION_COUNT_TASK_ID,
        TYPE_UNION_COUNT_TASK_ID,
        COUNT_ARITHMETIC_TASK_ID,
        TYPE_FREQUENCY_COUNT_TASK_ID,
    ):
        taxonomy = resolve_task_taxonomy(task_id)

        assert task_id in TASK_REGISTRY
        assert taxonomy.domain == "three_d"
        assert taxonomy.scene_id == "object_cluster"
        assert not taxonomy.source_scene_id
