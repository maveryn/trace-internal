"""TRACE task registry exports.

Task modules are registered lazily. Importing :mod:`trace.tasks` should not
import every task in the repository because scene-scoped review and migration
tools must be able to work while unrelated domains are temporarily broken.
Use ``register_all_tasks`` only for global inventory/build commands.
"""

from .registry import (
    TASK_REGISTRY,
    create_task,
    ensure_all_tasks_registered,
    ensure_scene_tasks_registered,
    ensure_task_registered,
    is_default_dataset_task,
    list_default_task_ids,
    list_task_ids,
)


def register_all_tasks() -> None:
    """Import every discoverable task module into the registry."""

    ensure_all_tasks_registered()


__all__ = [
    "TASK_REGISTRY",
    "create_task",
    "ensure_all_tasks_registered",
    "ensure_scene_tasks_registered",
    "ensure_task_registered",
    "is_default_dataset_task",
    "list_default_task_ids",
    "list_task_ids",
    "register_all_tasks",
]
