"""Prompt rendering entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence

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
    """Render one prompt template with strict placeholder requirements."""
    rendered = str(template).format_map(_StrictSlotMap({str(k): v for k, v in dict(slots).items()})).strip()
    if not rendered:
        raise ValueError("rendered prompt template is empty")
    return rendered


def _validate_required_slots(
    required_slots_by_key: Mapping[str, tuple[str, ...]],
    *,
    task_type_key: str,
    query_type: str,
    answer_or_evidence_key: str | None,
    slots: Mapping[str, Any],
) -> None:
    """Ensure all slots declared by the selected task/query keys are present."""
    required_task = required_slots_by_key.get(f"task_type:{task_type_key}", ())
    required_query = required_slots_by_key.get(f"query_type:{query_type}", ())
    required_mode = (
        required_slots_by_key.get(f"answer_or_evidence:{answer_or_evidence_key}", ())
        if answer_or_evidence_key
        else ()
    )
    missing = [
        name
        for name in list(required_task) + list(required_query) + list(required_mode)
        if str(name) not in slots
    ]
    if missing:
        raise ValueError(f"missing required prompt slots: {sorted(set(missing))}")


def _resolve_answer_or_evidence_key(bundle, requested_key: str | None) -> str | None:
    """Resolve optional answer/evidence mode key for one bundle."""
    mode_templates = bundle.answer_or_evidence_templates
    if not mode_templates:
        return None
    if requested_key is not None:
        key = str(requested_key).strip()
        if key not in mode_templates:
            raise ValueError(f"missing answer_or_evidence key in bundle: {key}")
        return key
    if "answer_and_evidence" in mode_templates:
        return "answer_and_evidence"
    return sorted(mode_templates.keys())[0]


def render_prompt(
    *,
    domain: str,
    task_group: str,
    bundle_id: str,
    task_type_key: str,
    query_type: str,
    answer_or_evidence_key: str | None = None,
    slots: Mapping[str, Any],
    instance_seed: int,
) -> PromptRenderResult:
    """Render one prompt using deterministic task-type/query-type template variants."""
    bundle = load_prompt_bundle(domain=domain, task_group=task_group, bundle_id=bundle_id)

    if task_type_key not in bundle.task_type_templates:
        raise ValueError(f"missing task_type key in bundle: {task_type_key}")
    if query_type not in bundle.query_type_templates:
        raise ValueError(f"missing query_type key in bundle: {query_type}")

    resolved_mode_key = _resolve_answer_or_evidence_key(bundle, answer_or_evidence_key)
    _validate_required_slots(
        bundle.required_slots_by_key,
        task_type_key=task_type_key,
        query_type=query_type,
        answer_or_evidence_key=resolved_mode_key,
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
    mode_text = ""
    mode_idx = None
    mode_count = None
    if resolved_mode_key is not None:
        mode_template, mode_idx, mode_count = choose_variant(
            bundle.answer_or_evidence_templates[resolved_mode_key],
            instance_seed=instance_seed,
            namespace=f"prompt.answer_or_evidence.{resolved_mode_key}",
        )
        mode_text = _render_template(mode_template, slots)

    task_text = _render_template(task_template, slots)
    query_text = _render_template(query_template, slots)
    prompt = " ".join(text for text in (task_text, query_text, mode_text) if text).strip()

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
        "slot_values": {str(key): slots[key] for key in sorted(slots.keys(), key=str)},
        "template_paths": [bundle.source_path],
    }
    if resolved_mode_key is not None and mode_idx is not None and mode_count is not None:
        metadata["answer_or_evidence_key"] = str(resolved_mode_key)
        metadata["answer_or_evidence_variant_index"] = int(mode_idx)
        metadata["variant_count_by_key"][f"answer_or_evidence:{resolved_mode_key}"] = int(mode_count)
    return PromptRenderResult(prompt=prompt, metadata=metadata)


def render_prompt_variants(
    *,
    domain: str,
    task_group: str,
    bundle_id: str,
    task_type_key: str,
    query_type: str,
    answer_or_evidence_keys: Sequence[str],
    slots: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, PromptRenderResult]:
    """Render multiple answer/evidence prompt modes deterministically for one instance."""
    rendered: Dict[str, PromptRenderResult] = {}
    for key in [str(item).strip() for item in answer_or_evidence_keys]:
        if not key:
            raise ValueError("answer_or_evidence_keys must not contain empty values")
        rendered[key] = render_prompt(
            domain=domain,
            task_group=task_group,
            bundle_id=bundle_id,
            task_type_key=task_type_key,
            query_type=query_type,
            answer_or_evidence_key=key,
            slots=slots,
            instance_seed=instance_seed,
        )
    return rendered
