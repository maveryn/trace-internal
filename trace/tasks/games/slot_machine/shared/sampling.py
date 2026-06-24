"""Sampling primitives for slot-machine games tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default

from .defaults import (
    PAYLINE_ROW_IDS,
    SCENE_NAMESPACE,
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_STYLE_VARIANTS,
    SYMBOL_KEYS,
)
from .state import SlotCell, SlotMachineAxes, SlotMachineScene, validate_slot_machine_scene


def _uniform_probability(values: Sequence[str]) -> dict[str, float]:
    """Return a JSON-friendly uniform probability map for finite axes."""

    items = tuple(str(value) for value in values)
    return {str(value): 1.0 / float(len(items)) for value in items}


def _sample_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    values: Sequence[str],
    namespace: str,
) -> str:
    """Resolve a scene axis from explicit params, sample cursor, or RNG."""

    explicit = params.get(str(key))
    choices = tuple(str(value) for value in values)
    if explicit is not None:
        value = str(explicit)
        if value not in choices:
            raise ValueError(f"unsupported slot-machine {key}: {explicit}")
        return value
    cursor = params.get("_sample_cursor")
    if cursor is not None and bool(group_default(defaults, f"balanced_{key}_sampling", True)):
        return choices[abs(int(cursor)) % len(choices)]
    weights = params.get(f"{key}_weights", group_default(defaults, f"{key}_weights", {}))
    rng = spawn_rng(int(instance_seed), str(namespace))
    parsed = [max(0.0, float(dict(weights or {}).get(str(value), 1.0))) for value in choices]
    total = sum(parsed) or float(len(choices))
    threshold = rng.random() * total
    cursor_value = 0.0
    for value, weight in zip(choices, parsed):
        cursor_value += float(weight if sum(parsed) else 1.0)
        if threshold <= cursor_value:
            return str(value)
    return str(choices[-1])


def resolve_slot_machine_axes(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> SlotMachineAxes:
    """Resolve nonsemantic scene and style axes for a slot-machine instance."""

    scene_variant = _sample_axis(
        instance_seed=int(instance_seed),
        params=params,
        defaults=gen_defaults,
        key="scene_variant",
        values=SUPPORTED_SCENE_VARIANTS,
        namespace=f"{SCENE_NAMESPACE}.scene_variant",
    )
    style_variant = _sample_axis(
        instance_seed=int(instance_seed),
        params=params,
        defaults=gen_defaults,
        key="style_variant",
        values=SUPPORTED_STYLE_VARIANTS,
        namespace=f"{SCENE_NAMESPACE}.style_variant",
    )
    return SlotMachineAxes(
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        scene_variant_probabilities=_uniform_probability(SUPPORTED_SCENE_VARIANTS),
        style_variant_probabilities=_uniform_probability(SUPPORTED_STYLE_VARIANTS),
    )


def sample_slot_machine_grid(
    *,
    rng: Any,
    axes: SlotMachineAxes,
    target_winning_count: int,
) -> SlotMachineScene:
    """Sample a 5 x 3 reel window with exactly the requested winning rows."""

    target = int(target_winning_count)
    if target < 0 or target > len(PAYLINE_ROW_IDS):
        raise ValueError("target_winning_count must be between 0 and 3")
    winning_rows = tuple(sorted(rng.sample(list(PAYLINE_ROW_IDS), target)))
    cells: list[SlotCell] = []
    for row in range(3):
        if row in winning_rows:
            symbol = str(rng.choice(SYMBOL_KEYS))
            row_symbols = [symbol for _ in range(5)]
        else:
            first = str(rng.choice(SYMBOL_KEYS))
            second_choices = [symbol for symbol in SYMBOL_KEYS if symbol != first]
            second = str(rng.choice(second_choices))
            row_symbols = [str(rng.choice(SYMBOL_KEYS)) for _ in range(5)]
            row_symbols[0] = first
            row_symbols[int(rng.randrange(1, 5))] = second
        for col, symbol in enumerate(row_symbols):
            cells.append(SlotCell(row=int(row), col=int(col), symbol_key=str(symbol)))
    scene = SlotMachineScene(
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        cells=tuple(cells),
        winning_rows=tuple(winning_rows),
    )
    validate_slot_machine_scene(scene)
    return scene


__all__ = [
    "resolve_slot_machine_axes",
    "sample_slot_machine_grid",
]
