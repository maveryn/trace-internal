#!/usr/bin/env python3
"""Build Trace RLVR train/validation parquet files from task split v1."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import trace.tasks  # noqa: F401,E402 - register tasks
from trace.core.builder import build_dataset, resolve_build_paths  # noqa: E402
from trace.core.config import BuildConfig, BuildTaskConfig  # noqa: E402
from trace.core.rlvr_export import export_trace_dataset_to_rlvr  # noqa: E402
from trace.tasks.registry import list_default_task_ids  # noqa: E402

SPLIT_ID = "trace_rlvr_task_split_v1"


def _env_bool(name: str, default: str = "0") -> bool:
    return str(os.environ.get(name, default)).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }


def _load_test_tasks() -> list[str]:
    split_doc = Path("docs/RLVR_TASK_SPLIT_PLAN.md").read_text(encoding="utf-8")
    manifest_block = split_doc.split("## Test Task Manifest", 1)[1].split(
        "## Validation Rules", 1
    )[0]
    return sorted(
        set(
            re.findall(
                r"`(task_[a-z0-9_]+__[a-z0-9_]+__[a-z0-9_]+)`",
                manifest_block,
            )
        )
    )


def _reset_for(config: BuildConfig, parquet: Path) -> None:
    paths = resolve_build_paths(config)
    for target in [
        paths.temp_root,
        paths.repro_root,
        paths.final_root,
        paths.failure_root,
        parquet,
    ]:
        if not target.exists():
            continue
        print(f"[reset] removing {target}")
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()


def _jsonl_line_count(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open("rb") as handle:
        return sum(1 for _line in handle)


def _remove_existing_export(path: Path) -> None:
    if path.exists():
        print(f"[reset] removing {path}")
        path.unlink()
    manifest_path = path.with_suffix(path.suffix + ".manifest.json")
    if manifest_path.exists():
        print(f"[reset] removing {manifest_path}")
        manifest_path.unlink()


def _build_and_export(
    *,
    name: str,
    tasks: list[str],
    per_task: int,
    parquet: Path,
    split_role: str,
    output_root: Path,
    seed: int,
    code_hash: str,
    image_cap: int,
) -> None:
    config = BuildConfig(
        output_root=str(output_root),
        dataset_name=name,
        instance_version="v0",
        image_format="png",
        tasks=[BuildTaskConfig(task_id=task_id, count=per_task) for task_id in tasks],
        num_instances=None,
        strict_repro=False,
        max_attempts_per_instance=128,
        sampling_seed=int(seed),
        workers=0,
        max_in_flight=0,
    )

    expected_rows = len(tasks) * int(per_task)
    print(
        f"[build] {name}: split_role={split_role} tasks={len(tasks)} "
        f"per_task={per_task} rows={expected_rows} workers=all max_in_flight=auto"
    )
    build_paths = resolve_build_paths(config)
    temp_train_instances = build_paths.temp_root / "train_instances.jsonl"
    final_train_instances = build_paths.final_root / "train_instances.jsonl"

    if build_paths.final_root.exists():
        final_rows = _jsonl_line_count(final_train_instances)
        if final_rows != expected_rows:
            raise RuntimeError(
                f"final dataset row count mismatch for {name}: {final_rows} != {expected_rows}"
            )
        dataset_root = build_paths.final_root
        print(f"[resume] using finalized dataset {dataset_root}")
        _remove_existing_export(parquet)
    elif build_paths.temp_root.exists() and _jsonl_line_count(temp_train_instances) == expected_rows:
        dataset_root = build_paths.temp_root
        print(f"[resume] using complete staging dataset {dataset_root}")
        _remove_existing_export(parquet)
    else:
        _reset_for(config, parquet)
        dataset_root = build_dataset(config, code_hash=code_hash)

    parquet.parent.mkdir(parents=True, exist_ok=True)
    print(f"[export] {name}: {dataset_root} -> {parquet}")

    result = export_trace_dataset_to_rlvr(
        dataset_root,
        parquet,
        output_format="parquet",
        prompt_variant="answer_and_annotation",
        image_path_mode="relative",
        image_storage_mode="embedded_bytes",
        parquet_cpu_count=0,
        max_embedded_image_pixels=image_cap,
    )

    if int(result.row_count) != expected_rows:
        raise RuntimeError(
            f"{name} exported {result.row_count} rows, expected {expected_rows}"
        )

    manifest = {
        "split_id": SPLIT_ID,
        "split_role": split_role,
        "dataset_name": name,
        "seed": int(seed),
        "task_count": len(tasks),
        "samples_per_task": int(per_task),
        "rows": int(result.row_count),
        "parquet": str(result.output_path),
        "prompt_storage": (
            "both prompt_answer_only and prompt_answer_and_annotation are stored; "
            "active prompt is answer_and_annotation"
        ),
        "max_embedded_image_pixels": int(image_cap),
    }
    manifest_path = result.output_path.with_suffix(
        result.output_path.suffix + ".manifest.json"
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"[done] {name}: rows={result.row_count} manifest={manifest_path}")


def main() -> int:
    seed = int(os.environ["SEED"])
    train_per_task = int(os.environ["TRAIN_PER_TASK"])
    validation_per_task = int(os.environ["VALIDATION_PER_TASK"])
    image_cap = int(os.environ["IMAGE_CAP"])
    output_root = Path(os.environ["OUTPUT_ROOT"])
    code_hash = str(os.environ["CODE_HASH"])
    dry_run = _env_bool("DRY_RUN")

    train_name = str(os.environ["TRAIN_NAME"])
    validation_name = str(os.environ["VALIDATION_NAME"])
    train_parquet = Path(os.environ["TRAIN_PARQUET"])
    validation_parquet = Path(os.environ["VALIDATION_PARQUET"])

    active_tasks = sorted(str(task_id) for task_id in list_default_task_ids())
    test_tasks = _load_test_tasks()
    active_set = set(active_tasks)
    test_set = set(test_tasks)
    train_tasks = sorted(active_set - test_set)

    if len(active_tasks) != 1000:
        raise RuntimeError(f"expected 1000 active tasks, found {len(active_tasks)}")
    if len(test_tasks) != 100:
        raise RuntimeError(f"expected 100 test tasks, found {len(test_tasks)}")
    unknown_test_tasks = sorted(test_set - active_set)
    if unknown_test_tasks:
        raise RuntimeError(f"test tasks not active: {unknown_test_tasks[:10]}")
    if len(train_tasks) != 900:
        raise RuntimeError(f"expected 900 train tasks, found {len(train_tasks)}")

    print(
        f"[split] {SPLIT_ID}: active={len(active_tasks)} train={len(train_tasks)} "
        f"validation={len(test_tasks)} seed={seed}"
    )

    if dry_run:
        print(
            f"[dry-run] train: name={train_name} tasks={len(train_tasks)} "
            f"per_task={train_per_task} rows={len(train_tasks) * train_per_task} "
            f"parquet={train_parquet}"
        )
        print(
            f"[dry-run] validation: name={validation_name} tasks={len(test_tasks)} "
            f"per_task={validation_per_task} rows={len(test_tasks) * validation_per_task} "
            f"parquet={validation_parquet}"
        )
        return 0

    _build_and_export(
        name=train_name,
        tasks=train_tasks,
        per_task=train_per_task,
        parquet=train_parquet,
        split_role="train",
        output_root=output_root,
        seed=seed,
        code_hash=code_hash,
        image_cap=image_cap,
    )
    _build_and_export(
        name=validation_name,
        tasks=test_tasks,
        per_task=validation_per_task,
        parquet=validation_parquet,
        split_role="validation",
        output_root=output_root,
        seed=seed,
        code_hash=code_hash,
        image_cap=image_cap,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
