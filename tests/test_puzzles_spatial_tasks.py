"""Behavior tests for puzzle spatial tasks."""

from __future__ import annotations

from itertools import permutations

from trace.tasks.puzzles.spatial.cube_view_label import PuzzlesSpatialCubeViewLabelTask
from tests.helpers import extract_prompt_json_example


_FACE_NORMALS = {
    "U": (0, 0, 1),
    "D": (0, 0, -1),
    "F": (0, 1, 0),
    "B": (0, -1, 0),
    "R": (1, 0, 0),
    "L": (-1, 0, 0),
}
_NORMAL_TO_FACE = {tuple(value): key for key, value in _FACE_NORMALS.items()}


def _dot(lhs: tuple[int, int, int], rhs: tuple[int, int, int]) -> int:
    """Return one integer dot product for cube face normals."""

    return int(sum(int(a) * int(b) for a, b in zip(lhs, rhs)))


def _cross(lhs: tuple[int, int, int], rhs: tuple[int, int, int]) -> tuple[int, int, int]:
    """Return one integer cross product for cube face normals."""

    lx, ly, lz = lhs
    rx, ry, rz = rhs
    return (
        int((ly * rz) - (lz * ry)),
        int((lz * rx) - (lx * rz)),
        int((lx * ry) - (ly * rx)),
    )


def _valid_triplets(face_object_types: dict[str, str]) -> list[tuple[str, str, str]]:
    """Enumerate every valid visible `(top, front, right)` cube view."""

    triplets = []
    for top_face, top_normal in _FACE_NORMALS.items():
        for front_face, front_normal in _FACE_NORMALS.items():
            if int(_dot(top_normal, front_normal)) != 0:
                continue
            right_face = str(_NORMAL_TO_FACE[_cross(front_normal, top_normal)])
            triplets.append(
                (
                    str(face_object_types[str(top_face)]),
                    str(face_object_types[str(front_face)]),
                    str(face_object_types[str(right_face)]),
                )
            )
    return triplets


def test_puzzle_spatial_cube_view_label_contract_matches_winning_option_panel() -> None:
    task = PuzzlesSpatialCubeViewLabelTask()
    task_variants = (
        "same_cube_view",
        "impossible_cube_view",
    )
    scene_variants = (
        "cube_strip",
        "cube_card",
        "cube_outline",
    )

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 24720 + (variant_index * 20) + scene_index
            out = task.generate(
                seed,
                params={"task_variant": task_variant, "scene_variant": scene_variant},
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            solver = execution["solver_trace"]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            face_object_types = {str(key): str(value) for key, value in execution["face_object_types"].items()}
            reference_triplet = [str(value) for value in execution["reference_triplet"]]
            expected_valid = _valid_triplets(face_object_types)
            expected_invalid = [
                tuple(str(value) for value in triplet)
                for triplet in permutations(face_object_types.values(), 3)
                if tuple(str(value) for value in triplet) not in set(expected_valid)
            ]

            assert str(out.task_variant) == str(task_variant)
            assert out.answer_gt.type == "option_letter"
            assert out.evidence_gt.type == "bbox_set"
            assert len(evidence_bboxes) == 1
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert int(execution["option_count"]) == 6
            assert int(execution["visible_face_count"]) == 3
            assert str(execution["question_format"]) == "cube_view_mcq"
            assert str(execution["view_family"]) == "cube_view_with_opposite_face_hints"
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert str(out.answer_gt.value) == str(execution["answer_option_label"])
            assert str(out.answer_gt.value) in {"A", "B", "C", "D", "E", "F"}

            expected_bbox = [
                float(value)
                for value in render_map["option_panel_bboxes_px"][str(execution["correct_option_panel_id"])]
            ]
            assert evidence_bboxes[0] == expected_bbox
            assert sorted(tuple(item) for item in execution["valid_triplets"]) == sorted(expected_valid)
            assert sorted(tuple(item) for item in execution["invalid_triplets"]) == sorted(expected_invalid)
            assert len(execution["opposite_pair_specs"]) == 3
            assert len({str(item["left_object_type"]) for item in execution["opposite_pair_specs"]} | {str(item["right_object_type"]) for item in execution["opposite_pair_specs"]}) == 6

            option_specs = execution["option_specs"]
            assert len(option_specs) == 6
            assert [str(option["option_label"]) for option in option_specs] == ["A", "B", "C", "D", "E", "F"]
            assert sum(1 for option in option_specs if bool(option["is_correct"])) == 1
            assert len({tuple(option["visible_triplet"]) for option in option_specs}) == 6
            for option in option_specs:
                assert len(set(option["visible_triplet"])) == 3
                assert set(option["visible_triplet"]).issubset(set(face_object_types.values()))

            winning_option = next(option for option in option_specs if bool(option["is_correct"]))
            assert str(winning_option["option_label"]) == str(out.answer_gt.value)
            assert str(winning_option["option_panel_id"]) == str(execution["correct_option_panel_id"])
            assert str(solver["correct_option_label"]) == str(out.answer_gt.value)
            assert int(solver["correct_option_index"]) == int(execution["correct_option_index"])
            assert [bool(value) for value in solver["options_are_valid_views"]] == [
                bool(option["is_valid_view"]) for option in option_specs
            ]

            if str(task_variant) == "same_cube_view":
                assert sum(1 for option in option_specs if bool(option["is_valid_view"])) == 1
                assert tuple(winning_option["visible_triplet"]) in set(expected_valid)
            else:
                assert sum(1 for option in option_specs if bool(option["is_valid_view"])) == 5
                assert not bool(winning_option["is_valid_view"])
                assert tuple(winning_option["visible_triplet"]) in set(expected_invalid)


def test_puzzle_spatial_prompt_examples_match_selected_variants() -> None:
    task = PuzzlesSpatialCubeViewLabelTask()
    expected = {
        "same_cube_view": (
            {"evidence": [[340, 638, 484, 824]], "answer": "C"},
            {"answer": "C"},
        ),
        "impossible_cube_view": (
            {"evidence": [[668, 638, 812, 824]], "answer": "E"},
            {"answer": "E"},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=24790):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_spatial_cube_view_label_task_is_deterministic() -> None:
    task = PuzzlesSpatialCubeViewLabelTask()
    params = {"task_variant": "same_cube_view", "scene_variant": "cube_card"}
    out_a = task.generate(24820, params=params, max_attempts=10)
    out_b = task.generate(24820, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_spatial_answer_letters_cover_all_four_options() -> None:
    task = PuzzlesSpatialCubeViewLabelTask()
    observed_letters = set()
    for seed in range(24860, 24880):
        out = task.generate(seed, params={"task_variant": "same_cube_view"}, max_attempts=10)
        observed_letters.add(str(out.answer_gt.value))
    assert observed_letters == {"A", "B", "C", "D", "E", "F"}
