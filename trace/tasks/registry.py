"""Task registry for TRACE generation."""

from __future__ import annotations

import re
from functools import wraps
from typing import Dict, Type

from ..core.taxonomy import resolve_task_query_id
from .base import Task
from .shared.fixed_query import rewrite_public_query_output


TASK_REGISTRY: Dict[str, Type[Task]] = {}
_V0_TASK_ID_PATTERN = re.compile(
    r"^task_(?P<domain>[a-z0-9_]+)__(?P<scene>[a-z0-9_]+)__(?P<objective>[a-z0-9_]+)$"
)


def _validate_task_id_contract(cls: Type[Task], task_id: str) -> None:
    """Validate canonical task-id naming and taxonomy alignment."""
    task_id_text = str(task_id)
    v0_match = _V0_TASK_ID_PATTERN.match(task_id_text)
    if v0_match is None:
        raise ValueError(
            "task_id must follow taxonomy-v0 public form "
            "'task_<domain>__<scene_id>__<objective_contract>' "
            f"(got: {task_id})"
        )
    domain = getattr(cls, "domain", None)
    task_group = getattr(cls, "task_group", None)
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError(f"task '{task_id}' must define non-empty string attribute 'domain'")
    if not isinstance(task_group, str) or not task_group.strip():
        raise ValueError(f"task '{task_id}' must define non-empty string attribute 'task_group'")
    if v0_match is not None:
        task_domain = str(v0_match.group("domain"))
        if task_domain != str(domain):
            raise ValueError(
                "taxonomy-v0 task_id domain segment must match class domain "
                f"'{domain}' (got: {task_id_text})"
            )


def register_task(cls: Type[Task]) -> Type[Task]:
    """Register task class under `task_id`."""
    task_id = str(getattr(cls, "task_id"))
    _validate_task_id_contract(cls, task_id)
    if task_id in TASK_REGISTRY:
        raise KeyError(f"duplicate task_id: {task_id}")
    v0_match = _V0_TASK_ID_PATTERN.match(task_id)
    if v0_match is not None:
        original_generate = cls.generate
        taxonomy_scene_id = str(v0_match.group("scene"))

        @wraps(original_generate)
        def _generate_with_public_query_contract(self, instance_seed, *, params, max_attempts):
            output = original_generate(self, instance_seed, params=params, max_attempts=max_attempts)
            query_id = str(
                output.query_id
                or resolve_task_query_id(trace_payload=output.trace_payload)
            )
            if not query_id:
                return output
            scene_id = str(output.scene_id or taxonomy_scene_id)
            return rewrite_public_query_output(
                output,
                query_id=query_id,
                scene_id=scene_id,
                preserve_internal_query_id_as="internal_query_id",
            )

        cls.generate = _generate_with_public_query_contract  # type: ignore[method-assign]
    TASK_REGISTRY[task_id] = cls
    return cls


def create_task(task_id: str) -> Task:
    """Instantiate task by id."""
    if task_id not in TASK_REGISTRY:
        raise KeyError(task_id)
    return TASK_REGISTRY[task_id]()


def is_default_dataset_task(task_id: str) -> bool:
    """Return whether a registered task participates in default dataset builds."""

    if task_id not in TASK_REGISTRY:
        raise KeyError(task_id)
    return bool(getattr(TASK_REGISTRY[task_id], "default_dataset_enabled", True))


def list_task_ids() -> list[str]:
    """Return all registered task ids in deterministic order."""

    return sorted(TASK_REGISTRY)


def list_default_task_ids() -> list[str]:
    """Return registered task ids included in default dataset builds."""

    return [task_id for task_id in list_task_ids() if is_default_dataset_task(task_id)]
