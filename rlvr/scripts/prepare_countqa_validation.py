from __future__ import annotations

import argparse
import json
import math
import os
import random
from io import BytesIO
from pathlib import Path
from typing import Any

from datasets import Dataset, load_dataset
from PIL import Image
from tqdm import tqdm


DATASET_ID = "Jayant-Sravan/CountQA"
BENCHMARK_ID = "countqa"
DEFAULT_SEED = 20260504
DEFAULT_SAMPLE_SIZE = 512
DEFAULT_OUTPUT = Path("rlvr_legacy/dataset/validation/countqa.parquet")
DEFAULT_SYMLINK = Path("rlvr/dataset/validation/countqa.parquet")


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _resize_image_bytes(image: Image.Image, *, max_image_pixels: int | None) -> tuple[bytes, dict[str, Any]]:
    image.load()
    original_width, original_height = image.size
    resized = False
    if max_image_pixels is not None and max_image_pixels > 0:
        pixel_count = int(original_width) * int(original_height)
        if pixel_count > int(max_image_pixels):
            scale = math.sqrt(float(max_image_pixels) / float(pixel_count))
            new_width = max(1, int(original_width * scale))
            new_height = max(1, int(original_height * scale))
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            resized = True
    if image.mode != "RGB":
        image = image.convert("RGB")

    output = BytesIO()
    image.save(output, format="JPEG", quality=95, optimize=True)
    stored_bytes = output.getvalue()
    stored_width, stored_height = image.size

    return stored_bytes, {
        "original_width": int(original_width),
        "original_height": int(original_height),
        "stored_width": int(stored_width),
        "stored_height": int(stored_height),
        "resized": bool(resized),
        "storage_format": "JPEG",
        "jpeg_quality": 95,
    }


def _flatten_qa_indices(dataset) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    for source_index, source_row in enumerate(dataset):
        questions = list(source_row["questions"])
        answers = list(source_row["answers"])
        if len(questions) != len(answers):
            raise ValueError(
                f"CountQA row {source_index} has questions={len(questions)} answers={len(answers)}"
            )
        for qa_index in range(len(questions)):
            pairs.append((int(source_index), int(qa_index)))
    return pairs


def _build_rows(*, sample_size: int, seed: int, max_image_pixels: int | None) -> list[dict[str, Any]]:
    dataset = load_dataset(DATASET_ID, split="test")
    pairs = _flatten_qa_indices(dataset)
    if sample_size > len(pairs):
        raise ValueError(f"sample_size={sample_size} exceeds available CountQA question pairs={len(pairs)}")

    rng = random.Random(seed)
    rng.shuffle(pairs)
    sampled_pairs = pairs[:sample_size]

    image_cache: dict[int, tuple[bytes, dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    for local_index, (source_index, qa_index) in enumerate(tqdm(sampled_pairs, desc="CountQA question rows")):
        source_row = dataset[source_index]
        if source_index not in image_cache:
            image_cache[source_index] = _resize_image_bytes(
                source_row["image"],
                max_image_pixels=max_image_pixels,
            )
        image_bytes, image_info = image_cache[source_index]

        question = str(source_row["questions"][qa_index]).strip()
        answer = str(source_row["answers"][qa_index]).strip()
        uid = f"{BENCHMARK_ID}::test::{source_index:06d}::{qa_index:02d}"
        prompt = f"Question: {question}\n\nAnswer with a single integer."
        metadata = {
            "source_dataset": DATASET_ID,
            "source_split": "test",
            "source_index": int(source_index),
            "qa_index": int(qa_index),
            "question": question,
            "objects": list(source_row["objects"]),
            "categories": list(source_row["categories"]),
            "is_focused": bool(source_row["is_focused"]),
            "full_config": str(source_row["full_config"]),
            "image_info": image_info,
            "sample_seed": int(seed),
            "sample_local_index": int(local_index),
            "sample_size": int(sample_size),
        }
        rows.append(
            {
                "uid": uid,
                "instance_id": uid,
                "benchmark_id": BENCHMARK_ID,
                "source_id": f"test::{source_index:06d}",
                "prompt": prompt,
                "prompt_answer": prompt,
                "prompt_mode": "integer_count",
                "images": [{"bytes": image_bytes}],
                "ground_truth": answer,
                "answer_gt": answer,
                "parser_family": "exact_or_choice",
                "metadata": metadata,
            }
        )
    return rows


def _write_manifest_sidecar(output_path: Path, *, rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    category_counts: dict[str, int] = {}
    answer_counts: dict[str, int] = {}
    resized_count = 0
    focused_count = 0
    unique_source_images: set[int] = set()
    for row in rows:
        metadata = row["metadata"]
        unique_source_images.add(int(metadata["source_index"]))
        if metadata["is_focused"]:
            focused_count += 1
        for category in metadata["categories"]:
            category_key = str(category)
            category_counts[category_key] = category_counts.get(category_key, 0) + 1
        answer = str(row["ground_truth"])
        answer_counts[answer] = answer_counts.get(answer, 0) + 1
        if metadata["image_info"]["resized"]:
            resized_count += 1

    sidecar = {
        "benchmark_id": BENCHMARK_ID,
        "dataset_id": DATASET_ID,
        "file": str(output_path),
        "row_count": len(rows),
        "unique_source_image_count": len(unique_source_images),
        "sample_seed": int(args.seed),
        "sample_size": int(args.sample_size),
        "split": "test",
        "category_counts": category_counts,
        "answer_counts": answer_counts,
        "focused_question_count": int(focused_count),
        "max_image_pixels": args.max_image_pixels,
        "resized_image_count": int(resized_count),
    }
    output_path.with_suffix(".manifest.json").write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Trace-style CountQA validation parquet.")
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--symlink", type=Path, default=DEFAULT_SYMLINK)
    parser.add_argument("--max-image-pixels", type=int, default=1_048_576)
    args = parser.parse_args()

    rows = _build_rows(
        sample_size=int(args.sample_size),
        seed=int(args.seed),
        max_image_pixels=args.max_image_pixels,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    Dataset.from_list(rows).to_parquet(str(args.output))
    _write_manifest_sidecar(args.output, rows=rows, args=args)

    if args.symlink:
        args.symlink.parent.mkdir(parents=True, exist_ok=True)
        if args.symlink.exists() or args.symlink.is_symlink():
            args.symlink.unlink()
        target = os.path.abspath(args.output)
        args.symlink.symlink_to(target)

    print(
        json.dumps(
            {
                "output": str(args.output),
                "symlink": str(args.symlink) if args.symlink else None,
                "rows": len(rows),
                "sidecar": str(args.output.with_suffix(".manifest.json")),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
