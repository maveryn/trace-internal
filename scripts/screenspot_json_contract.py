#!/usr/bin/env python3
"""Shared no-system JSON point contract for the ScreenSpot benchmark family."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Iterable


SCREENSPOT_JSON_PROMPT_CONTRACT = "screenspot-json-point-no-system-v1"
SCREENSPOT_JSON_PREDICTION_CONTRACT = "screenspot-json-point-to-vlmevalkit-xy-v1"
SCREENSPOT_JSON_KEYS = frozenset({"screenspot", "screenspotpro", "screenspot_v2"})
# Pinned VLMEvalKit maps unparseable text to (0, 0), which can accidentally hit
# a target touching the origin. This explicit out-of-frame point preserves the
# official parser and guarantees an unresolved response is scored incorrect.
SCREENSPOT_JSON_UNRESOLVED = "pyautogui.click(x=1000000000000, y=1000000000000)"


@dataclass(frozen=True)
class ScreenSpotPointParse:
    status: str
    value: tuple[float, float] | None
    method: str
    candidates: tuple[tuple[float, float], ...]


def is_screenspot_json_key(key: Any) -> bool:
    value = str(key or "")
    return value in SCREENSPOT_JSON_KEYS or value.startswith("screenspotpro_")


def uses_screenspot_json_contract(spec: Any) -> bool:
    """Return whether a benchmark spec belongs to the scoped ScreenSpot family."""

    return bool(
        is_screenspot_json_key(getattr(spec, "key", ""))
        or str(getattr(spec, "aggregate_group", "")) == "screenspotpro"
    )


def screenspot_json_prompt(row: Any) -> str:
    """Render the VERO reasoning-evaluation point prompt without a system message."""

    values = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    instruction = next(
        (
            str(values[key]).strip()
            for key in ("question", "instruction", "description")
            if key in values and values[key] is not None and str(values[key]).strip()
        ),
        "",
    )
    if not instruction:
        raise ValueError("ScreenSpot JSON prompt requires question, instruction, or description")
    terminal = instruction[-1] if instruction[-1] in ".?!" else "."
    instruction = instruction.rstrip(".?!").rstrip() + terminal
    return (
        f"Provide the point for the command: {instruction} "
        'Output the point in a JSON array format: [{"point_2d": [x, y]}].'
    )


def apply_screenspot_json_prompt(spec: Any, row: Any, struct: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep official media entries and replace only ScreenSpot-family prompt text."""

    items = list(struct)
    if not uses_screenspot_json_contract(spec):
        return items
    media = [item for item in items if item.get("type") in {"image", "video"}]
    if not media:
        raise ValueError("ScreenSpot JSON prompt requires at least one official media item")
    return [*media, {"type": "text", "value": screenspot_json_prompt(row)}]


def _decoded_json_values(text: str) -> Iterable[Any]:
    """Yield non-overlapping JSON values embedded in a model response."""

    decoder = json.JSONDecoder()
    position = 0
    while position < len(text):
        starts = [offset for token in ("[", "{") if (offset := text.find(token, position)) >= 0]
        if not starts:
            return
        start = min(starts)
        try:
            value, end = decoder.raw_decode(text[start:])
        except ValueError:
            position = start + 1
            continue
        yield value
        position = start + end


def _point_from_object(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, dict) or set(value) != {"point_2d"}:
        return None
    point = value["point_2d"]
    if not isinstance(point, list) or len(point) != 2:
        return None
    if any(isinstance(coordinate, bool) or not isinstance(coordinate, (int, float)) for coordinate in point):
        return None
    parsed = (float(point[0]), float(point[1]))
    if not all(math.isfinite(coordinate) and coordinate >= 0 for coordinate in parsed):
        return None
    return parsed


def parse_screenspot_json_point(value: Any) -> ScreenSpotPointParse:
    """Resolve one unambiguous point from strict ``[{"point_2d": [x, y]}]`` JSON."""

    text = "" if value is None else str(value).strip()
    if not text:
        return ScreenSpotPointParse("invalid", None, "empty", ())

    candidates: list[tuple[float, float]] = []
    malformed_schema = False
    for decoded in _decoded_json_values(text):
        if not isinstance(decoded, list):
            if isinstance(decoded, dict) and "point_2d" in decoded:
                malformed_schema = True
            continue
        point_bearing = any(isinstance(item, dict) and "point_2d" in item for item in decoded)
        if not point_bearing:
            continue
        for item in decoded:
            if not isinstance(item, dict) or "point_2d" not in item:
                malformed_schema = True
                continue
            point = _point_from_object(item)
            if point is None:
                malformed_schema = True
            else:
                candidates.append(point)

    ordered_unique = tuple(dict.fromkeys(candidates))
    if malformed_schema:
        return ScreenSpotPointParse("invalid", None, "malformed_json_point_2d", ordered_unique)
    if len(ordered_unique) > 1:
        return ScreenSpotPointParse("ambiguous", None, "conflicting_json_point_2d", ordered_unique)
    if not ordered_unique:
        return ScreenSpotPointParse("invalid", None, "missing_json_point_2d", ())
    return ScreenSpotPointParse("resolved", ordered_unique[0], "json_point_2d", ordered_unique)


def _coordinate_text(value: float) -> str:
    return str(int(value)) if value.is_integer() else format(value, ".15g")


def vlmevalkit_point_prediction(parsed: ScreenSpotPointParse) -> str:
    """Translate a resolved JSON point to the pinned VLMEvalKit named-x/y parser."""

    if parsed.status != "resolved" or parsed.value is None:
        return SCREENSPOT_JSON_UNRESOLVED
    x, y = (_coordinate_text(coordinate) for coordinate in parsed.value)
    return f"pyautogui.click(x={x}, y={y})"


def adapt_screenspot_prediction_frame(data: Any) -> tuple[Any, dict[str, Any]]:
    """Adapt one saved prediction table while retaining raw responses and audit fields."""

    if "prediction" not in data:
        raise KeyError("ScreenSpot prediction workbook lacks prediction column")
    adapted = data.copy()
    original = (
        adapted["raw_prediction"].copy()
        if "raw_prediction" in adapted
        else adapted["prediction"].copy()
    )
    parsed = [parse_screenspot_json_point(value) for value in original]
    adapted["raw_prediction"] = original
    adapted["prediction"] = [vlmevalkit_point_prediction(item) for item in parsed]
    adapted["trace_extraction_status"] = [item.status for item in parsed]
    adapted["trace_extraction_method"] = [item.method for item in parsed]
    adapted["trace_extraction_candidates"] = [
        json.dumps(item.candidates, separators=(",", ":")) for item in parsed
    ]
    status_counts: dict[str, int] = {}
    method_counts: dict[str, int] = {}
    for item in parsed:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
        method_counts[item.method] = method_counts.get(item.method, 0) + 1
    return adapted, {
        "contract": SCREENSPOT_JSON_PREDICTION_CONTRACT,
        "prompt_contract": SCREENSPOT_JSON_PROMPT_CONTRACT,
        "rows": len(adapted),
        "resolved_rows": status_counts.get("resolved", 0),
        "unresolved_rows": len(adapted) - status_counts.get("resolved", 0),
        "status_counts": status_counts,
        "method_counts": method_counts,
    }


def weighted_screenspot_accuracy(scores: Any) -> tuple[float, int] | None:
    """Return the pooled official accuracy for one ScreenSpot concat result."""

    if not isinstance(scores, dict):
        return None
    if "Overall_Accuracy" in scores:
        try:
            return float(scores["Overall_Accuracy"]), 0
        except (TypeError, ValueError):
            return None

    total = 0
    weighted = 0.0
    for key, value in scores.items():
        key = str(key)
        if not key.endswith(":Overall_Accuracy"):
            continue
        prefix = key[: -len(":Overall_Accuracy")]
        try:
            accuracy = float(value)
        except (TypeError, ValueError):
            continue
        count = 0
        for count_key, count_value in scores.items():
            count_key = str(count_key)
            if count_key.startswith(prefix + ":") and count_key.endswith(":cnt"):
                try:
                    count += int(count_value)
                except (TypeError, ValueError):
                    pass
        if count > 0:
            total += count
            weighted += accuracy * count
    return (weighted / total, total) if total else None
