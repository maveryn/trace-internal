#!/usr/bin/env python3
"""Strict, reusable answer parsing for TRACE benchmark evaluation."""

from __future__ import annotations

import json
import math
import re
from typing import Any


_CLICK_CALL_RE = re.compile(r"pyautogui\.(?:click|moveTo)\s*\((.*?)\)", flags=re.I | re.S)
_XY_RE = re.compile(
    r"(?<![A-Za-z])x\s*=\s*(-?\d+(?:\.\d+)?)\s*,\s*y\s*=\s*(-?\d+(?:\.\d+)?)",
    flags=re.I,
)
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def last_boxed(text: Any) -> str | None:
    """Return the content of the final balanced ``\\boxed{...}`` expression."""

    raw = _clean_cell(text)
    values: list[str] = []
    for match in re.finditer(r"\\boxed\s*\{", raw):
        start = match.end()
        depth = 1
        pos = start
        while pos < len(raw) and depth:
            if raw[pos] == "{":
                depth += 1
            elif raw[pos] == "}":
                depth -= 1
            pos += 1
        if depth == 0:
            values.append(raw[start : pos - 1])
    return values[-1] if values else None


def clean_final_answer(text: Any) -> str:
    value = _clean_cell(text)
    value = re.sub(r"</?answer>", "", value, flags=re.I).strip()
    value = re.sub(r"^\s*[:：,\-]+\s*", "", value).strip()
    value = value.strip("` \n\t\r").strip("\"'")
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    if len(lines) > 1 and len(lines[0]) <= 160:
        value = lines[0]
    return value.strip().strip("\"'")


def extract_final_answer(value: Any) -> tuple[str, str]:
    """Extract a final answer while preserving the parsing method for audits.

    The deterministic contracts accepted here are the response wrappers used by
    TRACE evaluations. Unwrapped responses are returned unchanged rather than
    guessed from arbitrary reasoning text.
    """

    text = _clean_cell(value)
    if not text:
        return "", "empty"

    tagged = list(re.finditer(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S))
    if tagged:
        return clean_final_answer(tagged[-1].group(1)), "answer_tag"

    boxed = last_boxed(text)
    if boxed is not None:
        return clean_final_answer(boxed), "boxed"

    decoder = json.JSONDecoder()
    json_answers: list[Any] = []
    for match in re.finditer(r"\{", text):
        try:
            payload, _ = decoder.raw_decode(text[match.start() :])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and "answer" in payload:
            json_answers.append(payload["answer"])
    if json_answers:
        return clean_final_answer(json_answers[-1]), "json_answer"

    final_markers = list(
        re.finditer(
            r"(?is)(?:^|\n|\b)(?:the\s+)?(?:final\s+)?answer\s*(?:is|=|:|：)\s*(.+)",
            text,
        )
    )
    if final_markers:
        return clean_final_answer(final_markers[-1].group(1)), "answer_marker"

    return text, "raw"


def extract_click_point(value: Any) -> tuple[float, float] | None:
    """Extract a GUI click point from TRACE and VLMEvalKit answer formats."""

    text = _clean_cell(value)
    if not text:
        return None

    candidates: list[str] = []
    candidates.extend(
        match.group(1)
        for match in re.finditer(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    )
    boxed = last_boxed(text)
    if boxed is not None:
        candidates.append(boxed)
    candidates.append(text)

    for candidate in reversed(candidates):
        calls = list(_CLICK_CALL_RE.finditer(candidate))
        if calls:
            args = calls[-1].group(1)
            xy = _XY_RE.search(args)
            if xy:
                return float(xy.group(1)), float(xy.group(2))
            numbers = _NUMBER_RE.findall(args)
            if len(numbers) >= 2:
                return float(numbers[0]), float(numbers[1])

        xy = _XY_RE.search(candidate)
        if xy:
            return float(xy.group(1)), float(xy.group(2))

        # Common grounding formats: ``[x, y]``, ``[[x, y]]``, or ``(x, y)``.
        pair = re.search(
            r"(?:^|[^\d.\-])(?:\[\s*){0,2}\(?\s*(-?\d+(?:\.\d+)?)\s*,\s*"
            r"(-?\d+(?:\.\d+)?)\s*\)?(?:\s*\]){0,2}(?:$|[^\d.])",
            candidate,
        )
        if pair:
            return float(pair.group(1)), float(pair.group(2))
    return None


def parse_binary_score(value: Any) -> float | None:
    """Parse an explicit binary judge decision; return ``None`` if malformed."""

    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(float(value)):
            return None
        if float(value) in {0.0, 1.0}:
            return float(value)
        return None

    text = _clean_cell(value).lower()
    if text in {"1", "true", "yes", "correct"}:
        return 1.0
    if text in {"0", "false", "no", "incorrect"}:
        return 0.0

    match = re.search(
        r"[\"']?(?:score|judg(?:e)?ment|judge\s+output|correct)[\"']?\s*[:=]\s*([01])\b",
        text,
    )
    if match:
        return float(match.group(1))
    return None
