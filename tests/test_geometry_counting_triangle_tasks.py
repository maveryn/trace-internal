"""Behavior tests for geometry counting triangle task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.geometry.counting.triangle import GeometryCountingTriangleTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_geometry_counting_triangle_contract_matches_scene() -> None:
    task = GeometryCountingTriangleTask()
    for variant in (
        "equilateral_triangle",
        "isosceles_triangle",
        "scalene_triangle",
        "right_triangle",
        "acute_triangle",
        "obtuse_triangle",
    ):
        out = task.generate(
            11210 + len(variant),
            params={"task_variant": variant, "object_count": 7, "target_count": 3},
            max_attempts=500,
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
        assert trace["scene_ir"]["scene_kind"] == "geometry_2d_triangle_counting"

        class_by_label = {
            str(key): dict(value) for key, value in execution["class_by_label"].items()
        }
        matching = list(out.evidence_gt.value)
        assert matching == sorted(matching)
        assert matching == sorted(str(label) for label in execution["matching_labels"])
        if variant == "equilateral_triangle":
            assert sum(1 for attrs in class_by_label.values() if str(attrs["side_kind"]) == "equilateral") == 3
        elif variant == "isosceles_triangle":
            assert sum(1 for attrs in class_by_label.values() if str(attrs["side_kind"]) == "isosceles") == 3
        elif variant == "scalene_triangle":
            assert sum(1 for attrs in class_by_label.values() if str(attrs["side_kind"]) == "scalene") == 3
        elif variant == "right_triangle":
            assert sum(1 for attrs in class_by_label.values() if str(attrs["angle_kind"]) == "right") == 3
        elif variant == "acute_triangle":
            assert sum(1 for attrs in class_by_label.values() if str(attrs["angle_kind"]) == "acute") == 3
        else:
            assert sum(1 for attrs in class_by_label.values() if str(attrs["angle_kind"]) == "obtuse") == 3
        for label in matching:
            attrs = class_by_label[str(label)]
            if variant.endswith("triangle") and variant.startswith("equilateral"):
                assert str(attrs["side_kind"]) == "equilateral"
            elif variant == "isosceles_triangle":
                assert str(attrs["side_kind"]) == "isosceles"
            elif variant == "scalene_triangle":
                assert str(attrs["side_kind"]) == "scalene"
            elif variant == "right_triangle":
                assert str(attrs["angle_kind"]) == "right"
            elif variant == "acute_triangle":
                assert str(attrs["angle_kind"]) == "acute"
            elif variant == "obtuse_triangle":
                assert str(attrs["angle_kind"]) == "obtuse"


def test_geometry_counting_triangle_prompt_example_matches_contract() -> None:
    task = GeometryCountingTriangleTask()
    out = task.generate(11217, params={"task_variant": "acute_triangle"}, max_attempts=500)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 3}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert answer_and_evidence["answer"] == 3
    assert answer_and_evidence["evidence"] == ["A", "C", "F"]


def test_geometry_counting_triangle_balanced_sampling_defaults() -> None:
    task = GeometryCountingTriangleTask()
    variant_counts: Counter[str] = Counter()
    object_counts: Counter[int] = Counter()
    target_counts: Counter[int] = Counter()
    for index in range(96):
        out = task.generate(
            hash64(11218, "counting_triangle", index),
            params={"_sampling_index": index},
            max_attempts=500,
        )
        execution = out.trace_payload["execution_trace"]
        variant_counts[str(execution["task_variant"])] += 1
        object_counts[int(execution["object_count"])] += 1
        target_counts[int(execution["target_count"])] += 1
        assert 1 <= int(execution["target_count"]) < int(execution["object_count"])
    assert set(variant_counts.keys()) == {
        "equilateral_triangle",
        "isosceles_triangle",
        "scalene_triangle",
        "right_triangle",
        "acute_triangle",
        "obtuse_triangle",
    }
    assert set(object_counts.keys()) == {5, 6, 7, 8}
    assert max(variant_counts.values()) - min(variant_counts.values()) <= 1
    assert max(target_counts.values()) - min(target_counts.values()) <= 1
    assert min(target_counts.keys()) >= 1
    assert max(target_counts.keys()) <= 7
