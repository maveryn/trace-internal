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
        choices=("active", "answer_only", "answer_and_evidence"),
        default="answer_and_evidence",
        help="Which TRACE prompt variant to export into the RLVR prompt column.",
    )
    parser.add_argument(
        "--image-path-mode",
        choices=("relative", "absolute", "dataset_relative"),
        default="relative",
        help="How to rewrite image paths for the exported RLVR rows.",
    )
    args = parser.parse_args()

    result = export_trace_dataset_to_rlvr(
        args.source,
        args.output,
        output_format=args.format,
        prompt_variant=args.prompt_variant,
        image_path_mode=args.image_path_mode,
    )
    print(
        str(result.output_path),
        f"(rows={result.row_count}, format={result.output_format}, prompt_variant={result.prompt_variant}, "
        f"image_path_mode={result.image_path_mode})",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
