"""Scene-local primitives for Mancala-style pit-board sowing tasks."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import group_default, required_group_defaults
from trace.tasks.shared.font_assets import font_role_trace, sample_font_family
from trace.tasks.shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.games.shared.layout import apply_games_layout_jitter_to_bbox, resolve_games_layout_jitter
from trace.tasks.games.shared.marking import draw_optional_marker_x
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.games.shared.scene_style import draw_panel_scene_chrome, make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.text import draw_game_text_traced as draw_text_traced
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "mancala_pit_board"
SOWING_LANDING_QUERY_ID = "sowing_landing_pit_label"
POST_SOW_COUNT_QUERY_ID = "post_sow_pit_count_value"
LABELS: Tuple[str, ...] = tuple(chr(ord("A") + index) for index in range(12))
STYLE_VARIANTS: Tuple[str, ...] = ("wood_tray", "sand_stone", "slate_bowls", "cloth_pits", "arcade_pits")
SCENE_VARIANTS: Tuple[str, ...] = ("low_seed", "mixed_seed", "busy_seed")
PitBBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Mancala pit-board scenes."""

    target_count_support: Tuple[int, ...] = tuple(range(9))
    target_landing_label_support: Tuple[str, ...] = LABELS
    min_seed_count_per_pit: int = 0
    max_seed_count_per_pit: int = 8
    min_source_seed_count: int = 1
    max_source_seed_count: int = 8
    canvas_width: int = 980
    canvas_height: int = 440
    canvas_min_width_px: int = 760
    canvas_min_height_px: int = 340
    canvas_side_padding_px: int = 168
    canvas_vertical_padding_px: int = 132
    pit_width_px: int = 108
    pit_height_px: int = 68
    pit_gap_px: int = 20
    row_gap_px: int = 74
    board_padding_px: int = 48
    seed_diameter_min_px: int = 16
    seed_diameter_max_px: int = 20
    pit_outline_width_px: int = 4
    marker_width_px: int = 5


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved generation and style axes for one sample."""

    scene_variant: str
    style_variant: str
    target_landing_label: str
    target_landing_label_probabilities: Dict[str, float]
    target_count: int
    target_count_support: Tuple[int, ...]
    target_count_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    min_seed_count_per_pit: int
    max_seed_count_per_pit: int
    min_source_seed_count: int
    max_source_seed_count: int


@dataclass(frozen=True)
class _Sample:
    """One symbolic Mancala-style sowing sample."""

    query_id: str
    scene_variant: str
    style_variant: str
    initial_counts: Tuple[int, ...]
    final_counts: Tuple[int, ...]
    source_index: int
    sowing_path_indices: Tuple[int, ...]
    landing_index: int
    target_index: int | None
    answer: str | int
    construction_mode: str


@dataclass(frozen=True)
class _Theme:
    """Scene-local palette for a Mancala-style board."""

    tray_fill_rgb: Tuple[int, int, int]
    tray_border_rgb: Tuple[int, int, int]
    pit_fill_rgb: Tuple[int, int, int]
    pit_shadow_rgb: Tuple[int, int, int]
    pit_outline_rgb: Tuple[int, int, int]
    seed_rgbs: Tuple[Tuple[int, int, int], ...]
    seed_outline_rgb: Tuple[int, int, int]
    label_fill_rgb: Tuple[int, int, int]
    label_text_rgb: Tuple[int, int, int]
    arrow_rgb: Tuple[int, int, int]
    source_marker_rgb: Tuple[int, int, int]
    target_marker_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered board plus trace-friendly maps."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class GeneratedComponents:
    """Rendered and prompted scene components before public output wrapping."""

    prompt: str
    prompt_variants: Dict[str, str]
    answer_gt: TypedValue
    annotation_gt: TypedValue
    image: Image.Image
    trace_payload: Dict[str, Any]
    query_id: str


_DEFAULTS = _TaskDefaults()
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _pit_label(index: int) -> str:
    return str(LABELS[int(index) % len(LABELS)])


def _pit_index(label: str) -> int:
    normalized = str(label).strip().upper()
    if normalized not in LABELS:
        raise ValueError(f"unknown pit label: {label!r}")
    return int(LABELS.index(normalized))


def _visual_row_col(index: int) -> Tuple[int, int]:
    index = int(index) % 12
    if index < 6:
        return 0, index
    return 1, 11 - index


def _sowing_path(source_index: int, seed_count: int) -> Tuple[int, ...]:
    return tuple((int(source_index) + step) % 12 for step in range(1, int(seed_count) + 1))


def _sow_counts(initial_counts: Sequence[int], source_index: int) -> Tuple[Tuple[int, ...], Tuple[int, ...]]:
    counts = [int(value) for value in initial_counts]
    source = int(source_index) % 12
    seed_count = int(counts[source])
    counts[source] = 0
    path = _sowing_path(source, seed_count)
    for pit_index in path:
        counts[int(pit_index)] += 1
    return tuple(int(value) for value in counts), tuple(int(value) for value in path)


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace_root: str,
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=str(namespace_root),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace=f"{namespace_root}.{namespace}",
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=tuple(str(value) for value in supported),
    )


def resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace: str,
) -> _ResolvedAxes:
    scene_variant, scene_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SCENE_VARIANTS,
    )
    style_variant, style_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=STYLE_VARIANTS,
    )
    landing_label, landing_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="target_landing_label",
        explicit_key="target_landing_label",
        weights_key="target_landing_label_weights",
        balance_flag_key="balanced_target_landing_label_sampling",
        supported=tuple(
            str(value)
            for value in group_default(
                gen_defaults,
                "target_landing_label_support",
                _DEFAULTS.target_landing_label_support,
            )
        ),
    )
    target_count, target_count_probs = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="target_count_support",
        explicit_key="target_count",
        fallback_support=_DEFAULTS.target_count_support,
        namespace=f"{namespace}.target_count",
        balanced_flag_key="balanced_target_count_sampling",
        namespace_support_permutation=True,
    )
    target_count_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="target_count_support",
        fallback=_DEFAULTS.target_count_support,
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_landing_label=str(landing_label),
        target_landing_label_probabilities=dict(landing_probs),
        target_count=int(target_count),
        target_count_support=tuple(int(value) for value in target_count_support),
        target_count_probabilities=dict(target_count_probs),
        scene_variant_probabilities=dict(scene_probs),
        style_variant_probabilities=dict(style_probs),
        min_seed_count_per_pit=int(group_default(gen_defaults, "min_seed_count_per_pit", _DEFAULTS.min_seed_count_per_pit)),
        max_seed_count_per_pit=int(group_default(gen_defaults, "max_seed_count_per_pit", _DEFAULTS.max_seed_count_per_pit)),
        min_source_seed_count=int(group_default(gen_defaults, "min_source_seed_count", _DEFAULTS.min_source_seed_count)),
        max_source_seed_count=int(group_default(gen_defaults, "max_source_seed_count", _DEFAULTS.max_source_seed_count)),
    )


def _seed_count_bounds(scene_variant: str) -> Tuple[int, int]:
    if str(scene_variant) == "low_seed":
        return (0, 5)
    if str(scene_variant) == "busy_seed":
        return (2, 8)
    return (0, 8)


def _random_initial_counts(*, rng: Any, axes: _ResolvedAxes) -> List[int]:
    low, high = _seed_count_bounds(str(axes.scene_variant))
    low = int(max(int(axes.min_seed_count_per_pit), int(low)))
    high = int(min(int(axes.max_seed_count_per_pit), int(high)))
    return [int(rng.randint(low, high)) for _ in range(12)]


def sample_landing_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    target_index = _pit_index(str(axes.target_landing_label))
    min_source = int(axes.min_source_seed_count)
    max_source = int(axes.max_source_seed_count)
    viable_seed_counts = [
        seed_count
        for seed_count in range(max(1, min_source), max_source + 1)
        if seed_count <= 11
    ]
    rng.shuffle(viable_seed_counts)
    if not viable_seed_counts:
        raise ValueError("no viable source seed counts")
    source_seed_count = int(viable_seed_counts[0])
    source_index = (int(target_index) - int(source_seed_count)) % 12
    counts = _random_initial_counts(rng=rng, axes=axes)
    counts[int(source_index)] = int(source_seed_count)
    final_counts, path = _sow_counts(counts, int(source_index))
    if not path or int(path[-1]) != int(target_index):
        raise ValueError("constructed Mancala landing mismatch")
    return _Sample(
        query_id=SOWING_LANDING_QUERY_ID,
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        initial_counts=tuple(int(value) for value in counts),
        final_counts=tuple(int(value) for value in final_counts),
        source_index=int(source_index),
        sowing_path_indices=tuple(int(value) for value in path),
        landing_index=int(path[-1]),
        target_index=None,
        answer=_pit_label(int(path[-1])),
        construction_mode="target_conditioned_last_seed_landing_label",
    )


def sample_post_sow_count_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    target_answer = int(axes.target_count)
    min_source = int(axes.min_source_seed_count)
    max_source = int(axes.max_source_seed_count)
    max_seed = int(axes.max_seed_count_per_pit)
    if target_answer < 0 or target_answer > max_seed:
        raise ValueError("Mancala post-sow target count must fit seed support")
    for _attempt in range(200):
        source_index = int(rng.randrange(12))
        source_seed_count = int(rng.randint(max(1, min_source), max_source))
        path = _sowing_path(source_index, source_seed_count)
        target_candidates = [index for index in range(12) if index != source_index]
        rng.shuffle(target_candidates)
        for target_index in target_candidates:
            receives_seed = int(target_index) in set(path)
            initial_target_count = int(target_answer) - (1 if receives_seed else 0)
            if initial_target_count < 0 or initial_target_count > max_seed:
                continue
            counts = _random_initial_counts(rng=rng, axes=axes)
            counts[int(source_index)] = int(source_seed_count)
            counts[int(target_index)] = int(initial_target_count)
            final_counts, computed_path = _sow_counts(counts, int(source_index))
            if int(final_counts[int(target_index)]) != int(target_answer):
                continue
            return _Sample(
                query_id=POST_SOW_COUNT_QUERY_ID,
                scene_variant=str(axes.scene_variant),
                style_variant=str(axes.style_variant),
                initial_counts=tuple(int(value) for value in counts),
                final_counts=tuple(int(value) for value in final_counts),
                source_index=int(source_index),
                sowing_path_indices=tuple(int(value) for value in computed_path),
                landing_index=int(computed_path[-1]),
                target_index=int(target_index),
                answer=int(target_answer),
                construction_mode="target_conditioned_post_sow_target_pit_count",
            )
    raise ValueError("failed to construct Mancala post-sow count sample")


def _theme_for_style(style_variant: str) -> Tuple[_Theme, Dict[str, Any]]:
    themes: dict[str, _Theme] = {
        "wood_tray": _Theme(
            tray_fill_rgb=(189, 128, 74),
            tray_border_rgb=(90, 56, 34),
            pit_fill_rgb=(123, 75, 43),
            pit_shadow_rgb=(80, 48, 30),
            pit_outline_rgb=(236, 190, 126),
            seed_rgbs=((241, 232, 196), (142, 78, 55), (64, 82, 106)),
            seed_outline_rgb=(54, 38, 32),
            label_fill_rgb=(250, 232, 185),
            label_text_rgb=(62, 42, 25),
            arrow_rgb=(56, 39, 28),
            source_marker_rgb=(224, 38, 42),
            target_marker_rgb=(25, 127, 194),
        ),
        "sand_stone": _Theme(
            tray_fill_rgb=(219, 202, 162),
            tray_border_rgb=(106, 94, 68),
            pit_fill_rgb=(175, 157, 116),
            pit_shadow_rgb=(114, 101, 76),
            pit_outline_rgb=(249, 239, 202),
            seed_rgbs=((48, 55, 69), (198, 80, 62), (246, 236, 202)),
            seed_outline_rgb=(53, 48, 39),
            label_fill_rgb=(66, 72, 82),
            label_text_rgb=(248, 244, 229),
            arrow_rgb=(72, 67, 54),
            source_marker_rgb=(218, 43, 50),
            target_marker_rgb=(26, 117, 190),
        ),
        "slate_bowls": _Theme(
            tray_fill_rgb=(58, 70, 86),
            tray_border_rgb=(213, 220, 228),
            pit_fill_rgb=(32, 41, 55),
            pit_shadow_rgb=(14, 22, 34),
            pit_outline_rgb=(154, 170, 190),
            seed_rgbs=((240, 244, 247), (255, 188, 74), (86, 205, 189)),
            seed_outline_rgb=(13, 20, 31),
            label_fill_rgb=(228, 235, 242),
            label_text_rgb=(25, 32, 43),
            arrow_rgb=(236, 242, 249),
            source_marker_rgb=(255, 82, 94),
            target_marker_rgb=(72, 191, 255),
        ),
        "cloth_pits": _Theme(
            tray_fill_rgb=(65, 119, 96),
            tray_border_rgb=(225, 232, 216),
            pit_fill_rgb=(38, 86, 69),
            pit_shadow_rgb=(23, 58, 47),
            pit_outline_rgb=(174, 218, 185),
            seed_rgbs=((252, 235, 169), (112, 43, 82), (43, 50, 77)),
            seed_outline_rgb=(24, 35, 33),
            label_fill_rgb=(245, 243, 217),
            label_text_rgb=(33, 74, 58),
            arrow_rgb=(235, 241, 220),
            source_marker_rgb=(227, 43, 59),
            target_marker_rgb=(31, 128, 203),
        ),
        "arcade_pits": _Theme(
            tray_fill_rgb=(43, 42, 83),
            tray_border_rgb=(255, 213, 87),
            pit_fill_rgb=(28, 24, 55),
            pit_shadow_rgb=(10, 9, 25),
            pit_outline_rgb=(96, 219, 232),
            seed_rgbs=((251, 90, 154), (96, 231, 168), (255, 235, 99)),
            seed_outline_rgb=(11, 12, 28),
            label_fill_rgb=(255, 230, 98),
            label_text_rgb=(29, 27, 61),
            arrow_rgb=(96, 219, 232),
            source_marker_rgb=(255, 78, 95),
            target_marker_rgb=(98, 215, 255),
        ),
    }
    resolved = str(style_variant) if str(style_variant) in themes else "wood_tray"
    return themes[resolved], {
        "style_variant": str(resolved),
        "available_styles": list(STYLE_VARIANTS),
        "board_style_policy": "scene_local_mancala_pit_board_palette",
    }


def _bbox_pad(bbox: Sequence[float], pad: float) -> PitBBox:
    return (
        round(float(bbox[0]) - float(pad), 3),
        round(float(bbox[1]) - float(pad), 3),
        round(float(bbox[2]) + float(pad), 3),
        round(float(bbox[3]) + float(pad), 3),
    )


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    text: str,
    *,
    font: Any,
    fill: Sequence[int],
    surface_rgb: Sequence[int],
    instance_seed: int,
    namespace: str,
    role: str,
    stroke_width: int = 1,
) -> Dict[str, Any]:
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
    width = float(text_bbox[2] - text_bbox[0])
    height = float(text_bbox[3] - text_bbox[1])
    x = 0.5 * (float(bbox[0]) + float(bbox[2]) - width)
    y = 0.5 * (float(bbox[1]) + float(bbox[3]) - height)
    return draw_text_traced(
        draw,
        (float(x), float(y)),
        str(text),
        font=font,
        fill=tuple(int(v) for v in fill[:3]),
        stroke_width=max(0, int(stroke_width)),
        role=str(role),
        required=True,
        surface_rgbs=(tuple(int(v) for v in surface_rgb[:3]),),
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )


def _draw_arrow(draw: ImageDraw.ImageDraw, start: Tuple[float, float], end: Tuple[float, float], *, fill: Sequence[int], width: int) -> None:
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    draw.line((sx, sy, ex, ey), fill=tuple(int(v) for v in fill[:3]) + (235,), width=max(2, int(width)))
    angle = math.atan2(ey - sy, ex - sx)
    head_len = max(10.0, float(width) * 3.0)
    head_angle = math.radians(30.0)
    for sign in (-1.0, 1.0):
        hx = ex - head_len * math.cos(angle + sign * head_angle)
        hy = ey - head_len * math.sin(angle + sign * head_angle)
        draw.line((ex, ey, hx, hy), fill=tuple(int(v) for v in fill[:3]) + (235,), width=max(2, int(width)))


def _seed_offsets(count: int, *, pit_width: float, pit_height: float, seed_diameter: float, rng: Any) -> Tuple[Tuple[float, float], ...]:
    count = int(count)
    if count <= 0:
        return ()
    if count <= 4:
        rows = 1
    else:
        rows = 2
    first_row = int(math.ceil(float(count) / float(rows)))
    row_counts = [first_row]
    if rows == 2:
        row_counts.append(count - first_row)
    offsets: list[Tuple[float, float]] = []
    y_positions = [0.0] if rows == 1 else [-0.32 * pit_height, 0.32 * pit_height]
    for row_index, row_count in enumerate(row_counts):
        if row_count <= 0:
            continue
        if row_count == 1:
            xs = [0.0]
        else:
            span = min(float(pit_width) - (1.55 * float(seed_diameter)), (float(row_count) - 1.0) * float(seed_diameter) * 1.18)
            xs = [-0.5 * span + (span * float(col) / float(row_count - 1)) for col in range(row_count)]
        for x in xs:
            jitter_x = float(rng.uniform(-1.2, 1.2))
            jitter_y = float(rng.uniform(-1.1, 1.1))
            offsets.append((round(float(x) + jitter_x, 3), round(float(y_positions[row_index]) + jitter_y, 3)))
    return tuple(offsets[:count])


def _render_scene(
    *,
    sample: _Sample,
    axes: _ResolvedAxes,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    namespace: str,
) -> _RenderedScene:
    rng = spawn_rng(int(instance_seed), f"{namespace}.render")
    pit_width = int(params.get("pit_width_px", group_default(render_defaults, "pit_width_px", _DEFAULTS.pit_width_px)))
    pit_height = int(params.get("pit_height_px", group_default(render_defaults, "pit_height_px", _DEFAULTS.pit_height_px)))
    pit_gap = int(params.get("pit_gap_px", group_default(render_defaults, "pit_gap_px", _DEFAULTS.pit_gap_px)))
    row_gap = int(params.get("row_gap_px", group_default(render_defaults, "row_gap_px", _DEFAULTS.row_gap_px)))
    board_padding = int(params.get("board_padding_px", group_default(render_defaults, "board_padding_px", _DEFAULTS.board_padding_px)))
    seed_diameter_min = int(params.get("seed_diameter_min_px", group_default(render_defaults, "seed_diameter_min_px", _DEFAULTS.seed_diameter_min_px)))
    seed_diameter_max = int(params.get("seed_diameter_max_px", group_default(render_defaults, "seed_diameter_max_px", _DEFAULTS.seed_diameter_max_px)))
    seed_diameter = int(rng.randint(min(seed_diameter_min, seed_diameter_max), max(seed_diameter_min, seed_diameter_max)))
    pit_outline_width = int(params.get("pit_outline_width_px", group_default(render_defaults, "pit_outline_width_px", _DEFAULTS.pit_outline_width_px)))
    marker_width = int(params.get("marker_width_px", group_default(render_defaults, "marker_width_px", _DEFAULTS.marker_width_px)))
    board_width = (6 * pit_width) + (5 * pit_gap)
    board_height = (2 * pit_height) + row_gap
    side_padding = int(params.get("canvas_side_padding_px", group_default(render_defaults, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px)))
    vertical_padding = int(params.get("canvas_vertical_padding_px", group_default(render_defaults, "canvas_vertical_padding_px", _DEFAULTS.canvas_vertical_padding_px)))
    canvas_width = min(
        int(params.get("canvas_width", group_default(render_defaults, "canvas_width", _DEFAULTS.canvas_width))),
        max(
            int(params.get("canvas_min_width_px", group_default(render_defaults, "canvas_min_width_px", _DEFAULTS.canvas_min_width_px))),
            int(board_width + side_padding),
        ),
    )
    canvas_height = min(
        int(params.get("canvas_height", group_default(render_defaults, "canvas_height", _DEFAULTS.canvas_height))),
        max(
            int(params.get("canvas_min_height_px", group_default(render_defaults, "canvas_min_height_px", _DEFAULTS.canvas_min_height_px))),
            int(board_height + vertical_padding),
        ),
    )
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.panel_scene_style",
        treatment_weights=params.get("panel_scene_treatment_weights", group_default(render_defaults, "panel_scene_treatment_weights", None)),
        palette_weights=params.get("panel_scene_palette_weights", group_default(render_defaults, "panel_scene_palette_weights", None)),
    )
    image, background_meta = make_panel_scene_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=panel_style,
    )
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    theme, theme_meta = _theme_for_style(str(axes.style_variant))
    board_bbox = (
        round(0.5 * (float(canvas_width) - float(board_width)), 3),
        round(0.5 * (float(canvas_height) - float(board_height)), 3),
        round(0.5 * (float(canvas_width) + float(board_width)), 3),
        round(0.5 * (float(canvas_height) + float(board_height)), 3),
    )
    layout_jitter = resolve_games_layout_jitter(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.layout",
    )
    board_bbox, _dx, _dy, resolved_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=board_bbox,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        jitter=layout_jitter,
    )
    tray_bbox = _bbox_pad(board_bbox, float(board_padding))
    draw_panel_scene_chrome(
        draw,
        bbox=tuple(int(round(value)) for value in tray_bbox),
        style=panel_style,
        radius=32,
        border_width=max(2, int(round(float(pit_outline_width) * 0.8))),
    )
    draw.rounded_rectangle(
        tray_bbox,
        radius=max(28, int(round(float(pit_height) * 0.55))),
        fill=tuple(theme.tray_fill_rgb) + (242,),
        outline=tuple(theme.tray_border_rgb) + (255,),
        width=max(2, int(pit_outline_width)),
    )

    pit_bboxes: Dict[str, List[float]] = {}
    pit_centers: Dict[str, List[float]] = {}
    seed_centers: Dict[str, List[List[float]]] = {}
    entities: List[Dict[str, Any]] = []
    label_font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.pit_labels",
        params=params,
        explicit_key="pit_label_font_family",
        weights_key="pit_label_font_family_weights",
    )
    label_font = load_font(max(16, int(round(float(pit_height) * 0.30))), bold=True, font_family=label_font_family)
    mark_font = load_font(max(15, int(round(float(pit_height) * 0.24))), bold=True, font_family=label_font_family)
    board_left = float(board_bbox[0])
    board_top = float(board_bbox[1])
    for pit_index in range(12):
        row, col = _visual_row_col(pit_index)
        x0 = board_left + (float(col) * float(pit_width + pit_gap))
        y0 = board_top + (float(row) * float(pit_height + row_gap))
        pit_bbox: PitBBox = (round(x0, 3), round(y0, 3), round(x0 + pit_width, 3), round(y0 + pit_height, 3))
        center = [round(0.5 * (pit_bbox[0] + pit_bbox[2]), 3), round(0.5 * (pit_bbox[1] + pit_bbox[3]), 3)]
        label = _pit_label(pit_index)
        pit_id = f"pit_{label}"
        shadow_bbox = (pit_bbox[0] + 0.0, pit_bbox[1] + 5.0, pit_bbox[2], pit_bbox[3] + 5.0)
        draw.ellipse(shadow_bbox, fill=tuple(theme.pit_shadow_rgb) + (120,))
        draw.ellipse(
            pit_bbox,
            fill=tuple(theme.pit_fill_rgb) + (255,),
            outline=tuple(theme.pit_outline_rgb) + (255,),
            width=max(2, int(pit_outline_width)),
        )
        label_radius = max(15, int(round(float(pit_height) * 0.22)))
        label_center = (pit_bbox[0] + label_radius + 5.0, pit_bbox[1] + label_radius + 5.0)
        label_bbox = (
            label_center[0] - label_radius,
            label_center[1] - label_radius,
            label_center[0] + label_radius,
            label_center[1] + label_radius,
        )
        draw.ellipse(
            label_bbox,
            fill=tuple(theme.label_fill_rgb) + (245,),
            outline=tuple(theme.tray_border_rgb) + (210,),
            width=1,
        )
        _draw_centered_text(
            draw,
            label_bbox,
            label,
            font=label_font,
            fill=theme.label_text_rgb,
            surface_rgb=theme.label_fill_rgb,
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.label.{label}",
            role="board_mark",
            stroke_width=0,
        )
        pit_bboxes[pit_id] = [float(value) for value in pit_bbox]
        pit_centers[pit_id] = [float(value) for value in center]
        seed_rng = spawn_rng(int(instance_seed), f"{namespace}.pit.{label}.seeds")
        offsets = _seed_offsets(
            int(sample.initial_counts[pit_index]),
            pit_width=float(pit_width) * 0.78,
            pit_height=float(pit_height) * 0.50,
            seed_diameter=float(seed_diameter),
            rng=seed_rng,
        )
        pit_seed_centers: list[list[float]] = []
        for seed_index, offset in enumerate(offsets):
            sx = float(center[0]) + float(offset[0]) + 8.0
            sy = float(center[1]) + float(offset[1]) + 5.0
            seed_bbox = (
                sx - (0.5 * float(seed_diameter)),
                sy - (0.5 * float(seed_diameter)),
                sx + (0.5 * float(seed_diameter)),
                sy + (0.5 * float(seed_diameter)),
            )
            seed_rgb = tuple(theme.seed_rgbs[(pit_index + seed_index) % len(theme.seed_rgbs)])
            draw.ellipse(
                seed_bbox,
                fill=seed_rgb + (255,),
                outline=tuple(theme.seed_outline_rgb) + (235,),
                width=max(1, int(round(float(seed_diameter) * 0.10))),
            )
            highlight_radius = max(2.0, float(seed_diameter) * 0.15)
            draw.ellipse(
                (
                    sx - (0.20 * float(seed_diameter)),
                    sy - (0.24 * float(seed_diameter)),
                    sx - (0.20 * float(seed_diameter)) + highlight_radius,
                    sy - (0.24 * float(seed_diameter)) + highlight_radius,
                ),
                fill=(255, 255, 255, 84),
            )
            pit_seed_centers.append([round(float(sx), 3), round(float(sy), 3)])
        seed_centers[pit_id] = pit_seed_centers
        entities.append(
            {
                "entity_id": str(pit_id),
                "entity_type": "mancala_pit",
                "pit_index": int(pit_index),
                "label": str(label),
                "row": int(row),
                "col": int(col),
                "initial_seed_count": int(sample.initial_counts[pit_index]),
                "final_seed_count": int(sample.final_counts[pit_index]),
                "center_px": list(center),
                "bbox_px": [float(value) for value in pit_bbox],
            }
        )

    arrow_width = max(3, int(round(float(pit_outline_width) * 0.85)))
    top_y = float(board_bbox[1]) - 20.0
    bottom_y = float(board_bbox[3]) + 20.0
    left_x = float(board_bbox[0]) - 24.0
    right_x = float(board_bbox[2]) + 24.0
    for pit_index in range(5):
        start_pit = pit_centers[f"pit_{_pit_label(pit_index)}"]
        end_pit = pit_centers[f"pit_{_pit_label(pit_index + 1)}"]
        _draw_arrow(draw, (start_pit[0] + 0.36 * pit_width, top_y), (end_pit[0] - 0.36 * pit_width, top_y), fill=theme.arrow_rgb, width=arrow_width)
    _draw_arrow(draw, (right_x, float(pit_centers["pit_F"][1]) + 0.30 * pit_height), (right_x, float(pit_centers["pit_G"][1]) - 0.30 * pit_height), fill=theme.arrow_rgb, width=arrow_width)
    for pit_index in range(6, 11):
        start_pit = pit_centers[f"pit_{_pit_label(pit_index)}"]
        end_pit = pit_centers[f"pit_{_pit_label(pit_index + 1)}"]
        _draw_arrow(draw, (start_pit[0] - 0.36 * pit_width, bottom_y), (end_pit[0] + 0.36 * pit_width, bottom_y), fill=theme.arrow_rgb, width=arrow_width)
    _draw_arrow(draw, (left_x, float(pit_centers["pit_L"][1]) - 0.30 * pit_height), (left_x, float(pit_centers["pit_A"][1]) + 0.30 * pit_height), fill=theme.arrow_rgb, width=arrow_width)

    source_pit_id = f"pit_{_pit_label(sample.source_index)}"
    source_bbox = pit_bboxes[source_pit_id]
    source_marker_bbox = _bbox_pad(source_bbox, max(5.0, float(marker_width) * 1.2))
    draw.ellipse(
        source_marker_bbox,
        outline=tuple(theme.source_marker_rgb) + (255,),
        width=max(3, int(marker_width)),
    )
    source_badge_size = max(24, int(round(float(pit_height) * 0.36)))
    source_badge_bbox = (
        float(source_bbox[2]) - source_badge_size - 4.0,
        float(source_bbox[1]) + 4.0,
        float(source_bbox[2]) - 4.0,
        float(source_bbox[1]) + source_badge_size + 4.0,
    )
    draw.rounded_rectangle(
        source_badge_bbox,
        radius=max(5, int(round(float(source_badge_size) * 0.25))),
        fill=(255, 255, 255, 246),
        outline=tuple(theme.source_marker_rgb) + (255,),
        width=max(1, int(round(float(marker_width) * 0.38))),
    )
    draw_optional_marker_x(
        draw,
        source_badge_bbox,
        enabled=True,
        width=max(3, int(round(float(marker_width) * 0.85))),
        inset_fraction=0.20,
        outer_rgb=(255, 255, 255),
        inner_rgb=theme.source_marker_rgb,
        marker_kind="source_pit_x",
        extra_metadata={"pit_id": source_pit_id},
    )
    marker_metadata: Dict[str, Any] = {
        "source_pit_marker": {
            "pit_id": source_pit_id,
            "bbox_px": list(source_marker_bbox),
            "x_badge_bbox_px": list(source_badge_bbox),
        }
    }
    if sample.target_index is not None:
        target_pit_id = f"pit_{_pit_label(int(sample.target_index))}"
        target_bbox = pit_bboxes[target_pit_id]
        target_marker_bbox = _bbox_pad(target_bbox, max(7.0, float(marker_width) * 1.5))
        draw.ellipse(
            target_marker_bbox,
            outline=tuple(theme.target_marker_rgb) + (255,),
            width=max(3, int(marker_width)),
        )
        badge_size = max(22, int(round(float(pit_height) * 0.32)))
        badge_bbox = (
            float(target_bbox[2]) - badge_size - 4.0,
            float(target_bbox[1]) + 4.0,
            float(target_bbox[2]) - 4.0,
            float(target_bbox[1]) + badge_size + 4.0,
        )
        draw.rounded_rectangle(
            badge_bbox,
            radius=max(5, int(round(float(badge_size) * 0.25))),
            fill=tuple(theme.target_marker_rgb) + (245,),
            outline=tuple(theme.pit_outline_rgb) + (230,),
            width=1,
        )
        _draw_centered_text(
            draw,
            badge_bbox,
            "T",
            font=mark_font,
            fill=(255, 255, 255),
            surface_rgb=theme.target_marker_rgb,
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.target_badge",
            role="board_mark",
            stroke_width=0,
        )
        marker_metadata["target_pit_marker"] = {"pit_id": target_pit_id, "bbox_px": list(target_marker_bbox)}

    render_map = {
        "board_bbox_px": [float(value) for value in board_bbox],
        "tray_bbox_px": [float(value) for value in tray_bbox],
        "pit_bboxes_px": dict(pit_bboxes),
        "pit_centers_px": dict(pit_centers),
        "seed_centers_px": dict(seed_centers),
        "layout_jitter": dict(resolved_jitter),
        "marker_metadata": dict(marker_metadata),
        "effective_pit_width_px": int(pit_width),
        "effective_pit_height_px": int(pit_height),
        "effective_seed_diameter_px": int(seed_diameter),
        "effective_pit_outline_width_px": int(pit_outline_width),
        "pit_label_font": font_role_trace(str(label_font_family), role="readout"),
    }
    return _RenderedScene(
        image=image.convert("RGB"),
        entities=tuple(entities),
        render_map=render_map,
        style_meta={
            "panel_scene_style": dict(panel_style_meta),
            "mancala_pit_board_style": dict(theme_meta),
            "pit_label_font": font_role_trace(str(label_font_family), role="readout"),
        },
        background_meta=dict(background_meta),
    )


def _json_examples(query_id: str) -> Tuple[str, str]:
    if str(query_id) == POST_SOW_COUNT_QUERY_ID:
        annotation = {"source_pit": [80, 140, 180, 204], "target_pit": [420, 140, 520, 204]}
        return (
            json.dumps({"annotation": annotation, "answer": 5}, separators=(",", ":"), ensure_ascii=True),
            json.dumps({"answer": 5}, separators=(",", ":"), ensure_ascii=True),
        )
    annotation = [[420, 140, 520, 204]]
    return (
        json.dumps({"annotation": annotation, "answer": "G"}, separators=(",", ":"), ensure_ascii=True),
        json.dumps({"answer": "G"}, separators=(",", ":"), ensure_ascii=True),
    )


def _build_prompt(
    *,
    sample: _Sample,
    query_id: str,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    answer_hint_key = f"answer_hint_{str(query_id)}"
    annotation_hint_key = f"annotation_hint_{str(query_id)}"
    required_keys = [
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        f"object_description_{str(sample.scene_variant)}",
        "sowing_rule_text",
        answer_hint_key,
        annotation_hint_key,
    ]
    prompt_defaults = required_group_defaults(
        prompt_defaults,
        tuple(required_keys),
        context=f"prompt defaults for {SCENE_ID}",
    )
    json_example, json_example_answer_only = _json_examples(str(query_id))
    prompt_selection = render_scene_prompt_variants(
        domain="games",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "object_description": str(prompt_defaults[f"object_description_{str(sample.scene_variant)}"]),
            "sowing_rule_text": str(prompt_defaults["sowing_rule_text"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults[answer_hint_key]),
            "annotation_hint": str(prompt_defaults[annotation_hint_key]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "bundle_id": str(prompt_defaults["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
    }


def _annotation_for_sample(sample: _Sample, rendered: _RenderedScene) -> Tuple[TypedValue, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    pit_bboxes = rendered.render_map["pit_bboxes_px"]
    if str(sample.query_id) == POST_SOW_COUNT_QUERY_ID:
        assert sample.target_index is not None
        source_id = f"pit_{_pit_label(sample.source_index)}"
        target_id = f"pit_{_pit_label(int(sample.target_index))}"
        annotation_map = {
            "source_pit": list(pit_bboxes[source_id]),
            "target_pit": list(pit_bboxes[target_id]),
        }
        return (
            TypedValue(type="keyed_bbox_map", value=dict(annotation_map)),
            {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_map),
                "pixel_keyed_bbox_map": dict(annotation_map),
            },
            {"type": "keyed_bbox_map", "ids": {"source_pit": source_id, "target_pit": target_id}},
            {"source_pit": source_id, "target_pit": target_id},
        )
    landing_id = f"pit_{_pit_label(sample.landing_index)}"
    annotation_boxes = [list(pit_bboxes[landing_id])]
    return (
        TypedValue(type="bbox_set", value=annotation_boxes),
        {
            "type": "bbox_set",
            "bbox_set": [list(box) for box in annotation_boxes],
            "pixel_bbox_set": [list(box) for box in annotation_boxes],
        },
        {"type": "bbox_set", "ids": [landing_id]},
        {"landing_pit": landing_id},
    )


def build_components(
    *,
    query_id: str,
    sampled: _Sample,
    axes: _ResolvedAxes,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    namespace: str,
) -> GeneratedComponents:
    rendered = _render_scene(
        sample=sampled,
        axes=axes,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=render_defaults,
        namespace=str(namespace),
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    prompt, prompt_variants, prompt_meta = _build_prompt(
        sample=sampled,
        query_id=str(query_id),
        prompt_defaults=prompt_defaults,
        instance_seed=int(instance_seed),
    )
    answer_gt = TypedValue(type="string", value=str(sampled.answer)) if str(query_id) == SOWING_LANDING_QUERY_ID else TypedValue(type="integer", value=int(sampled.answer))
    annotation_gt, projected_annotation, witness_symbolic, annotation_entity_ids = _annotation_for_sample(sampled, rendered)
    trace_payload = {
        "scene_ir": {
            "scene_kind": "games_mancala_pit_board",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_id": SCENE_ID,
                "scene_variant": str(sampled.scene_variant),
                "query_id": str(query_id),
                "style_variant": str(sampled.style_variant),
                "source_pit": str(_pit_label(sampled.source_index)),
                "target_pit": None if sampled.target_index is None else str(_pit_label(int(sampled.target_index))),
                "landing_pit": str(_pit_label(sampled.landing_index)),
                "annotation_entity_ids": dict(annotation_entity_ids),
            },
        },
        "query_spec": {
            "query_id": str(query_id),
            "template_id": str(prompt_meta["bundle_id"]),
            "prompt_variant": dict(prompt_meta["prompt_variant"]),
            "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
            "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
            "params": {
                "scene_variant": str(axes.scene_variant),
                "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                "style_variant": str(axes.style_variant),
                "style_variant_probabilities": dict(axes.style_variant_probabilities),
                "target_landing_label": str(axes.target_landing_label),
                "target_landing_label_support": list(LABELS),
                "target_landing_label_probabilities": dict(axes.target_landing_label_probabilities),
                "target_count": int(axes.target_count),
                "target_count_support": [int(value) for value in axes.target_count_support],
                "target_count_probabilities": dict(axes.target_count_probabilities),
            },
        },
        "render_spec": {
            "scene_variant": str(sampled.scene_variant),
            "style_variant": str(sampled.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(rendered.style_meta.get("panel_scene_style", {})),
            "mancala_pit_board_style": dict(rendered.style_meta.get("mancala_pit_board_style", {})),
            "pit_label_font": dict(rendered.style_meta.get("pit_label_font", {})),
            "effective_pit_width_px": int(rendered.render_map["effective_pit_width_px"]),
            "effective_pit_height_px": int(rendered.render_map["effective_pit_height_px"]),
            "effective_seed_diameter_px": int(rendered.render_map["effective_seed_diameter_px"]),
        },
        "render_map": dict(rendered.render_map),
        "execution_trace": {
            "scene_variant": str(sampled.scene_variant),
            "query_id": str(query_id),
            "style_variant": str(sampled.style_variant),
            "construction_mode": str(sampled.construction_mode),
            "initial_counts_by_label": {
                _pit_label(index): int(sampled.initial_counts[index])
                for index in range(12)
            },
            "final_counts_by_label": {
                _pit_label(index): int(sampled.final_counts[index])
                for index in range(12)
            },
            "source_index": int(sampled.source_index),
            "source_label": str(_pit_label(sampled.source_index)),
            "source_seed_count": int(sampled.initial_counts[sampled.source_index]),
            "sowing_path_indices": [int(value) for value in sampled.sowing_path_indices],
            "sowing_path_labels": [str(_pit_label(value)) for value in sampled.sowing_path_indices],
            "landing_index": int(sampled.landing_index),
            "landing_label": str(_pit_label(sampled.landing_index)),
            "target_index": None if sampled.target_index is None else int(sampled.target_index),
            "target_label": None if sampled.target_index is None else str(_pit_label(int(sampled.target_index))),
            "answer": sampled.answer,
            "annotation_entity_ids": dict(annotation_entity_ids),
        },
        "witness_symbolic": dict(witness_symbolic),
        "projected_annotation": dict(projected_annotation),
        "background": dict(rendered.background_meta),
        "post_image_noise": post_noise_meta,
    }
    return GeneratedComponents(
        prompt=str(prompt),
        prompt_variants=dict(prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        trace_payload=trace_payload,
        query_id=str(query_id),
    )


__all__ = [
    "POST_SOW_COUNT_QUERY_ID",
    "SCENE_ID",
    "SOWING_LANDING_QUERY_ID",
    "GeneratedComponents",
    "build_components",
    "resolve_axes",
    "sample_landing_scene",
    "sample_post_sow_count_scene",
]
