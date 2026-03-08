"""Tests for canonical task-id and module naming conventions."""

from __future__ import annotations

import re

from trace.tasks import TASK_REGISTRY


_TASK_ID_PATTERN = re.compile(r"^task_[a-z0-9_]+$")
_TASK_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


def test_registered_task_ids_follow_canonical_pattern() -> None:
    for task_id, task_cls in TASK_REGISTRY.items():
        task_id_text = str(task_id)
        assert _TASK_ID_PATTERN.match(task_id_text) is not None, task_id

        domain = str(getattr(task_cls, "domain"))
        task_group = str(getattr(task_cls, "task_group"))
        prefix = f"task_{domain}_{task_group}_"
        assert task_id_text.startswith(prefix), task_id

        task_name = task_id_text[len(prefix):]
        assert task_name, task_id
        assert _TASK_NAME_PATTERN.match(task_name) is not None, task_id


def test_task_module_filenames_match_task_name() -> None:
    for task_id, task_cls in TASK_REGISTRY.items():
        module_name = str(getattr(task_cls, "__module__", ""))
        if not module_name.startswith("trace.tasks."):
            continue
        domain = str(getattr(task_cls, "domain"))
        task_group = str(getattr(task_cls, "task_group"))
        prefix = f"task_{domain}_{task_group}_"
        task_id_text = str(task_id)
        assert task_id_text.startswith(prefix), task_id
        expected_task_name = task_id_text[len(prefix):]
        expected_prefix = f"trace.tasks.{domain}.{task_group}."
        assert module_name.startswith(expected_prefix), module_name
        assert module_name.rsplit(".", 1)[-1] == expected_task_name, module_name
