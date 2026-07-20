#!/usr/bin/env python3
"""Build the reviewed internal-to-public map for the paper RLVR release."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    REPO_ROOT
    / "docs"
    / "workflows"
    / "PUBLIC_RELEASE"
    / "rlvr_public_file_manifest.v1.json"
)

TRAINING_3B_REVISION = "847e9f5279f8111fdbfef1c8b8631fc621c23456"
TRAINING_7B_REVISION = "d29b23f6085764ea831adb5edc5a23f89b0d98f3"
EVALUATION_REVISION = "5cea97310204b197fdacecdd83ef938c1e3b67cd"
EASYR1_UPSTREAM_REVISION = "dd71bbd252694f5f850213eec15795b6b88d9fea"
TRAINING_CONFIG_RECEIPT = (
    "docs/workflows/PUBLIC_RELEASE/rlvr_training_configs.v1.json"
)
TRAINING_ENVIRONMENT_RECEIPT = (
    "docs/workflows/PUBLIC_RELEASE/rlvr_training_environments.v1.json"
)

TRAINING_EXPLICIT = (
    "rlvr/easyr1_backend/LICENSE",
    "rlvr/easyr1_backend/examples/__init__.py",
    "rlvr/easyr1_backend/examples/reward_function/trace_rlvr.py",
    "rlvr/easyr1_backend/scripts/model_merger.py",
    "rlvr/examples/prompts/trace_vero_json_system_prompt_answer.txt",
)

TRAINING_PUBLIC_ENTRYPOINTS = (
    "rlvr/configs/trace-qwen2.5-vl-3b.yaml",
    "rlvr/configs/trace-qwen2.5-vl-7b.yaml",
    "rlvr/train.py",
)

TRAINING_ADAPTATIONS = {
    "rlvr/easyr1_backend/examples/reward_function/trace_rlvr.py": (
        "replace internal trace imports with the public trace_tasks scoring API",
        "hardcode the answer-only exact-JSON reward boundary and fail on invalid ground truth",
        "remove annotation, task-conditioned, and legacy fallback modes",
    ),
    "rlvr/easyr1_backend/scripts/model_merger.py": (
        "remove Hugging Face upload functions and command-line arguments",
        "retain local checkpoint validation and model merging only",
    ),
    "rlvr/easyr1_backend/verl/trainer/config.py": (
        "remove annotation, task-conditioned, and per-mode prompt configuration fields",
        "retain the generic answer-only system-prompt and solve-threshold fields",
    ),
    "rlvr/easyr1_backend/verl/trainer/data_loader.py": (
        "stop forwarding task identifiers and annotation-routing arguments",
        "retain generic train and validation dataset construction",
    ),
    "rlvr/easyr1_backend/verl/trainer/metrics.py": (
        "remove annotation-type, mixed-mode, and per-mode metric families",
        "retain generic numeric reward and solve-rate metrics",
    ),
    "rlvr/easyr1_backend/verl/utils/dataset.py": (
        "remove internal trace imports and task-conditioned supervision routing",
        "retain prompt_answer loading, answer_gt ground truth, uid, and multimodal handling",
    ),
}

EVALUATION_PATHS = (
    "evaluation/requirements-eval.txt",
    "evaluation/trace_eval/README.md",
    "evaluation/trace_eval/suite.v1.json",
    "rlvr/examples/prompts/chat_template_no_think.jinja",
    "rlvr/vlmevalkit_extensions/evochart.py",
    "rlvr/vlmevalkit_extensions/trace_final25_answer_parsing.py",
    "rlvr/vlmevalkit_extensions/trace_local_vqa.py",
    "scripts/apply_vlmevalkit_trace_extensions.py",
    "scripts/benchmark_queue_lib.py",
    "scripts/final25_archive_hooks.py",
    "scripts/final25_hf_archive.py",
    "scripts/final25_hf_archive_lib.py",
    "scripts/final25_media_contract.py",
    "scripts/prepare_trace_eval_manifest.py",
    "scripts/prepare_trace_final25_datasets.py",
    "scripts/prepare_trace_final25_models.py",
    "scripts/run_external_benchmark_generation_api_queue.py",
    "scripts/run_external_benchmark_generation_queue.py",
    "scripts/run_external_benchmark_score_queue.py",
    "scripts/run_mme_reasoning_eval.py",
    "scripts/run_official_vlmevalkit_saved_score.py",
    "scripts/run_trace_eval.sh",
    "scripts/run_trace_eval_publish_worker.py",
    "scripts/run_trace_eval_score_campaign.py",
    "scripts/run_trace_final26_official_score_campaign.py",
    "scripts/setup_trace_eval_env.sh",
    "scripts/start_vllm_endpoint_pool.sh",
    "scripts/status_trace_eval.py",
    "scripts/stop_vllm_endpoint_pool.sh",
    "scripts/summarize_trace_final25_multiseed.py",
    "scripts/trace_benchmark_answer_parsing.py",
    "scripts/trace_eval_code_provenance.py",
    "scripts/trace_eval_evaluator_provenance.py",
    "scripts/trace_eval_public_export.py",
    "scripts/trace_eval_score_receipts.py",
    "scripts/trace_eval_suite.py",
    "scripts/trace_final25_contract.py",
    "scripts/verify_trace_eval.py",
    "scripts/verify_trace_final25_campaign.py",
)

RELEASE_DATA_PATHS = (
    "evaluation/trace_eval/benchmark_provenance.v1.json",
    "results/canonical/trace_eval_v1/release/README.md",
    "results/canonical/trace_eval_v1/release/results.json",
    "scripts/build_trace_eval_release_results.py",
    "scripts/validate_rlvr_release_inputs.py",
    "tests/test_rlvr_release_inputs.py",
)

EVALUATION_RENAMES = {
    "evaluation/requirements-eval.txt": "rlvr/evaluation/requirements.txt",
    "evaluation/trace_eval/README.md": "rlvr/evaluation/trace_eval/README.md",
    "evaluation/trace_eval/suite.v1.json": "rlvr/evaluation/trace_eval/suite.v1.json",
    "rlvr/vlmevalkit_extensions/trace_final25_answer_parsing.py": (
        "rlvr/evaluation/vlmevalkit_extensions/trace_eval_answer_parsing.py"
    ),
    "rlvr/vlmevalkit_extensions/trace_local_vqa.py": (
        "rlvr/evaluation/vlmevalkit_extensions/trace_eval_local_vqa.py"
    ),
    "rlvr/vlmevalkit_extensions/evochart.py": (
        "rlvr/evaluation/vlmevalkit_extensions/evochart.py"
    ),
    "scripts/final25_archive_hooks.py": "rlvr/evaluation/scripts/trace_eval_archive_hooks.py",
    "scripts/final25_hf_archive.py": "rlvr/evaluation/scripts/trace_eval_hf_archive.py",
    "scripts/final25_hf_archive_lib.py": "rlvr/evaluation/scripts/trace_eval_hf_archive_lib.py",
    "scripts/final25_media_contract.py": "rlvr/evaluation/scripts/trace_eval_media_contract.py",
    "scripts/prepare_trace_final25_datasets.py": (
        "rlvr/evaluation/scripts/prepare_trace_eval_datasets.py"
    ),
    "scripts/prepare_trace_final25_models.py": (
        "rlvr/evaluation/scripts/prepare_trace_eval_models.py"
    ),
    "scripts/run_trace_final26_official_score_campaign.py": (
        "rlvr/evaluation/scripts/run_trace_eval_official_score_campaign.py"
    ),
    "scripts/summarize_trace_final25_multiseed.py": (
        "rlvr/evaluation/scripts/summarize_trace_eval.py"
    ),
    "scripts/trace_final25_contract.py": (
        "rlvr/evaluation/scripts/trace_eval_scoring_contract.py"
    ),
    "scripts/verify_trace_final25_campaign.py": (
        "rlvr/evaluation/scripts/trace_eval_campaign_verification.py"
    ),
}

RELEASE_DATA_RENAMES = {
    "evaluation/trace_eval/benchmark_provenance.v1.json": (
        "rlvr/evaluation/trace_eval/benchmark_provenance.v1.json"
    ),
    "results/canonical/trace_eval_v1/release/README.md": (
        "rlvr/evaluation/trace_eval/RESULTS.md"
    ),
    "results/canonical/trace_eval_v1/release/results.json": (
        "rlvr/evaluation/trace_eval/results.json"
    ),
    "scripts/build_trace_eval_release_results.py": (
        "rlvr/evaluation/scripts/build_release_results.py"
    ),
    "scripts/validate_rlvr_release_inputs.py": (
        "rlvr/evaluation/scripts/validate_release_inputs.py"
    ),
    "tests/test_rlvr_release_inputs.py": (
        "rlvr/evaluation/tests/test_release_inputs.py"
    ),
}

HISTORICAL_DENYLIST = (
    {
        "path_or_pattern": "rlvr/experiments/final_answer_only_manifest.json",
        "reason": (
            "Historical Final25 experiment ledger; it predates the canonical "
            "trace_eval_v1 reruns and is not a release input."
        ),
    },
    {
        "path_or_pattern": "evaluation/final{24,25,26,31}/**",
        "reason": "Historical and provisional suite definitions are outside trace_eval_v1.",
    },
    {
        "path_or_pattern": "scripts/run_trace_final*.{py,sh}",
        "reason": (
            "Historical campaign launchers are excluded, except the one scoring engine "
            "explicitly mapped above for scope reduction and neutral renaming."
        ),
    },
    {
        "path_or_pattern": "scripts/*repair*|scripts/*recover*|scripts/*reuse*",
        "reason": "Incident recovery, parser repair, and reuse machinery remains internal.",
    },
    {
        "path_or_pattern": "scripts/run_trace_eval_rl_baselines.sh",
        "reason": (
            "Baseline-specific processor aliases and compatibility views remain internal; "
            "the public evaluator accepts model descriptors generically."
        ),
    },
    {
        "path_or_pattern": "scripts/{migrate_trace_eval_archive.py,trace_eval_archive_migration_lib.py}",
        "reason": "Private archive migration and recovery operations are not a public API.",
    },
    {
        "path_or_pattern": "rlvr/vlmevalkit_extensions/{mirage.py,visiongraph.py,scripts/**}",
        "reason": "Extensions not used by the 24-benchmark release suite are excluded.",
    },
    {
        "path_or_pattern": "scripts/screenspot_json_contract.py",
        "reason": "ScreenSpot is not in trace_eval_v1; stale imports are removed during adaptation.",
    },
    {
        "path_or_pattern": "rlvr/**/annotation*|rlvr/**/task_conditioned*",
        "reason": "Annotation and task-conditioned training are experimental, not paper release scope.",
    },
    {
        "path_or_pattern": (
            "rlvr/easyr1_backend/{examples/config.yaml,pyproject.toml,requirements.txt,"
            "setup.py,tests/**}"
        ),
        "reason": (
            "The generic math example, backend packaging, unpinned environment, and "
            "internal tests are not curated public training inputs."
        ),
    },
    {
        "path_or_pattern": "scripts/run_trace_qwen25vl{3b,7b}_easyr1*.sh",
        "reason": (
            "Operational launchers contain machine paths and historical wrapper behavior; "
            "the public interface is the reviewed two-config Python CLI."
        ),
    },
    {
        "path_or_pattern": "results/** (except canonical trace_eval_v1 release/results.json)",
        "reason": "Historical workbooks, provisional summaries, raw dumps, and local paths stay internal.",
    },
    {
        "path_or_pattern": "benchmark/**|runs/**|logs/**|*token*|*.env",
        "reason": "No benchmark payloads, run caches, machine logs, credentials, or secrets are released.",
    },
)


def _run_git(*arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *arguments],
        check=True,
        capture_output=True,
    ).stdout


def _git_paths(revision: str, prefix: str) -> tuple[str, ...]:
    output = _run_git("ls-tree", "-r", "--name-only", revision, "--", prefix)
    return tuple(line for line in output.decode("utf-8").splitlines() if line)


def _git_content(revision: str, path: str) -> bytes:
    return _run_git("show", f"{revision}:{path}")


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _destination_for_evaluation(path: str) -> str:
    if path in EVALUATION_RENAMES:
        return EVALUATION_RENAMES[path]
    if path.startswith("scripts/"):
        return f"rlvr/evaluation/{path}"
    return path


def _entry(
    *,
    component: str,
    source_path: str,
    source_revision: str,
    destination_path: str,
    review_status: str,
    adaptations: Iterable[str] = (),
) -> dict[str, Any]:
    content = _git_content(source_revision, source_path)
    return {
        "component": component,
        "source_path": source_path,
        "source_revision": source_revision,
        "source_sha256": _sha256_bytes(content),
        "destination_path": destination_path,
        "owner": "rlvr",
        "review_status": review_status,
        "adaptations": list(adaptations),
    }


def _training_entries() -> list[dict[str, Any]]:
    paths = set(TRAINING_EXPLICIT)
    paths.update(_git_paths(TRAINING_3B_REVISION, "rlvr/easyr1_backend/verl"))
    entries: list[dict[str, Any]] = []
    for path in sorted(paths):
        adaptations = TRAINING_ADAPTATIONS.get(path, ())
        status = (
            "approved_for_public_adaptation"
            if adaptations
            else "approved_exact_copy"
        )
        entries.append(
            _entry(
                component="answer_only_training",
                source_path=path,
                source_revision=TRAINING_3B_REVISION,
                destination_path=path,
                review_status=status,
                adaptations=adaptations,
            )
        )
    receipt_path = REPO_ROOT / TRAINING_CONFIG_RECEIPT
    for destination in TRAINING_PUBLIC_ENTRYPOINTS:
        if destination.endswith(".yaml"):
            adaptations = [
                "select only the matching config_id from the sanitized canonical receipt",
                "encode the immutable answer-only EasyR1 semantics without machine-local paths",
                "permit only runtime input, output, cache, telemetry, and CUDA-device locations",
            ]
        else:
            adaptations = [
                "implement the receipt's check, prepare, run, smoke, and merge interface",
                "make full runs fail closed on semantic overrides, resume, nonempty output, and GPU count",
                "use standard Hugging Face authentication and never upload models or checkpoints",
            ]
        entries.append(
            {
                "component": "answer_only_training_entrypoint",
                "source_path": TRAINING_CONFIG_RECEIPT,
                "source_revision": "content_sha256_frozen_pending_internal_commit",
                "source_sha256": _sha256_path(receipt_path),
                "destination_path": destination,
                "owner": "rlvr",
                "review_status": "approved_for_public_adaptation",
                "adaptations": adaptations,
            }
        )
    return entries


def _evaluation_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    exact = {
        "evaluation/requirements-eval.txt",
        "evaluation/trace_eval/suite.v1.json",
        "rlvr/examples/prompts/chat_template_no_think.jinja",
    }
    for path in EVALUATION_PATHS:
        status = "approved_exact_copy" if path in exact else "approved_for_public_adaptation"
        adaptations: tuple[str, ...] = ()
        if status != "approved_exact_copy":
            adaptations = (
                "restrict registries and command choices to trace_eval_v1",
                "rename Final25/Final26 compatibility symbols to neutral trace_eval names",
                "remove private paths, recovery operations, and baseline-specific compatibility fixtures",
                "replace internal package imports with trace_tasks and repository-relative resource lookup",
            )
        entries.append(
            _entry(
                component="trace_eval_v1_runtime",
                source_path=path,
                source_revision=EVALUATION_REVISION,
                destination_path=_destination_for_evaluation(path),
                review_status=status,
                adaptations=adaptations,
            )
        )
    return entries


def _release_data_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in RELEASE_DATA_PATHS:
        absolute = REPO_ROOT / path
        if not absolute.is_file():
            raise FileNotFoundError(absolute)
        status = "approved_exact_copy"
        adaptations: list[str] = []
        if path.startswith(("scripts/", "tests/")):
            status = "approved_for_public_adaptation"
            adaptations = [
                "update default paths and imports for the public rlvr/evaluation layout",
                "retain fail-closed model, benchmark, source-hash, and aggregation checks",
            ]
        entries.append(
            {
                "component": "release_metadata",
                "source_path": path,
                "source_revision": "content_sha256_frozen_pending_internal_commit",
                "source_sha256": _sha256_path(absolute),
                "destination_path": RELEASE_DATA_RENAMES[path],
                "owner": "rlvr",
                "review_status": status,
                "adaptations": adaptations,
            }
        )
    return entries


def _run_source_hashes(paths: Iterable[str], revision: str) -> dict[str, str]:
    return {
        path: _sha256_bytes(_git_content(revision, path)) for path in sorted(paths)
    }


def build_manifest() -> dict[str, Any]:
    training_paths = set(TRAINING_EXPLICIT)
    training_paths.update(_git_paths(TRAINING_3B_REVISION, "rlvr/easyr1_backend/verl"))
    entries = _training_entries() + _evaluation_entries() + _release_data_entries()
    destinations = [entry["destination_path"] for entry in entries]
    if len(destinations) != len(set(destinations)):
        duplicates = sorted({path for path in destinations if destinations.count(path) > 1})
        raise RuntimeError(f"duplicate public destinations: {duplicates}")

    prompt_path = REPO_ROOT / "rlvr/examples/prompts/trace_vero_json_system_prompt_answer.txt"
    manifest: dict[str, Any] = {
        "schema_version": "trace-rlvr-public-file-manifest-v1",
        "status": "reviewed_release_input_freeze",
        "reviewed_on": "2026-07-18",
        "release_scope": (
            "Paper-reported Qwen2.5-VL 3B/7B answer-only training and canonical "
            "trace_eval_v1 generation, extraction, scoring, verification, summary, and publication."
        ),
        "public_base": "d5d0215ff887e15c2ffafac632f27a3e0e76b5e8",
        "release_inputs": {
            "trace_dataset": {
                "repository_id": "maveryn/trace",
                "revision": "e317b746b258630682367cc6a9d87dedd195113c",
            },
            "training_runs": [
                {
                    "parameter_scale": "3B",
                    "wandb_run_id": "kijsydl8",
                    "source_revision": TRAINING_3B_REVISION,
                    "merged_model": (
                        "maveryn/trace-qwen2.5-vl-3b@"
                        "2ec2374d5c219e6b12e26bda93d3b3adeb1e30c5"
                    ),
                    "source_file_sha256": _run_source_hashes(
                        training_paths, TRAINING_3B_REVISION
                    ),
                },
                {
                    "parameter_scale": "7B",
                    "wandb_run_id": "usqbkpd6",
                    "source_revision": TRAINING_7B_REVISION,
                    "merged_model": (
                        "maveryn/trace-qwen2.5-vl-7b@"
                        "4d0f1ae8ee25022058090dbdbff61957ece7331d"
                    ),
                    "source_file_sha256": _run_source_hashes(
                        training_paths, TRAINING_7B_REVISION
                    ),
                },
            ],
            "training_receipts": {
                "resolved_configs": {
                    "path": TRAINING_CONFIG_RECEIPT,
                    "sha256": _sha256_path(REPO_ROOT / TRAINING_CONFIG_RECEIPT),
                    "schema_version": "trace-rlvr-training-config-receipt-v1",
                },
                "environments": {
                    "path": TRAINING_ENVIRONMENT_RECEIPT,
                    "sha256": _sha256_path(REPO_ROOT / TRAINING_ENVIRONMENT_RECEIPT),
                    "schema_version": "trace-rlvr-training-environment-receipt-v1",
                },
            },
            "vendored_runtime": {
                "upstream_repository": "https://github.com/hiyouga/EasyR1",
                "upstream_revision": EASYR1_UPSTREAM_REVISION,
                "license": "Apache-2.0",
                "internal_source_revision": TRAINING_3B_REVISION,
                "verl_file_count": 64,
            },
            "training_source_equivalence_review": {
                "status": "reviewed_nonsemantic_difference",
                "primary_public_source_revision": TRAINING_3B_REVISION,
                "compared_revision": TRAINING_7B_REVISION,
                "differing_release_files": [
                    "rlvr/easyr1_backend/examples/reward_function/trace_rlvr.py",
                    "rlvr/easyr1_backend/verl/trainer/config.py",
                ],
                "finding": (
                    "The differences only capitalize user-facing 'Trace' strings to 'TRACE'; "
                    "configuration and runtime behavior are unchanged."
                ),
            },
            "training_contract": {
                "scope": "qwen2.5_vl_3b_and_7b_answer_only_grpo",
                "dataset_revision": "e317b746b258630682367cc6a9d87dedd195113c",
                "train_rows": 64000,
                "validation_rows": 2000,
                "prompt_key": "prompt_answer",
                "answer_key": "answer_gt",
                "output_mode": "answer",
                "reward": {
                    "answer_scoring": "exact_json",
                    "answer_weight": 1.0,
                    "format_weight": 0.05,
                    "annotation_weight": 0.0,
                },
                "algorithm": {
                    "name": "grpo",
                    "disable_kl": True,
                    "use_kl_loss": False,
                    "kl_coefficient": 0.0,
                    "actor_learning_rate": 1e-6,
                    "actor_lr_scheduler": "constant",
                    "actor_lr_warmup_ratio": 0.0,
                    "actor_ppo_epochs": 1,
                },
                "batching": {
                    "rollout_batch_size": 128,
                    "actor_global_batch_size": 128,
                    "rollouts_per_prompt": 8,
                    "validation_batch_size": 1024,
                    "max_prompt_tokens": 2048,
                    "max_response_tokens": 2048,
                },
                "decoding": {
                    "training_temperature": 1.0,
                    "training_top_p": 1.0,
                    "validation_temperature": 0.6,
                    "validation_top_p": 0.95,
                    "validation_rollouts_per_prompt": 1,
                },
                "schedule": {
                    "max_steps": 500,
                    "save_every_steps": 100,
                    "validate_every_steps": 100,
                    "validate_before_training": False,
                    "checkpoint_selection": "global_step_500",
                },
                "scale_specific": {
                    "3B": {
                        "base_model": (
                            "Qwen/Qwen2.5-VL-3B-Instruct@"
                            "66285546d2b821cf421d4f5eb2576359d3770cd3"
                        ),
                        "save_limit": 1,
                        "find_last_checkpoint": False,
                        "load_checkpoint_path": None,
                    },
                    "7B": {
                        "base_model": (
                            "Qwen/Qwen2.5-VL-7B-Instruct@"
                            "cc594898137f460bfe9f0759e9844b3ce807cfb5"
                        ),
                        "save_limit": 1,
                        "find_last_checkpoint": False,
                        "load_checkpoint_path": None,
                    },
                },
            },
            "answer_prompt_sha256": _sha256_path(prompt_path),
            "vlmevalkit": {
                "repository": "https://github.com/open-compass/VLMEvalKit",
                "revision": "a8b12bf1c3737a33fc1de967c202f9c592b22e86",
            },
            "judge": {
                "repository_id": "Qwen/Qwen3-32B",
                "revision": "9216db5781bf21249d130ec9da846c4624c16137",
            },
            "evaluation_source_revision": EVALUATION_REVISION,
            "canonical_result_artifacts": [
                "maveryn/trace-eval-runs@4178a839b689babe16f8ac36f0de7b1b2c5ef36c",
                "maveryn/trace-eval-runs@4ca25af7a4d7daa644e6f35e070dbed1af078321",
            ],
        },
        "review_policy": {
            "approved_exact_copy": "May be copied byte-for-byte after its hash is verified.",
            "approved_for_public_adaptation": (
                "May be used only for the named destination after the listed scope/path "
                "adaptations and a second public-tree review."
            ),
            "default": "deny",
        },
        "dependency_review": {
            "status": "reviewed",
            "imports_removed_during_public_adaptation": [
                {
                    "import": "scripts/screenspot_json_contract.py",
                    "from": [
                        "scripts/run_external_benchmark_generation_api_queue.py",
                        "scripts/run_external_benchmark_generation_queue.py",
                        "scripts/run_external_benchmark_score_queue.py",
                        "scripts/run_official_vlmevalkit_saved_score.py",
                    ],
                    "reason": "ScreenSpot is not a trace_eval_v1 benchmark.",
                },
                {
                    "import": "scripts/trace_eval_archive_migration_lib.py",
                    "from": ["scripts/run_trace_eval_publish_worker.py"],
                    "reason": (
                        "The public worker publishes only a sanitized new run; private "
                        "repository migration and recovery operations are removed."
                    ),
                },
                {
                    "import": "scripts/build_rlvr_public_file_manifest.py",
                    "from": ["tests/test_rlvr_release_inputs.py"],
                    "reason": (
                        "The generator is an internal review tool; the public test validates "
                        "the checked-in source map and release inputs directly."
                    ),
                },
            ],
        },
        "files": sorted(entries, key=lambda item: item["destination_path"]),
        "denylist": list(HISTORICAL_DENYLIST),
    }
    manifest["counts"] = {
        "files": len(entries),
        "exact_copy": sum(
            entry["review_status"] == "approved_exact_copy" for entry in entries
        ),
        "public_adaptation": sum(
            entry["review_status"] == "approved_for_public_adaptation"
            for entry in entries
        ),
    }
    return manifest


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = _canonical_bytes(build_manifest())
    output = args.output.expanduser().resolve()
    if args.check:
        if not output.is_file() or output.read_bytes() != content:
            raise SystemExit(f"stale or missing public file manifest: {output}")
        print(f"Verified {output}")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
