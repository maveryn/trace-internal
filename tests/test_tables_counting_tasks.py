"""Behavior tests for table counting tasks."""

from __future__ import annotations

from trace.tasks.tables.counting.value_count import TablesCountingValueCountTask
from tests.helpers import extract_prompt_json_example


def test_table_counting_value_count_variants_match_contract() -> None:
    task = TablesCountingValueCountTask()
    cases = (
        ("above_threshold", "spreadsheet"),
        ("below_threshold", "zebra"),
        ("in_interval", "ledger"),
        ("above_threshold", "card_table"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=18210):
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        row_labels = [str(label) for label in execution["row_labels"]]
        column_headers = [str(header) for header in execution["column_headers"]]
        query_column = str(execution["query_column"])
        values_by_row = {
            str(row_label): {
                str(header): int(value)
                for header, value in row_values.items()
            }
            for row_label, row_values in execution["values_by_row"].items()
        }
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
        matching_row_indices = [int(value) for value in execution["matching_row_indices"]]
        expected_cell_ids = [str(cell_id) for cell_id in execution["supporting_cell_ids"]]

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 5 <= int(execution["row_count"]) <= 10
        assert 3 <= int(execution["numeric_column_count"]) <= 5
        assert len(row_labels) == int(execution["row_count"])
        assert len(column_headers) == int(execution["numeric_column_count"])
        assert str(query_column) in set(column_headers)
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert len(evidence_bboxes) == int(out.answer_gt.value) == len(expected_cell_ids)

        query_values = [int(values_by_row[str(row_label)][str(query_column)]) for row_label in row_labels]
        if str(task_variant) == "above_threshold":
            threshold_value = int(execution["threshold_value"])
            expected_row_indices = [
                int(index) for index, value in enumerate(query_values) if int(value) > int(threshold_value)
            ]
        elif str(task_variant) == "below_threshold":
            threshold_value = int(execution["threshold_value"])
            expected_row_indices = [
                int(index) for index, value in enumerate(query_values) if int(value) < int(threshold_value)
            ]
        else:
            interval_min = int(execution["interval_min"])
            interval_max = int(execution["interval_max"])
            expected_row_indices = [
                int(index)
                for index, value in enumerate(query_values)
                if int(interval_min) <= int(value) <= int(interval_max)
            ]
        assert matching_row_indices == expected_row_indices
        assert [str(row_labels[int(index)]) for index in matching_row_indices] == [str(label) for label in execution["matching_row_labels"]]

        expected_bboxes = [
            [float(value) for value in trace["render_map"]["cell_bboxes_px"][str(cell_id)]]
            for cell_id in expected_cell_ids
        ]
        assert evidence_bboxes == expected_bboxes


def test_table_counting_prompt_examples_match_selected_variant() -> None:
    task = TablesCountingValueCountTask()
    expected = {
        "above_threshold": {"evidence": [[260, 180, 372, 236], [260, 236, 372, 292]], "answer": 2},
        "below_threshold": {"evidence": [[260, 180, 372, 236]], "answer": 1},
        "in_interval": {"evidence": [[260, 180, 372, 236], [260, 236, 372, 292], [260, 292, 372, 348]], "answer": 3},
    }
    for index, task_variant in enumerate(expected, start=18230):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_table_counting_value_count_task_is_deterministic() -> None:
    task = TablesCountingValueCountTask()
    params = {"task_variant": "in_interval", "scene_variant": "spreadsheet"}
    out_a = task.generate(18260, params=params, max_attempts=10)
    out_b = task.generate(18260, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_table_counting_pairwise_variants_match_contract() -> None:
    task = TablesCountingValueCountTask()
    cases = (
        ("col_a_gt_col_b", "spreadsheet"),
        ("col_a_lt_col_b", "zebra"),
        ("col_a_gt_col_b", "ledger"),
        ("col_a_lt_col_b", "card_table"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=18290):
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        row_labels = [str(label) for label in execution["row_labels"]]
        query_column_a = str(execution["query_column_a"])
        query_column_b = str(execution["query_column_b"])
        values_by_row = {
            str(row_label): {
                str(header): int(value)
                for header, value in row_values.items()
            }
            for row_label, row_values in execution["values_by_row"].items()
        }
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
        matching_row_indices = [int(value) for value in execution["matching_row_indices"]]
        expected_cell_ids = [str(cell_id) for cell_id in execution["supporting_cell_ids"]]

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 5 <= int(execution["row_count"]) <= 10
        assert 3 <= int(execution["numeric_column_count"]) <= 5
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert len(evidence_bboxes) == (2 * int(out.answer_gt.value)) == len(expected_cell_ids)
        assert query_column_a != query_column_b

        expected_row_indices = []
        for index, row_label in enumerate(row_labels):
            row_values = values_by_row[str(row_label)]
            a_value = int(row_values[query_column_a])
            b_value = int(row_values[query_column_b])
            if str(task_variant) == "col_a_gt_col_b":
                if int(a_value) > int(b_value):
                    expected_row_indices.append(int(index))
            else:
                if int(a_value) < int(b_value):
                    expected_row_indices.append(int(index))
        assert matching_row_indices == expected_row_indices
        assert [str(row_labels[int(index)]) for index in matching_row_indices] == [str(label) for label in execution["matching_row_labels"]]

        expected_bboxes = [
            [float(value) for value in trace["render_map"]["cell_bboxes_px"][str(cell_id)]]
            for cell_id in expected_cell_ids
        ]
        assert evidence_bboxes == expected_bboxes


def test_table_counting_pairwise_prompt_examples_match_selected_variant() -> None:
    task = TablesCountingValueCountTask()
    expected = {
        "col_a_gt_col_b": {
            "evidence": [[260, 180, 372, 236], [374, 180, 486, 236], [260, 236, 372, 292], [374, 236, 486, 292]],
            "answer": 2,
        },
        "col_a_lt_col_b": {
            "evidence": [[260, 180, 372, 236], [374, 180, 486, 236]],
            "answer": 1,
        },
    }
    for index, task_variant in enumerate(expected, start=18320):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_table_counting_pairwise_task_is_deterministic() -> None:
    task = TablesCountingValueCountTask()
    params = {"task_variant": "col_a_gt_col_b", "scene_variant": "spreadsheet"}
    out_a = task.generate(18350, params=params, max_attempts=10)
    out_b = task.generate(18350, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
