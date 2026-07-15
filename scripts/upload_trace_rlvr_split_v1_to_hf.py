#!/usr/bin/env python3
"""Upload Trace RLVR split-v1 parquet datasets to Hugging Face Hub."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable

import pyarrow.parquet as pq
from huggingface_hub import HfApi


DEFAULT_REPO_ID = "maveryn/trace"
DEFAULT_TOKEN_FILE = "hf-token.txt"

TRAIN_PARQUET = Path(
    "rlvr/dataset/train/trace_rlvr_train_230400_task_split_v1_seed42.parquet"
)
TRAIN_MANIFEST = Path(
    "rlvr/dataset/train/trace_rlvr_train_230400_task_split_v1_seed42.parquet.manifest.json"
)
VALIDATION_PARQUET = Path(
    "rlvr/dataset/validation/trace_rlvr_validation_2500_task_split_v1_seed42.parquet"
)
VALIDATION_MANIFEST = Path(
    "rlvr/dataset/validation/trace_rlvr_validation_2500_task_split_v1_seed42.parquet.manifest.json"
)

EXPECTED = {
    TRAIN_PARQUET: {
        "rows": 230_400,
        "tasks": 900,
        "samples_per_task": 256,
        "split_role": "train",
    },
    VALIDATION_PARQUET: {
        "rows": 2_500,
        "tasks": 100,
        "samples_per_task": 25,
        "split_role": "validation",
    },
}


def _read_token(path: Path) -> str:
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError(f"HF token file is empty: {path}")
    if not token.startswith("hf_"):
        raise RuntimeError(f"HF token file does not look like an HF token: {path}")
    return token


def _format_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for suffix in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if value < 1024.0 or suffix == "TiB":
            return f"{value:.1f} {suffix}"
        value /= 1024.0
    return f"{size_bytes} B"


def _validate_parquet(path: Path) -> None:
    expected = EXPECTED[path]
    pf = pq.ParquetFile(path)
    rows = int(pf.metadata.num_rows)
    if rows != expected["rows"]:
        raise RuntimeError(f"{path} has {rows} rows, expected {expected['rows']}")
    task_counts: dict[str, int] = {}
    max_pixels = 0
    null_or_empty: dict[str, int] = {}
    required_columns = [
        "task",
        "prompt_answer_only",
        "prompt_answer_and_annotation",
        "answer_gt",
        "annotation_gt",
        "reward_contract",
        "trace_ref",
        "image_sizes_exported",
    ]
    for batch in pf.iter_batches(batch_size=4096, columns=required_columns):
        data = batch.to_pydict()
        for task_id in data["task"]:
            task_counts[str(task_id)] = task_counts.get(str(task_id), 0) + 1
        for column in required_columns[1:7]:
            null_or_empty[column] = null_or_empty.get(column, 0) + sum(
                value is None or value == "" for value in data[column]
            )
        for sizes in data["image_sizes_exported"]:
            if not sizes:
                raise RuntimeError(f"{path} has a row without exported image sizes")
            for size in sizes:
                pixels = int(size["width"]) * int(size["height"])
                max_pixels = max(max_pixels, pixels)
                if pixels > 1_280_000:
                    raise RuntimeError(
                        f"{path} has exported image over cap: {pixels} pixels"
                    )
    if len(task_counts) != expected["tasks"]:
        raise RuntimeError(
            f"{path} has {len(task_counts)} tasks, expected {expected['tasks']}"
        )
    min_count = min(task_counts.values())
    max_count = max(task_counts.values())
    if min_count != expected["samples_per_task"] or max_count != expected["samples_per_task"]:
        raise RuntimeError(
            f"{path} has per-task count range {min_count}..{max_count}, "
            f"expected {expected['samples_per_task']}"
        )
    bad_fields = {key: value for key, value in null_or_empty.items() if value}
    if bad_fields:
        raise RuntimeError(f"{path} has missing required fields: {bad_fields}")
    print(
        f"[check] {path}: rows={rows} tasks={len(task_counts)} "
        f"per_task={min_count} max_pixels={max_pixels}"
    )


def _validate_manifest(path: Path, manifest_path: Path) -> None:
    expected = EXPECTED[path]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = {
        "split_role": expected["split_role"],
        "rows": expected["rows"],
        "task_count": expected["tasks"],
        "samples_per_task": expected["samples_per_task"],
        "max_embedded_image_pixels": 1_280_000,
    }
    for key, value in checks.items():
        if manifest.get(key) != value:
            raise RuntimeError(
                f"{manifest_path} field {key!r} is {manifest.get(key)!r}, expected {value!r}"
            )
    print(f"[check] {manifest_path}: ok")


def _write_dataset_card(path: Path) -> None:
    path.write_text(
        """---
pretty_name: Trace RLVR
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
---

# Trace RLVR

Private Trace RLVR task-split-v1 parquet export.

## Files

- `data/train/trace_rlvr_train_230400_task_split_v1_seed42.parquet`
  - 900 train tasks
  - 256 samples per task
  - 230,400 rows
- `data/validation/trace_rlvr_validation_2500_task_split_v1_seed42.parquet`
  - 100 held-out validation tasks
  - 25 samples per task
  - 2,500 rows

Each row stores both answer-only and answer-plus-annotation prompt fields,
ground-truth answer and annotation payloads, reward contract metadata, embedded
image bytes, image size metadata, and `trace_ref`.

The split is documented in `docs/RLVR_TASK_SPLIT_PLAN.md` in the Trace repo.
""",
        encoding="utf-8",
    )


def _files_to_upload(card_path: Path) -> list[tuple[Path, str]]:
    return [
        (card_path, "README.md"),
        (TRAIN_PARQUET, f"data/train/{TRAIN_PARQUET.name}"),
        (TRAIN_MANIFEST, f"data/train/{TRAIN_MANIFEST.name}"),
        (VALIDATION_PARQUET, f"data/validation/{VALIDATION_PARQUET.name}"),
        (VALIDATION_MANIFEST, f"data/validation/{VALIDATION_MANIFEST.name}"),
    ]


def _validate_files(files: Iterable[Path]) -> None:
    for path in files:
        if not path.exists():
            raise FileNotFoundError(path)
        if path.is_file() and path.stat().st_size <= 0:
            raise RuntimeError(f"empty file: {path}")
        print(f"[file] {path} {_format_size(path.stat().st_size)}")
    _validate_manifest(TRAIN_PARQUET, TRAIN_MANIFEST)
    _validate_manifest(VALIDATION_PARQUET, VALIDATION_MANIFEST)
    _validate_parquet(TRAIN_PARQUET)
    _validate_parquet(VALIDATION_PARQUET)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--token-file", default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--revision", default="main")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-readme", action="store_true")
    parser.add_argument(
        "--commit-message",
        default="Upload Trace RLVR task split v1 train and validation parquet",
    )
    args = parser.parse_args()

    token_file = Path(args.token_file)
    token = _read_token(token_file)
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    card_path = Path(".tmp/hf_trace_dataset_card.md")
    card_path.parent.mkdir(parents=True, exist_ok=True)
    _write_dataset_card(card_path)

    paths = [TRAIN_PARQUET, TRAIN_MANIFEST, VALIDATION_PARQUET, VALIDATION_MANIFEST]
    if not args.skip_readme:
        paths.append(card_path)
    _validate_files(paths)

    upload_files = _files_to_upload(card_path)
    if args.skip_readme:
        upload_files = [item for item in upload_files if item[1] != "README.md"]

    print(f"[repo] dataset {args.repo_id} private=True revision={args.revision}")
    if args.dry_run:
        for local_path, path_in_repo in upload_files:
            print(f"[dry-run] would upload {local_path} -> {path_in_repo}")
        return 0

    api = HfApi(token=token)
    whoami = api.whoami()
    print(f"[auth] user={whoami.get('name')}")
    api.create_repo(
        repo_id=args.repo_id,
        repo_type="dataset",
        private=True,
        exist_ok=True,
        token=token,
    )
    for local_path, path_in_repo in upload_files:
        print(f"[upload] {local_path} -> {args.repo_id}/{path_in_repo}")
        info = api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=path_in_repo,
            repo_id=args.repo_id,
            repo_type="dataset",
            revision=args.revision,
            token=token,
            commit_message=args.commit_message,
        )
        print(f"[uploaded] {path_in_repo}: {info.commit_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
