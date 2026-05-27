"""Contract tests for the physics fluids hydraulic-piston task."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.physics.fluids.hydraulic_missing_value import PhysicsFluidsHydraulicMissingValueTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        (
            {
                "query_variant": "missing_output_force",
                "scene_variant": "wide_bench",
                "target_answer": 48,
                "mechanical_advantage": 4,
                "accent_color_name": "blue",
            },
            48,
        ),
        (
            {
                "query_variant": "missing_input_force",
                "scene_variant": "compact_frame",
                "target_answer": 8,
                "mechanical_advantage": 5,
                "accent_color_name": "green",
            },
            8,
        ),
        (
            {
                "query_variant": "missing_piston_area",
                "scene_variant": "tall_columns",
                "target_answer": 30,
                "mechanical_advantage": 5,
                "accent_color_name": "purple",
            },
            30,
        ),
    ),
)
def test_physics_fluids_hydraulic_task_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = PhysicsFluidsHydraulicMissingValueTask().generate(61001, params=params, max_attempts=40)
    trace = out.trace_payload
    execution = trace["execution_trace"]


    assert out.answer_gt.type == "integer"

    assert int(out.answer_gt.value) == int(expected_answer)

    assert out.evidence_gt.type == "bbox_set"

    assert len(out.evidence_gt.value) == 6

    assert out.query_variant == "default"

    assert out.scene_id == "hydraulic"

    assert out.query_id == params["query_variant"]

    assert trace["query_spec"]["query_variant"] == "default"

    assert trace["query_spec"]["query_id"] == params["query_variant"]
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value


    assert int(execution["output_force_value"]) * int(execution["input_area_value"]) == int(
        execution["input_force_value"]
    ) * int(execution["output_area_value"])

    assert int(execution["middle_force_value"]) * int(execution["input_area_value"]) == int(
        execution["input_force_value"]
    ) * int(execution["middle_area_value"])

    assert int(execution["mechanical_advantage"]) == int(execution["output_area_value"]) // int(
        execution["input_area_value"]
    )

    assert int(execution["middle_mechanical_advantage"]) == int(execution["middle_area_value"]) // int(
        execution["input_area_value"]
    )
    if str(params["query_variant"]) == "missing_output_force":

        assert execution["shown_output_force_value"] is None

        assert int(execution["shown_input_force_value"]) == int(execution["input_force_value"])
    elif str(params["query_variant"]) == "missing_input_force":

        assert execution["shown_input_force_value"] is None

        assert int(execution["shown_output_force_value"]) == int(execution["output_force_value"])
    else:

        assert execution["shown_output_area_value"] is None

        assert int(execution["shown_output_force_value"]) == int(execution["output_force_value"])


def test_physics_fluids_hydraulic_task_is_deterministic() -> None:
    params = {
        "query_variant": "missing_piston_area",
        "scene_variant": "wide_bench",
        "target_answer": 24,
        "mechanical_advantage": 4,
        "accent_color_name": "cyan",
    }
    task = PhysicsFluidsHydraulicMissingValueTask()
    out_a = task.generate(61021, params=params, max_attempts=40)
    out_b = task.generate(61021, params=params, max_attempts=40)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()

    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()

    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]

    assert out_a.prompt == out_b.prompt

    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_physics_fluids_hydraulic_sampling_covers_scene_query_cross_product() -> None:
    task = PhysicsFluidsHydraulicMissingValueTask()
    combos: Counter[tuple[str, str]] = Counter()
    answers_by_query: dict[str, set[int]] = {
        "missing_output_force": set(),
        "missing_input_force": set(),
        "missing_piston_area": set(),
    }
    for sampling_index in range(90):
        out = task.generate(
            61100 + sampling_index,
            params={},
            max_attempts=50,
        )
        execution = out.trace_payload["execution_trace"]
        internal_query_variant = str(out.query_id)
        combos[(str(execution["scene_variant"]), internal_query_variant)] += 1
        answers_by_query[internal_query_variant].add(int(out.answer_gt.value))


    assert len(combos) == 9

    assert all(count >= 1 for count in combos.values())

    assert len(answers_by_query["missing_output_force"]) >= 20

    assert len(answers_by_query["missing_input_force"]) == 9

    assert len(answers_by_query["missing_piston_area"]) >= 20


def test_physics_fluids_hydraulic_rejects_unknown_query_variant() -> None:
    with pytest.raises(ValueError):
        PhysicsFluidsHydraulicMissingValueTask().generate(
            61200,
            params={"query_variant": "missing_pressure"},
            max_attempts=20,
        )


def test_physics_fluids_hydraulic_prompt_bundle_supports_variants() -> None:
    bundle = json.loads(Path("prompts/physics/fluids/physics_fluids_v0.json").read_text(encoding="utf-8"))

    assert len(bundle["scene_templates"]["hydraulic_piston_diagram"]) == 5

    assert set(bundle["query_templates"]) == {
        "missing_output_force",
        "missing_input_force",
        "missing_piston_area",
    }

    assert len(bundle["query_templates"]["missing_output_force"]) == 5


def test_physics_fluids_hydraulic_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_physics__hydraulic__hydraulic_missing_value"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_physics__hydraulic__hydraulic_missing_value",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_physics__hydraulic__hydraulic_missing_value",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=40,
        sampling_seed=91,
    )
    final_path = build_dataset(config, code_hash="physics-fluids-hydraulic-smoke")

    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")

    assert len(train_records) == 4

    assert all(record["domain"] == "physics" for record in train_records)

    assert all(record["task_group"] == "fluids" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))

    assert int(build_report["accepted_counts_by_task"]["task_physics__hydraulic__hydraulic_missing_value"]) == 4
