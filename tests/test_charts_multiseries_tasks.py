"""Behavior tests for chart multiseries tasks."""

from __future__ import annotations

import json

from trace.tasks.charts.multiseries.comparison_query import (
    ChartsMultiseriesCategoryTotalExtremumLabelTask,
    ChartsMultiseriesComparisonQueryTask,
)


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


def _evidence_point_values(out: object) -> list[list[float]]:
    return [list(point) for point in out.evidence_gt.value.values()]


def _assert_keyed_point_evidence(out: object) -> None:
    projected = out.trace_payload["projected_evidence"]
    assert out.evidence_gt.type == "keyed_point_map"
    assert projected["type"] == "keyed_point_map"
    assert projected["keyed_point_map"] == out.evidence_gt.value
    assert projected["pixel_keyed_point_map"] == out.evidence_gt.value


def test_chart_multiseries_pairwise_comparison_count_matches_contract() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    cases = (
        ("series_comparison_count", "grouped_bar", "greater_than"),
        ("series_comparison_count", "grouped_horizontal_bar", "less_than"),
        ("series_comparison_count", "multi_line", "greater_than"),
        ("series_comparison_count", "grouped_lollipop", "less_than"),
    )
    for seed, (query_id, scene_variant, comparison) in enumerate(cases, start=11010):
        out = task.generate(
            seed,
            params={"query_id": query_id, "scene_variant": scene_variant, "comparison": comparison},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        category_labels = [str(label) for label in execution["category_labels"]]
        series_labels = [str(label) for label in execution["series_labels"]]
        query_pair = [str(label) for label in execution["queried_series_labels"]]
        evidence_labels = [str(label) for label in execution["evidence_labels"]]
        evidence_points = _evidence_point_values(out)
        values_by_category = {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in series_values.items()
            }
            for category_label, series_values in execution["values_by_category"].items()
        }

        assert str(out.query_id) == str(query_id)
        assert out.answer_gt.type == "integer"
        _assert_keyed_point_evidence(out)
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert str(execution["comparison"]) == str(comparison)
        assert 8 <= int(execution["category_count"]) <= 12
        assert 4 <= int(execution["series_count"]) <= 5
        assert len(category_labels) == int(execution["category_count"])
        assert len(series_labels) == int(execution["series_count"])
        assert all(str(label).istitle() for label in series_labels)
        assert all(str(label).isalpha() for label in series_labels)
        assert all(2 <= len(str(label)) <= 4 for label in series_labels)
        assert len(query_pair) == 2
        assert set(query_pair).issubset(set(series_labels))
        assert evidence_labels == sorted(evidence_labels)
        assert int(out.answer_gt.value) == len(evidence_labels)
        assert trace["projected_evidence"]["point_set"] == evidence_points
        assert len(evidence_points) == 2 * len(evidence_labels)
        assert len(trace["projected_evidence"]["bbox_set"]) == 2 * len(evidence_labels)
        for x_coord, y_coord in evidence_points:
            assert 0 <= float(x_coord) <= int(render["canvas_width"])
            assert 0 <= float(y_coord) <= int(render["canvas_height"])
        assert len(trace["scene_ir"]["entities"]) == int(execution["category_count"]) * int(execution["series_count"])
        assert set(str(entity["attrs"]["category_label"]) for entity in trace["scene_ir"]["entities"]) == set(category_labels)
        assert set(str(entity["attrs"]["series_label"]) for entity in trace["scene_ir"]["entities"]) == set(series_labels)
        assert set(trace["render_map"]["category_label_centers_px"].keys()) == set(category_labels)

        left_series, right_series = query_pair
        assert f'"{left_series}"' in str(out.prompt)
        assert f'"{right_series}"' in str(out.prompt)
        for category_label in category_labels:
            left_value = int(values_by_category[str(category_label)][str(left_series)])
            right_value = int(values_by_category[str(category_label)][str(right_series)])
            if str(comparison) == "greater_than":
                assert (left_value > right_value) is (str(category_label) in set(evidence_labels))
            else:
                assert (left_value < right_value) is (str(category_label) in set(evidence_labels))


def test_chart_multiseries_prompts_match_scene_variant_wording() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    prompts = {}
    for seed, scene_variant in enumerate(
        ("grouped_bar", "grouped_horizontal_bar", "multi_line", "grouped_lollipop"),
        start=11030,
    ):
        out = task.generate(
            seed,
            params={"query_id": "series_comparison_count", "scene_variant": scene_variant},
            max_attempts=10,
        )
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


def test_chart_multiseries_grouped_horizontal_bar_evidence_uses_value_endpoint() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    out = task.generate(
        11035,
        params={
            "query_id": "series_comparison_count",
            "scene_variant": "grouped_horizontal_bar",
            "comparison": "less_than",
        },
        max_attempts=10,
    )
    entities_by_key = {
        f"{str(entity['attrs']['category_label'])}:{str(entity['attrs']['series_label'])}": entity["attrs"]
        for entity in out.trace_payload["scene_ir"]["entities"]
    }
    for key, point in out.trace_payload["projected_evidence"]["pixel_point_map"].items():
        bbox = [float(value) for value in entities_by_key[str(key)]["mark_bbox_px"]]
        point_x, point_y = [float(value) for value in point]
        assert abs(float(point_x) - float(bbox[2])) <= 1e-6
        assert abs(float(point_y) - (0.5 * (float(bbox[1]) + float(bbox[3])))) <= 1e-3


def test_chart_multiseries_prompt_examples_match_selected_variant() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    expected = {
        "evidence": {
            "Q:Orly": [180, 260],
            "Q:Vega": [180, 190],
            "M:Orly": [360, 320],
            "M:Vega": [360, 240],
            "Z:Orly": [540, 210],
            "Z:Vega": [540, 280],
        },
        "answer": 3,
    }
    for index, comparison in enumerate(("greater_than", "less_than"), start=11040):
        out = task.generate(
            index,
            params={"query_id": "series_comparison_count", "comparison": comparison},
            max_attempts=10,
        )
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected
        assert answer_only == {"answer": expected["answer"]}


def test_chart_multiseries_task_is_deterministic() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    params = {
        "query_id": "series_comparison_count",
        "scene_variant": "multi_line",
        "comparison": "greater_than",
    }
    out_a = task.generate(11050, params=params, max_attempts=10)
    out_b = task.generate(11050, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_multiseries_complexity_is_normalized_and_monotonic() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    easy = task.generate(
        11055,
        params={
            "query_id": "series_comparison_count",
            "scene_variant": "grouped_bar",
            "comparison": "greater_than",
            "category_count_min": 5,
            "category_count_max": 5,
            "series_count_min": 2,
            "series_count_max": 2,
        },
        max_attempts=10,
    )
    hard = task.generate(
        11055,
        params={
            "query_id": "series_comparison_count",
            "scene_variant": "multi_line",
            "comparison": "greater_than",
            "category_count_min": 15,
            "category_count_max": 15,
            "series_count_min": 4,
            "series_count_max": 4,
        },
        max_attempts=10,
    )
    _assert_normalized_complexity(easy)
    _assert_normalized_complexity(hard)
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)


def test_chart_multiseries_supports_explicit_category_and_series_counts() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    out = task.generate(
        11060,
        params={
            "query_id": "series_comparison_count",
            "scene_variant": "grouped_bar",
            "comparison": "greater_than",
            "category_count_min": 15,
            "category_count_max": 15,
            "series_count_min": 4,
            "series_count_max": 4,
        },
        max_attempts=10,
    )
    assert int(out.trace_payload["execution_trace"]["category_count"]) == 15
    assert int(out.trace_payload["execution_trace"]["series_count"]) == 4


def test_chart_multiseries_extremum_label_delta_matches_contract() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    cases = (
        ("ranked_change_extremum", "grouped_bar", {"change_measure": "directional_change", "change_direction": "increase"}),
        ("ranked_change_extremum", "grouped_horizontal_bar", {"change_measure": "directional_change", "change_direction": "decrease"}),
        ("ranked_change_extremum", "multi_line", {"change_measure": "absolute_gap", "extremum_direction": "largest"}),
        ("ranked_change_extremum", "grouped_lollipop", {"change_measure": "absolute_gap", "extremum_direction": "smallest"}),
    )
    for seed, (query_id, scene_variant, axis_params) in enumerate(cases, start=11110):
        out = task.generate(
            seed,
            params={"query_id": query_id, "scene_variant": scene_variant, **axis_params},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        category_labels = [str(label) for label in execution["category_labels"]]
        series_labels = [str(label) for label in execution["series_labels"]]
        query_pair = [str(label) for label in execution["queried_series_labels"]]
        answer_label = str(out.answer_gt.value)
        evidence_values = [int(value) for value in execution["evidence_values"]]
        evidence_points = _evidence_point_values(out)
        values_by_category = {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in series_values.items()
            }
            for category_label, series_values in execution["values_by_category"].items()
        }

        assert str(out.query_id) == str(query_id)
        assert str(execution["internal_query_id"]).startswith("ranked_")
        assert out.answer_gt.type == "option_letter"
        _assert_keyed_point_evidence(out)
        assert len(evidence_values) == 3
        assert len(evidence_points) == 2
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert 10 <= int(execution["category_count"]) <= 15
        assert 3 <= int(execution["series_count"]) <= 4
        assert len(category_labels) == int(execution["category_count"])
        assert len(series_labels) == int(execution["series_count"])
        assert len(query_pair) == 2
        assert set(query_pair).issubset(set(series_labels))
        assert answer_label in set(category_labels)
        assert trace["projected_evidence"]["point_set"] == evidence_points
        assert "integer_list" not in trace["projected_evidence"]
        assert len(trace["projected_evidence"]["bbox_set"]) == 2
        for x_coord, y_coord in evidence_points:
            assert 0 <= float(x_coord) <= int(render["canvas_width"])
            assert 0 <= float(y_coord) <= int(render["canvas_height"])
        assert len(trace["scene_ir"]["entities"]) == int(execution["category_count"]) * int(execution["series_count"])
        assert set(trace["render_map"]["category_label_centers_px"].keys()) == set(category_labels)

        left_series, right_series = query_pair
        assert f'"{left_series}"' in str(out.prompt)
        assert f'"{right_series}"' in str(out.prompt)
        derived_values = {}
        internal_query_id = str(execution["internal_query_id"])
        for category_label in category_labels:
            left_value = int(values_by_category[str(category_label)][str(left_series)])
            right_value = int(values_by_category[str(category_label)][str(right_series)])
            if internal_query_id == "ranked_largest_increase":
                derived_value = int(right_value) - int(left_value)
                assert derived_value > 0
            elif internal_query_id == "ranked_largest_decrease":
                derived_value = int(left_value) - int(right_value)
                assert derived_value > 0
            else:
                derived_value = abs(int(right_value) - int(left_value))
                assert derived_value > 0
            derived_values[str(category_label)] = int(derived_value)
            assert int(execution["derived_values_by_category"][str(category_label)]) == int(derived_value)

        if internal_query_id == "ranked_smallest_gap":
            ranked_labels = [
                str(label)
                for label, _value in sorted(derived_values.items(), key=lambda item: (int(item[1]), str(item[0])))
            ]
        else:
            ranked_labels = [
                str(label)
                for label, _value in sorted(derived_values.items(), key=lambda item: (-int(item[1]), str(item[0])))
            ]
        answer_rank = int(execution["answer_rank"])
        assert 1 <= answer_rank <= 3
        assert answer_label == ranked_labels[int(answer_rank) - 1]
        assert int(execution["answer_score"]) == int(derived_values[str(answer_label)])
        assert evidence_values[0] == int(values_by_category[str(answer_label)][str(left_series)])
        assert evidence_values[1] == int(values_by_category[str(answer_label)][str(right_series)])
        assert evidence_values[2] == int(derived_values[str(answer_label)])


def test_chart_multiseries_extremum_delta_prompt_examples_match_selected_variant() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    expected = {
        "directional_change": {
            "evidence": {"Q:Orly": [260, 320], "Q:Vega": [260, 180]},
            "answer": "Q",
        },
        "absolute_gap": {
            "evidence": {"M:Orly": [260, 340], "M:Vega": [260, 160]},
            "answer": "M",
        },
    }
    params_by_measure = {
        "directional_change": {"change_direction": "increase"},
        "absolute_gap": {"extremum_direction": "largest"},
    }
    for index, change_measure in enumerate(expected, start=11140):
        out = task.generate(
            index,
            params={
                "query_id": "ranked_change_extremum",
                "change_measure": change_measure,
                **params_by_measure[change_measure],
            },
            max_attempts=10,
        )
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[change_measure]
        assert answer_only == {"answer": expected[change_measure]["answer"]}


def test_chart_multiseries_extremum_delta_balanced_axes_are_decoupled() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    observed = set()
    query_id_counts = {}
    scene_query_id_counts = {}
    for index in range(120):
        out = task.generate(11200 + index, params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        query_id = str(execution["query_id"])
        scene_variant = str(execution["scene_variant"])
        observed.add((query_id, scene_variant))
        query_id_counts[query_id] = query_id_counts.get(query_id, 0) + 1
        scene_query_id_counts[scene_variant] = scene_query_id_counts.get(scene_variant, 0) + 1

    assert set(query_id_counts) == {
        "category_total_extremum_label",
        "conditional_gap_aggregate_value",
        "conditional_gap_extremum_value",
        "ranked_change_extremum",
        "ranked_ratio_extremum",
        "series_comparison_count",
    }
    assert len(observed) == 24
    assert all(10 <= count <= 35 for count in query_id_counts.values())
    assert all(20 <= count <= 40 for count in scene_query_id_counts.values())


def test_chart_multiseries_extremum_delta_task_is_deterministic() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    params = {
        "query_id": "ranked_change_extremum",
        "change_measure": "absolute_gap",
        "scene_variant": "multi_line",
        "extremum_direction": "largest",
    }
    out_a = task.generate(11150, params=params, max_attempts=10)
    out_b = task.generate(11150, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_multiseries_extremum_label_ratio_matches_contract() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    cases = (
        ("ranked_ratio_extremum", "grouped_bar", {"ratio_measure": "series_share", "extremum_direction": "largest"}),
        ("ranked_ratio_extremum", "grouped_horizontal_bar", {"ratio_measure": "series_share", "extremum_direction": "smallest"}),
        ("ranked_ratio_extremum", "multi_line", {"ratio_measure": "pair_ratio", "extremum_direction": "largest"}),
        ("ranked_ratio_extremum", "grouped_lollipop", {"ratio_measure": "pair_ratio", "extremum_direction": "smallest"}),
    )
    for seed, (query_id, scene_variant, axis_params) in enumerate(cases, start=11210):
        out = task.generate(
            seed,
            params={"query_id": query_id, "scene_variant": scene_variant, **axis_params},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        category_labels = [str(label) for label in execution["category_labels"]]
        series_labels = [str(label) for label in execution["series_labels"]]
        answer_label = str(out.answer_gt.value)
        evidence_values = [int(value) for value in execution["evidence_values"]]
        evidence_points = _evidence_point_values(out)
        values_by_category = {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in series_values.items()
            }
            for category_label, series_values in execution["values_by_category"].items()
        }

        assert str(out.query_id) == str(query_id)
        assert out.answer_gt.type == "option_letter"
        _assert_keyed_point_evidence(out)
        assert len(evidence_values) == 3
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert 5 <= int(execution["category_count"]) <= 10
        assert 3 <= int(execution["series_count"]) <= 4
        assert len(category_labels) == int(execution["category_count"])
        assert len(series_labels) == int(execution["series_count"])
        assert answer_label in set(category_labels)
        assert trace["projected_evidence"]["point_set"] == evidence_points
        assert "integer_list" not in trace["projected_evidence"]
        assert len(trace["scene_ir"]["entities"]) == int(execution["category_count"]) * int(execution["series_count"])
        for x_coord, y_coord in evidence_points:
            assert 0 <= float(x_coord) <= int(render["canvas_width"])
            assert 0 <= float(y_coord) <= int(render["canvas_height"])
        assert set(trace["render_map"]["category_label_centers_px"].keys()) == set(category_labels)

        is_share_variant = str(execution["ratio_measure"]) == "series_share"
        assert len(evidence_points) == (len(series_labels) if is_share_variant else 2)
        assert len(trace["projected_evidence"]["bbox_set"]) == len(evidence_points)
        derived_values = {}
        if is_share_variant:
            target_series = str(execution["target_series_label"])
            assert target_series in set(series_labels)
            assert f'"{target_series}"' in str(out.prompt)
            for category_label in category_labels:
                target_value = int(values_by_category[str(category_label)][str(target_series)])
                category_total = sum(int(value) for value in values_by_category[str(category_label)].values())
                assert int(execution["denominator_values_by_category"][str(category_label)]) == int(category_total)
                assert (int(target_value) * 100) % int(category_total) == 0
                ratio_percent = (int(target_value) * 100) // int(category_total)
                derived_values[str(category_label)] = int(ratio_percent)
                assert int(execution["ratio_percent_by_category"][str(category_label)]) == int(ratio_percent)
        else:
            numerator_series = str(execution["numerator_series_label"])
            denominator_series = str(execution["denominator_series_label"])
            assert numerator_series in set(series_labels)
            assert denominator_series in set(series_labels)
            assert numerator_series != denominator_series
            assert f'"{numerator_series}"' in str(out.prompt)
            assert f'"{denominator_series}"' in str(out.prompt)
            for category_label in category_labels:
                numerator_value = int(values_by_category[str(category_label)][str(numerator_series)])
                denominator_value = int(values_by_category[str(category_label)][str(denominator_series)])
                assert int(execution["denominator_values_by_category"][str(category_label)]) == int(denominator_value)
                assert (int(numerator_value) * 100) % int(denominator_value) == 0
                ratio_percent = (int(numerator_value) * 100) // int(denominator_value)
                derived_values[str(category_label)] = int(ratio_percent)
                assert int(execution["ratio_percent_by_category"][str(category_label)]) == int(ratio_percent)

        if str(execution["extremum_direction"]) == "smallest":
            ranked_labels = [
                str(label)
                for label, _value in sorted(derived_values.items(), key=lambda item: (int(item[1]), str(item[0])))
            ]
        else:
            ranked_labels = [
                str(label)
                for label, _value in sorted(derived_values.items(), key=lambda item: (-int(item[1]), str(item[0])))
            ]
        answer_rank = int(execution["answer_rank"])
        assert 1 <= answer_rank <= 3
        assert answer_label == ranked_labels[int(answer_rank) - 1]
        assert int(execution["answer_score_percent"]) == int(derived_values[str(answer_label)])
        assert evidence_values[0] == int(
            values_by_category[str(answer_label)][
                str(execution["target_series_label"] if is_share_variant else execution["numerator_series_label"])
            ]
        )
        assert evidence_values[1] == int(execution["denominator_values_by_category"][str(answer_label)])
        assert evidence_values[2] == int(derived_values[str(answer_label)])


def test_chart_multiseries_extremum_ratio_prompt_examples_match_selected_variant() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    expected = {
        "series_share": {
            "evidence": {
                "Q:Orly": [300, 240],
                "Q:Vega": [300, 320],
                "Q:Tana": [300, 400],
            },
            "answer": "Q",
        },
        "pair_ratio": {
            "evidence": {"M:Orly": [300, 180], "M:Vega": [300, 300]},
            "answer": "M",
        },
    }
    for index, ratio_measure in enumerate(expected, start=11240):
        out = task.generate(
            index,
            params={"query_id": "ranked_ratio_extremum", "ratio_measure": ratio_measure, "extremum_direction": "largest"},
            max_attempts=10,
        )
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[ratio_measure]
        assert answer_only == {"answer": expected[ratio_measure]["answer"]}


def test_chart_multiseries_extremum_ratio_balanced_axes_are_decoupled() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    observed = set()
    query_id_counts = {}
    scene_query_id_counts = {}
    for index in range(120):
        out = task.generate(11300 + index, params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        query_id = str(execution["query_id"])
        scene_variant = str(execution["scene_variant"])
        observed.add((query_id, scene_variant))
        query_id_counts[query_id] = query_id_counts.get(query_id, 0) + 1
        scene_query_id_counts[scene_variant] = scene_query_id_counts.get(scene_variant, 0) + 1

    assert set(query_id_counts) == {
        "category_total_extremum_label",
        "conditional_gap_aggregate_value",
        "conditional_gap_extremum_value",
        "ranked_change_extremum",
        "ranked_ratio_extremum",
        "series_comparison_count",
    }
    assert len(observed) == 24
    assert all(10 <= count <= 35 for count in query_id_counts.values())
    assert all(20 <= count <= 40 for count in scene_query_id_counts.values())


def test_chart_multiseries_extremum_ratio_task_is_deterministic() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    params = {
        "query_id": "ranked_ratio_extremum",
        "ratio_measure": "series_share",
        "scene_variant": "multi_line",
        "extremum_direction": "largest",
    }
    out_a = task.generate(11250, params=params, max_attempts=10)
    out_b = task.generate(11250, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_multiseries_category_total_extremum_matches_contract() -> None:
    task = ChartsMultiseriesCategoryTotalExtremumLabelTask()
    cases = (
        ("grouped_bar", "largest"),
        ("grouped_horizontal_bar", "smallest"),
        ("multi_line", "largest"),
        ("grouped_lollipop", "smallest"),
    )
    for seed, (scene_variant, extremum_direction) in enumerate(cases, start=11270):
        out = task.generate(
            seed,
            params={
                "scene_variant": scene_variant,
                "extremum_direction": extremum_direction,
            },
            max_attempts=10,
        )
        execution = out.trace_payload["execution_trace"]
        render = out.trace_payload["render_spec"]
        values_by_category = {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in series_values.items()
            }
            for category_label, series_values in execution["values_by_category"].items()
        }
        totals_by_category = {
            str(category_label): sum(int(value) for value in series_values.values())
            for category_label, series_values in values_by_category.items()
        }
        ranked = sorted(
            totals_by_category,
            key=lambda label: (totals_by_category[str(label)], str(label)),
            reverse=str(extremum_direction) == "largest",
        )
        answer_label = str(ranked[int(execution["answer_rank"]) - 1])

        assert out.query_id == "category_total_extremum_label"
        assert out.answer_gt.type == "option_letter"
        assert out.answer_gt.value == answer_label
        assert int(execution["answer_score"]) == int(totals_by_category[str(answer_label)])
        assert execution["category_totals_by_category"] == totals_by_category
        assert 6 <= int(execution["category_count"]) <= 10
        assert 3 <= int(execution["series_count"]) <= 5
        _assert_keyed_point_evidence(out)
        assert len(out.evidence_gt.value) == int(execution["series_count"])
        assert str(render["scene_variant"]) == str(scene_variant)
        _assert_normalized_complexity(out)


def test_chart_multiseries_conditional_gap_value_matches_contract() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    cases = (
        ("conditional_gap_aggregate_value", "sum", "grouped_bar", "greater_than", None),
        ("conditional_gap_aggregate_value", "mean", "grouped_horizontal_bar", "less_than", None),
        ("conditional_gap_aggregate_value", "range", "multi_line", "greater_than", None),
        ("conditional_gap_extremum_value", None, "grouped_lollipop", "less_than", "smallest"),
    )
    for seed, (query_id, aggregate_kind, scene_variant, comparison, extremum_direction) in enumerate(cases, start=11310):
        params = {
            "query_id": query_id,
            "scene_variant": scene_variant,
            "condition_comparison": comparison,
        }
        if aggregate_kind is not None:
            params["conditional_gap_aggregate_kind"] = aggregate_kind
        if extremum_direction is not None:
            params["extremum_direction"] = extremum_direction
        out = task.generate(seed, params=params, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        category_labels = [str(label) for label in execution["category_labels"]]
        series_labels = [str(label) for label in execution["series_labels"]]
        filtered_labels = [str(label) for label in execution["filtered_category_labels"]]
        condition_left, condition_right = [str(label) for label in execution["condition_series_labels"]]
        target_left, target_right = [str(label) for label in execution["target_series_labels"]]
        values_by_category = {
            str(category_label): {
                str(series_label): int(value)
                for series_label, value in series_values.items()
            }
            for category_label, series_values in execution["values_by_category"].items()
        }

        assert str(out.query_id) == str(query_id)
        assert out.answer_gt.type == "integer"
        _assert_keyed_point_evidence(out)
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert str(execution["scene_variant"]) == str(scene_variant)
        assert str(render["scene_variant"]) == str(scene_variant)
        assert 8 <= int(execution["category_count"]) <= 12
        assert 4 <= int(execution["series_count"]) <= 5
        assert 3 <= int(execution["filtered_category_count"]) <= 6
        assert len(category_labels) == int(execution["category_count"])
        assert len(series_labels) == int(execution["series_count"])
        assert len(filtered_labels) == int(execution["filtered_category_count"])
        assert set(execution["condition_series_labels"]).isdisjoint(set(execution["target_series_labels"]))
        assert set(filtered_labels).issubset(set(category_labels))
        assert len(trace["scene_ir"]["entities"]) == int(execution["category_count"]) * int(execution["series_count"])
        assert trace["projected_evidence"]["point_set"] == _evidence_point_values(out)
        assert len(out.evidence_gt.value) == 4 * len(filtered_labels)
        assert len(trace["projected_evidence"]["bbox_set"]) == 4 * len(filtered_labels)
        for series_label in (condition_left, condition_right, target_left, target_right):
            assert f'"{series_label}"' in str(out.prompt)

        recomputed_filtered_labels = []
        recomputed_gaps = []
        for category_label in category_labels:
            condition_left_value = int(values_by_category[str(category_label)][condition_left])
            condition_right_value = int(values_by_category[str(category_label)][condition_right])
            if str(comparison) == "greater_than":
                relation_holds = condition_left_value > condition_right_value
            else:
                relation_holds = condition_left_value < condition_right_value
            assert bool(execution["condition_holds_by_category"][str(category_label)]) is bool(relation_holds)
            target_gap = abs(
                int(values_by_category[str(category_label)][target_left])
                - int(values_by_category[str(category_label)][target_right])
            )
            assert int(execution["target_gap_by_category"][str(category_label)]) == int(target_gap)
            if relation_holds:
                recomputed_filtered_labels.append(str(category_label))
                recomputed_gaps.append(int(target_gap))

        assert recomputed_filtered_labels == filtered_labels
        assert [int(value) for value in execution["filtered_gap_values"]] == recomputed_gaps
        if str(aggregate_kind) == "sum":
            expected_answer = sum(recomputed_gaps)
        elif str(aggregate_kind) == "mean":
            expected_answer = sum(recomputed_gaps) // len(recomputed_gaps)
            assert sum(recomputed_gaps) % len(recomputed_gaps) == 0
        elif str(aggregate_kind) == "range":
            expected_answer = max(recomputed_gaps) - min(recomputed_gaps)
        elif str(execution["extremum_direction"]) == "smallest":
            expected_answer = min(recomputed_gaps)
        else:
            expected_answer = max(recomputed_gaps)
        assert int(out.answer_gt.value) == int(expected_answer)
        _assert_normalized_complexity(out)


def test_chart_multiseries_conditional_gap_prompt_examples_match_selected_variant() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    expected = {
        "evidence": {
            "Q:Orly": [160, 310],
            "Q:Vega": [160, 250],
            "Q:Tana": [160, 190],
            "Q:Mira": [160, 280],
            "M:Orly": [300, 330],
            "M:Vega": [300, 260],
            "M:Tana": [300, 210],
            "M:Mira": [300, 300],
        },
        "answer": 24,
    }
    for index, query_id in enumerate(
        (
            "conditional_gap_aggregate_value",
            "conditional_gap_extremum_value",
        ),
        start=11340,
    ):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected
        assert answer_only == {"answer": expected["answer"]}


def test_chart_multiseries_conditional_gap_axes_are_decoupled() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    observed = set()
    query_id_counts = {}
    scene_query_id_counts = {}
    condition_counts = {}
    aggregate_counts = {}
    for index in range(100):
        out = task.generate(
            11400 + index,
            params={
                "query_id": "conditional_gap_aggregate_value",
            },
            max_attempts=10,
        )
        execution = out.trace_payload["execution_trace"]
        query_id = str(execution["query_id"])
        scene_variant = str(execution["scene_variant"])
        condition = str(execution["condition_comparison"])
        aggregate_kind = str(execution["conditional_gap_aggregate_kind"])
        observed.add((query_id, scene_variant))
        query_id_counts[query_id] = query_id_counts.get(query_id, 0) + 1
        scene_query_id_counts[scene_variant] = scene_query_id_counts.get(scene_variant, 0) + 1
        condition_counts[condition] = condition_counts.get(condition, 0) + 1
        aggregate_counts[aggregate_kind] = aggregate_counts.get(aggregate_kind, 0) + 1

    assert set(query_id_counts) == {
        "conditional_gap_aggregate_value",
    }
    assert len(observed) == 4
    assert sorted(query_id_counts.values()) == [100]
    assert set(scene_query_id_counts) == {"grouped_bar", "grouped_horizontal_bar", "grouped_lollipop", "multi_line"}
    assert set(condition_counts) == {"greater_than", "less_than"}
    assert set(aggregate_counts) == {"mean", "range"}
    assert max(condition_counts.values()) - min(condition_counts.values()) <= 20
    assert max(aggregate_counts.values()) - min(aggregate_counts.values()) <= 10


def test_chart_multiseries_conditional_gap_task_is_deterministic() -> None:
    task = ChartsMultiseriesComparisonQueryTask()
    params = {
        "query_id": "conditional_gap_aggregate_value",
        "conditional_gap_aggregate_kind": "range",
        "scene_variant": "multi_line",
        "condition_comparison": "greater_than",
    }
    out_a = task.generate(11450, params=params, max_attempts=10)
    out_b = task.generate(11450, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
