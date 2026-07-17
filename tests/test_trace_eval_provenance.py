from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from trace_eval_code_provenance import trace_eval_code_manifest
from trace_eval_evaluator_provenance import build_evaluator_provenance


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(["git", "-C", str(root), *arguments], check=True, capture_output=True)


def _init_git(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init")
    _git(root, "config", "user.email", "trace-eval-test@example.invalid")
    _git(root, "config", "user.name", "TRACE Eval Test")


def test_evaluator_provenance_tracks_dirty_untracked_deleted_and_local_sources(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "trace"
    _init_git(repo_root)
    extension = repo_root / "rlvr" / "vlmevalkit_extensions" / "adapter.py"
    installer = repo_root / "scripts" / "apply_vlmevalkit_trace_extensions.py"
    extension.parent.mkdir(parents=True)
    installer.parent.mkdir(parents=True)
    extension.write_text("VALUE = 1\n", encoding="utf-8")
    installer.write_text("print('apply')\n", encoding="utf-8")
    _git(repo_root, "add", "rlvr/vlmevalkit_extensions", "scripts/apply_vlmevalkit_trace_extensions.py")
    _git(repo_root, "commit", "-m", "add extensions")

    vlmeval_root = repo_root / "external" / "VLMEvalKit"
    _init_git(vlmeval_root)
    evaluator = vlmeval_root / "vlmeval" / "evaluator.py"
    evaluator.parent.mkdir(parents=True)
    evaluator.write_text("VALUE = 1\n", encoding="utf-8")
    _git(vlmeval_root, "add", "vlmeval/evaluator.py")
    _git(vlmeval_root, "commit", "-m", "add evaluator")

    initial = build_evaluator_provenance(repo_root=repo_root, vlmeval_root=vlmeval_root)
    repeated = build_evaluator_provenance(repo_root=repo_root, vlmeval_root=vlmeval_root)
    assert initial == repeated

    evaluator.write_text("VALUE = 2\n", encoding="utf-8")
    dirty = build_evaluator_provenance(repo_root=repo_root, vlmeval_root=vlmeval_root)
    assert dirty["sha256"] != initial["sha256"]

    (vlmeval_root / "untracked.py").write_text("VALUE = 3\n", encoding="utf-8")
    untracked = build_evaluator_provenance(repo_root=repo_root, vlmeval_root=vlmeval_root)
    assert untracked["sha256"] != dirty["sha256"]

    evaluator.unlink()
    deleted = build_evaluator_provenance(repo_root=repo_root, vlmeval_root=vlmeval_root)
    assert deleted["sha256"] != untracked["sha256"]
    assert any(
        record["path"] == "vlmeval/evaluator.py" and record["kind"] == "missing"
        for record in deleted["vlmevalkit"]["files"]
    )

    extension.write_text("VALUE = 4\n", encoding="utf-8")
    local_changed = build_evaluator_provenance(repo_root=repo_root, vlmeval_root=vlmeval_root)
    assert local_changed["sha256"] != deleted["sha256"]


def test_code_provenance_covers_active_trace_eval_control_surface() -> None:
    manifest = trace_eval_code_manifest(
        repo_root=REPO_ROOT,
        evaluator_sha256="e" * 64,
    )
    required = {
        "evaluation/requirements-eval.txt",
        "evaluation/trace_eval/suite.v1.json",
        "scripts/prepare_trace_eval_manifest.py",
        "scripts/prepare_trace_final25_models.py",
        "scripts/run_trace_eval.sh",
        "scripts/run_trace_eval_score_campaign.py",
        "scripts/setup_trace_eval_env.sh",
        "scripts/status_trace_eval.py",
        "scripts/trace_eval_score_receipts.py",
        "scripts/verify_trace_eval.py",
    }
    assert required <= set(manifest["files"])
    assert manifest["evaluator_provenance_sha256"] == "e" * 64
    assert manifest == trace_eval_code_manifest(
        repo_root=REPO_ROOT,
        evaluator_sha256="e" * 64,
    )
