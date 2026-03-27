"""Behavior tests for chart statistics tasks."""

from __future__ import annotations

import json

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

    assert "y-values" in str(line.prompt)
    assert "y-values" in str(scatter.prompt)


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
