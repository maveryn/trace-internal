"""Shared parameter resolution helpers for puzzle task families."""

from __future__ import annotations

from typing import Any, Mapping

from ...shared.config_defaults import group_default


def resolve_puzzle_int_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer puzzle parameter with task params taking precedence."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))
