"""Tests for synthetic 3D surface-fixture repeated-element counts."""

from __future__ import annotations

import inspect
from pathlib import Path

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.scene_package_migration import parse_public_task_id
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import TASK_REGISTRY, ensure_scene_tasks_registered
from trace.tasks.shared.named_colors import available_named_colors
from trace.tasks.three_d.shared.object_resources import object_profiles
from trace.tasks.three_d.surface_fixture.adjacent_to_reference_count import TASK_ID as ADJACENT_TASK_ID
from trace.tasks.three_d.surface_fixture.colored_element_count import TASK_ID as COLORED_TASK_ID
from trace.tasks.three_d.surface_fixture.empty_or_missing_cell_count import TASK_ID as EMPTY_MISSING_TASK_ID
from trace.tasks.three_d.surface_fixture.repeated_element_count import TASK_ID
from trace.tasks.three_d.surface_fixture.repeated_element_count import TASK_ID as REPEATED_TASK_ID
from trace.tasks.three_d.surface_fixture.scoped_colored_element_count import TASK_ID as SCOPED_COLORED_TASK_ID
from trace.tasks.three_d.surface_fixture.shared.state import (
    ELEMENT_TYPE_BY_SCENE_VARIANT,
    SEMANTIC_COLOR_RGB,
    SEMANTIC_COLOR_SUPPORT,
)
from trace.tasks.three_d.surface_fixture.shared.layout import VALID_LAYOUT_FAMILIES, VALID_LAYOUT_STYLES
from trace.tasks.three_d.surface_fixture.state_element_count import TASK_ID as STATE_TASK_ID


SURFACE_FIXTURE_TASK_IDS = (
    REPEATED_TASK_ID,
    COLORED_TASK_ID,
    STATE_TASK_ID,
    SCOPED_COLORED_TASK_ID,
    EMPTY_MISSING_TASK_ID,
    ADJACENT_TASK_ID,
)


def test_surface_fixture_semantic_colors_use_canonical_palette() -> None:
    canonical = {
        str(name): (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        for name, rgb in available_named_colors()
    }

    assert dict(SEMANTIC_COLOR_RGB) == canonical
    assert tuple(SEMANTIC_COLOR_SUPPORT) == tuple(canonical)


def test_surface_fixture_repeated_element_count_variants() -> None:
    task = create_task(TASK_ID)

    for index, (scene_variant, element_type) in enumerate(ELEMENT_TYPE_BY_SCENE_VARIANT.items()):
        count = 8 + (index % 9)
        output = task.generate(
            20260604 + index,
            params={
                "query_id": "single",
                "scene_variant": scene_variant,
                "target_count": count,
                "post_image_noise_apply_prob": 0.0,
            },
            max_attempts=10,
        )

        trace = output.trace_payload["execution_trace"]
        render_map = output.trace_payload["render_map"]
        target_element_ids = [str(element_id) for element_id in trace["target_element_ids"]]

        assert output.scene_id == "surface_fixture"
        assert output.query_id == "single"
        assert output.answer_gt.type == "integer"
        assert output.answer_gt.value == count
        assert output.annotation_gt.type == "point_set"
        assert len(output.annotation_gt.value) == count
        assert trace["scene_variant"] == scene_variant
        assert trace["target_element_type"] == element_type
        assert trace["layout_family"] in set(VALID_LAYOUT_FAMILIES)
        assert trace["layout_style"] in set(VALID_LAYOUT_STYLES)
        if scene_variant == "perforated_panel":
            assert trace["layout_family"] == "tiled_staggered"
            assert trace["layout_style"] != "panel_scatter"
        assert output.annotation_gt.value == [render_map["element_centers_px"][element_id] for element_id in target_element_ids]
        assert output.trace_payload["projected_annotation"]["point_set"] == output.annotation_gt.value
        assert output.trace_payload["projected_annotation"]["pixel_point_set"] == output.annotation_gt.value
        assert output.trace_payload["query_spec"]["params"]["target_element_type"] == element_type
        assert output.trace_payload["query_spec"]["prompt_variant"]["scene_key"] == "surface_fixture"
        assert any(entity["entity_id"] == "surface_fixture_panel" for entity in output.trace_payload["scene_ir"]["entities"])
        assert "{target_" not in output.prompt
        assert "repeated" not in output.prompt.lower()
        assert output.image.size == (1180, 900)


def test_surface_fixture_predicate_count_tasks() -> None:
    cases = [
        (
            COLORED_TASK_ID,
            {
                "query_id": "single",
                "scene_variant": "locker_bank",
                "target_count": 4,
                "distractor_count": 6,
                "target_color_name": "red",
                "post_image_noise_apply_prob": 0.0,
            },
        ),
        (
            STATE_TASK_ID,
            {
                "query_id": "single",
                "scene_variant": "server_rack",
                "target_count": 3,
                "distractor_count": 7,
                "target_state": "lit",
                "post_image_noise_apply_prob": 0.0,
            },
        ),
        (
            SCOPED_COLORED_TASK_ID,
            {
                "query_id": "single",
                "scene_variant": "solar_panel_array",
                "target_count": 3,
                "target_color_name": "blue",
                "scope_axis": "row",
                "scope_index": 1,
                "layout_rows": 4,
                "layout_columns": 5,
                "post_image_noise_apply_prob": 0.0,
            },
        ),
        (
            EMPTY_MISSING_TASK_ID,
            {
                "query_id": "single",
                "scene_variant": "brick_wall",
                "missing_count": 5,
                "total_slots": 16,
                "post_image_noise_apply_prob": 0.0,
            },
        ),
        (
            ADJACENT_TASK_ID,
            {
                "query_id": "single",
                "scene_variant": "control_panel",
                "target_count": 4,
                "reference_color_name": "purple",
                "layout_rows": 4,
                "layout_columns": 5,
                "reference_index": 6,
                "post_image_noise_apply_prob": 0.0,
            },
        ),
    ]

    for index, (task_id, params) in enumerate(cases):
        output = create_task(task_id).generate(20260630 + index, params=params, max_attempts=20)
        trace = output.trace_payload["execution_trace"]
        target_element_ids = [str(element_id) for element_id in trace["target_element_ids"]]

        assert output.scene_id == "surface_fixture"
        assert output.answer_gt.type == "integer"
        assert output.answer_gt.value == len(target_element_ids)
        assert output.annotation_gt.type == "point_set"
        assert len(output.annotation_gt.value) == output.answer_gt.value
        assert output.annotation_gt.value == [
            output.trace_payload["render_map"]["element_centers_px"][element_id] for element_id in target_element_ids
        ]
        assert "{target_" not in output.prompt
        assert "{scope_" not in output.prompt
        assert "{reference_" not in output.prompt


def test_surface_fixture_task_registered_in_three_d_taxonomy() -> None:
    ensure_scene_tasks_registered("three_d", "surface_fixture")

    for task_id in SURFACE_FIXTURE_TASK_IDS:
        task = create_task(task_id)
        taxonomy = resolve_task_taxonomy(task_id)
        parts = parse_public_task_id(task_id)
        expected_source = (
            Path(__file__).resolve().parents[1]
            / "trace"
            / "tasks"
            / parts.domain
            / parts.scene_id
            / f"{parts.objective_contract}.py"
        ).resolve()

        assert task_id in TASK_REGISTRY
        assert not hasattr(task, "scene_id")
        assert Path(inspect.getsourcefile(task.__class__) or "").resolve() == expected_source
        assert taxonomy.domain == "three_d"
        assert taxonomy.scene_id == "surface_fixture"
        assert not taxonomy.source_scene_id


def test_surface_fixture_resource_profiles_match_scene_variants() -> None:
    profile_variants = {profile.object_type for profile in object_profiles(source_scene="surface_fixture")}

    assert profile_variants == set(ELEMENT_TYPE_BY_SCENE_VARIANT)
