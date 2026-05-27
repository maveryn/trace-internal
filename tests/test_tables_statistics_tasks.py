"""Behavior tests for table statistics tasks."""

from __future__ import annotations

from trace.core.type_registry import load_type_registry
from trace.tasks.charts.table.statistics.filtered_subset_value import TablesStatisticsFilteredSubsetValueTask
from trace.tasks.charts.table.statistics.column_summary_value import TablesStatisticsColumnSummaryValueTask
from tests.helpers import extract_prompt_json_example


def test_table_statistics_column_summary_value_variants_match_contract() -> None:
    task = TablesStatisticsColumnSummaryValueTask()
    cases = (
        ("column_sum", "spreadsheet"),
        ("column_mean", "zebra"),
        ("column_median", "ledger"),
    )
    for seed, (query_id, scene_variant) in enumerate(cases, start=18110):
        out = task.generate(seed, params={"query_id": query_id, "scene_variant": scene_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        row_labels = [str(label) for label in execution["row_labels"]]
        column_headers = [str(header) for header in execution["column_headers"]]
        values_by_row = {
            str(row_label): {
                str(header): int(value)
                for header, value in row_values.items()
            }
            for row_label, row_values in execution["values_by_row"].items()
        }
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

        assert str(out.query_id) == str(query_id)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 10 <= int(execution["row_count"]) <= 20
        assert 3 <= int(execution["numeric_column_count"]) <= 5
        assert len(row_labels) == int(execution["row_count"])
        assert len(column_headers) == int(execution["numeric_column_count"])
        assert len(evidence_bboxes) == 1
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes

        query_column = str(execution["query_column"])
        query_values = [int(values_by_row[str(row_label)][str(query_column)]) for row_label in row_labels]
        assert str(query_column) in set(column_headers)
        assert evidence_bboxes[0] == [
            float(value) for value in trace["render_map"]["column_region_bboxes_px"][query_column]
        ]

        if str(query_id) == "column_sum":
            assert int(out.answer_gt.value) == sum(query_values)
        elif str(query_id) == "column_mean":
            assert int(out.answer_gt.value) == (sum(query_values) // len(query_values))
            assert sum(query_values) % len(query_values) == 0
        else:
            assert len(query_values) % 2 == 1
            sorted_values = sorted(query_values)
            assert int(out.answer_gt.value) == int(sorted_values[len(sorted_values) // 2])


def test_table_statistics_column_summary_value_prompt_examples_match_selected_variant() -> None:
    task = TablesStatisticsColumnSummaryValueTask()
    expected = {
        "column_sum": {"evidence": [[260, 180, 372, 520]], "answer": 84},
        "column_mean": {"evidence": [[260, 180, 372, 520]], "answer": 14},
        "column_median": {"evidence": [[260, 180, 372, 520]], "answer": 13},
    }
    for index, query_id in enumerate(expected, start=18130):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[query_id]
        assert answer_only == {"answer": expected[query_id]["answer"]}


def test_table_statistics_column_summary_value_task_is_deterministic() -> None:
    task = TablesStatisticsColumnSummaryValueTask()
    params = {"query_id": "column_mean", "scene_variant": "spreadsheet"}
    out_a = task.generate(18160, params=params, max_attempts=10)
    out_b = task.generate(18160, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()

def test_table_statistics_registers_integer_and_bbox_evidence_for_column_summary_value() -> None:
    registry = load_type_registry()
    assert registry.validate_answer_type("integer") is True
    assert registry.validate_evidence_type("bbox_set") is True


def test_table_statistics_filtered_subset_value_variants_match_contract() -> None:
    task = TablesStatisticsFilteredSubsetValueTask()
    cases = (
        ("filtered_column_sum", "spreadsheet"),
        ("filtered_column_mean", "zebra"),
        ("filtered_column_sum", "ledger"),
        ("filtered_column_mean", "card_table"),
    )
    for seed, (query_id, scene_variant) in enumerate(cases, start=18190):
        out = task.generate(seed, params={"query_id": query_id, "scene_variant": scene_variant}, max_attempts=10)
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
        filter_column = str(execution["filter_column"])
        target_column = str(execution["target_column"])
        selected_row_indices = [int(value) for value in execution["selected_row_indices"]]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
        expected_cell_ids = [str(cell_id) for cell_id in execution["supporting_cell_ids"]]

        assert str(out.query_id) == str(query_id)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 10 <= int(execution["row_count"]) <= 20
        assert 3 <= int(execution["numeric_column_count"]) <= 5
        assert filter_column != target_column
        assert list(execution["selected_row_count_range"]) == [6, 7]
        assert 6 <= len(selected_row_indices) <= int(execution["row_count"]) - 1
        assert len(evidence_bboxes) == (2 * len(selected_row_indices)) == len(expected_cell_ids)
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes

        filter_values = [int(values_by_row[str(row_label)][filter_column]) for row_label in row_labels]
        if str(execution["filter_variant"]) == "above_threshold":
            threshold_value = int(execution["threshold_value"])
            expected_row_indices = [
                int(index) for index, value in enumerate(filter_values) if int(value) > int(threshold_value)
            ]
        elif str(execution["filter_variant"]) == "below_threshold":
            threshold_value = int(execution["threshold_value"])
            expected_row_indices = [
                int(index) for index, value in enumerate(filter_values) if int(value) < int(threshold_value)
            ]
        else:
            interval_min = int(execution["interval_min"])
            interval_max = int(execution["interval_max"])
            expected_row_indices = [
                int(index)
                for index, value in enumerate(filter_values)
                if int(interval_min) <= int(value) <= int(interval_max)
            ]
        assert selected_row_indices == expected_row_indices
        assert [str(row_labels[int(index)]) for index in selected_row_indices] == [
            str(label) for label in execution["selected_row_labels"]
        ]

        target_values = [int(values_by_row[str(row_labels[int(index)])][target_column]) for index in selected_row_indices]
        if str(query_id) == "filtered_column_sum":
            assert int(out.answer_gt.value) == sum(target_values)
        else:
            assert int(out.answer_gt.value) == (sum(target_values) // len(target_values))
            assert sum(target_values) % len(target_values) == 0

        expected_bboxes = [
            [float(value) for value in trace["render_map"]["cell_bboxes_px"][str(cell_id)]]
            for cell_id in expected_cell_ids
        ]
        assert evidence_bboxes == expected_bboxes


def test_table_statistics_filtered_subset_value_prompt_examples_match_selected_variant() -> None:
    task = TablesStatisticsFilteredSubsetValueTask()
    expected = {
        "filtered_column_sum": {
            "evidence": [[260, 180, 372, 236], [374, 180, 486, 236], [260, 236, 372, 292], [374, 236, 486, 292]],
            "answer": 27,
        },
        "filtered_column_mean": {
            "evidence": [[260, 180, 372, 236], [374, 180, 486, 236], [260, 236, 372, 292], [374, 236, 486, 292]],
            "answer": 14,
        },
    }
    for index, query_id in enumerate(expected, start=18230):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[query_id]
        assert answer_only == {"answer": expected[query_id]["answer"]}


def test_table_statistics_filtered_subset_value_task_is_deterministic() -> None:
    task = TablesStatisticsFilteredSubsetValueTask()
    params = {"query_id": "filtered_column_mean", "scene_variant": "spreadsheet"}
    out_a = task.generate(18260, params=params, max_attempts=10)
    out_b = task.generate(18260, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
