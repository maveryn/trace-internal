"""Contract tests for the physics mechanics lever-balance task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.physics.mechanics.lever_balance import PhysicsMechanicsLeverBalanceTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        ({"scene_variant": "center_fulcrum", "query_variant": "left_torque", "target_answer": 8}, 8),
        ({"scene_variant": "offset_fulcrum", "query_variant": "right_torque", "target_answer": 12}, 12),
        ({"scene_variant": "textured_beam", "query_variant": "missing_weight_to_balance", "target_answer": 5}, 5),
    ),
)
def test_physics_mechanics_lever_balance_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = PhysicsMechanicsLeverBalanceTask().generate(25001, params=params, max_attempts=40)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert str(trace["query_spec"]["params"]["accent_color_name"]) == str(trace["execution_trace"]["accent_color_name"])
    assert str(trace["render_map"]["accent_color_name"]) == str(trace["execution_trace"]["accent_color_name"])
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    if str(out.task_variant) == "missing_weight_to_balance":
        assert out.evidence_gt.value == [trace["render_map"]["missing_weight_marker_bbox_px"]]
        assert execution["evidence_entity_ids"] == ["missing_weight_marker"]
        assert execution["placeholder_side"] in {"left", "right"}
    else:
        assert len(out.evidence_gt.value) == len(execution["relevant_weight_ids"])
        assert len(out.evidence_gt.value) >= 1
        queried_side = "left" if str(out.task_variant) == "left_torque" else "right"
        for spec in execution["weight_specs"]:
            if bool(spec["relevant_to_query"]):
                assert str(spec["side"]) == queried_side


def test_physics_mechanics_lever_balance_is_deterministic() -> None:
    params = {
        "scene_variant": "offset_fulcrum",
        "query_variant": "missing_weight_to_balance",
        "target_answer": 7,
    }
    task = PhysicsMechanicsLeverBalanceTask()
    out_a = task.generate(25021, params=params, max_attempts=40)
    out_b = task.generate(25021, params=params, max_attempts=40)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_mechanics_lever_balance_accepts_explicit_accent_color() -> None:
    out = PhysicsMechanicsLeverBalanceTask().generate(
        25029,
        params={
            "scene_variant": "center_fulcrum",
            "query_variant": "left_torque",
            "target_answer": 8,
            "accent_color_name": "purple",
        },
        max_attempts=40,
    )
    assert str(out.trace_payload["execution_trace"]["accent_color_name"]) == "purple"
    assert str(out.trace_payload["render_map"]["accent_color_name"]) == "purple"


def test_physics_mechanics_lever_balance_rejects_unknown_scene_variant() -> None:
    with pytest.raises(ValueError):
        PhysicsMechanicsLeverBalanceTask().generate(
            25031,
            params={"scene_variant": "swinging_beam", "query_variant": "left_torque"},
            max_attempts=20,
        )


def test_physics_mechanics_lever_balance_prompt_bundle_supports_variants() -> None:
    bundle = json.loads(Path("prompts/physics/mechanics/physics_mechanics_v1.json").read_text(encoding="utf-8"))
    assert len(bundle["task_variant_templates"]["left_torque"]) == 5
    assert len(bundle["task_variant_templates"]["right_torque"]) == 5
    assert len(bundle["task_variant_templates"]["missing_weight_to_balance"]) == 5


def test_physics_mechanics_lever_balance_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_physics_mechanics_lever_balance"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_physics_mechanics_lever_balance",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_physics_mechanics_lever_balance",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=40,
        sampling_seed=52,
    )
    final_path = build_dataset(config, code_hash="physics-mechanics-lever-balance-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "physics" for record in train_records)
    assert all(record["task_group"] == "mechanics" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_physics_mechanics_lever_balance"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
