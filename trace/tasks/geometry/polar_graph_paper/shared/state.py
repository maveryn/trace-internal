"""State objects for polar graph paper rendering and sampling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ReadoutComponent = Literal["radius", "angle_degrees"]


@dataclass(frozen=True)
class PolarReadoutOption:
    label: str
    value: int
    display_text: str


@dataclass(frozen=True)
class PolarReadoutCase:
    component: ReadoutComponent
    radius: int
    theta_degrees: int
    correct_value: int
    correct_label: str
    options: tuple[PolarReadoutOption, ...]
    option_label_probabilities: dict[str, float]

    @property
    def option_values_by_label(self) -> dict[str, int]:
        return {option.label: option.value for option in self.options}

    @property
    def option_display_by_label(self) -> dict[str, str]:
        return {option.label: option.display_text for option in self.options}


@dataclass(frozen=True)
class RenderedPolarGraphPaperScene:
    image: Any
    render_map: dict[str, Any]
    render_spec: dict[str, Any]
    style_metadata: dict[str, Any]
