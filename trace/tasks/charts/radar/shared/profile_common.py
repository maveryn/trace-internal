"""Shared constants and specs for radar chart profile tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from .....core.scene_config import get_scene_defaults
from ....shared.config_defaults import group_default, split_scene_generation_rendering_prompt_defaults
from ....shared.font_assets import sample_font_family
from ....shared.render_variation import resolve_render_rgb
from ...shared.visual_defaults import load_chart_scene_background_defaults, load_chart_scene_noise_defaults

TASK_ID = "charts_radar_query_base"
SCENE_ID = "radar"
SMALL_MULTIPLE_VARIANTS = frozenset(
    {
        "highlighted_metric_threshold_panel_count",
        "threshold_metric_count_for_panel",
        "matching_condition_panel_count",
    }
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "small_multiple_radar",
    "single_radar_multi_profile",
)

_SCENE_DEFAULTS = get_scene_defaults("charts", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_chart_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)

_PANEL_LABELS: Tuple[str, ...] = tuple("ABCDEFGH")
_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "highlighted_metric_threshold_panel_count": 0.56,
    "threshold_metric_count_for_panel": 0.58,
    "profile_advantage_count": 0.70,
    "matching_condition_panel_count": 0.82,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {
    "small_multiple_radar": 0.72,
    "single_radar_multi_profile": 0.58,
}

BBox = Tuple[float, float, float, float]
RGB = Tuple[int, int, int]
Point = List[float]


@dataclass(frozen=True)
class _Profile:
    profile_label: str
    values: Dict[str, int]
    color_rgb: RGB


@dataclass(frozen=True)
class _Panel:
    panel_label: str
    profiles: Tuple[_Profile, ...]


@dataclass(frozen=True)
class _Query:
    query_id: str
    scene_variant: str
    answer: str | int
    answer_type: str
    metric_label: str
    panel_label: str
    profile_a_label: str
    profile_b_label: str
    threshold_value: int
    minimum_metric_count: int
    annotation_point_ids: Tuple[str, ...]
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    metrics: Tuple[str, ...]
    panels: Tuple[_Panel, ...]
    query: _Query


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    point_bboxes: Dict[str, List[float]]
    panel_bboxes: Dict[str, List[float]]
    panel_title_bboxes: Dict[str, List[float]]
    legend_bboxes: Dict[str, List[float]]
    plot_bbox_px: List[float]
    render_meta: Dict[str, Any]


def _sample_chart_font_family(instance_seed: int, params: Mapping[str, Any]) -> str:
    return str(
        sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.chart_font",
            params=params,
            exclude_tags=("display",),
            explicit_key="chart_font_family",
            weights_key="chart_font_family_weights",
        )
    )


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), _RENDER_DEFAULTS.get(str(key), int(fallback))))


def _resolve_gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw = params.get("profile_palette_rgb", _RENDER_DEFAULTS.get("profile_palette_rgb", ()))
    colors: List[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            if isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) >= 3:
                colors.append(tuple(max(0, min(255, int(channel))) for channel in item[:3]))  # type: ignore[index]
    if colors:
        return tuple(colors)
    return (
        (41, 108, 179),
        (205, 82, 74),
        (55, 148, 104),
        (139, 92, 186),
        (214, 139, 44),
        (54, 148, 168),
    )


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]
