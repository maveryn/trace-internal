"""Identity-free darts scene state for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

from .rendering import DartInstance, DartScoreOption


@dataclass(frozen=True)
class DartsSceneAxes:
    """Resolved scene and visual axes shared by darts tasks."""

    scene_variant: str
    style_variant: str
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class DartsIntegerAxis:
    """Resolved integer sampling axis with trace metadata."""

    value: int
    support: Tuple[int, ...]
    probabilities: Dict[str, float]


@dataclass(frozen=True)
class DartsScoreSlot:
    """One scoring area on the board."""

    sector_value: int | None
    ring: str
    score: int


@dataclass(frozen=True)
class DartsSampledScene:
    """One sampled darts scene with query-specific witness metadata."""

    darts: Tuple[DartInstance, ...]
    annotation_dart_ids: Tuple[str, ...]
    total_score: int
    score_options: Tuple[DartScoreOption, ...] = ()
    answer_label: str | None = None


__all__ = [
    "DartsIntegerAxis",
    "DartsSceneAxes",
    "DartsSampledScene",
    "DartsScoreSlot",
]
