#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, List, Tuple

from datasets import Dataset, Sequence, load_dataset
from datasets import Image as HFImage
from PIL import Image


DEFAULT_DATASET = "Jayant-Sravan/CountQA"
DEFAULT_SPLIT = "test"
DEFAULT_SAMPLE_COUNT = 500
DEFAULT_SEED = 42
DEFAULT_OUT_FILENAME = "countqa_test_500.parquet"


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


def _format_problem(prompt: str, num_images: int) -> str:
    cleaned = (prompt or "").replace("<image>", "").strip()
    if num_images <= 0:
        return cleaned
    return f"{'<image>' * num_images}{cleaned}"


def _stringify_answer(answer: Any) -> str:
    if isinstance(answer, str):
        return answer
    return json.dumps(answer, ensure_ascii=True)


def _collect_question_pairs(dataset: Iterable[dict[str, Any]]) -> List[Tuple[int, int]]:
    pairs: List[Tuple[int, int]] = []
    for row_idx, example in enumerate(dataset):
        questions = example.get("questions") or []
        for q_idx in range(len(questions)):
            pairs.append((row_idx, q_idx))
    return pairs


def generate_rows(dataset, pairs: Iterable[Tuple[int, int]]) -> Iterable[dict[str, Any]]:
    for row_idx, q_idx in pairs:
        example = dataset[int(row_idx)]
        questions = example.get("questions") or []
        answers = example.get("answers") or []
        question = questions[q_idx] if q_idx < len(questions) else ""
        answer = answers[q_idx] if q_idx < len(answers) else ""
        images = _normalize_images(example.get("image"))
        problem = _format_problem(question, len(images))
        yield {
            "images": images,
            "problem": problem,
            "answer": _stringify_answer(answer),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert CountQA test split to HF parquet format.")
    parser.add_argument("--out", type=str, default="", help="Output directory (default: rlvr/mydata)")
    parser.add_argument("--filename", type=str, default=DEFAULT_OUT_FILENAME, help="Parquet filename")
    parser.add_argument("--dataset", type=str, default=DEFAULT_DATASET, help="HF dataset name")
    parser.add_argument("--split", type=str, default=DEFAULT_SPLIT, help="HF split to use")
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT, help="Number of questions to sample")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Shuffle seed")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out) if args.out else root / "mydata"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.filename

    dataset = load_dataset(args.dataset, split=args.split)
    pairs = _collect_question_pairs(dataset)
    if not pairs:
        raise RuntimeError("No questions found in dataset")

    if args.sample_count and args.sample_count < len(pairs):
        rng = random.Random(args.seed)
        pairs = rng.sample(pairs, args.sample_count)

    ds = Dataset.from_generator(generate_rows, gen_kwargs={"dataset": dataset, "pairs": pairs})
    ds = ds.cast_column("images", Sequence(HFImage()))
    ds.to_parquet(str(out_path))
    print(f"[done] wrote {len(ds)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
