"""Contract tests for the physics mechanics force-diagram task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.physics.mechanics.force_diagram import PhysicsMechanicsForceDiagramTask
from tests.helpers import read_jsonl


def _bboxes_overlap(a: list[float], b: list[float]) -> bool:
    """Return whether two axis-aligned bboxes overlap with positive area."""

    return (
        float(a[0]) < float(b[2])
        and float(a[2]) > float(b[0])
        and float(a[1]) < float(b[3])
        and float(a[3]) > float(b[1])
    )


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        ({"scene_variant": "free_body_box", "query_variant": "net_horizontal_force", "target_force": 5}, 5),
        ({"scene_variant": "surface_block", "query_variant": "net_vertical_force", "target_force": 0}, 0),
        ({"scene_variant": "surface_block", "query_variant": "balancing_force_horizontal", "target_force": 4}, 4),
        ({"scene_variant": "textured_block", "task_variant": "balancing_force_vertical", "target_force": 6}, 6),
    ),
)
def test_physics_mechanics_force_diagram_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = PhysicsMechanicsForceDiagramTask().generate(24001, params=params, max_attempts=30)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert int(execution["target_force"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(out.evidence_gt.value) == len(execution["evidence_arrow_ids"])
    assert len(out.evidence_gt.value) >= 2
    if str(out.task_variant).startswith("balancing_force_"):
        assert "marked" in out.prompt.lower()
        assert execution["balancing_direction"] is not None
    for arrow_spec in execution["arrow_specs"]:
        if bool(arrow_spec["relevant_to_query"]):
            assert str(arrow_spec["axis"]) == str(execution["query_axis"])


def test_physics_mechanics_force_diagram_is_deterministic() -> None:
    params = {
        "scene_variant": "free_body_box",
        "query_variant": "balancing_force_horizontal",
        "target_force": 7,
    }
    task = PhysicsMechanicsForceDiagramTask()
    out_a = task.generate(24021, params=params, max_attempts=30)
    out_b = task.generate(24021, params=params, max_attempts=30)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_mechanics_force_diagram_rejects_unknown_scene_variant() -> None:
    with pytest.raises(ValueError):
        PhysicsMechanicsForceDiagramTask().generate(
            24031,
            params={"scene_variant": "hanging_mass", "query_variant": "net_horizontal_force"},
            max_attempts=20,
        )


def test_physics_mechanics_force_diagram_uses_non_overlapping_balancing_marker_lane() -> None:
    task = PhysicsMechanicsForceDiagramTask()
    cases = (
        {"scene_variant": "surface_block", "query_variant": "balancing_force_horizontal", "target_force": 5},
        {"scene_variant": "textured_block", "query_variant": "balancing_force_vertical", "target_force": 6},
    )
    for seed_offset, params in enumerate(cases):
        for sample_index in range(6):
            out = task.generate(24041 + (100 * seed_offset) + sample_index, params=params, max_attempts=30)
            render_map = out.trace_payload["render_map"]
            marker_bbox = render_map["balancing_force_marker_bbox_px"]
            for arrow_bbox in render_map["arrow_bboxes_px"].values():
                assert not _bboxes_overlap(list(marker_bbox), list(arrow_bbox))


def test_physics_mechanics_force_diagram_block_aspect_ratio_stays_within_two_to_one() -> None:
    out = PhysicsMechanicsForceDiagramTask().generate(
        24051,
        params={"scene_variant": "textured_block", "query_variant": "net_vertical_force", "target_force": 3},
        max_attempts=30,
    )
    execution = out.trace_payload["execution_trace"]
    width = int(execution["object_width_px"])
    height = int(execution["object_height_px"])
    aspect_ratio = float(width) / float(height)
    assert 0.5 <= float(aspect_ratio) <= 2.0
    assert min(width, height) >= 104


def test_physics_mechanics_force_diagram_prompt_bundle_uses_balancing_slots() -> None:
    bundle = json.loads(Path("prompts/physics/mechanics/physics_mechanics_v1.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["task_variant:balancing_force_horizontal"] == ["marked_direction_label"]
    assert required["task_variant:balancing_force_vertical"] == ["marked_direction_label"]


def test_physics_mechanics_force_diagram_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_physics_mechanics_force_diagram"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_physics_mechanics_force_diagram",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_physics_mechanics_force_diagram",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=30,
        sampling_seed=41,
    )
    final_path = build_dataset(config, code_hash="physics-mechanics-force-diagram-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "physics" for record in train_records)
    assert all(record["task_group"] == "mechanics" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_physics_mechanics_force_diagram"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
