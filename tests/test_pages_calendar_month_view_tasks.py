"""Behavior tests for the month-view calendar task."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.pages.calendar.month_view import (
    PagesCalendarMarkedDayClassCountTask,
    PagesCalendarWeekdayOccurrenceDateTask,
    SUPPORTED_PAGE_CALENDAR_LAYOUT_MODES,
    SUPPORTED_PAGE_CALENDAR_TITLE_MODES,
)
from trace.tasks.shared.time_artifact_style import (
    SUPPORTED_TIME_ARTIFACT_COLOR_NAMES,
    SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS,
)
from tests.helpers import extract_prompt_json_example


def test_pages_calendar_month_view_contract_matches_trace() -> None:
    task_cases = (
        (PagesCalendarWeekdayOccurrenceDateTask(), None),
        (PagesCalendarMarkedDayClassCountTask(), "weekend"),
        (PagesCalendarMarkedDayClassCountTask(), "weekday"),
    )
    scene_variants = ("classic", "outline")
    style_variants = ("studio", "marker")
    accent_colors = ("blue", "orange")
    for query_id_index, (task, marked_day_class) in enumerate(task_cases):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 21800 + (query_id_index * 10) + scene_index
            params = {
                "scene_variant": scene_variant,
                "style_variant": style_variants[scene_index],
                "accent_color_name": accent_colors[scene_index],
                "layout_mode": "left_with_side_note" if scene_index == 0 else "top_with_bottom_note",
                "title_mode": "none" if scene_index == 0 else "generic",
            }
            if marked_day_class is not None:
                params["marked_day_class"] = marked_day_class
            out = task.generate(
                seed,
                params=params,
                max_attempts=20,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]

            assert out.answer_gt.type == "integer"
            assert out.evidence_gt.type == "bbox_set"
            expected_source_variant = (
                "count_marked_day_class"
                if marked_day_class is not None
                else "date_of_weekday_occurrence"
            )
            assert str(execution["source_query_id"]) == expected_source_variant
            if marked_day_class is not None:
                assert out.query_id == f"count_marked_{marked_day_class}_days"
                assert str(execution["marked_day_class"]) == marked_day_class
            else:
                assert out.query_id == "date_of_weekday_occurrence"
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["style_variant"]) == str(style_variants[scene_index])
            assert str(execution["accent_color_name"]) == str(accent_colors[scene_index])
            assert str(execution["layout_mode"]) == str(params["layout_mode"])
            assert str(execution["title_mode"]) == str(params["title_mode"])
            assert str(execution["month_name"]) not in out.prompt
            assert str(execution["year"]) not in out.prompt
            assert trace["scene_ir"]["scene_kind"] == "pages_month_calendar"
            panel_bbox = trace["render_map"]["calendar_panel_bbox_px"]
            assert 0 <= float(panel_bbox[0]) < float(panel_bbox[2]) <= 860
            assert 0 <= float(panel_bbox[1]) < float(panel_bbox[3]) <= 760
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
            if marked_day_class is None:
                assert len(out.evidence_gt.value) == 1
                assert int(out.answer_gt.value) == int(evidence_dates[0])
            else:
                weekend_indices = {int(value) for value in execution["weekend_weekday_indices"]}
                evidence_weekday_indices = {
                    (int(execution["start_weekday_index"]) + int(day) - 1) % 7 for day in evidence_dates
                }
                assert int(out.answer_gt.value) == len(evidence_dates)
                assert all(int(day) in set(execution["marked_dates"]) for day in evidence_dates)
                if str(execution["marked_day_class"]) == "weekend":
                    assert evidence_weekday_indices.issubset(weekend_indices)
                else:
                    assert not evidence_weekday_indices.intersection(weekend_indices)


def test_pages_calendar_month_view_prompt_examples_match_variants() -> None:
    expected = (
        (PagesCalendarWeekdayOccurrenceDateTask(), {}, (
            {"evidence": [[354, 256, 456, 352]], "answer": 18},
            {"answer": 18},
        )),
        (PagesCalendarMarkedDayClassCountTask(), {"marked_day_class": "weekend"}, (
            {
                "evidence": [[148, 352, 250, 448], [560, 352, 662, 448]],
                "answer": 2,
            },
            {"answer": 2},
        )),
        (PagesCalendarMarkedDayClassCountTask(), {"marked_day_class": "weekday"}, (
            {
                "evidence": [[148, 352, 250, 448], [560, 352, 662, 448]],
                "answer": 2,
            },
            {"answer": 2},
        )),
    )
    for index, (task, params, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected, start=21840):
        out = task.generate(
            index,
            params=params,
            max_attempts=20,
        )
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_pages_calendar_month_view_balanced_sampling_defaults_cover_axes() -> None:
    tasks = (PagesCalendarWeekdayOccurrenceDateTask(), PagesCalendarMarkedDayClassCountTask())
    query_ids: Counter[str] = Counter()
    marked_day_classes: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    layout_modes: Counter[str] = Counter()
    title_modes: Counter[str] = Counter()
    row_counts: Counter[int] = Counter()
    for task in tasks:
        for index in range(90):
            out = task.generate(
                hash64(21880, task.task_id, index),
                params={},
                max_attempts=20,
            )
            execution = out.trace_payload["execution_trace"]
            query_ids[str(execution["source_query_id"])] += 1
            if execution["marked_day_class"] is not None:
                marked_day_classes[str(execution["marked_day_class"])] += 1
            scene_variants[str(execution["scene_variant"])] += 1
            style_variants[str(execution["style_variant"])] += 1
            accent_color_names[str(execution["accent_color_name"])] += 1
            layout_modes[str(execution["layout_mode"])] += 1
            title_modes[str(execution["title_mode"])] += 1
            row_counts[int(execution["row_count"])] += 1

    assert set(query_ids.keys()) == {
        "date_of_weekday_occurrence",
        "count_marked_day_class",
    }
    assert set(marked_day_classes.keys()) == {"weekend", "weekday"}
    assert set(scene_variants.keys()) == {"classic", "minimal", "outline"}
    assert set(style_variants.keys()) == set(SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS)
    assert set(accent_color_names.keys()) == set(SUPPORTED_TIME_ARTIFACT_COLOR_NAMES)
    assert set(layout_modes.keys()) == set(SUPPORTED_PAGE_CALENDAR_LAYOUT_MODES)
    assert set(title_modes.keys()) == set(SUPPORTED_PAGE_CALENDAR_TITLE_MODES)
    assert set(row_counts.keys()).issubset({4, 5, 6})
