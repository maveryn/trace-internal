"""Behavior tests for the temporal day-planner schedule task."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

from trace.core.seed import hash64
from trace.tasks.temporal.schedule.day_planner import TemporalScheduleDayPlannerTask
from trace.tasks.temporal.shared.style import SUPPORTED_TEMPORAL_COLOR_NAMES, SUPPORTED_TEMPORAL_STYLE_VARIANTS
from tests.helpers import extract_prompt_json_example


def _intervals_overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    """Return whether two half-open slot intervals overlap."""

    return bool(int(left[0]) < int(right[1]) and int(right[0]) < int(left[1]))


def _maximum_non_overlapping_subsets(events: list[dict[str, object]]) -> tuple[int, list[tuple[str, ...]]]:
    """Return the maximum compatible subset size and every optimum subset."""

    event_ids = [str(event["event_id"]) for event in events]
    intervals = {
        str(event["event_id"]): (int(event["start_slot"]), int(event["end_slot"]))
        for event in events
    }
    best_size = 0
    best_subsets: list[tuple[str, ...]] = []
    for subset_size in range(1, len(event_ids) + 1):
        for subset in combinations(event_ids, subset_size):
            if any(_intervals_overlap(intervals[left], intervals[right]) for left, right in combinations(subset, 2)):
                continue
            if int(subset_size) > int(best_size):
                best_size = int(subset_size)
                best_subsets = [tuple(sorted(subset))]
            elif int(subset_size) == int(best_size):
                best_subsets.append(tuple(sorted(subset)))
    return int(best_size), sorted(set(tuple(subset) for subset in best_subsets))


def test_temporal_schedule_day_planner_contract_matches_trace() -> None:
    task = TemporalScheduleDayPlannerTask()
    task_variants = (
        "overlap_count",
        "longer_than_reference_count",
        "maximum_non_overlapping_count",
    )
    scene_variants = ("classic", "outline")
    style_variants = ("studio", "marker")
    accent_colors = ("blue", "orange")
    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 22050 + (variant_index * 10) + scene_index
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
            events = [dict(event) for event in execution["events"]]
            intervals = {
                str(event["event_id"]): (int(event["start_slot"]), int(event["end_slot"]))
                for event in events
            }
            durations = {
                str(event["event_id"]): int(event["duration_slots"])
                for event in events
            }

            assert out.answer_gt.type == "integer"
            assert out.evidence_gt.type == "bbox_set"
            assert str(execution["task_variant"]) == str(task_variant)
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["style_variant"]) == str(style_variants[scene_index])
            assert str(execution["accent_color_name"]) == str(accent_colors[scene_index])
            assert trace["scene_ir"]["scene_kind"] == "temporal_day_schedule"
            assert 7 <= int(execution["event_count"]) <= 10 or str(task_variant) == "maximum_non_overlapping_count"
            assert 1 <= int(execution["lane_count"]) <= 5
            assert set(out.complexity.complexity_components.keys()) == {
                "interval_reasoning",
                "visual_scan",
                "ambiguity",
                "clutter",
            }
            assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert int(out.answer_gt.value) == len(execution["answer_event_ids"])

            if str(task_variant) == "overlap_count":
                reference_event_id = str(execution["reference_event_id"])
                reference_interval = intervals[reference_event_id]
                expected_event_ids = sorted(
                    event_id
                    for event_id, interval in intervals.items()
                    if event_id != reference_event_id and _intervals_overlap(interval, reference_interval)
                )
                assert sorted(str(value) for value in execution["answer_event_ids"]) == expected_event_ids
            elif str(task_variant) == "longer_than_reference_count":
                reference_event_id = str(execution["reference_event_id"])
                reference_duration = int(durations[reference_event_id])
                expected_event_ids = sorted(
                    event_id
                    for event_id, duration in durations.items()
                    if event_id != reference_event_id and int(duration) > int(reference_duration)
                )
                assert sorted(str(value) for value in execution["answer_event_ids"]) == expected_event_ids
            else:
                best_size, best_subsets = _maximum_non_overlapping_subsets(events)
                assert int(out.answer_gt.value) == int(best_size)
                assert len(best_subsets) == 1
                assert tuple(sorted(str(value) for value in execution["answer_event_ids"])) == tuple(best_subsets[0])


def test_temporal_schedule_day_planner_prompt_examples_match_variants() -> None:
    task = TemporalScheduleDayPlannerTask()
    expected = {
        "overlap_count": (
            {
                "evidence": [[250, 276, 396, 366], [404, 318, 550, 438]],
                "answer": 2,
            },
            {"answer": 2},
        ),
        "longer_than_reference_count": (
            {
                "evidence": [[250, 240, 396, 408], [404, 430, 550, 634], [558, 352, 704, 568]],
                "answer": 3,
            },
            {"answer": 3},
        ),
        "maximum_non_overlapping_count": (
            {
                "evidence": [
                    [250, 220, 396, 316],
                    [404, 316, 550, 412],
                    [558, 412, 704, 508],
                    [250, 508, 396, 604],
                ],
                "answer": 4,
            },
            {"answer": 4},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=22110):
        out = task.generate(
            index,
            params={"task_variant": task_variant},
            max_attempts=20,
        )
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_temporal_schedule_day_planner_balanced_sampling_defaults_cover_axes() -> None:
    task = TemporalScheduleDayPlannerTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    lane_counts: Counter[int] = Counter()
    for index in range(90):
        out = task.generate(
            hash64(22140, "temporal_schedule_day_planner", index),
            params={"_sampling_index": index},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        accent_color_names[str(execution["accent_color_name"])] += 1
        lane_counts[int(execution["lane_count"])] += 1

    assert set(task_variants.keys()) == {
        "overlap_count",
        "longer_than_reference_count",
        "maximum_non_overlapping_count",
    }
    assert set(scene_variants.keys()) == {"classic", "minimal", "outline"}
    assert set(style_variants.keys()) == set(SUPPORTED_TEMPORAL_STYLE_VARIANTS)
    assert set(accent_color_names.keys()) == set(SUPPORTED_TEMPORAL_COLOR_NAMES)
    assert set(lane_counts.keys()).issubset({1, 2, 3, 4, 5})
