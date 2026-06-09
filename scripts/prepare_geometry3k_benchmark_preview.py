#!/usr/bin/env python3
"""Prepare a dataset-only Geometry3K preview for the benchmark app."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageOps


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = REPO_ROOT / "runs" / "external_benchmarks" / "qwen25vl7b" / "20260522T062435Z"
DEFAULT_DATASET_ID = "hiyouga/geometry3k"
DEFAULT_BENCHMARK = "geometry3k"


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
        problem = str(row.get("problem") or "").strip()
        answer = str(row.get("answer") or "").strip()
        images = [image for image in (row.get("images") or []) if image is not None]
        if not problem or not answer or not images:
            continue

        prompt = _format_prompt(problem)
        image_name = f"{args.benchmark}_{args.split}_{index:05d}.png"
        output_image_path = image_dir / image_name
        preview_image = _compose_preview_image(images)
        preview_image.save(output_image_path, format="PNG", optimize=True)

        source = {
            "dataset_id": args.dataset_id,
            "split": args.split,
            "row_index": index,
            "image_count": len(images),
            "original_problem": problem,
        }
        doc_id = f"{args.split}_{index:05d}"
        rows.append(
            {
                "doc_id": doc_id,
                "id": doc_id,
                "input": prompt,
                "question": prompt,
                "target": answer,
                "answer": answer,
                "filtered_resps": [],
                "prediction": "",
                "response": "",
                "image": f"images/{image_name}",
                "doc_hash": _stable_hash(
                    json.dumps(
                        {
                            "problem": problem,
                            "answer": answer,
                            "source": source,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                ),
                "preview_mode": "dataset_only",
                "category": "Geometry3K",
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
        "image_format": "png",
    }
    (bench_dir / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (bench_dir / "dataset_preview_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {len(rows)} samples")
    print(f"benchmark: {bench_dir}")
    print(f"samples: {sample_file}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--split", default="test")
    parser.add_argument("--benchmark", default=DEFAULT_BENCHMARK)
    parser.add_argument("--display", default="Geometry3K")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def _format_prompt(problem: str) -> str:
    text = str(problem or "").replace("<image>", " ").strip()
    return " ".join(text.split())


def _compose_preview_image(images: Sequence[Image.Image]) -> Image.Image:
    converted = [_white_background(image) for image in images]
    if len(converted) == 1:
        return converted[0]

    margin = 18
    label_height = 22
    width = max(image.width for image in converted) + (2 * margin)
    height = margin + sum(image.height + label_height + margin for image in converted)
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    y = margin
    for index, image in enumerate(converted, start=1):
        draw.text((margin, y), f"Image {index}", fill=(40, 40, 40))
        y += label_height
        x = (width - image.width) // 2
        canvas.paste(image, (x, y))
        y += image.height + margin
    return canvas


def _white_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    background = Image.new("RGBA", rgba.size, "white")
    background.alpha_composite(rgba)
    return background.convert("RGB")


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    main()
