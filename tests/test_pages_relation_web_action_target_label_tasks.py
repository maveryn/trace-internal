"""Behavior tests for the web-style GUI action target task."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.pages.relation.web_action_target_label import (
    SUPPORTED_QUERY_VARIANTS,
    PagesRelationWebActionTargetLabelTask,
)
from tests.helpers import extract_prompt_json_example, read_jsonl


TASK_ID = "task_pages__web_action__web_action_target_label"
SCENE_KIND = "gui_web_action_target"


def test_gui_relation_web_action_target_contract_matches_trace() -> None:
    task = PagesRelationWebActionTargetLabelTask()
    scene_variants = ("shop_catalog", "travel_booking", "support_center")
    style_variants = ("standard", "compact", "contrast")

    for index, query_variant in enumerate(SUPPORTED_QUERY_VARIANTS):
        out = task.generate(
            99100 + index,
            params={
                "query_variant": query_variant,
                "scene_variant": scene_variants[index],
                "style_variant": style_variants[index],
            },
            max_attempts=20,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        target = dict(execution["target_control"])
        evidence_supports = [dict(record) for record in execution["evidence_support_records"]]

        assert out.answer_gt.type == "option_letter"
        assert out.evidence_gt.type == "bbox_set"
        assert str(out.query_variant) == "default"
        assert str(out.query_id) == str(query_variant)
        assert str(execution["query_variant"]) == "default"
        assert str(execution["query_id"]) == str(query_variant)
        assert str(execution["scene_variant"]) == str(scene_variants[index])
        assert str(execution["style_variant"]) == str(style_variants[index])
        assert trace["scene_ir"]["scene_kind"] == SCENE_KIND
        assert str(out.answer_gt.value) == str(execution["target_label"])
        assert str(target["candidate_label"]) == str(execution["target_label"])
        assert str(target["context_label"]) == str(execution["context_label"])
        assert str(target["action_label"]) == str(execution["action_label"])
        assert str(target["action_cue_label"]) == str(execution["instruction_cue_label"])
        assert str(target["action_code_label"]) == str(execution["instruction_code_label"])
        assert str(execution["instruction_text"]).strip()
        assert str(execution["context_label"]) in str(execution["instruction_text"])
        assert str(execution["instruction_cue_label"]) in str(execution["instruction_text"])
        assert str(execution["action_label"]).lower() not in str(execution["instruction_text"]).lower()

        assert out.evidence_gt.value == [record["bbox_px"] for record in evidence_supports] + [target["bbox_px"]]
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert len(out.evidence_gt.value) == 4
        evidence_support_kinds = [record["support_kind"] for record in evidence_supports]
        assert evidence_support_kinds[0] == "instruction_banner"
        assert evidence_support_kinds[1] in {"action_guide_card", "field_guide_card", "option_guide_card"}
        assert evidence_support_kinds[2] == str(target["support_kind"])
        assert str(evidence_supports[1]["support_id"]) == str(execution["guide_support_id"])
        assert str(evidence_supports[1]["cue_label"]) == str(execution["instruction_cue_label"])
        assert str(evidence_supports[1]["code_label"]) == str(execution["instruction_code_label"])
        assert str(evidence_supports[2]["support_id"]) == str(target["support_id"])

        if query_variant == "click_target_label":
            assert str(target["role"]) == "web_button"
            assert 12 <= int(execution["total_control_count"]) <= 24
            assert str(target["context_display_label"]).strip()
            assert str(target["context_display_label"]) not in str(execution["instruction_text"])
            assert str(target["context_attribute_1"]) in str(execution["instruction_text"])
            assert str(target["context_attribute_2"]) in str(execution["instruction_text"])
        elif query_variant == "type_field_label":
            assert str(target["role"]) == "web_input"
            assert 9 <= int(execution["total_control_count"]) <= 16
        else:
            assert str(target["role"]) == "web_option"
            assert 9 <= int(execution["total_control_count"]) <= 16

        assert set(out.complexity.complexity_components.keys()) == {
            "visual_scan",
            "relational_grounding",
            "layout_complexity",
            "output_burden",
        }
        assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
        assert all(0.0 <= float(coord) <= 1280.0 for box in out.evidence_gt.value for coord in (box[0], box[2]))
        assert all(0.0 <= float(coord) <= 800.0 for box in out.evidence_gt.value for coord in (box[1], box[3]))


def test_gui_relation_web_action_target_prompt_examples_match_option_contract() -> None:
    task = PagesRelationWebActionTargetLabelTask()
    out = task.generate(99200, params={}, max_attempts=20)
    assert extract_prompt_json_example(out.prompt_variants["answer_and_evidence"]) == {
        "evidence": [[80, 150, 1200, 210], [210, 222, 430, 278], [92, 310, 590, 430], [410, 378, 560, 418]],
        "answer": "G",
    }
    assert extract_prompt_json_example(out.prompt_variants["answer_only"]) == {"answer": "G"}


def test_gui_relation_web_action_target_balanced_sampling_defaults_cover_axes_and_answers() -> None:
    task = PagesRelationWebActionTargetLabelTask()
    query_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    answers_by_query_variant: defaultdict[str, Counter[str]] = defaultdict(Counter)

    for index in range(180):
        out = task.generate(
            hash64(99300, TASK_ID, index),
            params={},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        query_variant = str(execution["query_id"])
        query_variants[query_variant] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        answers_by_query_variant[query_variant][str(execution["target_label"])] += 1

    assert set(query_variants.keys()) == set(SUPPORTED_QUERY_VARIANTS)
    assert max(query_variants.values()) - min(query_variants.values()) <= 12
    assert set(scene_variants.keys()) == {
        "shop_catalog",
        "travel_booking",
        "support_center",
        "learning_portal",
        "finance_portal",
        "content_cms",
    }
    assert set(style_variants.keys()) == {"standard", "compact", "contrast", "cool", "warm", "sage"}
    for query_variant in SUPPORTED_QUERY_VARIANTS:
        assert len(answers_by_query_variant[query_variant]) >= 20


def test_gui_relation_web_action_target_deterministic() -> None:
    task = PagesRelationWebActionTargetLabelTask()
    params = {
        "query_variant": "select_option_label",
        "scene_variant": "finance_portal",
        "style_variant": "contrast",
        "target_label": "M",
    }
    out_a = task.generate(99400, params=params, max_attempts=20)
    out_b = task.generate(99400, params=params, max_attempts=20)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_gui_relation_web_action_target_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / TASK_ID
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name=f"build_smoke_{TASK_ID}",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id=TASK_ID,
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=20,
        sampling_seed=41,
    )
    final_path = build_dataset(config, code_hash=f"{TASK_ID}-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "pages" for record in train_records)
    assert all(record["task_group"] == "relation" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"][TASK_ID]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
