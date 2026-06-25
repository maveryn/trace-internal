"""Passive state contracts for slot-machine games tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from .defaults import PAYLINE_COORDS, PAYLINE_IDS, REEL_COUNT, ROW_COUNT, SUPPORTED_SCENE_VARIANTS, SUPPORTED_STYLE_VARIANTS, SYMBOL_KEYS


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
    winning_payline_ids: Tuple[str, ...]


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


PAYLINE_CELLS_BY_ID = {
    str(payline_id): tuple((int(row), int(col)) for row, col in coords)
    for payline_id, coords in zip(PAYLINE_IDS, PAYLINE_COORDS)
}


def payline_entity_id(payline_key: str) -> str:
    """Return the stable rendered entity id for one conceptual payline."""

    key = str(payline_key)
    if key not in PAYLINE_CELLS_BY_ID:
        raise ValueError(f"unsupported slot-machine payline: {key}")
    return f"payline_{key}"


def cell_grid(scene: SlotMachineScene) -> tuple[tuple[str, ...], ...]:
    """Return a row-major symbol grid for trace/debug output."""

    grid = [["" for _ in range(REEL_COUNT)] for _ in range(ROW_COUNT)]
    for cell in scene.cells:
        grid[int(cell.row)][int(cell.col)] = str(cell.symbol_key)
    return tuple(tuple(row) for row in grid)


def winning_payline_ids_for_grid(grid: tuple[tuple[str, ...], ...]) -> tuple[str, ...]:
    """Return conceptual payline ids whose three symbols match."""

    winners: list[str] = []
    for payline_key in PAYLINE_IDS:
        cells = PAYLINE_CELLS_BY_ID[str(payline_key)]
        symbols = {str(grid[int(row)][int(col)]) for row, col in cells}
        if len(symbols) == 1:
            winners.append(str(payline_key))
    return tuple(winners)


def validate_slot_machine_scene(scene: SlotMachineScene) -> None:
    """Validate scene consistency independent of one public objective."""

    if scene.scene_variant not in SUPPORTED_SCENE_VARIANTS:
        raise ValueError(f"unsupported slot-machine scene variant: {scene.scene_variant}")
    if scene.style_variant not in SUPPORTED_STYLE_VARIANTS:
        raise ValueError(f"unsupported slot-machine style variant: {scene.style_variant}")
    if len(scene.cells) != REEL_COUNT * ROW_COUNT:
        raise ValueError("slot-machine scene must contain exactly 3 x 3 visible cells")
    seen = {(int(cell.row), int(cell.col)) for cell in scene.cells}
    expected = {(row, col) for row in range(ROW_COUNT) for col in range(REEL_COUNT)}
    if seen != expected:
        raise ValueError("slot-machine cells must cover every visible reel position exactly once")
    if any(str(cell.symbol_key) not in SYMBOL_KEYS for cell in scene.cells):
        raise ValueError("slot-machine cells use unsupported symbols")
    grid = cell_grid(scene)
    actual_winning_paylines = winning_payline_ids_for_grid(grid)
    if tuple(scene.winning_payline_ids) != actual_winning_paylines:
        raise ValueError("slot-machine winning paylines must match the symbol grid")


__all__ = [
    "SlotCell",
    "SlotMachineAxes",
    "SlotMachineScene",
    "PAYLINE_CELLS_BY_ID",
    "cell_grid",
    "payline_entity_id",
    "slot_cell_id",
    "validate_slot_machine_scene",
    "winning_payline_ids_for_grid",
]
