from __future__ import annotations

import argparse
import ast
import json
import math
import os
from io import BytesIO
from pathlib import Path
from typing import Any

from datasets import Dataset, load_dataset
from PIL import Image
from tqdm import tqdm


DATASET_ID = "MMMU/MMMU_Pro"
DATASET_CONFIG = "vision"
BENCHMARK_ID = "mmmu_pro_vision"
DEFAULT_SEED = 20260504
DEFAULT_SAMPLE_SIZE = 512
DEFAULT_OUTPUT = Path("rlvr_legacy/dataset/validation/mmmu_pro_vision.parquet")
DEFAULT_SYMLINK = Path("rlvr/dataset/validation/mmmu_pro_vision.parquet")
DEFAULT_PROMPT = "Please answer with the option letter from the multiple-choice question shown in the image."


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
    image.save(output, format="PNG", optimize=True)
    stored_bytes = output.getvalue()
    stored_width, stored_height = image.size

    return stored_bytes, {
        "original_width": int(original_width),
        "original_height": int(original_height),
        "stored_width": int(stored_width),
        "stored_height": int(stored_height),
        "resized": bool(resized),
    }


def _build_rows(*, sample_size: int | None, seed: int, max_image_pixels: int | None) -> list[dict[str, Any]]:
    pool = load_dataset(DATASET_ID, DATASET_CONFIG, split="test")
    if sample_size is not None and sample_size > len(pool):
        raise ValueError(f"sample_size={sample_size} exceeds available MMMU-Pro vision rows={len(pool)}")
    sampled = pool.shuffle(seed=seed).select(range(sample_size)) if sample_size is not None else pool

    rows: list[dict[str, Any]] = []
    for local_index, source_row in enumerate(tqdm(sampled, desc="MMMU-Pro vision rows")):
        source_id = str(source_row["id"])
        uid = f"{BENCHMARK_ID}::{source_id}"
        answer = str(source_row["answer"]).strip().upper()
        image_bytes, image_info = _resize_image_bytes(
            source_row["image"],
            max_image_pixels=max_image_pixels,
        )
        raw_options = source_row["options"]
        if isinstance(raw_options, str):
            options = list(ast.literal_eval(raw_options))
        else:
            options = list(raw_options)
        metadata = {
            "source_dataset": DATASET_ID,
            "source_config": DATASET_CONFIG,
            "source_split": "test",
            "source_id": source_id,
            "source_index": int(local_index),
            "subject": str(source_row["subject"]),
            "option_count": len(options),
            "options": options,
            "image_info": image_info,
            "sample_seed": int(seed),
            "sample_size": sample_size if sample_size is not None else "all",
            "prompt_style": "mmmu_pro_vision_direct_trace_json",
        }
        rows.append(
            {
                "uid": uid,
                "instance_id": uid,
                "benchmark_id": BENCHMARK_ID,
                "source_id": source_id,
                "prompt": DEFAULT_PROMPT,
                "prompt_answer": DEFAULT_PROMPT,
                "prompt_mode": "multiple_choice_image_question",
                "images": [{"bytes": image_bytes}],
                "ground_truth": answer,
                "answer_gt": answer,
                "parser_family": "exact_or_choice",
                "metadata": metadata,
            }
        )
    return rows


def _write_manifest_sidecar(output_path: Path, *, rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    subject_counts: dict[str, int] = {}
    option_count_counts: dict[str, int] = {}
    resized_count = 0
    for row in rows:
        metadata = row["metadata"]
        subject = str(metadata["subject"])
        option_count = str(metadata["option_count"])
        subject_counts[subject] = subject_counts.get(subject, 0) + 1
        option_count_counts[option_count] = option_count_counts.get(option_count, 0) + 1
        if metadata["image_info"]["resized"]:
            resized_count += 1

    sidecar = {
        "benchmark_id": BENCHMARK_ID,
        "dataset_id": DATASET_ID,
        "dataset_config": DATASET_CONFIG,
        "file": str(output_path),
        "row_count": len(rows),
        "sample_seed": int(args.seed),
        "sample_size": args.sample_size if args.sample_size > 0 else "all",
        "split": "test",
        "subject_counts": subject_counts,
        "option_count_counts": option_count_counts,
        "max_image_pixels": args.max_image_pixels,
        "resized_image_count": int(resized_count),
    }
    output_path.with_suffix(".manifest.json").write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Trace-style MMMU-Pro vision validation parquet.")
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE, help="Use <=0 to keep all rows.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--symlink", type=Path, default=DEFAULT_SYMLINK)
    parser.add_argument("--max-image-pixels", type=int, default=1_048_576)
    args = parser.parse_args()

    sample_size = int(args.sample_size)
    rows = _build_rows(
        sample_size=sample_size if sample_size > 0 else None,
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
