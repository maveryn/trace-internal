"""Contract tests for the games Go group-liberty count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.go.group_liberty_count import GamesGoGroupLibertyCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer"),
    (
        (
            {
                "query_variant": "marked_black_group_liberty_count",
                "target_answer": 2,
            },
            2,
        ),
        (
            {
                "task_variant": "marked_white_group_liberty_count",
                "target_answer": 5,
            },
            5,
        ),
        (
            {
                "query_variant": "marked_black_group_liberty_count",
                "target_answer": 8,
            },
            8,
        ),
    ),
)
def test_games_go_group_liberty_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
) -> None:
    out = GamesGoGroupLibertyCountTask().generate(34101, params=params, max_attempts=64)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.evidence_gt.type == "bbox_set"
    assert trace["query_spec"]["params"]["task_variant"] == out.task_variant
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value) == int(expected_answer)
    assert len(execution["liberty_coords"]) == int(expected_answer)
    assert len(execution["marked_group_coords"]) >= 1
    expected_color = "black" if str(out.task_variant) == "marked_black_group_liberty_count" else "white"
    assert str(execution["marked_group_color"]) == expected_color


def test_games_go_group_liberty_count_is_deterministic() -> None:
    params = {
        "query_variant": "marked_white_group_liberty_count",
        "target_answer": 6,
    }
    task = GamesGoGroupLibertyCountTask()
    out_a = task.generate(34111, params=params, max_attempts=64)
    out_b = task.generate(34111, params=params, max_attempts=64)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_go_group_liberty_count_prompt_bundle_requires_rule_texts() -> None:
    bundle = json.loads(Path("prompts/games/go/games_go_v1.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["task_variant:marked_black_group_liberty_count"] == [
        "marked_group_rule_text",
        "group_rule_text",
        "liberty_rule_text",
    ]
    assert required["task_variant:marked_white_group_liberty_count"] == [
        "marked_group_rule_text",
        "group_rule_text",
        "liberty_rule_text",
    ]


def test_games_go_group_liberty_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games_go_group_liberty_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games_go_group_liberty_count",
        instance_version="v1",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games_go_group_liberty_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=64,
        sampling_seed=91,
    )
    final_path = build_dataset(config, code_hash="games-go-group-liberty-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "go" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games_go_group_liberty_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
