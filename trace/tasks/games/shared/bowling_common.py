"""Shared Bowling helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


SUPPORTED_BOWLING_QUERY_IDS: Tuple[str, ...] = (
    "first_pin_hit_label",
    "spare_path_label",
)
SUPPORTED_BOWLING_SCENE_VARIANTS: Tuple[str, ...] = ("lane_rack",)
SUPPORTED_BOWLING_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "cosmic",
    "paper",
    "tournament",
    "retro",
)


@dataclass(frozen=True)
class BowlingPin:
    """One visible bowling pin."""

    pin_id: str
    label: str
    rack_index: int
    row: int
    col: int
    color_index: int
    standing: bool = True
    x_norm: float | None = None
    y_norm: float | None = None


@dataclass(frozen=True)
class BowlingPathOption:
    """One labeled aiming path."""

    path_id: str
    label: str
    aim_x_norm: float
    color_index: int


@dataclass(frozen=True)
class BowlingSample:
    """Generated bowling scene state."""

    query_id: str
    scene_variant: str
    style_variant: str
    answer: str
    pins: Tuple[BowlingPin, ...]
    path_options: Tuple[BowlingPathOption, ...]
    ball_x_norm: float
    target_pin_id: str | None
    target_pin_label: str | None
    target_path_id: str | None
    target_path_label: str | None
    remaining_pin_ids: Tuple[str, ...]
    evidence_entity_ids: Tuple[str, ...]
    construction_mode: str
    path_visible_fraction: float | None = None
    path_clearance_px: float | None = None


def pin_entity_id(rack_index: int) -> str:
    """Return stable entity id for one rack pin."""

    return f"pin_{int(rack_index)}"


def path_entity_id(path_index: int) -> str:
    """Return stable entity id for one path option marker."""

    return f"path_{int(path_index)}"


def option_label(index: int) -> str:
    """Return a short numeric path-option label."""

    return str(int(index) + 1)


def validate_bowling_sample(sample: BowlingSample) -> None:
    """Validate that answer and evidence match the active Bowling query."""

    query = str(sample.query_id)
    pin_ids = [str(pin.pin_id) for pin in sample.pins]
    pin_labels = [str(pin.label) for pin in sample.pins]
    path_ids = [str(path.path_id) for path in sample.path_options]
    path_labels = [str(path.label) for path in sample.path_options]
    if len(pin_ids) != len(set(pin_ids)):
        raise ValueError("bowling pin ids must be unique")
    if len(pin_labels) != len(set(pin_labels)):
        raise ValueError("bowling pin labels must be unique")
    if len(path_ids) != len(set(path_ids)):
        raise ValueError("bowling path ids must be unique")
    if len(path_labels) != len(set(path_labels)):
        raise ValueError("bowling path labels must be unique")
    standing_ids = {str(pin.pin_id) for pin in sample.pins if bool(pin.standing)}
    known_entities = set(pin_ids) | set(path_ids) | {"ball"}
    if not set(sample.evidence_entity_ids) <= known_entities:
        raise ValueError("bowling evidence references unknown entities")
    if not set(sample.remaining_pin_ids) <= standing_ids:
        raise ValueError("bowling remaining pins must be standing pins")

    if query == "first_pin_hit_label":
        if sample.target_pin_id is None or sample.target_pin_label is None:
            raise ValueError("first_pin_hit_label requires a target pin")
        if str(sample.target_pin_id) not in standing_ids:
            raise ValueError("first-hit target pin must be standing")
        expected_answer = str(sample.target_pin_label)
        expected_evidence = {str(sample.target_pin_id)}
    elif query == "spare_path_label":
        if sample.target_path_id is None or sample.target_path_label is None:
            raise ValueError("spare_path_label requires a target path")
        if str(sample.target_path_id) not in set(path_ids):
            raise ValueError("target path id must reference a visible path")
        if len(sample.remaining_pin_ids) < 1:
            raise ValueError("spare_path_label needs at least one remaining pin")
        expected_answer = str(sample.target_path_label)
        expected_evidence = {str(sample.target_path_id)}
    else:
        raise ValueError(f"unsupported bowling query_id: {sample.query_id}")
    if str(sample.answer) != str(expected_answer):
        raise ValueError("bowling answer does not match active query")
    if set(sample.evidence_entity_ids) != expected_evidence:
        raise ValueError("bowling evidence ids do not match active query")


__all__ = [
    "SUPPORTED_BOWLING_QUERY_IDS",
    "SUPPORTED_BOWLING_SCENE_VARIANTS",
    "SUPPORTED_BOWLING_STYLE_VARIANTS",
    "BowlingPathOption",
    "BowlingPin",
    "BowlingSample",
    "option_label",
    "path_entity_id",
    "pin_entity_id",
    "validate_bowling_sample",
]
