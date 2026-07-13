#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from PIL import Image

from vlmeval.dataset.chartmuseum import COMPARE_ANSWER_PROMPT

DEFAULT_DATA_ROOT = Path.home() / "LMUData"


def load_existing(path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return {}
    out = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                out[str(row["index"])] = row
    return out


def append_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def extract_answer(text: str) -> str:
    m = re.search(r"<answer>(.*?)</answer>", str(text) + "</answer>", flags=re.S | re.I)
    return m.group(1).strip() if m else str(text or "").strip()


def format_compare_prompt(question: str, answer: str, prediction: str) -> str:
    return (
        COMPARE_ANSWER_PROMPT
        .replace("[QUESTION]", str(question))
        .replace("[ANSWER1]", str(answer))
        .replace("[ANSWER2]", str(prediction))
    )


def parse_judge_output(text: str) -> bool:
    clean = str(text or "").strip().lower()
    if re.search(r"\b(no|false|different|not equivalent)\b", clean):
        return False
    if re.search(r"\b(yes|true|equivalent|same)\b", clean):
        return True
    return clean[:1] == "1"


def load_chartmuseum_rows(split: str, data_root: Path | str = DEFAULT_DATA_ROOT, limit: int | None = None, sample_seed: int = 0):
    del data_root, sample_seed
    from vlmeval.dataset import build_dataset

    dataset = build_dataset(f"ChartMuseum_{split}")
    rows = []
    for _, row in dataset.data.iterrows():
        item = row.to_dict()
        # Route through VLMEvalKit's image dumper so stale or truncated cached PNGs
        # are re-materialized from the TSV before the batched vLLM path opens them.
        image_paths = dataset.dump_image(row)
        if image_paths:
            item["image_path"] = image_paths[0]
        rows.append(item)
    return rows[:limit] if limit is not None else rows


def make_vl_requests(processor: Any, rows: list[dict[str, Any]], max_pixels: int | None = None):
    del max_pixels
    requests = []
    for row in rows:
        image_path = row.get("image_path") or row.get("image")
        content = []
        images = []
        if image_path:
            images.append(Image.open(image_path).convert("RGB"))
            content.append({"type": "image"})
        content.append({"type": "text", "text": str(row.get("question", ""))})
        prompt = processor.apply_chat_template(
            [{"role": "user", "content": content}],
            tokenize=False,
            add_generation_prompt=True,
        )
        req = {"prompt": prompt}
        if images:
            req["multi_modal_data"] = {"image": images}
        requests.append(req)
    return requests
