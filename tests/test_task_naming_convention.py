"""Tests for canonical task-id and module naming conventions."""

from __future__ import annotations

import re

from trace.tasks import TASK_REGISTRY


_TASK_ID_PATTERN = re.compile(
    r"^task_(?P<domain>[a-z0-9]+)_(?P<task_group>[a-z0-9]+)_(?P<task_name>[a-z0-9_]+)$"
)


def test_registered_task_ids_follow_canonical_pattern() -> None:
    for task_id, task_cls in TASK_REGISTRY.items():
        match = _TASK_ID_PATTERN.match(str(task_id))
        assert match is not None, task_id
        assert str(match.group("domain")) == str(getattr(task_cls, "domain"))
        assert str(match.group("task_group")) == str(getattr(task_cls, "task_group"))


def test_task_module_filenames_match_task_name() -> None:
    for task_id, task_cls in TASK_REGISTRY.items():
        module_name = str(getattr(task_cls, "__module__", ""))
        if not module_name.startswith("trace.tasks."):
            continue
        match = _TASK_ID_PATTERN.match(str(task_id))
        assert match is not None, task_id
        expected_task_name = str(match.group("task_name"))
        expected_prefix = f"trace.tasks.{match.group('domain')}.{match.group('task_group')}."
        assert module_name.startswith(expected_prefix), module_name
        assert module_name.rsplit(".", 1)[-1] == expected_task_name, module_name

