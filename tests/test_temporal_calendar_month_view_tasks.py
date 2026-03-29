"""Behavior tests for the temporal month-view calendar task."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.temporal.calendar.month_view import TemporalCalendarMonthViewTask
from trace.tasks.temporal.shared.style import SUPPORTED_TEMPORAL_COLOR_NAMES, SUPPORTED_TEMPORAL_STYLE_VARIANTS
from tests.helpers import extract_prompt_json_example


def test_temporal_calendar_month_view_contract_matches_trace() -> None:
    task = TemporalCalendarMonthViewTask()
    task_variants = (
        "date_of_weekday_occurrence",
        "count_marked_weekend_days",
        "days_between_marked_dates",
    )
    scene_variants = ("classic", "outline")
    style_variants = ("studio", "marker")
    accent_colors = ("blue", "orange")
    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 21800 + (variant_index * 10) + scene_index
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

            assert out.answer_gt.type == "integer"
            assert out.evidence_gt.type == "bbox_set"
            assert str(execution["task_variant"]) == str(task_variant)
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["style_variant"]) == str(style_variants[scene_index])
            assert str(execution["accent_color_name"]) == str(accent_colors[scene_index])
            assert trace["scene_ir"]["scene_kind"] == "temporal_month_calendar"
            assert 4 <= int(execution["row_count"]) <= 6
            assert 28 <= int(execution["days_in_month"]) <= 31
            assert set(out.complexity.complexity_components.keys()) == {
                "calendar_lookup",
                "visual_scan",
                "ambiguity",
                "clutter",
            }
            assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

            evidence_dates = [int(day) for day in execution["evidence_dates"]]
            if str(task_variant) == "date_of_weekday_occurrence":
                assert len(out.evidence_gt.value) == 1
                assert int(out.answer_gt.value) == int(evidence_dates[0])
            elif str(task_variant) == "count_marked_weekend_days":
                assert int(out.answer_gt.value) == len(evidence_dates)
                assert all(int(day) in set(execution["marked_dates"]) for day in evidence_dates)
            else:
                assert len(out.evidence_gt.value) == 2
                assert int(out.answer_gt.value) == abs(int(evidence_dates[1]) - int(evidence_dates[0]))


def test_temporal_calendar_month_view_prompt_examples_match_variants() -> None:
    task = TemporalCalendarMonthViewTask()
    expected = {
        "date_of_weekday_occurrence": (
            {"evidence": [[354, 256, 456, 352]], "answer": 18},
            {"answer": 18},
        ),
        "count_marked_weekend_days": (
            {
                "evidence": [[148, 352, 250, 448], [560, 352, 662, 448]],
                "answer": 2,
            },
            {"answer": 2},
        ),
        "days_between_marked_dates": (
            {
                "evidence": [[250, 448, 352, 544], [560, 448, 662, 544]],
                "answer": 9,
            },
            {"answer": 9},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=21840):
        out = task.generate(
            index,
            params={"task_variant": task_variant},
            max_attempts=20,
        )
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_temporal_calendar_month_view_balanced_sampling_defaults_cover_axes() -> None:
    task = TemporalCalendarMonthViewTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    row_counts: Counter[int] = Counter()
    for index in range(90):
        out = task.generate(
            hash64(21880, "temporal_calendar_month_view", index),
            params={"_sampling_index": index},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        accent_color_names[str(execution["accent_color_name"])] += 1
        row_counts[int(execution["row_count"])] += 1

    assert set(task_variants.keys()) == {
        "date_of_weekday_occurrence",
        "count_marked_weekend_days",
        "days_between_marked_dates",
    }
    assert set(scene_variants.keys()) == {"classic", "minimal", "outline"}
    assert set(style_variants.keys()) == set(SUPPORTED_TEMPORAL_STYLE_VARIANTS)
    assert set(accent_color_names.keys()) == set(SUPPORTED_TEMPORAL_COLOR_NAMES)
    assert set(row_counts.keys()).issubset({4, 5, 6})
