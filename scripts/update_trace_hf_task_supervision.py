#!/usr/bin/env python3
"""Append task supervision modes to the published Trace RLVR parquet files."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from huggingface_hub import CommitOperationAdd, HfApi
import pyarrow as pa
import pyarrow.parquet as pq

from trace.core.task_supervision_policy import load_task_supervision_policy


DEFAULT_REPO_ID = "maveryn/trace"
DEFAULT_SNAPSHOT_DIR = Path(".tmp/hf_maveryn_trace")
DEFAULT_OUTPUT_DIR = Path(".tmp/hf_maveryn_trace_task_conditioned")
DEFAULT_TOKEN_FILE = Path("hf-token.txt")
MODE_COLUMN = "trace_supervision_mode"
POLICY_UPLOAD_PATH = Path("metadata/task_supervision/trace_supervision_policy.json")
UPDATE_MANIFEST_PATH = Path("metadata/task_supervision/parquet_update_manifest.json")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_token(path: Path) -> str:
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError(f"HF token file is empty: {path}")
    return token


def _updated_huggingface_metadata(schema: pa.Schema) -> dict[bytes, bytes] | None:
    metadata = dict(schema.metadata or {})
    raw_hf_metadata = metadata.get(b"huggingface")
    if raw_hf_metadata is None:
        return metadata or None

    payload = json.loads(raw_hf_metadata.decode("utf-8"))
    features = payload.setdefault("info", {}).setdefault("features", {})
    features[MODE_COLUMN] = {"dtype": "string", "_type": "Value"}
    metadata[b"huggingface"] = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return metadata


def _writer_options(column_names: list[str]) -> dict[str, Any]:
    uncompressed = {"images", "image_sizes"}
    return {
        "compression": {
            column: ("NONE" if column in uncompressed else "SNAPPY") for column in column_names
        },
        "use_dictionary": [column for column in column_names if column not in uncompressed],
        "write_statistics": True,
    }


def _mode_array(tasks: list[str], mode_by_task: Mapping[str, str], *, source: Path) -> pa.Array:
    missing = sorted({task for task in tasks if task not in mode_by_task})
    if missing:
        raise RuntimeError(f"{source} contains unmapped task ids: {missing[:10]}")
    return pa.array([mode_by_task[task] for task in tasks], type=pa.string())


def augment_parquet(
    source: Path,
    destination: Path,
    mode_by_task: Mapping[str, str],
) -> dict[str, Any]:
    """Append ``trace_supervision_mode`` while preserving every existing value and row order."""

    parquet = pq.ParquetFile(source)
    source_schema = parquet.schema_arrow
    if MODE_COLUMN in source_schema.names:
        raise RuntimeError(f"{source} already contains {MODE_COLUMN}")
    if "task" not in source_schema.names:
        raise RuntimeError(f"{source} does not contain task")

    output_schema = source_schema.append(pa.field(MODE_COLUMN, pa.string()))
    output_schema = output_schema.with_metadata(_updated_huggingface_metadata(output_schema))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.unlink(missing_ok=True)

    mode_counts: Counter[str] = Counter()
    task_counts: Counter[str] = Counter()
    try:
        with pq.ParquetWriter(temporary, output_schema, **_writer_options(output_schema.names)) as writer:
            for row_group_index in range(parquet.metadata.num_row_groups):
                table = parquet.read_row_group(row_group_index)
                tasks = [str(task) for task in table.column("task").to_pylist()]
                modes = _mode_array(tasks, mode_by_task, source=source)
                table = table.append_column(MODE_COLUMN, modes).replace_schema_metadata(output_schema.metadata)
                writer.write_table(table, row_group_size=table.num_rows)
                mode_counts.update(modes.to_pylist())
                task_counts.update(tasks)
        temporary.replace(destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise

    verify_augmented_parquet(source, destination, mode_by_task)
    return {
        "source": str(source),
        "path": str(destination),
        "rows": int(parquet.metadata.num_rows),
        "tasks": len(task_counts),
        "mode_counts": dict(sorted(mode_counts.items())),
        "source_bytes": source.stat().st_size,
        "output_bytes": destination.stat().st_size,
        "sha256": _sha256(destination),
    }


def verify_augmented_parquet(
    source: Path,
    augmented: Path,
    mode_by_task: Mapping[str, str],
) -> None:
    """Prove that old values and ordering are unchanged and the appended modes are correct."""

    source_file = pq.ParquetFile(source)
    output_file = pq.ParquetFile(augmented)
    old_columns = source_file.schema_arrow.names
    if output_file.schema_arrow.names != [*old_columns, MODE_COLUMN]:
        raise RuntimeError(f"unexpected augmented schema for {augmented}: {output_file.schema_arrow.names}")
    if source_file.metadata.num_rows != output_file.metadata.num_rows:
        raise RuntimeError(f"row count changed for {augmented}")
    if source_file.metadata.num_row_groups != output_file.metadata.num_row_groups:
        raise RuntimeError(f"row-group count changed for {augmented}")

    for row_group_index in range(source_file.metadata.num_row_groups):
        source_table = source_file.read_row_group(row_group_index)
        output_table = output_file.read_row_group(row_group_index)
        if not source_table.equals(output_table.select(old_columns)):
            raise RuntimeError(
                f"existing values changed in {augmented}, row group {row_group_index}"
            )
        tasks = [str(task) for task in source_table.column("task").to_pylist()]
        expected_modes = _mode_array(tasks, mode_by_task, source=source)
        if not expected_modes.equals(output_table.column(MODE_COLUMN).combine_chunks()):
            raise RuntimeError(f"incorrect supervision modes in {augmented}, row group {row_group_index}")


def _update_dataset_card(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    text = text.replace("trace_rlvr_viewer_v1", "trace_rlvr_viewer_v2")
    old_schema_text = (
        "7. `reward_contract`\n\n"
        "`image_sizes` stores the final exported image dimensions used by annotation rewards. "
        "Additional identity/provenance columns follow: `instance_id`, `domain`, `task`, `scene_id`, "
        "`query_id`, `scene_variant`, and `trace_ref`."
    )
    new_schema_text = (
        "7. `reward_contract`\n\n"
        "`image_sizes` stores the final exported image dimensions used by annotation rewards. "
        "Additional identity/provenance columns follow: `instance_id`, `domain`, `task`, `scene_id`, "
        "`query_id`, `scene_variant`, and `trace_ref`. The final `trace_supervision_mode` column is "
        "the fixed per-task selection between `answer` and `answer_and_annotation`."
    )
    if old_schema_text not in text:
        raise RuntimeError("dataset card viewer-schema section has changed unexpectedly")
    text = text.replace(old_schema_text, new_schema_text)

    old_training_text = (
        "For EasyR1 training, use `data.prompt_key=prompt_answer` for answer-only runs and "
        "`data.prompt_key=prompt_answer_and_annotation` for annotation runs. The current Trace "
        "repo loader synthesizes `uid` from `instance_id` internally when needed."
    )
    new_training_text = (
        "For EasyR1 training, the existing global modes remain available: use "
        "`data.prompt_key=prompt_answer` for answer-only runs and "
        "`data.prompt_key=prompt_answer_and_annotation` for answer-plus-annotation runs. The new "
        "`task_conditioned` mode reads `trace_supervision_mode` per row and selects the matching "
        "prompt, system prompt, and reward. The Trace loader synthesizes `uid` from `instance_id` "
        "internally when needed."
    )
    if old_training_text not in text:
        raise RuntimeError("dataset card training section has changed unexpectedly")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text.replace(old_training_text, new_training_text), encoding="utf-8")


def _update_split_manifest(
    source: Path,
    destination: Path,
    *,
    policy_id: str,
    policy_sha256: str,
    mode_counts: Mapping[str, int],
) -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    columns = list(payload.get("columns", []))
    if MODE_COLUMN in columns:
        raise RuntimeError(f"{source} already lists {MODE_COLUMN}")
    columns.append(MODE_COLUMN)
    payload["columns"] = columns
    payload["schema_profile"] = "trace_rlvr_viewer_v2"
    payload["task_supervision"] = {
        "mode_column": MODE_COLUMN,
        "mode_counts": dict(sorted(mode_counts.items())),
        "policy_id": policy_id,
        "policy_path": str(POLICY_UPLOAD_PATH),
        "policy_sha256": policy_sha256,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parquet_sources(snapshot_dir: Path) -> list[Path]:
    sources = sorted((snapshot_dir / "data/train").glob("*.parquet"))
    sources.extend(sorted((snapshot_dir / "data/validation").glob("*.parquet")))
    if len(sources) != 17:
        raise RuntimeError(f"expected 17 published parquet files, found {len(sources)}")
    return sources


def build_update(
    *,
    repo_root: Path,
    snapshot_dir: Path,
    output_dir: Path,
    source_commit: str,
    workers: int,
) -> dict[str, Any]:
    policy = load_task_supervision_policy(repo_root)
    if policy.policy_id != "task_conditioned":
        raise RuntimeError(f"expected policy_id='task_conditioned', got {policy.policy_id!r}")
    if len(policy.assignments) != 1_000:
        raise RuntimeError(f"expected 1,000 policy assignments, got {len(policy.assignments)}")
    mode_by_task = {task_id: assignment.mode for task_id, assignment in policy.assignments.items()}

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    sources = _parquet_sources(snapshot_dir)

    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = {
            executor.submit(
                augment_parquet,
                source,
                output_dir / source.relative_to(snapshot_dir),
                mode_by_task,
            ): source
            for source in sources
        }
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            print(
                f"[augmented] {futures[future].name} rows={record['rows']} "
                f"modes={record['mode_counts']}"
            )
    records.sort(key=lambda item: item["path"])

    observed_task_counts: Counter[str] = Counter()
    split_mode_counts: dict[str, Counter[str]] = {
        "train": Counter(),
        "validation": Counter(),
    }
    for source in sources:
        table = pq.read_table(source, columns=["task"])
        tasks = [str(task) for task in table.column("task").to_pylist()]
        observed_task_counts.update(tasks)
        split = "train" if "/train/" in source.as_posix() else "validation"
        split_mode_counts[split].update(mode_by_task[task] for task in tasks)
    observed_tasks = set(observed_task_counts)
    policy_tasks = set(mode_by_task)
    if observed_tasks != policy_tasks:
        raise RuntimeError(
            f"dataset/policy task mismatch: missing={sorted(policy_tasks - observed_tasks)[:10]} "
            f"stale={sorted(observed_tasks - policy_tasks)[:10]}"
        )

    policy_destination = output_dir / POLICY_UPLOAD_PATH
    policy_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(policy.path, policy_destination)
    policy_sha256 = _sha256(policy_destination)
    _update_dataset_card(snapshot_dir / "README.md", output_dir / "README.md")
    _update_split_manifest(
        snapshot_dir / "metadata/train/trace_rlvr_train_64000_all1000_seed42.parquet.manifest.json",
        output_dir / "metadata/train/trace_rlvr_train_64000_all1000_seed42.parquet.manifest.json",
        policy_id=policy.policy_id,
        policy_sha256=policy_sha256,
        mode_counts=split_mode_counts["train"],
    )
    _update_split_manifest(
        snapshot_dir
        / "metadata/validation_iid/trace_rlvr_validation_iid_2000_all1000_seed1042.parquet.manifest.json",
        output_dir
        / "metadata/validation_iid/trace_rlvr_validation_iid_2000_all1000_seed1042.parquet.manifest.json",
        policy_id=policy.policy_id,
        policy_sha256=policy_sha256,
        mode_counts=split_mode_counts["validation"],
    )

    update_manifest = {
        "dataset_rows_unchanged": True,
        "existing_columns_value_verified": True,
        "mode_column": MODE_COLUMN,
        "parquet_files": records,
        "policy_id": policy.policy_id,
        "policy_sha256": policy_sha256,
        "source_commit": source_commit,
        "split_mode_counts": {
            split: dict(sorted(counts.items())) for split, counts in split_mode_counts.items()
        },
        "task_count": len(policy.assignments),
    }
    manifest_destination = output_dir / UPDATE_MANIFEST_PATH
    manifest_destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_destination.write_text(
        json.dumps(update_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"[built] {output_dir}")
    return update_manifest


def upload_update(
    *,
    api: HfApi,
    repo_id: str,
    revision: str,
    output_dir: Path,
    parent_commit: str,
    token: str,
    threads: int,
) -> str:
    files = sorted(path for path in output_dir.rglob("*") if path.is_file())
    operations = [
        CommitOperationAdd(path_in_repo=str(path.relative_to(output_dir)), path_or_fileobj=str(path))
        for path in files
    ]
    commit = api.create_commit(
        repo_id=repo_id,
        repo_type="dataset",
        revision=revision,
        parent_commit=parent_commit,
        operations=operations,
        commit_message="Add task-conditioned supervision modes to Trace RLVR",
        commit_description=(
            "Appends trace_supervision_mode while preserving all existing rows, images, prompts, "
            "answers, annotations, reward contracts, identities, and row ordering."
        ),
        token=token,
        num_threads=max(1, threads),
    )
    print(f"[uploaded] commit={commit.oid} url={commit.commit_url}")
    return str(commit.oid)


def verify_remote(
    *,
    api: HfApi,
    repo_id: str,
    revision: str,
    output_dir: Path,
    token: str,
) -> None:
    info = api.dataset_info(repo_id, revision=revision, files_metadata=True, token=token)
    remote_files = {sibling.rfilename: sibling for sibling in info.siblings}
    staged_files = sorted(path for path in output_dir.rglob("*") if path.is_file())
    for path in staged_files:
        relative = str(path.relative_to(output_dir))
        remote = remote_files.get(relative)
        if remote is None:
            raise RuntimeError(f"uploaded file missing from HF revision: {relative}")
        if path.suffix == ".parquet":
            remote_sha = getattr(remote.lfs, "sha256", None)
            local_sha = _sha256(path)
            if remote_sha != local_sha:
                raise RuntimeError(
                    f"remote parquet hash mismatch for {relative}: {remote_sha} != {local_sha}"
                )

    update_manifest = json.loads((output_dir / UPDATE_MANIFEST_PATH).read_text(encoding="utf-8"))
    expected: Counter[str] = Counter()
    for split_counts in update_manifest["split_mode_counts"].values():
        expected.update(split_counts)
    total_rows = sum(int(record["rows"]) for record in update_manifest["parquet_files"])
    if total_rows != 66_000:
        raise RuntimeError(f"staged row count is {total_rows}, expected 66,000")
    print(
        f"[remote-verified] revision={revision} parquet_lfs_hashes=17 "
        f"rows={total_rows} modes={dict(expected)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--snapshot-dir", type=Path, default=DEFAULT_SNAPSHOT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--revision", default="main")
    parser.add_argument("--token-file", type=Path, default=DEFAULT_TOKEN_FILE)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--upload-threads", type=int, default=8)
    parser.add_argument("--upload", action="store_true")
    args = parser.parse_args()

    token = _read_token(args.token_file)
    api = HfApi(token=token)
    source_info = api.dataset_info(args.repo_id, revision=args.revision, token=token)
    source_commit = str(source_info.sha)
    build_update(
        repo_root=args.repo_root,
        snapshot_dir=args.snapshot_dir,
        output_dir=args.output_dir,
        source_commit=source_commit,
        workers=args.workers,
    )
    if not args.upload:
        print("[dry-run] local update verified; pass --upload to replace the published parquet files")
        return 0

    commit = upload_update(
        api=api,
        repo_id=args.repo_id,
        revision=args.revision,
        output_dir=args.output_dir,
        parent_commit=source_commit,
        token=token,
        threads=args.upload_threads,
    )
    verify_remote(
        api=api,
        repo_id=args.repo_id,
        revision=commit,
        output_dir=args.output_dir,
        token=token,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
