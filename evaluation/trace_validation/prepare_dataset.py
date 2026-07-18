#!/usr/bin/env python3
"""Prepare the pinned 2,000-row TRACE validation set for inference.

The source parquet embeds encoded image bytes.  This preparer writes those
bytes unchanged to content-addressed files and records a deterministic
manifest.  It intentionally does not decode/re-encode or resize the images.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PARQUET = Path(
    "/dev/shm/trace_rlvr/datasets/maveryn_trace_e317b746/data/validation/"
    "trace_rlvr_validation_iid_2000_all1000_seed1042.parquet"
)

DATASET_REPO_ID = "maveryn/trace"
DATASET_REVISION = "e317b746b258630682367cc6a9d87dedd195113c"
DATASET_FILE = (
    "data/validation/trace_rlvr_validation_iid_2000_all1000_seed1042.parquet"
)
DATASET_FILE_SHA256 = (
    "0cb46bcf858ae3e9f39b88f60a24549a5de133976b9e8b74a45b4e6e4d699470"
)
EXPECTED_ROWS = 2_000

MANIFEST_SCHEMA = "trace-validation-dataset-manifest-v1"
MANIFEST_NAME = "manifest.json"
MEDIA_STORAGE = "content-addressed-original-encoded-bytes"

_REQUIRED_COLUMNS = {
    "images",
    "image_sizes",
    "prompt_answer",
    "answer_gt",
    "instance_id",
    "domain",
    "task",
}
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_IMAGE_FORMATS = {
    "BMP": ("bmp", "image/bmp"),
    "GIF": ("gif", "image/gif"),
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "TIFF": ("tiff", "image/tiff"),
    "WEBP": ("webp", "image/webp"),
}


def canonical_json_bytes(value: object) -> bytes:
    """Return the stable JSON encoding used by all validation artifacts."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Atomically replace ``path`` after syncing bytes and its directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.tmp.",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    atomic_write_bytes(path, canonical_json_bytes(payload))


def _inspect_image(payload: bytes) -> dict[str, Any]:
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image_format = str(image.format or "").upper()
            width, height = image.size
            image.verify()
    except Exception as exc:
        raise RuntimeError("embedded image bytes are not a valid image") from exc
    if image_format not in _IMAGE_FORMATS:
        raise RuntimeError(f"unsupported embedded image format: {image_format!r}")
    extension, mime_type = _IMAGE_FORMATS[image_format]
    return {
        "format": image_format,
        "extension": extension,
        "mime_type": mime_type,
        "width": int(width),
        "height": int(height),
    }


def _materialize_image(output_root: Path, payload: bytes) -> dict[str, Any]:
    inspection = _inspect_image(payload)
    digest = sha256_bytes(payload)
    relative_path = PurePosixPath(
        "media",
        "sha256",
        digest[:2],
        f"{digest}.{inspection['extension']}",
    )
    target = output_root.joinpath(*relative_path.parts)
    if target.exists():
        if target.stat().st_size != len(payload) or sha256_file(target) != digest:
            raise RuntimeError(f"corrupt content-addressed image already exists: {target}")
    else:
        atomic_write_bytes(target, payload)
    return {
        "sha256": digest,
        "size_bytes": len(payload),
        "width": inspection["width"],
        "height": inspection["height"],
        "format": inspection["format"],
        "mime_type": inspection["mime_type"],
        "relative_path": relative_path.as_posix(),
    }


def _parse_answer_gt(raw_answer: Any, *, row_index: int) -> dict[str, Any]:
    if not isinstance(raw_answer, str):
        raise RuntimeError(f"row {row_index} answer_gt is not encoded JSON")
    try:
        answer = json.loads(raw_answer)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"row {row_index} answer_gt is invalid JSON") from exc
    if not isinstance(answer, dict):
        raise RuntimeError(f"row {row_index} answer_gt must be a JSON object")
    if not isinstance(answer.get("type"), str) or not answer["type"]:
        raise RuntimeError(f"row {row_index} answer_gt has no answer type")
    if "value" not in answer:
        raise RuntimeError(f"row {row_index} answer_gt has no value")
    canonical_json_bytes(answer)
    return answer


def prepare_dataset(
    parquet_path: Path,
    output_root: Path,
    *,
    dataset_repo_id: str = DATASET_REPO_ID,
    dataset_revision: str = DATASET_REVISION,
    dataset_file: str = DATASET_FILE,
    expected_file_sha256: str = DATASET_FILE_SHA256,
    expected_rows: int = EXPECTED_ROWS,
) -> Path:
    """Prepare a parquet and return the resulting manifest path.

    Non-default identity/count arguments exist for focused tests.  The CLI is
    deliberately pinned to the production constants above.
    """

    parquet_path = parquet_path.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    if not parquet_path.is_file():
        raise FileNotFoundError(f"missing TRACE validation parquet: {parquet_path}")
    source_sha256 = sha256_file(parquet_path)
    if source_sha256 != expected_file_sha256:
        raise RuntimeError(
            "TRACE validation parquet SHA-256 mismatch: "
            f"{source_sha256} != {expected_file_sha256}"
        )

    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - dependency error is environment-specific.
        raise RuntimeError("pyarrow is required to prepare TRACE validation") from exc

    parquet = pq.ParquetFile(parquet_path)
    missing_columns = _REQUIRED_COLUMNS - set(parquet.schema_arrow.names)
    if missing_columns:
        raise RuntimeError(
            f"TRACE validation parquet is missing columns: {sorted(missing_columns)}"
        )
    if parquet.metadata.num_rows != expected_rows:
        raise RuntimeError(
            "TRACE validation row count mismatch: "
            f"{parquet.metadata.num_rows} != {expected_rows}"
        )

    rows: list[dict[str, Any]] = []
    seen_instance_ids: set[str] = set()
    columns = [
        "images",
        "image_sizes",
        "prompt_answer",
        "answer_gt",
        "instance_id",
        "domain",
        "task",
    ]
    for batch in parquet.iter_batches(columns=columns, batch_size=128):
        for source_row in batch.to_pylist():
            row_index = len(rows)
            instance_id = source_row.get("instance_id")
            if not isinstance(instance_id, str) or not instance_id:
                raise RuntimeError(f"row {row_index} has no instance_id")
            if instance_id in seen_instance_ids:
                raise RuntimeError(f"duplicate TRACE instance_id: {instance_id}")
            seen_instance_ids.add(instance_id)

            prompt_answer = source_row.get("prompt_answer")
            if not isinstance(prompt_answer, str) or not prompt_answer:
                raise RuntimeError(f"row {row_index} has no prompt_answer")
            domain = source_row.get("domain")
            task = source_row.get("task")
            if not isinstance(domain, str) or not domain:
                raise RuntimeError(f"row {row_index} has no domain")
            if not isinstance(task, str) or not task:
                raise RuntimeError(f"row {row_index} has no task")

            answer_gt = _parse_answer_gt(source_row.get("answer_gt"), row_index=row_index)
            embedded_images = source_row.get("images")
            declared_sizes = source_row.get("image_sizes")
            if not isinstance(embedded_images, list) or not embedded_images:
                raise RuntimeError(f"row {row_index} has no embedded images")
            if not isinstance(declared_sizes, list) or len(declared_sizes) != len(embedded_images):
                raise RuntimeError(f"row {row_index} image_sizes do not match images")

            images: list[dict[str, Any]] = []
            for image_index, (embedded, declared_size) in enumerate(
                zip(embedded_images, declared_sizes)
            ):
                if not isinstance(embedded, dict):
                    raise RuntimeError(
                        f"row {row_index} image {image_index} has invalid storage"
                    )
                payload = embedded.get("bytes")
                if not isinstance(payload, bytes) or not payload:
                    raise RuntimeError(
                        f"row {row_index} image {image_index} has no embedded bytes"
                    )
                image_record = _materialize_image(output_root, payload)
                if not isinstance(declared_size, dict):
                    raise RuntimeError(
                        f"row {row_index} image {image_index} has invalid declared size"
                    )
                expected_size = (
                    int(declared_size.get("width", -1)),
                    int(declared_size.get("height", -1)),
                )
                actual_size = (image_record["width"], image_record["height"])
                if expected_size != actual_size:
                    raise RuntimeError(
                        f"row {row_index} image {image_index} size mismatch: "
                        f"{actual_size} != {expected_size}"
                    )
                image_record["image_index"] = image_index
                images.append(image_record)

            rows.append(
                {
                    "row_index": row_index,
                    "instance_id": instance_id,
                    "task": task,
                    "domain": domain,
                    "answer_type": answer_gt["type"],
                    "prompt_answer": prompt_answer,
                    "answer_gt": answer_gt,
                    "images": images,
                }
            )

    if len(rows) != expected_rows or len(seen_instance_ids) != expected_rows:
        raise RuntimeError(
            "TRACE validation preparation did not produce the exact unique row set: "
            f"rows={len(rows)} unique_instance_ids={len(seen_instance_ids)} "
            f"expected={expected_rows}"
        )

    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA,
        "dataset": {
            "repo_id": dataset_repo_id,
            "revision": dataset_revision,
            "config": "default",
            "split": "validation",
            "file": dataset_file,
            "file_sha256": source_sha256,
            "file_size_bytes": parquet_path.stat().st_size,
            "row_count": expected_rows,
        },
        "media": {
            "storage": MEDIA_STORAGE,
            "paths_relative_to": MANIFEST_NAME,
            "reencoded": False,
            "resized": False,
        },
        "rows": rows,
    }
    manifest_path = output_root / MANIFEST_NAME
    atomic_write_json(manifest_path, manifest)
    load_manifest(
        manifest_path,
        expected_rows=expected_rows,
        require_pinned=(
            dataset_repo_id == DATASET_REPO_ID
            and dataset_revision == DATASET_REVISION
            and dataset_file == DATASET_FILE
            and expected_file_sha256 == DATASET_FILE_SHA256
        ),
        verify_media=True,
    )
    return manifest_path


def _safe_media_path(manifest_path: Path, relative_path: Any) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise RuntimeError("manifest image has no relative_path")
    pure_path = PurePosixPath(relative_path)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise RuntimeError(f"unsafe manifest media path: {relative_path!r}")
    root = manifest_path.parent.resolve()
    path = root.joinpath(*pure_path.parts).resolve()
    if not path.is_relative_to(root):
        raise RuntimeError(f"manifest media escapes its root: {relative_path!r}")
    return path


def load_manifest(
    manifest_path: Path,
    *,
    expected_rows: int = EXPECTED_ROWS,
    require_pinned: bool = True,
    verify_media: bool = True,
) -> dict[str, Any]:
    """Load and fully validate a prepared TRACE validation manifest."""

    manifest_path = manifest_path.expanduser().resolve()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot load TRACE validation manifest: {manifest_path}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise RuntimeError(f"unsupported TRACE validation manifest: {manifest_path}")

    dataset = manifest.get("dataset")
    if not isinstance(dataset, dict):
        raise RuntimeError("TRACE validation manifest has no dataset identity")
    if require_pinned:
        expected_identity = {
            "repo_id": DATASET_REPO_ID,
            "revision": DATASET_REVISION,
            "file": DATASET_FILE,
            "file_sha256": DATASET_FILE_SHA256,
            "row_count": EXPECTED_ROWS,
        }
        for key, expected in expected_identity.items():
            if dataset.get(key) != expected:
                raise RuntimeError(
                    f"TRACE validation manifest dataset {key} mismatch: "
                    f"{dataset.get(key)!r} != {expected!r}"
                )
    if dataset.get("row_count") != expected_rows:
        raise RuntimeError(
            f"TRACE validation manifest row_count is not {expected_rows}: "
            f"{dataset.get('row_count')!r}"
        )

    rows = manifest.get("rows")
    if not isinstance(rows, list) or len(rows) != expected_rows:
        raise RuntimeError(
            f"TRACE validation manifest must contain exactly {expected_rows} rows"
        )
    seen_instance_ids: set[str] = set()
    verified_media: dict[str, dict[str, Any]] = {}
    for expected_index, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("row_index") != expected_index:
            raise RuntimeError(
                f"TRACE validation manifest row index mismatch at {expected_index}"
            )
        instance_id = row.get("instance_id")
        if not isinstance(instance_id, str) or not instance_id:
            raise RuntimeError(f"manifest row {expected_index} has no instance_id")
        if instance_id in seen_instance_ids:
            raise RuntimeError(f"duplicate manifest instance_id: {instance_id}")
        seen_instance_ids.add(instance_id)
        if not isinstance(row.get("prompt_answer"), str) or not row["prompt_answer"]:
            raise RuntimeError(f"manifest row {expected_index} has no prompt_answer")
        if not isinstance(row.get("task"), str) or not row["task"]:
            raise RuntimeError(f"manifest row {expected_index} has no task")
        if not isinstance(row.get("domain"), str) or not row["domain"]:
            raise RuntimeError(f"manifest row {expected_index} has no domain")
        answer_gt = row.get("answer_gt")
        if not isinstance(answer_gt, dict) or "type" not in answer_gt or "value" not in answer_gt:
            raise RuntimeError(f"manifest row {expected_index} has invalid answer_gt")
        if row.get("answer_type") != answer_gt.get("type"):
            raise RuntimeError(f"manifest row {expected_index} answer_type is inconsistent")

        images = row.get("images")
        if not isinstance(images, list) or not images:
            raise RuntimeError(f"manifest row {expected_index} has no images")
        for expected_image_index, image_record in enumerate(images):
            if not isinstance(image_record, dict):
                raise RuntimeError(f"manifest row {expected_index} has invalid image metadata")
            if image_record.get("image_index") != expected_image_index:
                raise RuntimeError(
                    f"manifest row {expected_index} image index mismatch at "
                    f"{expected_image_index}"
                )
            digest = image_record.get("sha256")
            if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                raise RuntimeError(f"manifest row {expected_index} has invalid image SHA-256")
            if not isinstance(image_record.get("size_bytes"), int) or image_record["size_bytes"] <= 0:
                raise RuntimeError(f"manifest row {expected_index} has invalid image byte size")
            if not isinstance(image_record.get("width"), int) or image_record["width"] <= 0:
                raise RuntimeError(f"manifest row {expected_index} has invalid image width")
            if not isinstance(image_record.get("height"), int) or image_record["height"] <= 0:
                raise RuntimeError(f"manifest row {expected_index} has invalid image height")
            media_path = _safe_media_path(manifest_path, image_record.get("relative_path"))
            if not verify_media:
                continue
            if digest not in verified_media:
                if not media_path.is_file():
                    raise RuntimeError(f"missing prepared TRACE image: {media_path}")
                if media_path.stat().st_size != image_record["size_bytes"]:
                    raise RuntimeError(f"prepared TRACE image size changed: {media_path}")
                if sha256_file(media_path) != digest:
                    raise RuntimeError(f"prepared TRACE image content changed: {media_path}")
                inspection = _inspect_image(media_path.read_bytes())
                for key in ("width", "height", "format", "mime_type"):
                    if inspection[key] != image_record.get(key):
                        raise RuntimeError(
                            f"prepared TRACE image {key} changed: {media_path}"
                        )
                verified_media[digest] = image_record
            else:
                canonical = verified_media[digest]
                for key in (
                    "size_bytes",
                    "width",
                    "height",
                    "format",
                    "mime_type",
                    "relative_path",
                ):
                    if image_record.get(key) != canonical.get(key):
                        raise RuntimeError(
                            f"inconsistent metadata for prepared TRACE image {digest}"
                        )

    if len(seen_instance_ids) != expected_rows:
        raise RuntimeError(
            "TRACE validation manifest does not contain the exact unique instance set"
        )
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--parquet",
        type=Path,
        default=DEFAULT_PARQUET,
        help="local copy of the pinned validation parquet",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        required=True,
        help="directory for manifest.json and original encoded media bytes",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="verify an existing output-root/manifest.json without reading parquet",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.verify_only:
        manifest_path = args.output_root.expanduser().resolve() / MANIFEST_NAME
        manifest = load_manifest(manifest_path)
    else:
        manifest_path = prepare_dataset(args.parquet, args.output_root)
        manifest = load_manifest(manifest_path)
    print(
        json.dumps(
            {
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
                "rows": len(manifest["rows"]),
                "dataset_revision": manifest["dataset"]["revision"],
                "dataset_file_sha256": manifest["dataset"]["file_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
