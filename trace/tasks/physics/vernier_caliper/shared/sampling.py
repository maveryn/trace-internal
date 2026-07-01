"""Sampling helpers for Vernier-caliper apparatus parameters."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import uniform_probability_map

from .state import (
    DEFAULTS,
    SCENE_NAMESPACE,
    VERNIER_DIVISIONS,
    CaliperScenario,
)


def probability_map(values: Sequence[int], selected: int | None = None) -> Dict[str, float]:
    """Return a string-keyed probability map for an integer support."""

    resolved = tuple(int(value) for value in values)
    if selected is not None:
        return {
            str(int(value)): (1.0 if int(value) == int(selected) else 0.0)
            for value in resolved
        }
    if not resolved:
        return {}
    probability = 1.0 / float(len(resolved))
    return {str(int(value)): float(probability) for value in resolved}


def integer_support(
    defaults: Mapping[str, Any],
    key: str,
    fallback: Sequence[int],
) -> Tuple[int, ...]:
    """Resolve a non-empty sorted integer support from scene defaults."""

    raw = group_default(defaults, str(key), tuple(int(value) for value in fallback))
    support = tuple(sorted({int(value) for value in raw}))
    if not support:
        raise ValueError(f"{key} must contain at least one integer")
    return support


def main_mm_support(defaults: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return supported main-scale millimeter readings."""

    return integer_support(defaults, "main_mm_support", DEFAULTS.main_mm_support)


def aligned_tick_support(defaults: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return supported aligned Vernier tick indices."""

    support = integer_support(
        defaults,
        "aligned_vernier_tick_support",
        DEFAULTS.aligned_vernier_tick_support,
    )
    if any(value < 0 or value >= VERNIER_DIVISIONS for value in support):
        raise ValueError("aligned_vernier_tick_support must be in 0..9")
    return support


def resolve_caliper_scenario(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    namespace: str = SCENE_NAMESPACE,
) -> CaliperScenario:
    """Resolve operands while preserving answer-balanced caliper sampling invariants."""

    main_support = main_mm_support(defaults)
    tick_support = aligned_tick_support(defaults)
    explicit_main = params.get("main_mm")
    explicit_tick = params.get("aligned_vernier_tick", params.get("vernier_tick"))
    explicit_answer = params.get("target_answer", params.get("answer_mm"))
    if explicit_answer is not None:
        answer_tenths = int(round(float(explicit_answer) * 10.0))
        inferred_main_mm = int(answer_tenths // 10)
        inferred_aligned_tick = int(answer_tenths % 10)
        main_mm = int(explicit_main) if explicit_main is not None else inferred_main_mm
        aligned_tick = (
            int(explicit_tick) if explicit_tick is not None else inferred_aligned_tick
        )
        if main_mm not in set(main_support) or aligned_tick not in set(tick_support):
            raise ValueError(f"unsupported target_answer for Vernier caliper: {explicit_answer}")
        if int(main_mm * 10 + aligned_tick) != int(answer_tenths):
            raise ValueError(
                "target_answer is inconsistent with explicit main_mm or "
                "aligned_vernier_tick"
            )
    else:
        if explicit_main is not None:
            main_mm = int(explicit_main)
            if main_mm not in set(main_support):
                raise ValueError(f"main_mm={main_mm} is outside configured support")
        else:
            rng = spawn_rng(int(instance_seed), f"{namespace}.main_mm")
            main_mm = int(rng.choice(main_support))

        if explicit_tick is not None:
            aligned_tick = int(explicit_tick)
            if aligned_tick not in set(tick_support):
                raise ValueError(
                    f"aligned_vernier_tick={aligned_tick} is outside configured support"
                )
        else:
            rng = spawn_rng(int(instance_seed), f"{namespace}.aligned_vernier_tick")
            aligned_tick = int(rng.choice(tick_support))

    answer_tenths = int(main_mm * 10 + aligned_tick)
    answer_mm = round(float(answer_tenths) / 10.0, 1)
    answer_support = [
        int(main * 10 + tick)
        for main in main_support
        for tick in tick_support
    ]
    selected = int(answer_tenths)
    return CaliperScenario(
        main_mm=int(main_mm),
        aligned_vernier_tick=int(aligned_tick),
        answer_mm=float(answer_mm),
        target_answer_probabilities={
            f"{value / 10.0:.1f}": (1.0 if int(value) == selected else 0.0)
            for value in answer_support
        },
        main_mm_probabilities=probability_map(main_support, selected=int(main_mm)),
        aligned_vernier_tick_probabilities=uniform_probability_map(
            tick_support,
            selected=int(aligned_tick),
        ),
    )


__all__ = [
    "aligned_tick_support",
    "integer_support",
    "main_mm_support",
    "probability_map",
    "resolve_caliper_scenario",
]
