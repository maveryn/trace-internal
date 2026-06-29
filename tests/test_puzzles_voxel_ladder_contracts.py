"""Contract tests for migrated voxel-ladder puzzle tasks."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.puzzles.voxel_ladder.checkpoint_sequence_label import (
    PuzzlesVoxelLadderCheckpointSequenceLabelTask,
)
from trace.tasks.puzzles.voxel_ladder.reachable_checkpoint_count import (
    PuzzlesVoxelLadderReachableCheckpointCountTask,
)
from trace.tasks.puzzles.voxel_ladder.unreachable_checkpoint_label import (
    PuzzlesVoxelLadderUnreachableCheckpointLabelTask,
)
from trace.tasks.shared.named_colors import available_named_colors

from tests.helpers import extract_prompt_json_example

SCENE_VARIANTS = (
    "clean_isometric_voxels",
    "worksheet_voxel_maze",
    "game_board_voxel_maze",
)


def _bbox(value: object) -> list[float]:
    """Return one bbox with stable float conversion."""

    return [float(item) for item in value]  # type: ignore[union-attr]


def _bbox_set(value: object) -> list[list[float]]:
    """Return a bbox set with stable float conversion."""

    return [[float(item) for item in bbox] for bbox in value]  # type: ignore[union-attr]


def _assert_bbox_in_canvas(bbox: list[float], *, width: int, height: int) -> None:
    """Check that one bbox is nonempty and inside the rendered canvas."""

    x0, y0, x1, y1 = bbox
    assert 0.0 <= x0 < x1 <= float(width)
    assert 0.0 <= y0 < y1 <= float(height)


def test_voxel_ladder_contract_matches_trace() -> None:
    """Verify answer and annotation are bound from the same rendered trace."""

    task_cases = (
        (
            PuzzlesVoxelLadderCheckpointSequenceLabelTask(),
            "checkpoint_sequence_label",
        ),
        (
            PuzzlesVoxelLadderUnreachableCheckpointLabelTask(),
            "unreachable_checkpoint_label",
        ),
        (
            PuzzlesVoxelLadderReachableCheckpointCountTask(),
            "reachable_checkpoint_count",
        ),
    )
    canonical_color_names = {str(name) for name, _rgb in available_named_colors()}

    for task_index, (task, prompt_query_key) in enumerate(task_cases):
        for scene_index, scene_variant in enumerate(SCENE_VARIANTS):
            out = task.generate(
                29920 + (task_index * 20) + scene_index,
                params={
                    "query_id": SINGLE_QUERY_ID,
                    "scene_variant": scene_variant,
                },
                max_attempts=50,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            dataset = execution["dataset"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            item_bboxes = render_map["item_bboxes_px"]
            canvas_width = int(render["canvas_width"])
            canvas_height = int(render["canvas_height"])

            assert str(out.query_id) == SINGLE_QUERY_ID
            assert str(out.scene_id) == "voxel_ladder"
            assert str(execution["query_id"]) == SINGLE_QUERY_ID
            assert str(execution["internal_query_id"]) == SINGLE_QUERY_ID
            assert str(execution["prompt_query_key"]) == prompt_query_key
            assert str(dataset["scene_variant"]) == scene_variant
            assert str(render["scene_variant"]) == scene_variant
            assert str(render["layout"]) == "isometric_voxel_platforms_with_ladders"
            assert sorted(out.prompt_variants.keys()) == [
                "answer_and_annotation",
                "answer_only",
            ]
            assert out.image.size == (canvas_width, canvas_height)
            assert str(render_map["annotation_source"]) == str(
                execution["supporting_annotation_source"]
            )

            checkpoints = [dict(item) for item in dataset["checkpoints"]]
            route_sequence = [
                str(item) for item in dataset["route_checkpoint_sequence"]
            ]
            checkpoint_color_names = [str(item["color_name"]) for item in checkpoints]
            assert set(checkpoint_color_names).issubset(canonical_color_names)
            assert len(checkpoint_color_names) == len(set(checkpoint_color_names))
            assert route_sequence == [
                str(item["color_name"])
                for item in checkpoints
                if bool(item["on_goal_route"])
            ]

            if prompt_query_key == "checkpoint_sequence_label":
                assert out.answer_gt.type == "option_letter"
                assert out.annotation_gt.type == "bbox"
                correct_options = [
                    str(option["option_label"])
                    for option in dataset["option_specs"]
                    if bool(option["is_correct"])
                ]
                assert correct_options == [str(out.answer_gt.value)]
                assert [
                    str(option["option_label"]) for option in dataset["option_specs"]
                ] == list("ABCDEF")
                expected_bbox = _bbox(item_bboxes[f"option_{out.answer_gt.value}"])
                annotation_bbox = _bbox(out.annotation_gt.value)
                assert annotation_bbox == expected_bbox
                assert trace["projected_annotation"]["type"] == "bbox"
                assert trace["projected_annotation"]["bbox"] == annotation_bbox
                _assert_bbox_in_canvas(
                    annotation_bbox,
                    width=canvas_width,
                    height=canvas_height,
                )
            elif prompt_query_key == "unreachable_checkpoint_label":
                unreachable = [
                    item for item in checkpoints if not bool(item["reachable"])
                ]
                assert len(unreachable) == 1
                assert out.answer_gt.type == "string"
                assert out.annotation_gt.type == "bbox"
                assert str(out.answer_gt.value) == str(unreachable[0]["color_name"])
                assert str(out.answer_gt.value) in canonical_color_names
                expected_bbox = _bbox(item_bboxes[f"checkpoint_{out.answer_gt.value}"])
                annotation_bbox = _bbox(out.annotation_gt.value)
                assert annotation_bbox == expected_bbox
                assert trace["projected_annotation"]["type"] == "bbox"
                assert trace["projected_annotation"]["bbox"] == annotation_bbox
                _assert_bbox_in_canvas(
                    annotation_bbox,
                    width=canvas_width,
                    height=canvas_height,
                )
            elif prompt_query_key == "reachable_checkpoint_count":
                reachable = [item for item in checkpoints if bool(item["reachable"])]
                expected_bboxes = [
                    _bbox(item_bboxes[f"checkpoint_{item['color_name']}"])
                    for item in reachable
                ]
                annotation_bboxes = _bbox_set(out.annotation_gt.value)
                assert out.answer_gt.type == "integer"
                assert out.annotation_gt.type == "bbox_set"
                assert int(out.answer_gt.value) == len(reachable)
                assert int(out.answer_gt.value) == int(
                    dataset["reachable_checkpoint_count"]
                )
                assert 2 <= int(out.answer_gt.value) <= 5
                assert annotation_bboxes == expected_bboxes
                assert trace["projected_annotation"]["type"] == "bbox_set"
                assert trace["projected_annotation"]["bbox_set"] == annotation_bboxes
                for bbox in annotation_bboxes:
                    _assert_bbox_in_canvas(
                        bbox,
                        width=canvas_width,
                        height=canvas_height,
                    )
            else:
                raise AssertionError(f"unhandled voxel-ladder query {prompt_query_key}")


def test_voxel_ladder_prompt_examples_match_annotation_contracts() -> None:
    """Prompt examples should match scalar bbox and bbox-set contracts."""

    expected = {
        "checkpoint_sequence_label": (
            PuzzlesVoxelLadderCheckpointSequenceLabelTask(),
            {"annotation": [760, 160, 1030, 202], "answer": "B"},
            {"answer": "B"},
        ),
        "reachable_checkpoint_count": (
            PuzzlesVoxelLadderReachableCheckpointCountTask(),
            {
                "annotation": [
                    [318, 404, 390, 474],
                    [472, 276, 544, 346],
                    [664, 128, 736, 198],
                ],
                "answer": 3,
            },
            {"answer": 3},
        ),
        "unreachable_checkpoint_label": (
            PuzzlesVoxelLadderUnreachableCheckpointLabelTask(),
            {"annotation": [758, 318, 830, 388], "answer": "purple"},
            {"answer": "purple"},
        ),
    }
    for index, (_query, case) in enumerate(expected.items(), start=30010):
        task, expected_answer_and_annotation, expected_answer_only = case
        out = task.generate(
            index, params={"query_id": SINGLE_QUERY_ID}, max_attempts=50
        )
        answer_and_annotation = extract_prompt_json_example(
            out.prompt_variants["answer_and_annotation"]
        )
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation == expected_answer_and_annotation
        assert answer_only == expected_answer_only


def test_voxel_ladder_task_is_deterministic() -> None:
    """Pinned seed and params should reproduce image, prompt, and verifier payload."""

    task = PuzzlesVoxelLadderReachableCheckpointCountTask()
    params = {
        "query_id": SINGLE_QUERY_ID,
        "scene_variant": "game_board_voxel_maze",
        "reachable_checkpoint_count": 4,
    }
    out_a = task.generate(30100, params=params, max_attempts=50)
    out_b = task.generate(30100, params=params, max_attempts=50)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert out_a.trace_payload["query_spec"] == out_b.trace_payload["query_spec"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_voxel_ladder_explicit_support_axes_generate() -> None:
    """Explicit scene and answer-support params should smoke-generate."""

    sequence_task = PuzzlesVoxelLadderCheckpointSequenceLabelTask()
    count_task = PuzzlesVoxelLadderReachableCheckpointCountTask()
    unreachable_task = PuzzlesVoxelLadderUnreachableCheckpointLabelTask()

    for cursor, scene_variant in enumerate(SCENE_VARIANTS):
        sequence_out = sequence_task.generate(
            30200 + cursor,
            params={
                "query_id": SINGLE_QUERY_ID,
                "scene_variant": scene_variant,
                "answer_option_label": "F",
                "route_checkpoint_count": 3,
            },
            max_attempts=50,
        )
        assert str(sequence_out.answer_gt.value) == "F"
        assert (
            sequence_out.trace_payload["execution_trace"]["dataset"]["scene_variant"]
            == scene_variant
        )

        unreachable_out = unreachable_task.generate(
            30220 + cursor,
            params={
                "query_id": SINGLE_QUERY_ID,
                "scene_variant": scene_variant,
                "route_checkpoint_count": 3,
            },
            max_attempts=50,
        )
        assert unreachable_out.annotation_gt.type == "bbox"

    observed_counts: set[int] = set()
    for target_count in range(2, 6):
        out = count_task.generate(
            30250 + target_count,
            params={
                "query_id": SINGLE_QUERY_ID,
                "reachable_checkpoint_count": target_count,
            },
            max_attempts=50,
        )
        observed_counts.add(int(out.answer_gt.value))
        assert len(out.annotation_gt.value) == int(out.answer_gt.value)
    assert observed_counts == {2, 3, 4, 5}
