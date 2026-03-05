"""Domain/task-group default configuration loader.

This module provides deterministic, cached access to:
- domain defaults from `configs/domains/<domain>.yaml`,
- task-group overrides from `configs/task_groups/<domain>/<task_group>.yaml`.
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


def _domain_config_root() -> Path:
    """Resolve domain config root with optional environment override."""
    override = os.getenv("TRACE_DOMAIN_CONFIG_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "configs" / "domains"


def _config_path(domain: str, task_group: str) -> Path:
    """Build config path for one domain/task-group pair."""
    return _config_root() / str(domain) / f"{str(task_group)}.yaml"


def _domain_config_path(domain: str) -> Path:
    """Build domain-default config path."""
    return _domain_config_root() / f"{str(domain)}.yaml"


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


def _deep_merge_mappings(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    """Deep-merge two mappings with override precedence."""
    merged: Dict[str, Any] = {}
    ordered_keys = list(base.keys()) + [key for key in override.keys() if key not in base]
    for key in ordered_keys:
        if key in override:
            over_value = override[key]
            if key in base and isinstance(base[key], Mapping) and isinstance(over_value, Mapping):
                merged[key] = _deep_merge_mappings(base[key], over_value)
            else:
                merged[key] = deepcopy(over_value)
        else:
            merged[key] = deepcopy(base[key])
    return merged


def get_domain_defaults(domain: str) -> Dict[str, Any]:
    """Return deep-copied defaults for a domain."""
    path = _domain_config_path(domain)
    cfg = _load_group_config(path)
    if not isinstance(cfg, Mapping):
        return {}
    return deepcopy(dict(cfg))


def get_task_group_defaults(domain: str, task_group: str) -> Dict[str, Any]:
    """Return deep-copied merged defaults for a domain/task_group pair.

    Merge order:
    1) domain defaults (`configs/domains/<domain>.yaml`)
    2) task-group defaults (`configs/task_groups/<domain>/<task_group>.yaml`)
    """
    domain_cfg = _load_group_config(_domain_config_path(domain))
    group_cfg = _load_group_config(_config_path(domain, task_group))
    if not isinstance(domain_cfg, Mapping) and not isinstance(group_cfg, Mapping):
        return {}
    domain_map = dict(domain_cfg) if isinstance(domain_cfg, Mapping) else {}
    group_map = dict(group_cfg) if isinstance(group_cfg, Mapping) else {}
    merged = _deep_merge_mappings(domain_map, group_map)
    return deepcopy(merged)
