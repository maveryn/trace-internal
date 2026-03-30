"""Contract tests for the games dominoes chain-count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.dominoes.chain_count import GamesDominoesChainCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_evidence_count"),
    (
        (
            {
                "scene_variant": "single_row",
                "query_variant": "matching_end_count",
                "target_answer": 3,
                "candidate_count": 8,
            },
            3,
            3,
        ),
        (
            {
                "scene_variant": "single_row",
                "task_variant": "higher_sum_than_reference_count",
                "target_answer": 4,
                "candidate_count": 9,
            },
            4,
            4,
        ),
        (
            {
                "scene_variant": "two_row",
                "query_variant": "sum_to_target_count",
                "target_answer": 3,
                "candidate_count": 10,
                "target_total": 7,
            },
            3,
            3,
        ),
        (
            {
                "scene_variant": "two_row",
                "query_variant": "double_count",
                "target_answer": 5,
                "candidate_count": 12,
            },
            5,
            5,
        ),
    ),
)
def test_games_dominoes_chain_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_evidence_count: int,
) -> None:
    out = GamesDominoesChainCountTask().generate(26001, params=params, max_attempts=48)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == int(expected_evidence_count)
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == int(expected_evidence_count)
    assert all(str(tile_id).startswith("candidate_") for tile_id in execution["evidence_entity_ids"])


def test_games_dominoes_chain_count_matching_end_marks_reference_and_open_half() -> None:
    out = GamesDominoesChainCountTask().generate(
        26011,
        params={
            "scene_variant": "single_row",
            "query_variant": "matching_end_count",
            "target_answer": 2,
            "candidate_count": 8,
        },
        max_attempts=48,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    reference_id = str(execution["reference_tile_id"])
    reference_spec = next(spec for spec in execution["chain_tile_specs"] if str(spec["tile_id"]) == reference_id)
    assert bool(reference_spec["is_reference"]) is True
    assert int(execution["open_end_value"]) in range(7)
    assert str(reference_id) in trace["render_map"]["reference_tag_bboxes_px"]


def test_games_dominoes_chain_count_sum_to_target_records_target_total() -> None:
    out = GamesDominoesChainCountTask().generate(
        26021,
        params={
            "scene_variant": "single_row",
            "query_variant": "sum_to_target_count",
            "target_answer": 2,
            "candidate_count": 8,
            "target_total": 6,
        },
        max_attempts=48,
    )
    execution = out.trace_payload["execution_trace"]
    assert int(execution["target_total"]) == 6
    assert "6" in out.prompt


def test_games_dominoes_chain_count_is_deterministic() -> None:
    params = {
        "scene_variant": "two_row",
        "query_variant": "higher_sum_than_reference_count",
        "target_answer": 5,
        "candidate_count": 12,
    }
    task = GamesDominoesChainCountTask()
    out_a = task.generate(26031, params=params, max_attempts=48)
    out_b = task.generate(26031, params=params, max_attempts=48)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_dominoes_chain_count_prompt_bundle_requires_rule_text_for_query_specific_prompts() -> None:
    bundle = json.loads(Path("prompts/games/dominoes/games_dominoes_v1.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["task_variant:matching_end_count"] == ["connection_rule_text"]
    assert required["task_variant:higher_sum_than_reference_count"] == ["pip_sum_rule_text"]
    assert required["task_variant:sum_to_target_count"] == ["pip_sum_rule_text", "target_total_text"]
    assert required["task_variant:double_count"] == ["double_rule_text"]


def test_games_dominoes_chain_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games_dominoes_chain_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games_dominoes_chain_count",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games_dominoes_chain_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=48,
        sampling_seed=59,
    )
    final_path = build_dataset(config, code_hash="games-dominoes-chain-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "dominoes" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games_dominoes_chain_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
