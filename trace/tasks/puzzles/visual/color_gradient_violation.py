"""Color-gradient swatch puzzle tasks."""

from __future__ import annotations

import colorsys
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.color_distance import color_distance
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_centered_text, draw_rounded_rect
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import load_font, temporary_default_font_family
from ..shared.common import projected_puzzle_bbox_annotation, resolve_puzzle_axis_variant
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


VIOLATION_TASK_ID = "task_puzzles__color_gradient__color_gradient_violation_cell_label"
COMPLETION_TASK_ID = "task_puzzles__color_gradient__color_gradient_completion_label"
SCENE_ID = "color_gradient"
VIOLATION_QUERY_ID = "color_gradient_violation_cell_label"
COMPLETION_QUERY_ID = "linear_gradient_completion_label"
TASK_ID = VIOLATION_TASK_ID
QUERY_ID = VIOLATION_QUERY_ID

_GRID_SIZE_VARIANTS: Tuple[str, ...] = ("3x3", "4x4")
_RULE_VARIANTS: Tuple[str, ...] = (
    "column_hue_row_lightness",
    "row_hue_column_lightness",
    "column_hue_row_saturation",
)
_COMPLETION_LENGTH_VARIANTS: Tuple[str, ...] = ("5_cell", "6_cell", "7_cell")
_COMPLETION_OPTION_COUNT_VARIANTS: Tuple[str, ...] = ("4_options", "5_options", "6_options")
_COMPLETION_RULE_VARIANTS: Tuple[str, ...] = ("hue_gradient", "lightness_gradient", "hue_lightness_gradient")
_SCENE_VARIANTS: Tuple[str, ...] = ("swatch_clean", "swatch_card", "swatch_notebook")
_LABELS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_SCENE_LOAD_BY_VARIANT = {
    "swatch_clean": 0.16,
    "swatch_card": 0.22,
    "swatch_notebook": 0.26,
}
_RULE_LOAD_BY_VARIANT = {
    "column_hue_row_lightness": 0.46,
    "row_hue_column_lightness": 0.50,
    "column_hue_row_saturation": 0.58,
}
_COMPLETION_RULE_LOAD_BY_VARIANT = {
    "hue_gradient": 0.42,
    "lightness_gradient": 0.38,
    "hue_lightness_gradient": 0.54,
}


@dataclass(frozen=True)
class _RenderParams:
    """Resolved rendering parameters for the color-gradient scene."""

    canvas_width: int
    canvas_height: int
    swatch_size_px: int
    swatch_gap_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    panel_border_width_px: int
    swatch_corner_radius_px: int
    swatch_border_width_px: int
    label_chip_size_px: int
    label_margin_px: int
    label_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    swatch_border_rgb: Tuple[int, int, int]
    notebook_line_rgb: Tuple[int, int, int]
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class _CellSpec:
    """One swatch-grid cell before rendering."""

    cell_id: str
    label: str
    row: int
    col: int
    expected_hsl: Tuple[float, float, float]
    observed_hsl: Tuple[float, float, float]
    expected_rgb: Tuple[int, int, int]
    observed_rgb: Tuple[int, int, int]
    is_violation: bool


@dataclass(frozen=True)
class _Dataset:
    """Sampled color-gradient puzzle dataset."""

    rows: int
    cols: int
    grid_size_variant: str
    rule_variant: str
    rule_params: Dict[str, Any]
    cells: Tuple[_CellSpec, ...]
    answer_label: str
    violation_cell_id: str
    violation_index: int
    borrowed_from_label: str


@dataclass(frozen=True)
class _CompletionCellSpec:
    """One cell in the visible linear-gradient completion strip."""

    cell_id: str
    index: int
    expected_hsl: Tuple[float, float, float]
    expected_rgb: Tuple[int, int, int]
    is_missing: bool


@dataclass(frozen=True)
class _CompletionOptionSpec:
    """One labeled answer option for the linear-gradient completion task."""

    option_id: str
    label: str
    hsl: Tuple[float, float, float]
    rgb: Tuple[int, int, int]
    is_correct: bool


@dataclass(frozen=True)
class _CompletionDataset:
    """Sampled linear-gradient completion puzzle dataset."""

    sequence_length: int
    sequence_length_variant: str
    option_count: int
    option_count_variant: str
    rule_variant: str
    rule_params: Dict[str, Any]
    cells: Tuple[_CompletionCellSpec, ...]
    options: Tuple[_CompletionOptionSpec, ...]
    missing_index: int
    missing_cell_id: str
    answer_label: str
    correct_option_id: str


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered color-gradient scene and trace maps."""

    image: Image.Image
    scene_bbox_px: Tuple[int, int, int, int]
    cell_bbox_map: Dict[str, Tuple[int, int, int, int]]
    item_bbox_map: Dict[str, Tuple[int, int, int, int]]
    entities: Tuple[Dict[str, Any], ...]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for the color-gradient task."""

    canvas_width: int = 900
    canvas_height: int = 760
    swatch_size_px: int = 112
    swatch_gap_px: int = 14
    panel_padding_px: int = 34
    panel_corner_radius_px: int = 26
    panel_border_width_px: int = 3
    swatch_corner_radius_px: int = 12
    swatch_border_width_px: int = 3
    label_chip_size_px: int = 32
    label_margin_px: int = 9
    label_font_size_px: int = 18
    panel_fill_rgb: Tuple[int, int, int] = (250, 251, 253)
    panel_border_rgb: Tuple[int, int, int] = (88, 96, 110)
    swatch_border_rgb: Tuple[int, int, int] = (40, 46, 58)
    notebook_line_rgb: Tuple[int, int, int] = (218, 226, 236)
    hue_step_min: float = 34.0
    hue_step_max: float = 58.0
    lightness_step_min: float = 0.060
    lightness_step_max: float = 0.090
    saturation_step_min: float = 0.070
    saturation_step_max: float = 0.110


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "visual")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="visual")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="visual", apply_prob=0.0)


def _sample_color_gradient_font(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> str:
    """Sample one role-aware font family for visible swatch labels."""

    return sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.color_gradient_label_font",
        params={**dict(render_defaults), **dict(params)},
    )


def _font_trace_record(font_family: str, *, scope: str) -> Dict[str, Any]:
    """Build trace metadata for one sampled visible-label font."""

    return {
        "source": "global_font_pool",
        "font_family": str(font_family),
        "font_asset_version": font_asset_version(),
        "scope": str(scope),
    }


def _post_noise_policy_trace() -> Dict[str, Any]:
    """Document why color-gradient scenes intentionally do not add post-render noise."""

    return {
        "default_override": True,
        "reason": "color_semantics_preserve_rgb_separability",
    }


def _clamp_unit(value: float) -> float:
    """Clamp a float into [0, 1]."""

    return max(0.0, min(1.0, float(value)))


def _hsl_to_rgb(hue_degrees: float, saturation: float, lightness: float) -> Tuple[int, int, int]:
    """Convert HSL-like values to RGB using Python's HLS convention."""

    red, green, blue = colorsys.hls_to_rgb(
        (float(hue_degrees) % 360.0) / 360.0,
        _clamp_unit(float(lightness)),
        _clamp_unit(float(saturation)),
    )
    return (
        max(0, min(255, int(round(red * 255.0)))),
        max(0, min(255, int(round(green * 255.0)))),
        max(0, min(255, int(round(blue * 255.0)))),
    )


def _luminance(rgb: Sequence[int]) -> float:
    """Return approximate sRGB luminance for text contrast."""

    red, green, blue = (float(max(0, min(255, int(value)))) for value in rgb[:3])
    return ((0.2126 * red) + (0.7152 * green) + (0.0722 * blue)) / 255.0


def _resolve_render_params(
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> _RenderParams:
    """Resolve render params from config defaults."""

    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.color_gradient.unit_size",
    )
    return _RenderParams(
        canvas_width=int(group_default(render_defaults, "canvas_width", _DEFAULTS.canvas_width)),
        canvas_height=int(group_default(render_defaults, "canvas_height", _DEFAULTS.canvas_height)),
        swatch_size_px=scale_puzzle_px(group_default(render_defaults, "swatch_size_px", _DEFAULTS.swatch_size_px), unit_scale, min_px=42),
        swatch_gap_px=scale_puzzle_px(group_default(render_defaults, "swatch_gap_px", _DEFAULTS.swatch_gap_px), unit_scale, min_px=6),
        panel_padding_px=scale_puzzle_px(group_default(render_defaults, "panel_padding_px", _DEFAULTS.panel_padding_px), unit_scale, min_px=14),
        panel_corner_radius_px=scale_puzzle_px(group_default(render_defaults, "panel_corner_radius_px", _DEFAULTS.panel_corner_radius_px), unit_scale, min_px=8),
        panel_border_width_px=scale_puzzle_px(group_default(render_defaults, "panel_border_width_px", _DEFAULTS.panel_border_width_px), unit_scale, min_px=1),
        swatch_corner_radius_px=scale_puzzle_px(group_default(render_defaults, "swatch_corner_radius_px", _DEFAULTS.swatch_corner_radius_px), unit_scale, min_px=5),
        swatch_border_width_px=scale_puzzle_px(group_default(render_defaults, "swatch_border_width_px", _DEFAULTS.swatch_border_width_px), unit_scale, min_px=1),
        label_chip_size_px=scale_puzzle_px(group_default(render_defaults, "label_chip_size_px", _DEFAULTS.label_chip_size_px), unit_scale, min_px=16),
        label_margin_px=scale_puzzle_px(group_default(render_defaults, "label_margin_px", _DEFAULTS.label_margin_px), unit_scale, min_px=4),
        label_font_size_px=scale_puzzle_px(group_default(render_defaults, "label_font_size_px", _DEFAULTS.label_font_size_px), unit_scale, min_px=10),
        panel_fill_rgb=_rgb(group_default(render_defaults, "panel_fill_rgb", _DEFAULTS.panel_fill_rgb), _DEFAULTS.panel_fill_rgb),
        panel_border_rgb=_rgb(group_default(render_defaults, "panel_border_rgb", _DEFAULTS.panel_border_rgb), _DEFAULTS.panel_border_rgb),
        swatch_border_rgb=_rgb(group_default(render_defaults, "swatch_border_rgb", _DEFAULTS.swatch_border_rgb), _DEFAULTS.swatch_border_rgb),
        notebook_line_rgb=_rgb(group_default(render_defaults, "notebook_line_rgb", _DEFAULTS.notebook_line_rgb), _DEFAULTS.notebook_line_rgb),
        unit_size_jitter=dict(unit_meta),
    )


def _resolve_axis_variant(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str = TASK_ID,
    supported_variants: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    axis_namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one visual/semantic axis for this puzzle task."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=tuple(str(value) for value in supported_variants),
        task_id=str(task_id),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        axis_namespace=str(axis_namespace),
    )


def _rule_hsl(
    *,
    row: int,
    col: int,
    rule_variant: str,
    rule_params: Mapping[str, Any],
) -> Tuple[float, float, float]:
    """Return expected HSL for one grid coordinate."""

    hue_base = float(rule_params["hue_base"])
    hue_step = float(rule_params["hue_step"])
    lightness_base = float(rule_params["lightness_base"])
    lightness_step = float(rule_params["lightness_step"])
    saturation_base = float(rule_params["saturation_base"])
    saturation_step = float(rule_params["saturation_step"])

    if str(rule_variant) == "column_hue_row_lightness":
        hue = float(hue_base + (float(col) * hue_step))
        saturation = float(saturation_base)
        lightness = float(lightness_base + (float(row) * lightness_step))
    elif str(rule_variant) == "row_hue_column_lightness":
        hue = float(hue_base + (float(row) * hue_step))
        saturation = float(saturation_base)
        lightness = float(lightness_base + (float(col) * lightness_step))
    elif str(rule_variant) == "column_hue_row_saturation":
        hue = float(hue_base + (float(col) * hue_step))
        saturation = float(saturation_base + (float(row) * saturation_step))
        lightness = float(lightness_base)
    else:
        raise ValueError(f"unsupported color-gradient rule_variant: {rule_variant}")
    return (float(hue % 360.0), _clamp_unit(float(saturation)), _clamp_unit(float(lightness)))


def _sample_rule_params(rng, *, gen_defaults: Mapping[str, Any], rule_variant: str) -> Dict[str, Any]:
    """Sample one smooth color-progression rule."""

    hue_step_min = float(group_default(gen_defaults, "hue_step_min", _DEFAULTS.hue_step_min))
    hue_step_max = float(group_default(gen_defaults, "hue_step_max", _DEFAULTS.hue_step_max))
    lightness_step_min = float(group_default(gen_defaults, "lightness_step_min", _DEFAULTS.lightness_step_min))
    lightness_step_max = float(group_default(gen_defaults, "lightness_step_max", _DEFAULTS.lightness_step_max))
    saturation_step_min = float(group_default(gen_defaults, "saturation_step_min", _DEFAULTS.saturation_step_min))
    saturation_step_max = float(group_default(gen_defaults, "saturation_step_max", _DEFAULTS.saturation_step_max))

    hue_direction = -1.0 if bool(rng.randint(0, 1)) else 1.0
    lightness_direction = -1.0 if bool(rng.randint(0, 1)) else 1.0
    saturation_direction = -1.0 if bool(rng.randint(0, 1)) else 1.0
    lightness_step = float(rng.uniform(lightness_step_min, lightness_step_max)) * lightness_direction
    saturation_step = float(rng.uniform(saturation_step_min, saturation_step_max)) * saturation_direction

    if lightness_direction > 0:
        lightness_base = float(rng.uniform(0.36, 0.46))
    else:
        lightness_base = float(rng.uniform(0.64, 0.74))
    if saturation_direction > 0:
        saturation_base = float(rng.uniform(0.44, 0.54))
    else:
        saturation_base = float(rng.uniform(0.76, 0.88))

    if str(rule_variant) == "column_hue_row_saturation":
        lightness_base = float(rng.uniform(0.54, 0.64))
    else:
        saturation_base = float(rng.uniform(0.66, 0.84))

    return {
        "hue_base": round(float(rng.uniform(0.0, 360.0)), 6),
        "hue_step": round(float(rng.uniform(hue_step_min, hue_step_max) * hue_direction), 6),
        "lightness_base": round(float(lightness_base), 6),
        "lightness_step": round(float(lightness_step), 6),
        "saturation_base": round(float(saturation_base), 6),
        "saturation_step": round(float(saturation_step), 6),
    }


def _build_dataset(*, params: Mapping[str, Any], instance_seed: int, gen_defaults: Mapping[str, Any]) -> _Dataset:
    """Construct one color-gradient violation dataset."""

    grid_size_variant, _grid_size_probabilities = _resolve_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=_GRID_SIZE_VARIANTS,
        explicit_key="grid_size_variant",
        weights_key="grid_size_variant_weights",
        balance_flag_key="balanced_grid_size_variant_sampling",
        axis_namespace="grid_size_variant",
    )
    if str(grid_size_variant) not in _GRID_SIZE_VARIANTS:
        raise ValueError(f"unsupported grid_size_variant: {grid_size_variant}")
    rows = int(str(grid_size_variant).split("x", maxsplit=1)[0])
    cols = int(str(grid_size_variant).split("x", maxsplit=1)[1])

    rule_variant, _rule_variant_probabilities = _resolve_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=_RULE_VARIANTS,
        explicit_key="rule_variant",
        weights_key="rule_variant_weights",
        balance_flag_key="balanced_rule_variant_sampling",
        axis_namespace="rule_variant",
    )

    labels = tuple(_LABELS[index] for index in range(int(rows * cols)))
    explicit_label = str(params.get("answer_label", "") or params.get("violation_label", "")).strip().upper()
    if explicit_label:
        if explicit_label not in labels:
            raise ValueError(f"answer_label {explicit_label!r} is outside visible labels for {grid_size_variant}")
        violation_index = int(labels.index(explicit_label))
    else:
        selection = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:answer_label:{grid_size_variant}",
        )
        violation_index = int(selection % len(labels))

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset")
    rule_params = _sample_rule_params(rng, gen_defaults=gen_defaults, rule_variant=str(rule_variant))
    expected_hsl: List[Tuple[float, float, float]] = []
    expected_rgb: List[Tuple[int, int, int]] = []
    for row in range(int(rows)):
        for col in range(int(cols)):
            hsl = _rule_hsl(row=int(row), col=int(col), rule_variant=str(rule_variant), rule_params=rule_params)
            expected_hsl.append(hsl)
            expected_rgb.append(_hsl_to_rgb(*hsl))

    violation_row = int(violation_index // cols)
    violation_col = int(violation_index % cols)
    candidate_indices = [
        int(index)
        for index in range(int(rows * cols))
        if int(index) != int(violation_index)
        and abs(int(index // cols) - int(violation_row)) + abs(int(index % cols) - int(violation_col)) >= 2
    ]
    if not candidate_indices:
        candidate_indices = [int(index) for index in range(int(rows * cols)) if int(index) != int(violation_index)]
    borrowed_index = int(rng.choice(candidate_indices))
    observed_hsl = list(expected_hsl)
    observed_rgb = list(expected_rgb)
    observed_hsl[int(violation_index)] = tuple(expected_hsl[int(borrowed_index)])
    observed_rgb[int(violation_index)] = tuple(expected_rgb[int(borrowed_index)])

    cells: List[_CellSpec] = []
    for index, label in enumerate(labels):
        row = int(index // cols)
        col = int(index % cols)
        cells.append(
            _CellSpec(
                cell_id=f"cell_{label}",
                label=str(label),
                row=int(row),
                col=int(col),
                expected_hsl=tuple(float(value) for value in expected_hsl[int(index)]),
                observed_hsl=tuple(float(value) for value in observed_hsl[int(index)]),
                expected_rgb=tuple(int(value) for value in expected_rgb[int(index)]),
                observed_rgb=tuple(int(value) for value in observed_rgb[int(index)]),
                is_violation=bool(index == int(violation_index)),
            )
        )

    return _Dataset(
        rows=int(rows),
        cols=int(cols),
        grid_size_variant=str(grid_size_variant),
        rule_variant=str(rule_variant),
        rule_params=dict(rule_params),
        cells=tuple(cells),
        answer_label=str(labels[int(violation_index)]),
        violation_cell_id=f"cell_{labels[int(violation_index)]}",
        violation_index=int(violation_index),
        borrowed_from_label=str(labels[int(borrowed_index)]),
    )


def _parse_completion_length_variant(value: str) -> int:
    """Return sequence length from a completion length variant key."""

    if str(value) not in _COMPLETION_LENGTH_VARIANTS:
        raise ValueError(f"unsupported sequence_length_variant: {value}")
    return int(str(value).split("_", maxsplit=1)[0])


def _parse_completion_option_count_variant(value: str) -> int:
    """Return option count from a completion option-count variant key."""

    if str(value) not in _COMPLETION_OPTION_COUNT_VARIANTS:
        raise ValueError(f"unsupported option_count_variant: {value}")
    return int(str(value).split("_", maxsplit=1)[0])


def _completion_rule_hsl(
    *,
    index: int,
    rule_variant: str,
    rule_params: Mapping[str, Any],
) -> Tuple[float, float, float]:
    """Return the expected HSL for one position in a linear gradient."""

    hue_base = float(rule_params["hue_base"])
    hue_step = float(rule_params["hue_step"])
    lightness_base = float(rule_params["lightness_base"])
    lightness_step = float(rule_params["lightness_step"])
    saturation_base = float(rule_params["saturation_base"])

    if str(rule_variant) == "hue_gradient":
        hue = hue_base + (float(index) * hue_step)
        lightness = lightness_base
    elif str(rule_variant) == "lightness_gradient":
        hue = hue_base
        lightness = lightness_base + (float(index) * lightness_step)
    elif str(rule_variant) == "hue_lightness_gradient":
        hue = hue_base + (float(index) * hue_step)
        lightness = lightness_base + (float(index) * lightness_step)
    else:
        raise ValueError(f"unsupported completion rule_variant: {rule_variant}")
    return (float(hue % 360.0), _clamp_unit(float(saturation_base)), _clamp_unit(float(lightness)))


def _sample_completion_rule_params(
    rng,
    *,
    sequence_length: int,
    gen_defaults: Mapping[str, Any],
    rule_variant: str,
) -> Dict[str, Any]:
    """Sample one linearly progressing color rule without hue-wheel wraparound."""

    hue_step_min = float(group_default(gen_defaults, "completion_hue_step_min", group_default(gen_defaults, "hue_step_min", 34.0)))
    hue_step_max = float(group_default(gen_defaults, "completion_hue_step_max", min(58.0, max(34.0, hue_step_min + 20.0))))
    lightness_step_min = float(group_default(gen_defaults, "completion_lightness_step_min", 0.060))
    lightness_step_max = float(group_default(gen_defaults, "completion_lightness_step_max", 0.088))
    hue_step_min = max(20.0, float(hue_step_min))
    hue_step_max = max(float(hue_step_min), float(hue_step_max))

    hue_direction = -1.0 if bool(rng.randint(0, 1)) else 1.0
    lightness_direction = -1.0 if bool(rng.randint(0, 1)) else 1.0
    uses_hue = str(rule_variant) in {"hue_gradient", "hue_lightness_gradient"}
    uses_lightness = str(rule_variant) in {"lightness_gradient", "hue_lightness_gradient"}

    hue_step = 0.0
    if uses_hue:
        max_step_without_wrap = max(float(hue_step_min), 320.0 / max(1.0, float(sequence_length - 1)))
        hue_step = float(rng.uniform(float(hue_step_min), min(float(hue_step_max), float(max_step_without_wrap))))
        hue_span = abs(float(hue_step)) * max(1.0, float(sequence_length - 1))
        if hue_direction > 0:
            hue_base = float(rng.uniform(6.0, max(6.0, 354.0 - hue_span)))
        else:
            hue_base = float(rng.uniform(min(354.0, 6.0 + hue_span), 354.0))
        hue_step *= hue_direction
    else:
        hue_base = float(rng.uniform(0.0, 360.0))

    lightness_step = 0.0
    if uses_lightness:
        lightness_step = float(rng.uniform(lightness_step_min, lightness_step_max)) * lightness_direction
        lightness_span = abs(float(lightness_step)) * max(1.0, float(sequence_length - 1))
        if lightness_direction > 0:
            lightness_base = float(rng.uniform(0.34, max(0.34, 0.76 - lightness_span)))
        else:
            lightness_base = float(rng.uniform(min(0.76, 0.34 + lightness_span), 0.76))
    else:
        lightness_base = float(rng.uniform(0.55, 0.66))

    return {
        "hue_base": round(float(hue_base), 6),
        "hue_step": round(float(hue_step), 6),
        "lightness_base": round(float(lightness_base), 6),
        "lightness_step": round(float(lightness_step), 6),
        "saturation_base": round(float(rng.uniform(0.68, 0.84)), 6),
    }


def _append_distinct_rgb(
    candidates: List[Tuple[int, int, int]],
    rgb: Tuple[int, int, int],
    *,
    min_lab_distance: float,
) -> bool:
    """Append one RGB candidate when it is visually distinct enough."""

    normalized = tuple(int(value) for value in rgb)
    if any(float(color_distance(normalized, existing, distance_space="lab")) < float(min_lab_distance) for existing in candidates):
        return False
    candidates.append(normalized)
    return True


def _build_completion_distractor_rgbs(
    *,
    rng,
    option_count: int,
    correct_rgb: Tuple[int, int, int],
    missing_index: int,
    rule_variant: str,
    rule_params: Mapping[str, Any],
) -> Tuple[Tuple[int, int, int], ...]:
    """Build visually distinct but plausible color-option distractors."""

    candidate_rgbs: List[Tuple[int, int, int]] = [tuple(int(value) for value in correct_rgb)]
    offsets = (-2, -1, 1, 2, -3, 3)
    for offset in offsets:
        if len(candidate_rgbs) >= int(option_count):
            break
        hsl = _completion_rule_hsl(
            index=int(missing_index) + int(offset),
            rule_variant=str(rule_variant),
            rule_params=rule_params,
        )
        _append_distinct_rgb(candidate_rgbs, _hsl_to_rgb(*hsl), min_lab_distance=18.0)

    correct_h, correct_s, correct_l = _completion_rule_hsl(
        index=int(missing_index),
        rule_variant=str(rule_variant),
        rule_params=rule_params,
    )
    attempts = 0
    while len(candidate_rgbs) < int(option_count) and attempts < 200:
        attempts += 1
        hue_jitter = float(rng.choice([-1.0, 1.0])) * float(rng.uniform(30.0, 80.0))
        lightness_jitter = float(rng.choice([-1.0, 1.0])) * float(rng.uniform(0.06, 0.16))
        saturation_jitter = float(rng.choice([-1.0, 1.0])) * float(rng.uniform(0.03, 0.10))
        hsl = (
            float(correct_h + hue_jitter),
            _clamp_unit(float(correct_s + saturation_jitter)),
            _clamp_unit(float(correct_l + lightness_jitter)),
        )
        _append_distinct_rgb(candidate_rgbs, _hsl_to_rgb(*hsl), min_lab_distance=18.0)

    fallback_index = 0
    while len(candidate_rgbs) < int(option_count):
        fallback_index += 1
        fallback_hsl = (
            float(correct_h + (45.0 * fallback_index)),
            _clamp_unit(float(correct_s)),
            _clamp_unit(float(correct_l)),
        )
        if not _append_distinct_rgb(candidate_rgbs, _hsl_to_rgb(*fallback_hsl), min_lab_distance=8.0):
            candidate_rgbs.append(_hsl_to_rgb(float(correct_h + (31.0 * fallback_index)), correct_s, correct_l))

    return tuple(tuple(int(channel) for channel in rgb) for rgb in candidate_rgbs[1:int(option_count)])


def _build_completion_dataset(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
) -> _CompletionDataset:
    """Construct one linear color-gradient completion dataset."""

    length_variant, _length_probabilities = _resolve_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=COMPLETION_TASK_ID,
        supported_variants=_COMPLETION_LENGTH_VARIANTS,
        explicit_key="sequence_length_variant",
        weights_key="sequence_length_variant_weights",
        balance_flag_key="balanced_sequence_length_variant_sampling",
        axis_namespace="sequence_length_variant",
    )
    option_count_variant, _option_count_probabilities = _resolve_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=COMPLETION_TASK_ID,
        supported_variants=_COMPLETION_OPTION_COUNT_VARIANTS,
        explicit_key="option_count_variant",
        weights_key="option_count_variant_weights",
        balance_flag_key="balanced_option_count_variant_sampling",
        axis_namespace="option_count_variant",
    )
    rule_variant, _rule_variant_probabilities = _resolve_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=COMPLETION_TASK_ID,
        supported_variants=_COMPLETION_RULE_VARIANTS,
        explicit_key="rule_variant",
        weights_key="rule_variant_weights",
        balance_flag_key="balanced_rule_variant_sampling",
        axis_namespace="rule_variant",
    )
    sequence_length = _parse_completion_length_variant(str(length_variant))
    option_count = _parse_completion_option_count_variant(str(option_count_variant))
    option_labels = tuple(_LABELS[index] for index in range(int(option_count)))

    explicit_label = str(params.get("answer_label", "") or params.get("correct_option_label", "")).strip().upper()
    if explicit_label:
        if explicit_label not in option_labels:
            raise ValueError(f"answer_label {explicit_label!r} is outside visible options for {option_count_variant}")
        correct_option_index = int(option_labels.index(explicit_label))
    else:
        selection = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{COMPLETION_TASK_ID}:answer_label:{option_count_variant}",
        )
        correct_option_index = int(selection % int(option_count))

    if "missing_index" in params and params.get("missing_index") is not None:
        missing_index = int(params.get("missing_index"))
        if missing_index <= 0 or missing_index >= int(sequence_length) - 1:
            raise ValueError("missing_index must be an interior position for linear gradient completion")
    else:
        missing_selection = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{COMPLETION_TASK_ID}:missing_index:{length_variant}",
        )
        missing_index = int(missing_selection % max(1, int(sequence_length) - 2)) + 1

    rng = spawn_rng(int(instance_seed), f"{COMPLETION_TASK_ID}.dataset")
    rule_params = _sample_completion_rule_params(
        rng,
        sequence_length=int(sequence_length),
        gen_defaults=gen_defaults,
        rule_variant=str(rule_variant),
    )
    cells: List[_CompletionCellSpec] = []
    expected_rgbs: List[Tuple[int, int, int]] = []
    expected_hsls: List[Tuple[float, float, float]] = []
    for index in range(int(sequence_length)):
        hsl = _completion_rule_hsl(index=int(index), rule_variant=str(rule_variant), rule_params=rule_params)
        rgb = _hsl_to_rgb(*hsl)
        expected_hsls.append(tuple(float(value) for value in hsl))
        expected_rgbs.append(tuple(int(value) for value in rgb))
        cells.append(
            _CompletionCellSpec(
                cell_id=f"sequence_cell_{index}",
                index=int(index),
                expected_hsl=tuple(float(value) for value in hsl),
                expected_rgb=tuple(int(value) for value in rgb),
                is_missing=bool(index == int(missing_index)),
            )
        )

    correct_rgb = tuple(int(value) for value in expected_rgbs[int(missing_index)])
    distractor_rgbs = list(
        _build_completion_distractor_rgbs(
            rng=rng,
            option_count=int(option_count),
            correct_rgb=correct_rgb,
            missing_index=int(missing_index),
            rule_variant=str(rule_variant),
            rule_params=rule_params,
        )
    )
    options: List[_CompletionOptionSpec] = []
    distractor_index = 0
    correct_option_id = ""
    for option_index, label in enumerate(option_labels):
        is_correct = bool(option_index == int(correct_option_index))
        if is_correct:
            rgb = correct_rgb
            hsl = tuple(float(value) for value in expected_hsls[int(missing_index)])
            correct_option_id = f"option_{label}"
        else:
            rgb = tuple(int(value) for value in distractor_rgbs[int(distractor_index)])
            distractor_index += 1
            hsl = (0.0, 0.0, 0.0)
        options.append(
            _CompletionOptionSpec(
                option_id=f"option_{label}",
                label=str(label),
                hsl=tuple(float(value) for value in hsl),
                rgb=tuple(int(value) for value in rgb),
                is_correct=bool(is_correct),
            )
        )

    answer_label = str(option_labels[int(correct_option_index)])
    return _CompletionDataset(
        sequence_length=int(sequence_length),
        sequence_length_variant=str(length_variant),
        option_count=int(option_count),
        option_count_variant=str(option_count_variant),
        rule_variant=str(rule_variant),
        rule_params=dict(rule_params),
        cells=tuple(cells),
        options=tuple(options),
        missing_index=int(missing_index),
        missing_cell_id=f"sequence_cell_{missing_index}",
        answer_label=str(answer_label),
        correct_option_id=str(correct_option_id),
    )


def _draw_notebook_lines(draw: ImageDraw.ImageDraw, *, bbox: Tuple[int, int, int, int], color: Tuple[int, int, int]) -> None:
    """Draw subtle notebook-style guide lines inside a panel."""

    left, top, right, bottom = bbox
    for y in range(int(top) + 28, int(bottom), 28):
        draw.line([(int(left) + 10, int(y)), (int(right) - 10, int(y))], fill=tuple(color), width=1)
    for x in range(int(left) + 34, int(right), 34):
        draw.line([(int(x), int(top) + 10), (int(x), int(bottom) - 10)], fill=tuple(color), width=1)


def _render_scene(
    *,
    background: Image.Image,
    dataset: _Dataset,
    scene_variant: str,
    render_params: _RenderParams,
) -> _RenderedScene:
    """Render the color-gradient swatch grid."""

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    grid_width = (int(dataset.cols) * int(render_params.swatch_size_px)) + (
        (int(dataset.cols) - 1) * int(render_params.swatch_gap_px)
    )
    grid_height = (int(dataset.rows) * int(render_params.swatch_size_px)) + (
        (int(dataset.rows) - 1) * int(render_params.swatch_gap_px)
    )
    grid_left = int(round((int(render_params.canvas_width) - int(grid_width)) / 2.0))
    grid_top = int(round((int(render_params.canvas_height) - int(grid_height)) / 2.0))
    panel_bbox = (
        int(grid_left - int(render_params.panel_padding_px)),
        int(grid_top - int(render_params.panel_padding_px)),
        int(grid_left + int(grid_width) + int(render_params.panel_padding_px)),
        int(grid_top + int(grid_height) + int(render_params.panel_padding_px)),
    )

    if str(scene_variant) in {"swatch_card", "swatch_notebook"}:
        draw_rounded_rect(
            draw,
            panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=tuple(render_params.panel_fill_rgb),
            outline=tuple(render_params.panel_border_rgb),
            width=int(render_params.panel_border_width_px),
        )
        if str(scene_variant) == "swatch_notebook":
            _draw_notebook_lines(draw, bbox=panel_bbox, color=tuple(render_params.notebook_line_rgb))

    cell_bbox_map: Dict[str, Tuple[int, int, int, int]] = {}
    item_bbox_map: Dict[str, Tuple[int, int, int, int]] = {}
    entities: List[Dict[str, Any]] = [
        {
            "id": "gradient_grid_panel",
            "type": "color_gradient_panel",
            "bbox_px": [int(value) for value in panel_bbox],
            "rows": int(dataset.rows),
            "cols": int(dataset.cols),
            "scene_variant": str(scene_variant),
        }
    ]
    label_font = load_font(int(render_params.label_font_size_px), bold=True)

    for cell in dataset.cells:
        x0 = int(grid_left + (int(cell.col) * (int(render_params.swatch_size_px) + int(render_params.swatch_gap_px))))
        y0 = int(grid_top + (int(cell.row) * (int(render_params.swatch_size_px) + int(render_params.swatch_gap_px))))
        bbox = (
            int(x0),
            int(y0),
            int(x0 + int(render_params.swatch_size_px)),
            int(y0 + int(render_params.swatch_size_px)),
        )
        draw_rounded_rect(
            draw,
            bbox,
            radius=int(render_params.swatch_corner_radius_px),
            fill=tuple(cell.observed_rgb),
            outline=tuple(render_params.swatch_border_rgb),
            width=int(render_params.swatch_border_width_px),
        )
        chip_size = int(render_params.label_chip_size_px)
        chip_margin = int(render_params.label_margin_px)
        chip_bbox = (
            int(x0 + chip_margin),
            int(y0 + chip_margin),
            int(x0 + chip_margin + chip_size),
            int(y0 + chip_margin + chip_size),
        )
        chip_fill = (255, 255, 255) if _luminance(cell.observed_rgb) < 0.72 else (36, 42, 52)
        chip_outline = (36, 42, 52) if chip_fill == (255, 255, 255) else (255, 255, 255)
        label_fill = (28, 32, 38) if chip_fill == (255, 255, 255) else (255, 255, 255)
        draw.rounded_rectangle(chip_bbox, radius=8, fill=chip_fill, outline=chip_outline, width=1)
        draw_centered_text(
            draw,
            text=str(cell.label),
            center=((chip_bbox[0] + chip_bbox[2]) / 2.0, (chip_bbox[1] + chip_bbox[3]) / 2.0),
            font=label_font,
            fill=label_fill,
            stroke_fill=chip_outline,
            stroke_width=0,
        )

        cell_bbox_map[str(cell.cell_id)] = tuple(int(value) for value in bbox)
        item_bbox_map[str(cell.cell_id)] = tuple(int(value) for value in bbox)
        entities.append(
            {
                "id": str(cell.cell_id),
                "type": "color_gradient_swatch_cell",
                "label": str(cell.label),
                "row_index": int(cell.row),
                "col_index": int(cell.col),
                "bbox_px": [int(value) for value in bbox],
                "expected_hsl": [round(float(value), 6) for value in cell.expected_hsl],
                "observed_hsl": [round(float(value), 6) for value in cell.observed_hsl],
                "expected_rgb": [int(value) for value in cell.expected_rgb],
                "observed_rgb": [int(value) for value in cell.observed_rgb],
                "is_violation": bool(cell.is_violation),
            }
        )

    return _RenderedScene(
        image=image,
        scene_bbox_px=tuple(int(value) for value in panel_bbox),
        cell_bbox_map=dict(cell_bbox_map),
        item_bbox_map=dict(item_bbox_map),
        entities=tuple(entities),
    )


def _draw_option_label_chip(
    draw: ImageDraw.ImageDraw,
    *,
    label: str,
    swatch_bbox: Tuple[int, int, int, int],
    swatch_rgb: Tuple[int, int, int],
    render_params: _RenderParams,
) -> None:
    """Draw a compact label chip on a colored swatch."""

    chip_size = int(render_params.label_chip_size_px)
    chip_margin = int(render_params.label_margin_px)
    chip_bbox = (
        int(swatch_bbox[0] + chip_margin),
        int(swatch_bbox[1] + chip_margin),
        int(swatch_bbox[0] + chip_margin + chip_size),
        int(swatch_bbox[1] + chip_margin + chip_size),
    )
    chip_fill = (255, 255, 255) if _luminance(swatch_rgb) < 0.72 else (36, 42, 52)
    chip_outline = (36, 42, 52) if chip_fill == (255, 255, 255) else (255, 255, 255)
    label_fill = (28, 32, 38) if chip_fill == (255, 255, 255) else (255, 255, 255)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    draw.rounded_rectangle(chip_bbox, radius=8, fill=chip_fill, outline=chip_outline, width=1)
    draw_centered_text(
        draw,
        text=str(label),
        center=((chip_bbox[0] + chip_bbox[2]) / 2.0, (chip_bbox[1] + chip_bbox[3]) / 2.0),
        font=label_font,
        fill=label_fill,
        stroke_fill=chip_outline,
        stroke_width=0,
    )


def _draw_missing_swatch(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[int, int, int, int],
    render_params: _RenderParams,
) -> None:
    """Draw the neutral blank swatch used by the completion task."""

    fill = (239, 242, 247)
    outline = tuple(render_params.swatch_border_rgb)
    draw_rounded_rect(
        draw,
        bbox,
        radius=int(render_params.swatch_corner_radius_px),
        fill=fill,
        outline=outline,
        width=int(render_params.swatch_border_width_px),
    )
    for offset in range(-int(bbox[3] - bbox[1]), int(bbox[2] - bbox[0]), 18):
        start_x = max(int(bbox[0]), int(bbox[0] + offset))
        start_y = int(bbox[1]) if offset >= 0 else int(bbox[1] - offset)
        end_x = min(int(bbox[2]), int(bbox[0] + offset + int(bbox[3] - bbox[1])))
        end_y = int(bbox[1] + (end_x - (int(bbox[0]) + offset)))
        draw.line([(start_x, start_y), (end_x, min(int(bbox[3]), end_y))], fill=(207, 214, 225), width=2)
    question_font = load_font(max(28, int(render_params.label_font_size_px) + 12), bold=True)
    draw_centered_text(
        draw,
        text="?",
        center=((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0),
        font=question_font,
        fill=(55, 62, 75),
        stroke_fill=(255, 255, 255),
        stroke_width=2,
    )


def _render_completion_scene(
    *,
    background: Image.Image,
    dataset: _CompletionDataset,
    scene_variant: str,
    render_params: _RenderParams,
) -> _RenderedScene:
    """Render a linear gradient with one missing swatch and labeled color options."""

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    gap = int(render_params.swatch_gap_px)
    swatch_size = min(
        int(render_params.swatch_size_px),
        max(
            76,
            int(
                (
                    int(render_params.canvas_width)
                    - (2 * int(render_params.panel_padding_px))
                    - ((int(dataset.sequence_length) - 1) * gap)
                    - 80
                )
                / max(1, int(dataset.sequence_length))
            ),
        ),
    )
    option_size = min(int(swatch_size), 104)
    sequence_width = (int(dataset.sequence_length) * int(swatch_size)) + ((int(dataset.sequence_length) - 1) * gap)
    options_width = (int(dataset.option_count) * int(option_size)) + ((int(dataset.option_count) - 1) * gap)
    sequence_left = int(round((int(render_params.canvas_width) - int(sequence_width)) / 2.0))
    option_left = int(round((int(render_params.canvas_width) - int(options_width)) / 2.0))
    sequence_top = 188
    option_top = int(sequence_top + int(swatch_size) + 118)
    panel_bbox = (
        int(min(sequence_left, option_left) - int(render_params.panel_padding_px)),
        int(sequence_top - int(render_params.panel_padding_px)),
        int(max(sequence_left + sequence_width, option_left + options_width) + int(render_params.panel_padding_px)),
        int(option_top + int(option_size) + int(render_params.panel_padding_px)),
    )

    if str(scene_variant) in {"swatch_card", "swatch_notebook"}:
        draw_rounded_rect(
            draw,
            panel_bbox,
            radius=int(render_params.panel_corner_radius_px),
            fill=tuple(render_params.panel_fill_rgb),
            outline=tuple(render_params.panel_border_rgb),
            width=int(render_params.panel_border_width_px),
        )
        if str(scene_variant) == "swatch_notebook":
            _draw_notebook_lines(draw, bbox=panel_bbox, color=tuple(render_params.notebook_line_rgb))

    cell_bbox_map: Dict[str, Tuple[int, int, int, int]] = {}
    item_bbox_map: Dict[str, Tuple[int, int, int, int]] = {}
    entities: List[Dict[str, Any]] = [
        {
            "id": "linear_gradient_panel",
            "type": "linear_color_gradient_panel",
            "bbox_px": [int(value) for value in panel_bbox],
            "sequence_length": int(dataset.sequence_length),
            "option_count": int(dataset.option_count),
            "scene_variant": str(scene_variant),
        }
    ]

    for cell in dataset.cells:
        x0 = int(sequence_left + (int(cell.index) * (int(swatch_size) + gap)))
        y0 = int(sequence_top)
        bbox = (int(x0), int(y0), int(x0 + swatch_size), int(y0 + swatch_size))
        if bool(cell.is_missing):
            _draw_missing_swatch(draw, bbox=bbox, render_params=render_params)
        else:
            draw_rounded_rect(
                draw,
                bbox,
                radius=int(render_params.swatch_corner_radius_px),
                fill=tuple(cell.expected_rgb),
                outline=tuple(render_params.swatch_border_rgb),
                width=int(render_params.swatch_border_width_px),
            )
        cell_bbox_map[str(cell.cell_id)] = tuple(int(value) for value in bbox)
        item_bbox_map[str(cell.cell_id)] = tuple(int(value) for value in bbox)
        entities.append(
            {
                "id": str(cell.cell_id),
                "type": "linear_gradient_sequence_cell",
                "index": int(cell.index),
                "bbox_px": [int(value) for value in bbox],
                "expected_hsl": [round(float(value), 6) for value in cell.expected_hsl],
                "expected_rgb": [int(value) for value in cell.expected_rgb],
                "is_missing": bool(cell.is_missing),
            }
        )

    for option_index, option in enumerate(dataset.options):
        x0 = int(option_left + (int(option_index) * (int(option_size) + gap)))
        y0 = int(option_top)
        bbox = (int(x0), int(y0), int(x0 + option_size), int(y0 + option_size))
        draw_rounded_rect(
            draw,
            bbox,
            radius=int(render_params.swatch_corner_radius_px),
            fill=tuple(option.rgb),
            outline=tuple(render_params.swatch_border_rgb),
            width=int(render_params.swatch_border_width_px),
        )
        _draw_option_label_chip(
            draw,
            label=str(option.label),
            swatch_bbox=bbox,
            swatch_rgb=tuple(option.rgb),
            render_params=render_params,
        )
        cell_bbox_map[str(option.option_id)] = tuple(int(value) for value in bbox)
        item_bbox_map[str(option.option_id)] = tuple(int(value) for value in bbox)
        entities.append(
            {
                "id": str(option.option_id),
                "type": "linear_gradient_option_swatch",
                "label": str(option.label),
                "option_index": int(option_index),
                "bbox_px": [int(value) for value in bbox],
                "rgb": [int(value) for value in option.rgb],
                "is_correct": bool(option.is_correct),
            }
        )

    return _RenderedScene(
        image=image,
        scene_bbox_px=tuple(int(value) for value in panel_bbox),
        cell_bbox_map=dict(cell_bbox_map),
        item_bbox_map=dict(item_bbox_map),
        entities=tuple(entities),
    )


def _build_prompt(
    *,
    prompt_defaults: Mapping[str, Any],
    scene_variant: str,
    instance_seed: int,
    task_id: str = TASK_ID,
    query_id: str = QUERY_ID,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    """Render the prompt from external prompt templates."""

    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        f"object_description_{scene_variant}",
        "json_output_contract",
        "json_output_contract_answer_only",
        "annotation_hint",
        "answer_hint",
        "json_example",
        "json_example_answer_only",
    )
    prompt_values = required_group_defaults(
        prompt_defaults,
        required_keys,
        context=f"prompt defaults for {task_id}",
    )
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_values["annotation_hint"]),
        "answer_hint": str(prompt_values["answer_hint"]),
        "json_example": str(prompt_values["json_example"]),
        "json_example_answer_only": str(prompt_values["json_example_answer_only"]),
    }
    prompt_selection = render_task_prompt_variants(
        domain="puzzles",
        task_group="visual",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
        "bundle_id": str(prompt_values["bundle_id"]),
    }


@register_task
class PuzzlesVisualColorGradientViolationCellLabelTask:
    """Identify the labeled swatch that breaks a smooth color progression."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "visual"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            get_task_group_defaults("puzzles", "visual"),
            task_id=TASK_ID,
        )
        complexity_weights = resolve_puzzle_complexity_weights(get_task_group_defaults("puzzles", "visual"), task_id=TASK_ID)
        last_error: Exception | None = None
        dataset: _Dataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset(
                    params=params,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    gen_defaults=gen_defaults,
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate color-gradient puzzle instance") from last_error

        scene_variant, scene_variant_probabilities = _resolve_axis_variant(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            supported_variants=_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )
        grid_size_variant_probabilities = {
            key: float(value)
            for key, value in _resolve_axis_variant(
                params=params,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                supported_variants=_GRID_SIZE_VARIANTS,
                explicit_key="grid_size_variant",
                weights_key="grid_size_variant_weights",
                balance_flag_key="balanced_grid_size_variant_sampling",
                axis_namespace="grid_size_variant",
            )[1].items()
        }
        rule_variant_probabilities = {
            key: float(value)
            for key, value in _resolve_axis_variant(
                params=params,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                supported_variants=_RULE_VARIANTS,
                explicit_key="rule_variant",
                weights_key="rule_variant_weights",
                balance_flag_key="balanced_rule_variant_sampling",
                axis_namespace="rule_variant",
            )[1].items()
        }

        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        font_family = _sample_color_gradient_font(
            task_id=TASK_ID,
            instance_seed=int(instance_seed),
            params=params,
            render_defaults=render_defaults,
        )
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{VIOLATION_TASK_ID}.color_gradient_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            panel_border_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            swatch_border_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            notebook_line_rgb=tuple(int(value) for value in scene_style.notebook_line_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        with temporary_default_font_family(str(font_family)):
            rendered_scene = _render_scene(
                background=background,
                dataset=dataset,
                scene_variant=str(scene_variant),
                render_params=render_params,
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            prompt_defaults=prompt_defaults,
            scene_variant=str(scene_variant),
            instance_seed=int(instance_seed),
        )
        annotation_projection = projected_puzzle_bbox_annotation(rendered_scene.item_bbox_map, [dataset.violation_cell_id])
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in annotation_projection["bbox_set"]
        ]
        answer_gt = TypedValue(type="option_letter", value=str(dataset.answer_label))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

        query_params = {
            "query_id": QUERY_ID,
            "query_id_probabilities": {QUERY_ID: 1.0},
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "grid_size_variant": str(dataset.grid_size_variant),
            "grid_size_variant_probabilities": dict(grid_size_variant_probabilities),
            "rule_variant": str(dataset.rule_variant),
            "rule_variant_probabilities": dict(rule_variant_probabilities),
            "grid_rows": int(dataset.rows),
            "grid_cols": int(dataset.cols),
            "answer_label": str(dataset.answer_label),
        }
        cells_trace = [
            {
                "cell_id": str(cell.cell_id),
                "label": str(cell.label),
                "row_index": int(cell.row),
                "col_index": int(cell.col),
                "expected_hsl": [round(float(value), 6) for value in cell.expected_hsl],
                "observed_hsl": [round(float(value), 6) for value in cell.observed_hsl],
                "expected_rgb": [int(value) for value in cell.expected_rgb],
                "observed_rgb": [int(value) for value in cell.observed_rgb],
                "is_violation": bool(cell.is_violation),
            }
            for cell in dataset.cells
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": QUERY_ID,
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "grid_size_variant": str(dataset.grid_size_variant),
                    "rule_variant": str(dataset.rule_variant),
                    "answer_label": str(dataset.answer_label),
                },
            },
            "query_spec": {
                "query_id": QUERY_ID,
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "post_image_noise_policy": _post_noise_policy_trace(),
                "scene_bbox_px": [int(value) for value in rendered_scene.scene_bbox_px],
                "render_params": {
                    "swatch_size_px": int(render_params.swatch_size_px),
                    "swatch_gap_px": int(render_params.swatch_gap_px),
                    "label_chip_size_px": int(render_params.label_chip_size_px),
                },
                "label_style": {
                    "font": _font_trace_record(
                        str(font_family),
                        scope="color_gradient_swatch_labels",
                    ),
                },
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": [int(value) for value in rendered_scene.scene_bbox_px],
                "cell_bboxes_px": {str(key): list(value) for key, value in rendered_scene.cell_bbox_map.items()},
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bbox_map.items()},
                "annotation_source": "item_bboxes_px",
            }, render_params.unit_size_jitter),
            "execution_trace": {
                **dict(query_params),
                "question_format": QUERY_ID,
                "cells": cells_trace,
                "rule_params": dict(dataset.rule_params),
                "violation_cell_id": str(dataset.violation_cell_id),
                "violation_index": int(dataset.violation_index),
                "borrowed_from_label": str(dataset.borrowed_from_label),
                "supporting_item_ids": [str(dataset.violation_cell_id)],
                "answer_value": str(dataset.answer_label),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(annotation_bboxes),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": list(annotation_bboxes),
                "value": list(annotation_bboxes),
            },
        }
        grid_area = int(dataset.rows * dataset.cols)
        visual_scan = normalize_int_with_bounds(int(grid_area), [9, 16])
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(_RULE_LOAD_BY_VARIANT[str(dataset.rule_variant)]),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
            prompt_variants=dict(prompt_variants),
        )


@register_task
class PuzzlesVisualColorGradientCompletionLabelTask:
    """Choose the labeled option that completes a one-dimensional color gradient."""

    task_id = COMPLETION_TASK_ID
    domain = "puzzles"
    task_group = "visual"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            get_task_group_defaults("puzzles", "visual"),
            task_id=COMPLETION_TASK_ID,
        )
        complexity_weights = resolve_puzzle_complexity_weights(
            get_task_group_defaults("puzzles", "visual"),
            task_id=COMPLETION_TASK_ID,
        )
        last_error: Exception | None = None
        dataset: _CompletionDataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_completion_dataset(
                    params=params,
                    instance_seed=int(instance_seed) + int(attempt_index),
                    gen_defaults=gen_defaults,
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate color-gradient completion puzzle instance") from last_error

        scene_variant, scene_variant_probabilities = _resolve_axis_variant(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=COMPLETION_TASK_ID,
            supported_variants=_SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )
        sequence_length_variant_probabilities = {
            key: float(value)
            for key, value in _resolve_axis_variant(
                params=params,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                task_id=COMPLETION_TASK_ID,
                supported_variants=_COMPLETION_LENGTH_VARIANTS,
                explicit_key="sequence_length_variant",
                weights_key="sequence_length_variant_weights",
                balance_flag_key="balanced_sequence_length_variant_sampling",
                axis_namespace="sequence_length_variant",
            )[1].items()
        }
        option_count_variant_probabilities = {
            key: float(value)
            for key, value in _resolve_axis_variant(
                params=params,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                task_id=COMPLETION_TASK_ID,
                supported_variants=_COMPLETION_OPTION_COUNT_VARIANTS,
                explicit_key="option_count_variant",
                weights_key="option_count_variant_weights",
                balance_flag_key="balanced_option_count_variant_sampling",
                axis_namespace="option_count_variant",
            )[1].items()
        }
        rule_variant_probabilities = {
            key: float(value)
            for key, value in _resolve_axis_variant(
                params=params,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                task_id=COMPLETION_TASK_ID,
                supported_variants=_COMPLETION_RULE_VARIANTS,
                explicit_key="rule_variant",
                weights_key="rule_variant_weights",
                balance_flag_key="balanced_rule_variant_sampling",
                axis_namespace="rule_variant",
            )[1].items()
        }

        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        font_family = _sample_color_gradient_font(
            task_id=COMPLETION_TASK_ID,
            instance_seed=int(instance_seed),
            params=params,
            render_defaults=render_defaults,
        )
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{COMPLETION_TASK_ID}.color_gradient_background",
        )
        render_params = replace(
            render_params,
            panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
            panel_border_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
            swatch_border_rgb=tuple(int(value) for value in scene_style.grid_rgb),
            notebook_line_rgb=tuple(int(value) for value in scene_style.notebook_line_rgb),
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        with temporary_default_font_family(str(font_family)):
            rendered_scene = _render_completion_scene(
                background=background,
                dataset=dataset,
                scene_variant=str(scene_variant),
                render_params=render_params,
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            prompt_defaults=prompt_defaults,
            scene_variant=str(scene_variant),
            instance_seed=int(instance_seed),
            task_id=COMPLETION_TASK_ID,
            query_id=COMPLETION_QUERY_ID,
        )
        supporting_item_ids = [str(dataset.missing_cell_id), str(dataset.correct_option_id)]
        annotation_projection = projected_puzzle_bbox_annotation(rendered_scene.item_bbox_map, supporting_item_ids)
        annotation_bboxes = [
            [round(float(value), 3) for value in bbox]
            for bbox in annotation_projection["bbox_set"]
        ]
        annotation_keyed_bboxes = {
            "blank_swatch": list(annotation_bboxes[0]),
            "selected_option": list(annotation_bboxes[1]),
        }
        answer_gt = TypedValue(type="option_letter", value=str(dataset.answer_label))
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes))

        query_params = {
            "query_id": COMPLETION_QUERY_ID,
            "query_id_probabilities": {COMPLETION_QUERY_ID: 1.0},
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "sequence_length_variant": str(dataset.sequence_length_variant),
            "sequence_length_variant_probabilities": dict(sequence_length_variant_probabilities),
            "option_count_variant": str(dataset.option_count_variant),
            "option_count_variant_probabilities": dict(option_count_variant_probabilities),
            "rule_variant": str(dataset.rule_variant),
            "rule_variant_probabilities": dict(rule_variant_probabilities),
            "sequence_length": int(dataset.sequence_length),
            "option_count": int(dataset.option_count),
            "missing_index": int(dataset.missing_index),
            "answer_label": str(dataset.answer_label),
        }
        cells_trace = [
            {
                "cell_id": str(cell.cell_id),
                "index": int(cell.index),
                "expected_hsl": [round(float(value), 6) for value in cell.expected_hsl],
                "expected_rgb": [int(value) for value in cell.expected_rgb],
                "is_missing": bool(cell.is_missing),
            }
            for cell in dataset.cells
        ]
        options_trace = [
            {
                "option_id": str(option.option_id),
                "label": str(option.label),
                "rgb": [int(value) for value in option.rgb],
                "is_correct": bool(option.is_correct),
            }
            for option in dataset.options
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": COMPLETION_QUERY_ID,
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "sequence_length_variant": str(dataset.sequence_length_variant),
                    "option_count_variant": str(dataset.option_count_variant),
                    "rule_variant": str(dataset.rule_variant),
                    "answer_label": str(dataset.answer_label),
                },
            },
            "query_spec": {
                "query_id": COMPLETION_QUERY_ID,
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "post_image_noise_policy": _post_noise_policy_trace(),
                "scene_bbox_px": [int(value) for value in rendered_scene.scene_bbox_px],
                "render_params": {
                    "swatch_gap_px": int(render_params.swatch_gap_px),
                    "label_chip_size_px": int(render_params.label_chip_size_px),
                },
                "label_style": {
                    "font": _font_trace_record(
                        str(font_family),
                        scope="color_gradient_sequence_and_option_labels",
                    ),
                },
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": [int(value) for value in rendered_scene.scene_bbox_px],
                "cell_bboxes_px": {str(key): list(value) for key, value in rendered_scene.cell_bbox_map.items()},
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bbox_map.items()},
                "annotation_source": "item_bboxes_px",
            }, render_params.unit_size_jitter),
            "execution_trace": {
                **dict(query_params),
                "question_format": COMPLETION_QUERY_ID,
                "cells": cells_trace,
                "options": options_trace,
                "rule_params": dict(dataset.rule_params),
                "missing_cell_id": str(dataset.missing_cell_id),
                "correct_option_id": str(dataset.correct_option_id),
                "supporting_item_ids": list(supporting_item_ids),
                "answer_value": str(dataset.answer_label),
            },
            "witness_symbolic": {
                "type": "keyed_bbox_map",
                "value": dict(annotation_keyed_bboxes),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_keyed_bboxes),
                "pixel_keyed_bbox_map": dict(annotation_keyed_bboxes),
                "bbox_set": list(annotation_bboxes),
                "value": dict(annotation_keyed_bboxes),
            },
        }
        visual_scan = normalize_int_with_bounds(int(dataset.sequence_length + dataset.option_count), [9, 13])
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(_COMPLETION_RULE_LOAD_BY_VARIANT[str(dataset.rule_variant)]),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=COMPLETION_QUERY_ID,
            prompt_variants=dict(prompt_variants),
        )


__all__ = [
    "COMPLETION_QUERY_ID",
    "COMPLETION_TASK_ID",
    "PuzzlesVisualColorGradientCompletionLabelTask",
    "PuzzlesVisualColorGradientViolationCellLabelTask",
    "QUERY_ID",
    "SCENE_ID",
    "TASK_ID",
    "VIOLATION_QUERY_ID",
    "VIOLATION_TASK_ID",
]
