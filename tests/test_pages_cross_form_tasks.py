"""Behavior tests for pages cross-form reconciliation tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.pages.cross_form.reconciliation_value import (
    PagesCrossFormReconciliationValueTask,
)
from tests.helpers import extract_prompt_json_example


def _answer_from_trace(query_id: str, item_specs: list[dict[str, object]]) -> int:
    if str(query_id) == "total_amount_delta":
        return sum(
            abs(int(spec["order_qty"]) - int(spec["received_qty"])) * int(spec["unit_value"])
            for spec in item_specs
            if int(spec["order_qty"]) != int(spec["received_qty"])
        )
    if str(query_id) == "shortfall_minus_overage_value":
        return sum(
            (int(spec["order_qty"]) - int(spec["received_qty"])) * int(spec["unit_value"])
            for spec in item_specs
        )
    if str(query_id) == "sum_absolute_quantity_differences":
        return sum(abs(int(spec["order_qty"]) - int(spec["received_qty"])) for spec in item_specs)
    raise AssertionError(f"unknown variant {query_id}")


def test_pages_cross_form_reconciliation_value_contract_matches_trace() -> None:
    task = PagesCrossFormReconciliationValueTask()
    query_ids = (
        "total_amount_delta",
        "shortfall_minus_overage_value",
        "sum_absolute_quantity_differences",
    )

    for index, query_id in enumerate(query_ids):
        out = task.generate(
            70080 + index,
            params={"query_id": query_id, "scene_variant": "purchase_receipt_pair"},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        item_specs = [dict(spec) for spec in execution["item_specs"]]
        evidence_bbox_ids = [str(item) for item in execution["evidence_bbox_ids"]]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(out.query_id) == "default"
        assert str(out.query_id) == str(query_id)
        assert str(execution["query_id"]) == "default"
        assert str(execution["query_id"]) == str(query_id)
        assert str(execution["scene_variant"]) == "purchase_receipt_pair"
        assert str(execution["question_format"]) == "cross_form_reconciliation_value"
        assert str(execution["view_family"]) == "cross_form_reconciliation"
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert int(out.answer_gt.value) == int(execution["answer_value"])
        assert int(out.answer_gt.value) == _answer_from_trace(str(query_id), item_specs)
        assert 6 <= int(execution["item_count"]) <= 9
        assert len(item_specs) == int(execution["item_count"])
        assert set(execution["receiving_item_order_ids"]) == {str(spec["item_id"]) for spec in item_specs}
        assert [str(item) for item in execution["receiving_item_order_ids"]] != [
            str(spec["item_id"]) for spec in item_specs
        ]
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert [str(item) for item in execution["supporting_bbox_ids"]] == evidence_bbox_ids

        expected_bboxes = [
            [float(value) for value in render_map["cell_value_bboxes_px"][bbox_id]]
            for bbox_id in evidence_bbox_ids
        ]
        assert evidence_bboxes == expected_bboxes

        visible_numbers = {
            int(value)
            for spec in item_specs
            for value in (int(spec["order_qty"]), int(spec["received_qty"]), int(spec["unit_value"]))
        }
        assert int(out.answer_gt.value) not in visible_numbers

        if str(query_id) == "total_amount_delta":
            assert 3 <= len(execution["mismatch_item_ids"]) <= 5
            assert len(evidence_bbox_ids) == 5 * len(execution["mismatch_item_ids"])
        elif str(query_id) == "shortfall_minus_overage_value":
            assert len(execution["shortfall_item_ids"]) >= 1
            assert len(execution["overage_item_ids"]) >= 1
            assert 3 <= len(execution["mismatch_item_ids"]) <= 5
            assert len(evidence_bbox_ids) == 5 * len(execution["mismatch_item_ids"])
        elif str(query_id) == "sum_absolute_quantity_differences":
            assert 3 <= len(execution["mismatch_item_ids"]) <= 5
            assert len(evidence_bbox_ids) == 4 * len(execution["mismatch_item_ids"])


def test_pages_cross_form_reconciliation_prompt_examples_match_contract() -> None:
    task = PagesCrossFormReconciliationValueTask()
    expected_answers = {
        "total_amount_delta": 864,
        "shortfall_minus_overage_value": 324,
        "sum_absolute_quantity_differences": 42,
    }

    for index, (query_id, expected_answer) in enumerate(expected_answers.items(), start=70120):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])

        assert answer_and_evidence["answer"] == expected_answer
        assert answer_only["answer"] == expected_answer
        assert isinstance(answer_and_evidence["evidence"], list)
        assert all(len(bbox) == 4 for bbox in answer_and_evidence["evidence"])


def test_pages_cross_form_reconciliation_value_is_deterministic() -> None:
    task = PagesCrossFormReconciliationValueTask()
    params = {"query_id": "total_amount_delta", "scene_variant": "purchase_receipt_pair"}
    out_a = task.generate(70170, params=params, max_attempts=10)
    out_b = task.generate(70170, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_pages_cross_form_reconciliation_balanced_sampling_covers_variants() -> None:
    task = PagesCrossFormReconciliationValueTask()
    query_ids: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()

    for index in range(18):
        out = task.generate(
            hash64(70220, "pages_cross_form", index),
            params={},
            max_attempts=10,
        )
        execution = out.trace_payload["execution_trace"]
        query_ids[str(execution["query_id"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(query_ids.keys()) == {
        "total_amount_delta",
        "shortfall_minus_overage_value",
        "sum_absolute_quantity_differences",
    }
    assert set(scene_variants.keys()) == {"purchase_receipt_pair"}
    assert all(count >= 3 for count in query_ids.values())
