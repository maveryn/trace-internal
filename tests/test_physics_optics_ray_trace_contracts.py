"""Contract tests for the physics optics ray-trace task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.physics.optics.ray_trace import PhysicsOpticsRayTraceTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        ({"scene_variant": "quad_mirror", "query_variant": "bounce_count", "target_answer": 4}, 4),
        ({"scene_variant": "quad_mirror", "query_variant": "bounce_count", "target_answer": 3}, 3),
        ({"scene_variant": "single_mirror", "query_variant": "target_hit_count", "target_answer": 2}, 2),
    ),
)
def test_physics_optics_ray_trace_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = PhysicsOpticsRayTraceTask().generate(27001, params=params, max_attempts=60)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "graph_point_set"
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["grid_point_set"] == out.evidence_gt.value
    if str(params["query_variant"]) == "bounce_count":
        assert len(execution["bounce_cells"]) == int(expected_answer)
        assert len(out.evidence_gt.value) == int(expected_answer)
        assert execution["target_specs"] == []
    else:
        hit_targets = [spec for spec in execution["target_specs"] if bool(spec["hit"])]
        assert len(hit_targets) == int(expected_answer)
        assert len(out.evidence_gt.value) == int(expected_answer)
        assert all("graph_point" in spec for spec in execution["target_specs"])
    assert trace["render_map"]["accent_color_name"] == execution["accent_color_name"]
    assert "ray_polyline_px" in trace["render_map"]
    assert "source_direction_px" in trace["render_map"]


def test_physics_optics_ray_trace_is_deterministic() -> None:
    params = {
        "scene_variant": "double_mirror",
        "query_variant": "target_hit_count",
        "target_answer": 2,
        "accent_color_name": "purple",
    }
    task = PhysicsOpticsRayTraceTask()
    out_a = task.generate(27021, params=params, max_attempts=60)
    out_b = task.generate(27021, params=params, max_attempts=60)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_optics_ray_trace_rejects_unknown_scene_variant() -> None:
    with pytest.raises(ValueError):
        PhysicsOpticsRayTraceTask().generate(
            27031,
            params={"scene_variant": "hex_mirror"},
            max_attempts=20,
        )


def test_physics_optics_ray_trace_prompt_bundle_supports_variants() -> None:
    bundle = json.loads(Path("prompts/physics/optics/physics_optics_v1.json").read_text(encoding="utf-8"))
    assert len(bundle["task_variant_templates"]["bounce_count"]) == 5
    assert len(bundle["task_variant_templates"]["target_hit_count"]) == 5


def test_physics_optics_ray_trace_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_physics_optics_ray_trace"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_physics_optics_ray_trace",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_physics_optics_ray_trace",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=60,
        sampling_seed=71,
    )
    final_path = build_dataset(config, code_hash="physics-optics-ray-trace-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "physics" for record in train_records)
    assert all(record["task_group"] == "optics" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_physics_optics_ray_trace"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
