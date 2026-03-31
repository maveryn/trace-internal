#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from datasets import Dataset, Sequence, load_dataset
from datasets import Image as HFImage
from huggingface_hub import hf_hub_download
from PIL import Image


DEFAULT_DATASET = "MMVP/MMVP"
DEFAULT_SPLIT = "train"
DEFAULT_QUESTIONS_FILE = "Questions.csv"
DEFAULT_OUT_FILENAME = "mmvp_300.parquet"


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
    # Always convert to drop any filename/path metadata so bytes are stored in parquet.
    return img.convert("RGB")


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


def _parse_options(options_raw: str) -> List[Tuple[str, str]]:
    matches = re.findall(
        r"\(\s*([A-Za-z])\s*\)\s*(.*?)(?=\s*\(\s*[A-Za-z]\s*\)\s*|$)",
        options_raw or "",
        flags=re.DOTALL,
    )
    return [(label.upper(), text.strip()) for label, text in matches if text.strip()]


def _format_problem(prompt: str, num_images: int, options: List[Tuple[str, str]]) -> str:
    cleaned = _strip_image_tokens(prompt)
    lines = [f"Question: {cleaned}"]
    if options:
        lines.append("Options:")
        for label, text in options:
            lines.append(f"{label}. {text}")
        lines.append("Please select the correct answer from the options above.")
    formatted = "\n".join(lines)
    if num_images <= 0:
        return formatted
    return f"{'<image>' * num_images}{formatted}"


def _answer_from_options(correct_raw: str, options: List[Tuple[str, str]]) -> str:
    if not correct_raw:
        return ""
    match = re.search(r"\(\s*([a-zA-Z])\s*\)", correct_raw)
    if not match:
        cleaned = correct_raw.strip()
        if not cleaned:
            return ""
        upper = cleaned.upper()
        if upper in {"A", "B", "C", "D", "E"}:
            return upper
        for opt_label, opt_text in options:
            if cleaned == opt_text:
                return opt_label
        return cleaned
    label = match.group(1).upper()
    return label


def _load_questions(repo_id: str, filename: str) -> Dict[str, Dict[str, str]]:
    path = hf_hub_download(repo_id=repo_id, filename=filename, repo_type="dataset")
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    mapping: Dict[str, Dict[str, str]] = {}
    for row in rows:
        idx = str(row.get("Index", "")).strip()
        if not idx:
            continue
        mapping[idx] = {
            "question": row.get("Question", "") or "",
            "options": row.get("Options", "") or "",
            "answer": row.get("Correct Answer", "") or "",
        }
    return mapping


def _extract_index(image: Image.Image) -> str:
    filename = getattr(image, "filename", "") or ""
    if filename:
        return Path(filename).stem
    return ""


def generate_rows(dataset: Iterable[dict[str, Any]], qa_map: Dict[str, Dict[str, str]]) -> Iterable[dict[str, Any]]:
    for example in dataset:
        raw_image = example.get("image")
        idx = ""
        if isinstance(raw_image, (list, tuple)) and raw_image:
            idx = _extract_index(raw_image[0])
        elif raw_image is not None:
            idx = _extract_index(raw_image)
        images = _normalize_images(raw_image)
        qa = qa_map.get(idx)
        if qa is None:
            continue
        options = _parse_options(qa["options"])
        problem = _format_problem(qa["question"], len(images), options)
        answer = _answer_from_options(qa["answer"], options)
        yield {
            "images": images,
            "problem": problem,
            "answer": answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=True),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert MMVP to HF parquet format.")
    parser.add_argument("--out", type=str, default="", help="Output directory (default: rlvr/mydata)")
    parser.add_argument("--filename", type=str, default=DEFAULT_OUT_FILENAME, help="Parquet filename")
    parser.add_argument("--dataset", type=str, default=DEFAULT_DATASET, help="HF dataset name")
    parser.add_argument("--split", type=str, default=DEFAULT_SPLIT, help="HF split to use")
    parser.add_argument("--questions-file", type=str, default=DEFAULT_QUESTIONS_FILE, help="Questions CSV in repo")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out) if args.out else root / "mydata"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.filename

    qa_map = _load_questions(args.dataset, args.questions_file)
    dataset = load_dataset(args.dataset, split=args.split)

    ds = Dataset.from_generator(generate_rows, gen_kwargs={"dataset": dataset, "qa_map": qa_map})
    ds = ds.cast_column("images", Sequence(HFImage()))
    ds.to_parquet(str(out_path))
    print(f"[done] wrote {len(ds)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
