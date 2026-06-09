"""Contract tests for physics switch-circuit lit-bulb counting."""

from __future__ import annotations

import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.task_group_config import get_task_group_defaults
from trace.tasks.physics.circuits.switch_circuit import (
    PhysicsSwitchCircuitLitBulbCountTask,
    _lit_bulbs_from_edges,
    _make_edges,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults
from tests.helpers import read_jsonl


def _assert_bbox_set_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "bbox_set"
    for bbox in out.annotation_gt.value:
        assert 0 <= bbox[0] < bbox[2] <= width
        assert 0 <= bbox[1] < bbox[3] <= height


def test_physics_switch_circuit_target_answer_support() -> None:
    task = PhysicsSwitchCircuitLitBulbCountTask()
    for target_answer in range(6):
        out = task.generate(
            28800 + target_answer,
            params={"target_answer": target_answer},
            max_attempts=20,
        )
        render_map = out.trace_payload["render_map"]

        assert out.scene_id == "switch_circuit"
        assert out.query_id == "lit_bulb_count"
        assert out.answer_gt.type == "integer"
        assert out.answer_gt.value == target_answer
        assert len(out.annotation_gt.value) == target_answer
        assert render_map["lit_bulbs"] == out.trace_payload["execution_trace"]["lit_bulbs"]
        assert render_map["annotation_bbox_set"] == out.annotation_gt.value
        assert len(render_map["bulb_bboxes"]) == 5
        assert len(render_map["switch_bboxes"]) == 5
        _assert_bbox_set_in_bounds(out)


def test_physics_switch_circuit_explicit_switch_state_logic() -> None:
    states = {
        "S1": "closed",
        "S2": "closed",
        "S3": "open",
        "S4": "closed",
        "S5": "open",
    }
    out = PhysicsSwitchCircuitLitBulbCountTask().generate(
        28831,
        params={"target_answer": 3, "switch_states": states},
        max_attempts=20,
    )

    assert out.answer_gt.value == 3
    assert out.trace_payload["execution_trace"]["lit_bulbs"] == ["B1", "B2", "B4"]
    assert len(out.annotation_gt.value) == 3
    assert out.annotation_gt.value == [
        out.trace_payload["render_map"]["bulb_bboxes"]["B1"],
        out.trace_payload["render_map"]["bulb_bboxes"]["B2"],
        out.trace_payload["render_map"]["bulb_bboxes"]["B4"],
    ]


def test_physics_switch_circuit_empty_annotation_for_zero_count() -> None:
    out = PhysicsSwitchCircuitLitBulbCountTask().generate(
        28841,
        params={
            "target_answer": 0,
            "switch_states": {
                "S1": "open",
                "S2": "open",
                "S3": "closed",
                "S4": "closed",
                "S5": "open",
            },
        },
        max_attempts=20,
    )

    assert out.answer_gt.value == 0
    assert out.annotation_gt.type == "bbox_set"
    assert out.annotation_gt.value == []
    assert out.trace_payload["projected_annotation"]["bbox_set"] == []
    assert out.trace_payload["execution_trace"]["lit_bulbs"] == []


def test_physics_switch_circuit_graph_edge_lighting_logic() -> None:
    states = {
        "S1": True,
        "S2": True,
        "S3": False,
        "S4": True,
        "S5": False,
    }

    assert _lit_bulbs_from_edges(_make_edges(states)) == ("B1", "B2", "B4")
    assert _lit_bulbs_from_edges(_make_edges({label: False for label in states})) == ()
    assert _lit_bulbs_from_edges(_make_edges({label: True for label in states})) == ("B1", "B2", "B3", "B4", "B5")


def test_physics_switch_circuit_is_deterministic() -> None:
    params = {
        "target_answer": 4,
        "accent_color_name": "cyan",
    }
    task = PhysicsSwitchCircuitLitBulbCountTask()
    out_a = task.generate(28851, params=params, max_attempts=20)
    out_b = task.generate(28851, params=params, max_attempts=20)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_switch_circuit_defaults_and_prompt_bundle() -> None:
    cfg = get_task_group_defaults("physics", "circuits")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="physics_circuits_switch_circuit_family",
    )
    bundle = json.loads(Path("prompts/physics/circuits/physics_circuits_v0.json").read_text(encoding="utf-8"))

    assert set(generation["query_id_weights"]) == {"lit_bulb_count"}
    assert set(generation["scene_variant_weights"]) == {"mixed_branch"}
    assert list(generation["target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert int(rendering["canvas_width"]) == 1280
    assert str(prompt["scene_key"]) == "switch_circuit_diagram"
    assert str(prompt["task_key"]) == "switch_circuit_query"
    assert "lit_bulb_count" in bundle["query_templates"]
    assert len(bundle["query_templates"]["lit_bulb_count"]) == 5
    assert "scene:switch_circuit_diagram" in bundle["required_slots_by_key"]


def test_physics_switch_circuit_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "physics_switch_circuit"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_physics_switch_circuit",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_physics__switch_circuit__lit_bulb_count",
                count=2,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=20,
        sampling_seed=89,
    )
    final_path = build_dataset(config, code_hash="physics-switch-circuit-smoke")
    train_records = read_jsonl(final_path / "train_instances.jsonl")

    assert len(train_records) == 2
    assert all(record["domain"] == "physics" for record in train_records)
    assert all(record["task_group"] == "circuits" for record in train_records)
    assert {record["task"] for record in train_records} == {"task_physics__switch_circuit__lit_bulb_count"}
    assert {record["scene_id"] for record in train_records} == {"switch_circuit"}
    assert {record["query_id"] for record in train_records} == {"lit_bulb_count"}

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
