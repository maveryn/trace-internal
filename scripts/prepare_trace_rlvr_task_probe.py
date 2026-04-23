#!/usr/bin/env python3
"""Build and export a task-specific TRACE dataset for calibration probing."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import trace.tasks  # noqa: F401  # Ensure task registration side effects run.

from trace.core.builder import BuildError, build_dataset, resolve_build_paths
from trace.core.config import BuildConfig, BuildTaskConfig
from trace.core.rlvr_export import export_trace_dataset_to_rlvr, resolve_export_output_path
from trace.tasks.registry import TASK_REGISTRY


def _remove_path(path: Path) -> None:
    """Remove one file or directory if it exists."""

    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def _parse_task_params(raw: str) -> dict[str, Any]:
    """Parse optional task params from a JSON object string."""

    if not str(raw).strip():
        return {}
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("--task-params-json must decode to a JSON object")
    return dict(value)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build one task-only TRACE dataset and export it to an RLVR-ready parquet for calibration probing."
    )
    parser.add_argument("--task-id", required=True, help="TRACE task id to build")
    parser.add_argument(
        "--output-root",
        default="./out/calibration",
        help="TRACE build output root for task-specific calibration datasets",
    )
    parser.add_argument(
        "--dataset-name",
        default=None,
        help="Logical TRACE dataset name (default: derived from task-id and num-instances)",
    )
    parser.add_argument(
        "--num-instances",
        type=int,
        default=200,
        help="Number of task instances to generate for the calibration probe",
    )
    parser.add_argument("--instance-version", default="v1", help="TRACE instance ABI version")
    parser.add_argument("--image-format", default="png", help="TRACE image format")
    parser.add_argument(
        "--max-attempts-per-instance",
        type=int,
        default=100,
        help="Per-instance bounded resampling limit",
    )
    parser.add_argument("--sampling-seed", type=int, default=0, help="TRACE build sampling seed")
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="Generation worker processes (0=all visible CPUs)",
    )
    parser.add_argument(
        "--max-in-flight",
        type=int,
        default=0,
        help="Max queued multiprocessing attempts (0=2x workers)",
    )
    parser.add_argument("--code-hash", default="local", help="Code provenance hash")
    parser.add_argument(
        "--task-params-json",
        default="",
        help="Optional JSON object of task params to inject into the build",
    )
    parser.add_argument(
        "--rlvr-output",
        default=None,
        help="RLVR parquet output path (default: out/calibration/<dataset_name>.parquet)",
    )
    parser.add_argument(
        "--prompt-variant",
        choices=("active", "answer", "answer_only", "evidence", "answer_and_evidence"),
        default="answer",
        help="Which TRACE prompt variant to export into the RLVR prompt column",
    )
    parser.add_argument(
        "--image-path-mode",
        choices=("relative", "absolute", "dataset_relative"),
        default="relative",
        help="How to rewrite image paths in the RLVR export",
    )
    parser.add_argument(
        "--image-storage-mode",
        choices=("path_dict", "embedded_bytes"),
        default="embedded_bytes",
        help="How to store exported images in parquet rows",
    )
    parser.add_argument(
        "--parquet-cpu-count",
        type=int,
        default=0,
        help="Parquet write CPU count (0=all visible CPUs)",
    )
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Build the TRACE dataset but skip RLVR parquet export",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing artifacts for this dataset/output before rebuilding",
    )
    args = parser.parse_args()

    task_id = str(args.task_id).strip()
    if task_id not in TASK_REGISTRY:
        raise SystemExit(f"unknown task-id: {task_id}")

    dataset_name = (
        str(args.dataset_name).strip()
        if args.dataset_name
        else f"{task_id}_probe_{int(args.num_instances)}"
    )
    task_params = _parse_task_params(str(args.task_params_json))
    config = BuildConfig(
        output_root=str(args.output_root),
        dataset_name=str(dataset_name),
        instance_version=str(args.instance_version),
        image_format=str(args.image_format).lower(),
        tasks=[
            BuildTaskConfig(
                task_id=task_id,
                count=int(args.num_instances),
                params=task_params,
            )
        ],
        num_instances=None,
        strict_repro=False,
        max_attempts_per_instance=int(args.max_attempts_per_instance),
        sampling_seed=int(args.sampling_seed),
        workers=int(args.workers),
        max_in_flight=int(args.max_in_flight),
    )

    rlvr_output = (
        Path(args.rlvr_output)
        if args.rlvr_output
        else Path(args.output_root) / f"{dataset_name}.parquet"
    )
    final_rlvr_output, _ = resolve_export_output_path(rlvr_output, output_format="parquet")

    if args.reset:
        build_paths = resolve_build_paths(config)
        reset_targets = [
            build_paths.temp_root,
            build_paths.repro_root,
            build_paths.final_root,
            build_paths.failure_root,
            final_rlvr_output,
        ]
        print("Reset artifacts:")
        for target in reset_targets:
            if target.exists():
                print(f"  removing {target}")
            _remove_path(target)

    try:
        final_path = build_dataset(config, code_hash=str(args.code_hash))
    except BuildError as exc:
        raise SystemExit(f"build failed: {exc}") from exc

    print(f"TRACE dataset: {final_path}")
    if args.build_only:
        return 0

    export_result = export_trace_dataset_to_rlvr(
        final_path,
        final_rlvr_output,
        output_format="parquet",
        prompt_variant=args.prompt_variant,
        image_path_mode=args.image_path_mode,
        image_storage_mode=args.image_storage_mode,
        parquet_cpu_count=args.parquet_cpu_count,
    )
    print(
        f"RLVR parquet: {export_result.output_path} "
        f"(rows={export_result.row_count}, prompt_variant={export_result.prompt_variant})"
    )
    manifest_path = final_rlvr_output.with_suffix(final_rlvr_output.suffix + ".manifest.json")
    manifest_payload = {
        "task_id": task_id,
        "dataset_name": dataset_name,
        "num_instances": int(args.num_instances),
        "task_params": task_params,
        "trace_dataset_root": str(final_path),
        "rlvr_output_path": str(export_result.output_path),
        "row_count": int(export_result.row_count),
        "prompt_variant": str(export_result.prompt_variant),
    }
    manifest_path.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Probe manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
