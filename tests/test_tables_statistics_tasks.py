"""Behavior tests for table statistics tasks."""

from __future__ import annotations

import json

from trace.core.type_registry import load_type_registry
from trace.tasks.tables.statistics.summary_label import TablesStatisticsSummaryLabelTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


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
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
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
