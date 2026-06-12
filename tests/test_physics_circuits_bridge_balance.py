"""Contract tests for physics balanced bridge-circuit tasks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.scene_config import get_scene_defaults
from trace.tasks.physics.circuits.bridge_balance import PhysicsBridgeCircuitMissingResistanceValueTask
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def _assert_keyed_bbox_map_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "keyed_bbox_map"
    for bbox in out.annotation_gt.value.values():
        assert 0 <= bbox[0] < bbox[2] <= width
        assert 0 <= bbox[1] < bbox[3] <= height


@pytest.mark.parametrize("missing_resistor", ("R1", "R2", "R3", "R4"))
def test_physics_bridge_missing_resistance_answer_matches_balance(missing_resistor: str) -> None:
    out = PhysicsBridgeCircuitMissingResistanceValueTask().generate(
        28001,
        params={
            "missing_resistor": missing_resistor,
            "target_answer": 8,
            "accent_color_name": "cyan",
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    values = {str(key): int(value) for key, value in execution["resistor_values"].items()}
    known_labels = set(values) - {missing_resistor}

    assert out.scene_id == "bridge_circuit"
    assert out.query_id == "missing_bridge_resistance"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == values[missing_resistor] == 8
    assert values["R1"] * values["R4"] == values["R2"] * values["R3"]
    assert execution["bridge_balance_product_left"] == execution["bridge_balance_product_right"]
    assert execution["zero_meter_reading"] == 0
    assert set(out.annotation_gt.value) == known_labels | {"target_resistor", "zero_meter"}
    assert missing_resistor not in out.annotation_gt.value
    _assert_keyed_bbox_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value


def test_physics_bridge_missing_resistance_accepts_explicit_balanced_values() -> None:
    out = PhysicsBridgeCircuitMissingResistanceValueTask().generate(
        28011,
        params={
            "missing_resistor": "R3",
            "target_answer": 12,
            "resistor_values": {"R1": 6, "R2": 10, "R3": 12, "R4": 20},
        },
        max_attempts=20,
    )

    assert out.answer_gt.value == 12
    assert out.trace_payload["execution_trace"]["resistor_values"] == {"R1": 6, "R2": 10, "R3": 12, "R4": 20}
    assert "target_resistor" in out.annotation_gt.value


def test_physics_bridge_missing_resistance_rejects_unbalanced_explicit_values() -> None:
    with pytest.raises(ValueError, match="balanced bridge equation"):
        PhysicsBridgeCircuitMissingResistanceValueTask().generate(
            28021,
            params={
                "missing_resistor": "R4",
                "target_answer": 5,
                "resistor_values": {"R1": 2, "R2": 3, "R3": 4, "R4": 5},
            },
            max_attempts=20,
        )


def test_physics_bridge_missing_resistance_task_is_deterministic() -> None:
    params = {
        "missing_resistor": "R2",
        "target_answer": 9,
        "accent_color_name": "purple",
    }
    task = PhysicsBridgeCircuitMissingResistanceValueTask()
    out_a = task.generate(28031, params=params, max_attempts=20)
    out_b = task.generate(28031, params=params, max_attempts=20)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_bridge_missing_resistance_defaults_and_prompt_bundle() -> None:
    cfg = get_scene_defaults("physics", "circuits")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_circuits_bridge_missing_resistance_family",
    )
    bundle = json.loads(Path("prompts/physics/circuits/physics_circuits_v0.json").read_text(encoding="utf-8"))

    assert set(generation["query_id_weights"]) == {"missing_bridge_resistance"}
    assert set(generation["scene_variant_weights"]) == {"rectangular_bridge"}
    assert set(generation["missing_resistor_weights"]) == {"R1", "R2", "R3", "R4"}
    assert list(generation["target_answer_support"]) == list(range(1, 21))
    assert int(rendering["component_label_font_size_px"]) == 20
    assert str(prompt["scene_key"]) == "bridge_circuit_diagram"
    assert str(prompt["task_key"]) == "bridge_missing_resistance_query"
    assert "bridge_circuit_diagram" in bundle["scene_templates"]
    assert "missing_bridge_resistance" in bundle["query_templates"]
    assert len(bundle["query_templates"]["missing_bridge_resistance"]) == 5
