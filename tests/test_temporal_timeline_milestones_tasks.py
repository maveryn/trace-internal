"""Behavior tests for the temporal milestone-timeline task."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.temporal.shared.style import SUPPORTED_TEMPORAL_COLOR_NAMES, SUPPORTED_TEMPORAL_STYLE_VARIANTS
from trace.tasks.temporal.timeline.milestones import TemporalTimelineMilestonesTask
from tests.helpers import extract_prompt_json_example


def test_temporal_timeline_milestones_contract_matches_trace() -> None:
    task = TemporalTimelineMilestonesTask()
    task_variants = (
        "before_reference_count",
        "between_reference_events_count",
        "position_of_reference",
    )
    scene_variants = ("classic", "roadmap")
    style_variants = ("studio", "marker")
    accent_colors = ("blue", "orange")
    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 22600 + (variant_index * 10) + scene_index
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
            ordered_event_ids = [str(event["event_id"]) for event in sorted(events, key=lambda event: int(event["order_index"]))]
            primary_reference_index = next(
                int(event["order_index"])
                for event in events
                if str(event["reference_kind"]) == "primary"
            )

            assert out.answer_gt.type == "integer"
            assert out.evidence_gt.type == "bbox_set"
            assert str(execution["task_variant"]) == str(task_variant)
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["style_variant"]) == str(style_variants[scene_index])
            assert str(execution["accent_color_name"]) == str(accent_colors[scene_index])
            assert trace["scene_ir"]["scene_kind"] == "temporal_milestone_timeline"
            assert 6 <= int(execution["event_count"]) <= 9
            assert set(out.complexity.complexity_components.keys()) == {
                "temporal_order_reasoning",
                "visual_scan",
                "ambiguity",
                "clutter",
            }
            assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert int(out.answer_gt.value) == int(execution["answer_value"])

            if str(task_variant) == "before_reference_count":
                expected_ids = tuple(ordered_event_ids[:primary_reference_index])
                assert tuple(str(value) for value in execution["answer_event_ids"]) == expected_ids
                assert int(out.answer_gt.value) == len(expected_ids)
            elif str(task_variant) == "between_reference_events_count":
                secondary_reference_index = next(
                    int(event["order_index"])
                    for event in events
                    if str(event["reference_kind"]) == "secondary"
                )
                expected_ids = tuple(ordered_event_ids[primary_reference_index + 1 : secondary_reference_index])
                assert tuple(str(value) for value in execution["answer_event_ids"]) == expected_ids
                assert int(out.answer_gt.value) == len(expected_ids)
            else:
                expected_ids = tuple(ordered_event_ids[: primary_reference_index + 1])
                assert tuple(str(value) for value in execution["answer_event_ids"]) == expected_ids
                assert int(out.answer_gt.value) == len(expected_ids)


def test_temporal_timeline_milestones_prompt_examples_match_variants() -> None:
    task = TemporalTimelineMilestonesTask()
    expected = {
        "before_reference_count": (
            {
                "evidence": [[160, 158, 264, 228], [286, 158, 390, 228]],
                "answer": 2,
            },
            {"answer": 2},
        ),
        "between_reference_events_count": (
            {
                "evidence": [[412, 410, 516, 480], [538, 158, 642, 228]],
                "answer": 2,
            },
            {"answer": 2},
        ),
        "position_of_reference": (
            {
                "evidence": [[160, 158, 264, 228], [286, 158, 390, 228], [412, 410, 516, 480]],
                "answer": 3,
            },
            {"answer": 3},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=22640):
        out = task.generate(
            index,
            params={"task_variant": task_variant},
            max_attempts=20,
        )
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_temporal_timeline_milestones_balanced_sampling_defaults_cover_axes() -> None:
    task = TemporalTimelineMilestonesTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    event_counts: Counter[int] = Counter()
    for index in range(90):
        out = task.generate(
            hash64(22680, "temporal_timeline_milestones", index),
            params={"_sampling_index": index},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        accent_color_names[str(execution["accent_color_name"])] += 1
        event_counts[int(execution["event_count"])] += 1

    assert set(task_variants.keys()) == {
        "before_reference_count",
        "between_reference_events_count",
        "position_of_reference",
    }
    assert set(scene_variants.keys()) == {"classic", "roadmap", "minimal"}
    assert set(style_variants.keys()) == set(SUPPORTED_TEMPORAL_STYLE_VARIANTS)
    assert set(accent_color_names.keys()) == set(SUPPORTED_TEMPORAL_COLOR_NAMES)
    assert set(event_counts.keys()).issubset({6, 7, 8, 9})
