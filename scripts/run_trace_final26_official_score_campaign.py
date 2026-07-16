#!/usr/bin/env python3
"""Score three saved Final26 campaigns without touching generation outputs.

This is orchestration only. It stages prediction workbooks into a clean tree,
then delegates benchmark behavior to the pinned VLMEvalKit evaluator, the
existing Final25 direct scorer, or the dedicated MME-Reasoning scorer.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
import queue
import shlex
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from final25_media_contract import (
    GENERATION_CONTRACT_VERSION,
    MEDIA_CONTRACT_VERSION,
    MEDIA_TRANSPORT,
    QWEN_MAX_IMAGE_PIXELS,
    QWEN_MIN_IMAGE_PIXELS,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
DEFAULT_VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
DEFAULT_EVAL_DEPS = REPO_ROOT / ".tmp" / "eval_deps"
DEFAULT_PYTHON = Path("/home/shadeform/venv/bin/python")
DEFAULT_LMU_DATA = Path("/dev/shm/trace_rlvr/LMUData")
DEFAULT_HF_HOME = Path("/dev/shm/trace_rlvr/huggingface")
DEFAULT_JUDGE_MODEL = Path("/dev/shm/trace_rlvr/final25_models/qwen3-32b-judge")
PINNED_VLMEVALKIT_COMMIT = "a8b12bf1c3737a33fc1de967c202f9c592b22e86"
CONTRACT_VERSION = "trace-final26-official-score-campaign-v1"

# These routes are intentionally explicit. Do not derive them from the legacy
# generic-extraction registry: this campaign replaces that route with the
# pinned dataset.evaluate implementation.
OFFICIAL_SCORE_KEYS = (
    "chartqapro",
    "wemath",
    "phyx_mini_mc",
    "mmmu_pro_vision",
    "mmstar",
    "spatialvizbench_cot",
    "cvbench_3d",
    "erqa",
    "blink",
    "countbenchqa",
    "countqa",
    "treebench",
    "puzzlevqa",
    "visualpuzzles",
    "mmvp",
)
DIRECT_SCORE_KEYS = (
    "chartmuseum",
    "charxivreason",
    "tablevqabench",
    "evochart",
    "mathvision",
    "mathvista",
    "mathverse",
    "physics",
    "screenspot",
    "logicvista",
)
MME_SCORE_KEY = "mme_reasoning"
ALL_SCORE_KEYS = (*DIRECT_SCORE_KEYS, *OFFICIAL_SCORE_KEYS, MME_SCORE_KEY)


@dataclass(frozen=True)
class Campaign:
    model: str
    slug: str
    root: Path


@dataclass(frozen=True)
class Workbook:
    benchmark_key: str
    alias: str
    run_name: str
    source: Path
    staged: Path
    sha256: str
    primary: bool


@dataclass(frozen=True)
class OfficialJob:
    campaign: Campaign
    workbook: Workbook
    output_dir: Path
    judge_kwargs: dict[str, Any]
    primary_metric: str | None
    primary_value_scale: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _default_endpoints() -> list[str]:
    return [f"http://127.0.0.1:{18100 + offset}/v1" for offset in range(8)]


def _normalize_endpoint(value: str) -> str:
    endpoint = value.strip().rstrip("/")
    for suffix in ("/chat/completions", "/completions"):
        if endpoint.endswith(suffix):
            endpoint = endpoint[: -len(suffix)]
    if not endpoint.startswith(("http://", "https://")):
        raise ValueError(f"Judge endpoint must be HTTP(S): {value!r}")
    return endpoint.rstrip("/")


def _chat_completions_url(endpoint: str) -> str:
    return _normalize_endpoint(endpoint) + "/chat/completions"


def _load_specs() -> dict[str, Any]:
    sys.path.insert(0, str(SCRIPTS_ROOT))
    from benchmark_queue_lib import spec_by_key
    from trace_final25_contract import (
        DEDICATED_SCORE_KEYS as CONTRACT_DEDICATED_KEYS,
        DIRECT_SCORE_KEYS as CONTRACT_DIRECT_KEYS,
        OFFICIAL_VLMEVAL_SCORE_KEYS as CONTRACT_OFFICIAL_KEYS,
    )

    if set(DIRECT_SCORE_KEYS) != set(CONTRACT_DIRECT_KEYS):
        raise RuntimeError("Final26 direct route disagrees with trace_final25_contract")
    if set(OFFICIAL_SCORE_KEYS) != set(CONTRACT_OFFICIAL_KEYS):
        raise RuntimeError("Final26 official route disagrees with trace_final25_contract")
    if set(CONTRACT_DEDICATED_KEYS) != {MME_SCORE_KEY}:
        raise RuntimeError("Final26 dedicated route must contain only MME-Reasoning")

    return {key: spec_by_key(key) for key in ALL_SCORE_KEYS}


def _source_run_root(campaign: Campaign, seed: int) -> Path:
    return campaign.root / f"seed_{seed}" / "runs"


def _run_dir(root: Path, key: str, slug: str, run_name: str) -> Path:
    return root / key / slug / run_name


def _canonical_prediction_files(spec: Any, source_dir: Path) -> tuple[Path, list[Path]]:
    alias_prediction = source_dir / f"{spec.alias}_predictions.xlsx"
    fallback_prediction = source_dir / "predictions.xlsx"
    if alias_prediction.is_file():
        primary = alias_prediction
    elif spec.key == "chartmuseum" and fallback_prediction.is_file():
        primary = fallback_prediction
    else:
        raise FileNotFoundError(
            f"Missing canonical prediction workbook for {spec.key}: expected {alias_prediction}"
        )

    extras: list[Path] = []
    if spec.key == "screenspot":
        for name in (
            "ScreenSpot_Desktop_predictions.xlsx",
            "ScreenSpot_Mobile_predictions.xlsx",
            "ScreenSpot_Web_predictions.xlsx",
        ):
            path = source_dir / name
            if path.is_file() and path != primary:
                extras.append(path)
    return primary, extras


def _discover_workbooks(
    campaigns: list[Campaign],
    *,
    seed: int,
    staged_run_root: Path,
    specs: dict[str, Any],
) -> dict[str, list[Workbook]]:
    result: dict[str, list[Workbook]] = {}
    failures: list[str] = []
    for campaign in campaigns:
        campaign_workbooks: list[Workbook] = []
        source_root = _source_run_root(campaign, seed)
        if not source_root.is_dir():
            failures.append(f"{campaign.slug}: missing generated run root {source_root}")
            result[campaign.slug] = campaign_workbooks
            continue
        for key in ALL_SCORE_KEYS:
            spec = specs[key]
            source_dir = _run_dir(source_root, key, campaign.slug, spec.run_name)
            try:
                primary, extras = _canonical_prediction_files(spec, source_dir)
            except FileNotFoundError as error:
                failures.append(str(error))
                continue
            staged_dir = _run_dir(staged_run_root, key, campaign.slug, spec.run_name)
            for source in (primary, *extras):
                campaign_workbooks.append(
                    Workbook(
                        benchmark_key=key,
                        alias=spec.alias,
                        run_name=spec.run_name,
                        source=source.resolve(),
                        staged=staged_dir / source.name,
                        sha256=_sha256(source),
                        primary=source == primary,
                    )
                )
        result[campaign.slug] = campaign_workbooks
    if failures:
        preview = "\n".join(f"  - {item}" for item in failures)
        raise FileNotFoundError(f"Final26 prediction preflight failed:\n{preview}")
    return result


def _primary_workbook(workbooks: dict[str, list[Workbook]], slug: str, key: str) -> Workbook:
    matches = [
        item
        for item in workbooks[slug]
        if item.benchmark_key == key and item.primary
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one primary workbook for {slug}/{key}, found {len(matches)}")
    return matches[0]


def _validate_media_generation_contract(generation: dict[str, Any]) -> None:
    expected = {
        "contract_version": GENERATION_CONTRACT_VERSION,
        "media_contract_version": MEDIA_CONTRACT_VERSION,
        "media_transport": MEDIA_TRANSPORT,
        "min_image_pixels": QWEN_MIN_IMAGE_PIXELS,
        "max_image_pixels": QWEN_MAX_IMAGE_PIXELS,
    }
    for field, value in expected.items():
        if generation.get(field) != value:
            raise ValueError(f"generation.{field}={generation.get(field)!r}, expected {value!r}")


def _validate_generation_inputs(
    campaigns: list[Campaign],
    workbooks: dict[str, list[Workbook]],
    *,
    seed: int,
) -> dict[str, dict[str, dict[str, Any]]]:
    import pandas as pd

    validated: dict[str, dict[str, dict[str, Any]]] = {}
    failures: list[str] = []
    expected_generation = {
        "temperature": 0.6,
        "top_p": 1.0,
        "top_k": -1,
        "presence_penalty": 0.0,
        "repetition_penalty": 1.0,
        "max_tokens": 4096,
        "seed": seed,
    }
    for campaign in campaigns:
        campaign_inputs: dict[str, dict[str, Any]] = {}
        snapshots: set[str] = set()
        for key in ALL_SCORE_KEYS:
            workbook = _primary_workbook(workbooks, campaign.slug, key)
            summary_path = workbook.source.parent / "generation_summary.json"
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                rows = int(summary["rows"])
                expected_rows = int(summary["expected_rows"])
                if rows <= 0 or rows != expected_rows:
                    raise ValueError(f"rows={rows} expected_rows={expected_rows}")
                if str(summary.get("model")) != campaign.model:
                    raise ValueError(f"model={summary.get('model')!r}")
                if str(summary.get("model_slug")) != campaign.slug:
                    raise ValueError(f"model_slug={summary.get('model_slug')!r}")

                generation = summary.get("generation") or {}
                for field, expected in expected_generation.items():
                    if generation.get(field) != expected:
                        raise ValueError(
                            f"generation.{field}={generation.get(field)!r}, expected {expected!r}"
                        )
                if generation.get("api_model") != campaign.slug:
                    raise ValueError(f"generation.api_model={generation.get('api_model')!r}")
                _validate_media_generation_contract(generation)
                snapshot = str(generation.get("dataset_snapshot_sha256") or "")
                if len(snapshot) != 64:
                    raise ValueError(f"invalid dataset snapshot {snapshot!r}")
                snapshots.add(snapshot)

                finish_reason = summary.get("finish_reason") or {}
                if not isinstance(finish_reason, dict) or set(finish_reason) - {"stop", "length"}:
                    raise ValueError(f"unexpected finish reasons {finish_reason!r}")
                if sum(int(value) for value in finish_reason.values()) != rows:
                    raise ValueError(f"finish reasons do not cover all {rows} rows: {finish_reason!r}")

                workbook_rows = len(pd.read_excel(workbook.source, usecols=[0]))
                if workbook_rows != rows:
                    raise ValueError(f"workbook rows={workbook_rows}, summary rows={rows}")
                artifact = Path(str((summary.get("artifacts") or {}).get("eval_file", "")))
                if artifact.resolve() != workbook.source:
                    raise ValueError(f"summary eval_file={artifact}, workbook={workbook.source}")
            except Exception as error:
                failures.append(f"{campaign.slug}/{key}: {error}")
                continue

            campaign_inputs[key] = {
                "rows": rows,
                "generation_summary": str(summary_path),
                "generation_summary_sha256": _sha256(summary_path),
                "dataset_snapshot_sha256": snapshot,
                "finish_reason": finish_reason,
            }
        if len(snapshots) > 1:
            failures.append(
                f"{campaign.slug}: inconsistent dataset snapshots across generation summaries: "
                f"{sorted(snapshots)}"
            )
        validated[campaign.slug] = campaign_inputs
    if failures:
        raise RuntimeError("Generation input preflight failed:\n  - " + "\n  - ".join(failures))
    return validated


def _validate_dataset_manifest(path: Path, lmu_data: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Dataset manifest does not exist: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("vlmevalkit_commit") != PINNED_VLMEVALKIT_COMMIT:
        raise RuntimeError(
            "Dataset manifest VLMEvalKit commit mismatch: "
            f"{manifest.get('vlmevalkit_commit')!r}"
        )
    if int(manifest.get("failed", -1)) != 0 or int(manifest.get("ready", -1)) != 26:
        raise RuntimeError(
            f"Dataset manifest is not ready for all26: ready={manifest.get('ready')} "
            f"failed={manifest.get('failed')}"
        )
    view = manifest.get("dataset_views", {}).get("all26")
    if not isinstance(view, list) or set(view) != set(ALL_SCORE_KEYS):
        raise RuntimeError("Dataset manifest all26 view does not match the scoring route")
    datasets = manifest.get("datasets", {})
    not_ready = [key for key in ALL_SCORE_KEYS if datasets.get(key, {}).get("status") != "ready"]
    if not_ready:
        raise RuntimeError(f"Dataset receipts are not ready: {not_ready}")
    recorded_root = Path(str(manifest.get("lmu_data_root", ""))).resolve()
    if recorded_root != lmu_data.resolve():
        raise RuntimeError(
            f"Dataset manifest uses LMUData={recorded_root}, requested {lmu_data.resolve()}"
        )
    return manifest


def _base_env(args: argparse.Namespace) -> dict[str, str]:
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("TRACE_FINAL25_HF_"):
            env.pop(key, None)
    for key in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        env.pop(key, None)

    required_python_paths = [
        args.eval_deps,
        REPO_ROOT,
        SCRIPTS_ROOT,
        args.vlmeval_root,
        args.vlmeval_root / "scripts",
    ]
    previous = [item for item in env.get("PYTHONPATH", "").split(os.pathsep) if item]
    env["PYTHONPATH"] = os.pathsep.join(
        [str(path) for path in required_python_paths] + previous
    )
    env["LMUData"] = str(args.lmu_data)
    env["HF_HOME"] = str(args.hf_home)
    env["TOKENIZERS_PARALLELISM"] = "false"
    # Pinned VLMEvalKit enables its OpenAI-compatible judge path only for
    # syntactically valid ``sk-`` keys. The endpoint is still localhost-only.
    env["OPENAI_API_KEY"] = "sk-local"
    env["LOCAL_LLM"] = args.judge_api_model
    env["CUDA_VISIBLE_DEVICES"] = ""
    return env


def _validate_runtime(args: argparse.Namespace, env: dict[str, str]) -> None:
    if not args.python.is_file() or not os.access(args.python, os.X_OK):
        raise FileNotFoundError(f"Evaluation Python is not executable: {args.python}")
    if not args.eval_deps.is_dir():
        raise FileNotFoundError(f"Evaluation dependency target is missing: {args.eval_deps}")
    if not args.vlmeval_root.is_dir():
        raise FileNotFoundError(f"VLMEvalKit checkout is missing: {args.vlmeval_root}")
    commit = _git(args.vlmeval_root, "rev-parse", "HEAD")
    if commit != PINNED_VLMEVALKIT_COMMIT:
        raise RuntimeError(
            f"VLMEvalKit must be pinned to {PINNED_VLMEVALKIT_COMMIT}, found {commit}"
        )
    if not args.lmu_data.is_dir():
        raise FileNotFoundError(f"LMUData root is missing: {args.lmu_data}")
    if not args.hf_home.is_dir():
        raise FileNotFoundError(f"HF_HOME cache is missing: {args.hf_home}")
    if not args.judge_model.is_dir():
        raise FileNotFoundError(f"Qwen3 judge model is missing: {args.judge_model}")
    probe = subprocess.run(
        [
            str(args.python),
            "-c",
            "import pandas, tabulate; import vlmeval",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    if probe.returncode:
        detail = (probe.stderr or probe.stdout).strip()
        raise RuntimeError(f"Evaluation dependency preflight failed: {detail}")


def _judge_kwargs(args: argparse.Namespace, key: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": args.judge_api_model,
        "nproc": args.eval_nproc,
        "temperature": 0,
        "max_tokens": args.judge_max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    # Pinned PhyX requires an explicit official validation mode. This is the
    # multiple-choice benchmark, so use its string-level official scorer.
    if key == "phyx_mini_mc":
        kwargs["valid_type"] = "STR"
    return kwargs


def _primary_metric_contract(key: str) -> tuple[str | None, str]:
    # Most datasets expose one primary metric through report_primary_metric.
    # Explicit exceptions are kept here rather than changing evaluator output.
    if key == "wemath":
        return "Score (Strict)", "percent"
    return None, "auto"


def _contract(
    args: argparse.Namespace,
    campaigns: list[Campaign],
    workbooks: dict[str, list[Workbook]],
    generation_inputs: dict[str, dict[str, dict[str, Any]]],
    dataset_manifest: dict[str, Any],
    endpoints: list[str],
) -> dict[str, Any]:
    sources = []
    for campaign in campaigns:
        for workbook in workbooks[campaign.slug]:
            sources.append(
                {
                    "model": campaign.model,
                    "model_slug": campaign.slug,
                    "campaign_root": str(campaign.root),
                    "benchmark_key": workbook.benchmark_key,
                    "alias": workbook.alias,
                    "run_name": workbook.run_name,
                    "source": str(workbook.source),
                    "staged": str(workbook.staged),
                    "sha256": workbook.sha256,
                    "primary": workbook.primary,
                }
            )
    return {
        "contract_version": CONTRACT_VERSION,
        "seed": args.seed,
        "routes": {
            "official_vlmevalkit": list(OFFICIAL_SCORE_KEYS),
            "direct": list(DIRECT_SCORE_KEYS),
            "mme_reasoning": [MME_SCORE_KEY],
        },
        "campaigns": [
            {"model": item.model, "model_slug": item.slug, "campaign_root": str(item.root)}
            for item in campaigns
        ],
        "sources": sources,
        "generation_inputs": generation_inputs,
        "dataset_manifest": {
            "path": str(args.dataset_manifest),
            "sha256": _sha256(args.dataset_manifest),
            "dataset_snapshot_sha256": dataset_manifest.get("dataset_snapshot_sha256"),
            "all26_snapshot_sha256": dataset_manifest.get("view_snapshot_sha256", {}).get("all26"),
            "vlmevalkit_commit": dataset_manifest.get("vlmevalkit_commit"),
        },
        "judge": {
            "api_model": args.judge_api_model,
            "model_path": str(args.judge_model),
            "endpoints": endpoints,
            "kwargs_by_benchmark": {
                key: _judge_kwargs(args, key) for key in OFFICIAL_SCORE_KEYS
            },
            "api_parallelism": args.judge_api_parallelism,
            "api_batch_size": args.judge_api_batch_size,
            "api_batches_per_endpoint": args.judge_api_batches_per_endpoint,
            "api_max_batch_chars": args.judge_api_max_batch_chars,
            "cache_contract_version": args.judge_cache_contract_version,
        },
        "scoring_implementation": {
            str(path.relative_to(REPO_ROOT)): _sha256(path)
            for path in (
                Path(__file__).resolve(),
                SCRIPTS_ROOT / "run_official_vlmevalkit_saved_score.py",
                SCRIPTS_ROOT / "run_external_benchmark_score_queue.py",
                SCRIPTS_ROOT / "run_mme_reasoning_eval.py",
                SCRIPTS_ROOT / "trace_final25_contract.py",
                REPO_ROOT / "evaluation" / "final25" / "suite.v1.json",
            )
        },
        "runtime": {
            "python": str(args.python),
            "eval_deps": str(args.eval_deps),
            "vlmeval_root": str(args.vlmeval_root),
            "lmu_data": str(args.lmu_data),
            "hf_home": str(args.hf_home),
        },
    }


def _prepare_score_root(score_root: Path, contract: dict[str, Any], resume: bool) -> str:
    manifest_path = score_root / "score_campaign_manifest.json"
    if score_root.exists() and any(score_root.iterdir()):
        if not resume:
            raise FileExistsError(
                f"Score root is not empty: {score_root}; pass --resume only for this exact contract"
            )
        if not manifest_path.is_file():
            raise RuntimeError(f"Cannot resume without {manifest_path}")
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("contract") != contract:
            raise RuntimeError("Existing score root manifest does not match source hashes/judge contract")
        return str(existing["contract_sha256"])

    score_root.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    contract_sha256 = hashlib.sha256(encoded).hexdigest()
    _write_json(
        manifest_path,
        {
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "contract_sha256": contract_sha256,
            "contract": contract,
        },
    )
    return contract_sha256


def _stage_workbooks(workbooks: dict[str, list[Workbook]], *, resume: bool) -> None:
    for items in workbooks.values():
        for workbook in items:
            workbook.staged.parent.mkdir(parents=True, exist_ok=True)
            if workbook.staged.exists():
                if not resume:
                    raise FileExistsError(workbook.staged)
                if _sha256(workbook.staged) != workbook.sha256:
                    shutil.copy2(workbook.source, workbook.staged)
                    if _sha256(workbook.staged) != workbook.sha256:
                        raise RuntimeError(f"Restaged workbook hash mismatch: {workbook.staged}")
                    print(f"[stage:restore] {workbook.staged}", flush=True)
                continue
            shutil.copy2(workbook.source, workbook.staged)
            if _sha256(workbook.staged) != workbook.sha256:
                raise RuntimeError(f"Staged workbook hash mismatch: {workbook.staged}")


def _command_text(command: list[str]) -> str:
    return shlex.join(command)


def _run_logged(
    command: list[str],
    *,
    env: dict[str, str],
    log_path: Path,
    label: str,
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[score:start] {label} log={log_path}", flush=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"\n[{dt.datetime.now(dt.timezone.utc).isoformat()}] {_command_text(command)}\n")
        log.flush()
        result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"{label} exited {result.returncode}; see {log_path}")
    print(f"[score:done] {label}", flush=True)


def _official_complete(job: OfficialJob) -> bool:
    scores_path = job.output_dir / "scores.json"
    if not scores_path.is_file():
        return False
    summary = json.loads(scores_path.read_text(encoding="utf-8"))
    provenance = summary.get("provenance", {})
    source_sha256 = provenance.get("source_prediction_sha256", provenance.get("prediction_sha256"))
    if source_sha256 != job.workbook.sha256:
        raise RuntimeError(f"Official score source hash mismatch: {scores_path}")
    if provenance.get("judge_kwargs") != job.judge_kwargs:
        raise RuntimeError(f"Official score judge contract mismatch: {scores_path}")
    return True


def _validate_score_outputs(
    campaigns: list[Campaign],
    keys: tuple[str, ...],
    *,
    benchmark_root: Path,
    specs: dict[str, Any],
    generation_inputs: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    completed: list[dict[str, Any]] = []
    failures: list[str] = []
    for campaign in campaigns:
        for key in keys:
            path = _run_dir(
                benchmark_root,
                key,
                campaign.slug,
                specs[key].run_name,
            ) / "scores.json"
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                score = float(payload["score"])
                if not math.isfinite(score):
                    raise ValueError(f"non-finite score {score!r}")
                rows = int(payload["rows"])
                expected_rows = int(generation_inputs[campaign.slug][key]["rows"])
                if rows != expected_rows:
                    raise ValueError(f"rows={rows}, expected {expected_rows}")
                if payload.get("model") is not None and str(payload["model"]) != campaign.model:
                    raise ValueError(f"model={payload.get('model')!r}")
                if payload.get("model_slug") is not None and str(payload["model_slug"]) != campaign.slug:
                    raise ValueError(f"model_slug={payload.get('model_slug')!r}")
            except Exception as error:
                failures.append(f"{campaign.slug}/{key}: {path}: {error}")
                continue
            completed.append(
                {
                    "benchmark_key": key,
                    "model": campaign.model,
                    "model_slug": campaign.slug,
                    "rows": rows,
                    "score": score,
                    "scores_path": str(path),
                    "scores_sha256": _sha256(path),
                }
            )
    if failures:
        raise RuntimeError("Score output validation failed:\n  - " + "\n  - ".join(failures))
    return completed


def _official_command(args: argparse.Namespace, job: OfficialJob) -> list[str]:
    command = [
        str(args.python),
        str(SCRIPTS_ROOT / "run_official_vlmevalkit_saved_score.py"),
        "--benchmark-key",
        job.workbook.benchmark_key,
        "--prediction-xlsx",
        str(job.workbook.staged),
        "--output-dir",
        str(job.output_dir),
        "--model",
        job.campaign.model,
        "--model-slug",
        job.campaign.slug,
        "--run-name",
        job.workbook.run_name,
        "--judge-kwargs-json",
        json.dumps(job.judge_kwargs, sort_keys=True, separators=(",", ":")),
        "--primary-value-scale",
        job.primary_value_scale,
        "--vlmeval-root",
        str(args.vlmeval_root),
    ]
    if job.primary_metric:
        command.extend(["--primary-metric", job.primary_metric])
    return command


def _direct_command(
    args: argparse.Namespace,
    campaign: Campaign,
    *,
    staged_run_root: Path,
    benchmark_root: Path,
    queue_root: Path,
    endpoints: list[str],
    contract_sha256: str,
) -> list[str]:
    command = [
        str(args.python),
        str(SCRIPTS_ROOT / "run_external_benchmark_score_queue.py"),
        "--model",
        campaign.model,
        "--model-slug",
        campaign.slug,
        "--run-set",
        "trace_final25",
        "--seed",
        str(args.seed),
        "--run-root",
        str(staged_run_root),
        "--benchmark-root",
        str(benchmark_root),
        "--queue-root",
        str(queue_root),
        "--queue-name",
        f"official-final26-{campaign.slug}-{contract_sha256[:16]}-direct",
        "--worker-id",
        f"official-final26-{campaign.slug}-direct",
        "--only",
        *DIRECT_SCORE_KEYS,
        "--eval-judge-model",
        "exact_matching",
        "--eval-nproc",
        str(args.eval_nproc),
        "--judge-model",
        str(args.judge_model),
        "--judge-api-model",
        args.judge_api_model,
        "--judge-api-tokenizer-model",
        str(args.judge_model),
        "--judge-api-parallelism",
        str(args.judge_api_parallelism),
        "--judge-api-batch-size",
        str(args.judge_api_batch_size),
        "--judge-api-batches-per-endpoint",
        str(args.judge_api_batches_per_endpoint),
        "--judge-api-max-batch-chars",
        str(args.judge_api_max_batch_chars),
        "--judge-cache-contract-version",
        args.judge_cache_contract_version,
        "--stop-on-error",
    ]
    for endpoint in endpoints:
        command.extend(["--judge-api-base", endpoint])
    return command


def _mme_command(
    args: argparse.Namespace,
    campaign: Campaign,
    *,
    staged_run_root: Path,
    benchmark_root: Path,
    endpoints: list[str],
) -> list[str]:
    command = [
        str(args.python),
        str(SCRIPTS_ROOT / "run_mme_reasoning_eval.py"),
        "score",
        "--model",
        campaign.model,
        "--model-slug",
        campaign.slug,
        "--seed",
        str(args.seed),
        "--run-root",
        str(staged_run_root),
        "--benchmark-root",
        str(benchmark_root),
        "--judge-model",
        str(args.judge_model),
        "--judge-api-model",
        args.judge_api_model,
        "--judge-api-tokenizer-model",
        str(args.judge_model),
        "--judge-api-parallelism",
        str(args.judge_api_parallelism),
        "--judge-api-batch-size",
        str(args.judge_api_batch_size),
        "--judge-api-batches-per-endpoint",
        str(args.judge_api_batches_per_endpoint),
        "--judge-api-max-batch-chars",
        str(args.judge_api_max_batch_chars),
        "--judge-cache-contract-version",
        args.judge_cache_contract_version,
    ]
    for endpoint in endpoints:
        command.extend(["--judge-api-base", endpoint])
    return command


def _check_endpoints(endpoints: list[str], model: str) -> None:
    failures: list[str] = []
    for endpoint in endpoints:
        url = endpoint.rstrip("/") + "/models"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                payload = json.load(response)
            models = [str(item.get("id")) for item in payload.get("data", [])]
            if model not in models:
                failures.append(f"{url}: served models={models}")
        except Exception as error:
            failures.append(f"{url}: {error}")
    if failures:
        raise RuntimeError("Judge endpoint preflight failed:\n  - " + "\n  - ".join(failures))


def _official_jobs(
    args: argparse.Namespace,
    campaigns: list[Campaign],
    workbooks: dict[str, list[Workbook]],
    benchmark_root: Path,
) -> list[OfficialJob]:
    jobs: list[OfficialJob] = []
    for campaign in campaigns:
        for key in OFFICIAL_SCORE_KEYS:
            workbook = _primary_workbook(workbooks, campaign.slug, key)
            primary_metric, value_scale = _primary_metric_contract(key)
            jobs.append(
                OfficialJob(
                    campaign=campaign,
                    workbook=workbook,
                    output_dir=_run_dir(
                        benchmark_root,
                        key,
                        campaign.slug,
                        workbook.run_name,
                    ),
                    judge_kwargs=_judge_kwargs(args, key),
                    primary_metric=primary_metric,
                    primary_value_scale=value_scale,
                )
            )
    return jobs


def _run_official_phase(
    args: argparse.Namespace,
    jobs: list[OfficialJob],
    *,
    endpoints: list[str],
    env: dict[str, str],
    log_root: Path,
) -> None:
    pending = [job for job in jobs if not (args.resume and _official_complete(job))]
    skipped = len(jobs) - len(pending)
    print(f"[official:plan] pending={len(pending)} skipped={skipped}", flush=True)
    if not pending:
        return

    endpoint_pool: queue.Queue[str] = queue.Queue()
    for endpoint in endpoints:
        endpoint_pool.put(endpoint)

    def execute(job: OfficialJob) -> None:
        endpoint = endpoint_pool.get()
        try:
            job_env = env.copy()
            job_env["OPENAI_API_BASE"] = _chat_completions_url(endpoint)
            label = f"official/{job.campaign.slug}/{job.workbook.benchmark_key}"
            _run_logged(
                _official_command(args, job),
                env=job_env,
                log_path=log_root / "official" / job.campaign.slug / f"{job.workbook.benchmark_key}.log",
                label=label,
            )
        finally:
            endpoint_pool.put(endpoint)

    errors: list[str] = []
    workers = min(args.official_workers, len(endpoints), len(pending))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(execute, job): job for job in pending}
        for future in concurrent.futures.as_completed(futures):
            job = futures[future]
            try:
                future.result()
            except Exception as error:
                errors.append(f"{job.campaign.slug}/{job.workbook.benchmark_key}: {error}")
    if errors:
        raise RuntimeError("Official scoring failures:\n  - " + "\n  - ".join(errors))


def _print_plan(
    args: argparse.Namespace,
    campaigns: list[Campaign],
    jobs: list[OfficialJob],
    *,
    staged_run_root: Path,
    benchmark_root: Path,
    queue_root: Path,
    endpoints: list[str],
    contract_sha256: str,
) -> None:
    print(
        f"[preflight:ok] campaigns={len(campaigns)} benchmarks={len(ALL_SCORE_KEYS)} "
        f"official_jobs={len(jobs)} direct_jobs={len(campaigns) * len(DIRECT_SCORE_KEYS)} "
        f"mme_jobs={len(campaigns)} endpoints={len(endpoints)} contract={contract_sha256}"
    )
    for job in jobs:
        print(
            f"[plan:official] endpoint=<leased> "
            f"{_command_text(_official_command(args, job))}"
        )
    for campaign in campaigns:
        print(
            "[plan:direct] "
            + _command_text(
                _direct_command(
                    args,
                    campaign,
                    staged_run_root=staged_run_root,
                    benchmark_root=benchmark_root,
                    queue_root=queue_root,
                    endpoints=endpoints,
                    contract_sha256=contract_sha256,
                )
            )
        )
        print(
            "[plan:mme] "
            + _command_text(
                _mme_command(
                    args,
                    campaign,
                    staged_run_root=staged_run_root,
                    benchmark_root=benchmark_root,
                    endpoints=endpoints,
                )
            )
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score three saved Final26 campaigns in an isolated official-evaluation tree."
    )
    parser.add_argument(
        "--campaign",
        action="append",
        nargs=3,
        required=True,
        metavar=("MODEL", "MODEL_SLUG", "CAMPAIGN_ROOT"),
        help="Repeat exactly three times; CAMPAIGN_ROOT contains seed_<seed>/runs.",
    )
    parser.add_argument("--score-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--python", type=Path, default=DEFAULT_PYTHON)
    parser.add_argument("--eval-deps", type=Path, default=DEFAULT_EVAL_DEPS)
    parser.add_argument("--vlmeval-root", type=Path, default=DEFAULT_VLMEVAL_ROOT)
    parser.add_argument("--lmu-data", type=Path, default=DEFAULT_LMU_DATA)
    parser.add_argument("--hf-home", type=Path, default=DEFAULT_HF_HOME)
    parser.add_argument("--dataset-manifest", type=Path)
    parser.add_argument("--judge-model", type=Path, default=DEFAULT_JUDGE_MODEL)
    parser.add_argument("--judge-api-model", default="qwen3-32b-judge")
    parser.add_argument("--judge-endpoint", action="append", default=[])
    parser.add_argument("--judge-max-tokens", type=int, default=256)
    parser.add_argument("--eval-nproc", type=int, default=16)
    parser.add_argument("--official-workers", type=int, default=8)
    parser.add_argument("--judge-api-parallelism", type=int, default=64)
    parser.add_argument("--judge-api-batch-size", type=int, default=64)
    parser.add_argument("--judge-api-batches-per-endpoint", type=int, default=1)
    parser.add_argument("--judge-api-max-batch-chars", type=int, default=200_000)
    parser.add_argument("--judge-cache-contract-version", default="trace-persistent-judge-v2")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--preflight", "--dry-run", action="store_true", dest="preflight")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if len(args.campaign) != 3:
        raise SystemExit(f"error: pass exactly three --campaign descriptors, got {len(args.campaign)}")
    if args.seed < 0 or args.eval_nproc < 1 or args.official_workers < 1:
        raise SystemExit("error: seed must be non-negative and worker counts must be positive")
    if args.judge_max_tokens < 1:
        raise SystemExit("error: --judge-max-tokens must be positive")

    campaigns = [
        Campaign(model=model, slug=slug, root=Path(root).expanduser().resolve())
        for model, slug, root in args.campaign
    ]
    if len({item.slug for item in campaigns}) != len(campaigns):
        raise SystemExit("error: campaign model slugs must be unique")

    args.score_root = args.score_root.expanduser().resolve()
    # Keep the venv launcher path; resolving its symlink would silently select
    # the system interpreter and drop the venv site-packages.
    args.python = args.python.expanduser().absolute()
    args.eval_deps = args.eval_deps.expanduser().resolve()
    args.vlmeval_root = args.vlmeval_root.expanduser().resolve()
    args.lmu_data = args.lmu_data.expanduser().resolve()
    args.hf_home = args.hf_home.expanduser().resolve()
    args.judge_model = args.judge_model.expanduser().resolve()
    args.dataset_manifest = (
        args.dataset_manifest.expanduser().resolve()
        if args.dataset_manifest
        else args.lmu_data / "trace_final25_dataset_manifest.json"
    )
    endpoints = list(dict.fromkeys(_normalize_endpoint(item) for item in (args.judge_endpoint or _default_endpoints())))
    if not endpoints:
        raise SystemExit("error: at least one judge endpoint is required")

    staged_run_root = args.score_root / f"seed_{args.seed}" / "runs"
    benchmark_root = args.score_root / f"seed_{args.seed}" / "benchmark"
    queue_root = args.score_root / f"seed_{args.seed}" / "queues"
    log_root = args.score_root / "logs"

    specs = _load_specs()
    env = _base_env(args)
    _validate_runtime(args, env)
    dataset_manifest = _validate_dataset_manifest(args.dataset_manifest, args.lmu_data)
    workbooks = _discover_workbooks(
        campaigns,
        seed=args.seed,
        staged_run_root=staged_run_root,
        specs=specs,
    )
    generation_inputs = _validate_generation_inputs(
        campaigns,
        workbooks,
        seed=args.seed,
    )
    contract = _contract(
        args,
        campaigns,
        workbooks,
        generation_inputs,
        dataset_manifest,
        endpoints,
    )
    contract_sha256 = hashlib.sha256(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    jobs = _official_jobs(args, campaigns, workbooks, benchmark_root)

    if args.preflight:
        _check_endpoints(endpoints, args.judge_api_model)
        _print_plan(
            args,
            campaigns,
            jobs,
            staged_run_root=staged_run_root,
            benchmark_root=benchmark_root,
            queue_root=queue_root,
            endpoints=endpoints,
            contract_sha256=contract_sha256,
        )
        return

    _check_endpoints(endpoints, args.judge_api_model)
    contract_sha256 = _prepare_score_root(args.score_root, contract, args.resume)
    _stage_workbooks(workbooks, resume=args.resume)

    _run_official_phase(
        args,
        jobs,
        endpoints=endpoints,
        env=env,
        log_root=log_root,
    )
    _validate_score_outputs(
        campaigns,
        OFFICIAL_SCORE_KEYS,
        benchmark_root=benchmark_root,
        specs=specs,
        generation_inputs=generation_inputs,
    )
    for campaign in campaigns:
        _run_logged(
            _direct_command(
                args,
                campaign,
                staged_run_root=staged_run_root,
                benchmark_root=benchmark_root,
                queue_root=queue_root,
                endpoints=endpoints,
                contract_sha256=contract_sha256,
            ),
            env=env,
            log_path=log_root / "direct" / f"{campaign.slug}.log",
            label=f"direct/{campaign.slug}",
        )
        _validate_score_outputs(
            [campaign],
            DIRECT_SCORE_KEYS,
            benchmark_root=benchmark_root,
            specs=specs,
            generation_inputs=generation_inputs,
        )
    for campaign in campaigns:
        mme_output = _run_dir(
            benchmark_root,
            MME_SCORE_KEY,
            campaign.slug,
            specs[MME_SCORE_KEY].run_name,
        )
        if args.resume and (mme_output / "scores.json").is_file():
            try:
                _validate_score_outputs(
                    [campaign],
                    (MME_SCORE_KEY,),
                    benchmark_root=benchmark_root,
                    specs=specs,
                    generation_inputs=generation_inputs,
                )
            except RuntimeError:
                print(f"[score:rerun] mme/{campaign.slug} existing output is invalid", flush=True)
            else:
                print(f"[score:skip] mme/{campaign.slug}", flush=True)
                continue
        _run_logged(
            _mme_command(
                args,
                campaign,
                staged_run_root=staged_run_root,
                benchmark_root=benchmark_root,
                endpoints=endpoints,
            ),
            env=env,
            log_path=log_root / "mme_reasoning" / f"{campaign.slug}.log",
            label=f"mme/{campaign.slug}",
        )
        _validate_score_outputs(
            [campaign],
            (MME_SCORE_KEY,),
            benchmark_root=benchmark_root,
            specs=specs,
            generation_inputs=generation_inputs,
        )
    completed = _validate_score_outputs(
        campaigns,
        ALL_SCORE_KEYS,
        benchmark_root=benchmark_root,
        specs=specs,
        generation_inputs=generation_inputs,
    )
    _write_json(
        args.score_root / "score_campaign_completion.json",
        {
            "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "contract_sha256": contract_sha256,
            "expected_slices": len(campaigns) * len(ALL_SCORE_KEYS),
            "completed_slices": len(completed),
            "slices": completed,
        },
    )
    print(f"[campaign:done] score_root={args.score_root}", flush=True)


if __name__ == "__main__":
    main()
