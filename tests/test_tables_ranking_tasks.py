"""Behavior tests for table ranking tasks."""

from __future__ import annotations

from trace.tasks.charts.table.ranking.label import TablesRankingLabelTask
from tests.helpers import extract_prompt_json_example


def test_table_ranking_label_variants_match_contract() -> None:
    task = TablesRankingLabelTask()
    cases = (
        ("highest", "spreadsheet"),
        ("lowest", "zebra"),
        ("highest", "ledger"),
        ("lowest", "card_table"),
    )
    for seed, (rank_direction, scene_variant) in enumerate(cases, start=18610):
        out = task.generate(
            seed,
            params={
                "query_variant": "kth_rank_in_column",
                "rank_direction": rank_direction,
                "scene_variant": scene_variant,
            },
            max_attempts=10,
        )
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
        query_column = str(execution["query_column"])
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

        assert str(out.query_variant) == "kth_rank_in_column"
        assert out.answer_gt.type == "string"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert 10 <= int(execution["row_count"]) <= 20
        assert 3 <= int(execution["numeric_column_count"]) <= 5
        assert len(evidence_bboxes) == 1
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert evidence_bboxes[0] == [
            float(value) for value in trace["render_map"]["column_region_bboxes_px"][query_column]
        ]

        query_rank = int(execution["query_rank"])
        assert 2 <= int(query_rank) <= 4
        query_values = [
            {
                "row_label": str(row_label),
                "value": int(values_by_row[str(row_label)][str(query_column)]),
            }
            for row_label in row_labels
        ]
        assert len({int(item["value"]) for item in query_values}) == len(query_values)
        sorted_rows = sorted(
            query_values,
            key=lambda item: int(item["value"]),
            reverse=(str(rank_direction) == "highest"),
        )
        assert str(out.answer_gt.value) == str(sorted_rows[int(query_rank) - 1]["row_label"])


def test_table_ranking_label_prompt_examples_match_selected_variant() -> None:
    task = TablesRankingLabelTask()
    expected = {"evidence": [[260, 180, 372, 520]], "answer": "Ava"}
    for index, rank_direction in enumerate(("highest", "lowest"), start=18640):
        out = task.generate(
            index,
            params={"query_variant": "kth_rank_in_column", "rank_direction": rank_direction},
            max_attempts=10,
        )
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected
        assert answer_only == {"answer": expected["answer"]}


def test_table_ranking_label_task_is_deterministic() -> None:
    task = TablesRankingLabelTask()
    params = {"query_variant": "kth_highest_in_column", "scene_variant": "spreadsheet"}
    out_a = task.generate(18670, params=params, max_attempts=10)
    out_b = task.generate(18670, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
