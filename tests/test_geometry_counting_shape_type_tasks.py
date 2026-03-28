"""Behavior tests for geometry counting shape-type task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.geometry.counting.shape_type import GeometryCountingShapeTypeTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_geometry_counting_shape_type_contract_matches_scene() -> None:
    task = GeometryCountingShapeTypeTask()
    for variant in ("triangle", "quadrilateral", "pentagon", "hexagon", "circle", "ellipse"):
        out = task.generate(
            14110 + len(variant),
            params={"task_variant": variant, "object_count": 7, "target_count": 3},
            max_attempts=700,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == 3
        assert out.evidence_gt.type == "label_set"
        assert out.evidence_gt.value == sorted(out.evidence_gt.value)
        assert len(out.evidence_gt.value) == 3
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert "graph-paper" not in out.prompt.lower()
        assert str(trace["render_spec"]["background_style"]["selected_style"]).startswith("solid_")
        assert str(execution["task_variant"]) == variant
        assert int(execution["target_count"]) == 3
        assert int(execution["object_count"]) == 7
        assert execution["question_format"] == "count_matching_labeled_objects"
        assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
        assert trace["scene_ir"]["scene_kind"] == "geometry_2d_shape_type_counting"
        assert 0.0 <= float(out.complexity.complexity_score) <= 1.0
        assert set(out.complexity.complexity_components.keys()) == {
            "visual_scan",
            "classification_reasoning",
            "ambiguity",
            "output_burden",
        }
        assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())

        class_by_label = {str(key): dict(value) for key, value in execution["class_by_label"].items()}
        matching = list(out.evidence_gt.value)
        assert matching == sorted(matching)
        assert matching == sorted(str(label) for label in execution["matching_labels"])
        assert sum(1 for attrs in class_by_label.values() if str(attrs["shape_type"]) == variant) == 3
        for label in matching:
            assert str(class_by_label[str(label)]["shape_type"]) == variant


def test_geometry_counting_shape_type_prompt_example_matches_contract() -> None:
    task = GeometryCountingShapeTypeTask()
    out = task.generate(14117, params={"task_variant": "circle"}, max_attempts=700)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 3}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert answer_and_evidence["answer"] == 3
    assert answer_and_evidence["evidence"] == ["A", "D", "F"]


def test_geometry_counting_shape_type_balanced_sampling_defaults() -> None:
    task = GeometryCountingShapeTypeTask()
    variant_counts: Counter[str] = Counter()
    target_counts: Counter[int] = Counter()
    object_counts: Counter[int] = Counter()
    for index in range(96):
        out = task.generate(
            hash64(14118, "counting_shape_type", index),
            params={"_sampling_index": index},
            max_attempts=700,
        )
        execution = out.trace_payload["execution_trace"]
        variant_counts[str(execution["task_variant"])] += 1
        target_counts[int(execution["target_count"])] += 1
        object_counts[int(execution["object_count"])] += 1
        assert 1 <= int(execution["target_count"]) < int(execution["object_count"])
    assert set(variant_counts.keys()) == {"triangle", "quadrilateral", "pentagon", "hexagon", "circle", "ellipse"}
    assert set(object_counts.keys()) == {6, 7, 8, 9}
    assert max(variant_counts.values()) - min(variant_counts.values()) <= 1
    assert max(target_counts.values()) - min(target_counts.values()) <= 1
    assert min(target_counts.keys()) >= 1
    assert max(target_counts.keys()) <= 8
