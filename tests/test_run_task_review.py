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


def test_staged_task_publish_keeps_live_artifacts_until_swap(tmp_path: Path) -> None:
    out_root = tmp_path / "review" / "task-reviews"
    final_task_dir = out_root / "dummy" / "review" / "task_dummy__review__query"
    final_task_dir.mkdir(parents=True)
    (final_task_dir / "old.txt").write_text("live", encoding="utf-8")

    stage_task_dir = review._task_stage_dir(
        out_root=out_root,
        final_task_dir=final_task_dir,
        task_id="task_dummy__review__query",
    )
    review._prepare_staged_task_dir(final_task_dir, stage_task_dir)
    assert (final_task_dir / "old.txt").read_text(encoding="utf-8") == "live"

    (stage_task_dir / "old.txt").write_text("staged", encoding="utf-8")
    (stage_task_dir / "random_review_100.json").write_text("{}", encoding="utf-8")
    (stage_task_dir / "distribution_review.json").write_text("{}", encoding="utf-8")

    review._validate_staged_task_artifacts(
        out_root=out_root,
        final_task_dir=final_task_dir,
        stage_task_dir=stage_task_dir,
        task_id="task_dummy__review__query",
        require_random=True,
        require_distribution=True,
        require_inspection=False,
    )
    assert (final_task_dir / "old.txt").read_text(encoding="utf-8") == "live"

    review._publish_staged_task_dir(
        out_root=out_root,
        final_task_dir=final_task_dir,
        stage_task_dir=stage_task_dir,
        domain="dummy",
        scene_id="review",
    )

    assert (final_task_dir / "old.txt").read_text(encoding="utf-8") == "staged"
    assert (final_task_dir / "random_review_100.json").exists()
    assert not stage_task_dir.exists()


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


def test_review_generation_refuses_unregistered_review_target_scene(tmp_path: Path, monkeypatch) -> None:
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
            task_ids=["task_pages__workspace__control_label"],
            out_root=tmp_path / "review" / "task-reviews",
        )


def _write_scene_gate_statuses(
    out_root: Path,
    *,
    domain: str,
    scene_id: str,
    task_ids: list[str],
    include_manual: bool = True,
    include_taxonomy: bool = True,
    include_source_layout: bool = True,
    scalar_annotation_checked: bool | None = True,
) -> None:
    """Write passing source-layout gate sidecars for review-runner tests."""

    scene_dir = out_root / domain / scene_id
    scene_dir.mkdir(parents=True, exist_ok=True)
    if include_manual:
        (scene_dir / "manual_code_audit_status.json").write_text(
            json.dumps(
                {
                    "schema": "trace_scene_manual_code_audit_status_v1",
                    "domain": domain,
                    "scene_id": scene_id,
                    "passed": True,
                    "status": "passed",
                    "summary": "role-boundary audit passed",
                }
            ),
            encoding="utf-8",
        )
    if include_taxonomy:
        (scene_dir / "taxonomy_review_status.json").write_text(
            json.dumps(
                {
                    "schema": "trace_scene_taxonomy_review_status_v1",
                    "domain": domain,
                    "scene_id": scene_id,
                    "passed": True,
                    "status": "passed",
                    "summary": "taxonomy contract audit passed",
                    "task_ids": list(task_ids),
                    "checklist": {
                        "task_contracts_stable": True,
                        "program_codes_concrete": True,
                        "query_ids_semantic": True,
                        "prompt_taxonomy_aligned": True,
                        "annotation_contracts_stable": True,
                        "all_query_branches_smoked": True,
                        **(
                            {}
                            if scalar_annotation_checked is None
                            else {"scalar_annotation_checked": bool(scalar_annotation_checked)}
                        ),
                    },
                }
            ),
            encoding="utf-8",
        )
    if include_source_layout:
        (scene_dir / "source_layout_test_status.json").write_text(
            json.dumps(
                {
                    "schema": "trace_scene_source_layout_test_status_v1",
                    "domain": domain,
                    "scene_id": scene_id,
                    "passed": True,
                    "status": "passed",
                    "summary": "scene-scoped source-layout checks passed",
                    "command": (
                        f"TRACE_SCENE_PACKAGE_REVIEW_SCENE={domain}/{scene_id} "
                        "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q "
                        "tests/test_review_app.py tests/test_run_task_review.py "
                        "tests/test_source_layout_contracts.py"
                    ),
                    "test_files": [
                        "tests/test_review_app.py",
                        "tests/test_run_task_review.py",
                        "tests/test_source_layout_contracts.py",
                    ],
                }
            ),
            encoding="utf-8",
        )


def test_review_generation_refuses_missing_taxonomy_review_for_registered_scene(
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
    out_root = tmp_path / "review" / "task-reviews"
    _write_scene_gate_statuses(
        out_root,
        domain="charts",
        scene_id="bar_3d",
        task_ids=["task_charts__bar_3d__category_total_value"],
        include_taxonomy=False,
    )

    with pytest.raises(ValueError, match="taxonomy review passes"):
        review._validate_tasks_may_write_review_artifacts(
            task_ids=["task_charts__bar_3d__category_total_value"],
            out_root=out_root,
        )


def test_review_generation_refuses_missing_source_layout_test_status_for_registered_scene(
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
    out_root = tmp_path / "review" / "task-reviews"
    _write_scene_gate_statuses(
        out_root,
        domain="charts",
        scene_id="bar_3d",
        task_ids=["task_charts__bar_3d__category_total_value"],
        include_source_layout=False,
    )

    with pytest.raises(ValueError, match="scene-scoped source-layout checks pass"):
        review._validate_tasks_may_write_review_artifacts(
            task_ids=["task_charts__bar_3d__category_total_value"],
            out_root=out_root,
        )


def test_review_generation_refuses_taxonomy_status_without_requested_task(
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
        "audit_scene_package_review_target",
        lambda domain, scene_id: {"passed": True, "failures": []},
    )
    out_root = tmp_path / "review" / "task-reviews"
    _write_scene_gate_statuses(
        out_root,
        domain="charts",
        scene_id="bar_3d",
        task_ids=["task_charts__bar_3d__category_total_gap_value"],
    )

    with pytest.raises(ValueError, match="missing requested task ids"):
        review._validate_tasks_may_write_review_artifacts(
            task_ids=["task_charts__bar_3d__category_total_value"],
            out_root=out_root,
        )


def test_review_generation_refuses_taxonomy_status_without_scalar_annotation_check(
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
        "audit_scene_package_review_target",
        lambda domain, scene_id: {"passed": True, "failures": []},
    )
    out_root = tmp_path / "review" / "task-reviews"
    _write_scene_gate_statuses(
        out_root,
        domain="charts",
        scene_id="bar_3d",
        task_ids=["task_charts__bar_3d__category_total_value"],
        scalar_annotation_checked=None,
    )

    with pytest.raises(ValueError, match="scalar_annotation_checked=true"):
        review._validate_tasks_may_write_review_artifacts(
            task_ids=["task_charts__bar_3d__category_total_value"],
            out_root=out_root,
        )


def test_review_generation_refuses_false_scalar_annotation_check(
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
        "audit_scene_package_review_target",
        lambda domain, scene_id: {"passed": True, "failures": []},
    )
    out_root = tmp_path / "review" / "task-reviews"
    _write_scene_gate_statuses(
        out_root,
        domain="charts",
        scene_id="bar_3d",
        task_ids=["task_charts__bar_3d__category_total_value"],
        scalar_annotation_checked=False,
    )

    with pytest.raises(ValueError, match="scalar_annotation_checked=true"):
        review._validate_tasks_may_write_review_artifacts(
            task_ids=["task_charts__bar_3d__category_total_value"],
            out_root=out_root,
        )


def test_review_generation_refuses_remaining_scalar_annotation_candidate(
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
        "audit_scene_package_review_target",
        lambda domain, scene_id: {"passed": True, "failures": []},
    )
    monkeypatch.setattr(
        review,
        "scalar_annotation_review_failures_for_tasks",
        lambda **kwargs: ["charts/bar_3d -> scalar candidate still uses one-item point_set"],
    )
    out_root = tmp_path / "review" / "task-reviews"
    _write_scene_gate_statuses(
        out_root,
        domain="charts",
        scene_id="bar_3d",
        task_ids=["task_charts__bar_3d__category_total_value"],
    )

    with pytest.raises(ValueError, match="scalar candidate"):
        review._validate_tasks_may_write_review_artifacts(
            task_ids=["task_charts__bar_3d__category_total_value"],
            out_root=out_root,
        )


def test_review_generation_allows_passing_scene_source_layout_gates_for_registered_scene(
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
        "audit_scene_package_review_target",
        lambda domain, scene_id: {"passed": True, "failures": []},
    )
    out_root = tmp_path / "review" / "task-reviews"
    _write_scene_gate_statuses(
        out_root,
        domain="charts",
        scene_id="bar_3d",
        task_ids=["task_charts__bar_3d__category_total_value"],
    )

    review._validate_tasks_may_write_review_artifacts(
        task_ids=["task_charts__bar_3d__category_total_value"],
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
        "audit_scene_package_review_target",
        lambda domain, scene_id: {
            "passed": False,
            "failures": [
                "charts/bar_3d: category_total_value.py and category_total_gap_value.py look duplicated"
            ],
        },
    )
    out_root = tmp_path / "review" / "task-reviews"
    _write_scene_gate_statuses(
        out_root,
        domain="charts",
        scene_id="bar_3d",
        task_ids=["task_charts__bar_3d__category_total_value"],
    )

    with pytest.raises(ValueError, match="automated source-layout source audit failed"):
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


def test_task_review_distribution_does_not_relax_declared_small_categorical_support() -> None:
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

    assert report["checks"]["min_unique_answers"]["threshold"] == 4
    assert report["checks"]["min_unique_answers"]["pass"] is False
    assert report["checks"]["max_answer_frequency"]["threshold"] == (1.0 / 3.0)
    assert report["checks"]["max_answer_frequency"]["pass"] is False
    assert report["pass"] is False
