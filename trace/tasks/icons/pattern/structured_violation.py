"""Consolidated icon structured-violation task spanning row and grid rules."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.consolidated_legacy import (
    normalize_legacy_icons_output,
    strip_consolidated_params,
    unregister_legacy_tasks,
)
from ..sequence.rotation_violation import IconsSequenceRotationViolationTask
from .grid_rotation_violation import IconsPatternGridRotationViolationTask
from .grid_size_violation import IconsPatternGridSizeViolationTask

LEGACY_TASK_IDS: Tuple[str, ...] = (
    "task_icons_sequence_rotation_violation",
    "task_icons_pattern_grid_rotation_violation",
    "task_icons_pattern_grid_size_violation",
)
unregister_legacy_tasks(LEGACY_TASK_IDS)

TASK_ID = "task_icons_pattern_structured_violation"
_SUPPORTED_VARIANTS: Tuple[str, ...] = (
    "row_rotation_violation",
    "grid_rotation_violation",
    "grid_size_violation",
)
_VARIANT_ALIASES: Dict[str, str] = {
    "constant_rotation_step_violation": "row_rotation_violation",
    "row_col_rotation_grid_violation": "grid_rotation_violation",
    "row_col_size_grid_violation": "grid_size_violation",
}
_SCENE_VARIANTS: Dict[str, str] = {
    "row_rotation_violation": "sequence_row",
    "grid_rotation_violation": "numbered_grid",
    "grid_size_violation": "numbered_grid",
}
_LEGACY_BUILDERS = {
    "row_rotation_violation": IconsSequenceRotationViolationTask,
    "grid_rotation_violation": IconsPatternGridRotationViolationTask,
    "grid_size_violation": IconsPatternGridSizeViolationTask,
}
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "pattern")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _normalize_variant(variant: str) -> str:
    """Normalize explicit task-variant aliases to the consolidated vocabulary."""

    normalized = _VARIANT_ALIASES.get(str(variant), str(variant))
    if normalized not in _SUPPORTED_VARIANTS:
        raise ValueError(f"unsupported task_variant: {variant}")
    return str(normalized)


def _resolve_task_variant(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve which structured-rule family this instance should use."""

    normalized_params = dict(params)
    explicit_variant = normalized_params.get("task_variant")
    if explicit_variant is not None:
        normalized_params["task_variant"] = _normalize_variant(str(explicit_variant))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.task_variant")
    selected_variant, variant_probabilities = resolve_variant(
        rng,
        params=normalized_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_SUPPORTED_VARIANTS,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
    )
    selected_variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=normalized_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected_variant),
        variant_probabilities=variant_probabilities,
        supported_variants=_SUPPORTED_VARIANTS,
        balance_flag_key="balanced_variant_sampling",
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        sampling_namespace=f"{TASK_ID}.task_variant",
    )
    return str(selected_variant), {str(key): float(value) for key, value in sorted(variant_probabilities.items())}


def _variant_mapping(defaults: Mapping[str, Any], key: str, *, variant: str) -> Mapping[str, Any]:
    """Return one per-variant mapping from merged task defaults."""

    raw = defaults.get(str(key), {})
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError(f"{key} must be a mapping for {TASK_ID}")
    selected = raw.get(str(variant), {})
    if selected is None:
        return {}
    if not isinstance(selected, Mapping):
        raise ValueError(f"{key}.{variant} must be a mapping for {TASK_ID}")
    return {str(name): value for name, value in dict(selected).items()}


def _render_prompt(*, instance_seed: int, task_variant: str):
    """Render prompt variants for the consolidated structured-violation task."""

    required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "task_family_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_by_variant",
            "question_text_by_variant",
            "evidence_hint",
            "answer_hint",
            "json_example",
            "json_example_answer_only",
        ),
        context=f"prompt defaults for {TASK_ID}",
    )
    object_description_map = _PROMPT_DEFAULTS.get("object_description_by_variant", {})
    question_text_map = _PROMPT_DEFAULTS.get("question_text_by_variant", {})
    if not isinstance(object_description_map, Mapping) or not isinstance(question_text_map, Mapping):
        raise ValueError(f"structured-violation prompt mappings must be dictionaries for {TASK_ID}")
    object_description = object_description_map.get(str(task_variant))
    question_text = question_text_map.get(str(task_variant))
    if not isinstance(object_description, str) or not object_description.strip():
        raise ValueError(f"missing object description for {TASK_ID}:{task_variant}")
    if not isinstance(question_text, str) or not question_text.strip():
        raise ValueError(f"missing question text for {TASK_ID}:{task_variant}")

    prompt_selection = render_task_prompt_variants(
        domain="icons",
        task_group="pattern",
        bundle_id=str(_PROMPT_DEFAULTS["bundle_id"]),
        task_family_key=str(_PROMPT_DEFAULTS["task_family_key"]),
        task_key=str(_PROMPT_DEFAULTS["task_key"]),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(object_description),
            "question_text": str(question_text),
            "json_output_contract": str(_PROMPT_DEFAULTS["json_output_contract"]),
            "json_output_contract_answer_only": str(_PROMPT_DEFAULTS["json_output_contract_answer_only"]),
            "evidence_hint": str(_PROMPT_DEFAULTS["evidence_hint"]),
            "answer_hint": str(_PROMPT_DEFAULTS["answer_hint"]),
            "json_example": str(_PROMPT_DEFAULTS["json_example"]),
            "json_example_answer_only": str(_PROMPT_DEFAULTS["json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


@register_task
class IconsPatternStructuredViolationTask:
    """Unified icon structured-violation task for numbered rows and grids."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "pattern"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_variant, variant_probabilities = _resolve_task_variant(int(instance_seed), params)
        legacy_task = _LEGACY_BUILDERS[str(task_variant)]()
        legacy_params = strip_consolidated_params(params)
        legacy_params.update(dict(_variant_mapping(_GEN_DEFAULTS, "variant_generation_params", variant=str(task_variant))))
        legacy_params.update(dict(_variant_mapping(_RENDER_DEFAULTS, "variant_render_params", variant=str(task_variant))))
        output = legacy_task.generate(int(instance_seed), params=legacy_params, max_attempts=int(max_attempts))
        prompt_artifacts = _render_prompt(instance_seed=int(instance_seed), task_variant=str(task_variant))
        legacy_trace = dict(output.trace_payload.get("execution_trace") or {})
        scene_variant = str(_SCENE_VARIANTS[str(task_variant)])
        return normalize_legacy_icons_output(
            output,
            scene_variant=scene_variant,
            task_variant=str(task_variant),
            legacy_task_id=str(legacy_task.task_id),
            variant_probabilities=variant_probabilities,
            scene_variant_probabilities={scene_variant: 1.0},
            legacy_scene_variant=str(legacy_trace.get("scene_variant", scene_variant)),
            legacy_task_variant=str(output.task_variant),
            scene_kind="icons_pattern_structured_violation",
            prompt_bundle_id=str(_PROMPT_DEFAULTS["bundle_id"]),
            prompt_artifacts=prompt_artifacts,
        )


__all__ = ["IconsPatternStructuredViolationTask"]
