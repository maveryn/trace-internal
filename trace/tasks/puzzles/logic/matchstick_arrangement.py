"""Matchstick arrangement puzzle tasks."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_centered_text, draw_rounded_rect
from ...shared.mcq import option_label_for_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ..shared.common import load_puzzle_task_defaults, projected_puzzle_bbox_evidence, resolve_puzzle_axis_variant
from ..shared.complexity import build_puzzle_complexity, clamp_unit_interval, normalize_int_with_bounds
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


SCENE_ID = "matchstick"
NUMBER_TASK_ID = "task_puzzles__matchstick__matchstick_number_transform_label"
ENDPOINT_TASK_ID = "task_puzzles__matchstick__matchstick_loose_endpoint_extremum_label"

NUMBER_QUERY_IDS: Tuple[str, ...] = ("add_one_stick", "remove_one_stick")
ENDPOINT_QUERY_IDS: Tuple[str, ...] = ("most_loose_endpoints", "fewest_loose_endpoints")
SCENE_VARIANTS: Tuple[str, ...] = (
    "wooden_matches",
    "colored_rods",
    "chalk_sticks",
    "neon_rods",
    "metal_rods",
)
_LABEL_POOL = tuple("ABCDEF")

Color = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]
Point = Tuple[int, int]
Edge = Tuple[Point, Point]

_DIGIT_SEGMENTS: Dict[int, frozenset[str]] = {
    0: frozenset(("a", "b", "c", "d", "e", "f")),
    1: frozenset(("b", "c")),
    2: frozenset(("a", "b", "g", "e", "d")),
    3: frozenset(("a", "b", "c", "d", "g")),
    4: frozenset(("f", "g", "b", "c")),
    5: frozenset(("a", "f", "g", "c", "d")),
    6: frozenset(("a", "f", "e", "d", "c", "g")),
    7: frozenset(("a", "b", "c")),
    8: frozenset(("a", "b", "c", "d", "e", "f", "g")),
    9: frozenset(("a", "b", "c", "d", "f", "g")),
}
_SEGMENT_POINTS: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]] = {
    "a": ((0.0, 0.0), (1.0, 0.0)),
    "b": ((1.0, 0.0), (1.0, 1.0)),
    "c": ((1.0, 1.0), (1.0, 2.0)),
    "d": ((0.0, 2.0), (1.0, 2.0)),
    "e": ((0.0, 1.0), (0.0, 2.0)),
    "f": ((0.0, 0.0), (0.0, 1.0)),
    "g": ((0.0, 1.0), (1.0, 1.0)),
}
_SCENE_LOAD = {
    "wooden_matches": 0.18,
    "colored_rods": 0.22,
    "chalk_sticks": 0.24,
    "neon_rods": 0.28,
    "metal_rods": 0.26,
}
_QUERY_LOAD = {
    "add_one_stick": 0.48,
    "remove_one_stick": 0.48,
    "most_loose_endpoints": 0.56,
    "fewest_loose_endpoints": 0.56,
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "logic")
POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="logic")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="logic", apply_prob=0.15)


@dataclass(frozen=True)
class _RenderParams:
    """Resolved matchstick-render parameters."""

    canvas_width: int
    canvas_height: int
    margin_px: int
    source_panel_height_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    panel_corner_radius_px: int
    panel_border_width_px: int
    stick_width_px: int
    option_label_font_size_px: int
    caption_font_size_px: int
    source_caption_font_size_px: int


@dataclass(frozen=True)
class _OptionSpec:
    """One labeled option panel."""

    label: str
    is_correct: bool
    value: Any
    metric_value: int | None = None


@dataclass(frozen=True)
class _NumberDataset:
    """Resolved number-transform instance."""

    query_id: str
    scene_variant: str
    source_number: int
    answer_number: int
    answer_label: str
    option_count: int
    option_specs: Tuple[_OptionSpec, ...]
    changed_digit_index: int
    removed_segment_keys: Tuple[str, ...]
    added_segment_keys: Tuple[str, ...]


@dataclass(frozen=True)
class _ShapeDataset:
    """Resolved loose-endpoint extremum instance."""

    query_id: str
    scene_variant: str
    answer_label: str
    option_count: int
    option_specs: Tuple[_OptionSpec, ...]
    grid_size: int


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered image plus projection maps."""

    image: Image.Image
    scene_bbox_px: BBox
    item_bbox_map: Dict[str, BBox]
    entities: Tuple[Dict[str, Any], ...]


def _to_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(fallback)


def _resolve_render_params(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> _RenderParams:
    return _RenderParams(
        canvas_width=max(900, _to_int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 1200)), 1200)),
        canvas_height=max(760, _to_int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 900)), 900)),
        margin_px=max(40, _to_int(params.get("margin_px", group_default(render_defaults, "margin_px", 58)), 58)),
        source_panel_height_px=max(160, _to_int(params.get("source_panel_height_px", group_default(render_defaults, "source_panel_height_px", 230)), 230)),
        option_panel_width_px=max(180, _to_int(params.get("option_panel_width_px", group_default(render_defaults, "option_panel_width_px", 320)), 320)),
        option_panel_height_px=max(150, _to_int(params.get("option_panel_height_px", group_default(render_defaults, "option_panel_height_px", 218)), 218)),
        option_gap_px=max(12, _to_int(params.get("option_gap_px", group_default(render_defaults, "option_gap_px", 28)), 28)),
        panel_corner_radius_px=max(0, _to_int(params.get("panel_corner_radius_px", group_default(render_defaults, "panel_corner_radius_px", 20)), 20)),
        panel_border_width_px=max(1, _to_int(params.get("panel_border_width_px", group_default(render_defaults, "panel_border_width_px", 3)), 3)),
        stick_width_px=max(5, _to_int(params.get("stick_width_px", group_default(render_defaults, "stick_width_px", 13)), 13)),
        option_label_font_size_px=max(18, _to_int(params.get("option_label_font_size_px", group_default(render_defaults, "option_label_font_size_px", 26)), 26)),
        caption_font_size_px=max(16, _to_int(params.get("caption_font_size_px", group_default(render_defaults, "caption_font_size_px", 21)), 21)),
        source_caption_font_size_px=max(18, _to_int(params.get("source_caption_font_size_px", group_default(render_defaults, "source_caption_font_size_px", 24)), 24)),
    )


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_puzzle_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_axis_variant(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    supported_variants: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    axis_namespace: str,
) -> Tuple[str, Dict[str, float]]:
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


def _resolve_option_count(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    *,
    rng,
    force_count: int | None = None,
) -> Tuple[int, Tuple[int, int]]:
    if force_count is not None:
        count = max(4, min(len(_LABEL_POOL), int(force_count)))
        return int(count), (int(count), int(count))
    if "option_count" in params:
        count = max(4, min(len(_LABEL_POOL), int(params["option_count"])))
        return int(count), (int(count), int(count))
    low, high = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=4,
        fallback_max=6,
        context="matchstick option count",
    )
    low = max(4, min(len(_LABEL_POOL), int(low)))
    high = max(int(low), min(len(_LABEL_POOL), int(high)))
    return int(rng.randint(int(low), int(high))), (int(low), int(high))


def _number_digits(value: int) -> Tuple[int, int]:
    text = f"{int(value):02d}"
    return int(text[0]), int(text[1])


def _number_text(value: int) -> str:
    return f"{int(value):02d}"


def _number_segment_keys(value: int) -> frozenset[str]:
    keys: List[str] = []
    for digit_index, digit in enumerate(_number_digits(int(value))):
        for segment in sorted(_DIGIT_SEGMENTS[int(digit)]):
            keys.append(f"digit{digit_index}:{segment}")
    return frozenset(keys)


def _number_transition_allowed(source_number: int, target_number: int, query_id: str) -> bool:
    source = _number_segment_keys(int(source_number))
    target = _number_segment_keys(int(target_number))
    removed = source - target
    added = target - source
    if str(query_id) == "add_one_stick":
        return not removed and len(added) == 1
    if str(query_id) == "remove_one_stick":
        return len(removed) == 1 and not added
    raise ValueError(f"unsupported matchstick number query: {query_id}")


def _changed_digit_index(source_number: int, target_number: int) -> int:
    source_digits = _number_digits(int(source_number))
    target_digits = _number_digits(int(target_number))
    changed = [index for index, (left, right) in enumerate(zip(source_digits, target_digits)) if int(left) != int(right)]
    return int(changed[0]) if changed else -1


def _build_number_dataset(
    *,
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    task_id: str,
    instance_seed: int,
) -> _NumberDataset:
    rng = spawn_rng(int(instance_seed), f"{task_id}.number_dataset")
    option_count, option_range = _resolve_option_count(params, gen_defaults, rng=rng, force_count=6)
    answer_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.answer_option:{option_range[1]}",
        )
        % max(1, int(option_count))
    )

    numbers = list(range(10, 100))
    rng.shuffle(numbers)
    for source_number in numbers:
        reachable = [
            target_number
            for target_number in range(10, 100)
            if int(target_number) != int(source_number)
            and _number_transition_allowed(int(source_number), int(target_number), str(query_id))
        ]
        if not reachable:
            continue
        answer_number = int(reachable[int(rng.randrange(len(reachable)))])
        distractors = [
            target_number
            for target_number in range(10, 100)
            if int(target_number) != int(source_number)
            and int(target_number) != int(answer_number)
            and not _number_transition_allowed(int(source_number), int(target_number), str(query_id))
        ]
        rng.shuffle(distractors)
        if len(distractors) < int(option_count) - 1:
            continue
        options = [int(value) for value in distractors[: int(option_count) - 1]]
        options.insert(int(answer_index), int(answer_number))
        option_specs: List[_OptionSpec] = []
        for index, number in enumerate(options):
            label = option_label_for_index(int(index))
            option_specs.append(
                _OptionSpec(
                    label=str(label),
                    is_correct=bool(index == int(answer_index)),
                    value=int(number),
                    metric_value=None,
                )
            )
        source_keys = _number_segment_keys(int(source_number))
        answer_keys = _number_segment_keys(int(answer_number))
        return _NumberDataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            source_number=int(source_number),
            answer_number=int(answer_number),
            answer_label=str(option_label_for_index(int(answer_index))),
            option_count=int(option_count),
            option_specs=tuple(option_specs),
            changed_digit_index=int(_changed_digit_index(int(source_number), int(answer_number))),
            removed_segment_keys=tuple(sorted(source_keys - answer_keys)),
            added_segment_keys=tuple(sorted(answer_keys - source_keys)),
        )
    raise RuntimeError(f"failed to sample matchstick number dataset for {query_id}")


def _edge_key(a: Point, b: Point) -> Edge:
    left = (int(a[0]), int(a[1]))
    right = (int(b[0]), int(b[1]))
    return (left, right) if left <= right else (right, left)


def _all_square_grid_edges(grid_size: int) -> Tuple[Edge, ...]:
    edges: List[Edge] = []
    for row in range(int(grid_size) + 1):
        for col in range(int(grid_size)):
            edges.append(_edge_key((col, row), (col + 1, row)))
    for row in range(int(grid_size)):
        for col in range(int(grid_size) + 1):
            edges.append(_edge_key((col, row), (col, row + 1)))
    return tuple(edges)


def _edge_signature(edges: Iterable[Edge]) -> Tuple[Edge, ...]:
    return tuple(sorted({_edge_key(a, b) for a, b in edges}))


def _loose_endpoint_count(edges: Iterable[Edge]) -> int:
    degree: Counter[Point] = Counter()
    for a, b in _edge_signature(edges):
        degree[(int(a[0]), int(a[1]))] += 1
        degree[(int(b[0]), int(b[1]))] += 1
    return int(sum(1 for value in degree.values() if int(value) == 1))


def _shape_metric(edges: Iterable[Edge], query_id: str, *, grid_size: int) -> int:
    if str(query_id) in ENDPOINT_QUERY_IDS:
        return _loose_endpoint_count(edges)
    raise ValueError(f"unsupported matchstick endpoint query: {query_id}")


def _edge_trace(edges: Iterable[Edge]) -> List[List[List[int]]]:
    return [
        [[int(a[0]), int(a[1])], [int(b[0]), int(b[1])]]
        for a, b in _edge_signature(edges)
    ]


def _random_source_edges(rng, *, all_edges: Sequence[Edge], edge_count_min: int, edge_count_max: int) -> Tuple[Edge, ...]:
    edge_count = int(rng.randint(int(edge_count_min), int(edge_count_max)))
    edge_count = max(4, min(len(all_edges) - 2, int(edge_count)))
    chosen = rng.sample(list(all_edges), int(edge_count))
    return _edge_signature(chosen)


def _build_shape_dataset(
    *,
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    task_id: str,
    instance_seed: int,
) -> _ShapeDataset:
    rng = spawn_rng(int(instance_seed), f"{task_id}.shape_dataset")
    option_count, option_range = _resolve_option_count(params, gen_defaults, rng=rng, force_count=6)
    grid_size = int(params.get("grid_size", group_default(gen_defaults, "grid_size", 3)))
    grid_size = max(2, min(4, int(grid_size)))
    all_edges = _all_square_grid_edges(int(grid_size))
    edge_min, edge_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="shape_edge_count_min",
        max_key="shape_edge_count_max",
        fallback_min=8,
        fallback_max=15,
        context=f"{task_id} shape edge count",
    )
    answer_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.answer_option:{option_range[1]}",
        )
        % max(1, int(option_count))
    )

    for _attempt in range(500):
        sampled: Dict[Tuple[Edge, ...], int] = {}
        for _sample_index in range(180):
            candidate = _random_source_edges(rng, all_edges=all_edges, edge_count_min=int(edge_min), edge_count_max=int(edge_max))
            sampled[tuple(candidate)] = _shape_metric(candidate, str(query_id), grid_size=int(grid_size))
        if len(sampled) < int(option_count):
            continue
        metric_to_candidates: Dict[int, List[Tuple[Edge, ...]]] = defaultdict(list)
        for candidate, metric in sampled.items():
            metric_to_candidates[int(metric)].append(tuple(candidate))
        if len(metric_to_candidates) < 2:
            continue
        metrics = sorted(int(value) for value in metric_to_candidates)
        target_metric = int(metrics[-1] if str(query_id) == "most_loose_endpoints" else metrics[0])
        distractor_metrics = [metric for metric in metrics if int(metric) != int(target_metric)]
        distractor_pool = [candidate for metric in distractor_metrics for candidate in metric_to_candidates[int(metric)]]
        rng.shuffle(distractor_pool)
        if len(distractor_pool) < int(option_count) - 1:
            continue
        answer_edges = tuple(metric_to_candidates[target_metric][int(rng.randrange(len(metric_to_candidates[target_metric])))] )
        chosen = list(distractor_pool[: int(option_count) - 1])
        options = list(chosen)
        options.insert(int(answer_index), answer_edges)
        option_specs: List[_OptionSpec] = []
        for index, edges in enumerate(options):
            label = option_label_for_index(int(index))
            metric = _shape_metric(edges, str(query_id), grid_size=int(grid_size))
            option_specs.append(
                _OptionSpec(
                    label=str(label),
                    is_correct=bool(index == int(answer_index)),
                    value=tuple(edges),
                    metric_value=int(metric),
                )
            )
        return _ShapeDataset(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            answer_label=str(option_label_for_index(int(answer_index))),
            option_count=int(option_count),
            option_specs=tuple(option_specs),
            grid_size=int(grid_size),
        )
    raise RuntimeError(f"failed to sample matchstick endpoint-extremum dataset for {query_id}")


def _style(scene_variant: str) -> Dict[str, Any]:
    if scene_variant == "chalk_sticks":
        return {
            "background": (33, 39, 45),
            "panel_fill": (42, 49, 57),
            "panel_outline": (142, 154, 166),
            "stick": (235, 237, 230),
            "stick_shadow": (22, 26, 30),
            "label_fill": (248, 249, 244),
            "label_text": (25, 30, 36),
            "caption": (244, 246, 240),
            "tip": None,
            "palette": (),
        }
    if scene_variant == "neon_rods":
        return {
            "background": (20, 24, 39),
            "panel_fill": (26, 30, 49),
            "panel_outline": (80, 95, 150),
            "stick": (84, 214, 230),
            "stick_shadow": (30, 74, 92),
            "label_fill": (236, 244, 255),
            "label_text": (24, 30, 48),
            "caption": (232, 240, 255),
            "tip": None,
            "palette": ((84, 214, 230), (238, 111, 196), (255, 214, 96), (140, 226, 153)),
        }
    if scene_variant == "colored_rods":
        return {
            "background": (246, 249, 252),
            "panel_fill": (255, 255, 255),
            "panel_outline": (86, 99, 122),
            "stick": (78, 137, 205),
            "stick_shadow": (225, 232, 242),
            "label_fill": (32, 40, 54),
            "label_text": (255, 255, 255),
            "caption": (28, 34, 44),
            "tip": None,
            "palette": ((64, 129, 202), (224, 107, 82), (64, 156, 118), (171, 108, 202), (222, 167, 62)),
        }
    if scene_variant == "metal_rods":
        return {
            "background": (247, 248, 250),
            "panel_fill": (252, 253, 255),
            "panel_outline": (102, 111, 124),
            "stick": (154, 163, 174),
            "stick_shadow": (218, 222, 228),
            "label_fill": (40, 45, 54),
            "label_text": (255, 255, 255),
            "caption": (30, 35, 43),
            "tip": None,
            "palette": (),
        }
    return {
        "background": (251, 247, 238),
        "panel_fill": (255, 253, 247),
        "panel_outline": (128, 103, 75),
        "stick": (213, 174, 112),
        "stick_shadow": (236, 219, 188),
        "label_fill": (67, 52, 35),
        "label_text": (255, 255, 255),
        "caption": (55, 43, 31),
        "tip": (197, 54, 48),
        "palette": (),
    }


def _stick_color(style: Mapping[str, Any], stick_id: str) -> Color:
    palette = style.get("palette") or ()
    if isinstance(palette, tuple) and palette:
        index = sum(ord(ch) for ch in str(stick_id)) % len(palette)
        return tuple(int(value) for value in palette[index])  # type: ignore[return-value]
    return tuple(int(value) for value in style["stick"])  # type: ignore[return-value]


def _draw_stick(
    draw: ImageDraw.ImageDraw,
    *,
    start: Tuple[float, float],
    end: Tuple[float, float],
    width: int,
    style: Mapping[str, Any],
    stick_id: str,
) -> None:
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    shadow = tuple(int(value) for value in style["stick_shadow"])
    color = _stick_color(style, str(stick_id))
    shadow_width = int(width) + max(2, int(width // 3))
    draw.line([(sx, sy), (ex, ey)], fill=shadow, width=shadow_width)
    radius = max(2, int(shadow_width // 2))
    draw.ellipse((sx - radius, sy - radius, sx + radius, sy + radius), fill=shadow)
    draw.ellipse((ex - radius, ey - radius, ex + radius, ey + radius), fill=shadow)
    draw.line([(sx, sy), (ex, ey)], fill=color, width=int(width))
    radius = max(2, int(width // 2))
    draw.ellipse((sx - radius, sy - radius, sx + radius, sy + radius), fill=color)
    draw.ellipse((ex - radius, ey - radius, ex + radius, ey + radius), fill=color)
    tip = style.get("tip")
    if tip is not None:
        tip_radius = max(3, int(width // 2))
        draw.ellipse((ex - tip_radius, ey - tip_radius, ex + tip_radius, ey + tip_radius), fill=tuple(int(v) for v in tip))


def _draw_label_chip(draw: ImageDraw.ImageDraw, *, bbox: Tuple[int, int, int, int], label: str, render_params: _RenderParams, style: Mapping[str, Any]) -> None:
    chip = int(max(34, render_params.option_label_font_size_px + 16))
    chip_bbox = (int(bbox[0] + 12), int(bbox[1] + 10), int(bbox[0] + 12 + chip), int(bbox[1] + 10 + chip))
    draw.rounded_rectangle(chip_bbox, radius=9, fill=tuple(style["label_fill"]), outline=(255, 255, 255), width=1)
    font = load_font(int(render_params.option_label_font_size_px), bold=True)
    draw_centered_text(
        draw,
        text=str(label),
        center=((chip_bbox[0] + chip_bbox[2]) / 2, (chip_bbox[1] + chip_bbox[3]) / 2),
        font=font,
        fill=tuple(style["label_text"]),
        stroke_fill=tuple(style["label_fill"]),
        stroke_width=0,
    )


def _draw_caption(draw: ImageDraw.ImageDraw, *, bbox: Tuple[int, int, int, int], text: str, font_size: int, style: Mapping[str, Any]) -> None:
    font = load_font(int(font_size), bold=True)
    draw_centered_text(
        draw,
        text=str(text),
        center=((bbox[0] + bbox[2]) / 2.0, bbox[1] + int(font_size * 0.9)),
        font=font,
        fill=tuple(style["caption"]),
        stroke_fill=tuple(style["panel_fill"]),
        stroke_width=1,
    )


def _number_segments(value: int) -> List[Tuple[str, Tuple[float, float], Tuple[float, float]]]:
    segments: List[Tuple[str, Tuple[float, float], Tuple[float, float]]] = []
    gap = 0.42
    for digit_index, digit in enumerate(_number_digits(int(value))):
        base_x = float(digit_index) * (1.0 + gap)
        for segment in sorted(_DIGIT_SEGMENTS[int(digit)]):
            start, end = _SEGMENT_POINTS[str(segment)]
            segments.append((f"digit{digit_index}:{segment}", (base_x + start[0], start[1]), (base_x + end[0], end[1])))
    return segments


def _draw_number(
    draw: ImageDraw.ImageDraw,
    *,
    number: int,
    bbox: Tuple[int, int, int, int],
    render_params: _RenderParams,
    style: Mapping[str, Any],
    small: bool,
) -> None:
    segments = _number_segments(int(number))
    min_x = min(min(start[0], end[0]) for _sid, start, end in segments)
    max_x = max(max(start[0], end[0]) for _sid, start, end in segments)
    min_y = min(min(start[1], end[1]) for _sid, start, end in segments)
    max_y = max(max(start[1], end[1]) for _sid, start, end in segments)
    usable_w = max(1, int((bbox[2] - bbox[0]) * (0.62 if small else 0.52)))
    usable_h = max(1, int((bbox[3] - bbox[1]) * (0.58 if small else 0.66)))
    scale = min(float(usable_w) / max(1e-6, max_x - min_x), float(usable_h) / max(1e-6, max_y - min_y))
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0 + (10 if small else 14)
    total_w = (max_x - min_x) * scale
    total_h = (max_y - min_y) * scale
    origin_x = cx - (total_w / 2.0) - (min_x * scale)
    origin_y = cy - (total_h / 2.0) - (min_y * scale)
    width = max(5, int(render_params.stick_width_px * (0.82 if small else 1.20)))
    for segment_id, start, end in segments:
        _draw_stick(
            draw,
            start=(origin_x + start[0] * scale, origin_y + start[1] * scale),
            end=(origin_x + end[0] * scale, origin_y + end[1] * scale),
            width=width,
            style=style,
            stick_id=f"number:{segment_id}",
        )


def _draw_edge_arrangement(
    draw: ImageDraw.ImageDraw,
    *,
    edges: Sequence[Edge],
    bbox: Tuple[int, int, int, int],
    grid_size: int,
    render_params: _RenderParams,
    style: Mapping[str, Any],
    small: bool,
) -> None:
    left = bbox[0] + int((bbox[2] - bbox[0]) * 0.20)
    right = bbox[2] - int((bbox[2] - bbox[0]) * 0.16)
    top = bbox[1] + int((bbox[3] - bbox[1]) * (0.24 if small else 0.22))
    bottom = bbox[3] - int((bbox[3] - bbox[1]) * 0.14)
    scale = min((right - left) / max(1, int(grid_size)), (bottom - top) / max(1, int(grid_size)))
    offset_x = (left + right - (int(grid_size) * scale)) / 2.0
    offset_y = (top + bottom - (int(grid_size) * scale)) / 2.0
    width = max(5, int(render_params.stick_width_px * (0.72 if small else 0.95)))
    for edge_index, (a, b) in enumerate(_edge_signature(edges)):
        start = (offset_x + int(a[0]) * scale, offset_y + int(a[1]) * scale)
        end = (offset_x + int(b[0]) * scale, offset_y + int(b[1]) * scale)
        _draw_stick(
            draw,
            start=start,
            end=end,
            width=width,
            style=style,
            stick_id=f"edge:{edge_index}:{a}:{b}",
        )


def _option_bboxes(render_params: _RenderParams, option_count: int, *, include_source: bool) -> List[Tuple[int, int, int, int]]:
    cols = 3
    rows = 2
    total_w = cols * render_params.option_panel_width_px + (cols - 1) * render_params.option_gap_px
    start_x = int((render_params.canvas_width - total_w) / 2)
    if include_source:
        start_y = int(render_params.margin_px + render_params.source_panel_height_px + 44)
    else:
        total_h = rows * render_params.option_panel_height_px + (rows - 1) * render_params.option_gap_px
        start_y = int((render_params.canvas_height - total_h) / 2)
    bboxes: List[Tuple[int, int, int, int]] = []
    for index in range(int(option_count)):
        row = int(index // cols)
        col = int(index % cols)
        if row >= rows:
            break
        x0 = int(start_x + col * (render_params.option_panel_width_px + render_params.option_gap_px))
        y0 = int(start_y + row * (render_params.option_panel_height_px + render_params.option_gap_px))
        bboxes.append((x0, y0, int(x0 + render_params.option_panel_width_px), int(y0 + render_params.option_panel_height_px)))
    return bboxes


def _draw_panel(draw: ImageDraw.ImageDraw, bbox: Tuple[int, int, int, int], *, render_params: _RenderParams, style: Mapping[str, Any]) -> None:
    draw_rounded_rect(
        draw,
        bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=tuple(style["panel_fill"]),
        outline=tuple(style["panel_outline"]),
        width=int(render_params.panel_border_width_px),
    )


def _render_number_scene(
    *,
    background: Image.Image,
    dataset: _NumberDataset,
    render_params: _RenderParams,
) -> _RenderedScene:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    style = _style(str(dataset.scene_variant))
    source_bbox = (
        int(render_params.margin_px),
        int(render_params.margin_px),
        int(render_params.canvas_width - render_params.margin_px),
        int(render_params.margin_px + render_params.source_panel_height_px),
    )
    _draw_panel(draw, source_bbox, render_params=render_params, style=style)
    _draw_caption(draw, bbox=source_bbox, text="Source", font_size=int(render_params.source_caption_font_size_px), style=style)
    _draw_number(draw, number=int(dataset.source_number), bbox=source_bbox, render_params=render_params, style=style, small=False)
    item_bbox_map: Dict[str, BBox] = {"source_panel": tuple(float(value) for value in source_bbox)}
    entities: List[Dict[str, Any]] = [
        {
            "id": "source_panel",
            "type": "matchstick_number_source",
            "bbox_px": [int(value) for value in source_bbox],
            "number": _number_text(int(dataset.source_number)),
        }
    ]
    for index, option in enumerate(dataset.option_specs):
        bbox = _option_bboxes(render_params, int(dataset.option_count), include_source=True)[int(index)]
        option_id = f"option_{option.label}"
        _draw_panel(draw, bbox, render_params=render_params, style=style)
        _draw_label_chip(draw, bbox=bbox, label=str(option.label), render_params=render_params, style=style)
        _draw_number(draw, number=int(option.value), bbox=bbox, render_params=render_params, style=style, small=True)
        item_bbox_map[str(option_id)] = tuple(float(value) for value in bbox)
        entities.append(
            {
                "id": str(option_id),
                "type": "matchstick_number_option",
                "label": str(option.label),
                "bbox_px": [int(value) for value in bbox],
                "number": _number_text(int(option.value)),
                "is_correct": bool(option.is_correct),
            }
        )
    scene_bbox = (
        float(render_params.margin_px),
        float(render_params.margin_px),
        float(render_params.canvas_width - render_params.margin_px),
        float(render_params.canvas_height - render_params.margin_px),
    )
    return _RenderedScene(image=image, scene_bbox_px=scene_bbox, item_bbox_map=item_bbox_map, entities=tuple(entities))


def _render_shape_scene(
    *,
    background: Image.Image,
    dataset: _ShapeDataset,
    render_params: _RenderParams,
) -> _RenderedScene:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    style = _style(str(dataset.scene_variant))
    item_bbox_map: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    for index, option in enumerate(dataset.option_specs):
        bbox = _option_bboxes(render_params, int(dataset.option_count), include_source=False)[int(index)]
        option_id = f"option_{option.label}"
        _draw_panel(draw, bbox, render_params=render_params, style=style)
        _draw_label_chip(draw, bbox=bbox, label=str(option.label), render_params=render_params, style=style)
        _draw_edge_arrangement(
            draw,
            edges=option.value,
            bbox=bbox,
            grid_size=int(dataset.grid_size),
            render_params=render_params,
            style=style,
            small=True,
        )
        item_bbox_map[str(option_id)] = tuple(float(value) for value in bbox)
        entities.append(
            {
                "id": str(option_id),
                "type": "matchstick_endpoint_option",
                "label": str(option.label),
                "bbox_px": [int(value) for value in bbox],
                "edges": _edge_trace(option.value),
                "loose_endpoint_count": int(option.metric_value or 0),
                "is_correct": bool(option.is_correct),
            }
        )
    scene_bbox = (
        float(render_params.margin_px),
        float(render_params.margin_px),
        float(render_params.canvas_width - render_params.margin_px),
        float(render_params.canvas_height - render_params.margin_px),
    )
    return _RenderedScene(image=image, scene_bbox_px=scene_bbox, item_bbox_map=item_bbox_map, entities=tuple(entities))


def _build_prompt(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
    task_key: str,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    required_keys = (
        "bundle_id",
        "scene_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        f"object_description_{scene_variant}",
        f"answer_hint_{query_id}",
        f"evidence_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    )
    prompt_values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {task_id}")
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_values[f"answer_hint_{query_id}"]),
        "evidence_hint": str(prompt_values[f"evidence_hint_{query_id}"]),
        "json_example": str(prompt_values[f"json_example_{query_id}"]),
        "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
    }
    prompt_selection = render_task_prompt_variants(
        domain="puzzles",
        task_group="logic",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(task_key),
        query_key=str(query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "bundle_id": str(prompt_values["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
    }


class _PuzzlesLogicMatchstickBaseTask:
    """Shared output assembly for matchstick logic tasks."""

    domain = "puzzles"
    task_group = "logic"
    default_dataset_enabled = True
    task_key: str

    def _common_trace(
        self,
        *,
        query_id: str,
        scene_variant: str,
        scene_variant_probabilities: Mapping[str, float],
        prompt_meta: Mapping[str, Any],
        rendered_scene: _RenderedScene,
        render_params: _RenderParams,
        background_meta: Mapping[str, Any],
        post_noise_meta: Mapping[str, Any],
        evidence_bboxes: Sequence[Sequence[float]],
        answer_value: str,
        option_count: int,
    ) -> Dict[str, Any]:
        params = {
            "query_id": "default",
            "query_id_probabilities": {"default": 1.0},
            "query_id": str(query_id),
            "query_id_probabilities": {str(query_id): 1.0},
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": {str(key): float(value) for key, value in scene_variant_probabilities.items()},
            "option_count": int(option_count),
            "answer_label": str(answer_value),
        }
        return {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "answer_label": str(answer_value),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "stick_width_px": int(render_params.stick_width_px),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "item_bboxes_px": {
                    str(key): [round(float(v), 3) for v in value]
                    for key, value in rendered_scene.item_bbox_map.items()
                },
                "evidence_source": "item_bboxes_px",
            },
            "execution_trace": {
                **dict(params),
                "question_format": str(query_id),
                "answer_value": str(answer_value),
                "supporting_item_ids": [f"option_{answer_value}"],
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "value": list(evidence_bboxes),
            },
        }


@register_task
class PuzzlesLogicMatchstickNumberTransformLabelTask(_PuzzlesLogicMatchstickBaseTask):
    """Select the one number reachable by adding or removing one matchstick."""

    task_id = NUMBER_TASK_ID
    task_key = "matchstick_number_transform_query"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(str(self.task_id))
        query_id, query_probabilities = _resolve_axis_variant(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
            supported_variants=NUMBER_QUERY_IDS,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            axis_namespace="query_id",
        )
        scene_variant, scene_variant_probabilities = _resolve_axis_variant(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
            supported_variants=SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )
        last_error: Exception | None = None
        dataset: _NumberDataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_number_dataset(
                    query_id=str(query_id),
                    scene_variant=str(scene_variant),
                    params=params,
                    gen_defaults=gen_defaults,
                    task_id=str(self.task_id),
                    instance_seed=int(instance_seed) + int(attempt_index),
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate matchstick number-transform puzzle") from last_error
        render_params = _resolve_render_params(params, render_defaults)
        scene_style, _scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.matchstick_number_background",
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = _render_number_scene(background=background, dataset=dataset, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(rendered_scene.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(
            task_id=str(self.task_id),
            query_id=str(query_id),
            scene_variant=str(dataset.scene_variant),
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
            task_key=str(self.task_key),
        )
        evidence_projection = projected_puzzle_bbox_evidence(rendered_scene.item_bbox_map, [f"option_{dataset.answer_label}"])
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_gt = TypedValue(type="option_letter", value=str(dataset.answer_label))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        trace_payload = self._common_trace(
            query_id=str(query_id),
            scene_variant=str(dataset.scene_variant),
            scene_variant_probabilities=scene_variant_probabilities,
            prompt_meta=prompt_meta,
            rendered_scene=rendered_scene,
            render_params=render_params,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            evidence_bboxes=evidence_bboxes,
            answer_value=str(dataset.answer_label),
            option_count=int(dataset.option_count),
        )
        trace_payload["query_spec"]["params"]["query_id_probabilities"] = {str(key): float(value) for key, value in query_probabilities.items()}
        trace_payload["execution_trace"].update(
            {
                "query_id_probabilities": {str(key): float(value) for key, value in query_probabilities.items()},
                "source_number": _number_text(int(dataset.source_number)),
                "answer_number": _number_text(int(dataset.answer_number)),
                "changed_digit_index": int(dataset.changed_digit_index),
                "removed_segment_keys": list(dataset.removed_segment_keys),
                "added_segment_keys": list(dataset.added_segment_keys),
                "option_specs": [
                    {
                        "option_label": str(option.label),
                        "number": _number_text(int(option.value)),
                        "is_reachable": bool(_number_transition_allowed(int(dataset.source_number), int(option.value), str(query_id))),
                        "is_correct": bool(option.is_correct),
                    }
                    for option in dataset.option_specs
                ],
            }
        )
        visual_scan = clamp_unit_interval(0.35 + (0.08 * int(dataset.option_count)) + (0.05 * len(dataset.removed_segment_keys + dataset.added_segment_keys)))
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(_QUERY_LOAD[str(query_id)]),
                "scene_variant_load": float(_SCENE_LOAD[str(dataset.scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class PuzzlesLogicMatchstickLooseEndpointExtremumLabelTask(_PuzzlesLogicMatchstickBaseTask):
    """Select the arrangement with the most or fewest loose endpoints."""

    task_id = ENDPOINT_TASK_ID
    task_key = "matchstick_loose_endpoint_extremum_query"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(str(self.task_id))
        query_id, query_probabilities = _resolve_axis_variant(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
            supported_variants=ENDPOINT_QUERY_IDS,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            axis_namespace="query_id",
        )
        scene_variant, scene_variant_probabilities = _resolve_axis_variant(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
            supported_variants=SCENE_VARIANTS,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            balance_flag_key="balanced_scene_variant_sampling",
            axis_namespace="scene_variant",
        )
        last_error: Exception | None = None
        dataset: _ShapeDataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_shape_dataset(
                    query_id=str(query_id),
                    scene_variant=str(scene_variant),
                    params=params,
                    gen_defaults=gen_defaults,
                    task_id=str(self.task_id),
                    instance_seed=int(instance_seed) + int(attempt_index),
                )
                break
            except RuntimeError as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate matchstick loose-endpoint extremum puzzle") from last_error
        render_params = _resolve_render_params(params, render_defaults)
        scene_style, _scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.matchstick_endpoint_background",
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = _render_shape_scene(background=background, dataset=dataset, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(rendered_scene.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(
            task_id=str(self.task_id),
            query_id=str(query_id),
            scene_variant=str(dataset.scene_variant),
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
            task_key=str(self.task_key),
        )
        evidence_projection = projected_puzzle_bbox_evidence(rendered_scene.item_bbox_map, [f"option_{dataset.answer_label}"])
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_gt = TypedValue(type="option_letter", value=str(dataset.answer_label))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        trace_payload = self._common_trace(
            query_id=str(query_id),
            scene_variant=str(dataset.scene_variant),
            scene_variant_probabilities=scene_variant_probabilities,
            prompt_meta=prompt_meta,
            rendered_scene=rendered_scene,
            render_params=render_params,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            evidence_bboxes=evidence_bboxes,
            answer_value=str(dataset.answer_label),
            option_count=int(dataset.option_count),
        )
        trace_payload["query_spec"]["params"].update(
            {
                "query_id_probabilities": {str(key): float(value) for key, value in query_probabilities.items()},
                "grid_size": int(dataset.grid_size),
            }
        )
        trace_payload["execution_trace"].update(
            {
                "query_id_probabilities": {str(key): float(value) for key, value in query_probabilities.items()},
                "grid_size": int(dataset.grid_size),
                "option_specs": [
                    {
                        "option_label": str(option.label),
                        "edges": _edge_trace(option.value),
                        "loose_endpoint_count": int(option.metric_value or 0),
                        "is_correct": bool(option.is_correct),
                    }
                    for option in dataset.option_specs
                ],
            }
        )
        visual_scan = clamp_unit_interval(
            0.45 * normalize_int_with_bounds(
                sum(len(option.value) for option in dataset.option_specs) / max(1, int(dataset.option_count)),
                [8, 15],
            )
            + 0.35 * normalize_int_with_bounds(int(dataset.option_count), [4, 6])
            + 0.20 * normalize_int_with_bounds(int(dataset.grid_size * dataset.grid_size), [4, 16])
        )
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": float(_QUERY_LOAD[str(query_id)]),
                "scene_variant_load": float(_SCENE_LOAD[str(dataset.scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )


__all__ = [
    "PuzzlesLogicMatchstickNumberTransformLabelTask",
    "PuzzlesLogicMatchstickLooseEndpointExtremumLabelTask",
]
