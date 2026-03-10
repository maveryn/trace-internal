"""Behavior tests for geometry analytical 3D volume task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.geometry.analytical_3d.volume import GeometryAnalyticalVolume3DTask
from trace.tasks.geometry.shared.analytical_3d_volume import (
    INTEGER_VOLUME_VARIANTS,
    PI_VOLUME_VARIANTS,
    VOLUME_VARIANTS,
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


def test_analytical_3d_volume_variants_match_contract() -> None:
    task = GeometryAnalyticalVolume3DTask()
    for index, variant in enumerate(VOLUME_VARIANTS):
        out = task.generate(
            99100 + index,
            params={"task_variant": variant},
            max_attempts=260,
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
        assert "volume" in str(out.prompt).lower()
        question_text = str(trace["query_spec"]["prompt_variant"]["slot_values"]["question_text"]).lower()
        assert not question_text.startswith("use the annotated")
        background_style = trace["render_spec"]["background_style"]
        assert str(background_style.get("selected_style", "")).startswith("solid_")
        if variant in INTEGER_VOLUME_VARIANTS:
            assert out.answer_gt.type == "integer"
            assert int(out.answer_gt.value) == int(execution["answer_scalar"])
        else:
            assert variant in PI_VOLUME_VARIANTS
            assert out.answer_gt.type == "pi_expression"
            assert str(out.answer_gt.value).endswith("π")
            assert int(_pi_coeff(str(out.answer_gt.value))) == int(execution["answer_scalar"])

        if str(variant) == "cylinder_given_r_h":
            attrs = trace["scene_ir"]["entities"][0]["attrs"]
            cap_radius_y_px = float(attrs["render_cap_radius_y_px"])
            height_px = float(attrs["render_height_px"])
            assert (2.0 * float(cap_radius_y_px)) < float(height_px)


def test_analytical_3d_volume_prompt_examples_match_active_case() -> None:
    task = GeometryAnalyticalVolume3DTask()
    for index in range(40):
        out = task.generate(
            hash64(99101, "analytical_3d_volume", index),
            params={"_sampling_index": index},
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


def test_analytical_3d_volume_balanced_variant_sampling_defaults() -> None:
    task = GeometryAnalyticalVolume3DTask()
    counts: Counter[str] = Counter()
    for index in range(60):
        out = task.generate(
            hash64(99102, "analytical_3d_volume_balance", index),
            params={"_sampling_index": index},
            max_attempts=260,
        )
        counts[str(out.trace_payload["execution_trace"]["task_variant"])] += 1
    assert set(counts.keys()) == set(VOLUME_VARIANTS)
    assert max(counts.values()) - min(counts.values()) <= 1
