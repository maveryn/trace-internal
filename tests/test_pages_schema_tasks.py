"""Behavior tests for pages database-schema diagram tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.pages.schema.database_diagram import (
    FIELD_ROLE_COUNT_TASK_ID,
    RELATIONSHIP_COUNT_TASK_ID,
    PagesSchemaFieldRoleCountTask,
    PagesSchemaRelationshipCountTask,
)


def _assert_bboxes_inside_image(out) -> None:
    width, height = out.image.size
    for bbox in out.evidence_gt.value:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 <= x1 <= float(width)
        assert 0.0 <= y0 <= y1 <= float(height)


def test_pages_schema_tasks_are_registered_in_public_taxonomy() -> None:
    for task_id in [FIELD_ROLE_COUNT_TASK_ID, RELATIONSHIP_COUNT_TASK_ID]:
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "pages"
        assert taxonomy.scene_id == "schema"
        assert taxonomy.source_task_group == "schema"


def test_pages_schema_field_role_count_contract() -> None:
    task = PagesSchemaFieldRoleCountTask()
    for query_id in ("all_field_count", "attribute_field_count"):
        out = task.generate(94200, params={"query_id": query_id, "layout_variant": "grid"}, max_attempts=10)
        trace = out.trace_payload
        query = trace["execution_trace"]["query"]
        expected = [
            trace["render_map"]["field_bboxes_px"][str(field_id)]
            for field_id in query["evidence_field_ids"]
        ]

        assert out.scene_id == "schema"
        assert out.query_variant == "default"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert int(out.answer_gt.value) == int(query["answer"])
        assert len(out.evidence_gt.value) == int(out.answer_gt.value)
        assert out.evidence_gt.value == expected
        assert sorted(out.prompt_variants) == ["answer_and_evidence", "answer_only"]
        _assert_bboxes_inside_image(out)


def test_pages_schema_relationship_count_contract() -> None:
    task = PagesSchemaRelationshipCountTask()
    for query_id in ("total_relationship_count",):
        out = task.generate(94240, params={"query_id": query_id, "layout_variant": "radial"}, max_attempts=10)
        trace = out.trace_payload
        query = trace["execution_trace"]["query"]
        expected = [
            trace["render_map"]["relationship_bboxes_px"][str(relationship_id)]
            for relationship_id in query["evidence_relationship_ids"]
        ]

        assert out.scene_id == "schema"
        assert out.query_variant == "default"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == int(query["answer"])
        assert len(out.evidence_gt.value) == int(out.answer_gt.value)
        assert out.evidence_gt.value == expected
        _assert_bboxes_inside_image(out)


def test_pages_schema_generation_is_deterministic() -> None:
    task = PagesSchemaFieldRoleCountTask()
    params = {"query_id": "attribute_field_count", "layout_variant": "grid", "style_variant": "green_erd"}
    out_a = task.generate(94280, params=params, max_attempts=10)
    out_b = task.generate(94280, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_pages_schema_sampling_covers_visual_and_text_axes() -> None:
    task = PagesSchemaRelationshipCountTask()
    layouts: Counter[str] = Counter()
    styles: Counter[str] = Counter()
    contexts: Counter[str] = Counter()
    queries: Counter[str] = Counter()

    for index in range(24):
        out = task.generate(hash64(94320, "schema_axes", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        layouts[str(execution["layout_variant"])] += 1
        styles[str(execution["style_variant"])] += 1
        contexts[str(execution["context_id"])] += 1
        queries[str(execution["query_id"])] += 1

    assert set(layouts) == {"grid", "layered", "radial"}
    assert set(styles) == {"green_erd", "violet_cards", "monochrome_sql", "amber_blueprint"}
    assert len(contexts) >= 5
    assert set(queries) == {"total_relationship_count"}
