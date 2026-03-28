"""Behavior tests for geometry analytical 3D surface-area task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.geometry.analytical_3d.surface_area import GeometryAnalyticalSurfaceArea3DTask
from trace.tasks.geometry.shared.analytical_3d_solids import (
    INTEGER_SURFACE_AREA_VARIANTS,
    PI_SURFACE_AREA_VARIANTS,
    SURFACE_AREA_VARIANTS,
)


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


def _expected_surface_area_scalar(execution: dict) -> int:
    variant = str(execution["task_variant"])
    role_values = dict(execution["evidence_role_values"])
    if variant == "rectangular_prism_given_lwh":
        length = int(role_values["l"])
        width = int(role_values["w"])
        height = int(role_values["h"])
        return 2 * ((length * width) + (length * height) + (width * height))
    if variant == "triangular_prism_given_a_b_c_l":
        return (int(role_values["a"]) * int(role_values["b"])) + (
            int(role_values["L"]) * (int(role_values["a"]) + int(role_values["b"]) + int(role_values["c"]))
        )
    if variant == "square_pyramid_given_base_side_slant_height":
        side = int(role_values["s"])
        slant = int(role_values["l"])
        return (side * side) + (2 * side * slant)
    if variant == "cylinder_given_r_h":
        radius = int(role_values["r"])
        height = int(role_values["h"])
        return 2 * radius * (radius + height)
    if variant == "cone_given_r_slant_height":
        radius = int(role_values["r"])
        slant = int(role_values["l"])
        return radius * (radius + slant)
    if variant == "sphere_given_r":
        radius = int(role_values["r"])
        return 4 * radius * radius
    raise AssertionError(f"unexpected surface-area variant: {variant}")


def test_analytical_3d_surface_area_variants_match_contract() -> None:
    task = GeometryAnalyticalSurfaceArea3DTask()
    for index, variant in enumerate(SURFACE_AREA_VARIANTS):
        out = task.generate(
            99100 + index,
            params={"task_variant": variant},
            max_attempts=320,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        assert str(out.task_variant) == str(variant)
        assert out.evidence_gt.type == "measurement_ref_map"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
        assert str(execution["task_variant"]) == str(variant)
        evidence_map = dict(out.evidence_gt.value)
        assert set(evidence_map.keys()) == set(execution["required_annotations"])
        assert evidence_map == execution["evidence_map"]
        assert all(str(key).strip() for key in evidence_map.keys())
        assert 0.0 <= float(out.complexity.complexity_score) <= 1.0
        assert set(out.complexity.complexity_components.keys()) == {
            "visual_scan",
            "analytical_reasoning",
            "ambiguity",
            "output_burden",
        }
        assert "surface area" in str(out.prompt).lower()
        assert int(execution["answer_scalar"]) == int(_expected_surface_area_scalar(execution))
        question_text = str(trace["query_spec"]["prompt_variant"]["slot_values"]["question_text"]).lower()
        assert not question_text.startswith("use the annotated")
        background_style = trace["render_spec"]["background_style"]
        assert str(background_style.get("selected_style", "")).startswith("solid_")
        if variant in INTEGER_SURFACE_AREA_VARIANTS:
            assert out.answer_gt.type == "integer"
            assert int(out.answer_gt.value) == int(execution["answer_scalar"])
        else:
            assert variant in PI_SURFACE_AREA_VARIANTS
            assert out.answer_gt.type == "pi_expression"
            assert str(out.answer_gt.value).endswith("π")
            assert int(_pi_coeff(str(out.answer_gt.value))) == int(execution["answer_scalar"])

        if str(variant) == "cylinder_given_r_h":
            attrs = trace["scene_ir"]["entities"][0]["attrs"]
            cap_radius_y_px = float(attrs["render_cap_radius_y_px"])
            height_px = float(attrs["render_height_px"])
            assert (2.0 * float(cap_radius_y_px)) < float(height_px)


def test_analytical_3d_surface_area_prompt_examples_match_active_case() -> None:
    task = GeometryAnalyticalSurfaceArea3DTask()
    for index in range(40):
        out = task.generate(
            hash64(99101, "analytical_3d_surface_area", index),
            params={"_sampling_index": index},
            max_attempts=320,
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


def test_analytical_3d_surface_area_balanced_variant_sampling_defaults() -> None:
    task = GeometryAnalyticalSurfaceArea3DTask()
    counts: Counter[str] = Counter()
    for index in range(60):
        out = task.generate(
            hash64(99102, "analytical_3d_surface_area_balance", index),
            params={"_sampling_index": index},
            max_attempts=320,
        )
        counts[str(out.trace_payload["execution_trace"]["task_variant"])] += 1
    assert set(counts.keys()) == set(SURFACE_AREA_VARIANTS)
    assert max(counts.values()) - min(counts.values()) <= 1
