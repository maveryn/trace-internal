"""Behavior tests for geometry analytical 2D length task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.geometry.analytical_2d.length import GeometryAnalyticalLength2DTask, LENGTH_VARIANTS


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_analytical_length_variants_match_contract() -> None:
    task = GeometryAnalyticalLength2DTask()
    for index, variant in enumerate(LENGTH_VARIANTS):
        out = task.generate(
            9600 + index,
            params={"task_variant": variant},
            max_attempts=320,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        assert str(out.task_variant) == str(variant)
        assert out.answer_gt.type == "number"
        assert isinstance(out.answer_gt.value, float)
        assert out.evidence_gt.type == "measurement_ref_map"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
        assert set(out.evidence_gt.value.keys()) == set(execution["required_annotations"])
        assert out.evidence_gt.value == execution["evidence_map"]
        assert 0.0 <= float(out.complexity.complexity_score) <= 1.0
        assert set(out.complexity.complexity_components.keys()) == {
            "visual_scan",
            "analytical_reasoning",
            "ambiguity",
            "output_burden",
        }
        assert execution["answer_value"] == out.answer_gt.value
        assert abs(float(execution["answer_value"]) - round(float(execution["raw_answer_value"]), 1)) <= 1e-9
        assert str(execution["target_annotation"]).strip()
        assert "length" in str(out.prompt).lower()
        assert "one decimal place" in str(out.prompt).lower()
        for annotation in out.evidence_gt.value:
            assert str(annotation) in trace["render_map"]["annotation_centers"]


def test_analytical_length_prompt_examples_match_active_case() -> None:
    task = GeometryAnalyticalLength2DTask()
    for index in range(30):
        out = task.generate(
            hash64(9601, "analytical_length", index),
            params={"_sampling_index": index},
            max_attempts=320,
        )
        example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        assert list(example.keys()) == ["evidence", "answer"]
        assert isinstance(example["evidence"], dict)
        assert set(example["evidence"].keys()) == set(out.evidence_gt.value.keys())
        assert isinstance(example["answer"], float)


def test_analytical_length_balanced_variant_sampling_defaults() -> None:
    task = GeometryAnalyticalLength2DTask()
    counts: Counter[str] = Counter()
    for index in range(len(LENGTH_VARIANTS) * 12):
        out = task.generate(
            hash64(9602, "analytical_length", index),
            params={"_sampling_index": index},
            max_attempts=320,
        )
        counts[str(out.task_variant)] += 1
    assert set(counts.keys()) == set(LENGTH_VARIANTS)
    assert max(counts.values()) - min(counts.values()) <= 1


def test_analytical_length_unit_scale_is_decoupled_from_graph_cells() -> None:
    task = GeometryAnalyticalLength2DTask()
    out = task.generate(
        9603,
        params={
            "task_variant": "triangle_altitude_side",
            "canvas_size": 512,
            "graph_cells": 6,
            "analytical_unit_spacing_px": 8,
            "dimension_min": 18,
            "dimension_max": 18,
            "answer_min": 10,
            "answer_max": 100,
        },
        max_attempts=400,
    )
    assert out.answer_gt.type == "number"
    assert str(out.task_variant) == "triangle_altitude_side"
