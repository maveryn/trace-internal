"""Behavior tests for puzzle topology tasks."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

from trace.tasks.shared.color_distance import color_distance
from trace.tasks.shared.named_colors import available_named_colors
from trace.tasks.puzzles.shared.bead_loop_common import bead_sequences_are_rotation_equivalent
from trace.tasks.puzzles.topology.cyclic_order_match import (
    PuzzlesTopologyCyclicOrderEquivalentLabelTask,
)
from trace.tasks.puzzles.topology.maze_exit_label import (
    PuzzlesTopologyMazeExitReachabilityLabelTask,
    PuzzlesTopologyMazeReachableExitCountTask,
)
from trace.tasks.puzzles.topology.string_component_count import (
    PuzzlesTopologyStringComponentCountTask,
)
from trace.tasks.puzzles.topology.voxel_ladder_maze import (
    PuzzlesTopologyVoxelLadderRouteCountTask,
    PuzzlesTopologyVoxelLadderRouteLabelTask,
)
from tests.helpers import assert_counter_support_within, extract_prompt_json_example


def test_puzzle_topology_cyclic_order_match_contract_matches_valid_options() -> None:
    tasks = (
        (PuzzlesTopologyCyclicOrderEquivalentLabelTask(), "cyclic_order_equivalent_label"),
    )
    token_render_styles = (
        "colored_beads",
        "shape_tokens",
        "colored_shape_tokens",
        "outline_shape_tokens",
        "symbol_badges",
    )
    scene_variants = (
        "necklace_board",
        "charm_card_grid",
        "route_loop_diagram",
        "token_ring_outline",
    )
    loop_path_styles = (
        "ellipse",
        "rounded_rect",
        "polygon_loop",
        "wavy_loop",
        "beaded_string",
    )

    for query_id_index, (task, query_id) in enumerate(tasks):
        for mode_index, token_render_style in enumerate(token_render_styles):
            for scene_index, scene_variant in enumerate(scene_variants):
                loop_path_style = loop_path_styles[(query_id_index + mode_index + scene_index) % len(loop_path_styles)]
                seed = 27320 + (query_id_index * 1000) + (mode_index * 100) + (scene_index * 10)
                out = task.generate(
                    seed,
                    params={
                        "query_id": query_id,
                        "token_render_style": token_render_style,
                        "scene_variant": scene_variant,
                        "loop_path_style": loop_path_style,
                    },
                    max_attempts=10,
                )
                trace = out.trace_payload
                execution = trace["execution_trace"]
                render = trace["render_spec"]
                render_map = trace["render_map"]
                solver = execution["solver_trace"]
                evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

                assert str(out.query_id) == "default"
                assert str(out.query_id) == str(query_id)
                assert str(out.scene_id) == "cyclic_order"
                assert str(execution["token_render_style"]) == str(token_render_style)
                assert str(execution["loop_path_style"]) == str(loop_path_style)
                assert str(execution["query_id"]) == "default"
                assert str(execution["query_id"]) == str(query_id)
                assert str(execution["internal_query_id"]) == str(query_id)
                assert out.evidence_gt.type == "bbox_set"
                assert out.answer_gt.type == "option_letter"
                assert str(out.answer_gt.value) == str(execution["answer_option_label"])
                assert int(execution["valid_option_count"]) == 1
                assert len(evidence_bboxes) == 1
                assert str(execution["view_family"]) == "topology_loop_option_label"
                assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
                assert str(execution["scene_variant"]) == str(scene_variant)
                assert str(render["scene_variant"]) == str(scene_variant)
                assert str(render["loop_path_style"]) == str(loop_path_style)
                assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
                assert list(execution["option_count_range"]) == [6, 6]
                assert int(execution["option_count"]) == 6
                assert 4 <= int(execution["bead_count"]) <= 5
                assert 4 <= int(execution["bead_count_range"][0]) <= int(execution["bead_count_range"][1]) <= 5
                assert int(execution["bead_count"]) >= int(execution["bead_count_range"][0])
                assert int(execution["bead_count"]) <= int(execution["bead_count_range"][1])
                assert str(execution["question_format"]) == str(query_id)
                assert str(execution["equivalence_rule"]) == "same_cyclic_order_up_to_rotation_no_reflection"
                assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes

                option_specs = execution["option_specs"]
                assert len(option_specs) == int(execution["option_count"])
                assert sum(1 for option in option_specs if bool(option["is_valid"])) == int(execution["valid_option_count"])
                assert [str(option["option_label"]) for option in option_specs] == [
                    chr(ord("A") + index) for index in range(int(execution["option_count"]))
                ]

                expected_bboxes = [
                    [float(value) for value in render_map["option_choice_bboxes_px"][str(option_id)]]
                    for option_id in execution["valid_option_choice_ids"]
                ]
                assert evidence_bboxes == expected_bboxes
                assert [str(value) for value in execution["supporting_option_choice_ids"]] == [
                    str(value) for value in execution["valid_option_choice_ids"]
                ]

                reference_sequence = [str(value) for value in execution["reference_token_sequence"]]
                valid_labels = []
                for option in option_specs:
                    token_sequence = [str(value) for value in option["token_sequence"]]
                    is_equivalent = bead_sequences_are_rotation_equivalent(reference_sequence, token_sequence)
                    assert bool(is_equivalent) == bool(option["is_valid"])
                    if bool(option["is_valid"]):
                        valid_labels.append(str(option["option_label"]))

                assert valid_labels == [str(value) for value in execution["valid_option_labels"]]
                assert valid_labels == [str(value) for value in solver["valid_option_labels"]]
                assert [str(value) for value in execution["valid_option_choice_ids"]] == [
                    str(value) for value in solver["valid_option_choice_ids"]
                ]

                if str(token_render_style) in {"colored_beads", "colored_shape_tokens", "symbol_badges"}:
                    distinct_colors = sorted(
                        {
                            tuple(int(channel) for channel in bead_spec["fill_rgb"])
                            for bead_spec in option_specs[0]["bead_specs"]
                        }
                    )
                    assert len(distinct_colors) == int(execution["bead_count"])
                    assert float(execution["min_color_distance"]) == 50.0
                    assert str(execution["color_distance_space"]) == "lab"
                    for color_a, color_b in combinations(distinct_colors, 2):
                        assert float(color_distance(color_a, color_b, distance_space="lab")) >= 50.0


def test_puzzle_topology_prompt_examples_match_selected_variants() -> None:
    expected = {
        "cyclic_order_equivalent_label": (
            PuzzlesTopologyCyclicOrderEquivalentLabelTask(),
            {"evidence": [[574, 463, 746, 617]], "answer": "C"},
            {"answer": "C"},
        ),
    }
    for index, (query_id, (task, expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=27410):
        out = task.generate(index, params={}, max_attempts=10)
        assert str(out.query_id) == str(query_id)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_topology_cyclic_order_match_task_is_deterministic() -> None:
    task = PuzzlesTopologyCyclicOrderEquivalentLabelTask()
    params = {
        "token_render_style": "symbol_badges",
        "scene_variant": "charm_card_grid",
        "loop_path_style": "wavy_loop",
    }
    out_a = task.generate(27480, params=params, max_attempts=10)
    out_b = task.generate(27480, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_topology_cyclic_order_match_sampling_balances_visual_and_answer_axes() -> None:
    token_render_styles = Counter()
    scene_variants = Counter()
    loop_path_styles = Counter()
    label_variant_answer_labels = Counter()

    task = PuzzlesTopologyCyclicOrderEquivalentLabelTask()
    for sampling_index in range(200):
        out = task.generate(
            27520 + sampling_index,
            params={},
            max_attempts=10,
        )
        trace = out.trace_payload["execution_trace"]
        assert str(trace["query_id"]) == "cyclic_order_equivalent_label"
        assert int(trace["option_count"]) == 6
        token_render_styles[str(trace["token_render_style"])] += 1
        scene_variants[str(trace["scene_variant"])] += 1
        loop_path_styles[str(trace["loop_path_style"])] += 1
        label_variant_answer_labels[str(trace["answer_option_label"])] += 1

    assert_counter_support_within(
        token_render_styles,
        {"colored_beads", "shape_tokens", "colored_shape_tokens", "outline_shape_tokens", "symbol_badges"},
        expected_per_key=40,
        tolerance=15,
    )
    assert_counter_support_within(
        scene_variants,
        {"necklace_board", "charm_card_grid", "route_loop_diagram", "token_ring_outline"},
        expected_per_key=50,
        tolerance=15,
    )
    assert_counter_support_within(
        loop_path_styles,
        {"ellipse", "rounded_rect", "polygon_loop", "wavy_loop", "beaded_string"},
        expected_per_key=40,
        tolerance=15,
    )
    assert_counter_support_within(
        label_variant_answer_labels,
        {"A", "B", "C", "D", "E", "F"},
        expected_per_key=33,
        tolerance=10,
    )


def test_puzzle_topology_string_component_count_contract_matches_metadata() -> None:
    task_cases = (
        (PuzzlesTopologyStringComponentCountTask(), "open_rope_count"),
        (PuzzlesTopologyStringComponentCountTask(), "closed_loop_count"),
        (PuzzlesTopologyStringComponentCountTask(), "knotted_component_count"),
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
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert str(out.query_id) == "default"
            assert str(out.query_id) == str(query_id)
            assert str(out.scene_id) == "string_topology"
            assert out.answer_gt.type == "integer"
            assert out.evidence_gt.type == "bbox_set"
            assert int(out.answer_gt.value) == int(execution["answer_value"])
            assert int(out.answer_gt.value) == len(evidence_bboxes)
            assert int(out.answer_gt.value) >= 1
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["query_id"]) == "default"
            assert str(execution["query_id"]) == str(query_id)
            assert str(execution["internal_query_id"]) == str(query_id)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert str(execution["question_format"]) == "string_component_count"
            assert str(execution["view_family"]) == "topology_string_component_count"
            assert str(execution["topology_rule"]) == "crossings_do_not_merge_components_over_under_recorded"
            assert len(components) == int(execution["component_count"])
            assert len(groups) == int(execution["visual_group_count"])
            assert len(render_map["visual_group_bboxes_px"]) == len(groups)
            assert len(render_map["crossing_bboxes_px"]) == len(crossings)
            assert set(render_map["crossing_bboxes_px"]) == {
                str(crossing["crossing_id"]) for crossing in crossings
            }
            assert str(render_map["evidence_source"]) == str(execution["supporting_evidence_source"])
            assert str(render["layout"]) == "random_open_canvas"
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes

            assert not any(str(group["group_type"]) == "linked_pair" for group in groups)
            assert not any(str(group["group_type"]) == "tangled_rope_bundle" for group in groups)
            assert 6 <= int(execution["visual_group_count"]) <= 20
            assert 6 <= int(execution["component_count"]) <= 20
            assert int(execution["component_count"]) == int(execution["object_count"])
            assert int(execution["visual_group_count"]) == int(execution["object_count"])
            assert int(execution["answer_value"]) == int(execution["target_count"])
            assert int(execution["answer_value"]) == int(execution["target_answer"])
            assert int(execution["object_count"]) == int(execution["target_count"]) + int(execution["distractor_count"])
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
                evidence_source = render_map["component_bboxes_px"]
                expected_count = int(execution["open_rope_count"])
            elif str(query_id) == "closed_loop_count":
                expected_ids = [str(component["component_id"]) for component in components if bool(component["closed"])]
                evidence_source = render_map["component_bboxes_px"]
                expected_count = sum(1 for component in components if bool(component["closed"]))
            else:
                expected_ids = [
                    str(component["component_id"])
                    for component in components
                    if int(component.get("knot_count", 0)) > 0
                ]
                evidence_source = render_map["component_bboxes_px"]
                expected_count = sum(1 for component in components if int(component.get("knot_count", 0)) > 0)

            assert int(out.answer_gt.value) == int(expected_count)
            assert [str(value) for value in execution["supporting_item_ids"]] == expected_ids
            assert [str(value) for value in execution["solver_trace"]["supporting_item_ids"]] == expected_ids
            expected_bboxes = [
                [float(value) for value in evidence_source[str(item_id)]]
                for item_id in expected_ids
            ]
            assert evidence_bboxes == expected_bboxes

            for bbox in evidence_bboxes:
                x1, y1, x2, y2 = bbox
                assert 0.0 <= x1 < x2 <= float(render["canvas_width"])
                assert 0.0 <= y1 < y2 <= float(render["canvas_height"])

            visual_group_bboxes = [
                [float(value) for value in render_map["visual_group_bboxes_px"][str(group["visual_group_id"])]]
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


def test_puzzle_topology_string_component_prompt_examples_match_selected_variants() -> None:
    expected = {
        "open_rope_count": (
            PuzzlesTopologyStringComponentCountTask(),
            {
                "evidence": [
                    [92, 132, 266, 228],
                    [512, 176, 686, 272],
                    [786, 430, 960, 526],
                    [224, 602, 398, 698],
                ],
                "answer": 4,
            },
            {"answer": 4},
        ),
        "closed_loop_count": (
            PuzzlesTopologyStringComponentCountTask(),
            {"evidence": [[122, 168, 284, 270], [790, 168, 952, 270]], "answer": 2},
            {"answer": 2},
        ),
        "knotted_component_count": (
            PuzzlesTopologyStringComponentCountTask(),
            {"evidence": [[456, 168, 628, 290]], "answer": 1},
            {"answer": 1},
        ),
    }
    for index, (query_id, (task, expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=28610):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        assert str(out.query_id) == "default"
        assert str(out.query_id) == str(query_id)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_topology_string_component_count_task_is_deterministic() -> None:
    task = PuzzlesTopologyStringComponentCountTask()
    params = {"scene_variant": "string_card", "query_id": "knotted_component_count"}
    out_a = task.generate(28680, params=params, max_attempts=10)
    out_b = task.generate(28680, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_topology_open_rope_count_uses_knotted_closed_distractors() -> None:
    task = PuzzlesTopologyStringComponentCountTask()
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


def test_puzzle_topology_string_component_sampling_decouples_variant_scene_and_answers() -> None:
    task = PuzzlesTopologyStringComponentCountTask()
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
        assert str(trace["query_id"]) == "default"
        assert str(trace["internal_query_id"]) == str(query_id)
        combos[(query_id, str(trace["scene_variant"]))] += 1
        answers_by_variant.setdefault(query_id, set()).add(int(out.answer_gt.value))
        distractors_by_variant.setdefault(query_id, set()).add(int(trace["distractor_count"]))
        assert int(trace["object_count"]) == int(trace["target_count"]) + int(trace["distractor_count"])
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
    for sampling_index in range(120):
        out = task.generate(
            28880 + sampling_index,
            params={"scene_variant": "string_card"},
            max_attempts=10,
        )
        trace = out.trace_payload["execution_trace"]
        query_id = str(trace["query_id"])
        assert query_id == "default"
        query_id = str(trace["query_id"])
        assert str(trace["scene_variant"]) == "string_card"
        fixed_scene_answers.setdefault(query_id, set()).add(int(out.answer_gt.value))
        fixed_scene_distractors.setdefault(query_id, set()).add(int(trace["distractor_count"]))

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
        assert str(trace["query_id"]) == "default"
        assert str(trace["query_id"]) == "knotted_component_count"
        assert str(trace["internal_query_id"]) == "knotted_component_count"
        fixed_task_scenes[str(trace["scene_variant"])] += 1
        fixed_task_answers.add(int(out.answer_gt.value))
        fixed_task_distractors.add(int(trace["distractor_count"]))

    assert set(fixed_task_scenes) == {"string_strip", "string_card", "string_outline"}
    assert fixed_task_answers == expected_count_support
    assert fixed_task_distractors == expected_count_support


def test_puzzle_topology_maze_exit_label_contract_matches_maze_trace() -> None:
    task_cases = (
        (PuzzlesTopologyMazeExitReachabilityLabelTask(), "exit_reachability_label", "reachable"),
        (PuzzlesTopologyMazeExitReachabilityLabelTask(), "exit_reachability_label", "unreachable"),
        (PuzzlesTopologyMazeReachableExitCountTask(), "reachable_exit_count", None),
    )
    scene_variants = (
        "classic_wall_maze",
        "paper_labyrinth_maze",
        "block_wall_maze",
    )

    for query_id_index, (task, query_id, target_reachability) in enumerate(task_cases):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 29120 + (query_id_index * 20) + scene_index
            params = {"scene_variant": scene_variant, "query_id": query_id}
            if target_reachability is not None:
                params["target_reachability"] = target_reachability
            out = task.generate(
                seed,
                params=params,
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            supporting_ids = [str(value) for value in execution["supporting_item_ids"]]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
            reachable_labels = [str(value) for value in execution["reachable_exit_labels"]]
            unreachable_labels = [str(value) for value in execution["unreachable_exit_labels"]]

            assert str(out.query_id) == "default"
            assert str(out.query_id) == str(query_id)
            assert str(out.scene_id) == "maze"
            assert out.answer_gt.type == ("integer" if str(query_id) == "reachable_exit_count" else "string")
            assert out.evidence_gt.type == "bbox_set"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(execution["query_id"]) == "default"
            assert str(execution["query_id"]) == str(query_id)
            assert str(execution["internal_query_id"]) == str(query_id)
            assert execution["target_reachability"] == target_reachability
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert str(execution["view_family"]) == "topology_orthogonal_maze_exit_label"
            assert str(execution["topology_rule"]) == "move_through_open_corridors_from_start_walls_block_motion"
            assert 6 <= int(execution["maze_rows"]) <= 8
            assert 7 <= int(execution["maze_cols"]) <= 10
            assert 4 <= int(execution["exit_count"]) <= 6
            assert len(execution["exits"]) == int(execution["exit_count"])
            assert len(reachable_labels) == int(execution["reachable_exit_count"])
            assert len(reachable_labels) + len(unreachable_labels) == int(execution["exit_count"])
            assert str(render_map["evidence_source"]) == str(execution["supporting_evidence_source"])
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert evidence_bboxes == [
                [float(value) for value in render_map["item_bboxes_px"][str(item_id)]]
                for item_id in supporting_ids
            ]

            if str(query_id) == "exit_reachability_label" and str(target_reachability) == "reachable":
                assert len(reachable_labels) == 1
                assert str(out.answer_gt.value) == str(reachable_labels[0])
                assert len(supporting_ids) == 1
            elif str(query_id) == "exit_reachability_label" and str(target_reachability) == "unreachable":
                assert len(unreachable_labels) == 1
                assert str(out.answer_gt.value) == str(unreachable_labels[0])
                assert len(supporting_ids) == 1
            else:
                assert int(out.answer_gt.value) == len(reachable_labels)
                assert len(supporting_ids) == len(reachable_labels)

            for bbox in evidence_bboxes:
                x1, y1, x2, y2 = bbox
                assert 0.0 <= x1 < x2 <= float(render["canvas_width"])
                assert 0.0 <= y1 < y2 <= float(render["canvas_height"])


def test_puzzle_topology_maze_exit_prompt_examples_match_selected_variants() -> None:
    expected = {
        "exit_reachability_label": (
            PuzzlesTopologyMazeExitReachabilityLabelTask(),
            {"evidence": [[166, 91, 221, 146]], "answer": "C"},
            {"answer": "C"},
        ),
        "reachable_exit_count": (
            PuzzlesTopologyMazeReachableExitCountTask(),
            {"evidence": [[166, 91, 221, 146], [472, 789, 527, 844], [979, 676, 1034, 731]], "answer": 3},
            {"answer": 3},
        ),
    }
    for index, (query_id, (task, expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=29210):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        assert str(out.query_id) == str(query_id)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_topology_maze_exit_label_task_is_deterministic() -> None:
    task = PuzzlesTopologyMazeReachableExitCountTask()
    params = {"query_id": "reachable_exit_count", "scene_variant": "block_wall_maze"}
    out_a = task.generate(29280, params=params, max_attempts=10)
    out_b = task.generate(29280, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_puzzle_topology_maze_exit_sampling_decouples_variant_scene_and_counts() -> None:
    label_task = PuzzlesTopologyMazeExitReachabilityLabelTask()
    count_task = PuzzlesTopologyMazeReachableExitCountTask()
    label_scene_combos = Counter()
    count_scene_combos = Counter()
    target_combos = Counter()
    exit_counts_by_variant: dict[str, set[int]] = {}

    for sampling_index in range(120):
        out = label_task.generate(
            29320 + sampling_index,
            params={},
            max_attempts=10,
        )
        trace = out.trace_payload["execution_trace"]
        assert str(trace["query_id"]) == "exit_reachability_label"
        label_scene_combos[str(trace["scene_variant"])] += 1
        target_combos[(str(trace["target_reachability"]), str(trace["scene_variant"]))] += 1
        exit_counts_by_variant.setdefault("exit_reachability_label", set()).add(int(trace["exit_count"]))

    for sampling_index in range(120):
        out = count_task.generate(
            29480 + sampling_index,
            params={},
            max_attempts=10,
        )
        trace = out.trace_payload["execution_trace"]
        assert str(trace["query_id"]) == "reachable_exit_count"
        count_scene_combos[str(trace["scene_variant"])] += 1
        exit_counts_by_variant.setdefault("reachable_exit_count", set()).add(int(trace["exit_count"]))

    expected_scene_support = {"classic_wall_maze", "paper_labyrinth_maze", "block_wall_maze"}
    assert_counter_support_within(
        label_scene_combos,
        expected_scene_support,
        expected_per_key=40,
        tolerance=10,
    )
    assert_counter_support_within(
        count_scene_combos,
        expected_scene_support,
        expected_per_key=40,
        tolerance=10,
    )
    assert set(target_combos) == {
        ("reachable", "classic_wall_maze"),
        ("reachable", "paper_labyrinth_maze"),
        ("reachable", "block_wall_maze"),
        ("unreachable", "classic_wall_maze"),
        ("unreachable", "paper_labyrinth_maze"),
        ("unreachable", "block_wall_maze"),
    }
    assert_counter_support_within(
        target_combos,
        {
            ("reachable", "classic_wall_maze"),
            ("reachable", "paper_labyrinth_maze"),
            ("reachable", "block_wall_maze"),
            ("unreachable", "classic_wall_maze"),
            ("unreachable", "paper_labyrinth_maze"),
            ("unreachable", "block_wall_maze"),
        },
        expected_per_key=20,
        tolerance=12,
    )
    expected_exit_support = {4, 5, 6}
    assert exit_counts_by_variant["exit_reachability_label"] == expected_exit_support
    assert exit_counts_by_variant["reachable_exit_count"] == expected_exit_support


def test_puzzle_topology_maze_exit_reachability_label_samples_target_reachability() -> None:
    task = PuzzlesTopologyMazeExitReachabilityLabelTask()
    cases = {
        "reachable": "reachable",
        "unreachable": "unreachable",
    }
    for index, (target_reachability, expected) in enumerate(cases.items()):
        out = task.generate(
            29440 + index,
            params={"query_id": "exit_reachability_label", "target_reachability": target_reachability},
            max_attempts=10,
        )
        trace = out.trace_payload["execution_trace"]
        assert out.query_id == "default"
        assert out.query_id == "exit_reachability_label"
        assert trace["query_id"] == "default"
        assert trace["query_id"] == "exit_reachability_label"
        assert trace["target_reachability"] == expected


def test_puzzle_topology_voxel_ladder_contract_matches_trace() -> None:
    task_cases = (
        (PuzzlesTopologyVoxelLadderRouteLabelTask(), "checkpoint_sequence_label"),
        (PuzzlesTopologyVoxelLadderRouteLabelTask(), "unreachable_checkpoint_label"),
        (PuzzlesTopologyVoxelLadderRouteCountTask(), "reachable_checkpoint_count"),
        (PuzzlesTopologyVoxelLadderRouteCountTask(), "shortest_ladder_count"),
    )
    scene_variants = (
        "clean_isometric_voxels",
        "worksheet_voxel_maze",
        "game_board_voxel_maze",
    )
    canonical_color_names = {str(name) for name, _rgb in available_named_colors()}

    for query_index, (task, query_id) in enumerate(task_cases):
        for scene_index, scene_variant in enumerate(scene_variants):
            out = task.generate(
                29920 + (query_index * 20) + scene_index,
                params={"query_id": query_id, "scene_variant": scene_variant},
                max_attempts=10,
            )
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
            supporting_ids = [str(value) for value in execution["supporting_item_ids"]]

            assert str(out.query_id) == "default"
            assert str(out.query_id) == str(query_id)
            assert str(out.scene_id) == "voxel_ladder"
            assert str(execution["query_id"]) == "default"
            assert str(execution["query_id"]) == str(query_id)
            assert str(execution["internal_query_id"]) == str(query_id)
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert str(render["layout"]) == "isometric_voxel_platforms_with_ladders"
            assert out.evidence_gt.type == "bbox_set"
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert str(render_map["evidence_source"]) == str(execution["supporting_evidence_source"])
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert evidence_bboxes == [
                [float(value) for value in render_map["item_bboxes_px"][str(item_id)]]
                for item_id in supporting_ids
            ]

            checkpoint_specs = [dict(item) for item in execution["checkpoints"]]
            ladder_specs = [dict(item) for item in execution["ladders"]]
            route_checkpoint_labels = [str(value) for value in execution["route_checkpoint_sequence"]]
            reachable_labels = [
                str(item["label"])
                for item in checkpoint_specs
                if bool(item["reachable"])
            ]
            unreachable_labels = [
                str(item["label"])
                for item in checkpoint_specs
                if not bool(item["reachable"])
            ]
            checkpoint_color_names = [str(item["color_name"]) for item in checkpoint_specs]
            assert set(checkpoint_color_names).issubset(canonical_color_names)
            assert len(checkpoint_color_names) == len(set(checkpoint_color_names))
            assert route_checkpoint_labels == [
                str(item["color_name"])
                for item in checkpoint_specs
                if bool(item["on_goal_route"])
            ]

            if str(query_id) == "checkpoint_sequence_label":
                assert out.answer_gt.type == "option_letter"
                correct_options = [
                    str(option["option_label"])
                    for option in execution["option_specs"]
                    if bool(option["is_correct"])
                ]
                assert correct_options == [str(out.answer_gt.value)]
                assert len(execution["option_specs"]) in {4, 5}
                for option in execution["option_specs"]:
                    assert set(str(item) for item in option["sequence_items"]).issubset(canonical_color_names)
                    assert str(option["sequence_text"]) == " > ".join(str(item) for item in option["sequence_items"])
                assert supporting_ids[0] == "cube_start"
                assert supporting_ids[-1] == "cube_goal"
                for label in route_checkpoint_labels:
                    assert f"checkpoint_{label}" in supporting_ids
            elif str(query_id) == "unreachable_checkpoint_label":
                assert out.answer_gt.type == "string"
                assert str(out.answer_gt.value) in unreachable_labels
                assert str(out.answer_gt.value) in canonical_color_names
                assert supporting_ids == [f"checkpoint_{out.answer_gt.value}"]
            elif str(query_id) == "reachable_checkpoint_count":
                assert out.answer_gt.type == "integer"
                assert int(out.answer_gt.value) == len(reachable_labels)
                assert 2 <= int(out.answer_gt.value) <= 5
                assert supporting_ids == [f"checkpoint_{label}" for label in reachable_labels]
            else:
                assert str(query_id) == "shortest_ladder_count"
                assert out.answer_gt.type == "integer"
                assert int(out.answer_gt.value) == len(ladder_specs)
                assert 1 <= int(out.answer_gt.value) <= 3
                assert supporting_ids == [str(ladder["ladder_id"]) for ladder in ladder_specs]

            for bbox in evidence_bboxes:
                x1, y1, x2, y2 = bbox
                assert 0.0 <= x1 < x2 <= float(render["canvas_width"])
                assert 0.0 <= y1 < y2 <= float(render["canvas_height"])


def test_puzzle_topology_voxel_ladder_prompt_examples_match_selected_queries() -> None:
    expected = {
        "checkpoint_sequence_label": (
            PuzzlesTopologyVoxelLadderRouteLabelTask(),
            {
                "evidence": [
                    [128, 522, 206, 590],
                    [318, 404, 390, 474],
                    [472, 276, 544, 346],
                    [592, 206, 626, 336],
                    [664, 128, 736, 198],
                ],
                "answer": "B",
            },
            {"answer": "B"},
        ),
        "reachable_checkpoint_count": (
            PuzzlesTopologyVoxelLadderRouteCountTask(),
            {"evidence": [[318, 404, 390, 474], [472, 276, 544, 346], [664, 128, 736, 198]], "answer": 3},
            {"answer": 3},
        ),
    }
    for index, (query_id, (task, expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=30010):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        assert str(out.query_id) == str(query_id)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_topology_voxel_ladder_sampling_balances_public_queries_and_scenes() -> None:
    label_task = PuzzlesTopologyVoxelLadderRouteLabelTask()
    count_task = PuzzlesTopologyVoxelLadderRouteCountTask()
    label_combos = Counter()
    count_combos = Counter()
    count_answers: dict[str, set[int]] = {}

    for sampling_index in range(120):
        label_out = label_task.generate(30120 + sampling_index, params={}, max_attempts=10)
        label_trace = label_out.trace_payload["execution_trace"]
        label_combos[(str(label_trace["query_id"]), str(label_trace["scene_variant"]))] += 1

        count_out = count_task.generate(30320 + sampling_index, params={}, max_attempts=10)
        count_trace = count_out.trace_payload["execution_trace"]
        count_query = str(count_trace["query_id"])
        count_combos[(count_query, str(count_trace["scene_variant"]))] += 1
        count_answers.setdefault(count_query, set()).add(int(count_out.answer_gt.value))

    expected_label_combos = {
        (query_id, scene_variant)
        for query_id in ("checkpoint_sequence_label", "unreachable_checkpoint_label")
        for scene_variant in ("clean_isometric_voxels", "worksheet_voxel_maze", "game_board_voxel_maze")
    }
    expected_count_combos = {
        (query_id, scene_variant)
        for query_id in ("reachable_checkpoint_count", "shortest_ladder_count")
        for scene_variant in ("clean_isometric_voxels", "worksheet_voxel_maze", "game_board_voxel_maze")
    }
    assert set(label_combos) == expected_label_combos
    assert set(count_combos) == expected_count_combos
    assert min(label_combos.values()) >= 19
    assert max(label_combos.values()) <= 21
    assert min(count_combos.values()) >= 19
    assert max(count_combos.values()) <= 21
    assert count_answers["reachable_checkpoint_count"] == {2, 3, 4, 5}
    assert count_answers["shortest_ladder_count"] == {1, 2, 3}
