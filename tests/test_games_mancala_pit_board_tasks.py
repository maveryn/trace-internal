"""Contract tests for Mancala-style pit-board games tasks."""

from __future__ import annotations

from pathlib import Path
import json

from trace.core.scene_config import get_scene_defaults
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.games.mancala_pit_board.post_sow_pit_count_value import (
    TASK_ID as POST_SOW_COUNT_TASK_ID,
)
from trace.tasks.games.mancala_pit_board.shared.rules import pit_index, pit_label, sow_counts
from trace.tasks.games.mancala_pit_board.shared.state import LABELS
from trace.tasks.games.mancala_pit_board.sowing_landing_pit_label import (
    TASK_ID as SOWING_LANDING_TASK_ID,
)
from trace.tasks.registry import create_task, ensure_scene_tasks_registered, is_default_dataset_task
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def test_games_mancala_pit_board_defaults_and_prompt_bundle() -> None:
    cfg = get_scene_defaults("games", "mancala_pit_board")
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg)

    assert set(generation["scene_variant_weights"].keys()) == {"low_seed", "mixed_seed", "busy_seed"}
    assert set(generation["style_variant_weights"].keys()) == {
        "wood_tray",
        "sand_stone",
        "slate_bowls",
        "cloth_pits",
        "arcade_pits",
    }
    task_overrides = cfg["generation"]["task_overrides"]
    assert list(task_overrides[SOWING_LANDING_TASK_ID]["target_landing_label_support"]) == list(LABELS)
    assert list(task_overrides[POST_SOW_COUNT_TASK_ID]["target_count_support"]) == list(range(9))
    assert int(rendering["seed_diameter_min_px"]) == 16
    assert int(rendering["seed_diameter_max_px"]) == 20
    assert str(prompt["bundle_id"]) == "games_mancala_pit_board_v1"


def test_games_mancala_pit_board_prompt_bundle_has_queries() -> None:
    bundle = json.loads(
        Path("prompts/games/mancala_pit_board/games_mancala_pit_board_v1.json").read_text(encoding="utf-8")
    )
    assert bundle["schema_version"] == "v1"
    assert set(bundle["templates"]["query"].keys()) == {
        "sowing_landing_pit_label",
        "post_sow_pit_count_value",
    }
    assert bool(bundle["allow_empty_task_templates"])


def test_games_mancala_pit_board_sowing_logic() -> None:
    counts = [0] * 12
    counts[pit_index("F")] = 3
    final_counts, path = sow_counts(counts, pit_index("F"))
    assert [pit_label(index) for index in path] == ["G", "H", "I"]
    assert final_counts[pit_index("F")] == 0
    assert final_counts[pit_index("G")] == 1
    assert final_counts[pit_index("H")] == 1
    assert final_counts[pit_index("I")] == 1


def test_games_mancala_pit_board_registry_and_taxonomy() -> None:
    ensure_scene_tasks_registered("games", "mancala_pit_board")
    assert is_default_dataset_task(SOWING_LANDING_TASK_ID)
    assert is_default_dataset_task(POST_SOW_COUNT_TASK_ID)
    for task_id in (SOWING_LANDING_TASK_ID, POST_SOW_COUNT_TASK_ID):
        taxonomy = resolve_task_taxonomy(task_id)
        assert taxonomy.domain == "games"
        assert taxonomy.scene_id == "mancala_pit_board"
        assert taxonomy.source_scene_id == ""


def test_games_mancala_pit_board_landing_answer_matches_trace() -> None:
    out = create_task(SOWING_LANDING_TASK_ID).generate(
        881003,
        params={"target_landing_label": "G"},
        max_attempts=100,
    )
    trace = out.trace_payload["execution_trace"]

    assert out.scene_id == "mancala_pit_board"
    assert out.query_id == "single"
    assert out.trace_payload["query_spec"]["params"]["prompt_query_key"] == "sowing_landing_pit_label"
    assert out.answer_gt.type == "string"
    assert str(out.answer_gt.value) == "G"
    assert trace["landing_label"] == "G"
    assert trace["sowing_path_labels"][-1] == "G"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 1
    assert out.trace_payload["projected_annotation"]["type"] == "bbox_set"


def test_games_mancala_pit_board_post_sow_count_answer_matches_trace() -> None:
    out = create_task(POST_SOW_COUNT_TASK_ID).generate(
        882003,
        params={"target_count": 8},
        max_attempts=100,
    )
    trace = out.trace_payload["execution_trace"]
    target_label = str(trace["target_label"])

    assert out.scene_id == "mancala_pit_board"
    assert out.query_id == "single"
    assert out.trace_payload["query_spec"]["params"]["prompt_query_key"] == "post_sow_pit_count_value"
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 8
    assert trace["final_counts_by_label"][target_label] == 8
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value.keys()) == {"source_pit", "target_pit"}
    assert out.trace_payload["projected_annotation"]["type"] == "keyed_bbox_map"
    assert set(out.trace_payload["projected_annotation"]["pixel_keyed_bbox_map"].keys()) == {"source_pit", "target_pit"}


def test_games_mancala_pit_board_support_endpoints_are_constructible() -> None:
    landing_task = create_task(SOWING_LANDING_TASK_ID)
    for label in ("A", "L"):
        out = landing_task.generate(883000 + pit_index(label), params={"target_landing_label": label}, max_attempts=100)
        assert str(out.answer_gt.value) == label

    count_task = create_task(POST_SOW_COUNT_TASK_ID)
    for target in (0, 8):
        out = count_task.generate(884000 + target, params={"target_count": target}, max_attempts=100)
        assert int(out.answer_gt.value) == target
