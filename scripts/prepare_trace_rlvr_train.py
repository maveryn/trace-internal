#!/usr/bin/env python3
"""Build and export an equal-split TRACE dataset for RLVR training."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from trace.core.build_presets import build_equal_split_all_tasks_config
from trace.core.builder import BuildError, build_dataset, resolve_build_paths
from trace.core.rlvr_export import export_trace_dataset_to_rlvr, resolve_export_output_path


def _remove_path(path: Path) -> None:
    """Remove one file or directory if it exists."""

    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an equal-split all-task TRACE dataset and export it to RLVR parquet"
    )
    parser.add_argument("--output-root", default="./out", help="TRACE build output root")
    parser.add_argument(
        "--dataset-name",
        default="trace_rlvr_train_128k_all_tasks",
        help="Logical TRACE dataset name used in the build config",
    )
    parser.add_argument(
        "--num-instances",
        type=int,
        default=128000,
        help="Total TRACE instances to generate; must divide evenly across active tasks",
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
        "--rlvr-output",
        default=None,
        help="RLVR parquet output path (default: rlvr/dataset/train/<dataset_name>.parquet)",
    )
    parser.add_argument(
        "--prompt-variant",
        choices=("active", "answer_only", "answer_and_evidence"),
        default="answer_and_evidence",
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
        help="How to store exported images in parquet rows (default: embedded_bytes for training exports)",
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

    config = build_equal_split_all_tasks_config(
        output_root=str(args.output_root),
        dataset_name=str(args.dataset_name),
        num_instances=int(args.num_instances),
        instance_version=str(args.instance_version),
        image_format=str(args.image_format),
        strict_repro=False,
        max_attempts_per_instance=int(args.max_attempts_per_instance),
        sampling_seed=int(args.sampling_seed),
        workers=int(args.workers),
        max_in_flight=int(args.max_in_flight),
    )
    task_count = len(config.tasks)
    per_task_count = int(config.tasks[0].count or 0) if config.tasks else 0
    print(
        f"TRACE build: tasks={task_count} per_task={per_task_count} total={args.num_instances} "
        f"workers={args.workers} max_in_flight={args.max_in_flight}"
    )

    rlvr_output = (
        Path(args.rlvr_output)
        if args.rlvr_output
        else Path("rlvr") / "dataset" / "train" / f"{args.dataset_name}.parquet"
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
