from __future__ import annotations

from pathlib import Path


TRACE_OUTPUT_MODE_ANSWER = "answer"
TRACE_OUTPUT_MODE_ANSWER_AND_EVIDENCE = "answer_and_evidence"
DEFAULT_TRACE_OUTPUT_MODE = TRACE_OUTPUT_MODE_ANSWER

_TRACE_OUTPUT_MODE_ALIASES = {
    "answer": TRACE_OUTPUT_MODE_ANSWER,
    "answer_only": TRACE_OUTPUT_MODE_ANSWER,
    "evidence": TRACE_OUTPUT_MODE_ANSWER_AND_EVIDENCE,
    "answer_and_evidence": TRACE_OUTPUT_MODE_ANSWER_AND_EVIDENCE,
}

_TRACE_PROMPT_KEY_BY_OUTPUT_MODE = {
    TRACE_OUTPUT_MODE_ANSWER: "prompt_answer",
    TRACE_OUTPUT_MODE_ANSWER_AND_EVIDENCE: "prompt_answer_and_evidence",
}

_TRACE_SYSTEM_PROMPT_BY_OUTPUT_MODE = {
    TRACE_OUTPUT_MODE_ANSWER: "trace_vero_json_system_prompt_answer.txt",
    TRACE_OUTPUT_MODE_ANSWER_AND_EVIDENCE: "trace_vero_json_system_prompt_answer_and_evidence.txt",
}


def normalize_trace_output_mode(trace_output_mode: str | None) -> str:
    raw_mode = (trace_output_mode or DEFAULT_TRACE_OUTPUT_MODE).strip().lower()
    if raw_mode in {"", "auto"}:
        return DEFAULT_TRACE_OUTPUT_MODE
    normalized_mode = _TRACE_OUTPUT_MODE_ALIASES.get(raw_mode)
    if normalized_mode is None:
        raise ValueError(
            "TRACE output mode must be one of {'answer', 'answer_and_evidence'}; "
            "legacy alias 'answer_only' and shorthand alias 'evidence' are also accepted. "
            f"got {trace_output_mode!r}"
        )
    return normalized_mode


def resolve_trace_reward_mode(trace_reward_mode: str | None, *, trace_output_mode: str | None = None) -> str:
    raw_mode = (trace_reward_mode or "").strip().lower()
    if raw_mode in {"", "auto"}:
        return normalize_trace_output_mode(trace_output_mode)
    return normalize_trace_output_mode(trace_reward_mode)


def resolve_trace_prompt_key(prompt_key: str | None, *, trace_output_mode: str | None = None) -> str:
    raw_key = (prompt_key or "").strip()
    if raw_key and raw_key.lower() != "auto":
        return raw_key
    normalized_mode = normalize_trace_output_mode(trace_output_mode)
    return _TRACE_PROMPT_KEY_BY_OUTPUT_MODE[normalized_mode]


def default_trace_rlvr_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_trace_system_prompt_path(
    *, trace_output_mode: str | None = None, repo_root: str | Path | None = None
) -> Path:
    normalized_mode = normalize_trace_output_mode(trace_output_mode)
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
    return str(default_trace_system_prompt_path(trace_output_mode=trace_output_mode, repo_root=repo_root))
