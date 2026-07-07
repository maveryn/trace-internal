"""Run the current TRACE task calibration sweep.

The sweep is intentionally task-at-a-time and resumable.  It builds one fixed
50-sample dataset per task, exports the matching task-review workbook, probes
each calibration model, exports solve-rate workbooks, and writes an aggregate
status file under review/.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
RLVR_ROOT = REPO_ROOT / "rlvr"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import trace.tasks  # noqa: F401  # Register task classes.
from trace.core.taxonomy import resolve_task_taxonomy
from trace.tasks.registry import list_default_task_ids


@dataclass(frozen=True)
class ModelSpec:
    slug: str
    model_id: str
    response_cap_threshold: float


MODEL_SPECS: dict[str, ModelSpec] = {
    "qwen25vl7b": ModelSpec(
        slug="qwen25vl7b",
        model_id="Qwen/Qwen2.5-VL-7B-Instruct",
        response_cap_threshold=0.25,
    ),
    "qwen3vl8b": ModelSpec(
        slug="qwen3vl8b",
        model_id="Qwen/Qwen3-VL-8B-Instruct",
        response_cap_threshold=0.25,
    ),
    "qwen3vl4b": ModelSpec(
        slug="qwen3vl4b",
        model_id="Qwen/Qwen3-VL-4B-Instruct",
        response_cap_threshold=0.25,
    ),
}


HARD_FRACTION_THRESHOLD = 0.50
EASY_FRACTION_THRESHOLD = 0.25
MEAN_SOLVE_RATE_MIN = 0.10
MEAN_SOLVE_RATE_MAX = 0.80
SAMPLE_DISTRIBUTION_MIN_UNIQUE_ANSWERS = 4
SAMPLE_DISTRIBUTION_MAX_ANSWER_FREQUENCY = 1.0 / 3.0
SAMPLE_DISTRIBUTION_VALIDATION_MAX_ATTEMPTS = 5
CALIBRATION_SOURCE_FINGERPRINT_VERSION = "v1"
CALIBRATION_FINGERPRINT_SKIP_DIRS = frozenset({"__pycache__", ".pytest_cache", ".mypy_cache"})
CALIBRATION_FINGERPRINT_SKIP_SUFFIXES = frozenset({".pyc", ".pyo", ".tmp", ".swp"})
CURRENT_CALIBRATION_REVIEW_DIR = "review/calibration/50x8_qwen25vl3b_prompt_pilot_seed20260703"

SERVER_BASE_URL_DEFAULTS: dict[str, str] = {
    "qwen25vl7b": "http://127.0.0.1:8002/v1",
    "qwen3vl8b": "http://127.0.0.1:8001/v1",
}

SERVER_ENDPOINT_POOLS: dict[str, tuple[str, ...]] = {
    "qwen25vl7b": (
        "http://127.0.0.1:8002/v1",
    ),
}

MAX_TOKENS_DEFAULTS: dict[str, int] = {
    "qwen25vl7b": 2048,
    "qwen3vl8b": 4096,
    "qwen3vl4b": 4096,
}

MAX_MODEL_LEN_DEFAULTS: dict[str, int] = {
    "qwen25vl7b": 4096,
    "qwen3vl8b": 8192,
    "qwen3vl4b": 8192,
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="", help="Comma-separated task ids. Defaults to all active defaults.")
    parser.add_argument("--domain", action="append", default=[], help="Restrict to one public domain. Repeatable.")
    parser.add_argument("--scene", action="append", default=[], help="Restrict to <domain>/<scene_id>. Repeatable.")
    parser.add_argument("--start-at", default="", help="Start at this task id after sorting.")
    parser.add_argument("--start-after", default="", help="Start after this task id after sorting.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of tasks to process.")
    parser.add_argument("--models", default="qwen25vl7b", help="Comma-separated model aliases or HF ids.")
    parser.add_argument("--seed", type=int, default=20260507)
    parser.add_argument("--sample-count", type=int, default=50)
    parser.add_argument("--rollouts-per-prompt", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=400)
    parser.add_argument("--retry-batch-size", type=int, default=200)
    parser.add_argument("--max-prompt-length", type=int, default=2048)
    parser.add_argument("--max-tokens", type=int, default=0)
    parser.add_argument("--max-model-len", type=int, default=0)
    parser.add_argument("--max-num-batched-tokens", type=int, default=24576)
    parser.add_argument("--max-num-seqs", type=int, default=1600)
    parser.add_argument("--max-pixels", type=int, default=1280000)
    parser.add_argument("--gpu", default=os.environ.get("CUDA_VISIBLE_DEVICES", "0").split(",")[0] or "0")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--gpu-wait-interval", type=int, default=60)
    parser.add_argument("--gpu-max-used-mb", type=int, default=1024)
    parser.add_argument("--gpu-max-utilization", type=int, default=10)
    parser.add_argument("--no-wait-for-gpu", action="store_true")
    parser.add_argument(
        "--probe-backend",
        choices=("local_vllm", "openai_server"),
        default=os.environ.get("TRACE_PROBE_BACKEND", "openai_server"),
        help="Generation backend for trace_curriculum_probe.py.",
    )
    parser.add_argument("--server-base-url", default=os.environ.get("TRACE_VLLM_BASE_URL", ""))
    parser.add_argument("--server-api-key", default=os.environ.get("TRACE_VLLM_API_KEY", "EMPTY"))
    parser.add_argument("--server-model", default=os.environ.get("TRACE_VLLM_SERVED_MODEL", ""))
    parser.add_argument("--server-timeout", type=float, default=float(os.environ.get("TRACE_VLLM_TIMEOUT", "600")))
    parser.add_argument("--server-max-retries", type=int, default=int(os.environ.get("TRACE_VLLM_MAX_RETRIES", "3")))
    parser.add_argument("--server-concurrency", type=int, default=int(os.environ.get("TRACE_VLLM_CONCURRENCY", "128")))
    parser.add_argument("--server-pool-lock-root", default=os.environ.get("TRACE_VLLM_LOCK_ROOT", "logs/vllm/locks"))
    parser.add_argument("--server-pool-wait-interval", type=int, default=int(os.environ.get("TRACE_VLLM_POOL_WAIT_INTERVAL", "30")))
    parser.add_argument("--no-server-pool-locks", action="store_true")
    parser.add_argument("--output-root", default="out/calibration/current")
    parser.add_argument("--probe-root", default="rlvr/outputs/calibration/current")
    parser.add_argument("--review-root", default="review/task-reviews")
    parser.add_argument(
        "--status-json",
        default=f"{CURRENT_CALIBRATION_REVIEW_DIR}/latest_single_task_calibration_sweep_status.json",
        help="Single-sweep status output. The global calibration status is derived from task_status_records.json.",
    )
    parser.add_argument(
        "--status-md",
        default=f"{CURRENT_CALIBRATION_REVIEW_DIR}/latest_single_task_calibration_sweep_status.md",
        help="Single-sweep Markdown output. The global calibration status is derived from task_status_records.json.",
    )
    parser.add_argument(
        "--calibration-baseline",
        default="v0",
        help=(
            "Artifact baseline label for the current repo calibration pass. "
            "Existing artifacts without this exact baseline metadata are treated as stale."
        ),
    )
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--parquet-cpu-count", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="Rebuild/reprobe/re-export everything selected.")
    parser.add_argument("--force-build", action="store_true")
    parser.add_argument("--force-review", action="store_true")
    parser.add_argument("--force-models", action="store_true")
    parser.add_argument("--force-stats", action="store_true")
    review_export_group = parser.add_mutually_exclusive_group()
    review_export_group.add_argument(
        "--export-review",
        dest="skip_review",
        action="store_false",
        help=(
            "Also export the 50-row calibration sample into review/task-reviews. "
            "This replaces app review images/data and is not used for the normal "
            "browser review workflow."
        ),
    )
    review_export_group.add_argument(
        "--skip-review",
        dest="skip_review",
        action="store_true",
        help="Do not replace browser review artifacts with calibration samples. This is the default.",
    )
    parser.set_defaults(skip_review=True)
    parser.add_argument("--skip-models", action="store_true")
    parser.add_argument("--skip-scene-workbooks", action="store_true")
    parser.add_argument(
        "--sample-distribution-min-unique-answers",
        type=int,
        default=SAMPLE_DISTRIBUTION_MIN_UNIQUE_ANSWERS,
        help="Hard minimum unique-answer gate on the exact calibration parquet before model probing.",
    )
    parser.add_argument(
        "--sample-distribution-max-answer-frequency",
        type=float,
        default=SAMPLE_DISTRIBUTION_MAX_ANSWER_FREQUENCY,
        help="Hard maximum top-answer frequency gate on the exact calibration parquet before model probing.",
    )
    parser.add_argument(
        "--skip-sample-distribution-check",
        action="store_true",
        help="Debugging only: bypass exact calibration-parquet answer-distribution gating.",
    )
    parser.add_argument("--per-rollout-response-mode", choices=("none", "full", "truncated"), default="full")
    parser.add_argument("--per-rollout-response-max-chars", type=int, default=4000)
    parser.add_argument("--dry-run", action="store_true", help="Print selected tasks and commands without running them.")
    return parser.parse_args()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _easy_threshold_for_rollouts(rollout_count: int) -> int:
    """Minimum solved rollouts for the perfect-solve tail."""
    return int(rollout_count)


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _run_command(cmd: list[str], *, env: dict[str, str] | None = None, log_path: Path | None = None, dry_run: bool) -> None:
    printable = " ".join(cmd)
    if dry_run:
        print(f"[dry-run] {printable}")
        return
    if log_path is None:
        subprocess.run(cmd, cwd=REPO_ROOT, env=env, check=True)
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"$ {printable}\n\n")
        log.flush()
        subprocess.run(cmd, cwd=REPO_ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _metadata_calibration_baseline(payload: dict[str, Any]) -> str:
    value = payload.get("calibration_baseline")
    if value is not None:
        return str(value)
    config = payload.get("config")
    if isinstance(config, dict) and config.get("calibration_baseline") is not None:
        return str(config.get("calibration_baseline"))
    return ""


def _metadata_matches_baseline(payload: dict[str, Any], baseline: str) -> bool:
    return _metadata_calibration_baseline(payload).strip() == str(baseline).strip()


def _json_file_matches_baseline(path: Path, baseline: str) -> bool:
    if not path.exists():
        return False
    try:
        payload = _load_json(path)
    except Exception:
        return False
    return _metadata_matches_baseline(payload, baseline)


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _fingerprint_roots_for_task(task_id: str) -> list[Path]:
    taxonomy = resolve_task_taxonomy(task_id)
    domain = str(taxonomy.domain)
    scene_id = str(taxonomy.scene_id)
    candidates = [
        REPO_ROOT / "trace" / "tasks" / domain / scene_id,
        REPO_ROOT / "trace" / "tasks" / domain / "shared",
        REPO_ROOT / "trace" / "tasks" / domain / "__init__.py",
        REPO_ROOT / "trace" / "tasks" / "shared",
        REPO_ROOT / "trace" / "tasks" / "__init__.py",
        REPO_ROOT / "trace" / "tasks" / "registry.py",
        REPO_ROOT / "trace" / "core",
        REPO_ROOT / "trace" / "configs",
        REPO_ROOT / "configs" / "domains" / domain / "base.yaml",
        REPO_ROOT / "configs" / "domains" / domain / f"{scene_id}.yaml",
        REPO_ROOT / "prompts" / domain,
        REPO_ROOT / "assets",
        REPO_ROOT / "requirements.txt",
        REPO_ROOT / "pyproject.toml",
    ]
    roots: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if not candidate.exists():
            continue
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        roots.append(candidate)
    return roots


def _should_fingerprint_file(path: Path) -> bool:
    if any(part in CALIBRATION_FINGERPRINT_SKIP_DIRS for part in path.parts):
        return False
    if path.suffix in CALIBRATION_FINGERPRINT_SKIP_SUFFIXES:
        return False
    return path.is_file()


def _iter_fingerprint_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if _should_fingerprint_file(root):
            yield root
        return
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*"), key=lambda item: _repo_relative(item)):
        if _should_fingerprint_file(path):
            yield path


@lru_cache(maxsize=None)
def _fingerprint_file_digest(path_text: str) -> str:
    return hashlib.sha256(Path(path_text).read_bytes()).hexdigest()


@lru_cache(maxsize=None)
def _fingerprint_root_entries(root_text: str) -> tuple[tuple[str, str], ...]:
    root = Path(root_text)
    entries: list[tuple[str, str]] = []
    for path in _iter_fingerprint_files(root):
        entries.append((_repo_relative(path), _fingerprint_file_digest(str(path.resolve()))))
    return tuple(sorted(entries))


def _calibration_source_fingerprint(task_id: str) -> dict[str, Any]:
    roots = _fingerprint_roots_for_task(task_id)
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for root in roots:
        for rel, file_digest in _fingerprint_root_entries(str(root.resolve())):
            if rel in seen:
                continue
            seen.add(rel)
            entries.append((rel, file_digest))

    digest = hashlib.sha256()
    digest.update(CALIBRATION_SOURCE_FINGERPRINT_VERSION.encode("utf-8"))
    digest.update(b"\0")
    for rel, file_digest in sorted(entries):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\0")

    return {
        "version": CALIBRATION_SOURCE_FINGERPRINT_VERSION,
        "digest": digest.hexdigest(),
        "file_count": len(entries),
        "roots": [_repo_relative(root) for root in roots],
    }


def _fingerprint_digest(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("digest") or "")


def _fingerprints_match(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    return (
        str(left.get("version") or "") == str(right.get("version") or "")
        and _fingerprint_digest(left) == _fingerprint_digest(right)
    )


def _parquet_manifest_path(parquet: Path) -> Path:
    return parquet.with_suffix(parquet.suffix + ".manifest.json")


def _parquet_source_fingerprint(parquet: Path) -> dict[str, Any]:
    manifest = _load_json(_parquet_manifest_path(parquet))
    value = manifest.get("calibration_source_fingerprint")
    return dict(value) if isinstance(value, dict) else {}


def _probe_run_manifest_path(output_dir: Path) -> Path:
    return output_dir / "calibration_probe_manifest.json"


def _probe_manifest_matches_parquet(path: Path, parquet: Path, baseline: str) -> bool:
    payload = _load_json(path)
    if not _metadata_matches_baseline(payload, baseline):
        return False
    expected_fingerprint = _parquet_source_fingerprint(parquet)
    payload_fingerprint = payload.get("calibration_source_fingerprint")
    if not _fingerprints_match(
        payload_fingerprint if isinstance(payload_fingerprint, dict) else {},
        expected_fingerprint,
    ):
        return False
    try:
        if Path(str(payload.get("parquet") or "")).resolve() != parquet.resolve():
            return False
    except OSError:
        return False
    return True


def _write_probe_run_manifest(output_dir: Path, parquet: Path, baseline: str, *, batch_size: int) -> None:
    payload = {
        "calibration_baseline": str(baseline),
        "parquet": str(parquet),
        "calibration_source_fingerprint": _parquet_source_fingerprint(parquet),
        "batch_size": int(batch_size),
        "updated_at": _now(),
    }
    _write_json(_probe_run_manifest_path(output_dir), payload)


def _stats_match_parquet(stats_path: Path, parquet: Path, baseline: str) -> bool:
    stats = _load_json(stats_path)
    if not _metadata_matches_baseline(stats, baseline):
        return False
    config = stats.get("config")
    if not isinstance(config, dict):
        return False
    expected_fingerprint = _parquet_source_fingerprint(parquet)
    stats_fingerprint = config.get("calibration_source_fingerprint")
    if not _fingerprints_match(
        stats_fingerprint if isinstance(stats_fingerprint, dict) else {},
        expected_fingerprint,
    ):
        return False
    try:
        if Path(str(config.get("parquet") or "")).resolve() != parquet.resolve():
            return False
    except OSError:
        return False
    return True


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for count, _ in enumerate(fh, 1):
            pass
    return count


def _git_revision() -> str:
    try:
        rev = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "local"
    try:
        dirty = subprocess.run(["git", "diff", "--quiet"], cwd=REPO_ROOT).returncode != 0
    except Exception:
        dirty = False
    return f"{rev}-dirty" if dirty else rev


def _task_sort_key(task_id: str) -> tuple[str, str, str]:
    taxonomy = resolve_task_taxonomy(task_id)
    return str(taxonomy.domain), str(taxonomy.scene_id), str(task_id)


def _select_tasks(args: argparse.Namespace) -> list[str]:
    if str(args.tasks).strip():
        task_ids = [item.strip() for item in str(args.tasks).split(",") if item.strip()]
    else:
        task_ids = sorted(list_default_task_ids(), key=_task_sort_key)

    domains = {str(item).strip() for item in args.domain if str(item).strip()}
    scenes = {str(item).strip().strip("/") for item in args.scene if str(item).strip()}
    if domains:
        task_ids = [task_id for task_id in task_ids if str(resolve_task_taxonomy(task_id).domain) in domains]
    if scenes:
        task_ids = [
            task_id
            for task_id in task_ids
            if f"{resolve_task_taxonomy(task_id).domain}/{resolve_task_taxonomy(task_id).scene_id}" in scenes
        ]

    if args.start_at:
        start_at = str(args.start_at).strip()
        if start_at not in task_ids:
            raise SystemExit(f"--start-at task is not selected: {start_at}")
        task_ids = task_ids[task_ids.index(start_at) :]
    if args.start_after:
        start_after = str(args.start_after).strip()
        if start_after not in task_ids:
            raise SystemExit(f"--start-after task is not selected: {start_after}")
        task_ids = task_ids[task_ids.index(start_after) + 1 :]
    if int(args.limit) > 0:
        task_ids = task_ids[: int(args.limit)]
    return task_ids


def _model_spec(raw: str) -> ModelSpec:
    key = str(raw).strip()
    if key in MODEL_SPECS:
        return MODEL_SPECS[key]
    lower = key.lower()
    if "qwen2.5-vl-7b" in lower or "qwen25vl7b" in lower:
        return MODEL_SPECS["qwen25vl7b"]
    if "qwen3-vl-8b" in lower or "qwen3vl8b" in lower:
        return MODEL_SPECS["qwen3vl8b"]
    if "qwen3-vl-4b" in lower or "qwen3vl4b" in lower:
        return MODEL_SPECS["qwen3vl4b"]
    slug = re.sub(r"[^a-z0-9]+", "_", lower).strip("_") or "model"
    return ModelSpec(slug=slug, model_id=key, response_cap_threshold=0.25)


def _parse_models(raw_models: str) -> list[ModelSpec]:
    specs = [_model_spec(item) for item in str(raw_models).split(",") if item.strip()]
    seen: set[str] = set()
    deduped: list[ModelSpec] = []
    for spec in specs:
        if spec.slug in seen:
            continue
        seen.add(spec.slug)
        deduped.append(spec)
    if not deduped:
        raise SystemExit("No calibration models selected")
    return deduped


def _query_gpu(gpu_id: str) -> tuple[int, int] | None:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                f"--id={gpu_id}",
                "--query-gpu=memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        )
    except Exception:
        return None
    first = output.strip().splitlines()[0]
    used_text, util_text = [part.strip() for part in first.split(",")[:2]]
    return int(float(used_text)), int(float(util_text))


def _wait_for_gpu(args: argparse.Namespace) -> None:
    if args.no_wait_for_gpu:
        return
    while True:
        state = _query_gpu(str(args.gpu))
        if state is None:
            return
        used_mb, util = state
        if used_mb <= int(args.gpu_max_used_mb) and util <= int(args.gpu_max_utilization):
            return
        print(
            f"[wait] gpu {args.gpu} busy: memory_used={used_mb} MiB util={util}%; "
            f"sleeping {args.gpu_wait_interval}s"
        )
        time.sleep(max(1, int(args.gpu_wait_interval)))


def _dataset_paths(
    args: argparse.Namespace,
    task_id: str,
    *,
    seed: int | None = None,
    sample_count: int | None = None,
    dataset_suffix: str = "",
) -> tuple[Path, str, Path, Path]:
    taxonomy = resolve_task_taxonomy(task_id)
    task_root = Path(args.output_root) / str(taxonomy.domain) / str(taxonomy.scene_id) / task_id
    active_seed = int(args.seed if seed is None else seed)
    active_sample_count = int(args.sample_count if sample_count is None else sample_count)
    dataset_name = f"{task_id}_calib{int(active_sample_count)}_seed{int(active_seed)}{str(dataset_suffix)}"
    parquet = task_root / f"{dataset_name}.parquet"
    dataset_root = task_root / dataset_name
    return task_root, dataset_name, parquet, dataset_root


def _probe_output_dir(args: argparse.Namespace, task_id: str, model: ModelSpec) -> Path:
    taxonomy = resolve_task_taxonomy(task_id)
    return (
        Path(args.probe_root)
        / model.slug
        / str(taxonomy.domain)
        / str(taxonomy.scene_id)
        / task_id
        / f"{int(args.sample_count)}x{int(args.rollouts_per_prompt)}_seed{int(args.seed)}"
    )


def _review_workbook_path(args: argparse.Namespace, task_id: str) -> Path:
    taxonomy = resolve_task_taxonomy(task_id)
    return Path(args.review_root) / str(taxonomy.domain) / str(taxonomy.scene_id) / task_id / f"{task_id}.xlsx"


def _review_matches_sample(args: argparse.Namespace, task_id: str, parquet: Path) -> bool:
    manifest_path = _review_workbook_path(args, task_id).parent / "manifest.json"
    manifest = _load_json(manifest_path)
    if not _metadata_matches_baseline(manifest, str(args.calibration_baseline)):
        return False
    source = manifest.get("source_parquet")
    if not source:
        return False
    try:
        return Path(str(source)).resolve() == parquet.resolve()
    except OSError:
        return False


def _build_sample(
    args: argparse.Namespace,
    task_id: str,
    *,
    code_revision: str,
    seed: int | None = None,
    sample_count: int | None = None,
    dataset_suffix: str = "",
    reset: bool | None = None,
) -> tuple[Path, Path]:
    active_seed = int(args.seed if seed is None else seed)
    active_sample_count = int(args.sample_count if sample_count is None else sample_count)
    _, dataset_name, parquet, dataset_root = _dataset_paths(
        args,
        task_id,
        seed=int(active_seed),
        sample_count=int(active_sample_count),
        dataset_suffix=str(dataset_suffix),
    )
    manifest = _parquet_manifest_path(parquet)
    current_fingerprint = _calibration_source_fingerprint(task_id)
    manifest_payload = _load_json(manifest)
    manifest_matches_baseline = _metadata_matches_baseline(manifest_payload, str(args.calibration_baseline))
    manifest_matches_source = _fingerprints_match(
        manifest_payload.get("calibration_source_fingerprint")
        if isinstance(manifest_payload.get("calibration_source_fingerprint"), dict)
        else {},
        current_fingerprint,
    )
    should_reset = (
        (args.force or args.force_build or not manifest_matches_baseline or not manifest_matches_source)
        if reset is None
        else bool(reset)
    )
    if parquet.exists() and manifest.exists() and not bool(should_reset):
        return parquet, Path(manifest_payload.get("trace_dataset_root") or dataset_root)
    if parquet.exists() and manifest.exists() and bool(should_reset) and not (args.force or args.force_build):
        reasons: list[str] = []
        if not manifest_matches_baseline:
            reasons.append("baseline changed/missing")
        if not manifest_matches_source:
            old_digest = _fingerprint_digest(
                manifest_payload.get("calibration_source_fingerprint")
                if isinstance(manifest_payload.get("calibration_source_fingerprint"), dict)
                else {}
            )
            new_digest = _fingerprint_digest(current_fingerprint)
            reasons.append(f"source fingerprint changed {old_digest or '<missing>'}->{new_digest}")
        print(f"[build] rebuilding stale calibration dataset for {task_id}: {', '.join(reasons)}")

    cmd = [
        sys.executable,
        "scripts/prepare_trace_rlvr_task_probe.py",
        "--task-id",
        task_id,
        "--output-root",
        str(parquet.parent),
        "--dataset-name",
        dataset_name,
        "--num-instances",
        str(active_sample_count),
        "--sampling-seed",
        str(active_seed),
        "--workers",
        str(args.workers),
        "--parquet-cpu-count",
        str(args.parquet_cpu_count),
        "--code-hash",
        code_revision,
        "--prompt-variant",
        "answer",
        "--image-storage-mode",
        "embedded_bytes",
        "--image-path-mode",
        "relative",
        "--rlvr-output",
        str(parquet),
    ]
    if bool(should_reset):
        cmd.append("--reset")
    _run_command(cmd, dry_run=bool(args.dry_run))
    if args.dry_run:
        return parquet, dataset_root
    manifest_payload = _load_json(manifest)
    manifest_payload["calibration_baseline"] = str(args.calibration_baseline)
    manifest_payload["calibration_sample_count"] = int(active_sample_count)
    manifest_payload["calibration_seed"] = int(active_seed)
    manifest_payload["calibration_code_revision"] = str(code_revision)
    manifest_payload["calibration_source_fingerprint"] = current_fingerprint
    _write_json(manifest, manifest_payload)
    return parquet, Path(manifest_payload["trace_dataset_root"])


def _sample_distribution_report_path(parquet: Path) -> Path:
    return parquet.with_suffix(parquet.suffix + ".distribution_report.json")


def _run_sample_distribution_check(
    args: argparse.Namespace,
    *,
    parquets: Sequence[Path],
    dataset_roots: Sequence[Path],
    report_path: Path,
) -> bool:
    cmd = [
        sys.executable,
        "scripts/check_rlvr_probe_distribution.py",
        "--out",
        str(report_path),
        "--min-unique-answers",
        str(args.sample_distribution_min_unique_answers),
        "--max-answer-frequency",
        str(args.sample_distribution_max_answer_frequency),
    ]
    for parquet in parquets:
        cmd.extend(["--parquet", str(parquet)])
    for dataset_root in dataset_roots:
        cmd.extend(["--dataset-root", str(dataset_root)])
    if args.dry_run:
        print(f"[dry-run] {' '.join(cmd)}")
        return True
    result = subprocess.run(cmd, cwd=REPO_ROOT)
    return int(result.returncode) == 0


def _check_sample_distribution(
    args: argparse.Namespace,
    task_id: str,
    *,
    parquet: Path,
    dataset_root: Path,
    code_revision: str,
) -> tuple[bool, Path | None]:
    if bool(args.skip_sample_distribution_check):
        return True, None
    report_path = _sample_distribution_report_path(parquet)
    parquets = [Path(parquet)]
    dataset_roots = [Path(dataset_root)]
    if _run_sample_distribution_check(args, parquets=parquets, dataset_roots=dataset_roots, report_path=report_path):
        return True, report_path
    for attempt in range(2, int(SAMPLE_DISTRIBUTION_VALIDATION_MAX_ATTEMPTS) + 1):
        validation_seed = int(args.seed) + int(attempt) - 1
        validation_parquet, validation_root = _build_sample(
            args,
            task_id,
            code_revision=code_revision,
            seed=int(validation_seed),
            sample_count=int(args.sample_count),
            dataset_suffix=f"_distval{attempt}",
        )
        parquets.append(Path(validation_parquet))
        dataset_roots.append(Path(validation_root))
        if _run_sample_distribution_check(args, parquets=parquets, dataset_roots=dataset_roots, report_path=report_path):
            return True, report_path
    return False, report_path


def _export_review(args: argparse.Namespace, task_id: str, parquet: Path, dataset_root: Path) -> Path:
    workbook = _review_workbook_path(args, task_id)
    if workbook.exists() and _review_matches_sample(args, task_id, parquet) and not (args.force or args.force_review):
        return workbook
    if not args.dry_run:
        shutil.rmtree(workbook.parent, ignore_errors=True)
    cmd = [
        sys.executable,
        "scripts/export_task_review_workbook.py",
        "--parquet",
        str(parquet),
        "--dataset-root",
        str(dataset_root),
        "--out-root",
        str(args.review_root),
        "--calibration-baseline",
        str(args.calibration_baseline),
    ]
    _run_command(cmd, dry_run=bool(args.dry_run))
    return workbook


def _probe_env(args: argparse.Namespace) -> dict[str, str]:
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "" if str(args.probe_backend) == "openai_server" else str(args.gpu)
    env["PYTHONPATH"] = f"{RLVR_ROOT}:{REPO_ROOT}:{env.get('PYTHONPATH', '')}"
    env.setdefault("TRANSFORMERS_NO_TF", "1")
    env.setdefault("TOKENIZERS_PARALLELISM", "false")
    env.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
    env.setdefault("VLLM_ATTENTION_BACKEND", "FLASH_ATTN")
    env.setdefault("VLLM_USE_TRTLLM_ATTENTION", "false")
    env.setdefault("VLLM_LOGGING_LEVEL", "WARN")
    return env


def _server_base_url_for_model(args: argparse.Namespace, model: ModelSpec) -> str:
    explicit_url = str(args.server_base_url).strip()
    if explicit_url:
        return explicit_url
    if model.slug in SERVER_BASE_URL_DEFAULTS:
        return SERVER_BASE_URL_DEFAULTS[model.slug]
    raise ValueError(f"--server-base-url is required for unknown calibration model {model.model_id!r}")


def _server_endpoint_pool_for_model(args: argparse.Namespace, model: ModelSpec) -> tuple[str, ...]:
    explicit_url = str(args.server_base_url).strip()
    if explicit_url:
        return (explicit_url,)
    if model.slug in SERVER_ENDPOINT_POOLS:
        return tuple(SERVER_ENDPOINT_POOLS[str(model.slug)])
    return (_server_base_url_for_model(args, model),)


def _server_model_for_model(args: argparse.Namespace, model: ModelSpec) -> str:
    explicit_model = str(args.server_model).strip()
    return explicit_model if explicit_model else model.model_id


def _endpoint_lock_name(model: ModelSpec, endpoint: str) -> str:
    match = re.search(r":(\d+)(?:/|$)", str(endpoint))
    port = match.group(1) if match else re.sub(r"[^a-z0-9]+", "_", str(endpoint).lower()).strip("_")
    return f"{model.slug}_{port}.lock"


@contextmanager
def _claim_server_endpoint(args: argparse.Namespace, model: ModelSpec, *, task_id: str):
    if str(args.probe_backend) != "openai_server":
        yield ""
        return

    endpoints = _server_endpoint_pool_for_model(args, model)
    explicit_url = str(args.server_base_url).strip()
    if explicit_url or bool(args.no_server_pool_locks):
        yield endpoints[0]
        return

    lock_root = Path(str(args.server_pool_lock_root))
    wait_interval = max(1, int(args.server_pool_wait_interval))
    warned = False
    while True:
        for endpoint in endpoints:
            lock_root.mkdir(parents=True, exist_ok=True)
            lock_path = lock_root / _endpoint_lock_name(model, endpoint)
            fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o664)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                continue

            metadata = {
                "acquired_at": _now(),
                "endpoint": str(endpoint),
                "model": str(model.model_id),
                "model_slug": str(model.slug),
                "pid": int(os.getpid()),
                "task_id": str(task_id),
            }
            payload = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")
            os.ftruncate(fd, 0)
            os.write(fd, payload)
            os.fsync(fd)
            print(f"[server-pool] claimed {model.slug} endpoint {endpoint} for {task_id}")
            try:
                yield str(endpoint)
            finally:
                try:
                    os.ftruncate(fd, 0)
                    os.fsync(fd)
                    fcntl.flock(fd, fcntl.LOCK_UN)
                finally:
                    os.close(fd)
                print(f"[server-pool] released {model.slug} endpoint {endpoint} for {task_id}")
            return

        if not warned:
            print(
                f"[server-pool] all {model.slug} endpoints busy; waiting every {wait_interval}s "
                f"under {lock_root}"
            )
            warned = True
        time.sleep(wait_interval)


def _max_tokens_for_model(args: argparse.Namespace, model: ModelSpec) -> int:
    if int(args.max_tokens) > 0:
        return int(args.max_tokens)
    if model.slug in MAX_TOKENS_DEFAULTS:
        return int(MAX_TOKENS_DEFAULTS[model.slug])
    return 2048


def _max_model_len_for_model(args: argparse.Namespace, model: ModelSpec) -> int:
    if int(args.max_model_len) > 0:
        return int(args.max_model_len)
    if model.slug in MAX_MODEL_LEN_DEFAULTS:
        return int(MAX_MODEL_LEN_DEFAULTS[model.slug])
    return 4096


def _probe_command(
    args: argparse.Namespace,
    model: ModelSpec,
    parquet: Path,
    output_dir: Path,
    *,
    batch_size: int,
    server_base_url: str = "",
) -> list[str]:
    cmd = [
        sys.executable,
        "rlvr/scripts/trace_curriculum_probe.py",
        "--parquet",
        str(parquet),
        "--output-dir",
        str(output_dir),
        "--model",
        model.model_id,
        "--backend",
        str(args.probe_backend),
        "--trace-output-mode",
        "answer",
        "--prompt-key",
        "prompt_answer",
        "--system-prompt",
        str(RLVR_ROOT / "examples/prompts/trace_vero_json_system_prompt_answer.txt"),
        "--trace-reward-mode",
        "answer",
        "--trace-answer-scoring",
        "legacy_strict",
        "--trace-format-weight",
        "0.0",
        "--batch-size",
        str(batch_size),
        "--rollouts-per-prompt",
        str(args.rollouts_per_prompt),
        "--temperature",
        "1.0",
        "--max-tokens",
        str(_max_tokens_for_model(args, model)),
        "--tensor-parallel-size",
        "1",
        "--replica-workers",
        "1",
        "--gpu-memory-utilization",
        str(args.gpu_memory_utilization),
        "--max-model-len",
        str(_max_model_len_for_model(args, model)),
        "--max-num-batched-tokens",
        str(args.max_num_batched_tokens),
        "--max-num-seqs",
        str(args.max_num_seqs),
        "--max-prompt-length",
        str(args.max_prompt_length),
        "--max-pixels",
        str(args.max_pixels),
        "--prefetch-workers",
        "1",
        "--seed",
        str(args.seed),
        "--write-per-rollout",
        "--per-rollout-response-mode",
        str(args.per_rollout_response_mode),
        "--per-rollout-response-max-chars",
        str(args.per_rollout_response_max_chars),
    ]
    if str(args.probe_backend) == "openai_server":
        server_model = _server_model_for_model(args, model)
        cmd.extend(
            [
                "--server-base-url",
                str(server_base_url) if str(server_base_url).strip() else _server_base_url_for_model(args, model),
                "--server-api-key",
                str(args.server_api_key),
                "--server-timeout",
                str(args.server_timeout),
                "--server-max-retries",
                str(args.server_max_retries),
                "--server-concurrency",
                str(args.server_concurrency),
            ]
        )
        if server_model:
            cmd.extend(["--server-model", server_model])
    return cmd


def _looks_like_oom(log_path: Path) -> bool:
    text = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""
    needles = ("CUDA out of memory", "OutOfMemoryError", "out of memory", "No available memory")
    return any(needle.lower() in text.lower() for needle in needles)


def _discard_failed_output(output_dir: Path, *, batch_size: int) -> None:
    if not output_dir.exists():
        return
    print(f"[retry] removing failed probe output {output_dir} after batch={batch_size}")
    shutil.rmtree(output_dir, ignore_errors=True)


def _run_probe(args: argparse.Namespace, task_id: str, model: ModelSpec, parquet: Path) -> tuple[Path, int, str | None]:
    output_dir = _probe_output_dir(args, task_id, model)
    stats_path = output_dir / "calibration_stats.json"
    per_instance = output_dir / "per_instance.jsonl"
    probe_manifest = _probe_run_manifest_path(output_dir)
    expected_rows = int(args.sample_count)
    default_endpoint = _server_base_url_for_model(args, model) if str(args.probe_backend) == "openai_server" else None
    if output_dir.exists() and (args.force or args.force_models):
        shutil.rmtree(output_dir, ignore_errors=True)
    elif stats_path.exists() and not _stats_match_parquet(stats_path, parquet, str(args.calibration_baseline)):
        shutil.rmtree(output_dir, ignore_errors=True)
    elif per_instance.exists() and not stats_path.exists() and not _probe_manifest_matches_parquet(
        probe_manifest,
        parquet,
        str(args.calibration_baseline),
    ):
        shutil.rmtree(output_dir, ignore_errors=True)

    if (
        stats_path.exists()
        and _stats_match_parquet(stats_path, parquet, str(args.calibration_baseline))
        and not (args.force or args.force_models or args.force_stats)
    ):
        return output_dir, int(_load_json(stats_path).get("config", {}).get("batch_size", args.batch_size)), default_endpoint
    if (
        per_instance.exists()
        and _line_count(per_instance) == expected_rows
        and _probe_manifest_matches_parquet(probe_manifest, parquet, str(args.calibration_baseline))
        and not (args.force or args.force_models)
    ):
        return output_dir, int(args.batch_size), default_endpoint

    batch_sizes = [int(args.batch_size)]
    if int(args.retry_batch_size) > 0 and int(args.retry_batch_size) != int(args.batch_size):
        batch_sizes.append(int(args.retry_batch_size))

    last_error: subprocess.CalledProcessError | None = None
    for batch_size in batch_sizes:
        if str(args.probe_backend) == "local_vllm":
            _wait_for_gpu(args)
        output_dir.mkdir(parents=True, exist_ok=True)
        log_path = output_dir / f"run_batch{batch_size}.log"
        with _claim_server_endpoint(args, model, task_id=task_id) as claimed_endpoint:
            cmd = _probe_command(
                args,
                model,
                parquet,
                output_dir,
                batch_size=batch_size,
                server_base_url=str(claimed_endpoint),
            )
            try:
                _run_command(cmd, env=_probe_env(args), log_path=log_path, dry_run=bool(args.dry_run))
                if not args.dry_run:
                    _write_probe_run_manifest(
                        output_dir,
                        parquet,
                        str(args.calibration_baseline),
                        batch_size=int(batch_size),
                    )
                return output_dir, batch_size, str(claimed_endpoint) if str(claimed_endpoint).strip() else None
            except subprocess.CalledProcessError as exc:
                last_error = exc
                if batch_size == batch_sizes[-1] or not _looks_like_oom(log_path):
                    raise
                print(f"[retry] {task_id}/{model.slug} failed with likely OOM at batch={batch_size}; retrying smaller batch")
                _discard_failed_output(output_dir, batch_size=batch_size)
    assert last_error is not None
    raise last_error


def _export_stats(args: argparse.Namespace, task_id: str, model: ModelSpec, parquet: Path, output_dir: Path) -> dict[str, Any]:
    stats_path = output_dir / "calibration_stats.json"
    if (
        stats_path.exists()
        and _stats_match_parquet(stats_path, parquet, str(args.calibration_baseline))
        and not (args.force or args.force_stats)
    ):
        return _load_json(stats_path)
    label = (
        f"{model.slug}_{str(args.calibration_baseline)}_"
        f"{int(args.sample_count)}x{int(args.rollouts_per_prompt)}_seed{int(args.seed)}"
    )
    cmd = [
        sys.executable,
        "scripts/export_curriculum_probe_calibration_stats.py",
        "--task-id",
        task_id,
        "--parquet",
        str(parquet),
        "--probe-output-dir",
        str(output_dir),
        "--out-root",
        str(args.review_root),
        "--review-label",
        label,
        "--calibration-baseline",
        str(args.calibration_baseline),
        "--hard-threshold",
        "0",
        "--easy-threshold",
        str(_easy_threshold_for_rollouts(int(args.rollouts_per_prompt))),
        "--max-prompt-length",
        str(args.max_prompt_length),
        "--max-response-length",
        str(_max_tokens_for_model(args, model)),
        "--group-key",
        "query_id",
    ]
    _run_command(cmd, dry_run=bool(args.dry_run))
    stats = _load_json(stats_path) if stats_path.exists() else {}
    if stats:
        config = stats.setdefault("config", {})
        if isinstance(config, dict):
            config["calibration_source_fingerprint"] = _parquet_source_fingerprint(parquet)
            _write_json(stats_path, stats)
    return stats


def _model_status(stats: dict[str, Any], *, cap_threshold: float) -> tuple[str, list[str]]:
    reasons: list[str] = []
    overall = stats.get("overall") if isinstance(stats.get("overall"), dict) else {}
    prompt_stats = stats.get("prompt_token_stats") if isinstance(stats.get("prompt_token_stats"), dict) else {}
    response_stats = stats.get("response_token_stats") if isinstance(stats.get("response_token_stats"), dict) else {}
    if int(prompt_stats.get("over_limit_count") or 0) > 0:
        reasons.append("prompt_over_limit")
    if float(response_stats.get("cap_rate") or 0.0) > float(cap_threshold):
        reasons.append("response_cap_rate")
    if not overall:
        reasons.append("missing_overall_stats")
    if reasons:
        return "blocked", reasons

    difficulty_reasons: list[str] = []
    if float(overall.get("hard_frac") or 0.0) > HARD_FRACTION_THRESHOLD:
        difficulty_reasons.append("hard_frac")
    if float(overall.get("easy_frac") or 0.0) > EASY_FRACTION_THRESHOLD:
        difficulty_reasons.append("easy_frac")
    mean = float(overall.get("mean_solve_rate") or 0.0)
    if mean < MEAN_SOLVE_RATE_MIN or mean > MEAN_SOLVE_RATE_MAX:
        difficulty_reasons.append("mean_solve_rate")
    if difficulty_reasons:
        return "needs_manual_tuning", difficulty_reasons
    return "accepted", []


def _combined_status(model_records: dict[str, dict[str, Any]]) -> str:
    statuses = [str(record.get("status", "")) for record in model_records.values()]
    if not statuses:
        return "blocked"
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if all(status == "accepted" for status in statuses):
        return "accepted"
    return "needs_manual_tuning"


def _metric(stats: dict[str, Any], key: str) -> str:
    overall = stats.get("overall") if isinstance(stats.get("overall"), dict) else {}
    value = overall.get(key)
    if value is None:
        return "-"
    return f"{float(value):.3f}"


def _cap_rate(stats: dict[str, Any]) -> str:
    response_stats = stats.get("response_token_stats") if isinstance(stats.get("response_token_stats"), dict) else {}
    value = response_stats.get("cap_rate")
    if value is None:
        return "-"
    return f"{float(value):.3f}"


def _prompt_max(stats: dict[str, Any]) -> str:
    prompt_stats = stats.get("prompt_token_stats") if isinstance(stats.get("prompt_token_stats"), dict) else {}
    value = prompt_stats.get("max")
    return "-" if value is None else str(int(value))


def _write_status_files(args: argparse.Namespace, status: dict[str, Any]) -> None:
    status_json_path = Path(args.status_json)
    current_tasks: dict[str, Any] = {}
    if status_json_path.exists():
        try:
            current_status = json.loads(status_json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current_status = {}
        if isinstance(current_status, dict) and isinstance(current_status.get("tasks"), dict):
            current_tasks = {
                str(task_id): record
                for task_id, record in current_status["tasks"].items()
                if isinstance(record, dict)
            }
    if current_tasks:
        tasks = status.setdefault("tasks", {})
        if isinstance(tasks, dict):
            for task_id, record in current_tasks.items():
                tasks.setdefault(str(task_id), record)
    tasks = status.get("tasks")
    if isinstance(tasks, dict):
        active_task_ids = set(list_default_task_ids())
        for task_id in list(tasks.keys()):
            if str(task_id) not in active_task_ids:
                del tasks[task_id]
    status["updated_at"] = _now()
    _write_json(status_json_path, status)

    rows: list[str] = []
    rows.append("# TRACE Calibration Sweep Status")
    rows.append("")
    rows.append(f"Updated: `{status['updated_at']}`")
    rows.append("")
    config_models = status.get("config", {}).get("models") if isinstance(status.get("config"), dict) else {}
    if isinstance(config_models, dict) and config_models:
        model_slugs = sorted(str(slug) for slug in config_models.keys())
    else:
        model_slugs = sorted(
            {
                str(slug)
                for record in status.get("tasks", {}).values()
                if isinstance(record, dict)
                for slug in (record.get("models") or {}).keys()
            }
        )
    model_headers = " | ".join(f"`{slug}` H/E/Mean/Cap/PromptMax" for slug in model_slugs)
    rows.append(f"| Domain | Scene | Task | Status | {model_headers} | Artifacts |")
    rows.append("|---|---|---|---|" + "---|" * len(model_slugs) + "---|")
    for task_id, record in sorted(status.get("tasks", {}).items(), key=lambda item: (item[1].get("domain", ""), item[1].get("scene_id", ""), item[0])):
        models = record.get("models", {})

        def fmt_model(model_record: dict[str, Any]) -> str:
            stats = model_record.get("stats") if isinstance(model_record.get("stats"), dict) else {}
            return (
                f"{_metric(stats, 'hard_frac')}/"
                f"{_metric(stats, 'easy_frac')}/"
                f"{_metric(stats, 'mean_solve_rate')}/"
                f"{_cap_rate(stats)}/"
                f"{_prompt_max(stats)}"
            )

        artifacts = []
        if record.get("parquet"):
            artifacts.append(f"parquet: `{record['parquet']}`")
        if record.get("sample_distribution_report"):
            artifacts.append(f"sample_distribution: `{record['sample_distribution_report']}`")
        if record.get("review_workbook"):
            artifacts.append(f"review: `{record['review_workbook']}`")
        for slug in model_slugs:
            model_record = models.get(slug, {})
            if model_record.get("output_dir"):
                artifacts.append(f"{slug}: `{model_record['output_dir']}`")
        model_cells = " | ".join(fmt_model(models.get(slug, {})) for slug in model_slugs)
        rows.append(
            f"| `{record.get('domain', '')}` | `{record.get('scene_id', '')}` | `{task_id}` | "
            f"`{record.get('status', '')}` | {model_cells} | {'<br>'.join(artifacts)} |"
        )
    Path(args.status_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.status_md).write_text("\n".join(rows) + "\n", encoding="utf-8")


def _prune_unselected_status_tasks(
    status: dict[str, Any],
    *,
    selected_task_ids: Sequence[str],
    retain_default_tasks: bool,
) -> None:
    tasks = status.get("tasks")
    if not isinstance(tasks, dict):
        status["tasks"] = {}
        return
    if not bool(retain_default_tasks):
        return
    retained = set(list_default_task_ids()) | {str(task_id) for task_id in selected_task_ids}
    for task_id in list(tasks.keys()):
        if str(task_id) not in retained:
            del tasks[task_id]


def _uses_scoped_task_selection(args: argparse.Namespace) -> bool:
    return bool(
        str(args.tasks).strip()
        or args.domain
        or args.scene
        or str(args.start_at).strip()
        or str(args.start_after).strip()
        or args.limit is not None
    )


def _calibrate_task(
    args: argparse.Namespace,
    task_id: str,
    models: list[ModelSpec],
    *,
    code_revision: str,
    existing_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    taxonomy = resolve_task_taxonomy(task_id)
    active_model_slugs = {model.slug for model in models}
    existing_models = existing_record.get("models", {}) if isinstance(existing_record, dict) else {}
    record: dict[str, Any] = {
        "task_id": task_id,
        "domain": str(taxonomy.domain),
        "scene_id": str(taxonomy.scene_id),
        "calibration_baseline": str(args.calibration_baseline),
        "updated_at": _now(),
        "status": "blocked",
        "models": dict(existing_models) if isinstance(existing_models, dict) else {},
    }

    parquet, dataset_root = _build_sample(args, task_id, code_revision=code_revision)
    record["parquet"] = _rel(parquet)
    record["dataset_root"] = _rel(dataset_root)

    distribution_ok, distribution_report = _check_sample_distribution(
        args,
        task_id,
        parquet=parquet,
        dataset_root=dataset_root,
        code_revision=code_revision,
    )
    if distribution_report is not None:
        record["sample_distribution_report"] = _rel(distribution_report)
    if not bool(distribution_ok):
        record["status"] = "blocked"
        record["reasons"] = ["sample_distribution_check_failed"]
        record["models"] = {}
        return record

    if not args.skip_review:
        workbook = _export_review(args, task_id, parquet, dataset_root)
        record["review_workbook"] = _rel(workbook)

    if args.skip_models or args.dry_run:
        record["status"] = "dry_run" if args.dry_run else "reviewed_pending_probe"
        record["models"] = {}
        return record

    for model in models:
        model_record: dict[str, Any] = {
            "model_id": model.model_id,
            "response_cap_threshold": model.response_cap_threshold,
            "max_response_length": _max_tokens_for_model(args, model),
            "max_model_len": _max_model_len_for_model(args, model),
            "status": "blocked",
        }
        if str(args.probe_backend) == "openai_server":
            model_record["server_endpoint_pool"] = list(_server_endpoint_pool_for_model(args, model))
            model_record["server_model"] = _server_model_for_model(args, model)
        try:
            output_dir, batch_size, server_base_url = _run_probe(args, task_id, model, parquet)
            stats = _export_stats(args, task_id, model, parquet, output_dir)
            model_status, reasons = _model_status(stats, cap_threshold=model.response_cap_threshold)
            stats_artifacts = stats.get("artifacts") if isinstance(stats.get("artifacts"), dict) else {}
            model_record.update(
                {
                    "output_dir": _rel(output_dir),
                    "calibration_stats": _rel(output_dir / "calibration_stats.json"),
                    "solve_workbook": stats_artifacts.get("solve_workbook"),
                    "batch_size": int(batch_size),
                    "server_base_url": str(server_base_url) if server_base_url else None,
                    "status": model_status,
                    "reasons": reasons,
                    "stats": stats,
                }
            )
        except subprocess.CalledProcessError as exc:
            model_record.update({"status": "blocked", "reasons": [f"command_failed:{exc.returncode}"]})
        except Exception as exc:  # Keep the sweep moving task-by-task.
            model_record.update({"status": "blocked", "reasons": [f"{type(exc).__name__}:{exc}"]})
        record["models"][model.slug] = model_record

    active_records = {
        slug: model_record
        for slug, model_record in record["models"].items()
        if slug in active_model_slugs
    }
    record["status"] = _combined_status(active_records)
    return record


def _rebuild_scene_workbooks(args: argparse.Namespace, scene_keys: Iterable[tuple[str, str]]) -> None:
    if args.skip_scene_workbooks or args.dry_run:
        return
    for domain, scene_id in sorted(set(scene_keys)):
        cmd = [
            sys.executable,
            "scripts/build_scene_task_review_workbooks.py",
            "--out-root",
            str(args.review_root),
            "--scene",
            f"{domain}/{scene_id}",
        ]
        _run_command(cmd, dry_run=False)


def main() -> int:
    args = _parse_args()
    task_ids = _select_tasks(args)
    models = _parse_models(args.models)
    code_revision = _git_revision()

    print(f"[sweep] selected_tasks={len(task_ids)} models={[model.slug for model in models]} code={code_revision}")
    if args.dry_run:
        for task_id in task_ids:
            taxonomy = resolve_task_taxonomy(task_id)
            print(f"[dry-run] {taxonomy.domain}/{taxonomy.scene_id}/{task_id}")

    status_path = Path(args.status_json)
    status = _load_json(status_path)
    if status and not _metadata_matches_baseline(status.get("config", {}) if isinstance(status.get("config"), dict) else status, str(args.calibration_baseline)):
        print(
            f"[sweep] ignoring stale status file without calibration_baseline={args.calibration_baseline}: "
            f"{args.status_json}"
        )
        status = {}
    if not status:
        status = {"tasks": {}}
    _prune_unselected_status_tasks(
        status,
        selected_task_ids=task_ids,
        retain_default_tasks=not _uses_scoped_task_selection(args),
    )
    status["config"] = {
        "sample_count": int(args.sample_count),
        "calibration_baseline": str(args.calibration_baseline),
        "rollouts_per_prompt": int(args.rollouts_per_prompt),
        "hard_threshold_solved_rollouts": 0,
        "hard_fraction_threshold": HARD_FRACTION_THRESHOLD,
        "easy_threshold_solved_rollouts": _easy_threshold_for_rollouts(int(args.rollouts_per_prompt)),
        "easy_fraction_threshold": EASY_FRACTION_THRESHOLD,
        "easy_definition": f"solved_rollouts >= {_easy_threshold_for_rollouts(int(args.rollouts_per_prompt))}",
        "mean_solve_rate_min": MEAN_SOLVE_RATE_MIN,
        "mean_solve_rate_max": MEAN_SOLVE_RATE_MAX,
        "seed": int(args.seed),
        "max_prompt_length": int(args.max_prompt_length),
        "max_response_length": int(args.max_tokens) if int(args.max_tokens) > 0 else None,
        "max_response_length_defaults": dict(MAX_TOKENS_DEFAULTS) if int(args.max_tokens) <= 0 else None,
        "max_model_len": int(args.max_model_len) if int(args.max_model_len) > 0 else None,
        "max_model_len_defaults": dict(MAX_MODEL_LEN_DEFAULTS) if int(args.max_model_len) <= 0 else None,
        "models": {model.slug: {"model_id": model.model_id, "response_cap_threshold": model.response_cap_threshold} for model in models},
        "probe_backend": str(args.probe_backend),
        "server_base_url": str(args.server_base_url).strip() if str(args.probe_backend) == "openai_server" and str(args.server_base_url).strip() else None,
        "server_base_url_defaults": dict(SERVER_BASE_URL_DEFAULTS) if str(args.probe_backend) == "openai_server" and not str(args.server_base_url).strip() else None,
        "server_endpoint_pools": {key: list(value) for key, value in SERVER_ENDPOINT_POOLS.items()} if str(args.probe_backend) == "openai_server" and not str(args.server_base_url).strip() else None,
        "server_pool_locks": (not bool(args.no_server_pool_locks)) if str(args.probe_backend) == "openai_server" and not str(args.server_base_url).strip() else None,
        "server_pool_lock_root": str(args.server_pool_lock_root) if str(args.probe_backend) == "openai_server" and not str(args.server_base_url).strip() else None,
        "server_model": str(args.server_model) if str(args.probe_backend) == "openai_server" and str(args.server_model).strip() else None,
        "server_concurrency": int(args.server_concurrency) if str(args.probe_backend) == "openai_server" else None,
        "code_revision": code_revision,
        "sample_distribution_check": {
            "enabled": not bool(args.skip_sample_distribution_check),
            "min_unique_answers": int(args.sample_distribution_min_unique_answers),
            "max_answer_frequency": float(args.sample_distribution_max_answer_frequency),
            "scope": "same_generator_distribution_validation_before_review_and_model_probe",
            "sample_count_per_attempt": int(args.sample_count),
            "max_attempts": int(SAMPLE_DISTRIBUTION_VALIDATION_MAX_ATTEMPTS),
            "max_cumulative_samples": int(args.sample_count) * int(SAMPLE_DISTRIBUTION_VALIDATION_MAX_ATTEMPTS),
            "review_and_solve_rate_use_first_attempt_only": True,
        },
        "per_rollout_response_mode": str(args.per_rollout_response_mode),
        "per_rollout_response_max_chars": int(args.per_rollout_response_max_chars),
    }

    touched_scenes: set[tuple[str, str]] = set()
    for index, task_id in enumerate(task_ids, 1):
        taxonomy = resolve_task_taxonomy(task_id)
        touched_scenes.add((str(taxonomy.domain), str(taxonomy.scene_id)))
        print(f"[task {index}/{len(task_ids)}] {taxonomy.domain}/{taxonomy.scene_id}/{task_id}")
        existing_record = status.get("tasks", {}).get(task_id) if isinstance(status.get("tasks"), dict) else None
        record = _calibrate_task(args, task_id, models, code_revision=code_revision, existing_record=existing_record)
        status.setdefault("tasks", {})[task_id] = record
        if not args.dry_run:
            _write_status_files(args, status)
        print(f"[task {index}/{len(task_ids)}] status={record['status']}")

    _rebuild_scene_workbooks(args, touched_scenes)
    if not args.dry_run:
        _write_status_files(args, status)
    print(f"[done] status_json={args.status_json} status_md={args.status_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
