"""Contract tests for games Minesweeper-grid tasks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.minesweeper.forced_cell_count import GamesMinesweeperForcedCellCountTask
from trace.tasks.games.minesweeper.remaining_mine_count_value import GamesMinesweeperRemainingMineCountValueTask
from trace.tasks.games.minesweeper.reveal_outcome_label import GamesMinesweeperRevealOutcomeLabelTask
from trace.tasks.games.minesweeper.satisfied_clue_count import GamesMinesweeperSatisfiedClueCountTask
from trace.tasks.games.minesweeper.shared.rules import (
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


def _bbox_row_counts(bboxes: dict[str, list[float]], *, tolerance_px: float = 4.0) -> tuple[int, ...]:
    centers = sorted((float(bbox[1]) + float(bbox[3])) / 2.0 for bbox in bboxes.values())
    rows: list[list[float]] = []
    for center_y in centers:
        if rows and abs(float(rows[-1][0]) - center_y) <= float(tolerance_px):
            rows[-1].append(center_y)
        else:
            rows.append([center_y])
    return tuple(len(row) for row in rows)


@pytest.mark.parametrize(
    ("task_cls", "params", "expected_query", "expected_answer_type", "expected_annotation_type"),
    (
        (
            GamesMinesweeperForcedCellCountTask,
            {"query_id": "forced_mine_count", "target_answer": 3, "scene_variant": "mixed_grid", "board_size": 5},
            "forced_mine_count",
            "integer",
            "bbox_set",
        ),
        (
            GamesMinesweeperForcedCellCountTask,
            {"query_id": "forced_safe_count", "target_answer": 4, "scene_variant": "open_grid", "board_size": 5},
            "forced_safe_count",
            "integer",
            "bbox_set",
        ),
        (
            GamesMinesweeperSatisfiedClueCountTask,
            {"target_answer": 5, "scene_variant": "mixed_grid", "board_size": 7},
            "single",
            "integer",
            "bbox_set",
        ),
        (
            GamesMinesweeperRemainingMineCountValueTask,
            {"target_answer": 3, "scene_variant": "mixed_grid", "board_size": 6},
            "single",
            "integer",
            "bbox",
        ),
        (
            GamesMinesweeperRevealOutcomeLabelTask,
            {"target_answer": 4, "scene_variant": "mixed_grid", "board_size": 6},
            "single",
            "option_letter",
            "keyed_bbox_set_map",
        ),
    ),
)
def test_games_minesweeper_grid_emits_expected_contract(
    task_cls: type,
    params: dict[str, int | str],
    expected_query: str,
    expected_answer_type: str,
    expected_annotation_type: str,
) -> None:
    out = task_cls().generate(51201, params=params, max_attempts=128)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == str(expected_answer_type)
    assert out.annotation_gt.type == str(expected_annotation_type)
    assert out.query_id == str(expected_query)
    assert trace["query_spec"]["query_id"] == str(expected_query)
    assert trace["query_spec"]["params"]["query_id"] == str(expected_query)
    assert execution["query_id"] == str(expected_query)
    if str(expected_annotation_type) == "keyed_bbox_set_map":
        assert trace["projected_annotation"]["keyed_bbox_set_map"] == out.annotation_gt.value
        assert trace["projected_annotation"]["pixel_keyed_bbox_set_map"] == out.annotation_gt.value
        assert set(out.annotation_gt.value) == {"target_cell", "supporting_clues", "supporting_flags"}
    elif str(expected_annotation_type) == "bbox":
        assert trace["projected_annotation"]["bbox"] == out.annotation_gt.value
        assert len(execution["annotation_entity_ids"]) == 1
    else:
        assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
        assert len(execution["annotation_entity_ids"]) == len(out.annotation_gt.value)
    assert "panel_scene_style" in trace["render_spec"]
    assert trace["render_spec"]["text_style"]["font_family"]


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
    assert set(_coords(execution["annotation_coords"])) == set(supports)


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
    assert set(_coords(execution["annotation_coords"])) == set(supports)


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

    assert out.query_id == "single"
    assert int(out.answer_gt.value) == 5
    assert set(satisfied) == set(_coords(execution["satisfied_clue_coords"]))
    assert set(unsatisfied) == set(_coords(execution["unsatisfied_clue_coords"]))
    assert len(satisfied) == int(out.answer_gt.value)
    assert len(unsatisfied) >= 4
    assert set(_coords(execution["annotation_coords"])) == set(satisfied)
    for coord in satisfied:
        clue = clue_number(coord, mine_coords=mine_coords, size=size)
        assert clue > 0
        assert adjacent_flag_count(coord, flagged_coords=flagged_coords, size=size) == clue


@pytest.mark.parametrize("target_answer", (0, 1, 2, 3, 4, 5))
def test_games_minesweeper_remaining_mine_count_matches_marked_clue(target_answer: int) -> None:
    out = GamesMinesweeperRemainingMineCountValueTask().generate(
        51251 + int(target_answer),
        params={"target_answer": int(target_answer), "scene_variant": "mixed_grid", "board_size": 6},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    size = int(execution["board_size"])
    mine_coords = _coords(execution["mine_coords"])
    revealed_coords = _coords(execution["revealed_coords"])
    flagged_coords = _coords(execution["flagged_coords"])
    hidden_coords = _coords(execution["hidden_coords"])
    forcing_clues = _coords(execution["forcing_clue_coords"])
    annotation_coords = _coords(execution["annotation_coords"])

    validate_board_contract(
        size=size,
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords,
        hidden_coords=hidden_coords,
    )
    assert out.query_id == "single"
    assert out.annotation_gt.type == "bbox"
    assert int(out.answer_gt.value) == int(target_answer)
    assert len(forcing_clues) == 1
    assert annotation_coords == forcing_clues
    marked = forcing_clues[0]
    assert marked in set(revealed_coords)
    clue = clue_number(marked, mine_coords=mine_coords, size=size)
    flags = adjacent_flag_count(marked, flagged_coords=flagged_coords, size=size)
    assert clue > 0
    assert clue - flags == int(target_answer)
    if int(target_answer) == 0:
        assert flags == clue


@pytest.mark.parametrize("target_answer", tuple(range(9)))
def test_games_minesweeper_reveal_outcome_matches_marked_hidden_cell(target_answer: int) -> None:
    out = GamesMinesweeperRevealOutcomeLabelTask().generate(
        51271 + int(target_answer),
        params={"target_answer": int(target_answer), "scene_variant": "mixed_grid", "board_size": 6},
        max_attempts=256,
    )
    execution = out.trace_payload["execution_trace"]
    size = int(execution["board_size"])
    mine_coords = _coords(execution["mine_coords"])
    revealed_coords = _coords(execution["revealed_coords"])
    flagged_coords = _coords(execution["flagged_coords"])
    hidden_coords = _coords(execution["hidden_coords"])
    target = tuple(int(value) for value in execution["target_cell_coord"])
    reveal_outcome_by_code = {
        0: "mine",
        1: "empty",
        2: "1",
        3: "2",
        4: "3",
        5: "4",
        6: "5",
        7: "6",
        8: "7",
    }
    expected_outcome = reveal_outcome_by_code[int(target_answer)]
    option_by_label = {str(item["label"]): str(item["outcome"]) for item in execution["answer_options"]}

    validate_board_contract(
        size=size,
        mine_coords=mine_coords,
        revealed_coords=revealed_coords,
        flagged_coords=flagged_coords,
        hidden_coords=hidden_coords,
    )
    assert out.query_id == "single"
    assert out.answer_gt.type == "option_letter"
    assert str(out.answer_gt.value) in set("ABCDEF")
    assert option_by_label[str(out.answer_gt.value)] == expected_outcome
    assert str(execution["reveal_outcome"]) == expected_outcome
    assert target in set(hidden_coords)
    assert target not in set(flagged_coords)
    assert out.annotation_gt.type == "keyed_bbox_set_map"
    assert len(out.annotation_gt.value["target_cell"]) == 1
    assert len(out.annotation_gt.value["supporting_clues"]) >= 1
    assert set(out.annotation_gt.value) == {"target_cell", "supporting_clues", "supporting_flags"}

    if expected_outcome == "mine":
        supports = forced_mine_supports(
            size=size,
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords,
            hidden_coords=hidden_coords,
        )
        assert target in set(mine_coords)
        assert target in supports
    else:
        supports = forced_safe_supports(
            size=size,
            mine_coords=mine_coords,
            revealed_coords=revealed_coords,
            flagged_coords=flagged_coords,
            hidden_coords=hidden_coords,
        )
        actual_count = clue_number(target, mine_coords=mine_coords, size=size)
        expected_count = 0 if expected_outcome == "empty" else int(expected_outcome)
        assert target not in set(mine_coords)
        assert target in supports
        assert actual_count == expected_count


def test_games_minesweeper_reveal_outcome_lays_out_four_options_as_two_by_two() -> None:
    out = GamesMinesweeperRevealOutcomeLabelTask().generate(
        51270,
        params={"target_answer": 0, "scene_variant": "mixed_grid", "board_size": 6, "option_count": 4},
        max_attempts=256,
    )
    option_bboxes = out.trace_payload["render_map"]["reveal_outcome_option_bboxes_px"]

    assert set(option_bboxes) == {"A", "B", "C", "D"}
    assert _bbox_row_counts(option_bboxes) == (2, 2)


def test_games_minesweeper_task_sampling_covers_supports() -> None:
    forced_task = GamesMinesweeperForcedCellCountTask()
    forced_answers: dict[str, set[int]] = {"forced_mine_count": set(), "forced_safe_count": set()}
    forced_boards: dict[str, set[int]] = {"forced_mine_count": set(), "forced_safe_count": set()}
    for sampling_index in range(120):
        out = forced_task.generate(51301 + int(sampling_index), params={}, max_attempts=128)
        execution = out.trace_payload["execution_trace"]
        forced_answers[str(out.query_id)].add(int(out.answer_gt.value))
        forced_boards[str(out.query_id)].add(int(execution["board_size"]))
    assert forced_answers == {"forced_mine_count": {1, 2, 3, 4, 5}, "forced_safe_count": {1, 2, 3, 4, 5}}
    assert forced_boards == {"forced_mine_count": {4, 5}, "forced_safe_count": {4, 5}}

    remaining_answers = {
        int(GamesMinesweeperRemainingMineCountValueTask().generate(51401 + i, params={}, max_attempts=128).answer_gt.value)
        for i in range(80)
    }
    satisfied_answers = {
        int(GamesMinesweeperSatisfiedClueCountTask().generate(51501 + i, params={}, max_attempts=128).answer_gt.value)
        for i in range(80)
    }
    reveal_targets = {
        int(
            GamesMinesweeperRevealOutcomeLabelTask()
            .generate(51601 + i, params={}, max_attempts=256)
            .trace_payload["execution_trace"]["target_answer"]
        )
        for i in range(120)
    }
    assert remaining_answers == {0, 1, 2, 3, 4, 5}
    assert satisfied_answers == {1, 2, 3, 4, 5}
    assert reveal_targets == set(range(9))


def test_games_minesweeper_style_sampling_covers_supported_variants() -> None:
    styles: set[str] = set()
    scenes: set[str] = set()
    for sampling_index in range(120):
        out = GamesMinesweeperSatisfiedClueCountTask().generate(51701 + sampling_index, params={}, max_attempts=128)
        execution = out.trace_payload["execution_trace"]
        styles.add(str(execution["style_variant"]))
        scenes.add(str(execution["scene_variant"]))
    assert styles == set(SUPPORTED_MINESWEEPER_STYLE_VARIANTS)
    assert scenes == {"open_grid", "mixed_grid"}


def test_games_minesweeper_grid_is_deterministic() -> None:
    params = {"query_id": "forced_safe_count", "target_answer": 3, "scene_variant": "mixed_grid", "board_size": 5}
    task = GamesMinesweeperForcedCellCountTask()
    out_a = task.generate(51241, params=params, max_attempts=128)
    out_b = task.generate(51241, params=params, max_attempts=128)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_minesweeper_grid_prompt_bundle_requires_rule_texts() -> None:
    bundle = json.loads(Path("prompts/games/minesweeper/games_minesweeper_v1.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:forced_mine_count"] == ["minesweeper_rule_text"]
    assert required["query:forced_safe_count"] == ["minesweeper_rule_text"]
    assert required["query:remaining_mine_count"] == ["minesweeper_rule_text"]
    assert required["query:reveal_outcome_label"] == ["minesweeper_rule_text"]
    assert required["query:satisfied_clue_count"] == ["minesweeper_rule_text"]


def test_games_minesweeper_grid_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__minesweeper__forced_cell_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__minesweeper__forced_cell_count",
        instance_version="v0",
        image_format="png",
        tasks=[BuildTaskConfig(task_id="task_games__minesweeper__forced_cell_count", count=4, params={})],
        strict_repro=False,
        max_attempts_per_instance=128,
        sampling_seed=61,
    )
    final_path = build_dataset(config, code_hash="games-minesweeper-grid-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record.get("scene_id") == "minesweeper" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__minesweeper__forced_cell_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
