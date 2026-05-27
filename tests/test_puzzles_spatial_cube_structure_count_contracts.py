"""Contract tests for split puzzle cube-structure counting tasks."""

from __future__ import annotations

from collections import Counter

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.shared.spatial_blocks_common import total_cubes_from_height_rows
from trace.tasks.puzzles.spatial.cube_structure_count import (
    PuzzlesSpatialCubeCountTask,
    PuzzlesSpatialCubePaintedFaceCountTask,
    PuzzlesSpatialCubeStructureChangeCountTask,
)
from tests.helpers import extract_prompt_json_example


CUBE_COUNT_TASK_ID = "task_puzzles__voxel_cube__cube_count"
CUBE_STRUCTURE_CHANGE_COUNT_TASK_ID = "task_puzzles__voxel_cube__cube_structure_change_count"
CUBE_PAINTED_FACE_COUNT_TASK_ID = "task_puzzles__voxel_cube__cube_painted_face_count"

CUBE_CASES = (
    (PuzzlesSpatialCubeCountTask, CUBE_COUNT_TASK_ID, "cube_count", "total_cube_count", {}),
    (
        PuzzlesSpatialCubeStructureChangeCountTask,
        CUBE_STRUCTURE_CHANGE_COUNT_TASK_ID,
        "cube_structure_change_count",
        "missing_to_complete_cuboid_count",
        {"change_type": "missing_to_complete"},
    ),
    (
        PuzzlesSpatialCubeStructureChangeCountTask,
        CUBE_STRUCTURE_CHANGE_COUNT_TASK_ID,
        "cube_structure_change_count",
        "removed_cube_count",
        {"change_type": "removed"},
    ),
    (
        PuzzlesSpatialCubePaintedFaceCountTask,
        CUBE_PAINTED_FACE_COUNT_TASK_ID,
        "painted_face_count",
        "painted_exterior_face_count",
        {"painted_query": "exterior_face_total"},
    ),
    (
        PuzzlesSpatialCubePaintedFaceCountTask,
        CUBE_PAINTED_FACE_COUNT_TASK_ID,
        "painted_face_count",
        "exact_k_painted_faces_cube_count",
        {"painted_query": "exact_k_faces_cube_count"},
    ),
)


def _hidden_cube_count(cube_records: list[dict[str, object]]) -> int:
    return sum(1 for record in cube_records if bool(record["is_hidden"]))


def _is_readable_edge(record: dict[str, object], *, row_count: int, col_count: int) -> bool:
    return int(record["row_index"]) == int(row_count) - 1 or int(record["col_index"]) == int(col_count) - 1


def _assert_wall_like_shape(execution: dict[str, object]) -> None:
    assert int(execution["row_count"]) == 1 or int(execution["col_count"]) == 1
    assert int(execution["row_count"]) <= 6
    assert int(execution["col_count"]) <= 6


def _actual_max_height(height_rows: list[list[int]]) -> int:
    return max(int(value) for row in height_rows for value in row)


def _assert_counter_covered(counter: Counter, expected_keys: set[object], *, min_fraction: float = 0.20) -> None:
    assert set(counter) == set(expected_keys)
    sample_count = sum(int(value) for value in counter.values())
    min_count = max(1, int(float(sample_count) * float(min_fraction)))
    for key in expected_keys:
        assert int(counter[key]) >= int(min_count)


def test_puzzle_spatial_cube_structure_split_tasks_registered() -> None:
    assert TASK_REGISTRY[CUBE_COUNT_TASK_ID] is PuzzlesSpatialCubeCountTask
    assert TASK_REGISTRY[CUBE_STRUCTURE_CHANGE_COUNT_TASK_ID] is PuzzlesSpatialCubeStructureChangeCountTask
    assert TASK_REGISTRY[CUBE_PAINTED_FACE_COUNT_TASK_ID] is PuzzlesSpatialCubePaintedFaceCountTask


def test_puzzle_spatial_cube_structure_split_contracts_match_trace() -> None:
    for case_index, (task_cls, _task_id, query_id, internal_variant, extra_params) in enumerate(CUBE_CASES):
        task = task_cls()
        out = task.generate(
            31200 + case_index,
            params={"scene_variant": "stack_card", **dict(extra_params)},
            max_attempts=10,
        )
        trace = out.trace_payload
        query = trace["query_spec"]
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

        assert str(out.query_id) == "default"
        assert str(out.query_id) == str(query_id)
        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert str(query["query_id"]) == "default"
        assert str(query["query_id"]) == str(query_id)
        assert str(query["params"]["query_id"]) == "default"
        assert str(query["params"]["query_id"]) == str(query_id)
        assert str(query["params"]["internal_query_id"]) == str(internal_variant)
        assert str(execution["query_id"]) == "default"
        assert str(execution["query_id"]) == str(query_id)
        assert str(execution["internal_query_id"]) == str(internal_variant)
        assert str(execution["question_format"]) == str(internal_variant)
        assert str(execution["scene_variant"]) == "stack_card"
        assert str(render["scene_variant"]) == "stack_card"
        assert str(render["scene_id"]).strip()
        assert str(render["cube_color"]["name"])
        assert render["cube_color"] == execution["cube_color"]
        assert 0.50 <= float(render["voxel_scale"]) <= 1.00
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert int(out.answer_gt.value) == int(execution["answer_value"])
        _assert_wall_like_shape(execution)

        if internal_variant in {"missing_to_complete_cuboid_count", "removed_cube_count"}:
            assert len(evidence_bboxes) == 2
            expected_original_bbox = [
                float(value)
                for value in render_map["structure_bboxes_px"][str(execution["original_structure_bbox_id"])]
            ]
            expected_remaining_bbox = [
                float(value)
                for value in render_map["structure_bboxes_px"][str(execution["remaining_structure_bbox_id"])]
            ]
            assert evidence_bboxes == [expected_original_bbox, expected_remaining_bbox]
            assert int(execution["original_total_cubes"]) > int(execution["remaining_total_cubes"])
            assert len(execution["original_cube_records"]) == int(execution["original_total_cubes"])
            assert len(execution["remaining_cube_records"]) == int(execution["remaining_total_cubes"])
            assert _hidden_cube_count(execution["original_cube_records"]) == 0
            assert _hidden_cube_count(execution["remaining_cube_records"]) == 0
            if internal_variant == "removed_cube_count":
                assert _actual_max_height(execution["original_height_rows"]) == int(execution["max_height"])
        else:
            assert len(evidence_bboxes) == 1
            expected_bbox = [float(value) for value in render_map["structure_bboxes_px"][str(execution["structure_bbox_id"])]]
            assert evidence_bboxes == [expected_bbox]
            assert len(execution["cube_records"]) == int(execution["total_cubes"])
            assert _hidden_cube_count(execution["cube_records"]) == 0
            assert int(total_cubes_from_height_rows(execution["height_rows"])) == int(execution["total_cubes"])
            assert max(max(int(value) for value in row) for row in execution["height_rows"]) <= 3
            assert _actual_max_height(execution["height_rows"]) == int(execution["max_height"])

        if internal_variant == "total_cube_count":
            assert int(out.answer_gt.value) == int(execution["total_cubes"])
        elif internal_variant == "missing_to_complete_cuboid_count":
            assert int(out.answer_gt.value) == int(execution["missing_cube_count"])
            assert int(out.answer_gt.value) == int(execution["original_total_cubes"]) - int(execution["remaining_total_cubes"])
            assert len(execution["missing_cube_records"]) == int(out.answer_gt.value)
            assert bool(execution["missing_cells_restricted_to_readable_edges"])
            assert int(execution["cuboid_height"]) <= 3
            assert _actual_max_height(execution["original_height_rows"]) == int(execution["cuboid_height"])
            assert all(
                _is_readable_edge(
                    record,
                    row_count=int(execution["row_count"]),
                    col_count=int(execution["col_count"]),
                )
                for record in execution["missing_cube_records"]
            )
        elif internal_variant == "removed_cube_count":
            assert int(out.answer_gt.value) == int(execution["removed_cube_count"])
            assert int(out.answer_gt.value) == int(execution["original_total_cubes"]) - int(execution["remaining_total_cubes"])
            assert len(execution["removed_cube_records"]) == int(out.answer_gt.value)
            assert bool(execution["removed_cells_restricted_to_readable_edges"])
            assert int(execution["max_height"]) <= 3
            assert all(
                _is_readable_edge(
                    record,
                    row_count=int(execution["row_count"]),
                    col_count=int(execution["col_count"]),
                )
                for record in execution["removed_cube_records"]
            )
        elif internal_variant == "painted_exterior_face_count":
            assert int(out.answer_gt.value) == sum(
                int(record["painted_face_count"]) for record in execution["painted_cube_records"]
            )
        else:
            painted_face_target_k = int(execution["painted_face_target_k"])
            assert int(out.answer_gt.value) == sum(
                1
                for record in execution["painted_cube_records"]
                if int(record["painted_face_count"]) == int(painted_face_target_k)
            )


def test_puzzle_spatial_cube_structure_prompt_examples_match_selected_queries() -> None:
    expected_examples = {
        "total_cube_count": ({"evidence": [[310, 170, 890, 700]], "answer": 14}, {"answer": 14}),
        "missing_to_complete_cuboid_count": (
            {"evidence": [[132, 175, 459, 700], [750, 207, 1080, 700]], "answer": 5},
            {"answer": 5},
        ),
        "removed_cube_count": (
            {"evidence": [[132, 175, 459, 700], [750, 207, 1080, 700]], "answer": 4},
            {"answer": 4},
        ),
        "painted_exterior_face_count": ({"evidence": [[310, 170, 890, 700]], "answer": 42}, {"answer": 42}),
        "exact_k_painted_faces_cube_count": ({"evidence": [[310, 170, 890, 700]], "answer": 3}, {"answer": 3}),
    }

    for case_index, (task_cls, _task_id, _query_id, internal_variant, extra_params) in enumerate(CUBE_CASES):
        out = task_cls().generate(
            31300 + case_index,
            params=dict(extra_params),
            max_attempts=10,
        )
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_examples[internal_variant][0]
        assert answer_only == expected_examples[internal_variant][1]


def test_puzzle_spatial_cube_count_sampling_covers_answers_and_heights() -> None:
    task = PuzzlesSpatialCubeCountTask()
    answers = set()
    heights = Counter()
    cube_colors: set[str] = set()

    for sampling_index in range(50):
        out = task.generate(
            31400 + sampling_index,
            params={},
            max_attempts=10,
        )
        execution = out.trace_payload["execution_trace"]
        assert str(out.query_id) == "default"
        assert str(out.query_id) == "cube_count"
        assert str(execution["internal_query_id"]) == "total_cube_count"
        answers.add(int(out.answer_gt.value))
        heights[int(execution["max_height"])] += 1
        cube_colors.add(str(out.trace_payload["render_spec"]["cube_color"]["name"]))

    assert answers >= {8, 9, 10, 11, 12}
    _assert_counter_covered(heights, {2, 3})
    assert len(cube_colors) >= 5


def test_puzzle_spatial_cube_structure_change_sampling_covers_subqueries_and_answers() -> None:
    task = PuzzlesSpatialCubeStructureChangeCountTask()
    internal_counter = Counter()
    answer_by_variant: dict[str, set[int]] = {
        "missing_to_complete_cuboid_count": set(),
        "removed_cube_count": set(),
    }
    heights_by_variant: dict[str, Counter[int]] = {key: Counter() for key in answer_by_variant}

    for sampling_index in range(72):
        out = task.generate(
            31480 + sampling_index,
            params={},
            max_attempts=10,
        )
        execution = out.trace_payload["execution_trace"]
        internal_variant = str(execution["internal_query_id"])
        assert str(out.query_id) == "default"
        assert str(out.query_id) == "cube_structure_change_count"
        assert internal_variant in answer_by_variant
        internal_counter[internal_variant] += 1
        answer_by_variant[internal_variant].add(int(out.answer_gt.value))
        heights_by_variant[internal_variant][int(execution.get("max_height", execution.get("cuboid_height")))] += 1

    _assert_counter_covered(internal_counter, set(answer_by_variant))
    assert answer_by_variant["missing_to_complete_cuboid_count"] >= {1, 2, 3, 4, 5, 6}
    assert answer_by_variant["removed_cube_count"] >= {1, 2, 3, 4, 5, 6}
    for counter in heights_by_variant.values():
        _assert_counter_covered(counter, {2, 3})


def test_puzzle_spatial_cube_painted_face_sampling_covers_subqueries() -> None:
    task = PuzzlesSpatialCubePaintedFaceCountTask()
    internal_counter = Counter()
    answer_by_variant: dict[str, set[int]] = {
        "painted_exterior_face_count": set(),
        "exact_k_painted_faces_cube_count": set(),
    }
    height_by_variant: dict[str, Counter[int]] = {key: Counter() for key in answer_by_variant}

    for sampling_index in range(72):
        out = task.generate(
            31580 + sampling_index,
            params={},
            max_attempts=10,
        )
        execution = out.trace_payload["execution_trace"]
        internal_variant = str(execution["internal_query_id"])
        assert str(out.query_id) == "default"
        assert str(out.query_id) == "painted_face_count"
        assert internal_variant in answer_by_variant
        internal_counter[internal_variant] += 1
        answer_by_variant[internal_variant].add(int(out.answer_gt.value))
        height_by_variant[internal_variant][int(execution["max_height"])] += 1

    _assert_counter_covered(internal_counter, set(answer_by_variant))
    assert answer_by_variant["painted_exterior_face_count"] >= {14, 16, 18, 20, 22}
    assert len(answer_by_variant["exact_k_painted_faces_cube_count"]) >= 5
    assert set(height_by_variant["painted_exterior_face_count"]) == {2}
    _assert_counter_covered(height_by_variant["exact_k_painted_faces_cube_count"], {2, 3})


def test_puzzle_spatial_cube_structure_change_count_task_is_deterministic() -> None:
    task = PuzzlesSpatialCubeStructureChangeCountTask()
    params = {"change_type": "removed", "scene_variant": "stack_card"}
    out_a = task.generate(31680, params=params, max_attempts=10)
    out_b = task.generate(31680, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
