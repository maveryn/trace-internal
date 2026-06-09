"""Behavior tests for the milestone-timeline task."""

from __future__ import annotations

from collections import Counter, defaultdict

from trace.core.seed import hash64
from trace.tasks.shared.text_rendering import resolve_text_stroke_fill
from trace.tasks.shared.time_artifact_style import SUPPORTED_TIME_ARTIFACT_COLOR_NAMES, SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS
from trace.tasks.pages.timeline.milestones import PagesTimelineEventDateGapValueTask, PagesTimelineIntervalMembershipCountTask
from tests.helpers import extract_prompt_json_example


def test_pages_timeline_milestones_contract_matches_trace() -> None:
    task = PagesTimelineIntervalMembershipCountTask()
    query_ids = (
        "between_reference_events_count",
        "outside_reference_interval_count",
    )
    scene_variants = ("classic", "roadmap")
    style_variants = ("studio", "marker")
    accent_colors = ("blue", "orange")
    for query_id_index, query_id in enumerate(query_ids):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 22600 + (query_id_index * 10) + scene_index
            out = task.generate(
                seed,
                params={
                    "query_id": query_id,
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
            assert out.annotation_gt.type == "bbox_set"
            expected_relation = "between" if str(query_id) == "between_reference_events_count" else "outside"
            assert out.query_id == str(query_id)
            assert str(execution["query_id"]) == str(query_id)
            assert str(execution["source_query_id"]) == "interval_membership_count"
            assert str(execution["interval_relation"]) == expected_relation
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["style_variant"]) == str(style_variants[scene_index])
            assert str(execution["accent_color_name"]) == str(accent_colors[scene_index])
            assert trace["scene_ir"]["scene_kind"] == "pages_milestone_timeline"
            assert 6 <= int(execution["event_count"]) <= 12
            assert set(out.complexity.complexity_components.keys()) == {
                "timeline_order_reasoning",
                "visual_scan",
                "ambiguity",
                "clutter",
            }
            assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
            assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
            assert int(out.answer_gt.value) == int(execution["answer_value"])
            resolved_colors = trace["render_spec"]["timeline_style"]["resolved_colors_rgb"]
            assert resolved_colors["primary_reference_fill"] == resolved_colors["secondary_reference_fill"]
            assert resolved_colors["primary_reference_fill"] != resolved_colors["event_fill"]

            secondary_reference_index = next(
                int(event["order_index"])
                for event in events
                if str(event["reference_kind"]) == "secondary"
            )
            if expected_relation == "between":
                expected_ids = tuple(ordered_event_ids[primary_reference_index + 1 : secondary_reference_index])
                assert tuple(str(value) for value in execution["answer_event_ids"]) == expected_ids
                assert int(out.answer_gt.value) == len(expected_ids)
            else:
                expected_ids = tuple(ordered_event_ids[:primary_reference_index]) + tuple(
                    ordered_event_ids[secondary_reference_index + 1 :]
                )
                assert tuple(str(value) for value in execution["answer_event_ids"]) == expected_ids
                assert int(out.answer_gt.value) == len(expected_ids)


def test_pages_timeline_event_date_gap_value_contract_matches_trace() -> None:
    task = PagesTimelineEventDateGapValueTask()
    out = task.generate(
        22632,
        params={
            "scene_variant": "minimal",
            "style_variant": "accented",
            "accent_color_name": "green",
        },
        max_attempts=20,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render_map = trace["render_map"]
    events_by_id = {str(event["event_id"]): dict(event) for event in execution["events"]}
    earlier_event_id, later_event_id = [str(value) for value in execution["endpoint_event_ids"]]
    earlier_event = events_by_id[earlier_event_id]
    later_event = events_by_id[later_event_id]

    assert out.query_id == "event_date_gap_value"
    assert str(execution["query_id"]) == "event_date_gap_value"
    assert str(execution["source_query_id"]) == "event_date_gap_value"
    assert str(execution["interval_relation"]) == "date_gap"
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert int(earlier_event["day_of_month"]) < int(later_event["day_of_month"])
    assert int(out.answer_gt.value) == int(later_event["day_of_month"]) - int(earlier_event["day_of_month"])
    assert set(out.annotation_gt.value.keys()) == {"earlier_event", "later_event"}
    assert out.annotation_gt.value["earlier_event"] == render_map["event_bboxes_by_id"][earlier_event_id]
    assert out.annotation_gt.value["later_event"] == render_map["event_bboxes_by_id"][later_event_id]
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert tuple(str(value) for value in render_map["endpoint_event_ids"]) == (earlier_event_id, later_event_id)


def test_pages_timeline_milestones_prompt_examples_match_variants() -> None:
    task = PagesTimelineIntervalMembershipCountTask()
    expected = {
        "between_reference_events_count": (
            {
                "annotation": [[412, 410, 516, 480], [538, 158, 642, 228]],
                "answer": 2,
            },
            {"answer": 2},
        ),
        "outside_reference_interval_count": (
            {
                "annotation": [[160, 158, 264, 228], [790, 410, 894, 480]],
                "answer": 2,
            },
            {"answer": 2},
        ),
    }
    for index, (query_id, (expected_answer_and_annotation, expected_answer_only)) in enumerate(expected.items(), start=22640):
        out = task.generate(
            index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation == expected_answer_and_annotation
        assert answer_only == expected_answer_only


def test_pages_timeline_event_date_gap_value_prompt_examples_match_variants() -> None:
    task = PagesTimelineEventDateGapValueTask()
    out = task.generate(
        22643,
        params={},
        max_attempts=20,
    )
    answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_annotation == {
        "annotation": {
            "earlier_event": [160, 158, 264, 228],
            "later_event": [538, 158, 642, 228],
        },
        "answer": 9,
    }
    assert answer_only == {"answer": 9}


def test_pages_timeline_milestones_balanced_sampling_defaults_cover_axes() -> None:
    task = PagesTimelineIntervalMembershipCountTask()
    query_ids: Counter[str] = Counter()
    interval_relations: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    event_counts: Counter[int] = Counter()
    scenes_by_query_id: defaultdict[str, Counter[str]] = defaultdict(Counter)
    styles_by_query_id: defaultdict[str, Counter[str]] = defaultdict(Counter)
    answers_by_query_id: defaultdict[str, Counter[int]] = defaultdict(Counter)
    for index in range(90):
        out = task.generate(
            hash64(22680, "pages_timeline_interval_membership_count", index),
            params={},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        query_id = str(execution["source_query_id"])
        interval_relation = str(execution["interval_relation"])
        scene_variant = str(execution["scene_variant"])
        style_variant = str(execution["style_variant"])
        query_ids[query_id] += 1
        interval_relations[interval_relation] += 1
        scene_variants[scene_variant] += 1
        style_variants[style_variant] += 1
        accent_color_names[str(execution["accent_color_name"])] += 1
        event_counts[int(execution["event_count"])] += 1
        scenes_by_query_id[query_id][scene_variant] += 1
        styles_by_query_id[query_id][style_variant] += 1
        answers_by_query_id[query_id][int(out.answer_gt.value)] += 1

    assert set(query_ids.keys()) == {"interval_membership_count"}
    assert set(interval_relations.keys()) == {"between", "outside"}
    assert set(scene_variants.keys()) == {"classic", "roadmap", "minimal"}
    assert set(style_variants.keys()) == set(SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS)
    assert set(accent_color_names.keys()) == set(SUPPORTED_TIME_ARTIFACT_COLOR_NAMES)
    assert set(event_counts.keys()).issubset({6, 7, 8, 9, 10, 11, 12})
    assert max(event_counts) >= 10
    for query_id in query_ids:
        assert set(scenes_by_query_id[query_id].keys()) == {"classic", "roadmap", "minimal"}
        assert set(styles_by_query_id[query_id].keys()) == set(SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS)
        assert len(answers_by_query_id[query_id]) >= 5


def test_pages_timeline_event_date_gap_value_balanced_sampling_covers_answers_and_prompt_order() -> None:
    task = PagesTimelineEventDateGapValueTask()
    answers: Counter[int] = Counter()
    prompt_orders: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    for index in range(90):
        out = task.generate(
            hash64(22690, "pages_timeline_event_date_gap_value", index),
            params={},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        answers[int(out.answer_gt.value)] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        accent_color_names[str(execution["accent_color_name"])] += 1
        endpoint_ids = tuple(str(value) for value in execution["endpoint_event_ids"])
        prompt_endpoint_ids = tuple(str(value) for value in execution["prompt_endpoint_event_ids"])
        prompt_orders["later_first" if prompt_endpoint_ids == tuple(reversed(endpoint_ids)) else "earlier_first"] += 1

    assert len(answers) >= 8
    assert set(prompt_orders.keys()) == {"earlier_first", "later_first"}
    assert set(scene_variants.keys()) == {"classic", "roadmap", "minimal"}
    assert set(style_variants.keys()) == set(SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS)
    assert set(accent_color_names.keys()) == set(SUPPORTED_TIME_ARTIFACT_COLOR_NAMES)


def test_resolve_text_stroke_fill_tracks_text_luminance() -> None:
    assert resolve_text_stroke_fill((255, 255, 255)) == (36, 42, 52)
    assert resolve_text_stroke_fill((44, 52, 64)) == (255, 255, 255)
