"""Task-agnostic answer-distribution checks for development review."""

from __future__ import annotations

from collections import Counter
import math
from typing import Any, Dict, List, Mapping, Sequence


def canonicalize_answer_value(*, answer_type: str, answer_value: Any) -> str:
    """Return one deterministic answer label for frequency counting."""
    kind = str(answer_type)
    if kind == "integer":
        return str(int(answer_value))
    if kind == "number":
        numeric = float(answer_value)
        if not math.isfinite(float(numeric)):
            raise ValueError("number answers must be finite")
        return format(float(numeric), ".12g")
    return str(answer_value)


def parse_numeric_answer_value(*, answer_type: str, answer_value: Any) -> float | None:
    """Return numeric answer scalar when the answer type is numeric."""
    kind = str(answer_type)
    if kind not in {"integer", "number"}:
        return None
    numeric = float(answer_value)
    if not math.isfinite(float(numeric)):
        raise ValueError("number answers must be finite")
    return float(numeric)


def _format_bound(value: float) -> str:
    """Format one numeric bound for bin labels."""
    text = format(float(value), ".6f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text if text else "0"


def _five_bin_report(values: Sequence[float]) -> Dict[str, Any]:
    """Build fixed 5-bin equal-width report for numeric answers."""
    if not values:
        return {
            "bin_count": 5,
            "range_min": None,
            "range_max": None,
            "max_bin_count": 0,
            "max_bin_frequency": 0.0,
            "bins": [],
        }
    v_min = float(min(values))
    v_max = float(max(values))
    total = len(values)
    if abs(float(v_max) - float(v_min)) <= 1e-12:
        return {
            "bin_count": 5,
            "range_min": float(v_min),
            "range_max": float(v_max),
            "max_bin_count": int(total),
            "max_bin_frequency": 1.0,
            "bins": [
                {
                    "bin_id": 0,
                    "label": f"[{_format_bound(v_min)}, {_format_bound(v_max)}]",
                    "count": int(total),
                }
            ],
        }

    bin_count = 5
    width = (float(v_max) - float(v_min)) / float(bin_count)
    counts: List[int] = [0 for _ in range(bin_count)]
    for raw in values:
        value = float(raw)
        if abs(float(value) - float(v_max)) <= 1e-12:
            index = int(bin_count - 1)
        else:
            index = int((float(value) - float(v_min)) / float(width))
            index = max(0, min(int(bin_count - 1), int(index)))
        counts[int(index)] += 1

    bins: List[Dict[str, Any]] = []
    for index, count in enumerate(counts):
        start = float(v_min + (float(index) * float(width)))
        end = float(v_min + (float(index + 1) * float(width)))
        label = f"[{_format_bound(start)}, {_format_bound(end)})"
        if int(index) == int(bin_count - 1):
            label = f"[{_format_bound(start)}, {_format_bound(end)}]"
        bins.append(
            {
                "bin_id": int(index),
                "label": str(label),
                "count": int(count),
            }
        )
    max_count = int(max(counts))
    return {
        "bin_count": int(bin_count),
        "range_min": float(v_min),
        "range_max": float(v_max),
        "max_bin_count": int(max_count),
        "max_bin_frequency": float(max_count) / float(total),
        "bins": bins,
    }


def evaluate_answer_distribution(
    answers: Sequence[Mapping[str, Any]],
    *,
    min_unique_answers: int = 5,
    max_answer_frequency: float = 1.0 / 3.0,
) -> Dict[str, Any]:
    """Evaluate lightweight anti-degeneracy checks over one task answer sample."""
    if not answers:
        raise ValueError("answers must be non-empty")

    labels: Counter[str] = Counter()
    answer_type_counts: Counter[str] = Counter()
    numeric_values: List[float] = []
    numeric_only = True
    for item in answers:
        answer_type = str(item.get("answer_type", "")).strip()
        answer_value = item.get("answer_value")
        label = canonicalize_answer_value(answer_type=answer_type, answer_value=answer_value)
        labels[str(label)] += 1
        answer_type_counts[str(answer_type)] += 1
        numeric = parse_numeric_answer_value(answer_type=answer_type, answer_value=answer_value)
        if numeric is None:
            numeric_only = False
        else:
            numeric_values.append(float(numeric))

    sample_count = int(sum(labels.values()))
    unique_answers = int(len(labels))
    max_answer_count = int(max(labels.values()))
    max_answer_frequency_observed = float(max_answer_count) / float(sample_count)

    min_unique_target = int(min(int(min_unique_answers), int(sample_count)))
    check_unique = bool(unique_answers >= int(min_unique_target))
    check_max_freq = bool(float(max_answer_frequency_observed) < float(max_answer_frequency))

    numeric_bins = _five_bin_report(numeric_values) if bool(numeric_only) else None
    if numeric_bins is None:
        max_bin_frequency_observed = None
    else:
        max_bin_frequency_observed = float(numeric_bins["max_bin_frequency"])

    pass_overall = bool(check_unique and check_max_freq)
    top_answers = [
        {"answer_label": str(label), "count": int(count)}
        for label, count in sorted(labels.items(), key=lambda item: (-int(item[1]), str(item[0])))
    ]

    return {
        "sample_count": int(sample_count),
        "answer_type_counts": {str(key): int(value) for key, value in sorted(answer_type_counts.items())},
        "unique_answers": int(unique_answers),
        "max_answer_count": int(max_answer_count),
        "max_answer_frequency": float(max_answer_frequency_observed),
        "top_answers": top_answers,
        "five_bin_numeric": numeric_bins,
        "checks": {
            "min_unique_answers": {
                "threshold": int(min_unique_target),
                "observed": int(unique_answers),
                "pass": bool(check_unique),
            },
            "max_answer_frequency": {
                "threshold": float(max_answer_frequency),
                "observed": float(max_answer_frequency_observed),
                "pass": bool(check_max_freq),
            },
            "max_five_bin_frequency": (
                {
                    "observed": float(max_bin_frequency_observed),
                    "pass": None,
                    "status": "reported_not_gated_numeric_answers",
                }
                if numeric_bins is not None
                else {
                    "observed": None,
                    "pass": None,
                    "status": "not_applicable_non_numeric_answers",
                }
            ),
        },
        "pass": bool(pass_overall),
    }
