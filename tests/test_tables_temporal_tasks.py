"""Behavior tests for table temporal tasks."""

from __future__ import annotations

from trace.tasks.tables.temporal.value import TablesTemporalValueTask
from tests.helpers import extract_prompt_json_example


def test_table_temporal_value_contract_matches_queried_year_cells() -> None:
    task = TablesTemporalValueTask()
    task_variants = (
        "value_at_year",
        "delta_between_years",
        "absolute_difference_between_years",
        "sum_over_year_interval",
        "mean_over_year_interval",
    )
    scene_variants = ("spreadsheet", "zebra", "ledger", "card_table")
    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 19010 + (variant_index * 20) + scene_index
            out = task.generate(
                seed,
                params={"task_variant": task_variant, "scene_variant": scene_variant},
                max_attempts=10,
            )
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
            query_row_label = str(execution["query_row_label"])
            query_years = [str(year) for year in execution["query_years"]]
            query_cells = [dict(cell) for cell in execution["query_cells"]]
            supporting_cell_ids = [str(cell_id) for cell_id in execution["supporting_cell_ids"]]
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
            assert str(query_row_label) in set(row_labels)
            assert all(str(year).isdigit() and len(str(year)) == 4 for year in column_headers)
            assert [int(year) for year in column_headers] == list(
                range(int(column_headers[0]), int(column_headers[0]) + len(column_headers))
            )
            assert query_years == [str(cell["column"]) for cell in query_cells]
            assert [str(cell["row_label"]) for cell in query_cells] == [str(query_row_label)] * len(query_cells)
            assert [int(year) for year in query_years] == sorted(int(year) for year in query_years)
            assert len(evidence_bboxes) == len(query_cells) == len(supporting_cell_ids)
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes

            queried_values = [
                int(values_by_row[str(query_row_label)][str(cell["column"])])
                for cell in query_cells
            ]
            if str(task_variant) == "value_at_year":
                assert len(query_cells) == 1
                assert int(out.answer_gt.value) == int(queried_values[0])
            elif str(task_variant) == "delta_between_years":
                assert len(query_cells) == 2
                assert int(out.answer_gt.value) == int(queried_values[1] - queried_values[0])
            elif str(task_variant) == "absolute_difference_between_years":
                assert len(query_cells) == 2
                assert int(out.answer_gt.value) == int(abs(int(queried_values[1]) - int(queried_values[0])))
            elif str(task_variant) == "sum_over_year_interval":
                assert len(query_cells) >= 2
                assert int(out.answer_gt.value) == int(sum(queried_values))
            else:
                assert len(query_cells) >= 2
                assert int(out.answer_gt.value) == int(sum(queried_values) // len(queried_values))
                assert sum(queried_values) % len(queried_values) == 0

            expected_bboxes = [
                [float(value) for value in trace["render_map"]["cell_bboxes_px"][str(cell_id)]]
                for cell_id in supporting_cell_ids
            ]
            assert evidence_bboxes == expected_bboxes


def test_table_temporal_prompt_examples_match_selected_variants() -> None:
    task = TablesTemporalValueTask()
    expected = {
        "value_at_year": (
            {"evidence": [[260, 180, 372, 236]], "answer": 17},
            {"answer": 17},
        ),
        "delta_between_years": (
            {"evidence": [[260, 180, 372, 236], [374, 180, 486, 236]], "answer": -4},
            {"answer": -4},
        ),
        "absolute_difference_between_years": (
            {"evidence": [[260, 180, 372, 236], [374, 180, 486, 236]], "answer": 4},
            {"answer": 4},
        ),
        "sum_over_year_interval": (
            {"evidence": [[260, 180, 372, 236], [374, 180, 486, 236], [488, 180, 600, 236]], "answer": 29},
            {"answer": 29},
        ),
        "mean_over_year_interval": (
            {"evidence": [[260, 180, 372, 236], [374, 180, 486, 236], [488, 180, 600, 236]], "answer": 14},
            {"answer": 14},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=19040):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_table_temporal_value_task_is_deterministic() -> None:
    task = TablesTemporalValueTask()
    params = {"task_variant": "mean_over_year_interval", "scene_variant": "spreadsheet"}
    out_a = task.generate(19080, params=params, max_attempts=10)
    out_b = task.generate(19080, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
