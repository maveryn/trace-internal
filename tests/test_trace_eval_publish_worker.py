from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.run_trace_eval_publish_worker as worker
from scripts.final25_hf_archive_lib import ArchiveDaemon, emit_slice_ready
from scripts.trace_eval_suite import load_trace_eval_suite


SOURCE_RUN = "private-3b-campaign"
PUBLIC_RUN = "qwen25vl3b-comparison-v1"
SOURCE_MODEL = "private-qwen25vl3b-step500"
PUBLIC_MODEL = "trace-qwen2.5-vl-3b"
SOURCE_REVISION = "a" * 40
PUBLIC_REVISION = "b" * 40
REPOSITORY_ID = "example/trace-qwen2.5-vl-3b"
REPOSITORY_REVISION = "c" * 40
JUDGE_REVISION = "d" * 40
CODE_HASH = "e" * 64
CAMPAIGN_HASH = "f" * 64
DATASET_REVISION = "trace-eval-dataset-v1:" + "1" * 64
TOKEN = "hf_synthetic_private_token"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _record(stage: str) -> dict[str, object]:
    common: dict[str, object] = {
        "source_index": "sample-0",
        "source_ordinal": 0,
        "source_row_hash": _sha("source"),
        "request_hash": _sha(stage),
        "question": "Question?",
        "ground_truth": "A",
    }
    if stage == "generation":
        return common | {
            "source_row": {"index": "sample-0"},
            "prompt": "Question?",
            "model_response": "A",
            "sampling": {"temperature": 0.6},
            "finish_reason": "stop",
            "usage": {},
        }
    if stage == "extraction":
        return common | {
            "model_response": "A",
            "judge_prompt": "Extract.",
            "judge_response": "A",
            "normalized_extraction": "A",
            "retries": [],
        }
    return common | {
        "prediction": "A",
        "score": 1.0,
        "scorer": "exact",
        "excluded": False,
    }


def _emit(
    config: worker.WorkerConfig,
    *,
    stage: str = "generation",
    run_id: str = SOURCE_RUN,
    benchmark: str | None = None,
    seed: int = 42,
) -> Path:
    suite = load_trace_eval_suite()
    return emit_slice_ready(
        config.archive_spool_root,
        stage=stage,
        run_id=run_id,
        model=f"{REPOSITORY_ID}@{REPOSITORY_REVISION}",
        model_revision=SOURCE_REVISION,
        model_slug=SOURCE_MODEL,
        seed=seed,
        benchmark=benchmark or suite.benchmark_keys[0],
        dataset_alias="Synthetic",
        dataset_split="test",
        dataset_revision=DATASET_REVISION,
        records=[_record(stage)],
        provenance={
            "trace_git_commit": "2" * 40,
            "vlmevalkit_git_commit": "3" * 40,
            "contract_version": f"synthetic-{stage}-v1",
            "campaign_config_hash": CAMPAIGN_HASH,
            "final25_code_hash": CODE_HASH,
        },
    )


def _config(tmp_path: Path, **changes: object) -> worker.WorkerConfig:
    token_file = tmp_path / "hf-token.txt"
    token_file.write_text(TOKEN + "\n", encoding="utf-8")
    token_file.chmod(0o600)
    values: dict[str, object] = {
        "campaign_root": tmp_path / "campaign",
        "score_root": tmp_path / "campaign" / "scoring",
        "archive_spool_root": tmp_path / "campaign" / "hf_archive",
        "dataset_manifest": tmp_path / "dataset.json",
        "vlmeval_root": tmp_path / "vlmeval",
        "work_root": tmp_path / "publish-state",
        "lock_root": tmp_path / "worker-locks",
        "source_run_id": SOURCE_RUN,
        "public_run_id": PUBLIC_RUN,
        "seeds": (42,),
        "models": (
            worker.ModelConfig(
                source_model_id=SOURCE_MODEL,
                local_model_path="/models/private-qwen25vl3b-step500",
                source_revision=SOURCE_REVISION,
                model_id=PUBLIC_MODEL,
                model_revision=PUBLIC_REVISION,
                display_name="TRACE Qwen2.5-VL 3B",
                repository_id=REPOSITORY_ID,
                repository_revision=REPOSITORY_REVISION,
            ),
        ),
        "judge": {
            "source_model_id": "qwen3-32b-judge",
            "model_id": "Qwen/Qwen3-32B",
            "model_revision": JUDGE_REVISION,
        },
        "token_file": token_file,
        "paper_repo": "maveryn/trace-eval-runs",
        "revision": "main",
        "poll_seconds": 0.0,
        "settle_seconds": 0.0,
        "timeout_seconds": 1.0,
        "verification_grace_seconds": 0.1,
        "upload_attempts": 2,
        "retry_base_seconds": 0.0,
        "retry_cap_seconds": 0.0,
        "batch_size": 48,
        "allow_upload": True,
        "confirmation": f"UPLOAD maveryn/trace-eval-runs/{PUBLIC_RUN}",
    }
    values.update(changes)
    return worker.WorkerConfig(**values)


def _complete_coverage(config: worker.WorkerConfig) -> worker.Coverage:
    return worker.Coverage(
        ready=config.expected_slices,
        expected=config.expected_slices,
        missing=(),
        fingerprint="4" * 64,
        campaign_config_hash=CAMPAIGN_HASH,
        dataset_revision=DATASET_REVISION,
        code_hash=CODE_HASH,
        descriptor_paths=(),
    )


def _complete_reports() -> dict[str, dict[str, object]]:
    return {
        phase: {
            "complete": True,
            "completed_slices": 24,
            "expected_slices": 24,
            "incomplete": [],
        }
        for phase in ("generation", "score")
    }


def test_ready_scan_is_exact_and_ignores_other_runs(tmp_path: Path) -> None:
    config = _config(tmp_path)
    suite = load_trace_eval_suite()
    _emit(config)
    _emit(config, run_id="unrelated-campaign")

    coverage = worker.inspect_ready_coverage(config, suite)
    assert coverage.ready == 1
    assert coverage.expected == 72
    assert len(coverage.missing) == 71
    assert coverage.campaign_config_hash == CAMPAIGN_HASH

    _emit(config, benchmark="unexpected-benchmark")
    with pytest.raises(worker.PublishWorkerError, match="unexpected ready slice"):
        worker.inspect_ready_coverage(config, suite)


def test_incremental_builder_resumes_registered_ready_row(tmp_path: Path) -> None:
    config = _config(tmp_path)
    descriptor_path = _emit(config)
    unrelated_path = _emit(config, run_id="unrelated-campaign")
    daemon = ArchiveDaemon(spool_root=config.archive_spool_root, api=object())
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    unrelated = json.loads(unrelated_path.read_text(encoding="utf-8"))
    daemon.ledger.register(descriptor["descriptor_id"], descriptor_path.absolute())
    daemon.ledger.register(unrelated["descriptor_id"], unrelated_path.absolute())

    assert worker.build_new_descriptors(daemon, (descriptor_path,)) == 1
    rows = daemon.ledger.rows()
    selected = next(
        row for row in rows if row["descriptor_id"] == descriptor["descriptor_id"]
    )
    other = next(
        row for row in rows if row["descriptor_id"] == unrelated["descriptor_id"]
    )
    assert selected["status"] == "built"
    assert Path(selected["parquet_path"]).is_file()
    assert other["status"] == "ready"

    daemon.ledger.mark_error(unrelated["descriptor_id"], "unrelated", permanent=True)
    assert worker.build_new_descriptors(daemon, (descriptor_path,)) == 0


def test_incomplete_campaign_times_out_without_network(tmp_path: Path) -> None:
    config = _config(tmp_path, timeout_seconds=0.1)
    api_calls: list[dict[str, object]] = []
    clock = iter((0.0, 0.2, 0.3, 0.4))

    result = worker.run_worker(
        config,
        sleep=lambda _seconds: None,
        monotonic=lambda: next(clock),
        api_factory=lambda **kwargs: api_calls.append(kwargs),
    )

    assert result == 2
    assert api_calls == []
    status_doc = json.loads(config.status_path.read_text(encoding="utf-8"))
    assert status_doc["phase"] == "error"
    assert "timed out" in status_doc["error"]
    assert stat.S_IMODE(config.work_root.stat().st_mode) == 0o700
    assert stat.S_IMODE(config.status_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(config.worker_lock_path.stat().st_mode) == 0o600


def test_publish_is_resumable_and_redacts_upload_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    coverage = _complete_coverage(config)
    events: list[str] = []
    upload_attempts = 0

    monkeypatch.setattr(
        worker,
        "_wait_for_complete_source",
        lambda *_args, **_kwargs: coverage,
    )
    monkeypatch.setattr(
        worker,
        "inspect_ready_coverage",
        lambda *_args, **_kwargs: coverage,
    )
    monkeypatch.setattr(
        worker,
        "verify_local_campaign",
        lambda *_args, **_kwargs: _complete_reports(),
    )

    def build_plan(*_args: object, **_kwargs: object) -> dict[str, object]:
        events.append("plan")
        return {}

    monkeypatch.setattr(worker, "build_private_export_plan", build_plan)
    monkeypatch.setattr(
        worker,
        "export_public_artifacts",
        lambda *_args, **_kwargs: events.append("export"),
    )
    monkeypatch.setattr(
        worker,
        "load_and_verify_public_export",
        lambda *_args, **kwargs: (
            events.append(f"verify:{kwargs['expected_artifacts']}")
            or SimpleNamespace(manifest_sha256="5" * 64)
        ),
    )

    def fake_upload(**kwargs: object) -> dict[str, object]:
        nonlocal upload_attempts
        upload_attempts += 1
        events.append("upload")
        if upload_attempts == 1:
            raise RuntimeError(f"temporary service error for {TOKEN}")
        return {
            "run_id": PUBLIC_RUN,
            "verified_files": 73,
            "public_export_manifest_sha256": "5" * 64,
        }

    monkeypatch.setattr(worker, "upload_paper_run", fake_upload)
    api_factory = lambda **_kwargs: SimpleNamespace()

    first = worker.run_worker(
        config, api_factory=api_factory, sleep=lambda _seconds: None
    )
    assert first == 0
    assert upload_attempts == 2
    status_text = config.status_path.read_text(encoding="utf-8")
    assert TOKEN not in status_text
    status_doc = json.loads(status_text)
    assert status_doc["phase"] == "complete"
    assert status_doc["upload_report"]["run_id"] == PUBLIC_RUN
    assert events == [
        "plan",
        "export",
        f"verify:{config.expected_public_artifacts}",
        "plan",
        "upload",
        "upload",
    ]

    assert worker.run_worker(config, api_factory=api_factory) == 0
    assert upload_attempts == 2


def test_worker_lock_is_nonblocking_and_private(tmp_path: Path) -> None:
    path = tmp_path / "private" / "worker.lock"
    with worker.HeldLock(path, blocking=False):
        with pytest.raises(
            worker.PublishWorkerError, match="another publication worker"
        ):
            with worker.HeldLock(path, blocking=False):
                pass
    with worker.HeldLock(path, blocking=False):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_campaign_lock_is_shared_across_work_roots(tmp_path: Path) -> None:
    first = _config(tmp_path, work_root=tmp_path / "publish-a")
    second = _config(tmp_path, work_root=tmp_path / "publish-b")
    assert first.campaign_lock_path == second.campaign_lock_path
    with worker.HeldLock(first.campaign_lock_path, blocking=False):
        with pytest.raises(
            worker.PublishWorkerError, match="another publication worker"
        ):
            with worker.HeldLock(second.campaign_lock_path, blocking=False):
                pass
