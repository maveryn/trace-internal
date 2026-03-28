"""Behavior tests for table statistics tasks."""

from __future__ import annotations

from trace.core.type_registry import load_type_registry
from trace.tasks.tables.statistics.filtered_subset_value import TablesStatisticsFilteredSubsetValueTask
from trace.tasks.tables.statistics.summary_label import TablesStatisticsSummaryLabelTask
from trace.tasks.tables.statistics.summary_value import TablesStatisticsSummaryValueTask
from tests.helpers import extract_prompt_json_example


def test_table_statistics_summary_label_variants_match_contract() -> None:
    task = TablesStatisticsSummaryLabelTask()
    cases = (
        ("argmax", "spreadsheet"),
        ("argmin", "zebra"),
        ("row_sum_argmax", "ledger"),
        ("row_sum_argmin", "card_table"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=18010):
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
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
        answer = str(out.answer_gt.value)
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

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

        if str(task_variant).startswith("row_sum_"):
            row_totals = {
                str(row_label): sum(int(values_by_row[str(row_label)][str(header)]) for header in column_headers)
                for row_label in row_labels
            }
            assert evidence_bboxes[0] == [
                float(value) for value in trace["render_map"]["row_region_bboxes_px"][answer]
            ]
            if str(task_variant) == "row_sum_argmax":
                assert int(row_totals[str(answer)]) == max(row_totals.values())
            else:
                assert int(row_totals[str(answer)]) == min(row_totals.values())
            assert len(set(int(total) for total in row_totals.values())) == len(row_totals)
        else:
            query_column = str(execution["query_column"])
            winning_value = int(values_by_row[str(answer)][str(query_column)])
            query_values = {str(label): int(row_values[str(query_column)]) for label, row_values in values_by_row.items()}
            assert str(query_column) in set(column_headers)
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
        "row_sum_argmax": {"evidence": [[150, 180, 780, 236]], "answer": "Ava"},
        "row_sum_argmin": {"evidence": [[150, 180, 780, 236]], "answer": "Milo"},
    }
    for index, task_variant in enumerate(expected, start=18040):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_table_statistics_summary_label_task_is_deterministic() -> None:
    task = TablesStatisticsSummaryLabelTask()
    params = {"task_variant": "row_sum_argmax", "scene_variant": "spreadsheet"}
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
        ("row_sum", "card_table"),
        ("row_mean", "spreadsheet"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=18110):
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
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

        if str(task_variant).startswith("row_"):
            query_row_label = str(execution["query_row_label"])
            query_values = [int(values_by_row[str(query_row_label)][str(header)]) for header in column_headers]
            assert str(query_row_label) in set(row_labels)
            assert evidence_bboxes[0] == [
                float(value) for value in trace["render_map"]["row_region_bboxes_px"][query_row_label]
            ]
            if str(task_variant) == "row_sum":
                assert int(out.answer_gt.value) == sum(query_values)
            else:
                assert int(out.answer_gt.value) == (sum(query_values) // len(query_values))
                assert sum(query_values) % len(query_values) == 0
        else:
            query_column = str(execution["query_column"])
            query_values = [int(values_by_row[str(row_label)][str(query_column)]) for row_label in row_labels]
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
        "row_sum": {"evidence": [[150, 180, 780, 236]], "answer": 62},
        "row_mean": {"evidence": [[150, 180, 780, 236]], "answer": 15},
    }
    for index, task_variant in enumerate(expected, start=18130):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_table_statistics_summary_value_task_is_deterministic() -> None:
    task = TablesStatisticsSummaryValueTask()
    params = {"task_variant": "row_mean", "scene_variant": "spreadsheet"}
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


def test_table_statistics_filtered_subset_value_variants_match_contract() -> None:
    task = TablesStatisticsFilteredSubsetValueTask()
    cases = (
        ("filtered_column_sum", "spreadsheet"),
        ("filtered_column_mean", "zebra"),
        ("filtered_column_sum", "ledger"),
        ("filtered_column_mean", "card_table"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=18190):
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
        filter_column = str(execution["filter_column"])
        target_column = str(execution["target_column"])
        selected_row_indices = [int(value) for value in execution["selected_row_indices"]]
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
        assert filter_column != target_column
        assert len(selected_row_indices) >= 1
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
        if str(task_variant) == "filtered_column_sum":
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
    for index, task_variant in enumerate(expected, start=18230):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_table_statistics_filtered_subset_value_task_is_deterministic() -> None:
    task = TablesStatisticsFilteredSubsetValueTask()
    params = {"task_variant": "filtered_column_mean", "scene_variant": "spreadsheet"}
    out_a = task.generate(18260, params=params, max_attempts=10)
    out_b = task.generate(18260, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
