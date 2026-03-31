"""Task registry for TRACE generation."""

from __future__ import annotations

import re
from typing import Dict, Type

from .base import Task


TASK_REGISTRY: Dict[str, Type[Task]] = {}
_TASK_ID_PATTERN = re.compile(r"^task_[a-z0-9_]+$")
_TASK_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")


def _validate_task_id_contract(cls: Type[Task], task_id: str) -> None:
    """Validate canonical task-id naming and taxonomy alignment."""
    task_id_text = str(task_id)
    if _TASK_ID_PATTERN.match(task_id_text) is None:
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
    prefix = f"task_{str(domain)}_{str(task_group)}_"
    if not task_id_text.startswith(prefix):
        raise ValueError(
            "task_id must include class domain/task_group prefix "
            f"'{prefix}' (got: {task_id_text})"
        )
    task_name = task_id_text[len(prefix):]
    if not task_name or _TASK_NAME_PATTERN.match(task_name) is None:
        raise ValueError(f"invalid task_name segment in task_id '{task_id_text}'")


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


def list_task_ids() -> list[str]:
    """Return all registered task ids in deterministic order."""

    return sorted(TASK_REGISTRY)
