#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, List

from datasets import Dataset, Sequence, load_dataset
from datasets import Image as HFImage
from PIL import Image


DEFAULT_DATASET = "MathLLMs/MathVision"
DEFAULT_SPLIT = "testmini"
DEFAULT_SAMPLE_COUNT = 0  # 0 = use full split
DEFAULT_SEED = 42
DEFAULT_OUT_FILENAME = "mathvision_testmini.parquet"


def _ensure_pil(value: Any) -> Image.Image:
    if isinstance(value, Image.Image):
        img = value
    elif isinstance(value, bytes):
        img = Image.open(BytesIO(value))
    elif isinstance(value, str):
        img = Image.open(value)
    elif isinstance(value, dict) and "bytes" in value:
        img = Image.open(BytesIO(value["bytes"]))
    else:
        raise TypeError(f"Unsupported image type: {type(value)}")
    img.load()
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _normalize_images(raw: Any) -> List[Image.Image]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        items = raw
    else:
        items = [raw]
    return [_ensure_pil(item) for item in items]


def _strip_image_tokens(text: str) -> str:
    if not text:
        return ""
    text = text.replace("<image>", "")
    text = re.sub(r"<image\\d+>", "", text)
    return text.strip()


def _format_problem(prompt: str, num_images: int, options: list[str]) -> str:
    cleaned = _strip_image_tokens(prompt)
    if options:
        if not all(opt in {"A", "B", "C", "D", "E"} for opt in options):
            labeled = [f"{chr(65 + i)}. {opt}" for i, opt in enumerate(options)]
            cleaned = f"{cleaned}\nOptions:\n" + "\n".join(labeled)
    if num_images <= 0:
        return cleaned
    return f"{'<image>' * num_images}{cleaned}"


def _stringify_answer(answer: Any, options: list[str]) -> str:
    if isinstance(answer, str) and len(answer) == 1 and answer.isalpha():
        idx = ord(answer.upper()) - ord("A")
        if 0 <= idx < len(options):
            return options[idx]
        return answer
    if isinstance(answer, str):
        return answer
    return json.dumps(answer, ensure_ascii=True)


def generate_rows(dataset: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for example in dataset:
        image_field = example.get("decoded_image")
        if image_field is None:
            image_field = example.get("image")
        images = _normalize_images(image_field)
        options = list(example.get("options") or [])
        problem = _format_problem(example.get("question", ""), len(images), options)
        answer = _stringify_answer(example.get("answer", ""), options)
        yield {
            "images": images,
            "problem": problem,
            "answer": answer,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert MathVision testmini to HF parquet format.")
    parser.add_argument("--out", type=str, default="", help="Output directory (default: rlvr/mydata)")
    parser.add_argument("--filename", type=str, default=DEFAULT_OUT_FILENAME, help="Parquet filename")
    parser.add_argument("--dataset", type=str, default=DEFAULT_DATASET, help="HF dataset name")
    parser.add_argument("--split", type=str, default=DEFAULT_SPLIT, help="HF split to use")
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT, help="Number of samples (0=all)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Shuffle seed (for sampling)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out) if args.out else root / "mydata"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.filename

    dataset = load_dataset(args.dataset, split=args.split)
    if args.sample_count and args.sample_count < len(dataset):
        dataset = dataset.shuffle(seed=args.seed).select(range(args.sample_count))

    ds = Dataset.from_generator(generate_rows, gen_kwargs={"dataset": dataset})
    ds = ds.cast_column("images", Sequence(HFImage()))
    ds.to_parquet(str(out_path))
    print(f"[done] wrote {len(ds)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
