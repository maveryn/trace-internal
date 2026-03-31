#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, List

from datasets import Dataset, Sequence
from datasets import Image as HFImage
from huggingface_hub import hf_hub_download
from PIL import Image


DEFAULT_DATASET = "VisuLogic/VisuLogic"
DEFAULT_SAMPLE_COUNT = 500
DEFAULT_SEED = 42
DEFAULT_OUT_FILENAME = "visulogic_test_500.parquet"


def _ensure_pil(value: Any) -> Image.Image:
    if isinstance(value, Image.Image):
        img = value
    elif isinstance(value, bytes):
        img = Image.open(BytesIO(value))
    else:
        raise TypeError(f"Unsupported image type: {type(value)}")
    img.load()
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _strip_image_tokens(text: str) -> str:
    if not text:
        return ""
    text = text.replace("<image>", "")
    text = re.sub(r"<image\\d+>", "", text)
    return text.strip()


def _format_problem(question: str, num_images: int) -> str:
    cleaned = _strip_image_tokens(question)
    if num_images <= 0:
        return cleaned
    return f"{'<image>' * num_images}{cleaned}"


def _stringify_answer(answer: Any) -> str:
    if answer is None:
        return ""
    if isinstance(answer, str):
        return answer
    return json.dumps(answer, ensure_ascii=True)


def _load_records(dataset: str) -> list[dict[str, Any]]:
    jsonl_path = hf_hub_download(repo_id=dataset, filename="data.jsonl", repo_type="dataset")
    records: list[dict[str, Any]] = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _open_zip(dataset: str) -> zipfile.ZipFile:
    zip_path = hf_hub_download(repo_id=dataset, filename="images.zip", repo_type="dataset")
    return zipfile.ZipFile(zip_path, "r")


def generate_rows(records: Iterable[dict[str, Any]], zip_file: zipfile.ZipFile) -> Iterable[dict[str, Any]]:
    for example in records:
        image_path = example.get("image_path") or example.get("image") or ""
        if not image_path:
            continue
        with zip_file.open(image_path, "r") as f:
            img = _ensure_pil(f.read())
        question = example.get("question", "")
        problem = _format_problem(question, 1)
        answer = _stringify_answer(example.get("label", ""))
        yield {
            "images": [img],
            "problem": problem,
            "answer": answer,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert VisuLogic to HF parquet format.")
    parser.add_argument("--out", type=str, default="", help="Output directory (default: rlvr/mydata)")
    parser.add_argument("--filename", type=str, default=DEFAULT_OUT_FILENAME, help="Parquet filename")
    parser.add_argument("--dataset", type=str, default=DEFAULT_DATASET, help="HF dataset name")
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT, help="Number of samples (0=all)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Shuffle seed (for sampling)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out) if args.out else root / "mydata"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.filename

    records = _load_records(args.dataset)
    if args.sample_count and args.sample_count < len(records):
        rng = random.Random(args.seed)
        rng.shuffle(records)
        records = records[: args.sample_count]

    with _open_zip(args.dataset) as zip_file:
        ds = Dataset.from_generator(generate_rows, gen_kwargs={"records": records, "zip_file": zip_file})
    ds = ds.cast_column("images", Sequence(HFImage()))
    ds.to_parquet(str(out_path))
    print(f"[done] wrote {len(ds)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
