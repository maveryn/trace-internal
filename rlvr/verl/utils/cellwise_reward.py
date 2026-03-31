from __future__ import annotations

import ast
import re
from numbers import Integral
from typing import Any, Iterable, List, Optional, Tuple

import numpy as np


_SINGLE_BINARY_RE = re.compile(r"(?<!\d)[01](?!\d)")


def to_binary_grid(value: Any) -> Optional[List[List[int]]]:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return None
    if isinstance(value, np.ndarray):
        if value.ndim != 2:
            return None
        if not np.isin(value, (0, 1)).all():
            return None
        return value.astype(int).tolist()
    if isinstance(value, list):
        rows = value
    elif isinstance(value, tuple):
        rows = list(value)
    else:
        return None
    if not rows:
        return None
    normalized: List[List[int]] = []
    row_len: Optional[int] = None
    for row in rows:
        if not isinstance(row, (list, tuple)):
            return None
        row_list = list(row)
        if row_len is None:
            row_len = len(row_list)
            if row_len == 0:
                return None
        elif len(row_list) != row_len:
            return None
        norm_row: List[int] = []
        for cell in row_list:
            if not isinstance(cell, Integral):
                return None
            val = int(cell)
            if val not in (0, 1):
                return None
            norm_row.append(val)
        normalized.append(norm_row)
    return normalized


def extract_boxed_span(text: str) -> Optional[Tuple[int, int]]:
    if not text:
        return None
    start_tag = "\\boxed{"
    idx = text.rfind(start_tag)
    if idx == -1:
        return None
    start = idx + len(start_tag)
    depth = 1
    i = start
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return (start, i)
        i += 1
    return None


def parse_matrix_with_cell_char_spans(
    text: str, rows: int, cols: int, base_offset: int = 0
) -> Tuple[Optional[List[List[int]]], Optional[List[List[Tuple[int, int]]]], bool]:
    if rows <= 0 or cols <= 0:
        return None, None, False
    matches = list(_SINGLE_BINARY_RE.finditer(text))
    if len(matches) != rows * cols:
        return None, None, False

    pred: List[List[int]] = [[0 for _ in range(cols)] for _ in range(rows)]
    spans: List[List[Tuple[int, int]]] = [[(0, 0) for _ in range(cols)] for _ in range(rows)]
    idx = 0
    for r in range(rows):
        for c in range(cols):
            match = matches[idx]
            val = int(match.group())
            pred[r][c] = val
            spans[r][c] = (base_offset + match.start(), base_offset + match.end())
            idx += 1

    return pred, spans, True


def char_spans_to_token_spans(
    token_offsets: Iterable[Tuple[int, int]],
    cell_char_spans: List[List[Tuple[int, int]]],
) -> Optional[List[List[Tuple[int, int]]]]:
    offsets = list(token_offsets)
    if not offsets:
        return None
    rows = len(cell_char_spans)
    cols = len(cell_char_spans[0]) if rows > 0 else 0
    token_spans: List[List[Tuple[int, int]]] = [[(-1, -1) for _ in range(cols)] for _ in range(rows)]
    for i in range(rows):
        for j in range(cols):
            start, end = cell_char_spans[i][j]
            indices = []
            for t, (ts, te) in enumerate(offsets):
                if ts == te:
                    continue
                if ts < end and te > start:
                    indices.append(t)
            if not indices:
                return None
            token_spans[i][j] = (min(indices), max(indices) + 1)
    return token_spans
