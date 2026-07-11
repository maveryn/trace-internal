#!/usr/bin/env python3
"""Package and upload the TRACE all1000 IID RLVR dataset to Hugging Face."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
import zstandard as zstd
from datasets import load_dataset
from huggingface_hub import HfApi


DEFAULT_REPO_ID = "maveryn/trace"
DEFAULT_TOKEN_FILE = "hf-token.txt"
DEFAULT_TMPFS_ROOT = Path("/dev/shm/trace_rlvr")
DEFAULT_ROW_ORDER_SEED = 20260711

VIEWER_COLUMNS = [
    "images",
    "prompt_answer",
    "prompt_answer_and_annotation",
    "answer_gt",
    "annotation_gt",
    "reward_contract",
    "instance_id",
    "domain",
    "task",
    "scene_id",
    "query_id",
    "scene_variant",
    "trace_ref",
]

DROPPED_COLUMNS = [
    "uid",
    "prompt",
    "prompt_active",
    "prompt_answer_only",
    "prompt_mode",
    "difficulty_bin",
    "bucket_id_str",
    "image_sizes_original",
    "image_sizes_exported",
]


def _read_token(path: Path) -> str:
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError(f"HF token file is empty: {path}")
    return token


def _find_dataset_root(role_root: Path) -> Path:
    candidates = sorted((role_root / "datasets").glob("blake3:*"))
    if len(candidates) != 1:
        raise RuntimeError(f"expected exactly one dataset root under {role_root / 'datasets'}, got {candidates}")
    return candidates[0]


def _compress_zstd(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    cctx = zstd.ZstdCompressor(level=6, threads=0)
    with src.open("rb") as input_file, dst.open("wb") as output_file:
        with cctx.stream_writer(output_file) as compressor:
            shutil.copyfileobj(input_file, compressor)


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _package_sidecars(dataset_root: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []

    for name in ("build_report.json", "validation_report.json"):
        src = dataset_root / name
        dst = out_dir / name
        _copy_file(src, dst)
        files.append({"path": str(dst.name), "source": str(src), "bytes": dst.stat().st_size})

    for name in ("curriculum_index.jsonl", "train_instances.jsonl"):
        src = dataset_root / name
        dst = out_dir / f"{name}.zst"
        _compress_zstd(src, dst)
        files.append(
            {
                "path": str(dst.name),
                "source": str(src),
                "bytes": dst.stat().st_size,
                "compression": "zstd",
            }
        )

    traces_out = out_dir / "traces"
    trace_files = sorted((dataset_root / "traces").glob("*.jsonl.zst"))
    if not trace_files:
        raise RuntimeError(f"no compressed trace shards found under {dataset_root / 'traces'}")
    for src in trace_files:
        dst = traces_out / src.name
        _copy_file(src, dst)
        files.append({"path": f"traces/{dst.name}", "source": str(src), "bytes": dst.stat().st_size})

    manifest = {
        "source_dataset_root": str(dataset_root),
        "included": files,
        "excluded": [
            {
                "path": "images/",
                "reason": "raw image files are omitted because the training parquet embeds image bytes",
            }
        ],
    }
    (out_dir / "sidecar_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _build_viewer_parquet(
    *,
    src: Path,
    dst: Path,
    manifest_dst: Path,
    rows: int,
    task_count: int,
    samples_per_task: int,
    generation_seed: int,
    split_role: str,
    row_order_seed: int,
    sidecar_paths: list[str],
    cache_dir: Path,
) -> dict[str, Any]:
    schema_names = set(pq.read_schema(src).names)
    missing = [column for column in VIEWER_COLUMNS if column not in schema_names]
    if missing:
        raise RuntimeError(f"{src} is missing required columns: {missing}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    os.environ["HF_DATASETS_CACHE"] = str(cache_dir)
    original_ids = set(pq.read_table(src, columns=["instance_id"]).column("instance_id").to_pylist())
    dataset = load_dataset("parquet", data_files=str(src), split="train")
    dataset = dataset.select_columns(VIEWER_COLUMNS).shuffle(seed=row_order_seed)
    dataset.to_parquet(str(dst), batch_size=512)

    pf = pq.ParquetFile(dst)
    if int(pf.metadata.num_rows) != rows:
        raise RuntimeError(f"{dst} has {pf.metadata.num_rows} rows, expected {rows}")
    if list(pq.read_schema(dst).names) != VIEWER_COLUMNS:
        raise RuntimeError(f"{dst} has unexpected columns: {pq.read_schema(dst).names}")
    uploaded_ids = set(pq.read_table(dst, columns=["instance_id"]).column("instance_id").to_pylist())
    if uploaded_ids != original_ids:
        raise RuntimeError(f"{dst} row membership differs from source parquet")

    manifest = {
        "columns": VIEWER_COLUMNS,
        "dataset_name": dst.name.removesuffix(".parquet"),
        "dropped_columns": DROPPED_COLUMNS,
        "image_storage_mode": "embedded_bytes",
        "max_embedded_image_pixels": 1_280_000,
        "prompt_storage": "RLVR export stores prompt_answer and prompt_answer_and_annotation.",
        "recipe": "trace_rlvr_all1000_iid_tmpfs",
        "row_order": "deterministic_shuffle",
        "row_order_seed": row_order_seed,
        "rows": rows,
        "samples_per_task": samples_per_task,
        "schema_profile": "trace_rlvr_viewer_v1",
        "seed": generation_seed,
        "sidecars": sidecar_paths,
        "split_role": split_role,
        "task_count": task_count,
    }
    manifest_dst.parent.mkdir(parents=True, exist_ok=True)
    manifest_dst.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[parquet] {dst} rows={rows} columns={len(VIEWER_COLUMNS)} bytes={dst.stat().st_size}")
    return manifest


def _write_readme(path: Path) -> None:
    path.write_text(
        """---
pretty_name: TRACE RLVR
language:
- en
license: other
task_categories:
- visual-question-answering
tags:
- rlvr
- visual-reasoning
- synthetic
- trace
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train/trace_rlvr_train_64000_all1000_seed42.parquet
  - split: validation
    path: data/validation/trace_rlvr_validation_iid_2000_all1000_seed1042.parquet
---

# TRACE RLVR

Private TRACE RLVR all1000 IID parquet export for Qwen2.5-VL RLVR training.

## Files

- `data/train/trace_rlvr_train_64000_all1000_seed42.parquet`
  - 1,000 training tasks
  - 64 samples per task
  - 64,000 rows
  - generation seed: 42
- `data/validation/trace_rlvr_validation_iid_2000_all1000_seed1042.parquet`
  - IID validation over the same 1,000 tasks
  - 2 samples per task
  - 2,000 rows
  - generation seed: 1042

## Row Order

The uploaded parquet row order is deterministically shuffled for easier browsing in the Hugging Face viewer.

- `row_order`: `deterministic_shuffle`
- `row_order_seed`: `20260711`

The shuffle changes only row order. It does not change prompts, images, answers, annotations, reward contracts, trace refs, or row membership.

## Viewer Schema

The main parquet files use `trace_rlvr_viewer_v1`. The first columns are ordered for browsing:

1. `images`
2. `prompt_answer`
3. `prompt_answer_and_annotation`
4. `answer_gt`
5. `annotation_gt`
6. `reward_contract`

Additional identity/provenance columns follow: `instance_id`, `domain`, `task`, `scene_id`, `query_id`, `scene_variant`, and `trace_ref`.

The previous viewer-noisy compatibility columns were removed from the main parquet: `uid`, `prompt`, `prompt_active`, `prompt_answer_only`, `prompt_mode`, `difficulty_bin`, `bucket_id_str`, `image_sizes_original`, and `image_sizes_exported`.

## Sidecars

Non-image TRACE sidecars are uploaded under `sidecars/`.

- `sidecars/train/`
- `sidecars/validation_iid/`

Each sidecar directory includes build reports, curriculum indices, train-instance records, compressed execution trace shards, and a `sidecar_manifest.json`. Raw image directories are intentionally not uploaded as sidecars because the main parquet embeds image bytes.

For EasyR1 training, use `data.prompt_key=prompt_answer` for answer-only runs and `data.prompt_key=prompt_answer_and_annotation` for annotation runs. The current TRACE repo loader synthesizes `uid` from `instance_id` internally when needed.
""",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--token-file", default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--tmpfs-root", type=Path, default=DEFAULT_TMPFS_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_TMPFS_ROOT / "hf_upload_trace_all1000_iid")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--row-order-seed", type=int, default=DEFAULT_ROW_ORDER_SEED)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    args = parser.parse_args()

    token = _read_token(Path(args.token_file))
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
    cache_dir = args.tmpfs_root / "cache/hf_datasets_trace_all1000_upload"

    train_src = args.tmpfs_root / "datasets/trace_rlvr_train_64000_all1000_seed42.parquet"
    val_src = args.tmpfs_root / "datasets/trace_rlvr_validation_iid_2000_all1000_seed1042.parquet"
    train_root = _find_dataset_root(args.tmpfs_root / "builds/all1000_iid/train")
    val_root = _find_dataset_root(args.tmpfs_root / "builds/all1000_iid/validation_iid")

    if args.output_dir.exists():
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    train_sidecars = _package_sidecars(train_root, args.output_dir / "sidecars/train")
    val_sidecars = _package_sidecars(val_root, args.output_dir / "sidecars/validation_iid")
    _build_viewer_parquet(
        src=train_src,
        dst=args.output_dir / f"data/train/{train_src.name}",
        manifest_dst=args.output_dir / f"metadata/train/{train_src.name}.manifest.json",
        rows=64_000,
        task_count=1_000,
        samples_per_task=64,
        generation_seed=42,
        split_role="train",
        row_order_seed=args.row_order_seed,
        sidecar_paths=[f"sidecars/train/{item['path']}" for item in train_sidecars["included"]],
        cache_dir=cache_dir,
    )
    _build_viewer_parquet(
        src=val_src,
        dst=args.output_dir / f"data/validation/{val_src.name}",
        manifest_dst=args.output_dir / f"metadata/validation_iid/{val_src.name}.manifest.json",
        rows=2_000,
        task_count=1_000,
        samples_per_task=2,
        generation_seed=1042,
        split_role="validation_iid",
        row_order_seed=args.row_order_seed,
        sidecar_paths=[f"sidecars/validation_iid/{item['path']}" for item in val_sidecars["included"]],
        cache_dir=cache_dir,
    )
    _write_readme(args.output_dir / "README.md")

    print(f"[package] {args.output_dir}")
    if args.dry_run or args.skip_upload:
        return 0

    api = HfApi(token=token)
    api.create_repo(repo_id=args.repo_id, repo_type="dataset", private=True, exist_ok=True)
    api.upload_folder(
        repo_id=args.repo_id,
        repo_type="dataset",
        folder_path=str(args.output_dir),
        path_in_repo="",
        revision=args.revision,
        commit_message="Upload TRACE all1000 IID viewer parquet and sidecars",
        delete_patterns=[
            "data/train/*.manifest.json",
            "data/validation/*.manifest.json",
        ],
    )
    print(f"[uploaded] {args.repo_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
