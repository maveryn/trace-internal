#!/usr/bin/env python3
"""Prepare a dataset-only CharXiv reasoning preview for the benchmark app."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = REPO_ROOT / "runs" / "external_benchmarks" / "qwen25vl7b" / "20260522T062435Z"
DEFAULT_DATASET_ID = "princeton-nlp/CharXiv"
DEFAULT_BENCHMARK = "charxiv_reasoning"


def main() -> None:
    args = _parse_args()
    run_root = args.run_root.resolve()
    bench_dir = run_root / args.benchmark
    image_dir = bench_dir / "images"
    sample_file = bench_dir / f"{args.benchmark}_{args.split}_samples.jsonl"

    if bench_dir.exists() and not args.overwrite:
        raise SystemExit(f"{bench_dir} already exists; pass --overwrite to refresh it")

    from datasets import load_dataset

    dataset = load_dataset(args.dataset_id, split=args.split)
    total_rows = len(dataset)
    limit = total_rows if args.max_samples is None else min(int(args.max_samples), total_rows)

    bench_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for index in range(limit):
        row = dataset[index]
        question = str(row.get("reasoning_q") or "").strip()
        answer = str(row.get("reasoning_a") or "").strip()
        if not question or not answer:
            continue

        image = row["image"].convert("RGB")
        image_name = f"{args.benchmark}_{args.split}_{index:05d}.jpg"
        image_path = image_dir / image_name
        image.save(image_path, format="JPEG", quality=args.jpeg_quality, optimize=True)

        doc_id = f"{args.split}_{index:05d}"
        source = {
            "dataset_id": args.dataset_id,
            "split": args.split,
            "row_index": index,
            "category": row.get("category"),
            "year": row.get("year"),
            "original_id": row.get("original_id"),
            "original_figure_path": row.get("original_figure_path"),
            "figure_path": row.get("figure_path"),
            "num_subplots": row.get("num_subplots"),
            "subplot_row": row.get("subplot_row"),
            "subplot_col": row.get("subplot_col"),
            "subplot_loc": row.get("subplot_loc"),
            "reasoning_q_source": row.get("reasoning_q_source"),
            "reasoning_a_type": row.get("reasoning_a_type"),
        }
        rows.append(
            {
                "doc_id": doc_id,
                "id": doc_id,
                "input": question,
                "question": question,
                "target": answer,
                "filtered_resps": [],
                "prediction": "",
                "response": "",
                "image": f"images/{image_name}",
                "doc_hash": _stable_hash(json.dumps({"q": question, "a": answer, "source": source}, sort_keys=True)),
                "preview_mode": "dataset_only",
                "source": source,
            }
        )

    with sample_file.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "benchmark": args.benchmark,
        "display": args.display,
        "model_id": "dataset-preview/no-model-response",
        "datetime": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "mode": "dataset_only_preview",
        "dataset_id": args.dataset_id,
        "dataset_split": args.split,
        "sample_file": sample_file.name,
        "sample_count": len(rows),
        "source_row_count": total_rows,
        "max_samples": args.max_samples,
        "image_format": "jpeg",
        "license": "cc-by-sa-4.0",
    }
    (bench_dir / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (bench_dir / "dataset_preview_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {len(rows)} samples")
    print(f"benchmark: {bench_dir}")
    print(f"samples: {sample_file}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--split", default="validation")
    parser.add_argument("--benchmark", default=DEFAULT_BENCHMARK)
    parser.add_argument("--display", default="CharXiv Reasoning")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--jpeg-quality", type=int, default=95)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    main()
