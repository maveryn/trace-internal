"""Behavior tests for chart statistics tasks."""

from __future__ import annotations

import json

import pytest

from trace.core.type_registry import load_type_registry
from trace.tasks.charts.statistics.summary_label import ChartsStatisticsSummaryLabelTask
from trace.tasks.charts.statistics.summary_value import ChartsStatisticsSummaryValueTask
from trace.tasks.shared.color_distance import color_distance
from trace.tasks.shared.named_colors import darken_color


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _expected_answer(task_variant: str, values: list[int]) -> int:
    if str(task_variant) == "max":
        return int(max(values))
    if str(task_variant) == "min":
        return int(min(values))
    if str(task_variant) == "range":
        return int(max(values) - min(values))
    if str(task_variant) == "mean":
        return int(sum(values) // len(values))
    if str(task_variant) == "median":
        ordered = sorted(int(value) for value in values)
        return int(ordered[len(ordered) // 2])
    if str(task_variant) == "sum":
        return int(sum(values))
    if str(task_variant) == "mode":
        frequencies = {int(value): int(values.count(value)) for value in set(values)}
        modal_frequency = max(frequencies.values())
        winners = [value for value, frequency in frequencies.items() if int(frequency) == int(modal_frequency)]
        assert len(winners) == 1
        return int(winners[0])
    raise AssertionError(f"unsupported variant: {task_variant}")


def _expected_label(task_variant: str, labels: list[str], values: list[int]) -> str:
    by_label = {str(label): int(value) for label, value in zip(labels, values)}
    if str(task_variant) == "argmax":
        winning_value = int(max(values))
    elif str(task_variant) == "argmin":
        winning_value = int(min(values))
    elif str(task_variant) == "median_label":
        ordered = sorted((int(value), str(label)) for label, value in by_label.items())
        return str(ordered[len(ordered) // 2][1])
    else:
        raise AssertionError(f"unsupported label-answer variant: {task_variant}")
    winners = [str(label) for label, value in by_label.items() if int(value) == int(winning_value)]
    assert len(winners) == 1
    return str(winners[0])


def test_chart_statistics_summary_value_variants_match_contract() -> None:
    task = ChartsStatisticsSummaryValueTask()
    cases = (
        ("max", "bar"),
        ("min", "line"),
        ("range", "scatter"),
        ("mean", "bar"),
        ("median", "line"),
        ("sum", "scatter"),
        ("mode", "bar"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=9100):
        out = task.generate(
            seed,
            params={"task_variant": task_variant, "scene_variant": scene_variant},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "label_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))

        labels = [str(label) for label in execution["labels"]]
        values = [int(value) for value in execution["values"]]
        evidence_labels = [str(label) for label in out.evidence_gt.value]
        assert len(labels) == int(execution["mark_count"])
        assert evidence_labels == sorted(evidence_labels)
        assert trace["projected_evidence"]["label_set"] == evidence_labels
        assert len(trace["projected_evidence"]["bbox_set"]) == len(evidence_labels)
        assert int(out.answer_gt.value) == _expected_answer(str(task_variant), values)
        assert int(out.answer_gt.value) == int(execution["answer_value"])
        assert str(trace["query_spec"]["task_variant"]) == str(task_variant)
        assert str(trace["query_spec"]["params"]["scene_variant"]) == str(scene_variant)
        assert len(trace["scene_ir"]["entities"]) == int(execution["mark_count"])
        assert set(str(entity["attrs"]["label"]) for entity in trace["scene_ir"]["entities"]) == set(labels)
        assert set(trace["render_map"]["label_centers_px"].keys()) == set(labels)
        assert len(render["y_ticks"]) == int(render["y_axis_max"]) + 1

        if str(task_variant) in {"mean", "sum"}:
            assert evidence_labels == sorted(labels)
        elif str(task_variant) == "range":
            evidence_values = sorted(int(execution["values_by_label"][label]) for label in evidence_labels)
            assert evidence_values == [min(values), max(values)]
        elif str(task_variant) == "mode":
            evidence_values = {int(execution["values_by_label"][label]) for label in evidence_labels}
            assert evidence_values == {int(out.answer_gt.value)}
            assert len(evidence_labels) >= 2
        else:
            assert len(evidence_labels) == 1
            assert int(execution["values_by_label"][evidence_labels[0]]) == int(out.answer_gt.value)


def test_chart_statistics_line_and_scatter_prompts_mention_y_values() -> None:
    task = ChartsStatisticsSummaryValueTask()
    line = task.generate(9201, params={"task_variant": "mean", "scene_variant": "line"}, max_attempts=10)
    scatter = task.generate(9202, params={"task_variant": "mean", "scene_variant": "scatter"}, max_attempts=10)
    area = task.generate(9203, params={"task_variant": "mean", "scene_variant": "area"}, max_attempts=10)

    assert "y-values" in str(line.prompt)
    assert "y-values" in str(scatter.prompt)
    assert "y-values" in str(area.prompt)


def test_chart_statistics_supports_additional_scene_variants() -> None:
    task = ChartsStatisticsSummaryValueTask()
    prompts = {}
    for seed, scene_variant in enumerate(("area", "horizontal_bar", "dot_plot", "lollipop"), start=9205):
        out = task.generate(seed, params={"task_variant": "max", "scene_variant": scene_variant}, max_attempts=10)
        prompts[str(scene_variant)] = str(out.prompt)
        assert str(out.trace_payload["execution_trace"]["scene_variant"]) == str(scene_variant)
        assert str(out.trace_payload["render_spec"]["scene_variant"]) == str(scene_variant)
        assert len(out.trace_payload["render_spec"]["y_ticks"]) == int(out.trace_payload["render_spec"]["y_axis_max"]) + 1
    assert "y-values" in prompts["area"]
    assert "horizontal axis" in prompts["horizontal_bar"]
    assert "y-values" in prompts["dot_plot"]
    assert "y-values" in prompts["lollipop"]
    with pytest.raises(ValueError):
        task.generate(9215, params={"task_variant": "max", "scene_variant": "pie"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(9216, params={"task_variant": "max", "scene_variant": "donut"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(9217, params={"task_variant": "max", "scene_variant": "radar"}, max_attempts=10)


def test_chart_statistics_prompt_examples_match_selected_variant() -> None:
    task = ChartsStatisticsSummaryValueTask()
    expected = {
        "max": {"evidence": ["D"], "answer": 8},
        "min": {"evidence": ["B"], "answer": 2},
        "range": {"evidence": ["B", "T"], "answer": 6},
        "mean": {"evidence": ["A", "C", "F", "M", "Q"], "answer": 7},
        "median": {"evidence": ["M"], "answer": 6},
        "sum": {"evidence": ["A", "C", "F", "M", "Q"], "answer": 35},
        "mode": {"evidence": ["B", "E", "K"], "answer": 6},
    }
    for index, task_variant in enumerate(expected, start=9300):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_chart_statistics_task_is_deterministic() -> None:
    task = ChartsStatisticsSummaryValueTask()
    params = {"task_variant": "mode", "scene_variant": "scatter"}
    out_a = task.generate(9401, params=params, max_attempts=10)
    out_b = task.generate(9401, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_statistics_summary_label_variants_match_contract() -> None:
    task = ChartsStatisticsSummaryLabelTask()
    cases = (
        ("argmax", "bar"),
        ("argmin", "line"),
        ("median_label", "scatter"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=9450):
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
        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "integer"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert str(out.answer_gt.value) == _expected_label(str(task_variant), labels, values)
        assert int(out.evidence_gt.value) == int(execution["evidence_value"])
        assert trace["projected_evidence"]["integer"] == int(out.evidence_gt.value)
        assert len(trace["projected_evidence"]["bbox_set"]) == 1
        assert str(trace["query_spec"]["task_variant"]) == str(task_variant)
        assert str(trace["query_spec"]["params"]["scene_variant"]) == str(scene_variant)
        assert len(trace["scene_ir"]["entities"]) == int(execution["mark_count"])
        assert set(str(entity["attrs"]["label"]) for entity in trace["scene_ir"]["entities"]) == set(labels)
        assert set(trace["render_map"]["label_centers_px"].keys()) == set(labels)
        assert len(render["y_ticks"]) == int(render["y_axis_max"]) + 1

        if str(task_variant) == "argmax":
            assert int(out.evidence_gt.value) == int(max(values))
        elif str(task_variant) == "argmin":
            assert int(out.evidence_gt.value) == int(min(values))
        else:
            ordered_values = sorted(int(value) for value in values)
            assert int(out.evidence_gt.value) == int(ordered_values[len(ordered_values) // 2])


def test_chart_statistics_summary_label_prompt_examples_match_selected_variant() -> None:
    task = ChartsStatisticsSummaryLabelTask()
    expected = {
        "argmax": {"evidence": 8, "answer": "D"},
        "argmin": {"evidence": 2, "answer": "B"},
        "median_label": {"evidence": 6, "answer": "M"},
    }
    for index, task_variant in enumerate(expected, start=9550):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_chart_statistics_summary_label_task_is_deterministic() -> None:
    task = ChartsStatisticsSummaryLabelTask()
    params = {"task_variant": "median_label", "scene_variant": "scatter"}
    out_a = task.generate(9651, params=params, max_attempts=10)
    out_b = task.generate(9651, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_statistics_summary_label_supports_additional_scene_variants() -> None:
    task = ChartsStatisticsSummaryLabelTask()
    prompts = {}
    for seed, scene_variant in enumerate(("area", "horizontal_bar", "dot_plot", "lollipop", "pie", "donut", "radar"), start=9660):
        out = task.generate(
            seed,
            params={"task_variant": "argmax", "scene_variant": scene_variant},
            max_attempts=10,
        )
        prompts[str(scene_variant)] = str(out.prompt)
        assert str(out.trace_payload["execution_trace"]["scene_variant"]) == str(scene_variant)
        assert str(out.trace_payload["render_spec"]["scene_variant"]) == str(scene_variant)
    assert "y-values" in prompts["area"]
    assert "percentages" in prompts["pie"]
    assert "legend on the right" in prompts["pie"]
    assert "percentages" in prompts["donut"]
    assert "legend on the right" in prompts["donut"]
    assert "spoke per label" in prompts["radar"]
    assert "printed values near those points" in prompts["radar"]


def test_chart_statistics_summary_label_pie_caps_default_mark_count() -> None:
    task = ChartsStatisticsSummaryLabelTask()
    out = task.generate(9675, params={"task_variant": "argmax", "scene_variant": "pie"}, max_attempts=10)
    assert 5 <= int(out.trace_payload["execution_trace"]["mark_count"]) <= 8
    assert sum(int(value) for value in out.trace_payload["execution_trace"]["values"]) == 100


def test_chart_statistics_summary_label_donut_caps_default_mark_count() -> None:
    task = ChartsStatisticsSummaryLabelTask()
    out = task.generate(9676, params={"task_variant": "argmax", "scene_variant": "donut"}, max_attempts=10)
    assert 5 <= int(out.trace_payload["execution_trace"]["mark_count"]) <= 8
    assert sum(int(value) for value in out.trace_payload["execution_trace"]["values"]) == 100


def test_chart_statistics_pie_and_donut_use_distinct_slice_colors_and_legend() -> None:
    task = ChartsStatisticsSummaryLabelTask()
    for seed, scene_variant in enumerate(("pie", "donut"), start=9685):
        out = task.generate(seed, params={"task_variant": "argmax", "scene_variant": scene_variant}, max_attempts=10)
        render_spec = out.trace_payload["render_spec"]
        entities = out.trace_payload["scene_ir"]["entities"]
        fill_colors = {tuple(int(channel) for channel in entity["attrs"]["mark_fill_rgb"]) for entity in entities}
        assert len(fill_colors) >= 3
        assert all("legend_swatch_bbox_px" in entity["attrs"] for entity in entities)
        assert all("percentage_center_px" in entity["attrs"] for entity in entities)
        assert float(render_spec["mark_style"]["mark_color_min_distance"]) >= 58.0
        assert int(render_spec["mark_style"]["pie_like_mark_color_channel_max"]) <= 200
        assert all(
            float(entity["attrs"]["legend_swatch_bbox_px"][2]) - float(entity["attrs"]["legend_swatch_bbox_px"][0]) >= 28.0
            for entity in entities
        )


def test_chart_statistics_summary_label_radar_caps_default_mark_count() -> None:
    task = ChartsStatisticsSummaryLabelTask()
    out = task.generate(9688, params={"task_variant": "argmax", "scene_variant": "radar"}, max_attempts=10)
    assert 5 <= int(out.trace_payload["execution_trace"]["mark_count"]) <= 7
    assert all("value_center_px" in entity["attrs"] for entity in out.trace_payload["scene_ir"]["entities"])


def test_integer_evidence_type_is_registered_for_chart_label_tasks() -> None:
    registry = load_type_registry()
    assert registry.validate_evidence_type("integer") is True


def test_chart_statistics_labels_use_random_uppercase_subset() -> None:
    task = ChartsStatisticsSummaryValueTask()
    out = task.generate(
        9100,
        params={"task_variant": "max", "scene_variant": "bar"},
        max_attempts=10,
    )

    labels = [str(label) for label in out.trace_payload["execution_trace"]["labels"]]
    assert len(labels) >= 5
    assert len(labels) == len(set(labels))
    assert all(label.isalpha() and label.isupper() for label in labels)
    assert set(labels) != set(["A", "B", "C", "D", "E"])


def test_chart_statistics_supports_explicit_mark_count_10() -> None:
    task = ChartsStatisticsSummaryValueTask()

    for seed, task_variant in enumerate(("max", "mean", "mode", "sum"), start=9500):
        out = task.generate(
            seed,
            params={"task_variant": task_variant, "scene_variant": "bar", "mark_count": 10},
            max_attempts=10,
        )
        assert int(out.trace_payload["execution_trace"]["mark_count"]) == 10


def test_chart_statistics_median_supports_mark_count_9() -> None:
    task = ChartsStatisticsSummaryValueTask()
    out = task.generate(
        9601,
        params={"task_variant": "median", "scene_variant": "line", "mark_count": 9},
        max_attempts=10,
    )

    assert int(out.trace_payload["execution_trace"]["mark_count"]) == 9


def test_chart_statistics_mark_color_is_randomized_and_traced() -> None:
    task = ChartsStatisticsSummaryValueTask()

    observed_colors = set()
    for seed in range(9700, 9708):
        out = task.generate(
            seed,
            params={"task_variant": "max", "scene_variant": "bar"},
            max_attempts=10,
        )
        render_spec = out.trace_payload["render_spec"]
        execution = out.trace_payload["execution_trace"]
        fill_rgb = tuple(int(channel) for channel in render_spec["mark_style"]["mark_fill_rgb"])
        outline_rgb = tuple(int(channel) for channel in render_spec["mark_style"]["mark_outline_rgb"])

        assert render_spec["mark_style"]["sampling_policy"] == "random_rgb"
        assert outline_rgb == darken_color(fill_rgb, factor=0.55)
        assert float(render_spec["mark_style"]["mark_color_min_distance"]) == 40.0
        assert str(render_spec["mark_style"]["mark_color_distance_space"]) == "lab"
        assert float(color_distance(fill_rgb, (255, 255, 255), distance_space="lab")) >= 40.0
        assert float(color_distance(fill_rgb, (248, 248, 248), distance_space="lab")) >= 40.0
        assert execution["mark_color_sampling_policy"] == "random_rgb"
        assert tuple(int(channel) for channel in execution["mark_fill_rgb"]) == fill_rgb
        assert tuple(int(channel) for channel in execution["mark_outline_rgb"]) == outline_rgb
        observed_colors.add(fill_rgb)

    assert len(observed_colors) >= 2


def test_chart_statistics_render_uses_traced_mark_fill_color() -> None:
    task = ChartsStatisticsSummaryValueTask()
    out = task.generate(
        9801,
        params={"task_variant": "max", "scene_variant": "bar"},
        max_attempts=10,
    )

    fill_rgb = tuple(int(channel) for channel in out.trace_payload["render_spec"]["mark_style"]["mark_fill_rgb"])
    first_entity = out.trace_payload["scene_ir"]["entities"][0]
    left, top, right, bottom = first_entity["attrs"]["mark_bbox_px"]
    sample_x = int(round((float(left) + float(right)) / 2.0))
    sample_y = int(round(float(top) + 0.7 * (float(bottom) - float(top))))
    pixel = tuple(int(channel) for channel in out.image.convert("RGB").getpixel((sample_x, sample_y)))

    assert pixel == fill_rgb
