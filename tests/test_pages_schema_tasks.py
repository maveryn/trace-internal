"""Behavior tests for pages database-schema diagram tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.pages.schema.database_diagram import (
    FIELD_ROLE_COUNT_TASK_ID,
    RELATIONSHIP_CARDINALITY_TASK_ID,
    RELATIONSHIP_ENDPOINT_TASK_ID,
    RELATIONSHIP_COUNT_TASK_ID,
    PagesSchemaFieldRoleCountTask,
    PagesSchemaRelationshipCardinalityLabelTask,
    PagesSchemaRelationshipEndpointLabelTask,
    PagesSchemaRelationshipCountTask,
)


def _assert_bboxes_inside_image(out) -> None:
    width, height = out.image.size
    annotation_value = out.annotation_gt.value
    bboxes = annotation_value.values() if isinstance(annotation_value, dict) else annotation_value
    for bbox in bboxes:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 <= x1 <= float(width)
        assert 0.0 <= y0 <= y1 <= float(height)


def _assert_point_pairs_inside_image(out) -> None:
    width, height = out.image.size
    for point_pair in out.annotation_gt.value:
        assert len(point_pair) == 2
        for point in point_pair:
            x, y = [float(value) for value in point]
            assert 0.0 <= x <= float(width)
            assert 0.0 <= y <= float(height)


def test_pages_schema_tasks_are_registered_in_public_taxonomy() -> None:
    for task_id in [
        FIELD_ROLE_COUNT_TASK_ID,
        RELATIONSHIP_COUNT_TASK_ID,
        RELATIONSHIP_ENDPOINT_TASK_ID,
        RELATIONSHIP_CARDINALITY_TASK_ID,
    ]:
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "pages"
        assert taxonomy.scene_id == "schema"
        assert taxonomy.source_scene_id == "schema"


def test_pages_schema_field_role_count_contract() -> None:
    task = PagesSchemaFieldRoleCountTask()
    for query_id in ("all_field_count", "attribute_field_count"):
        out = task.generate(94200, params={"query_id": query_id, "layout_variant": "grid"}, max_attempts=10)
        trace = out.trace_payload
        query = trace["execution_trace"]["query"]
        expected = [
            trace["render_map"]["field_bboxes_px"][str(field_id)]
            for field_id in query["annotation_field_ids"]
        ]

        assert out.scene_id == "schema"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.annotation_gt.type == "bbox_set"
        assert int(out.answer_gt.value) == int(query["answer"])
        assert len(out.annotation_gt.value) == int(out.answer_gt.value)
        assert out.annotation_gt.value == expected
        assert sorted(out.prompt_variants) == ["answer_and_annotation", "answer_only"]
        _assert_bboxes_inside_image(out)


def test_pages_schema_relationship_count_contract() -> None:
    task = PagesSchemaRelationshipCountTask()
    for query_id in ("total_relationship_count",):
        out = task.generate(94240, params={"query_id": query_id, "layout_variant": "radial"}, max_attempts=10)
        trace = out.trace_payload
        query = trace["execution_trace"]["query"]
        expected = [
            trace["render_map"]["relationship_point_pairs_px"][str(relationship_id)]
            for relationship_id in query["annotation_relationship_ids"]
        ]

        assert out.scene_id == "schema"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.annotation_gt.type == "point_pair_set"
        assert int(out.answer_gt.value) == int(query["answer"])
        assert len(out.annotation_gt.value) == int(out.answer_gt.value)
        assert out.annotation_gt.value == expected
        _assert_point_pairs_inside_image(out)


def test_pages_schema_relationship_endpoint_label_contract() -> None:
    task = PagesSchemaRelationshipEndpointLabelTask()
    out = task.generate(
        94260,
        params={"query_id": "target_table_for_relationship_label", "layout_variant": "grid"},
        max_attempts=10,
    )
    trace = out.trace_payload
    query = trace["execution_trace"]["query"]
    relationships = trace["execution_trace"]["relationships"]
    matches = [
        relationship
        for relationship in relationships
        if str(relationship["source_label"]) == str(query["source_table_label"])
        and str(relationship["label"]) == str(query["relationship_label"])
    ]
    expected = {
        "source_table": trace["render_map"]["table_bboxes_px"][str(query["source_table_id"])],
        "relationship_label": trace["render_map"]["relationship_label_bboxes_px"][str(query["relationship_id"])],
        "target_table": trace["render_map"]["table_bboxes_px"][str(query["target_table_id"])],
    }

    assert out.scene_id == "schema"
    assert out.query_id == "target_table_for_relationship_label"
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert str(out.answer_gt.value) == str(query["target_table_label"])
    assert str(out.answer_gt.value) == str(query["answer"])
    assert len(matches) == 1
    assert str(matches[0]["target_label"]) == str(out.answer_gt.value)
    assert out.annotation_gt.value == expected
    assert trace["projected_annotation"]["type"] == "keyed_bbox_map"
    assert trace["witness_symbolic"]["type"] == "keyed_bbox_id_map"
    _assert_bboxes_inside_image(out)


def test_pages_schema_relationship_cardinality_label_contract() -> None:
    task = PagesSchemaRelationshipCardinalityLabelTask()
    out = task.generate(
        94270,
        params={"query_id": "relationship_cardinality_between_tables", "layout_variant": "grid"},
        max_attempts=10,
    )
    trace = out.trace_payload
    query = trace["execution_trace"]["query"]
    relationships = trace["execution_trace"]["relationships"]
    relationship_id = str(query["relationship_id"])
    matches = [
        relationship
        for relationship in relationships
        if str(relationship["relationship_id"]) == relationship_id
    ]
    expected = {
        "source_table": trace["render_map"]["table_bboxes_px"][str(query["source_table_id"])],
        "target_table": trace["render_map"]["table_bboxes_px"][str(query["target_table_id"])],
        "source_cardinality_marker": trace["render_map"]["cardinality_marker_bboxes_px"][f"{relationship_id}:source"],
        "target_cardinality_marker": trace["render_map"]["cardinality_marker_bboxes_px"][f"{relationship_id}:target"],
    }

    assert out.scene_id == "schema"
    assert out.query_id == "relationship_cardinality_between_tables"
    assert out.answer_gt.type == "string"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert str(out.answer_gt.value) == str(query["cardinality_kind"])
    assert str(out.answer_gt.value) == str(query["answer"])
    assert str(out.answer_gt.value) in {"one_to_one", "one_to_many", "optional_many"}
    assert trace["query_spec"]["params"]["answer_support"] == ["one_to_many", "optional_many", "one_to_one"]
    assert len(matches) == 1
    assert str(matches[0]["cardinality_kind"]) == str(out.answer_gt.value)
    assert str(matches[0]["source_marker"]) == str(query["source_cardinality_marker"])
    assert str(matches[0]["target_marker"]) == str(query["target_cardinality_marker"])
    assert list(out.annotation_gt.value.keys()) == [
        "source_table",
        "target_table",
        "source_cardinality_marker",
        "target_cardinality_marker",
    ]
    assert out.annotation_gt.value == expected
    assert trace["projected_annotation"]["type"] == "keyed_bbox_map"
    assert trace["projected_annotation"]["keyed_bbox_map"] == expected
    assert trace["witness_symbolic"]["type"] == "keyed_bbox_id_map"
    _assert_bboxes_inside_image(out)


def test_pages_schema_generation_is_deterministic() -> None:
    task = PagesSchemaRelationshipEndpointLabelTask()
    params = {
        "query_id": "target_table_for_relationship_label",
        "layout_variant": "grid",
        "style_variant": "green_erd",
    }
    out_a = task.generate(94280, params=params, max_attempts=10)
    out_b = task.generate(94280, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_pages_schema_relationship_cardinality_generation_is_deterministic() -> None:
    task = PagesSchemaRelationshipCardinalityLabelTask()
    params = {
        "query_id": "relationship_cardinality_between_tables",
        "layout_variant": "radial",
        "style_variant": "amber_blueprint",
    }
    out_a = task.generate(94290, params=params, max_attempts=10)
    out_b = task.generate(94290, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_pages_schema_sampling_covers_visual_and_text_axes() -> None:
    task = PagesSchemaRelationshipEndpointLabelTask()
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
    assert set(queries) == {"target_table_for_relationship_label"}
