"""Task registry for TRACE generation."""

from __future__ import annotations

from typing import Dict, Type

from .base import Task


TASK_REGISTRY: Dict[str, Type[Task]] = {}


def register_task(cls: Type[Task]) -> Type[Task]:
    """Register task class under `task_id`."""
    task_id = getattr(cls, "task_id")
    if task_id in TASK_REGISTRY:
        raise KeyError(f"duplicate task_id: {task_id}")
    TASK_REGISTRY[task_id] = cls
    return cls


def create_task(task_id: str) -> Task:
    """Instantiate task by id."""
    if task_id not in TASK_REGISTRY:
        raise KeyError(task_id)
    return TASK_REGISTRY[task_id]()
