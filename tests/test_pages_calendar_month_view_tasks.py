"""Behavior tests for the month-view calendar task."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.pages.calendar.month_view import (
    PagesCalendarMarkedDayClassCountTask,
    PagesCalendarWorkdayOffsetDateTask,
    PagesCalendarWeekdayOccurrenceDateTask,
    SUPPORTED_PAGE_CALENDAR_LAYOUT_MODES,
    SUPPORTED_PAGE_CALENDAR_SURFACE_MODES,
    SUPPORTED_PAGE_CALENDAR_TEXT_COLOR_MODES,
    SUPPORTED_PAGE_CALENDAR_TITLE_MODES,
)
from trace.tasks.shared.time_artifact_style import (
    SUPPORTED_TIME_ARTIFACT_COLOR_NAMES,
    SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS,
    build_time_artifact_calendar_theme,
)
from trace.tasks.shared.text_legibility import READ_REQUIRED_TEXT_MIN_CONTRAST_RATIO, contrast_ratio
from tests.helpers import extract_prompt_json_example


def _rgb_saturation(rgb: tuple[int, int, int]) -> float:
    channels = [max(0.0, min(1.0, float(channel) / 255.0)) for channel in rgb]
    high = max(channels)
    low = min(channels)
    if high <= 0.0:
        return 0.0
    return float((high - low) / high)


def _weekday_target_date(
    *,
    reference_date: int,
    offset: int,
    direction: str,
    days_in_month: int,
    start_weekday_index: int,
    weekend_weekday_indices: list[int],
) -> int:
    weekend_indices = {int(value) for value in weekend_weekday_indices}
    workdays = [
        int(day)
        for day in range(1, int(days_in_month) + 1)
        if ((int(start_weekday_index) + int(day) - 1) % 7) not in weekend_indices
    ]
    reference_index = workdays.index(int(reference_date))
    target_index = int(reference_index + int(offset)) if str(direction) == "after" else int(reference_index - int(offset))
    return int(workdays[int(target_index)])


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
                "surface_mode": "dark" if scene_index == 0 else "light",
                "text_color_mode": "cool" if scene_index == 0 else "warm",
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
            assert out.annotation_gt.type == "bbox_set"
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
            assert str(execution["surface_mode"]) == str(params["surface_mode"])
            assert str(execution["text_color_mode"]) == str(params["text_color_mode"])
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
            assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value

            annotation_dates = [int(day) for day in execution["annotation_dates"]]
            if marked_day_class is None:
                assert len(out.annotation_gt.value) == 1
                assert int(out.answer_gt.value) == int(annotation_dates[0])
            else:
                weekend_indices = {int(value) for value in execution["weekend_weekday_indices"]}
                annotation_weekday_indices = {
                    (int(execution["start_weekday_index"]) + int(day) - 1) % 7 for day in annotation_dates
                }
                assert int(out.answer_gt.value) == len(annotation_dates)
                assert all(int(day) in set(execution["marked_dates"]) for day in annotation_dates)
                if str(execution["marked_day_class"]) == "weekend":
                    assert annotation_weekday_indices.issubset(weekend_indices)
                else:
                    assert not annotation_weekday_indices.intersection(weekend_indices)


def test_pages_calendar_workday_offset_date_contract_matches_trace() -> None:
    task = PagesCalendarWorkdayOffsetDateTask()
    for index, query_id in enumerate(("workday_after_offset_date", "workday_before_offset_date")):
        out = task.generate(
            21832 + index,
            params={
                "query_id": query_id,
                "scene_variant": "outline",
                "style_variant": "accented",
                "accent_color_name": "green",
                "layout_mode": "center_clean",
                "title_mode": "full_month_year",
                "surface_mode": "light",
                "text_color_mode": "accent",
            },
            max_attempts=20,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render_map = trace["render_map"]
        reference_date = int(execution["reference_date"])
        target_date = int(execution["target_date"])
        expected_target = _weekday_target_date(
            reference_date=reference_date,
            offset=int(execution["workday_offset"]),
            direction=str(execution["workday_direction"]),
            days_in_month=int(execution["days_in_month"]),
            start_weekday_index=int(execution["start_weekday_index"]),
            weekend_weekday_indices=[int(value) for value in execution["weekend_weekday_indices"]],
        )

        assert out.query_id == str(query_id)
        assert str(execution["query_id"]) == str(query_id)
        assert str(execution["source_query_id"]) == str(query_id)
        assert out.answer_gt.type == "integer"
        assert out.annotation_gt.type == "keyed_bbox_map"
        assert int(out.answer_gt.value) == int(target_date) == int(expected_target)
        assert execution["marked_dates"] == [reference_date]
        assert execution["annotation_dates"] == [reference_date, target_date]
        assert set(out.annotation_gt.value.keys()) == {"reference_date", "target_date"}
        assert out.annotation_gt.value["reference_date"] == render_map["date_cells_by_day"][str(reference_date)]
        assert out.annotation_gt.value["target_date"] == render_map["date_cells_by_day"][str(target_date)]
        assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value


def test_pages_calendar_month_view_prompt_examples_match_variants() -> None:
    expected = (
        (PagesCalendarWeekdayOccurrenceDateTask(), {}, (
            {"annotation": [[354, 256, 456, 352]], "answer": 18},
            {"answer": 18},
        )),
        (PagesCalendarMarkedDayClassCountTask(), {"marked_day_class": "weekend"}, (
            {
                "annotation": [[148, 352, 250, 448], [560, 352, 662, 448]],
                "answer": 2,
            },
            {"answer": 2},
        )),
        (PagesCalendarMarkedDayClassCountTask(), {"marked_day_class": "weekday"}, (
            {
                "annotation": [[148, 352, 250, 448], [560, 352, 662, 448]],
                "answer": 2,
            },
            {"answer": 2},
        )),
        (PagesCalendarWorkdayOffsetDateTask(), {"query_id": "workday_after_offset_date"}, (
            {
                "annotation": {
                    "reference_date": [354, 256, 456, 352],
                    "target_date": [560, 256, 662, 352],
                },
                "answer": 20,
            },
            {"answer": 20},
        )),
        (PagesCalendarWorkdayOffsetDateTask(), {"query_id": "workday_before_offset_date"}, (
            {
                "annotation": {
                    "reference_date": [560, 256, 662, 352],
                    "target_date": [354, 256, 456, 352],
                },
                "answer": 18,
            },
            {"answer": 18},
        )),
    )
    for index, (task, params, (expected_answer_and_annotation, expected_answer_only)) in enumerate(expected, start=21840):
        out = task.generate(
            index,
            params=params,
            max_attempts=20,
        )
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation == expected_answer_and_annotation
        assert answer_only == expected_answer_only


def test_pages_calendar_workday_offset_date_balanced_sampling_defaults_cover_query_axes() -> None:
    task = PagesCalendarWorkdayOffsetDateTask()
    query_ids: Counter[str] = Counter()
    offsets: Counter[int] = Counter()
    directions: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    layout_modes: Counter[str] = Counter()
    for index in range(120):
        out = task.generate(
            hash64(21870, task.task_id, index),
            params={},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        query_ids[str(execution["source_query_id"])] += 1
        offsets[int(execution["workday_offset"])] += 1
        directions[str(execution["workday_direction"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        layout_modes[str(execution["layout_mode"])] += 1

    assert set(query_ids.keys()) == {"workday_after_offset_date", "workday_before_offset_date"}
    assert set(directions.keys()) == {"after", "before"}
    assert set(offsets.keys()) == {2, 3, 4, 5, 6, 7}
    assert set(scene_variants.keys()) == {"classic", "minimal", "outline"}
    assert set(layout_modes.keys()) == set(SUPPORTED_PAGE_CALENDAR_LAYOUT_MODES)


def test_pages_calendar_month_view_balanced_sampling_defaults_cover_axes() -> None:
    tasks = (PagesCalendarWeekdayOccurrenceDateTask(), PagesCalendarMarkedDayClassCountTask())
    query_ids: Counter[str] = Counter()
    marked_day_classes: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    layout_modes: Counter[str] = Counter()
    title_modes: Counter[str] = Counter()
    surface_modes: Counter[str] = Counter()
    text_color_modes: Counter[str] = Counter()
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
            surface_modes[str(execution["surface_mode"])] += 1
            text_color_modes[str(execution["text_color_mode"])] += 1
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
    assert set(surface_modes.keys()) == set(SUPPORTED_PAGE_CALENDAR_SURFACE_MODES)
    assert min(surface_modes.values()) >= 70
    assert set(text_color_modes.keys()) == set(SUPPORTED_PAGE_CALENDAR_TEXT_COLOR_MODES)
    assert set(row_counts.keys()).issubset({4, 5, 6})


def test_pages_calendar_dark_surface_theme_keeps_required_text_readable() -> None:
    for accent_color_name in SUPPORTED_TIME_ARTIFACT_COLOR_NAMES:
        for style_variant in SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS:
            for text_color_mode in SUPPORTED_PAGE_CALENDAR_TEXT_COLOR_MODES:
                theme = build_time_artifact_calendar_theme(
                    accent_color_name=str(accent_color_name),
                    style_variant=str(style_variant),
                    surface_mode="dark",
                    text_color_mode=str(text_color_mode),
                )
                assert str(theme.surface_mode) == "dark"
                assert str(theme.text_color_mode) == str(text_color_mode)
                assert max(theme.panel_fill_rgb) <= 70
                assert contrast_ratio(theme.title_text_rgb, theme.panel_fill_rgb) >= READ_REQUIRED_TEXT_MIN_CONTRAST_RATIO
                assert contrast_ratio(theme.date_text_rgb, theme.panel_fill_rgb) >= READ_REQUIRED_TEXT_MIN_CONTRAST_RATIO
                assert contrast_ratio(theme.weekday_text_rgb, theme.weekday_fill_rgb) >= READ_REQUIRED_TEXT_MIN_CONTRAST_RATIO
                marker_surface = theme.marker_fill_rgb if str(theme.marker_kind) == "fill" else theme.panel_fill_rgb
                assert contrast_ratio(theme.marker_text_rgb, marker_surface) >= READ_REQUIRED_TEXT_MIN_CONTRAST_RATIO
                assert _rgb_saturation(theme.title_text_rgb) >= 0.20
                assert _rgb_saturation(theme.weekday_text_rgb) >= 0.20
                assert _rgb_saturation(theme.date_text_rgb) >= 0.20
                assert _rgb_saturation(theme.marker_text_rgb) >= 0.20


def test_pages_calendar_light_surface_theme_keeps_required_text_readable() -> None:
    for accent_color_name in SUPPORTED_TIME_ARTIFACT_COLOR_NAMES:
        for style_variant in SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS:
            for text_color_mode in SUPPORTED_PAGE_CALENDAR_TEXT_COLOR_MODES:
                theme = build_time_artifact_calendar_theme(
                    accent_color_name=str(accent_color_name),
                    style_variant=str(style_variant),
                    surface_mode="light",
                    text_color_mode=str(text_color_mode),
                )
                assert str(theme.surface_mode) == "light"
                assert str(theme.text_color_mode) == str(text_color_mode)
                assert min(theme.panel_fill_rgb) >= 220
                assert contrast_ratio(theme.title_text_rgb, theme.panel_fill_rgb) >= READ_REQUIRED_TEXT_MIN_CONTRAST_RATIO
                assert contrast_ratio(theme.date_text_rgb, theme.panel_fill_rgb) >= READ_REQUIRED_TEXT_MIN_CONTRAST_RATIO
                assert contrast_ratio(theme.weekday_text_rgb, theme.weekday_fill_rgb) >= READ_REQUIRED_TEXT_MIN_CONTRAST_RATIO
                marker_surface = theme.marker_fill_rgb if str(theme.marker_kind) == "fill" else theme.panel_fill_rgb
                assert contrast_ratio(theme.marker_text_rgb, marker_surface) >= READ_REQUIRED_TEXT_MIN_CONTRAST_RATIO
                assert _rgb_saturation(theme.title_text_rgb) >= 0.20
                assert _rgb_saturation(theme.weekday_text_rgb) >= 0.20
                assert _rgb_saturation(theme.date_text_rgb) >= 0.20
                assert _rgb_saturation(theme.marker_text_rgb) >= 0.20
