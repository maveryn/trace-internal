"""Tests for canonical task-id and module naming conventions."""

from __future__ import annotations

import re

from trace.tasks import TASK_REGISTRY


_TASK_ID_PATTERN = re.compile(r"^task_[a-z0-9_]+$")
_TASK_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$")
_FAMILY_MODULE_EXCEPTIONS = {
    "trace.tasks.geometry.measurement.composite_measurement",
}
_REGISTERED_MODULE_COUNTS = {
    module_name: sum(
        1
        for task_cls in TASK_REGISTRY.values()
        if str(getattr(task_cls, "__module__", "")) == module_name
    )
    for module_name in {str(getattr(task_cls, "__module__", "")) for task_cls in TASK_REGISTRY.values()}
}


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
        if domain == "charts" and module_name.startswith("trace.tasks.charts.table."):
            continue
        if domain == "puzzles" and module_name.startswith("trace.tasks.puzzles.cell_board."):
            continue
        assert module_name.startswith(expected_prefix), module_name
        if hasattr(task_cls, "fixed_query_variant") or hasattr(task_cls, "fixed_query_variants"):
            continue
        if module_name in _FAMILY_MODULE_EXCEPTIONS or int(_REGISTERED_MODULE_COUNTS.get(module_name, 0)) > 1:
            continue
        module_leaf = module_name.rsplit(".", 1)[-1]
        if (
            expected_task_name.endswith(module_leaf)
            or module_leaf.endswith(expected_task_name)
            or expected_task_name.startswith(module_leaf)
        ):
            continue
        if sorted(module_leaf.split("_")) == sorted(expected_task_name.split("_")):
            continue
        assert module_leaf == expected_task_name, module_name
