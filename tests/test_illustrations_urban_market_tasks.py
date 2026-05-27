"""Contract tests for illustration urban-market tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks import create_task
from trace.tasks.illustrations.counting._market_shop_category_branch import _sample_spec as _sample_shop_category_spec
from trace.tasks.illustrations.counting._market_shop_color_branch import _sample_spec as _sample_shop_color_spec
from trace.tasks.illustrations.counting._market_shop_selling_branch import _sample_spec as _sample_shop_selling_spec
from trace.tasks.illustrations.counting.customer_at_shop_type_count import _sample_spec as _sample_customer_at_shop_spec


def _assert_hash_balanced_counts(counts: Counter, expected_keys) -> None:
    assert sorted(counts) == sorted(expected_keys)
    expected = sum(counts.values()) / max(1, len(counts))
    assert min(counts.values()) >= max(1, int(expected * 0.4))
    assert max(counts.values()) <= int(expected * 1.7) + 1


def test_shop_selling_object_count_contract() -> None:
    out = create_task("task_illustrations__market__shop_attribute_count").generate(
        hash64(2026052401, "shop-selling-count", 0),
        params={"query_id": "shop_selling_object_count", "target_item_type": "apple", "target_count": 3, "shop_count": 7},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_shop_ids = execution["counted_shop_ids"]
    shop_bboxes = trace["render_map"]["shop_bboxes_px"]
    shop_inventory = trace["render_map"]["shop_inventory"]

    assert out.scene_id == "market"
    assert out.query_id == "shop_selling_object_count"
    assert out.query_id == "default"
    assert trace["query_spec"]["task_id"] == "task_illustrations__market__shop_attribute_count"
    assert trace["query_spec"]["branch_id"] == "market_shop_selling"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 3
    assert len(counted_shop_ids) == 3
    assert execution["target_item_type"] == "apple"
    assert sorted(out.evidence_gt.value) == sorted(shop_bboxes[shop_id] for shop_id in counted_shop_ids)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    for shop_id, item_types in shop_inventory.items():
        if shop_id in set(counted_shop_ids):
            assert "apple" in set(item_types)
        else:
            assert "apple" not in set(item_types)


def test_shop_selling_object_countseeded_sampler_balances_answer_counts() -> None:
    answers = [
        _sample_shop_selling_spec(
            instance_seed=hash64(2026052401, "shop-selling-sampling", index),
            params={},
            attempt_index=0,
        ).target_count
        for index in range(100)
    ]
    counts = Counter(answers)
    _assert_hash_balanced_counts(counts, [1, 2, 3, 4, 5])


def test_shop_category_count_contract() -> None:
    out = create_task("task_illustrations__market__shop_attribute_count").generate(
        hash64(2026052402, "shop-category-count", 0),
        params={"query_id": "shop_category_count", "shop_type": "books", "target_count": 4, "shop_count": 14},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_shop_ids = execution["counted_shop_ids"]
    shop_bboxes = trace["render_map"]["shop_bboxes_px"]
    layout = trace["render_spec"]["style"]["layout"]["shop_layout"]

    assert out.scene_id == "market"
    assert out.query_id == "shop_category_count"
    assert out.query_id == "default"
    assert trace["query_spec"]["task_id"] == "task_illustrations__market__shop_attribute_count"
    assert trace["query_spec"]["branch_id"] == "market_shop_category"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 4
    assert len(counted_shop_ids) == 4
    assert execution["target_shop_type"] == "books"
    assert execution["target_shop_label"] == "BOOKS"
    assert layout["layout_mode"] == "sign_dense"
    assert layout["lane_axis"] in {"rows", "columns"}
    assert layout["lane_count"] in {2, 3}
    assert trace["render_spec"]["canvas_size"] == [1280, 960]
    assert sorted(out.evidence_gt.value) == sorted(shop_bboxes[shop_id] for shop_id in counted_shop_ids)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    for shop in execution["shops"]:
        if shop["shop_id"] in set(counted_shop_ids):
            assert shop["shop_type"] == "books"
        else:
            assert shop["shop_type"] != "books"


def test_shop_category_countseeded_sampler_balances_answer_counts() -> None:
    answers = [
        _sample_shop_category_spec(
            instance_seed=hash64(2026052402, "shop-category-sampling", index),
            params={},
            attempt_index=0,
        ).target_count
        for index in range(100)
    ]
    counts = Counter(answers)
    _assert_hash_balanced_counts(counts, [1, 2, 3, 4, 5])


def test_customer_at_shop_type_count_contract() -> None:
    out = create_task("task_illustrations__market__customer_at_shop_count").generate(
        hash64(2026052404, "customer-shop-count", 0),
        params={"shop_type": "coffee", "target_count": 3, "customer_count": 8, "shop_count": 9},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_customer_ids = execution["counted_customer_ids"]
    customer_bboxes = trace["render_map"]["customer_bboxes_px"]
    layout = trace["render_spec"]["style"]["layout"]["shop_layout"]

    assert out.scene_id == "market"
    assert out.query_id == "customer_at_shop_type_count"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 3
    assert len(counted_customer_ids) == 3
    assert execution["target_shop_type"] == "coffee"
    assert execution["target_shop_label"] == "COFFEE"
    assert layout["layout_mode"] == "customer_plaza"
    assert layout["path_style"] == "dirt_market_path"
    assert sorted(out.evidence_gt.value) == sorted(customer_bboxes[customer_id] for customer_id in counted_customer_ids)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    for customer in execution["customers"]:
        attrs = customer["attributes"]
        is_target = attrs["near_shop_type"] == "coffee"
        assert (customer["decor_id"] in set(counted_customer_ids)) == is_target
        assert customer["decor_type"] == "customer"


def test_customer_at_shop_type_countseeded_sampler_balances_answer_counts() -> None:
    answers = [
        _sample_customer_at_shop_spec(
            instance_seed=hash64(2026052404, "customer-shop-sampling", index),
            params={},
            attempt_index=0,
        ).target_count
        for index in range(100)
    ]
    counts = Counter(answers)
    _assert_hash_balanced_counts(counts, [1, 2, 3, 4, 5])


def test_shop_color_attribute_count_contract() -> None:
    out = create_task("task_illustrations__market__shop_attribute_count").generate(
        hash64(2026052403, "shop-color-count", 0),
        params={"query_id": "awning_color_count", "color_name": "red", "target_count": 3, "shop_count": 14},
        max_attempts=100,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    counted_shop_ids = execution["counted_shop_ids"]
    awning_bboxes = trace["render_map"]["shop_awning_bboxes_px"]
    assignments = trace["render_map"]["color_assignments"]

    assert out.scene_id == "market"
    assert out.query_id == "awning_color_count"
    assert out.query_id == "default"
    assert trace["query_spec"]["task_id"] == "task_illustrations__market__shop_attribute_count"
    assert trace["query_spec"]["branch_id"] == "market_shop_color"
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert int(out.answer_gt.value) == 3
    assert len(counted_shop_ids) == 3
    assert execution["target_surface"] == "awning"
    assert execution["target_color_name"] == "red"
    assert execution["target_color_label"] == "red [#E63232]"
    assert sorted(out.evidence_gt.value) == sorted(awning_bboxes[shop_id] for shop_id in counted_shop_ids)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    for shop_id, colors in assignments.items():
        if shop_id in set(counted_shop_ids):
            assert colors["awning_color_name"] == "red"
        else:
            assert colors["awning_color_name"] != "red"


def test_shop_color_attribute_countseeded_sampler_balances_answer_counts() -> None:
    samples = [
        _sample_shop_color_spec(
            instance_seed=hash64(2026052403, "shop-color-sampling", index),
            params={},
            attempt_index=0,
        )
        for index in range(100)
    ]
    counts = Counter(sample.target_count for sample in samples)
    _assert_hash_balanced_counts(counts, [1, 2, 3, 4, 5])
    assert {sample.query_id for sample in samples} == {"signboard_color_count", "awning_color_count", "facade_color_count"}
    assert {sample.color_name for sample in samples} >= {"red", "blue", "green", "orange", "purple", "cyan"}
