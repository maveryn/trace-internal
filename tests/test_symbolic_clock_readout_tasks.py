"""Behavior tests for clock-readout task."""

from __future__ import annotations

from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.symbolic.clock.readout import SymbolicClockOffsetReadoutTask
from trace.tasks.shared.time_artifact_style import (
    SUPPORTED_TIME_ARTIFACT_CLOCK_COLOR_NAMES,
    SUPPORTED_TIME_ARTIFACT_CLOCK_STYLE_VARIANTS,
)
from trace.tasks.shared.time_format import (
    add_clock_minutes,
    add_clock_seconds,
    clock_total_minutes,
    format_clock_hhmm,
    format_clock_hhmmss,
)
from tests.helpers import extract_prompt_json_example


def test_symbolic_clock_readout_contract_matches_trace() -> None:
    task_cases = (
        (SymbolicClockOffsetReadoutTask(), "minutes", "after"),
        (SymbolicClockOffsetReadoutTask(), "minutes", "before"),
        (SymbolicClockOffsetReadoutTask(), "seconds", "after"),
        (SymbolicClockOffsetReadoutTask(), "seconds", "before"),
    )
    scene_variants = ("classic", "minimal", "outline")
    style_variants = ("studio", "accented", "marker")
    accent_colors = ("blue", "orange", "magenta")
    for query_id_index, (task, expected_unit, expected_direction) in enumerate(task_cases):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 20300 + (query_id_index * 20) + scene_index
            out = task.generate(
                seed,
                params={
                    "offset_unit": expected_unit,
                    "offset_direction": expected_direction,
                    "scene_variant": scene_variant,
                    "style_variant": style_variants[scene_index],
                    "accent_color_name": accent_colors[scene_index],
                    "delta_minutes": 25,
                    "delta_seconds": 25,
                },
                max_attempts=20,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            scene_entities = trace["scene_ir"]["entities"]
            hand_entities = [entity for entity in scene_entities if entity["entity_kind"] == "clock_hand"]

            assert out.answer_gt.type == "string"
            assert out.annotation_gt.type == "keyed_point_map"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
            expected_hand_count = 3 if expected_unit == "seconds" else 2
            expected_point_count = expected_hand_count + 1
            assert len(out.annotation_gt.value) == expected_point_count
            assert trace["scene_ir"]["scene_kind"] == "symbolic_clock_single"
            assert out.query_id == f"{expected_unit}_{expected_direction}"
            assert str(execution["query_id"]) == out.query_id
            assert str(execution["source_query_id"]) == "offset_time"
            assert str(execution["offset_unit"]) == expected_unit
            assert str(execution["offset_direction"]) == expected_direction
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["style_variant"]) == str(style_variants[scene_index])
            assert str(execution["accent_color_name"]) == str(accent_colors[scene_index])
            assert len(hand_entities) == expected_hand_count
            shown_total_minutes = int(execution["shown_total_minutes"])
            shown_total_seconds = int(execution["shown_total_seconds"])
            shown_text = (
                str(format_clock_hhmmss(int(shown_total_seconds)))
                if expected_unit == "seconds"
                else str(format_clock_hhmm(int(shown_total_minutes)))
            )
            assert str(execution["shown_time_text"]) == shown_text
            assert trace["projected_annotation"]["keyed_point_map"] == out.annotation_gt.value
            expected_points = {
                "clock_center",
                "hour_hand_tip",
                "minute_hand_tip",
            }
            if expected_unit == "seconds":
                expected_points.add("second_hand_tip")
            assert set(out.annotation_gt.value.keys()) == expected_points
            assert set(trace["projected_annotation"]["pixel_keyed_point_map"].keys()) == expected_points
            assert set(trace["projected_annotation"]["pixel_point_map"].keys()) == expected_points
            assert set(execution["supporting_point_roles"]) == expected_points
            assert len(trace["render_map"]["hand_bboxes_px"]) == expected_hand_count
            assert trace["render_map"]["annotation_source"] == "center_px_and_hand_tips_px"
            assert trace["render_spec"]["clock_style"]["font"]["source"] == "global_font_pool"
            assert trace["render_spec"]["clock_style"]["font"]["font_family"]
            assert str(trace["render_spec"]["clock_style"]["accent_color_name"]) == str(accent_colors[scene_index])
            assert str(trace["render_spec"]["clock_style"]["style_variant"]) == str(style_variants[scene_index])
            assert isinstance(trace["render_spec"]["clock_style"]["resolved_colors_rgb"], dict)
            assert int(execution["minute_support"][2]) == 5
            assert int(execution["second_support"][2]) == 5
            assert float(execution["min_hand_angle_gap_deg"]) == pytest.approx(10.0)

            if expected_unit == "minutes" and expected_direction == "after":
                expected = format_clock_hhmm(add_clock_minutes(int(shown_total_minutes), 25))
                assert str(out.answer_gt.value) == str(expected)
                assert int(execution["delta_minutes"]) == 25
            elif expected_unit == "minutes" and expected_direction == "before":
                expected = format_clock_hhmm(add_clock_minutes(int(shown_total_minutes), -25))
                assert str(out.answer_gt.value) == str(expected)
                assert int(execution["delta_minutes"]) == 25
            elif expected_unit == "seconds" and expected_direction == "after":
                expected = format_clock_hhmmss(add_clock_seconds(int(shown_total_seconds), 25))
                assert str(out.answer_gt.value) == str(expected)
                assert int(execution["delta_seconds"]) == 25
            else:
                expected = format_clock_hhmmss(add_clock_seconds(int(shown_total_seconds), -25))
                assert str(out.answer_gt.value) == str(expected)
                assert int(execution["delta_seconds"]) == 25


def test_symbolic_clock_prompt_examples_match_variant_offsets() -> None:
    minutes_example = {
        "clock_center": [320, 320],
        "hour_hand_tip": [430, 350],
        "minute_hand_tip": [484, 461],
    }
    seconds_example = {
        **minutes_example,
        "second_hand_tip": [140, 424],
    }
    expected = (
        (SymbolicClockOffsetReadoutTask(), "minutes", "after", (
            {"annotation": minutes_example, "answer": "03:50"},
            {"answer": "03:50"},
        )),
        (SymbolicClockOffsetReadoutTask(), "minutes", "before", (
            {"annotation": minutes_example, "answer": "03:00"},
            {"answer": "03:00"},
        )),
        (SymbolicClockOffsetReadoutTask(), "seconds", "after", (
            {"annotation": seconds_example, "answer": "03:26:05"},
            {"answer": "03:26:05"},
        )),
        (SymbolicClockOffsetReadoutTask(), "seconds", "before", (
            {"annotation": seconds_example, "answer": "03:25:15"},
            {"answer": "03:25:15"},
        )),
    )
    for index, (task, offset_unit, offset_direction, (expected_answer_and_annotation, expected_answer_only)) in enumerate(expected, start=20340):
        out = task.generate(
            index,
            params={"offset_unit": offset_unit, "offset_direction": offset_direction, "delta_minutes": 25, "delta_seconds": 25},
            max_attempts=20,
        )
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation == expected_answer_and_annotation
        assert answer_only == expected_answer_only


def test_symbolic_clock_balanced_sampling_defaults_cover_public_axes() -> None:
    task = SymbolicClockOffsetReadoutTask()
    offset_units: Counter[str] = Counter()
    offset_directions: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    for index in range(60):
        out = task.generate(
            hash64(20380, task.task_id, index),
            params={},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        assert str(execution["query_id"]) in {"minutes_after", "minutes_before"}
        offset_units[str(execution["offset_unit"])] += 1
        offset_directions[str(execution["offset_direction"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        accent_color_names[str(execution["accent_color_name"])] += 1
    assert set(offset_units.keys()) == {"minutes"}
    assert set(offset_directions.keys()) == {"after", "before"}
    assert set(scene_variants.keys()) == {"classic", "minimal", "outline"}
    assert set(style_variants.keys()) == set(SUPPORTED_TIME_ARTIFACT_CLOCK_STYLE_VARIANTS)
    assert set(accent_color_names.keys()) == set(SUPPORTED_TIME_ARTIFACT_CLOCK_COLOR_NAMES)


def test_symbolic_clock_marker_style_uses_dot_minor_ticks() -> None:
    task = SymbolicClockOffsetReadoutTask()
    out = task.generate(
        20400,
        params={
            "offset_unit": "minutes",
            "offset_direction": "after",
            "delta_minutes": 25,
            "scene_variant": "classic",
            "style_variant": "marker",
            "accent_color_name": "cyan",
        },
        max_attempts=20,
    )
    clock_style = out.trace_payload["render_spec"]["clock_style"]
    assert str(clock_style["style_variant"]) == "marker"
    assert str(clock_style["minor_tick_mode"]) == "dot"
    assert list(clock_style["resolved_colors_rgb"]["minute_hand"]) != list(clock_style["resolved_colors_rgb"]["hour_hand"])


def test_symbolic_clock_rejects_near_overlapping_explicit_time() -> None:
    task = SymbolicClockOffsetReadoutTask()
    with pytest.raises(ValueError):
        task.generate(
            20420,
            params={"offset_unit": "minutes", "shown_hour": 12, "shown_minute": 0},
            max_attempts=20,
        )
