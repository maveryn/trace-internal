#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import re
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import Dataset, Sequence
from datasets import Image as HFImage
from PIL import Image


DEFAULT_SRC = Path.home() / "LMUData" / "VStarBench.tsv"
DEFAULT_OUT = "vstarbench_test.parquet"


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def _decode_image_b64(value: str) -> Image.Image:
    text = _as_text(value)
    if not text:
        raise ValueError("empty image field")
    text = re.sub(r"^data:image/[^;]+;base64,", "", text.strip(), flags=re.IGNORECASE)
    image_bytes = base64.b64decode(text, validate=False)
    img = Image.open(BytesIO(image_bytes))
    img.load()
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _build_problem(row: pd.Series) -> str:
    question = _as_text(row.get("question"))
    options: list[tuple[str, str]] = []
    for letter in ("A", "B", "C", "D", "E"):
        val = _as_text(row.get(letter))
        if not val or val.lower() == "nan":
            continue
        options.append((letter, val))

    lines = [f"Question: {question}"]
    if options:
        lines.append("Options:")
        lines.extend([f"{letter}. {text}" for letter, text in options])
        lines.append("Please select the correct answer from the options above.")
    return "<image>" + "\n".join(lines)


def _normalize_answer(value: Any) -> str:
    text = _as_text(value).upper()
    m = re.match(r"^\(?([A-Z])[\)\.\:]?$", text)
    if m:
        return m.group(1)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert VStarBench TSV to Tesserae parquet format.")
    parser.add_argument("--src", type=str, default=str(DEFAULT_SRC), help="Input VStarBench.tsv path")
    parser.add_argument("--out-dir", type=str, default="", help="Output directory (default: rlvr/mydata)")
    parser.add_argument("--filename", type=str, default=DEFAULT_OUT, help="Output parquet filename")
    args = parser.parse_args()

    src = Path(args.src).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"source TSV not found: {src}")

    root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else (root / "mydata")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.filename

    df = pd.read_csv(src, sep="\t")

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        image = _decode_image_b64(row.get("image"))
        problem = _build_problem(row)
        answer = _normalize_answer(row.get("answer"))
        rows.append({"images": [image], "problem": problem, "answer": answer})

    ds = Dataset.from_list(rows)
    ds = ds.cast_column("images", Sequence(HFImage()))
    ds.to_parquet(str(out_path))
    print(f"[done] wrote {len(ds)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
