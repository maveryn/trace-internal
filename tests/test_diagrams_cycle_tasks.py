"""Behavior tests for diagrams cycle tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.diagrams.cycle.offset_stage_label import DiagramsCycleOffsetStageLabelTask
from tests.helpers import extract_prompt_json_example


def test_diagrams_cycle_offset_stage_label_contract_matches_answer_stage_bbox() -> None:
    task = DiagramsCycleOffsetStageLabelTask()
    task_variants = ("after_k_steps", "before_k_steps")

    for variant_index, task_variant in enumerate(task_variants):
        seed = 61400 + variant_index
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": "cycle_ring"}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

        assert out.answer_gt.type == "string"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(out.task_variant) == str(task_variant)
        assert str(execution["task_variant"]) == str(task_variant)
        assert str(execution["scene_variant"]) == "cycle_ring"
        assert str(execution["question_format"]) == "cycle_offset_stage_label"
        assert str(execution["view_family"]) == "cycle_diagram"
        assert str(execution["direction"]) == "clockwise"
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert len(evidence_bboxes) == 1
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert str(out.answer_gt.value) == str(execution["answer_stage_label"])

        expected_bbox = [
            float(value)
            for value in render_map["stage_bboxes_px"][str(execution["answer_stage_bbox_id"])]
        ]
        assert evidence_bboxes == [expected_bbox]
        assert [str(item) for item in execution["supporting_stage_bbox_ids"]] == [str(execution["answer_stage_bbox_id"])]
        assert len(execution["stage_specs"]) == int(execution["stage_count"])
        assert len(render_map["stage_bboxes_px"]) == int(execution["stage_count"])
        assert len(render_map["edge_bboxes_px"]) == int(execution["stage_count"])


def test_diagrams_cycle_prompt_examples_match_variant_contract() -> None:
    task = DiagramsCycleOffsetStageLabelTask()
    expected = {
        "after_k_steps": (
            {"evidence": [[747, 242, 869, 300]], "answer": "Mina"},
            {"answer": "Mina"},
        ),
        "before_k_steps": (
            {"evidence": [[329, 641, 451, 699]], "answer": "Davi"},
            {"answer": "Davi"},
        ),
    }

    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=61460):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_diagrams_cycle_offset_stage_label_is_deterministic() -> None:
    task = DiagramsCycleOffsetStageLabelTask()
    params = {"task_variant": "before_k_steps", "scene_variant": "cycle_ring"}
    out_a = task.generate(61510, params=params, max_attempts=10)
    out_b = task.generate(61510, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_diagrams_cycle_balanced_sampling_defaults_cover_variants() -> None:
    task = DiagramsCycleOffsetStageLabelTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()

    for index in range(12):
        out = task.generate(hash64(61540, "diagrams_cycle", index), params={"_sampling_index": index}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(task_variants.keys()) == {"after_k_steps", "before_k_steps"}
    assert set(scene_variants.keys()) == {"cycle_ring"}


def test_diagrams_cycle_uses_short_names_and_respects_stage_and_step_ranges() -> None:
    task = DiagramsCycleOffsetStageLabelTask()
    out = task.generate(61590, params={"task_variant": "after_k_steps", "scene_variant": "cycle_ring"}, max_attempts=10)
    execution = out.trace_payload["execution_trace"]
    stage_count = int(execution["stage_count"])
    step_count = int(execution["step_count"])

    assert 5 <= stage_count <= 10
    assert 1 <= step_count <= stage_count - 1
    for stage_spec in execution["stage_specs"]:
        label = str(stage_spec["stage_label"])
        assert " " not in label
        assert 2 <= len(label) <= 8

    query_index = int(execution["query_stage_index"])
    answer_index = int(execution["answer_stage_index"])
    assert answer_index == (query_index + step_count) % stage_count


def test_diagrams_cycle_before_variant_is_harder_than_after_variant() -> None:
    task = DiagramsCycleOffsetStageLabelTask()
    after = task.generate(61620, params={"task_variant": "after_k_steps", "scene_variant": "cycle_ring"}, max_attempts=10)
    before = task.generate(61620, params={"task_variant": "before_k_steps", "scene_variant": "cycle_ring"}, max_attempts=10)

    assert float(before.complexity.complexity_components["reasoning_load"]) > float(
        after.complexity.complexity_components["reasoning_load"]
    )
