"""Behavior tests for the GUI navigation-path relation task."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.pages.relation.navigation_path_target_label import (
    SUPPORTED_QUERY_IDS,
    PagesRelationNavigationPathTargetLabelTask,
)
from tests.helpers import extract_prompt_json_example, read_jsonl


def test_gui_relation_navigation_path_target_label_contract_matches_trace() -> None:
    task = PagesRelationNavigationPathTargetLabelTask()
    scene_variants = ("office_document", "creative_workspace", "developer_ide")
    style_variants = ("standard", "compact", "contrast")

    for index, query_id in enumerate(SUPPORTED_QUERY_IDS):
        out = task.generate(
            78100 + index,
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
        assert trace["scene_ir"]["scene_kind"] == "gui_navigation_path"
        assert str(out.answer_gt.value) == str(execution["target_label"])
        assert str(target["candidate_label"]) == str(execution["target_label"])
        assert list(target["path_keys"]) == list(execution["path_labels"])
        if query_id == "menu_path_target_label":
            expected_roles = ("menu_root", "menu_group", "target_command")
        elif query_id == "sidebar_tree_target_label":
            expected_roles = ("sidebar_section", "sidebar_group", "target_item")
        else:
            expected_roles = ("ribbon_tab", "ribbon_group", "target_command")
        expected_annotation = {
            expected_roles[0]: annotation_supports[0]["bbox_px"],
            expected_roles[1]: annotation_supports[1]["bbox_px"],
            expected_roles[2]: target["bbox_px"],
        }
        assert out.annotation_gt.value == expected_annotation
        assert trace["projected_annotation"]["type"] == "keyed_bbox_map"
        assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
        assert set(out.annotation_gt.value) == set(expected_roles)
        assert execution["annotation_role_support_ids"] == {
            expected_roles[0]: str(execution["annotation_support_ids"][0]),
            expected_roles[1]: str(execution["annotation_support_ids"][1]),
            expected_roles[2]: str(target["control_id"]),
        }

        if query_id == "menu_path_target_label":
            assert list(execution["menu_command_count_range"]) == [3, 4]
            assert int(execution["menu_command_count"]) == 3
            assert int(execution["total_control_count"]) == 2 * 2 * 2 * int(execution["menu_command_count"])
            assert str(target["role"]) == "menu_item"
            assert [record["support_kind"] for record in annotation_supports] == ["menu_root", "menu_group"]
        elif query_id == "sidebar_tree_target_label":
            assert int(execution["total_control_count"]) == 12
            assert str(target["role"]) == "sidebar_tree_item"
            assert [record["support_kind"] for record in annotation_supports] == ["sidebar_section", "sidebar_group"]
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
            assert [record["support_kind"] for record in annotation_supports] == ["ribbon_tab", "ribbon_group"]

        assert set(out.complexity.complexity_components.keys()) == {
            "visual_scan",
            "relational_grounding",
            "layout_complexity",
            "output_burden",
        }
        assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
        assert all(0.0 <= float(coord) <= 1280.0 for box in out.annotation_gt.value.values() for coord in (box[0], box[2]))
        assert all(0.0 <= float(coord) <= 800.0 for box in out.annotation_gt.value.values() for coord in (box[1], box[3]))


def test_gui_relation_navigation_path_target_label_prompt_examples_match_option_contract() -> None:
    task = PagesRelationNavigationPathTargetLabelTask()
    out = task.generate(78200, params={"query_id": "menu_path_target_label"}, max_attempts=20)
    assert extract_prompt_json_example(out.prompt_variants["answer_and_annotation"]) == {
        "annotation": {
            "menu_root": [82, 214, 308, 252],
            "menu_group": [104, 270, 286, 302],
            "target_command": [112, 316, 286, 354],
        },
        "answer": "G",
    }
    assert extract_prompt_json_example(out.prompt_variants["answer_only"]) == {"answer": "G"}


def test_gui_relation_navigation_path_target_label_balanced_sampling_defaults_cover_axes_and_answers() -> None:
    task = PagesRelationNavigationPathTargetLabelTask()
    query_ids: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    answers_by_query_id: defaultdict[str, Counter[str]] = defaultdict(Counter)
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
        query_id = str(execution["query_id"])
        query_ids[query_id] += 1
        scene_variants[str(execution["scene_variant"])] += 1
        style_variants[str(execution["style_variant"])] += 1
        answers_by_query_id[query_id][str(execution["target_label"])] += 1
        if query_id == "menu_path_target_label":
            menu_command_counts[int(execution["menu_command_count"])] += 1
        if query_id == "ribbon_group_command_label":
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
                for key, value in dict(execution["query_id_probabilities"]).items()
                if float(value) > 0.0
            }

    assert active_variants
    assert set(query_ids.keys()) == active_variants
    assert all(count >= 0.30 * 156 for count in query_ids.values())
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
    for query_id in active_variants:
        assert len(answers_by_query_id[query_id]) >= 20


def test_gui_relation_navigation_path_target_label_deterministic() -> None:
    task = PagesRelationNavigationPathTargetLabelTask()
    params = {
        "query_id": "ribbon_group_command_label",
        "scene_variant": "cad_workspace",
        "style_variant": "contrast",
        "target_label": "M",
    }
    out_a = task.generate(78400, params=params, max_attempts=20)
    out_b = task.generate(78400, params=params, max_attempts=20)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.annotation_gt.to_dict() == out_b.annotation_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_gui_relation_navigation_path_target_label_build_smoke(tmp_path: Path) -> None:
    task_id = "task_pages__navigation_flow__menu_path_target_label"
    output_root = tmp_path / task_id
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name=f"build_smoke_{task_id}",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id=task_id,
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
    assert int(build_report["accepted_counts_by_task"][task_id]) == 4

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
