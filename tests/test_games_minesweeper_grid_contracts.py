"""Contract tests for games Minesweeper-grid tasks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.minesweeper.grid_tasks import (
    GamesMinesweeperForcedCellCountTask,
    GamesMinesweeperGridTask,
    GamesMinesweeperSatisfiedClueCountTask,
)
from trace.tasks.games.shared.minesweeper_common import (
    adjacent_flag_count,
    clue_number,
    forced_mine_supports,
    forced_safe_supports,
    satisfied_clue_coords,
    unsatisfied_clue_coords,
    validate_board_contract,
)
from trace.tasks.games.shared.style import SUPPORTED_MINESWEEPER_STYLE_VARIANTS
from tests.helpers import read_jsonl


def _coords(values: list[list[int]]) -> tuple[tuple[int, int], ...]:
    """Return trace coordinate lists as stable coordinate tuples."""

    return tuple((int(row), int(col)) for row, col in values)


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query", "expected_answer_type"),
    (
        (
            GamesMinesweeperForcedCellCountTask,
            {"query_id": "forced_mine_count", "target_answer": 3, "scene_variant": "mixed_grid", "board_size": 5},
            "forced_mine_count",
            "integer",
        ),
        (
            GamesMinesweeperForcedCellCountTask,
            {"query_id": "forced_safe_count", "target_answer": 4, "scene_variant": "open_grid", "board_size": 5},
            "forced_safe_count",
            "integer",
        ),
        (
            GamesMinesweeperSatisfiedClueCountTask,
            {"target_answer": 5, "scene_variant": "mixed_grid", "board_size": 7},
            "satisfied_clue_count",
            "integer",
        ),
    ),
)
def test_games_minesweeper_grid_emits_expected_contract(
    task_cls: type[GamesMinesweeperGridTask],
    params: dict[str, int | str],
    expected_query: str,
    expected_answer_type: str,
) -> None:
    out = task_cls().generate(51201, params=params, max_attempts=128)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == str(expected_answer_type)
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_id == "default"
    assert out.query_id == str(expected_query)
    assert trace["query_spec"]["query_id"] == str(expected_query)
    assert trace["query_spec"]["query_id"] == "default"
    assert trace["query_spec"]["params"]["query_id"] == str(expected_query)
    assert trace["query_spec"]["params"]["query_id"] == "default"
    assert execution["query_id"] == str(expected_query)
    assert execution["query_id"] == "default"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)


def test_games_minesweeper_forced_mine_count_matches_basic_rule_supports() -> None:
    out = GamesMinesweeperForcedCellCountTask().generate(
        51211,
        params={"query_id": "forced_mine_count", "target_answer": 4, "scene_variant": "mixed_grid", "board_size": 5},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    size = int(execution["board_size"])
    mine_coords = _coords(execution["mine_coords"])
    revealed_coords = _coords(execution["revealed_coords"])
    flagged_coords = _coords(execution["flagged_coords"])
    hidden_coords = _coords(execution["hidden_coords"])

    validate_board_contract(
        size=size,
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords,
        hidden_coords=hidden_coords,
    )
    supports = forced_mine_supports(
        size=size,
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords,
        hidden_coords=hidden_coords,
    )

    assert int(out.answer_gt.value) == 4
    assert set(supports) == set(_coords(execution["forced_mine_coords"]))
    assert len(supports) == int(out.answer_gt.value)
    assert set(supports) <= set(mine_coords)
    assert set(_coords(execution["evidence_coords"])) == set(supports)


def test_games_minesweeper_forced_safe_count_matches_basic_rule_supports() -> None:
    out = GamesMinesweeperForcedCellCountTask().generate(
        51221,
        params={"query_id": "forced_safe_count", "target_answer": 5, "scene_variant": "mixed_grid", "board_size": 5},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    size = int(execution["board_size"])
    mine_coords = _coords(execution["mine_coords"])
    revealed_coords = _coords(execution["revealed_coords"])
    flagged_coords = _coords(execution["flagged_coords"])
    hidden_coords = _coords(execution["hidden_coords"])
    supports = forced_safe_supports(
        size=size,
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords,
        hidden_coords=hidden_coords,
    )

    assert int(out.answer_gt.value) == 5
    assert set(supports) == set(_coords(execution["forced_safe_coords"]))
    assert len(supports) == int(out.answer_gt.value)
    assert not (set(supports) & set(mine_coords))
    assert set(_coords(execution["evidence_coords"])) == set(supports)


def test_games_minesweeper_satisfied_clue_count_matches_adjacent_flags() -> None:
    out = GamesMinesweeperSatisfiedClueCountTask().generate(
        51231,
        params={"target_answer": 5, "scene_variant": "open_grid", "board_size": 7},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    size = int(execution["board_size"])
    mine_coords = _coords(execution["mine_coords"])
    revealed_coords = _coords(execution["revealed_coords"])
    flagged_coords = _coords(execution["flagged_coords"])
    satisfied = satisfied_clue_coords(
        size=size,
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords,
    )
    unsatisfied = unsatisfied_clue_coords(
        size=size,
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords,
    )

    assert int(out.answer_gt.value) == 5
    assert set(satisfied) == set(_coords(execution["satisfied_clue_coords"]))
    assert set(unsatisfied) == set(_coords(execution["unsatisfied_clue_coords"]))
    assert len(satisfied) == int(out.answer_gt.value)
    assert len(unsatisfied) >= 4
    assert set(_coords(execution["evidence_coords"])) == set(satisfied)
    for coord in satisfied:
        clue = clue_number(coord, mine_coords=mine_coords, size=size)
        assert clue > 0
        assert adjacent_flag_count(coord, flagged_coords=flagged_coords, size=size) == clue
    assert all(
        adjacent_flag_count(coord, flagged_coords=flagged_coords, size=size)
        < clue_number(coord, mine_coords=mine_coords, size=size)
        for coord in unsatisfied
    )
    assert any(
        clue_number(coord, mine_coords=mine_coords, size=size) >= 2
        and adjacent_flag_count(coord, flagged_coords=flagged_coords, size=size) == 0
        for coord in unsatisfied
    )


def test_games_minesweeper_grid_query_cycle_covers_answer_scene_status_board_and_style_support() -> None:
    task = GamesMinesweeperGridTask()
    answers_by_query: dict[str, set[int | str]] = {
        "forced_mine_count": set(),
        "forced_safe_count": set(),
        "satisfied_clue_count": set(),
    }
    scenes_by_query: dict[str, set[str]] = {key: set() for key in answers_by_query}
    boards_by_query: dict[str, set[int]] = {key: set() for key in answers_by_query}
    styles_by_query: dict[str, set[str]] = {key: set() for key in answers_by_query}

    for sampling_index in range(240):
        out = task.generate(
            51301 + int(sampling_index),
            params={},
            max_attempts=128,
        )
        execution = out.trace_payload["execution_trace"]
        query = str(execution["query_id"])
        answers_by_query[query].add(out.answer_gt.value)
        scenes_by_query[query].add(str(execution["scene_variant"]))
        boards_by_query[query].add(int(execution["board_size"]))
        styles_by_query[query].add(str(execution["style_variant"]))

    assert answers_by_query == {
        "forced_mine_count": {1, 2, 3, 4, 5},
        "forced_safe_count": {1, 2, 3, 4, 5},
        "satisfied_clue_count": {1, 2, 3, 4, 5},
    }
    assert all(values == {"open_grid", "mixed_grid"} for values in scenes_by_query.values())
    assert all(values == {4, 5, 6, 7, 8} for values in boards_by_query.values())
    assert all(values == set(SUPPORTED_MINESWEEPER_STYLE_VARIANTS) for values in styles_by_query.values())


def test_games_minesweeper_forced_cell_task_uses_eased_board_support() -> None:
    task = GamesMinesweeperForcedCellCountTask()
    boards_by_query: dict[str, set[int]] = {"forced_mine_count": set(), "forced_safe_count": set()}

    for sampling_index in range(80):
        out = task.generate(
            51401 + int(sampling_index),
            params={},
            max_attempts=128,
        )
        execution = out.trace_payload["execution_trace"]
        boards_by_query[str(execution["query_id"])].add(int(execution["board_size"]))

    assert boards_by_query == {"forced_mine_count": {4, 5}, "forced_safe_count": {4, 5}}


def test_games_minesweeper_grid_is_deterministic() -> None:
    params = {
        "query_id": "forced_safe_count",
        "target_answer": 3,
        "scene_variant": "mixed_grid",
        "board_size": 7,
    }
    task = GamesMinesweeperGridTask()
    out_a = task.generate(51241, params=params, max_attempts=128)
    out_b = task.generate(51241, params=params, max_attempts=128)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_minesweeper_grid_prompt_bundle_requires_rule_texts() -> None:
    bundle = json.loads(Path("prompts/games/minesweeper/games_minesweeper_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:forced_mine_count"] == ["minesweeper_rule_text"]
    assert required["query:forced_safe_count"] == ["minesweeper_rule_text"]
    assert required["query:satisfied_clue_count"] == ["minesweeper_rule_text"]


def test_games_minesweeper_grid_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__minesweeper__forced_cell_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__minesweeper__forced_cell_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__minesweeper__forced_cell_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=128,
        sampling_seed=61,
    )
    final_path = build_dataset(config, code_hash="games-minesweeper-grid-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "minesweeper" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__minesweeper__forced_cell_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
