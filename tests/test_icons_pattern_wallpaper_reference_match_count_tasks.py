"""Behavior tests for the wallpaper reference-match count task."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.tasks.icons.pattern.wallpaper_reference_match_count import (
    IconsPatternWallpaperReferenceMatchCountTask,
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


def test_icons_wallpaper_reference_match_count_contract_matches_scene() -> None:
    task = IconsPatternWallpaperReferenceMatchCountTask()
    out = task.generate(
        2026060904,
        params={
            "match_count": 3,
            "matching_labels": ["B", "D", "F"],
            "reference_wallpaper_group_id": "p1",
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

    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 3
    assert out.annotation_gt.type == "keyed_bbox_set_map"
    assert sorted(out.annotation_gt.value.keys()) == ["matching_candidate_panels", "reference_panel"]
    assert out.scene_id == "wallpaper_panels"
    assert out.query_id == "reference_pattern_match_count"
    assert trace["scene_ir"]["scene_kind"] == "icons_wallpaper_panels_reference_match_count"
    assert execution["question_format"] == "count_candidate_panels_matching_reference_wallpaper_pattern"
    assert int(execution["option_count"]) == 6
    assert execution["option_labels"] == list("ABCDEF")
    assert execution["matching_labels"] == ["B", "D", "F"]
    assert int(execution["match_count"]) == 3
    assert str(execution["reference_wallpaper_group_id"]) == "p1"
    assert execution["visible_internal_grid"] is False
    assert trace["render_spec"]["style"]["visible_internal_grid"] is False
    assert trace["render_spec"]["style"]["wallpaper_panel_chrome_policy"] == WALLPAPER_PANEL_CHROME_POLICY
    assert trace["render_spec"]["style"]["safe_canvas_treatments"] == list(SAFE_WALLPAPER_CANVAS_TREATMENTS)
    assert trace["render_spec"]["style"]["icon_canvas_style"]["treatment"] in SAFE_WALLPAPER_CANVAS_TREATMENTS

    reference_panels = [panel for panel in scene_panels if bool(panel["is_reference"])]
    candidate_panels = [panel for panel in scene_panels if str(panel["panel_role"]) == "candidate"]
    assert len(reference_panels) == 1
    assert len(candidate_panels) == 6
    assert [str(panel["label"]) for panel in candidate_panels] == list("ABCDEF")

    reference = reference_panels[0]
    matching = [panel for panel in candidate_panels if bool(panel["matches_reference_pattern"])]
    nonmatching = [panel for panel in candidate_panels if not bool(panel["matches_reference_pattern"])]
    assert [str(panel["label"]) for panel in matching] == ["B", "D", "F"]
    assert str(reference["wallpaper_group_id"]) == "p1"
    assert all(str(panel["wallpaper_group_id"]) == "p1" for panel in matching)
    assert all(str(panel["wallpaper_group_id"]) != "p1" for panel in nonmatching)
    assert len({str(panel["wallpaper_group_id"]) for panel in nonmatching}) == 3
    assert len({str(panel["icon_id"]) for panel in scene_panels}) == 7

    non_symmetry_pool = set(resolve_icon_pool("non_symmetry.txt"))
    assert set(execution["icon_ids_by_label"].keys()) == {"Reference", *set("ABCDEF")}
    assert len(set(execution["icon_ids_by_label"].values())) == 7
    assert set(execution["icon_ids_by_label"].values()).issubset(non_symmetry_pool)

    expected_annotation = {
        "reference_panel": [list(reference["panel_bbox_xyxy"])],
        "matching_candidate_panels": [list(panel["panel_bbox_xyxy"]) for panel in matching],
    }
    assert out.annotation_gt.value == expected_annotation
    assert trace["projected_annotation"]["type"] == "keyed_bbox_set_map"
    assert trace["projected_annotation"]["keyed_bbox_set_map"] == expected_annotation
    assert trace["projected_annotation"]["pixel_keyed_bbox_set_map"] == expected_annotation
    assert sorted(out.prompt_variants.keys()) == ["answer_and_annotation", "answer_only"]
    assert "How many labeled panels use the same wallpaper arrangement as the Reference panel?" in out.prompt


def test_icons_wallpaper_reference_match_count_prompt_example_matches_contract() -> None:
    task = IconsPatternWallpaperReferenceMatchCountTask()
    out = task.generate(2026060905, params={"match_count": 2}, max_attempts=300)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_annotation = _extract_prompt_json_example(out.prompt_variants["answer_and_annotation"])
    assert answer_only == {"answer": 2}
    assert list(answer_and_annotation.keys()) == ["annotation", "answer"]
    assert sorted(answer_and_annotation["annotation"].keys()) == ["matching_candidate_panels", "reference_panel"]
    assert isinstance(answer_and_annotation["annotation"]["reference_panel"], list)
    assert len(answer_and_annotation["annotation"]["reference_panel"]) == 1
    assert isinstance(answer_and_annotation["annotation"]["matching_candidate_panels"], list)
    assert answer_and_annotation["answer"] == 2


def test_icons_wallpaper_reference_match_count_rejects_unsafe_canvas_treatment() -> None:
    task = IconsPatternWallpaperReferenceMatchCountTask()
    with pytest.raises(ValueError, match="quiet canvas treatments"):
        task.generate(2026060913, params={"icon_canvas_treatment": "dot_sheet"}, max_attempts=20)


def test_icons_wallpaper_reference_match_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / TASK_ID
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name=f"build_smoke_{TASK_ID}",
        instance_version="v0",
        image_format="png",
        tasks=[BuildTaskConfig(task_id=TASK_ID, count=3, params={})],
        strict_repro=False,
        max_attempts_per_instance=300,
        sampling_seed=37,
    )
    final_path = build_dataset(config, code_hash="icons-wallpaper-reference-count-smoke")
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
