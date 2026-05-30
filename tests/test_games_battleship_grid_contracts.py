"""Contract tests for games Battleship-grid tasks."""

from __future__ import annotations

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.battleship.sunk_ship_count import (
    GamesBattleshipGridTask,
    GamesBattleshipShipStatusCountTask,
)
from trace.tasks.games.shared.battleship_common import (
    FLEET_SHAPES,
    coord_to_cell_id,
    matching_fleet_shape_ids,
)
from trace.tasks.games.shared.style import SUPPORTED_BATTLESHIP_STYLE_VARIANTS
from tests.helpers import read_jsonl


def _coords(values: list[list[int]]) -> tuple[tuple[int, int], ...]:
    """Return trace coordinate lists as stable coordinate tuples."""

    return tuple((int(row), int(col)) for row, col in values)


def test_games_battleship_sunk_ship_count_emits_expected_contract() -> None:
    out = GamesBattleshipShipStatusCountTask().generate(
        74101,
        params={"target_answer": 3, "board_size": 9, "style_variant": "navy", "query_id": "sunk_ship_count"},
        max_attempts=128,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 3
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_id == "sunk_ship_count"
    assert out.scene_id == "battleship"
    assert trace["query_spec"]["query_id"] == "sunk_ship_count"
    assert trace["query_spec"]["params"]["query_id"] == "sunk_ship_count"
    assert execution["query_id"] == "sunk_ship_count"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)
    assert trace["render_spec"]["text_style"]["font_family"]
    assert trace["render_map"]["font_family"] == trace["render_spec"]["text_style"]["font_family"]


def test_games_battleship_sunk_ship_count_places_each_ship_once_and_counts_sunk_ships() -> None:
    out = GamesBattleshipShipStatusCountTask().generate(
        74111,
        params={"target_answer": 4, "board_size": 10, "style_variant": "paper", "query_id": "sunk_ship_count"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    hit_coords = set(_coords(execution["hit_coords"]))
    miss_coords = set(_coords(execution["miss_coords"]))
    evidence_coords = set(_coords(execution["evidence_coords"]))
    ships = execution["ship_placements"]
    sunk_ships = [ship for ship in ships if bool(ship["is_sunk"])]
    ship_cells = {coord for ship in ships for coord in _coords(ship["coords"])}

    assert len(ships) == len(FLEET_SHAPES)
    assert {ship["shape_id"] for ship in ships} == {shape.shape_id for shape in FLEET_SHAPES}
    assert hit_coords <= ship_cells
    assert not (miss_coords & ship_cells)
    assert len(sunk_ships) == int(out.answer_gt.value) == 4
    assert evidence_coords == {
        coord
        for ship in sunk_ships
        for coord in _coords(ship["coords"])
    }
    assert set(execution["evidence_entity_ids"]) == {coord_to_cell_id(coord) for coord in evidence_coords}
    for ship in ships:
        coords = _coords(ship["coords"])
        ship_hits = set(_coords(ship["hit_coords"]))
        matches = matching_fleet_shape_ids(coords)
        assert str(ship["shape_id"]) in matches
        assert ship_hits <= set(coords)
        assert bool(ship["is_sunk"]) == (ship_hits == set(coords))


def test_games_battleship_partial_ship_count_emits_expected_contract() -> None:
    out = GamesBattleshipShipStatusCountTask().generate(
        74131,
        params={"target_answer": 3, "board_size": 9, "style_variant": "classic", "query_id": "partial_ship_count"},
        max_attempts=128,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 3
    assert out.evidence_gt.type == "bbox_set"
    assert out.query_id == "partial_ship_count"
    assert out.scene_id == "battleship"
    assert trace["query_spec"]["query_id"] == "partial_ship_count"
    assert trace["query_spec"]["params"]["query_id"] == "partial_ship_count"
    assert execution["query_id"] == "partial_ship_count"
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert len(execution["evidence_entity_ids"]) == len(out.evidence_gt.value)
    assert trace["render_spec"]["text_style"]["font_family"]
    assert trace["render_map"]["font_family"] == trace["render_spec"]["text_style"]["font_family"]


def test_games_battleship_partial_ship_count_places_each_ship_once_and_counts_partial_ships() -> None:
    out = GamesBattleshipShipStatusCountTask().generate(
        74141,
        params={"target_answer": 4, "board_size": 10, "style_variant": "outlined", "query_id": "partial_ship_count"},
        max_attempts=128,
    )
    execution = out.trace_payload["execution_trace"]
    hit_coords = set(_coords(execution["hit_coords"]))
    miss_coords = set(_coords(execution["miss_coords"]))
    evidence_coords = set(_coords(execution["evidence_coords"]))
    ships = execution["ship_placements"]
    partial_ships = [
        ship
        for ship in ships
        if bool(ship["hit_coords"]) and not bool(ship["is_sunk"])
    ]
    ship_cells = {coord for ship in ships for coord in _coords(ship["coords"])}

    assert len(ships) == len(FLEET_SHAPES)
    assert {ship["shape_id"] for ship in ships} == {shape.shape_id for shape in FLEET_SHAPES}
    assert hit_coords <= ship_cells
    assert not (miss_coords & ship_cells)
    assert len(partial_ships) == int(out.answer_gt.value) == 4
    assert evidence_coords == {
        coord
        for ship in partial_ships
        for coord in _coords(ship["coords"])
    }
    assert set(execution["evidence_entity_ids"]) == {coord_to_cell_id(coord) for coord in evidence_coords}
    for ship in ships:
        coords = _coords(ship["coords"])
        ship_hits = set(_coords(ship["hit_coords"]))
        matches = matching_fleet_shape_ids(coords)
        assert str(ship["shape_id"]) in matches
        assert ship_hits <= set(coords)
        assert bool(ship["is_sunk"]) == (ship_hits == set(coords))


def test_games_battleship_grid_query_cycle_covers_answer_board_and_style_support() -> None:
    task = GamesBattleshipGridTask()
    query_ids: set[str] = set()
    boards: set[int] = set()
    styles: set[str] = set()

    for sampling_index in range(192):
        out = task.generate(
            74201 + int(sampling_index),
            params={},
            max_attempts=128,
        )
        execution = out.trace_payload["execution_trace"]
        query_ids.add(str(out.query_id))
        boards.add(int(execution["board_size"]))
        styles.add(str(execution["style_variant"]))

    assert query_ids == {"partial_ship_count", "sunk_ship_count"}
    assert boards == {8, 9, 10}
    assert styles == set(SUPPORTED_BATTLESHIP_STYLE_VARIANTS)

    for query_id in ("partial_ship_count", "sunk_ship_count"):
        for target_answer in (1, 2, 3, 4):
            out = task.generate(
                74400 + (10 * target_answer),
                params={"query_id": query_id, "target_answer": target_answer},
                max_attempts=128,
            )
            assert int(out.answer_gt.value) == target_answer


def test_games_battleship_grid_is_deterministic() -> None:
    params = {"target_answer": 2, "board_size": 8, "style_variant": "radar"}
    task = GamesBattleshipGridTask()
    out_a = task.generate(74121, params=params, max_attempts=128)
    out_b = task.generate(74121, params=params, max_attempts=128)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]


def test_games_battleship_grid_build_dataset_smoke(tmp_path) -> None:
    output_root = tmp_path / "task_games__battleship__ship_status_count"
    cfg = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games_battleship_grid",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__battleship__ship_status_count",
                count=2,
                params={"board_size": 9, "target_answer": 2},
            ),
        ],
        max_attempts_per_instance=128,
        workers=1,
    )
    final_path = build_dataset(cfg, code_hash="games-battleship-grid-smoke")
    rows = read_jsonl(final_path / "train_instances.jsonl")

    assert len(rows) == 2
    assert all(row["domain"] == "games" for row in rows)
    assert all(row["task_group"] == "battleship" for row in rows)
    assert all(row["answer_gt"]["type"] == "integer" for row in rows)
    assert all(row["evidence_gt"]["type"] == "bbox_set" for row in rows)
