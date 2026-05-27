from __future__ import annotations

import argparse
import json
import math
import os
from io import BytesIO
from pathlib import Path
from typing import Any

from datasets import concatenate_datasets, load_dataset
from huggingface_hub import hf_hub_download
from PIL import Image
from tqdm import tqdm


DATASET_ID = "lytang/ChartMuseum"
BENCHMARK_ID = "chartmuseum"
DEFAULT_SEED = 20260504
DEFAULT_SAMPLE_SIZE = 512
DEFAULT_OUTPUT = Path("rlvr_legacy/dataset/validation/chartmuseum.parquet")
DEFAULT_SYMLINK = Path("rlvr/dataset/validation/chartmuseum.parquet")


def _json_default(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _resize_image_bytes(raw_bytes: bytes, *, max_image_pixels: int | None) -> tuple[bytes, dict[str, Any]]:
    with Image.open(BytesIO(raw_bytes)) as image:
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


def _load_pool(splits: tuple[str, ...]):
    loaded = []
    for split in splits:
        dataset = load_dataset(DATASET_ID, split=split)
        dataset = dataset.add_column("_chartmuseum_split", [split] * len(dataset))
        dataset = dataset.add_column("_chartmuseum_source_index", list(range(len(dataset))))
        loaded.append(dataset)
    return loaded[0] if len(loaded) == 1 else concatenate_datasets(loaded)


def _build_rows(
    *,
    sample_size: int,
    seed: int,
    splits: tuple[str, ...],
    max_image_pixels: int | None,
) -> list[dict[str, Any]]:
    pool = _load_pool(splits)
    if sample_size > len(pool):
        raise ValueError(f"sample_size={sample_size} exceeds available ChartMuseum rows={len(pool)}")

    sampled = pool.shuffle(seed=seed).select(range(sample_size))
    rows: list[dict[str, Any]] = []
    for local_index, source_row in enumerate(tqdm(sampled, desc="ChartMuseum rows")):
        image_path = str(source_row["image"])
        local_image_path = Path(
            hf_hub_download(
                repo_id=DATASET_ID,
                repo_type="dataset",
                filename=image_path,
            )
        )
        image_bytes, image_info = _resize_image_bytes(
            local_image_path.read_bytes(),
            max_image_pixels=max_image_pixels,
        )
        source_split = str(source_row["_chartmuseum_split"])
        source_index = int(source_row["_chartmuseum_source_index"])
        source_hash = str(source_row["hash"])
        uid = f"{BENCHMARK_ID}::{source_split}::{source_index:06d}"
        question = str(source_row["question"]).strip()
        answer = str(source_row["answer"]).strip()
        prompt = f"Question: {question}\n\nAnswer concisely."
        metadata = {
            "source_dataset": DATASET_ID,
            "source_split": source_split,
            "source_index": source_index,
            "source_hash": source_hash,
            "source_url": str(source_row["source"]),
            "reasoning_type": str(source_row["reasoning_type"]),
            "image_path": image_path,
            "image_info": image_info,
            "sample_seed": int(seed),
            "sample_local_index": int(local_index),
        }
        rows.append(
            {
                "uid": uid,
                "instance_id": uid,
                "benchmark_id": BENCHMARK_ID,
                "source_id": source_hash,
                "prompt": prompt,
                "prompt_answer": prompt,
                "prompt_mode": "open_answer",
                "images": [{"bytes": image_bytes}],
                "ground_truth": answer,
                "answer_gt": answer,
                "parser_family": "exact_or_choice",
                "metadata": metadata,
            }
        )
    return rows


def _write_manifest_sidecar(output_path: Path, *, rows: list[dict[str, Any]], args: argparse.Namespace) -> None:
    reasoning_counts: dict[str, int] = {}
    split_counts: dict[str, int] = {}
    resized_count = 0
    for row in rows:
        metadata = row["metadata"]
        reasoning_counts[metadata["reasoning_type"]] = reasoning_counts.get(metadata["reasoning_type"], 0) + 1
        split_counts[metadata["source_split"]] = split_counts.get(metadata["source_split"], 0) + 1
        if metadata["image_info"]["resized"]:
            resized_count += 1

    sidecar = {
        "benchmark_id": BENCHMARK_ID,
        "dataset_id": DATASET_ID,
        "file": str(output_path),
        "row_count": len(rows),
        "sample_seed": int(args.seed),
        "splits": list(args.splits),
        "split_counts": split_counts,
        "reasoning_type_counts": reasoning_counts,
        "max_image_pixels": args.max_image_pixels,
        "resized_image_count": int(resized_count),
    }
    output_path.with_suffix(".manifest.json").write_text(
        json.dumps(sidecar, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a TRACE-style ChartMuseum validation parquet.")
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--splits", nargs="+", default=["test", "dev"])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--symlink", type=Path, default=DEFAULT_SYMLINK)
    parser.add_argument("--max-image-pixels", type=int, default=1_048_576)
    args = parser.parse_args()

    rows = _build_rows(
        sample_size=args.sample_size,
        seed=args.seed,
        splits=tuple(str(split) for split in args.splits),
        max_image_pixels=args.max_image_pixels,
    )

    from datasets import Dataset

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
