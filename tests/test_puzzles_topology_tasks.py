"""Behavior tests for puzzle topology tasks."""

from __future__ import annotations

from trace.tasks.puzzles.shared.bead_loop_common import bead_sequences_are_rotation_equivalent
from trace.tasks.puzzles.topology.bead_equivalence_count import PuzzlesTopologyBeadEquivalenceCountTask
from tests.helpers import extract_prompt_json_example


def test_puzzle_topology_bead_equivalence_count_contract_matches_valid_options() -> None:
    task = PuzzlesTopologyBeadEquivalenceCountTask()
    task_variants = (
        "color_cycle_count",
        "shape_cycle_count",
        "mixed_cycle_count",
    )
    scene_variants = (
        "loop_strip",
        "loop_card",
        "loop_outline",
    )

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 27320 + (variant_index * 20) + scene_index
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

            assert str(out.task_variant) == str(task_variant)
            assert out.answer_gt.type == "integer"
            assert out.evidence_gt.type == "bbox_set"
            assert int(out.answer_gt.value) == int(execution["valid_option_count"])
            assert len(evidence_bboxes) == int(out.answer_gt.value)
            assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert list(execution["option_count_range"]) == [6, 7]
            assert list(execution["valid_option_count_range"]) == [1, 5]
            assert int(execution["option_count"]) in {6, 7}
            assert 1 <= int(execution["valid_option_count"]) <= 5
            assert 5 <= int(execution["bead_count"]) <= 7
            assert str(execution["question_format"]) == "bead_equivalence_count"
            assert str(execution["view_family"]) == "topology_loop_option_count"
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


def test_puzzle_topology_prompt_examples_match_selected_variants() -> None:
    task = PuzzlesTopologyBeadEquivalenceCountTask()
    expected = {
        "color_cycle_count": (
            {"evidence": [[174, 463, 346, 617], [574, 463, 746, 617]], "answer": 2},
            {"answer": 2},
        ),
        "shape_cycle_count": (
            {"evidence": [[374, 463, 546, 617], [774, 463, 946, 617], [174, 671, 346, 825]], "answer": 3},
            {"answer": 3},
        ),
        "mixed_cycle_count": (
            {"evidence": [[574, 671, 746, 825]], "answer": 1},
            {"answer": 1},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=27410):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_puzzle_topology_bead_equivalence_count_task_is_deterministic() -> None:
    task = PuzzlesTopologyBeadEquivalenceCountTask()
    params = {"task_variant": "mixed_cycle_count", "scene_variant": "loop_card"}
    out_a = task.generate(27480, params=params, max_attempts=10)
    out_b = task.generate(27480, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()
