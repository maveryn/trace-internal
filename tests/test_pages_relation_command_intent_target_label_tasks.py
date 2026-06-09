"""Behavior tests for the GUI command-intent relation task."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.pages.relation.command_intent_target_label import (
    SUPPORTED_QUERY_IDS,
    PagesRelationCommandIntentTargetLabelTask,
)
from tests.helpers import extract_prompt_json_example, read_jsonl


def test_gui_relation_command_intent_target_label_contract_matches_trace() -> None:
    task = PagesRelationCommandIntentTargetLabelTask()
    scene_variants = ("office_document", "creative_workspace", "developer_ide", "cad_workspace", "scientific_plotter")
    style_variants = ("standard", "compact", "contrast", "standard", "compact")

    for index, query_id in enumerate(SUPPORTED_QUERY_IDS):
        out = task.generate(
            79100 + index,
            params={
                "query_id": query_id,
                "scene_variant": scene_variants[index],
                "style_variant": style_variants[index],
            },
            max_attempts=20,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        target = dict(execution["target_control"])
        annotation_supports = [dict(record) for record in execution["annotation_support_records"]]

        assert out.answer_gt.type == "option_letter"
        assert out.annotation_gt.type == "keyed_bbox_map"
        assert str(out.query_id) == str(query_id)
        assert str(execution["query_id"]) == str(query_id)
        assert str(execution["scene_variant"]) == str(scene_variants[index])
        assert str(execution["style_variant"]) == str(style_variants[index])
        assert trace["scene_ir"]["scene_kind"] == "gui_command_intent"
        assert str(out.answer_gt.value) == str(execution["target_label"])
        assert str(target["candidate_label"]) == str(execution["target_label"])
        assert str(target["role"]) == "command_matrix_cell"
        assert str(target["object_label"]) == str(execution["object_label"])
        assert str(target["object_cue_label"]) == str(execution["object_cue_label"])
        assert str(target["action_label"]) == str(execution["action_label"])
        assert str(target["action_cue_label"]) == str(execution["instruction_cue_label"])
        assert str(target["action_code_label"]) == str(execution["instruction_code_label"])
        assert str(execution["instruction_text"]).strip()
        if str(query_id) == "dual_guide_command_label":
            assert str(execution["object_cue_label"]) in str(execution["instruction_text"])
            assert str(execution["object_label"]) not in str(execution["instruction_text"])
        else:
            assert str(execution["object_label"]) in str(execution["instruction_text"])
        assert str(execution["instruction_cue_label"]) in str(execution["instruction_text"])
        assert str(execution["action_label"]).lower() not in str(execution["instruction_text"]).lower()
        assert int(execution["total_control_count"]) == 25
        annotation_role_support_ids = dict(execution["annotation_role_support_ids"])
        expected_annotation = {
            "action_cue_guide": annotation_supports[0]["bbox_px"],
            "object_row": next(
                record["bbox_px"] for record in annotation_supports if record["support_kind"] == "object_row"
            ),
            "action_code_header": next(
                record["bbox_px"] for record in annotation_supports if record["support_kind"] == "action_header"
            ),
            "target_command_cell": target["bbox_px"],
        }
        if str(query_id) == "dual_guide_command_label":
            assert [record["support_kind"] for record in annotation_supports] == [
                "intent_cue_card",
                "object_cue_card",
                "object_row",
                "action_header",
            ]
            assert str(annotation_supports[1]["object_cue_label"]) == str(execution["object_cue_label"])
            assert str(annotation_supports[1]["object_label"]) == str(execution["object_label"])
            expected_annotation["object_cue_guide"] = annotation_supports[1]["bbox_px"]
            action_support = annotation_supports[3]
        else:
            assert [record["support_kind"] for record in annotation_supports] == [
                "intent_cue_card",
                "object_row",
                "action_header",
            ]
            action_support = annotation_supports[2]
        assert out.annotation_gt.value == expected_annotation
        assert trace["projected_annotation"]["type"] == "keyed_bbox_map"
        assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
        assert set(annotation_role_support_ids) == set(expected_annotation)
        assert str(annotation_supports[0]["action_cue_label"]) == str(execution["instruction_cue_label"])
        assert str(annotation_supports[0]["action_code_label"]) == str(execution["instruction_code_label"])
        assert str(action_support["action_label"]) == str(execution["action_label"])
        assert str(action_support["action_code_label"]) == str(execution["instruction_code_label"])

        target_bbox = target["bbox_px"]
        badge_bbox = target["candidate_label_bbox_px"]
        assert float(target_bbox[2]) - float(target_bbox[0]) >= 150.0
        assert float(target_bbox[3]) - float(target_bbox[1]) >= 58.0
        assert float(badge_bbox[2]) - float(badge_bbox[0]) >= 20.0
        assert float(badge_bbox[3]) - float(badge_bbox[1]) >= 20.0

        assert set(out.complexity.complexity_components.keys()) == {
            "visual_scan",
            "relational_grounding",
            "layout_complexity",
            "output_burden",
        }
        assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
        assert all(
            0.0 <= float(coord) <= 1280.0
            for box in out.annotation_gt.value.values()
            for coord in (box[0], box[2])
        )
        assert all(
            0.0 <= float(coord) <= 800.0
            for box in out.annotation_gt.value.values()
            for coord in (box[1], box[3])
        )


def test_gui_relation_command_intent_target_label_prompt_examples_match_option_contract() -> None:
    task = PagesRelationCommandIntentTargetLabelTask()
    out = task.generate(79200, params={"query_id": "create_insert_command_label"}, max_attempts=20)
    assert extract_prompt_json_example(out.prompt_variants["answer_and_annotation"]) == {
        "annotation": {
            "action_cue_guide": [290, 150, 480, 190],
            "object_row": [70, 240, 270, 310],
            "action_code_header": [290, 200, 480, 235],
            "target_command_cell": [290, 320, 480, 390],
        },
        "answer": "G",
    }
    assert extract_prompt_json_example(out.prompt_variants["answer_only"]) == {"answer": "G"}


def test_gui_relation_command_intent_target_label_balanced_sampling_defaults_cover_axes_and_answers() -> None:
    task = PagesRelationCommandIntentTargetLabelTask()
    query_ids: Counter[str] = Counter()
    intent_categories: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    answers_by_query_id: defaultdict[str, Counter[str]] = defaultdict(Counter)

    for index in range(260):
        out = task.generate(
            hash64(79300, "gui_relation_command_intent_target_label", index),
            params={},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        query_id = str(execution["query_id"])
        query_ids[query_id] += 1
        intent_categories[str(execution["intent_category"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        answers_by_query_id[query_id][str(execution["target_label"])] += 1

    assert set(query_ids.keys()) == set(SUPPORTED_QUERY_IDS)
    assert all(abs(count - 130) <= 10 for count in query_ids.values())
    assert set(intent_categories.keys()) == {
        "create_insert",
        "select_choose",
        "view_toggle",
        "edit_transform",
        "format_style",
    }
    assert all(count >= 40 for count in intent_categories.values())
    # Balanced sampling is seeded uniform selection, not an exact cycle.
    assert max(intent_categories.values()) - min(intent_categories.values()) <= 32
    assert set(scene_variants.keys()) == {
        "office_document",
        "creative_workspace",
        "developer_ide",
        "cad_workspace",
        "scientific_plotter",
        "os_file_manager",
    }
    assert set(style_variants.keys()) == {"standard", "compact", "contrast", "cool", "warm", "sage"}
    for query_id in SUPPORTED_QUERY_IDS:
        assert len(answers_by_query_id[query_id]) >= 20


def test_gui_relation_command_intent_target_label_deterministic() -> None:
    task = PagesRelationCommandIntentTargetLabelTask()
    params = {
        "query_id": "edit_transform_command_label",
        "scene_variant": "cad_workspace",
        "style_variant": "contrast",
        "target_label": "M",
    }
    out_a = task.generate(79400, params=params, max_attempts=20)
    out_b = task.generate(79400, params=params, max_attempts=20)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_gui_relation_command_intent_target_label_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_pages__command_matrix__command_intent_target_label"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_pages__command_matrix__command_intent_target_label",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_pages__command_matrix__command_intent_target_label",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=20,
        sampling_seed=41,
    )
    final_path = build_dataset(config, code_hash="gui-relation-command-intent-target-label-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "pages" for record in train_records)
    assert all(record["task_group"] == "relation" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_pages__command_matrix__command_intent_target_label"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
