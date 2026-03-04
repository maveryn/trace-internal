"""Prompt bundle schema parsing and validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple


MIN_PROMPT_VARIANTS = 10


@dataclass(frozen=True)
class PromptBundle:
    """Validated prompt bundle payload."""

    bundle_id: str
    schema_version: str
    task_type_templates: Dict[str, Tuple[str, ...]]
    query_type_templates: Dict[str, Tuple[str, ...]]
    required_slots_by_key: Dict[str, Tuple[str, ...]]
    source_path: str


def _parse_template_map(raw: Any, *, field_name: str) -> Dict[str, Tuple[str, ...]]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{field_name} must be a mapping")
    parsed: Dict[str, Tuple[str, ...]] = {}
    for key, values in raw.items():
        entry_key = str(key)
        if not isinstance(values, list):
            raise ValueError(f"{field_name}.{entry_key} must be a list")
        templates = tuple(str(item).strip() for item in values if str(item).strip())
        if len(templates) < MIN_PROMPT_VARIANTS:
            raise ValueError(
                f"{field_name}.{entry_key} must contain at least {MIN_PROMPT_VARIANTS} prompt variants"
            )
        parsed[entry_key] = templates
    return parsed


def _parse_required_slots(raw: Any) -> Dict[str, Tuple[str, ...]]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError("required_slots_by_key must be a mapping")
    parsed: Dict[str, Tuple[str, ...]] = {}
    for key, values in raw.items():
        entry_key = str(key)
        if not isinstance(values, list):
            raise ValueError(f"required_slots_by_key.{entry_key} must be a list")
        slot_names = tuple(str(item).strip() for item in values if str(item).strip())
        parsed[entry_key] = slot_names
    return parsed


def parse_prompt_bundle(raw: Mapping[str, Any], *, source_path: str) -> PromptBundle:
    """Parse and validate a prompt bundle mapping."""
    bundle_id = str(raw.get("bundle_id", "")).strip()
    schema_version = str(raw.get("schema_version", "")).strip()
    if not bundle_id:
        raise ValueError("bundle_id is required")
    if not schema_version:
        raise ValueError("schema_version is required")

    task_type_templates = _parse_template_map(raw.get("task_type_templates"), field_name="task_type_templates")
    query_type_templates = _parse_template_map(raw.get("query_type_templates"), field_name="query_type_templates")
    required_slots_by_key = _parse_required_slots(raw.get("required_slots_by_key"))

    return PromptBundle(
        bundle_id=bundle_id,
        schema_version=schema_version,
        task_type_templates=task_type_templates,
        query_type_templates=query_type_templates,
        required_slots_by_key=required_slots_by_key,
        source_path=str(source_path),
    )

