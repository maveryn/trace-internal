#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, List

from datasets import Dataset, Sequence, load_dataset
from datasets import Image as HFImage
from PIL import Image


DEFAULT_DATASET = "lscpku/LogicVista"
DEFAULT_SPLIT = "test"
DEFAULT_OUT_FILENAME = "logicvista_test.parquet"


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
    return img.convert("RGB")


def _normalize_images(raw: Any) -> List[Image.Image]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        items = raw
    else:
        items = [raw]
    return [_ensure_pil(item) for item in items]


def _format_problem(prompt: str, num_images: int) -> str:
    cleaned = (prompt or "").replace("<image>", "").strip()
    if num_images <= 0:
        return cleaned
    return f"{'<image>' * num_images}{cleaned}"


def _stringify_answer(answer: Any) -> str:
    if isinstance(answer, str):
        return answer
    return json.dumps(answer, ensure_ascii=True)


def generate_rows(dataset: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for example in dataset:
        images = _normalize_images(example.get("image"))
        problem = _format_problem(example.get("question", ""), len(images))
        answer = _stringify_answer(example.get("answer", ""))
        yield {
            "images": images,
            "problem": problem,
            "answer": answer,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert LogicVista test split to HF parquet format.")
    parser.add_argument("--out", type=str, default="", help="Output directory (default: rlvr/mydata)")
    parser.add_argument("--filename", type=str, default=DEFAULT_OUT_FILENAME, help="Parquet filename")
    parser.add_argument("--dataset", type=str, default=DEFAULT_DATASET, help="HF dataset name")
    parser.add_argument("--split", type=str, default=DEFAULT_SPLIT, help="HF split to use")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out) if args.out else root / "mydata"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.filename

    dataset = load_dataset(args.dataset, split=args.split)
    ds = Dataset.from_generator(generate_rows, gen_kwargs={"dataset": dataset})
    ds = ds.cast_column("images", Sequence(HFImage()))
    ds.to_parquet(str(out_path))
    print(f"[done] wrote {len(ds)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
