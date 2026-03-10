"""Shared prompt-text helpers for geometry tasks."""

from __future__ import annotations

from typing import Iterable


def append_required_labels_clause(base_text: str, labels: Iterable[str]) -> str:
    """Append one deterministic `Required labels:` sentence to a prompt fragment."""
    text = str(base_text).strip()
    normalized = [str(label).strip() for label in labels if str(label).strip()]
    if not normalized:
        return text
    if not text:
        return f"Required labels: {', '.join(normalized)}"
    return f"{text.rstrip('.')}. Required labels: {', '.join(normalized)}"
