"""Shared query-type resolution helpers for builders and tooling."""

from __future__ import annotations

from typing import Any, List, Mapping


def resolve_query_types(task: Any, params: Mapping[str, Any]) -> List[str]:
    """Resolve supported query types with deterministic deduplicated ordering."""
    if hasattr(task, "supported_query_types"):
        values = getattr(task, "supported_query_types")(dict(params))
        out = [str(item) for item in values]
    elif "query_type" in params:
        out = [str(params["query_type"])]
    else:
        out = ["default"]

    deduped: List[str] = []
    seen: set[str] = set()
    for item in out:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped or ["default"]
