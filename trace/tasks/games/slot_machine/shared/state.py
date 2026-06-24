"""Passive state contracts for slot-machine games tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .defaults import REEL_COUNT, ROW_COUNT, SUPPORTED_SCENE_VARIANTS, SUPPORTED_STYLE_VARIANTS, SYMBOL_KEYS


@dataclass(frozen=True)
class SlotCell:
    """One visible symbol cell in the reel window."""

    row: int
    col: int
    symbol_key: str


@dataclass(frozen=True)
class SlotMachineScene:
    """Generated slot-machine state before rendering."""

    scene_variant: str
    style_variant: str
    cells: Tuple[SlotCell, ...]
    winning_rows: Tuple[int, ...]


@dataclass(frozen=True)
class SlotMachineAxes:
    """Resolved nonsemantic slot-machine scene axes."""

    scene_variant: str
    style_variant: str
    scene_variant_probabilities: dict[str, float]
    style_variant_probabilities: dict[str, float]


def slot_cell_id(row: int, col: int) -> str:
    """Return the stable rendered entity id for one reel cell."""

    return f"cell_{int(row)}_{int(col)}"


def payline_id(row: int) -> str:
    """Return the stable rendered entity id for one horizontal payline."""

    return f"payline_{int(row)}"


def cell_grid(scene: SlotMachineScene) -> tuple[tuple[str, ...], ...]:
    """Return a row-major symbol grid for trace/debug output."""

    grid = [["" for _ in range(REEL_COUNT)] for _ in range(ROW_COUNT)]
    for cell in scene.cells:
        grid[int(cell.row)][int(cell.col)] = str(cell.symbol_key)
    return tuple(tuple(row) for row in grid)


def validate_slot_machine_scene(scene: SlotMachineScene) -> None:
    """Validate scene consistency independent of one public objective."""

    if scene.scene_variant not in SUPPORTED_SCENE_VARIANTS:
        raise ValueError(f"unsupported slot-machine scene variant: {scene.scene_variant}")
    if scene.style_variant not in SUPPORTED_STYLE_VARIANTS:
        raise ValueError(f"unsupported slot-machine style variant: {scene.style_variant}")
    if len(scene.cells) != REEL_COUNT * ROW_COUNT:
        raise ValueError("slot-machine scene must contain exactly 5 x 3 visible cells")
    seen = {(int(cell.row), int(cell.col)) for cell in scene.cells}
    expected = {(row, col) for row in range(ROW_COUNT) for col in range(REEL_COUNT)}
    if seen != expected:
        raise ValueError("slot-machine cells must cover every visible reel position exactly once")
    if any(str(cell.symbol_key) not in SYMBOL_KEYS for cell in scene.cells):
        raise ValueError("slot-machine cells use unsupported symbols")
    grid = cell_grid(scene)
    actual_winning_rows = tuple(row for row in range(ROW_COUNT) if len(set(grid[row])) == 1)
    if tuple(scene.winning_rows) != actual_winning_rows:
        raise ValueError("slot-machine winning rows must match the symbol grid")


__all__ = [
    "SlotCell",
    "SlotMachineAxes",
    "SlotMachineScene",
    "cell_grid",
    "payline_id",
    "slot_cell_id",
    "validate_slot_machine_scene",
]
