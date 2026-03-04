"""Task-group default configuration loader.

This module provides deterministic, cached access to task-group defaults from
`configs/task_groups/<domain>/<task_group>.yaml`.
"""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping

import yaml


_CACHE_BY_PATH: Dict[str, Dict[str, Any]] = {}


def _config_root() -> Path:
    """Resolve task-group config root with optional environment override."""
    override = os.getenv("TRACE_TASK_GROUP_CONFIG_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "configs" / "task_groups"


def _config_path(domain: str, task_group: str) -> Path:
    """Build config path for one domain/task-group pair."""
    return _config_root() / str(domain) / f"{str(task_group)}.yaml"


def _load_group_config(path: Path) -> Dict[str, Any]:
    """Load and cache one task-group config file as a plain mapping."""
    key = str(path.resolve())
    if key in _CACHE_BY_PATH:
        return _CACHE_BY_PATH[key]

    if not path.exists():
        _CACHE_BY_PATH[key] = {}
        return _CACHE_BY_PATH[key]

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raw = {}
    _CACHE_BY_PATH[key] = dict(raw)
    return _CACHE_BY_PATH[key]


def get_task_group_defaults(domain: str, task_group: str) -> Dict[str, Any]:
    """Return deep-copied defaults for a domain/task_group pair."""
    path = _config_path(domain, task_group)
    cfg = _load_group_config(path)
    if not isinstance(cfg, Mapping):
        return {}
    return deepcopy(dict(cfg))
