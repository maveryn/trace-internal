from __future__ import annotations

from typing import Any

from verl.utils.local_strict_eval import strict_score_response
from verl.utils.trace_mode import TRACE_OUTPUT_MODE_ANSWER, resolve_trace_reward_mode
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
    trace_format_weight: float = 0.0,
    trace_reward_mode: str = "auto",
    trace_output_mode: str | None = None,
    trace_answer_scoring: str = "exact_json",
    trace_annotation_reward_formula: str = "gated",
    trace_answer_weight: float = 0.5,
    trace_annotation_weight: float = 0.5,
    bbox_iou_threshold: float | None = None,
    point_half_life_px: float | None = None,
) -> dict[str, float]:
    response = str(reward_input.get("response", "") or "")
    extra_info = reward_input.get("extra_info")
    extra_info = extra_info if isinstance(extra_info, dict) else {}
    row_effective_output_mode = reward_input.get("trace_output_mode") or extra_info.get("trace_output_mode")
    row_supervision_mode = reward_input.get("trace_supervision_mode") or extra_info.get("trace_supervision_mode")
    trace_reward_input = is_trace_reward_input(reward_input)
    if not trace_reward_input and row_effective_output_mode is None and row_supervision_mode is None:
        row_effective_output_mode = TRACE_OUTPUT_MODE_ANSWER
    normalized_mode = resolve_trace_reward_mode(
        trace_reward_mode,
        trace_output_mode=trace_output_mode,
        trace_supervision_mode=row_supervision_mode,
        trace_effective_output_mode=row_effective_output_mode,
    )
    normalized_answer_scoring = _normalize_trace_answer_scoring(trace_answer_scoring)
    if trace_reward_input:
        trace_score = score_trace_response(
            response=response,
            answer_gt=reward_input["answer_gt"],
            annotation_gt=reward_input["annotation_gt"],
            reward_contract=reward_input["reward_contract"],
            bbox_iou_threshold=bbox_iou_threshold,
            point_half_life_px=point_half_life_px,
            image_size=reward_input.get("image_size") or reward_input.get("source_image_size"),
            image_sizes=reward_input.get("image_sizes") or reward_input.get("image_sizes_exported"),
            metadata=reward_input.get("metadata"),
            extra_info=reward_input.get("extra_info"),
            trace_reward_mode=normalized_mode,
            trace_answer_scoring=normalized_answer_scoring,
            trace_annotation_reward_formula=trace_annotation_reward_formula,
            answer_weight=float(trace_answer_weight),
            annotation_weight=float(trace_annotation_weight),
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
    for key in (
        "answer_gt",
        "annotation_gt",
        "reward_contract",
        "metadata",
        "trace_ref",
        "prompt",
        "image_size",
        "image_sizes",
        "image_sizes_exported",
        "source_image_size",
        "trace_supervision_mode",
        "trace_output_mode",
    ):
        if key in extra_info:
            reward_input[key] = extra_info[key]
    if extra_info:
        reward_input["extra_info"] = dict(extra_info)
    return reward_input


def compute_score(*args, **kwargs):
    """Trace reward adapter supporting both legacy batch and Vero per-sample reward-manager calls."""
    if kwargs.get("reward_inputs") is not None:
        reward_inputs = kwargs.pop("reward_inputs")
        return [compute_score(reward_input=reward_input, **kwargs) for reward_input in reward_inputs]

    if args and isinstance(args[0], list):
        reward_inputs = args[0]
        return [compute_score(reward_input=reward_input, **kwargs) for reward_input in reward_inputs]

    if kwargs.get("solution_strs") is not None:
        solution_strs = list(kwargs.pop("solution_strs"))
        data_sources = list(kwargs.pop("data_sources", ["trace"] * len(solution_strs)))
        ground_truths = list(kwargs.pop("ground_truths", [None] * len(solution_strs)))
        extra_infos = list(kwargs.pop("extra_infos", [{} for _ in solution_strs]))
        if not (len(data_sources) == len(solution_strs) == len(ground_truths) == len(extra_infos)):
            raise ValueError("Batched Trace reward inputs must have matching lengths")
        return [
            compute_score(
                data_source=data_source,
                solution_str=solution_str,
                ground_truth=ground_truth,
                extra_info=extra_info,
                **kwargs,
            )
            for data_source, solution_str, ground_truth, extra_info in zip(
                data_sources,
                solution_strs,
                ground_truths,
                extra_infos,
                strict=True,
            )
        ]

    if kwargs.get("reward_input") is not None:
        reward_input = kwargs.pop("reward_input")
        trace_format_weight = float(kwargs.pop("trace_format_weight", 0.0))
        trace_reward_mode = kwargs.pop("trace_reward_mode", "auto")
        trace_output_mode = kwargs.pop("trace_output_mode", None)
        trace_answer_scoring = kwargs.pop("trace_answer_scoring", "exact_json")
        trace_annotation_reward_formula = kwargs.pop("trace_annotation_reward_formula", "gated")
        trace_answer_weight = float(kwargs.pop("trace_answer_weight", 0.5))
        trace_annotation_weight = float(kwargs.pop("trace_annotation_weight", 0.5))
        bbox_iou_threshold = kwargs.pop("bbox_iou_threshold", None)
        bbox_iou_threshold = None if bbox_iou_threshold is None else float(bbox_iou_threshold)
        point_half_life_px = kwargs.pop("point_half_life_px", None)
        point_half_life_px = None if point_half_life_px is None else float(point_half_life_px)
        return _score_single_reward_input(
            reward_input,
            trace_format_weight=trace_format_weight,
            trace_reward_mode=trace_reward_mode,
            trace_output_mode=trace_output_mode,
            trace_answer_scoring=trace_answer_scoring,
            trace_annotation_reward_formula=trace_annotation_reward_formula,
            trace_answer_weight=trace_answer_weight,
            trace_annotation_weight=trace_annotation_weight,
            bbox_iou_threshold=bbox_iou_threshold,
            point_half_life_px=point_half_life_px,
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
