"""Behavior tests for table statistics tasks."""

from __future__ import annotations

from trace.core.type_registry import load_type_registry
from trace.tasks.tables.statistics.summary_label import TablesStatisticsSummaryLabelTask
from trace.tasks.tables.statistics.row_summary_value import TablesStatisticsRowSummaryValueTask
from trace.tasks.tables.statistics.summary_value import TablesStatisticsSummaryValueTask
from tests.helpers import extract_prompt_json_example


def test_table_statistics_summary_label_variants_match_contract() -> None:
    task = TablesStatisticsSummaryLabelTask()
    cases = (
        ("argmax", "spreadsheet"),
        ("argmin", "zebra"),
        ("argmax", "ledger"),
        ("argmin", "card_table"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=18010):
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
        answer = str(out.answer_gt.value)
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
        winning_value = int(values_by_row[str(answer)][str(query_column)])

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "string"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 5 <= int(execution["row_count"]) <= 10
        assert 3 <= int(execution["numeric_column_count"]) <= 5
        assert len(row_labels) == int(execution["row_count"])
        assert len(column_headers) == int(execution["numeric_column_count"])
        assert all(str(label).isalpha() for label in row_labels)
        assert all(str(label).istitle() for label in row_labels)
        assert all(2 <= len(str(label)) <= 4 for label in row_labels)
        assert len(evidence_bboxes) == 1
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert str(answer) in set(row_labels)
        assert str(query_column) in set(column_headers)

        query_values = {str(label): int(row_values[str(query_column)]) for label, row_values in values_by_row.items()}
        if str(task_variant) == "argmax":
            assert int(winning_value) == max(query_values.values())
        else:
            assert int(winning_value) == min(query_values.values())

        evidence_cell_id = str(execution["supporting_cell_id"])
        assert evidence_bboxes[0] == [float(value) for value in trace["render_map"]["cell_bboxes_px"][evidence_cell_id]]
        evidence_entity = next(entity for entity in trace["scene_ir"]["entities"] if str(entity["entity_id"]) == evidence_cell_id)
        assert str(evidence_entity["attrs"]["row_label"]) == str(answer)
        assert str(evidence_entity["attrs"]["column_header"]) == str(query_column)
        assert int(evidence_entity["attrs"]["value"]) == int(winning_value)


def test_table_statistics_summary_label_prompts_match_scene_variant_wording() -> None:
    task = TablesStatisticsSummaryLabelTask()
    prompts = {}
    for seed, scene_variant in enumerate(("spreadsheet", "zebra", "ledger", "card_table"), start=18030):
        out = task.generate(seed, params={"scene_variant": scene_variant}, max_attempts=10)
        prompts[str(scene_variant)] = str(out.prompt)
    assert "spreadsheet-style table" in prompts["spreadsheet"]
    assert "zebra-striped table" in prompts["zebra"]
    assert "ledger-style table" in prompts["ledger"]
    assert "card-style table" in prompts["card_table"]


def test_table_statistics_summary_label_prompt_examples_match_selected_variant() -> None:
    task = TablesStatisticsSummaryLabelTask()
    expected = {
        "argmax": {"evidence": [[260, 180, 372, 236]], "answer": "Ava"},
        "argmin": {"evidence": [[260, 180, 372, 236]], "answer": "Milo"},
    }
    for index, task_variant in enumerate(expected, start=18040):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_table_statistics_summary_label_task_is_deterministic() -> None:
    task = TablesStatisticsSummaryLabelTask()
    params = {"task_variant": "argmax", "scene_variant": "spreadsheet"}
    out_a = task.generate(18060, params=params, max_attempts=10)
    out_b = task.generate(18060, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_table_statistics_registers_string_answer_and_bbox_evidence() -> None:
    registry = load_type_registry()
    assert registry.validate_answer_type("string") is True
    assert registry.validate_evidence_type("bbox_set") is True


def test_table_statistics_summary_value_variants_match_contract() -> None:
    task = TablesStatisticsSummaryValueTask()
    cases = (
        ("column_sum", "spreadsheet"),
        ("column_mean", "zebra"),
        ("column_median", "ledger"),
        ("column_sum", "card_table"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=18110):
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
        query_values = [int(values_by_row[str(row_label)][str(query_column)]) for row_label in row_labels]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

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
        assert len(evidence_bboxes) == 1
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert str(query_column) in set(column_headers)
        assert evidence_bboxes[0] == [
            float(value) for value in trace["render_map"]["column_region_bboxes_px"][query_column]
        ]

        if str(task_variant) == "column_sum":
            assert int(out.answer_gt.value) == sum(query_values)
        elif str(task_variant) == "column_mean":
            assert int(out.answer_gt.value) == (sum(query_values) // len(query_values))
            assert sum(query_values) % len(query_values) == 0
        else:
            assert len(query_values) % 2 == 1
            sorted_values = sorted(query_values)
            assert int(out.answer_gt.value) == int(sorted_values[len(sorted_values) // 2])


def test_table_statistics_summary_value_prompt_examples_match_selected_variant() -> None:
    task = TablesStatisticsSummaryValueTask()
    expected = {
        "column_sum": {"evidence": [[260, 180, 372, 520]], "answer": 84},
        "column_mean": {"evidence": [[260, 180, 372, 520]], "answer": 14},
        "column_median": {"evidence": [[260, 180, 372, 520]], "answer": 13},
    }
    for index, task_variant in enumerate(expected, start=18130):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_table_statistics_summary_value_task_is_deterministic() -> None:
    task = TablesStatisticsSummaryValueTask()
    params = {"task_variant": "column_mean", "scene_variant": "spreadsheet"}
    out_a = task.generate(18160, params=params, max_attempts=10)
    out_b = task.generate(18160, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_table_statistics_registers_integer_and_bbox_evidence_for_summary_value() -> None:
    registry = load_type_registry()
    assert registry.validate_answer_type("integer") is True
    assert registry.validate_evidence_type("bbox_set") is True


def test_table_statistics_row_summary_value_variants_match_contract() -> None:
    task = TablesStatisticsRowSummaryValueTask()
    cases = (
        ("row_sum", "spreadsheet"),
        ("row_mean", "zebra"),
        ("row_sum", "ledger"),
        ("row_mean", "card_table"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=18190):
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        row_labels = [str(label) for label in execution["row_labels"]]
        column_headers = [str(header) for header in execution["column_headers"]]
        query_row_label = str(execution["query_row_label"])
        values_by_row = {
            str(row_label): {
                str(header): int(value)
                for header, value in row_values.items()
            }
            for row_label, row_values in execution["values_by_row"].items()
        }
        query_values = [int(values_by_row[str(query_row_label)][str(header)]) for header in column_headers]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

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
        assert len(evidence_bboxes) == 1
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert str(query_row_label) in set(row_labels)
        assert evidence_bboxes[0] == [
            float(value) for value in trace["render_map"]["row_region_bboxes_px"][query_row_label]
        ]

        if str(task_variant) == "row_sum":
            assert int(out.answer_gt.value) == sum(query_values)
        else:
            assert int(out.answer_gt.value) == (sum(query_values) // len(query_values))
            assert sum(query_values) % len(query_values) == 0


def test_table_statistics_row_summary_value_prompt_examples_match_selected_variant() -> None:
    task = TablesStatisticsRowSummaryValueTask()
    expected = {
        "row_sum": {"evidence": [[150, 180, 780, 236]], "answer": 62},
        "row_mean": {"evidence": [[150, 180, 780, 236]], "answer": 15},
    }
    for index, task_variant in enumerate(expected, start=18220):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_table_statistics_row_summary_value_task_is_deterministic() -> None:
    task = TablesStatisticsRowSummaryValueTask()
    params = {"task_variant": "row_mean", "scene_variant": "spreadsheet"}
    out_a = task.generate(18260, params=params, max_attempts=10)
    out_b = task.generate(18260, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
