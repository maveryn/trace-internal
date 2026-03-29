"""Behavior tests for temporal clock-readout task."""

from __future__ import annotations

from collections import Counter

import pytest

from trace.core.seed import hash64
from trace.tasks.temporal.clock.readout import TemporalClockReadoutTask
from trace.tasks.temporal.shared.style import (
    SUPPORTED_TEMPORAL_CLOCK_COLOR_NAMES,
    SUPPORTED_TEMPORAL_CLOCK_STYLE_VARIANTS,
)
from trace.tasks.temporal.shared.time_format import (
    add_clock_minutes,
    clock_total_minutes,
    format_clock_hhmm,
)
from tests.helpers import extract_prompt_json_example


def test_temporal_clock_readout_contract_matches_trace() -> None:
    task = TemporalClockReadoutTask()
    task_variants = ("shown_time", "minutes_after", "minutes_before")
    scene_variants = ("classic", "minimal", "outline")
    style_variants = ("studio", "accented", "marker")
    accent_colors = ("blue", "orange", "magenta")
    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 20300 + (variant_index * 20) + scene_index
            out = task.generate(
                seed,
                params={
                    "task_variant": task_variant,
                    "scene_variant": scene_variant,
                    "style_variant": style_variants[scene_index],
                    "accent_color_name": accent_colors[scene_index],
                    "delta_minutes": 25,
                },
                max_attempts=20,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            scene_entities = trace["scene_ir"]["entities"]
            hand_entities = [entity for entity in scene_entities if entity["entity_kind"] == "clock_hand"]

            assert out.answer_gt.type == "string"
            assert out.evidence_gt.type == "bbox_set"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert len(out.evidence_gt.value) == 2
            assert trace["scene_ir"]["scene_kind"] == "temporal_clock_single"
            assert str(execution["task_variant"]) == str(task_variant)
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["style_variant"]) == str(style_variants[scene_index])
            assert str(execution["accent_color_name"]) == str(accent_colors[scene_index])
            assert len(hand_entities) == 2
            assert set(out.complexity.complexity_components.keys()) == {
                "time_reading",
                "visual_scan",
                "ambiguity",
                "clutter",
            }
            assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())

            shown_total_minutes = int(execution["shown_total_minutes"])
            shown_text = str(format_clock_hhmm(int(shown_total_minutes)))
            assert str(execution["shown_time_text"]) == shown_text
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert set(trace["projected_evidence"]["pixel_point_map"].keys()) == {
                "clock_center",
                "hour_hand_tip",
                "minute_hand_tip",
            }
            assert len(trace["render_map"]["hand_bboxes_px"]) == 2
            assert str(trace["render_spec"]["clock_style"]["accent_color_name"]) == str(accent_colors[scene_index])
            assert str(trace["render_spec"]["clock_style"]["style_variant"]) == str(style_variants[scene_index])
            assert isinstance(trace["render_spec"]["clock_style"]["resolved_colors_rgb"], dict)
            assert int(execution["minute_support"][2]) == 5
            assert float(execution["min_hand_angle_gap_deg"]) == pytest.approx(10.0)

            if str(task_variant) == "shown_time":
                assert str(out.answer_gt.value) == shown_text
                assert execution["delta_minutes"] is None
            elif str(task_variant) == "minutes_after":
                expected = format_clock_hhmm(add_clock_minutes(int(shown_total_minutes), 25))
                assert str(out.answer_gt.value) == str(expected)
                assert int(execution["delta_minutes"]) == 25
            else:
                expected = format_clock_hhmm(add_clock_minutes(int(shown_total_minutes), -25))
                assert str(out.answer_gt.value) == str(expected)
                assert int(execution["delta_minutes"]) == 25


def test_temporal_clock_prompt_examples_match_variant_offsets() -> None:
    task = TemporalClockReadoutTask()
    expected = {
        "shown_time": (
            {"evidence": [[298, 270, 322, 405], [314, 148, 330, 406]], "answer": "03:25"},
            {"answer": "03:25"},
        ),
        "minutes_after": (
            {"evidence": [[298, 270, 322, 405], [314, 148, 330, 406]], "answer": "03:50"},
            {"answer": "03:50"},
        ),
        "minutes_before": (
            {"evidence": [[298, 270, 322, 405], [314, 148, 330, 406]], "answer": "03:00"},
            {"answer": "03:00"},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=20340):
        out = task.generate(
            index,
            params={"task_variant": task_variant, "delta_minutes": 25},
            max_attempts=20,
        )
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_temporal_clock_balanced_sampling_defaults_cover_variants() -> None:
    task = TemporalClockReadoutTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    for index in range(30):
        out = task.generate(
            hash64(20380, "temporal_clock_readout", index),
            params={"_sampling_index": index},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        accent_color_names[str(execution["accent_color_name"])] += 1
    assert set(task_variants.keys()) == {"shown_time", "minutes_after", "minutes_before"}
    assert set(scene_variants.keys()) == {"classic", "minimal", "outline"}
    assert set(style_variants.keys()) == set(SUPPORTED_TEMPORAL_CLOCK_STYLE_VARIANTS)
    assert set(accent_color_names.keys()) == set(SUPPORTED_TEMPORAL_CLOCK_COLOR_NAMES)


def test_temporal_clock_marker_style_uses_dot_minor_ticks() -> None:
    task = TemporalClockReadoutTask()
    out = task.generate(
        20400,
        params={
            "task_variant": "shown_time",
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


def test_temporal_clock_rejects_near_overlapping_explicit_time() -> None:
    task = TemporalClockReadoutTask()
    with pytest.raises(ValueError):
        task.generate(
            20420,
            params={"shown_hour": 12, "shown_minute": 0},
            max_attempts=20,
        )
