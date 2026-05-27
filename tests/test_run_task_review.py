"""Regression tests for task-review workflow helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

from scripts import check_task_answer_distribution as distribution_review
from scripts import run_task_review as review
from trace.core.types import TaskComplexity, TypedValue
from trace.tasks.base import TaskOutput


class _DummyVariantTask:
    """Minimal task stub used to verify inspection workbook variant routing."""

    task_id = "task_dummy__review__query"
    domain = "dummy"
    task_group = "review"

    def __init__(self) -> None:
        self.calls: list[tuple[int, dict[str, object]]] = []

    def generate(self, instance_seed: int, *, params: dict[str, object], max_attempts: int) -> TaskOutput:
        self.calls.append((int(instance_seed), dict(params)))
        query_id = str(params.get("query_id", "default"))
        image = Image.new("RGB", (64, 64), color=(255, 255, 255))
        return TaskOutput(
            prompt=f"prompt for {query_id}",
            answer_gt=TypedValue(type="integer", value=1),
            evidence_gt=TypedValue(type="bbox_set", value=[[8, 8, 24, 24]]),
            image=image,
            image_id=f"img_{instance_seed}",
            trace_payload={"projected_evidence": {}},
            complexity=TaskComplexity(complexity_score=1.0, complexity_components={}),
            task_versions={},
            query_id=query_id,
            prompt_variants={
                "answer_only": '{"answer":1}',
                "answer_and_evidence": '{"evidence":[[8,8,24,24]],"answer":1}',
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
    task_dir = review._resolve_task_review_dir(
        out_root=out_root,
        task_id="task_dummy__review__query",
        task_obj=dummy_task,
    )
    assert task_dir == out_root / "dummy" / "review" / "task_dummy__review__query"


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
