from __future__ import annotations

from typing import Any

from verl.utils.local_strict_eval import strict_score_response
from verl.utils.trace_mode import resolve_trace_reward_mode
from verl.utils.trace_reward import (
    _canonical_jsonable,
    _normalize_trace_answer_scoring,
    _parse_json_like,
    extract_trace_answer_for_scoring,
    is_trace_reward_input,
    score_trace_response,
)


def _score_ground_truth_exact(
    response: str,
    ground_truth: Any,
    *,
    trace_answer_scoring: str = "exact_json",
) -> dict[str, float]:
    normalized_scoring = _normalize_trace_answer_scoring(trace_answer_scoring)
    if normalized_scoring == "legacy_strict":
        accuracy, extracted, _, _ = strict_score_response(response=response, ground_truth=ground_truth)
        accuracy = float(accuracy)
        return {
            "overall": accuracy,
            "score": accuracy,
            "accuracy": accuracy,
            "format": 0.0,
            "extracted": float(extracted),
            "zero_reward": 1.0 if accuracy <= 0.0 else 0.0,
        }

    normalized_pred = _canonical_jsonable(_parse_json_like(response))
    normalized_gt = _canonical_jsonable(ground_truth)
    accuracy = 1.0 if normalized_pred == normalized_gt else 0.0
    return {
        "overall": accuracy,
        "score": accuracy,
        "accuracy": accuracy,
        "format": 0.0,
        "zero_reward": 1.0 if accuracy <= 0.0 else 0.0,
    }


def _score_single_reward_input(
    reward_input: dict[str, Any],
    *,
    trace_format_weight: float = 0.1,
    trace_reward_mode: str = "auto",
    trace_output_mode: str | None = None,
    trace_answer_scoring: str = "exact_json",
    bbox_iou_threshold: float = 0.5,
) -> dict[str, float]:
    response = str(reward_input.get("response", "") or "")
    normalized_mode = resolve_trace_reward_mode(trace_reward_mode, trace_output_mode=trace_output_mode)
    normalized_answer_scoring = _normalize_trace_answer_scoring(trace_answer_scoring)
    if is_trace_reward_input(reward_input):
        trace_score = score_trace_response(
            response=response,
            answer_gt=reward_input["answer_gt"],
            evidence_gt=reward_input["evidence_gt"],
            reward_contract=reward_input["reward_contract"],
            bbox_iou_threshold=bbox_iou_threshold,
            trace_reward_mode=normalized_mode,
            trace_answer_scoring=normalized_answer_scoring,
            format_weight=trace_format_weight,
        )
        return {"score": float(trace_score["overall"]), **trace_score}

    answer_text = extract_trace_answer_for_scoring(response)
    candidate = answer_text if answer_text is not None else response
    return _score_ground_truth_exact(
        candidate,
        reward_input.get("ground_truth"),
        trace_answer_scoring=normalized_answer_scoring,
    )


def _build_single_reward_input(
    *,
    data_source: str,
    solution_str: str,
    ground_truth: Any,
    extra_info: dict[str, Any] | None,
) -> dict[str, Any]:
    reward_input: dict[str, Any] = {
        "data_source": data_source,
        "response": solution_str,
        "ground_truth": ground_truth,
    }
    extra_info = extra_info or {}
    for key in ("answer_gt", "evidence_gt", "reward_contract", "metadata", "trace_ref", "prompt"):
        if key in extra_info:
            reward_input[key] = extra_info[key]
    return reward_input


def compute_score(*args, **kwargs):
    """TRACE reward adapter supporting both legacy batch and Vero per-sample reward-manager calls."""
    if kwargs.get("reward_inputs") is not None:
        reward_inputs = kwargs.pop("reward_inputs")
        return [compute_score(reward_input=reward_input, **kwargs) for reward_input in reward_inputs]

    if args and isinstance(args[0], list):
        reward_inputs = args[0]
        return [compute_score(reward_input=reward_input, **kwargs) for reward_input in reward_inputs]

    if kwargs.get("reward_input") is not None:
        reward_input = kwargs.pop("reward_input")
        trace_format_weight = float(kwargs.pop("trace_format_weight", 0.1))
        trace_reward_mode = kwargs.pop("trace_reward_mode", "auto")
        trace_output_mode = kwargs.pop("trace_output_mode", None)
        trace_answer_scoring = kwargs.pop("trace_answer_scoring", "exact_json")
        bbox_iou_threshold = float(kwargs.pop("bbox_iou_threshold", 0.5))
        return _score_single_reward_input(
            reward_input,
            trace_format_weight=trace_format_weight,
            trace_reward_mode=trace_reward_mode,
            trace_output_mode=trace_output_mode,
            trace_answer_scoring=trace_answer_scoring,
            bbox_iou_threshold=bbox_iou_threshold,
        )

    data_source = kwargs.pop("data_source")
    solution_str = kwargs.pop("solution_str")
    ground_truth = kwargs.pop("ground_truth", None)
    extra_info = kwargs.pop("extra_info", None)
    reward_input = _build_single_reward_input(
        data_source=data_source,
        solution_str=solution_str,
        ground_truth=ground_truth,
        extra_info=extra_info,
    )
    return compute_score(reward_input=reward_input, **kwargs)
