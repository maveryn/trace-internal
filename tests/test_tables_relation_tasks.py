"""Behavior tests for table relation tasks."""

from __future__ import annotations

from trace.tasks.tables.relation.extremum_transfer_value import TablesRelationExtremumTransferValueTask
from trace.tasks.tables.relation.row_compare_label import TablesRelationRowCompareLabelTask
from tests.helpers import extract_prompt_json_example


def test_table_relation_row_compare_label_variants_match_contract() -> None:
    task = TablesRelationRowCompareLabelTask()
    cases = (
        ("higher_of_two_rows", "spreadsheet"),
        ("lower_of_two_rows", "zebra"),
        ("higher_of_two_rows", "ledger"),
        ("lower_of_two_rows", "card_table"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=18410):
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        query_column = str(execution["query_column"])
        query_rows = [dict(row) for row in execution["query_rows"]]
        values_by_row = {
            str(row_label): {
                str(header): int(value)
                for header, value in row_values.items()
            }
            for row_label, row_values in execution["values_by_row"].items()
        }
        compared_values = [
            int(values_by_row[str(row["row_label"])][str(query_column)])
            for row in query_rows
        ]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
        supporting_cell_ids = [str(cell_id) for cell_id in execution["supporting_cell_ids"]]

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "string"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 5 <= int(execution["row_count"]) <= 10
        assert 3 <= int(execution["numeric_column_count"]) <= 5
        assert len(query_rows) == 2
        assert len(evidence_bboxes) == 2
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert evidence_bboxes == [
            [float(value) for value in trace["render_map"]["cell_bboxes_px"][str(cell_id)]]
            for cell_id in supporting_cell_ids
        ]

        winning_answer = str(out.answer_gt.value)
        query_row_labels = [str(row["row_label"]) for row in query_rows]
        assert str(winning_answer) in set(query_row_labels)
        assert compared_values[0] != compared_values[1]
        if str(task_variant) == "higher_of_two_rows":
            expected_label = query_row_labels[0] if compared_values[0] > compared_values[1] else query_row_labels[1]
        else:
            expected_label = query_row_labels[0] if compared_values[0] < compared_values[1] else query_row_labels[1]
        assert str(winning_answer) == str(expected_label)


def test_table_relation_prompt_examples_match_selected_variant() -> None:
    task = TablesRelationRowCompareLabelTask()
    expected = {
        "higher_of_two_rows": {"evidence": [[260, 180, 372, 236], [260, 238, 372, 294]], "answer": "Ava"},
        "lower_of_two_rows": {"evidence": [[260, 180, 372, 236], [260, 238, 372, 294]], "answer": "Milo"},
    }
    for index, task_variant in enumerate(expected, start=18430):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_table_relation_row_compare_label_task_is_deterministic() -> None:
    task = TablesRelationRowCompareLabelTask()
    params = {"task_variant": "higher_of_two_rows", "scene_variant": "spreadsheet"}
    out_a = task.generate(18460, params=params, max_attempts=10)
    out_b = task.generate(18460, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_table_relation_extremum_transfer_value_variants_match_contract() -> None:
    task = TablesRelationExtremumTransferValueTask()
    cases = (
        ("argmax_transfer", "spreadsheet"),
        ("argmin_transfer", "zebra"),
        ("argmax_transfer", "ledger"),
        ("argmin_transfer", "card_table"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=18490):
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        row_labels = [str(label) for label in execution["row_labels"]]
        values_by_row = {
            str(row_label): {
                str(header): int(value)
                for header, value in row_values.items()
            }
            for row_label, row_values in execution["values_by_row"].items()
        }
        source_column = str(execution["source_column"])
        target_column = str(execution["target_column"])
        answer_row_label = str(execution["answer_row_label"])
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
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
        assert source_column != target_column
        assert len(evidence_bboxes) == 2 == len(expected_cell_ids)
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes

        source_values = {str(row_label): int(row_values[source_column]) for row_label, row_values in values_by_row.items()}
        assert len(set(source_values.values())) == len(source_values)
        if str(task_variant) == "argmax_transfer":
            assert int(source_values[answer_row_label]) == max(source_values.values())
        else:
            assert int(source_values[answer_row_label]) == min(source_values.values())
        assert int(out.answer_gt.value) == int(values_by_row[answer_row_label][target_column])

        expected_bboxes = [
            [float(value) for value in trace["render_map"]["cell_bboxes_px"][str(cell_id)]]
            for cell_id in expected_cell_ids
        ]
        assert evidence_bboxes == expected_bboxes


def test_table_relation_extremum_transfer_prompt_examples_match_selected_variant() -> None:
    task = TablesRelationExtremumTransferValueTask()
    expected = {
        "argmax_transfer": {"evidence": [[260, 180, 372, 236], [374, 180, 486, 236]], "answer": 19},
        "argmin_transfer": {"evidence": [[260, 180, 372, 236], [374, 180, 486, 236]], "answer": 7},
    }
    for index, task_variant in enumerate(expected, start=18520):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_table_relation_extremum_transfer_value_task_is_deterministic() -> None:
    task = TablesRelationExtremumTransferValueTask()
    params = {"task_variant": "argmax_transfer", "scene_variant": "spreadsheet"}
    out_a = task.generate(18550, params=params, max_attempts=10)
    out_b = task.generate(18550, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
