"""Tests for synthetic 3D surface-fixture repeated-element counts."""

from __future__ import annotations

import trace.tasks  # noqa: F401 - registers tasks.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks import create_task
from trace.tasks.registry import list_default_task_ids
from trace.tasks.three_d.spatial.surface_fixture_count import (
    ELEMENT_TYPE_BY_SCENE_VARIANT,
    TASK_ID,
)


def test_surface_fixture_repeated_element_count_variants() -> None:
    task = create_task(TASK_ID)

    for index, (scene_variant, element_type) in enumerate(ELEMENT_TYPE_BY_SCENE_VARIANT.items()):
        count = 8 + index * 2
        output = task.generate(
            20260604 + index,
            params={
                "query_id": "element_type_count",
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
        assert output.query_id == "element_type_count"
        assert output.answer_gt.type == "integer"
        assert output.answer_gt.value == count
        assert output.annotation_gt.type == "bbox_set"
        assert len(output.annotation_gt.value) == count
        assert trace["scene_variant"] == scene_variant
        assert trace["target_element_type"] == element_type
        assert output.annotation_gt.value == [render_map["element_bboxes_px"][element_id] for element_id in target_element_ids]
        assert output.trace_payload["projected_annotation"]["bbox_set"] == output.annotation_gt.value
        assert output.trace_payload["query_spec"]["params"]["target_element_type"] == element_type
        assert output.trace_payload["query_spec"]["prompt_variant"]["scene_key"] == "surface_fixture"
        assert any(entity["entity_id"] == "surface_fixture_panel" for entity in output.trace_payload["scene_ir"]["entities"])
        assert "{target_" not in output.prompt
        assert output.image.size == (1180, 900)


def test_surface_fixture_task_registered_in_three_d_taxonomy() -> None:
    taxonomy = resolve_task_taxonomy(TASK_ID)

    assert TASK_ID in list_default_task_ids()
    assert taxonomy.domain == "three_d"
    assert taxonomy.scene_id == "surface_fixture"
    assert taxonomy.source_task_group == "spatial"
