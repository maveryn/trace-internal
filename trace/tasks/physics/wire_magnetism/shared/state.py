"""State and dataclasses for wire-magnetism diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from PIL import Image


SCENE_ID = "wire_magnetism"
SCENE_NAMESPACE = "physics_wire_magnetism"
SCENE_PROMPT_KEY = "wire_magnetism_diagram"
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
SUPPORTED_ORIENTATIONS: Tuple[str, ...] = ("horizontal", "vertical")


@dataclass(frozen=True)
class WireMagnetismDefaults:
    """Stable fallback defaults for wire-magnetism diagrams."""

    canvas_width: int = 1080
    canvas_height: int = 700


@dataclass(frozen=True)
class WireScenario:
    """Resolved physical setup and answer binding for one wire diagram."""

    orientation: str
    current_direction: str
    point_side: str
    current_vector_phys: Tuple[int, int]
    point_offset_phys: Tuple[int, int]
    field_direction: str
    option_map: Dict[str, str]
    correct_label: str
    orientation_probabilities: Dict[str, float]
    current_direction_probabilities: Dict[str, float]
    point_side_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class RenderedWireMagnetismScene:
    """Rendered wire-magnetism scene plus verifier-facing metadata."""

    image: Image.Image
    annotation_bboxes: Dict[str, List[float]]
    annotation_entity_ids: List[str]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


__all__ = [
    "OPTION_LABELS",
    "RenderedWireMagnetismScene",
    "SCENE_ID",
    "SCENE_NAMESPACE",
    "SCENE_PROMPT_KEY",
    "SUPPORTED_ORIENTATIONS",
    "WireMagnetismDefaults",
    "WireScenario",
]
