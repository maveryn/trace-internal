"""Core TRACE regression tests for determinism and build contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from trace.core.build_presets import (
    build_equal_split_all_tasks_config,
    resolve_equal_split_task_count,
    resolve_task_active_variant_count,
    resolve_variant_aware_task_weights,
    resolve_weighted_task_counts,
)
from trace.core.builder import BuildError, build_dataset
from trace.core.canonical import CanonicalizationError, canonical_json_bytes
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.identity import compute_instance_id
from trace.core.reward_contracts import ANSWER_REWARD_CONTRACT_ID, resolve_reward_contract
from trace.core.seed import hash64
from trace.core.taxonomy import (
    ACTIVE_DOMAINS,
    inject_taxonomy_metadata,
    missing_taxonomy_task_ids,
    resolve_task_taxonomy,
)
from trace.core.trace_store import read_trace_shard
from trace.core.types import TaskComplexity, TypedValue
from trace.tasks import create_task
from trace.tasks.base import TaskOutput
from trace.tasks.registry import TASK_REGISTRY, list_default_task_ids, list_task_ids, register_task
from trace.tasks.puzzles.cell_board.path_shortest_path import TileShortestPathTask
from tests.helpers import read_jsonl


DUMMY_PROMPT_ROOT = Path("tests/fixtures/prompts")


@pytest.fixture(autouse=True)
def _restore_task_registry_after_test():
    """Keep dummy registry entries from leaking into unrelated tests."""

    original_registry = dict(TASK_REGISTRY)
    yield
    TASK_REGISTRY.clear()
    TASK_REGISTRY.update(original_registry)


def _generate_first_successful_output(task_id: str) -> TaskOutput:
    last_exc: Exception | None = None
    task = create_task(task_id)
    for seed_index in range(8):
        instance_seed = hash64(0, f"{task_id}:instance_seed", seed_index)
        try:
            return task.generate(
                int(instance_seed),
                params={},
                max_attempts=100,
            )
        except Exception as exc:  # pragma: no cover - exercised only on unlucky seeds.
            last_exc = exc
    pytest.fail(f"failed to generate a sample for {task_id}: {last_exc}")


def _register_dummy_tasks() -> None:
    if "task_dummy__weights__weighted_a" not in TASK_REGISTRY:

        @register_task
        class DummyWeightedTaskA:
            task_id = "task_dummy__weights__weighted_a"
            domain = "dummy"
            task_group = "weights"
            default_dataset_enabled = False

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
                            "query_id": "default",
                            "template_id": "dummy",
                            "prompt_variant": {
                                "prompt_bundle_id": "dummy_weights_v0",
                                "scene_key": "weighted_task",
                                "task_key": "default_task",
                                "query_key": None,
                                "scene_template_index": 0,
                                "task_template_index": 0,
                                "query_template_index": None,
                                "variant_count_by_key": {
                                    "scene:weighted_task": 5,
                                    "task:default_task": 5,
                                },
                                "slot_values": {},
                                "template_paths": [
                                    "tests/fixtures/prompts/dummy/weights/dummy_weights_v0.json"
                                ],
                            },
                        },
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 1},
                        "witness_symbolic": {"type": "point_set", "count": 1},
                        "projected_evidence": {"pixel_point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.1, complexity_components={"variant": "a"}),
                    task_versions={
                        "dsl_spec_version": "v0",
                        "template_version": "v0",
                        "operator_bundle_version": "v0",
                        "domain_capability_version": "v0",
                        "renderer_version": "v0",
                    },
                    query_id="default",
                )

    if "task_dummy__weights__weighted_b" not in TASK_REGISTRY:

        @register_task
        class DummyWeightedTaskB:
            task_id = "task_dummy__weights__weighted_b"
            domain = "dummy"
            task_group = "weights"
            default_dataset_enabled = False

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
                            "query_id": "default",
                            "template_id": "dummy",
                            "prompt_variant": {
                                "prompt_bundle_id": "dummy_weights_v0",
                                "scene_key": "weighted_task",
                                "task_key": "default_task",
                                "query_key": None,
                                "scene_template_index": 1,
                                "task_template_index": 1,
                                "query_template_index": None,
                                "variant_count_by_key": {
                                    "scene:weighted_task": 5,
                                    "task:default_task": 5,
                                },
                                "slot_values": {},
                                "template_paths": [
                                    "tests/fixtures/prompts/dummy/weights/dummy_weights_v0.json"
                                ],
                            },
                        },
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 2},
                        "witness_symbolic": {"type": "point_set", "count": 1},
                        "projected_evidence": {"pixel_point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.2, complexity_components={"variant": "b"}),
                    task_versions={
                        "dsl_spec_version": "v0",
                        "template_version": "v0",
                        "operator_bundle_version": "v0",
                        "domain_capability_version": "v0",
                        "renderer_version": "v0",
                    },
                    query_id="default",
                )

    if "task_dummy__weights__variant_support" not in TASK_REGISTRY:

        @register_task
        class DummyWeightedQueryVariantSupport:
            task_id = "task_dummy__weights__variant_support"
            domain = "dummy"
            task_group = "weights"
            default_dataset_enabled = False

            def generate(self, instance_seed: int, *, params, max_attempts: int) -> TaskOutput:
                image = Image.new("RGB", (32, 32), (245, 245, 245))
                point = [[6.0, 6.0]]
                probabilities = {"alpha": 0.25, "beta": 0.25, "gamma": 0.5}
                return TaskOutput(
                    prompt="dummy variant support",
                    answer_gt=TypedValue(type="integer", value=5),
                    evidence_gt=TypedValue(type="point_set", value=point),
                    image=image,
                    image_id="img0",
                    trace_payload={
                        "scene_ir": {"entities": []},
                        "query_spec": {
                            "query_id": "alpha",
                            "template_id": "dummy",
                            "params": {"query_id_probabilities": probabilities},
                            "prompt_variant": {
                                "prompt_bundle_id": "dummy_weights_v0",
                                "scene_key": "weighted_task",
                                "task_key": "default_task",
                                "query_key": "alpha",
                                "scene_template_index": 0,
                                "task_template_index": 0,
                                "query_template_index": 0,
                                "variant_count_by_key": {
                                    "scene:weighted_task": 5,
                                    "task:default_task": 5,
                                    "query:alpha": 5,
                                },
                                "slot_values": {},
                                "template_paths": [
                                    "tests/fixtures/prompts/dummy/weights/dummy_weights_v0.json"
                                ],
                            },
                        },
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 5, "query_id_probabilities": probabilities},
                        "witness_symbolic": {"type": "point_set", "count": 1},
                        "projected_evidence": {"pixel_point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.3, complexity_components={"variant": "support"}),
                    task_versions={
                        "dsl_spec_version": "v0",
                        "template_version": "v0",
                        "operator_bundle_version": "v0",
                        "domain_capability_version": "v0",
                        "renderer_version": "v0",
                    },
                    query_id="alpha",
                )


def test_canonical_non_finite_rejected() -> None:
    with pytest.raises(CanonicalizationError) as exc_info:
        canonical_json_bytes({"x": float("inf")})
    assert exc_info.value.code == "schema_non_finite_number"


def test_cell_board_shortest_path_deterministic() -> None:
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
    assert out_a.trace_payload["query_spec"]["prompt_variant"]["prompt_bundle_id"] == "puzzles_cell_board_path_v0"
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
        "instance_version": "v0",
        "instance_seed": 42,
        "domain": "puzzles",
        "task_group": "cell_board",
        "task": "task_puzzles__cell_board__path_distance",
        "scene_id": "cell_board",
        "query_id": "shortest_path",
        "prompt": "p",
        "prompt_variants": {"answer_only": "p0", "answer_and_evidence": "p1"},
        "images": [{"image_id": "img0", "format": "png", "image_hash": "blake3:abc", "path": "a.png"}],
        "answer_gt": {"type": "integer", "value": 5},
        "evidence_gt": {"type": "point_sequence", "value": [[120, 120], [168, 120]]},
        "reward_contract": resolve_reward_contract(
            answer_type="integer",
            evidence_type="point_sequence",
        ).to_dict(),
        "versions": {"dsl_spec_version": "v0"},
    }
    variant = dict(base)
    variant["images"] = [{"image_id": "img0", "format": "png", "image_hash": "blake3:abc", "path": "other/path.png"}]
    assert compute_instance_id(base) == compute_instance_id(variant)


def test_build_dataset_end_to_end_and_strict_repro(tmp_path: Path) -> None:
    output_root = tmp_path / "out"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="test_build",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_puzzles__cell_board__path_distance",
                count=4,
                params={
                    "rows": 7,
                    "cols": 7,
                    "query_id": "shortest_path",
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
        assert instance["domain"] == "puzzles"
        assert instance["task_group"] == "cell_board"
        assert instance["scene_id"] == "cell_board"
        assert instance["query_id"] == "shortest_path"
        assert not Path(instance["images"][0]["path"]).is_absolute()
        assert instance["answer_gt"]["type"] == "integer"
        assert instance["evidence_gt"]["type"] == "point_sequence"
        assert instance["reward_contract"]["answer"]["id"] == ANSWER_REWARD_CONTRACT_ID
        assert instance["reward_contract"]["answer"]["type"] == "integer"
        assert instance["reward_contract"]["evidence"]["id"] == "point_sequence_soft_distance_v0"
        assert instance["reward_contract"]["evidence"]["type"] == "point_sequence"
        assert sorted(instance["prompt_variants"].keys()) == ["answer_and_evidence", "answer_only"]
        assert instance["prompt"] == instance["prompt_variants"]["answer_and_evidence"]

    validation_report = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation_report["total_errors"] == 0

    trace_records = read_trace_shard(final_path / "traces" / "trace_shard_0001.jsonl.zst")
    assert len(trace_records) == len(train_instances)
    for instance, trace_record in zip(train_instances, trace_records):
        assert trace_record["reward_contract"] == instance["reward_contract"]
        assert trace_record["taxonomy"]["domain"] == instance["domain"]
        assert trace_record["taxonomy"]["scene_id"] == instance["scene_id"]
        assert trace_record["query_spec"]["scene_id"] == instance["scene_id"]

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert build_report["dataset_id"].startswith("blake3:")
    assert build_report["accepted_counts_by_task"]["task_puzzles__cell_board__path_distance"] == 4

    strict_output_root = tmp_path / "strict_out"
    strict_config = BuildConfig(
        output_root=str(strict_output_root),
        dataset_name="test_strict_repro",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_puzzles__cell_board__path_distance",
                count=3,
                params={
                    "rows": 6,
                    "cols": 6,
                    "query_id": "shortest_path",
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
        "query_id": "shortest_path",
        "target_shortest_len_min": 4,
        "target_shortest_len_max": 10,
    }
    serial_config = BuildConfig(
        output_root=str(tmp_path / "serial_out"),
        dataset_name="parallel_match",
        instance_version="v0",
        image_format="png",
        tasks=[BuildTaskConfig(task_id="task_puzzles__cell_board__path_distance", count=4, params=task_params)],
        strict_repro=False,
        max_attempts_per_instance=120,
        sampling_seed=23,
        workers=1,
    )
    parallel_config = BuildConfig(
        output_root=str(tmp_path / "parallel_out"),
        dataset_name="parallel_match",
        instance_version="v0",
        image_format="png",
        tasks=[BuildTaskConfig(task_id="task_puzzles__cell_board__path_distance", count=4, params=task_params)],
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


def test_equal_split_all_tasks_build_preset_uses_default_enabled_tasks() -> None:
    default_task_ids = list_default_task_ids()
    active_table_tasks = {
        "task_charts__table__value_predicate_count",
        "task_charts__table__column_rank_label",
        "task_charts__table__column_summary_value",
        "task_charts__table__temporal_row_interval_difference_value",
    }
    active_cell_board_tasks = {
        "task_puzzles__cell_board__attribute_count",
        "task_puzzles__cell_board__color_region_count",
        "task_puzzles__cell_board__reachability_count",
        "task_puzzles__cell_board__path_distance",
        "task_puzzles__cell_board__symmetry_violation_count",
    }
    active_page_time_artifact_tasks = {
        "task_pages__calendar__marked_day_class_count",
        "task_pages__calendar__weekday_occurrence_date",
        "task_pages__schedule__longer_than_reference_count",
        "task_pages__schedule__maximum_non_overlapping_count",
        "task_pages__schedule__overlap_count",
        "task_pages__timeline__interval_membership_count",
    }
    active_puzzle_clock_tasks = {
        "task_puzzles__clock_collection__compare",
        "task_puzzles__analog_clock__offset_readout",
    }
    active_brick_breaker_tasks = {
        "task_games__brick_breaker__hit_row_remaining_count",
        "task_games__brick_breaker__trajectory_target_label",
    }
    assert default_task_ids
    assert len(default_task_ids) == len(set(default_task_ids))
    assert all("__" in task_id for task_id in default_task_ids if task_id.startswith("task_"))
    assert all("__" in task_id for task_id in TASK_REGISTRY if task_id.startswith("task_"))
    assert {task_id for task_id in default_task_ids if task_id.startswith("task_games__brick_breaker__")} == active_brick_breaker_tasks
    assert {task_id for task_id in TASK_REGISTRY if task_id.startswith("task_games__brick_breaker__")} == active_brick_breaker_tasks
    assert {task_id for task_id in default_task_ids if task_id.startswith("task_charts__table__")} == active_table_tasks
    assert {task_id for task_id in TASK_REGISTRY if task_id.startswith("task_charts__table__")} == active_table_tasks
    assert {
        task_id for task_id in default_task_ids if task_id.startswith("task_puzzles__cell_board__")
    } == active_cell_board_tasks
    assert {task_id for task_id in TASK_REGISTRY if task_id.startswith("task_puzzles__cell_board__")} == active_cell_board_tasks
    assert active_page_time_artifact_tasks <= set(default_task_ids)
    assert active_puzzle_clock_tasks <= set(default_task_ids)
    assert not missing_taxonomy_task_ids(default_task_ids)
    assert set(ACTIVE_DOMAINS) == {
        "charts",
        "games",
        "geometry",
        "graph",
        "icons",
        "illustrations",
        "pages",
        "physics",
        "puzzles",
        "three_d",
    }
    assert resolve_task_taxonomy("task_charts__table__column_rank_label").domain == "charts"
    assert resolve_task_taxonomy("task_puzzles__cell_board__path_distance").domain == "puzzles"
    assert resolve_task_taxonomy("task_pages__control_board__filter_count").domain == "pages"
    assert resolve_task_taxonomy("task_pages__calendar__marked_day_class_count").domain == "pages"
    assert resolve_task_taxonomy("task_puzzles__clock_collection__compare").domain == "puzzles"

    taxonomy = resolve_task_taxonomy("task_puzzles__cell_board__path_distance")
    injected = inject_taxonomy_metadata(
        {
            "query_spec": {
                "source_task_id": "cell_board_shortest_path_internal",
                "source_domain": "puzzles",
                "source_task_group": "cell_board_path",
                "prompt_variant": {
                    "prompt_domain": "puzzles",
                    "prompt_task_group": "cell_board_path",
                },
            },
            "execution_trace": {"query_id": "shortest_path"},
        },
        task_id="task_puzzles__cell_board__path_distance",
        taxonomy=taxonomy,
        query_id="shortest_path",
        registered_domain="puzzles",
        registered_task_group="cell_board",
    )
    metadata = injected["taxonomy"]
    assert metadata["public"] == {
        "domain": "puzzles",
        "scene_id": "cell_board",
        "task_id": "task_puzzles__cell_board__path_distance",
        "query_id": "shortest_path",
    }
    assert metadata["registered"] == {
        "task_id": "task_puzzles__cell_board__path_distance",
        "domain": "puzzles",
        "task_group": "cell_board",
    }
    assert metadata["source"] == {
        "implementation_task_id": "cell_board_shortest_path_internal",
        "implementation_domain": "puzzles",
        "implementation_task_group": "cell_board_path",
        "config_domain": "puzzles",
        "config_task_group": "cell_board",
        "prompt_domain": "puzzles",
        "prompt_task_group": "cell_board_path",
    }

    per_task = resolve_equal_split_task_count(num_instances=len(default_task_ids) * 2, task_count=len(default_task_ids))
    assert per_task == 2

    preset = build_equal_split_all_tasks_config(
        output_root="./out",
        dataset_name="all_tasks_equal_split",
        num_instances=len(default_task_ids) * 2,
        sampling_seed=5,
        workers=0,
        max_in_flight=0,
    )
    assert len(preset.tasks) == len(default_task_ids)
    assert [task.task_id for task in preset.tasks] == default_task_ids
    assert all(int(task.count or 0) == 2 for task in preset.tasks)
    assert preset.workers == 0

    with pytest.raises(ValueError):
        resolve_equal_split_task_count(num_instances=(len(default_task_ids) * 2) + 1, task_count=len(default_task_ids))


def test_variant_aware_task_weight_helpers() -> None:
    _register_dummy_tasks()

    counts = resolve_weighted_task_counts(
        num_instances=10,
        task_weights={
            "task_dummy__weights__weighted_a": 1.0,
            "task_dummy__weights__variant_support": 2.0,
        },
    )
    assert counts == {
        "task_dummy__weights__variant_support": 7,
        "task_dummy__weights__weighted_a": 3,
    }

    assert resolve_task_active_variant_count(
        "task_dummy__weights__variant_support",
        probe_samples=1,
        max_attempts_per_instance=10,
    ) == 3

    weights, variant_counts = resolve_variant_aware_task_weights(
        task_ids=[
            "task_dummy__weights__weighted_a",
            "task_dummy__weights__variant_support",
        ],
        alpha=0.5,
        probe_samples=1,
        max_attempts_per_instance=10,
    )
    assert variant_counts == {
        "task_dummy__weights__variant_support": 3,
        "task_dummy__weights__weighted_a": 1,
    }
    assert weights == {
        "task_dummy__weights__variant_support": 2.0,
        "task_dummy__weights__weighted_a": 1.0,
    }


def test_weighted_task_sampler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _register_dummy_tasks()
    monkeypatch.setenv("TRACE_PROMPT_ROOT", str(DUMMY_PROMPT_ROOT.resolve()))
    output_root = tmp_path / "out"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="test_weighted_sampler",
        instance_version="v0",
        image_format="png",
        num_instances=30,
        tasks=[
            BuildTaskConfig(task_id="task_dummy__weights__weighted_a", weight=3.0, params={}),
            BuildTaskConfig(task_id="task_dummy__weights__weighted_b", weight=1.0, params={}),
        ],
        strict_repro=False,
        max_attempts_per_instance=20,
        sampling_seed=11,
    )

    final_path = build_dataset(config, code_hash="weighted-test")
    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))

    sampler = build_report["sampler"]
    assert sampler["mode"] == "weighted_task_sampler"
    assert pytest.approx(sampler["task_sampling_probabilities"]["task_dummy__weights__weighted_a"], rel=1e-9) == 0.75
    assert pytest.approx(sampler["task_sampling_probabilities"]["task_dummy__weights__weighted_b"], rel=1e-9) == 0.25
    assert (
        build_report["accepted_counts_by_task"]["task_dummy__weights__weighted_a"]
        + build_report["accepted_counts_by_task"]["task_dummy__weights__weighted_b"]
    ) == 30


def test_prompt_validation_error_codes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRACE_PROMPT_ROOT", str(DUMMY_PROMPT_ROOT.resolve()))
    if "task_dummy__query__prompt_missing" not in TASK_REGISTRY:

        @register_task
        class DummyPromptMissingTask:
            task_id = "task_dummy__query__prompt_missing"
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
                        "query_spec": {"query_id": "default", "template_id": "dummy_query"},
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 3},
                        "witness_symbolic": {"type": "point_set", "count": 1},
                        "projected_evidence": {"pixel_point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.1, complexity_components={}),
                    task_versions={
                        "dsl_spec_version": "v0",
                        "template_version": "v0",
                        "operator_bundle_version": "v0",
                        "domain_capability_version": "v0",
                        "renderer_version": "v0",
                    },
                    query_id="default",
                )

    if "task_dummy__weights__prompt_unresolved" not in TASK_REGISTRY:

        @register_task
        class DummyPromptUnresolvedTask:
            task_id = "task_dummy__weights__prompt_unresolved"
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
                            "query_id": "default",
                            "template_id": "dummy_query",
                            "prompt_variant": {
                                "prompt_bundle_id": "dummy_weights_v0",
                                "scene_key": "weighted_task",
                                "task_key": "default_task",
                                "query_key": None,
                                "scene_template_index": 0,
                                "task_template_index": 0,
                                "query_template_index": None,
                                "variant_count_by_key": {
                                    "scene:weighted_task": 5,
                                    "task:default_task": 5,
                                },
                                "slot_values": {},
                                "template_paths": [
                                    "tests/fixtures/prompts/dummy/weights/dummy_weights_v0.json"
                                ],
                            },
                        },
                        "render_spec": {"coord_space": "pixel"},
                        "render_map": {"image_id": "img0", "anchors": {}},
                        "execution_trace": {"answer": 4},
                        "witness_symbolic": {"type": "point_set", "count": 1},
                        "projected_evidence": {"pixel_point_set": point},
                    },
                    complexity=TaskComplexity(complexity_score=0.1, complexity_components={}),
                    task_versions={
                        "dsl_spec_version": "v0",
                        "template_version": "v0",
                        "operator_bundle_version": "v0",
                        "domain_capability_version": "v0",
                        "renderer_version": "v0",
                    },
                    query_id="default",
                )

    cases = [
        (
            "test_prompt_metadata_missing",
            "task_dummy__query__prompt_missing",
            17,
            "prompt-missing",
            "prompt_metadata_missing",
        ),
        (
            "test_prompt_unresolved_placeholder",
            "task_dummy__weights__prompt_unresolved",
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
            instance_version="v0",
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
