"""Contracts for Star Battle scene-package puzzle tasks."""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from trace.core.prompts import load_prompt_bundle
from trace.core.prompts.schema import REQUIRED_PROMPT_VARIANTS
from trace.core.scene_config import get_scene_defaults
from trace.tasks.puzzles.star_battle.remaining_valid_cell_count import (
    SUPPORTED_QUERY_IDS as REMAINING_COUNT_QUERY_IDS,
    PuzzlesStarBattleRemainingValidCellCountTask,
)
from trace.tasks.puzzles.star_battle.scoped_valid_cell_label import (
    SUPPORTED_QUERY_IDS as SCOPED_VALID_CELL_QUERY_IDS,
    PuzzlesStarBattleScopedValidCellLabelTask,
)
from trace.tasks.puzzles.star_battle.shared.state import SCENE_ID
from trace.tasks.puzzles.star_battle.valid_cell_anywhere_label import (
    SUPPORTED_QUERY_IDS as VALID_CELL_ANYWHERE_QUERY_IDS,
    PuzzlesStarBattleValidCellAnywhereLabelTask,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


LABEL_TASK_CLASSES = (
    PuzzlesStarBattleValidCellAnywhereLabelTask,
    PuzzlesStarBattleScopedValidCellLabelTask,
)
TASK_CLASSES = (
    *LABEL_TASK_CLASSES,
    PuzzlesStarBattleRemainingValidCellCountTask,
)


def test_star_battle_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults("puzzles", "star_battle")
    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "puzzles_star_battle_v1"

    generation_defaults, rendering_defaults, prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_puzzles__star_battle__remaining_valid_cell_count",
        )
    )
    assert str(prompt_defaults["scene_key"]).strip() == "star_battle"
    assert str(prompt_defaults["task_key"]).strip() == "star_battle_remaining_count_query"
    assert "query_id_weights" not in generation_defaults
    assert int(generation_defaults["target_count_min"]) == 1
    assert int(generation_defaults["target_count_max"]) == 6
    assert int(rendering_defaults["canvas_width"]) == 1080


def test_star_battle_prompt_bundle_supports_scene_package_variants() -> None:
    bundle = load_prompt_bundle("puzzles", "star_battle", "puzzles_star_battle_v1")
    assert bundle.schema_version == "v1"
    assert len(bundle.task_templates["star_battle_valid_cell_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.task_templates["star_battle_remaining_count_query"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["valid_cell_anywhere_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["valid_cell_in_marked_region_label"]) == REQUIRED_PROMPT_VARIANTS
    assert len(bundle.query_templates["valid_cell_for_marked_row_label"]) == REQUIRED_PROMPT_VARIANTS
    assert (
        len(bundle.query_templates["remaining_valid_cells_in_marked_region_count"])
        == REQUIRED_PROMPT_VARIANTS
    )
    assert (
        len(bundle.query_templates["remaining_valid_cells_in_marked_row_count"])
        == REQUIRED_PROMPT_VARIANTS
    )
    assert (
        len(bundle.query_templates["remaining_valid_cells_in_marked_column_count"])
        == REQUIRED_PROMPT_VARIANTS
    )
    assert list(bundle.required_slots_by_key["scene:star_battle"]) == ["object_description"]


def _internal_query_id(output: Any) -> str:
    payload = output.trace_payload
    assert isinstance(payload, Mapping)
    execution = payload["execution_trace"]
    if "internal_query_id" in execution:
        return str(execution["internal_query_id"])
    return str(execution["query_id"])


@pytest.mark.parametrize("task_cls", LABEL_TASK_CLASSES)
def test_star_battle_label_tasks_emit_scalar_bbox_contract(task_cls) -> None:
    task = task_cls()
    out = task.generate(83101, params={}, max_attempts=80)

    assert out.scene_id == SCENE_ID
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "bbox"
    assert len(out.annotation_gt.value) == 4
    assert "annotation" in out.prompt_variants["answer_and_annotation"].lower()
    assert '"answer"' in out.prompt_variants["answer_only"]

    trace = out.trace_payload
    assert trace["query_spec"]["params"]["scene_id"] == SCENE_ID
    assert trace["projected_annotation"]["type"] == "bbox"
    assert trace["annotation_gt"]["type"] == "bbox"


def test_star_battle_remaining_count_emits_bbox_set_contract() -> None:
    task = PuzzlesStarBattleRemainingValidCellCountTask()
    out = task.generate(83102, params={}, max_attempts=80)

    assert out.scene_id == SCENE_ID
    assert out.answer_gt.type == "integer"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == int(out.answer_gt.value)
    assert out.trace_payload["projected_annotation"]["type"] == "bbox_set"


@pytest.mark.parametrize(
    ("task_cls", "query_id"),
    [
        (PuzzlesStarBattleValidCellAnywhereLabelTask, VALID_CELL_ANYWHERE_QUERY_IDS[0]),
        *[
            (PuzzlesStarBattleScopedValidCellLabelTask, query_id)
            for query_id in SCOPED_VALID_CELL_QUERY_IDS
        ],
    ],
)
def test_star_battle_valid_cell_task_has_one_correct_labeled_cell(task_cls, query_id: str) -> None:
    task = task_cls()
    params = {} if task_cls is PuzzlesStarBattleValidCellAnywhereLabelTask else {"query_id": query_id}
    out = task.generate(83111, params=params, max_attempts=80)
    trace = out.trace_payload["execution_trace"]

    assert _internal_query_id(out) == query_id
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value in {"A", "B", "C", "D", "E", "F", "G", "H"}
    correct = [spec for spec in trace["candidate_specs"] if spec["is_correct"]]
    legal = [spec for spec in trace["candidate_specs"] if spec["is_legal"]]
    assert len(correct) == 1
    assert len(legal) == 1
    assert correct[0]["label"] == out.answer_gt.value


@pytest.mark.parametrize("query_id", REMAINING_COUNT_QUERY_IDS)
def test_star_battle_remaining_count_matches_scoped_legal_cells(query_id: str) -> None:
    task = PuzzlesStarBattleRemainingValidCellCountTask()
    out = task.generate(83121, params={"query_id": query_id}, max_attempts=80)
    trace = out.trace_payload["execution_trace"]

    assert _internal_query_id(out) == query_id
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == len(trace["scoped_legal_cells"])
    assert int(out.answer_gt.value) == len(out.annotation_gt.value)
    target_min, target_max = trace["target_count_range"]
    assert int(target_min) <= int(out.answer_gt.value) <= int(target_max)


@pytest.mark.parametrize("task_cls", TASK_CLASSES)
def test_star_battle_tasks_are_deterministic(task_cls) -> None:
    task = task_cls()
    params = {}
    out_a = task.generate(83131, params=params, max_attempts=80)
    out_b = task.generate(83131, params=params, max_attempts=80)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.annotation_gt == out_b.annotation_gt
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
