from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time

from PIL import Image

from trace.review_app.artifact_index import build_review_index
from trace.review_app.feedback import FeedbackStore


TASK_ID = "task_pages__workspace__toolbar_palette_control_label"
TASK_ID_2 = "task_pages__workspace__property_panel_control_label"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _make_review_fixture(tmp_path: Path, *, prompt: str = "What label is on the target control?") -> Path:
    root = tmp_path / "review" / "task-reviews"
    task_dir = root / "pages" / "workspace" / TASK_ID
    image_rel = f"pages/workspace/{TASK_ID}/images/lookup/0000.png"
    data_rel = f"pages/workspace/{TASK_ID}/data/lookup/0000.json"

    image_path = root / image_rel
    image_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (120, 90), (245, 247, 250)).save(image_path)

    _write_json(
        root / "pages" / "workspace" / "scene_review_manifest.json",
        {
            "calibration_baseline": "v0",
            "domain": "pages",
            "scene_id": "workspace",
            "task_count": 1,
            "inspection_count": 1,
            "workbook": "pages/workspace/scene_review.xlsx",
            "tasks": {TASK_ID: {"task_manifest": f"pages/workspace/{TASK_ID}/manifest.json"}},
        },
    )
    _write_json(
        root / "pages" / "workspace" / "migration_test_status.json",
        {
            "schema": "trace_scene_migration_test_status_v1",
            "domain": "pages",
            "scene_id": "workspace",
            "passed": True,
            "status": "passed",
            "summary": "3 passed",
            "checked_at": "2026-06-12T00:00:00+00:00",
            "command": "pytest -q tests/test_review_app.py tests/test_run_task_review.py",
            "test_files": ["tests/test_review_app.py", "tests/test_run_task_review.py"],
        },
    )
    _write_json(
        root / "pages" / "workspace" / "manual_code_audit_status.json",
        {
            "schema": "trace_scene_manual_code_audit_status_v1",
            "domain": "pages",
            "scene_id": "workspace",
            "passed": True,
            "status": "passed",
            "summary": "role-boundary audit passed",
            "checked_at": "2026-06-12T00:00:00+00:00",
            "checked_by": "test",
            "checklist": {
                "public_tasks_own_objectives": True,
                "shared_code_identity_free": True,
            },
            "files_reviewed": ["trace/tasks/pages/workspace/example.py"],
        },
    )
    _write_json(
        root / "pages" / "workspace" / "taxonomy_review_status.json",
        {
            "schema": "trace_scene_taxonomy_review_status_v1",
            "domain": "pages",
            "scene_id": "workspace",
            "passed": True,
            "status": "passed",
            "summary": "taxonomy contract audit passed",
            "checked_at": "2026-06-12T00:00:00+00:00",
            "checked_by": "test",
            "checklist": {
                "program_codes_concrete": True,
                "query_ids_semantic": True,
                "task_contracts_stable": True,
            },
            "task_ids": [TASK_ID],
        },
    )
    _write_json(
        task_dir / "manifest.json",
        {
            "calibration_baseline": "v0",
            "inspection_count": 1,
            "query_ids": {"lookup": 1},
            "task_id": TASK_ID,
            "workbook": f"pages/workspace/{TASK_ID}/{TASK_ID}.xlsx",
        },
    )
    _write_json(
        task_dir / "distribution_review.json",
        {
            "task_id": TASK_ID,
            "domain": "pages",
            "scene_id": "workspace",
            "mode": "single_sample",
            "pass": True,
            "overall": {
                "checks": {
                    "max_answer_frequency": {
                        "observed": 0.25,
                        "pass": True,
                        "threshold": 0.3333333333333333,
                    },
                    "max_five_bin_frequency": {
                        "observed": 0.335,
                        "pass": None,
                        "status": "reported_not_gated_numeric_answers",
                    },
                    "min_unique_answers": {
                        "observed": 5,
                        "pass": True,
                        "threshold": 4,
                    },
                },
                "max_answer_frequency": 0.25,
                "sample_count": 100,
                "unique_answers": 5,
            },
        },
    )
    _write_json(
        root / data_rel,
        {
            "answer_gt": {"type": "option_letter", "value": "G"},
            "domain": "pages",
            "annotation_gt": {"type": "bbox_set", "value": [[10, 10, 40, 40]]},
            "image": {"format": "png", "path": image_rel},
            "instance_seed": 123,
            "prompt": prompt,
            "prompt_variants": {
                "answer_only": prompt + " Answer only.",
                "answer_and_annotation": prompt + " Include annotation.",
            },
            "query_id": "lookup",
            "scene_id": "workspace",
            "task": TASK_ID,
            "trace_payload": {
                "execution_trace": {"query_id": "lookup"},
                "taxonomy": {
                    "public": {
                        "domain": "pages",
                        "scene_id": "workspace",
                        "task_id": TASK_ID,
                        "query_id": "lookup",
                    }
                },
            },
        },
    )
    task_doc = tmp_path / "docs" / "tasks" / "pages" / "workspace" / f"{TASK_ID}.md"
    task_doc.parent.mkdir(parents=True, exist_ok=True)
    task_doc.write_text(
        "\n".join(
            [
                f"# `{TASK_ID}`",
                "",
                "## Contract",
                "1. Domain: `pages`",
                "2. Scene id: `workspace`",
                "3. Query id: `lookup`",
                "4. Answer schema: `option_letter`",
                "5. Annotation schema: `bbox_set`",
                "",
                "## Program Contract",
                "- `select_labeled_control(toolbar_palette, target_role=palette_control); scene=workspace; scope=toolbar_palette_control_label`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return root


def _write_accepted_solve_status(root: Path) -> None:
    _write_json(
        root.parent / "calibration_sweep_status.json",
        {
            "config": {"calibration_baseline": "v0"},
            "tasks": {
                TASK_ID: {
                    "domain": "pages",
                    "scene_id": "workspace",
                    "status": "accepted",
                    "models": {
                        "qwen25vl7b": {
                            "status": "accepted",
                            "stats": {
                                "overall": {
                                    "mean_solve_rate": 0.42,
                                    "hard_frac": 0.08,
                                    "easy_frac": 0.12,
                                    "band_frac": 0.80,
                                    "prompt_count": 100,
                                    "rollout_count": 2400,
                                },
                                "prompt_token_stats": {"over_limit_count": 0},
                                "response_token_stats": {"cap_rate": 0.0},
                            },
                        }
                    },
                }
            },
        },
    )


def _write_taxonomy_audit_fixture(tmp_path: Path) -> None:
    audit_dir = tmp_path / "review" / "task-reviews" / "taxonomy" / "contract_v0_reanalysis"
    audit_dir.mkdir(parents=True, exist_ok=True)
    program_arguments = json.dumps(
        {
            "schema_version": "program_arguments_v0",
            "status": "inferred",
            "parameter_axes": ["role_selection"],
            "arguments": {
                "reference_or_rule": {
                    "value_type": "semantic_role",
                    "allowed_values": ["target_control"],
                    "source": "test_fixture",
                    "notes": "",
                },
                "candidate_options": {
                    "value_type": "semantic_role",
                    "allowed_values": ["visible_candidate_options"],
                    "source": "test_fixture",
                    "notes": "",
                },
            },
            "constraints": [],
        },
        sort_keys=True,
    )
    program_arguments_csv = program_arguments.replace('"', '""')
    _write_json(
        audit_dir / "summary.json",
        {
            "live_task_count": 2,
            "proposed_task_count": 3,
            "split_task_count": 1,
            "query_row_count": 2,
            "program_signature_count": 1,
            "base_program_contract_count": 3,
            "duplicate_base_program_contract_count": 0,
            "program_argument_row_count": 2,
            "program_argument_status_counts": {"inferred": 2},
            "domains": {"pages": {"current_tasks": 2, "proposed_tasks": 3, "split_tasks": 1}},
        },
    )
    (audit_dir / "domain_taxonomies").mkdir(parents=True, exist_ok=True)
    (audit_dir / "domain_taxonomies" / "pages.md").write_text(
        "# Pages Taxonomy\n\nWorkspace target lookup review notes.\n",
        encoding="utf-8",
    )
    (audit_dir / "proposed_task_summary.csv").write_text(
        "\n".join(
            [
                "domain,scene_id,current_task_id,decision,proposed_task_count,proposed_task_ids,query_ids,program_signature_ids,base_program_contracts,program_argument_axes_json,answer_schemas,annotation_schemas,rationale",
                (
                    "pages,workspace,"
                    f"{TASK_ID},split,2,"
                    "task_pages__workspace__control_text_label|task_pages__workspace__target_state_label,"
                    "lookup,selection.option_match,"
                    "\"select_option(reference_or_rule, candidate_options); scene=workspace; scope=control_text_label\","
                    f"\"{program_arguments_csv}\","
                    "option_letter,bbox_set,"
                    "Split control text from state lookup."
                ),
                (
                    "pages,workspace,"
                    f"{TASK_ID_2},keep,1,"
                    f"{TASK_ID_2},"
                    "lookup,selection.option_match,"
                    "\"select_option(reference_or_rule, candidate_options); scene=workspace; scope=secondary_target_label\","
                    f"\"{program_arguments_csv}\","
                    "option_letter,bbox_set,"
                    "Keep secondary target lookup as one task."
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (audit_dir / "task_query_analysis.csv").write_text(
        "\n".join(
            [
                "domain,scene_id,current_task_id,current_query_id,current_task_slug,proposed_task_id,proposed_task_slug,scene_contract,view_contract,answer_schema,answer_type_observed,annotation_schema,annotation_type_observed,annotation_schema_notes,program_signature_id,program_schema,base_program_contract,parameter_axes,program_arguments_json,decision_source,rationale,generation_failures,source_file,doc_path,sample_count,example_json_paths,example_image_paths,decision,split_from,merge_with,proposed_scene_id_size",
                (
                    "pages,workspace,"
                    f"{TASK_ID},lookup,toolbar_palette_control_label,"
                    "task_pages__workspace__control_text_label,"
                    "control_text_label,"
                    "pages/workspace renderer grammar,workspace.default_view,"
                    "option_letter,option_letter,bbox_set,bbox_set,,"
                    "selection.option_match,"
                    "\"select_option(reference_or_rule, candidate_options); scene=workspace; scope=control_text_label\","
                    "\"select_option(reference_or_rule, candidate_options); scene=workspace; scope=control_text_label\","
                    f"role_selection,\"{program_arguments_csv}\",manual_boundary_seed,"
                    "Contract-v0 keeps the narrower visible-control objective.,"
                    ",trace/tasks/pages/workspace.py,docs/tasks/example.md,1,,,split,"
                    f"{TASK_ID},,2"
                ),
                (
                    "pages,workspace,"
                    f"{TASK_ID_2},lookup,secondary_target_label,"
                    f"{TASK_ID_2},"
                    "secondary_target_label,"
                    "pages/workspace renderer grammar,workspace.default_view,"
                    "option_letter,option_letter,bbox_set,bbox_set,,"
                    "selection.option_match,"
                    "\"select_option(reference_or_rule, candidate_options); scene=workspace; scope=secondary_target_label\","
                    "\"select_option(reference_or_rule, candidate_options); scene=workspace; scope=secondary_target_label\","
                    f"role_selection,\"{program_arguments_csv}\",manual_boundary_seed,"
                    "Contract-v0 keeps the secondary visible-control objective.,"
                    ",trace/tasks/pages/workspace.py,docs/tasks/example.md,0,,,keep,"
                    f"{TASK_ID_2},,1"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_review_index_scans_domain_scene_task_query_samples(tmp_path: Path) -> None:
    root = _make_review_fixture(tmp_path)
    _write_json(
        root / "assets" / "fonts" / "scene_review_manifest.json",
        {"domain": "assets", "scene_id": "fonts", "task_count": 99},
    )
    _write_json(
        root / "scratch_domain" / "scratch_scene" / "scene_review_manifest.json",
        {"domain": "scratch_domain", "scene_id": "scratch_scene", "task_count": 99},
    )

    index = build_review_index(root, repo_root=tmp_path, enforce_migration_registry=False)

    assert sorted(index.domains) == ["pages"]
    assert sorted(index.scenes) == ["pages/workspace"]
    assert sorted(index.tasks) == [f"pages/workspace/{TASK_ID}"]
    assert len(index.samples) == 1
    task = index.tasks[f"pages/workspace/{TASK_ID}"]
    assert task.query_counts == {"lookup": 1}
    assert task.distribution_pass is True
    scene = index.scenes["pages/workspace"]
    assert scene.migration_test_pass is True
    assert scene.migration_test_summary["summary"] == "3 passed"
    assert scene.migration_test_status_rel_path == "pages/workspace/migration_test_status.json"
    assert scene.manual_code_audit_pass is True
    assert scene.manual_code_audit_summary["summary"] == "role-boundary audit passed"
    assert scene.manual_code_audit_status_rel_path == "pages/workspace/manual_code_audit_status.json"
    assert scene.taxonomy_review_pass is True
    assert scene.taxonomy_review_summary["summary"] == "taxonomy contract audit passed"
    assert scene.taxonomy_review_status_rel_path == "pages/workspace/taxonomy_review_status.json"
    sample = next(iter(index.samples.values()))
    assert sample.answer_value == "G"
    assert sample.image_exists is True
    assert sample.image_mtime_ns > 0
    assert index.media[sample.media_id].exists()
    assert "assets" not in index.domains
    assert "scratch_domain" not in index.domains
    assert "assets/fonts" not in index.scenes


def test_review_index_accepts_program_schema_after_contract_metadata(tmp_path: Path) -> None:
    root = _make_review_fixture(tmp_path)
    task_doc = tmp_path / "docs" / "tasks" / "pages" / "workspace" / f"{TASK_ID}.md"
    task_doc.write_text(
        "\n".join(
            [
                f"# `{TASK_ID}`",
                "",
                "## Contract",
                "- Domain: `pages`",
                "- Scene id: `workspace`",
                "- Query id: `lookup`",
                "- Answer schema: `option_letter`",
                "- Annotation schema: `bbox_set`",
                "",
                "## Program Contract",
                "- Domain: `pages`",
                "- Scene: `workspace`",
                "- Public task id: `task_pages__workspace__toolbar_palette_control_label`",
                "- Program schema: `select_labeled_control(toolbar_palette, target_role=palette_control); scene=workspace; scope=toolbar_palette_control_label`",
                "- Program code: `select.pages.toolbar_palette_control`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    index = build_review_index(root, repo_root=tmp_path, enforce_migration_registry=False)

    scene = index.scenes["pages/workspace"]
    task = index.tasks[f"pages/workspace/{TASK_ID}"]
    assert scene.taxonomy_review_pass is True
    assert task.taxonomy_summary["program_contract"] == (
        "select_labeled_control(toolbar_palette, target_role=palette_control); "
        "scene=workspace; scope=toolbar_palette_control_label"
    )
    assert not any("taxonomy_review_status.json claims passed" in error for error in index.errors)


def test_review_index_default_hides_unregistered_migration_scenes(tmp_path: Path) -> None:
    root = _make_review_fixture(tmp_path)

    index = build_review_index(root, repo_root=tmp_path)

    assert index.domains == {}
    assert index.scenes == {}
    assert index.tasks == {}
    assert index.samples == {}


def test_review_sample_uid_changes_when_sample_content_changes(tmp_path: Path) -> None:
    root = _make_review_fixture(tmp_path, prompt="First prompt")
    first_uid = next(iter(build_review_index(root, repo_root=tmp_path, enforce_migration_registry=False).samples))

    _make_review_fixture(tmp_path, prompt="Changed prompt")
    second_uid = next(iter(build_review_index(root, repo_root=tmp_path, enforce_migration_registry=False).samples))

    assert first_uid != second_uid


def test_feedback_store_persists_and_updates_records(tmp_path: Path) -> None:
    root = _make_review_fixture(tmp_path)
    sample = next(iter(build_review_index(root, repo_root=tmp_path, enforce_migration_registry=False).samples.values()))
    store = FeedbackStore(tmp_path / "feedback.sqlite")

    created = store.add_feedback(sample=sample, comment="Annotation box is too broad.", category="annotation")
    updated = store.update_feedback(created.id, status="resolved", severity="note")

    assert updated.status == "resolved"
    assert updated.severity == "note"
    assert store.list_for_sample(sample.uid)[0].comment == "Annotation box is too broad."
    assert store.counts_by_task()[f"pages/workspace/{TASK_ID}"]["resolved"] == 1

    task_feedback = store.add_task_feedback(
        domain="pages",
        scene_id="workspace",
        task_id=TASK_ID,
        comment="Needs more font variation across samples.",
    )
    assert task_feedback.sample_uid == ""
    assert store.list_task_feedback(domain="pages", scene_id="workspace", task_id=TASK_ID)[0].comment == (
        "Needs more font variation across samples."
    )
    assert sample.uid in store.counts_by_sample()
    assert "" not in store.counts_by_sample()
    assert store.counts_by_task()[f"pages/workspace/{TASK_ID}"]["total"] == 2
    assert [record.comment for record in store.list_open_feedback()] == ["Needs more font variation across samples."]

    note = store.add_feedback_note(
        created.id,
        note="Narrowed the annotation box and regenerated the review sample.",
        author="agent",
    )
    comment = store.add_feedback_comment(
        created.id,
        comment="Reviewer confirmed the new box is closer, but still slightly tall.",
        author="reviewer",
    )
    assert note.feedback_id == created.id
    assert note.author == "agent"
    assert comment.feedback_id == created.id
    assert comment.author == "reviewer"
    assert store.list_comments_for_feedback(created.id)[0].comment == (
        "Reviewer confirmed the new box is closer, but still slightly tall."
    )
    assert store.list_notes_for_feedback(created.id)[0].note == (
        "Narrowed the annotation box and regenerated the review sample."
    )
    exported = {record["id"]: record for record in store.export_records()}
    assert exported[created.id]["reviewer_comments"][0]["comment"] == (
        "Reviewer confirmed the new box is closer, but still slightly tall."
    )
    assert exported[created.id]["agent_notes"][0]["note"] == "Narrowed the annotation box and regenerated the review sample."


def test_feedback_store_persists_task_audit_status(tmp_path: Path) -> None:
    store = FeedbackStore(tmp_path / "feedback.sqlite")

    default = store.get_task_audit(domain="pages", scene_id="workspace", task_id=TASK_ID)
    assert default.manual_pass is False
    assert default.review_pass is False
    assert default.passed_count == 0

    updated = store.update_task_audit(
        domain="pages",
        scene_id="workspace",
        task_id=TASK_ID,
        prompt_pass=True,
        image_pass=True,
        annotation_pass=True,
        distribution_pass=True,
        code_review_pass=True,
        taxonomy_review_pass=True,
        solve_rate_pass=True,
        updated_by="reviewer",
    )

    assert updated.manual_pass is True
    assert updated.review_pass is True
    assert updated.code_review_pass is True
    assert updated.taxonomy_review_pass is True
    assert updated.review_count == 6
    assert updated.passed_count == 7
    assert store.task_audits_by_task()[f"pages/workspace/{TASK_ID}"].updated_by == "reviewer"

    illustration_review = store.update_illustration_object_review(
        item_id="top_down_pixel_rpg__pixel_rpg__tree__oak",
        renderer_style="top_down_pixel_rpg",
        category="plant",
        object_type="tree",
        label="tree · oak",
        decision="improve",
        notes="Canopy needs stronger isometric lighting.",
        updated_by="reviewer",
    )
    assert illustration_review.decision == "improve"
    assert illustration_review.notes == "Canopy needs stronger isometric lighting."
    assert store.get_illustration_object_review(
        item_id="top_down_pixel_rpg__pixel_rpg__tree__oak"
    ).updated_by == "reviewer"
    assert "top_down_pixel_rpg__pixel_rpg__tree__oak" in store.illustration_object_reviews_by_item()
    assert "Canopy needs stronger isometric lighting." in store.export_illustration_object_reviews_jsonl()


def test_feedback_store_migrates_task_audit_code_review_gate(tmp_path: Path) -> None:
    db_path = tmp_path / "feedback.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE task_audit (
                domain TEXT NOT NULL,
                scene_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                prompt_pass INTEGER NOT NULL DEFAULT 0,
                image_pass INTEGER NOT NULL DEFAULT 0,
                annotation_pass INTEGER NOT NULL DEFAULT 0,
                distribution_pass INTEGER NOT NULL DEFAULT 0,
                solve_rate_pass INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (domain, scene_id, task_id)
            )
            """
        )

    store = FeedbackStore(db_path)
    migrated = store.update_task_audit(
        domain="pages",
        scene_id="workspace",
        task_id=TASK_ID,
        prompt_pass=True,
        image_pass=True,
        annotation_pass=True,
        distribution_pass=True,
        code_review_pass=True,
        taxonomy_review_pass=True,
        solve_rate_pass=True,
    )

    assert migrated.code_review_pass is True
    assert migrated.taxonomy_review_pass is True
    assert migrated.review_pass is True
    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(task_audit)").fetchall()}
    assert "code_review_pass" in columns
    assert "taxonomy_review_pass" in columns


def test_illustration_object_review_uses_variant_pixel_footprints() -> None:
    from trace.review_app.illustration_object_review import _pixel_footprint_for_item, illustration_object_review_item

    chicken = illustration_object_review_item("isometric_pixel_rpg__pixel_rpg__domestic_animal__chicken")
    cow = illustration_object_review_item("isometric_pixel_rpg__pixel_rpg__domestic_animal__cow")
    cart = illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__cart__default")
    crop_row = illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__crop_row__default")
    carrot = illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__vegetable_patch__carrot")
    pumpkin = illustration_object_review_item("isometric_pixel_rpg__pixel_rpg__vegetable_patch__pumpkin")
    shelf = illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__shelf__mixed")
    produce_bin = illustration_object_review_item("isometric_pixel_rpg__pixel_rpg__produce_bin__fruit")
    cave_entrance = illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__cave_entrance__default")
    ore_vein = illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__ore_vein__default")
    rail_track = illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__rail_track__horizontal")
    stairs = illustration_object_review_item("isometric_pixel_rpg__pixel_rpg__stairs__down")
    long_table = illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__table__long")
    square_table = illustration_object_review_item("isometric_pixel_rpg__pixel_rpg__table__square")
    double_bed = illustration_object_review_item("isometric_pixel_rpg__pixel_rpg__bed__double")
    single_bed = illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__bed__single")
    fireplace = illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__fireplace__lit")
    room_divider = illustration_object_review_item("isometric_pixel_rpg__pixel_rpg__room_divider__screen")

    assert chicken is not None
    assert cow is not None
    assert cart is not None
    assert crop_row is not None
    assert carrot is not None
    assert pumpkin is not None
    assert shelf is not None
    assert produce_bin is not None
    assert cave_entrance is not None
    assert ore_vein is not None
    assert rail_track is not None
    assert stairs is not None
    assert long_table is not None
    assert square_table is not None
    assert double_bed is not None
    assert single_bed is not None
    assert fireplace is not None
    assert room_divider is not None
    assert _pixel_footprint_for_item(chicken) == (1, 1)
    assert _pixel_footprint_for_item(cow) == (2, 1)
    assert _pixel_footprint_for_item(cart) == (2, 1)
    assert _pixel_footprint_for_item(crop_row) == (4, 1)
    assert _pixel_footprint_for_item(carrot) == (1, 1)
    assert _pixel_footprint_for_item(pumpkin) == (1, 1)
    assert _pixel_footprint_for_item(shelf) == (3, 1)
    assert _pixel_footprint_for_item(produce_bin) == (2, 1)
    assert _pixel_footprint_for_item(cave_entrance) == (4, 3)
    assert _pixel_footprint_for_item(ore_vein) == (1, 1)
    assert _pixel_footprint_for_item(rail_track) == (1, 1)
    assert _pixel_footprint_for_item(stairs) == (2, 2)
    assert _pixel_footprint_for_item(long_table) == (3, 2)
    assert _pixel_footprint_for_item(square_table) == (2, 2)
    assert _pixel_footprint_for_item(double_bed) == (3, 3)
    assert _pixel_footprint_for_item(single_bed) == (2, 3)
    assert _pixel_footprint_for_item(fireplace) == (2, 1)
    assert _pixel_footprint_for_item(room_divider) == (3, 1)


def test_pixel_rpg_object_review_inventory_matches_between_rpg_renderers() -> None:
    from trace.review_app.illustration_object_review import illustration_object_review_item, illustration_object_review_items

    def normalized_items(renderer_style: str) -> set[tuple[str, str]]:
        return {
            (item.object_type, item.variant_label or "default")
            for item in illustration_object_review_items()
            if item.renderer_style == renderer_style and item.source == "pixel_rpg_shared"
        }

    top_down_items = normalized_items("top_down_pixel_rpg")
    isometric_items = normalized_items("isometric_pixel_rpg")

    assert top_down_items == isometric_items
    assert all(object_type not in {"bottle", "bowl", "mug"} for object_type, _ in top_down_items)
    assert ("chair", "up") not in top_down_items
    assert illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__chair__up") is None
    assert illustration_object_review_item("isometric_pixel_rpg__pixel_rpg__chair__up") is None
    assert illustration_object_review_item("top_down_pixel_rpg__pixel_rpg__bowl__default") is None
    assert illustration_object_review_item("isometric_pixel_rpg__pixel_rpg__mug__default") is None


def test_review_app_requires_token_and_serves_index(tmp_path: Path) -> None:
    fastapi = __import__("pytest").importorskip("fastapi")
    assert fastapi is not None
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        enforce_migration_registry=False,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    client = TestClient(app)

    assert client.get("/api/index").status_code == 401
    response = client.get("/api/index", headers={"Authorization": "Bearer secret"})
    assert response.status_code == 200
    assert response.json()["sample_count"] == 1

    page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert page.status_code == 200
    assert "TRACE Review" in page.text


def test_review_app_supports_proxy_base_url(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    asset_image = root / "assets" / "fonts" / "readout_pool_v0" / "readout_pool_v0_spritesheet.png"
    asset_image.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (180, 80), (255, 255, 255)).save(asset_image)
    _write_json(
        root / "assets" / "fonts" / "readout_pool_v0" / "readout_pool_v0_spritesheet_manifest.json",
        {"title": "Readout font pool"},
    )
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        enforce_migration_registry=False,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
        base_url="/proxy/7860",
    )
    client = TestClient(app)

    redirect = client.get("/", follow_redirects=False)
    assert redirect.status_code == 303
    assert redirect.headers["location"] == "/proxy/7860/login?next=/"

    page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert page.status_code == 200
    assert 'href="/proxy/7860/domains/pages"' in page.text
    assert 'href="/proxy/7860/static/app.css?v=' in page.text
    assert 'src="/proxy/7860/static/app.js?v=' in page.text
    assert 'window.TRACE_REVIEW_BASE = "/proxy/7860";' in page.text
    assert "Review root: review/task-reviews" in page.text
    assert str(root.resolve()) not in page.text
    assert 'class="site-header"' in page.text
    assert 'class="sidebar"' not in page.text
    assert 'data-suggest-url="/proxy/7860/api/search-suggest"' in page.text
    assert 'href="/proxy/7860/resources"' in page.text
    assert 'href="/proxy/7860/three-d/objects"' not in page.text
    assert 'href="/proxy/7860/illustrations/objects"' not in page.text
    assert 'href="/proxy/7860/issues"' in page.text
    assert 'class="theme-switch"' in page.text
    assert 'data-theme-choice="dark"' in page.text
    assert 'data-theme-choice="light"' in page.text

    resources_page = client.get("/resources", headers={"Authorization": "Bearer secret"})
    assert resources_page.status_code == 200
    assert 'href="/proxy/7860/three-d/objects"' in resources_page.text
    assert 'href="/proxy/7860/illustrations/objects"' in resources_page.text

    suggestions = client.get("/api/search-suggest?q=workspace", headers={"Authorization": "Bearer secret"})
    assert suggestions.status_code == 200
    results = suggestions.json()["results"]
    assert any(
        result["type"] == "scene" and result["url"] == "/proxy/7860/domains/pages/scenes/workspace"
        for result in results
    )
    assert any(result["type"] == "task" and result["label"] == TASK_ID for result in results)

    task_page = client.get(
        f"/domains/pages/scenes/workspace/tasks/{TASK_ID}",
        headers={"Authorization": "Bearer secret"},
    )
    assert task_page.status_code == 200
    assert 'data-preview-root data-active-view="rows"' in task_page.text
    assert 'data-preview-switch="rows"' in task_page.text
    assert 'data-preview-switch="images"' in task_page.text
    assert 'class="sample-row-list"' in task_page.text
    assert 'class="sample-row"' in task_page.text
    assert 'data-task-feedback-toggle' in task_page.text
    assert 'data-task-feedback-form' in task_page.text
    assert "<h2>Taxonomy</h2>" in task_page.text
    assert "Program Code" in task_page.text
    assert "select_labeled_control(toolbar_palette, target_role=palette_control)" in task_page.text
    assert "Answer Schema" in task_page.text
    assert "option_letter" in task_page.text
    assert "Annotation Schema" in task_page.text
    assert "bbox_set" in task_page.text
    assert "<h2>Distribution</h2>" in task_page.text
    assert "PASS" in task_page.text
    assert "mode single_sample" in task_page.text
    assert "max_answer_frequency" in task_page.text
    assert "min_unique_answers" in task_page.text
    assert "max_five_bin_frequency" not in task_page.text
    assert "reported_not_gated_numeric_answers" not in task_page.text
    assert "Query Collection" not in task_page.text
    assert "<th>Generated</th>" not in task_page.text
    assert 'name="distribution_pass" value="1" checked' in task_page.text
    assert f"/media/{next(iter(app.state.review.index().samples.values())).media_id}?v=" in task_page.text
    assert "Include annotation." in task_page.text
    assert "<p data-selectable-text>" in task_page.text
    assert 'class="sample-row-main" href="/proxy/7860/samples/' in task_page.text
    assert 'draggable="false"' in task_page.text
    assert "answer" in task_page.text
    assert "annotation" in task_page.text

    sample = next(iter(app.state.review.index().samples.values()))
    image_task_page = client.get(
        f"/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images",
        headers={"Authorization": "Bearer secret"},
    )
    assert image_task_page.status_code == 200
    assert 'data-preview-root data-active-view="images"' in image_task_page.text
    assert 'class="image-only-grid"' in image_task_page.text
    assert 'class="image-only-card"' in image_task_page.text
    assert 'class="image-pair-card"' in image_task_page.text
    assert "Original" in image_task_page.text
    assert "Annotation" in image_task_page.text
    assert f"/proxy/7860/media/{sample.media_id}?v=" in image_task_page.text
    assert f"/proxy/7860/overlay/{sample.uid}.png?v=" in image_task_page.text
    assert 'class="sample-row-list"' in image_task_page.text
    assert f"/domains/pages/scenes/workspace/tasks/{TASK_ID}/queries/lookup?view=images" in image_task_page.text

    task_feedback = client.post(
        f"/domains/pages/scenes/workspace/tasks/{TASK_ID}/issues",
        headers={"Authorization": "Bearer secret"},
        data={
            "comment": "Task-level note.",
            "next": f"/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images",
        },
        follow_redirects=False,
    )
    assert task_feedback.status_code == 303
    assert task_feedback.headers["location"] == f"/proxy/7860/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images"
    task_thread = app.state.review.feedback.list_task_feedback(domain="pages", scene_id="workspace", task_id=TASK_ID)[0]
    assert task_thread.comment == "Task-level note."

    sample_feedback = app.state.review.feedback.add_feedback(
        sample=sample,
        comment="Annotation should be tighter.",
        category="annotation",
    )
    feedback_note = client.post(
        f"/issues/{sample_feedback.id}/notes",
        headers={"Authorization": "Bearer secret"},
        data={
            "note": "Adjusted annotation projection and regenerated the task review.",
            "author": "agent",
            "next": f"/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images",
        },
        follow_redirects=False,
    )
    assert feedback_note.status_code == 303
    assert feedback_note.headers["location"] == f"/proxy/7860/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images"
    assert app.state.review.feedback.list_notes_for_feedback(sample_feedback.id)[0].note == (
        "Adjusted annotation projection and regenerated the task review."
    )
    feedback_comment = client.post(
        f"/issues/{sample_feedback.id}/comments",
        headers={"Authorization": "Bearer secret"},
        data={
            "comment": "Reviewer follow-up should stay on the same thread.",
            "author": "reviewer",
            "next": f"/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images",
        },
        follow_redirects=False,
    )
    assert feedback_comment.status_code == 303
    assert feedback_comment.headers["location"] == f"/proxy/7860/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images"
    assert app.state.review.feedback.list_comments_for_feedback(sample_feedback.id)[0].comment == (
        "Reviewer follow-up should stay on the same thread."
    )

    image_task_page = client.get(
        f"/domains/pages/scenes/workspace/tasks/{TASK_ID}?view=images",
        headers={"Authorization": "Bearer secret"},
    )
    assert "Annotation should be tighter." in image_task_page.text
    assert "Adjusted annotation projection and regenerated the task review." in image_task_page.text
    assert "Reviewer follow-up should stay on the same thread." in image_task_page.text
    assert "Continue task issue" in image_task_page.text
    assert f'action="/proxy/7860/issues/{task_thread.id}/comments"' in image_task_page.text
    assert "Continue existing sample issue" in image_task_page.text
    assert f'action="/proxy/7860/issues/{sample_feedback.id}/comments"' in image_task_page.text
    assert f'href="/proxy/7860/issues/{sample_feedback.id}"' in image_task_page.text
    assert "Brief repair note after changing code or artifacts" not in image_task_page.text
    assert f'id="sample-{sample.uid}"' in image_task_page.text

    sample_page = client.get(f"/samples/{sample.uid}", headers={"Authorization": "Bearer secret"})
    assert sample_page.status_code == 200
    assert 'class="sample-image-pair"' in sample_page.text
    assert f"/proxy/7860/media/{sample.media_id}?v=" in sample_page.text
    assert f"/proxy/7860/overlay/{sample.uid}.png?v=" in sample_page.text
    assert "Reviewer follow-up should stay on the same thread." in sample_page.text
    assert "Adjusted annotation projection and regenerated the task review." in sample_page.text
    assert "Brief repair note after changing code or artifacts" not in sample_page.text

    feedback_redirect = client.get("/feedback", headers={"Authorization": "Bearer secret"}, follow_redirects=False)
    assert feedback_redirect.status_code == 303
    assert feedback_redirect.headers["location"] == "/proxy/7860/issues"

    feedback_queue = client.get("/issues", headers={"Authorization": "Bearer secret"})
    assert feedback_queue.status_code == 200
    assert "Issue Work Queue" in feedback_queue.text
    assert "review items with open issues" in feedback_queue.text
    assert 'class="feedback-domain-filter"' in feedback_queue.text
    assert 'href="/proxy/7860/issues?domain=pages"' in feedback_queue.text
    assert "Task-level note." in feedback_queue.text
    assert "Annotation should be tighter." in feedback_queue.text
    assert "Missing manual audit: prompt, image, annotation" not in feedback_queue.text
    assert "Missing manual audit: prompt, image, annotation, distribution" not in feedback_queue.text
    assert "Solve-rate manual checkbox not checked" not in feedback_queue.text
    assert "Automated solve-rate missing" not in feedback_queue.text
    assert f'href="/proxy/7860/samples/{sample.uid}"' in feedback_queue.text
    assert f'href="/proxy/7860/issues/{sample_feedback.id}"' in feedback_queue.text
    assert (
        f'href="/proxy/7860/domains/pages/scenes/workspace/tasks/{TASK_ID}'
        f'/queries/{sample.query_id}?view=rows#sample-{sample.uid}"'
    ) in feedback_queue.text

    filtered_feedback_queue = client.get("/issues?domain=pages", headers={"Authorization": "Bearer secret"})
    assert filtered_feedback_queue.status_code == 200
    assert "Task-level note." in filtered_feedback_queue.text
    assert "Annotation should be tighter." in filtered_feedback_queue.text
    assert 'value="/issues?domain=pages"' in filtered_feedback_queue.text

    empty_feedback_queue = client.get("/issues?domain=charts", headers={"Authorization": "Bearer secret"})
    assert empty_feedback_queue.status_code == 200
    assert "No open issues." in empty_feedback_queue.text
    assert "Task-level note." not in empty_feedback_queue.text

    app.state.review.feedback.add_task_feedback(
        domain="games",
        scene_id="stale_scene",
        task_id="task_games__stale_scene__missing_task",
        comment="Stale game feedback.",
        category="rendering",
    )
    stale_feedback_queue = client.get("/issues?domain=games", headers={"Authorization": "Bearer secret"})
    assert stale_feedback_queue.status_code == 200
    assert "Stale game feedback." in stale_feedback_queue.text
    assert "not in current index" in stale_feedback_queue.text
    assert "No open issues." not in stale_feedback_queue.text

    detail_redirect = client.get(f"/feedback/{sample_feedback.id}", headers={"Authorization": "Bearer secret"}, follow_redirects=False)
    assert detail_redirect.status_code == 303
    assert detail_redirect.headers["location"] == f"/proxy/7860/issues/{sample_feedback.id}"

    feedback_thread = client.get(f"/issues/{sample_feedback.id}", headers={"Authorization": "Bearer secret"})
    assert feedback_thread.status_code == 200
    assert "Issue Thread" in feedback_thread.text
    assert "Reviewer Follow-Ups" in feedback_thread.text
    assert "Repair Notes" in feedback_thread.text
    assert "Reviewer issue" in feedback_thread.text
    assert "Reviewer follow-up" in feedback_thread.text
    assert "Agent repair note" in feedback_thread.text
    assert "Annotation should be tighter." in feedback_thread.text
    assert "Reviewer follow-up should stay on the same thread." in feedback_thread.text
    assert "Adjusted annotation projection and regenerated the task review." in feedback_thread.text
    assert feedback_thread.text.index("Annotation should be tighter.") < feedback_thread.text.index(
        "Reviewer follow-up should stay on the same thread."
    )
    assert feedback_thread.text.index("Annotation should be tighter.") < feedback_thread.text.index(
        "Adjusted annotation projection and regenerated the task review."
    )
    assert "Open source" in feedback_thread.text
    assert (
        f'href="/proxy/7860/domains/pages/scenes/workspace/tasks/{TASK_ID}'
        f'/queries/{sample.query_id}?view=rows#sample-{sample.uid}"'
    ) in feedback_thread.text
    assert f'href="/proxy/7860/samples/{sample.uid}"' in feedback_thread.text
    assert f"/proxy/7860/media/{sample.media_id}?v=" in feedback_thread.text
    assert f"/proxy/7860/overlay/{sample.uid}.png?v=" in feedback_thread.text

    resolve = client.post(
        f"/issues/{sample_feedback.id}",
        headers={"Authorization": "Bearer secret"},
        data={"status": "resolved", "next": "/issues"},
        follow_redirects=False,
    )
    assert resolve.status_code == 303
    assert resolve.headers["location"] == "/proxy/7860/issues"
    feedback_queue = client.get("/issues", headers={"Authorization": "Bearer secret"})
    assert "Task-level note." in feedback_queue.text
    assert "Annotation should be tighter." not in feedback_queue.text

    assets_redirect = client.get("/domains/assets", headers={"Authorization": "Bearer secret"}, follow_redirects=False)
    assert assets_redirect.status_code == 303
    assert assets_redirect.headers["location"] == "/proxy/7860/resources"

    resources_page = client.get("/resources", headers={"Authorization": "Bearer secret"})
    assert resources_page.status_code == 200
    assert 'class="resource-tabbar"' in resources_page.text
    assert 'data-resource-tabs' in resources_page.text
    assert "data-resource-page-tabs" in resources_page.text
    assert 'href="#resource-collection-1"' in resources_page.text
    assert 'id="resource-collection-1"' in resources_page.text
    assert "<small>1 img</small>" not in resources_page.text
    assert 'data-tooltip="fonts / readout pool v0 · 1 image(s), 1 manifest(s)"' in resources_page.text
    assert 'aria-label="fonts / readout pool v0, 1 image(s), 1 manifest(s)"' in resources_page.text
    assert 'title="fonts / readout pool v0' not in resources_page.text
    assert "fonts / readout pool v0" in resources_page.text
    assert "readout_pool_v0_spritesheet.png" in resources_page.text
    assert "readout_pool_v0_spritesheet_manifest.json" in resources_page.text
    assert re.search(r'<a href="/proxy/7860/resources/media/[^"]+" target="_blank" rel="noopener noreferrer">', resources_page.text)
    assert re.search(r'<a class="pill" href="/proxy/7860/resources/media/[^"]+" target="_blank" rel="noopener noreferrer">', resources_page.text)
    media_match = re.search(r'href="/proxy/7860/resources/media/([^"]+)"', resources_page.text)
    assert media_match is not None
    resource_media = client.get(f"/resources/media/{media_match.group(1)}", headers={"Authorization": "Bearer secret"})
    assert resource_media.status_code == 200
    assert resource_media.headers["cache-control"] == "no-cache"

    illustration_objects = client.get(
        "/illustrations/objects?renderer=top_down_pixel_rpg&category=plant",
        headers={"Authorization": "Bearer secret"},
    )
    assert illustration_objects.status_code == 200
    assert "Illustration Object Review" in illustration_objects.text
    assert "data-illustration-object-tabs" in illustration_objects.text
    assert 'class="illustration-object-grid"' in illustration_objects.text
    assert "Top-down RPG" in illustration_objects.text
    assert "Plants" in illustration_objects.text
    assert "top_down_pixel_rpg__pixel_rpg__tree__oak" in illustration_objects.text
    assert 'name="decision" value="approve"' in illustration_objects.text
    assert 'name="decision" value="remove"' in illustration_objects.text
    assert 'name="decision" value="improve"' in illustration_objects.text
    assert 'textarea name="notes"' in illustration_objects.text
    assert re.search(r'src="/proxy/7860/illustrations/objects/previews/[^"]+\.png"', illustration_objects.text)

    vegetable_objects = client.get(
        "/illustrations/objects?renderer=top_down_pixel_rpg&category=vegetable",
        headers={"Authorization": "Bearer secret"},
    )
    assert vegetable_objects.status_code == 200
    assert "Vegetables" in vegetable_objects.text
    for vegetable_style in ("carrot", "cabbage", "corn", "tomato", "pumpkin"):
        assert f"top_down_pixel_rpg__pixel_rpg__vegetable_patch__{vegetable_style}" in vegetable_objects.text

    resource_objects = client.get(
        "/illustrations/objects?renderer=top_down_pixel_rpg&category=resource",
        headers={"Authorization": "Bearer secret"},
    )
    assert resource_objects.status_code == 200
    assert "Resources" in resource_objects.text
    assert "top_down_pixel_rpg__pixel_rpg__ore_vein__default" in resource_objects.text
    assert "top_down_pixel_rpg__pixel_rpg__crystal_cluster__default" in resource_objects.text

    route_objects = client.get(
        "/illustrations/objects?renderer=top_down_pixel_rpg&category=route_feature",
        headers={"Authorization": "Bearer secret"},
    )
    assert route_objects.status_code == 200
    assert "Route Features" in route_objects.text
    assert "top_down_pixel_rpg__pixel_rpg__rail_track__horizontal" in route_objects.text
    assert "top_down_pixel_rpg__pixel_rpg__stairs__down" in route_objects.text

    vegetable_preview = client.get(
        "/illustrations/objects/previews/top_down_pixel_rpg__pixel_rpg__vegetable_patch__carrot.png",
        headers={"Authorization": "Bearer secret"},
    )
    assert vegetable_preview.status_code == 200
    assert vegetable_preview.headers["content-type"] == "image/png"
    assert len(vegetable_preview.content) > 200

    preview = client.get(
        "/illustrations/objects/previews/top_down_pixel_rpg__pixel_rpg__tree__oak.png",
        headers={"Authorization": "Bearer secret"},
    )
    assert preview.status_code == 200
    assert preview.headers["cache-control"] == "no-cache"
    assert preview.headers["content-type"] == "image/png"
    assert len(preview.content) > 200

    illustration_review = client.post(
        "/illustrations/objects/reviews/top_down_pixel_rpg__pixel_rpg__tree__oak",
        headers={"Authorization": "Bearer secret"},
        data={
            "decision": "improve",
            "notes": "Oak canopy needs clearer highlight.",
            "updated_by": "reviewer",
            "next": "/illustrations/objects?renderer=top_down_pixel_rpg&category=plant#tree",
        },
        follow_redirects=False,
    )
    assert illustration_review.status_code == 303
    assert illustration_review.headers["location"] == (
        "/proxy/7860/illustrations/objects?renderer=top_down_pixel_rpg&category=plant#tree"
    )
    saved_illustration_review = app.state.review.feedback.get_illustration_object_review(
        item_id="top_down_pixel_rpg__pixel_rpg__tree__oak"
    )
    assert saved_illustration_review.decision == "improve"
    assert saved_illustration_review.notes == "Oak canopy needs clearer highlight."

    improve_filtered_objects = client.get(
        "/illustrations/objects?renderer=top_down_pixel_rpg&category=plant&decision=improve",
        headers={"Authorization": "Bearer secret"},
    )
    assert improve_filtered_objects.status_code == 200
    assert "All decisions" in improve_filtered_objects.text
    assert "Oak canopy needs clearer highlight." in improve_filtered_objects.text
    assert "top_down_pixel_rpg__pixel_rpg__tree__oak" in improve_filtered_objects.text
    assert "top_down_pixel_rpg__pixel_rpg__tree__pine" not in improve_filtered_objects.text
    assert (
        'href="/proxy/7860/illustrations/objects?renderer=top_down_pixel_rpg&amp;category=plant&amp;decision=improve"'
        in improve_filtered_objects.text
    )

    illustration_ajax_review = client.post(
        "/illustrations/objects/reviews/top_down_pixel_rpg__pixel_rpg__tree__oak",
        headers={
            "Authorization": "Bearer secret",
            "Accept": "application/json",
            "X-Requested-With": "fetch",
        },
        data={
            "decision": "approve",
            "notes": "Highlight is acceptable after review.",
            "updated_by": "reviewer",
        },
        follow_redirects=False,
    )
    assert illustration_ajax_review.status_code == 200
    assert illustration_ajax_review.json()["decision"] == "approve"
    assert illustration_ajax_review.json()["status_label"] == "Approved"

    illustration_objects = client.get(
        "/illustrations/objects?renderer=top_down_pixel_rpg&category=plant",
        headers={"Authorization": "Bearer secret"},
    )
    assert "Highlight is acceptable after review." in illustration_objects.text
    assert 'class="illustration-object-status approve"' in illustration_objects.text

    illustration_reviews_api = client.get(
        "/api/illustrations/objects/reviews?renderer=top_down_pixel_rpg&category=plant",
        headers={"Authorization": "Bearer secret"},
    )
    assert illustration_reviews_api.status_code == 200
    assert illustration_reviews_api.json()["summary"]["approve"] == 1

    illustration_multipart_review = client.post(
        "/illustrations/objects/reviews/top_down_pixel_rpg__pixel_rpg__tree__oak",
        headers={
            "Authorization": "Bearer secret",
            "Accept": "application/json",
            "X-Requested-With": "fetch",
        },
        files={
            "decision": (None, "improve"),
            "notes": (None, "Browser FormData save should keep notes."),
            "updated_by": (None, "reviewer"),
        },
        follow_redirects=False,
    )
    assert illustration_multipart_review.status_code == 200
    assert illustration_multipart_review.json()["decision"] == "improve"
    saved_multipart_illustration_review = app.state.review.feedback.get_illustration_object_review(
        item_id="top_down_pixel_rpg__pixel_rpg__tree__oak"
    )
    assert saved_multipart_illustration_review.decision == "improve"
    assert saved_multipart_illustration_review.notes == "Browser FormData save should keep notes."

    media = client.get(f"/media/{sample.media_id}", headers={"Authorization": "Bearer secret"})
    assert media.status_code == 200
    assert media.headers["cache-control"] == "no-cache"

    static_asset = client.get("/static/app.css")
    assert static_asset.status_code == 200
    assert ":root" in static_asset.text


def test_review_app_browses_taxonomy_audit_with_feedback(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    _write_taxonomy_audit_fixture(tmp_path)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        enforce_migration_registry=False,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
    )
    client = TestClient(app)

    redirect = client.get("/taxonomy", follow_redirects=False)
    assert redirect.status_code == 303
    assert redirect.headers["location"] == "/taxonomy/contract-v0"

    overview = client.get("/taxonomy/contract-v0?domain=pages")
    assert overview.status_code == 200
    assert "Taxonomy Audit" in overview.text
    assert "current tasks" in overview.text
    assert "base program contracts" in overview.text
    assert "approved decisions" in overview.text
    assert "0/2" in overview.text
    assert "argument metadata rows" in overview.text
    assert "argument rows needing review" in overview.text
    assert "2→3" in overview.text
    assert "Pages Taxonomy" in overview.text
    assert "/taxonomy/contract-v0/tree" in overview.text
    assert TASK_ID in overview.text
    assert "task_pages__workspace__control_text_label" in overview.text
    assert "/media/" in overview.text

    tree_page = client.get("/taxonomy/contract-v0/tree?domain=pages")
    assert tree_page.status_code == 200
    assert "Taxonomy Tree" in tree_page.text
    assert "selection" in tree_page.text
    assert "selection.option_match" in tree_page.text
    assert "task_pages__workspace__control_text_label" in tree_page.text

    task_page = client.get(f"/taxonomy/contract-v0/domains/pages/scenes/workspace/tasks/{TASK_ID}")
    assert task_page.status_code == 200
    assert "Program Taxonomy" in task_page.text
    assert "selection / selection.option_match / control_text_label" in task_page.text
    assert "base: select_option(reference_or_rule, candidate_options); scene=workspace; scope=control_text_label" in task_page.text
    assert "Current → Updated Mapping" in task_page.text
    assert "lookup" in task_page.text
    assert "Contract-v0 keeps the narrower visible-control objective." in task_page.text
    assert "What label is on the target control?" in task_page.text
    assert "annotation" in task_page.text
    assert f"/domains/pages/scenes/workspace/tasks/{TASK_ID}" in task_page.text
    assert "Decision Approval" in task_page.text
    assert "not approved" in task_page.text
    assert "Approve and Next" in task_page.text
    assert "Arguments / Variant Axes" in task_page.text
    assert "target_control" in task_page.text
    assert "visible_candidate_options" in task_page.text

    next_task_path = f"/taxonomy/contract-v0/domains/pages/scenes/workspace/tasks/{TASK_ID_2}"
    approve_response = client.post(
        f"/taxonomy/contract-v0/domains/pages/scenes/workspace/tasks/{TASK_ID}/decision-review",
        data={
            "action": "approve_next",
            "notes": "Boundary decision reviewed.",
            "updated_by": "tester",
            "next": f"/taxonomy/contract-v0/domains/pages/scenes/workspace/tasks/{TASK_ID}",
            "next_pending": next_task_path,
        },
        follow_redirects=False,
    )
    assert approve_response.status_code == 303
    assert approve_response.headers["location"] == next_task_path
    decision_review = app.state.review.feedback.get_taxonomy_decision_review(
        round_id="contract_v0_reanalysis",
        domain="pages",
        scene_id="workspace",
        task_id=TASK_ID,
    )
    assert decision_review.approved is True
    assert decision_review.notes == "Boundary decision reviewed."

    overview = client.get("/taxonomy/contract-v0?domain=pages")
    assert "1/2" in overview.text
    task_page = client.get(f"/taxonomy/contract-v0/domains/pages/scenes/workspace/tasks/{TASK_ID}")
    assert "approved" in task_page.text

    feedback_response = client.post(
        f"/taxonomy/contract-v0/domains/pages/scenes/workspace/tasks/{TASK_ID}/issues",
        data={
            "query_id": "lookup",
            "comment": "This query should stay with the original task.",
            "next": f"/taxonomy/contract-v0/domains/pages/scenes/workspace/tasks/{TASK_ID}",
        },
        follow_redirects=False,
    )
    assert feedback_response.status_code == 303
    assert feedback_response.headers["location"] == f"/taxonomy/contract-v0/domains/pages/scenes/workspace/tasks/{TASK_ID}"
    stored = app.state.review.feedback.list_task_feedback(domain="pages", scene_id="workspace", task_id=TASK_ID)[0]
    assert stored.comment == "[taxonomy:contract_v0_reanalysis query=lookup] This query should stay with the original task."
    decision_review = app.state.review.feedback.get_taxonomy_decision_review(
        round_id="contract_v0_reanalysis",
        domain="pages",
        scene_id="workspace",
        task_id=TASK_ID,
    )
    assert decision_review.approved is False

    task_page = client.get(f"/taxonomy/contract-v0/domains/pages/scenes/workspace/tasks/{TASK_ID}")
    assert "This query should stay with the original task." in task_page.text
    assert "1 open issue" in task_page.text


def test_review_app_shows_and_updates_task_audit_status(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    _write_accepted_solve_status(root)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        enforce_migration_registry=False,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    client = TestClient(app)

    domain_page = client.get("/domains/pages", headers={"Authorization": "Bearer secret"})
    assert domain_page.status_code == 200
    assert "<label>scenes</label>" in domain_page.text
    assert "review passed" in domain_page.text
    assert "solve rate passed" in domain_page.text
    assert "<th>Task Progress</th>" in domain_page.text
    assert "task-progress-cell" in domain_page.text
    assert 'href="/issues?domain=pages"' in domain_page.text
    assert 'aria-label="Open issues for pages"' in domain_page.text
    assert "Review 0/1" in domain_page.text
    assert "Solve rate 0/1" in domain_page.text
    assert "Completed 0/1" not in domain_page.text

    old_gate_update = client.patch(
        f"/api/tasks/pages/workspace/{TASK_ID}/audit",
        headers={"Authorization": "Bearer secret"},
        json={
            "prompt_pass": True,
            "image_pass": True,
            "annotation_pass": True,
            "distribution_pass": True,
            "solve_rate_pass": True,
            "updated_by": "reviewer",
        },
    )
    assert old_gate_update.status_code == 200
    assert old_gate_update.json()["status"]["complete"] is False
    assert old_gate_update.json()["status"]["review_pass"] is False
    assert old_gate_update.json()["status"]["code_review_pass"] is False
    assert old_gate_update.json()["status"]["taxonomy_review_pass"] is False
    assert old_gate_update.json()["status"]["review_count"] == 4
    assert old_gate_update.json()["status"]["review_total"] == 6

    update = client.patch(
        f"/api/tasks/pages/workspace/{TASK_ID}/audit",
        headers={"Authorization": "Bearer secret"},
        json={
            "prompt_pass": True,
            "image_pass": True,
            "annotation_pass": True,
            "distribution_pass": True,
            "code_review_pass": True,
            "taxonomy_review_pass": True,
            "solve_rate_pass": True,
            "updated_by": "reviewer",
        },
    )
    assert update.status_code == 200
    assert update.json()["status"]["complete"] is True
    assert update.json()["status"]["review_pass"] is True
    assert update.json()["status"]["code_review_pass"] is True
    assert update.json()["status"]["taxonomy_review_pass"] is True
    assert update.json()["status"]["solve_rate_pass"] is True
    assert update.json()["status"]["solve_artifact_pass"] is True

    domain_page = client.get("/domains/pages", headers={"Authorization": "Bearer secret"})
    assert "Review 1/1" in domain_page.text
    assert "Solve rate 1/1" in domain_page.text
    assert "Completed 1/1" not in domain_page.text

    scene_page = client.get("/domains/pages/scenes/workspace", headers={"Authorization": "Bearer secret"})
    assert scene_page.status_code == 200
    assert "review done" in scene_page.text
    assert "6/6" in scene_page.text
    assert "solve rate done" in scene_page.text


def test_review_app_supports_scene_review_and_scene_level_issues(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        enforce_migration_registry=False,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer secret"}
    sample = next(iter(app.state.review.index().samples.values()))

    scene_page = client.get("/domains/pages/scenes/workspace", headers=headers)
    assert scene_page.status_code == 200
    assert "Open Scene Review" in scene_page.text
    assert "Migration Tests" in scene_page.text
    assert "Taxonomy Review" in scene_page.text
    assert "3 passed" in scene_page.text
    assert "taxonomy contract audit passed" in scene_page.text
    assert 'href="/domains/pages/scenes/workspace/review"' in scene_page.text
    assert "<label>open scene issues</label>" in scene_page.text

    review_page = client.get("/domains/pages/scenes/workspace/review", headers=headers)
    assert review_page.status_code == 200
    assert "Scene Review: workspace" in review_page.text
    assert "<label>queries</label>" in review_page.text
    assert "<label>preview cards</label>" in review_page.text
    assert "missing sample" in review_page.text
    assert f'href="/samples/{sample.uid}"' in review_page.text
    assert f'src="/media/{sample.media_id}?v=' in review_page.text
    assert "What label is on the target control?" in review_page.text
    assert 'action="/domains/pages/scenes/workspace/issues"' in review_page.text

    response = client.post(
        "/domains/pages/scenes/workspace/issues",
        headers=headers,
        data={
            "comment": "Scene grammar needs broader visual coverage.",
            "category": "rendering",
            "severity": "issue",
            "author": "reviewer",
            "next": "/domains/pages/scenes/workspace/review",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/domains/pages/scenes/workspace/review"

    review_page = client.get("/domains/pages/scenes/workspace/review", headers=headers)
    assert "Scene grammar needs broader visual coverage." in review_page.text
    assert "<label>open scene issues</label>" in review_page.text

    queue = client.get("/issues?domain=pages", headers=headers)
    assert queue.status_code == 200
    assert "Scene grammar needs broader visual coverage." in queue.text
    assert "scene-level" in queue.text
    assert 'href="/domains/pages/scenes/workspace/review"' in queue.text

    scene_feedback = app.state.review.feedback.list_scene_feedback(domain="pages", scene_id="workspace")
    assert len(scene_feedback) == 1
    assert scene_feedback[0].task_id == ""
    assert scene_feedback[0].sample_uid == ""
    assert app.state.review.feedback.counts_by_task() == {}

    detail = client.get(f"/issues/{scene_feedback[0].id}", headers=headers)
    assert detail.status_code == 200
    assert "<dt>scope</dt><dd>scene</dd>" in detail.text
    assert "Open scene review" in detail.text
    assert 'href="/domains/pages/scenes/workspace/review#scene-feedback"' in detail.text


def test_review_app_warns_when_review_artifacts_are_stale(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        enforce_migration_registry=False,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    client = TestClient(app)

    page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert page.status_code == 200
    assert "Review artifacts changed." not in page.text

    touched = root / "pages" / "workspace" / TASK_ID / "manifest.json"
    future = time.time() + 5
    os.utime(touched, (future, future))
    app.state.review._stale_cache_until_ns = 0

    stale_page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert "Review artifacts changed." in stale_page.text
    assert "Start an index reload before inspecting generated samples." in stale_page.text

    reload_response = client.post("/api/reload", headers={"Authorization": "Bearer secret"})
    assert reload_response.status_code == 200
    deadline = time.time() + 5
    while time.time() < deadline:
        status = client.get("/api/reload/status", headers={"Authorization": "Bearer secret"}).json()
        if not status["in_progress"]:
            break
        time.sleep(0.01)
    assert status["status"] == "succeeded"
    fresh_page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert "Review artifacts changed." not in fresh_page.text


def test_review_app_reload_keeps_serving_current_index_while_rebuilding(tmp_path: Path, monkeypatch) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient
    import trace.review_app.server as review_server

    root = _make_review_fixture(tmp_path)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        enforce_migration_registry=False,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    client = TestClient(app)
    current_index = app.state.review.index()
    started = threading.Event()
    release = threading.Event()

    def slow_build_review_index(*args, **kwargs):
        started.set()
        if not release.wait(timeout=5):
            raise TimeoutError("test did not release index rebuild")
        return current_index

    monkeypatch.setattr(review_server, "build_review_index", slow_build_review_index)

    began = time.monotonic()
    reload_response = client.post("/api/reload", headers={"Authorization": "Bearer secret"})
    elapsed = time.monotonic() - began
    assert reload_response.status_code == 200
    assert elapsed < 1.0
    assert reload_response.json()["in_progress"] is True
    assert started.wait(timeout=2)

    page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert page.status_code == 200
    assert "Index reload running." in page.text

    running = client.get("/api/reload/status", headers={"Authorization": "Bearer secret"}).json()
    assert running["status"] == "running"
    assert running["in_progress"] is True

    release.set()
    deadline = time.time() + 5
    while time.time() < deadline:
        finished = client.get("/api/reload/status", headers={"Authorization": "Bearer secret"}).json()
        if not finished["in_progress"]:
            break
        time.sleep(0.01)
    assert finished["status"] == "succeeded"


def test_review_app_scene_reload_updates_one_scene_without_full_rebuild(tmp_path: Path, monkeypatch) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient
    import trace.review_app.server as review_server

    root = _make_review_fixture(tmp_path)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        enforce_migration_registry=False,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    client = TestClient(app)
    assert next(iter(app.state.review.index().samples.values())).prompt == "What label is on the target control?"

    data_path = root / "pages" / "workspace" / TASK_ID / "data" / "lookup" / "0000.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    payload["prompt"] = "Updated prompt from scoped reload."
    _write_json(data_path, payload)

    def fail_full_rebuild(*args, **kwargs):
        raise AssertionError("scene-scoped reload should not call full build_review_index")

    monkeypatch.setattr(review_server, "build_review_index", fail_full_rebuild)

    reload_response = client.post(
        "/api/reload/scene/pages/workspace",
        headers={"Authorization": "Bearer secret"},
    )
    assert reload_response.status_code == 200
    assert reload_response.json()["scope"] == "scene:pages/workspace"

    deadline = time.time() + 5
    while time.time() < deadline:
        finished = client.get("/api/reload/status", headers={"Authorization": "Bearer secret"}).json()
        if not finished["in_progress"]:
            break
        time.sleep(0.01)
    assert finished["status"] == "succeeded"
    assert finished["scope"] == "scene:pages/workspace"
    assert next(iter(app.state.review.index().samples.values())).prompt == "Updated prompt from scoped reload."


def test_review_app_deferred_initial_index_binds_before_index_scan(tmp_path: Path, monkeypatch) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient
    import trace.review_app.server as review_server

    root = _make_review_fixture(tmp_path)
    from trace.review_app.server import create_app

    original_build_review_index = review_server.build_review_index
    started = threading.Event()
    release = threading.Event()

    def slow_build_review_index(*args, **kwargs):
        started.set()
        if not release.wait(timeout=5):
            raise TimeoutError("test did not release deferred index rebuild")
        return original_build_review_index(*args, **kwargs)

    monkeypatch.setattr(review_server, "build_review_index", slow_build_review_index)

    began = time.monotonic()
    app = create_app(
        review_root=root,
        enforce_migration_registry=False,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
        defer_initial_index=True,
    )
    elapsed = time.monotonic() - began
    assert elapsed < 1.0
    assert started.wait(timeout=2)

    client = TestClient(app)
    page = client.get("/", headers={"Authorization": "Bearer secret"})
    assert page.status_code == 200
    assert "Index reload running." in page.text
    assert "Review index is loading in the background." in page.text

    release.set()
    deadline = time.time() + 5
    while time.time() < deadline:
        finished = client.get("/api/reload/status", headers={"Authorization": "Bearer secret"}).json()
        if not finished["in_progress"]:
            break
        time.sleep(0.01)
    assert finished["status"] == "succeeded"


def test_review_app_adds_feedback_via_api(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        enforce_migration_registry=False,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    sample_uid = next(iter(app.state.review.index().samples))
    client = TestClient(app)

    response = client.post(
        f"/api/samples/{sample_uid}/feedback",
        headers={"Authorization": "Bearer secret"},
        json={"comment": "Prompt wording is confusing.", "category": "prompt", "severity": "issue"},
    )

    assert response.status_code == 200
    assert response.json()["feedback"]["category"] == "prompt"
    listed = client.get(f"/api/samples/{sample_uid}/feedback", headers={"Authorization": "Bearer secret"})
    assert listed.json()["feedback"][0]["comment"] == "Prompt wording is confusing."


def test_review_app_reviews_three_d_object_profiles(tmp_path: Path) -> None:
    __import__("pytest").importorskip("fastapi")
    from fastapi.testclient import TestClient

    root = _make_review_fixture(tmp_path)
    from trace.review_app.server import create_app

    app = create_app(
        review_root=root,
        enforce_migration_registry=False,
        repo_root=tmp_path,
        feedback_db=tmp_path / "feedback.sqlite",
        token="secret",
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer secret"}
    profile_id = "object_scene:spatial_small_shape:sphere"
    encoded_profile_id = "object_scene%3Aspatial_small_shape%3Asphere"

    page = client.get("/three-d/objects", headers=headers)
    assert page.status_code == 200
    assert "3D Object Review" in page.text
    assert "Object Scene" in page.text
    assert profile_id in page.text
    assert 'href="/resources"' in page.text
    assert "data-three-d-object-tabs" in page.text
    assert 'class="three-d-object-grid"' in page.text
    assert 'data-three-d-review-form' in page.text
    assert 'data-three-d-object-status' in page.text
    assert 'href="/three-d/objects?decision=improve"' in page.text

    preview = client.get(f"/three-d/objects/previews/{encoded_profile_id}.png", headers=headers)
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"
    assert len(preview.content) > 1000

    saved = client.post(
        f"/three-d/objects/reviews/{encoded_profile_id}",
        headers=headers,
        data={
            "decision": "improve",
            "notes": "Needs a clearer silhouette.",
            "updated_by": "reviewer",
            "next": "/three-d/objects",
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303
    assert saved.headers["location"] == "/three-d/objects"

    api = client.get("/api/three-d/objects/reviews", headers=headers)
    assert api.status_code == 200
    payload = api.json()
    assert payload["summary"]["improve"] == 1
    review = next(record for record in payload["reviews"] if record["profile_id"] == profile_id)
    assert review["decision"] == "improve"
    assert review["notes"] == "Needs a clearer silhouette."

    improve_filtered = client.get(
        "/three-d/objects?group=object_scene__object_scene_shape&decision=improve",
        headers=headers,
    )
    assert improve_filtered.status_code == 200
    assert "All decisions" in improve_filtered.text
    assert "Needs a clearer silhouette." in improve_filtered.text
    assert profile_id in improve_filtered.text
    assert (
        'href="/three-d/objects?group=object_scene__object_scene_shape&amp;decision=improve"'
        in improve_filtered.text
    )

    ajax_saved = client.post(
        f"/three-d/objects/reviews/{encoded_profile_id}",
        headers={
            "Authorization": "Bearer secret",
            "Accept": "application/json",
            "X-Requested-With": "fetch",
        },
        data={
            "decision": "remove",
            "notes": "Remove from the current object pool.",
            "updated_by": "reviewer",
        },
        follow_redirects=False,
    )
    assert ajax_saved.status_code == 200
    assert ajax_saved.json()["decision"] == "remove"
    assert ajax_saved.json()["status_label"] == "Remove"

    multipart_saved = client.post(
        f"/three-d/objects/reviews/{encoded_profile_id}",
        headers=headers,
        files={
            "decision": (None, "approve"),
            "notes": (None, "Browser FormData save should keep 3D notes."),
            "updated_by": (None, "reviewer"),
            "next": (None, "/three-d/objects"),
        },
        follow_redirects=False,
    )
    assert multipart_saved.status_code == 303
    assert multipart_saved.headers["location"] == "/three-d/objects"
    multipart_review = app.state.review.feedback.get_three_d_object_review(profile_id=profile_id)
    assert multipart_review.decision == "approve"
    assert multipart_review.notes == "Browser FormData save should keep 3D notes."


def test_review_app_launcher_defaults_to_proxy_base_url(monkeypatch) -> None:
    import scripts.run_review_app as run_review_app

    monkeypatch.delenv("TRACE_REVIEW_APP_BASE_URL", raising=False)
    assert run_review_app._resolve_base_url(None, port=7860) == "/proxy/7860"
    assert run_review_app._resolve_base_url(None, port=7877) == "/proxy/7877"

    monkeypatch.setenv("TRACE_REVIEW_APP_BASE_URL", "/custom/{port}")
    assert run_review_app._resolve_base_url(None, port=7860) == "/custom/7860"

    assert run_review_app._resolve_base_url("", port=7860) == ""
    assert run_review_app._resolve_base_url("none", port=7860) == ""
    assert run_review_app._resolve_base_url("/review", port=7860) == "/review"
