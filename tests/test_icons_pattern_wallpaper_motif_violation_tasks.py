"""Behavior tests for the curated-icon wallpaper motif-violation task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.icons.pattern.wallpaper_motif_violation import (
    IconsPatternWallpaperMotifViolationTask,
    TASK_ID,
)
from trace.tasks.icons.pattern.wallpaper_shared import (
    SAFE_WALLPAPER_CANVAS_TREATMENTS,
    WALLPAPER_PANEL_CHROME_POLICY,
)
from trace.tasks.icons.shared.icon_assets import resolve_icon_pool
from tests.helpers import read_jsonl


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    return json.loads(str(prompt).split(marker, 1)[1].strip())


def test_icons_wallpaper_motif_violation_contract_matches_scene() -> None:
    task = IconsPatternWallpaperMotifViolationTask()
    out = task.generate(
        2026060804,
        params={
            "answer_label": "D",
            "shared_wallpaper_group_id": "p1",
            "odd_wallpaper_group_id": "p4",
        },
        max_attempts=300,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_panels = [
        entity
        for entity in trace["scene_ir"]["entities"]
        if str(entity.get("entity_kind")) == "wallpaper_panel"
    ]

    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 1
    assert out.scene_id == "wallpaper_panels"
    assert out.query_id == "wallpaper_motif_violation_label"
    assert trace["scene_ir"]["scene_kind"] == "icons_wallpaper_panels_global_pattern_outlier"
    assert execution["question_format"] == "select_panel_with_different_wallpaper_pattern"
    assert int(execution["option_count"]) == 6
    assert execution["option_labels"] == list("ABCDEF")
    assert str(execution["shared_wallpaper_group_id"]) == "p1"
    assert str(execution["odd_wallpaper_group_id"]) == "p4"
    assert execution["wallpaper_group_ids_by_label"] == {
        "A": "p1",
        "B": "p1",
        "C": "p1",
        "D": "p4",
        "E": "p1",
        "F": "p1",
    }
    assert execution["visible_internal_grid"] is False
    assert trace["render_spec"]["style"]["visible_internal_grid"] is False
    assert trace["render_spec"]["style"]["wallpaper_panel_chrome_policy"] == WALLPAPER_PANEL_CHROME_POLICY
    assert trace["render_spec"]["style"]["safe_canvas_treatments"] == list(SAFE_WALLPAPER_CANVAS_TREATMENTS)
    assert trace["render_spec"]["style"]["icon_canvas_style"]["treatment"] in SAFE_WALLPAPER_CANVAS_TREATMENTS

    assert len(scene_panels) == 6
    assert [str(panel["label"]) for panel in scene_panels] == list("ABCDEF")
    assert [str(panel["wallpaper_group_id"]) for panel in scene_panels if str(panel["label"]) == "D"] == ["p4"]
    assert all(str(panel["wallpaper_group_id"]) == "p1" for panel in scene_panels if str(panel["label"]) != "D")
    assert len({str(panel["icon_id"]) for panel in scene_panels}) == 6
    assert out.annotation_gt.value == [
        next(panel["panel_bbox_xyxy"] for panel in scene_panels if str(panel["label"]) == "D")
    ]
    assert trace["projected_annotation"]["type"] == "bbox_set"
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value

    non_symmetry_pool = set(resolve_icon_pool("non_symmetry.txt"))
    assert set(execution["icon_ids_by_label"].keys()) == set("ABCDEF")
    assert len(set(execution["icon_ids_by_label"].values())) == 6
    assert set(execution["icon_ids_by_label"].values()).issubset(non_symmetry_pool)
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert "different wallpaper pattern" in out.prompt
    assert 0.0 <= float(out.complexity.complexity_score) <= 1.0


def test_icons_wallpaper_motif_violation_rejects_four_option_layout() -> None:
    task = IconsPatternWallpaperMotifViolationTask()
    with pytest.raises(ValueError):
        task.generate(2026060805, params={"option_count": 4, "answer_label": "B"}, max_attempts=20)


def test_icons_wallpaper_motif_violation_rejects_unsafe_canvas_treatment() -> None:
    task = IconsPatternWallpaperMotifViolationTask()
    with pytest.raises(ValueError, match="quiet canvas treatments"):
        task.generate(2026060815, params={"icon_canvas_treatment": "worksheet_panel"}, max_attempts=20)


def test_icons_wallpaper_motif_violation_all_motifs_have_unique_answer() -> None:
    task = IconsPatternWallpaperMotifViolationTask()
    for index, group_id in enumerate(("p2", "pm", "pg", "cm", "pmm", "p4", "p3")):
        out = task.generate(
            hash64(2026060806, group_id, index),
            params={"shared_wallpaper_group_id": "p1", "odd_wallpaper_group_id": group_id, "answer_label": "F"},
            max_attempts=300,
        )
        execution = out.trace_payload["execution_trace"]
        group_ids_by_label = execution["wallpaper_group_ids_by_label"]
        assert str(execution["shared_wallpaper_group_id"]) == "p1"
        assert str(execution["odd_wallpaper_group_id"]) == group_id
        assert group_ids_by_label["F"] == group_id
        assert sum(1 for value in group_ids_by_label.values() if str(value) == group_id) == 1
        assert all(str(value) == "p1" for label, value in group_ids_by_label.items() if str(label) != "F")


def test_icons_wallpaper_motif_violation_prompt_example_matches_contract() -> None:
    task = IconsPatternWallpaperMotifViolationTask()
    out = task.generate(
        2026060807,
        params={"answer_label": "C"},
        max_attempts=300,
    )
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_annotation = _extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    assert answer_only == {"answer": "C"}
    assert list(answer_and_annotation.keys()) == ["annotation", "answer"]
    assert answer_and_annotation["answer"] == "C"
    assert isinstance(answer_and_annotation["annotation"], list)
    assert len(answer_and_annotation["annotation"]) == 1


def test_icons_wallpaper_motif_violation_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / TASK_ID
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name=f"build_smoke_{TASK_ID}",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id=TASK_ID,
                count=3,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=300,
        sampling_seed=37,
    )
    final_path = build_dataset(config, code_hash="icons-wallpaper-motif-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 3
    assert all(record["domain"] == "icons" for record in train_records)
    assert all(record["scene_id"] == "wallpaper_panels" for record in train_records)
    assert all(record["task_group"] == "pattern" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"][TASK_ID]) == 3

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
