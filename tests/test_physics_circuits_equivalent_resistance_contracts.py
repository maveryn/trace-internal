"""Contract tests for the physics circuits equivalent-resistance task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.physics.circuits.equivalent_resistance import PhysicsCircuitsEquivalentResistanceTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_resistor_count", "expected_evidence_count"),
    (
        ({"scene_variant": "parallel", "query_variant": "total_resistance", "target_answer": 2}, 2, 3, 3),
        (
            {"scene_variant": "simple_series_parallel", "query_variant": "total_resistance", "target_answer": 5},
            5,
            4,
            4,
        ),
        ({"scene_variant": "parallel", "query_variant": "missing_resistor_value", "target_answer": 4}, 4, 4, 1),
        (
            {"scene_variant": "simple_series_parallel", "query_variant": "missing_resistor_value", "target_answer": 6},
            6,
            6,
            1,
        ),
    ),
)
def test_physics_circuits_equivalent_resistance_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_resistor_count: int,
    expected_evidence_count: int,
) -> None:
    out = PhysicsCircuitsEquivalentResistanceTask().generate(26001, params=params, max_attempts=40)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    if str(params.get("query_variant", "total_resistance")) == "missing_resistor_value":
        assert len(out.evidence_gt.value) == int(expected_evidence_count)
    else:
        assert len(out.evidence_gt.value) >= int(expected_evidence_count)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert trace["query_spec"]["params"]["accent_color_name"] == execution["accent_color_name"]
    assert trace["render_map"]["accent_color_name"] == execution["accent_color_name"]
    assert len(execution["resistor_specs"]) >= int(expected_resistor_count)
    if str(params.get("query_variant", "total_resistance")) == "missing_resistor_value":
        assert int(execution["paired_total_resistance"]) >= 1
        assert len(execution["evidence_entity_ids"]) == 1
        assert sum(1 for spec in execution["resistor_specs"] if bool(spec["missing"])) == 1
        if str(params["scene_variant"]) == "parallel":
            assert execution["left_series_values"] == []
            assert len(execution["left_parallel_values"]) >= 2
        else:
            assert len(execution["left_series_values"]) == 1
            assert len(execution["left_parallel_values"]) == 2
    else:
        assert len(execution["parallel_values"]) >= 2
        if str(params["scene_variant"]) == "parallel":
            assert execution["series_values"] == []
        else:
            assert len(execution["series_values"]) >= 1
        assert execution["evidence_entity_ids"] == [spec["resistor_id"] for spec in execution["resistor_specs"]]


def test_physics_circuits_equivalent_resistance_is_deterministic() -> None:
    params = {
        "scene_variant": "parallel",
        "query_variant": "missing_resistor_value",
        "target_answer": 3,
        "accent_color_name": "cyan",
    }
    task = PhysicsCircuitsEquivalentResistanceTask()
    out_a = task.generate(26021, params=params, max_attempts=40)
    out_b = task.generate(26021, params=params, max_attempts=40)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_circuits_equivalent_resistance_rejects_unknown_scene_variant() -> None:
    with pytest.raises(ValueError):
        PhysicsCircuitsEquivalentResistanceTask().generate(
            26031,
            params={"scene_variant": "bridge_network"},
            max_attempts=20,
        )


def test_physics_circuits_equivalent_resistance_prompt_bundle_supports_variants() -> None:
    bundle = json.loads(Path("prompts/physics/circuits/physics_circuits_v1.json").read_text(encoding="utf-8"))
    assert len(bundle["task_variant_templates"]["total_resistance"]) == 5
    assert len(bundle["task_variant_templates"]["missing_resistor_value"]) == 5


def test_physics_circuits_equivalent_resistance_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_physics_circuits_equivalent_resistance"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_physics_circuits_equivalent_resistance",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_physics_circuits_equivalent_resistance",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=40,
        sampling_seed=61,
    )
    final_path = build_dataset(config, code_hash="physics-circuits-equivalent-resistance-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "physics" for record in train_records)
    assert all(record["task_group"] == "circuits" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_physics_circuits_equivalent_resistance"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
