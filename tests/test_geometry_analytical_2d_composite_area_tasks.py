"""Behavior tests for geometry analytical 2D composite-area task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.geometry.analytical_2d.composite_area import (
    COMPOSITE_AREA_VARIANTS,
    GeometryAnalyticalCompositeArea2DTask,
)


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_analytical_composite_area_variants_match_contract() -> None:
    task = GeometryAnalyticalCompositeArea2DTask()
    for index, variant in enumerate(COMPOSITE_AREA_VARIANTS):
        out = task.generate(9750 + index, params={"task_variant": variant}, max_attempts=360)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        assert str(out.task_variant) == str(variant)
        assert out.answer_gt.type == "integer"
        assert isinstance(out.answer_gt.value, int)
        assert out.evidence_gt.type == "measurement_ref_map"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
        assert set(out.evidence_gt.value.keys()) == set(execution["required_annotations"])
        assert out.evidence_gt.value == execution["evidence_map"]
        assert execution["answer_value"] == out.answer_gt.value
        assert execution["target_quantity"] == "area"
        assert execution["scene_kind"] == "composite_region"
        assert "area" in str(out.prompt).lower()
        assert "shaded" in str(out.prompt).lower()
        for annotation in out.evidence_gt.value:
            assert str(annotation) in trace["render_map"]["annotation_centers"]


def test_analytical_composite_area_prompt_examples_match_active_case() -> None:
    task = GeometryAnalyticalCompositeArea2DTask()
    for index in range(25):
        out = task.generate(
            hash64(9751, "analytical_composite_area", index),
            params={"_sampling_index": index},
            max_attempts=360,
        )
        example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        assert list(example.keys()) == ["evidence", "answer"]
        assert isinstance(example["evidence"], dict)
        assert set(example["evidence"].keys()) == set(out.evidence_gt.value.keys())
        assert isinstance(example["answer"], int)


def test_analytical_composite_area_balanced_variant_sampling_defaults() -> None:
    task = GeometryAnalyticalCompositeArea2DTask()
    counts: Counter[str] = Counter()
    for index in range(len(COMPOSITE_AREA_VARIANTS) * 12):
        out = task.generate(
            hash64(9752, "analytical_composite_area", index),
            params={"_sampling_index": index},
            max_attempts=360,
        )
        counts[str(out.task_variant)] += 1
    assert set(counts.keys()) == set(COMPOSITE_AREA_VARIANTS)
    assert max(counts.values()) - min(counts.values()) <= 1


def test_analytical_composite_area_uses_reduced_scene_fill_ratio() -> None:
    task = GeometryAnalyticalCompositeArea2DTask()
    out = task.generate(
        9753,
        params={
            "task_variant": "rectangle_inner_cutout",
            "canvas_size": 512,
            "graph_cells": 6,
            "analytical_unit_spacing_px": 8,
            "dimension_min": 18,
            "dimension_max": 18,
            "answer_min": 20,
            "answer_max": 2500,
        },
        max_attempts=420,
    )
    assert out.answer_gt.type == "integer"
    assert str(out.task_variant) == "rectangle_inner_cutout"
