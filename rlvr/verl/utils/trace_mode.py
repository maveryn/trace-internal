from __future__ import annotations

from pathlib import Path

from trace.core.task_supervision_runtime import (
    DEFAULT_TRACE_OUTPUT_MODE,
    TRACE_OUTPUT_MODE_ANSWER,
    TRACE_OUTPUT_MODE_ANSWER_AND_ANNOTATION,
    TRACE_OUTPUT_MODE_TASK_CONDITIONED,
    TRACE_SUPERVISION_MODES,
    normalize_trace_output_mode,
    normalize_trace_supervision_mode,
    resolve_trace_reward_mode,
    resolve_trace_row_output_mode,
)

_TRACE_PROMPT_KEY_BY_OUTPUT_MODE = {
    TRACE_OUTPUT_MODE_ANSWER: "prompt_answer",
    TRACE_OUTPUT_MODE_ANSWER_AND_ANNOTATION: "prompt_answer_and_annotation",
}

_TRACE_SYSTEM_PROMPT_BY_OUTPUT_MODE = {
    TRACE_OUTPUT_MODE_ANSWER: "trace_vero_json_system_prompt_answer.txt",
    TRACE_OUTPUT_MODE_ANSWER_AND_ANNOTATION: "trace_vero_json_system_prompt_answer_and_annotation.txt",
}

def resolve_trace_prompt_key(prompt_key: str | None, *, trace_output_mode: str | None = None) -> str:
    raw_key = (prompt_key or "").strip()
    if raw_key and raw_key.lower() != "auto":
        return raw_key
    normalized_mode = normalize_trace_output_mode(trace_output_mode)
    if normalized_mode == TRACE_OUTPUT_MODE_TASK_CONDITIONED:
        return "auto"
    return _TRACE_PROMPT_KEY_BY_OUTPUT_MODE[normalized_mode]


def default_trace_rlvr_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_trace_system_prompt_path(
    *, trace_output_mode: str | None = None, repo_root: str | Path | None = None
) -> Path:
    normalized_mode = normalize_trace_output_mode(trace_output_mode)
    if normalized_mode == TRACE_OUTPUT_MODE_TASK_CONDITIONED:
        raise ValueError("task_conditioned has no single default system prompt; resolve the row mode first")
    root = Path(repo_root) if repo_root is not None else default_trace_rlvr_root()
    return root / "examples" / "prompts" / _TRACE_SYSTEM_PROMPT_BY_OUTPUT_MODE[normalized_mode]


def resolve_trace_system_prompt(
    configured_value: str | None,
    *,
    trace_output_mode: str | None = None,
    repo_root: str | Path | None = None,
) -> str:
    raw_value = (configured_value or "").strip()
    if raw_value and raw_value.lower() != "auto":
        return raw_value
    if normalize_trace_output_mode(trace_output_mode) == TRACE_OUTPUT_MODE_TASK_CONDITIONED:
        return "auto"
    return str(default_trace_system_prompt_path(trace_output_mode=trace_output_mode, repo_root=repo_root))
