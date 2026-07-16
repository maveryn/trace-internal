#!/usr/bin/env python3
"""Download and verify every Final25 dataset plus provisional MMVP.

Dataset construction alone is not sufficient for VLMEvalKit: many TSVs keep
images as base64 and only write them to disk from ``build_prompt``.  This
script walks every row, materializes the exact prompt media used at inference,
decodes each unique image, and writes an atomic resumable manifest.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import traceback
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from final25_media_contract import (  # noqa: E402
    DATASET_MANIFEST_SCHEMA,
    dataset_snapshot_sha256,
    manifest_snapshot_sha256,
    media_set_sha256,
    source_record_sha256,
)
from run_external_benchmark_generation_queue import _row_hash  # noqa: E402

DEFAULT_SUITE_PATH = REPO_ROOT / "evaluation" / "final25" / "suite.v1.json"
DEFAULT_VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
DEFAULT_LMU_ROOT = Path("/dev/shm/trace_rlvr/LMUData")
MANIFEST_SCHEMA = DATASET_MANIFEST_SCHEMA

# These are the source row counts used by the frozen comparison table.  An
# exact check catches truncated downloads and accidental alias/split changes.
EXPECTED_ROWS = {
    "chartmuseum": 1000,
    "chartqapro": 1948,
    "charxivreason": 1000,
    "tablevqabench": 1500,
    "evochart": 1250,
    "mathvision": 3040,
    "mathvista": 1000,
    "mathverse": 788,
    "wemath": 1740,
    "phyx_mini_mc": 1000,
    "physics": 1297,
    "mmmu_pro_vision": 1730,
    "mmstar": 1500,
    "screenspot": 1272,
    "spatialvizbench_cot": 1180,
    "cvbench_3d": 1200,
    "erqa": 400,
    "blink": 1901,
    "countbenchqa": 487,
    "countqa": 1528,
    "mmvp": 300,
    "treebench": 405,
    "puzzlevqa": 2000,
    "visualpuzzles": 1168,
    "logicvista": 447,
    "mme_reasoning": 1188,
}

CHARTMUSEUM_REPO = "yujieouo/ChartMuseum"
CHARTMUSEUM_FILE = "ChartMuseum_test.tsv"
CHARTMUSEUM_MD5 = "983586eace6ee33cdb189d63124768c8"

PHYSICS_URL = "https://opencompass.openxlab.space/utils/benchmarks/physics/Physics.tsv"
PHYSICS_MD5 = "528d66b7365f9d4db2b58fdeadeade71"
PHYSICS_BLANKIM_MD5 = "b4136f27f09339698f636111c07824e9"
PHYSICS_BLANK_IMAGE_SHA256 = "f18c6b02a63165bb10dedf69a1cb2be16b1cbfbc9bb99199e0bcdae51c89b047"
PHYSICS_TEXT_ONLY_ROWS = 999


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _md5_file(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - upstream artifact identity, not security.
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    temporary.write_text(_canonical_json(payload) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _read_token(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise RuntimeError(f"token file must have mode 600 or stricter: {path}")
    token = path.read_text(encoding="utf-8").strip()
    return token or None


def _git_commit(path: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load_suite(path: Path) -> dict[str, Any]:
    suite = json.loads(path.read_text(encoding="utf-8"))
    if suite.get("schema_version") != "trace-final25-suite-v1":
        raise RuntimeError(f"unsupported Final25 suite schema in {path}")
    return suite


def _selected_keys(suite: dict[str, Any], view: str, only: Iterable[str]) -> list[str]:
    if view == "frozen":
        keys = list(suite["suites"]["frozen"])
    elif view == "provisional-mmvp":
        keys = list(suite["suites"]["provisional_mmvp"])
    else:
        keys = list(suite["suites"]["frozen"])
        for key in suite["suites"]["provisional_mmvp"]:
            if key not in keys:
                keys.append(key)

    requested = set(only)
    unknown = requested - set(keys)
    if unknown:
        raise RuntimeError(f"requested dataset keys are not in {view}: {sorted(unknown)}")
    return [key for key in keys if not requested or key in requested]


def _benchmark_config(suite: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["key"]): dict(item) for item in suite["benchmarks"]}


def _new_manifest(
    *, suite_path: Path, suite: dict[str, Any], lmu_root: Path, vlmeval_root: Path
) -> dict[str, Any]:
    frozen = [str(key) for key in suite["suites"]["frozen"]]
    provisional = [str(key) for key in suite["suites"]["provisional_mmvp"]]
    all26 = [*frozen, *(key for key in provisional if key not in frozen)]
    return {
        "schema_version": MANIFEST_SCHEMA,
        "suite_path": str(suite_path.resolve()),
        "suite_sha256": _sha256_file(suite_path),
        "vlmevalkit_repository": suite["vlmevalkit"]["repository"],
        "vlmevalkit_expected_commit": suite["vlmevalkit"]["commit"],
        "vlmevalkit_commit": _git_commit(vlmeval_root),
        "lmu_data_root": str(lmu_root.resolve()),
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "dataset_views": {
            "frozen": frozen,
            "provisional-mmvp": provisional,
            "all26": all26,
        },
        "view_snapshot_sha256": {},
        "datasets": {},
    }


def _load_or_initialize_manifest(
    path: Path,
    *,
    suite_path: Path,
    suite: dict[str, Any],
    lmu_root: Path,
    vlmeval_root: Path,
) -> dict[str, Any]:
    fresh = _new_manifest(
        suite_path=suite_path,
        suite=suite,
        lmu_root=lmu_root,
        vlmeval_root=vlmeval_root,
    )
    if not path.exists():
        return fresh
    previous = json.loads(path.read_text(encoding="utf-8"))
    stable_fields = (
        "schema_version",
        "suite_sha256",
        "vlmevalkit_expected_commit",
        "vlmevalkit_commit",
        "lmu_data_root",
        "dataset_views",
    )
    mismatched = [field for field in stable_fields if previous.get(field) != fresh.get(field)]
    if mismatched:
        print(f"[dataset:manifest-reset] changed={','.join(mismatched)} path={path}", flush=True)
        return fresh
    fresh["created_at"] = previous.get("created_at", fresh["created_at"])
    fresh["datasets"] = previous.get("datasets", {})
    fresh["view_snapshot_sha256"] = previous.get("view_snapshot_sha256", {})
    return fresh


def _configure_environment(lmu_root: Path, hf_home: Path, token: str | None) -> None:
    lmu_root.mkdir(parents=True, exist_ok=True)
    hf_home.mkdir(parents=True, exist_ok=True)
    os.environ["LMUData"] = str(lmu_root.resolve())
    os.environ["HF_HOME"] = str(hf_home.resolve())
    os.environ["HF_DATASETS_CACHE"] = str((hf_home / "datasets").resolve())
    os.environ["HUGGINGFACE_HUB_CACHE"] = str((hf_home / "hub").resolve())
    # This command never needs CUDA and must not contend with active training.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    if token:
        os.environ["HF_TOKEN"] = token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = token


def _install_import_paths(vlmeval_root: Path) -> None:
    for path in (SCRIPTS_ROOT, vlmeval_root, vlmeval_root / "scripts"):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)


def _stage_chartmuseum(lmu_root: Path, token: str | None) -> Path:
    target = lmu_root / CHARTMUSEUM_FILE
    if target.is_file() and _md5_file(target) == CHARTMUSEUM_MD5:
        return target

    from huggingface_hub import hf_hub_download

    cached = Path(
        hf_hub_download(
            repo_id=CHARTMUSEUM_REPO,
            filename=CHARTMUSEUM_FILE,
            repo_type="dataset",
            token=token,
        )
    )
    if _md5_file(cached) != CHARTMUSEUM_MD5:
        raise RuntimeError(
            f"ChartMuseum checksum mismatch for {cached}: "
            f"{_md5_file(cached)} != {CHARTMUSEUM_MD5}"
        )
    temporary = target.with_suffix(target.suffix + f".tmp.{os.getpid()}")
    shutil.copyfile(cached, temporary)
    os.replace(temporary, target)
    return target


def _stage_physics(lmu_root: Path) -> Path:
    """Restore the pinned text-only Physics TSV from the misserved blank-image variant."""

    import pandas as pd

    target = lmu_root / "Physics.tsv"
    if not target.is_file():
        temporary_download = target.with_suffix(target.suffix + f".download.{os.getpid()}")
        with urllib.request.urlopen(PHYSICS_URL) as response, temporary_download.open("wb") as output:
            shutil.copyfileobj(response, output)
        os.replace(temporary_download, target)

    current_md5 = _md5_file(target)
    if current_md5 == PHYSICS_MD5:
        return target
    if current_md5 != PHYSICS_BLANKIM_MD5:
        raise RuntimeError(
            f"Physics checksum mismatch for {target}: {current_md5} is neither the pinned "
            f"Physics checksum {PHYSICS_MD5} nor the known Physics_blankim checksum "
            f"{PHYSICS_BLANKIM_MD5}"
        )

    data = pd.read_csv(target, sep="\t")
    if "image" not in data:
        raise RuntimeError(f"Physics_blankim has no image column: {target}")
    counts = data["image"].value_counts(dropna=True)
    if counts.empty:
        raise RuntimeError(f"Physics_blankim has no image payloads: {target}")
    blank_image = str(counts.index[0])
    blank_rows = int(counts.iloc[0])
    blank_sha256 = hashlib.sha256(blank_image.encode("utf-8")).hexdigest()
    if blank_rows != PHYSICS_TEXT_ONLY_ROWS or blank_sha256 != PHYSICS_BLANK_IMAGE_SHA256:
        raise RuntimeError(
            "Physics_blankim repeated-image contract changed: "
            f"rows={blank_rows} sha256={blank_sha256}"
        )

    backup = lmu_root / "Physics_blankim.tsv"
    if backup.exists() and _md5_file(backup) != PHYSICS_BLANKIM_MD5:
        raise RuntimeError(f"Existing Physics_blankim backup has an unexpected checksum: {backup}")
    if not backup.exists():
        shutil.copy2(target, backup)

    data.loc[data["image"] == blank_image, "image"] = pd.NA
    temporary = target.with_suffix(target.suffix + f".tmp.{os.getpid()}")
    data.to_csv(
        temporary,
        sep="\t",
        index=False,
        quoting=csv.QUOTE_ALL,
        lineterminator="\n",
        na_rep="",
    )
    repaired_md5 = _md5_file(temporary)
    if repaired_md5 != PHYSICS_MD5:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"Repaired Physics checksum mismatch: {repaired_md5} != {PHYSICS_MD5}"
        )
    os.replace(temporary, target)
    print(
        f"[dataset:physics-repair] text_only_rows={blank_rows} md5={repaired_md5} path={target}",
        flush=True,
    )
    return target


def _build_dataset(key: str, alias: str) -> Any:
    from benchmark_queue_lib import build_vlmeval_dataset, spec_by_key

    if key == "mmvp":
        from vlmeval.dataset import build_dataset

        dataset = build_dataset(alias)
        if dataset is None:
            raise RuntimeError(f"VLMEvalKit could not build dataset {alias}")
        return dataset
    return build_vlmeval_dataset(spec_by_key(key))


def _flatten_media_value(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        flattened: list[str] = []
        for item in value:
            flattened.extend(_flatten_media_value(item))
        return flattened
    if isinstance(value, os.PathLike):
        return [os.fspath(value)]
    if isinstance(value, str):
        return [value]
    raise TypeError(f"unsupported prompt media value type: {type(value).__name__}")


def _resolve_media_path(value: str, working_directory: Path) -> Path:
    parsed = urlparse(value)
    if parsed.scheme and parsed.scheme != "file":
        raise RuntimeError(f"prompt media was not materialized locally: {value[:160]}")
    if parsed.scheme == "file":
        path = Path(parsed.path)
    else:
        path = Path(value).expanduser()
    if not path.is_absolute():
        path = working_directory / path
    return path.resolve()


def _prompt_media(dataset: Any, row: Any, working_directory: Path) -> list[tuple[str, Path]]:
    prompt = dataset.build_prompt(row)
    if not isinstance(prompt, list):
        raise TypeError(f"build_prompt returned {type(prompt).__name__}, expected list")
    media: list[tuple[str, Path]] = []
    for item in prompt:
        if not isinstance(item, dict):
            continue
        media_type = str(item.get("type", "")).lower()
        if media_type not in {"image", "video"}:
            continue
        for value in _flatten_media_value(item.get("value")):
            media.append((media_type, _resolve_media_path(value, working_directory)))
    return media


def _verify_media(item: tuple[str, Path]) -> dict[str, Any]:
    media_type, path = item
    if not path.is_file():
        raise FileNotFoundError(f"missing {media_type}: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise RuntimeError(f"empty {media_type}: {path}")
    if media_type == "image":
        from PIL import Image

        with Image.open(path) as image:
            image.load()
            width, height = image.size
            image_format = image.format
        if width <= 0 or height <= 0:
            raise RuntimeError(f"invalid image dimensions for {path}: {width}x{height}")
        return {
            "path": str(path),
            "type": media_type,
            "size_bytes": size,
            "sha256": _sha256_file(path),
            "width": width,
            "height": height,
            "format": image_format,
        }
    return {
        "path": str(path),
        "type": media_type,
        "size_bytes": size,
        "sha256": _sha256_file(path),
    }


def _verify_media_batch(
    items: Iterable[tuple[str, Path]], workers: int
) -> tuple[list[dict[str, Any]], list[tuple[tuple[str, Path], Exception]]]:
    records: list[dict[str, Any]] = []
    failures: list[tuple[tuple[str, Path], Exception]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        pending = [(item, pool.submit(_verify_media, item)) for item in items]
        for item, future in pending:
            try:
                records.append(future.result())
            except Exception as exc:
                failures.append((item, exc))
    return records, failures


def _metadata_files(dataset: Any, alias: str, lmu_root: Path) -> list[dict[str, Any]]:
    candidates = []
    pending = [dataset]
    visited: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        data_path = getattr(current, "data_path", None)
        if data_path:
            candidates.append(Path(str(data_path)))
        dataset_map = getattr(current, "dataset_map", None)
        if isinstance(dataset_map, dict):
            pending.extend(dataset_map.values())
    candidates.extend((lmu_root / f"{alias}.tsv", lmu_root / f"{alias}_local.tsv"))
    files = []
    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.expanduser().resolve()
        if candidate in seen or not candidate.is_file():
            continue
        seen.add(candidate)
        files.append(
            {
                "path": str(candidate),
                "size_bytes": candidate.stat().st_size,
                "sha256": _sha256_file(candidate),
            }
        )
    if not files:
        raise RuntimeError(f"no persistent metadata file found for alias {alias} under {lmu_root}")
    return files


def _materialize_dataset(
    *,
    key: str,
    alias: str,
    expected_rows: int,
    lmu_root: Path,
    workers: int,
    token: str | None,
) -> dict[str, Any]:
    started = _utc_now()
    if key == "chartmuseum":
        _stage_chartmuseum(lmu_root, token)
    elif key == "physics":
        _stage_physics(lmu_root)
    dataset = _build_dataset(key, alias)
    actual_rows = len(dataset.data)
    if actual_rows != expected_rows:
        raise RuntimeError(
            f"{key} row-count mismatch: downloaded {actual_rows}, expected {expected_rows}"
        )

    working_directory = REPO_ROOT.resolve()
    unique_media: dict[tuple[str, str], tuple[str, Path]] = {}
    media_source_rows: dict[tuple[str, str], int] = {}
    row_media_paths: list[tuple[dict[str, Any], list[tuple[str, Path]]]] = []
    media_references = 0
    rows_without_media: list[str] = []
    progress_every = max(100, min(500, actual_rows // 5 or 100))
    for ordinal, (_, row) in enumerate(dataset.data.iterrows(), start=1):
        row_media = _prompt_media(dataset, row, working_directory)
        row_mapping = row.to_dict() if hasattr(row, "to_dict") else dict(row)
        row_media_paths.append((row_mapping, row_media))
        if not row_media:
            rows_without_media.append(str(row.get("index", ordinal - 1)))
        for media_type, path in row_media:
            media_key = (media_type, str(path))
            unique_media[media_key] = (media_type, path)
            media_source_rows.setdefault(media_key, ordinal - 1)
        media_references += len(row_media)
        if ordinal % progress_every == 0 or ordinal == actual_rows:
            print(
                f"[dataset:prompts] key={key} rows={ordinal}/{actual_rows} "
                f"unique_media={len(unique_media)}",
                flush=True,
            )
    expected_rows_without_media = PHYSICS_TEXT_ONLY_ROWS if key == "physics" else 0
    if len(rows_without_media) != expected_rows_without_media:
        raise RuntimeError(
            f"{key} has {len(rows_without_media)} rows without prompt media, expected "
            f"{expected_rows_without_media}; "
            f"first indices={rows_without_media[:10]}"
        )

    media_files: list[dict[str, Any]] = []
    for verification_attempt in range(2):
        media_files, media_failures = _verify_media_batch(unique_media.values(), workers)
        if not media_failures:
            break
        if verification_attempt:
            details = "; ".join(
                f"{path}: {type(exc).__name__}: {exc}"
                for (_, path), exc in media_failures[:10]
            )
            raise RuntimeError(
                f"{key} has {len(media_failures)} invalid media files after repair: {details}"
            )

        invalid_keys = [(media_type, str(path)) for (media_type, path), _ in media_failures]
        non_images = [path for (media_type, path), _ in media_failures if media_type != "image"]
        if non_images:
            raise RuntimeError(f"{key} has invalid non-image media that cannot be rebuilt: {non_images[:10]}")
        for (_, path), _ in media_failures:
            path.unlink(missing_ok=True)
        for media_key in invalid_keys:
            source_row = dataset.data.iloc[media_source_rows[media_key]]
            rebuilt = {
                (media_type, str(path))
                for media_type, path in _prompt_media(dataset, source_row, working_directory)
            }
            if media_key not in rebuilt:
                raise RuntimeError(f"{key} failed to rebuild invalid media: {media_key[1]}")
        print(
            f"[dataset:media-repair] key={key} repaired={len(media_failures)}",
            flush=True,
        )
    media_files.sort(key=lambda item: (item["type"], item["path"]))
    media_by_path = {
        (str(item["type"]), str(Path(str(item["path"])).resolve())): item
        for item in media_files
    }
    row_media: list[dict[str, Any]] = []
    for ordinal, (row, prompt_media) in enumerate(row_media_paths):
        ordered_media = []
        for media_type, path in prompt_media:
            media = media_by_path[(media_type, str(path.resolve()))]
            ordered_media.append(
                {
                    "type": media_type,
                    "path": str(path.resolve()),
                    "size_bytes": int(media["size_bytes"]),
                    "sha256": str(media["sha256"]),
                }
            )
        source_row_hash = _row_hash(row)
        media_hash = media_set_sha256(ordered_media)
        row_media.append(
            {
                "ordinal": ordinal,
                "index": str(row.get("index", ordinal)),
                "source_row_hash": source_row_hash,
                "media": ordered_media,
                "media_set_sha256": media_hash,
                "source_record_sha256": source_record_sha256(source_row_hash, media_hash),
            }
        )
    metadata_files = _metadata_files(dataset, alias, lmu_root)
    total_bytes = sum(int(item["size_bytes"]) for item in media_files)
    return {
        "status": "ready",
        "key": key,
        "alias": alias,
        "expected_rows": expected_rows,
        "rows": actual_rows,
        "media_references": media_references,
        "rows_without_media": len(rows_without_media),
        "unique_media": len(media_files),
        "media_bytes": total_bytes,
        "metadata_files": metadata_files,
        "media_files": media_files,
        "row_media": row_media,
        "dataset_snapshot_sha256": dataset_snapshot_sha256(row_media),
        "trace_normalization": getattr(dataset, "trace_normalization", {}),
        "started_at": started,
        "completed_at": _utc_now(),
    }


def _receipt_is_complete(receipt: dict[str, Any], *, alias: str, expected_rows: int) -> bool:
    if not (
        receipt.get("status") == "ready"
        and receipt.get("alias") == alias
        and receipt.get("rows") == expected_rows
        and receipt.get("expected_rows") == expected_rows
    ):
        return False
    metadata_files = receipt.get("metadata_files")
    media_files = receipt.get("media_files")
    row_media = receipt.get("row_media")
    if (
        not isinstance(metadata_files, list)
        or not isinstance(media_files, list)
        or not media_files
        or not isinstance(row_media, list)
        or len(row_media) != expected_rows
        or not receipt.get("dataset_snapshot_sha256")
    ):
        return False
    for item in [*metadata_files, *media_files]:
        try:
            path = Path(str(item["path"]))
            size = int(item["size_bytes"])
        except (KeyError, TypeError, ValueError):
            return False
        if not path.is_file() or path.stat().st_size != size or size <= 0:
            return False
        expected_sha256 = str(item.get("sha256") or "")
        if len(expected_sha256) != 64 or _sha256_file(path) != expected_sha256:
            return False
    if dataset_snapshot_sha256(row_media) != receipt.get("dataset_snapshot_sha256"):
        return False
    return True


def _save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    datasets = manifest.get("datasets", {})
    manifest["updated_at"] = _utc_now()
    manifest["ready"] = sum(item.get("status") == "ready" for item in datasets.values())
    manifest["failed"] = sum(item.get("status") == "error" for item in datasets.values())
    manifest["dataset_snapshot_sha256"] = manifest_snapshot_sha256(
        suite_sha256=str(manifest.get("suite_sha256") or ""),
        vlmevalkit_commit=str(manifest.get("vlmevalkit_commit") or ""),
        datasets=datasets,
    )
    view_snapshots: dict[str, str] = {}
    for view, keys in (manifest.get("dataset_views") or {}).items():
        if all(
            (datasets.get(key) or {}).get("status") == "ready"
            and (datasets.get(key) or {}).get("dataset_snapshot_sha256")
            for key in keys
        ):
            view_snapshots[str(view)] = manifest_snapshot_sha256(
                suite_sha256=str(manifest.get("suite_sha256") or ""),
                vlmevalkit_commit=str(manifest.get("vlmevalkit_commit") or ""),
                datasets=datasets,
                keys=keys,
            )
    manifest["view_snapshot_sha256"] = view_snapshots
    _write_json_atomic(path, manifest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE_PATH)
    parser.add_argument(
        "--view",
        choices=("all26", "frozen", "provisional-mmvp"),
        default="all26",
    )
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--lmu-root", type=Path, default=DEFAULT_LMU_ROOT)
    parser.add_argument("--hf-home", type=Path, default=None)
    parser.add_argument("--vlmeval-root", type=Path, default=DEFAULT_VLMEVAL_ROOT)
    parser.add_argument("--token-file", type=Path, default=REPO_ROOT / "hf-token.txt")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=min(32, os.cpu_count() or 1))
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify the existing content hashes and snapshot without downloading or repairing files.",
    )
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    suite_path = args.suite.expanduser().resolve()
    lmu_root = args.lmu_root.expanduser().resolve()
    hf_home = (args.hf_home or (lmu_root / ".hf-cache")).expanduser().resolve()
    vlmeval_root = args.vlmeval_root.expanduser().resolve()
    manifest_path = (
        args.manifest or (lmu_root / "trace_final25_dataset_manifest.json")
    ).expanduser().resolve()
    if args.workers < 1:
        raise SystemExit("--workers must be at least 1")

    token = _read_token(args.token_file.expanduser().resolve() if args.token_file else None)
    _configure_environment(lmu_root, hf_home, token)
    _install_import_paths(vlmeval_root)
    suite = _load_suite(suite_path)
    expected_commit = str(suite["vlmevalkit"]["commit"])
    actual_commit = _git_commit(vlmeval_root)
    if actual_commit != expected_commit:
        raise SystemExit(
            f"VLMEvalKit commit mismatch: {actual_commit} != {expected_commit} ({vlmeval_root})"
        )
    keys = _selected_keys(suite, args.view, args.only)
    configs = _benchmark_config(suite)
    missing_counts = set(keys) - set(EXPECTED_ROWS)
    if missing_counts:
        raise SystemExit(f"missing expected row counts for: {sorted(missing_counts)}")

    manifest = _load_or_initialize_manifest(
        manifest_path,
        suite_path=suite_path,
        suite=suite,
        lmu_root=lmu_root,
        vlmeval_root=vlmeval_root,
    )
    if not args.verify_only:
        _save_manifest(manifest_path, manifest)
    failures: list[str] = []
    for position, key in enumerate(keys, start=1):
        alias = str(configs[key]["vlmeval_alias"])
        expected_rows = EXPECTED_ROWS[key]
        previous = manifest["datasets"].get(key, {})
        if not args.force and _receipt_is_complete(
            previous, alias=alias, expected_rows=expected_rows
        ):
            print(
                f"[dataset:skip] {position}/{len(keys)} key={key} alias={alias} "
                f"rows={expected_rows} media={previous.get('unique_media')}",
                flush=True,
            )
            continue
        if args.verify_only:
            failures.append(key)
            print(
                f"[dataset:verify-error] {position}/{len(keys)} key={key} alias={alias} "
                "receipt or content hash is stale",
                flush=True,
            )
            continue

        manifest["datasets"][key] = {
            "status": "preparing",
            "key": key,
            "alias": alias,
            "expected_rows": expected_rows,
            "started_at": _utc_now(),
        }
        _save_manifest(manifest_path, manifest)
        print(
            f"[dataset:start] {position}/{len(keys)} key={key} alias={alias} "
            f"expected_rows={expected_rows}",
            flush=True,
        )
        try:
            receipt = _materialize_dataset(
                key=key,
                alias=alias,
                expected_rows=expected_rows,
                lmu_root=lmu_root,
                workers=args.workers,
                token=token,
            )
        except KeyboardInterrupt:
            manifest["datasets"][key] = {
                **manifest["datasets"][key],
                "status": "interrupted",
                "completed_at": _utc_now(),
            }
            _save_manifest(manifest_path, manifest)
            raise
        except Exception as exc:
            failures.append(key)
            manifest["datasets"][key] = {
                **manifest["datasets"][key],
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
                "completed_at": _utc_now(),
            }
            _save_manifest(manifest_path, manifest)
            print(f"[dataset:error] key={key} error={type(exc).__name__}: {exc}", flush=True)
            if args.fail_fast:
                break
            continue

        manifest["datasets"][key] = receipt
        _save_manifest(manifest_path, manifest)
        print(
            f"[dataset:done] key={key} rows={receipt['rows']} "
            f"unique_media={receipt['unique_media']} media_bytes={receipt['media_bytes']}",
            flush=True,
        )

    selected_ready = sum(
        _receipt_is_complete(
            manifest["datasets"].get(key, {}),
            alias=str(configs[key]["vlmeval_alias"]),
            expected_rows=EXPECTED_ROWS[key],
        )
        for key in keys
    )
    print(
        f"[dataset:summary] ready={selected_ready}/{len(keys)} failures={failures} "
        f"manifest={manifest_path} lmu_root={lmu_root}",
        flush=True,
    )
    if failures or selected_ready != len(keys):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
