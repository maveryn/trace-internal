"""Contract tests for the games darts score/count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.games.shared.darts_scene import dartboard_anchor_colors
from trace.tasks.shared.color_distance import color_distance
from trace.tasks.games.darts.score_count import GamesDartsScoreCountTask
from tests.helpers import read_jsonl


@pytest.mark.parametrize(
    ("params", "expected_answer", "expected_annotation_count"),
    (
        (
            {"scene_variant": "single_board", "query_id": "ring_count", "target_ring": "double", "target_answer": 3, "dart_count": 8},
            3,
            3,
        ),
        (
                {
                    "scene_variant": "single_board",
                    "query_id": "threshold_score_count",
                    "target_threshold": 40,
                    "target_answer": 4,
                    "dart_count": 8,
                },
            4,
            4,
        ),
    ),
)
def test_games_darts_score_count_emits_expected_count_contract(
    params: dict[str, int | str],
    expected_answer: int,
    expected_annotation_count: int,
) -> None:
    out = GamesDartsScoreCountTask().generate(92001, params=params, max_attempts=48)
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == int(expected_answer)
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == int(expected_annotation_count)
    assert trace["projected_annotation"]["type"] == "point_set"
    assert trace["projected_annotation"]["point_set"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point_set"] == out.annotation_gt.value
    assert len(execution["annotation_entity_ids"]) == int(expected_annotation_count)
    assert trace["query_spec"]["params"]["query_id"] == out.query_id
    assert int(execution["target_answer"]) == int(expected_answer)
    assert all(str(dart_id).startswith("dart_") for dart_id in execution["annotation_entity_ids"])


def test_games_darts_score_count_total_score_uses_one_dart_as_annotation() -> None:
    out = GamesDartsScoreCountTask().generate(
        92011,
        params={"scene_variant": "single_board", "query_id": "total_score", "dart_count": 1},
        max_attempts=48,
    )
    execution = out.trace_payload["execution_trace"]
    dart_scores = [int(spec["score"]) for spec in execution["dart_specs"]]
    answer_label = str(out.answer_gt.value)
    answer_options = {
        str(option["label"]): int(option["score"])
        for option in execution["score_options"]
    }
    assert out.answer_gt.type == "string"
    assert answer_label in {"A", "B", "C", "D", "E", "F"}
    assert len(answer_options) in {4, 6}
    assert len(set(answer_options.values())) == len(answer_options)
    assert int(execution["target_answer"]) == sum(dart_scores)
    assert answer_options[answer_label] == int(execution["target_answer"])
    assert [option for option in execution["score_options"] if bool(option["is_answer"])] == [
        {"label": answer_label, "score": int(execution["target_answer"]), "is_answer": True}
    ]
    assert len(out.annotation_gt.value) == 1
    assert out.annotation_gt.type == "point_set"
    assert len(execution["annotation_entity_ids"]) == 1
    assert execution["annotation_entity_ids"][0].startswith("dart_")
    assert execution["target_answer_support"] is None


def test_games_darts_score_count_query_cycle_covers_count_answers_and_scenes() -> None:
    task = GamesDartsScoreCountTask()
    answers_by_variant: dict[str, set[int]] = {
        "ring_count": set(),
        "threshold_score_count": set(),
    }
    scenes_by_variant: dict[str, set[str]] = {
        "total_score": set(),
        "ring_count": set(),
        "threshold_score_count": set(),
    }
    dart_counts_by_variant: dict[str, set[int]] = {"total_score": set(), "ring_count": set(), "threshold_score_count": set()}
    for sampling_index in range(90):
        out = task.generate(
            92101 + int(sampling_index),
            params={"_sample_cursor": int(sampling_index)},
            max_attempts=64,
        )
        query_id = str(out.query_id)
        execution = out.trace_payload["execution_trace"]
        scenes_by_variant[query_id].add(str(execution["scene_variant"]))
        dart_counts_by_variant[query_id].add(int(execution["dart_count"]))
        if query_id in answers_by_variant:
            answers_by_variant[query_id].add(int(out.answer_gt.value))

    assert answers_by_variant == {
        "ring_count": {0, 1, 2, 3, 4, 5},
        "threshold_score_count": {0, 1, 2, 3, 4, 5},
    }
    assert all(values == {"single_board"} for values in scenes_by_variant.values())
    assert dart_counts_by_variant["total_score"] == {1}
    assert dart_counts_by_variant["ring_count"] == {5, 6, 7, 8}
    assert dart_counts_by_variant["threshold_score_count"] == {5, 6, 7, 8}


def test_games_darts_score_count_is_deterministic() -> None:
    params = {
        "scene_variant": "single_board",
        "query_id": "threshold_score_count",
        "target_threshold": 30,
        "target_answer": 4,
        "dart_count": 8,
    }
    task = GamesDartsScoreCountTask()
    out_a = task.generate(92031, params=params, max_attempts=48)
    out_b = task.generate(92031, params=params, max_attempts=48)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_games_darts_score_count_dart_color_is_lab_separated_from_board() -> None:
    out = GamesDartsScoreCountTask().generate(
        92041,
        params={"scene_variant": "single_board", "query_id": "ring_count", "target_ring": "single", "target_answer": 2, "dart_count": 8},
        max_attempts=48,
    )
    execution = out.trace_payload["execution_trace"]
    color = tuple(int(v) for v in execution["dart_fill_color"])
    anchors = dartboard_anchor_colors(str(execution["style_variant"]))
    distances = [float(color_distance(color, anchor, distance_space="lab")) for anchor in anchors]
    assert min(distances) >= 40.0


def test_games_darts_score_count_prompt_bundle_requires_query_specific_slots() -> None:
    bundle = json.loads(Path("prompts/games/darts/games_darts_v0.json").read_text(encoding="utf-8"))
    required = bundle["required_slots_by_key"]
    assert required["query:total_score"] == ["scoring_rule_text"]
    assert required["query:ring_count"] == ["ring_rule_text", "target_ring_text"]
    assert required["query:threshold_score_count"] == ["scoring_rule_text", "target_threshold_text"]


def test_games_darts_score_count_total_score_prompt_asks_for_visible_option_letter() -> None:
    out = GamesDartsScoreCountTask().generate(
        92052,
        params={"scene_variant": "single_board", "query_id": "total_score", "dart_count": 1},
        max_attempts=48,
    )

    assert "option letter" in out.prompt
    assert "shown in the image" in out.prompt
    assert "marked dart" in out.prompt
    assert "marked darts" not in out.prompt


@pytest.mark.parametrize(
    ("target_ring", "expected_phrase"),
    (
        ("single", "yellow-highlighted single area"),
        ("double", "yellow-highlighted double ring"),
        ("triple", "yellow-highlighted triple ring"),
        ("bull", "yellow-highlighted bull area"),
    ),
)
def test_games_darts_score_count_ring_prompt_uses_natural_area_names(
    target_ring: str,
    expected_phrase: str,
) -> None:
    out = GamesDartsScoreCountTask().generate(
        92051,
        params={
            "scene_variant": "single_board",
            "query_id": "ring_count",
            "target_ring": target_ring,
            "target_answer": 2,
            "dart_count": 8,
        },
        max_attempts=48,
    )

    assert expected_phrase in out.prompt


def test_games_darts_score_count_ring_prompt_describes_double_and_triple_bands() -> None:
    out = GamesDartsScoreCountTask().generate(
        92061,
        params={
            "scene_variant": "single_board",
            "query_id": "ring_count",
            "target_ring": "double",
            "target_answer": 2,
            "dart_count": 8,
        },
        max_attempts=48,
    )

    assert "double ring is the outer scoring band" in out.prompt
    assert "triple ring is the inner scoring band" in out.prompt
    assert "Single areas are the numbered wedge areas" in out.prompt


def test_games_darts_score_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_games__darts__total_score_option_label"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_games__darts__total_score_option_label",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_games__darts__total_score_option_label",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=48,
        sampling_seed=71,
    )
    final_path = build_dataset(config, code_hash="games-darts-score-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "games" for record in train_records)
    assert all(record["task_group"] == "darts" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_games__darts__total_score_option_label"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
