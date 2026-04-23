"""Behavior tests for stacked composition-chart arithmetic tasks."""

from __future__ import annotations

import json

import pytest

from trace.core.type_registry import load_type_registry
from trace.tasks.charts.composition.subset_value import ChartsCompositionSubsetValueTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _assert_normalized_complexity(out: object) -> None:
    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values())


def test_chart_composition_variants_match_contract() -> None:
    task = ChartsCompositionSubsetValueTask()
    cases = (
        ("category_subset_sum", "stacked_bar"),
        ("series_across_categories_sum", "stacked_horizontal_bar"),
        ("subset_margin_sum", "stacked_bar"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=17010):
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        evidence_values = [int(value) for value in out.evidence_gt.value]

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "integer_list"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert trace["projected_evidence"]["integer_list"] == evidence_values
        assert len(trace["projected_evidence"]["bbox_set"]) == len(execution["evidence_cells"])
        assert int(execution["category_count"]) >= 6
        assert int(execution["series_count"]) >= 5
        assert all("value_center_px" in entity["attrs"] for entity in trace["scene_ir"]["entities"])
        assert all("legend_swatch_bbox_px" in entity["attrs"] for entity in trace["scene_ir"]["entities"])
        assert all("legend_label_bbox_px" in entity["attrs"] for entity in trace["scene_ir"]["entities"])

        values_by_category = execution["values_by_category"]
        if str(task_variant) == "category_subset_sum":
            category_label = str(execution["query_category_label"])
            subset_labels = [str(label) for label in execution["query_series_subset_labels"]]
            expected = [
                int(values_by_category[category_label][str(series_label)])
                for series_label in subset_labels
            ]
            assert evidence_values == expected
            assert int(out.answer_gt.value) == int(sum(expected))
        elif str(task_variant) == "series_across_categories_sum":
            series_label = str(execution["query_series_label"])
            category_labels = [str(label) for label in execution["query_category_subset_labels"]]
            expected = [
                int(values_by_category[str(category_label)][series_label])
                for category_label in category_labels
            ]
            assert evidence_values == expected
            assert int(out.answer_gt.value) == int(sum(expected))
        else:
            assert len(evidence_values) == int(execution["category_count"])
            positive_margin_sum = sum(int(value) for value in evidence_values if int(value) > 0)
            assert int(out.answer_gt.value) == int(positive_margin_sum)


def test_chart_composition_prompts_match_scene_variant_wording() -> None:
    task = ChartsCompositionSubsetValueTask()
    stacked = task.generate(
        17030,
        params={"task_variant": "category_subset_sum", "scene_variant": "stacked_bar"},
        max_attempts=10,
    )
    horizontal = task.generate(
        17031,
        params={"task_variant": "series_across_categories_sum", "scene_variant": "stacked_horizontal_bar"},
        max_attempts=10,
    )
    comparison = task.generate(
        17032,
        params={"task_variant": "subset_margin_sum", "scene_variant": "stacked_bar"},
        max_attempts=10,
    )

    assert "printed segment values" in str(stacked.prompt)
    assert "printed segment values" in str(horizontal.prompt)
    assert "horizontal bar" in str(horizontal.prompt)
    assert (
        "positive margins" in str(comparison.prompt)
        or "total margin" in str(comparison.prompt)
        or "positive differences" in str(comparison.prompt)
    )


def test_chart_composition_invalid_scene_variant_combinations_raise() -> None:
    task = ChartsCompositionSubsetValueTask()
    with pytest.raises(ValueError):
        task.generate(17040, params={"task_variant": "category_subset_sum", "scene_variant": "pie"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(17041, params={"task_variant": "series_across_categories_sum", "scene_variant": "donut"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(17042, params={"task_variant": "subset_margin_sum", "scene_variant": "pie"}, max_attempts=10)


def test_chart_composition_prompt_examples_match_selected_variant() -> None:
    task = ChartsCompositionSubsetValueTask()
    expected = {
        "category_subset_sum": {"evidence": [6, 9, 5], "answer": 20},
        "series_across_categories_sum": {"evidence": [7, 11, 8], "answer": 26},
        "subset_margin_sum": {"evidence": [5, -3, 9, 1], "answer": 15},
    }
    for seed, task_variant in enumerate(expected, start=17050):
        out = task.generate(seed, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_chart_composition_prompt_metadata_uses_variant_specific_required_slots() -> None:
    task = ChartsCompositionSubsetValueTask()
    cases = (
        ("category_subset_sum", "stacked_bar", ["query_category_label", "query_series_subset_labels"]),
        ("series_across_categories_sum", "stacked_bar", ["query_series_label", "query_category_subset_labels"]),
        ("subset_margin_sum", "stacked_horizontal_bar", ["left_series_subset_labels", "right_series_subset_labels"]),
    )
    for seed, (task_variant, scene_variant, required_slots) in enumerate(cases, start=17055):
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
        slot_values = out.trace_payload["query_spec"]["prompt_variant"]["slot_values"]
        assert str(out.trace_payload["query_spec"]["prompt_variant"]["task_variant_key"]) == str(task_variant)
        for slot in required_slots:
            assert str(slot_values[str(slot)]).strip()


def test_chart_composition_task_is_deterministic() -> None:
    task = ChartsCompositionSubsetValueTask()
    params = {"task_variant": "series_across_categories_sum", "scene_variant": "stacked_bar"}
    out_a = task.generate(17060, params=params, max_attempts=10)
    out_b = task.generate(17060, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_composition_complexity_is_normalized_and_monotonic() -> None:
    task = ChartsCompositionSubsetValueTask()
    easy = task.generate(
        17061,
        params={
            "task_variant": "category_subset_sum",
            "scene_variant": "stacked_bar",
            "category_count_min": 6,
            "category_count_max": 6,
            "series_count_min": 5,
            "series_count_max": 5,
            "query_series_subset_size_min": 3,
            "query_series_subset_size_max": 3,
        },
        max_attempts=10,
    )
    hard = task.generate(
        17061,
        params={
            "task_variant": "subset_margin_sum",
            "scene_variant": "stacked_horizontal_bar",
            "category_count_min": 9,
            "category_count_max": 9,
            "series_count_min": 7,
            "series_count_max": 7,
            "comparison_subset_size_min": 3,
            "comparison_subset_size_max": 3,
        },
        max_attempts=10,
    )
    _assert_normalized_complexity(easy)
    _assert_normalized_complexity(hard)
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)


def test_chart_composition_registers_integer_list_evidence() -> None:
    registry = load_type_registry()
    assert registry.validate_evidence_type("integer_list") is True
