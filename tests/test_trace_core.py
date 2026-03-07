"""Core TRACE regression tests for determinism and build contracts."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from PIL import Image

from trace.core.builder import BuildError, build_dataset
from trace.core.canonical import CanonicalizationError, canonical_json_bytes
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.identity import compute_instance_id
from trace.core.types import TaskComplexity, TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import TASK_REGISTRY, register_task
from trace.tasks.tile.path.shortest_path import TileShortestPathTask
from tests.helpers import read_jsonl


def _register_dummy_tasks() -> None:
    if "task_dummy_weights_weighted_a" not in TASK_REGISTRY:

        @register_task
        class DummyWeightedTaskA:
            task_id = "task_dummy_weights_weighted_a"
            domain = "dummy"
            task_group = "weights"

            @staticmethod
            def supported_query_types(_params=None):
                return ["default"]

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
                            "query_type": "default",
                            "template_id": "dummy",
                            "prompt_variant": {
                                "prompt_bundle_id": "dummy_weights_v1",
                                "task_type_key": "weighted_task",
                                "query_type_key": "default",
                                "task_type_variant_index": 0,
                                "query_type_variant_index": 0,
                                "variant_count_by_key": {
                                    "task_type:weighted_task": 10,
                                    "query_type:default": 10,
                                },
                                "slot_values": {},
                                "template_paths": ["dummy/weights/dummy_weights_v1.json"],
                            },
                        },
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 1},
                        "witness_symbolic": {"type": "id_set", "ids": []},
                        "projected_evidence": {"point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.1, complexity_components={"variant": "a"}),
                    task_versions={
                        "dsl_spec_version": "v1",
                        "template_version": "v1",
                        "operator_bundle_version": "v1",
                        "domain_capability_version": "v1",
                        "renderer_version": "v1",
                    },
                    query_type="default",
                )

    if "task_dummy_weights_weighted_b" not in TASK_REGISTRY:

        @register_task
        class DummyWeightedTaskB:
            task_id = "task_dummy_weights_weighted_b"
            domain = "dummy"
            task_group = "weights"

            @staticmethod
            def supported_query_types(_params=None):
                return ["default"]

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
                            "query_type": "default",
                            "template_id": "dummy",
                            "prompt_variant": {
                                "prompt_bundle_id": "dummy_weights_v1",
                                "task_type_key": "weighted_task",
                                "query_type_key": "default",
                                "task_type_variant_index": 1,
                                "query_type_variant_index": 1,
                                "variant_count_by_key": {
                                    "task_type:weighted_task": 10,
                                    "query_type:default": 10,
                                },
                                "slot_values": {},
                                "template_paths": ["dummy/weights/dummy_weights_v1.json"],
                            },
                        },
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 2},
                        "witness_symbolic": {"type": "id_set", "ids": []},
                        "projected_evidence": {"point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.2, complexity_components={"variant": "b"}),
                    task_versions={
                        "dsl_spec_version": "v1",
                        "template_version": "v1",
                        "operator_bundle_version": "v1",
                        "domain_capability_version": "v1",
                        "renderer_version": "v1",
                    },
                    query_type="default",
                )

    if "task_dummy_query_query_task" not in TASK_REGISTRY:

        @register_task
        class DummyQueryTask:
            task_id = "task_dummy_query_query_task"
            domain = "dummy"
            task_group = "query"

            @staticmethod
            def supported_query_types(_params=None):
                return ["q1", "q2"]

            def generate(self, instance_seed: int, *, params, max_attempts: int) -> TaskOutput:
                query_type = str(params.get("query_type", "q1"))
                if query_type not in {"q1", "q2"}:
                    raise ValueError(query_type)
                value = 1 if query_type == "q1" else 2
                x_coord = 6.0 if query_type == "q1" else 26.0
                image = Image.new("RGB", (32, 32), (255, 255, 255))
                point = [[x_coord, 16.0]]
                return TaskOutput(
                    prompt=f"dummy query {query_type}",
                    answer_gt=TypedValue(type="integer", value=value),
                    evidence_gt=TypedValue(type="point_set", value=point),
                    image=image,
                    image_id="img0",
                    trace_payload={
                        "scene_ir": {"entities": []},
                        "query_spec": {
                            "query_type": query_type,
                            "template_id": "dummy_query",
                            "prompt_variant": {
                                "prompt_bundle_id": "dummy_query_v1",
                                "task_type_key": "query_task",
                                "query_type_key": query_type,
                                "task_type_variant_index": 0,
                                "query_type_variant_index": 0,
                                "variant_count_by_key": {
                                    "task_type:query_task": 10,
                                    f"query_type:{query_type}": 10,
                                },
                                "slot_values": {},
                                "template_paths": ["dummy/query/dummy_query_v1.json"],
                            },
                        },
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"query_type": query_type, "answer": value},
                        "witness_symbolic": {"type": "id_set", "ids": []},
                        "projected_evidence": {"point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.3, complexity_components={"query_type": query_type}),
                    task_versions={
                        "dsl_spec_version": "v1",
                        "template_version": "v1",
                        "operator_bundle_version": "v1",
                        "domain_capability_version": "v1",
                        "renderer_version": "v1",
                    },
                    query_type=query_type,
                )


def test_canonical_non_finite_rejected() -> None:
    try:
        canonical_json_bytes({"x": float("inf")})
        assert False, "expected canonicalization failure"
    except CanonicalizationError as exc:
        assert exc.code == "schema_non_finite_number"


def test_tile_shortest_path_deterministic() -> None:
    task = TileShortestPathTask()
    params = {"rows": 7, "cols": 7, "min_shortest_len": 5, "evidence_type": "point_path"}

    out_a = task.generate(123456, params=params, max_attempts=120)
    out_b = task.generate(123456, params=params, max_attempts=120)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["witness_symbolic"] == out_b.trace_payload["witness_symbolic"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "tile_path_v1"
    assert sorted(out_a.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert out_a.prompt == out_a.prompt_variants["answer_and_evidence"]
    assert out_a.image.tobytes() == out_b.image.tobytes()


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
        "evidence_gt": {"type": "point_path", "value": [[1.0, 2.0]]},
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
                params={"rows": 7, "cols": 7, "min_shortest_len": 5, "evidence_type": "point_path"},
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
        assert instance["evidence_gt"]["type"] == "point_path"
        assert sorted(instance["prompt_variants"].keys()) == ["answer_and_evidence", "answer_only"]
        assert instance["prompt"] == instance["prompt_variants"]["answer_and_evidence"]

    validation_report = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation_report["total_errors"] == 0

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
                params={"rows": 6, "cols": 6, "min_shortest_len": 4, "evidence_type": "point_path"},
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


def test_weighted_task_sampler_and_query_counts(tmp_path: Path) -> None:
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
    assert build_report["accepted_counts_by_task"]["task_dummy_weights_weighted_a"] + build_report["accepted_counts_by_task"]["task_dummy_weights_weighted_b"] == 30


def test_query_sampling_validation_failures(tmp_path: Path) -> None:
    _register_dummy_tasks()
    output_root = tmp_path / "query_count_validation"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="test_query_count_validation",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_dummy_query_query_task",
                count=8,
                params={},
                query_weights={"q1": 1.0, "q2": 1.0},
                expected_query_counts={"q1": 8, "q2": 8},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=20,
        sampling_seed=5,
    )

    with pytest.raises(BuildError):
        build_dataset(config, code_hash="query-fail")

    failure_dirs = sorted((output_root / "failed_builds").glob("*"))
    assert failure_dirs, "expected a persisted failure bundle"
    report_path = failure_dirs[0] / "validation_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["total_errors"] > 0
    assert any("query-type accepted count below expectation" in err.get("message", "") for err in report["errors"])
    assert "count_per_task_shortfall" in report["error_counts_by_code"]

    edge_cases = [
        ("test_query_weights_zero_sum", {"q1": 0.0, "q2": 0.0}, 3),
        ("test_query_weights_unknown_only", {"unknown_query": 1.0}, 9),
    ]
    for dataset_name, query_weights, sampling_seed in edge_cases:
        edge_output_root = tmp_path / dataset_name
        edge_config = BuildConfig(
            output_root=str(edge_output_root),
            dataset_name=dataset_name,
            instance_version="v1",
            image_format="png",
            tasks=[
                BuildTaskConfig(
                    task_id="task_dummy_query_query_task",
                    count=4,
                    params={},
                    query_weights=query_weights,
                )
            ],
            strict_repro=False,
            max_attempts_per_instance=20,
            sampling_seed=sampling_seed,
        )

        with pytest.raises(BuildError, match="query_weights must have at least one positive weight"):
            build_dataset(edge_config, code_hash="query-weights-edge")


def test_query_weights_fallback_to_task_group_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _register_dummy_tasks()
    domain_root = tmp_path / "domains"
    (domain_root / "dummy").mkdir(parents=True, exist_ok=True)
    (domain_root / "dummy" / "query.yaml").write_text(
        "\n".join(
            [
                "sampling:",
                "  shared:",
                "    query_weights:",
                "      q1: 0.0",
                "      q2: 1.0",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TRACE_DOMAIN_CONFIG_ROOT", str(domain_root))

    output_root = tmp_path / "out"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="test_query_weight_fallback",
        instance_version="v1",
        image_format="png",
        tasks=[BuildTaskConfig(task_id="task_dummy_query_query_task", count=6, params={})],
        strict_repro=False,
        max_attempts_per_instance=20,
        sampling_seed=123,
    )

    final_path = build_dataset(config, code_hash="query-weight-defaults")
    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    sampler_probs = build_report["sampler"]["query_sampling_probabilities_by_task"]["task_dummy_query_query_task"]
    accepted = build_report["query_type_accepted_counts_by_task"]["task_dummy_query_query_task"]
    assert sampler_probs == {"q2": 1.0}
    assert accepted == {"q2": 6}


def test_prompt_validation_error_codes(tmp_path: Path) -> None:
    if "task_dummy_query_prompt_missing" not in TASK_REGISTRY:

        @register_task
        class DummyPromptMissingTask:
            task_id = "task_dummy_query_prompt_missing"
            domain = "dummy"
            task_group = "query"

            @staticmethod
            def supported_query_types(_params=None):
                return ["default"]

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
                        "query_spec": {"query_type": "default", "template_id": "dummy_query"},
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 3},
                        "witness_symbolic": {"type": "id_set", "ids": []},
                        "projected_evidence": {"point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.1, complexity_components={}),
                    task_versions={
                        "dsl_spec_version": "v1",
                        "template_version": "v1",
                        "operator_bundle_version": "v1",
                        "domain_capability_version": "v1",
                        "renderer_version": "v1",
                    },
                    query_type="default",
                )

    if "task_dummy_weights_prompt_unresolved" not in TASK_REGISTRY:

        @register_task
        class DummyPromptUnresolvedTask:
            task_id = "task_dummy_weights_prompt_unresolved"
            domain = "dummy"
            task_group = "weights"

            @staticmethod
            def supported_query_types(_params=None):
                return ["default"]

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
                            "query_type": "default",
                            "template_id": "dummy_query",
                            "prompt_variant": {
                                "prompt_bundle_id": "dummy_weights_v1",
                                "task_type_key": "weighted_task",
                                "query_type_key": "default",
                                "task_type_variant_index": 0,
                                "query_type_variant_index": 0,
                                "variant_count_by_key": {
                                    "task_type:weighted_task": 10,
                                    "query_type:default": 10,
                                },
                                "slot_values": {},
                                "template_paths": ["dummy/weights/dummy_weights_v1.json"],
                            },
                        },
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 4},
                        "witness_symbolic": {"type": "id_set", "ids": []},
                        "projected_evidence": {"point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.1, complexity_components={}),
                    task_versions={
                        "dsl_spec_version": "v1",
                        "template_version": "v1",
                        "operator_bundle_version": "v1",
                        "domain_capability_version": "v1",
                        "renderer_version": "v1",
                    },
                    query_type="default",
                )

    cases = [
        ("test_prompt_metadata_missing", "task_dummy_query_prompt_missing", 17, "prompt-missing", "prompt_metadata_missing"),
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
