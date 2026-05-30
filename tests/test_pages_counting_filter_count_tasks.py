"""Behavior tests for the consolidated GUI filter-counting task."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path

from trace.core.builder import build_dataset
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.seed import hash64
from trace.tasks.pages.counting.filter_count import (
    CONTROL_QUERY_IDS,
    SUPPORTED_QUERY_IDS,
    TABLE_QUERY_IDS,
    PagesControlBoardControlFilterCountTask,
    PagesDataTableRowFilterCountTask,
)
from tests.helpers import extract_prompt_json_example, read_jsonl


def test_gui_counting_filter_count_contract_matches_trace() -> None:
    task_cases = (
        (PagesControlBoardControlFilterCountTask(), CONTROL_QUERY_IDS),
        (PagesDataTableRowFilterCountTask(), TABLE_QUERY_IDS),
    )
    scene_variants = ("office_document", "creative_workspace", "developer_ide", "cad_workspace", "scientific_plotter")
    style_variants = ("standard", "compact", "contrast", "standard", "compact")

    case_index = 0
    for task, supported_query_ids in task_cases:
        for query_id in supported_query_ids:
            out = task.generate(
                55100 + case_index,
                params={
                    "query_id": query_id,
                    "scene_variant": scene_variants[case_index],
                    "style_variant": style_variants[case_index],
                },
                max_attempts=20,
            )
            index = case_index
            case_index += 1
            trace = out.trace_payload
            execution = trace["execution_trace"]

            assert out.answer_gt.type == "integer"
            assert out.evidence_gt.type == "bbox_set"
            assert str(out.query_id) == str(query_id)
            assert str(execution["query_id"]) == str(query_id)
            assert str(execution["source_query_id"]) == str(query_id)
            assert str(execution["scene_variant"]) == str(scene_variants[index])
            assert str(execution["style_variant"]) == str(style_variants[index])
            assert int(out.answer_gt.value) == len(out.evidence_gt.value)
            assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
            assert set(execution["query_id_probabilities"].keys()) == set(supported_query_ids)

            if query_id in CONTROL_QUERY_IDS:
                controls = [dict(record) for record in execution["controls"]]
                matching_ids = [str(value) for value in execution["matching_control_ids"]]
                matching_records = [record for record in controls if str(record["control_id"]) in set(matching_ids)]
                assert trace["scene_ir"]["scene_kind"] == "gui_grouped_control_board"
                assert out.evidence_gt.value == [record["bbox_px"] for record in matching_records]
                target_group = str(execution["target_group_name"])
                assert all(str(record["group_name"]) == target_group for record in matching_records)
                if query_id == "disabled_controls_in_group_count":
                    assert all(bool(record["enabled"]) is False for record in matching_records)
                else:
                    assert all(bool(record["selected"]) is True and bool(record["enabled"]) is True for record in matching_records)
            else:
                rows = [dict(record) for record in execution["rows"]]
                matching_ids = [str(value) for value in execution["matching_row_ids"]]
                matching_records = [record for record in rows if str(record["row_id"]) in set(matching_ids)]
                assert trace["scene_ir"]["scene_kind"] == "gui_table_row_filter"
                assert out.evidence_gt.value == [record["bbox_px"] for record in matching_records]
                if query_id == "selected_rows_with_status_count":
                    target_status = str(execution["target_status"])
                    assert all(bool(record["selected"]) and str(record["status_label"]) == target_status for record in matching_records)
                elif query_id == "enabled_action_for_type_count":
                    target_type = str(execution["target_type"])
                    target_action = str(execution["target_action_label"])
                    assert all(str(record["type_label"]) == target_type for record in matching_records)
                    assert all(str(record["action_label"]) == target_action and bool(record["action_enabled"]) for record in matching_records)
                else:
                    target_section = str(execution["target_section_name"])
                    threshold = int(execution["size_threshold_mb"])
                    assert all(str(record["section_name"]) == target_section for record in matching_records)
                    assert all(int(record["size_mb"]) >= threshold for record in matching_records)

            assert set(out.complexity.complexity_components.keys()) == {
                "visual_scan",
                "state_filtering",
                "grouping",
                "output_burden",
            }
            assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
            assert all(0.0 <= float(coord) <= 1280.0 for box in out.evidence_gt.value for coord in (box[0], box[2]))
            assert all(0.0 <= float(coord) <= 800.0 for box in out.evidence_gt.value for coord in (box[1], box[3]))


def test_gui_counting_filter_count_prompt_examples_match_integer_contract() -> None:
    task = PagesControlBoardControlFilterCountTask()
    out = task.generate(55200, params={"query_id": "disabled_controls_in_group_count"}, max_attempts=20)
    assert extract_prompt_json_example(out.prompt_variants["answer_and_evidence"]) == {
        "evidence": [[96, 218, 221, 300], [233, 218, 358, 300], [370, 310, 495, 392]],
        "answer": 3,
    }
    assert extract_prompt_json_example(out.prompt_variants["answer_only"]) == {"answer": 3}


def test_gui_counting_filter_count_balanced_sampling_defaults_cover_axes_and_answers() -> None:
    tasks = (PagesControlBoardControlFilterCountTask(), PagesDataTableRowFilterCountTask())
    query_ids: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()
    style_variants: Counter[str] = Counter()
    answers_by_query_id: defaultdict[str, Counter[int]] = defaultdict(Counter)

    for task in tasks:
        for index in range(75):
            out = task.generate(
                hash64(55300, task.task_id, index),
                params={},
                max_attempts=20,
            )
            execution = out.trace_payload["execution_trace"]
            query_id = str(execution["query_id"])
            query_ids[query_id] += 1
            scene_variants[str(execution["scene_variant"])] += 1
            style_variants[str(execution["style_variant"])] += 1
            answers_by_query_id[query_id][int(execution["answer_value"])] += 1

    assert set(query_ids.keys()) == set(SUPPORTED_QUERY_IDS)
    assert query_ids["disabled_controls_in_group_count"] >= 30
    assert query_ids["selected_enabled_controls_in_group_count"] >= 30
    assert query_ids["selected_rows_with_status_count"] >= 20
    assert query_ids["enabled_action_for_type_count"] >= 20
    assert query_ids["value_threshold_in_group_count"] >= 20
    assert set(scene_variants.keys()) == {
        "office_document",
        "creative_workspace",
        "developer_ide",
        "cad_workspace",
        "scientific_plotter",
        "os_file_manager",
    }
    assert set(style_variants.keys()) == {"standard", "compact", "contrast", "cool", "warm", "sage"}
    assert set(answers_by_query_id["disabled_controls_in_group_count"].keys()).issubset({2, 3, 4, 5, 6})
    assert set(answers_by_query_id["selected_enabled_controls_in_group_count"].keys()).issubset({3, 4, 5, 6, 7})
    assert set(answers_by_query_id["enabled_action_for_type_count"].keys()).issubset({2, 3, 4, 5, 6})
    assert set(answers_by_query_id["selected_rows_with_status_count"].keys()).issubset({2, 3, 4, 5, 6, 7})
    assert set(answers_by_query_id["value_threshold_in_group_count"].keys()).issubset({2, 3, 4, 5, 6, 7})
    assert all(len(values) >= 5 for values in answers_by_query_id.values())


def test_gui_counting_filter_count_deterministic() -> None:
    task = PagesDataTableRowFilterCountTask()
    params = {
        "query_id": "value_threshold_in_group_count",
        "scene_variant": "cad_workspace",
        "style_variant": "contrast",
        "answer_value": 5,
    }
    out_a = task.generate(55400, params=params, max_attempts=20)
    out_b = task.generate(55400, params=params, max_attempts=20)
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_gui_counting_filter_count_build_smoke(tmp_path: Path) -> None:
    output_root = tmp_path / "task_pages__control_board__control_filter_count"
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name="build_smoke_task_pages__control_board__control_filter_count",
        instance_version="v0",
        image_format="png",
        tasks=[
            BuildTaskConfig(
                task_id="task_pages__control_board__control_filter_count",
                count=5,
                params={},
            )
        ],
        strict_repro=False,
        max_attempts_per_instance=20,
        sampling_seed=41,
    )
    final_path = build_dataset(config, code_hash="gui-counting-filter-count-smoke")
    assert final_path.exists()
    train_records = read_jsonl(final_path / "train_instances.jsonl")
    assert len(train_records) == 5
    assert all(record["domain"] == "pages" for record in train_records)
    assert all(record["task_group"] == "counting" for record in train_records)

    build_report = json.loads((final_path / "build_report.json").read_text(encoding="utf-8"))
    assert int(build_report["accepted_counts_by_task"]["task_pages__control_board__control_filter_count"]) == 5

    validation = json.loads((final_path / "validation_report.json").read_text(encoding="utf-8"))
    assert validation["total_errors"] == 0
