#!/usr/bin/env python3
"""Build and export a default-task Trace dataset for RLVR training."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from trace.core.build_presets import (
    build_equal_split_all_tasks_config,
    build_query_id_weighted_all_tasks_config,
)
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
        description="Build a default-task Trace dataset and export it to RLVR parquet"
    )
    parser.add_argument("--output-root", default="./out", help="Trace build output root")
    parser.add_argument(
        "--dataset-name",
        default="trace_rlvr_train_128k_all_tasks",
        help="Logical Trace dataset name used in the build config",
    )
    parser.add_argument(
        "--num-instances",
        type=int,
        default=128000,
        help="Total Trace instances to generate; equal mode requires divisibility across active tasks",
    )
    parser.add_argument(
        "--task-sampling-policy",
        choices=("equal", "query_id_aware"),
        default="equal",
        help="Task-level sampling policy: equal per-task counts or counts scaled by active query-id support",
    )
    parser.add_argument(
        "--query-id-weight-alpha",
        type=float,
        default=0.0,
        help="Query-id-aware task weight alpha: weight = 1 + alpha * (active_query_id_count - 1)",
    )
    parser.add_argument(
        "--query-id-count-probe-samples",
        type=int,
        default=8,
        help="Deterministic per-task probes used to resolve active query-id counts for query-id-aware sampling",
    )
    parser.add_argument("--instance-version", default="v0", help="Trace instance ABI version")
    parser.add_argument("--image-format", default="png", help="Trace image format")
    parser.add_argument(
        "--max-attempts-per-instance",
        type=int,
        default=100,
        help="Per-instance bounded resampling limit",
    )
    parser.add_argument("--sampling-seed", type=int, default=0, help="Trace build sampling seed")
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
        choices=("active", "answer", "answer_only", "annotation", "answer_and_annotation"),
        default="answer_and_annotation",
        help=(
            "Which Trace prompt variant to export into the RLVR prompt column "
            "(answer=answer_only, annotation=answer_and_annotation)"
        ),
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
        "--max-embedded-image-pixels",
        type=int,
        default=None,
        help=(
            "Resize embedded parquet images to this pixel cap and scale annotation_gt "
            "into exported-image coordinates"
        ),
    )
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Build the Trace dataset but skip RLVR parquet export",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing artifacts for this dataset/output before rebuilding",
    )
    args = parser.parse_args()

    if str(args.task_sampling_policy) == "query_id_aware":
        config = build_query_id_weighted_all_tasks_config(
            output_root=str(args.output_root),
            dataset_name=str(args.dataset_name),
            num_instances=int(args.num_instances),
            query_id_weight_alpha=float(args.query_id_weight_alpha),
            instance_version=str(args.instance_version),
            image_format=str(args.image_format),
            strict_repro=False,
            max_attempts_per_instance=int(args.max_attempts_per_instance),
            sampling_seed=int(args.sampling_seed),
            workers=int(args.workers),
            max_in_flight=int(args.max_in_flight),
            query_id_count_probe_samples=int(args.query_id_count_probe_samples),
        )
    else:
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
    min_task_count = min((int(task.count or 0) for task in config.tasks), default=0)
    max_task_count = max((int(task.count or 0) for task in config.tasks), default=0)
    min_task_weight = min((float(task.weight or 1.0) for task in config.tasks), default=0.0)
    max_task_weight = max((float(task.weight or 1.0) for task in config.tasks), default=0.0)
    print(
        f"Trace build: tasks={task_count} policy={args.task_sampling_policy} per_task={per_task_count} "
        f"task_count_range={min_task_count}..{max_task_count} "
        f"task_weight_range={min_task_weight:.3f}..{max_task_weight:.3f} "
        f"total={args.num_instances} workers={args.workers} max_in_flight={args.max_in_flight}"
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

    print(f"Trace dataset: {final_path}")
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
        max_embedded_image_pixels=args.max_embedded_image_pixels,
    )
    print(
        f"RLVR parquet: {export_result.output_path} "
        f"(rows={export_result.row_count}, prompt_variant={export_result.prompt_variant})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
