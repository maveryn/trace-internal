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


DEFAULT_DATASET = "GML-FMGroup/VisNumBench"
DEFAULT_SPLIT = "train"
DEFAULT_SAMPLE_COUNT = 500
DEFAULT_SEED = 42
DEFAULT_OUT_FILENAME = "visnumbench_val_500.parquet"


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


def _extract_images(example: dict[str, Any]) -> List[Image.Image]:
    for key in ("image", "images", "img"):
        if key in example:
            return _normalize_images(example[key])
    return []


def _strip_image_tokens(text: str) -> str:
    if not text:
        return ""
    text = text.replace("<image>", "")
    text = re.sub(r"<image\\d+>", "", text)
    return text.strip()


def _parse_candidates(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, dict):
        # Some datasets pack options under nested keys.
        for key in ("candidates", "options", "choices"):
            if key in raw:
                return _parse_candidates(raw[key])
        return []
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
        # Parse compact MCQ strings like:
        # "(a) ... (b) ... (c) ... (d) ... (e) ..."
        option_matches = re.findall(
            r"\(\s*[A-Za-z]\s*\)\s*(.*?)(?=\s*\(\s*[A-Za-z]\s*\)\s*|$)",
            text,
            flags=re.DOTALL,
        )
        if option_matches:
            return [opt.strip() for opt in option_matches if opt.strip()]
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return lines
    return []


def _format_problem(prompt: str, num_images: int, candidates: list[str]) -> str:
    cleaned = _strip_image_tokens(prompt)
    if candidates:
        labeled = [f"{chr(65 + i)}. {opt}" for i, opt in enumerate(candidates)]
        cleaned = (
            f"{cleaned}\nOptions:\n"
            + "\n".join(labeled)
            + "\nPlease select the correct answer from the options above."
        )
    if num_images <= 0:
        return cleaned
    return f"{'<image>' * num_images}{cleaned}"


def _coerce_index(raw: Any, num_candidates: int) -> int | None:
    if num_candidates <= 0:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        if 0 <= raw < num_candidates:
            return raw
        if 1 <= raw <= num_candidates:
            return raw - 1
        return None
    if isinstance(raw, float) and raw.is_integer():
        return _coerce_index(int(raw), num_candidates)
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        if text.isdigit():
            return _coerce_index(int(text), num_candidates)
        match = re.match(r"^\(?([A-Za-z])[\)\.\:]?$", text)
        if match:
            idx = ord(match.group(1).upper()) - ord("A")
            if 0 <= idx < num_candidates:
                return idx
    return None


def _stringify_answer(answer: Any, candidates: list[str]) -> str:
    idx = _coerce_index(answer, len(candidates))
    if idx is not None:
        return candidates[idx]
    if isinstance(answer, str):
        text = answer.strip()
        if not text:
            return ""
        if text in candidates:
            return text
        # Map answers like "A) choice_text" to the candidate indexed by letter.
        leading_letter = re.match(r"^\s*\(?([A-Za-z])\)?[\)\.\:]\s*", text)
        if leading_letter:
            idx = ord(leading_letter.group(1).upper()) - ord("A")
            if 0 <= idx < len(candidates):
                return candidates[idx]
        return text
    if answer is None:
        return ""
    return json.dumps(answer, ensure_ascii=True)


def generate_rows(dataset: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    for example in dataset:
        images = _extract_images(example)
        question = (
            example.get("question")
            or example.get("prompt")
            or example.get("query")
            or ""
        )
        candidates = _parse_candidates(
            example.get("candidates")
            or example.get("choices")
            or example.get("options")
            or example.get("option")
        )
        problem = _format_problem(question, len(images), candidates)
        answer = _stringify_answer(
            example.get("answer") if "answer" in example else example.get("label"),
            candidates,
        )
        yield {
            "images": images,
            "problem": problem,
            "answer": answer,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert VisNumBench to HF parquet format.")
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
