"""Behavior tests for clock-compare task."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.misc.clock.compare import MiscClockCompareTask
from trace.tasks.shared.time_artifact_style import (
    SUPPORTED_TIME_ARTIFACT_CLOCK_COLOR_NAMES,
    SUPPORTED_TIME_ARTIFACT_CLOCK_STYLE_VARIANTS,
)
from tests.helpers import extract_prompt_json_example


def test_misc_clock_compare_contract_matches_trace() -> None:
    task = MiscClockCompareTask()
    query_ids = ("earliest_time", "latest_time")
    scene_variants = ("classic", "outline")
    style_variants = ("studio", "marker")
    accent_colors = ("blue", "orange")
    for query_id_index, query_id in enumerate(query_ids):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 20500 + (query_id_index * 10) + scene_index
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
            shown_total_minutes_by_label = {
                str(label): int(total)
                for label, total in execution["shown_total_minutes_by_label"].items()
            }

            assert out.answer_gt.type == "string"
            assert out.annotation_gt.type == "bbox_set"
            assert len(out.annotation_gt.value) == 1
            expected_direction = "earliest" if str(query_id) == "earliest_time" else "latest"
            assert out.query_id == f"{expected_direction}_time_label"
            assert str(execution["query_id"]) == f"{expected_direction}_time_label"
            assert str(execution["source_query_id"]) == "time_extremum_label"
            assert str(execution["extremum_direction"]) == expected_direction
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["style_variant"]) == str(style_variants[scene_index])
            assert str(execution["accent_color_name"]) == str(accent_colors[scene_index])
            assert trace["scene_ir"]["scene_kind"] == "misc_clock_collection"
            assert 6 <= int(execution["clock_count"]) <= 12
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
            assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
            assert str(trace["render_map"]["winning_label"]) == str(out.answer_gt.value)
            assert trace["render_spec"]["post_image_noise"]["apply_prob"] == 0.5
            assert trace["render_spec"]["clock_style"]["font"]["source"] == "global_font_pool"
            assert trace["render_spec"]["clock_style"]["font"]["font_family"]

            expected_winner = (
                min(shown_total_minutes_by_label.items(), key=lambda item: item[1])[0]
                if expected_direction == "earliest"
                else max(shown_total_minutes_by_label.items(), key=lambda item: item[1])[0]
            )
            assert str(out.answer_gt.value) == str(expected_winner)
            assert out.annotation_gt.value[0] == trace["render_map"]["winning_clock_bbox_px"]


def test_misc_clock_compare_prompt_examples_match_variants() -> None:
    task = MiscClockCompareTask()
    expected = {
        "earliest_time": (
            {"annotation": [[368, 94, 552, 278]], "answer": "B"},
            {"answer": "B"},
        ),
        "latest_time": (
            {"annotation": [[368, 94, 552, 278]], "answer": "B"},
            {"answer": "B"},
        ),
    }
    for index, (query_id, (expected_answer_and_annotation, expected_answer_only)) in enumerate(expected.items(), start=20540):
        out = task.generate(
            index,
            params={"query_id": query_id},
            max_attempts=20,
        )
        answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation == expected_answer_and_annotation
        assert answer_only == expected_answer_only


def test_misc_clock_compare_explicit_clock_count_supports_twelve_clocks() -> None:
    task = MiscClockCompareTask()
    out = task.generate(
        20570,
        params={"query_id": "latest_time", "clock_count": 12},
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    assert int(execution["clock_count"]) == 12
    assert len(execution["clock_labels"]) == 12
    assert len(set(execution["clock_labels"])) == 12
    assert str(out.answer_gt.value) in set(execution["clock_labels"])


def test_misc_clock_compare_balanced_sampling_defaults_cover_axes() -> None:
    task = MiscClockCompareTask()
    query_ids: Counter[str] = Counter()
    extremum_directions: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    accent_color_names: Counter[str] = Counter()
    clock_counts: Counter[int] = Counter()
    winner_labels: Counter[str] = Counter()
    for index in range(90):
        out = task.generate(
            hash64(20580, "misc_clock_compare", index),
            params={},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        query_ids[str(execution["query_id"])] += 1
        extremum_directions[str(execution["extremum_direction"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        accent_color_names[str(execution["accent_color_name"])] += 1
        clock_counts[int(execution["clock_count"])] += 1
        winner_labels[str(execution["winner_label"])] += 1

    assert set(query_ids.keys()) == {"earliest_time_label", "latest_time_label"}
    assert set(extremum_directions.keys()) == {"earliest", "latest"}
    assert set(scene_variants.keys()) == {"classic", "minimal", "outline"}
    assert set(style_variants.keys()) == set(SUPPORTED_TIME_ARTIFACT_CLOCK_STYLE_VARIANTS)
    assert set(accent_color_names.keys()) == set(SUPPORTED_TIME_ARTIFACT_CLOCK_COLOR_NAMES)
    assert set(clock_counts.keys()) == {6, 7, 8, 9, 10, 11, 12}
    assert set(winner_labels.keys()) == {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"}
