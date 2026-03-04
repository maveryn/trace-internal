"""Prompt rendering entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

from .assets import load_prompt_bundle
from .select import choose_variant


@dataclass(frozen=True)
class PromptRenderResult:
    """Rendered prompt and deterministic variant metadata."""

    prompt: str
    metadata: Dict[str, Any]


class _StrictSlotMap(dict):
    """Format-map dict that raises on missing placeholder keys."""

    def __missing__(self, key: str) -> str:  # pragma: no cover - exercised via caller exception path
        raise KeyError(f"missing prompt slot: {key}")


def _render_template(template: str, slots: Mapping[str, Any]) -> str:
    rendered = str(template).format_map(_StrictSlotMap({str(k): v for k, v in dict(slots).items()})).strip()
    if not rendered:
        raise ValueError("rendered prompt template is empty")
    return rendered


def _validate_required_slots(
    required_slots_by_key: Mapping[str, tuple[str, ...]],
    *,
    task_type_key: str,
    query_type: str,
    slots: Mapping[str, Any],
) -> None:
    required_task = required_slots_by_key.get(f"task_type:{task_type_key}", ())
    required_query = required_slots_by_key.get(f"query_type:{query_type}", ())
    missing = [name for name in list(required_task) + list(required_query) if str(name) not in slots]
    if missing:
        raise ValueError(f"missing required prompt slots: {sorted(set(missing))}")


def render_prompt(
    *,
    domain: str,
    task_group: str,
    bundle_id: str,
    task_type_key: str,
    query_type: str,
    slots: Mapping[str, Any],
    instance_seed: int,
) -> PromptRenderResult:
    """Render one prompt using deterministic task-type/query-type template variants."""
    bundle = load_prompt_bundle(domain=domain, task_group=task_group, bundle_id=bundle_id)

    if task_type_key not in bundle.task_type_templates:
        raise ValueError(f"missing task_type key in bundle: {task_type_key}")
    if query_type not in bundle.query_type_templates:
        raise ValueError(f"missing query_type key in bundle: {query_type}")

    _validate_required_slots(
        bundle.required_slots_by_key,
        task_type_key=task_type_key,
        query_type=query_type,
        slots=slots,
    )

    task_template, task_idx, task_count = choose_variant(
        bundle.task_type_templates[task_type_key],
        instance_seed=instance_seed,
        namespace="prompt.task_type",
    )
    query_template, query_idx, query_count = choose_variant(
        bundle.query_type_templates[query_type],
        instance_seed=instance_seed,
        namespace=f"prompt.query_type.{query_type}",
    )

    task_text = _render_template(task_template, slots)
    query_text = _render_template(query_template, slots)
    prompt = f"{task_text} {query_text}".strip()

    metadata = {
        "prompt_bundle_id": bundle.bundle_id,
        "schema_version": bundle.schema_version,
        "task_type_key": str(task_type_key),
        "query_type_key": str(query_type),
        "task_type_variant_index": int(task_idx),
        "query_type_variant_index": int(query_idx),
        "variant_count_by_key": {
            f"task_type:{task_type_key}": int(task_count),
            f"query_type:{query_type}": int(query_count),
        },
        "template_paths": [bundle.source_path],
    }
    return PromptRenderResult(prompt=prompt, metadata=metadata)

