"""Behavior tests for the GUI navigation-path relation task."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.pages.relation.navigation_path_target_label import (
    SUPPORTED_QUERY_VARIANTS,
    PagesRelationNavigationPathTargetLabelTask,
)
from tests.helpers import extract_prompt_json_example, read_jsonl


def test_gui_relation_navigation_path_target_label_contract_matches_trace() -> None:
    task = PagesRelationNavigationPathTargetLabelTask()
    scene_variants = ("office_document", "creative_workspace", "developer_ide")
    style_variants = ("standard", "compact", "contrast")

    for index, query_variant in enumerate(SUPPORTED_QUERY_VARIANTS):
        out = task.generate(
            78100 + index,
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
        assert trace["scene_ir"]["scene_kind"] == "gui_navigation_path"
        assert str(out.answer_gt.value) == str(execution["target_label"])
        assert str(target["candidate_label"]) == str(execution["target_label"])
        assert list(target["path_keys"]) == list(execution["path_labels"])
        assert out.evidence_gt.value == [record["bbox_px"] for record in evidence_supports] + [target["bbox_px"]]
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert len(out.evidence_gt.value) == 3

        if query_variant == "menu_path_target_label":
            assert list(execution["menu_command_count_range"]) == [3, 4]
            assert int(execution["menu_command_count"]) == 3
            assert int(execution["total_control_count"]) == 2 * 2 * 2 * int(execution["menu_command_count"])
            assert str(target["role"]) == "menu_item"
            assert [record["support_kind"] for record in evidence_supports] == ["menu_root", "menu_group"]
        elif query_variant == "sidebar_tree_target_label":
            assert int(execution["total_control_count"]) == 12
            assert str(target["role"]) == "sidebar_tree_item"
            assert [record["support_kind"] for record in evidence_supports] == ["sidebar_section", "sidebar_group"]
        else:
            assert list(execution["ribbon_tab_count_range"]) == [3, 5]
            assert list(execution["ribbon_group_count_range"]) == [2, 3]
            assert list(execution["ribbon_command_count_range"]) == [3, 4]
            assert int(execution["total_control_count"]) == (
                int(execution["ribbon_tab_count"])
                * int(execution["ribbon_group_count"])
                * int(execution["ribbon_command_count"])
            )
            assert int(execution["total_control_count"]) <= 26
            assert str(target["role"]) == "ribbon_command"
            assert [record["support_kind"] for record in evidence_supports] == ["ribbon_tab", "ribbon_group"]

        assert set(out.complexity.complexity_components.keys()) == {
            "visual_scan",
            "relational_grounding",
            "layout_complexity",
            "output_burden",
        }
        assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
        assert all(0.0 <= float(coord) <= 1280.0 for box in out.evidence_gt.value for coord in (box[0], box[2]))
        assert all(0.0 <= float(coord) <= 800.0 for box in out.evidence_gt.value for coord in (box[1], box[3]))


def test_gui_relation_navigation_path_target_label_prompt_examples_match_option_contract() -> None:
    task = PagesRelationNavigationPathTargetLabelTask()
    out = task.generate(78200, params={"query_variant": "menu_path_target_label"}, max_attempts=20)
    assert extract_prompt_json_example(out.prompt_variants["answer_and_evidence"]) == {
        "evidence": [[82, 214, 308, 252], [104, 270, 286, 302], [112, 316, 286, 354]],
        "answer": "G",
    }
    assert extract_prompt_json_example(out.prompt_variants["answer_only"]) == {"answer": "G"}


def test_gui_relation_navigation_path_target_label_balanced_sampling_defaults_cover_axes_and_answers() -> None:
    task = PagesRelationNavigationPathTargetLabelTask()
    query_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    answers_by_query_variant: defaultdict[str, Counter[str]] = defaultdict(Counter)
    menu_command_counts: Counter[int] = Counter()
    ribbon_count_tuples: Counter[tuple[int, int, int]] = Counter()
    active_variants: set[str] | None = None

    for index in range(156):
        out = task.generate(
            hash64(78300, "gui_relation_navigation_path_target_label", index),
            params={},
            max_attempts=20,
        )
        execution = out.trace_payload["execution_trace"]
        query_variant = str(execution["query_id"])
        query_variants[query_variant] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        answers_by_query_variant[query_variant][str(execution["target_label"])] += 1
        if query_variant == "menu_path_target_label":
            menu_command_counts[int(execution["menu_command_count"])] += 1
        if query_variant == "ribbon_group_command_label":
            ribbon_count_tuples[
                (
                    int(execution["ribbon_tab_count"]),
                    int(execution["ribbon_group_count"]),
                    int(execution["ribbon_command_count"]),
                )
            ] += 1
        if active_variants is None:
            active_variants = {
                str(key)
                for key, value in dict(execution["query_variant_probabilities"]).items()
                if float(value) > 0.0
            }

    assert active_variants
    assert set(query_variants.keys()) == active_variants
    assert all(count >= 0.30 * 156 for count in query_variants.values())
    assert set(scene_variants.keys()) == {
        "office_document",
        "creative_workspace",
        "developer_ide",
        "cad_workspace",
        "scientific_plotter",
        "os_file_manager",
    }
    assert set(style_variants.keys()) == {"standard", "compact", "contrast", "cool", "warm", "sage"}
    if "menu_path_target_label" in active_variants:
        assert set(menu_command_counts.keys()) == {3}
    if "ribbon_group_command_label" in active_variants:
        assert set(ribbon_count_tuples.keys()) == {(3, 2, 3), (3, 2, 4), (4, 2, 3)}
    for query_variant in active_variants:
        assert len(answers_by_query_variant[query_variant]) >= 20


def test_gui_relation_navigation_path_target_label_deterministic() -> None:
    task = PagesRelationNavigationPathTargetLabelTask()
    params = {
        "query_variant": "ribbon_group_command_label",
        "scene_variant": "cad_workspace",
        "style_variant": "contrast",
        "target_label": "M",
    }
    out_a = task.generate(78400, params=params, max_attempts=20)
    out_b = task.generate(78400, params=params, max_attempts=20)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_gui_relation_navigation_path_target_label_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_pages__navigation_flow__navigation_path_target_label"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_pages__navigation_flow__navigation_path_target_label",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_pages__navigation_flow__navigation_path_target_label",
                count=4,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=20,
        sampling_seed=41,
    )
    final_path = build_dataset(config, code_hash="gui-relation-navigation-path-target-label-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 4
    assert all(record["domain"] == "pages" for record in train_records)
    assert all(record["task_group"] == "relation" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_pages__navigation_flow__navigation_path_target_label"]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
