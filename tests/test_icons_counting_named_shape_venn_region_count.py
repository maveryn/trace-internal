"""Tests for named-shape Venn-region icon counting."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.icons.counting.named_shape_venn_region_count import QUERY_IDS, TARGET_ATTRIBUTE_MODES


TASK_ID = "task_icons__venn_field__scoped_attribute_count"


def _counted_categories(query_id: str) -> set[str]:
    if query_id == "inside_both_circles_count":
        return {"both"}
    if query_id == "inside_either_circle_count":
        return {"left_only", "right_only", "both"}
    if query_id == "inside_exactly_one_circle_count":
        return {"left_only", "right_only"}
    if query_id == "outside_both_circles_count":
        return {"neither"}
    raise AssertionError(f"unexpected query_id: {query_id}")


def _target_mode_params(mode: str) -> dict[str, object]:
    if mode == "shape_only":
        return {"target_attribute_mode": mode, "target_shape_id": "bell"}
    if mode == "color_shape":
        return {"target_attribute_mode": mode, "target_shape_id": "bell", "target_color_name": "red"}
    raise AssertionError(f"unexpected target mode: {mode}")


def _matches_target(entity: dict[str, object], trace_params: dict[str, object]) -> bool:
    if str(entity["shape_id"]) != str(trace_params["target_shape_id"]):
        return False
    mode = str(trace_params["target_attribute_mode"])
    if mode == "shape_only":
        return True
    if mode == "color_shape":
        return str(entity["color_name"]) == str(trace_params["target_color_name"])
    raise AssertionError(f"unexpected target mode: {mode}")


def test_icons_counting_named_shape_venn_contract_all_queries_and_target_modes() -> None:
    task = create_task(TASK_ID)
    for query_index, query_id in enumerate(QUERY_IDS):
        for mode_index, mode in enumerate(TARGET_ATTRIBUTE_MODES):
            out = task.generate(
                hash64(20260525, "named-shape-venn-contract", query_index, mode_index),
                params={
                    "named_venn_query_id": query_id,
                    "target_count": 2,
                    "object_count": 12,
                    **_target_mode_params(mode),
                },
                max_attempts=200,
            )
            trace = out.trace_payload
            params = trace["query_spec"]["params"]
            entities = list(trace["scene_ir"]["entities"])
            counted_categories = _counted_categories(query_id)
            counted_entities = [
                entity
                for entity in entities
                if _matches_target(entity, params) and str(entity["venn_category"]) in counted_categories
            ]

            assert out.scene_id == "venn_field"
            assert out.query_id == "single"
            assert trace["query_spec"]["params"]["internal_query_id"] == query_id
            assert out.answer_gt.type == "integer"
            assert out.answer_gt.value == 2
            assert out.annotation_gt.type == "bbox_set"
            assert len(out.annotation_gt.value) == 2
            assert len(counted_entities) == 2
            assert trace["scene_ir"]["scene_kind"] == "icons_named_shape_venn_region_field"
            assert trace["query_spec"]["template_id"] == "icons_counting_v0"
            assert set(trace["execution_trace"]["counted_venn_categories"]) == counted_categories
            assert set(trace["render_map"]["counted_instance_ids"]) == {
                str(entity["instance_id"]) for entity in counted_entities
            }
            assert sorted(out.annotation_gt.value) == sorted(entity["bbox_xyxy"] for entity in counted_entities)
            assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
            assert trace["projected_annotation"]["pixel_bbox_set"] == out.annotation_gt.value
            assert len(trace["projected_annotation"]["pixel_point_set"]) == 2
            assert '"bell"' in out.prompt
            if mode == "color_shape":
                assert "red [#E63232]" in out.prompt


def test_icons_counting_named_shape_venn_sampling_distribution() -> None:
    task = create_task(TASK_ID)
    query_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    answer_counts: Counter[int] = Counter()
    for index in range(120):
        out = task.generate(
            hash64(20260525, "named-shape-venn-sampling", index),
            params={},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        internal_query_id = str(execution["internal_query_id"])
        query_counts[internal_query_id] += 1
        mode_counts[str(execution["target_attribute_mode"])] += 1
        answer_counts[int(out.answer_gt.value)] += 1

        assert 8 <= int(execution["object_count"]) <= 16
        assert 1 <= int(out.answer_gt.value) <= 5
        assert len(out.annotation_gt.value) == int(out.answer_gt.value)
        assert set(execution["counted_venn_categories"]) == _counted_categories(internal_query_id)

    assert set(query_counts) == set(QUERY_IDS)
    assert set(mode_counts) == set(TARGET_ATTRIBUTE_MODES)
    assert set(answer_counts).issubset(set(range(1, 6)))
