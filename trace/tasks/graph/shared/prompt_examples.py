"""Shared graph prompt JSON example helpers."""

from __future__ import annotations

import json
from typing import Any, Tuple


def build_graph_prompt_json_examples(*, evidence_value: Any, answer_value: Any) -> Tuple[str, str]:
    """Return compact answer+evidence and answer-only JSON examples."""

    return (
        json.dumps(
            {"evidence": evidence_value, "answer": answer_value},
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ),
        json.dumps(
            {"answer": answer_value},
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ),
    )


__all__ = ["build_graph_prompt_json_examples"]
