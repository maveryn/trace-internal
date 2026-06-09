"""Tests for shared puzzle parameter helpers."""

from __future__ import annotations

from trace.tasks.puzzles.shared.params import resolve_puzzle_int_param


def test_resolve_puzzle_int_param_precedence_and_casting() -> None:
    defaults = {"width": "5", "height": 6}

    assert resolve_puzzle_int_param({"width": "8"}, defaults, "width", 2) == 8
    assert resolve_puzzle_int_param({}, defaults, "width", 2) == 5
    assert resolve_puzzle_int_param({}, defaults, "height", 2) == 6
    assert resolve_puzzle_int_param({}, defaults, "depth", 3) == 3
