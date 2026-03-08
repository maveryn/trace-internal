"""Behavior tests for geometry analytical 2D area task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.geometry.analytical_2d.area import GeometryAnalyticalArea2DTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _pi_coeff(value: str) -> int:
    text = str(value).strip()
    if text == "π":
        return 1
    assert text.endswith("π")
    return int(text[:-1])


def test_analytical_area_variants_match_contract() -> None:
    task = GeometryAnalyticalArea2DTask()
    cases = [
        ("rectangle", "explicit"),
        ("rectangle", "derived"),
        ("triangle", "explicit"),
        ("triangle", "derived"),
        ("parallelogram", "explicit"),
        ("parallelogram", "derived"),
        ("trapezoid", "explicit"),
        ("trapezoid", "derived"),
        ("rhombus", "explicit"),
        ("rhombus", "derived"),
        ("circle", "explicit"),
        ("circle", "derived"),
        ("ellipse", "explicit"),
        ("ellipse", "derived"),
    ]
    for index, (shape, mode) in enumerate(cases):
        out = task.generate(
            9200 + index,
            params={"query_type": "measure", "shape_variant": shape, "reasoning_mode": mode},
            max_attempts=260,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        assert out.query_type == "measure"
        assert out.evidence_gt.type == "measurement_ref_map"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
        assert str(execution["shape_variant"]) == str(shape)
        assert str(execution["reasoning_mode"]) == str(mode)
        assert str(trace["scene_ir"]["entities"][0]["entity_type"]) == str(shape)
        evidence_map = dict(out.evidence_gt.value)
        assert set(evidence_map.keys()) == set(execution["evidence_ids"])
        assert evidence_map == execution["evidence_map"]
        for annotation, payload in evidence_map.items():
            assert str(annotation).strip()
            assert isinstance(payload, (int, float, str))
            assert str(annotation) in trace["render_map"]["annotation_centers"]
        assert "area" in str(out.prompt).lower()
        background_style = trace["render_spec"]["background_style"]
        assert str(background_style.get("selected_style", "")).startswith("solid_")

        if shape in {"circle", "ellipse"}:
            assert out.answer_gt.type == "pi_expression"
            assert str(out.answer_gt.value).endswith("π")
            assert int(_pi_coeff(str(out.answer_gt.value))) == int(execution["answer_scalar"])
        else:
            assert out.answer_gt.type == "integer"
            assert int(out.answer_gt.value) == int(execution["answer_scalar"])


def test_analytical_area_prompt_examples_match_active_case() -> None:
    task = GeometryAnalyticalArea2DTask()
    for index in range(40):
        out = task.generate(
            hash64(9101, "analytical_area", index),
            params={"query_type": "measure", "_sampling_index": index},
            max_attempts=260,
        )
        example = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        assert list(example.keys()) == ["evidence", "answer"]
        assert isinstance(example["evidence"], dict)
        assert set(example["evidence"].keys()) == set(out.evidence_gt.value.keys())
        for payload in example["evidence"].values():
            assert isinstance(payload, (int, float, str))
        if out.answer_gt.type == "pi_expression":
            assert isinstance(example["answer"], str)
            assert str(example["answer"]).endswith("π")
        else:
            assert int(example["answer"]) >= 0


def test_analytical_area_balanced_shape_and_mode_sampling_defaults() -> None:
    task = GeometryAnalyticalArea2DTask()
    shape_counts: Counter[str] = Counter()
    mode_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    for index in range(140):
        out = task.generate(
            hash64(9102, "analytical_area", index),
            params={"query_type": "measure", "_sampling_index": index},
            max_attempts=260,
        )
        shape = str(out.trace_payload["execution_trace"]["shape_variant"])
        mode = str(out.trace_payload["execution_trace"]["reasoning_mode"])
        shape_counts[shape] += 1
        mode_counts[mode] += 1
        pair_counts[(shape, mode)] += 1
    assert set(shape_counts.keys()) == {
        "rectangle",
        "triangle",
        "parallelogram",
        "trapezoid",
        "rhombus",
        "circle",
        "ellipse",
    }
    assert set(mode_counts.keys()) == {"explicit", "derived"}
    assert max(shape_counts.values()) - min(shape_counts.values()) <= 1
    assert max(mode_counts.values()) - min(mode_counts.values()) <= 1
    assert max(pair_counts.values()) - min(pair_counts.values()) <= 1
