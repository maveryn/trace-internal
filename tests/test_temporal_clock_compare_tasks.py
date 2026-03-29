"""Behavior tests for temporal clock-compare task."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.temporal.clock.compare import TemporalClockCompareTask
from trace.tasks.temporal.shared.style import (
    SUPPORTED_TEMPORAL_CLOCK_COLOR_NAMES,
    SUPPORTED_TEMPORAL_CLOCK_STYLE_VARIANTS,
)
from tests.helpers import extract_prompt_json_example


def test_temporal_clock_compare_contract_matches_trace() -> None:
    task = TemporalClockCompareTask()
    task_variants = ("earliest_time", "latest_time")
    scene_variants = ("classic", "outline")
    style_variants = ("studio", "marker")
    accent_colors = ("blue", "orange")
    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 20500 + (variant_index * 10) + scene_index
            out = task.generate(
                seed,
                params={
                    "task_variant": task_variant,
                    "scene_variant": scene_variant,
                    "style_variant": style_variants[scene_index],
                    "accent_color_name": accent_colors[scene_index],
                },
                max_attempts=20,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            shown_total_minutes_by_label = {
                str(label): int(total)
                for label, total in execution["shown_total_minutes_by_label"].items()
            }

            assert out.answer_gt.type == "string"
            assert out.evidence_gt.type == "bbox_set"
            assert len(out.evidence_gt.value) == 1
            assert str(execution["task_variant"]) == str(task_variant)
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["style_variant"]) == str(style_variants[scene_index])
            assert str(execution["accent_color_name"]) == str(accent_colors[scene_index])
            assert trace["scene_ir"]["scene_kind"] == "temporal_clock_collection"
            assert 5 <= int(execution["clock_count"]) <= 9
            assert len(execution["clock_labels"]) == int(execution["clock_count"])
            assert len(set(execution["clock_labels"])) == len(execution["clock_labels"])
            assert set(execution["clock_labels"]).issubset(set(execution["clock_label_pool"]))
            assert set(out.complexity.complexity_components.keys()) == {
                "time_reading",
                "visual_scan",
                "ambiguity",
                "clutter",
            }
            assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert str(trace["render_map"]["winning_label"]) == str(out.answer_gt.value)

            expected_winner = (
                min(shown_total_minutes_by_label.items(), key=lambda item: item[1])[0]
                if str(task_variant) == "earliest_time"
                else max(shown_total_minutes_by_label.items(), key=lambda item: item[1])[0]
            )
            assert str(out.answer_gt.value) == str(expected_winner)
            assert out.evidence_gt.value[0] == trace["render_map"]["winning_clock_bbox_px"]


def test_temporal_clock_compare_prompt_examples_match_variants() -> None:
    task = TemporalClockCompareTask()
    expected = {
        "earliest_time": (
            {"evidence": [[368, 94, 552, 278]], "answer": "B"},
            {"answer": "B"},
        ),
        "latest_time": (
            {"evidence": [[368, 94, 552, 278]], "answer": "E"},
            {"answer": "E"},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=20540):
        out = task.generate(
            index,
            params={"task_variant": task_variant},
            max_attempts=20,
        )
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_temporal_clock_compare_explicit_clock_count_supports_nine_clocks() -> None:
    task = TemporalClockCompareTask()
    out = task.generate(
        20570,
        params={"task_variant": "latest_time", "clock_count": 9},
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    assert int(execution["clock_count"]) == 9
    assert len(execution["clock_labels"]) == 9
    assert len(set(execution["clock_labels"])) == 9
    assert str(out.answer_gt.value) in set(execution["clock_labels"])


def test_temporal_clock_compare_balanced_sampling_defaults_cover_axes() -> None:
    task = TemporalClockCompareTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    clock_counts: Counter[int] = Counter()
    winner_labels: Counter[str] = Counter()
    for index in range(90):
        out = task.generate(
            hash64(20580, "temporal_clock_compare", index),
            params={"_sampling_index": index},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        accent_color_names[str(execution["accent_color_name"])] += 1
        clock_counts[int(execution["clock_count"])] += 1
        winner_labels[str(execution["winner_label"])] += 1

    assert set(task_variants.keys()) == {"earliest_time", "latest_time"}
    assert set(scene_variants.keys()) == {"classic", "minimal", "outline"}
    assert set(style_variants.keys()) == set(SUPPORTED_TEMPORAL_CLOCK_STYLE_VARIANTS)
    assert set(accent_color_names.keys()) == set(SUPPORTED_TEMPORAL_CLOCK_COLOR_NAMES)
    assert set(clock_counts.keys()) == {5, 6, 7, 8, 9}
    assert set(winner_labels.keys()) == {"A", "B", "C", "D", "E", "F", "G", "H", "I"}
