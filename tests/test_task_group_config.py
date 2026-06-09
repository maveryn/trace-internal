"""Regression tests for shared task-group config helpers.

Domain-specific default assertions live in focused `tests/test_*_task_group_config.py`
files. Keep this module limited to cross-domain config-loader and helper invariants.
"""

from __future__ import annotations

import pytest

from trace.core.task_group_config import (
    get_domain_defaults,
    get_task_group_defaults,
    resolve_task_group_section_defaults,
)
from trace.tasks.shared.config_defaults import (
    required_group_default,
    required_group_defaults,
    resolve_optional_int_bounds,
    resolve_required_float_bounds,
    resolve_required_int_bounds,
)


def test_domain_defaults_and_missing_group_behavior() -> None:
    assert get_task_group_defaults("missing_domain", "missing_group") == {}
    domain_cfg = get_domain_defaults("geometry")
    cfg = get_task_group_defaults("geometry", "missing_group")
    assert cfg["rendering"]["shared"] == domain_cfg["rendering"]["shared"]


def test_section_defaults_require_shared_and_task_overrides_schema() -> None:
    mapping = {
        "rendering": {
            "canvas_size_min": 111,
            "shared": {"canvas_size_min": 512},
            "task_overrides": {"demo_task": {"canvas_size_min": 768}},
        }
    }
    shared_only = resolve_task_group_section_defaults(mapping, "rendering")
    task_specific = resolve_task_group_section_defaults(mapping, "rendering", task_id="demo_task")
    assert int(shared_only["canvas_size_min"]) == 512
    assert int(task_specific["canvas_size_min"]) == 768
    assert resolve_task_group_section_defaults({"rendering": {"canvas_size_min": 111}}, "rendering") == {}


def test_required_group_helpers_enforce_presence_and_nonempty() -> None:
    assert required_group_default({"value": 3}, "value", context="test") == 3
    resolved = required_group_defaults({"a": 1, "b": "ok"}, ("a", "b"), context="test")
    assert resolved == {"a": 1, "b": "ok"}
    with pytest.raises(ValueError):
        required_group_default({}, "value", context="test")
    with pytest.raises(ValueError):
        required_group_default({"value": "   "}, "value", context="test")
    with pytest.raises(ValueError):
        required_group_defaults({"a": 1}, ("a", "b"), context="test")


def test_resolve_numeric_bounds_helpers() -> None:
    assert resolve_optional_int_bounds(
        {"answer_min": 3},
        {"answer_max": 9},
        min_key="answer_min",
        max_key="answer_max",
        context="test",
    ) == (3, 9)
    assert resolve_optional_int_bounds(
        {},
        {},
        min_key="answer_min",
        max_key="answer_max",
        context="test",
    ) == (None, None)
    with pytest.raises(ValueError):
        resolve_optional_int_bounds(
            {"answer_min": 10, "answer_max": 2},
            {},
            min_key="answer_min",
            max_key="answer_max",
            context="test",
        )
    assert resolve_required_int_bounds(
        {"min": 2},
        {"max": 8},
        min_key="min",
        max_key="max",
        fallback_min=1,
        fallback_max=9,
        context="test",
    ) == (2, 8)
    assert resolve_required_float_bounds(
        {"min_f": 0.1},
        {"max_f": 0.6},
        min_key="min_f",
        max_key="max_f",
        fallback_min=0.0,
        fallback_max=1.0,
        context="test",
    ) == (0.1, 0.6)
    with pytest.raises(ValueError):
        resolve_required_int_bounds(
            {"min": 9, "max": 2},
            {},
            min_key="min",
            max_key="max",
            fallback_min=0,
            fallback_max=1,
            context="test",
        )
    with pytest.raises(ValueError):
        resolve_required_float_bounds(
            {"min_f": 0.9, "max_f": 0.2},
            {},
            min_key="min_f",
            max_key="max_f",
            fallback_min=0.0,
            fallback_max=1.0,
            context="test",
        )
