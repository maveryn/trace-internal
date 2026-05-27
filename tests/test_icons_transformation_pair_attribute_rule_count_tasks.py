"""Tests for icon pair attribute-rule counting."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.icons.transformation.attribute_rule_count import IconsTransformationPairAttributeRuleCountTask
from tests.helpers import read_jsonl


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    return json.loads(str(prompt).split(marker, 1)[1].strip())


def test_icons_transformation_pair_attribute_rule_count_contract_matches_scene() -> None:
    task = IconsTransformationPairAttributeRuleCountTask()
    out = task.generate(
        51200,
        params={
            "attribute_rule": "color_and_size_change",
            "object_count": 8,
            "target_count": 3,
        },
        max_attempts=200,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    scene_entities = [entity for entity in trace["scene_ir"]["entities"] if str(entity.get("panel")) == "scene"]
    assert out.answer_gt.type == "integer"
    assert int(out.answer_gt.value) == 3
    assert out.evidence_gt.type == "bbox_set"
    assert len(out.evidence_gt.value) == 3
    assert out.query_id == "default"
    assert out.query_id == "color_and_size_change"
    assert execution["query_id"] == "default"
    assert execution["query_id"] == "color_and_size_change"
    assert execution["question_format"] == "count_scene_cells_matching_reference_attribute_rule"
    assert execution["changed_attributes"] == ["color", "size"]
    assert int(execution["object_count"]) == 8
    assert int(execution["target_count"]) == 3
    assert len(scene_entities) == 8
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert 0.0 <= float(out.complexity.complexity_score) <= 1.0
    assert set(out.complexity.complexity_components.keys()) == {
        "visual_scan",
        "rule_inference",
        "ambiguity",
        "clutter",
    }

    matching_labels = set(str(value) for value in execution["matching_cell_labels"])
    evidence_by_label = {str(entity["label"]): list(entity["cell_bbox_xyxy"]) for entity in scene_entities}
    expected_evidence = [
        evidence_by_label[str(label)] for label in trace["witness_symbolic"]["matching_cell_labels_top_left"]
    ]
    assert out.evidence_gt.value == expected_evidence
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
    assert trace["render_map"]["anchors"]["reference_pair"]["attribute_rule"] == "color_and_size_change"

    for entity in scene_entities:
        label = str(entity["label"])
        is_match = label in matching_labels
        assert bool(entity["is_match"]) == is_match
        if is_match:
            assert entity["attribute_rule"] == "color_and_size_change"
            assert entity["changed_attributes"] == ["color", "size"]
        else:
            assert entity["attribute_rule"] in {"color_only_change", "size_only_change"}
        if "color" in entity["changed_attributes"]:
            assert entity["left_tint_rgb"] != entity["right_tint_rgb"]
        else:
            assert entity["left_tint_rgb"] == entity["right_tint_rgb"]
        if "size" in entity["changed_attributes"]:
            assert float(entity["left_size_scale"]) != float(entity["right_size_scale"])
        else:
            assert float(entity["left_size_scale"]) == float(entity["right_size_scale"]) == 1.0


def test_icons_transformation_pair_attribute_rule_count_deterministic_and_zero_match() -> None:
    task = IconsTransformationPairAttributeRuleCountTask()
    out_a = task.generate(51201, params={"attribute_rule": "color_only_change", "target_count": 0}, max_attempts=200)
    out_b = task.generate(51201, params={"attribute_rule": "color_only_change", "target_count": 0}, max_attempts=200)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.image.tobytes() == out_b.image.tobytes()
    assert int(out_a.answer_gt.value) == 0
    assert out_a.evidence_gt.value == []


def test_icons_transformation_pair_attribute_rule_count_prompt_example_matches_contract() -> None:
    task = IconsTransformationPairAttributeRuleCountTask()
    out = task.generate(51202, params={"attribute_rule": "size_only_change", "target_count": 2}, max_attempts=200)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": 3}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert answer_and_evidence["evidence"] == [[336, 104, 506, 274], [532, 104, 702, 274], [728, 104, 898, 274]]
    assert answer_and_evidence["answer"] == 3


def test_icons_transformation_pair_attribute_rule_count_balanced_sampling_defaults() -> None:
    task = IconsTransformationPairAttributeRuleCountTask()
    rules: Counter[str] = Counter()
    target_counts: Counter[int] = Counter()
    for index in range(60):
        out = task.generate(
            hash64(51203, "icons_pair_attribute_rule", index),
            params={},
            max_attempts=200,
        )
        execution = out.trace_payload["execution_trace"]
        rules[str(execution["query_id"])] += 1
        target_counts[int(execution["target_count"])] += 1
        assert 0 <= int(execution["target_count"]) <= 4
        assert 4 <= int(execution["object_count"]) <= 9
    assert set(rules.keys()) == {"color_only_change", "size_only_change", "color_and_size_change"}
    assert sum(rules.values()) == 60
    assert set(target_counts.keys()) == set(range(0, 5))


def test_icons_transformation_pair_attribute_rule_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_icons__pair_grid__pair_attribute_rule_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_icons__pair_grid__pair_attribute_rule_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_icons__pair_grid__pair_attribute_rule_count",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=200,
        sampling_seed=37,
    )
    final_path = build_dataset(config, code_hash="icons-transformation-attribute-rule-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "icons" for record in train_records)
    assert all(record["task_group"] == "transformation" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_icons__pair_grid__pair_attribute_rule_count"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
