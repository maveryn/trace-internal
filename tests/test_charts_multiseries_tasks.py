"""Behavior tests for chart multiseries tasks."""

from __future__ import annotations

import json

from trace.tasks.charts.multiseries.pairwise_comparison_count import (
    ChartsMultiseriesPairwiseComparisonCountTask,
)


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_chart_multiseries_pairwise_comparison_count_matches_contract() -> None:
    task = ChartsMultiseriesPairwiseComparisonCountTask()
    cases = (
        ("series_a_gt_b_count", "grouped_bar"),
        ("series_a_lt_b_count", "grouped_horizontal_bar"),
        ("series_a_gt_b_count", "multi_line"),
        ("series_a_lt_b_count", "grouped_lollipop"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=11010):
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        category_labels = [str(label) for label in execution["category_labels"]]
        series_labels = [str(label) for label in execution["series_labels"]]
        query_pair = [str(label) for label in execution["queried_series_labels"]]
        evidence_labels = [str(label) for label in out.evidence_gt.value]
        values_by_category = {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in series_values.items()
            }
            for category_label, series_values in execution["values_by_category"].items()
        }

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "label_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert 5 <= int(execution["category_count"]) <= 10
        assert 2 <= int(execution["series_count"]) <= 3
        assert len(category_labels) == int(execution["category_count"])
        assert len(series_labels) == int(execution["series_count"])
        assert all(str(label).istitle() for label in series_labels)
        assert all(str(label).isalpha() for label in series_labels)
        assert all(2 <= len(str(label)) <= 4 for label in series_labels)
        assert len(query_pair) == 2
        assert set(query_pair).issubset(set(series_labels))
        assert evidence_labels == sorted(evidence_labels)
        assert int(out.answer_gt.value) == len(evidence_labels)
        assert trace["projected_evidence"]["label_set"] == evidence_labels
        assert len(trace["projected_evidence"]["bbox_set"]) == len(evidence_labels)
        assert len(trace["scene_ir"]["entities"]) == int(execution["category_count"]) * int(execution["series_count"])
        assert set(str(entity["attrs"]["category_label"]) for entity in trace["scene_ir"]["entities"]) == set(category_labels)
        assert set(str(entity["attrs"]["series_label"]) for entity in trace["scene_ir"]["entities"]) == set(series_labels)
        assert set(trace["render_map"]["category_label_centers_px"].keys()) == set(category_labels)

        left_series, right_series = query_pair
        for category_label in category_labels:
            left_value = int(values_by_category[str(category_label)][str(left_series)])
            right_value = int(values_by_category[str(category_label)][str(right_series)])
            if str(task_variant) == "series_a_gt_b_count":
                assert (left_value > right_value) is (str(category_label) in set(evidence_labels))
            else:
                assert (left_value < right_value) is (str(category_label) in set(evidence_labels))


def test_chart_multiseries_prompts_match_scene_variant_wording() -> None:
    task = ChartsMultiseriesPairwiseComparisonCountTask()
    prompts = {}
    for seed, scene_variant in enumerate(
        ("grouped_bar", "grouped_horizontal_bar", "multi_line", "grouped_lollipop"),
        start=11030,
    ):
        out = task.generate(seed, params={"scene_variant": scene_variant}, max_attempts=10)
        prompts[str(scene_variant)] = str(out.prompt)
    assert "legend on the right" in prompts["grouped_bar"]
    assert "bar height" in prompts["grouped_bar"]
    assert "legend on the right" in prompts["grouped_horizontal_bar"]
    assert "bar length" in prompts["grouped_horizontal_bar"]
    assert "vertical axis" in prompts["grouped_horizontal_bar"]
    assert "legend on the right" in prompts["multi_line"]
    assert "y-values" in prompts["multi_line"]
    assert "legend on the right" in prompts["grouped_lollipop"]
    assert "vertical axis" in prompts["grouped_lollipop"]


def test_chart_multiseries_prompt_examples_match_selected_variant() -> None:
    task = ChartsMultiseriesPairwiseComparisonCountTask()
    expected = {
        "series_a_gt_b_count": {"evidence": ["B", "M", "Q"], "answer": 3},
        "series_a_lt_b_count": {"evidence": ["A", "T"], "answer": 2},
    }
    for index, task_variant in enumerate(expected, start=11040):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_chart_multiseries_task_is_deterministic() -> None:
    task = ChartsMultiseriesPairwiseComparisonCountTask()
    params = {"task_variant": "series_a_gt_b_count", "scene_variant": "multi_line"}
    out_a = task.generate(11050, params=params, max_attempts=10)
    out_b = task.generate(11050, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_multiseries_supports_explicit_category_and_series_counts() -> None:
    task = ChartsMultiseriesPairwiseComparisonCountTask()
    out = task.generate(
        11060,
        params={
            "task_variant": "series_a_gt_b_count",
            "scene_variant": "grouped_bar",
            "category_count_min": 10,
            "category_count_max": 10,
            "series_count_min": 3,
            "series_count_max": 3,
        },
        max_attempts=10,
    )
    assert int(out.trace_payload["execution_trace"]["category_count"]) == 10
    assert int(out.trace_payload["execution_trace"]["series_count"]) == 3
