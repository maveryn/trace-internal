"""Behavior tests for chart counting tasks."""

from __future__ import annotations

import json

from trace.tasks.charts.counting.value_count import ChartsCountingValueCountTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _expected_count(task_variant: str, values: list[int], trace: dict) -> int:
    if str(task_variant) == "above_threshold":
        threshold = int(trace["threshold"])
        return sum(1 for value in values if int(value) > int(threshold))
    if str(task_variant) == "below_threshold":
        threshold = int(trace["threshold"])
        return sum(1 for value in values if int(value) < int(threshold))
    if str(task_variant) == "in_interval":
        interval_min = int(trace["interval_min"])
        interval_max = int(trace["interval_max"])
        return sum(1 for value in values if int(interval_min) <= int(value) <= int(interval_max))
    raise AssertionError(f"unsupported variant: {task_variant}")


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


def test_chart_counting_variants_match_contract() -> None:
    task = ChartsCountingValueCountTask()
    cases = (
        ("above_threshold", "bar"),
        ("below_threshold", "line"),
        ("in_interval", "scatter"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=9910):
        out = task.generate(
            seed,
            params={"task_variant": task_variant, "scene_variant": scene_variant},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        labels = [str(label) for label in execution["labels"]]
        values = [int(value) for value in execution["values"]]
        evidence_labels = [str(label) for label in out.evidence_gt.value]
        values_by_label = {str(label): int(value) for label, value in execution["values_by_label"].items()}

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "label_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert evidence_labels == sorted(evidence_labels)
        assert trace["projected_evidence"]["label_set"] == evidence_labels
        assert len(trace["projected_evidence"]["bbox_set"]) == len(evidence_labels)
        assert int(out.answer_gt.value) == int(execution["answer_value"])
        assert int(out.answer_gt.value) == _expected_count(str(task_variant), values, execution)
        assert len(evidence_labels) == int(out.answer_gt.value)
        assert str(trace["query_spec"]["task_variant"]) == str(task_variant)
        assert str(trace["query_spec"]["params"]["scene_variant"]) == str(scene_variant)
        assert len(trace["scene_ir"]["entities"]) == int(execution["mark_count"])
        assert set(str(entity["attrs"]["label"]) for entity in trace["scene_ir"]["entities"]) == set(labels)
        assert set(trace["render_map"]["label_centers_px"].keys()) == set(labels)
        assert len(render["y_ticks"]) == int(render["y_axis_max"]) + 1

        if str(task_variant) == "above_threshold":
            threshold = int(execution["threshold"])
            assert all(int(values_by_label[label]) > int(threshold) for label in evidence_labels)
        elif str(task_variant) == "below_threshold":
            threshold = int(execution["threshold"])
            assert all(int(values_by_label[label]) < int(threshold) for label in evidence_labels)
        else:
            interval_min = int(execution["interval_min"])
            interval_max = int(execution["interval_max"])
            assert bool(execution["interval_inclusive"]) is True
            assert all(
                int(interval_min) <= int(values_by_label[label]) <= int(interval_max)
                for label in evidence_labels
            )


def test_chart_counting_line_and_scatter_prompts_mention_y_values() -> None:
    task = ChartsCountingValueCountTask()
    line = task.generate(9921, params={"task_variant": "above_threshold", "scene_variant": "line"}, max_attempts=10)
    scatter = task.generate(9922, params={"task_variant": "below_threshold", "scene_variant": "scatter"}, max_attempts=10)
    area = task.generate(9923, params={"task_variant": "above_threshold", "scene_variant": "area"}, max_attempts=10)

    assert "y-values" in str(line.prompt)
    assert "y-values" in str(scatter.prompt)
    assert "y-values" in str(area.prompt)


def test_chart_counting_supports_additional_scene_variants() -> None:
    task = ChartsCountingValueCountTask()
    prompts = {}
    for seed, scene_variant in enumerate(("area", "horizontal_bar", "dot_plot", "lollipop", "pie", "donut", "radar"), start=9924):
        out = task.generate(
            seed,
            params={"task_variant": "above_threshold", "scene_variant": scene_variant},
            max_attempts=10,
        )
        prompts[str(scene_variant)] = str(out.prompt)
        assert str(out.trace_payload["execution_trace"]["scene_variant"]) == str(scene_variant)
        assert str(out.trace_payload["render_spec"]["scene_variant"]) == str(scene_variant)
    assert "y-values" in prompts["area"]
    assert "horizontal axis" in prompts["horizontal_bar"]
    assert "y-values" in prompts["dot_plot"]
    assert "y-values" in prompts["lollipop"]
    assert "percentages" in prompts["pie"]
    assert "legend on the right" in prompts["pie"]
    assert "percentages" in prompts["donut"]
    assert "legend on the right" in prompts["donut"]
    assert "spoke per label" in prompts["radar"]
    assert "printed values near those points" in prompts["radar"]


def test_chart_counting_prompt_examples_match_selected_variant() -> None:
    task = ChartsCountingValueCountTask()
    expected = {
        "above_threshold": {"evidence": ["B", "K", "T"], "answer": 3},
        "below_threshold": {"evidence": ["A", "M"], "answer": 2},
        "in_interval": {"evidence": ["C", "F", "Q"], "answer": 3},
    }
    for index, task_variant in enumerate(expected, start=9930):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_chart_counting_task_is_deterministic() -> None:
    task = ChartsCountingValueCountTask()
    params = {"task_variant": "in_interval", "scene_variant": "scatter"}
    out_a = task.generate(9941, params=params, max_attempts=10)
    out_b = task.generate(9941, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_counting_complexity_is_normalized_and_monotonic() -> None:
    task = ChartsCountingValueCountTask()
    easy = task.generate(
        9942,
        params={"task_variant": "above_threshold", "scene_variant": "bar"},
        max_attempts=10,
    )
    hard = task.generate(
        9942,
        params={"task_variant": "in_interval", "scene_variant": "radar"},
        max_attempts=10,
    )
    _assert_normalized_complexity(easy)
    _assert_normalized_complexity(hard)
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)


def test_chart_counting_supports_zero_answer_with_empty_evidence() -> None:
    task = ChartsCountingValueCountTask()
    for seed, task_variant in enumerate(("above_threshold", "below_threshold", "in_interval"), start=9950):
        out = task.generate(
            seed,
            params={
                "task_variant": task_variant,
                "target_answer_min": 0,
                "target_answer_max": 0,
            },
            max_attempts=10,
        )
        assert int(out.answer_gt.value) == 0
        assert list(out.evidence_gt.value) == []


def test_chart_counting_supports_explicit_mark_count_10() -> None:
    task = ChartsCountingValueCountTask()
    for seed, task_variant in enumerate(("above_threshold", "below_threshold", "in_interval"), start=9960):
        out = task.generate(
            seed,
            params={"task_variant": task_variant, "scene_variant": "bar", "mark_count": 10},
            max_attempts=10,
        )
        assert int(out.trace_payload["execution_trace"]["mark_count"]) == 10

def test_chart_counting_pie_caps_default_mark_count() -> None:
    task = ChartsCountingValueCountTask()
    out = task.generate(9975, params={"task_variant": "above_threshold", "scene_variant": "pie"}, max_attempts=10)
    assert 5 <= int(out.trace_payload["execution_trace"]["mark_count"]) <= 8
    assert sum(int(value) for value in out.trace_payload["execution_trace"]["values"]) == 100
    assert str(out.trace_payload["execution_trace"]["value_semantics"]) == "percentage"


def test_chart_counting_donut_caps_default_mark_count() -> None:
    task = ChartsCountingValueCountTask()
    out = task.generate(9976, params={"task_variant": "above_threshold", "scene_variant": "donut"}, max_attempts=10)
    assert 5 <= int(out.trace_payload["execution_trace"]["mark_count"]) <= 8
    assert sum(int(value) for value in out.trace_payload["execution_trace"]["values"]) == 100
    assert str(out.trace_payload["execution_trace"]["value_semantics"]) == "percentage"


def test_chart_counting_pie_and_donut_use_distinct_slice_colors() -> None:
    task = ChartsCountingValueCountTask()
    for seed, scene_variant in enumerate(("pie", "donut"), start=9977):
        out = task.generate(seed, params={"task_variant": "above_threshold", "scene_variant": scene_variant}, max_attempts=10)
        fill_colors = {
            tuple(int(channel) for channel in entity["attrs"]["mark_fill_rgb"])
            for entity in out.trace_payload["scene_ir"]["entities"]
        }
        assert len(fill_colors) >= 3


def test_chart_counting_radar_caps_default_mark_count() -> None:
    task = ChartsCountingValueCountTask()
    out = task.generate(9980, params={"task_variant": "above_threshold", "scene_variant": "radar"}, max_attempts=10)
    assert 5 <= int(out.trace_payload["execution_trace"]["mark_count"]) <= 7
    assert all("value_center_px" in entity["attrs"] for entity in out.trace_payload["scene_ir"]["entities"])
