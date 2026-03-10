"""Shared task-level prompt-variant rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ...core.prompts import PromptRenderResult, render_prompt_variants


PROMPT_OUTPUT_MODES: Tuple[str, str] = ("answer_only", "answer_and_evidence")


@dataclass(frozen=True)
class _PromptVariantSelection:
    """Rendered prompt payload with deterministic active-mode selection."""

    prompt: str
    active_mode: str
    active_result: PromptRenderResult
    prompt_variants: Dict[str, str]
    prompt_results: Dict[str, PromptRenderResult]


@dataclass(frozen=True)
class _PromptTraceArtifacts:
    """Prompt artifacts consumed by `TaskOutput` and trace `query_spec` fields."""

    prompt: str
    prompt_variants: Dict[str, str]
    prompt_variant_active_key: str
    prompt_variant: Dict[str, Any]
    prompt_variants_for_trace: Dict[str, Dict[str, Any]]


def render_task_prompt_variants(
    *,
    domain: str,
    task_group: str,
    bundle_id: str,
    task_family_key: str,
    task_key: str,
    task_variant_key: str | None = None,
    slots: Mapping[str, Any],
    instance_seed: int,
    answer_or_evidence_keys: Sequence[str] = PROMPT_OUTPUT_MODES,
    preferred_mode: str = "answer_and_evidence",
) -> _PromptVariantSelection:
    """Render task prompt variants and choose one active output mode."""
    prompt_results = render_prompt_variants(
        domain=domain,
        task_group=task_group,
        bundle_id=bundle_id,
        task_family_key=task_family_key,
        task_key=task_key,
        task_variant_key=task_variant_key,
        answer_or_evidence_keys=answer_or_evidence_keys,
        slots=slots,
        instance_seed=instance_seed,
    )
    if not prompt_results:
        raise ValueError("render_prompt_variants returned an empty mapping")

    active_mode = str(preferred_mode)
    if active_mode not in prompt_results:
        active_mode = sorted(prompt_results.keys())[0]
    active_result = prompt_results[active_mode]
    prompt_variants = {
        key: result.prompt
        for key, result in sorted(prompt_results.items())
    }
    return _PromptVariantSelection(
        prompt=active_result.prompt,
        active_mode=active_mode,
        active_result=active_result,
        prompt_variants=prompt_variants,
        prompt_results=prompt_results,
    )


def build_prompt_trace_artifacts(selection: _PromptVariantSelection) -> _PromptTraceArtifacts:
    """Convert prompt-variant selection into normalized trace/output payload fields."""
    active_mode = str(selection.active_mode)
    active_result = selection.active_result
    prompt = str(selection.prompt)
    prompt_variants = dict(selection.prompt_variants)
    prompt_variant = dict(active_result.metadata)
    prompt_variants_for_trace = {
        key: {"prompt": result.prompt, "metadata": dict(result.metadata)}
        for key, result in sorted(selection.prompt_results.items())
    }
    return _PromptTraceArtifacts(
        prompt=prompt,
        prompt_variants=prompt_variants,
        prompt_variant_active_key=active_mode,
        prompt_variant=prompt_variant,
        prompt_variants_for_trace=prompt_variants_for_trace,
    )
