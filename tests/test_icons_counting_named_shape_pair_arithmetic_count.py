"""Tests for named-shape icon pair-arithmetic counting."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.icons.named_field.count_arithmetic import DIFFERENCE_QUERY_IDS, TOTAL_QUERY_IDS


TASK_ID = "task_icons__named_field__count_arithmetic"


def _matches(entity: dict[str, object], operand: dict[str, object], *, uses_color_binding: bool) -> bool:
    if str(entity["shape_id"]) != str(operand["shape_id"]):
        return False
    if uses_color_binding:
        return str(entity["color_name"]) == str(operand["color_name"])
    return True


def _bbox_sort_key(entity: dict[str, object]) -> tuple[int, int, int, int]:
    box = [int(value) for value in entity["bbox_xyxy"]]  # type: ignore[index]
    return (box[1], box[0], box[3], box[2])


def _expected_counted_annotation(
    left_entities: list[dict[str, object]],
    right_entities: list[dict[str, object]],
) -> list[list[int]]:
    return [
        list(entity["bbox_xyxy"])  # type: ignore[arg-type]
        for entity in sorted(left_entities + right_entities, key=_bbox_sort_key)
    ]


def test_icons_counting_named_shape_pair_arithmetic_contract_all_queries() -> None:
    query_cases = [
        *((TASK_ID, query_id) for query_id in TOTAL_QUERY_IDS),
        *((TASK_ID, query_id) for query_id in DIFFERENCE_QUERY_IDS),
    ]
    for index, (task_id, query_id) in enumerate(query_cases):
        task = create_task(task_id)
        is_difference = str(query_id).endswith("_difference_count")
        target_answer = 1 if is_difference else 5
        out = task.generate(
            hash64(20260524, "named-shape-pair-arithmetic-contract", index),
            params={
                "query_id": query_id,
                "left_shape_id": "star",
                "right_shape_id": "circle",
                "left_color_name": "red",
                "right_color_name": "blue",
                "left_count": 2,
                "right_count": 3,
                "target_answer": target_answer,
                "distractor_count": 4,
                "arrangement_mode": "ordered_grid",
            },
            max_attempts=200,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        entities = trace["scene_ir"]["entities"]
        left_operand = execution["left_operand"]
        right_operand = execution["right_operand"]
        uses_color_binding = bool(execution["uses_color_binding"])
        left_entities = [entity for entity in entities if _matches(entity, left_operand, uses_color_binding=uses_color_binding)]
        right_entities = [entity for entity in entities if _matches(entity, right_operand, uses_color_binding=uses_color_binding)]
        answer = len(left_entities) + len(right_entities)
        if is_difference:
            answer = abs(len(left_entities) - len(right_entities))

        assert out.scene_id == "named_field"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.answer_gt.value == target_answer
        assert out.answer_gt.value == answer
        assert out.annotation_gt.type == "bbox_set"
        assert len(left_entities) == 2
        assert len(right_entities) == 3
        assert len(out.annotation_gt.value) == 5
        assert set(trace["render_map"]["left_operand_instance_ids"]) == {str(entity["instance_id"]) for entity in left_entities}
        assert set(trace["render_map"]["right_operand_instance_ids"]) == {str(entity["instance_id"]) for entity in right_entities}
        assert set(trace["render_map"]["counted_instance_ids"]) == {
            str(entity["instance_id"]) for entity in left_entities + right_entities
        }
        expected_annotation = _expected_counted_annotation(left_entities, right_entities)
        assert out.annotation_gt.value == expected_annotation
        assert trace["projected_annotation"]["type"] == "bbox_set"
        assert trace["projected_annotation"]["bbox_set"] == expected_annotation
        assert trace["projected_annotation"]["pixel_bbox_set"] == expected_annotation
        assert str(left_operand["shape_name"]) in out.prompt
        assert str(right_operand["shape_name"]) in out.prompt
        if uses_color_binding:
            assert str(left_operand["color_label"]) in out.prompt
            assert str(right_operand["color_label"]) in out.prompt


def test_icons_counting_named_shape_pair_arithmetic_supports_zero_difference() -> None:
    task = create_task(TASK_ID)
    out = task.generate(
        hash64(20260524, "named-shape-pair-arithmetic-zero-diff", 0),
        params={
            "query_id": "two_bound_color_difference_count",
            "left_shape_id": "star",
            "right_shape_id": "circle",
            "left_color_name": "red",
            "right_color_name": "blue",
            "left_count": 3,
            "right_count": 3,
            "target_answer": 0,
            "distractor_count": 4,
            "arrangement_mode": "ordered_grid",
        },
        max_attempts=200,
    )
    trace = out.trace_payload
    assert out.answer_gt.value == 0
    assert trace["execution_trace"]["left_count"] == 3
    assert trace["execution_trace"]["right_count"] == 3
    assert len(out.annotation_gt.value) == 6
    assert out.annotation_gt.type == "bbox_set"


def test_icons_counting_named_shape_pair_arithmetic_sampling_distribution() -> None:
    query_counts: Counter[str] = Counter()
    answer_counts: Counter[int] = Counter()
    layouts: set[str] = set()
    for index in range(120):
        task = create_task(TASK_ID)
        out = task.generate(
            hash64(20260524, "named-shape-pair-arithmetic-sampling", index),
            params={},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        query_counts[str(execution["query_id"])] += 1
        answer_counts[int(out.answer_gt.value)] += 1
        layouts.add(str(execution["arrangement_mode"]))
        expected = int(execution["left_count"]) + int(execution["right_count"])
        if str(execution["operation"]) == "absolute_difference":
            expected = abs(int(execution["left_count"]) - int(execution["right_count"]))
        assert out.answer_gt.value == expected
        assert 6 <= int(execution["object_count"]) <= 20
        assert len(out.annotation_gt.value) == int(execution["left_count"]) + int(execution["right_count"])
        assert out.annotation_gt.type == "bbox_set"

    assert set(query_counts) == set(TOTAL_QUERY_IDS + DIFFERENCE_QUERY_IDS)
    assert set(answer_counts).issubset(set(range(0, 11)))
    assert layouts.issubset({"jittered_grid", "ordered_grid", "shelf_rows", "free_scatter"})
    assert layouts
