"""Behavior tests for table readout tasks."""

from __future__ import annotations

from trace.tasks.tables.readout.subset_value import TablesReadoutSubsetValueTask
from tests.helpers import extract_prompt_json_example


def test_table_readout_subset_value_contract_matches_queried_cells() -> None:
    task = TablesReadoutSubsetValueTask()
    task_variants = ("cell_lookup", "cell_sum_two", "cell_difference_two_abs")
    scene_variants = ("spreadsheet", "zebra", "ledger", "card_table")
    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 18310 + (variant_index * 20) + scene_index
            out = task.generate(
                seed,
                params={"task_variant": task_variant, "scene_variant": scene_variant},
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]

            values_by_row = {
                str(row_label): {
                    str(header): int(value)
                    for header, value in row_values.items()
                }
                for row_label, row_values in execution["values_by_row"].items()
            }
            query_cells = [dict(cell) for cell in execution["query_cells"]]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
            supporting_cell_ids = [str(cell_id) for cell_id in execution["supporting_cell_ids"]]

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
            assert len(query_cells) == len(evidence_bboxes) == len(supporting_cell_ids)
            assert len(query_cells) == (1 if str(task_variant) == "cell_lookup" else 2)

            queried_values = [
                int(values_by_row[str(cell["row_label"])][str(cell["column"])])
                for cell in query_cells
            ]
            if str(task_variant) == "cell_lookup":
                assert int(out.answer_gt.value) == int(queried_values[0])
            elif str(task_variant) == "cell_sum_two":
                assert int(out.answer_gt.value) == int(sum(queried_values))
            else:
                assert int(out.answer_gt.value) == int(abs(int(queried_values[0]) - int(queried_values[1])))

            expected_bboxes = [
                [float(value) for value in trace["render_map"]["cell_bboxes_px"][str(cell_id)]]
                for cell_id in supporting_cell_ids
            ]
            assert evidence_bboxes == expected_bboxes


def test_table_readout_prompt_examples_match_selected_variants() -> None:
    task = TablesReadoutSubsetValueTask()
    expected = {
        "cell_lookup": (
            {"evidence": [[260, 180, 372, 236]], "answer": 17},
            {"answer": 17},
        ),
        "cell_sum_two": (
            {"evidence": [[260, 180, 372, 236], [374, 180, 486, 236]], "answer": 29},
            {"answer": 29},
        ),
        "cell_difference_two_abs": (
            {"evidence": [[260, 180, 372, 236], [374, 180, 486, 236]], "answer": 6},
            {"answer": 6},
        ),
    }
    for task_variant, (expected_answer_and_evidence, expected_answer_only) in expected.items():
        out = task.generate(18330, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_table_readout_subset_value_task_is_deterministic() -> None:
    task = TablesReadoutSubsetValueTask()
    params = {"task_variant": "cell_sum_two", "scene_variant": "spreadsheet"}
    out_a = task.generate(18360, params=params, max_attempts=10)
    out_b = task.generate(18360, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
