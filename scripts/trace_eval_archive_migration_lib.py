#!/usr/bin/env python3
"""Integrity and safety primitives for the TRACE evaluation archive migration.

The old archive is treated as immutable input.  A migration starts by pinning
its commit and refs, then downloading a complete local backup.  The canonical
All31 campaign is split into the 648 Final24 stage identities used by the paper
and the 189 stage identities for the seven supplementary benchmarks.

Raw Final24 Parquet is never uploaded to the paper repository.  A separately
prepared neutral public export must be validated before it can be uploaded.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from huggingface_hub import CommitOperationAdd
from huggingface_hub.errors import RepositoryNotFoundError


INVENTORY_SCHEMA = "trace-eval-archive-inventory-v1"
BACKUP_SCHEMA = "trace-eval-archive-backup-v1"
SELECTION_SCHEMA = "trace-eval-archive-selection-v1"
VERIFICATION_SCHEMA = "trace-eval-archive-verification-v1"

DEFAULT_SOURCE_REPO = "maveryn/trace-final25-eval-runs"
DEFAULT_PAPER_REPO = "maveryn/trace-eval-runs"
DEFAULT_INTERNAL_REPO = "maveryn/trace-internal-eval-runs"
DEFAULT_SOURCE_REVISION = "main"
DEFAULT_CANONICAL_SUITE_PATH = (
    Path(__file__).resolve().parents[1] / "evaluation" / "trace_eval" / "suite.v1.json"
)
CANONICAL_RUN = "trace_final31_temp06_seed42_44_3models_v1"
CANONICAL_MODELS = (
    "qwen25vl7b-base",
    "trace-qwen25vl7b-answer-step500-rerun-20260715",
    "vero-qwen25-7b",
)
CANONICAL_SEEDS = (42, 43, 44)
CANONICAL_STAGES = ("generation", "extraction", "score")
SOURCE_STAGE_TO_CONFIG = {
    "generation": "responses",
    "extraction": "extractions",
    "score": "scores",
}
SUPPLEMENTARY_BENCHMARKS = (
    "chartmuseum",
    "physics",
    "screenspot",
    "mmvp",
    "screenspotpro",
    "screenspot_v2",
    "visulogic",
)
EXPECTED_PAPER_STAGE_SLICES = 648
EXPECTED_INTERNAL_STAGE_SLICES = 189

DATA_PATH_RE = re.compile(
    r"^data/(?P<stage>generation|extraction|score)/"
    r"run=(?P<run>[^/]+)/model=(?P<model>[^/]+)/seed=(?P<seed>[0-9]+)/"
    r"benchmark=(?P<benchmark>[^/]+)/part-(?P<digest>[0-9a-f]{64})\.parquet$"
)
NEUTRAL_REPO_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
PUBLIC_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
NON_NEUTRAL_REPO_TOKENS = frozenset(
    {"final24", "final25", "final31", "internal", "private", "raw", "archive"}
)


class MigrationError(RuntimeError):
    """Base class for migration failures."""


class MigrationIntegrityError(MigrationError):
    """Raised when content, coverage, or provenance differs from the plan."""


class MigrationSafetyError(MigrationError):
    """Raised when an operation would weaken privacy or delete data unsafely."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1_file(path: Path | str) -> str:
    file_path = Path(path)
    digest = hashlib.sha1()
    digest.update(f"blob {file_path.stat().st_size}\0".encode("ascii"))
    with file_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _document_digest(document: Mapping[str, Any], digest_key: str) -> str:
    material = dict(document)
    material.pop(digest_key, None)
    return sha256_bytes(canonical_json(material).encode("utf-8"))


def _seal_document(document: Mapping[str, Any], digest_key: str) -> dict[str, Any]:
    result = dict(document)
    result[digest_key] = _document_digest(result, digest_key)
    return result


def _verify_document(
    document: Mapping[str, Any], *, schema: str, digest_key: str, label: str
) -> dict[str, Any]:
    if document.get("schema_version") != schema:
        raise MigrationIntegrityError(
            f"{label} has unsupported schema {document.get('schema_version')!r}"
        )
    supplied = document.get(digest_key)
    actual = _document_digest(document, digest_key)
    if supplied != actual:
        raise MigrationIntegrityError(
            f"{label} digest mismatch: expected {supplied!r}, found {actual}"
        )
    return dict(document)


def _safe_repo_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise MigrationIntegrityError("repository path must be nonempty text")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise MigrationIntegrityError(f"unsafe repository path: {value!r}")
    normalized = path.as_posix()
    if normalized != value or normalized.startswith("/"):
        raise MigrationIntegrityError(f"non-canonical repository path: {value!r}")
    return normalized


def _portable_suite_path(path: Path | str) -> str:
    parts = Path(path).resolve().parts
    if "evaluation" in parts:
        offset = parts.index("evaluation")
        return PurePosixPath(*parts[offset:]).as_posix()
    return Path(path).name


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    _ensure_private_dir(path.parent)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _atomic_write_json(path: Path, document: Mapping[str, Any]) -> None:
    _atomic_write_bytes(
        path,
        (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def _load_json(path: Path | str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MigrationIntegrityError(f"cannot read JSON document {path}: {error}") from error
    if not isinstance(value, dict):
        raise MigrationIntegrityError(f"JSON document is not an object: {path}")
    return value


def read_token_file(path: Path | str) -> str:
    token_path = Path(path)
    mode = stat.S_IMODE(token_path.stat().st_mode)
    if mode & 0o077:
        raise MigrationSafetyError(f"token file must have mode 600 or stricter: {token_path}")
    token = token_path.read_text(encoding="utf-8").strip()
    if not token:
        raise MigrationSafetyError(f"token file is empty: {token_path}")
    return token


def _lfs_sha256(sibling: Any) -> str | None:
    lfs = getattr(sibling, "lfs", None)
    if isinstance(lfs, Mapping):
        value = lfs.get("sha256")
    else:
        value = getattr(lfs, "sha256", None) if lfs is not None else None
    return str(value) if value else None


def _ref_record(ref: Any) -> dict[str, str | None]:
    return {
        "name": str(getattr(ref, "name", "")),
        "ref": str(getattr(ref, "ref", "")),
        "target_commit": (
            str(getattr(ref, "target_commit"))
            if getattr(ref, "target_commit", None) is not None
            else None
        ),
    }


def _refs_document(refs: Any) -> dict[str, list[dict[str, str | None]]]:
    return {
        name: sorted(
            [_ref_record(ref) for ref in (getattr(refs, name, None) or [])],
            key=canonical_json,
        )
        for name in ("branches", "converts", "tags", "pull_requests")
    }


def _normalized_refs_document(value: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for name in ("branches", "converts", "tags", "pull_requests"):
        records = value.get(name)
        if not isinstance(records, list):
            raise MigrationIntegrityError(f"source ref section {name!r} is invalid")
        normalized: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, Mapping):
                raise MigrationIntegrityError(f"source ref record in {name!r} is invalid")
            normalized.append(
                {
                    "name": record.get("name"),
                    "ref": record.get("ref"),
                    "target_commit": record.get("target_commit"),
                }
            )
        result[name] = sorted(normalized, key=canonical_json)
    return result


def capture_source_inventory(
    *,
    api: Any,
    source_repo_id: str,
    source_revision: str,
    output: Path | str,
    token: str | None,
) -> dict[str, Any]:
    """Pin a private source repository and record its exact tree and refs."""

    initial = api.repo_info(
        repo_id=source_repo_id,
        repo_type="dataset",
        revision=source_revision,
        files_metadata=True,
        token=token,
    )
    if not bool(getattr(initial, "private", False)):
        raise MigrationSafetyError(f"source repository is not private: {source_repo_id}")
    commit = str(getattr(initial, "sha", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise MigrationIntegrityError(f"source did not resolve to a Git commit: {commit!r}")

    pinned = api.repo_info(
        repo_id=source_repo_id,
        repo_type="dataset",
        revision=commit,
        files_metadata=True,
        token=token,
    )
    if str(getattr(pinned, "sha", "")) != commit:
        raise MigrationIntegrityError("pinned source lookup resolved to a different commit")
    refs = api.list_repo_refs(repo_id=source_repo_id, repo_type="dataset", token=token)
    final_head = api.repo_info(
        repo_id=source_repo_id,
        repo_type="dataset",
        revision=source_revision,
        files_metadata=False,
        token=token,
    )
    if str(getattr(final_head, "sha", "")) != commit:
        raise MigrationIntegrityError(
            "source revision changed while it was being inventoried; retry from a stable head"
        )

    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sibling in sorted(getattr(pinned, "siblings", None) or [], key=lambda item: item.rfilename):
        path = _safe_repo_path(str(sibling.rfilename))
        if path in seen:
            raise MigrationIntegrityError(f"source inventory contains duplicate path: {path}")
        seen.add(path)
        size = getattr(sibling, "size", None)
        files.append(
            {
                "path": path,
                "size": int(size) if size is not None else None,
                "lfs_sha256": _lfs_sha256(sibling),
                "blob_id": (
                    str(getattr(sibling, "blob_id"))
                    if getattr(sibling, "blob_id", None) is not None
                    else None
                ),
            }
        )
    if not files:
        raise MigrationIntegrityError("source inventory is empty")

    document = _seal_document(
        {
            "schema_version": INVENTORY_SCHEMA,
            "captured_at": utc_now(),
            "source": {
                "repo_id": source_repo_id,
                "repo_type": "dataset",
                "requested_revision": source_revision,
                "resolved_commit": commit,
                "private": True,
            },
            "refs": _refs_document(refs),
            "file_count": len(files),
            "files": files,
        },
        "inventory_sha256",
    )
    _atomic_write_json(Path(output), document)
    return document


def load_inventory(path: Path | str) -> dict[str, Any]:
    document = _verify_document(
        _load_json(path),
        schema=INVENTORY_SCHEMA,
        digest_key="inventory_sha256",
        label="source inventory",
    )
    files = document.get("files")
    if not isinstance(files, list) or len(files) != document.get("file_count"):
        raise MigrationIntegrityError("source inventory file count is inconsistent")
    paths = [_safe_repo_path(str(item.get("path"))) for item in files if isinstance(item, Mapping)]
    if len(paths) != len(files) or len(set(paths)) != len(paths):
        raise MigrationIntegrityError("source inventory paths are invalid or duplicated")
    return document


def _download_remote_file(
    *, api: Any, repo_id: str, revision: str, path: str, token: str | None, temporary: Path
) -> Path:
    downloaded = api.hf_hub_download(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        filename=path,
        local_dir=str(temporary),
        force_download=True,
        token=token,
    )
    result = Path(downloaded)
    if not result.is_file():
        raise MigrationIntegrityError(f"download did not produce a file: {path}")
    return result


def create_or_resume_backup(
    *,
    api: Any,
    inventory_path: Path | str,
    backup_root: Path | str,
    token: str | None,
) -> dict[str, Any]:
    """Download every source file and persist an incrementally sealed backup."""

    inventory = load_inventory(inventory_path)
    root = Path(backup_root)
    files_root = root / "files"
    temporary_root = root / "tmp"
    manifest_path = root / "backup-manifest.json"
    _ensure_private_dir(root)
    _ensure_private_dir(files_root)
    _ensure_private_dir(temporary_root)

    completed: dict[str, dict[str, Any]] = {}
    if manifest_path.exists():
        previous = _verify_document(
            _load_json(manifest_path),
            schema=BACKUP_SCHEMA,
            digest_key="backup_manifest_sha256",
            label="backup manifest",
        )
        if previous.get("inventory_sha256") != inventory["inventory_sha256"]:
            raise MigrationIntegrityError("backup belongs to a different source inventory")
        for item in previous.get("files", []):
            if isinstance(item, Mapping):
                completed[str(item.get("path"))] = dict(item)

    source = inventory["source"]
    for ordinal, remote in enumerate(inventory["files"], start=1):
        remote_path = _safe_repo_path(str(remote["path"]))
        local_path = files_root.joinpath(*PurePosixPath(remote_path).parts)
        old = completed.get(remote_path)
        if old is not None and local_path.is_file():
            actual = sha256_file(local_path)
            if actual == old.get("sha256") and local_path.stat().st_size == old.get("size"):
                continue
            raise MigrationIntegrityError(f"existing backup file is corrupt: {remote_path}")

        with tempfile.TemporaryDirectory(prefix="download-", dir=temporary_root) as temporary:
            downloaded = _download_remote_file(
                api=api,
                repo_id=source["repo_id"],
                revision=source["resolved_commit"],
                path=remote_path,
                token=token,
                temporary=Path(temporary),
            )
            size = downloaded.stat().st_size
            expected_size = remote.get("size")
            if expected_size is not None and size != expected_size:
                raise MigrationIntegrityError(
                    f"downloaded size mismatch for {remote_path}: "
                    f"expected {expected_size}, found {size}"
                )
            digest = sha256_file(downloaded)
            expected_lfs = remote.get("lfs_sha256")
            if expected_lfs is not None and digest != expected_lfs:
                raise MigrationIntegrityError(
                    f"downloaded SHA-256 mismatch for {remote_path}: "
                    f"expected {expected_lfs}, found {digest}"
                )
            expected_blob = remote.get("blob_id")
            if (
                expected_lfs is None
                and expected_blob is not None
                and git_blob_sha1_file(downloaded) != expected_blob
            ):
                raise MigrationIntegrityError(f"downloaded Git blob mismatch for {remote_path}")
            _ensure_private_dir(local_path.parent)
            with downloaded.open("rb") as source_stream:
                _atomic_write_bytes(local_path, source_stream.read())
        completed[remote_path] = {"path": remote_path, "size": size, "sha256": digest}

        # An interrupted backup loses at most one manifest update.  Existing files
        # without a manifest entry are downloaded again rather than trusted.
        if ordinal % 16 == 0 or ordinal == len(inventory["files"]):
            partial = _seal_document(
                {
                    "schema_version": BACKUP_SCHEMA,
                    "source_captured_at": inventory["captured_at"],
                    "complete": len(completed) == len(inventory["files"]),
                    "inventory_sha256": inventory["inventory_sha256"],
                    "source": source,
                    "refs": inventory["refs"],
                    "storage": {"files_root": "files", "mode": "managed"},
                    "file_count": len(completed),
                    "files": [completed[path] for path in sorted(completed)],
                },
                "backup_manifest_sha256",
            )
            _atomic_write_json(manifest_path, partial)

    return verify_backup(inventory_path=inventory_path, backup_root=root)


def load_backup_manifest(path: Path | str) -> dict[str, Any]:
    return _verify_document(
        _load_json(path),
        schema=BACKUP_SCHEMA,
        digest_key="backup_manifest_sha256",
        label="backup manifest",
    )


def _backup_files_root(backup_root: Path, manifest: Mapping[str, Any]) -> Path:
    storage = manifest.get("storage")
    if not isinstance(storage, Mapping):
        # Backward compatibility for interrupted manifests written before the
        # adopted-snapshot mode was introduced.
        return backup_root / "files"
    relative = str(storage.get("files_root", ""))
    safe = _safe_repo_path(relative)
    root = (backup_root / PurePosixPath(safe)).resolve()
    base = backup_root.resolve()
    if root != base and base not in root.parents:
        raise MigrationIntegrityError("backup storage root escapes the backup directory")
    return root


def adopt_snapshot(
    *,
    inventory_path: Path | str,
    snapshot_root: Path | str,
    backup_root: Path | str,
) -> dict[str, Any]:
    """Seal an existing ``snapshot_download(local_dir=...)`` tree in place."""

    inventory = load_inventory(inventory_path)
    snapshot = Path(snapshot_root).resolve()
    root = Path(backup_root).resolve()
    if not snapshot.is_dir():
        raise MigrationIntegrityError(f"snapshot directory does not exist: {snapshot}")
    try:
        relative_snapshot = snapshot.relative_to(root).as_posix()
    except ValueError as error:
        raise MigrationSafetyError("adopted snapshot must be inside the backup root") from error
    _safe_repo_path(relative_snapshot)
    _ensure_private_dir(root)

    expected = {str(item["path"]): item for item in inventory["files"]}
    actual = {
        path.relative_to(snapshot).as_posix()
        for path in snapshot.rglob("*")
        if path.is_file() and ".cache" not in path.relative_to(snapshot).parts
    }
    if actual != set(expected):
        missing = sorted(set(expected) - actual)
        extra = sorted(actual - set(expected))
        raise MigrationIntegrityError(
            f"snapshot file set mismatch: missing={missing[:5]} extra={extra[:5]}"
        )

    records: list[dict[str, Any]] = []
    for path, source in sorted(expected.items()):
        local = snapshot / PurePosixPath(_safe_repo_path(path))
        size = local.stat().st_size
        if source.get("size") is not None and size != source["size"]:
            raise MigrationIntegrityError(f"snapshot size mismatch: {path}")
        digest = sha256_file(local)
        lfs = source.get("lfs_sha256")
        if lfs is not None and digest != lfs:
            raise MigrationIntegrityError(f"snapshot LFS digest mismatch: {path}")
        blob = source.get("blob_id")
        if lfs is None and blob is not None and git_blob_sha1_file(local) != blob:
            raise MigrationIntegrityError(f"snapshot Git blob digest mismatch: {path}")
        records.append({"path": path, "size": size, "sha256": digest})

    document = _seal_document(
        {
            "schema_version": BACKUP_SCHEMA,
            "source_captured_at": inventory["captured_at"],
            "complete": True,
            "inventory_sha256": inventory["inventory_sha256"],
            "source": inventory["source"],
            "refs": inventory["refs"],
            "storage": {"files_root": relative_snapshot, "mode": "adopted_snapshot"},
            "file_count": len(records),
            "files": records,
        },
        "backup_manifest_sha256",
    )
    _atomic_write_json(root / "backup-manifest.json", document)
    return verify_backup(inventory_path=inventory_path, backup_root=root)


def verify_backup(
    *, inventory_path: Path | str, backup_root: Path | str
) -> dict[str, Any]:
    inventory = load_inventory(inventory_path)
    root = Path(backup_root)
    manifest = load_backup_manifest(root / "backup-manifest.json")
    if not manifest.get("complete"):
        raise MigrationIntegrityError("backup manifest is not marked complete")
    if manifest.get("inventory_sha256") != inventory["inventory_sha256"]:
        raise MigrationIntegrityError("backup inventory digest mismatch")
    if manifest.get("refs") != inventory.get("refs"):
        raise MigrationIntegrityError("backup refs do not match the pinned inventory")

    expected = {str(item["path"]): item for item in inventory["files"]}
    backed = {str(item["path"]): item for item in manifest.get("files", [])}
    if set(backed) != set(expected):
        missing = sorted(set(expected) - set(backed))
        extra = sorted(set(backed) - set(expected))
        raise MigrationIntegrityError(
            f"backup file set mismatch: missing={missing[:5]} extra={extra[:5]}"
        )
    files_root = _backup_files_root(root, manifest)
    for path, record in sorted(backed.items()):
        local = files_root / PurePosixPath(_safe_repo_path(path))
        if not local.is_file():
            raise MigrationIntegrityError(f"backup file is missing: {path}")
        size = local.stat().st_size
        digest = sha256_file(local)
        if size != record.get("size") or digest != record.get("sha256"):
            raise MigrationIntegrityError(f"backup file digest mismatch: {path}")
        lfs = expected[path].get("lfs_sha256")
        if lfs is not None and digest != lfs:
            raise MigrationIntegrityError(f"backup file differs from source LFS digest: {path}")
        blob = expected[path].get("blob_id")
        if lfs is None and blob is not None and git_blob_sha1_file(local) != blob:
            raise MigrationIntegrityError(f"backup file differs from source Git blob: {path}")
    return manifest


def _manifest_path_for_parquet(parquet_path: str) -> str:
    match = DATA_PATH_RE.fullmatch(parquet_path)
    if match is None:
        raise MigrationIntegrityError(f"not a canonical archive Parquet path: {parquet_path}")
    relative = PurePosixPath(parquet_path).relative_to("data")
    return (
        PurePosixPath("metadata")
        / "slices"
        / relative.parent
        / f"part-{match.group('digest')}.manifest.json"
    ).as_posix()


def _slice_record(
    *, parquet: Mapping[str, Any], manifest: Mapping[str, Any], match: re.Match[str]
) -> dict[str, Any]:
    return {
        "identity": {
            "stage": match.group("stage"),
            "run": match.group("run"),
            "model": match.group("model"),
            "seed": int(match.group("seed")),
            "benchmark": match.group("benchmark"),
        },
        "parquet": dict(parquet),
        "manifest": dict(manifest),
    }


def _expected_identities(benchmarks: Sequence[str]) -> set[tuple[str, str, int, str]]:
    return {
        (stage, model, seed, benchmark)
        for stage in CANONICAL_STAGES
        for model in CANONICAL_MODELS
        for seed in CANONICAL_SEEDS
        for benchmark in benchmarks
    }


def _source_slice_set_sha256(records: Sequence[Mapping[str, Any]]) -> str:
    try:
        from scripts.trace_eval_public_export import source_slice_set_sha256
    except ModuleNotFoundError:  # Supports direct ``python scripts/...`` invocation.
        from trace_eval_public_export import source_slice_set_sha256

    return source_slice_set_sha256(records)


def _selection_export_dimensions(
    *,
    path: Path | str,
    source_run: str,
    source_models: Sequence[str],
    benchmarks: Sequence[str],
    seeds: Sequence[int],
) -> dict[str, Any]:
    """Read the private crosswalk needed to bind source files to neutral identities.

    Plan construction deliberately does not require the export plan's selection digest:
    adding the source-slice digest changes the sealed selection digest. Full validation
    requires both bindings after the two plans have been resealed.
    """

    value = _load_json(path)
    if value.get("schema_version") != "trace_eval_export_plan_v1":
        raise MigrationIntegrityError("public export plan has an unsupported schema")
    source = value.get("source")
    public = value.get("public")
    models = value.get("models")
    if not isinstance(source, Mapping) or not isinstance(public, Mapping):
        raise MigrationIntegrityError("public export plan source/public sections are invalid")
    if source.get("run_id") != source_run:
        raise MigrationIntegrityError("public export plan names a different private source run")
    if public.get("suite_id") != "trace_eval_v1":
        raise MigrationIntegrityError("public export plan has an unexpected suite id")
    if tuple(public.get("benchmarks", ())) != tuple(benchmarks):
        raise MigrationIntegrityError("public export plan benchmark order differs from the suite")
    if tuple(public.get("seeds", ())) != tuple(seeds):
        raise MigrationIntegrityError("public export plan seed coverage differs from the selection")
    run_id = public.get("run_id")
    if not isinstance(run_id, str) or not PUBLIC_ID_RE.fullmatch(run_id):
        raise MigrationIntegrityError("public export plan run id is invalid")
    if run_id == source_run:
        raise MigrationIntegrityError("public and private run ids must differ")
    if not isinstance(models, list):
        raise MigrationIntegrityError("public export plan model mapping is invalid")
    model_map: dict[str, str] = {}
    for ordinal, raw in enumerate(models):
        if not isinstance(raw, Mapping):
            raise MigrationIntegrityError(f"public export model {ordinal} is invalid")
        source_model = raw.get("source_model_id")
        public_model = raw.get("model_id")
        if not isinstance(source_model, str) or not source_model:
            raise MigrationIntegrityError(f"public export model {ordinal} source id is invalid")
        if not isinstance(public_model, str) or not PUBLIC_ID_RE.fullmatch(public_model):
            raise MigrationIntegrityError(f"public export model {ordinal} public id is invalid")
        if source_model in model_map:
            raise MigrationIntegrityError("public export plan repeats a source model")
        model_map[source_model] = public_model
    if set(model_map) != set(source_models):
        raise MigrationIntegrityError("public export plan source models differ from the selection")
    if len(set(model_map.values())) != len(model_map):
        raise MigrationIntegrityError("public export plan repeats a neutral model id")
    claimed_slice_set = source.get("slice_set_sha256")
    if claimed_slice_set is not None and (
        not isinstance(claimed_slice_set, str) or not HEX_64_RE.fullmatch(claimed_slice_set)
    ):
        raise MigrationIntegrityError("public export plan source slice-set digest is invalid")
    return {
        "run_id": run_id,
        "model_map": model_map,
        "source_selection_sha256": source.get("selection_sha256"),
        "source_slice_set_sha256": claimed_slice_set,
    }


def _selection_source_slice_records(
    source_slices: Sequence[Mapping[str, Any]], *, model_map: Mapping[str, str]
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for ordinal, source_slice in enumerate(source_slices):
        identity = source_slice.get("identity")
        if not isinstance(identity, Mapping):
            raise MigrationIntegrityError(f"source slice {ordinal} identity is invalid")
        stage = str(identity.get("stage"))
        source_model = str(identity.get("model"))
        try:
            config_name = SOURCE_STAGE_TO_CONFIG[stage]
            model_id = model_map[source_model]
        except KeyError as error:
            raise MigrationIntegrityError(
                f"source slice {ordinal} cannot be mapped to a neutral identity"
            ) from error
        record: dict[str, Any] = {
            "config_name": config_name,
            "model_id": model_id,
            "seed": identity.get("seed"),
            "benchmark_id": identity.get("benchmark"),
        }
        for kind in ("manifest", "parquet"):
            file_record = source_slice.get(kind)
            if not isinstance(file_record, Mapping):
                raise MigrationIntegrityError(f"source slice {ordinal} {kind} is invalid")
            record[kind] = {
                "sha256": file_record.get("sha256"),
                "size": file_record.get("size"),
            }
        records.append(record)
    return records


def build_selection_plan(
    *,
    inventory_path: Path | str,
    backup_root: Path | str,
    suite_path: Path | str,
    output: Path | str,
    public_export_plan: Path | str,
    paper_repo_id: str = DEFAULT_PAPER_REPO,
    internal_repo_id: str = DEFAULT_INTERNAL_REPO,
) -> dict[str, Any]:
    """Select exactly the canonical paper and supplementary All31 identities."""

    inventory = load_inventory(inventory_path)
    backup = verify_backup(inventory_path=inventory_path, backup_root=backup_root)
    suite_bytes = Path(suite_path).read_bytes()
    suite = json.loads(suite_bytes)
    canonical_suite_bytes = DEFAULT_CANONICAL_SUITE_PATH.read_bytes()
    if sha256_bytes(suite_bytes) != sha256_bytes(canonical_suite_bytes):
        raise MigrationIntegrityError(
            "selection suite differs from canonical evaluation/trace_eval/suite.v1.json"
        )
    paper_benchmarks = tuple(
        str(value.get("key")) if isinstance(value, Mapping) else str(value)
        for value in suite.get("benchmarks", [])
    )
    excluded = tuple(str(value) for value in suite.get("excluded_from_source_view", []))
    if len(paper_benchmarks) != 24 or len(set(paper_benchmarks)) != 24:
        raise MigrationIntegrityError("canonical suite must contain exactly 24 unique benchmarks")
    if excluded and set(excluded) != set(SUPPLEMENTARY_BENCHMARKS):
        raise MigrationIntegrityError(
            "canonical suite exclusions do not match the seven supplementary benchmarks"
        )
    if paper_repo_id in {inventory["source"]["repo_id"], internal_repo_id}:
        raise MigrationSafetyError("paper, internal, and source repositories must be distinct")
    if internal_repo_id == inventory["source"]["repo_id"]:
        raise MigrationSafetyError("internal and source repositories must be distinct")

    backed = {str(item["path"]): dict(item) for item in backup["files"]}
    paper_expected = _expected_identities(paper_benchmarks)
    internal_expected = _expected_identities(SUPPLEMENTARY_BENCHMARKS)
    found: dict[tuple[str, str, int, str], list[dict[str, Any]]] = {}
    for path, parquet in sorted(backed.items()):
        match = DATA_PATH_RE.fullmatch(path)
        if match is None or match.group("run") != CANONICAL_RUN:
            continue
        identity = (
            match.group("stage"),
            match.group("model"),
            int(match.group("seed")),
            match.group("benchmark"),
        )
        if identity not in paper_expected and identity not in internal_expected:
            continue
        manifest_path = _manifest_path_for_parquet(path)
        manifest = backed.get(manifest_path)
        if manifest is None:
            raise MigrationIntegrityError(f"source slice is missing its manifest: {path}")
        found.setdefault(identity, []).append(
            _slice_record(parquet=parquet, manifest=manifest, match=match)
        )

    missing = sorted((paper_expected | internal_expected) - set(found))
    duplicates = sorted(identity for identity, values in found.items() if len(values) != 1)
    if missing or duplicates:
        raise MigrationIntegrityError(
            f"canonical All31 coverage is invalid: missing={missing[:5]} "
            f"duplicates={duplicates[:5]}"
        )
    paper = [found[identity][0] for identity in sorted(paper_expected)]
    internal = [found[identity][0] for identity in sorted(internal_expected)]
    if len(paper) != EXPECTED_PAPER_STAGE_SLICES:
        raise MigrationIntegrityError(f"paper selection has {len(paper)} slices, expected 648")
    if len(internal) != EXPECTED_INTERNAL_STAGE_SLICES:
        raise MigrationIntegrityError(
            f"internal selection has {len(internal)} slices, expected 189"
        )
    paper_paths = {
        item[kind]["path"] for item in paper for kind in ("parquet", "manifest")
    }
    internal_paths = {
        item[kind]["path"] for item in internal for kind in ("parquet", "manifest")
    }
    if paper_paths & internal_paths:
        raise MigrationIntegrityError("paper and internal source selections overlap")

    export_dimensions = _selection_export_dimensions(
        path=public_export_plan,
        source_run=CANONICAL_RUN,
        source_models=CANONICAL_MODELS,
        benchmarks=paper_benchmarks,
        seeds=CANONICAL_SEEDS,
    )
    source_slice_set_digest = _source_slice_set_sha256(
        _selection_source_slice_records(
            paper, model_map=export_dimensions["model_map"]
        )
    )
    claimed_slice_set = export_dimensions["source_slice_set_sha256"]
    if claimed_slice_set is not None and claimed_slice_set != source_slice_set_digest:
        raise MigrationIntegrityError(
            "public export plan source slice-set digest differs from the selected source files"
        )

    document = _seal_document(
        {
            "schema_version": SELECTION_SCHEMA,
            "source_captured_at": inventory["captured_at"],
            "inventory_sha256": inventory["inventory_sha256"],
            "backup_manifest_sha256": backup["backup_manifest_sha256"],
            "source": inventory["source"],
            "source_run": CANONICAL_RUN,
            "suite": {
                "path": _portable_suite_path(suite_path),
                "sha256": sha256_bytes(suite_bytes),
                "schema_version": suite.get("schema_version"),
            },
            "models": list(CANONICAL_MODELS),
            "seeds": list(CANONICAL_SEEDS),
            "stages": list(CANONICAL_STAGES),
            "paper": {
                "repo_id": paper_repo_id,
                "neutral_export_required": True,
                "benchmarks": list(paper_benchmarks),
                "stage_slice_count": len(paper),
                "source_slice_set_sha256": source_slice_set_digest,
                "source_slices": paper,
            },
            "internal": {
                "repo_id": internal_repo_id,
                "lossless": True,
                "benchmarks": list(SUPPLEMENTARY_BENCHMARKS),
                "stage_slice_count": len(internal),
                "source_slices": internal,
            },
        },
        "selection_sha256",
    )
    _atomic_write_json(Path(output), document)
    return document


def load_selection_plan(path: Path | str) -> dict[str, Any]:
    document = _verify_document(
        _load_json(path),
        schema=SELECTION_SCHEMA,
        digest_key="selection_sha256",
        label="selection plan",
    )
    paper = document.get("paper", {})
    internal = document.get("internal", {})
    canonical_suite_bytes = DEFAULT_CANONICAL_SUITE_PATH.read_bytes()
    canonical_suite = json.loads(canonical_suite_bytes)
    expected_benchmarks = [
        str(item.get("key")) if isinstance(item, Mapping) else str(item)
        for item in canonical_suite.get("benchmarks", [])
    ]
    suite_binding = document.get("suite")
    if not isinstance(suite_binding, Mapping) or suite_binding.get(
        "sha256"
    ) != sha256_bytes(canonical_suite_bytes):
        raise MigrationIntegrityError("selection plan is not bound to the canonical suite")
    if suite_binding.get("schema_version") != canonical_suite.get("schema_version"):
        raise MigrationIntegrityError("selection plan canonical suite schema differs")
    if paper.get("benchmarks") != expected_benchmarks:
        raise MigrationIntegrityError("selection plan canonical benchmark order differs")
    if internal.get("benchmarks") != list(SUPPLEMENTARY_BENCHMARKS):
        raise MigrationIntegrityError("selection plan supplementary benchmark order differs")
    if paper.get("stage_slice_count") != EXPECTED_PAPER_STAGE_SLICES:
        raise MigrationIntegrityError("selection plan does not contain 648 paper slices")
    if internal.get("stage_slice_count") != EXPECTED_INTERNAL_STAGE_SLICES:
        raise MigrationIntegrityError("selection plan does not contain 189 internal slices")
    source_slice_set_digest = paper.get("source_slice_set_sha256")
    if not isinstance(source_slice_set_digest, str) or not HEX_64_RE.fullmatch(
        source_slice_set_digest
    ):
        raise MigrationIntegrityError("selection plan source slice-set digest is invalid")
    return document


def selected_internal_files(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    for slice_record in plan["internal"]["source_slices"]:
        for kind in ("parquet", "manifest"):
            record = dict(slice_record[kind])
            path = _safe_repo_path(str(record["path"]))
            if path in seen:
                raise MigrationIntegrityError(f"duplicate internal path: {path}")
            seen.add(path)
            files.append(record)
    expected = EXPECTED_INTERNAL_STAGE_SLICES * 2
    if len(files) != expected:
        raise MigrationIntegrityError(
            f"internal file selection has {len(files)} files, expected {expected}"
        )
    return sorted(files, key=lambda item: item["path"])


def assert_neutral_paper_repo_id(
    repo_id: str, *, forbidden_repo_ids: Iterable[str] = ()
) -> None:
    parts = repo_id.split("/")
    if len(parts) != 2 or not all(parts):
        raise MigrationSafetyError(f"invalid paper repository id: {repo_id!r}")
    name = parts[1].lower()
    if not NEUTRAL_REPO_NAME_RE.fullmatch(name):
        raise MigrationSafetyError(f"paper repository name is not neutral: {repo_id}")
    tokens = set(filter(None, re.split(r"[^a-z0-9]+", name)))
    if tokens & NON_NEUTRAL_REPO_TOKENS or any(
        token in name for token in ("final24", "final25", "final31")
    ):
        raise MigrationSafetyError(f"paper repository name exposes internal suite state: {repo_id}")
    if repo_id in set(forbidden_repo_ids):
        raise MigrationSafetyError(
            "paper repository cannot be the raw source or internal repository"
        )


def assert_neutral_public_repo_id(repo_id: str, *, plan: Mapping[str, Any]) -> None:
    assert_neutral_paper_repo_id(
        repo_id,
        forbidden_repo_ids=(plan["source"]["repo_id"], plan["internal"]["repo_id"]),
    )


@dataclass(frozen=True)
class UploadFile:
    path: str
    local_path: Path
    sha256: str
    size: int


def _repo_info_or_none(
    api: Any, *, repo_id: str, revision: str, token: str | None, files_metadata: bool
) -> Any | None:
    try:
        return api.repo_info(
            repo_id=repo_id,
            repo_type="dataset",
            revision=revision,
            files_metadata=files_metadata,
            token=token,
        )
    except RepositoryNotFoundError:
        return None


def ensure_private_destination(
    api: Any, *, repo_id: str, revision: str, token: str | None
) -> Any:
    info = _repo_info_or_none(
        api,
        repo_id=repo_id,
        revision=revision,
        token=token,
        files_metadata=False,
    )
    if info is None:
        api.create_repo(
            repo_id=repo_id,
            repo_type="dataset",
            private=True,
            exist_ok=False,
            token=token,
        )
        info = _repo_info_or_none(
            api,
            repo_id=repo_id,
            revision=revision,
            token=token,
            files_metadata=False,
        )
    if info is None or not bool(getattr(info, "private", False)):
        raise MigrationSafetyError(f"destination repository is not private: {repo_id}")
    return info


def _remote_file_digest(
    *,
    api: Any,
    repo_id: str,
    revision: str,
    path: str,
    token: str | None,
    temporary_root: Path,
) -> str:
    with tempfile.TemporaryDirectory(prefix="verify-", dir=temporary_root) as temporary:
        downloaded = _download_remote_file(
            api=api,
            repo_id=repo_id,
            revision=revision,
            path=path,
            token=token,
            temporary=Path(temporary),
        )
        return sha256_file(downloaded)


def _remote_paths(info: Any) -> set[str]:
    return {
        _safe_repo_path(str(item.rfilename))
        for item in (getattr(info, "siblings", None) or [])
    }


def _remote_lfs_digests(info: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in getattr(info, "siblings", None) or []:
        digest = _lfs_sha256(item)
        if digest is not None:
            result[_safe_repo_path(str(item.rfilename))] = digest
    return result


def upload_private_file_set(
    *,
    api: Any,
    repo_id: str,
    revision: str,
    files: Sequence[UploadFile],
    token: str | None,
    state_root: Path | str,
    commit_message: str,
    forbidden_remote_prefixes: Sequence[str] = (),
    allowed_extra_paths: Iterable[str] = (".gitattributes", "README.md"),
    batch_size: int = 48,
) -> dict[str, Any]:
    """Upload an exact file set to a private repo, resuming by content digest."""

    if batch_size < 1:
        raise ValueError("batch_size must be at least one")
    desired = {item.path: item for item in files}
    if len(desired) != len(files):
        raise MigrationIntegrityError("upload file set contains duplicate destination paths")
    for item in files:
        _safe_repo_path(item.path)
        if not item.local_path.is_file():
            raise MigrationIntegrityError(f"upload source is missing: {item.local_path}")
        if (
            item.local_path.stat().st_size != item.size
            or sha256_file(item.local_path) != item.sha256
        ):
            raise MigrationIntegrityError(f"upload source digest mismatch: {item.local_path}")

    ensure_private_destination(api, repo_id=repo_id, revision=revision, token=token)
    temporary_root = Path(state_root) / "remote-verify"
    _ensure_private_dir(temporary_root)
    info = api.repo_info(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        files_metadata=True,
        token=token,
    )
    remote = _remote_paths(info)
    remote_lfs = _remote_lfs_digests(info)
    allowed_extra = {_safe_repo_path(path) for path in allowed_extra_paths}
    for path in remote:
        if any(path.startswith(prefix) for prefix in forbidden_remote_prefixes):
            raise MigrationSafetyError(f"forbidden raw path exists in {repo_id}: {path}")
        if path not in desired and path not in allowed_extra:
            raise MigrationSafetyError(f"unexpected pre-existing file in {repo_id}: {path}")

    missing: list[UploadFile] = []
    verified = 0
    for path, item in sorted(desired.items()):
        if path not in remote:
            missing.append(item)
            continue
        actual = remote_lfs.get(path)
        if actual is None:
            actual = _remote_file_digest(
                api=api,
                repo_id=repo_id,
                revision=revision,
                path=path,
                token=token,
                temporary_root=temporary_root,
            )
        if actual != item.sha256:
            raise MigrationIntegrityError(
                f"immutable remote path differs from migration source: {repo_id}/{path}"
            )
        verified += 1

    uploaded = 0
    for offset in range(0, len(missing), batch_size):
        batch = missing[offset : offset + batch_size]
        api.create_commit(
            repo_id=repo_id,
            repo_type="dataset",
            revision=revision,
            operations=[
                CommitOperationAdd(path_in_repo=item.path, path_or_fileobj=str(item.local_path))
                for item in batch
            ],
            commit_message=f"{commit_message} ({offset + 1}-{offset + len(batch)})",
            num_threads=min(8, len(batch)),
            token=token,
        )
        batch_info = api.repo_info(
            repo_id=repo_id,
            repo_type="dataset",
            revision=revision,
            files_metadata=True,
            token=token,
        )
        batch_lfs = _remote_lfs_digests(batch_info)
        for item in batch:
            actual = batch_lfs.get(item.path)
            if actual is None:
                actual = _remote_file_digest(
                    api=api,
                    repo_id=repo_id,
                    revision=revision,
                    path=item.path,
                    token=token,
                    temporary_root=temporary_root,
                )
            if actual != item.sha256:
                raise MigrationIntegrityError(
                    f"post-upload digest mismatch: {repo_id}/{item.path}"
                )
        uploaded += len(batch)

    final = api.repo_info(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        files_metadata=True,
        token=token,
    )
    if not bool(getattr(final, "private", False)):
        raise MigrationSafetyError(f"destination became public during upload: {repo_id}")
    final_paths = _remote_paths(final)
    for path in final_paths:
        if any(path.startswith(prefix) for prefix in forbidden_remote_prefixes):
            raise MigrationSafetyError(f"forbidden raw path exists in {repo_id}: {path}")
        if path not in desired and path not in allowed_extra:
            raise MigrationSafetyError(f"unexpected remote file after upload: {repo_id}/{path}")
    if not set(desired).issubset(final_paths):
        raise MigrationIntegrityError(f"destination is missing uploaded files: {repo_id}")
    return {
        "repo_id": repo_id,
        "private": True,
        "revision": str(getattr(final, "sha", "")),
        "files": len(desired),
        "uploaded": uploaded,
        "already_verified": verified,
    }


def verify_remote_file_set(
    *,
    api: Any,
    repo_id: str,
    revision: str,
    files: Sequence[UploadFile],
    token: str | None,
    state_root: Path | str,
    require_private: bool,
    forbidden_remote_prefixes: Sequence[str] = (),
    allowed_extra_paths: Iterable[str] = (".gitattributes",),
) -> dict[str, Any]:
    """Read back an exact remote file set and verify every SHA-256 digest."""

    info = api.repo_info(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        files_metadata=True,
        token=token,
    )
    private = bool(getattr(info, "private", False))
    if require_private and not private:
        raise MigrationSafetyError(f"repository must remain private during migration: {repo_id}")
    desired = {item.path: item for item in files}
    if len(desired) != len(files):
        raise MigrationIntegrityError("remote verification file set contains duplicates")
    allowed_extra = {_safe_repo_path(path) for path in allowed_extra_paths}
    remote = _remote_paths(info)
    remote_lfs = _remote_lfs_digests(info)
    for path in remote:
        if any(path.startswith(prefix) for prefix in forbidden_remote_prefixes):
            raise MigrationSafetyError(f"forbidden raw path exists in {repo_id}: {path}")
        if path not in desired and path not in allowed_extra:
            raise MigrationSafetyError(f"unexpected remote file in {repo_id}: {path}")
    if not set(desired).issubset(remote):
        missing = sorted(set(desired) - remote)
        raise MigrationIntegrityError(f"remote repository is missing files: {missing[:5]}")

    temporary_root = Path(state_root) / "remote-verify"
    _ensure_private_dir(temporary_root)
    for path, item in sorted(desired.items()):
        actual = remote_lfs.get(path)
        if actual is None:
            actual = _remote_file_digest(
                api=api,
                repo_id=repo_id,
                revision=revision,
                path=path,
                token=token,
                temporary_root=temporary_root,
            )
        if actual != item.sha256:
            raise MigrationIntegrityError(f"remote digest mismatch: {repo_id}/{path}")
    return {
        "repo_id": repo_id,
        "private": private,
        "revision": str(getattr(info, "sha", "")),
        "file_count": len(desired),
        "content_set_sha256": sha256_bytes(
            canonical_json(
                [{"path": item.path, "sha256": item.sha256, "size": item.size} for item in files]
            ).encode("utf-8")
        ),
    }


def internal_upload_files(
    *,
    plan: Mapping[str, Any],
    backup_root: Path | str,
    state_root: Path | str,
    public_export_plan: Path | str | None = None,
) -> list[UploadFile]:
    backup = load_backup_manifest(Path(backup_root) / "backup-manifest.json")
    root = _backup_files_root(Path(backup_root), backup)
    result: list[UploadFile] = []
    for record in selected_internal_files(plan):
        path = _safe_repo_path(str(record["path"]))
        result.append(
            UploadFile(
                path=path,
                local_path=root / PurePosixPath(path),
                sha256=str(record["sha256"]),
                size=int(record["size"]),
            )
        )
    control_root = Path(state_root) / "internal-control"
    _ensure_private_dir(control_root)
    selected = selected_internal_files(plan)
    metadata = _seal_document(
        {
            "schema_version": "trace-eval-internal-archive-migration-v1",
            "private": True,
            "lossless": True,
            "source": {
                **plan["source"],
                "run": plan["source_run"],
                "original_paths_preserved": True,
            },
            "selection_sha256": plan["selection_sha256"],
            "backup_manifest_sha256": plan["backup_manifest_sha256"],
            "suite": plan["suite"],
            "paper_relationship": {
                "repo_id": plan["paper"]["repo_id"],
                "benchmarks": plan["paper"]["benchmarks"],
                "stage_slice_count": plan["paper"]["stage_slice_count"],
                "raw_paper_slices_are_local_backup_only": True,
            },
            "internal": {
                "repo_id": plan["internal"]["repo_id"],
                "benchmarks": plan["internal"]["benchmarks"],
                "models": plan["models"],
                "seeds": plan["seeds"],
                "stages": plan["stages"],
                "stage_slice_count": plan["internal"]["stage_slice_count"],
                "files": selected,
                "source_slices": plan["internal"]["source_slices"],
            },
        },
        "migration_metadata_sha256",
    )
    metadata_path = control_root / "archive-migration.json"
    _atomic_write_json(metadata_path, metadata)
    readme_path = control_root / "README.md"
    _atomic_write_bytes(
        readme_path,
        (
            "---\nlicense: other\npretty_name: TRACE Internal Evaluation Runs\n---\n\n"
            "Private supplementary evaluation archive. It preserves the seven benchmarks "
            "outside the public TRACE evaluation suite, including rich response, extraction, "
            "score, and provenance fields. Do not make this repository public.\n"
        ).encode("utf-8"),
    )
    for destination, local in (
        ("README.md", readme_path),
        ("metadata/archive-migration.json", metadata_path),
    ):
        result.append(
            UploadFile(
                path=destination,
                local_path=local,
                sha256=sha256_file(local),
                size=local.stat().st_size,
            )
        )

    if public_export_plan is not None:
        export_plan = Path(public_export_plan)
        if not export_plan.is_file():
            raise MigrationIntegrityError(f"private public-export plan is missing: {export_plan}")
        validate_private_public_export_plan(path=export_plan, plan=plan)
        # This mapping is deliberately never part of the public export allowlist.
        result.append(
            UploadFile(
                path="metadata/public-export-plan.json",
                local_path=export_plan,
                sha256=sha256_file(export_plan),
                size=export_plan.stat().st_size,
            )
        )
    return sorted(result, key=lambda item: item.path)


def validate_private_public_export_plan(
    *, path: Path | str, plan: Mapping[str, Any]
) -> dict[str, Any]:
    try:
        from scripts.trace_eval_public_export import ExportPlan
    except ModuleNotFoundError:  # Supports direct ``python scripts/...`` invocation.
        from trace_eval_public_export import ExportPlan

    export_path = Path(path)
    value = _load_json(export_path)
    export_plan = ExportPlan.from_mapping(value)
    if export_plan.source_selection_sha256 != plan["selection_sha256"]:
        raise MigrationIntegrityError("public export plan is bound to another source selection")
    if export_plan.source_run_id != plan["source_run"]:
        raise MigrationIntegrityError("public export plan names a different private source run")
    if set(export_plan.source_model_map) != set(plan["models"]):
        raise MigrationIntegrityError("public export plan source models differ from the selection")
    if tuple(export_plan.benchmarks) != tuple(plan["paper"]["benchmarks"]):
        raise MigrationIntegrityError("public export plan benchmark order differs from the suite")
    if tuple(export_plan.seeds) != tuple(plan["seeds"]):
        raise MigrationIntegrityError("public export plan seed coverage differs from the selection")
    if export_plan.suite_id != "trace_eval_v1":
        raise MigrationIntegrityError("public export plan has an unexpected suite id")
    expected_slice_set = _source_slice_set_sha256(
        _selection_source_slice_records(
            plan["paper"]["source_slices"],
            model_map={
                source_model: mapping.model_id
                for source_model, mapping in export_plan.source_model_map.items()
            },
        )
    )
    if expected_slice_set != plan["paper"].get("source_slice_set_sha256"):
        raise MigrationIntegrityError(
            "selection plan source slice-set digest does not match its selected files"
        )
    if export_plan.source_slice_set_sha256 != expected_slice_set:
        raise MigrationIntegrityError(
            "public export plan is bound to another source slice set"
        )
    return {
        "internal_path": "metadata/public-export-plan.json",
        "sha256": sha256_file(export_path),
        "schema_version": value.get("schema_version"),
        "public_run_id": export_plan.run_id,
        "public_model_ids": [model.model_id for model in export_plan.models],
        "source_slice_set_sha256": expected_slice_set,
    }


def _load_private_export_plan(path: Path | str) -> Any:
    try:
        from scripts.trace_eval_public_export import ExportPlan
    except ModuleNotFoundError:  # Supports direct ``python scripts/...`` invocation.
        from trace_eval_public_export import ExportPlan

    return ExportPlan.from_mapping(_load_json(path))


def _observed_public_source_slice_set(
    *, root: Path, artifacts: Sequence[Mapping[str, Any]]
) -> str:
    """Recompute source bindings directly from each verified public part manifest."""

    records: list[dict[str, Any]] = []
    for ordinal, artifact in enumerate(artifacts):
        manifest_path = _safe_repo_path(str(artifact.get("manifest_path")))
        part = _load_json(root / PurePosixPath(manifest_path))
        provenance = part.get("provenance")
        if not isinstance(provenance, Mapping):
            raise MigrationIntegrityError(
                f"public artifact {ordinal} part provenance is invalid"
            )
        records.append(
            {
                "config_name": artifact.get("config_name"),
                "model_id": artifact.get("model_id"),
                "seed": artifact.get("seed"),
                "benchmark_id": artifact.get("benchmark_id"),
                "manifest": {
                    "sha256": provenance.get("source_archive_manifest_sha256"),
                    "size": provenance.get("source_archive_manifest_size"),
                },
                "parquet": {
                    "sha256": provenance.get("source_archive_part_sha256"),
                    "size": provenance.get("source_archive_part_size"),
                },
            }
        )
    try:
        return _source_slice_set_sha256(records)
    except Exception as error:
        raise MigrationIntegrityError(
            f"public artifact source provenance is invalid: {error}"
        ) from error


def _validate_public_metadata_against_export_plan(
    *, root: Path, manifest: Mapping[str, Any], export_plan: Any
) -> None:
    suite = _load_json(root / "metadata" / "suites" / f"{export_plan.suite_id}.json")
    if suite.get("benchmark_ids") != list(export_plan.benchmarks):
        raise MigrationIntegrityError(
            "public suite benchmark ordering differs from the private export plan"
        )
    expected_categories = [
        {
            "category_id": re.sub(r"[^a-z0-9._-]+", "-", name.lower()).strip("-._"),
            "category_name": name,
            "benchmark_ids": list(members),
        }
        for name, members in export_plan.categories
    ]
    if suite.get("categories") != expected_categories:
        raise MigrationIntegrityError(
            "public suite categories differ from the private export plan"
        )

    run = _load_json(root / "metadata" / "runs" / f"{export_plan.run_id}.json")
    if run.get("run_id") != export_plan.run_id or run.get("suite_id") != export_plan.suite_id:
        raise MigrationIntegrityError("public run metadata identity differs from the export plan")
    if run.get("model_ids") != [model.model_id for model in export_plan.models]:
        raise MigrationIntegrityError(
            "public run model ordering differs from the private export plan"
        )
    if run.get("seeds") != list(export_plan.seeds):
        raise MigrationIntegrityError(
            "public run seed ordering differs from the private export plan"
        )
    expected_judge = {
        "model_id": export_plan.judge.model_id,
        "model_revision": export_plan.judge.model_revision,
    }
    if run.get("judge_model") != expected_judge:
        raise MigrationIntegrityError(
            "public run judge metadata differs from the private export plan"
        )
    if run.get("source_selection_sha256") != export_plan.source_selection_sha256:
        raise MigrationIntegrityError("public run source selection digest is inconsistent")
    if run.get("source_slice_set_sha256") != export_plan.source_slice_set_sha256:
        raise MigrationIntegrityError("public run source slice-set digest is inconsistent")

    for model in export_plan.models:
        metadata = _load_json(root / "metadata" / "models" / f"{model.model_id}.json")
        expected = {
            "model_id": model.model_id,
            "model_revision": model.model_revision,
            "display_name": model.display_name,
            "repository_id": model.repository_id,
            "repository_revision": model.repository_revision,
        }
        observed = {name: metadata.get(name) for name in expected}
        if observed != expected:
            raise MigrationIntegrityError(
                f"public model metadata differs from the private export plan: {model.model_id}"
            )

    allowlisted = {
        str(item.get("path"))
        for item in manifest.get("metadata_files", [])
        if isinstance(item, Mapping)
    }
    required = {
        f"metadata/suites/{export_plan.suite_id}.json",
        f"metadata/runs/{export_plan.run_id}.json",
        *(f"metadata/models/{model.model_id}.json" for model in export_plan.models),
    }
    if not required.issubset(allowlisted):
        raise MigrationIntegrityError("public manifest omits required attribution metadata")


def load_verified_public_run(
    *,
    root: Path | str,
    public_export_plan: Path | str,
    suite_path: Path | str = DEFAULT_CANONICAL_SUITE_PATH,
) -> tuple[Any, list[UploadFile], Any]:
    """Validate one trace_eval_v1 bundle against its private exporter plan."""

    try:
        from scripts.trace_eval_public_export import load_and_verify_public_export
    except ModuleNotFoundError:  # Supports direct ``python scripts/...`` invocation.
        from trace_eval_public_export import load_and_verify_public_export

    export_plan = _load_private_export_plan(public_export_plan)
    suite = _load_json(suite_path)
    suite_benchmarks = tuple(
        str(item.get("key")) if isinstance(item, Mapping) else str(item)
        for item in suite.get("benchmarks", [])
    )
    categories_raw = suite.get("categories")
    if len(suite_benchmarks) != 24 or len(set(suite_benchmarks)) != 24:
        raise MigrationIntegrityError("canonical trace_eval_v1 suite must contain 24 benchmarks")
    if not isinstance(categories_raw, Mapping):
        raise MigrationIntegrityError("canonical trace_eval_v1 categories are invalid")
    suite_categories = tuple(
        (str(name), tuple(str(member) for member in members))
        for name, members in categories_raw.items()
        if isinstance(members, list)
    )
    if export_plan.benchmarks != suite_benchmarks:
        raise MigrationIntegrityError(
            "public export plan benchmark order differs from canonical trace_eval_v1"
        )
    if export_plan.categories != suite_categories:
        raise MigrationIntegrityError(
            "public export plan categories differ from canonical trace_eval_v1"
        )
    root_path = Path(root)
    verified = load_and_verify_public_export(
        root_path,
        expected_artifacts=len(export_plan.expected_identities),
        dynamic_markers=(export_plan.source_run_id,),
    )
    manifest = verified.manifest
    _validate_public_metadata_against_export_plan(
        root=root_path, manifest=manifest, export_plan=export_plan
    )
    if manifest.get("neutralized") is not True:
        raise MigrationSafetyError("paper export is not marked neutralized")
    if manifest.get("suite_id") != "trace_eval_v1" or export_plan.suite_id != "trace_eval_v1":
        raise MigrationIntegrityError("paper export has an unexpected suite id")
    if manifest.get("run_ids") != [export_plan.run_id]:
        raise MigrationIntegrityError("paper export run differs from its private export plan")
    if manifest.get("source_selection_sha256") != export_plan.source_selection_sha256:
        raise MigrationIntegrityError(
            "paper export selection digest differs from its private export plan"
        )
    if manifest.get("source_slice_set_sha256") != export_plan.source_slice_set_sha256:
        raise MigrationIntegrityError(
            "paper export source slice-set digest differs from its private export plan"
        )
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise MigrationIntegrityError("paper export artifact list is invalid")
    identities = {
        (
            str(item.get("config_name")),
            str(item.get("model_id")),
            int(item.get("seed")),
            str(item.get("benchmark_id")),
        )
        for item in artifacts
        if isinstance(item, Mapping)
    }
    if len(artifacts) != len(identities) or identities != export_plan.expected_identities:
        raise MigrationIntegrityError(
            "paper export stage identities differ from its private export plan"
        )
    if any(str(item.get("run_id")) != export_plan.run_id for item in artifacts):
        raise MigrationIntegrityError("paper export artifacts name an unexpected run")
    observed_slice_set = _observed_public_source_slice_set(
        root=root_path, artifacts=artifacts
    )
    if observed_slice_set != export_plan.source_slice_set_sha256:
        raise MigrationIntegrityError(
            "public part provenance differs from the private export plan"
        )
    files = [
        UploadFile(
            path=_safe_repo_path(str(item.path)),
            local_path=root_path / PurePosixPath(_safe_repo_path(str(item.path))),
            sha256=str(item.sha256),
            size=int(item.size),
        )
        for item in verified.files
    ]
    return verified, files, export_plan


def load_verified_public_export(
    *,
    root: Path | str,
    plan: Mapping[str, Any],
    public_export_plan: Path | str,
) -> tuple[Any, list[UploadFile]]:
    """Validate the neutral export and bind it to the pinned source selection."""

    try:
        from scripts.trace_eval_public_export import load_and_verify_public_export
    except ModuleNotFoundError:  # Supports direct ``python scripts/...`` invocation.
        from trace_eval_public_export import load_and_verify_public_export

    validate_private_public_export_plan(path=public_export_plan, plan=plan)
    export_plan = _load_private_export_plan(public_export_plan)
    root_path = Path(root)
    verified = load_and_verify_public_export(
        root_path,
        expected_artifacts=EXPECTED_PAPER_STAGE_SLICES,
        dynamic_markers=(export_plan.source_run_id,),
    )
    manifest = verified.manifest
    _validate_public_metadata_against_export_plan(
        root=root_path, manifest=manifest, export_plan=export_plan
    )
    if manifest.get("neutralized") is not True:
        raise MigrationSafetyError("paper export is not marked neutralized")
    if manifest.get("source_selection_sha256") != plan["selection_sha256"]:
        raise MigrationIntegrityError("paper export is not bound to this source selection")
    if manifest.get("suite_id") != "trace_eval_v1":
        raise MigrationIntegrityError("paper export has an unexpected suite id")
    if manifest.get("source_slice_set_sha256") != plan["paper"].get(
        "source_slice_set_sha256"
    ):
        raise MigrationIntegrityError("paper export is not bound to this source slice set")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != EXPECTED_PAPER_STAGE_SLICES:
        raise MigrationIntegrityError("paper export must declare exactly 648 stage artifacts")
    expected_benchmarks = set(plan["paper"]["benchmarks"])
    actual_benchmarks = {str(item.get("benchmark_id")) for item in artifacts}
    if actual_benchmarks != expected_benchmarks:
        raise MigrationIntegrityError(
            "paper export benchmark coverage differs from the selection plan"
        )
    if {int(item.get("seed")) for item in artifacts} != set(CANONICAL_SEEDS):
        raise MigrationIntegrityError("paper export seed coverage is incomplete")
    if {str(item.get("config_name")) for item in artifacts} != {
        "responses",
        "extractions",
        "scores",
    }:
        raise MigrationIntegrityError(
            "paper export must contain responses, extractions, and scores"
        )
    public_models = {str(item.get("model_id")) for item in artifacts}
    expected_public_models = {item.model_id for item in export_plan.models}
    if public_models != expected_public_models:
        raise MigrationIntegrityError("paper export model identities differ from the crosswalk")
    identities = {
        (
            str(item.get("config_name")),
            str(item.get("run_id")),
            str(item.get("model_id")),
            int(item.get("seed")),
            str(item.get("benchmark_id")),
        )
        for item in artifacts
    }
    if len(identities) != EXPECTED_PAPER_STAGE_SLICES:
        raise MigrationIntegrityError("paper export contains duplicate stage identities")
    expected_identities = {
        (config, export_plan.run_id, model.model_id, seed, benchmark)
        for config in ("responses", "extractions", "scores")
        for model in export_plan.models
        for seed in export_plan.seeds
        for benchmark in export_plan.benchmarks
    }
    if identities != expected_identities:
        raise MigrationIntegrityError(
            "paper export stage identities differ from the private export plan"
        )
    observed_slice_set = _observed_public_source_slice_set(
        root=root_path, artifacts=artifacts
    )
    expected_slice_set = str(plan["paper"]["source_slice_set_sha256"])
    if observed_slice_set != expected_slice_set:
        raise MigrationIntegrityError(
            "public part provenance differs from the selected source slice set"
        )
    if observed_slice_set != export_plan.source_slice_set_sha256:
        raise MigrationIntegrityError(
            "public part provenance differs from the private export plan"
        )

    raw_digests = {
        str(slice_record[kind]["sha256"])
        for slice_record in plan["paper"]["source_slices"]
        for kind in ("parquet", "manifest")
    }
    files: list[UploadFile] = []
    for item in verified.files:
        path = _safe_repo_path(str(item.path))
        digest = str(item.sha256)
        if digest in raw_digests:
            raise MigrationSafetyError(
                f"paper export contains a byte-for-byte raw source artifact: {path}"
            )
        files.append(
            UploadFile(
                path=path,
                local_path=root_path / PurePosixPath(path),
                sha256=digest,
                size=int(item.size),
            )
        )
    if not any(item.path == "metadata/manifest.json" for item in files):
        raise MigrationIntegrityError("paper export allowlist omits metadata/manifest.json")
    if not any(item.path == "README.md" for item in files):
        raise MigrationIntegrityError("paper export allowlist omits README.md")
    return verified, files


RAW_ARCHIVE_PREFIXES = (
    "data/generation/",
    "data/extraction/",
    "data/score/",
    "metadata/slices/",
)

PAPER_ROOT_README = """---
license: other
pretty_name: TRACE Evaluation Runs
configs:
- config_name: responses
  data_files:
  - split: test
    path: runs/*/data/responses/**/*.parquet
- config_name: extractions
  data_files:
  - split: test
    path: runs/*/data/extractions/**/*.parquet
- config_name: scores
  data_files:
  - split: test
    path: runs/*/data/scores/**/*.parquet
---

# TRACE Evaluation Runs

Neutral evaluation artifacts are stored as immutable, provenance-bound run bundles.
Each run contains model responses, normalized extractions, scores, and metadata.
"""

_RAW_ARCHIVE_COMPONENTS = (
    ("data", "generation"),
    ("data", "extraction"),
    ("data", "score"),
    ("metadata", "slices"),
)


def _contains_raw_archive_path(path: str) -> bool:
    parts = PurePosixPath(_safe_repo_path(path)).parts
    return any(
        tuple(parts[offset : offset + len(pattern)]) == pattern
        for pattern in _RAW_ARCHIVE_COMPONENTS
        for offset in range(len(parts) - len(pattern) + 1)
    )


def _paper_run_files(
    *,
    verified: Any,
    files: Sequence[UploadFile],
    state_root: Path | str,
) -> tuple[str, list[UploadFile]]:
    run_ids = verified.manifest.get("run_ids")
    if not isinstance(run_ids, list) or len(run_ids) != 1:
        raise MigrationIntegrityError("paper export must contain exactly one run")
    run_id = run_ids[0]
    if not isinstance(run_id, str) or not PUBLIC_ID_RE.fullmatch(run_id):
        raise MigrationIntegrityError("paper export run id is invalid")
    root = Path(state_root) / "paper-control"
    readme_path = root / "README.md"
    _atomic_write_bytes(readme_path, PAPER_ROOT_README.encode("utf-8"))
    result = [
        UploadFile(
            path="README.md",
            local_path=readme_path,
            sha256=sha256_file(readme_path),
            size=readme_path.stat().st_size,
        )
    ]
    saw_bundle_readme = False
    for item in files:
        source_path = _safe_repo_path(item.path)
        if source_path == "README.md":
            saw_bundle_readme = True
            continue
        if _contains_raw_archive_path(source_path):
            raise MigrationSafetyError(
                f"paper export contains a forbidden raw archive path: {source_path}"
            )
        destination = f"runs/{run_id}/{source_path}"
        result.append(
            UploadFile(
                path=destination,
                local_path=item.local_path,
                sha256=item.sha256,
                size=item.size,
            )
        )
    if not saw_bundle_readme:
        raise MigrationIntegrityError("paper export allowlist omits README.md")
    manifest_path = f"runs/{run_id}/metadata/manifest.json"
    if not any(item.path == manifest_path for item in result):
        raise MigrationIntegrityError("paper run allowlist omits metadata/manifest.json")
    if len({item.path for item in result}) != len(result):
        raise MigrationIntegrityError("paper run upload allowlist contains duplicate paths")
    return run_id, sorted(result, key=lambda item: item.path)


def _validate_paper_remote_layout(
    *, remote_paths: Iterable[str], run_id: str, desired_paths: set[str], repo_id: str
) -> set[str]:
    other_runs: set[str] = set()
    current_prefix = f"runs/{run_id}/"
    for path in remote_paths:
        path = _safe_repo_path(path)
        if _contains_raw_archive_path(path):
            raise MigrationSafetyError(f"forbidden raw path exists in {repo_id}: {path}")
        if path in {".gitattributes", "README.md"}:
            continue
        parts = PurePosixPath(path).parts
        if len(parts) < 3 or parts[0] != "runs" or not PUBLIC_ID_RE.fullmatch(parts[1]):
            raise MigrationSafetyError(f"unexpected pre-existing file in {repo_id}: {path}")
        existing_run = parts[1]
        if existing_run == run_id:
            if path not in desired_paths:
                raise MigrationSafetyError(
                    f"unexpected immutable file under {current_prefix}: {path}"
                )
        else:
            other_runs.add(existing_run)
    return other_runs


def _verify_paper_run_remote(
    *,
    api: Any,
    repo_id: str,
    revision: str,
    run_id: str,
    files: Sequence[UploadFile],
    token: str | None,
    state_root: Path | str,
    require_private: bool,
) -> dict[str, Any]:
    info = api.repo_info(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        files_metadata=True,
        token=token,
    )
    private = bool(getattr(info, "private", False))
    if require_private and not private:
        raise MigrationSafetyError(f"repository must remain private during upload: {repo_id}")
    desired = {item.path: item for item in files}
    remote = _remote_paths(info)
    other_runs = _validate_paper_remote_layout(
        remote_paths=remote,
        run_id=run_id,
        desired_paths=set(desired),
        repo_id=repo_id,
    )
    missing = sorted(set(desired) - remote)
    if missing:
        raise MigrationIntegrityError(f"paper run is missing remote files: {missing[:5]}")
    temporary_root = Path(state_root) / "remote-verify"
    _ensure_private_dir(temporary_root)
    remote_lfs = _remote_lfs_digests(info)
    for path, item in sorted(desired.items()):
        actual = remote_lfs.get(path)
        if actual is None:
            actual = _remote_file_digest(
                api=api,
                repo_id=repo_id,
                revision=revision,
                path=path,
                token=token,
                temporary_root=temporary_root,
            )
        if actual != item.sha256:
            raise MigrationIntegrityError(
                f"immutable paper run path differs: {repo_id}/{path}"
            )
    return {
        "repo_id": repo_id,
        "private": private,
        "revision": str(getattr(info, "sha", "")),
        "run_id": run_id,
        "run_prefix": f"runs/{run_id}",
        "file_count": len(desired),
        "other_runs": sorted(other_runs),
        "content_set_sha256": sha256_bytes(
            canonical_json(
                [
                    {"path": item.path, "sha256": item.sha256, "size": item.size}
                    for item in sorted(files, key=lambda value: value.path)
                ]
            ).encode("utf-8")
        ),
    }


def _upload_paper_run_files(
    *,
    api: Any,
    repo_id: str,
    revision: str,
    run_id: str,
    files: Sequence[UploadFile],
    token: str | None,
    state_root: Path | str,
    batch_size: int,
) -> dict[str, Any]:
    if batch_size < 1:
        raise ValueError("batch_size must be at least one")
    desired = {item.path: item for item in files}
    if len(desired) != len(files):
        raise MigrationIntegrityError("paper run upload file set contains duplicates")
    for item in files:
        _safe_repo_path(item.path)
        if not item.local_path.is_file():
            raise MigrationIntegrityError(f"upload source is missing: {item.local_path}")
        if item.local_path.stat().st_size != item.size or sha256_file(
            item.local_path
        ) != item.sha256:
            raise MigrationIntegrityError(f"upload source digest mismatch: {item.local_path}")

    ensure_private_destination(api, repo_id=repo_id, revision=revision, token=token)
    info = api.repo_info(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        files_metadata=True,
        token=token,
    )
    remote = _remote_paths(info)
    _validate_paper_remote_layout(
        remote_paths=remote,
        run_id=run_id,
        desired_paths=set(desired),
        repo_id=repo_id,
    )
    manifest_path = f"runs/{run_id}/metadata/manifest.json"
    missing = [item for item in files if item.path not in remote]
    if manifest_path in remote and any(
        item.path.startswith(f"runs/{run_id}/") for item in missing
    ):
        raise MigrationIntegrityError(
            "completed paper run manifest exists but the run bundle is incomplete"
        )
    temporary_root = Path(state_root) / "remote-verify"
    _ensure_private_dir(temporary_root)
    remote_lfs = _remote_lfs_digests(info)
    already_verified = 0
    for path, item in sorted(desired.items()):
        if path not in remote:
            continue
        actual = remote_lfs.get(path)
        if actual is None:
            actual = _remote_file_digest(
                api=api,
                repo_id=repo_id,
                revision=revision,
                path=path,
                token=token,
                temporary_root=temporary_root,
            )
        if actual != item.sha256:
            raise MigrationIntegrityError(
                f"immutable paper run path differs: {repo_id}/{path}"
            )
        already_verified += 1

    before_manifest = sorted(
        (item for item in missing if item.path != manifest_path),
        key=lambda item: item.path,
    )
    uploaded = 0
    for offset in range(0, len(before_manifest), batch_size):
        batch = before_manifest[offset : offset + batch_size]
        api.create_commit(
            repo_id=repo_id,
            repo_type="dataset",
            revision=revision,
            operations=[
                CommitOperationAdd(path_in_repo=item.path, path_or_fileobj=str(item.local_path))
                for item in batch
            ],
            commit_message=f"Upload TRACE evaluation run {run_id}",
            num_threads=min(8, len(batch)),
            token=token,
        )
        uploaded += len(batch)
    if manifest_path in {item.path for item in missing}:
        manifest = desired[manifest_path]
        api.create_commit(
            repo_id=repo_id,
            repo_type="dataset",
            revision=revision,
            operations=[
                CommitOperationAdd(
                    path_in_repo=manifest.path,
                    path_or_fileobj=str(manifest.local_path),
                )
            ],
            commit_message=f"Seal TRACE evaluation run {run_id}",
            num_threads=1,
            token=token,
        )
        uploaded += 1
    report = _verify_paper_run_remote(
        api=api,
        repo_id=repo_id,
        revision=revision,
        run_id=run_id,
        files=files,
        token=token,
        state_root=state_root,
        require_private=True,
    )
    report.update({"uploaded": uploaded, "already_verified": already_verified})
    return report


def upload_paper_run(
    *,
    api: Any,
    repo_id: str,
    public_export_root: Path | str,
    public_export_plan: Path | str,
    state_root: Path | str,
    token: str | None,
    allow_upload: bool,
    confirmation: str | None,
    revision: str = "main",
    batch_size: int = 48,
) -> dict[str, Any]:
    """Guarded append of any provenance-bound trace_eval_v1 run bundle."""

    assert_neutral_paper_repo_id(
        repo_id, forbidden_repo_ids=(DEFAULT_SOURCE_REPO, DEFAULT_INTERNAL_REPO)
    )
    verified, export_files, _ = load_verified_public_run(
        root=public_export_root, public_export_plan=public_export_plan
    )
    run_id, files = _paper_run_files(
        verified=verified, files=export_files, state_root=state_root
    )
    require_confirmation(
        enabled=allow_upload,
        supplied=confirmation,
        expected=f"UPLOAD {repo_id}/{run_id}",
        action="paper-run upload",
    )
    report = _upload_paper_run_files(
        api=api,
        repo_id=repo_id,
        revision=revision,
        run_id=run_id,
        files=files,
        token=token,
        state_root=state_root,
        batch_size=batch_size,
    )
    report["public_export_manifest_sha256"] = verified.manifest_sha256
    return report


def upload_paper_export(
    *,
    api: Any,
    plan_path: Path | str,
    public_export_root: Path | str,
    public_export_plan: Path | str,
    state_root: Path | str,
    token: str | None,
    revision: str = "main",
    batch_size: int = 48,
) -> dict[str, Any]:
    plan = load_selection_plan(plan_path)
    repo_id = str(plan["paper"]["repo_id"])
    assert_neutral_public_repo_id(repo_id, plan=plan)
    verified, export_files = load_verified_public_export(
        root=public_export_root,
        plan=plan,
        public_export_plan=public_export_plan,
    )
    run_id, files = _paper_run_files(
        verified=verified, files=export_files, state_root=state_root
    )
    report = _upload_paper_run_files(
        api=api,
        repo_id=repo_id,
        revision=revision,
        run_id=run_id,
        files=files,
        token=token,
        state_root=state_root,
        batch_size=batch_size,
    )
    report["stage_slices"] = EXPECTED_PAPER_STAGE_SLICES
    report["public_export_manifest_sha256"] = verified.manifest_sha256
    return report


def upload_internal_archive(
    *,
    api: Any,
    plan_path: Path | str,
    backup_root: Path | str,
    state_root: Path | str,
    token: str | None,
    revision: str = "main",
    batch_size: int = 48,
    public_export_plan: Path | str | None = None,
) -> dict[str, Any]:
    plan = load_selection_plan(plan_path)
    repo_id = str(plan["internal"]["repo_id"])
    return upload_private_file_set(
        api=api,
        repo_id=repo_id,
        revision=revision,
        files=internal_upload_files(
            plan=plan,
            backup_root=backup_root,
            state_root=state_root,
            public_export_plan=public_export_plan,
        ),
        token=token,
        state_root=state_root,
        commit_message="Migrate supplementary TRACE evaluation slices",
        batch_size=batch_size,
    )


def verify_internal_archive(
    *,
    api: Any,
    plan: Mapping[str, Any],
    backup_root: Path | str,
    state_root: Path | str,
    token: str | None,
    revision: str = "main",
    public_export_plan: Path | str | None = None,
) -> dict[str, Any]:
    files = internal_upload_files(
        plan=plan,
        backup_root=backup_root,
        state_root=state_root,
        public_export_plan=public_export_plan,
    )
    report = verify_remote_file_set(
        api=api,
        repo_id=str(plan["internal"]["repo_id"]),
        revision=revision,
        files=files,
        token=token,
        state_root=state_root,
        require_private=True,
    )
    report["stage_slices"] = EXPECTED_INTERNAL_STAGE_SLICES
    report["benchmarks"] = list(SUPPLEMENTARY_BENCHMARKS)
    return report


def verify_paper_export(
    *,
    api: Any,
    plan: Mapping[str, Any],
    public_export_root: Path | str,
    public_export_plan: Path | str,
    state_root: Path | str,
    token: str | None,
    revision: str = "main",
    require_private: bool = True,
) -> dict[str, Any]:
    repo_id = str(plan["paper"]["repo_id"])
    assert_neutral_public_repo_id(repo_id, plan=plan)
    verified, export_files = load_verified_public_export(
        root=public_export_root,
        plan=plan,
        public_export_plan=public_export_plan,
    )
    run_id, files = _paper_run_files(
        verified=verified, files=export_files, state_root=state_root
    )
    report = _verify_paper_run_remote(
        api=api,
        repo_id=repo_id,
        revision=revision,
        run_id=run_id,
        files=files,
        token=token,
        state_root=state_root,
        require_private=require_private,
    )
    report["stage_slices"] = EXPECTED_PAPER_STAGE_SLICES
    report["public_export_manifest_sha256"] = verified.manifest_sha256
    return report


def verify_migration(
    *,
    api: Any,
    inventory_path: Path | str,
    backup_root: Path | str,
    plan_path: Path | str,
    public_export_root: Path | str,
    state_root: Path | str,
    output: Path | str,
    token: str | None,
    revision: str = "main",
    public_export_plan: Path | str | None = None,
) -> dict[str, Any]:
    """Verify source, backup, disjoint selections, and both private remotes."""

    if public_export_plan is None:
        raise MigrationSafetyError(
            "full migration verification requires the private public-export plan/crosswalk"
        )
    inventory = load_inventory(inventory_path)
    backup = verify_backup(inventory_path=inventory_path, backup_root=backup_root)
    plan = load_selection_plan(plan_path)
    if plan["inventory_sha256"] != inventory["inventory_sha256"]:
        raise MigrationIntegrityError("selection plan belongs to a different source inventory")
    if plan["backup_manifest_sha256"] != backup["backup_manifest_sha256"]:
        raise MigrationIntegrityError("selection plan belongs to a different local backup")

    paper_benchmarks = set(plan["paper"]["benchmarks"])
    internal_benchmarks = set(plan["internal"]["benchmarks"])
    if paper_benchmarks & internal_benchmarks:
        raise MigrationIntegrityError("paper and internal benchmark selections overlap")
    if len(paper_benchmarks) != 24 or internal_benchmarks != set(SUPPLEMENTARY_BENCHMARKS):
        raise MigrationIntegrityError("migration benchmark partition is incomplete")

    source_info = api.repo_info(
        repo_id=inventory["source"]["repo_id"],
        repo_type="dataset",
        revision=inventory["source"]["requested_revision"],
        files_metadata=False,
        token=token,
    )
    if not bool(getattr(source_info, "private", False)):
        raise MigrationSafetyError("source repository is unexpectedly public")
    source_commit = str(getattr(source_info, "sha", ""))
    if source_commit != inventory["source"]["resolved_commit"]:
        raise MigrationIntegrityError("source repository changed after it was inventoried")
    current_source_refs = _refs_document(
        api.list_repo_refs(
            repo_id=inventory["source"]["repo_id"],
            repo_type="dataset",
            token=token,
        )
    )
    if _normalized_refs_document(current_source_refs) != _normalized_refs_document(
        inventory["refs"]
    ):
        raise MigrationIntegrityError("source repository refs changed after inventory")

    paper_report = verify_paper_export(
        api=api,
        plan=plan,
        public_export_root=public_export_root,
        public_export_plan=public_export_plan,
        state_root=state_root,
        token=token,
        revision=revision,
        require_private=True,
    )
    internal_report = verify_internal_archive(
        api=api,
        plan=plan,
        backup_root=backup_root,
        state_root=state_root,
        token=token,
        revision=revision,
        public_export_plan=public_export_plan,
    )
    if paper_report["repo_id"] == internal_report["repo_id"]:
        raise MigrationSafetyError("paper and internal remotes are not disjoint")

    document = _seal_document(
        {
            "schema_version": VERIFICATION_SCHEMA,
            "verified_at": utc_now(),
            "source_repo_id": inventory["source"]["repo_id"],
            "source_commit": source_commit,
            "source_refs": current_source_refs,
            "inventory_sha256": inventory["inventory_sha256"],
            "backup_manifest_sha256": backup["backup_manifest_sha256"],
            "selection_sha256": plan["selection_sha256"],
            "paper": paper_report,
            "internal": internal_report,
            "coverage": {
                "paper_stage_slices": EXPECTED_PAPER_STAGE_SLICES,
                "internal_stage_slices": EXPECTED_INTERNAL_STAGE_SLICES,
                "paper_benchmarks": sorted(paper_benchmarks),
                "internal_benchmarks": sorted(internal_benchmarks),
                "disjoint": True,
            },
        },
        "verification_sha256",
    )
    _atomic_write_json(Path(output), document)
    return document


def load_verification_receipt(path: Path | str) -> dict[str, Any]:
    return _verify_document(
        _load_json(path),
        schema=VERIFICATION_SCHEMA,
        digest_key="verification_sha256",
        label="migration verification receipt",
    )


def require_confirmation(
    *, enabled: bool, supplied: str | None, expected: str, action: str
) -> None:
    if not enabled:
        raise MigrationSafetyError(f"{action} requires its explicit allow flag")
    if supplied != expected:
        raise MigrationSafetyError(f"{action} requires exact confirmation {expected!r}")


def delete_old_repository(
    *,
    api: Any,
    source_repo_id: str,
    token: str | None,
    allow_delete: bool,
    confirmation: str | None,
    verified_source_repo_id: str,
    verified_source_commit: str,
    verified_source_refs: Mapping[str, Any],
    verified_paper_repo_id: str,
    verified_paper_revision: str,
    verified_internal_repo_id: str,
    verified_internal_revision: str,
) -> None:
    require_confirmation(
        enabled=allow_delete,
        supplied=confirmation,
        expected=f"DELETE {source_repo_id}",
        action="old-repository deletion",
    )
    if source_repo_id != verified_source_repo_id:
        raise MigrationSafetyError(
            "deletion target differs from the repository in the verification receipt"
        )
    if len(
        {source_repo_id, verified_paper_repo_id, verified_internal_repo_id}
    ) != 3:
        raise MigrationSafetyError("source, paper, and internal repositories must be distinct")
    for label, repo_id, expected_revision in (
        ("paper", verified_paper_repo_id, verified_paper_revision),
        ("internal", verified_internal_repo_id, verified_internal_revision),
    ):
        destination = api.repo_info(
            repo_id=repo_id,
            repo_type="dataset",
            revision="main",
            files_metadata=False,
            token=token,
        )
        if not bool(getattr(destination, "private", False)):
            raise MigrationSafetyError(
                f"{label} repository is not private immediately before deletion"
            )
        if str(getattr(destination, "sha", "")) != expected_revision:
            raise MigrationSafetyError(
                f"{label} repository changed after migration verification"
            )
    current_refs = _refs_document(
        api.list_repo_refs(
            repo_id=source_repo_id,
            repo_type="dataset",
            token=token,
        )
    )
    if _normalized_refs_document(current_refs) != _normalized_refs_document(
        verified_source_refs
    ):
        raise MigrationSafetyError("old repository refs changed after migration verification")
    info = api.repo_info(
        repo_id=source_repo_id,
        repo_type="dataset",
        revision="main",
        files_metadata=False,
        token=token,
    )
    if str(getattr(info, "sha", "")) != verified_source_commit:
        raise MigrationSafetyError("old repository changed after migration verification")
    if not bool(getattr(info, "private", False)):
        raise MigrationSafetyError("old repository is unexpectedly public")
    api.delete_repo(
        repo_id=source_repo_id,
        repo_type="dataset",
        token=token,
        missing_ok=False,
    )


def promote_paper_repository(
    *,
    api: Any,
    repo_id: str,
    plan: Mapping[str, Any],
    token: str | None,
    allow_public: bool,
    confirmation: str | None,
    verified_revision: str,
    verified_other_runs: Sequence[str],
) -> None:
    assert_neutral_public_repo_id(repo_id, plan=plan)
    require_confirmation(
        enabled=allow_public,
        supplied=confirmation,
        expected=f"PUBLIC {repo_id}",
        action="paper-repository promotion",
    )
    if repo_id != plan["paper"]["repo_id"]:
        raise MigrationSafetyError("promotion target differs from the verified paper repository")
    if verified_other_runs:
        raise MigrationSafetyError(
            "paper repository contains additional runs without a multi-run public receipt"
        )
    info = api.repo_info(
        repo_id=repo_id,
        repo_type="dataset",
        revision="main",
        files_metadata=False,
        token=token,
    )
    if str(getattr(info, "sha", "")) != verified_revision:
        raise MigrationSafetyError("paper repository changed after migration verification")
    if not bool(getattr(info, "private", False)):
        raise MigrationSafetyError("paper repository is already public or visibility is unknown")
    api.update_repo_settings(
        repo_id=repo_id,
        repo_type="dataset",
        private=False,
        token=token,
    )
