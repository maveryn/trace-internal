"""Behavior tests for chart statistics tasks."""

from __future__ import annotations

import json

import pytest

from trace.core.type_registry import load_type_registry
from trace.tasks.charts.statistics.summary_query import ChartsStatisticsSummaryQueryTask
from trace.tasks.shared.color_distance import color_distance
from trace.tasks.shared.named_colors import darken_color


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _expected_answer(statistic_kind: str, values: list[int], *, rank_n: int | None = None) -> int:
    if str(statistic_kind) == "median":
        ordered = sorted(int(value) for value in values)
        return int(ordered[len(ordered) // 2])
    if str(statistic_kind) == "nth_highest":
        assert rank_n is not None
        return int(sorted(set(int(value) for value in values), reverse=True)[int(rank_n) - 1])
    if str(statistic_kind) == "nth_lowest":
        assert rank_n is not None
        return int(sorted(set(int(value) for value in values))[int(rank_n) - 1])
    raise AssertionError(f"unsupported statistic: {statistic_kind}")


def _expected_label(statistic_kind: str, labels: list[str], values: list[int], *, rank_n: int | None = None) -> str:
    by_label = {str(label): int(value) for label, value in zip(labels, values)}
    if str(statistic_kind) == "median":
        ordered = sorted((int(value), str(label)) for label, value in by_label.items())
        return str(ordered[len(ordered) // 2][1])
    if str(statistic_kind) == "nth_highest":
        assert rank_n is not None
        winning_value = sorted(set(int(value) for value in values), reverse=True)[int(rank_n) - 1]
    elif str(statistic_kind) == "nth_lowest":
        assert rank_n is not None
        winning_value = sorted(set(int(value) for value in values))[int(rank_n) - 1]
    else:
        raise AssertionError(f"unsupported label-answer statistic: {statistic_kind}")
    winners = [str(label) for label, value in by_label.items() if int(value) == int(winning_value)]
    assert len(winners) == 1
    return str(winners[0])


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


def _assert_value_axis_covers_values(render: dict, values: list[int]) -> None:
    assert bool(render["value_axis_window_enabled"]) is True
    assert int(render["value_axis_min"]) <= min(int(value) for value in values)
    assert max(int(value) for value in values) <= int(render["value_axis_max"])
    assert 1 <= int(render["value_axis_span"]) <= 25
    assert set(int(value) for value in render["y_ticks"]).issubset(
        set(int(value) for value in render["value_axis_minor_ticks"])
    )
    assert render["guide_line_style"] in {"dashed", "dotted", "solid"}
    assert len(render["guide_lines"]) == int(len(values))


def test_chart_statistics_summary_query_value_variants_match_contract() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    cases = (
        ("median", "line"),
        ("nth_highest", "bar"),
        ("nth_lowest", "scatter"),
    )
    for seed, (statistic_kind, scene_variant) in enumerate(cases, start=9100):
        query_id = "order_statistic_value"
        out = task.generate(
            seed,
            params={"query_id": query_id, "statistic_kind": statistic_kind, "scene_variant": scene_variant},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        assert str(out.query_id) == str(query_id)
        assert str(execution["statistic_kind"]) == str(statistic_kind)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "point_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))

        labels = [str(label) for label in execution["labels"]]
        values = [int(value) for value in execution["values"]]
        evidence_points = [list(point) for point in out.evidence_gt.value]
        evidence_labels = [str(label) for label in execution["evidence_labels"]]
        assert len(labels) == int(execution["mark_count"])
        assert evidence_labels == sorted(evidence_labels)
        assert trace["projected_evidence"]["point_set"] == evidence_points
        assert trace["projected_evidence"]["pixel_point_set"] == evidence_points
        assert len(trace["projected_evidence"]["bbox_set"]) == len(evidence_labels)
        assert int(out.answer_gt.value) == _expected_answer(
            str(statistic_kind),
            values,
            rank_n=int(execution["rank_n"]) if "rank_n" in execution else None,
        )
        assert int(out.answer_gt.value) == int(execution["answer_value"])
        assert str(trace["query_spec"]["query_id"]) == str(query_id)
        assert str(trace["query_spec"]["params"]["scene_variant"]) == str(scene_variant)
        assert len(trace["scene_ir"]["entities"]) == int(execution["mark_count"])
        assert set(str(entity["attrs"]["label"]) for entity in trace["scene_ir"]["entities"]) == set(labels)
        assert set(trace["render_map"]["label_centers_px"].keys()) == set(labels)
        _assert_value_axis_covers_values(render, values)

        assert len(evidence_labels) == 1
        assert len(evidence_points) == 1
        assert int(execution["values_by_label"][evidence_labels[0]]) == int(out.answer_gt.value)
        if str(statistic_kind) == "nth_highest":
            assert int(execution["rank_n"]) >= 3
            assert str(execution["rank_direction"]) == "highest"
        elif str(statistic_kind) == "nth_lowest":
            assert int(execution["rank_n"]) >= 3
            assert str(execution["rank_direction"]) == "lowest"


def test_chart_statistics_line_and_scatter_prompts_mention_y_values() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    params = {"query_id": "order_statistic_value", "statistic_kind": "median"}
    line = task.generate(9201, params={**params, "scene_variant": "line"}, max_attempts=10)
    scatter = task.generate(9202, params={**params, "scene_variant": "scatter"}, max_attempts=10)
    area = task.generate(9203, params={**params, "scene_variant": "area"}, max_attempts=10)

    assert "y-values" in str(line.prompt)
    assert "y-values" in str(scatter.prompt)
    assert "y-values" in str(area.prompt)


def test_chart_statistics_supports_additional_scene_variants() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    prompts = {}
    for seed, scene_variant in enumerate(("area", "horizontal_bar", "dot_plot", "lollipop"), start=9205):
        out = task.generate(
            seed,
            params={"query_id": "order_statistic_value", "statistic_kind": "nth_highest", "scene_variant": scene_variant},
            max_attempts=10,
        )
        prompts[str(scene_variant)] = str(out.prompt)
        assert str(out.trace_payload["execution_trace"]["scene_variant"]) == str(scene_variant)
        assert str(out.trace_payload["render_spec"]["scene_variant"]) == str(scene_variant)
        _assert_value_axis_covers_values(
            out.trace_payload["render_spec"],
            [int(value) for value in out.trace_payload["execution_trace"]["values"]],
        )
    assert "y-values" in prompts["area"]
    assert "horizontal axis" in prompts["horizontal_bar"]
    assert "y-values" in prompts["dot_plot"]
    assert "y-values" in prompts["lollipop"]
    with pytest.raises(ValueError):
        task.generate(9215, params={"query_id": "order_statistic_value", "statistic_kind": "nth_highest", "scene_variant": "pie"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(9216, params={"query_id": "order_statistic_value", "statistic_kind": "nth_highest", "scene_variant": "donut"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(9217, params={"query_id": "order_statistic_value", "statistic_kind": "nth_highest", "scene_variant": "radar"}, max_attempts=10)


def test_chart_statistics_prompt_examples_match_selected_variant() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    expected = {
        "median": {"evidence": [[300, 240]], "answer": 6},
        "nth_highest": {"evidence": [[420, 180]], "answer": 7},
        "nth_lowest": {"evidence": [[260, 360]], "answer": 4},
    }
    for index, statistic_kind in enumerate(expected, start=9300):
        out = task.generate(
            index,
            params={"query_id": "order_statistic_value", "statistic_kind": statistic_kind},
            max_attempts=10,
        )
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[statistic_kind]
        assert answer_only == {"answer": expected[statistic_kind]["answer"]}


def test_chart_statistics_task_is_deterministic() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    params = {"query_id": "order_statistic_value", "statistic_kind": "nth_lowest", "scene_variant": "scatter"}
    out_a = task.generate(9401, params=params, max_attempts=10)
    out_b = task.generate(9401, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_statistics_complexity_is_normalized_and_monotonic() -> None:
    value_task = ChartsStatisticsSummaryQueryTask()
    easy_value = value_task.generate(
        9440,
        params={"query_id": "order_statistic_value", "statistic_kind": "median", "scene_variant": "bar"},
        max_attempts=10,
    )
    hard_value = value_task.generate(
        9440,
        params={"query_id": "order_statistic_value", "statistic_kind": "nth_highest", "scene_variant": "scatter"},
        max_attempts=10,
    )
    _assert_normalized_complexity(easy_value)
    _assert_normalized_complexity(hard_value)
    assert float(hard_value.complexity.complexity_score) > float(easy_value.complexity.complexity_score)

    label_task = ChartsStatisticsSummaryQueryTask()
    easy_label = label_task.generate(
        9441,
        params={"query_id": "order_statistic_label", "statistic_kind": "median", "scene_variant": "bar"},
        max_attempts=10,
    )
    hard_label = label_task.generate(
        9441,
        params={"query_id": "order_statistic_label", "statistic_kind": "nth_highest", "scene_variant": "scatter"},
        max_attempts=10,
    )
    _assert_normalized_complexity(easy_label)
    _assert_normalized_complexity(hard_label)
    assert float(hard_label.complexity.complexity_score) > float(easy_label.complexity.complexity_score)


def test_chart_statistics_summary_query_label_variants_match_contract() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    cases = (
        ("nth_highest", "bar"),
        ("nth_lowest", "line"),
        ("median", "scatter"),
    )
    for seed, (statistic_kind, scene_variant) in enumerate(cases, start=9450):
        query_id = "order_statistic_label"
        out = task.generate(
            seed,
            params={"query_id": query_id, "statistic_kind": statistic_kind, "scene_variant": scene_variant},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        labels = [str(label) for label in execution["labels"]]
        values = [int(value) for value in execution["values"]]
        assert str(out.query_id) == str(query_id)
        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "point_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        rank_n = execution.get("rank_n", None)
        assert str(out.answer_gt.value) == _expected_label(
            str(statistic_kind),
            labels,
            values,
            rank_n=int(rank_n) if rank_n is not None else None,
        )
        evidence_points = [list(point) for point in out.evidence_gt.value]
        assert trace["projected_evidence"]["point_set"] == evidence_points
        assert trace["projected_evidence"]["pixel_point_set"] == evidence_points
        assert len(trace["projected_evidence"]["bbox_set"]) == 1
        assert str(trace["query_spec"]["query_id"]) == str(query_id)
        assert str(trace["query_spec"]["params"]["scene_variant"]) == str(scene_variant)
        assert len(trace["scene_ir"]["entities"]) == int(execution["mark_count"])
        assert set(str(entity["attrs"]["label"]) for entity in trace["scene_ir"]["entities"]) == set(labels)
        assert set(trace["render_map"]["label_centers_px"].keys()) == set(labels)
        _assert_value_axis_covers_values(render, values)

        if str(statistic_kind) == "median":
            ordered_values = sorted(int(value) for value in values)
            assert int(execution["evidence_value"]) == int(ordered_values[len(ordered_values) // 2])
        elif str(statistic_kind) == "nth_highest":
            unique_values = sorted(set(int(value) for value in values), reverse=True)
            assert int(execution["rank_n"]) >= 3
            assert int(execution["evidence_value"]) == int(unique_values[int(execution["rank_n"]) - 1])
            assert str(execution["rank_direction"]) == "highest"
        else:
            unique_values = sorted(set(int(value) for value in values))
            assert int(execution["rank_n"]) >= 3
            assert int(execution["evidence_value"]) == int(unique_values[int(execution["rank_n"]) - 1])
            assert str(execution["rank_direction"]) == "lowest"


def test_chart_statistics_summary_query_label_prompt_examples_match_selected_variant() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    expected = {
        "median": {"evidence": [[300, 240]], "answer": "M"},
        "nth_highest": {"evidence": [[420, 180]], "answer": "K"},
        "nth_lowest": {"evidence": [[260, 360]], "answer": "R"},
    }
    for index, statistic_kind in enumerate(expected, start=9550):
        out = task.generate(
            index,
            params={"query_id": "order_statistic_label", "statistic_kind": statistic_kind},
            max_attempts=10,
        )
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[statistic_kind]
        assert answer_only == {"answer": expected[statistic_kind]["answer"]}


def test_chart_statistics_summary_query_label_task_is_deterministic() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    params = {"query_id": "order_statistic_label", "statistic_kind": "median", "scene_variant": "scatter"}
    out_a = task.generate(9651, params=params, max_attempts=10)
    out_b = task.generate(9651, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_statistics_summary_query_label_supports_additional_scene_variants() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    prompts = {}
    for seed, scene_variant in enumerate(("area", "horizontal_bar", "dot_plot", "lollipop"), start=9660):
        out = task.generate(
            seed,
            params={"query_id": "order_statistic_label", "statistic_kind": "nth_highest", "scene_variant": scene_variant},
            max_attempts=10,
        )
        prompts[str(scene_variant)] = str(out.prompt)
        assert str(out.trace_payload["execution_trace"]["scene_variant"]) == str(scene_variant)
        assert str(out.trace_payload["render_spec"]["scene_variant"]) == str(scene_variant)
    assert "y-values" in prompts["area"]
    assert "horizontal axis" in prompts["horizontal_bar"]
    assert "y-values" in prompts["dot_plot"]
    assert "y-values" in prompts["lollipop"]
    with pytest.raises(ValueError):
        task.generate(9672, params={"query_id": "order_statistic_label", "statistic_kind": "nth_highest", "scene_variant": "pie"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(9673, params={"query_id": "order_statistic_label", "statistic_kind": "nth_highest", "scene_variant": "donut"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(9674, params={"query_id": "order_statistic_label", "statistic_kind": "nth_highest", "scene_variant": "radar"}, max_attempts=10)


def test_chart_statistics_summary_query_label_default_mark_count_range_is_15_to_25() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    out = task.generate(9675, params={"query_id": "order_statistic_label", "statistic_kind": "nth_lowest", "scene_variant": "bar"}, max_attempts=10)
    assert 15 <= int(out.trace_payload["execution_trace"]["mark_count"]) <= 25


def test_chart_statistics_summary_query_label_supports_explicit_mark_count_25() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    out = task.generate(
        9676,
        params={"query_id": "order_statistic_label", "statistic_kind": "nth_highest", "scene_variant": "bar", "mark_count": 25},
        max_attempts=10,
    )
    assert int(out.trace_payload["execution_trace"]["mark_count"]) == 25
    assert 3 <= int(out.trace_payload["execution_trace"]["rank_n"]) <= 8


def test_chart_statistics_summary_query_label_rejects_pie_and_donut() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    with pytest.raises(ValueError):
        task.generate(9685, params={"query_id": "order_statistic_label", "statistic_kind": "nth_highest", "scene_variant": "pie"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(9686, params={"query_id": "order_statistic_label", "statistic_kind": "nth_lowest", "scene_variant": "donut"}, max_attempts=10)


def test_chart_statistics_summary_query_label_rejects_radar() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    with pytest.raises(ValueError):
        task.generate(9688, params={"query_id": "order_statistic_label", "statistic_kind": "nth_highest", "scene_variant": "radar"}, max_attempts=10)


def test_chart_statistics_summary_query_label_rejects_removed_extremum_variants() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    with pytest.raises(ValueError):
        task.generate(9690, params={"query_id": "argmax", "scene_variant": "bar"}, max_attempts=10)
    with pytest.raises(ValueError):
        task.generate(9691, params={"query_id": "argmin", "scene_variant": "bar"}, max_attempts=10)


def test_point_set_evidence_type_is_registered_for_chart_label_tasks() -> None:
    registry = load_type_registry()
    assert registry.validate_evidence_type("point_set") is True


def test_chart_statistics_labels_use_random_uppercase_subset() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    out = task.generate(
        9100,
        params={"query_id": "order_statistic_value", "statistic_kind": "median", "scene_variant": "bar"},
        max_attempts=10,
    )

    labels = [str(label) for label in out.trace_payload["execution_trace"]["labels"]]
    assert len(labels) >= 10
    assert len(labels) == len(set(labels))
    assert all(label.isalpha() and label.isupper() for label in labels)
    assert set(labels) != set(["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"])


def test_chart_statistics_rank_supports_explicit_mark_count_15() -> None:
    task = ChartsStatisticsSummaryQueryTask()

    for seed, statistic_kind in enumerate(("nth_highest", "nth_lowest"), start=9500):
        out = task.generate(
            seed,
            params={"query_id": "order_statistic_value", "statistic_kind": statistic_kind, "scene_variant": "bar", "mark_count": 15},
            max_attempts=10,
        )
        assert int(out.trace_payload["execution_trace"]["mark_count"]) == 15


def test_chart_statistics_median_supports_mark_count_25() -> None:
    task = ChartsStatisticsSummaryQueryTask()
    out = task.generate(
        9601,
        params={"query_id": "order_statistic_value", "statistic_kind": "median", "scene_variant": "line", "mark_count": 25},
        max_attempts=10,
    )

    assert int(out.trace_payload["execution_trace"]["mark_count"]) == 25


def test_chart_statistics_mark_color_is_randomized_and_traced() -> None:
    task = ChartsStatisticsSummaryQueryTask()

    observed_colors = set()
    for seed in range(9700, 9708):
        out = task.generate(
            seed,
            params={"query_id": "order_statistic_value", "statistic_kind": "median", "scene_variant": "bar"},
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
    task = ChartsStatisticsSummaryQueryTask()
    out = task.generate(
        9801,
        params={"query_id": "order_statistic_value", "statistic_kind": "median", "scene_variant": "bar"},
        max_attempts=10,
    )

    fill_rgb = tuple(int(channel) for channel in out.trace_payload["render_spec"]["mark_style"]["mark_fill_rgb"])
    first_entity = out.trace_payload["scene_ir"]["entities"][0]
    left, top, right, bottom = first_entity["attrs"]["mark_bbox_px"]
    sample_x = int(round((float(left) + float(right)) / 2.0))
    sample_y = int(round(float(top) + 0.7 * (float(bottom) - float(top))))
    pixel = tuple(int(channel) for channel in out.image.convert("RGB").getpixel((sample_x, sample_y)))

    assert pixel == fill_rgb
