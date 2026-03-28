"""Behavior tests for chart composition tasks."""

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
    assert all(
        0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values()
    )


def test_chart_composition_variants_match_contract() -> None:
    task = ChartsCompositionSubsetValueTask()
    cases = (
        ("stack_total_at_label", "stacked_bar"),
        ("stack_segment_value", "stacked_horizontal_bar"),
        ("combined_share_subset", "pie"),
        ("combined_share_subset", "donut"),
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
        assert len(trace["projected_evidence"]["bbox_set"]) == len(evidence_values)

        if str(scene_variant) in {"stacked_bar", "stacked_horizontal_bar"}:
            assert int(execution["category_count"]) >= 4
            assert int(execution["series_count"]) >= 3
            query_category = str(execution["query_category_label"])
            stack_values = execution["values_by_category"][query_category]
            assert evidence_values == [int(stack_values[str(label)]) for label in execution["series_labels"]]
            if str(task_variant) == "stack_total_at_label":
                assert int(out.answer_gt.value) == int(sum(evidence_values))
            else:
                assert int(out.answer_gt.value) == int(stack_values[str(execution["query_series_label"])])
            assert all("value_center_px" in entity["attrs"] for entity in trace["scene_ir"]["entities"])
            assert all("legend_swatch_bbox_px" in entity["attrs"] for entity in trace["scene_ir"]["entities"])
            assert all("legend_label_bbox_px" in entity["attrs"] for entity in trace["scene_ir"]["entities"])
            assert all(
                float(entity["attrs"]["legend_label_bbox_px"][0]) > float(entity["attrs"]["legend_swatch_bbox_px"][2])
                for entity in trace["scene_ir"]["entities"]
            )
        else:
            assert sum(evidence_values) == 100
            assert str(execution["value_semantics"]) == "percentage"
            subset = [str(label) for label in execution["query_subset_labels"]]
            assert len(subset) == 2
            assert int(out.answer_gt.value) == int(sum(int(execution["values_by_label"][label]) for label in subset))


def test_chart_composition_prompts_match_scene_variant_wording() -> None:
    task = ChartsCompositionSubsetValueTask()
    stacked = task.generate(
        17030,
        params={"task_variant": "stack_total_at_label", "scene_variant": "stacked_bar"},
        max_attempts=10,
    )
    horizontal = task.generate(
        17031,
        params={"task_variant": "stack_segment_value", "scene_variant": "stacked_horizontal_bar"},
        max_attempts=10,
    )
    pie = task.generate(
        17032,
        params={"task_variant": "combined_share_subset", "scene_variant": "pie"},
        max_attempts=10,
    )
    donut = task.generate(
        17033,
        params={"task_variant": "combined_share_subset", "scene_variant": "donut"},
        max_attempts=10,
    )

    assert "printed inside the segments" in str(stacked.prompt)
    assert "printed inside the segments" in str(horizontal.prompt)
    assert "horizontal bar" in str(horizontal.prompt)
    assert "percentages" in str(pie.prompt)
    assert "legend on the right" in str(pie.prompt)
    assert "percentages" in str(donut.prompt)
    assert "legend on the right" in str(donut.prompt)


def test_chart_composition_invalid_scene_variant_combinations_raise() -> None:
    task = ChartsCompositionSubsetValueTask()
    with pytest.raises(ValueError):
        task.generate(17040, params={"task_variant": "stack_total_at_label", "scene_variant": "pie"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(17041, params={"task_variant": "stack_segment_value", "scene_variant": "donut"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(17042, params={"task_variant": "combined_share_subset", "scene_variant": "stacked_bar"}, max_attempts=10)


def test_chart_composition_prompt_examples_match_selected_variant() -> None:
    task = ChartsCompositionSubsetValueTask()
    expected = {
        "stack_total_at_label": {"evidence": [6, 9, 5], "answer": 20},
        "stack_segment_value": {"evidence": [6, 9, 5], "answer": 9},
        "combined_share_subset": {"evidence": [18, 27, 22, 33], "answer": 45},
    }
    for seed, task_variant in enumerate(expected, start=17050):
        out = task.generate(seed, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_chart_composition_task_is_deterministic() -> None:
    task = ChartsCompositionSubsetValueTask()
    params = {"task_variant": "stack_segment_value", "scene_variant": "stacked_bar"}
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
            "task_variant": "stack_segment_value",
            "scene_variant": "stacked_bar",
            "category_count_min": 4,
            "category_count_max": 4,
            "series_count_min": 3,
            "series_count_max": 3,
        },
        max_attempts=10,
    )
    hard = task.generate(
        17061,
        params={
            "task_variant": "combined_share_subset",
            "scene_variant": "donut",
            "series_count_min": 5,
            "series_count_max": 5,
        },
        max_attempts=10,
    )
    _assert_normalized_complexity(easy)
    _assert_normalized_complexity(hard)
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)


def test_chart_composition_registers_integer_list_evidence() -> None:
    registry = load_type_registry()
    assert registry.validate_evidence_type("integer_list") is True
