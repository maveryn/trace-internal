"""Contract tests for the physics mechanics spring-extension task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.physics.mechanics.spring_extension import PhysicsMechanicsSpringExtensionTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_evidence_count"),
    (
        ({"scene_variant": "paired_springs", "query_variant": "missing_weight_for_extension", "target_answer": 4}, 4, 4),
        ({"scene_variant": "staggered_springs", "query_variant": "missing_extension_for_weight", "target_answer": 6}, 6, 4),
        ({"scene_variant": "textured_spring", "query_variant": "extension_difference", "target_answer": 3}, 3, 2),
    ),
)
def test_physics_mechanics_spring_extension_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_evidence_count: int,
) -> None:
    out = PhysicsMechanicsSpringExtensionTask().generate(28001, params=params, max_attempts=40)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == int(expected_evidence_count)
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert int(execution["scale_factor"]) in {1, 2, 3}
    if str(out.task_variant) == "missing_weight_for_extension":
        assert execution["right_measurement"]["shown_weight_value"] is None
        assert execution["right_measurement"]["shown_extension_value"] == execution["right_measurement"]["true_extension_value"]
    elif str(out.task_variant) == "missing_extension_for_weight":
        assert execution["right_measurement"]["shown_weight_value"] == execution["right_measurement"]["true_weight_value"]
        assert execution["right_measurement"]["shown_extension_value"] is None
    else:
        left_extension = int(execution["left_measurement"]["shown_extension_value"])
        right_extension = int(execution["right_measurement"]["shown_extension_value"])
        assert abs(left_extension - right_extension) == int(expected_answer)


def test_physics_mechanics_spring_extension_is_deterministic() -> None:
    params = {
        "scene_variant": "staggered_springs",
        "query_variant": "missing_weight_for_extension",
        "target_answer": 5,
        "accent_color_name": "purple",
    }
    task = PhysicsMechanicsSpringExtensionTask()
    out_a = task.generate(28021, params=params, max_attempts=40)
    out_b = task.generate(28021, params=params, max_attempts=40)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_mechanics_spring_extension_accepts_explicit_accent_color() -> None:
    out = PhysicsMechanicsSpringExtensionTask().generate(
        28031,
        params={
            "scene_variant": "paired_springs",
            "query_variant": "extension_difference",
            "target_answer": 4,
            "accent_color_name": "orange",
        },
        max_attempts=40,
    )
    assert str(out.trace_payload["execution_trace"]["accent_color_name"]) == "orange"
    assert str(out.trace_payload["render_map"]["accent_color_name"]) == "orange"


def test_physics_mechanics_spring_extension_rejects_unknown_scene_variant() -> None:
    with pytest.raises(ValueError):
        PhysicsMechanicsSpringExtensionTask().generate(
            28041,
            params={"scene_variant": "coiled_trio", "query_variant": "missing_weight_for_extension"},
            max_attempts=20,
        )


def test_physics_mechanics_spring_extension_prompt_bundle_supports_variants() -> None:
    bundle = json.loads(Path("prompts/physics/mechanics/physics_mechanics_v1.json").read_text(encoding="utf-8"))
    assert len(bundle["task_variant_templates"]["missing_weight_for_extension"]) == 5
    assert len(bundle["task_variant_templates"]["missing_extension_for_weight"]) == 5
    assert len(bundle["task_variant_templates"]["extension_difference"]) == 5


def test_physics_mechanics_spring_extension_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_physics_mechanics_spring_extension"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_physics_mechanics_spring_extension",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_physics_mechanics_spring_extension",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=40,
        sampling_seed=81,
    )
    final_path = build_dataset(config, code_hash="physics-mechanics-spring-extension-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "physics" for record in train_records)
    assert all(record["task_group"] == "mechanics" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_physics_mechanics_spring_extension"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
