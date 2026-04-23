"""Prompt rendering entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
import re
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


_ANSWER_ONLY_SCHEMA_LINE_RE = re.compile(
    r'^Use a valid JSON object with key "answer" for the final answer\.\s*$',
    re.IGNORECASE,
)
_ANSWER_AND_EVIDENCE_SCHEMA_LINE_RE = re.compile(
    r'^Use a valid JSON object with keys "evidence" and "answer" in that order for the final answer\.\s*$',
    re.IGNORECASE,
)


def _render_template(
    template: str,
    slots: Mapping[str, Any],
    *,
    allow_empty: bool = False,
) -> str:
    """Render one prompt template with strict placeholder requirements."""
    rendered = str(template).format_map(_StrictSlotMap({str(k): v for k, v in dict(slots).items()})).strip()
    if not rendered and not bool(allow_empty):
        raise ValueError("rendered prompt template is empty")
    return rendered


def _strip_generic_output_contract_line(rendered_mode_text: str, *, answer_or_evidence_key: str | None) -> str:
    """Remove generic schema boilerplate while preserving task-specific format guidance."""
    if not rendered_mode_text or answer_or_evidence_key is None:
        return rendered_mode_text

    schema_line_re = (
        _ANSWER_ONLY_SCHEMA_LINE_RE
        if answer_or_evidence_key == "answer_only"
        else _ANSWER_AND_EVIDENCE_SCHEMA_LINE_RE
        if answer_or_evidence_key == "answer_and_evidence"
        else None
    )
    if schema_line_re is None:
        return rendered_mode_text

    filtered_lines = [line for line in rendered_mode_text.splitlines() if not schema_line_re.match(line.strip())]
    cleaned_lines: list[str] = []
    previous_blank = False
    for line in filtered_lines:
        is_blank = not line.strip()
        if is_blank and previous_blank:
            continue
        cleaned_lines.append(line.rstrip())
        previous_blank = is_blank
    return "\n".join(cleaned_lines).strip()


def _validate_required_slots(
    required_slots_by_key: Mapping[str, tuple[str, ...]],
    *,
    task_family_key: str,
    task_key: str,
    task_variant_key: str | None,
    answer_or_evidence_key: str | None,
    slots: Mapping[str, Any],
) -> None:
    """Ensure all slots declared by the selected task-family/task keys are present."""
    required_family = required_slots_by_key.get(f"task_family:{task_family_key}", ())
    required_task = required_slots_by_key.get(f"task:{task_key}", ())
    required_variant = (
        required_slots_by_key.get(f"task_variant:{task_variant_key}", ())
        if task_variant_key
        else ()
    )
    required_mode = (
        required_slots_by_key.get(f"answer_or_evidence:{answer_or_evidence_key}", ())
        if answer_or_evidence_key
        else ()
    )
    missing = [
        name
        for name in list(required_family) + list(required_task) + list(required_variant) + list(required_mode)
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
    task_family_key: str,
    task_key: str,
    task_variant_key: str | None = None,
    answer_or_evidence_key: str | None = None,
    slots: Mapping[str, Any],
    instance_seed: int,
) -> PromptRenderResult:
    """Render one prompt using deterministic task-family/task/variant templates."""
    bundle = load_prompt_bundle(domain=domain, task_group=task_group, bundle_id=bundle_id)

    if task_family_key not in bundle.task_family_templates:
        raise ValueError(f"missing task_family key in bundle: {task_family_key}")
    if task_key not in bundle.task_templates:
        raise ValueError(f"missing task key in bundle: {task_key}")
    resolved_task_variant_key = str(task_variant_key).strip() if task_variant_key is not None else None
    if resolved_task_variant_key:
        if resolved_task_variant_key not in bundle.task_variant_templates:
            raise ValueError(f"missing task_variant key in bundle: {resolved_task_variant_key}")
    else:
        resolved_task_variant_key = None

    resolved_mode_key = _resolve_answer_or_evidence_key(bundle, answer_or_evidence_key)
    _validate_required_slots(
        bundle.required_slots_by_key,
        task_family_key=task_family_key,
        task_key=task_key,
        task_variant_key=resolved_task_variant_key,
        answer_or_evidence_key=resolved_mode_key,
        slots=slots,
    )

    task_family_template, task_family_idx, task_family_count = choose_variant(
        bundle.task_family_templates[task_family_key],
        instance_seed=instance_seed,
        namespace=f"prompt.task_family.{task_family_key}",
    )
    task_template, task_idx, task_count = choose_variant(
        bundle.task_templates[task_key],
        instance_seed=instance_seed,
        namespace=f"prompt.task.{task_key}",
    )
    task_variant_text = ""
    task_variant_idx = None
    task_variant_count = None
    if resolved_task_variant_key is not None:
        variant_template, task_variant_idx, task_variant_count = choose_variant(
            bundle.task_variant_templates[resolved_task_variant_key],
            instance_seed=instance_seed,
            namespace=f"prompt.task_variant.{resolved_task_variant_key}",
        )
        task_variant_text = _render_template(variant_template, slots)
    mode_text = ""
    mode_idx = None
    mode_count = None
    if resolved_mode_key is not None:
        mode_template, mode_idx, mode_count = choose_variant(
            bundle.answer_or_evidence_templates[resolved_mode_key],
            instance_seed=instance_seed,
            namespace=f"prompt.answer_or_evidence.{resolved_mode_key}",
        )
        mode_text = _render_template(mode_template, slots, allow_empty=True)
        mode_text = _strip_generic_output_contract_line(mode_text, answer_or_evidence_key=resolved_mode_key)

    task_family_text = _render_template(task_family_template, slots)
    task_text = _render_template(task_template, slots)
    prompt = " ".join(text for text in (task_family_text, task_text, task_variant_text) if text).strip()
    if mode_text:
        prompt = f"{prompt}\n{mode_text}".strip()

    metadata = {
        "prompt_bundle_id": bundle.bundle_id,
        "schema_version": bundle.schema_version,
        "task_family_key": str(task_family_key),
        "task_key": str(task_key),
        "task_variant_key": (str(resolved_task_variant_key) if resolved_task_variant_key else None),
        "task_family_variant_index": int(task_family_idx),
        "task_variant_index": int(task_idx),
        "task_variant_template_index": (int(task_variant_idx) if task_variant_idx is not None else None),
        "variant_count_by_key": {
            f"task_family:{task_family_key}": int(task_family_count),
            f"task:{task_key}": int(task_count),
        },
        "slot_values": {str(key): slots[key] for key in sorted(slots.keys(), key=str)},
        "template_paths": [bundle.source_path],
    }
    if resolved_task_variant_key is not None and task_variant_count is not None:
        metadata["variant_count_by_key"][f"task_variant:{resolved_task_variant_key}"] = int(task_variant_count)
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
    task_family_key: str,
    task_key: str,
    task_variant_key: str | None = None,
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
            task_family_key=task_family_key,
            task_key=task_key,
            task_variant_key=task_variant_key,
            answer_or_evidence_key=key,
            slots=slots,
            instance_seed=instance_seed,
        )
    return rendered
