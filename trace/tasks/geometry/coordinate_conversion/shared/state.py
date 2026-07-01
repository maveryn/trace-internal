"""Passive state records for coordinate-conversion geometry tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PIL import Image

Point = tuple[float, float]
Segment = tuple[Point, Point]


@dataclass(frozen=True)
class CartesianPointCase:
    """One Cartesian point and its polar components."""

    x: int
    y: int
    radius: float
    angle_degrees: float
    selected_answer: float
    answer_support_count: int
    answer_candidate_probabilities: dict[str, float]


@dataclass(frozen=True)
class PolarPointCase:
    """One polar point and its Cartesian components."""

    radius: int
    theta_degrees: int
    x_component: float
    y_component: float
    selected_answer: float
    answer_support_count: int
    answer_candidate_probabilities: dict[str, float]


@dataclass(frozen=True)
class RenderedCoordinateScene:
    """Rendered coordinate-conversion scene with projection metadata."""

    image: Image.Image
    render_map: dict[str, Any]
    render_spec: dict[str, Any]
    scene_entities: list[dict[str, Any]]
    background_meta: dict[str, Any]
    style_meta: dict[str, Any]


__all__ = [
    "CartesianPointCase",
    "Point",
    "PolarPointCase",
    "RenderedCoordinateScene",
    "Segment",
]
