"""Resolve Trace run-level supervision policies to concrete row contracts."""

from __future__ import annotations


TRACE_OUTPUT_MODE_ANSWER = "answer"
TRACE_OUTPUT_MODE_ANSWER_AND_ANNOTATION = "answer_and_annotation"
TRACE_OUTPUT_MODE_TASK_CONDITIONED = "task_conditioned"
DEFAULT_TRACE_OUTPUT_MODE = TRACE_OUTPUT_MODE_ANSWER

TRACE_SUPERVISION_MODES = frozenset(
    {
        TRACE_OUTPUT_MODE_ANSWER,
        TRACE_OUTPUT_MODE_ANSWER_AND_ANNOTATION,
    }
)

_TRACE_OUTPUT_MODE_ALIASES = {
    "answer": TRACE_OUTPUT_MODE_ANSWER,
    "answer_only": TRACE_OUTPUT_MODE_ANSWER,
    "annotation": TRACE_OUTPUT_MODE_ANSWER_AND_ANNOTATION,
    "answer_and_annotation": TRACE_OUTPUT_MODE_ANSWER_AND_ANNOTATION,
    "task_conditioned": TRACE_OUTPUT_MODE_TASK_CONDITIONED,
}


def normalize_trace_output_mode(trace_output_mode: str | None) -> str:
    """Normalize a run policy, which may be task-conditioned."""

    raw_mode = str(trace_output_mode or DEFAULT_TRACE_OUTPUT_MODE).strip().lower()
    if raw_mode in {"", "auto"}:
        return DEFAULT_TRACE_OUTPUT_MODE
    normalized_mode = _TRACE_OUTPUT_MODE_ALIASES.get(raw_mode)
    if normalized_mode is None:
        raise ValueError(
            "Trace output mode must be one of "
            "{'answer', 'answer_and_annotation', 'task_conditioned'}; "
            "legacy alias 'answer_only' and shorthand alias 'annotation' are also accepted. "
            f"got {trace_output_mode!r}"
        )
    return normalized_mode


def normalize_trace_supervision_mode(trace_supervision_mode: str | None) -> str:
    """Normalize one row's concrete answer or answer-plus-annotation contract."""

    normalized_mode = str(trace_supervision_mode or "").strip().lower()
    if normalized_mode not in TRACE_SUPERVISION_MODES:
        raise ValueError(
            "Trace task-conditioned rows require trace_supervision_mode to be one of "
            f"{sorted(TRACE_SUPERVISION_MODES)!r}; got {trace_supervision_mode!r}"
        )
    return normalized_mode


def resolve_trace_row_output_mode(
    trace_output_mode: str | None,
    *,
    trace_supervision_mode: str | None = None,
) -> str:
    """Resolve a run policy to the concrete contract for one dataset row."""

    normalized_mode = normalize_trace_output_mode(trace_output_mode)
    if normalized_mode != TRACE_OUTPUT_MODE_TASK_CONDITIONED:
        return normalized_mode
    return normalize_trace_supervision_mode(trace_supervision_mode)


def resolve_trace_reward_mode(
    trace_reward_mode: str | None,
    *,
    trace_output_mode: str | None = None,
    trace_supervision_mode: str | None = None,
    trace_effective_output_mode: str | None = None,
) -> str:
    """Resolve configured reward policy to one row's concrete reward contract."""

    raw_mode = str(trace_reward_mode or "").strip().lower()
    if raw_mode in {"", "auto"}:
        normalized_mode = normalize_trace_output_mode(trace_output_mode)
    else:
        normalized_mode = normalize_trace_output_mode(trace_reward_mode)

    if normalized_mode != TRACE_OUTPUT_MODE_TASK_CONDITIONED:
        return normalized_mode

    row_mode = trace_effective_output_mode or trace_supervision_mode
    return normalize_trace_supervision_mode(row_mode)


__all__ = [
    "DEFAULT_TRACE_OUTPUT_MODE",
    "TRACE_OUTPUT_MODE_ANSWER",
    "TRACE_OUTPUT_MODE_ANSWER_AND_ANNOTATION",
    "TRACE_OUTPUT_MODE_TASK_CONDITIONED",
    "TRACE_SUPERVISION_MODES",
    "normalize_trace_output_mode",
    "normalize_trace_supervision_mode",
    "resolve_trace_reward_mode",
    "resolve_trace_row_output_mode",
]
