"""Behavior tests for table readout tasks."""

from __future__ import annotations

from trace.tasks.tables.readout.cell_value import TablesReadoutCellValueTask
from tests.helpers import extract_prompt_json_example


def test_table_readout_cell_value_contract_matches_query_cell() -> None:
    task = TablesReadoutCellValueTask()
    for seed, scene_variant in enumerate(("spreadsheet", "zebra", "ledger", "card_table"), start=18310):
        out = task.generate(seed, params={"scene_variant": scene_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        query_row_label = str(execution["query_row_label"])
        query_column = str(execution["query_column"])
        values_by_row = {
            str(row_label): {
                str(header): int(value)
                for header, value in row_values.items()
            }
            for row_label, row_values in execution["values_by_row"].items()
        }
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
        supporting_cell_id = str(execution["supporting_cell_id"])

        assert str(out.task_variant) == "cell_lookup"
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 5 <= int(execution["row_count"]) <= 10
        assert 3 <= int(execution["numeric_column_count"]) <= 5
        assert len(evidence_bboxes) == 1
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert int(out.answer_gt.value) == int(values_by_row[query_row_label][query_column])
        assert evidence_bboxes[0] == [float(value) for value in trace["render_map"]["cell_bboxes_px"][supporting_cell_id]]


def test_table_readout_prompt_example_matches_selected_variant() -> None:
    task = TablesReadoutCellValueTask()
    out = task.generate(18330, params={"task_variant": "cell_lookup"}, max_attempts=10)
    answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_evidence == {"evidence": [[260, 180, 372, 236]], "answer": 17}
    assert answer_only == {"answer": 17}


def test_table_readout_cell_value_task_is_deterministic() -> None:
    task = TablesReadoutCellValueTask()
    params = {"task_variant": "cell_lookup", "scene_variant": "spreadsheet"}
    out_a = task.generate(18360, params=params, max_attempts=10)
    out_b = task.generate(18360, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
