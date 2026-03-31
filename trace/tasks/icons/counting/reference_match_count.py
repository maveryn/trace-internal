"""Consolidated reference-vs-scene icon matching count task."""

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
from .attribute_binding import IconsCountingAttributeBindingTask
from .color import IconsCountingColorTask
from .orientation import IconsCountingOrientationTask
from .type import IconsCountingTypeTask

LEGACY_TASK_IDS: Tuple[str, ...] = (
    "task_icons_counting_type",
    "task_icons_counting_color",
    "task_icons_counting_orientation",
    "task_icons_counting_attribute_binding",
)
unregister_legacy_tasks(LEGACY_TASK_IDS)

TASK_ID = "task_icons_counting_reference_match_count"
_SUPPORTED_VARIANTS: Tuple[str, ...] = (
    "match_type",
    "match_color",
    "match_orientation",
    "match_attribute_binding",
)
_VARIANT_ALIASES: Dict[str, str] = {
    "same_icon_type": "match_type",
    "same_icon_color": "match_color",
    "same_orientation": "match_orientation",
    "attribute_binding_type_color_orientation": "match_attribute_binding",
}
_LEGACY_BUILDERS = {
    "match_type": IconsCountingTypeTask,
    "match_color": IconsCountingColorTask,
    "match_orientation": IconsCountingOrientationTask,
    "match_attribute_binding": IconsCountingAttributeBindingTask,
}
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
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
    """Resolve the active counting predicate for this consolidated task."""

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
    """Render prompt variants for the consolidated counting task."""

    required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "task_family_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description",
            "question_text_by_variant",
            "evidence_hint",
            "answer_hint",
            "json_example",
            "json_example_answer_only",
        ),
        context=f"prompt defaults for {TASK_ID}",
    )
    question_text_map = _PROMPT_DEFAULTS.get("question_text_by_variant", {})
    if not isinstance(question_text_map, Mapping):
        raise ValueError(f"question_text_by_variant must be a mapping for {TASK_ID}")
    question_text = question_text_map.get(str(task_variant))
    if not isinstance(question_text, str) or not question_text.strip():
        raise ValueError(f"missing prompt question text for {TASK_ID}:{task_variant}")

    prompt_selection = render_task_prompt_variants(
        domain="icons",
        task_group="counting",
        bundle_id=str(_PROMPT_DEFAULTS["bundle_id"]),
        task_family_key=str(_PROMPT_DEFAULTS["task_family_key"]),
        task_key=str(_PROMPT_DEFAULTS["task_key"]),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(_PROMPT_DEFAULTS["object_description"]),
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
class IconsCountingReferenceMatchCountTask:
    """Consolidated reference-match counting task spanning four matching predicates."""

    task_id = TASK_ID
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_variant, variant_probabilities = _resolve_task_variant(int(instance_seed), params)
        legacy_task = _LEGACY_BUILDERS[str(task_variant)]()
        legacy_params = strip_consolidated_params(params)
        legacy_params.update(dict(_variant_mapping(_GEN_DEFAULTS, "variant_generation_params", variant=str(task_variant))))
        legacy_params.update(dict(_variant_mapping(_RENDER_DEFAULTS, "variant_render_params", variant=str(task_variant))))
        output = legacy_task.generate(int(instance_seed), params=legacy_params, max_attempts=int(max_attempts))
        prompt_artifacts = _render_prompt(instance_seed=int(instance_seed), task_variant=str(task_variant))
        legacy_trace = dict(output.trace_payload.get("execution_trace") or {})
        return normalize_legacy_icons_output(
            output,
            scene_variant="reference_scene",
            task_variant=str(task_variant),
            legacy_task_id=str(legacy_task.task_id),
            variant_probabilities=variant_probabilities,
            scene_variant_probabilities={"reference_scene": 1.0},
            legacy_scene_variant=str(legacy_trace.get("scene_variant", "reference_scene")),
            legacy_task_variant=str(output.task_variant),
            scene_kind="icons_reference_match_count",
            prompt_bundle_id=str(_PROMPT_DEFAULTS["bundle_id"]),
            prompt_artifacts=prompt_artifacts,
        )


__all__ = ["IconsCountingReferenceMatchCountTask"]
