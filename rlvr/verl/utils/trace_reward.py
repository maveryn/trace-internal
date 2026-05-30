from __future__ import annotations

from typing import Any

from trace.core.reward_scoring import (
    TRACE_EVIDENCE_LOG_TYPES,
    _canonical_jsonable,
    _normalize_trace_answer_scoring,
    _parse_json_like,
    evaluate_trace_response_format,
    extract_trace_answer_for_scoring,
    extract_trace_prediction,
    is_trace_reward_input,
    score_trace_response as _score_trace_response,
)

from .local_strict_eval import strict_score_response


def score_trace_response(**kwargs: Any) -> dict[str, float]:
    """Score one TRACE response using the shared TRACE core scorer.

    RLVR keeps the legacy strict answer scorer adapter here because that parser
    is VERL/RLVR-local compatibility behavior. TRACE core owns the public
    answer/evidence contract dispatch and evidence geometry scoring.
    """

    kwargs.setdefault("legacy_strict_scorer", strict_score_response)
    return _score_trace_response(**kwargs)


__all__ = [
    "TRACE_EVIDENCE_LOG_TYPES",
    "evaluate_trace_response_format",
    "extract_trace_answer_for_scoring",
    "extract_trace_prediction",
    "is_trace_reward_input",
    "score_trace_response",
]
