"""Behavior tests for chart trend tasks."""

from __future__ import annotations

import json

import pytest

from trace.tasks.charts.trend.structure_value import ChartsTrendStructureValueTask


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


def _step_signs(values: list[int]) -> list[int]:
    return [1 if int(right) > int(left) else -1 for left, right in zip(values[:-1], values[1:])]


def _peak_labels(labels: list[str], values: list[int]) -> list[str]:
    signs = _step_signs(values)
    return sorted(
        str(labels[index + 1])
        for index in range(len(signs) - 1)
        if int(signs[index]) > 0 and int(signs[index + 1]) < 0
    )


def _trough_labels(labels: list[str], values: list[int]) -> list[str]:
    signs = _step_signs(values)
    return sorted(
        str(labels[index + 1])
        for index in range(len(signs) - 1)
        if int(signs[index]) < 0 and int(signs[index + 1]) > 0
    )


def _longest_run_labels(labels: list[str], values: list[int], *, increasing: bool) -> list[str]:
    signs = _step_signs(values)
    target = 1 if bool(increasing) else -1
    runs: list[list[str]] = []
    index = 0
    while int(index) < len(signs):
        if int(signs[index]) != int(target):
            index += 1
            continue
        start = int(index)
        while int(index) + 1 < len(signs) and int(signs[int(index) + 1]) == int(target):
            index += 1
        end = int(index) + 1
        runs.append([str(labels[position]) for position in range(int(start), int(end) + 1)])
        index += 1
    winners = [list(run) for run in runs if len(run) == max(len(candidate) for candidate in runs)]
    assert len(winners) == 1
    return sorted(str(label) for label in winners[0])


def test_chart_trend_variants_match_contract() -> None:
    task = ChartsTrendStructureValueTask()
    cases = (
        ("peak_count", "line"),
        ("trough_count", "area"),
        ("longest_increasing_streak", "bar"),
        ("longest_decreasing_streak", "dot_plot"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=16010):
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        labels = [str(label) for label in execution["labels"]]
        values = [int(value) for value in execution["values"]]
        evidence_labels = [str(label) for label in out.evidence_gt.value]

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
        assert str(trace["query_spec"]["task_variant"]) == str(task_variant)
        assert str(trace["query_spec"]["params"]["scene_variant"]) == str(scene_variant)
        assert len(trace["scene_ir"]["entities"]) == int(execution["mark_count"])
        assert set(str(entity["attrs"]["label"]) for entity in trace["scene_ir"]["entities"]) == set(labels)
        assert set(trace["render_map"]["label_centers_px"].keys()) == set(labels)
        assert len(render["y_ticks"]) == int(render["y_axis_max"]) + 1
        assert all(int(left) != int(right) for left, right in zip(values[:-1], values[1:]))

        if str(task_variant) == "peak_count":
            expected = _peak_labels(labels, values)
        elif str(task_variant) == "trough_count":
            expected = _trough_labels(labels, values)
        elif str(task_variant) == "longest_increasing_streak":
            expected = _longest_run_labels(labels, values, increasing=True)
        else:
            expected = _longest_run_labels(labels, values, increasing=False)
        assert evidence_labels == expected
        assert int(out.answer_gt.value) == int(len(expected))
        assert int(out.answer_gt.value) == int(execution["answer_value"])


def test_chart_trend_prompts_describe_chart_order() -> None:
    task = ChartsTrendStructureValueTask()
    line = task.generate(16021, params={"task_variant": "peak_count", "scene_variant": "line"}, max_attempts=10)
    horizontal = task.generate(16022, params={"task_variant": "peak_count", "scene_variant": "horizontal_bar"}, max_attempts=10)
    dot_plot = task.generate(16023, params={"task_variant": "peak_count", "scene_variant": "dot_plot"}, max_attempts=10)

    assert "displayed order" in str(line.prompt)
    assert "top to bottom" in str(horizontal.prompt)
    assert "left to right" in str(dot_plot.prompt)


def test_chart_trend_supports_all_ordered_scene_variants() -> None:
    task = ChartsTrendStructureValueTask()
    prompts = {}
    for seed, scene_variant in enumerate(("area", "bar", "horizontal_bar", "line", "dot_plot", "lollipop"), start=16024):
        out = task.generate(seed, params={"task_variant": "peak_count", "scene_variant": scene_variant}, max_attempts=10)
        prompts[str(scene_variant)] = str(out.prompt)
        assert str(out.trace_payload["execution_trace"]["scene_variant"]) == str(scene_variant)
        assert str(out.trace_payload["render_spec"]["scene_variant"]) == str(scene_variant)
    assert "left to right" in prompts["area"]
    assert "left to right" in prompts["bar"]
    assert "top to bottom" in prompts["horizontal_bar"]
    assert "left to right" in prompts["line"]
    assert "left to right" in prompts["dot_plot"]
    assert "left to right" in prompts["lollipop"]
    with pytest.raises(ValueError):
        task.generate(16040, params={"task_variant": "peak_count", "scene_variant": "scatter"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(16041, params={"task_variant": "peak_count", "scene_variant": "pie"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(16042, params={"task_variant": "peak_count", "scene_variant": "radar"}, max_attempts=10)


def test_chart_trend_prompt_examples_match_selected_variant() -> None:
    task = ChartsTrendStructureValueTask()
    expected = {
        "peak_count": {"evidence": ["C", "Q"], "answer": 2},
        "trough_count": {"evidence": ["F", "M"], "answer": 2},
        "longest_increasing_streak": {"evidence": ["B", "M", "Q", "T"], "answer": 4},
        "longest_decreasing_streak": {"evidence": ["A", "C", "F"], "answer": 3},
    }
    for index, task_variant in enumerate(expected, start=16050):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_chart_trend_task_is_deterministic() -> None:
    task = ChartsTrendStructureValueTask()
    params = {"task_variant": "longest_increasing_streak", "scene_variant": "line"}
    out_a = task.generate(16061, params=params, max_attempts=10)
    out_b = task.generate(16061, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_trend_complexity_is_normalized_and_monotonic() -> None:
    task = ChartsTrendStructureValueTask()
    easy = task.generate(
        16062,
        params={"task_variant": "peak_count", "scene_variant": "bar", "mark_count": 6},
        max_attempts=10,
    )
    hard = task.generate(
        16062,
        params={"task_variant": "longest_increasing_streak", "scene_variant": "area", "mark_count": 10},
        max_attempts=10,
    )
    _assert_normalized_complexity(easy)
    _assert_normalized_complexity(hard)
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)


def test_chart_trend_supports_zero_turning_point_answers() -> None:
    task = ChartsTrendStructureValueTask()
    for seed, task_variant in enumerate(("peak_count", "trough_count"), start=16070):
        out = task.generate(
            seed,
            params={"task_variant": task_variant, "target_answer_min": 0, "target_answer_max": 0},
            max_attempts=10,
        )
        assert int(out.answer_gt.value) == 0
        assert list(out.evidence_gt.value) == []


def test_chart_trend_supports_explicit_mark_count_10() -> None:
    task = ChartsTrendStructureValueTask()
    for seed, task_variant in enumerate(("peak_count", "trough_count", "longest_increasing_streak", "longest_decreasing_streak"), start=16080):
        out = task.generate(
            seed,
            params={"task_variant": task_variant, "scene_variant": "bar", "mark_count": 10},
            max_attempts=10,
        )
        assert int(out.trace_payload["execution_trace"]["mark_count"]) == 10
