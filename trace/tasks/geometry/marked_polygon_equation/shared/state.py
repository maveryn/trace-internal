"""State contracts for marked polygon equation diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from PIL import Image, ImageDraw

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]
Side = Tuple[int, int]


@dataclass(frozen=True)
class MarkedEquationCase:
    """Task-bound algebraic construction for one marked polygon diagram."""

    construction_family: str
    draw_kind: str
    answer: int | float
    target_name: str
    variable_name: str
    shape_kind: str
    relation: str
    formula_schema: str
    labels: Mapping[str, str]

    def trace_fields(self) -> Dict[str, Any]:
        """Return JSON-ready semantic fields shared by verifier trace sections."""

        return {
            "construction_family": str(self.construction_family),
            "draw_kind": str(self.draw_kind),
            "shape_kind": str(self.shape_kind),
            "relation": str(self.relation),
            "formula_schema": str(self.formula_schema),
            "target_name": str(self.target_name),
            "variable_name": str(self.variable_name),
            "labels": dict(self.labels),
            "answer_value": self.answer,
        }


@dataclass
class RenderContext:
    """Mutable PIL drawing context with resolved diagram style."""

    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    accent_color: Color
    fill_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]
    scene_transform: Any


@dataclass(frozen=True)
class RenderedMarkedEquationScene:
    """Rendered image and projected labeled construction points."""

    image: Image.Image
    annotation_points: Mapping[str, Point]
    render_map: Dict[str, Any]
    scene_entities: Tuple[Dict[str, Any], ...]


__all__ = [
    "BBox",
    "Color",
    "MarkedEquationCase",
    "Point",
    "RenderContext",
    "RenderedMarkedEquationScene",
    "Side",
]
