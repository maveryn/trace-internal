"""Contract tests for games Rhythm-lanes tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.rhythm.lane_tasks import (
    GamesRhythmHitWindowCountTask,
    GamesRhythmLaneChoiceLabelTask,
    GamesRhythmLanesTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query"),
    (
        (
            GamesRhythmHitWindowCountTask,
            {
                "query_id": "lane_color_hit_count",
                "lane_count": 6,
                "row_count": 12,
                "beat_window": 6,
                "target_hit_count": 3,
                "target_color_key": "cyan",
            },
            "lane_color_hit_count",
        ),
        (
            GamesRhythmLaneChoiceLabelTask,
            {
                "query_id": "earliest_hit_lane_label",
                "lane_count": 7,
                "row_count": 13,
                "beat_window": 5,
                "target_hit_count": 4,
            },
            "earliest_hit_lane_label",
        ),
    ),
)
def test_games_rhythm_public_tasks_emit_expected_contract(
    task_cls: type[GamesRhythmLanesTask],
    params: dict[str, int | str],
    expected_query: str,
) -> None:
    out = task_cls().generate(98400, params=params, max_attempts=512)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_id == "default"
    assert out.query_id == expected_query
    assert out.scene_id == "rhythm"
    assert trace["query_spec"]["query_id"] == expected_query
    assert trace["query_spec"]["query_id"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == expected_query
    assert trace["query_spec"]["params"]["query_id"] == "default"
    assert execution["query_id"] == expected_query
    assert execution["query_id"] == "default"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(out.evidence_gt.value) >= 1


def test_games_rhythm_lane_color_hit_count_matches_trace() -> None:
    out = GamesRhythmHitWindowCountTask().generate(
        98410,
        params={
            "query_id": "lane_color_hit_count",
            "lane_count": 6,
            "row_count": 12,
            "beat_window": 6,
            "target_hit_count": 4,
            "target_color_key": "magenta",
        },
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    selected_lane = int(execution["selected_lane_index"])
    beat_window = int(execution["beat_window"])
    target_color = str(execution["target_color_key"])
    expected = [
        note
        for note in execution["notes"]
        if int(note["lane_index"]) == selected_lane
        and str(note["color_key"]) == target_color
        and int(note["bottom_row_from_hit_line"]) <= beat_window
    ]

    assert int(out.answer_gt.value) == len(expected) == 4
    assert set(execution["evidence_entity_ids"]) == {str(note["note_id"]) for note in expected}
    assert len(out.evidence_gt.value) == len(expected)


def test_games_rhythm_most_hits_lane_label_matches_trace() -> None:
    out = GamesRhythmLaneChoiceLabelTask().generate(
        98420,
        params={
            "query_id": "most_hits_lane_label",
            "lane_count": 8,
            "row_count": 14,
            "beat_window": 7,
            "target_hit_count": 5,
        },
        max_attempts=512,
    )
    execution = out.trace_payload["execution_trace"]
    hit_counts: list[int] = []
    for lane in range(int(execution["lane_count"])):
        hit_counts.append(
            sum(
                1
                for note in execution["notes"]
                if int(note["lane_index"]) == lane
                and int(note["bottom_row_from_hit_line"]) <= int(execution["beat_window"])
            )
        )
    expected_lane = hit_counts.index(max(hit_counts))
    expected_ids = {
        str(note["note_id"])
        for note in execution["notes"]
        if int(note["lane_index"]) == expected_lane
        and int(note["bottom_row_from_hit_line"]) <= int(execution["beat_window"])
    }

    assert hit_counts.count(max(hit_counts)) == 1
    assert int(out.answer_gt.value) == expected_lane + 1
    assert set(execution["evidence_entity_ids"]) == expected_ids


def test_games_rhythm_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__rhythm"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__rhythm",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__rhythm__hit_window_count", count=1, params={}),
            BuildTaskConfig(task_id="task_games__rhythm__lane_choice_value", count=1, params={}),
        ],
        max_attempts_per_instance=512,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-rhythm-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 2
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "rhythm" for row in rows)
