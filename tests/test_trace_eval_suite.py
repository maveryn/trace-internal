from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    TRACE_EVAL_V1_BENCHMARKS,
    benchmark_specs_for_run_set,
    run_dir,
    score_path,
    spec_by_key,
)
from run_external_benchmark_generation_api_queue import build_parser as generation_parser  # noqa: E402
import run_trace_final26_official_score_campaign as score_campaign  # noqa: E402
from status_trace_eval import collect_status  # noqa: E402
from trace_eval_suite import load_trace_eval_suite  # noqa: E402
from trace_eval_code_provenance import trace_eval_code_manifest  # noqa: E402
from trace_eval_score_receipts import ScoreReceiptError, validate_score_campaign_receipts  # noqa: E402
from verify_trace_eval import verify_campaign  # noqa: E402


EXPECTED_KEYS = (
    "chartqapro",
    "charxivreason",
    "tablevqabench",
    "evochart",
    "mathvision",
    "mathvista",
    "mathverse",
    "wemath",
    "phyx_mini_mc",
    "mmmu_pro_vision",
    "realworldqa",
    "mmstar",
    "embspatial",
    "spatialvizbench_cot",
    "cvbench_3d",
    "erqa",
    "blink",
    "countbenchqa",
    "countqa",
    "treebench",
    "puzzlevqa",
    "visualpuzzles",
    "logicvista",
    "mme_reasoning",
)
EVALUATOR_SHA256 = "e" * 64


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _dataset_manifest(path: Path) -> Path:
    suite = load_trace_eval_suite()
    path.write_text(
        json.dumps(
            {
                "schema_version": "trace-final25-dataset-manifest-v2",
                "suite_id": suite.suite_id,
                "suite_sha256": suite.manifest_sha256,
                "dataset_views": {suite.dataset_manifest_view: list(suite.benchmark_keys)},
                "view_snapshot_sha256": {suite.dataset_manifest_view: "a" * 64},
                "datasets": {
                    item.key: {"rows": item.rows, "status": "ready"}
                    for item in suite.benchmarks
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_complete_score_tree(
    campaign_root: Path,
    score_root: Path,
    *,
    models: tuple[str, ...],
    seeds: tuple[int, ...],
    provenance_root: Path = REPO_ROOT,
) -> None:
    suite = load_trace_eval_suite()
    for seed in seeds:
        run_root = campaign_root / f"seed_{seed}" / "runs"
        benchmark_root = score_root / f"seed_{seed}" / "benchmark"
        for model in models:
            for benchmark in suite.benchmarks:
                spec = spec_by_key(benchmark.key)
                summary = run_dir(spec, model, run_root) / "generation_summary.json"
                summary.parent.mkdir(parents=True, exist_ok=True)
                summary.write_text(
                    json.dumps({"rows": benchmark.rows, "expected_rows": benchmark.rows}),
                    encoding="utf-8",
                )
                score = score_path(spec, model, benchmark_root)
                score.parent.mkdir(parents=True, exist_ok=True)
                metric = (
                    {"accuracy": 50.0}
                    if benchmark.key == "mme_reasoning"
                    else {"score": 50.0}
                )
                score.write_text(
                    json.dumps({**metric, "rows": benchmark.rows}),
                    encoding="utf-8",
                )
        generation_inputs = {}
        completion_slices = []
        for model in models:
            generation_inputs[model] = {}
            for benchmark in suite.benchmarks:
                spec = spec_by_key(benchmark.key)
                summary = run_dir(spec, model, run_root) / "generation_summary.json"
                generation_inputs[model][benchmark.key] = {
                    "rows": benchmark.rows,
                    "generation_summary": str(summary.resolve()),
                    "generation_summary_sha256": _sha256(summary),
                    "dataset_snapshot_sha256": "a" * 64,
                    "finish_reason": {"stop": benchmark.rows},
                }
                score = score_path(spec, model, benchmark_root).resolve()
                completion_slices.append(
                    {
                        "benchmark_key": benchmark.key,
                        "model": f"/models/{model}",
                        "model_slug": model,
                        "rows": benchmark.rows,
                        "score": 50.0,
                        "scores_path": str(score),
                        "scores_sha256": _sha256(score),
                    }
                )
        code_provenance = trace_eval_code_manifest(
            repo_root=provenance_root,
            evaluator_sha256=EVALUATOR_SHA256,
        )
        contract = {
            "contract_version": "trace-eval-score-campaign-v1",
            "suite": suite.suite_id,
            "selection": {
                "path": str(suite.path),
                "sha256": suite.manifest_sha256,
                "benchmarks": list(suite.benchmark_keys),
            },
            "dataset_view": suite.dataset_manifest_view,
            "seed": seed,
            "routes": {
                "official_vlmevalkit": list(suite.routes["official_vlmevalkit"]),
                "direct": list(suite.routes["direct_score"]),
                "mme_reasoning": list(suite.routes["dedicated_score"]),
            },
            "campaigns": [
                {
                    "model": f"/models/{model}",
                    "model_slug": model,
                    "campaign_root": str(campaign_root),
                }
                for model in models
            ],
            "generation_inputs": generation_inputs,
            "dataset_manifest": {"view_snapshot_sha256": "a" * 64},
            "evaluator_provenance": {
                "schema_version": "trace-eval-evaluator-provenance-v1",
                "sha256": EVALUATOR_SHA256,
            },
            "trace_eval_code_provenance": {
                "schema_version": code_provenance["schema_version"],
                "sha256": code_provenance["sha256"],
                "evaluator_provenance_sha256": code_provenance[
                    "evaluator_provenance_sha256"
                ],
            },
            "scoring_implementation": code_provenance["files"],
        }
        contract_sha = _canonical_sha(contract)
        (score_root / f"score_campaign_manifest_seed_{seed}.json").write_text(
            json.dumps({"contract_sha256": contract_sha, "contract": contract}),
            encoding="utf-8",
        )
        (score_root / f"score_campaign_completion_seed_{seed}.json").write_text(
            json.dumps(
                {
                    "contract_sha256": contract_sha,
                    "expected_slices": len(completion_slices),
                    "completed_slices": len(completion_slices),
                    "slices": completion_slices,
                }
            ),
            encoding="utf-8",
        )


def test_suite_is_self_contained_and_exact() -> None:
    suite = load_trace_eval_suite()
    assert suite.suite_id == "trace_eval_v1"
    assert suite.benchmark_keys == EXPECTED_KEYS
    assert suite.rows_per_model_seed == 32_805
    assert [len(keys) for keys in suite.categories.values()] == [4] * 6
    assert {route: len(keys) for route, keys in suite.routes.items()} == {
        "direct_score": 7,
        "official_vlmevalkit": 16,
        "dedicated_score": 1,
    }
    assert all(item.official_alias for item in suite.benchmarks)
    assert all(item.official_alias == spec_by_key(item.key).alias for item in suite.benchmarks)
    assert all(item.answer_contract for item in suite.benchmarks)
    assert all(item.score_contract for item in suite.benchmarks)

    serialized = suite.path.read_text(encoding="utf-8").lower()
    for forbidden in ("final24", "final25", "final31", "all31", "contract_source"):
        assert forbidden not in serialized


def test_neutral_run_set_resolves_exact_suite() -> None:
    assert TRACE_EVAL_V1_BENCHMARKS == EXPECTED_KEYS
    assert tuple(spec.key for spec in benchmark_specs_for_run_set("trace_eval_v1")) == EXPECTED_KEYS
    args = generation_parser().parse_args(
        [
            "--model",
            "model",
            "--model-slug",
            "model",
            "--api-model",
            "model",
            "--dataset-manifest-view",
            "trace_eval_v1",
            "--run-set",
            "trace_eval_v1",
        ]
    )
    assert args.dataset_manifest_view == "trace_eval_v1"
    assert args.run_set == "trace_eval_v1"


def test_score_campaign_uses_manifest_route_partition() -> None:
    try:
        score_campaign._activate_suite("trace_eval_v1")
        suite = load_trace_eval_suite()
        assert score_campaign.DIRECT_SCORE_KEYS == suite.routes["direct_score"]
        assert score_campaign.OFFICIAL_SCORE_KEYS == suite.routes["official_vlmevalkit"]
        assert score_campaign.ALL_SCORE_KEYS == (
            *suite.routes["direct_score"],
            *suite.routes["official_vlmevalkit"],
            "mme_reasoning",
        )
    finally:
        score_campaign._activate_suite("all26")


def test_status_and_score_verifier_support_multiple_models_and_seeds(tmp_path: Path) -> None:
    campaign_root = tmp_path / "campaign"
    score_root = campaign_root / "scoring"
    manifest = _dataset_manifest(tmp_path / "dataset_manifest.json")
    models = ("model-a", "model-b")
    seeds = (42, 44)
    _write_complete_score_tree(
        campaign_root,
        score_root,
        models=models,
        seeds=seeds,
    )
    suite = load_trace_eval_suite()
    status_args = argparse.Namespace(
        campaign_root=campaign_root,
        score_root=score_root,
        dataset_manifest=manifest,
        archive_spool_root=campaign_root / "hf_archive",
        model_slugs=models,
        seeds=seeds,
        rate_window_seconds=300.0,
        low_gpu_threshold=10,
        gpu=False,
        vlmeval_root=tmp_path / "vlmeval",
    )
    with patch(
        "status_trace_eval.evaluator_provenance_sha256", return_value=EVALUATOR_SHA256
    ) as fingerprint:
        report = collect_status(status_args, suite)
        repeated = collect_status(status_args, suite)
    assert fingerprint.call_count == 1
    assert repeated["complete"] is True
    assert report["complete"] is True
    assert report["expected_rows"] == 32_805 * len(models) * len(seeds)
    assert report["score_slices"] == 24 * len(models) * len(seeds)
    assert report["expected_archive_slices"] == 24 * len(models) * len(seeds) * 3

    verify_args = argparse.Namespace(
        campaign_root=campaign_root,
        score_root=score_root,
        phase="score",
        model_slugs=list(models),
        model_entry=[],
        seeds=seeds,
        dataset_manifest=manifest,
        suite_manifest=suite.path,
        dataset_revision=None,
        dataset_snapshot_sha256=None,
        code_hash=None,
        evaluator_provenance_sha256=None,
        vlmeval_root=tmp_path / "vlmeval",
    )
    with patch("verify_trace_eval.evaluator_provenance_sha256", return_value=EVALUATOR_SHA256):
        verification = verify_campaign(verify_args, suite)
    assert verification["complete"] is True
    assert verification["expected_slices"] == 24 * len(models) * len(seeds)


def test_score_receipts_fail_closed_on_contract_identity_and_artifact_changes(
    tmp_path: Path,
) -> None:
    campaign_root = tmp_path / "campaign"
    score_root = campaign_root / "scoring"
    models = ("model-a",)
    seed = 42
    _write_complete_score_tree(campaign_root, score_root, models=models, seeds=(seed,))
    suite = load_trace_eval_suite()
    kwargs = {
        "score_root": score_root,
        "seed": seed,
        "model_slugs": models,
        "suite": suite,
        "evaluator_sha256": EVALUATOR_SHA256,
        "repo_root": REPO_ROOT,
    }
    verified = validate_score_campaign_receipts(**kwargs)
    assert len(verified) == 24

    manifest_path = score_root / f"score_campaign_manifest_seed_{seed}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["contract"]["seed"] = 43
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ScoreReceiptError, match="contract SHA mismatch"):
        validate_score_campaign_receipts(**kwargs)

    _write_complete_score_tree(campaign_root, score_root, models=models, seeds=(seed,))
    completion_path = score_root / f"score_campaign_completion_seed_{seed}.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    completion["slices"][1] = dict(completion["slices"][0])
    completion_path.write_text(json.dumps(completion), encoding="utf-8")
    with pytest.raises(ScoreReceiptError, match="duplicate completion slice identity"):
        validate_score_campaign_receipts(**kwargs)

    _write_complete_score_tree(campaign_root, score_root, models=models, seeds=(seed,))
    score = score_path(
        spec_by_key(suite.benchmark_keys[0]),
        models[0],
        score_root / f"seed_{seed}" / "benchmark",
    )
    score.write_text(json.dumps({"score": 49.0, "rows": suite.benchmarks[0].rows}))
    with pytest.raises(ScoreReceiptError, match="score artifact SHA mismatch"):
        validate_score_campaign_receipts(**kwargs)


def test_status_and_verifier_do_not_accept_raw_scores_without_completion_receipt(
    tmp_path: Path,
) -> None:
    campaign_root = tmp_path / "campaign"
    score_root = campaign_root / "scoring"
    dataset_manifest = _dataset_manifest(tmp_path / "dataset_manifest.json")
    _write_complete_score_tree(campaign_root, score_root, models=("model-a",), seeds=(42,))
    (score_root / "score_campaign_completion_seed_42.json").unlink()
    suite = load_trace_eval_suite()

    status_args = argparse.Namespace(
        campaign_root=campaign_root,
        score_root=score_root,
        dataset_manifest=dataset_manifest,
        archive_spool_root=campaign_root / "hf_archive",
        model_slugs=("model-a",),
        seeds=(42,),
        rate_window_seconds=300.0,
        low_gpu_threshold=10,
        gpu=False,
        vlmeval_root=tmp_path / "vlmeval",
    )
    with patch("status_trace_eval.evaluator_provenance_sha256", return_value=EVALUATOR_SHA256):
        status = collect_status(status_args, suite)
    assert status["complete"] is False
    assert status["observed_score_files"] == 24
    assert status["score_slices"] == 0
    assert 42 in status["score_receipt_errors"]

    verify_args = argparse.Namespace(
        campaign_root=campaign_root,
        score_root=score_root,
        phase="score",
        model_slugs=["model-a"],
        model_entry=[],
        seeds=(42,),
        dataset_manifest=dataset_manifest,
        suite_manifest=suite.path,
        dataset_revision=None,
        dataset_snapshot_sha256=None,
        code_hash=None,
        evaluator_provenance_sha256=None,
        vlmeval_root=tmp_path / "vlmeval",
    )
    with patch("verify_trace_eval.evaluator_provenance_sha256", return_value=EVALUATOR_SHA256):
        verification = verify_campaign(verify_args, suite)
    assert verification["complete"] is False
    assert verification["completed_slices"] == 0
    assert all("receipt_invalid" in item["detail"] for item in verification["incomplete"])


def test_generation_verifier_requires_current_evaluator_and_code_hash(tmp_path: Path) -> None:
    suite = load_trace_eval_suite()
    args = argparse.Namespace(
        campaign_root=tmp_path / "campaign",
        score_root=None,
        phase="generation",
        model_slugs=[],
        model_entry=["model-a=/models/model-a=revision-a"],
        seeds=(42,),
        dataset_manifest=_dataset_manifest(tmp_path / "dataset_manifest.json"),
        suite_manifest=suite.path,
        dataset_revision=None,
        dataset_snapshot_sha256=None,
        code_hash="c" * 64,
        evaluator_provenance_sha256="f" * 64,
        vlmeval_root=tmp_path / "vlmeval",
    )
    with patch("verify_trace_eval.evaluator_provenance_sha256", return_value=EVALUATOR_SHA256):
        with pytest.raises(ValueError, match="evaluator provenance"):
            verify_campaign(args, suite)

    args.evaluator_provenance_sha256 = EVALUATOR_SHA256
    with (
        patch("verify_trace_eval.evaluator_provenance_sha256", return_value=EVALUATOR_SHA256),
        patch("verify_trace_eval.trace_eval_code_sha256", return_value="d" * 64),
    ):
        with pytest.raises(ValueError, match="generation code hash"):
            verify_campaign(args, suite)


def test_score_receipts_require_completion_and_current_evaluator(tmp_path: Path) -> None:
    campaign_root = tmp_path / "campaign"
    score_root = campaign_root / "scoring"
    _write_complete_score_tree(campaign_root, score_root, models=("model-a",), seeds=(42,))
    suite = load_trace_eval_suite()
    completion = score_root / "score_campaign_completion_seed_42.json"
    completion.unlink()
    with pytest.raises(ScoreReceiptError, match="missing score campaign completion"):
        validate_score_campaign_receipts(
            score_root=score_root,
            seed=42,
            model_slugs=("model-a",),
            suite=suite,
            evaluator_sha256=EVALUATOR_SHA256,
            repo_root=REPO_ROOT,
        )

    _write_complete_score_tree(campaign_root, score_root, models=("model-a",), seeds=(42,))
    with pytest.raises(ScoreReceiptError, match="evaluator provenance"):
        validate_score_campaign_receipts(
            score_root=score_root,
            seed=42,
            model_slugs=("model-a",),
            suite=suite,
            evaluator_sha256="f" * 64,
            repo_root=REPO_ROOT,
        )


def test_score_receipts_reject_tampered_scoring_helper(tmp_path: Path) -> None:
    original_manifest = trace_eval_code_manifest(
        repo_root=REPO_ROOT,
        evaluator_sha256=EVALUATOR_SHA256,
    )
    provenance_root = tmp_path / "provenance-repo"
    for relative in original_manifest["files"]:
        source = REPO_ROOT / relative
        destination = provenance_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    campaign_root = tmp_path / "campaign"
    score_root = campaign_root / "scoring"
    _write_complete_score_tree(
        campaign_root,
        score_root,
        models=("model-a",),
        seeds=(42,),
        provenance_root=provenance_root,
    )
    suite = load_trace_eval_suite()
    kwargs = {
        "score_root": score_root,
        "seed": 42,
        "model_slugs": ("model-a",),
        "suite": suite,
        "evaluator_sha256": EVALUATOR_SHA256,
        "repo_root": provenance_root,
    }
    assert len(validate_score_campaign_receipts(**kwargs)) == 24

    helper = provenance_root / "scripts" / "trace_benchmark_answer_parsing.py"
    helper.write_text(helper.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    with pytest.raises(ScoreReceiptError, match="code provenance"):
        validate_score_campaign_receipts(**kwargs)


def test_launcher_accepts_one_or_more_models_and_seeds() -> None:
    command = [
        "bash",
        str(REPO_ROOT / "scripts" / "run_trace_eval.sh"),
        "--model",
        "one",
        "/tmp/one",
        "rev-one",
        f"example/one@{'1' * 40}",
        "Model One",
        "--model",
        "two",
        "/tmp/two",
        "rev-two",
        f"example/two@{'2' * 40}",
        "Model Two",
        "--seeds",
        "42",
        "44",
        "--print-config",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    assert "suite=trace_eval_v1" in result.stdout
    assert "seeds=42 44" in result.stdout
    assert result.stdout.count("model=") == 2
    subprocess.run(
        ["bash", "-n", str(REPO_ROOT / "scripts" / "run_trace_eval.sh")],
        check=True,
    )


def test_launcher_rejects_mutable_or_nonrepository_model_source() -> None:
    result = subprocess.run(
        [
            "bash",
            str(REPO_ROOT / "scripts" / "run_trace_eval.sh"),
            "--model",
            "one",
            "/tmp/one",
            "rev-one",
            "training-run-name",
            "Model One",
            "--seeds",
            "42",
            "--print-config",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "owner/repo@immutable-commit" in result.stderr


def test_launcher_cannot_upload_legacy_raw_slices_to_paper_repo() -> None:
    launcher = (REPO_ROOT / "scripts" / "run_trace_eval.sh").read_text(encoding="utf-8")
    assert "maveryn/trace-eval-runs" not in launcher
    assert "legacy raw archive upload is disabled" in launcher
    assert "coverage --expect-run-id" in launcher  # Local coverage remains available.
    assert " daemon --poll-seconds" not in launcher
    assert " upload-paper " not in launcher


def test_launcher_passes_its_runtime_paths_to_scoring() -> None:
    launcher = (REPO_ROOT / "scripts" / "run_trace_eval.sh").read_text(encoding="utf-8")
    assert '--python "${PYTHON_BIN}" --eval-deps "${EVAL_DEPS_ROOT}"' in launcher
    assert '--lmu-data "${LMUData}" --hf-home "${HF_HOME}"' in launcher
    assert 'export HF_HOME="${HF_HOME:-${LMUData}/.hf-cache}"' in launcher
    assert 'CPU_AFFINITY_GROUPS="${CPU_AFFINITY_GROUPS:-}"' in launcher
    assert 'EVAL_CPUSET="${EVAL_CPUSET:-none}"' in launcher
    assert '"sources=${MODEL_SOURCES[*]}"' in launcher


def test_active_surface_has_no_larger_suite_fallback() -> None:
    active_paths = (
        REPO_ROOT / "evaluation" / "trace_eval" / "suite.v1.json",
        REPO_ROOT / "evaluation" / "trace_eval" / "README.md",
        REPO_ROOT / "scripts" / "prepare_trace_eval_manifest.py",
        REPO_ROOT / "scripts" / "status_trace_eval.py",
        REPO_ROOT / "scripts" / "verify_trace_eval.py",
    )
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in active_paths)
    assert "all31" not in text
    assert "trace_final31" not in text


def test_eval_requirements_pin_archive_dependencies() -> None:
    requirements = (REPO_ROOT / "evaluation" / "requirements-eval.txt").read_text(
        encoding="utf-8"
    )
    assert "pyarrow==24.0.0" in requirements
    assert "huggingface_hub==0.36.2" in requirements
