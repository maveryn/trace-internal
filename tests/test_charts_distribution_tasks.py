"""Behavior tests for chart distribution tasks."""

from __future__ import annotations

import json

from trace.tasks.charts.distribution.boxplot_label import ChartsDistributionBoxplotLabelTask
from trace.tasks.charts.distribution.density_label import ChartsDistributionDensityLabelTask
from trace.tasks.charts.distribution.histogram_count import ChartsDistributionHistogramCountTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _assert_normalized_complexity(out: object, *, expected_keys: set[str]) -> None:
    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == set(expected_keys)
    assert all(
        0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values()
    )


def test_chart_distribution_histogram_variants_match_contract() -> None:
    task = ChartsDistributionHistogramCountTask()
    for seed, task_variant in enumerate(("modal_bin_count", "interval_mass", "cumulative_count_to_bin"), start=11010):
        out = task.generate(seed, params={"task_variant": task_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]

        labels = [str(label) for label in execution["labels"]]
        counts = [int(value) for value in execution["bin_counts"]]
        counts_by_label = {str(label): int(value) for label, value in execution["counts_by_label"].items()}
        evidence_labels = [str(label) for label in out.evidence_gt.value]

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "label_set"
        assert str(execution["scene_variant"]) == "histogram"
        assert str(render["scene_variant"]) == "histogram"
        assert trace["projected_evidence"]["label_set"] == evidence_labels
        assert len(trace["projected_evidence"]["bbox_set"]) == len(evidence_labels)
        assert len(trace["scene_ir"]["entities"]) == int(execution["bin_count"])
        assert set(str(entity["attrs"]["label"]) for entity in trace["scene_ir"]["entities"]) == set(labels)
        assert set(trace["render_map"]["label_centers_px"].keys()) == set(labels)
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))

        if str(task_variant) == "modal_bin_count":
            assert len(evidence_labels) == 1
            assert int(out.answer_gt.value) == max(counts)
            assert int(counts_by_label[evidence_labels[0]]) == int(out.answer_gt.value)
        elif str(task_variant) == "interval_mass":
            assert len(evidence_labels) >= 2
            assert int(out.answer_gt.value) == sum(int(counts_by_label[label]) for label in evidence_labels)
            assert str(execution["query_interval_label"]).strip()
        else:
            assert len(evidence_labels) >= 2
            assert evidence_labels == labels[: len(evidence_labels)]
            assert int(out.answer_gt.value) == sum(int(counts_by_label[label]) for label in evidence_labels)
            assert str(execution["query_bin_label"]) == str(evidence_labels[-1])


def test_histogram_bins_are_contiguous_numeric_intervals() -> None:
    task = ChartsDistributionHistogramCountTask()
    out = task.generate(11030, params={"task_variant": "interval_mass"}, max_attempts=10)
    entities = out.trace_payload["scene_ir"]["entities"]
    intervals = [
        (
            int(entity["attrs"]["interval_start"]),
            int(entity["attrs"]["interval_end"]),
        )
        for entity in entities
    ]
    for index in range(len(intervals) - 1):
        assert int(intervals[index][1]) + 1 == int(intervals[index + 1][0])


def test_chart_distribution_histogram_prompt_examples_match_selected_variant() -> None:
    task = ChartsDistributionHistogramCountTask()
    expected = {
        "modal_bin_count": {"evidence": ["6-8"], "answer": 9},
        "interval_mass": {"evidence": ["6-8", "9-11"], "answer": 15},
        "cumulative_count_to_bin": {"evidence": ["0-2", "3-5", "6-8"], "answer": 18},
    }
    for index, task_variant in enumerate(expected, start=11040):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_chart_distribution_histogram_task_is_deterministic() -> None:
    task = ChartsDistributionHistogramCountTask()
    params = {"task_variant": "cumulative_count_to_bin"}
    out_a = task.generate(11060, params=params, max_attempts=10)
    out_b = task.generate(11060, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_distribution_histogram_complexity_is_normalized_and_monotonic() -> None:
    task = ChartsDistributionHistogramCountTask()
    easy = task.generate(
        11061,
        params={"task_variant": "modal_bin_count", "bin_count_min": 4, "bin_count_max": 4},
        max_attempts=10,
    )
    hard = task.generate(
        11061,
        params={"task_variant": "cumulative_count_to_bin", "bin_count_min": 7, "bin_count_max": 7},
        max_attempts=10,
    )
    _assert_normalized_complexity(easy, expected_keys={"visual_scan", "reasoning_load"})
    _assert_normalized_complexity(hard, expected_keys={"visual_scan", "reasoning_load"})
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)


def test_chart_distribution_boxplot_variants_match_contract() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    for seed, task_variant in enumerate(("median_above_reference_q3", "largest_iqr", "smallest_iqr"), start=11110):
        out = task.generate(seed, params={"task_variant": task_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        quartiles_by_label = {str(label): dict(values) for label, values in execution["quartiles_by_label"].items()}

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "integer"
        assert str(execution["scene_variant"]) == "boxplot"
        assert str(render["scene_variant"]) == "boxplot"
        assert trace["projected_evidence"]["integer"] == int(out.evidence_gt.value)
        assert len(trace["projected_evidence"]["bbox_set"]) == 1
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))

        for stats in quartiles_by_label.values():
            assert int(stats["whisker_min"]) <= int(stats["q1"]) < int(stats["median"]) < int(stats["q3"]) <= int(stats["whisker_max"])

        if str(task_variant) == "median_above_reference_q3":
            reference_label = str(execution["reference_label"])
            reference_q3 = int(execution["reference_q3"])
            target_label = max(
                (str(label) for label in quartiles_by_label if str(label) != str(reference_label)),
                key=lambda label: int(quartiles_by_label[label]["median"]) - int(reference_q3),
            )
            assert str(out.answer_gt.value) == str(target_label)
            assert int(out.evidence_gt.value) == int(quartiles_by_label[target_label]["median"]) - int(reference_q3)
        elif str(task_variant) == "largest_iqr":
            target_label = max(quartiles_by_label, key=lambda label: int(quartiles_by_label[label]["iqr"]))
            assert str(out.answer_gt.value) == str(target_label)
            assert int(out.evidence_gt.value) == int(quartiles_by_label[target_label]["iqr"])
        else:
            target_label = min(quartiles_by_label, key=lambda label: int(quartiles_by_label[label]["iqr"]))
            assert str(out.answer_gt.value) == str(target_label)
            assert int(out.evidence_gt.value) == int(quartiles_by_label[target_label]["iqr"])


def test_chart_distribution_boxplot_prompt_examples_match_selected_variant() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    expected = {
        "median_above_reference_q3": {"evidence": 2, "answer": "M"},
        "largest_iqr": {"evidence": 6, "answer": "Q"},
        "smallest_iqr": {"evidence": 2, "answer": "B"},
    }
    for index, task_variant in enumerate(expected, start=11140):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_chart_distribution_boxplot_task_is_deterministic() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    params = {"task_variant": "largest_iqr"}
    out_a = task.generate(11160, params=params, max_attempts=10)
    out_b = task.generate(11160, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_distribution_boxplot_can_tighten_reference_q3_winner_gap() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    out = task.generate(
        11162,
        params={
            "task_variant": "median_above_reference_q3",
            "category_count_min": 7,
            "category_count_max": 7,
            "median_reference_winner_gap_min": 1,
            "median_reference_winner_gap_max": 1,
        },
        max_attempts=10,
    )
    execution = out.trace_payload["execution_trace"]
    quartiles_by_label = execution["quartiles_by_label"]
    reference_q3 = int(execution["reference_q3"])
    margins = sorted(
        int(stats["median"]) - int(reference_q3)
        for label, stats in quartiles_by_label.items()
        if str(label) != str(execution["reference_label"]) and int(stats["median"]) > int(reference_q3)
    )
    assert margins[-1] - margins[-2] == 1


def test_chart_distribution_boxplot_supports_task_variant_overrides() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    out = task.generate(
        11164,
        params={
            "task_variant": "median_above_reference_q3",
            "category_count_min": 4,
            "category_count_max": 7,
            "task_variant_overrides": {
                "median_above_reference_q3": {
                    "category_count_min": 8,
                    "category_count_max": 8,
                    "median_reference_winner_gap_min": 1,
                    "median_reference_winner_gap_max": 1,
                }
            },
        },
        max_attempts=10,
    )
    execution = out.trace_payload["execution_trace"]
    assert int(execution["category_count"]) == 8
    reference_q3 = int(execution["reference_q3"])
    margins = sorted(
        int(stats["median"]) - int(reference_q3)
        for label, stats in execution["quartiles_by_label"].items()
        if str(label) != str(execution["reference_label"]) and int(stats["median"]) > int(reference_q3)
    )
    assert margins[-1] - margins[-2] == 1


def test_chart_distribution_boxplot_can_tighten_iqr_winner_gap() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    for seed, task_variant in enumerate(("largest_iqr", "smallest_iqr"), start=11163):
        out = task.generate(
            seed,
            params={
                "task_variant": task_variant,
                "category_count_min": 7,
                "category_count_max": 7,
                "iqr_winner_gap_min": 1,
                "iqr_winner_gap_max": 1,
            },
            max_attempts=10,
        )
        quartiles_by_label = out.trace_payload["execution_trace"]["quartiles_by_label"]
        iqrs = sorted(int(stats["iqr"]) for stats in quartiles_by_label.values())
        if task_variant == "largest_iqr":
            assert iqrs[-1] - iqrs[-2] == 1
        else:
            assert iqrs[1] - iqrs[0] == 1


def test_chart_distribution_boxplot_complexity_is_normalized_and_monotonic() -> None:
    task = ChartsDistributionBoxplotLabelTask()
    easy = task.generate(11161, params={"task_variant": "median_above_reference_q3"}, max_attempts=10)
    hard = task.generate(11161, params={"task_variant": "largest_iqr"}, max_attempts=10)
    _assert_normalized_complexity(easy, expected_keys={"visual_scan", "reasoning_load"})
    _assert_normalized_complexity(hard, expected_keys={"visual_scan", "reasoning_load"})
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)


def test_chart_distribution_density_variants_match_contract() -> None:
    task = ChartsDistributionDensityLabelTask()
    for seed, task_variant in enumerate(("highest_mode", "lowest_mode", "bimodal_label"), start=11210):
        out = task.generate(seed, params={"task_variant": task_variant}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        support_by_label = {str(label): dict(values) for label, values in execution["support_by_label"].items()}

        assert str(out.task_variant) == str(task_variant)
        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "integer_list"
        assert str(execution["scene_variant"]) == "violin"
        assert str(render["scene_variant"]) == "violin"
        assert trace["projected_evidence"]["integer_list"] == list(out.evidence_gt.value)
        assert len(trace["projected_evidence"]["bbox_set"]) == 1
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))

        for stats in support_by_label.values():
            assert int(stats["support_min"]) < int(stats["support_max"])
            assert len(stats["mode_values"]) in {1, 2}
            assert all(int(stats["support_min"]) < int(value) < int(stats["support_max"]) for value in stats["mode_values"])

        if str(task_variant) == "highest_mode":
            target_label = max(support_by_label, key=lambda label: int(support_by_label[label]["mode_values"][0]))
            assert str(out.answer_gt.value) == str(target_label)
            assert list(out.evidence_gt.value) == [int(support_by_label[target_label]["mode_values"][0])]
            assert sum(1 for values in support_by_label.values() if len(values["mode_values"]) == 2) == 0
        elif str(task_variant) == "lowest_mode":
            target_label = min(support_by_label, key=lambda label: int(support_by_label[label]["mode_values"][0]))
            assert str(out.answer_gt.value) == str(target_label)
            assert list(out.evidence_gt.value) == [int(support_by_label[target_label]["mode_values"][0])]
            assert sum(1 for values in support_by_label.values() if len(values["mode_values"]) == 2) == 0
        else:
            bimodal_labels = [label for label, values in support_by_label.items() if len(values["mode_values"]) == 2]
            assert len(bimodal_labels) == 1
            target_label = str(bimodal_labels[0])
            assert str(out.answer_gt.value) == str(target_label)
            assert list(out.evidence_gt.value) == sorted(int(value) for value in support_by_label[target_label]["mode_values"])


def test_chart_distribution_density_prompt_examples_match_selected_variant() -> None:
    task = ChartsDistributionDensityLabelTask()
    expected = {
        "highest_mode": {"evidence": [14], "answer": "Q"},
        "lowest_mode": {"evidence": [5], "answer": "B"},
        "bimodal_label": {"evidence": [6, 12], "answer": "M"},
    }
    for index, task_variant in enumerate(expected, start=11240):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[task_variant]
        assert answer_only == {"answer": expected[task_variant]["answer"]}


def test_chart_distribution_density_task_is_deterministic() -> None:
    task = ChartsDistributionDensityLabelTask()
    params = {"task_variant": "bimodal_label"}
    out_a = task.generate(11260, params=params, max_attempts=10)
    out_b = task.generate(11260, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_chart_distribution_density_complexity_is_normalized_and_monotonic() -> None:
    task = ChartsDistributionDensityLabelTask()
    easy = task.generate(11261, params={"task_variant": "highest_mode"}, max_attempts=10)
    hard = task.generate(11261, params={"task_variant": "bimodal_label"}, max_attempts=10)
    _assert_normalized_complexity(easy, expected_keys={"visual_scan", "reasoning_load"})
    _assert_normalized_complexity(hard, expected_keys={"visual_scan", "reasoning_load"})
    assert float(hard.complexity.complexity_score) > float(easy.complexity.complexity_score)
