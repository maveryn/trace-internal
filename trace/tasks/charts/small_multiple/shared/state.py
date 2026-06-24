"""Scene-local state for small-multiple composition charts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from PIL import Image


DOMAIN = "charts"
SCENE_ID = "small_multiple"
SCENE_NAMESPACE = "charts.small_multiple"

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("small_multiple_pie", "small_multiple_donut")

SEGMENT_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (54, 119, 196),
    (219, 107, 59),
    (84, 157, 85),
    (162, 94, 179),
    (224, 168, 55),
    (69, 178, 176),
    (197, 83, 125),
)


@dataclass(frozen=True)
class PanelSpec:
    label: str
    total: int
    shares_by_segment: Dict[str, int]


@dataclass(frozen=True)
class SmallMultipleDataset:
    panels: Tuple[PanelSpec, ...]
    segment_labels: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class AnnotationRole:
    role: str
    panel: str
    segment: str | None = None


@dataclass(frozen=True)
class SmallMultipleSelection:
    answer_value: int
    annotation_values: Tuple[int, ...]
    annotation_roles: Tuple[AnnotationRole, ...]
    trace: Dict[str, Any]
    question_format: str


@dataclass(frozen=True)
class RenderedSmallMultiples:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    panel_traces: Tuple[Dict[str, Any], ...]
    plot_bbox_px: Tuple[int, int, int, int]
    annotation_bbox_by_key: Dict[Tuple[str, str], List[float]]
    total_bbox_by_panel: Dict[str, List[float]]
    legend_bbox_px: List[float]
    legend_item_bboxes_px: Dict[str, List[float]]
    layout_jitter_meta: Dict[str, Any]
    render_meta: Dict[str, Any]
