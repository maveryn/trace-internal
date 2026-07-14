from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

from vlmeval.smp import LMUDataRoot, dump, get_intermediate_file_path, load
from .image_base import ImageBaseDataset


_NUMBER_PATTERN = re.compile(
    r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|[-+]?\d*\.\d+"
)


def _last_boxed(text: str) -> str | None:
    start = 0
    last = None
    while True:
        idx = text.find("\\boxed{", start)
        if idx < 0:
            return last
        i = idx + len("\\boxed{")
        depth = 1
        j = i
        while j < len(text) and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        if depth == 0:
            last = text[i:j - 1].strip()
            start = j
        else:
            return last


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_final_answer(value: Any) -> str:
    text = _coerce_text(value)
    boxed = _last_boxed(text)
    if boxed:
        return boxed.strip()
    answer_tag = re.search(r"<answer>(.*?)</answer>", text, flags=re.I | re.S)
    if answer_tag:
        return answer_tag.group(1).strip()
    json_match = re.search(r"\{.*\"answer\"\s*:\s*(.+?)\}", text, flags=re.S)
    if json_match:
        return json_match.group(1).strip().strip("\"'")
    matches = list(
        re.finditer(
            r"\b(?:final\s+answer|answer)\b\s*(?:is|=|:|：)?\s*(.+)",
            text,
            flags=re.I | re.S,
        )
    )
    if matches:
        return matches[-1].group(1).strip().splitlines()[0].strip()
    return text


def _normalize_text(value: Any) -> str:
    return _coerce_text(value).lower()


def _clean_number_text(text: str) -> str:
    text = text.strip()
    text = text.strip("$€£¥")
    text = text.replace(",", "")
    if text.endswith("."):
        text = text[:-1].strip()
    return text


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = _clean_number_text(_coerce_text(value))
    if not text:
        return None
    try:
        if text.endswith("%"):
            return float(text[:-1].strip()) / 100.0
        return float(text)
    except ValueError:
        return None


def _extract_numeric_value(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = _clean_number_text(_coerce_text(value))
    if not text:
        return None
    match = _NUMBER_PATTERN.search(text)
    if not match:
        return None
    candidate = match.group(0).replace(",", "")
    if candidate in {"", "+", "-"}:
        return None
    try:
        return float(candidate)
    except ValueError:
        return None


def _within_tolerance(value: float, reference: float, max_relative_change: float) -> bool:
    if reference == 0.0:
        return abs(value) <= max_relative_change
    return abs(value - reference) / abs(reference) <= max_relative_change


def _apply_relaxed_tolerance(
    prediction: Any,
    target: Any,
    max_relative_change: float = 0.05,
) -> bool:
    pred_text = _clean_number_text(_coerce_text(prediction))
    target_text = _clean_number_text(_coerce_text(target))
    if not pred_text or not target_text:
        return False

    pred_has_percent = pred_text.endswith("%")
    target_has_percent = target_text.endswith("%")
    pred_float = _to_float(pred_text)
    target_float = _to_float(target_text)

    if pred_float is not None and target_float is not None:
        if _within_tolerance(pred_float, target_float, max_relative_change):
            return True
        if pred_has_percent and not target_has_percent:
            return _within_tolerance(pred_float * 100.0, target_float, max_relative_change)
        if target_has_percent and not pred_has_percent:
            return _within_tolerance(pred_float, target_float * 100.0, max_relative_change)
        if not pred_has_percent and not target_has_percent and 0 < pred_float < 1:
            return _within_tolerance(pred_float * 100.0, target_float, max_relative_change)
        if not pred_has_percent and not target_has_percent and 0 < target_float < 1:
            return _within_tolerance(pred_float, target_float * 100.0, max_relative_change)

    return pred_text.lower() == target_text.lower()


def _compare_numeric_with_tolerance(
    prediction: Any,
    target: Any,
    max_relative_change: float = 0.05,
) -> bool:
    target_number = _extract_numeric_value(target)
    if target_number is None:
        return False
    pred_number = _extract_numeric_value(prediction)
    if pred_number is None:
        return False
    return _within_tolerance(pred_number, target_number, max_relative_change)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n", ""}:
        return False
    return bool(value)


def _save_image(image: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    if hasattr(image, "convert"):
        image = image.convert("RGB")
    image.save(path)


def _load_cached_with_images(data_path: Path) -> pd.DataFrame | None:
    frame = load(str(data_path))
    if "image_path" not in frame:
        return frame
    image_paths = [Path(str(path)) for path in frame["image_path"].dropna().unique()]
    missing = [path for path in image_paths if not path.exists()]
    if missing:
        print(
            f"[evochart] rebuilding {data_path.name}: "
            f"{len(missing)} cached image paths are missing"
        )
        return None
    return frame


def score_prediction(prediction: Any, answer: Any, is_clear: Any) -> float:
    final_answer = _extract_final_answer(prediction)
    if _as_bool(is_clear):
        if _normalize_text(final_answer) == _normalize_text(answer):
            return 1.0
        answer_number = _extract_numeric_value(answer)
        pred_number = _extract_numeric_value(final_answer) if answer_number is not None else None
        return float(
            answer_number is not None
            and pred_number is not None
            and abs(pred_number - answer_number) <= 1e-6
        )
    return float(
        _apply_relaxed_tolerance(final_answer, answer)
        or _compare_numeric_with_tolerance(final_answer, answer)
    )


class EvoChart(ImageBaseDataset):
    TYPE = "VQA"
    DATASET_URL = {
        "EvoChart": "",
        "EvoChart_Qwen25_ZS": "",
        "EvoChart_Qwen3_ZS": "",
        "EvoChart_reasoning": "",
    }
    DATASET_MD5 = {}
    HF_DATASET = "gsarch/EvoChart-QA"
    HF_SPLIT = "train"

    def load_data(self, dataset):
        root = Path(LMUDataRoot())
        data_path = root / f"{dataset}.tsv"
        if data_path.exists() and not os.environ.get("TRACE_FORCE_REBUILD_LOCAL_VLMEVAL"):
            cached = _load_cached_with_images(data_path)
            if cached is not None:
                return cached

        from datasets import load_dataset

        hf = load_dataset(self.HF_DATASET, split=self.HF_SPLIT, token=os.environ.get("HF_TOKEN"))
        image_root = root / "images" / dataset
        rows = []
        for idx, example in enumerate(hf):
            image_path = image_root / f"{idx}.png"
            _save_image(example["image"], image_path)
            rows.append(
                {
                    "index": str(idx),
                    "question": str(example.get("question", "")).strip(),
                    "answer": str(example.get("answer", "")).strip(),
                    "image_path": str(image_path),
                    "attribute": str(example.get("attribute", "")),
                    "is_clear": bool(example.get("is_clear", True)),
                    "chart_type": str(example.get("chart_type", "")),
                }
            )
        frame = pd.DataFrame(rows)
        dump(frame, str(data_path))
        return frame

    def build_prompt(self, line):
        msgs = super().build_prompt(line)
        assert msgs[-1]["type"] == "text"
        question = str(msgs[-1]["value"]).strip()
        if self.dataset_name == "EvoChart_Qwen25_ZS":
            question += "\nAnswer the question with a single word."
        elif self.dataset_name == "EvoChart_Qwen3_ZS":
            question += "\nAnswer the question using a single word or phrase."
        msgs[-1]["value"] = question
        return msgs

    def evaluate(self, eval_file, **judge_kwargs):
        del judge_kwargs
        data = load(eval_file)
        scores = []
        extracted = []
        for _, row in data.iterrows():
            final_answer = _extract_final_answer(row.get("prediction", ""))
            extracted.append(final_answer)
            scores.append(score_prediction(final_answer, row.get("answer", ""), row.get("is_clear", True)))
        data["eval_pred"] = extracted
        data["eval_score"] = scores
        dump(data, get_intermediate_file_path(eval_file, "_results"))

        rows = [
            {"split": "Overall", "tot": len(data), "hit": sum(scores), "acc": sum(scores) / len(scores) * 100 if scores else 0.0}
        ]
        for field in ("chart_type", "attribute"):
            if field not in data:
                continue
            for name, group in data.groupby(field, dropna=False):
                vals = [float(x) for x in group["eval_score"].tolist()]
                rows.append(
                    {
                        "split": f"{field}:{name}",
                        "tot": len(vals),
                        "hit": sum(vals),
                        "acc": sum(vals) / len(vals) * 100 if vals else 0.0,
                    }
                )
        result = pd.DataFrame(rows)
        dump(result, get_intermediate_file_path(eval_file, "_acc", "csv"))
        return result
