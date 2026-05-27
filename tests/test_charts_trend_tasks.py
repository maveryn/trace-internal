"""Behavior tests for chart trend tasks."""

from __future__ import annotations

import json

import pytest

from trace.tasks.charts.trend.value import ChartsTrendValueTask


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


def _assert_value_axis_covers_values(render: dict, values: list[int]) -> None:
    assert int(render["value_axis_min"]) <= min(int(value) for value in values)
    assert max(int(value) for value in values) <= int(render["value_axis_max"])
    assert int(render["value_axis_span"]) == int(render["value_axis_max"]) - int(render["value_axis_min"])
    assert set(int(value) for value in render["y_ticks"]).issubset(
        set(int(value) for value in render["value_axis_minor_ticks"])
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
    task = ChartsTrendValueTask()
    cases = (
        ("turning_point_count", "line", {"turning_point_type": "peak"}),
        ("turning_point_count", "area", {"turning_point_type": "trough"}),
        ("longest_monotone_streak", "bar", {"streak_direction": "increasing"}),
        ("longest_monotone_streak", "dot_plot", {"streak_direction": "decreasing"}),
    )
    for seed, (query_variant, scene_variant, extra_params) in enumerate(cases, start=16010):
        out = task.generate(
            seed,
            params={"query_variant": query_variant, "scene_variant": scene_variant, **extra_params},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        labels = [str(label) for label in execution["labels"]]
        values = [int(value) for value in execution["values"]]
        evidence_labels = [str(label) for label in execution["evidence_labels"]]
        evidence_points = [list(point) for point in out.evidence_gt.value]

        assert str(out.query_variant) == str(query_variant)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "point_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert evidence_labels == sorted(evidence_labels)
        assert trace["projected_evidence"]["point_set"] == evidence_points
        assert "label_set" not in trace["projected_evidence"]
        assert len(evidence_points) == len(evidence_labels)
        assert len(trace["projected_evidence"]["bbox_set"]) == len(evidence_labels)
        for x_coord, y_coord in evidence_points:
            assert 0 <= float(x_coord) <= int(render["canvas_width"])
            assert 0 <= float(y_coord) <= int(render["canvas_height"])
        assert str(trace["query_spec"]["query_variant"]) == str(query_variant)
        assert str(trace["query_spec"]["params"]["scene_variant"]) == str(scene_variant)
        assert len(trace["scene_ir"]["entities"]) == int(execution["mark_count"])
        assert set(str(entity["attrs"]["label"]) for entity in trace["scene_ir"]["entities"]) == set(labels)
        assert set(trace["render_map"]["label_centers_px"].keys()) == set(labels)
        _assert_value_axis_covers_values(render, values)
        assert all(int(left) != int(right) for left, right in zip(values[:-1], values[1:]))

        if str(query_variant) == "turning_point_count" and str(execution["turning_point_type"]) == "peak":
            expected = _peak_labels(labels, values)
        elif str(query_variant) == "turning_point_count" and str(execution["turning_point_type"]) == "trough":
            expected = _trough_labels(labels, values)
        elif str(query_variant) == "longest_monotone_streak" and str(execution["streak_direction"]) == "increasing":
            expected = _longest_run_labels(labels, values, increasing=True)
        else:
            assert str(query_variant) == "longest_monotone_streak"
            assert str(execution["streak_direction"]) == "decreasing"
            expected = _longest_run_labels(labels, values, increasing=False)
        assert evidence_labels == expected
        assert int(out.answer_gt.value) == int(len(expected))
        assert int(out.answer_gt.value) == int(execution["answer_value"])


def test_chart_trend_prompts_describe_chart_order() -> None:
    task = ChartsTrendValueTask()
    params = {"query_variant": "turning_point_count", "turning_point_type": "peak"}
    line = task.generate(16021, params={**params, "scene_variant": "line"}, max_attempts=10)
    horizontal = task.generate(16022, params={**params, "scene_variant": "horizontal_bar"}, max_attempts=10)
    dot_plot = task.generate(16023, params={**params, "scene_variant": "dot_plot"}, max_attempts=10)

    assert "displayed order" in str(line.prompt)
    assert "top to bottom" in str(horizontal.prompt)
    assert "left to right" in str(dot_plot.prompt)


def test_chart_trend_supports_all_ordered_scene_variants() -> None:
    task = ChartsTrendValueTask()
    prompts = {}
    for seed, scene_variant in enumerate(("area", "bar", "horizontal_bar", "line", "dot_plot", "lollipop"), start=16024):
        out = task.generate(
            seed,
            params={
                "query_variant": "turning_point_count",
                "turning_point_type": "peak",
                "scene_variant": scene_variant,
            },
            max_attempts=10,
        )
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
        task.generate(
            16040,
            params={"query_variant": "turning_point_count", "turning_point_type": "peak", "scene_variant": "scatter"},
            max_attempts=10,
        )
    with pytest.raises(ValueError):
        task.generate(
            16041,
            params={"query_variant": "turning_point_count", "turning_point_type": "peak", "scene_variant": "pie"},
            max_attempts=10,
        )
    with pytest.raises(ValueError):
        task.generate(
            16042,
            params={"query_variant": "turning_point_count", "turning_point_type": "peak", "scene_variant": "radar"},
            max_attempts=10,
        )


def test_chart_trend_prompt_examples_match_selected_variant() -> None:
    task = ChartsTrendValueTask()
    expected = {
        "turning_point_count": {"evidence": [[220, 180], [520, 210]], "answer": 2},
        "longest_monotone_streak": {
            "evidence": [[180, 420], [300, 350], [420, 260], [540, 170]],
            "answer": 4,
        },
    }
    params_by_variant = {
        "turning_point_count": {"turning_point_type": "peak"},
        "longest_monotone_streak": {"streak_direction": "increasing"},
    }
    for index, query_variant in enumerate(expected, start=16050):
        out = task.generate(index, params={"query_variant": query_variant, **params_by_variant[query_variant]}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[query_variant]
        assert answer_only == {"answer": expected[query_variant]["answer"]}


def test_chart_trend_task_is_deterministic() -> None:
    task = ChartsTrendValueTask()
    params = {"query_variant": "longest_monotone_streak", "streak_direction": "increasing", "scene_variant": "line"}
    out_a = task.generate(16061, params=params, max_attempts=10)
    out_b = task.generate(16061, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_trend_complexity_is_normalized_and_monotonic() -> None:
    task = ChartsTrendValueTask()
    easy = task.generate(
        16062,
        params={"query_variant": "turning_point_count", "turning_point_type": "peak", "scene_variant": "bar", "mark_count": 6},
        max_attempts=10,
    )
    hard = task.generate(
        16062,
        params={"query_variant": "longest_monotone_streak", "streak_direction": "increasing", "scene_variant": "area", "mark_count": 10},
        max_attempts=10,
    )
    _assert_normalized_complexity(easy)
    _assert_normalized_complexity(hard)
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)


def test_chart_trend_supports_zero_turning_point_answers() -> None:
    task = ChartsTrendValueTask()
    for seed, turning_point_type in enumerate(("peak", "trough"), start=16070):
        out = task.generate(
            seed,
            params={
                "query_variant": "turning_point_count",
                "turning_point_type": turning_point_type,
                "target_answer_min": 0,
                "target_answer_max": 0,
            },
            max_attempts=10,
        )
        assert int(out.answer_gt.value) == 0
        assert list(out.evidence_gt.value) == []


def test_chart_trend_supports_explicit_mark_count_10() -> None:
    task = ChartsTrendValueTask()
    cases = (
        {"query_variant": "turning_point_count", "turning_point_type": "peak"},
        {"query_variant": "turning_point_count", "turning_point_type": "trough"},
        {"query_variant": "longest_monotone_streak", "streak_direction": "increasing"},
        {"query_variant": "longest_monotone_streak", "streak_direction": "decreasing"},
    )
    for seed, params in enumerate(cases, start=16080):
        out = task.generate(
            seed,
            params={**params, "scene_variant": "bar", "mark_count": 10},
            max_attempts=10,
        )
        assert int(out.trace_payload["execution_trace"]["mark_count"]) == 10


def _first_crossing_index(values: list[int], *, threshold: int, comparison: str, start_index: int = 0) -> int:
    for index in range(int(start_index), len(values)):
        value = int(values[index])
        if str(comparison) == "greater_than" and int(value) > int(threshold):
            return int(index)
        if str(comparison) == "less_than" and int(value) < int(threshold):
            return int(index)
    raise AssertionError("no threshold crossing found")


def test_chart_trend_threshold_crossing_variants_match_contract() -> None:
    task = ChartsTrendValueTask()
    cases = (
        ("observed", "above", "line"),
        ("observed", "below", "bar"),
        ("linear_projection", "above", "dot_plot"),
        ("linear_projection", "below", "lollipop"),
    )
    for seed, (crossing_mode, crossing_direction, scene_variant) in enumerate(cases, start=16100):
        out = task.generate(
            seed,
            params={
                "query_variant": "threshold_crossing",
                "crossing_mode": crossing_mode,
                "crossing_direction": crossing_direction,
                "scene_variant": scene_variant,
            },
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        values = [int(value) for value in execution["values"]]
        labels = [str(label) for label in execution["labels"]]
        threshold = int(execution["threshold"])
        comparison = str(execution["comparison"])
        answer_index = int(execution["answer_index"])
        evidence_labels = [str(label) for label in execution["evidence_labels"]]
        ordered_evidence_labels = [str(label) for label in execution["ordered_evidence_labels"]]
        evidence_points = [list(point) for point in out.evidence_gt.value]

        assert str(out.query_variant) == "threshold_crossing"
        assert str(execution["crossing_mode"]) == str(crossing_mode)
        assert str(execution["crossing_direction"]) == str(crossing_direction)
        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "point_set"
        assert str(out.answer_gt.value) == str(labels[int(answer_index)])
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(trace["render_spec"]["scene_variant"]) == str(scene_variant)
        assert trace["render_spec"]["threshold_reference"] == {
            "threshold": int(threshold),
            "visible_guide": False,
        }
        assert str(threshold) in str(out.prompt)
        assert "red dashed" not in str(out.prompt).lower()
        assert trace["projected_evidence"]["point_set"] == evidence_points
        assert trace["projected_evidence"]["pixel_point_set"] == evidence_points
        assert "point_sequence" not in trace["projected_evidence"]
        assert "pixel_point_sequence" not in trace["projected_evidence"]
        assert "label_set" not in trace["projected_evidence"]
        assert "ordered_label_set" not in trace["projected_evidence"]
        assert len(evidence_points) == len(ordered_evidence_labels)
        assert len(trace["projected_evidence"]["bbox_set"]) == len(evidence_points)
        for x_coord, y_coord in evidence_points:
            assert 0 <= float(x_coord) <= int(render["canvas_width"])
            assert 0 <= float(y_coord) <= int(render["canvas_height"])
        assert set(trace["render_map"]["label_centers_px"].keys()) == set(labels)
        assert set(str(entity["attrs"]["label"]) for entity in trace["scene_ir"]["entities"]) == set(labels)

        if str(execution["internal_query_variant"]).startswith("linear_projection_"):
            projected_labels = [str(label) for label in execution["projected_labels"]]
            assert projected_labels
            first_projected_index = labels.index(projected_labels[0])
            observed_values = [int(value) for value in values[: int(first_projected_index)]]
            projected_values = [int(value) for value in values[int(first_projected_index):]]
            signed_delta = int(observed_values[-1]) - int(observed_values[-2])
            assert signed_delta != 0
            assert abs(int(signed_delta)) == int(execution["projection_delta"])
            assert all(
                int(right) - int(left) == int(signed_delta)
                for left, right in zip(observed_values[:-1], observed_values[1:])
            )
            assert all(
                int(value) == int(observed_values[-1]) + ((int(index) + 1) * int(signed_delta))
                for index, value in enumerate(projected_values)
            )
            if str(execution["crossing_direction"]) == "above":
                assert int(signed_delta) > 0
            else:
                assert int(signed_delta) < 0
            expected_index = _first_crossing_index(
                values,
                threshold=int(threshold),
                comparison=str(comparison),
                start_index=int(first_projected_index),
            )
            assert int(answer_index) == int(expected_index)
            assert all(str(execution["point_kind_by_label"][label]) == "projected" for label in projected_labels)
            projected_entities = {
                str(entity["attrs"]["label"]): entity
                for entity in trace["scene_ir"]["entities"]
                if str(entity["attrs"]["label"]) in set(projected_labels)
            }
            assert all(str(entity["entity_type"]) == "future_label_slot" for entity in projected_entities.values())
            assert all(bool(entity["attrs"]["visible"]) is False for entity in projected_entities.values())
            assert all("value" not in entity["attrs"] for entity in projected_entities.values())
            expected_evidence = set(labels[int(first_projected_index) - 2: int(answer_index) + 1])
        else:
            expected_index = _first_crossing_index(
                values,
                threshold=int(threshold),
                comparison=str(comparison),
            )
            assert int(answer_index) == int(expected_index)
            assert not execution["projected_labels"]
            expected_evidence = set(labels[: int(answer_index) + 1])
        assert set(evidence_labels) == expected_evidence
        assert set(ordered_evidence_labels) == expected_evidence


def test_chart_trend_threshold_crossing_supports_scene_variants_and_rejects_incompatible_ones() -> None:
    task = ChartsTrendValueTask()
    for seed, scene_variant in enumerate(("area", "bar", "line", "dot_plot", "lollipop"), start=16120):
        out = task.generate(
            seed,
            params={
                "query_variant": "threshold_crossing",
                "crossing_mode": "observed",
                "crossing_direction": "above",
                "scene_variant": scene_variant,
            },
            max_attempts=10,
        )
        assert str(out.trace_payload["execution_trace"]["scene_variant"]) == str(scene_variant)
    for scene_variant in ("horizontal_bar", "scatter", "radar", "pie", "donut"):
        with pytest.raises(ValueError):
            task.generate(
                16140,
                params={
                    "query_variant": "threshold_crossing",
                    "crossing_mode": "observed",
                    "crossing_direction": "above",
                    "scene_variant": scene_variant,
                },
                max_attempts=10,
            )


def test_chart_trend_threshold_crossing_prompt_examples_match_selected_variant() -> None:
    task = ChartsTrendValueTask()
    cases = (
        ("observed", "above", {"evidence": [[160, 420], [260, 360], [360, 240]], "answer": "C"}),
        ("observed", "below", {"evidence": [[180, 180], [280, 260], [380, 390]], "answer": "F"}),
        ("linear_projection", "above", {"evidence": [[300, 320], [420, 260], [540, 180]], "answer": "M"}),
        ("linear_projection", "below", {"evidence": [[300, 180], [420, 260], [540, 340]], "answer": "Q"}),
    )
    for index, (crossing_mode, crossing_direction, expected) in enumerate(cases, start=16150):
        out = task.generate(
            index,
            params={
                "query_variant": "threshold_crossing",
                "crossing_mode": crossing_mode,
                "crossing_direction": crossing_direction,
            },
            max_attempts=10,
        )
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected
        assert answer_only == {"answer": expected["answer"]}


def test_chart_trend_threshold_crossing_projection_supports_two_observed_marks() -> None:
    task = ChartsTrendValueTask()
    out = task.generate(
        16160,
        params={
            "query_variant": "threshold_crossing",
            "crossing_mode": "linear_projection",
            "crossing_direction": "above",
            "scene_variant": "line",
            "observed_count_min": 2,
            "observed_count_max": 2,
            "projection_count_min": 6,
            "projection_count_max": 6,
        },
        max_attempts=10,
    )
    execution = out.trace_payload["execution_trace"]
    assert int(execution["observed_count"]) == 2
    assert int(execution["projection_count"]) == 6
    assert len(execution["observed_labels"]) == 2
    assert len(execution["projected_labels"]) == 6
    assert out.evidence_gt.type == "point_set"
    assert len(out.evidence_gt.value) == len(execution["ordered_evidence_labels"])


def test_chart_trend_threshold_crossing_projection_counts_decouple_from_query_variant_sampling() -> None:
    task = ChartsTrendValueTask()
    observed_by_variant = {
        "linear_projection_crosses_above": set(),
        "linear_projection_crosses_below": set(),
    }
    for sampling_index in range(16):
        out = task.generate(
            16161 + int(sampling_index),
            params={
                "query_variant": "threshold_crossing",
                "crossing_mode": "linear_projection",
                "scene_variant": "line",
                "observed_count_min": 2,
                "observed_count_max": 5,
                "projection_count_min": 4,
                "projection_count_max": 6,
            },
            max_attempts=10,
        )
        internal_query_variant = str(out.trace_payload["execution_trace"]["internal_query_variant"])
        if internal_query_variant in observed_by_variant:
            observed_by_variant[internal_query_variant].add(int(out.trace_payload["execution_trace"]["observed_count"]))

    assert observed_by_variant["linear_projection_crosses_above"] == {2, 3, 4, 5}
    assert observed_by_variant["linear_projection_crosses_below"] == {2, 3, 4, 5}


def test_chart_trend_threshold_crossing_task_is_deterministic() -> None:
    task = ChartsTrendValueTask()
    params = {
        "query_variant": "threshold_crossing",
        "crossing_mode": "linear_projection",
        "crossing_direction": "above",
        "scene_variant": "line",
    }
    out_a = task.generate(16170, params=params, max_attempts=10)
    out_b = task.generate(16170, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_trend_threshold_crossing_complexity_is_normalized_and_monotonic() -> None:
    task = ChartsTrendValueTask()
    easy = task.generate(
        16180,
        params={
            "query_variant": "threshold_crossing",
            "crossing_mode": "observed",
            "crossing_direction": "above",
            "scene_variant": "bar",
        },
        max_attempts=10,
    )
    hard = task.generate(
        16181,
        params={
            "query_variant": "threshold_crossing",
            "crossing_mode": "linear_projection",
            "crossing_direction": "below",
            "scene_variant": "area",
        },
        max_attempts=10,
    )
    _assert_normalized_complexity(easy)
    _assert_normalized_complexity(hard)
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)


def test_chart_trend_threshold_crossing_uses_bounded_value_axis() -> None:
    task = ChartsTrendValueTask()
    out = task.generate(
        16190,
        params={
            "query_variant": "threshold_crossing",
            "crossing_mode": "observed",
            "crossing_direction": "below",
            "scene_variant": "bar",
        },
        max_attempts=10,
    )
    render_spec = out.trace_payload["render_spec"]
    execution = out.trace_payload["execution_trace"]
    _assert_value_axis_covers_values(render_spec, [int(value) for value in execution["values"]])
    assert 25 <= int(render_spec["value_axis_span"]) <= 100
    assert len(render_spec["y_ticks"]) <= 13


def test_chart_trend_interval_change_variants_match_contract() -> None:
    task = ChartsTrendValueTask()
    cases = (
        ("endpoint_change_value", "line", {"endpoint_change_kind": "absolute"}),
        ("endpoint_change_value", "bar", {"endpoint_change_kind": "signed"}),
        ("endpoint_change_value", "dot_plot", {"endpoint_change_kind": "percent"}),
        ("interval_rate_value", "horizontal_bar", {}),
    )
    for seed, (query_variant, scene_variant, extra_params) in enumerate(cases, start=16200):
        out = task.generate(
            seed,
            params={"query_variant": query_variant, "scene_variant": scene_variant, **extra_params},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        labels = [str(label) for label in execution["labels"]]
        values = [int(value) for value in execution["values"]]
        start_index = int(execution["start_index"])
        end_index = int(execution["end_index"])
        start_value = int(execution["start_value"])
        end_value = int(execution["end_value"])
        delta = int(execution["delta"])
        gap = int(execution["interval_gap"])
        internal_query_variant = str(execution["internal_query_variant"])
        evidence_labels = [str(label) for label in execution["ordered_evidence_labels"]]
        evidence_points = [list(point) for point in out.evidence_gt.value]

        assert str(out.query_variant) == str(query_variant)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "point_set"
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert labels[int(start_index)] == str(execution["start_label"])
        assert labels[int(end_index)] == str(execution["end_label"])
        assert values[int(start_index)] == int(start_value)
        assert values[int(end_index)] == int(end_value)
        assert int(delta) == int(end_value) - int(start_value)
        assert int(gap) == int(end_index) - int(start_index)
        assert evidence_labels == labels[int(start_index): int(end_index) + 1]
        assert trace["projected_evidence"]["point_set"] == evidence_points
        assert trace["projected_evidence"]["pixel_point_set"] == evidence_points
        assert "point_sequence" not in trace["projected_evidence"]
        assert "pixel_point_sequence" not in trace["projected_evidence"]
        assert "label_set" not in trace["projected_evidence"]
        assert len(evidence_points) == len(evidence_labels)
        assert len(trace["projected_evidence"]["bbox_set"]) == len(evidence_points)
        for x_coord, y_coord in evidence_points:
            assert 0 <= float(x_coord) <= int(render["canvas_width"])
            assert 0 <= float(y_coord) <= int(render["canvas_height"])
        assert set(trace["render_map"]["label_centers_px"].keys()) == set(labels)
        assert set(str(entity["attrs"]["label"]) for entity in trace["scene_ir"]["entities"]) == set(labels)
        assert str(execution["start_label"]) in str(out.prompt)
        assert str(execution["end_label"]) in str(out.prompt)
        _assert_value_axis_covers_values(render, values)
        assert render["guide_line_style"] in {"dashed", "dotted", "solid"}
        assert len(render["guide_lines"]) == int(execution["mark_count"])

        if str(internal_query_variant) == "absolute_change_between_labels":
            expected_answer = abs(int(delta))
        elif str(internal_query_variant) == "signed_change_between_labels":
            expected_answer = int(delta)
        elif str(internal_query_variant) == "percent_change_between_labels":
            assert int(delta) * 100 % int(start_value) == 0
            expected_answer = int(delta) * 100 // int(start_value)
        else:
            assert str(internal_query_variant) == "average_rate_over_interval"
            assert int(delta) % int(gap) == 0
            expected_answer = int(delta) // int(gap)
        assert int(out.answer_gt.value) == int(expected_answer)
        assert int(execution["answer_value"]) == int(expected_answer)


def test_chart_trend_interval_change_supports_scene_variants_and_rejects_incompatible_ones() -> None:
    task = ChartsTrendValueTask()
    for seed, scene_variant in enumerate(("area", "bar", "horizontal_bar", "line", "dot_plot", "lollipop"), start=16220):
        out = task.generate(
            seed,
            params={"query_variant": "endpoint_change_value", "endpoint_change_kind": "absolute", "scene_variant": scene_variant},
            max_attempts=10,
        )
        assert str(out.trace_payload["execution_trace"]["scene_variant"]) == str(scene_variant)
    for scene_variant in ("scatter", "radar", "pie", "donut"):
        with pytest.raises(ValueError):
            task.generate(
                16240,
                params={"query_variant": "endpoint_change_value", "endpoint_change_kind": "absolute", "scene_variant": scene_variant},
                max_attempts=10,
            )


def test_chart_trend_interval_change_prompt_examples_match_selected_variant() -> None:
    task = ChartsTrendValueTask()
    expected = {
        "endpoint_change_value": {"evidence": [[160, 420], [260, 360], [360, 300], [460, 220]], "answer": 20},
        "interval_rate_value": {"evidence": [[200, 420], [300, 360], [400, 300], [500, 240]], "answer": 6},
    }
    for index, query_variant in enumerate(expected, start=16250):
        params = {"query_variant": query_variant}
        if str(query_variant) == "endpoint_change_value":
            params["endpoint_change_kind"] = "absolute"
        out = task.generate(index, params=params, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[query_variant]
        assert answer_only == {"answer": expected[query_variant]["answer"]}


def test_chart_trend_interval_change_task_is_deterministic() -> None:
    task = ChartsTrendValueTask()
    params = {"query_variant": "endpoint_change_value", "endpoint_change_kind": "percent", "scene_variant": "line"}
    out_a = task.generate(16260, params=params, max_attempts=10)
    out_b = task.generate(16260, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_trend_interval_change_complexity_is_normalized_and_monotonic() -> None:
    task = ChartsTrendValueTask()
    easy = task.generate(
        16270,
        params={
            "query_variant": "endpoint_change_value",
            "endpoint_change_kind": "absolute",
            "scene_variant": "bar",
            "mark_count": 8,
            "interval_gap_max": 2,
        },
        max_attempts=10,
    )
    hard = task.generate(
        16271,
        params={
            "query_variant": "endpoint_change_value",
            "endpoint_change_kind": "percent",
            "scene_variant": "area",
            "mark_count": 14,
            "interval_gap_min": 6,
        },
        max_attempts=10,
    )
    _assert_normalized_complexity(easy)
    _assert_normalized_complexity(hard)
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)
