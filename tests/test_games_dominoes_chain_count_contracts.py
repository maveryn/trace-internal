"""Contract tests for the games dominoes chain-count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.dominoes.matching_end_count import (
    GamesDominoesChainCountTask,
    GamesDominoesExtendableFirstPlayCountTask,
    GamesDominoesMatchingEndCountTask,
    GamesDominoesSecondPlayCandidateCountTask,
)
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_annotation_count"),
    (
        (
            {
                "scene_variant": "single_row",
                "query_id": "matching_end_count",
                "target_answer": 3,
                "candidate_count": 8,
            },
            3,
            3,
        ),
        (
            {
                "scene_variant": "single_row",
                "query_id": "higher_sum_than_reference_count",
                "target_answer": 4,
                "candidate_count": 9,
            },
            4,
            4,
        ),
        (
            {
                "scene_variant": "two_row",
                "query_id": "sum_to_target_count",
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
                "query_id": "double_count",
                "target_answer": 5,
                "candidate_count": 12,
            },
            5,
            5,
        ),
        (
            {
                "scene_variant": "single_row",
                "query_id": "second_play_candidate_count",
                "target_answer": 2,
                "candidate_count": 8,
            },
            2,
            2,
        ),
        (
            {
                "scene_variant": "two_row",
                "query_id": "extendable_first_play_count",
                "target_answer": 3,
                "candidate_count": 10,
            },
            3,
            3,
        ),
    ),
)
def test_games_dominoes_chain_count_emits_expected_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_annotation_count: int,
) -> None:
    out = GamesDominoesChainCountTask().generate(26001, params=params, max_attempts=48)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == int(expected_annotation_count)
    assert trace["query_spec"]["params"]["query_id"] == out.query_id
    assert int(execution["target_answer"]) == int(expected_answer)
    assert trace["projected_annotation"]["type"] == "bbox_set"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_bbox_set"] == out.annotation_gt.value
    assert len(execution["annotation_entity_ids"]) == int(expected_annotation_count)
    assert all(str(tile_id).startswith("candidate_") for tile_id in execution["annotation_entity_ids"])
    assert set(trace["render_map"]["section_label_bboxes_px"].keys()) == {"chain", "candidates"}
    assert len(trace["render_map"]["section_separator_bbox_px"]) == 4
    width, height = out.image.size
    for bbox in trace["render_map"]["domino_bboxes_px"].values():
        x0, y0, x1, y1 = [float(value) for value in bbox]
        assert 0.0 <= x0 < x1 <= float(width)
        assert 0.0 <= y0 < y1 <= float(height)


def test_games_dominoes_chain_count_matching_end_marks_reference_and_open_half() -> None:
    out = GamesDominoesChainCountTask().generate(
        26011,
        params={
            "scene_variant": "single_row",
            "query_id": "matching_end_count",
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
            "query_id": "sum_to_target_count",
            "target_answer": 2,
            "candidate_count": 8,
            "target_total": 6,
        },
        max_attempts=48,
    )
    execution = out.trace_payload["execution_trace"]
    assert int(execution["target_total"]) == 6
    assert "6" in out.prompt


def test_games_dominoes_second_play_candidate_count_matches_unique_first_play() -> None:
    out = GamesDominoesSecondPlayCandidateCountTask().generate(
        26041,
        params={
            "scene_variant": "single_row",
            "query_id": "second_play_candidate_count",
            "target_answer": 3,
            "candidate_count": 8,
        },
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    candidates = {
        str(spec["tile_id"]): spec
        for spec in execution["candidate_tile_specs"]
    }
    first_id = str(execution["first_step_tile_id"])
    open_end = int(execution["open_end_value"])
    bridge = int(execution["bridge_value"])

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 3
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 3
    assert out.trace_payload["projected_annotation"]["type"] == "bbox_set"
    assert out.trace_payload["projected_annotation"]["bbox_set"] == out.annotation_gt.value
    assert out.trace_payload["witness_symbolic"] == {
        "type": "object_set",
        "ids": list(execution["annotation_entity_ids"]),
    }

    valid_first_ids = []
    valid_second_ids = []
    for candidate_id, candidate in candidates.items():
        tile = (int(candidate["left_value"]), int(candidate["right_value"]))
        if _can_connect(tile, open_end):
            valid_first_ids.append(str(candidate_id))
            continue
        if _can_connect(tile, bridge):
            valid_second_ids.append(str(candidate_id))
    assert valid_first_ids == [first_id]
    assert set(valid_second_ids) == set(execution["annotation_entity_ids"])
    prompt_lower = out.prompt.lower()
    assert "remaining" in prompt_lower
    assert "second" in prompt_lower
    assert "new open end" in prompt_lower


def test_games_dominoes_extendable_first_play_count_matches_followup_rule() -> None:
    out = GamesDominoesExtendableFirstPlayCountTask().generate(
        26043,
        params={
            "scene_variant": "two_row",
            "query_id": "extendable_first_play_count",
            "target_answer": 4,
            "candidate_count": 10,
        },
        max_attempts=96,
    )
    execution = out.trace_payload["execution_trace"]
    candidates = {
        str(spec["tile_id"]): spec
        for spec in execution["candidate_tile_specs"]
    }
    open_end = int(execution["open_end_value"])
    extendable_ids = []
    for candidate_id, candidate in candidates.items():
        tile = (int(candidate["left_value"]), int(candidate["right_value"]))
        if not _can_connect(tile, open_end):
            continue
        new_open = _new_open_end(tile, open_end)
        if any(
            str(other_id) != str(candidate_id)
            and _can_connect((int(other["left_value"]), int(other["right_value"])), new_open)
            for other_id, other in candidates.items()
        ):
            extendable_ids.append(str(candidate_id))

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 4
    assert out.annotation_gt.type == "bbox_set"
    assert set(extendable_ids) == set(execution["annotation_entity_ids"])
    assert len(out.annotation_gt.value) == 4


def test_games_dominoes_chain_count_query_cycle_covers_answer_and_scene_support() -> None:
    task = GamesDominoesChainCountTask()
    answers_by_variant: dict[str, set[int]] = {
        "double_count": set(),
        "extendable_first_play_count": set(),
        "higher_sum_than_reference_count": set(),
        "matching_end_count": set(),
        "second_play_candidate_count": set(),
        "sum_to_target_count": set(),
    }
    scenes_by_variant: dict[str, set[str]] = {
        "double_count": set(),
        "extendable_first_play_count": set(),
        "higher_sum_than_reference_count": set(),
        "matching_end_count": set(),
        "second_play_candidate_count": set(),
        "sum_to_target_count": set(),
    }
    styles_by_variant: dict[str, set[str]] = {
        "double_count": set(),
        "extendable_first_play_count": set(),
        "higher_sum_than_reference_count": set(),
        "matching_end_count": set(),
        "second_play_candidate_count": set(),
        "sum_to_target_count": set(),
    }
    for sampling_index in range(216):
        out = task.generate(
            26101 + int(sampling_index),
            params={},
            max_attempts=192,
        )
        query_id = str(out.query_id)
        execution = out.trace_payload["execution_trace"]
        answers_by_variant[query_id].add(int(out.answer_gt.value))
        scenes_by_variant[query_id].add(str(execution["scene_variant"]))
        styles_by_variant[query_id].add(str(execution["style_variant"]))

    assert answers_by_variant == {
        "double_count": {0, 1, 2, 3, 4, 5},
        "extendable_first_play_count": {0, 1, 2, 3, 4},
        "higher_sum_than_reference_count": {0, 1, 2, 3, 4, 5},
        "matching_end_count": {0, 1, 2, 3, 4, 5},
        "second_play_candidate_count": {0, 1, 2, 3, 4, 5},
        "sum_to_target_count": {0, 1, 2, 3, 4},
    }
    assert scenes_by_variant == {
        "double_count": {"single_row", "two_row"},
        "extendable_first_play_count": {"single_row", "two_row"},
        "higher_sum_than_reference_count": {"single_row", "two_row"},
        "matching_end_count": {"single_row", "two_row"},
        "second_play_candidate_count": {"single_row", "two_row"},
        "sum_to_target_count": {"single_row", "two_row"},
    }
    expected_styles = {"classic", "soft", "outlined", "ivory", "charcoal_tile", "wood_tile"}
    for observed_styles in styles_by_variant.values():
        assert observed_styles <= expected_styles
        assert len(observed_styles) >= 5


def test_games_dominoes_chain_count_is_deterministic() -> None:
    params = {
        "scene_variant": "two_row",
        "query_id": "higher_sum_than_reference_count",
        "target_answer": 5,
        "candidate_count": 12,
    }
    task = GamesDominoesChainCountTask()
    out_a = task.generate(26031, params=params, max_attempts=48)
    out_b = task.generate(26031, params=params, max_attempts=48)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_dominoes_chain_count_prompt_bundle_requires_rule_text_for_query_specific_prompts() -> None:
    bundle = json.loads(Path("prompts/games/dominoes/games_dominoes_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:matching_end_count"] == ["connection_rule_text"]
    assert required["query:higher_sum_than_reference_count"] == ["pip_sum_rule_text"]
    assert required["query:sum_to_target_count"] == ["pip_sum_rule_text", "target_total_text"]
    assert required["query:double_count"] == ["double_rule_text"]
    assert required["query:second_play_candidate_count"] == ["connection_rule_text", "second_play_rule_text"]
    assert required["query:extendable_first_play_count"] == ["connection_rule_text", "extendable_first_play_rule_text"]


def test_games_dominoes_chain_play_prompt_templates_name_counted_play() -> None:
    bundle = json.loads(Path("prompts/games/dominoes/games_dominoes_v0.json").read_text(encoding="utf-8"))
    second_templates = bundle["query_templates"]["second_play_candidate_count"]
    first_templates = bundle["query_templates"]["extendable_first_play_count"]

    assert second_templates
    assert first_templates
    assert all("second" in str(template).lower() for template in second_templates)
    assert all("{connection_rule_text}" in str(template) for template in second_templates)
    assert all("{second_play_rule_text}" in str(template) for template in second_templates)
    assert all("{connection_rule_text}" in str(template) for template in first_templates)
    assert all("{extendable_first_play_rule_text}" in str(template) for template in first_templates)


def test_games_dominoes_chain_count_prompt_avoids_table_color_and_sentence_splice() -> None:
    out = GamesDominoesMatchingEndCountTask().generate(
        20260509,
        params={
            "scene_variant": "two_row",
            "query_id": "matching_end_count",
            "target_answer": 3,
            "candidate_count": 12,
        },
        max_attempts=48,
    )

    assert "green table" not in out.prompt
    assert "Using the `REF` tile at the end of the chain, A loose" not in out.prompt


def _can_connect(tile: tuple[int, int], open_end: int) -> bool:
    return int(open_end) in {int(tile[0]), int(tile[1])}


def _new_open_end(tile: tuple[int, int], open_end: int) -> int:
    assert _can_connect(tile, open_end)
    if int(tile[0]) == int(tile[1]):
        return int(open_end)
    return int(tile[1]) if int(tile[0]) == int(open_end) else int(tile[0])


def test_games_dominoes_chain_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__dominoes__double_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__dominoes__double_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__dominoes__double_count",
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
    assert all(record.get("scene_id") == "dominoes" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__dominoes__double_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
