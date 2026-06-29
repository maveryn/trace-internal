"""Contract tests for cube surface/net puzzle tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY
from trace.tasks.puzzles.cube_net.cube_net_face_relation_label import (
    SUPPORTED_QUERY_IDS as FACE_RELATION_QUERY_IDS,
    TASK_ID as FACE_RELATION_TASK_ID,
    PuzzlesCubeNetFaceRelationLabelTask,
)
from trace.tasks.puzzles.cube_net.cube_rolling_result_label import (
    SUPPORTED_QUERY_IDS as ROLLING_QUERY_IDS,
    TASK_ID as ROLLING_RESULT_TASK_ID,
    PuzzlesCubeRollingResultLabelTask,
)
from trace.tasks.puzzles.cube_net.folded_path_endpoint_label import (
    TASK_ID as FOLDED_PATH_ENDPOINT_TASK_ID,
    PuzzlesCubeFoldedPathEndpointLabelTask,
)
from trace.tasks.puzzles.cube_net.folded_path_face_sequence_label import (
    TASK_ID as FOLDED_PATH_FACE_SEQUENCE_TASK_ID,
    PuzzlesCubeFoldedPathFaceSequenceLabelTask,
)
from trace.tasks.puzzles.cube_net.shared.state import SCENE_ID


def _assert_bbox_in_image(bbox: list[float], image_size: tuple[int, int]) -> None:
    assert len(bbox) == 4
    assert 0 <= float(bbox[0]) < float(bbox[2]) <= image_size[0]
    assert 0 <= float(bbox[1]) < float(bbox[3]) <= image_size[1]


def _assert_keyed_bboxes_in_image(annotation: dict[str, list[float]], image_size: tuple[int, int]) -> None:
    assert annotation
    for bbox in annotation.values():
        _assert_bbox_in_image(bbox, image_size)


def test_cube_surface_tasks_are_registered() -> None:
    assert TASK_REGISTRY[FACE_RELATION_TASK_ID] is PuzzlesCubeNetFaceRelationLabelTask
    assert TASK_REGISTRY[ROLLING_RESULT_TASK_ID] is PuzzlesCubeRollingResultLabelTask
    assert TASK_REGISTRY[FOLDED_PATH_ENDPOINT_TASK_ID] is PuzzlesCubeFoldedPathEndpointLabelTask
    assert TASK_REGISTRY[FOLDED_PATH_FACE_SEQUENCE_TASK_ID] is PuzzlesCubeFoldedPathFaceSequenceLabelTask

    for task_cls in (
        PuzzlesCubeNetFaceRelationLabelTask,
        PuzzlesCubeRollingResultLabelTask,
        PuzzlesCubeFoldedPathEndpointLabelTask,
        PuzzlesCubeFoldedPathFaceSequenceLabelTask,
    ):
        task = task_cls()
        assert task.domain == "puzzles"
        assert not hasattr(task, "scene_id")


def test_cube_net_face_relation_contracts() -> None:
    task = PuzzlesCubeNetFaceRelationLabelTask()
    for index, query_id in enumerate(FACE_RELATION_QUERY_IDS):
        out = task.generate(2026052800 + index, params={"query_id": query_id}, max_attempts=50)
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == SCENE_ID
        assert out.query_id == query_id
        assert out.answer_gt.type == "option_letter"
        assert out.annotation_gt.type == "bbox_map"
        assert trace["query_spec"]["params"]["query_id"] == query_id
        assert trace["render_spec"]["scene_id"] == SCENE_ID
        assert trace["render_spec"]["label_style"]["font"]["source"] == "global_font_pool"
        assert trace["render_spec"]["scene_variant_style"]["semantic_policy"] == "non_semantic_chrome_only_no_layout_or_answer_change"
        assert trace["render_spec"]["post_image_noise"]["apply_prob"] == 0.5
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]

        assert str(out.answer_gt.value) == str(execution["answer_value"])
        assert set(out.annotation_gt.value) == {"marked_face", "selected_option"}
        assert trace["projected_annotation"]["type"] == "bbox_map"
        assert trace["projected_annotation"]["bbox_map"] == out.annotation_gt.value
        option_labels = {str(option["option_label"]) for option in execution["option_specs"]}
        assert option_labels == {"A", "B", "C", "D"}
        assert str(out.answer_gt.value) in option_labels
        _assert_keyed_bboxes_in_image(out.annotation_gt.value, out.image.size)


def test_cube_rolling_result_contracts() -> None:
    task = PuzzlesCubeRollingResultLabelTask()
    for index, query_id in enumerate(ROLLING_QUERY_IDS):
        out = task.generate(2026052900 + index, params={"query_id": query_id}, max_attempts=50)
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == SCENE_ID
        assert out.query_id == query_id
        assert out.answer_gt.type == "option_letter"
        assert out.annotation_gt.type == "bbox_map"
        assert trace["query_spec"]["params"]["query_id"] == query_id
        assert trace["render_spec"]["scene_id"] == SCENE_ID
        assert trace["render_spec"]["label_style"]["font"]["source"] == "global_font_pool"
        assert trace["render_spec"]["scene_variant_style"]["semantic_policy"] == "non_semantic_chrome_only_no_layout_or_answer_change"
        assert trace["render_spec"]["post_image_noise"]["apply_prob"] == 0.5
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]

        assert str(out.answer_gt.value) == str(execution["answer_value"])
        assert set(out.annotation_gt.value) == {"start_cube", "roll_path", "selected_option"}
        assert trace["projected_annotation"]["type"] == "bbox_map"
        assert trace["projected_annotation"]["bbox_map"] == out.annotation_gt.value
        assert len(execution["path_cells"]) == len(execution["path_directions"]) + 1
        assert {str(option["option_label"]) for option in execution["option_specs"]} == {
            "A",
            "B",
            "C",
            "D",
        }
        assert execution["correct_face"] == execution["final_orientation"][execution["target_slot"]]
        _assert_keyed_bboxes_in_image(out.annotation_gt.value, out.image.size)


def test_cube_surface_path_contracts() -> None:
    cases = (
        (PuzzlesCubeFoldedPathEndpointLabelTask(), "single", "endpoint"),
        (PuzzlesCubeFoldedPathFaceSequenceLabelTask(), "single", "face_sequence"),
    )
    for index, (task, query_id, answer_mode) in enumerate(cases):
        out = task.generate(2026053000 + index, params={"query_id": query_id}, max_attempts=50)
        trace = out.trace_payload
        execution = trace["execution_trace"]

        assert out.scene_id == SCENE_ID
        assert out.query_id == query_id
        assert out.answer_gt.type == "option_letter"
        assert out.annotation_gt.type == "bbox_map"
        assert trace["query_spec"]["params"]["query_id"] == query_id
        assert trace["query_spec"]["params"]["answer_mode"] == answer_mode
        assert trace["render_spec"]["scene_id"] == SCENE_ID
        assert trace["render_spec"]["label_style"]["font"]["source"] == "global_font_pool"
        assert trace["render_spec"]["scene_variant_style"]["semantic_policy"] == "non_semantic_chrome_only_no_layout_or_answer_change"
        assert trace["render_spec"]["post_image_noise"]["apply_prob"] == 0.5
        assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]

        assert str(out.answer_gt.value) == str(execution["answer_value"])
        assert set(out.annotation_gt.value) == {"start_face", "move_instructions", "selected_option"}
        assert trace["projected_annotation"]["type"] == "bbox_map"
        assert trace["projected_annotation"]["bbox_map"] == out.annotation_gt.value
        assert len(execution["face_sequence"]) == len(execution["path_sides"]) + 1
        assert {str(option["option_label"]) for option in execution["option_specs"]} == {
            "A",
            "B",
            "C",
            "D",
        }
        assert execution["face_sequence"][0] == execution["start_face"]
        assert execution["face_sequence"][-1] == execution["endpoint_face"]
        correct = next(option for option in execution["option_specs"] if option["option_label"] == execution["answer_value"])
        if answer_mode == "endpoint":
            assert correct["face_id"] == execution["endpoint_face"]
        else:
            assert correct["face_ids"] == execution["face_sequence"]
        _assert_keyed_bboxes_in_image(out.annotation_gt.value, out.image.size)


def test_cube_surface_scene_variants_are_visible() -> None:
    task = PuzzlesCubeNetFaceRelationLabelTask()
    common = {"query_id": "opposite_face_label"}
    clean = task.generate(2026053010, params={**common, "scene_variant": "clean_net"}, max_attempts=50)
    paper = task.generate(2026053010, params={**common, "scene_variant": "paper_model"}, max_attempts=50)
    mat = task.generate(2026053010, params={**common, "scene_variant": "game_mat"}, max_attempts=50)

    assert clean.trace_payload["render_spec"]["scene_variant_style"]["scene_variant"] == "clean_net"
    assert paper.trace_payload["render_spec"]["scene_variant_style"]["scene_variant"] == "paper_model"
    assert mat.trace_payload["render_spec"]["scene_variant_style"]["scene_variant"] == "game_mat"
    assert clean.image.tobytes() != paper.image.tobytes()
    assert clean.image.tobytes() != mat.image.tobytes()


def test_cube_surface_generation_is_deterministic() -> None:
    task = PuzzlesCubeRollingResultLabelTask()
    params = {"query_id": "final_right_face_label", "scene_variant": "paper_model"}
    out_a = task.generate(2026052999, params=params, max_attempts=50)
    out_b = task.generate(2026052999, params=params, max_attempts=50)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
