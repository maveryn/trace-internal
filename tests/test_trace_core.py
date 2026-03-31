"""Core TRACE regression tests for determinism and build contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from trace.core.build_presets import build_equal_split_all_tasks_config, resolve_equal_split_task_count
from trace.core.builder import BuildError, build_dataset
from trace.core.canonical import CanonicalizationError, canonical_json_bytes
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.identity import compute_instance_id
from trace.core.reward_contracts import ANSWER_REWARD_CONTRACT_ID, resolve_reward_contract
from trace.core.seed import hash64
from trace.core.trace_store import read_trace_shard
from trace.core.types import TaskComplexity, TypedValue
from trace.tasks import create_task
from trace.tasks.base import TaskOutput
from trace.tasks.registry import TASK_REGISTRY, list_task_ids, register_task
from trace.tasks.tile.path_shortest_path import TileShortestPathTask
from tests.helpers import read_jsonl


def _generate_first_successful_output(task_id: str) -> TaskOutput:
    last_exc: Exception | None = None
    task = create_task(task_id)
    for seed_index in range(8):
        instance_seed = hash64(0, f"{task_id}:instance_seed", seed_index)
        try:
            return task.generate(
                int(instance_seed),
                params={"_sampling_index": int(seed_index)},
                max_attempts=100,
            )
        except Exception as exc:  # pragma: no cover - exercised only on unlucky seeds.
            last_exc = exc
    pytest.fail(f"failed to generate a sample for {task_id}: {last_exc}")


def _register_dummy_tasks() -> None:
    if "task_dummy_weights_weighted_a" not in TASK_REGISTRY:

        @register_task
        class DummyWeightedTaskA:
            task_id = "task_dummy_weights_weighted_a"
            domain = "dummy"
            task_group = "weights"

            def generate(self, instance_seed: int, *, params, max_attempts: int) -> TaskOutput:
                image = Image.new("RGB", (32, 32), (250, 250, 250))
                point = [[8.0, 8.0]]
                return TaskOutput(
                    prompt="dummy weighted a",
                    answer_gt=TypedValue(type="integer", value=1),
                    evidence_gt=TypedValue(type="point_set", value=point),
                    image=image,
                    image_id="img0",
                    trace_payload={
                        "scene_ir": {"entities": []},
                        "query_spec": {
                            "task_variant": "default",
                            "template_id": "dummy",
                            "prompt_variant": {
                                "prompt_bundle_id": "dummy_weights_v1",
                                "task_family_key": "weighted_task",
                                "task_key": "default_task",
                                "task_variant_key": None,
                                "task_family_variant_index": 0,
                                "task_variant_index": 0,
                                "task_variant_template_index": None,
                                "variant_count_by_key": {
                                    "task_family:weighted_task": 5,
                                    "task:default_task": 5,
                                },
                                "slot_values": {},
                                "template_paths": ["dummy/weights/dummy_weights_v1.json"],
                            },
                        },
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 1},
                        "witness_symbolic": {"type": "id_set", "ids": []},
                        "projected_evidence": {"pixel_point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.1, complexity_components={"variant": "a"}),
                    task_versions={
                        "dsl_spec_version": "v1",
                        "template_version": "v1",
                        "operator_bundle_version": "v1",
                        "domain_capability_version": "v1",
                        "renderer_version": "v1",
                    },
                    task_variant="default",
                )

    if "task_dummy_weights_weighted_b" not in TASK_REGISTRY:

        @register_task
        class DummyWeightedTaskB:
            task_id = "task_dummy_weights_weighted_b"
            domain = "dummy"
            task_group = "weights"

            def generate(self, instance_seed: int, *, params, max_attempts: int) -> TaskOutput:
                image = Image.new("RGB", (32, 32), (240, 240, 240))
                point = [[10.0, 10.0]]
                return TaskOutput(
                    prompt="dummy weighted b",
                    answer_gt=TypedValue(type="integer", value=2),
                    evidence_gt=TypedValue(type="point_set", value=point),
                    image=image,
                    image_id="img0",
                    trace_payload={
                        "scene_ir": {"entities": []},
                        "query_spec": {
                            "task_variant": "default",
                            "template_id": "dummy",
                            "prompt_variant": {
                                "prompt_bundle_id": "dummy_weights_v1",
                                "task_family_key": "weighted_task",
                                "task_key": "default_task",
                                "task_variant_key": None,
                                "task_family_variant_index": 1,
                                "task_variant_index": 1,
                                "task_variant_template_index": None,
                                "variant_count_by_key": {
                                    "task_family:weighted_task": 5,
                                    "task:default_task": 5,
                                },
                                "slot_values": {},
                                "template_paths": ["dummy/weights/dummy_weights_v1.json"],
                            },
                        },
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 2},
                        "witness_symbolic": {"type": "id_set", "ids": []},
                        "projected_evidence": {"pixel_point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.2, complexity_components={"variant": "b"}),
                    task_versions={
                        "dsl_spec_version": "v1",
                        "template_version": "v1",
                        "operator_bundle_version": "v1",
                        "domain_capability_version": "v1",
                        "renderer_version": "v1",
                    },
                    task_variant="default",
                )


def test_canonical_non_finite_rejected() -> None:
    with pytest.raises(CanonicalizationError) as exc_info:
        canonical_json_bytes({"x": float("inf")})
    assert exc_info.value.code == "schema_non_finite_number"


def test_tile_shortest_path_deterministic() -> None:
    task = TileShortestPathTask()
    params = {
        "rows": 7,
        "cols": 7,
        "target_shortest_len_min": 4,
        "target_shortest_len_max": 10,
    }

    out_a = task.generate(123456, params=params, max_attempts=120)
    out_b = task.generate(123456, params=params, max_attempts=120)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["witness_symbolic"] == out_b.trace_payload["witness_symbolic"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "tile_path_v1"
    assert out_a.trace_payload["execution_trace"]["target_shortest_len"] == out_b.trace_payload["execution_trace"]["target_shortest_len"]
    assert sorted(out_a.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert out_a.prompt == out_a.prompt_variants["answer_and_evidence"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_all_registered_tasks_emit_required_trace_fields() -> None:
    required_keys = {
        "scene_ir",
        "query_spec",
        "render_spec",
        "render_map",
        "execution_trace",
        "witness_symbolic",
        "projected_evidence",
    }
    for task_id in list_task_ids():
        output = _generate_first_successful_output(task_id)
        trace_payload = dict(output.trace_payload)
        assert required_keys <= set(trace_payload)
        canonical_json_bytes(trace_payload)


def test_instance_id_ignores_image_path() -> None:
    base = {
        "instance_version": "v1",
        "instance_seed": 42,
        "domain": "tile",
        "task_group": "path",
        "task": "task_tile_path_shortest_path",
        "prompt": "p",
        "prompt_variants": {"answer_only": "p0", "answer_and_evidence": "p1"},
        "images": [{"image_id": "img0", "format": "png", "image_hash": "blake3:abc", "path": "a.png"}],
        "answer_gt": {"type": "integer", "value": 5},
        "evidence_gt": {"type": "grid_point_path", "value": [[1, 2], [1, 3]]},
        "reward_contract": resolve_reward_contract(
            answer_type="integer",
            evidence_type="grid_point_path",
        ).to_dict(),
        "versions": {"dsl_spec_version": "v1"},
    }
    variant = dict(base)
    variant["images"] = [{"image_id": "img0", "format": "png", "image_hash": "blake3:abc", "path": "other/path.png"}]
    assert compute_instance_id(base) == compute_instance_id(variant)


def test_build_dataset_end_to_end_and_strict_repro(tmp_path: Path) -> None:
    output_root = tmp_path / "out"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="test_build",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_tile_path_shortest_path",
                count=4,
                params={
                    "rows": 7,
                    "cols": 7,
                    "target_shortest_len_min": 4,
                    "target_shortest_len_max": 10,
                },
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=120,
        sampling_seed=7,
    )

    final_path = build_dataset(config, code_hash="test")
    assert final_path.exists()

    train_instances = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_instances) == 4
    for instance in train_instances:
        assert instance["trace_ref"]["shard_id"] == "trace_shard_0001.jsonl.zst"
        assert not Path(instance["images"][0]["path"]).is_absolute()
        assert instance["answer_gt"]["type"] == "integer"
        assert instance["evidence_gt"]["type"] == "grid_point_path"
        assert instance["reward_contract"]["answer"]["id"] == ANSWER_REWARD_CONTRACT_ID
        assert instance["reward_contract"]["answer"]["type"] == "integer"
        assert instance["reward_contract"]["evidence"]["id"] == "sequence_exact_v1"
        assert instance["reward_contract"]["evidence"]["type"] == "grid_point_path"
        assert sorted(instance["prompt_variants"].keys()) == ["answer_and_evidence", "answer_only"]
        assert instance["prompt"] == instance["prompt_variants"]["answer_and_evidence"]

    validation_report = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation_report["total_errors"] == 0

    trace_records = read_trace_shard(final_path / "traces" / "trace_shard_0001.jsonl.zst")
    assert len(trace_records) == len(train_instances)
    for instance, trace_record in zip(train_instances, trace_records):
        assert trace_record["reward_contract"] == instance["reward_contract"]

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert build_report["dataset_id"].startswith("blake3:")
    assert build_report["accepted_counts_by_task"]["task_tile_path_shortest_path"] == 4

    strict_output_root = tmp_path / "strict_out"
    strict_config = BuildConfig(
        output_root=str(strict_output_root),
        dataset_name="test_strict_repro",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_tile_path_shortest_path",
                count=3,
                params={
                    "rows": 6,
                    "cols": 6,
                    "target_shortest_len_min": 4,
                    "target_shortest_len_max": 8,
                },
            )
        ],
        strict_repro=True,
        max_attempts_per_instance=120,
        sampling_seed=19,
    )

    strict_final_path = build_dataset(strict_config, code_hash="strict-test")
    assert strict_final_path.exists()
    tmp_dirs = [path.name for path in (strict_output_root / "tmp").glob("*")] if (strict_output_root / "tmp").exists() else []
    assert all(not name.endswith("__strict_repro") for name in tmp_dirs)


def test_parallel_build_matches_serial(tmp_path: Path) -> None:
    task_params = {
        "rows": 7,
        "cols": 7,
        "target_shortest_len_min": 4,
        "target_shortest_len_max": 10,
    }
    serial_config = BuildConfig(
        output_root=str(tmp_path / "serial_out"),
        dataset_name="parallel_match",
        instance_version="v1",
        image_format="png",
        tasks=[BuildTaskConfig(task_id="task_tile_path_shortest_path", count=4, params=task_params)],
        strict_repro=False,
        max_attempts_per_instance=120,
        sampling_seed=23,
        workers=1,
    )
    parallel_config = BuildConfig(
        output_root=str(tmp_path / "parallel_out"),
        dataset_name="parallel_match",
        instance_version="v1",
        image_format="png",
        tasks=[BuildTaskConfig(task_id="task_tile_path_shortest_path", count=4, params=task_params)],
        strict_repro=False,
        max_attempts_per_instance=120,
        sampling_seed=23,
        workers=2,
        max_in_flight=4,
    )

    serial_path = build_dataset(serial_config, code_hash="parallel-match")
    parallel_path = build_dataset(parallel_config, code_hash="parallel-match")

    serial_instances = read_jsonl(serial_path / "train_instances.jsonl")
    parallel_instances = read_jsonl(parallel_path / "train_instances.jsonl")
    assert parallel_instances == serial_instances

    serial_traces = read_trace_shard(serial_path / "traces" / "trace_shard_0001.jsonl.zst")
    parallel_traces = read_trace_shard(parallel_path / "traces" / "trace_shard_0001.jsonl.zst")
    assert parallel_traces == serial_traces

    for instance in serial_instances:
        image_rel_path = Path(instance["images"][0]["path"])
        assert (serial_path / image_rel_path).read_bytes() == (parallel_path / image_rel_path).read_bytes()


def test_equal_split_all_tasks_build_preset_uses_registered_tasks() -> None:
    per_task = resolve_equal_split_task_count(num_instances=len(TASK_REGISTRY) * 2, task_count=len(TASK_REGISTRY))
    assert per_task == 2

    preset = build_equal_split_all_tasks_config(
        output_root="./out",
        dataset_name="all_tasks_equal_split",
        num_instances=len(TASK_REGISTRY) * 2,
        sampling_seed=5,
        workers=0,
        max_in_flight=0,
    )
    assert len(preset.tasks) == len(TASK_REGISTRY)
    assert [task.task_id for task in preset.tasks] == sorted(TASK_REGISTRY)
    assert all(int(task.count or 0) == 2 for task in preset.tasks)
    assert preset.workers == 0

    with pytest.raises(ValueError):
        resolve_equal_split_task_count(num_instances=(len(TASK_REGISTRY) * 2) + 1, task_count=len(TASK_REGISTRY))


def test_weighted_task_sampler(tmp_path: Path) -> None:
    _register_dummy_tasks()
    output_root = tmp_path / "out"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="test_weighted_sampler",
        instance_version="v1",
        image_format="png",
        num_instances=30,
        tasks=[
            BuildTaskConfig(task_id="task_dummy_weights_weighted_a", weight=3.0, params={}),
            BuildTaskConfig(task_id="task_dummy_weights_weighted_b", weight=1.0, params={}),
        ],
        strict_repro=False,
        max_attempts_per_instance=20,
        sampling_seed=11,
    )

    final_path = build_dataset(config, code_hash="weighted-test")
    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))

    sampler = build_report["sampler"]
    assert sampler["mode"] == "weighted_task_sampler"
    assert pytest.approx(sampler["task_sampling_probabilities"]["task_dummy_weights_weighted_a"], rel=1e-9) == 0.75
    assert pytest.approx(sampler["task_sampling_probabilities"]["task_dummy_weights_weighted_b"], rel=1e-9) == 0.25
    assert (
        build_report["accepted_counts_by_task"]["task_dummy_weights_weighted_a"]
        + build_report["accepted_counts_by_task"]["task_dummy_weights_weighted_b"]
    ) == 30


def test_prompt_validation_error_codes(tmp_path: Path) -> None:
    if "task_dummy_query_prompt_missing" not in TASK_REGISTRY:

        @register_task
        class DummyPromptMissingTask:
            task_id = "task_dummy_query_prompt_missing"
            domain = "dummy"
            task_group = "query"

            def generate(self, instance_seed: int, *, params, max_attempts: int) -> TaskOutput:
                image = Image.new("RGB", (32, 32), (230, 230, 230))
                point = [[12.0, 12.0]]
                return TaskOutput(
                    prompt="dummy prompt without metadata",
                    answer_gt=TypedValue(type="integer", value=3),
                    evidence_gt=TypedValue(type="point_set", value=point),
                    image=image,
                    image_id="img0",
                    trace_payload={
                        "scene_ir": {"entities": []},
                        "query_spec": {"task_variant": "default", "template_id": "dummy_query"},
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 3},
                        "witness_symbolic": {"type": "id_set", "ids": []},
                        "projected_evidence": {"pixel_point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.1, complexity_components={}),
                    task_versions={
                        "dsl_spec_version": "v1",
                        "template_version": "v1",
                        "operator_bundle_version": "v1",
                        "domain_capability_version": "v1",
                        "renderer_version": "v1",
                    },
                    task_variant="default",
                )

    if "task_dummy_weights_prompt_unresolved" not in TASK_REGISTRY:

        @register_task
        class DummyPromptUnresolvedTask:
            task_id = "task_dummy_weights_prompt_unresolved"
            domain = "dummy"
            task_group = "weights"

            def generate(self, instance_seed: int, *, params, max_attempts: int) -> TaskOutput:
                image = Image.new("RGB", (32, 32), (225, 225, 225))
                point = [[5.0, 5.0]]
                return TaskOutput(
                    prompt="dummy unresolved prompt {missing_token}",
                    answer_gt=TypedValue(type="integer", value=4),
                    evidence_gt=TypedValue(type="point_set", value=point),
                    image=image,
                    image_id="img0",
                    trace_payload={
                        "scene_ir": {"entities": []},
                        "query_spec": {
                            "task_variant": "default",
                            "template_id": "dummy_query",
                            "prompt_variant": {
                                "prompt_bundle_id": "dummy_weights_v1",
                                "task_family_key": "weighted_task",
                                "task_key": "default_task",
                                "task_variant_key": None,
                                "task_family_variant_index": 0,
                                "task_variant_index": 0,
                                "task_variant_template_index": None,
                                "variant_count_by_key": {
                                    "task_family:weighted_task": 5,
                                    "task:default_task": 5,
                                },
                                "slot_values": {},
                                "template_paths": ["dummy/weights/dummy_weights_v1.json"],
                            },
                        },
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 4},
                        "witness_symbolic": {"type": "id_set", "ids": []},
                        "projected_evidence": {"pixel_point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.1, complexity_components={}),
                    task_versions={
                        "dsl_spec_version": "v1",
                        "template_version": "v1",
                        "operator_bundle_version": "v1",
                        "domain_capability_version": "v1",
                        "renderer_version": "v1",
                    },
                    task_variant="default",
                )

    cases = [
        (
            "test_prompt_metadata_missing",
            "task_dummy_query_prompt_missing",
            17,
            "prompt-missing",
            "prompt_metadata_missing",
        ),
        (
            "test_prompt_unresolved_placeholder",
            "task_dummy_weights_prompt_unresolved",
            21,
            "prompt-unresolved",
            "prompt_unresolved_placeholder",
        ),
    ]
    for dataset_name, task_id, sampling_seed, code_hash, expected_error_code in cases:
        output_root = tmp_path / dataset_name
        config = BuildConfig(
            output_root=str(output_root),
            dataset_name=dataset_name,
            instance_version="v1",
            image_format="png",
            tasks=[BuildTaskConfig(task_id=str(task_id), count=1, params={})],
            strict_repro=False,
            max_attempts_per_instance=20,
            sampling_seed=int(sampling_seed),
        )

        with pytest.raises(BuildError):
            build_dataset(config, code_hash=str(code_hash))

        failure_dirs = sorted((output_root / "failed_builds").glob("*"))
        assert failure_dirs, "expected a persisted failure bundle"
        report_path = failure_dirs[0] / "validation_report.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["total_errors"] > 0
        assert str(expected_error_code) in report["error_counts_by_code"]
