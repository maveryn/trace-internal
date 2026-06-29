"""Behavior tests for puzzle topology tasks."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

from trace.tasks.puzzles.string_topology.string_component_count import (
    PuzzlesStringTopologyComponentCountTask,
)
from tests.helpers import assert_counter_support_within, extract_prompt_json_example


def test_puzzle_topology_string_component_count_contract_matches_metadata() -> None:
    task_cases = (
        (PuzzlesStringTopologyComponentCountTask(), "open_rope_count"),
        (PuzzlesStringTopologyComponentCountTask(), "closed_loop_count"),
        (PuzzlesStringTopologyComponentCountTask(), "knotted_component_count"),
    )
    scene_variants = (
        "string_strip",
        "string_card",
        "string_outline",
    )

    for query_id_index, (task, query_id) in enumerate(task_cases):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 28520 + (query_id_index * 20) + scene_index
            out = task.generate(
                seed,
                params={"scene_variant": scene_variant, "query_id": query_id},
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            components = [dict(component) for component in execution["component_specs"]]
            groups = [dict(group) for group in execution["visual_group_specs"]]
            crossings = [dict(crossing) for crossing in execution["crossing_specs"]]
            annotation_bboxes = [
                [float(value) for value in bbox] for bbox in out.annotation_gt.value
            ]

            assert str(out.query_id) == str(query_id)
            assert str(out.scene_id) == "string_topology"
            assert out.answer_gt.type == "integer"
            assert out.annotation_gt.type == "bbox_set"
            assert int(out.answer_gt.value) == int(execution["answer_value"])
            assert int(out.answer_gt.value) == len(annotation_bboxes)
            assert int(out.answer_gt.value) >= 1
            assert sorted(out.prompt_variants.keys()) == [
                "answer_and_annotation",
                "answer_only",
            ]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["query_id"]) == str(query_id)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (
                int(render["canvas_width"]),
                int(render["canvas_height"]),
            )
            assert str(execution["question_format"]) == "string_component_count"
            assert str(execution["view_family"]) == "string_topology_component_count"
            assert (
                str(execution["topology_rule"])
                == "crossings_do_not_merge_components_over_under_recorded"
            )
            assert len(components) == int(execution["component_count"])
            assert len(groups) == int(execution["visual_group_count"])
            assert len(render_map["visual_group_bboxes_px"]) == len(groups)
            assert len(render_map["crossing_bboxes_px"]) == len(crossings)
            assert set(render_map["crossing_bboxes_px"]) == {
                str(crossing["crossing_id"]) for crossing in crossings
            }
            assert str(render_map["annotation_source"]) == str(
                execution["supporting_annotation_source"]
            )
            assert str(render["layout"]) == "random_open_canvas"
            assert trace["projected_annotation"]["bbox_set"] == annotation_bboxes

            assert not any(
                str(group["group_type"]) == "linked_pair" for group in groups
            )
            assert not any(
                str(group["group_type"]) == "tangled_rope_bundle" for group in groups
            )
            assert 6 <= int(execution["visual_group_count"]) <= 20
            assert 6 <= int(execution["component_count"]) <= 20
            assert int(execution["component_count"]) == int(execution["object_count"])
            assert int(execution["visual_group_count"]) == int(
                execution["object_count"]
            )
            assert int(execution["answer_value"]) == int(execution["target_count"])
            assert int(execution["answer_value"]) == int(execution["target_answer"])
            assert int(execution["object_count"]) == int(
                execution["target_count"]
            ) + int(execution["distractor_count"])
            assert 3 <= int(execution["target_count"]) <= 10
            assert 3 <= int(execution["distractor_count"]) <= 10
            assert list(execution["visual_group_count_range"]) == [6, 20]
            assert list(execution["component_count_range"]) == [6, 20]
            assert list(execution["object_count_range"]) == [6, 20]
            assert list(execution["target_count_range"]) == [3, 10]
            assert list(execution["distractor_count_range"]) == [3, 10]

            if str(query_id) == "open_rope_count":
                expected_ids = [
                    str(component["component_id"])
                    for component in components
                    if bool(component["open_ended"])
                ]
                annotation_source = render_map["component_bboxes_px"]
                expected_count = int(execution["open_rope_count"])
            elif str(query_id) == "closed_loop_count":
                expected_ids = [
                    str(component["component_id"])
                    for component in components
                    if bool(component["closed"])
                ]
                annotation_source = render_map["component_bboxes_px"]
                expected_count = sum(
                    1 for component in components if bool(component["closed"])
                )
            else:
                expected_ids = [
                    str(component["component_id"])
                    for component in components
                    if int(component.get("knot_count", 0)) > 0
                ]
                annotation_source = render_map["component_bboxes_px"]
                expected_count = sum(
                    1
                    for component in components
                    if int(component.get("knot_count", 0)) > 0
                )

            assert int(out.answer_gt.value) == int(expected_count)
            assert [
                str(value) for value in execution["supporting_item_ids"]
            ] == expected_ids
            assert [
                str(value) for value in execution["solver_trace"]["supporting_item_ids"]
            ] == expected_ids
            expected_bboxes = [
                [float(value) for value in annotation_source[str(item_id)]]
                for item_id in expected_ids
            ]
            assert annotation_bboxes == expected_bboxes

            for bbox in annotation_bboxes:
                x1, y1, x2, y2 = bbox
                assert 0.0 <= x1 < x2 <= float(render["canvas_width"])
                assert 0.0 <= y1 < y2 <= float(render["canvas_height"])

            visual_group_bboxes = [
                [
                    float(value)
                    for value in render_map["visual_group_bboxes_px"][
                        str(group["visual_group_id"])
                    ]
                ]
                for group in groups
            ]
            min_gap = float(render["group_min_gap_px"])
            for left_bbox, right_bbox in combinations(visual_group_bboxes, 2):
                assert (
                    left_bbox[2] + min_gap <= right_bbox[0]
                    or right_bbox[2] + min_gap <= left_bbox[0]
                    or left_bbox[3] + min_gap <= right_bbox[1]
                    or right_bbox[3] + min_gap <= left_bbox[1]
                )


def test_puzzle_topology_string_component_prompt_examples_match_selected_variants() -> (
    None
):
    expected = {
        "open_rope_count": (
            PuzzlesStringTopologyComponentCountTask(),
            {
                "annotation": [
                    [92, 132, 266, 228],
                    [512, 176, 686, 272],
                    [786, 430, 960, 526],
                ],
                "answer": 3,
            },
            {"answer": 3},
        ),
        "closed_loop_count": (
            PuzzlesStringTopologyComponentCountTask(),
            {
                "annotation": [
                    [92, 132, 266, 228],
                    [512, 176, 686, 272],
                    [786, 430, 960, 526],
                ],
                "answer": 3,
            },
            {"answer": 3},
        ),
        "knotted_component_count": (
            PuzzlesStringTopologyComponentCountTask(),
            {
                "annotation": [
                    [92, 132, 266, 228],
                    [512, 176, 686, 272],
                    [786, 430, 960, 526],
                ],
                "answer": 3,
            },
            {"answer": 3},
        ),
    }
    for index, (
        query_id,
        (task, expected_answer_and_annotation, expected_answer_only),
    ) in enumerate(expected.items(), start=28610):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        assert str(out.query_id) == str(query_id)
        answer_and_annotation = extract_prompt_json_example(
            out.prompt_variants["answer_and_annotation"]
        )
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_annotation == expected_answer_and_annotation
        assert answer_only == expected_answer_only


def test_puzzle_topology_string_component_count_task_is_deterministic() -> None:
    task = PuzzlesStringTopologyComponentCountTask()
    params = {"scene_variant": "string_card", "query_id": "knotted_component_count"}
    out_a = task.generate(28680, params=params, max_attempts=10)
    out_b = task.generate(28680, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert (
        out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    )
    assert (
        out_a.trace_payload["query_spec"]["prompt_variant"]
        == out_b.trace_payload["query_spec"]["prompt_variant"]
    )
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_topology_open_rope_count_uses_knotted_closed_distractors() -> None:
    task = PuzzlesStringTopologyComponentCountTask()
    out = task.generate(
        28695,
        params={
            "query_id": "open_rope_count",
            "target_count": 3,
            "distractor_count": 3,
            "scene_variant": "string_strip",
        },
        max_attempts=10,
    )
    execution = out.trace_payload["execution_trace"]

    assert int(execution["answer_value"]) == 3
    assert int(execution["open_rope_count"]) == 3
    assert int(execution["distractor_count"]) == 3
    assert int(execution["knotted_component_count"]) == 1
    assert any(
        str(component["component_type"]) == "knotted_loop"
        for component in execution["component_specs"]
    )


def test_puzzle_topology_string_component_sampling_decouples_variant_scene_and_answers() -> (
    None
):
    task = PuzzlesStringTopologyComponentCountTask()
    combos = Counter()
    answers_by_variant: dict[str, set[int]] = {}
    distractors_by_variant: dict[str, set[int]] = {}

    for sampling_index in range(300):
        out = task.generate(
            28720 + sampling_index,
            params={},
            max_attempts=10,
        )
        trace = out.trace_payload["execution_trace"]
        query_id = str(trace["query_id"])
        combos[(query_id, str(trace["scene_variant"]))] += 1
        answers_by_variant.setdefault(query_id, set()).add(int(out.answer_gt.value))
        distractors_by_variant.setdefault(query_id, set()).add(
            int(trace["distractor_count"])
        )
        assert int(trace["object_count"]) == int(trace["target_count"]) + int(
            trace["distractor_count"]
        )
        assert 6 <= int(trace["object_count"]) <= 20

    assert set(combos) == {
        ("open_rope_count", "string_strip"),
        ("open_rope_count", "string_card"),
        ("open_rope_count", "string_outline"),
        ("closed_loop_count", "string_strip"),
        ("closed_loop_count", "string_card"),
        ("closed_loop_count", "string_outline"),
        ("knotted_component_count", "string_strip"),
        ("knotted_component_count", "string_card"),
        ("knotted_component_count", "string_outline"),
    }
    assert_counter_support_within(
        combos,
        {
            ("open_rope_count", "string_strip"),
            ("open_rope_count", "string_card"),
            ("open_rope_count", "string_outline"),
            ("closed_loop_count", "string_strip"),
            ("closed_loop_count", "string_card"),
            ("closed_loop_count", "string_outline"),
            ("knotted_component_count", "string_strip"),
            ("knotted_component_count", "string_card"),
            ("knotted_component_count", "string_outline"),
        },
        expected_per_key=33,
        tolerance=17,
    )
    expected_count_support = {3, 4, 5, 6, 7, 8, 9, 10}
    assert answers_by_variant["open_rope_count"] == expected_count_support
    assert answers_by_variant["closed_loop_count"] == expected_count_support
    assert answers_by_variant["knotted_component_count"] == expected_count_support
    assert distractors_by_variant["open_rope_count"] == expected_count_support
    assert distractors_by_variant["closed_loop_count"] == expected_count_support
    assert distractors_by_variant["knotted_component_count"] == expected_count_support

    fixed_scene_answers: dict[str, set[int]] = {}
    fixed_scene_distractors: dict[str, set[int]] = {}
    for sampling_index in range(240):
        out = task.generate(
            28880 + sampling_index,
            params={"scene_variant": "string_card"},
            max_attempts=10,
        )
        trace = out.trace_payload["execution_trace"]
        query_id = str(trace["query_id"])
        assert str(trace["scene_variant"]) == "string_card"
        fixed_scene_answers.setdefault(query_id, set()).add(int(out.answer_gt.value))
        fixed_scene_distractors.setdefault(query_id, set()).add(
            int(trace["distractor_count"])
        )

    assert fixed_scene_answers["open_rope_count"] == expected_count_support
    assert fixed_scene_answers["closed_loop_count"] == expected_count_support
    assert fixed_scene_answers["knotted_component_count"] == expected_count_support
    assert fixed_scene_distractors["open_rope_count"] == expected_count_support
    assert fixed_scene_distractors["closed_loop_count"] == expected_count_support
    assert fixed_scene_distractors["knotted_component_count"] == expected_count_support

    fixed_task_scenes = Counter()
    fixed_task_answers: set[int] = set()
    fixed_task_distractors: set[int] = set()
    for sampling_index in range(120):
        out = task.generate(
            28980 + sampling_index,
            params={"query_id": "knotted_component_count"},
            max_attempts=10,
        )
        trace = out.trace_payload["execution_trace"]
        assert str(trace["query_id"]) == "knotted_component_count"
        fixed_task_scenes[str(trace["scene_variant"])] += 1
        fixed_task_answers.add(int(out.answer_gt.value))
        fixed_task_distractors.add(int(trace["distractor_count"]))

    assert set(fixed_task_scenes) == {"string_strip", "string_card", "string_outline"}
    assert fixed_task_answers == expected_count_support
    assert fixed_task_distractors == expected_count_support
