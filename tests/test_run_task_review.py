"""Regression tests for task-review workflow helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
import pytest

from scripts import check_task_answer_distribution as distribution_review
from scripts import run_task_review as review
from trace.core import task_review_distribution
from trace.core.task_review_paths import infer_task_domain, resolve_task_review_dir
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput


class _DummyVariantTask:
    """Minimal task stub used to verify inspection workbook variant routing."""

    task_id = "task_dummy__review__query"
    domain = "dummy"
    scene_id = "review"

    def __init__(self) -> None:
        self.calls: list[tuple[int, dict[str, object]]] = []

    def generate(self, instance_seed: int, *, params: dict[str, object], max_attempts: int) -> TaskOutput:
        self.calls.append((int(instance_seed), dict(params)))
        query_id = str(params.get("query_id", "default"))
        image = Image.new("RGB", (64, 64), color=(255, 255, 255))
        return TaskOutput(
            prompt=f"prompt for {query_id}",
            answer_gt=TypedValue(type="integer", value=1),
            annotation_gt=TypedValue(type="bbox_set", value=[[8, 8, 24, 24]]),
            image=image,
            image_id=f"img_{instance_seed}",
            trace_payload={"projected_annotation": {}},
            task_versions={},
            query_id=query_id,
            prompt_variants={
                "answer_only": '{"answer":1}',
                "answer_and_annotation": '{"annotation":[[8,8,24,24]],"answer":1}',
            },
        )


def test_build_inspection_rows_passes_requested_query_id(
    tmp_path: Path,
    monkeypatch,
) -> None:
    out_root = tmp_path / "task-reviews"
    task_dir = out_root / "dummy" / "task_dummy__review__query"
    out_root.mkdir(parents=True, exist_ok=True)
    task_dir.mkdir(parents=True, exist_ok=True)

    dummy_task = _DummyVariantTask()
    monkeypatch.setattr(review, "create_task", lambda task_id: dummy_task)

    manifest = review._build_inspection_rows(
        task_id="task_dummy__review__query",
        out_root=out_root,
        task_dir=task_dir,
        seed_rows_by_query_id={
            "query_alpha": [{"instance_seed": 101}],
            "query_beta": [{"instance_seed": 202}],
        },
        max_attempts_per_instance=10,
    )

    assert dummy_task.calls == [
        (101, {"query_id": "query_alpha"}),
        (202, {"query_id": "query_beta"}),
    ]
    assert manifest["query_ids"] == {"query_alpha": 1, "query_beta": 1}

    alpha_payload = json.loads((task_dir / "data" / "query_alpha" / "0000.json").read_text(encoding="utf-8"))
    beta_payload = json.loads((task_dir / "data" / "query_beta" / "0000.json").read_text(encoding="utf-8"))
    assert alpha_payload["query_id"] == "query_alpha"
    assert beta_payload["query_id"] == "query_beta"


def test_resolve_task_review_dir_uses_domain_scene_scoped_layout() -> None:
    dummy_task = _DummyVariantTask()
    out_root = Path("/tmp/task-reviews")
    task_dir = resolve_task_review_dir(
        out_root=out_root,
        task_id="task_dummy__review__query",
        task_obj=dummy_task,
    )
    assert task_dir == out_root / "dummy" / "review" / "task_dummy__review__query"


def test_review_path_helpers_parse_public_three_d_task_ids() -> None:
    out_root = Path("/tmp/task-reviews")
    task_id = "task_three_d__object_scene_3d__named_object_count"

    assert infer_task_domain(task_id) == "three_d"
    assert resolve_task_review_dir(out_root=out_root, task_id=task_id) == (
        out_root / "three_d" / "object_scene_3d" / task_id
    )


def test_review_cli_defaults_to_all_visible_cpus(monkeypatch) -> None:
    monkeypatch.setattr(review.os, "cpu_count", lambda: 12)
    monkeypatch.setattr(sys, "argv", ["run_task_review.py"])
    args = review._parse_cli()
    assert int(args.workers) == 12


def test_distribution_cli_defaults_to_all_visible_cpus(monkeypatch) -> None:
    monkeypatch.setattr(distribution_review.os, "cpu_count", lambda: 12)
    monkeypatch.setattr(sys, "argv", ["check_task_answer_distribution.py"])
    args = distribution_review._parse_cli()
    assert int(args.workers) == 12


def test_review_cli_uses_shared_distribution_helpers() -> None:
    assert review._random_collector is task_review_distribution.random_collector
    assert review._answer_collector is task_review_distribution.answer_collector
    assert review._build_random_review_report is task_review_distribution.build_random_review_report
    assert review._build_distribution_review_report is task_review_distribution.build_distribution_review_report


def test_review_generation_refuses_unregistered_migration_review_scene(tmp_path: Path, monkeypatch) -> None:
    dummy_task = _DummyVariantTask()
    monkeypatch.setattr(review, "create_task", lambda task_id: dummy_task)
    monkeypatch.setattr(
        review,
        "resolve_task_taxonomy",
        lambda *args, **kwargs: SimpleNamespace(domain="geometry", scene_id="unregistered_review_scene"),
    )

    with pytest.raises(ValueError, match="not centrally registered"):
        review._validate_tasks_may_write_review_artifacts(
            task_ids=["task_geometry__unregistered_review_scene__arc_angle_value"],
            out_root=tmp_path / "review" / "task-reviews",
        )


def test_review_generation_refuses_missing_manual_code_audit_for_registered_scene(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dummy_task = _DummyVariantTask()
    monkeypatch.setattr(review, "create_task", lambda task_id: dummy_task)
    monkeypatch.setattr(
        review,
        "resolve_task_taxonomy",
        lambda *args, **kwargs: SimpleNamespace(domain="pages", scene_id="workspace"),
    )
    monkeypatch.setattr(review, "is_scene_package_review_target_scene", lambda domain, scene_id: True)

    with pytest.raises(ValueError, match="manual code/role-boundary audit"):
        review._validate_tasks_may_write_review_artifacts(
            task_ids=["task_pages__workspace__toolbar_palette_control_label"],
            out_root=tmp_path / "review" / "task-reviews",
        )


def test_review_generation_allows_passing_manual_code_audit_for_registered_scene(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dummy_task = _DummyVariantTask()
    monkeypatch.setattr(review, "create_task", lambda task_id: dummy_task)
    monkeypatch.setattr(
        review,
        "resolve_task_taxonomy",
        lambda *args, **kwargs: SimpleNamespace(domain="pages", scene_id="workspace"),
    )
    monkeypatch.setattr(review, "is_scene_package_review_target_scene", lambda domain, scene_id: True)
    monkeypatch.setattr(
        review,
        "audit_scene_package_review_candidate",
        lambda domain, scene_id: {"passed": True, "failures": []},
    )
    out_root = tmp_path / "review" / "task-reviews"
    audit_path = out_root / "pages" / "workspace" / "manual_code_audit_status.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps({"passed": True}), encoding="utf-8")

    review._validate_tasks_may_write_review_artifacts(
        task_ids=["task_pages__workspace__toolbar_palette_control_label"],
        out_root=out_root,
    )


def test_review_generation_refuses_failed_automated_scene_source_audit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dummy_task = _DummyVariantTask()
    monkeypatch.setattr(review, "create_task", lambda task_id: dummy_task)
    monkeypatch.setattr(
        review,
        "resolve_task_taxonomy",
        lambda *args, **kwargs: SimpleNamespace(domain="charts", scene_id="bar_3d"),
    )
    monkeypatch.setattr(review, "is_scene_package_review_target_scene", lambda domain, scene_id: True)
    monkeypatch.setattr(
        review,
        "audit_scene_package_review_candidate",
        lambda domain, scene_id: {
            "passed": False,
            "failures": [
                "charts/bar_3d: category_total_value.py and category_total_gap_value.py look duplicated"
            ],
        },
    )
    out_root = tmp_path / "review" / "task-reviews"
    audit_path = out_root / "charts" / "bar_3d" / "manual_code_audit_status.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps({"passed": True}), encoding="utf-8")

    with pytest.raises(ValueError, match="automated scene-package source audit failed"):
        review._validate_tasks_may_write_review_artifacts(
            task_ids=["task_charts__bar_3d__category_total_value"],
            out_root=out_root,
        )


def test_task_review_distribution_collector_records_axes_and_replay_params() -> None:
    output = TaskOutput(
        prompt="prompt",
        answer_gt=TypedValue(type="integer", value=7),
        annotation_gt=TypedValue(type="point_set", value=[[10, 10]]),
        image=Image.new("RGB", (32, 32), color=(255, 255, 255)),
        image_id="img",
        trace_payload={
            "execution_trace": {
                "difficulty": "easy",
                "difficulty_probabilities": {"easy": 2, "hard": 1},
                "internal_query_id": "internal_branch",
            },
            "query_spec": {
                "params": {
                    "scene_variant": "bar",
                    "query_id_probabilities": {"alpha": 1, "beta": 1},
                    "scene_variant_support": ["bar", "line"],
                },
            },
        },
        task_versions={},
        scene_id="review",
        query_id="default",
    )

    row = task_review_distribution.random_collector(output, 123)

    assert row["instance_seed"] == 123
    assert row["answer_value"] == 7
    assert row["sampling_axes"]["difficulty"]["observed"] == "easy"
    assert row["sampling_axes"]["difficulty"]["expected_probabilities"] == {
        "easy": 2 / 3,
        "hard": 1 / 3,
    }
    assert row["sampling_axes"]["query_id"]["expected_probabilities"] == {"alpha": 0.5, "beta": 0.5}
    assert row["generation_params"] == {"scene_variant": "bar", "query_id": "internal_branch"}


def test_task_review_distribution_allows_declared_small_categorical_support() -> None:
    rows = []
    for label, count in (("one_to_one", 33), ("one_to_many", 34), ("optional_many", 33)):
        rows.extend(
            {
                "answer_type": "string",
                "answer_value": label,
                "answer_support": ["one_to_many", "optional_many", "one_to_one"],
            }
            for _ in range(count)
        )

    report = task_review_distribution.evaluate_rows(rows)

    assert report["checks"]["min_unique_answers"]["threshold"] == 3
    assert report["checks"]["min_unique_answers"]["pass"] is True
    assert report["checks"]["max_answer_frequency"]["threshold"] > (1.0 / 3.0)
    assert report["checks"]["max_answer_frequency"]["pass"] is True
    assert report["pass"] is True
