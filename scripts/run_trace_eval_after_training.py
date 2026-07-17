#!/usr/bin/env python3
"""Hand off one completed training run to TRACE evaluation and publication."""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import socket
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import HfHubHTTPError
from requests import RequestException


REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_SCHEMA = "trace-eval-training-handoff-status-v1"
RECEIPT_SCHEMA = "trace-eval-training-handoff-receipt-v1"
CLAIM_SCHEMA = "trace-eval-training-handoff-claim-v1"
CHILD_SCHEMA = "trace-eval-training-handoff-child-v1"
MODEL_MARKER = ".trace_model_revision.json"
HF_COMMIT_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
LOCAL_REVISION_RE = re.compile(r"^sha256set:[0-9a-f]{64}$")
REPO_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")
TRACE_EVAL_BENCHMARK_COUNT = 24
ARCHIVE_STAGE_COUNT = 3


class HandoffError(RuntimeError):
    """Raised when the handoff cannot continue without weakening provenance."""


@dataclass(frozen=True)
class ModelIdentity:
    local_revision: str
    repository_revision: str
    base_repository_revision: str


@dataclass(frozen=True)
class EvaluationModel:
    source_model_slug: str
    local_model_path: Path
    source_revision: str
    model_id: str
    model_revision: str
    display_name: str
    repository_id: str
    repository_revision: str


@dataclass(frozen=True)
class Config:
    experiment_name: str
    training_status: Path
    training_pid_file: Path
    training_script_name: str
    checkpoint_root: Path
    checkpoint_step: int
    world_size: int
    temporary_repo: str
    canonical_repo: str
    source_model_slug: str
    public_model_id: str
    display_name: str
    run_tag: str
    public_run_id: str
    paper_repo: str
    token_file: Path
    state_root: Path
    dataset_manifest: Path
    judge_model: Path
    judge_revision: str
    python_bin: Path
    eval_deps_root: Path
    vlmeval_root: Path
    seeds: tuple[int, ...]
    gpu_groups: tuple[str, ...]
    generation_port_start: int
    judge_port_start: int
    poll_seconds: float
    hf_attempts: int
    hf_retry_base_seconds: float
    hf_retry_cap_seconds: float
    publisher_timeout_seconds: float
    training_source_commit: str
    base_model_id: str
    base_model_revision: str
    base_source_model_slug: str
    base_model_path: Path
    base_public_model_id: str
    base_display_name: str
    dataset_id: str
    dataset_revision: str
    wandb_url: str

    @property
    def model_path(self) -> Path:
        return (
            self.checkpoint_root
            / f"global_step_{self.checkpoint_step}"
            / "actor"
            / "huggingface"
        )

    @property
    def campaign_root(self) -> Path:
        return Path("/dev/shm/trace_rlvr") / self.run_tag

    @property
    def score_root(self) -> Path:
        return self.campaign_root / "scoring"

    @property
    def archive_spool_root(self) -> Path:
        return self.campaign_root / "hf_archive"

    @property
    def eval_log_root(self) -> Path:
        return REPO_ROOT / "logs" / "benchmark" / self.run_tag

    @property
    def publish_root(self) -> Path:
        return REPO_ROOT / "logs" / "publish" / self.public_run_id

    @property
    def status_path(self) -> Path:
        return self.state_root / "status.json"

    @property
    def receipt_path(self) -> Path:
        return self.state_root / "handoff.json"

    @property
    def claim_path(self) -> Path:
        return self.state_root / "canonical-repo-claim.json"

    @property
    def child_root(self) -> Path:
        return self.state_root / "children"

    @property
    def lock_path(self) -> Path:
        return self.state_root / "supervisor.lock"

    def digest_document(self) -> dict[str, Any]:
        return {
            "base_model_id": self.base_model_id,
            "base_model_path": str(self.base_model_path),
            "base_model_revision": self.base_model_revision,
            "base_source_model_slug": self.base_source_model_slug,
            "base_public_model_id": self.base_public_model_id,
            "base_display_name": self.base_display_name,
            "canonical_repo": self.canonical_repo,
            "checkpoint_root": str(self.checkpoint_root),
            "checkpoint_step": self.checkpoint_step,
            "dataset_id": self.dataset_id,
            "dataset_manifest": str(self.dataset_manifest),
            "dataset_revision": self.dataset_revision,
            "display_name": self.display_name,
            "eval_deps_root": str(self.eval_deps_root),
            "experiment_name": self.experiment_name,
            "gpu_groups": list(self.gpu_groups),
            "generation_port_start": self.generation_port_start,
            "judge_model": str(self.judge_model),
            "judge_port_start": self.judge_port_start,
            "judge_revision": self.judge_revision,
            "paper_repo": self.paper_repo,
            "publisher_timeout_seconds": self.publisher_timeout_seconds,
            "public_model_id": self.public_model_id,
            "public_run_id": self.public_run_id,
            "python_bin": str(self.python_bin),
            "run_tag": self.run_tag,
            "seeds": list(self.seeds),
            "source_model_slug": self.source_model_slug,
            "temporary_repo": self.temporary_repo,
            "token_file": str(self.token_file),
            "training_pid_file": str(self.training_pid_file),
            "training_source_commit": self.training_source_commit,
            "training_status": str(self.training_status),
            "vlmeval_root": str(self.vlmeval_root),
            "wandb_url": self.wandb_url,
            "world_size": self.world_size,
        }

    @property
    def config_sha256(self) -> str:
        return _sha256_json(self.digest_document())


@dataclass
class ChildHandle:
    role: str
    pid: int
    start_ticks: int
    expected_tokens: tuple[str, ...]
    process: subprocess.Popen[bytes] | None = None


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _absolute(path: Path) -> Path:
    return path.expanduser().absolute()


def _reject_symlink_components(path: Path) -> None:
    requested = _absolute(path)
    for component in (requested, *requested.parents):
        if component.is_symlink():
            raise HandoffError(f"refusing path through symlink: {component}")


def _ensure_private_directory(path: Path) -> Path:
    requested = _absolute(path)
    _reject_symlink_components(requested)
    requested.mkdir(parents=True, exist_ok=True)
    if not requested.is_dir():
        raise HandoffError(f"private state path is not a directory: {requested}")
    os.chmod(requested, 0o700)
    return requested


def _atomic_json(path: Path, document: Mapping[str, Any]) -> None:
    parent = _ensure_private_directory(path.parent)
    _reject_symlink_components(path)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=parent)
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        directory_descriptor = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HandoffError(f"cannot read JSON receipt {path}: {error}") from error
    if not isinstance(value, dict):
        raise HandoffError(f"JSON receipt is not an object: {path}")
    return value


class StatusWriter:
    def __init__(self, config: Config):
        self.config = config
        self.started_at = _utc_now()

    def write(self, phase: str, **details: Any) -> None:
        document = {
            "schema_version": STATUS_SCHEMA,
            "config_sha256": self.config.config_sha256,
            "experiment_name": self.config.experiment_name,
            "run_tag": self.config.run_tag,
            "public_run_id": self.config.public_run_id,
            "phase": phase,
            "pid": os.getpid(),
            "started_at": self.started_at,
            "updated_at": _utc_now(),
            **details,
        }
        _atomic_json(self.config.status_path, document)
        summary = ""
        if "detail" in details:
            summary = f" detail={details['detail']}"
        print(f"[trace-eval-handoff] phase={phase}{summary}", flush=True)


class HeldLock:
    def __init__(self, path: Path):
        self.path = path
        self.descriptor = -1

    def __enter__(self) -> "HeldLock":
        _ensure_private_directory(self.path.parent)
        flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
        self.descriptor = os.open(self.path, flags, 0o600)
        os.fchmod(self.descriptor, 0o600)
        try:
            fcntl.flock(self.descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            os.close(self.descriptor)
            self.descriptor = -1
            raise HandoffError(f"another supervisor holds {self.path}") from error
        return self

    def __exit__(self, *_args: object) -> None:
        if self.descriptor >= 0:
            fcntl.flock(self.descriptor, fcntl.LOCK_UN)
            os.close(self.descriptor)
            self.descriptor = -1


def _read_pid(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    if not text.isdigit() or int(text) < 2:
        raise HandoffError(f"invalid PID file: {path}")
    return int(text)


def _process_cmdline(pid: int, proc_root: Path = Path("/proc")) -> tuple[str, ...] | None:
    try:
        raw = (proc_root / str(pid) / "cmdline").read_bytes()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None
    return tuple(part.decode("utf-8", "replace") for part in raw.split(b"\0") if part)


def _process_start_ticks(pid: int, proc_root: Path = Path("/proc")) -> int | None:
    try:
        fields = (proc_root / str(pid) / "stat").read_text(encoding="utf-8").split()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None
    return int(fields[21]) if len(fields) > 21 else None


def _process_matches(
    pid: int,
    *,
    start_ticks: int | None = None,
    expected_tokens: Sequence[str] = (),
    proc_root: Path = Path("/proc"),
) -> bool:
    cmdline = _process_cmdline(pid, proc_root)
    actual_start = _process_start_ticks(pid, proc_root)
    if cmdline is None or actual_start is None:
        return False
    if start_ticks is not None and actual_start != start_ticks:
        return False
    joined = "\0".join(cmdline)
    return all(token in joined for token in expected_tokens)


def _training_is_alive(config: Config) -> tuple[bool, int | None]:
    pid = _read_pid(config.training_pid_file)
    if pid is None:
        return False, None
    cmdline = _process_cmdline(pid)
    if cmdline is None:
        return False, pid
    if config.training_script_name not in "\0".join(cmdline):
        raise HandoffError(
            f"training PID {pid} is alive but does not match {config.training_script_name}"
        )
    return True, pid


def _training_status_text(config: Config) -> str:
    try:
        return config.training_status.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "missing"


def _validate_final_checkpoint(config: Config) -> None:
    root = config.checkpoint_root
    if root.is_symlink() or Path("/dev/shm") not in root.parents:
        raise HandoffError(f"unsafe checkpoint root: {root}")
    step_root = root / f"global_step_{config.checkpoint_step}"
    actor = step_root / "actor"
    tracker_path = root / "checkpoint_tracker.json"
    if not tracker_path.is_file():
        raise HandoffError(f"missing checkpoint tracker: {tracker_path}")
    tracker = _load_json(tracker_path)
    if int(tracker.get("last_global_step", -1)) != config.checkpoint_step:
        raise HandoffError(f"checkpoint tracker does not point to step {config.checkpoint_step}")
    for prefix in ("model", "optim", "extra_state"):
        expected = {
            f"{prefix}_world_size_{config.world_size}_rank_{rank}.pt"
            for rank in range(config.world_size)
        }
        files = {path.name: path for path in actor.glob(f"{prefix}_world_size_*_rank_*.pt")}
        if set(files) != expected or any(path.stat().st_size == 0 for path in files.values()):
            raise HandoffError(f"invalid final {prefix} shard set under {actor}")
    dataloader = step_root / "dataloader.pt"
    if not dataloader.is_file() or dataloader.stat().st_size == 0:
        raise HandoffError(f"missing final dataloader state: {dataloader}")


def _validate_model_shape(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise HandoffError(f"merged model directory is missing or unsafe: {path}")
    config_path = path / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HandoffError(f"invalid merged model config: {config_path}") from error
    if not isinstance(config, dict):
        raise HandoffError(f"merged model config is not an object: {config_path}")
    weights = sorted(path.glob("*.safetensors"))
    if not weights or any(item.stat().st_size == 0 for item in weights):
        raise HandoffError(f"missing or empty merged model weights under {path}")
    index_path = path / "model.safetensors.index.json"
    if index_path.is_file():
        index = _load_json(index_path)
        weight_map = index.get("weight_map")
        if not isinstance(weight_map, dict) or not weight_map:
            raise HandoffError(f"invalid safetensor index: {index_path}")
        referenced = {str(name) for name in weight_map.values()}
        missing = sorted(name for name in referenced if not (path / name).is_file())
        if missing:
            raise HandoffError(f"safetensor index references missing shards: {missing}")


def _snapshot_files(path: Path, *, include_marker: bool) -> list[Path]:
    result: list[Path] = []
    for candidate in path.rglob("*"):
        relative = candidate.relative_to(path)
        if candidate.is_symlink():
            raise HandoffError(f"model snapshot contains a symlink: {candidate}")
        if ".cache" in relative.parts or (
            candidate.name != MODEL_MARKER
            and candidate.name.startswith(".trace_model_revision.")
        ):
            continue
        if candidate.name == MODEL_MARKER and not include_marker:
            continue
        if candidate.is_file():
            result.append(candidate)
    return sorted(result, key=lambda item: item.relative_to(path).as_posix())


def _snapshot_manifest(path: Path, *, include_marker: bool) -> dict[str, dict[str, Any]]:
    return {
        item.relative_to(path).as_posix(): {
            "size": item.stat().st_size,
            "sha256": _sha256_file(item),
        }
        for item in _snapshot_files(path, include_marker=include_marker)
    }


def _clean_marker_temporaries(path: Path) -> None:
    candidates = {
        *path.glob(".trace_model_revision.*"),
        *path.glob("..trace_model_revision*"),
        *path.glob("trace_training_provenance.tmp.*"),
    }
    for candidate in sorted(candidates):
        if candidate.name == MODEL_MARKER:
            continue
        if candidate.is_symlink() or not candidate.is_file():
            raise HandoffError(f"unsafe model publication temporary: {candidate}")
        candidate.unlink()


def _ensure_training_provenance(config: Config) -> None:
    path = config.model_path / "trace_training_provenance.json"
    hashes = {
        item.name: _sha256_file(item)
        for item in sorted(config.model_path.glob("*.safetensors"))
    }
    if path.is_file():
        document = _load_json(path)
        expected = {
            "run_name": config.experiment_name,
            "source_commit": config.training_source_commit,
            "base_model": config.base_model_id,
            "base_revision": config.base_model_revision,
            "dataset": config.dataset_id,
            "dataset_revision": config.dataset_revision,
            "checkpoint_step": config.checkpoint_step,
            "checkpoint_retention": 1,
            "merged_safetensor_sha256": hashes,
        }
        mismatches = {
            key: (document.get(key), value)
            for key, value in expected.items()
            if document.get(key) != value
        }
        if mismatches:
            raise HandoffError(f"training provenance mismatch: {mismatches}")
        return
    document = {
        "run_name": config.experiment_name,
        "wandb_url": config.wandb_url,
        "source_commit": config.training_source_commit,
        "base_model": config.base_model_id,
        "base_revision": config.base_model_revision,
        "dataset": config.dataset_id,
        "dataset_revision": config.dataset_revision,
        "checkpoint_step": config.checkpoint_step,
        "checkpoint_retention": 1,
        "merged_safetensor_sha256": hashes,
        "provenance_created_at": _utc_now(),
        "provenance_created_by": "run_trace_eval_after_training.py",
    }
    temporary = path.with_suffix(f".tmp.{os.getpid()}")
    try:
        temporary.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_token(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise HandoffError(f"Hugging Face token file is missing or unsafe: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise HandoffError(f"Hugging Face token file must have mode 600 or stricter: {path}")
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise HandoffError(f"Hugging Face token file is empty: {path}")
    return token


def _redact(value: object, token: str | None) -> str:
    text = str(value)
    return text.replace(token, "<redacted>") if token else text


def _scrubbed_environment() -> dict[str, str]:
    secret_suffixes = ("_TOKEN", "_SECRET", "_PASSWORD", "_API_KEY", "_ACCESS_KEY")
    exact_secret_names = {"HF_TOKEN", "WANDB_API_KEY", "GITHUB_TOKEN", "GH_TOKEN"}
    return {
        key: value
        for key, value in os.environ.items()
        if key.upper() not in exact_secret_names
        and not key.upper().endswith(secret_suffixes)
    }


def _http_status(error: BaseException) -> int | None:
    response = getattr(error, "response", None)
    return getattr(response, "status_code", None)


def _retry(
    config: Config,
    operation: str,
    function: Callable[[], Any],
    *,
    token: str,
) -> Any:
    attempt = 1
    while True:
        try:
            return function()
        except (HfHubHTTPError, RequestException) as error:
            status = _http_status(error)
            if status == 409:
                raise
            if status is not None and status < 500 and status not in {408, 429}:
                raise
            if config.hf_attempts > 0 and attempt >= config.hf_attempts:
                raise
            delay = min(
                config.hf_retry_cap_seconds,
                config.hf_retry_base_seconds * (2 ** (attempt - 1)),
            )
            print(
                f"[trace-eval-handoff:retry] operation={operation} attempt={attempt} "
                f"sleep={delay:g} error={_redact(error, token)}",
                flush=True,
            )
            time.sleep(delay)
            attempt += 1


def _repo_info_optional(
    config: Config,
    api: HfApi,
    repo_id: str,
    *,
    token: str,
    revision: str | None = None,
) -> Any | None:
    try:
        return _retry(
            config,
            f"model_info:{repo_id}",
            lambda: api.model_info(
                repo_id,
                revision=revision,
                files_metadata=True,
                token=token,
            ),
            token=token,
        )
    except HfHubHTTPError as error:
        if _http_status(error) == 404:
            return None
        raise


def _require_private(info: Any, repo_id: str) -> None:
    if getattr(info, "private", None) is not True:
        raise HandoffError(f"refusing non-private model repository: {repo_id}")


def _sibling_lfs_sha(sibling: Any) -> str | None:
    lfs = getattr(sibling, "lfs", None)
    if isinstance(lfs, Mapping):
        value = lfs.get("sha256")
    else:
        value = getattr(lfs, "sha256", None)
    return str(value) if value else None


def _remote_names(info: Any) -> set[str]:
    siblings = getattr(info, "siblings", None)
    if not isinstance(siblings, (list, tuple)):
        raise HandoffError("repository returned no file inventory")
    return {str(getattr(item, "rfilename", "") or "") for item in siblings}


def _verify_remote_snapshot(
    config: Config,
    info: Any,
    manifest: Mapping[str, Mapping[str, Any]],
    *,
    repo_id: str,
    token: str,
    allow_subset: bool = False,
) -> None:
    _require_private(info, repo_id)
    siblings = {str(getattr(item, "rfilename", "") or ""): item for item in info.siblings}
    names = set(siblings)
    payload_names = names - {".gitattributes"}
    unexpected = sorted(payload_names - set(manifest))
    missing = [] if allow_subset else sorted(set(manifest) - payload_names)
    if missing or unexpected:
        raise HandoffError(
            f"remote snapshot inventory mismatch for {repo_id}: missing={missing} unexpected={unexpected}"
        )
    revision = str(getattr(info, "sha", "") or "")
    if not HF_COMMIT_RE.fullmatch(revision):
        if allow_subset and not payload_names:
            return
        raise HandoffError(f"repository did not return an immutable commit: {repo_id}")
    selected = sorted(payload_names) if allow_subset else sorted(manifest)
    for relative in selected:
        expected = manifest[relative]
        sibling = siblings[relative]
        remote_size = getattr(sibling, "size", None)
        if remote_size is not None and int(remote_size) != int(expected["size"]):
            raise HandoffError(f"remote size mismatch for {repo_id}/{relative}")
        lfs_sha = _sibling_lfs_sha(sibling)
        if lfs_sha:
            if lfs_sha != expected["sha256"]:
                raise HandoffError(f"remote LFS hash mismatch for {repo_id}/{relative}")
            continue
        if int(expected["size"]) > 64 * 1024 * 1024:
            raise HandoffError(f"large remote file lacks LFS hash metadata: {repo_id}/{relative}")
        downloaded = Path(
            _retry(
                config,
                f"download_remote_file:{relative}",
                lambda: hf_hub_download(
                    repo_id=repo_id,
                    filename=relative,
                    revision=revision,
                    repo_type="model",
                    token=token,
                ),
                token=token,
            )
        )
        if _sha256_file(downloaded) != expected["sha256"]:
            raise HandoffError(f"remote content hash mismatch for {repo_id}/{relative}")


def _validate_marker_document(
    config: Config,
    marker: Mapping[str, Any],
    base_manifest: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if marker.get("schema_version") != "trace-model-revision-v1":
        raise HandoffError("local model marker schema mismatch")
    if marker.get("model_origin") != "local_registration":
        raise HandoffError("local model marker origin mismatch")
    if marker.get("slug") != config.source_model_slug:
        raise HandoffError("local model marker slug mismatch")
    local_revision = str(marker.get("immutable_revision") or "")
    if not LOCAL_REVISION_RE.fullmatch(local_revision):
        raise HandoffError("local model marker has an invalid content revision")
    recorded = marker.get("file_sha256")
    expected_hashes = {key: value["sha256"] for key, value in base_manifest.items()}
    if recorded != expected_hashes:
        raise HandoffError("local model marker does not bind the current model snapshot")
    if marker.get("file_count") != len(expected_hashes):
        raise HandoffError("local model marker file count mismatch")
    expected_revision = f"sha256set:{hashlib.sha256(_canonical_json(expected_hashes).encode('utf-8')).hexdigest()}"
    if local_revision != expected_revision:
        raise HandoffError("local model marker content revision does not match its file hashes")
    source = str(marker.get("source") or "")
    prefix = f"{config.canonical_repo}@"
    if not source.startswith(prefix) or not HF_COMMIT_RE.fullmatch(source[len(prefix) :]):
        raise HandoffError("local model marker source is not a canonical immutable commit")
    return dict(marker)


def _marker_document(config: Config, base_manifest: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    return _validate_marker_document(
        config,
        _load_json(config.model_path / MODEL_MARKER),
        base_manifest,
    )


def _run_model_helper(config: Config, arguments: Sequence[str]) -> None:
    environment = _scrubbed_environment()
    environment["PYTHONPATH"] = ":".join(
        (
            str(config.eval_deps_root),
            str(REPO_ROOT),
            str(REPO_ROOT / "scripts"),
            str(config.vlmeval_root),
            environment.get("PYTHONPATH", ""),
        )
    )
    subprocess.run(
        [str(config.python_bin), str(REPO_ROOT / "scripts" / "prepare_trace_final25_models.py"), *arguments],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
    )


def _deep_verify_local(config: Config, local_revision: str) -> None:
    _run_model_helper(
        config,
        [
            "verify",
            "--entry",
            f"{config.source_model_slug}={config.model_path}={local_revision}",
            "--deep",
        ],
    )


def _register_local(config: Config, base_revision: str) -> str:
    _run_model_helper(
        config,
        [
            "register-local",
            "--slug",
            config.source_model_slug,
            "--path",
            str(config.model_path),
            "--source",
            f"{config.canonical_repo}@{base_revision}",
        ],
    )
    marker = _load_json(config.model_path / MODEL_MARKER)
    revision = str(marker.get("immutable_revision") or "")
    if not LOCAL_REVISION_RE.fullmatch(revision):
        raise HandoffError("register-local did not emit a valid sha256set revision")
    _deep_verify_local(config, revision)
    return revision


def _write_claim(config: Config, *, action: str, base_manifest_sha256: str, **details: Any) -> None:
    document = {
        "schema_version": CLAIM_SCHEMA,
        "config_sha256": config.config_sha256,
        "canonical_repo": config.canonical_repo,
        "temporary_repo": config.temporary_repo,
        "action": action,
        "base_manifest_sha256": base_manifest_sha256,
        **details,
    }
    if config.claim_path.exists():
        prior = _load_json(config.claim_path)
        if any(prior.get(key) != value for key, value in document.items()):
            raise HandoffError("canonical repository claim does not match the resumed operation")
        return
    _atomic_json(
        config.claim_path,
        {
            **document,
            "claimed_at": _utc_now(),
        },
    )


def _claim_allows_repair(config: Config, base_manifest_sha256: str) -> bool:
    if not config.claim_path.is_file():
        return False
    claim = _load_json(config.claim_path)
    return (
        claim.get("schema_version") == CLAIM_SCHEMA
        and claim.get("config_sha256") == config.config_sha256
        and claim.get("canonical_repo") == config.canonical_repo
        and claim.get("base_manifest_sha256") == base_manifest_sha256
        and claim.get("action") == "direct_upload"
    )


def _install_remote_marker(
    config: Config,
    base_manifest: Mapping[str, Mapping[str, Any]],
    *,
    revision: str,
    token: str,
) -> None:
    downloaded = Path(
        _retry(
            config,
            "download_remote_model_marker",
            lambda: hf_hub_download(
                repo_id=config.canonical_repo,
                filename=MODEL_MARKER,
                revision=revision,
                repo_type="model",
                token=token,
            ),
            token=token,
        )
    )
    payload = downloaded.read_bytes()
    try:
        marker = json.loads(payload)
    except json.JSONDecodeError as error:
        raise HandoffError("remote model marker is malformed") from error
    if not isinstance(marker, dict):
        raise HandoffError("remote model marker is not an object")
    _validate_marker_document(config, marker, base_manifest)
    temporary = config.model_path / f"{MODEL_MARKER}.tmp.{os.getpid()}"
    temporary.write_bytes(payload)
    os.replace(temporary, config.model_path / MODEL_MARKER)


def _complete_marker_handoff(
    config: Config,
    api: HfApi,
    info: Any,
    base_manifest: Mapping[str, Mapping[str, Any]],
    *,
    token: str,
) -> ModelIdentity:
    base_revision = str(info.sha)
    remote_has_marker = MODEL_MARKER in _remote_names(info)
    marker_path = config.model_path / MODEL_MARKER
    if remote_has_marker:
        if not marker_path.is_file():
            _install_remote_marker(
                config,
                base_manifest,
                revision=base_revision,
                token=token,
            )
        marker = _marker_document(config, base_manifest)
        local_revision = str(marker["immutable_revision"])
        _deep_verify_local(config, local_revision)
        full_manifest = _snapshot_manifest(config.model_path, include_marker=True)
        _verify_remote_snapshot(
            config,
            info,
            full_manifest,
            repo_id=config.canonical_repo,
            token=token,
        )
        source = str(marker.get("source") or "")
        prefix = f"{config.canonical_repo}@"
        if not source.startswith(prefix) or not HF_COMMIT_RE.fullmatch(source[len(prefix) :]):
            raise HandoffError("remote marker does not record a canonical immutable base commit")
        source_revision = source[len(prefix) :]
        source_info = _repo_info_optional(
            config,
            api,
            config.canonical_repo,
            token=token,
            revision=source_revision,
        )
        if source_info is None or str(source_info.sha) != source_revision:
            raise HandoffError("remote marker base repository commit is unavailable")
        _verify_remote_snapshot(
            config,
            source_info,
            base_manifest,
            repo_id=config.canonical_repo,
            token=token,
        )
        return ModelIdentity(local_revision, base_revision, source_revision)

    if marker_path.is_file():
        marker = _marker_document(config, base_manifest)
        if marker.get("source") != f"{config.canonical_repo}@{base_revision}":
            raise HandoffError("existing local marker was registered against a different repository commit")
        local_revision = str(marker["immutable_revision"])
        _deep_verify_local(config, local_revision)
    else:
        local_revision = _register_local(config, base_revision)

    marker_path = config.model_path / MODEL_MARKER
    try:
        _retry(
            config,
            "upload_model_marker",
            lambda: api.upload_file(
                path_or_fileobj=marker_path,
                path_in_repo=MODEL_MARKER,
                repo_id=config.canonical_repo,
                repo_type="model",
                parent_commit=base_revision,
                commit_message="Record TRACE model content revision",
                token=token,
            ),
            token=token,
        )
    except Exception:
        ambiguous = _repo_info_optional(config, api, config.canonical_repo, token=token)
        if ambiguous is None or MODEL_MARKER not in _remote_names(ambiguous):
            raise
    final_info = _repo_info_optional(config, api, config.canonical_repo, token=token)
    if final_info is None:
        raise HandoffError("canonical repository disappeared after marker upload")
    full_manifest = _snapshot_manifest(config.model_path, include_marker=True)
    _verify_remote_snapshot(
        config,
        final_info,
        full_manifest,
        repo_id=config.canonical_repo,
        token=token,
    )
    return ModelIdentity(local_revision, str(final_info.sha), base_revision)


def _write_handoff_receipt(
    config: Config,
    identity: ModelIdentity,
    full_manifest: Mapping[str, Mapping[str, Any]],
) -> None:
    document = {
        "schema_version": RECEIPT_SCHEMA,
        "config_sha256": config.config_sha256,
        "experiment_name": config.experiment_name,
        "checkpoint_step": config.checkpoint_step,
        "model_path": str(config.model_path),
        "source_model_slug": config.source_model_slug,
        "canonical_repo": config.canonical_repo,
        "base_repository_revision": identity.base_repository_revision,
        "local_revision": identity.local_revision,
        "repository_revision": identity.repository_revision,
        "model_manifest_sha256": _sha256_json(full_manifest),
        "verified_at": _utc_now(),
    }
    _atomic_json(config.receipt_path, document)


def _load_completed_handoff(
    config: Config,
    api: HfApi,
    *,
    token: str,
) -> ModelIdentity | None:
    if not config.receipt_path.is_file():
        return None
    receipt = _load_json(config.receipt_path)
    expected = {
        "schema_version": RECEIPT_SCHEMA,
        "config_sha256": config.config_sha256,
        "experiment_name": config.experiment_name,
        "model_path": str(config.model_path),
        "source_model_slug": config.source_model_slug,
        "canonical_repo": config.canonical_repo,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise HandoffError("handoff receipt does not match the requested configuration")
    identity = ModelIdentity(
        local_revision=str(receipt.get("local_revision") or ""),
        repository_revision=str(receipt.get("repository_revision") or ""),
        base_repository_revision=str(receipt.get("base_repository_revision") or ""),
    )
    if not LOCAL_REVISION_RE.fullmatch(identity.local_revision):
        raise HandoffError("handoff receipt has an invalid local revision")
    if not HF_COMMIT_RE.fullmatch(identity.repository_revision):
        raise HandoffError("handoff receipt has an invalid repository revision")
    if not HF_COMMIT_RE.fullmatch(identity.base_repository_revision):
        raise HandoffError("handoff receipt has an invalid base repository revision")
    _deep_verify_local(config, identity.local_revision)
    base_manifest = _snapshot_manifest(config.model_path, include_marker=False)
    marker = _marker_document(config, base_manifest)
    if marker.get("source") != (
        f"{config.canonical_repo}@{identity.base_repository_revision}"
    ):
        raise HandoffError("handoff receipt base revision disagrees with the local marker")
    full_manifest = _snapshot_manifest(config.model_path, include_marker=True)
    if receipt.get("model_manifest_sha256") != _sha256_json(full_manifest):
        raise HandoffError("handoff receipt model manifest no longer matches local files")
    info = _repo_info_optional(
        config,
        api,
        config.canonical_repo,
        token=token,
        revision=identity.repository_revision,
    )
    if info is None or str(info.sha) != identity.repository_revision:
        raise HandoffError("pinned canonical repository revision is unavailable")
    _verify_remote_snapshot(
        config,
        info,
        full_manifest,
        repo_id=config.canonical_repo,
        token=token,
    )
    base_info = _repo_info_optional(
        config,
        api,
        config.canonical_repo,
        token=token,
        revision=identity.base_repository_revision,
    )
    if base_info is None or str(base_info.sha) != identity.base_repository_revision:
        raise HandoffError("pinned canonical base revision is unavailable")
    _verify_remote_snapshot(
        config,
        base_info,
        base_manifest,
        repo_id=config.canonical_repo,
        token=token,
    )
    return identity


def _canonicalize_model(
    config: Config,
    status: StatusWriter,
    *,
    api_factory: Callable[..., HfApi] = HfApi,
) -> ModelIdentity:
    token = _read_token(config.token_file)
    try:
        api = api_factory(token=token)
        completed = _load_completed_handoff(config, api, token=token)
        if completed is not None:
            status.write("model_ready", detail="verified existing immutable handoff")
            return completed

        status.write("hashing_model", detail="building the local model manifest")
        base_manifest = _snapshot_manifest(config.model_path, include_marker=False)
        base_manifest_sha256 = _sha256_json(base_manifest)
        canonical = _repo_info_optional(config, api, config.canonical_repo, token=token)
        if canonical is not None:
            _require_private(canonical, config.canonical_repo)
            remote_has_marker = MODEL_MARKER in _remote_names(canonical)
            if remote_has_marker and not (
                config.model_path / MODEL_MARKER
            ).is_file():
                _install_remote_marker(
                    config,
                    base_manifest,
                    revision=str(canonical.sha),
                    token=token,
                )
            try:
                manifest = (
                    _snapshot_manifest(config.model_path, include_marker=True)
                    if MODEL_MARKER in _remote_names(canonical)
                    else base_manifest
                )
                _verify_remote_snapshot(
                    config,
                    canonical,
                    manifest,
                    repo_id=config.canonical_repo,
                    token=token,
                )
            except HandoffError:
                if remote_has_marker:
                    raise HandoffError(
                        "canonical repository has a marker but its immutable snapshot does not match; refusing repair"
                    )
                if not _claim_allows_repair(config, base_manifest_sha256):
                    raise HandoffError(
                        "canonical repository exists but does not match this model; refusing to overwrite it"
                    )
                remote_payload = _remote_names(canonical) - {".gitattributes", MODEL_MARKER}
                if not remote_payload.issubset(base_manifest):
                    raise HandoffError(
                        "claimed canonical repository contains files outside the expected model snapshot"
                    )
                _verify_remote_snapshot(
                    config,
                    canonical,
                    base_manifest,
                    repo_id=config.canonical_repo,
                    token=token,
                    allow_subset=True,
                )
                if "trace_training_provenance.json" in _remote_names(canonical):
                    remote_provenance = Path(
                        _retry(
                            config,
                            "download_remote_training_provenance",
                            lambda: hf_hub_download(
                                repo_id=config.canonical_repo,
                                filename="trace_training_provenance.json",
                                revision=str(canonical.sha),
                                token=token,
                            ),
                            token=token,
                        )
                    )
                    if remote_provenance.read_bytes() != (
                        config.model_path / "trace_training_provenance.json"
                    ).read_bytes():
                        raise HandoffError("claimed canonical repository contains different training provenance")
                status.write("uploading_model", detail="resuming canonical model upload")
                try:
                    _retry(
                        config,
                        "resume_canonical_upload",
                        lambda: api.upload_folder(
                            repo_id=config.canonical_repo,
                            repo_type="model",
                            folder_path=config.model_path,
                            parent_commit=(
                                str(canonical.sha)
                                if HF_COMMIT_RE.fullmatch(str(canonical.sha or ""))
                                else None
                            ),
                            delete_patterns="*",
                            ignore_patterns=[
                                MODEL_MARKER,
                                ".trace_model_revision.*",
                                "..trace_model_revision*",
                                ".cache",
                                ".cache/**",
                            ],
                            commit_message="Publish trained TRACE model",
                            token=token,
                        ),
                        token=token,
                    )
                except Exception:
                    ambiguous = _repo_info_optional(
                        config, api, config.canonical_repo, token=token
                    )
                    if ambiguous is None:
                        raise
                    try:
                        _verify_remote_snapshot(
                            config,
                            ambiguous,
                            base_manifest,
                            repo_id=config.canonical_repo,
                            token=token,
                        )
                    except HandoffError:
                        raise
                canonical = _repo_info_optional(config, api, config.canonical_repo, token=token)
                if canonical is None:
                    raise HandoffError("canonical repository disappeared after upload")
                _verify_remote_snapshot(
                    config,
                    canonical,
                    base_manifest,
                    repo_id=config.canonical_repo,
                    token=token,
                )
        else:
            temporary = _repo_info_optional(config, api, config.temporary_repo, token=token)
            moved = False
            if temporary is not None:
                _require_private(temporary, config.temporary_repo)
                try:
                    _verify_remote_snapshot(
                        config,
                        temporary,
                        base_manifest,
                        repo_id=config.temporary_repo,
                        token=token,
                    )
                except HandoffError as error:
                    print(
                        "[trace-eval-handoff] temporary repository is incomplete; "
                        f"using direct canonical upload ({_redact(error, token)})",
                        flush=True,
                    )
                else:
                    _write_claim(
                        config,
                        action="move",
                        base_manifest_sha256=base_manifest_sha256,
                        temporary_revision=str(temporary.sha),
                    )
                    latest_temp = _repo_info_optional(
                        config, api, config.temporary_repo, token=token
                    )
                    latest_canonical = _repo_info_optional(
                        config, api, config.canonical_repo, token=token
                    )
                    if latest_canonical is not None:
                        canonical = latest_canonical
                    elif latest_temp is None or str(latest_temp.sha) != str(temporary.sha):
                        raise HandoffError("temporary repository changed before the server-side move")
                    else:
                        _require_private(latest_temp, config.temporary_repo)
                        status.write("moving_model_repo", detail=f"{config.temporary_repo} -> {config.canonical_repo}")
                        try:
                            _retry(
                                config,
                                "move_model_repo",
                                lambda: api.move_repo(
                                    from_id=config.temporary_repo,
                                    to_id=config.canonical_repo,
                                    repo_type="model",
                                    token=token,
                                ),
                                token=token,
                            )
                        except Exception:
                            ambiguous = _repo_info_optional(
                                config, api, config.canonical_repo, token=token
                            )
                            if ambiguous is None:
                                raise
                        canonical = _repo_info_optional(
                            config, api, config.canonical_repo, token=token
                        )
                    moved = canonical is not None
            if not moved:
                _write_claim(
                    config,
                    action="direct_upload",
                    base_manifest_sha256=base_manifest_sha256,
                )
                status.write("uploading_model", detail=f"direct upload to {config.canonical_repo}")
                _retry(
                    config,
                    "create_canonical_repo",
                    lambda: api.create_repo(
                        repo_id=config.canonical_repo,
                        repo_type="model",
                        private=True,
                        exist_ok=True,
                        token=token,
                    ),
                    token=token,
                )
                canonical = _repo_info_optional(config, api, config.canonical_repo, token=token)
                parent_commit = (
                    str(canonical.sha)
                    if canonical is not None
                    and HF_COMMIT_RE.fullmatch(str(canonical.sha or ""))
                    else None
                )
                if canonical is not None:
                    _require_private(canonical, config.canonical_repo)
                    initial_payload = _remote_names(canonical) - {".gitattributes"}
                    if initial_payload:
                        raise HandoffError(
                            "canonical repository acquired unexpected content before direct upload"
                        )
                try:
                    _retry(
                        config,
                        "upload_canonical_model",
                        lambda: api.upload_folder(
                            repo_id=config.canonical_repo,
                            repo_type="model",
                            folder_path=config.model_path,
                            parent_commit=parent_commit,
                            delete_patterns="*",
                            ignore_patterns=[
                                MODEL_MARKER,
                                ".trace_model_revision.*",
                                "..trace_model_revision*",
                                ".cache",
                                ".cache/**",
                            ],
                            commit_message="Publish trained TRACE model",
                            token=token,
                        ),
                        token=token,
                    )
                except Exception:
                    ambiguous = _repo_info_optional(
                        config, api, config.canonical_repo, token=token
                    )
                    if ambiguous is None:
                        raise
                    try:
                        _verify_remote_snapshot(
                            config,
                            ambiguous,
                            base_manifest,
                            repo_id=config.canonical_repo,
                            token=token,
                        )
                    except HandoffError:
                        raise
                canonical = _repo_info_optional(config, api, config.canonical_repo, token=token)
            if canonical is None:
                raise HandoffError("canonical repository is unavailable after publication")
            _verify_remote_snapshot(
                config,
                canonical,
                base_manifest,
                repo_id=config.canonical_repo,
                token=token,
            )

        status.write("registering_model", detail="binding local content hashes to the canonical repository")
        identity = _complete_marker_handoff(
            config,
            api,
            canonical,
            base_manifest,
            token=token,
        )
        full_manifest = _snapshot_manifest(config.model_path, include_marker=True)
        _write_handoff_receipt(config, identity, full_manifest)
        status.write(
            "model_ready",
            local_revision=identity.local_revision,
            repository_revision=identity.repository_revision,
        )
        return identity
    except Exception as error:
        raise HandoffError(_redact(error, token)) from None
    finally:
        token = ""


def _eval_environment(config: Config) -> dict[str, str]:
    environment = _scrubbed_environment()
    environment.update(
        {
            "PYTHON_BIN": str(config.python_bin),
            "GPU_GROUPS": " ".join(config.gpu_groups),
            "EVAL_DEPS_ROOT": str(config.eval_deps_root),
            "VLMEVALKIT_ROOT": str(config.vlmeval_root),
            "DATASET_MANIFEST": str(config.dataset_manifest),
            "JUDGE_MODEL": str(config.judge_model),
            "JUDGE_REVISION": config.judge_revision,
            "GEN_PORT_START": str(config.generation_port_start),
            "JUDGE_PORT_START": str(config.judge_port_start),
            "CAMPAIGN_ROOT": str(config.campaign_root),
            "SCORE_ROOT": str(config.score_root),
            "LOG_ROOT": str(config.eval_log_root),
            "RUN_LOCAL_ARCHIVE": "1",
            "LOCAL_ARCHIVE_SPOOL_ROOT": str(config.archive_spool_root),
        }
    )
    return environment


def _campaign_models(
    config: Config,
    identity: ModelIdentity,
) -> tuple[EvaluationModel, ...]:
    return (
        EvaluationModel(
            source_model_slug=config.source_model_slug,
            local_model_path=config.model_path,
            source_revision=identity.local_revision,
            model_id=config.public_model_id,
            model_revision=identity.repository_revision,
            display_name=config.display_name,
            repository_id=config.canonical_repo,
            repository_revision=identity.repository_revision,
        ),
        EvaluationModel(
            source_model_slug=config.base_source_model_slug,
            local_model_path=config.base_model_path,
            source_revision=config.base_model_revision,
            model_id=config.base_public_model_id,
            model_revision=config.base_model_revision,
            display_name=config.base_display_name,
            repository_id=config.base_model_id,
            repository_revision=config.base_model_revision,
        ),
    )


def _model_receipt(model: EvaluationModel) -> dict[str, str]:
    return {
        "source_model_slug": model.source_model_slug,
        "local_model_path": str(model.local_model_path),
        "source_revision": model.source_revision,
        "model_id": model.model_id,
        "model_revision": model.model_revision,
        "display_name": model.display_name,
        "repository_id": model.repository_id,
        "repository_revision": model.repository_revision,
    }


def _eval_command(config: Config, identity: ModelIdentity) -> list[str]:
    command = [
        "bash",
        str(REPO_ROOT / "scripts" / "run_trace_eval.sh"),
    ]
    for model in _campaign_models(config, identity):
        command.extend(
            (
                "--model",
                model.source_model_slug,
                str(model.local_model_path),
                model.source_revision,
                f"{model.repository_id}@{model.repository_revision}",
                model.display_name,
            )
        )
    command.extend(
        (
            "--seeds",
            *(str(seed) for seed in config.seeds),
            "--delta",
            f"TRACE-Base={config.source_model_slug}={config.base_source_model_slug}",
            "--run-tag",
            config.run_tag,
        )
    )
    return command


def _publisher_command(config: Config, identity: ModelIdentity) -> list[str]:
    command = [
        "nice",
        "-n",
        "10",
        str(config.python_bin),
        str(REPO_ROOT / "scripts" / "run_trace_eval_publish_worker.py"),
        "--campaign-root",
        str(config.campaign_root),
        "--score-root",
        str(config.score_root),
        "--archive-spool-root",
        str(config.archive_spool_root),
        "--dataset-manifest",
        str(config.dataset_manifest),
        "--vlmeval-root",
        str(config.vlmeval_root),
        "--work-root",
        str(config.publish_root),
        "--source-run-id",
        config.run_tag,
        "--public-run-id",
        config.public_run_id,
        *(item for seed in config.seeds for item in ("--seed", str(seed))),
    ]
    for model in _campaign_models(config, identity):
        command.extend(
            (
                "--model",
                model.source_model_slug,
                str(model.local_model_path),
                model.source_revision,
                model.model_id,
                model.model_revision,
                model.display_name,
                model.repository_id,
                model.repository_revision,
            )
        )
    command.extend(
        (
            "--judge",
            "qwen3-32b-judge",
            "Qwen/Qwen3-32B",
            config.judge_revision,
            "--token-file",
            str(config.token_file),
            "--paper-repo",
            config.paper_repo,
            "--timeout-seconds",
            f"{config.publisher_timeout_seconds:g}",
            "--allow-paper-run-upload",
            "--confirm-paper-run",
            f"UPLOAD {config.paper_repo}/{config.public_run_id}",
        )
    )
    return command


def _status_command(config: Config) -> list[str]:
    command = [
        str(config.python_bin),
        str(REPO_ROOT / "scripts" / "status_trace_eval.py"),
        "--campaign-root",
        str(config.campaign_root),
        "--score-root",
        str(config.score_root),
        "--dataset-manifest",
        str(config.dataset_manifest),
        "--archive-spool-root",
        str(config.archive_spool_root),
        "--vlmeval-root",
        str(config.vlmeval_root),
    ]
    for slug in (config.source_model_slug, config.base_source_model_slug):
        command.extend(("--model-slug", slug))
    command.extend(
        ("--seeds", *(str(seed) for seed in config.seeds), "--fail-if-incomplete")
    )
    return command


def _campaign_complete(config: Config) -> bool:
    if not config.campaign_root.is_dir():
        return False
    completed = subprocess.run(
        _status_command(config),
        cwd=REPO_ROOT,
        env=_eval_environment(config),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def _gpu_compute_pids() -> tuple[int, ...]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid",
            "--format=csv,noheader,nounits",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise HandoffError(f"nvidia-smi failed while checking GPU ownership: {completed.stderr.strip()}")
    return tuple(sorted({int(line.strip()) for line in completed.stdout.splitlines() if line.strip().isdigit()}))


def _busy_ports(config: Config) -> tuple[int, ...]:
    ports = [
        *(config.generation_port_start + offset for offset in range(len(config.gpu_groups))),
        *(config.judge_port_start + offset for offset in range(len(config.gpu_groups))),
    ]
    busy: list[int] = []
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(0.1)
            if client.connect_ex(("127.0.0.1", port)) == 0:
                busy.append(port)
    return tuple(busy)


def _wait_for_gpu_release(config: Config, status: StatusWriter) -> None:
    while True:
        pids = _gpu_compute_pids()
        ports = _busy_ports(config)
        if not pids and not ports:
            return
        status.write(
            "waiting_gpu_release",
            detail=f"compute_pids={list(pids)} busy_ports={list(ports)}",
            compute_pids=list(pids),
            busy_ports=list(ports),
        )
        time.sleep(config.poll_seconds)


def _child_receipt_path(config: Config, role: str) -> Path:
    return config.child_root / f"{role}.json"


def _effective_child_command(command: Sequence[str]) -> tuple[str, ...]:
    if tuple(command[:3]) == ("nice", "-n", "10"):
        return tuple(command[3:])
    return tuple(command)


def _command_sha256(command: Sequence[str]) -> str:
    return hashlib.sha256("\0".join(command).encode("utf-8")).hexdigest()


def _discover_child(command: Sequence[str]) -> tuple[int, int] | None:
    expected = _effective_child_command(command)
    matches: list[tuple[int, int]] = []
    for candidate in Path("/proc").iterdir():
        if not candidate.name.isdigit():
            continue
        pid = int(candidate.name)
        if _process_cmdline(pid) != expected:
            continue
        start_ticks = _process_start_ticks(pid)
        if start_ticks is not None:
            matches.append((pid, start_ticks))
    if len(matches) > 1:
        raise HandoffError(f"multiple live children match command digest {_command_sha256(command)}")
    return matches[0] if matches else None


def _load_live_child(
    config: Config,
    role: str,
    *,
    command: Sequence[str],
    expected_tokens: Sequence[str],
) -> ChildHandle | None:
    path = _child_receipt_path(config, role)
    if not path.is_file():
        return None
    receipt = _load_json(path)
    expected_command_sha = _command_sha256(command)
    if (
        receipt.get("schema_version") != CHILD_SCHEMA
        or receipt.get("config_sha256") != config.config_sha256
        or receipt.get("role") != role
        or receipt.get("command_sha256") != expected_command_sha
        or receipt.get("expected_tokens") != list(expected_tokens)
    ):
        raise HandoffError(f"child receipt does not match this configuration: {path}")
    pid_value = receipt.get("pid")
    start_value = receipt.get("start_ticks")
    if pid_value is None or start_value is None:
        discovered = None
        for _ in range(20):
            discovered = _discover_child(command)
            if discovered is not None:
                break
            time.sleep(0.05)
        if discovered is None:
            return None
        pid_value, start_value = discovered
        _atomic_json(
            path,
            {
                **receipt,
                "pid": pid_value,
                "start_ticks": start_value,
                "discovered_at": _utc_now(),
            },
        )
    handle = ChildHandle(
        role=role,
        pid=int(pid_value),
        start_ticks=int(start_value),
        expected_tokens=tuple(expected_tokens),
    )
    return handle if _process_matches(
        handle.pid,
        start_ticks=handle.start_ticks,
        expected_tokens=handle.expected_tokens,
    ) else None


def _start_child(
    config: Config,
    *,
    role: str,
    command: Sequence[str],
    environment: Mapping[str, str],
    log_path: Path,
    expected_tokens: Sequence[str],
) -> ChildHandle:
    _ensure_private_directory(config.child_root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = _child_receipt_path(config, role)
    intent = {
        "schema_version": CHILD_SCHEMA,
        "config_sha256": config.config_sha256,
        "role": role,
        "pid": None,
        "start_ticks": None,
        "expected_tokens": list(expected_tokens),
        "command_sha256": _command_sha256(command),
        "launch_intent_at": _utc_now(),
    }
    _atomic_json(receipt_path, intent)
    stream = log_path.open("ab", buffering=0)
    try:
        process = subprocess.Popen(
            list(command),
            cwd=REPO_ROOT,
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    finally:
        stream.close()
    for _ in range(20):
        start_ticks = _process_start_ticks(process.pid)
        if start_ticks is not None:
            break
        if process.poll() is not None:
            raise HandoffError(f"{role} exited before its process receipt could be recorded")
        time.sleep(0.05)
    else:
        raise HandoffError(f"could not read {role} process identity")
    handle = ChildHandle(
        role=role,
        pid=process.pid,
        start_ticks=start_ticks,
        expected_tokens=tuple(expected_tokens),
        process=process,
    )
    _atomic_json(
        receipt_path,
        {
            **intent,
            "pid": process.pid,
            "start_ticks": start_ticks,
            "started_at": _utc_now(),
        },
    )
    return handle


def _child_running(handle: ChildHandle) -> bool:
    if handle.process is not None:
        return handle.process.poll() is None
    return _process_matches(
        handle.pid,
        start_ticks=handle.start_ticks,
        expected_tokens=handle.expected_tokens,
    )


def _publisher_config_sha256(config: Config, identity: ModelIdentity) -> str:
    models = _campaign_models(config, identity)
    document = {
        "archive_spool_root": str(config.archive_spool_root),
        "campaign_root": str(config.campaign_root),
        "dataset_manifest": str(config.dataset_manifest),
        "judge": {
            "source_model_id": "qwen3-32b-judge",
            "model_id": "Qwen/Qwen3-32B",
            "model_revision": config.judge_revision,
        },
        "models": [
            {
                "source_model_id": model.source_model_slug,
                "local_model_path": str(model.local_model_path),
                "source_revision": model.source_revision,
                "model_id": model.model_id,
                "model_revision": model.model_revision,
                "display_name": model.display_name,
                "repository_id": model.repository_id,
                "repository_revision": model.repository_revision,
            }
            for model in models
        ],
        "paper_repo": config.paper_repo,
        "public_run_id": config.public_run_id,
        "revision": "main",
        "score_root": str(config.score_root),
        "seeds": list(config.seeds),
        "source_run_id": config.run_tag,
        "suite_id": "trace_eval_v1",
        "vlmeval_root": str(config.vlmeval_root),
    }
    return _sha256_json(document)


def _publisher_complete(config: Config, identity: ModelIdentity) -> bool:
    path = config.publish_root / "status.json"
    if not path.is_file():
        return False
    try:
        status = _load_json(path)
    except HandoffError:
        return False
    upload_report = status.get("upload_report")
    manifest_sha = status.get("public_export_manifest_sha256")
    models = _campaign_models(config, identity)
    expected_slices = (
        ARCHIVE_STAGE_COUNT
        * TRACE_EVAL_BENCHMARK_COUNT
        * len(models)
        * len(config.seeds)
    )
    return (
        status.get("schema_version") == "trace-eval-publish-worker-status-v1"
        and status.get("config_sha256") == _publisher_config_sha256(config, identity)
        and status.get("phase") == "complete"
        and status.get("source_run_id") == config.run_tag
        and status.get("public_run_id") == config.public_run_id
        and status.get("models") == [model.source_model_slug for model in models]
        and status.get("seeds") == list(config.seeds)
        and status.get("expected_slices") == expected_slices
        and isinstance(manifest_sha, str)
        and re.fullmatch(r"[0-9a-f]{64}", manifest_sha) is not None
        and isinstance(upload_report, dict)
        and upload_report.get("run_id") == config.public_run_id
        and upload_report.get("public_export_manifest_sha256") == manifest_sha
    )


def _ensure_publisher(config: Config, identity: ModelIdentity) -> ChildHandle | None:
    _ensure_private_directory(config.publish_root)
    command = _publisher_command(config, identity)
    expected_tokens = ("run_trace_eval_publish_worker.py", config.public_run_id)
    existing = _load_live_child(
        config,
        "publisher",
        command=command,
        expected_tokens=expected_tokens,
    )
    if existing is not None:
        return existing
    return _start_child(
        config,
        role="publisher",
        command=command,
        environment=_eval_environment(config),
        log_path=config.publish_root / "worker.log",
        expected_tokens=expected_tokens,
    )


def _evaluation_receipt_path(config: Config) -> Path:
    return config.state_root / "evaluator-complete.json"


def _evaluation_complete(config: Config, identity: ModelIdentity) -> bool:
    path = _evaluation_receipt_path(config)
    if not path.is_file():
        return False
    receipt = _load_json(path)
    return (
        receipt.get("schema_version") == "trace-eval-supervised-launch-v2"
        and receipt.get("config_sha256") == config.config_sha256
        and receipt.get("models")
        == [_model_receipt(model) for model in _campaign_models(config, identity)]
        and receipt.get("command_sha256")
        == _command_sha256(_eval_command(config, identity))
    )


def _write_evaluation_receipt(config: Config, identity: ModelIdentity) -> None:
    _atomic_json(
        _evaluation_receipt_path(config),
        {
            "schema_version": "trace-eval-supervised-launch-v2",
            "config_sha256": config.config_sha256,
            "run_tag": config.run_tag,
            "models": [
                _model_receipt(model) for model in _campaign_models(config, identity)
            ],
            "command_sha256": _command_sha256(_eval_command(config, identity)),
            "completed_at": _utc_now(),
        },
    )


def _run_evaluation_and_publication(
    config: Config,
    identity: ModelIdentity,
    status: StatusWriter,
) -> None:
    eval_complete = _evaluation_complete(config, identity)
    eval_command = _eval_command(config, identity)
    eval_tokens = ("run_trace_eval.sh", config.run_tag)
    evaluator = (
        None
        if eval_complete
        else _load_live_child(
            config,
            "evaluator",
            command=eval_command,
            expected_tokens=eval_tokens,
        )
    )
    if not eval_complete and evaluator is None:
        _wait_for_gpu_release(config, status)
    publisher = _ensure_publisher(config, identity)
    if not eval_complete and evaluator is None:
        evaluator = _start_child(
            config,
            role="evaluator",
            command=eval_command,
            environment=_eval_environment(config),
            log_path=config.eval_log_root / "campaign.log",
            expected_tokens=eval_tokens,
        )

    attached_evaluator = evaluator is not None and evaluator.process is None
    while evaluator is not None and _child_running(evaluator):
        status.write(
            "evaluating",
            detail=f"evaluator_pid={evaluator.pid} publisher_pid={getattr(publisher, 'pid', None)}",
            evaluator_pid=evaluator.pid,
            publisher_pid=getattr(publisher, "pid", None),
        )
        time.sleep(config.poll_seconds)

    if evaluator is not None and evaluator.process is not None:
        return_code = evaluator.process.wait()
        if return_code != 0:
            raise HandoffError(f"evaluation launcher failed with exit code {return_code}")
        if not _campaign_complete(config):
            raise HandoffError("evaluation launcher exited without complete campaign receipts")
        _write_evaluation_receipt(config, identity)
    elif attached_evaluator:
        _wait_for_gpu_release(config, status)
        evaluator = _start_child(
            config,
            role="evaluator",
            command=eval_command,
            environment=_eval_environment(config),
            log_path=config.eval_log_root / "campaign.log",
            expected_tokens=eval_tokens,
        )
        while _child_running(evaluator):
            status.write("evaluating", detail=f"resume_evaluator_pid={evaluator.pid}")
            time.sleep(config.poll_seconds)
        if evaluator.process is None or evaluator.process.wait() != 0 or not _campaign_complete(config):
            raise HandoffError("resumed evaluation did not produce complete campaign receipts")
        _write_evaluation_receipt(config, identity)

    publisher_restarts = 0
    while not _publisher_complete(config, identity):
        if publisher is None or not _child_running(publisher):
            if publisher is not None and publisher.process is not None:
                publisher.process.wait()
            publisher_restarts += 1
            if publisher_restarts > 2:
                raise HandoffError("publication worker failed after two supervised restarts")
            publisher = _ensure_publisher(config, identity)
            if publisher is None:
                break
        status.write(
            "publishing",
            detail=f"publisher_pid={publisher.pid}",
            publisher_pid=publisher.pid,
        )
        time.sleep(config.poll_seconds)


def _validate_static_config(config: Config) -> None:
    for label, repo_id in (
        ("temporary repo", config.temporary_repo),
        ("canonical repo", config.canonical_repo),
        ("base model repo", config.base_model_id),
        ("paper repo", config.paper_repo),
    ):
        if not REPO_ID_RE.fullmatch(repo_id):
            raise HandoffError(f"invalid {label}: {repo_id}")
    if config.temporary_repo == config.canonical_repo:
        raise HandoffError("temporary and canonical repositories must differ")
    if not HF_COMMIT_RE.fullmatch(config.judge_revision):
        raise HandoffError("judge revision must be an immutable HF commit")
    if not HF_COMMIT_RE.fullmatch(config.training_source_commit):
        raise HandoffError("training source commit must be immutable")
    if not HF_COMMIT_RE.fullmatch(config.base_model_revision):
        raise HandoffError("base model revision must be an immutable HF commit")
    if config.source_model_slug == config.base_source_model_slug:
        raise HandoffError("TRACE and base source model slugs must differ")
    if config.public_model_id == config.base_public_model_id:
        raise HandoffError("TRACE and base public model ids must differ")
    if not config.seeds or len(set(config.seeds)) != len(config.seeds):
        raise HandoffError("evaluation seeds must be nonempty and unique")
    if not config.gpu_groups or len(set(config.gpu_groups)) != len(config.gpu_groups):
        raise HandoffError("GPU groups must be nonempty and unique")
    if config.poll_seconds <= 0 or config.hf_attempts < 0:
        raise HandoffError("poll interval must be positive and HF attempts cannot be negative")
    for path in (
        config.python_bin,
        config.dataset_manifest,
        config.judge_model,
        config.base_model_path,
        config.eval_deps_root,
        config.vlmeval_root,
    ):
        if not path.exists():
            raise HandoffError(f"required evaluation path is missing: {path}")


def _wait_for_training(config: Config, status: StatusWriter) -> None:
    while True:
        alive, pid = _training_is_alive(config)
        training_status = _training_status_text(config)
        if not alive:
            break
        status.write(
            "waiting_training",
            detail=f"training_pid={pid} training_status={training_status}",
            training_pid=pid,
            training_status=training_status,
        )
        time.sleep(config.poll_seconds)
    try:
        _validate_final_checkpoint(config)
        _validate_model_shape(config.model_path)
    except HandoffError as error:
        raise HandoffError(
            f"training process exited without a valid merged step-{config.checkpoint_step} model; "
            f"last_status={training_status!r}: {error}"
        ) from error


def run(config: Config) -> int:
    _validate_static_config(config)
    _ensure_private_directory(config.state_root)
    status = StatusWriter(config)
    token: str | None = None
    with HeldLock(config.lock_path):
        try:
            if config.status_path.is_file():
                prior = _load_json(config.status_path)
                if prior.get("config_sha256") != config.config_sha256:
                    raise HandoffError("existing supervisor state belongs to a different configuration")
                if prior.get("phase") == "complete" and config.receipt_path.is_file():
                    print(
                        "[trace-eval-handoff] revalidating prior complete handoff and campaign",
                        flush=True,
                    )
            _wait_for_training(config, status)
            status.write("validating_model", detail="final checkpoint and merged model are complete")
            _clean_marker_temporaries(config.model_path)
            _ensure_training_provenance(config)
            identity = _canonicalize_model(config, status)
            _run_evaluation_and_publication(config, identity, status)
            status.write(
                "complete",
                local_revision=identity.local_revision,
                repository_revision=identity.repository_revision,
                completed_at=_utc_now(),
            )
            return 0
        except Exception as error:
            safe_error = _redact(error, token)
            status.write(
                "error",
                error_type=type(error).__name__,
                error=safe_error,
                failed_at=_utc_now(),
            )
            print(f"[trace-eval-handoff:error] {type(error).__name__}: {safe_error}", file=sys.stderr)
            return 2
        finally:
            token = None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-name", required=True)
    parser.add_argument("--training-status", type=Path, required=True)
    parser.add_argument("--training-pid-file", type=Path, required=True)
    parser.add_argument("--training-script-name", required=True)
    parser.add_argument("--checkpoint-root", type=Path, required=True)
    parser.add_argument("--checkpoint-step", type=int, default=500)
    parser.add_argument("--world-size", type=int, default=8)
    parser.add_argument("--temporary-repo", required=True)
    parser.add_argument("--canonical-repo", required=True)
    parser.add_argument("--source-model-slug", required=True)
    parser.add_argument("--public-model-id", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--run-tag", required=True)
    parser.add_argument("--public-run-id", required=True)
    parser.add_argument("--paper-repo", default="maveryn/trace-eval-runs")
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--judge-model", type=Path, required=True)
    parser.add_argument("--judge-revision", required=True)
    parser.add_argument("--python-bin", type=Path, required=True)
    parser.add_argument("--eval-deps-root", type=Path, required=True)
    parser.add_argument("--vlmeval-root", type=Path, required=True)
    parser.add_argument("--seed", action="append", type=int, required=True)
    parser.add_argument("--gpu-group", action="append", required=True)
    parser.add_argument("--generation-port-start", type=int, default=18000)
    parser.add_argument("--judge-port-start", type=int, default=18100)
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    parser.add_argument(
        "--hf-attempts",
        type=int,
        default=0,
        help="maximum transient HF attempts; 0 retries until the service recovers",
    )
    parser.add_argument("--hf-retry-base-seconds", type=float, default=5.0)
    parser.add_argument("--hf-retry-cap-seconds", type=float, default=300.0)
    parser.add_argument("--publisher-timeout-seconds", type=float, default=172800.0)
    parser.add_argument("--training-source-commit", required=True)
    parser.add_argument("--base-model-id", required=True)
    parser.add_argument("--base-model-revision", required=True)
    parser.add_argument("--base-source-model-slug", required=True)
    parser.add_argument("--base-model-path", type=Path, required=True)
    parser.add_argument("--base-public-model-id", required=True)
    parser.add_argument("--base-display-name", required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--wandb-url", required=True)
    parser.add_argument("--assume-local-revision")
    parser.add_argument("--assume-repository-revision")
    parser.add_argument("--print-config", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _config_from_args(args: argparse.Namespace) -> Config:
    return Config(
        experiment_name=args.experiment_name,
        training_status=_absolute(args.training_status),
        training_pid_file=_absolute(args.training_pid_file),
        training_script_name=args.training_script_name,
        checkpoint_root=_absolute(args.checkpoint_root),
        checkpoint_step=args.checkpoint_step,
        world_size=args.world_size,
        temporary_repo=args.temporary_repo,
        canonical_repo=args.canonical_repo,
        source_model_slug=args.source_model_slug,
        public_model_id=args.public_model_id,
        display_name=args.display_name,
        run_tag=args.run_tag,
        public_run_id=args.public_run_id,
        paper_repo=args.paper_repo,
        token_file=_absolute(args.token_file),
        state_root=_absolute(args.state_root),
        dataset_manifest=_absolute(args.dataset_manifest),
        judge_model=_absolute(args.judge_model),
        judge_revision=args.judge_revision,
        python_bin=_absolute(args.python_bin),
        eval_deps_root=_absolute(args.eval_deps_root),
        vlmeval_root=_absolute(args.vlmeval_root),
        seeds=tuple(args.seed),
        gpu_groups=tuple(args.gpu_group),
        generation_port_start=args.generation_port_start,
        judge_port_start=args.judge_port_start,
        poll_seconds=args.poll_seconds,
        hf_attempts=args.hf_attempts,
        hf_retry_base_seconds=args.hf_retry_base_seconds,
        hf_retry_cap_seconds=args.hf_retry_cap_seconds,
        publisher_timeout_seconds=args.publisher_timeout_seconds,
        training_source_commit=args.training_source_commit,
        base_model_id=args.base_model_id,
        base_model_revision=args.base_model_revision,
        base_source_model_slug=args.base_source_model_slug,
        base_model_path=_absolute(args.base_model_path),
        base_public_model_id=args.base_public_model_id,
        base_display_name=args.base_display_name,
        dataset_id=args.dataset_id,
        dataset_revision=args.dataset_revision,
        wandb_url=args.wandb_url,
    )


def _print_config(config: Config, args: argparse.Namespace) -> None:
    identity = ModelIdentity(
        local_revision=args.assume_local_revision or "{local_revision}",
        repository_revision=args.assume_repository_revision or "{repository_revision}",
        base_repository_revision="{base_repository_revision}",
    )
    document = {
        "schema_version": "trace-eval-training-handoff-config-v1",
        "config_sha256": config.config_sha256,
        **config.digest_document(),
        "model_path": str(config.model_path),
        "campaign_root": str(config.campaign_root),
        "state_root": str(config.state_root),
        "eval_environment": {
            key: value
            for key, value in _eval_environment(config).items()
            if key
            in {
                "PYTHON_BIN",
                "GPU_GROUPS",
                "EVAL_DEPS_ROOT",
                "VLMEVALKIT_ROOT",
                "DATASET_MANIFEST",
                "JUDGE_MODEL",
                "CAMPAIGN_ROOT",
                "SCORE_ROOT",
            }
        },
        "eval_command": _eval_command(config, identity),
        "publisher_command": _publisher_command(config, identity),
    }
    print(json.dumps(document, indent=2, sort_keys=True))


def _dry_run(config: Config, args: argparse.Namespace) -> None:
    alive, pid = _training_is_alive(config)
    shallow_model_ready = True
    try:
        _validate_model_shape(config.model_path)
    except HandoffError:
        shallow_model_ready = False
    identity = ModelIdentity(
        local_revision=args.assume_local_revision or "{local_revision}",
        repository_revision=args.assume_repository_revision or "{repository_revision}",
        base_repository_revision="{base_repository_revision}",
    )
    print(
        json.dumps(
            {
                "training_alive": alive,
                "training_pid": pid,
                "training_status": _training_status_text(config),
                "model_ready": shallow_model_ready,
                "gpu_compute_pids": list(_gpu_compute_pids()),
                "busy_ports": list(_busy_ports(config)),
                "eval_command": _eval_command(config, identity),
                "publisher_command": _publisher_command(config, identity),
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    config = _config_from_args(args)
    if args.print_config:
        _print_config(config, args)
        return
    if args.dry_run:
        _dry_run(config, args)
        return
    raise SystemExit(run(config))


if __name__ == "__main__":
    main()
