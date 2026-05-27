"""Behavior tests for table counting tasks."""

from __future__ import annotations

from trace.tasks.charts.table.counting.value_count import TablesCountingValueCountTask
from tests.helpers import extract_prompt_json_example


def test_table_counting_value_count_variants_match_contract() -> None:
    task = TablesCountingValueCountTask()
    cases = (
        ("threshold_count", "greater_than", "spreadsheet"),
        ("threshold_count", "less_than", "zebra"),
        ("in_interval", None, "ledger"),
        ("categorical_value_count", None, "spreadsheet"),
        ("threshold_count", "greater_than", "card_table"),
    )
    for seed, (query_id, comparison, scene_variant) in enumerate(cases, start=18210):
        params = {"query_id": query_id, "scene_variant": scene_variant}
        if comparison is not None:
            params["comparison"] = str(comparison)
        out = task.generate(seed, params=params, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        row_labels = [str(label) for label in execution["row_labels"]]
        column_headers = [str(header) for header in execution["column_headers"]]
        query_column = str(execution["query_column"])
        raw_values_by_row = {
            str(row_label): {
                str(header): value
                for header, value in row_values.items()
            }
            for row_label, row_values in execution["values_by_row"].items()
        }
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
        matching_row_indices = [int(value) for value in execution["matching_row_indices"]]
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
        assert len(row_labels) == int(execution["row_count"])
        expected_column_count = (
            int(execution["numeric_column_count"]) + 1
            if str(query_id) == "categorical_value_count"
            else int(execution["numeric_column_count"])
        )
        assert len(column_headers) == expected_column_count
        assert str(query_column) in set(column_headers)
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert len(evidence_bboxes) == int(out.answer_gt.value) == len(expected_cell_ids)

        if str(query_id) == "categorical_value_count":
            target_category = str(execution["target_category"])
            query_values = [str(raw_values_by_row[str(row_label)][str(query_column)]) for row_label in row_labels]
            expected_row_indices = [
                int(index)
                for index, value in enumerate(query_values)
                if str(value) == str(target_category)
            ]
        elif str(query_id) == "threshold_count" and str(comparison) == "greater_than":
            query_values = [int(raw_values_by_row[str(row_label)][str(query_column)]) for row_label in row_labels]
            threshold_value = int(execution["threshold_value"])
            expected_row_indices = [
                int(index) for index, value in enumerate(query_values) if int(value) > int(threshold_value)
            ]
        elif str(query_id) == "threshold_count" and str(comparison) == "less_than":
            query_values = [int(raw_values_by_row[str(row_label)][str(query_column)]) for row_label in row_labels]
            threshold_value = int(execution["threshold_value"])
            expected_row_indices = [
                int(index) for index, value in enumerate(query_values) if int(value) < int(threshold_value)
            ]
        else:
            query_values = [int(raw_values_by_row[str(row_label)][str(query_column)]) for row_label in row_labels]
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
        "threshold_count": {"evidence": [[260, 180, 372, 236], [260, 236, 372, 292]], "answer": 2},
        "in_interval": {"evidence": [[260, 180, 372, 236], [260, 236, 372, 292], [260, 292, 372, 348]], "answer": 3},
        "categorical_value_count": {"evidence": [[260, 180, 372, 236], [260, 292, 372, 348]], "answer": 2},
    }
    for index, query_id in enumerate(expected, start=18230):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[query_id]
        assert answer_only == {"answer": expected[query_id]["answer"]}


def test_table_counting_value_count_task_is_deterministic() -> None:
    task = TablesCountingValueCountTask()
    params = {"query_id": "in_interval", "scene_variant": "spreadsheet"}
    out_a = task.generate(18260, params=params, max_attempts=10)
    out_b = task.generate(18260, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_table_counting_visual_style_axes_preserve_projected_bboxes() -> None:
    task = TablesCountingValueCountTask()
    params = {
        "query_id": "in_interval",
        "scene_variant": "spreadsheet",
        "header_style": "dark",
        "frame_style": "shadow",
        "inner_rule_style": "dashed",
        "numeric_alignment": "right",
        "table_margin_left_px": 80,
        "table_margin_right_px": 45,
        "table_margin_top_px": 70,
        "table_margin_bottom_px": 60,
    }
    out = task.generate(18295, params=params, max_attempts=10)
    trace = out.trace_payload
    render = trace["render_spec"]
    style = render["table_style"]

    assert style["header_style"] == "dark"
    assert style["frame_style"] == "shadow"
    assert style["inner_rule_style"] == "dashed"
    assert style["numeric_alignment"] == "right"
    assert render["table_bbox_px"] == [80.0, 70.0, 895.0, 840.0]
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

    expected_bboxes = [
        [float(value) for value in trace["render_map"]["cell_bboxes_px"][str(cell_id)]]
        for cell_id in trace["execution_trace"]["supporting_cell_ids"]
    ]
    assert out.evidence_gt.value == expected_bboxes


def test_table_counting_target_count_sampling_decouples_from_query_id_sampling() -> None:
    task = TablesCountingValueCountTask()
    answers_by_variant: dict[str, set[int]] = {}
    for sampling_index in range(30):
        out = task.generate(
            18360 + int(sampling_index),
            params={
                "row_count_min": 10,
                "row_count_max": 10,
            },
            max_attempts=10,
        )
        answers_by_variant.setdefault(str(out.query_id), set()).add(int(out.answer_gt.value))

    assert set(answers_by_variant) == {"threshold_count", "in_interval", "categorical_value_count"}
    assert answers_by_variant["threshold_count"].issubset(set(range(4, 9)))
    assert answers_by_variant["in_interval"].issubset(set(range(4, 9)))
    assert answers_by_variant["categorical_value_count"].issubset(set(range(10)))
    assert all(answers for answers in answers_by_variant.values())


def test_table_counting_interval_uses_bounded_answer_and_boundary_distractors() -> None:
    task = TablesCountingValueCountTask()
    for seed in range(18410, 18430):
        out = task.generate(
            seed,
            params={
                "query_id": "in_interval",
                "row_count_min": 10,
                "row_count_max": 10,
            },
            max_attempts=10,
        )
        execution = out.trace_payload["execution_trace"]
        row_labels = [str(label) for label in execution["row_labels"]]
        query_column = str(execution["query_column"])
        values_by_row = execution["values_by_row"]
        interval_min = int(execution["interval_min"])
        interval_max = int(execution["interval_max"])
        answer = int(out.answer_gt.value)

        assert 4 <= answer <= 8
        for row_label in row_labels:
            value = int(values_by_row[str(row_label)][str(query_column)])
            if int(interval_min) <= int(value) <= int(interval_max):
                continue
            assert (
                1 <= abs(int(value) - int(interval_min)) <= 2
                or 1 <= abs(int(value) - int(interval_max)) <= 2
            )


def test_table_counting_threshold_uses_bounded_answer_and_boundary_values() -> None:
    task = TablesCountingValueCountTask()
    cases = (("greater_than", 18440), ("less_than", 18460))
    for comparison, seed_start in cases:
        for seed in range(int(seed_start), int(seed_start) + 20):
            out = task.generate(
                seed,
                params={
                    "query_id": "threshold_count",
                    "comparison": str(comparison),
                    "row_count_min": 10,
                    "row_count_max": 10,
                },
                max_attempts=10,
            )
            execution = out.trace_payload["execution_trace"]
            row_labels = [str(label) for label in execution["row_labels"]]
            query_column = str(execution["query_column"])
            values_by_row = execution["values_by_row"]
            threshold_value = int(execution["threshold_value"])
            answer = int(out.answer_gt.value)

            assert 4 <= answer <= 8
            for row_label in row_labels:
                value = int(values_by_row[str(row_label)][str(query_column)])
                assert abs(int(value) - int(threshold_value)) <= 2
                if str(comparison) == "greater_than":
                    assert (int(value) > int(threshold_value)) == (
                        int(row_labels.index(str(row_label))) in set(execution["matching_row_indices"])
                    )
                else:
                    assert (int(value) < int(threshold_value)) == (
                        int(row_labels.index(str(row_label))) in set(execution["matching_row_indices"])
                    )
