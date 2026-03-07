"""Task registry for TRACE generation."""

from __future__ import annotations

import re
from typing import Dict, Type

from .base import Task


TASK_REGISTRY: Dict[str, Type[Task]] = {}
_TASK_ID_PATTERN = re.compile(
    r"^task_(?P<domain>[a-z0-9]+)_(?P<task_group>[a-z0-9]+)_(?P<task_name>[a-z0-9_]+)$"
)


def _validate_task_id_contract(cls: Type[Task], task_id: str) -> None:
    """Validate canonical task-id naming and taxonomy alignment."""
    match = _TASK_ID_PATTERN.match(str(task_id))
    if match is None:
        raise ValueError(
            "task_id must follow 'task_<domain>_<task_group>_<task_name>' "
            f"(got: {task_id})"
        )
    domain = getattr(cls, "domain", None)
    task_group = getattr(cls, "task_group", None)
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError(f"task '{task_id}' must define non-empty string attribute 'domain'")
    if not isinstance(task_group, str) or not task_group.strip():
        raise ValueError(f"task '{task_id}' must define non-empty string attribute 'task_group'")
    if str(domain) != str(match.group("domain")):
        raise ValueError(
            f"task_id domain segment '{match.group('domain')}' does not match class domain '{domain}'"
        )
    if str(task_group) != str(match.group("task_group")):
        raise ValueError(
            "task_id task_group segment "
            f"'{match.group('task_group')}' does not match class task_group '{task_group}'"
        )


def register_task(cls: Type[Task]) -> Type[Task]:
    """Register task class under `task_id`."""
    task_id = str(getattr(cls, "task_id"))
    _validate_task_id_contract(cls, task_id)
    if task_id in TASK_REGISTRY:
        raise KeyError(f"duplicate task_id: {task_id}")
    TASK_REGISTRY[task_id] = cls
    return cls


def create_task(task_id: str) -> Task:
    """Instantiate task by id."""
    if task_id not in TASK_REGISTRY:
        raise KeyError(task_id)
    return TASK_REGISTRY[task_id]()
