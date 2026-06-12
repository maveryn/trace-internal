"""Prompt helper fragments for graph binary-tree scene tasks."""

from __future__ import annotations

import json
from typing import Sequence, Tuple


def count_prompt_json_examples() -> Tuple[str, str]:
    """Return JSON examples for count tasks."""

    return (
        json.dumps({"annotation": [[156, 124, 204, 172], [470, 430, 520, 480]], "answer": 2}, separators=(",", ":")),
        json.dumps({"answer": 2}, separators=(",", ":")),
    )


def traversal_prompt_json_examples() -> Tuple[str, str]:
    """Return JSON examples for traversal sequence tasks."""

    return (
        json.dumps(
            {
                "annotation": [[156, 124, 204, 172], [250, 250, 298, 298], [470, 430, 520, 480]],
                "answer": "M",
            },
            separators=(",", ":"),
        ),
        json.dumps({"answer": "M"}, separators=(",", ":")),
    )


def keyed_node_prompt_json_examples(roles: Sequence[str]) -> Tuple[str, str]:
    """Return JSON examples for keyed node-label tasks."""

    example_boxes = (
        [156, 124, 204, 172],
        [470, 430, 520, 480],
        [250, 250, 298, 298],
    )
    annotation = {
        str(role): list(box)
        for role, box in zip(tuple(str(role) for role in roles), example_boxes)
    }
    return (
        json.dumps({"annotation": annotation, "answer": "M"}, separators=(",", ":")),
        json.dumps({"answer": "M"}, separators=(",", ":")),
    )


def operation_path_prompt_json_examples() -> Tuple[str, str]:
    """Return JSON examples for ordered BST path tasks."""

    return (
        json.dumps({"annotation": [[156, 124, 204, 172], [250, 250, 298, 298]], "answer": "42"}, separators=(",", ":")),
        json.dumps({"answer": "42"}, separators=(",", ":")),
    )


def heap_violation_prompt_json_examples() -> Tuple[str, str]:
    """Return JSON examples for keyed heap-violation tasks."""

    return (
        json.dumps(
            {
                "annotation": {
                    "parent": [156, 124, 204, 172],
                    "child": [250, 250, 298, 298],
                },
                "answer": "42",
            },
            separators=(",", ":"),
        ),
        json.dumps({"answer": "42"}, separators=(",", ":")),
    )


__all__ = [
    "count_prompt_json_examples",
    "heap_violation_prompt_json_examples",
    "keyed_node_prompt_json_examples",
    "operation_path_prompt_json_examples",
    "traversal_prompt_json_examples",
]
