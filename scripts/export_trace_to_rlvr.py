#!/usr/bin/env python3
"""Export a built TRACE dataset into an RLVR-ready file."""

from __future__ import annotations

import argparse

from trace.core.rlvr_export import export_trace_dataset_to_rlvr


def main() -> int:
    parser = argparse.ArgumentParser(description="Export TRACE train instances into RLVR-ready JSONL/parquet")
    parser.add_argument(
        "--source",
        required=True,
        help="TRACE dataset root or its train_instances.jsonl file",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file or directory for the RLVR export",
    )
    parser.add_argument(
        "--format",
        choices=("jsonl", "parquet"),
        default=None,
        help="Explicit output format. Defaults to the output suffix, then jsonl.",
    )
    parser.add_argument(
        "--prompt-variant",
        choices=("active", "answer", "answer_only", "annotation", "answer_and_annotation"),
        default="answer_and_annotation",
        help=(
            "Which TRACE prompt variant to export into the RLVR prompt column "
            "(answer=answer_only, annotation=answer_and_annotation)."
        ),
    )
    parser.add_argument(
        "--image-path-mode",
        choices=("relative", "absolute", "dataset_relative"),
        default="relative",
        help="How to rewrite image paths for the exported RLVR rows.",
    )
    parser.add_argument(
        "--image-storage-mode",
        choices=("path_dict", "embedded_bytes"),
        default="path_dict",
        help="How to store exported images (embedded_bytes is parquet-only and HF-friendly).",
    )
    parser.add_argument(
        "--parquet-cpu-count",
        type=int,
        default=None,
        help="Parquet write CPU count (0=all visible CPUs, default: PyArrow default).",
    )
    parser.add_argument(
        "--max-embedded-image-pixels",
        type=int,
        default=None,
        help=(
            "Resize embedded parquet images to this pixel cap and scale annotation_gt "
            "into exported-image coordinates."
        ),
    )
    args = parser.parse_args()

    result = export_trace_dataset_to_rlvr(
        args.source,
        args.output,
        output_format=args.format,
        prompt_variant=args.prompt_variant,
        image_path_mode=args.image_path_mode,
        image_storage_mode=args.image_storage_mode,
        parquet_cpu_count=args.parquet_cpu_count,
        max_embedded_image_pixels=args.max_embedded_image_pixels,
    )
    print(
        str(result.output_path),
        f"(rows={result.row_count}, format={result.output_format}, prompt_variant={result.prompt_variant}, "
        f"image_path_mode={result.image_path_mode})",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
