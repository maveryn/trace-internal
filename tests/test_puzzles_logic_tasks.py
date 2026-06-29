"""Behavior tests for Raven-matrix puzzle tasks."""

from __future__ import annotations

import json
from collections import Counter

from trace.tasks.puzzles.raven_matrix.raven_analogical_transform_label import (
    PuzzlesRavenMatrixAnalogicalTransformLabelTask,
)
from trace.tasks.puzzles.raven_matrix.raven_count_progression_label import (
    PuzzlesRavenMatrixCountProgressionLabelTask,
)
from trace.tasks.puzzles.raven_matrix.raven_position_progression_label import (
    PuzzlesRavenMatrixPositionProgressionLabelTask,
)
from trace.tasks.puzzles.raven_matrix.raven_set_operation_label import (
    PuzzlesRavenMatrixSetOperationLabelTask,
)
from trace.tasks.puzzles.raven_matrix.raven_spatial_transform_label import (
    PuzzlesRavenMatrixSpatialTransformLabelTask,
)
from tests.helpers import extract_prompt_json_example


def _panel_signature(panel_spec: dict) -> str:
    """Return a stable signature for one Raven panel spec."""

    return json.dumps(panel_spec, sort_keys=True, separators=(",", ":"))


def test_puzzle_raven_matrix_label_contract_matches_winning_option_panel() -> None:
    task_cases = (
        (PuzzlesRavenMatrixCountProgressionLabelTask(), "count_progression_matrix"),
        (PuzzlesRavenMatrixSpatialTransformLabelTask(), "spatial_transform_matrix"),
        (PuzzlesRavenMatrixSetOperationLabelTask(), "set_operation_matrix"),
        (PuzzlesRavenMatrixAnalogicalTransformLabelTask(), "analogical_transform_matrix"),
        (PuzzlesRavenMatrixPositionProgressionLabelTask(), "position_progression_matrix"),
    )
    scene_variants = (
        "raven_strip",
        "raven_card",
        "raven_outline",
    )

    for query_id_index, (task, rule_code) in enumerate(task_cases):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 25100 + (query_id_index * 20) + scene_index
            out = task.generate(
                seed,
                params={"scene_variant": scene_variant},
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            solver = execution["solver_trace"]
            annotation_bbox = [
                float(value) for value in out.annotation_gt.value
            ]

            assert str(out.query_id) == "single"
            assert str(trace["query_spec"]["query_id"]) == "single"
            assert str(execution["query_id"]) == "single"
            assert str(execution["raven_rule_code"]) == str(rule_code)
            assert out.answer_gt.type == "option_letter"
            assert out.annotation_gt.type == "bbox"
            assert sorted(out.prompt_variants.keys()) == [
                "answer_and_annotation",
                "answer_only",
            ]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (
                int(render["canvas_width"]),
                int(render["canvas_height"]),
            )
            assert int(execution["matrix_size"]) == 3
            assert int(execution["cell_count"]) == 9
            assert int(execution["visible_matrix_cell_count"]) == 8
            assert int(execution["option_count"]) == 6
            assert str(trace["query_spec"]["prompt_variant"]["query_key"]).startswith(
                "raven_"
            )
            assert str(execution["question_format"]).startswith("raven_")
            assert trace["projected_annotation"]["bbox"] == annotation_bbox
            assert [str(option_id) for option_id in execution["supporting_option_panel_ids"]] == [
                str(execution["correct_option_panel_id"])
            ]
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])
            assert str(out.answer_gt.value) in {"A", "B", "C", "D", "E", "F"}

            expected_bbox = [
                float(value)
                for value in render_map["option_panel_bboxes_px"][
                    str(execution["correct_option_panel_id"])
                ]
            ]
            assert annotation_bbox == expected_bbox
            assert all(
                float(bbox[0]) >= 0.0
                for bbox in render_map["matrix_cell_bboxes_px"].values()
            )
            assert all(
                float(bbox[1]) >= 0.0
                for bbox in render_map["matrix_cell_bboxes_px"].values()
            )
            assert all(
                float(bbox[2]) <= float(render["canvas_width"])
                for bbox in render_map["option_panel_bboxes_px"].values()
            )
            assert all(
                float(bbox[3]) <= float(render["canvas_height"])
                for bbox in render_map["option_panel_bboxes_px"].values()
            )

            matrix_rows = execution["matrix_rows"]
            matrix_panel_specs = execution["matrix_panel_specs"]
            unknown_cells = [
                cell
                for row in matrix_rows
                for cell in row
                if bool(cell["is_unknown"])
            ]
            assert len(unknown_cells) == 1
            assert str(unknown_cells[0]["cell_id"]) == "cell_2_2"
            assert int(execution["target_row_index"]) == 2
            assert int(execution["target_col_index"]) == 2
            assert execution["answer_panel_spec"] == matrix_panel_specs[2][2]

            option_specs = execution["option_specs"]
            assert len(option_specs) == 6
            assert [str(option["option_label"]) for option in option_specs] == [
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
            ]
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            assert len({_panel_signature(dict(option["panel_spec"])) for option in option_specs}) == 6
            winning_option = next(option for option in option_specs if bool(option["is_correct"]))
            assert str(winning_option["option_label"]) == str(out.answer_gt.value)
            assert str(winning_option["option_panel_id"]) == str(
                execution["correct_option_panel_id"]
            )
            assert dict(winning_option["panel_spec"]) == dict(execution["answer_panel_spec"])
            assert str(winning_option["panel_spec"]["panel_kind"]) in {
                "attribute",
                "count",
                "pattern",
            }

            assert str(solver["rule_type"]) == str(rule_code)
            assert str(solver["correct_option_label"]) == str(out.answer_gt.value)
            assert int(solver["correct_option_index"]) == int(
                execution["correct_option_index"]
            )
            if str(rule_code) == "count_progression_matrix":
                assert str(execution["answer_panel_spec"]["panel_kind"]) == "count"
                assert int(execution["answer_panel_spec"]["count"]) == int(
                    solver["count_table"][2][2]
                )
                assert int(execution["answer_panel_spec"]["count"]) == int(
                    solver["answer_count"]
                )
            elif str(rule_code) == "spatial_transform_matrix":
                assert str(execution["answer_panel_spec"]["panel_kind"]) == "pattern"
                assert execution["answer_panel_spec"]["cells"] == solver["answer_cells"]
                allowed_transforms = {"identity", "rot90", "rot180", "flip_h", "flip_v"}
                assert set(str(value) for value in solver["row_transforms"]) <= allowed_transforms
                assert set(str(value) for value in solver["column_transforms"]) <= allowed_transforms
            elif str(rule_code) == "set_operation_matrix":
                assert str(execution["answer_panel_spec"]["panel_kind"]) == "pattern"
                assert str(solver["operation"]) in {"union", "intersection", "xor"}
                assert execution["answer_panel_spec"]["cells"] == solver["answer_cells"]
            elif str(rule_code) == "analogical_transform_matrix":
                assert str(execution["answer_panel_spec"]["panel_kind"]) == "attribute"
                assert str(solver["transform_kind"]) in {
                    "shape_cycle",
                    "color_cycle",
                    "size_cycle",
                }
            else:
                assert str(execution["answer_panel_spec"]["panel_kind"]) == "pattern"
                assert len(execution["answer_panel_spec"]["cells"]) == 1
                assert execution["answer_panel_spec"]["cells"][0] == solver["answer_position"]


def test_puzzle_raven_prompt_examples_match_selected_variants() -> None:
    cases = (
        (
            PuzzlesRavenMatrixCountProgressionLabelTask(),
            {},
            {"annotation": [504, 650, 648, 822], "answer": "B"},
            {"answer": "B"},
        ),
        (
            PuzzlesRavenMatrixSpatialTransformLabelTask(),
            {},
            {"annotation": [668, 650, 812, 822], "answer": "D"},
            {"answer": "D"},
        ),
        (
            PuzzlesRavenMatrixSetOperationLabelTask(),
            {},
            {"annotation": [832, 650, 976, 822], "answer": "E"},
            {"answer": "E"},
        ),
        (
            PuzzlesRavenMatrixAnalogicalTransformLabelTask(),
            {},
            {"annotation": [996, 650, 1140, 822], "answer": "F"},
            {"answer": "F"},
        ),
        (
            PuzzlesRavenMatrixPositionProgressionLabelTask(),
            {},
            {"annotation": [12, 650, 156, 822], "answer": "A"},
            {"answer": "A"},
        ),
    )
    for index, (task, params, expected_answer_and_annotation, expected_answer_only) in enumerate(cases, start=25200):
        out = task.generate(index, params=params, max_attempts=10)
        answer_and_annotation = extract_prompt_json_example(
            out.prompt_variants["answer_and_annotation"]
        )
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation == expected_answer_and_annotation
        assert answer_only == expected_answer_only


def test_puzzle_raven_matrix_label_task_is_deterministic() -> None:
    task = PuzzlesRavenMatrixSpatialTransformLabelTask()
    params = {"scene_variant": "raven_card"}
    out_a = task.generate(25250, params=params, max_attempts=10)
    out_b = task.generate(25250, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_raven_sampler_index_covers_answer_letters_per_variant() -> None:
    task_cases = (
        PuzzlesRavenMatrixCountProgressionLabelTask(),
        PuzzlesRavenMatrixSpatialTransformLabelTask(),
        PuzzlesRavenMatrixSetOperationLabelTask(),
        PuzzlesRavenMatrixAnalogicalTransformLabelTask(),
        PuzzlesRavenMatrixPositionProgressionLabelTask(),
    )

    for task in task_cases:
        observed_letters = []
        for sampling_index in range(120):
            out = task.generate(
                25290 + sampling_index,
                params={},
                max_attempts=10,
            )
            observed_letters.append(str(out.answer_gt.value))
        letter_counts = Counter(observed_letters)
        assert set(letter_counts) == {"A", "B", "C", "D", "E", "F"}
        assert max(letter_counts.values()) <= 35
