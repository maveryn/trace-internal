"""Prompt bundle asset loading and caching."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

from .schema import PromptBundle, parse_prompt_bundle


_CACHE: Dict[str, PromptBundle] = {}


def _prompt_root() -> Path:
    """Resolve the prompt-bundle root directory."""
    override = os.getenv("TRACE_PROMPT_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "prompts"


def _bundle_rel_path(domain: str, task_group: str, bundle_id: str) -> Path:
    """Build bundle path relative to the prompt root."""
    return Path(str(domain)) / str(task_group) / f"{str(bundle_id)}.json"


def _bundle_abs_path(domain: str, task_group: str, bundle_id: str) -> Path:
    """Build absolute bundle path for one domain/task-group/bundle id."""
    return _prompt_root() / _bundle_rel_path(domain, task_group, bundle_id)


def load_prompt_bundle(domain: str, task_group: str, bundle_id: str) -> PromptBundle:
    """Load a prompt bundle for one domain/task_group."""
    abs_path = _bundle_abs_path(domain, task_group, bundle_id)
    cache_key = str(abs_path.resolve())
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    if not abs_path.exists():
        raise FileNotFoundError(f"prompt bundle not found: {abs_path}")

    raw = json.loads(abs_path.read_text(encoding="utf-8"))
    bundle = parse_prompt_bundle(raw, source_path=str(_bundle_rel_path(domain, task_group, bundle_id)))
    _CACHE[cache_key] = bundle
    return bundle
