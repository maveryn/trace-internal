"""Behavior tests for misc abacus readout tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.misc.abacus.match_panel import TASK_ID as MATCH_TASK_ID
from trace.tasks.misc.abacus.match_panel import MiscAbacusTargetValueMatchTask
from trace.tasks.misc.abacus.readout import TASK_ID, MiscAbacusDisplayedValueReadoutTask
from tests.helpers import extract_prompt_json_example


def _active_count_for_digit(digit: int) -> int:
    return (1 if int(digit) >= 5 else 0) + (int(digit) % 5)


def _vertical_gap(upper_bbox: list[float], lower_bbox: list[float]) -> float:
    return round(float(lower_bbox[1]) - float(upper_bbox[3]), 3)


def _bbox_center(bbox: list[float]) -> list[float]:
    return [round((float(bbox[0]) + float(bbox[2])) * 0.5, 3), round((float(bbox[1]) + float(bbox[3])) * 0.5, 3)]


def test_misc_abacus_displayed_value_contract_matches_trace() -> None:
    task = MiscAbacusDisplayedValueReadoutTask()
    cases = (0, 5, 40, 207, 603, 999)
    for index, answer_value in enumerate(cases):
        out = task.generate(
            50100 + index,
            params={
                "answer_value": answer_value,
                "scene_variant": "clean_card",
            },
            max_attempts=5,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.answer_gt.type == "integer"
        assert out.answer_gt.value == int(answer_value)
        assert out.annotation_gt.type == "keyed_point_set_map"
        assert set(out.annotation_gt.value.keys()) == {
            "hundreds_active_beads",
            "tens_active_beads",
            "ones_active_beads",
        }
        assert trace["scene_ir"]["scene_kind"] == "abacus_readout"
        assert out.scene_id == "abacus_readout"
        assert out.query_id == "displayed_value_readout"
        assert str(execution["query_id"]) == "displayed_value_readout"
        assert int(execution["answer_value"]) == int(answer_value)
        assert trace["projected_annotation"]["keyed_point_set_map"] == out.annotation_gt.value
        assert trace["projected_annotation"]["pixel_keyed_point_set_map"] == out.annotation_gt.value
        assert trace["render_map"]["active_bead_points_by_column_px"] == out.annotation_gt.value
        assert trace["render_spec"]["abacus_style"]["active_inactive_bead_color_shared"] is True
        assert trace["render_spec"]["abacus_style"]["active_bead_rgb"] == trace["render_spec"]["abacus_style"]["inactive_bead_rgb"]
        assert trace["render_spec"]["abacus_style"]["renderer"] == "abacus_readout_v0"
        assert trace["render_spec"]["post_image_noise"]["apply_prob"] == 0.18
        assert set(out.complexity.complexity_components.keys()) == {
            "visual_scan",
            "reasoning_load",
            "scene_variant_load",
        }

        digits = [int(char) for char in f"{int(answer_value):03d}"]
        expected_counts = {
            "hundreds_active_beads": _active_count_for_digit(digits[0]),
            "tens_active_beads": _active_count_for_digit(digits[1]),
            "ones_active_beads": _active_count_for_digit(digits[2]),
        }
        assert {key: len(value) for key, value in out.annotation_gt.value.items()} == expected_counts
        assert out.annotation_gt.value == {
            key: [_bbox_center(bbox) for bbox in bboxes]
            for key, bboxes in trace["render_map"]["active_bead_bboxes_by_column_px"].items()
        }
        assert execution["digits_by_role"] == {
            "hundreds": digits[0],
            "tens": digits[1],
            "ones": digits[2],
        }
        assert int(execution["place_values_by_role"]["hundreds"]) == 100
        assert int(execution["place_values_by_role"]["tens"]) == 10
        assert int(execution["place_values_by_role"]["ones"]) == 1


def test_misc_abacus_lower_inactive_beads_are_visually_separated_from_active_group() -> None:
    task = MiscAbacusDisplayedValueReadoutTask()
    out = task.generate(
        50316,
        params={"answer_value": 316, "scene_variant": "worksheet"},
        max_attempts=5,
    )
    trace = out.trace_payload
    bead_bboxes = trace["render_map"]["bead_bboxes_px"]
    active_by_column = trace["render_map"]["active_bead_ids_by_column"]

    assert out.image.size == (980, 760)
    assert active_by_column["tens"] == ["column_tens_lower_1"]
    assert active_by_column["hundreds"] == [
        "column_hundreds_lower_1",
        "column_hundreds_lower_2",
        "column_hundreds_lower_3",
    ]
    assert _vertical_gap(bead_bboxes["column_tens_lower_1"], bead_bboxes["column_tens_lower_2"]) >= 60.0
    assert _vertical_gap(bead_bboxes["column_hundreds_lower_3"], bead_bboxes["column_hundreds_lower_4"]) >= 60.0


def test_misc_abacus_prompt_examples_match_contract() -> None:
    task = MiscAbacusDisplayedValueReadoutTask()
    out = task.generate(
        50120,
        params={"answer_value": 603, "scene_variant": "wood_frame"},
        max_attempts=5,
    )
    answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert set(answer_and_annotation.keys()) == {"annotation", "answer"}
    assert set(answer_and_annotation["annotation"].keys()) == {
        "hundreds_active_beads",
        "tens_active_beads",
        "ones_active_beads",
    }
    assert answer_and_annotation["answer"] == 603
    assert answer_only == {"answer": 603}


def test_misc_abacus_balanced_sampling_defaults_cover_scene_axis() -> None:
    task = MiscAbacusDisplayedValueReadoutTask()
    scene_variants: Counter[str] = Counter()
    answers: set[int] = set()
    for index in range(36):
        out = task.generate(
            hash64(50140, TASK_ID, index),
            params={},
            max_attempts=5,
        )
        execution = out.trace_payload["execution_trace"]
        scene_variants[str(execution["scene_variant"])] += 1
        answers.add(int(execution["answer_value"]))
        assert str(execution["query_id"]) == "displayed_value_readout"
        assert 0 <= int(execution["answer_value"]) <= 999
    assert set(scene_variants.keys()) == {"clean_card", "wood_frame", "worksheet"}
    assert len(answers) > 20


def test_misc_abacus_match_panel_contract_matches_trace() -> None:
    task = MiscAbacusTargetValueMatchTask()
    out = task.generate(
        61100,
        params={
            "target_value": 316,
            "answer_label": "E",
            "scene_variant": "worksheet",
        },
        max_attempts=5,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "E"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 1
    assert out.scene_id == "abacus_match_panel"
    assert out.query_id == "target_value_match_label"
    assert trace["scene_ir"]["scene_kind"] == "abacus_match_panel"
    assert str(execution["query_id"]) == "target_value_match_label"
    assert int(execution["target_value"]) == 316
    assert execution["target_digits"] == [3, 1, 6]
    assert str(execution["correct_label"]) == "E"
    assert int(execution["option_values_by_label"]["E"]) == 316
    assert list(trace["projected_annotation"]["bbox_set"]) == out.annotation_gt.value
    assert list(trace["projected_annotation"]["pixel_bbox_set"]) == out.annotation_gt.value
    assert trace["render_map"]["selected_option_card_bbox_px"] == out.annotation_gt.value[0]
    assert trace["render_spec"]["abacus_style"]["renderer"] == "abacus_match_panel_v0"
    assert trace["render_spec"]["abacus_style"]["active_inactive_bead_color_shared"] is True
    assert trace["render_spec"]["abacus_style"]["active_bead_rgb"] == trace["render_spec"]["abacus_style"]["inactive_bead_rgb"]
    assert trace["render_spec"]["post_image_noise"]["apply_prob"] == 0.18
    assert out.image.size == (1200, 760)
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "reasoning_load",
        "scene_variant_load",
    }
    assert len(execution["option_labels"]) == 6
    assert len(set(execution["option_values_by_label"].values())) == 6


def test_misc_abacus_match_panel_prompt_examples_match_contract() -> None:
    task = MiscAbacusTargetValueMatchTask()
    out = task.generate(
        61120,
        params={"target_value": 742, "answer_label": "B"},
        max_attempts=5,
    )
    answer_and_annotation = extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
    assert answer_and_annotation == {
        "annotation": [[430, 74, 770, 354]],
        "answer": "B",
    }
    assert answer_only == {"answer": "B"}
    assert "742" in out.prompt


def test_misc_abacus_match_panel_balanced_sampling_defaults_cover_axes() -> None:
    task = MiscAbacusTargetValueMatchTask()
    scene_variants: Counter[str] = Counter()
    answer_labels: Counter[str] = Counter()
    target_values: set[int] = set()
    for index in range(72):
        out = task.generate(
            hash64(61140, MATCH_TASK_ID, index),
            params={},
            max_attempts=5,
        )
        execution = out.trace_payload["execution_trace"]
        scene_variants[str(execution["scene_variant"])] += 1
        answer_labels[str(execution["correct_label"])] += 1
        target_values.add(int(execution["target_value"]))
        assert int(execution["option_values_by_label"][str(execution["correct_label"])]) == int(execution["target_value"])
        assert list(execution["option_values_by_label"].values()).count(int(execution["target_value"])) == 1
    assert set(scene_variants.keys()) == {"clean_card", "wood_frame", "worksheet"}
    assert set(answer_labels.keys()) == {"A", "B", "C", "D", "E", "F"}
    assert len(target_values) > 50
