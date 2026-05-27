"""Behavior tests for chart table temporal tasks."""

from __future__ import annotations

from trace.tasks.charts.table.temporal.value import ChartsTableTemporalValueTaskBase
from tests.helpers import extract_prompt_json_example


def test_table_temporal_value_contract_matches_queried_year_cells() -> None:
    task = ChartsTableTemporalValueTaskBase()
    query_ids = (
        "absolute_difference_between_rows_over_year_interval",
        "sum_absolute_differences_between_rows_over_year_interval",
    )
    scene_variants = ("spreadsheet", "zebra", "ledger", "card_table")
    for query_id_index, query_id in enumerate(query_ids):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 19010 + (query_id_index * 20) + scene_index
            out = task.generate(
                seed,
                params={"query_id": query_id, "scene_variant": scene_variant},
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
            query_row_labels = [str(label) for label in execution["query_row_labels"]]
            query_years = [str(year) for year in execution["query_years"]]
            query_cells = [dict(cell) for cell in execution["query_cells"]]
            supporting_cell_ids = [str(cell_id) for cell_id in execution["supporting_cell_ids"]]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert str(out.query_id) == str(query_id)
            assert out.answer_gt.type == "integer"
            assert out.evidence_gt.type == "bbox_set"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert 10 <= int(execution["row_count"]) <= 20
            assert 8 <= int(execution["numeric_column_count"]) <= 16
            assert list(execution["interval_length_range"]) == [4, 5]
            assert list(execution["value_range"]) == [1, 99]
            assert str(query_row_label) in set(row_labels)
            assert set(query_row_labels).issubset(set(row_labels))
            assert all(str(year).isdigit() and len(str(year)) == 4 for year in column_headers)
            assert [int(year) for year in column_headers] == list(
                range(int(column_headers[0]), int(column_headers[0]) + len(column_headers))
            )
            assert [int(year) for year in query_years] == sorted(int(year) for year in query_years)
            assert 4 <= len(query_years) <= 5
            assert len(evidence_bboxes) == len(query_cells) == len(supporting_cell_ids)
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes

            row_a = str(execution["query_row_label_a"])
            row_b = str(execution["query_row_label_b"])
            assert row_a != row_b
            assert query_row_labels == [row_a, row_b]
            assert int(execution["query_row_index_a"]) != int(execution["query_row_index_b"])
            assert len(query_cells) == 2 * len(query_years)
            cells_a = query_cells[: len(query_years)]
            cells_b = query_cells[len(query_years) :]
            assert [str(cell["row_role"]) for cell in cells_a] == ["row_a"] * len(query_years)
            assert [str(cell["row_role"]) for cell in cells_b] == ["row_b"] * len(query_years)
            assert [str(cell["row_label"]) for cell in cells_a] == [row_a] * len(query_years)
            assert [str(cell["row_label"]) for cell in cells_b] == [row_b] * len(query_years)
            assert [str(cell["column"]) for cell in cells_a] == query_years
            assert [str(cell["column"]) for cell in cells_b] == query_years
            values_a = [int(values_by_row[row_a][str(cell["column"])]) for cell in cells_a]
            values_b = [int(values_by_row[row_b][str(cell["column"])]) for cell in cells_b]
            sum_a = int(sum(values_a))
            sum_b = int(sum(values_b))
            assert int(execution["row_interval_sums"][row_a]) == int(sum_a)
            assert int(execution["row_interval_sums"][row_b]) == int(sum_b)
            if str(query_id) == "absolute_difference_between_rows_over_year_interval":
                assert int(out.answer_gt.value) == int(abs(sum(values_a) - sum(values_b)))
            else:
                paired_differences = [
                    int(abs(int(value_a) - int(value_b)))
                    for value_a, value_b in zip(values_a, values_b)
                ]
                assert [int(value) for value in execution["paired_absolute_differences"]] == paired_differences
                assert int(out.answer_gt.value) == int(sum(paired_differences))

            expected_bboxes = [
                [float(value) for value in trace["render_map"]["cell_bboxes_px"][str(cell_id)]]
                for cell_id in supporting_cell_ids
            ]
            assert evidence_bboxes == expected_bboxes


def test_table_temporal_prompt_examples_match_selected_variants() -> None:
    task = ChartsTableTemporalValueTaskBase()
    evidence = [
        [260, 180, 320, 220],
        [322, 180, 382, 220],
        [384, 180, 444, 220],
        [260, 236, 320, 276],
        [322, 236, 382, 276],
        [384, 236, 444, 276],
    ]
    expected = {
        "absolute_difference_between_rows_over_year_interval": (
            {"evidence": evidence, "answer": 7},
            {"answer": 7},
        ),
        "sum_absolute_differences_between_rows_over_year_interval": (
            {"evidence": evidence, "answer": 17},
            {"answer": 17},
        ),
    }
    for index, (query_id, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=19040):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_table_temporal_value_task_is_deterministic() -> None:
    task = ChartsTableTemporalValueTaskBase()
    params = {"query_id": "sum_absolute_differences_between_rows_over_year_interval", "scene_variant": "spreadsheet"}
    out_a = task.generate(19080, params=params, max_attempts=10)
    out_b = task.generate(19080, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
