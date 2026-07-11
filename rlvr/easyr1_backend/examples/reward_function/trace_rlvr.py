from __future__ import annotations

import json
from typing import Any

from trace.core.reward_scoring import (
    _canonical_jsonable,
    _normalize_trace_answer_scoring,
    _parse_json_like,
    extract_trace_answer_for_scoring,
    is_trace_reward_input,
    score_trace_response,
)


REWARD_NAME = "trace_rlvr"
REWARD_TYPE = "batch"


def _jsonish(value: Any) -> Any:
    parsed = _parse_json_like(value)
    return parsed if parsed is not None else value


def _normalize_ground_truth_value(ground_truth: Any) -> Any:
    parsed = _jsonish(ground_truth)
    if isinstance(parsed, dict) and "type" in parsed and "value" in parsed:
        return parsed.get("value")
    return parsed


def _score_answer_exact(
    response: str,
    ground_truth: Any,
    *,
    trace_answer_scoring: str,
    trace_format_weight: float,
) -> dict[str, float]:
    answer_text = extract_trace_answer_for_scoring(response)
    format_score = 1.0 if answer_text is not None else 0.0
    candidate = answer_text if answer_text is not None else response

    normalized_scoring = _normalize_trace_answer_scoring(trace_answer_scoring)
    if normalized_scoring != "exact_json":
        # EasyR1 TRACE backend is intended for JSON-style TRACE rewards. Keep
        # legacy_strict explicit instead of silently approximating it here.
        raise ValueError("EasyR1 TRACE reward currently supports trace_answer_scoring=exact_json")

    pred = _canonical_jsonable(_jsonish(candidate))
    gold = _canonical_jsonable(_normalize_ground_truth_value(ground_truth))
    accuracy = 1.0 if pred == gold else 0.0
    overall = ((1.0 - trace_format_weight) * accuracy) + (trace_format_weight * format_score)
    return {
        "overall": float(overall),
        "score": float(overall),
        "accuracy": float(accuracy),
        "answer_reward": float(accuracy),
        "format": float(format_score),
        "zero_reward": 1.0 if accuracy <= 0.0 else 0.0,
        "trace_reward": 1.0,
    }


def _score_one(
    reward_input: dict[str, Any],
    *,
    trace_output_mode: str = "answer",
    trace_reward_mode: str = "auto",
    trace_answer_scoring: str = "exact_json",
    trace_annotation_reward_formula: str = "gated",
    trace_answer_weight: float = 0.5,
    trace_annotation_weight: float = 0.5,
    trace_format_weight: float = 0.05,
    bbox_iou_threshold: float | None = None,
    point_half_life_px: float | None = None,
) -> dict[str, float]:
    response = str(reward_input.get("response", "") or "")

    if is_trace_reward_input(reward_input):
        result = score_trace_response(
            response=response,
            answer_gt=_jsonish(reward_input["answer_gt"]),
            annotation_gt=_jsonish(reward_input["annotation_gt"]),
            reward_contract=_jsonish(reward_input["reward_contract"]),
            bbox_iou_threshold=bbox_iou_threshold,
            point_half_life_px=point_half_life_px,
            image_size=reward_input.get("image_size") or reward_input.get("source_image_size"),
            image_sizes=reward_input.get("image_sizes"),
            metadata=_jsonish(reward_input.get("metadata")),
            extra_info=_jsonish(reward_input.get("extra_info")),
            trace_reward_mode=trace_reward_mode if trace_reward_mode != "auto" else trace_output_mode,
            trace_answer_scoring=trace_answer_scoring,
            trace_annotation_reward_formula=trace_annotation_reward_formula,
            answer_weight=float(trace_answer_weight),
            annotation_weight=float(trace_annotation_weight),
            format_weight=float(trace_format_weight),
        )
        result["score"] = float(result["overall"])
        return {key: float(value) for key, value in result.items()}

    return _score_answer_exact(
        response,
        reward_input.get("ground_truth"),
        trace_answer_scoring=trace_answer_scoring,
        trace_format_weight=float(trace_format_weight),
    )


def compute_score(
    reward_inputs: list[dict[str, Any]],
    *,
    trace_output_mode: str = "answer",
    trace_reward_mode: str = "auto",
    trace_answer_scoring: str = "exact_json",
    trace_annotation_reward_formula: str = "gated",
    trace_answer_weight: float = 0.5,
    trace_annotation_weight: float = 0.5,
    trace_format_weight: float = 0.05,
    bbox_iou_threshold: float | None = None,
    point_half_life_px: float | None = None,
) -> list[dict[str, float]]:
    return [
        _score_one(
            reward_input,
            trace_output_mode=trace_output_mode,
            trace_reward_mode=trace_reward_mode,
            trace_answer_scoring=trace_answer_scoring,
            trace_annotation_reward_formula=trace_annotation_reward_formula,
            trace_answer_weight=trace_answer_weight,
            trace_annotation_weight=trace_annotation_weight,
            trace_format_weight=trace_format_weight,
            bbox_iou_threshold=bbox_iou_threshold,
            point_half_life_px=point_half_life_px,
        )
        for reward_input in reward_inputs
    ]

