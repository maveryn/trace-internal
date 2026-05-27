"""Contract tests for games Bowling lane tasks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.bowling.lane_tasks import (
    GamesBowlingFirstPinHitLabelTask,
    GamesBowlingLaneTask,
    GamesBowlingSparePathLabelTask,
    _first_intersected_pin_id,
)
from trace.tasks.games.shared.bowling_common import BowlingPin
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query"),
    (
        (
            GamesBowlingFirstPinHitLabelTask,
            {"target_pin_index": 7, "style_variant": "cosmic"},
            "first_pin_hit_label",
        ),
        (
            GamesBowlingSparePathLabelTask,
            {"path_option_count": 6, "target_path_index": 4, "style_variant": "paper"},
            "spare_path_label",
        ),
    ),
)
def test_games_bowling_public_tasks_emit_expected_contract(
    task_cls: type[GamesBowlingLaneTask],
    params: dict[str, int | str],
    expected_query: str,
) -> None:
    out = task_cls().generate(95000, params=params, max_attempts=256)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "string"
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 1
    assert out.query_variant == "default"
    assert out.query_id == expected_query
    assert out.scene_id == "bowling"
    assert trace["query_spec"]["query_id"] == expected_query
    assert trace["query_spec"]["query_variant"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == expected_query
    assert trace["query_spec"]["params"]["query_variant"] == "default"
    assert execution["query_id"] == expected_query
    assert execution["query_variant"] == "default"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == 1


def test_games_bowling_first_pin_hit_label_matches_target_pin() -> None:
    out = GamesBowlingFirstPinHitLabelTask().generate(
        95010,
        params={"target_pin_index": 8},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    target_id = str(execution["target_pin_id"])
    target_pin = next(pin for pin in execution["pins"] if str(pin["pin_id"]) == target_id)
    full_path = out.trace_payload["render_map"]["motion_paths_px"]["shown_path"]
    pins = tuple(
        BowlingPin(
            pin_id=str(pin["pin_id"]),
            label=str(pin["label"]),
            rack_index=int(pin["rack_index"]),
            row=int(pin["row"]),
            col=int(pin["col"]),
            color_index=0,
            standing=bool(pin["standing"]),
            x_norm=float(pin["x_norm"]),
            y_norm=float(pin["y_norm"]),
        )
        for pin in execution["pins"]
    )
    first_hit = _first_intersected_pin_id(
        pins=pins,
        ball_x_norm=float(execution["ball_x_norm"]),
        aim_x_norm=float(target_pin["x_norm"]),
        aim_y_norm=float(target_pin["y_norm"]),
    )

    assert str(out.answer_gt.value) == str(target_pin["label"]) == str(execution["target_pin_label"])
    assert str(first_hit) == target_id
    assert list(execution["evidence_entity_ids"]) == [target_id]
    assert bool(target_pin["standing"]) is True
    assert 4 <= int(execution["visible_pin_count"]) <= 9
    assert len(execution["pins"]) == int(execution["visible_pin_count"])
    assert full_path["visible_end"] != full_path["end"]


def test_games_bowling_spare_path_label_matches_target_path() -> None:
    out = GamesBowlingSparePathLabelTask().generate(
        95020,
        params={"path_option_count": 6, "target_path_index": 5},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    target_id = str(execution["target_path_id"])
    target_path = next(path for path in execution["path_options"] if str(path["path_id"]) == target_id)
    standing_pin_ids = {str(pin["pin_id"]) for pin in execution["pins"] if bool(pin["standing"])}

    assert str(out.answer_gt.value) == str(target_path["label"]) == str(execution["target_path_label"])
    assert list(execution["evidence_entity_ids"]) == [target_id]
    assert set(execution["remaining_pin_ids"]) == standing_pin_ids
    assert len(standing_pin_ids) >= 1
    assert all(bool(pin["standing"]) for pin in execution["pins"])
    assert len(execution["pins"]) == len(standing_pin_ids)
    assert target_id in out.trace_payload["render_map"]["motion_paths_px"]


def test_games_bowling_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__bowling"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__bowling",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(task_id="task_games__bowling__first_pin_hit_label", count=1, params={}),
            BuildTaskConfig(task_id="task_games__bowling__spare_path_label", count=1, params={}),
        ],
        max_attempts_per_instance=256,
        workers=1,
    )
    final_path = build_dataset(config, code_hash="games-bowling-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 2
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "bowling" for row in rows)
