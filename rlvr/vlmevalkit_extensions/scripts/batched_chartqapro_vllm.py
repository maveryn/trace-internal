#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
from typing import Any

from vlmeval.dataset.utils.chartqapro import evaluate_predictions_chartqapro


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


def extract_prediction(raw: str, question_type: str = "") -> str:
    del question_type
    text = str(raw or "").strip()
    boxed = _last_boxed(text)
    if boxed:
        return boxed
    answer_tag = re.search(r"<answer>(.*?)</answer>", text, flags=re.I | re.S)
    if answer_tag:
        return answer_tag.group(1).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "answer" in obj:
            return str(obj["answer"]).strip()
    except Exception:
        pass
    matches = list(re.finditer(r"\b(?:final\s+answer|answer)\b\s*[:：]?\s*(.+)", text, flags=re.I | re.S))
    if matches:
        tail = matches[-1].group(1).strip()
        return tail.splitlines()[0].strip()
    return text


def _literal(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return ast.literal_eval(value)
        except Exception:
            return value
    return value


def evaluate_rows(rows: list[dict[str, Any]], prediction_key: str = "prediction") -> dict[str, Any]:
    ans_list = []
    for row in rows:
        ans_list.append(
            {
                "Answer": _literal(row.get("answer")),
                "Question Type": row.get("question_type", ""),
                "Year": _literal(row.get("year")),
                "prediction": row.get(prediction_key, ""),
            }
        )
    raw_scores = evaluate_predictions_chartqapro(ans_list)
    return {str(k): float(v) if isinstance(v, (int, float)) else v for k, v in raw_scores.items()}
