"""Sampling helpers for wire-magnetism diagrams."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant

from .state import OPTION_LABELS, SUPPORTED_ORIENTATIONS, WireScenario


CURRENT_OPTIONS: Dict[str, Tuple[Tuple[str, Tuple[int, int]], ...]] = {
    "horizontal": (("right", (1, 0)), ("left", (-1, 0))),
    "vertical": (("up", (0, 1)), ("down", (0, -1))),
}
POINT_SIDE_OPTIONS: Dict[str, Tuple[Tuple[str, Tuple[int, int]], ...]] = {
    "horizontal": (("above", (0, 1)), ("below", (0, -1))),
    "vertical": (("right", (1, 0)), ("left", (-1, 0))),
}


def probability_map(values: Sequence[str], selected: str | None = None) -> Dict[str, float]:
    """Return a string-keyed probability map for a finite support."""

    supported = tuple(str(value) for value in values if str(value))
    if selected is not None:
        return {value: (1.0 if value == str(selected) else 0.0) for value in supported}
    probability = 1.0 / float(len(supported)) if supported else 0.0
    return {value: float(probability) for value in supported}


def _options_for_orientation(
    options_by_orientation: Mapping[str, Tuple[Tuple[str, Tuple[int, int]], ...]],
    orientation: str,
) -> Tuple[Tuple[str, Tuple[int, int]], ...]:
    options = tuple(options_by_orientation.get(str(orientation), ()))
    if not options:
        raise ValueError(f"unsupported wire orientation: {orientation}")
    return options


def _resolve_orientation(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{namespace}.orientation")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=defaults,
        supported_variants=SUPPORTED_ORIENTATIONS,
        explicit_key="orientation",
        weights_key="orientation_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_ORIENTATIONS,
        balance_flag_key="balanced_orientation_sampling",
        explicit_key="orientation",
        weights_key="orientation_weights",
        sampling_namespace=f"{namespace}.orientation",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_named_vector(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support: Tuple[Tuple[str, Tuple[int, int]], ...],
    explicit_key: str,
    namespace: str,
) -> Tuple[str, Tuple[int, int], Dict[str, float]]:
    labels = tuple(str(label) for label, _ in support)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        selected = str(explicit)
        if selected not in labels:
            raise ValueError(f"unsupported wire {explicit_key}: {selected}; supported: {labels}")
        vector = next(vector for label, vector in support if str(label) == selected)
        return selected, tuple(int(value) for value in vector), probability_map(labels, selected=selected)

    sample_cursor = params.get("_sample_cursor")
    choice_namespace = str(namespace) if sample_cursor is None else f"{namespace}.cursor.{int(sample_cursor)}"
    rng = spawn_rng(int(instance_seed), choice_namespace)
    selected_index = int(rng.randrange(len(labels)))
    selected = str(labels[selected_index])
    vector = tuple(int(value) for value in support[selected_index][1])
    return selected, vector, probability_map(labels)


def _resolve_target_label(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    explicit = params.get("target_label", params.get("correct_option_letter", params.get("target_answer")))
    if explicit is not None:
        selected = str(explicit).strip().upper()
        if selected not in OPTION_LABELS:
            raise ValueError(f"unsupported wire-magnetism target option: {selected}")
        return selected, probability_map(OPTION_LABELS, selected=selected)

    if bool(params.get("balanced_target_answer_sampling", group_default(defaults, "balanced_target_answer_sampling", True))):
        rng = spawn_rng(int(instance_seed), f"{namespace}.target_label")
        selected = str(rng.choice(OPTION_LABELS))
    else:
        rng = spawn_rng(int(instance_seed), f"{namespace}.target_label")
        selected = str(rng.choice(OPTION_LABELS))
    return selected, probability_map(OPTION_LABELS)


def _field_direction_for(current_vector: Tuple[int, int], point_offset: Tuple[int, int]) -> str:
    z_sign = int((int(current_vector[0]) * int(point_offset[1])) - (int(current_vector[1]) * int(point_offset[0])))
    if z_sign == 0:
        raise ValueError("wire current and point offset vectors must not be parallel")
    return "out_of_page" if z_sign > 0 else "into_page"


def build_wire_scenario(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    namespace: str,
) -> WireScenario:
    """Resolve one physical wire scenario and unique option-letter answer."""

    orientation, orientation_probs = _resolve_orientation(
        instance_seed=int(instance_seed),
        params=params,
        defaults=defaults,
        namespace=str(namespace),
    )
    current_options = _options_for_orientation(CURRENT_OPTIONS, orientation)
    side_options = _options_for_orientation(POINT_SIDE_OPTIONS, orientation)
    current_name, current_vector, current_probs = _resolve_named_vector(
        instance_seed=int(instance_seed),
        params=params,
        support=current_options,
        explicit_key="current_direction",
        namespace=f"{namespace}.current_direction.{orientation}",
    )
    point_side, point_offset, point_probs = _resolve_named_vector(
        instance_seed=int(instance_seed),
        params=params,
        support=side_options,
        explicit_key="point_side",
        namespace=f"{namespace}.point_side.{orientation}",
    )
    field_direction = _field_direction_for(current_vector, point_offset)
    correct_label, target_probs = _resolve_target_label(
        instance_seed=int(instance_seed),
        params=params,
        defaults=defaults,
        namespace=str(namespace),
    )
    distractors = ["north", "south", "east", "west"]
    distractors.append("into_page" if field_direction == "out_of_page" else "out_of_page")
    option_map: Dict[str, str] = {}
    distractor_cursor = 0
    for label in OPTION_LABELS:
        if str(label) == str(correct_label):
            option_map[str(label)] = str(field_direction)
        else:
            option_map[str(label)] = str(distractors[distractor_cursor])
            distractor_cursor += 1
    return WireScenario(
        orientation=str(orientation),
        current_direction=str(current_name),
        point_side=str(point_side),
        current_vector_phys=tuple(int(value) for value in current_vector),
        point_offset_phys=tuple(int(value) for value in point_offset),
        field_direction=str(field_direction),
        option_map=dict(option_map),
        correct_label=str(correct_label),
        orientation_probabilities=dict(orientation_probs),
        current_direction_probabilities=dict(current_probs),
        point_side_probabilities=dict(point_probs),
        target_answer_probabilities=dict(target_probs),
    )


__all__ = [
    "build_wire_scenario",
    "probability_map",
]
