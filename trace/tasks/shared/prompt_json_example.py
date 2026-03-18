"""Shared helpers for deterministic JSON prompt examples."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Sequence, Tuple


def _is_point_pair(value: Any) -> bool:
    """Return true when value is one numeric 2D point pair."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return False
    return all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)


def _example_answer_value(answer_type: str) -> Any:
    """Return one canonical answer example by answer type."""
    answer_kind = str(answer_type)
    if answer_kind == "integer":
        return 8
    if answer_kind == "number":
        return 42.3
    if answer_kind == "pi_expression":
        return "12π"
    if answer_kind == "option_letter":
        return "B"
    return "value"


def _canonical_point_examples(count: int) -> List[List[int]] | None:
    """Return one deterministic, non-degenerate point layout when available."""
    layouts: Dict[int, List[List[int]]] = {
        1: [[0, 0]],
        2: [[0, 0], [4, 0]],
        3: [[0, 0], [4, 0], [0, 3]],
        4: [[0, 0], [4, 0], [4, 2], [0, 2]],
        5: [[0, 0], [4, 0], [5, 2], [2, 4], [-1, 2]],
    }
    return layouts.get(int(count))


def _mapping_of_point_pairs(value: Any) -> Mapping[str, Any] | None:
    """Return mapping when all values are point pairs."""
    if not isinstance(value, Mapping) or not value:
        return None
    if all(_is_point_pair(item) for item in value.values()):
        return value
    return None


def _sequence_of_point_pairs(value: Any) -> Sequence[Any] | None:
    """Return sequence when all items are point pairs."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        return None
    if all(_is_point_pair(item) for item in value):
        return value
    return None


def _example_like(value: Any, *, index: int) -> Any:
    """Build one lightweight placeholder that preserves JSON shape."""
    point_map = _mapping_of_point_pairs(value)
    if point_map is not None:
        layout = _canonical_point_examples(len(point_map))
        if layout is not None:
            out: Dict[str, Any] = {}
            for offset, key in enumerate(point_map.keys()):
                out[str(key)] = list(layout[offset])
            return out
    point_seq = _sequence_of_point_pairs(value)
    if point_seq is not None:
        layout = _canonical_point_examples(len(point_seq))
        if layout is not None:
            return [list(point) for point in layout]
    if _is_point_pair(value):
        return [int(index), int(-index)]
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(index + 2)
    if isinstance(value, float):
        rounded = round(float(value))
        if abs(float(value) - float(rounded)) <= 1e-9:
            return int(index + 2)
        return float(index + 2.5)
    if isinstance(value, str):
        text = str(value).strip()
        if text.endswith("π"):
            return f"{int(index + 2)}π"
        return str(index + 2)
    if isinstance(value, Mapping):
        out: Dict[str, Any] = {}
        for offset, key in enumerate(value.keys()):
            out[str(key)] = _example_like(value[key], index=int(index + offset))
        return out
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        out_list: List[Any] = []
        for offset, item in enumerate(value):
            out_list.append(_example_like(item, index=int(index + offset)))
        return out_list
    return str(index + 2)


def build_prompt_json_examples(*, evidence_value: Any, answer_type: str) -> Tuple[str, str]:
    """Build deterministic `answer_and_evidence` and `answer_only` JSON examples."""
    answer_value = _example_answer_value(str(answer_type))
    example_answer_only = {"answer": answer_value}
    example_answer_and_evidence = {
        "evidence": _example_like(evidence_value, index=0),
        "answer": answer_value,
    }
    return (
        json.dumps(example_answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(example_answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )
