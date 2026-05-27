"""Contract tests for the split physics circuits resistance tasks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.physics.circuits.equivalent_resistance import (
    PhysicsCircuitsMissingResistorValueTask,
    PhysicsCircuitsTotalResistanceValueTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query_id", "expected_answer", "expected_resistor_count", "expected_evidence_count"),
    (
        (
            PhysicsCircuitsTotalResistanceValueTask,
            {"scene_variant": "parallel", "target_answer": 2},
            "total_resistance",
            2,
            4,
            4,
        ),
        (
            PhysicsCircuitsTotalResistanceValueTask,
            {"scene_variant": "simple_series_parallel", "target_answer": 5},
            "total_resistance",
            5,
            2,
            2,
        ),
        (
            PhysicsCircuitsMissingResistorValueTask,
            {"scene_variant": "parallel", "target_answer": 4},
            "missing_resistor_value",
            4,
            6,
            1,
        ),
        (
            PhysicsCircuitsMissingResistorValueTask,
            {"scene_variant": "simple_series_parallel", "target_answer": 6},
            "missing_resistor_value",
            6,
            8,
            1,
        ),
    ),
)
def test_physics_circuits_resistance_tasks_emit_expected_contract(
    task_cls: type,
    params: dict[str, int | str],
    expected_query_id: str,
    expected_answer: int,
    expected_resistor_count: int,
    expected_evidence_count: int,
) -> None:
    out = task_cls().generate(26001, params=params, max_attempts=40)
    trace = out.trace_payload
    execution = trace["execution_trace"]


    assert out.answer_gt.type == "integer"

    assert int(out.answer_gt.value) == int(expected_answer)

    assert out.evidence_gt.type == "bbox_set"

    assert out.query_id == "default"

    assert out.query_id == expected_query_id

    assert trace["query_spec"]["query_id"] == "default"

    assert trace["query_spec"]["query_id"] == expected_query_id
    assert trace["query_spec"]["params"]["query_id"] == "default"

    assert trace["query_spec"]["params"]["query_id"] == expected_query_id
    assert trace["query_spec"]["params"]["internal_query_id"] == expected_query_id

    assert execution["query_id"] == "default"

    assert execution["query_id"] == expected_query_id
    assert execution["internal_query_id"] == expected_query_id

    assert int(execution["target_answer"]) == int(expected_answer)
    if expected_query_id == "missing_resistor_value":

        assert len(out.evidence_gt.value) == int(expected_evidence_count)

        assert "common_total_resistance_label_bbox_px" in trace["render_map"]

        assert "left_known_resistance_label_bbox_px" in trace["render_map"]
    else:

        assert len(out.evidence_gt.value) >= int(expected_evidence_count)

        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

        assert trace["query_spec"]["params"]["accent_color_name"] == execution["accent_color_name"]

        assert trace["render_map"]["accent_color_name"] == execution["accent_color_name"]

        assert len(execution["resistor_specs"]) >= int(expected_resistor_count)
    if expected_query_id == "missing_resistor_value":

        assert int(execution["paired_total_resistance"]) >= 1

        assert len(execution["evidence_entity_ids"]) == 1

        assert sum(1 for spec in execution["resistor_specs"] if bool(spec["missing"])) == 1
        if str(params["scene_variant"]) == "parallel":

            assert execution["left_series_values"] == []

            assert len(execution["left_parallel_values"]) >= 3
        else:

            assert 2 <= len(execution["left_parallel_blocks"]) <= 3

            assert len(execution["left_inter_block_series_values"]) == len(execution["left_parallel_blocks"]) - 1

            assert len(execution["left_outer_series_values"]) == 2

            assert len(execution["right_outer_series_values"]) == 2

            assert execution["missing_component_group"] == "inter_block_series"
    else:

        assert len(execution["parallel_values"]) >= 2
        if str(params["scene_variant"]) == "parallel":

            assert execution["series_values"] == []
        else:

            assert 1 <= len(execution["parallel_blocks"]) <= 3

            assert len(execution["inter_block_series_values"]) == len(execution["parallel_blocks"]) - 1

            assert len(execution["outer_series_values"]) == 2

            assert execution["evidence_entity_ids"] == [spec["resistor_id"] for spec in execution["resistor_specs"]]


def test_physics_circuits_missing_resistor_value_is_deterministic() -> None:
    params = {
        "scene_variant": "parallel",
        "target_answer": 3,
        "accent_color_name": "cyan",
    }
    task = PhysicsCircuitsMissingResistorValueTask()
    out_a = task.generate(26021, params=params, max_attempts=40)
    out_b = task.generate(26021, params=params, max_attempts=40)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()

    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()

    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]

    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]

    assert out_a.prompt == out_b.prompt

    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_circuits_resistance_tasks_balance_compound_block_counts() -> None:
    total_task = PhysicsCircuitsTotalResistanceValueTask()
    total_counts = []
    for offset in range(6):
        out = total_task.generate(
            26200 + offset,
            params={
                "scene_variant": "simple_series_parallel",
                "target_answer": 10,
            },
            max_attempts=40,
        )
        total_counts.append(len(out.trace_payload["execution_trace"]["parallel_blocks"]))

    missing_task = PhysicsCircuitsMissingResistorValueTask()
    missing_counts = []
    for offset in range(6):
        out = missing_task.generate(
            26300 + offset,
            params={
                "scene_variant": "simple_series_parallel",
                "target_answer": 6,
            },
            max_attempts=40,
        )
        missing_counts.append(len(out.trace_payload["execution_trace"]["left_parallel_blocks"]))


    assert total_counts == [1, 1, 1, 1, 1, 1]

    assert missing_counts == [2, 3, 2, 3, 2, 3]


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_support"),
    (
        (
            PhysicsCircuitsTotalResistanceValueTask,
            {"scene_variant": "parallel"},
            [1, 2, 3],
        ),
            (
                PhysicsCircuitsMissingResistorValueTask,
                {"scene_variant": "parallel"},
                [3, 4, 5, 6, 8],
            ),
    ),
)
def test_physics_circuits_resistance_tasks_filter_support_to_feasible_targets(
    task_cls: type,
    params: dict[str, int | str],
    expected_support: list[int],
) -> None:
    out = task_cls().generate(26027, params=params, max_attempts=40)
    execution = out.trace_payload["execution_trace"]


    assert execution["target_answer_support"] == expected_support

    assert int(out.answer_gt.value) in set(int(value) for value in expected_support)


@pytest.mark.parametrize(
    ("task_cls", "params"),
    (
        (PhysicsCircuitsTotalResistanceValueTask, {"scene_variant": "parallel", "target_answer": 5}),
        (PhysicsCircuitsMissingResistorValueTask, {"scene_variant": "parallel", "target_answer": 1}),
    ),
)
def test_physics_circuits_resistance_tasks_reject_infeasible_target_answer(
    task_cls: type,
    params: dict[str, int | str],
) -> None:
    with pytest.raises(ValueError, match="unsupported target_answer"):
        task_cls().generate(26029, params=params, max_attempts=40)


def test_physics_circuits_resistance_tasks_reject_unknown_scene_variant() -> None:
    with pytest.raises(ValueError):
        PhysicsCircuitsTotalResistanceValueTask().generate(
            26031,
            params={"scene_variant": "bridge_network"},
            max_attempts=20,
        )


def test_physics_circuits_resistance_tasks_reject_source_query_id_param() -> None:
    with pytest.raises(ValueError, match="must match query_id"):
        PhysicsCircuitsTotalResistanceValueTask().generate(
            26033,
            params={"query_id": "missing_resistor_value"},
            max_attempts=20,
        )


def test_physics_circuits_resistance_prompt_bundle_supports_variants() -> None:
    bundle = json.loads(Path("prompts/physics/circuits/physics_circuits_v0.json").read_text(encoding="utf-8"))

    assert len(bundle["query_templates"]["total_resistance"]) == 5

    assert len(bundle["query_templates"]["missing_resistor_value"]) == 5


def test_physics_circuits_resistance_tasks_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "physics_circuits_resistance"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_physics_circuits_resistance",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_physics__resistor__total_resistance_value",
                count=2,
                params={},
            ),
            BuildTaskConfig(
                task_id="task_physics__paired_resistor__missing_resistor_value",
                count=2,
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

    assert {record["task"] for record in train_records} == {
        "task_physics__resistor__total_resistance_value",
        "task_physics__paired_resistor__missing_resistor_value",
    }

    assert {record["query_id"] for record in train_records} == {"total_resistance", "missing_resistor_value"}

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))

    assert int(build_report["accepted_counts_by_task"]["task_physics__resistor__total_resistance_value"]) == 2

    assert int(build_report["accepted_counts_by_task"]["task_physics__paired_resistor__missing_resistor_value"]) == 2

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))

    assert validation["total_errors"] == 0
