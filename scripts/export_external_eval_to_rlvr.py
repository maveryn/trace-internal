#!/usr/bin/env python3
"""Build external benchmark validation packs for RLVR."""

from __future__ import annotations

import argparse

from benchmark.external_rlvr_validation import export_external_validation_to_rlvr


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build RLVR validation parquet/JSONL files directly from official benchmark sources"
    )
    parser.add_argument(
        "--manifest",
        default="benchmark/configs/external_validation_v1.yaml",
        help="External validation manifest describing the benchmark sources and sampling policy",
    )
    parser.add_argument(
        "--output-root",
        required=True,
        help="Directory that will receive per-benchmark RLVR validation files",
    )
    parser.add_argument(
        "--format",
        choices=("jsonl", "parquet"),
        default=None,
        help="Optional output format override. Defaults to the manifest value.",
    )
    parser.add_argument(
        "--image-path-mode",
        choices=("relative", "absolute", "dataset_relative"),
        default=None,
        help="Optional image path rewrite override when using external image files.",
    )
    parser.add_argument(
        "--image-storage-mode",
        choices=("embedded_bytes", "external_files"),
        default=None,
        help="Optional image storage override. Defaults to standalone embedded bytes for parquet exports.",
    )
    args = parser.parse_args()

    result = export_external_validation_to_rlvr(
        args.manifest,
        output_root=args.output_root,
        output_format=args.format,
        image_path_mode=args.image_path_mode,
        image_storage_mode=args.image_storage_mode,
    )
    print(
        str(result.output_root),
        f"(benchmarks={result.benchmark_count}, rows={result.row_count}, format={result.output_format})",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
