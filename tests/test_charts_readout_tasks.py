"""Behavior tests for chart readout tasks."""

from __future__ import annotations

import json

from trace.core.type_registry import load_type_registry
from trace.tasks.charts.readout.subset_value import ChartsReadoutSubsetValueTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _expected_answer(task_variant: str, evidence_values: list[int]) -> int:
    if str(task_variant) == "sum_two":
        return int(sum(evidence_values))
    if str(task_variant) == "difference_two_abs":
        return int(abs(int(evidence_values[0]) - int(evidence_values[1])))
    if str(task_variant) == "max_two":
        return int(max(evidence_values))
    if str(task_variant) == "min_two":
        return int(min(evidence_values))
    if str(task_variant) == "mean_two":
        return int(sum(evidence_values) // 2)
    raise AssertionError(f"unsupported variant: {task_variant}")


def test_chart_readout_variants_match_contract() -> None:
    task = ChartsReadoutSubsetValueTask()
    cases = (
        ("sum_two", "bar"),
        ("difference_two_abs", "line"),
        ("max_two", "scatter"),
        ("min_two", "bar"),
        ("mean_two", "line"),
    )
    for seed, (task_variant, scene_variant) in enumerate(cases, start=10010):
        out = task.generate(
            seed,
            params={"task_variant": task_variant, "scene_variant": scene_variant},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        labels = [str(label) for label in execution["labels"]]
        query_labels = [str(label) for label in execution["query_labels"]]
        evidence_values = [int(value) for value in out.evidence_gt.value]
        values_by_label = {str(label): int(value) for label, value in execution["values_by_label"].items()}

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "integer_list"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert len(query_labels) == 2
        assert len(evidence_values) == 2
        assert len(trace["scene_ir"]["entities"]) == int(execution["mark_count"])
        assert set(str(entity["attrs"]["label"]) for entity in trace["scene_ir"]["entities"]) == set(labels)
        assert set(trace["render_map"]["label_centers_px"].keys()) == set(labels)
        assert trace["projected_evidence"]["integer_list"] == evidence_values
        assert len(trace["projected_evidence"]["bbox_set"]) == len(query_labels)
        assert evidence_values == [int(values_by_label[label]) for label in query_labels]
        assert int(out.answer_gt.value) == int(execution["answer_value"])
        assert int(out.answer_gt.value) == _expected_answer(str(task_variant), evidence_values)
        assert str(trace["query_spec"]["task_variant"]) == str(task_variant)
        assert str(trace["query_spec"]["params"]["scene_variant"]) == str(scene_variant)


def test_chart_readout_line_and_scatter_prompts_mention_y_values() -> None:
    task = ChartsReadoutSubsetValueTask()
    line = task.generate(10031, params={"task_variant": "sum_two", "scene_variant": "line"}, max_attempts=10)
    scatter = task.generate(10032, params={"task_variant": "min_two", "scene_variant": "scatter"}, max_attempts=10)
    area = task.generate(10033, params={"task_variant": "sum_two", "scene_variant": "area"}, max_attempts=10)

    assert "y-values" in str(line.prompt)
    assert "y-values" in str(scatter.prompt)
    assert "y-values" in str(area.prompt)


def test_chart_readout_supports_additional_scene_variants() -> None:
    task = ChartsReadoutSubsetValueTask()
    prompts = {}
    for seed, scene_variant in enumerate(("area", "horizontal_bar", "dot_plot", "lollipop", "pie", "donut", "radar"), start=10034):
        out = task.generate(
            seed,
            params={"task_variant": "sum_two", "scene_variant": scene_variant},
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


def test_chart_readout_prompt_examples_match_selected_variant() -> None:
    task = ChartsReadoutSubsetValueTask()
    expected = {
        "sum_two": {"evidence": [7, 11], "answer": 18},
        "difference_two_abs": {"evidence": [14, 9], "answer": 5},
        "max_two": {"evidence": [6, 13], "answer": 13},
        "min_two": {"evidence": [6, 13], "answer": 6},
        "mean_two": {"evidence": [6, 10], "answer": 8},
    }
    for index, task_variant in enumerate(expected, start=10040):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_chart_readout_task_is_deterministic() -> None:
    task = ChartsReadoutSubsetValueTask()
    params = {"task_variant": "difference_two_abs", "scene_variant": "scatter"}
    out_a = task.generate(10051, params=params, max_attempts=10)
    out_b = task.generate(10051, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_readout_supports_explicit_mark_count_10() -> None:
    task = ChartsReadoutSubsetValueTask()
    for seed, task_variant in enumerate(("sum_two", "difference_two_abs", "max_two", "min_two", "mean_two"), start=10060):
        out = task.generate(
            seed,
            params={"task_variant": task_variant, "scene_variant": "bar", "mark_count": 10},
            max_attempts=10,
        )
        assert int(out.trace_payload["execution_trace"]["mark_count"]) == 10


def test_chart_readout_pie_caps_default_mark_count() -> None:
    task = ChartsReadoutSubsetValueTask()
    out = task.generate(10090, params={"task_variant": "sum_two", "scene_variant": "pie"}, max_attempts=10)
    assert 5 <= int(out.trace_payload["execution_trace"]["mark_count"]) <= 8
    assert sum(int(value) for value in out.trace_payload["execution_trace"]["values"]) == 100
    assert str(out.trace_payload["execution_trace"]["value_semantics"]) == "percentage"


def test_chart_readout_donut_caps_default_mark_count() -> None:
    task = ChartsReadoutSubsetValueTask()
    out = task.generate(10091, params={"task_variant": "sum_two", "scene_variant": "donut"}, max_attempts=10)
    assert 5 <= int(out.trace_payload["execution_trace"]["mark_count"]) <= 8
    assert sum(int(value) for value in out.trace_payload["execution_trace"]["values"]) == 100
    assert str(out.trace_payload["execution_trace"]["value_semantics"]) == "percentage"


def test_chart_readout_pie_and_donut_use_distinct_slice_colors() -> None:
    task = ChartsReadoutSubsetValueTask()
    for seed, scene_variant in enumerate(("pie", "donut"), start=10092):
        out = task.generate(seed, params={"task_variant": "sum_two", "scene_variant": scene_variant}, max_attempts=10)
        fill_colors = {
            tuple(int(channel) for channel in entity["attrs"]["mark_fill_rgb"])
            for entity in out.trace_payload["scene_ir"]["entities"]
        }
        assert len(fill_colors) >= 3


def test_chart_readout_radar_caps_default_mark_count() -> None:
    task = ChartsReadoutSubsetValueTask()
    out = task.generate(10094, params={"task_variant": "sum_two", "scene_variant": "radar"}, max_attempts=10)
    assert 5 <= int(out.trace_payload["execution_trace"]["mark_count"]) <= 7
    assert all("value_center_px" in entity["attrs"] for entity in out.trace_payload["scene_ir"]["entities"])


def test_chart_readout_registers_integer_list_evidence() -> None:
    registry = load_type_registry()
    assert registry.validate_evidence_type("integer_list") is True
