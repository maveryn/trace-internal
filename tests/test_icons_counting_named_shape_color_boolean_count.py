"""Tests for named-shape / visual-attribute Boolean icon counting."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.icons.named_field.multi_attribute_and_count import QUERY_IDS, QUERY_IDS_BY_TASK_ID


TASK_ID_BY_QUERY_ID = {
    query_id: task_id
    for task_id, query_ids in QUERY_IDS_BY_TASK_ID.items()
    for query_id in query_ids
}


def _predicate(query_id: str, *, is_shape: bool, is_attribute: bool) -> bool:
    if query_id == "shape_and_color_count":
        return is_shape and is_attribute
    if query_id == "shape_or_color_count":
        return is_shape or is_attribute
    if query_id == "shape_and_not_color_count":
        return is_shape and not is_attribute
    if query_id == "color_and_not_shape_count":
        return is_attribute and not is_shape
    if query_id == "neither_shape_nor_color_count":
        return (not is_shape) and (not is_attribute)
    if query_id == "exactly_one_shape_or_color_count":
        return bool(is_shape) ^ bool(is_attribute)
    raise AssertionError(f"unexpected query_id: {query_id}")


def test_icons_counting_named_shape_color_boolean_contract_all_queries() -> None:
    for index, query_id in enumerate(QUERY_IDS):
        task = create_task(TASK_ID_BY_QUERY_ID[str(query_id)])
        out = task.generate(
            hash64(20260523, "named-shape-color-boolean-contract", index),
            params={
                "query_id": query_id,
                "attribute_axis": "color",
                "target_shape_id": "star",
                "target_color_name": "red",
                "target_count": 4,
                "object_count": 7,
                "arrangement_mode": "ordered_grid",
            },
            max_attempts=200,
        )
        trace = out.trace_payload
        entities = trace["scene_ir"]["entities"]
        target_shape = trace["query_spec"]["params"]["target_shape_id"]
        target_color = trace["query_spec"]["params"]["target_color_name"]
        counted_entities = [
            entity
            for entity in entities
            if _predicate(
                query_id,
                is_shape=str(entity["shape_id"]) == str(target_shape),
                is_attribute=str(entity["color_name"]) == str(target_color),
            )
        ]

        assert out.scene_id == "named_field"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.answer_gt.value == 4
        assert out.annotation_gt.type == "bbox_set"
        assert len(out.annotation_gt.value) == 4
        assert len(counted_entities) == 4
        assert "star" in out.prompt
        assert "red [#E63232]" in out.prompt
        assert all("color_name" in entity for entity in entities)
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
        assert trace["projected_annotation"]["type"] == "bbox_set"
        assert trace["projected_annotation"]["pixel_bbox_set"] == out.annotation_gt.value
        assert set(trace["render_map"]["counted_instance_ids"]) == {str(entity["instance_id"]) for entity in counted_entities}
        assert sorted(out.annotation_gt.value) == sorted(entity["bbox_xyxy"] for entity in counted_entities)


def test_icons_counting_named_shape_color_boolean_fill_style_axis_contract() -> None:
    query_id = "shape_and_color_count"
    task = create_task(TASK_ID_BY_QUERY_ID[str(query_id)])
    out = task.generate(
        hash64(20260523, "named-shape-fill-style-boolean-contract", 0),
        params={
            "query_id": query_id,
            "attribute_axis": "fill_style",
            "target_shape_id": "star",
            "target_fill_style": "striped",
            "target_count": 3,
            "object_count": 6,
            "arrangement_mode": "ordered_grid",
        },
        max_attempts=200,
    )
    trace = out.trace_payload
    entities = trace["scene_ir"]["entities"]
    target_shape = trace["query_spec"]["params"]["target_shape_id"]
    target_fill_style = trace["query_spec"]["params"]["target_fill_style"]
    counted_entities = [
        entity
        for entity in entities
        if _predicate(
            query_id,
            is_shape=str(entity["shape_id"]) == str(target_shape),
            is_attribute=str(entity["fill_style"]) == str(target_fill_style),
        )
    ]

    assert trace["query_spec"]["params"]["target_attribute_axis"] == "fill_style"
    assert out.answer_gt.value == 3
    assert len(counted_entities) == 3
    assert "striped fill style" in out.prompt
    assert all("fill_style" in entity for entity in entities)
    assert set(trace["render_map"]["counted_instance_ids"]) == {str(entity["instance_id"]) for entity in counted_entities}
    assert sorted(out.annotation_gt.value) == sorted(entity["bbox_xyxy"] for entity in counted_entities)


def test_icons_counting_named_shape_color_boolean_sampling_distribution() -> None:
    query_counts: Counter[str] = Counter()
    answer_counts: Counter[int] = Counter()
    attribute_axes: Counter[str] = Counter()
    layouts: set[str] = set()
    for task_id, supported_queries in QUERY_IDS_BY_TASK_ID.items():
        task = create_task(str(task_id))
        task_query_counts: Counter[str] = Counter()
        for index in range(24):
            out = task.generate(
                hash64(20260523, f"named-shape-color-boolean-sampling.{task_id}", index),
                params={},
                max_attempts=200,
            )
            execution = out.trace_payload["execution_trace"]
            query_id = str(execution["query_id"])
            task_query_counts[query_id] += 1
            query_counts[query_id] += 1
            answer_counts[int(out.answer_gt.value)] += 1
            attribute_axes[str(execution["target_attribute_axis"])] += 1
            layouts.add(str(execution["arrangement_mode"]))
            assert query_id in set(supported_queries)
            assert 4 <= int(execution["object_count"]) <= 10
            assert 1 <= int(out.answer_gt.value) <= 5
            assert len(out.annotation_gt.value) == int(out.answer_gt.value)
        assert set(task_query_counts).issubset(set(supported_queries))

    assert set(query_counts) == set(QUERY_IDS)
    assert set(answer_counts).issubset(set(range(1, 6)))
    assert set(attribute_axes) == {"color", "fill_style"}
    assert layouts.issubset({"jittered_grid", "ordered_grid", "shelf_rows", "free_scatter", "clustered_by_shape"})
    assert layouts


def test_icons_counting_named_shape_color_boolean_rejects_stack_layouts() -> None:
    task = create_task("task_icons__named_field__multi_attribute_and_count")
    try:
        task.generate(
            hash64(20260523, "named-shape-color-boolean-stack-reject", 0),
            params={"arrangement_mode": "shape_stacks"},
            max_attempts=20,
        )
    except RuntimeError as exc:
        assert "non-stack layouts" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Boolean named-icon task accepted a stack layout")
