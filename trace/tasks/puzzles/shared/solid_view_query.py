"""Shared solid-view cube-stack query used by cube-structure puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_centered_text, draw_rounded_rect
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ...geometry.shared.graph_paper import resolve_square_canvas_size
from ...geometry.shared.render_variation import sample_int_render_param
from ...geometry.shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from .complexity import (
    build_puzzle_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
)
from .solid_view_scene import (
    FRONT_VIEW_QUERY,
    RIGHT_VIEW_QUERY,
    SolidRenderStyle,
    TOP_VIEW_QUERY,
    CubeStack,
    ViewCell,
    build_solid_render_style,
    draw_cube_stack_panel,
    draw_query_view_panel,
    projected_view_cells,
    sample_connected_cube_stack,
    view_grid_dimensions,
    view_title_for_query,
)
from .scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from .visual_defaults import load_puzzle_background_defaults, load_puzzle_noise_defaults


TASK_ID = "puzzles_spatial_cube_structure_internal"

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("cube_stack",)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    TOP_VIEW_QUERY,
    FRONT_VIEW_QUERY,
    RIGHT_VIEW_QUERY,
)
SUPPORTED_PUBLIC_QUERY_IDS: Tuple[str, ...] = ("visible_cube_count",)
PROJECTION_MATCH_QUERY = "projection_match_label"
PROJECTION_CONSISTENCY_QUERY = "projection_consistency_label"
PROJECTION_MATCH_OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
PROJECTION_CONSISTENCY_QUERY_IDS: Tuple[str, ...] = (
    "inconsistent_projection_label",
    "candidate_stack_from_views_label",
)
_VIEW_DIRECTION_BY_QUERY_ID = {
    TOP_VIEW_QUERY: "top",
    FRONT_VIEW_QUERY: "front",
    RIGHT_VIEW_QUERY: "right",
}
_QUERY_ID_BY_VIEW_DIRECTION = {
    "top": TOP_VIEW_QUERY,
    "front": FRONT_VIEW_QUERY,
    "right": RIGHT_VIEW_QUERY,
}
_SUPPORTED_VIEW_DIRECTIONS: Tuple[str, ...] = ("top", "front", "right")
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "cube_stack": SUPPORTED_QUERY_IDS,
}

POST_IMAGE_BACKGROUND_DEFAULTS = load_puzzle_background_defaults(task_group="spatial")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.0)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for puzzle solid-view scenes."""

    canvas_size_min: int = 720
    canvas_size_max: int = 800
    scene_supersample_scale: int = 2
    line_width: int = 3
    line_width_min: int = 2
    line_width_max: int = 4
    panel_gap_px: int = 22
    outer_margin_px: int = 28
    stack_panel_ratio: float = 0.58
    panel_title_font_size_px: int = 20
    panel_title_font_size_min: int = 18
    panel_title_font_size_max: int = 24
    footprint_width_min: int = 2
    footprint_width_max: int = 4
    footprint_depth_min: int = 2
    footprint_depth_max: int = 4
    max_height: int = 3
    total_cubes_min: int = 4
    total_cubes_max: int = 9
    target_count_support: Tuple[int, ...] = (3, 4, 5, 6, 7)
    min_distinct_view_counts: int = 2
    allow_full_query_projection: bool = False


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved scene/query axes and answer-count support for one instance."""

    scene_variant: str
    query_id: str
    public_query_id: str
    view_direction: str
    target_count: int
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    view_direction_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedSolidScene:
    """Rendered solid-view scene payload with annotation + trace artifacts."""

    stack: CubeStack
    answer_value: int
    annotation_bboxes: List[List[float]]
    query_panel_bbox: List[float]
    stack_panel_bbox: List[float]
    query_grid_bbox: List[float]
    query_grid_dims: Tuple[int, int]
    projection_cells: List[List[int]]
    visible_counts_by_query: Dict[str, int]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = {
    "visual_scan": 0.24,
    "projection_reasoning": 0.46,
    "ambiguity": 0.20,
    "output_burden": 0.10,
}
_TARGET_COUNT_BALANCE_SALT = 48518


def _target_count_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve supported visible-cell counts for solid-view queries."""

    raw_support = params.get(
        "target_count_support",
        group_default(_GEN_DEFAULTS, "target_count_support", _DEFAULTS.target_count_support),
    )
    support: List[int] = []
    for value in raw_support:
        normalized = int(value)
        if 1 <= int(normalized) <= 9 and int(normalized) not in support:
            support.append(int(normalized))
    if not support:
        raise ValueError("target_count_support must contain at least one value in 1..9")
    return tuple(sorted(support))


def _resolve_target_count(
    rng,
    *,
    instance_seed: int,
    query_id: str,
    params: Mapping[str, Any],
) -> Tuple[int, Dict[str, float]]:
    """Resolve the answer-count support with deterministic balanced defaults."""

    support = _target_count_support(params)
    explicit = params.get("target_count")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"unsupported target_count: {selected}")
        return int(selected), uniform_probability_map(support, selected=int(selected))

    raw_weights = params.get("target_count_weights", {str(value): 1.0 for value in support})
    if not isinstance(raw_weights, Mapping):
        raise ValueError("target_count_weights must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if int(key) in set(support)
    }
    probabilities = normalize_positive_weights(weights, default_keys=[str(value) for value in support])
    selected = int(weighted_choice(rng, probabilities, sort_keys=True))

    balanced_enabled = bool(params.get("balanced_sampling", group_default(_GEN_DEFAULTS, "balanced_sampling", True)))
    overridden = any(params.get(key) is not None for key in ("target_count", "target_count_weights"))
    if bool(balanced_enabled) and (not overridden):
        ordered_support = [int(value) for value in support]
        selection_index = abs(int(hash64(int(instance_seed), f"{TASK_ID}.target_count.{query_id}", _TARGET_COUNT_BALANCE_SALT)))
        selected = int(ordered_support[int(selection_index) % len(ordered_support)])
    return int(selected), {
        str(key): float(value)
        for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))
    }


def _resolve_public_query_id(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the public solid-view query family, accepting old view names as aliases."""

    explicit_query = params.get("query_id")
    if explicit_query is not None and str(explicit_query) in _VIEW_DIRECTION_BY_QUERY_ID:
        return "visible_cube_count", {"visible_cube_count": 1.0}
    if explicit_query is not None and str(explicit_query) == "view_visible_count":
        return "visible_cube_count", {"visible_cube_count": 1.0}
    if explicit_query is not None and str(explicit_query) in SUPPORTED_PUBLIC_QUERY_IDS:
        return str(explicit_query), {str(explicit_query): 1.0}

    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PUBLIC_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_PUBLIC_QUERY_IDS,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_ID}.query_id",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_view_direction(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the orthographic view direction to query."""

    explicit_query = params.get("query_id")
    if explicit_query is not None and str(explicit_query) in _VIEW_DIRECTION_BY_QUERY_ID:
        selected = str(_VIEW_DIRECTION_BY_QUERY_ID[str(explicit_query)])
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_VIEW_DIRECTIONS}

    explicit_direction = params.get("view_direction")
    if explicit_direction is not None:
        selected = str(explicit_direction).strip().lower()
        if selected not in _SUPPORTED_VIEW_DIRECTIONS:
            raise ValueError(f"unsupported view_direction: {explicit_direction}")
        return selected, {key: (1.0 if key == selected else 0.0) for key in _SUPPORTED_VIEW_DIRECTIONS}

    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_SUPPORTED_VIEW_DIRECTIONS,
        explicit_key="view_direction",
        weights_key="view_direction_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=_SUPPORTED_VIEW_DIRECTIONS,
        balance_flag_key="balanced_view_direction_sampling",
        explicit_key="view_direction",
        weights_key="view_direction_weights",
        sampling_namespace=f"{TASK_ID}.view_direction",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _view_direction_description(view_direction: str) -> str:
    """Return prompt-facing text for one solid-view direction."""

    if str(view_direction) == "top":
        return "top view, looking directly from above"
    if str(view_direction) == "front":
        return "front view, looking straight at the left vertical face of the drawn stack"
    return "right view, looking straight at the right vertical face of the drawn stack"


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve chart-style scene/query axes plus balanced target-count support."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    public_query_id, query_probs = _resolve_public_query_id(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
    )
    view_direction, view_direction_probs = _resolve_view_direction(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
    )
    query_id = str(_QUERY_ID_BY_VIEW_DIRECTION[str(view_direction)])
    scene_variant, scene_probs = resolve_variant(
        axis_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    scene_variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(scene_variant),
        variant_probabilities=scene_probs,
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        balance_flag_key="balanced_scene_variant_sampling",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        sampling_namespace=f"{TASK_ID}.scene_variant",
    )
    target_count, target_count_probs = _resolve_target_count(
        axis_rng,
        instance_seed=int(instance_seed),
        query_id=str(query_id),
        params=params,
    )
    return _ResolvedQuery(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        public_query_id=str(public_query_id),
        view_direction=str(view_direction),
        target_count=int(target_count),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(query_probs),
        view_direction_probabilities=dict(view_direction_probs),
        target_count_probabilities=dict(target_count_probs),
    )


def _resolve_projection_match_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve solid-view axes for the projection-option label task."""

    axis_params = dict(params)
    axis_params.pop("query_id", None)
    axis_params.pop("query_id", None)
    base = _resolve_axes(int(instance_seed), params=axis_params)
    return _ResolvedQuery(
        scene_variant=str(base.scene_variant),
        query_id=str(base.query_id),
        public_query_id=PROJECTION_MATCH_QUERY,
        view_direction=str(base.view_direction),
        target_count=int(base.target_count),
        scene_variant_probabilities=dict(base.scene_variant_probabilities),
        query_id_probabilities={PROJECTION_MATCH_QUERY: 1.0},
        view_direction_probabilities=dict(base.view_direction_probabilities),
        target_count_probabilities=dict(base.target_count_probabilities),
    )


def _resolve_projection_consistency_query(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve the internal consistency question family for one public task."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.projection_consistency.axes")
    selected, probabilities = resolve_variant(
        axis_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=PROJECTION_CONSISTENCY_QUERY_IDS,
        explicit_key="consistency_query",
        weights_key="consistency_query_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=PROJECTION_CONSISTENCY_QUERY_IDS,
        balance_flag_key="balanced_consistency_query_sampling",
        explicit_key="consistency_query",
        weights_key="consistency_query_weights",
        sampling_namespace=f"{TASK_ID}.projection_consistency.query",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _sample_stack_matching_target(
    rng,
    *,
    query_id: str,
    target_count: int,
    params: Mapping[str, Any],
) -> Tuple[CubeStack, Dict[str, int]]:
    """Sample one non-degenerate cube stack whose queried view matches the target count."""

    width_min = int(params.get("footprint_width_min", group_default(_GEN_DEFAULTS, "footprint_width_min", _DEFAULTS.footprint_width_min)))
    width_max = int(params.get("footprint_width_max", group_default(_GEN_DEFAULTS, "footprint_width_max", _DEFAULTS.footprint_width_max)))
    depth_min = int(params.get("footprint_depth_min", group_default(_GEN_DEFAULTS, "footprint_depth_min", _DEFAULTS.footprint_depth_min)))
    depth_max = int(params.get("footprint_depth_max", group_default(_GEN_DEFAULTS, "footprint_depth_max", _DEFAULTS.footprint_depth_max)))
    total_cubes_min = max(
        int(target_count),
        int(params.get("total_cubes_min", group_default(_GEN_DEFAULTS, "total_cubes_min", _DEFAULTS.total_cubes_min))),
    )
    total_cubes_max = max(
        int(total_cubes_min),
        int(params.get("total_cubes_max", group_default(_GEN_DEFAULTS, "total_cubes_max", _DEFAULTS.total_cubes_max))),
    )
    max_height = int(params.get("max_height", group_default(_GEN_DEFAULTS, "max_height", _DEFAULTS.max_height)))
    min_distinct_view_counts = int(
        params.get(
            "min_distinct_view_counts",
            group_default(_GEN_DEFAULTS, "min_distinct_view_counts", _DEFAULTS.min_distinct_view_counts),
        )
    )
    allow_full_query_projection = bool(
        params.get(
            "allow_full_query_projection",
            group_default(_GEN_DEFAULTS, "allow_full_query_projection", _DEFAULTS.allow_full_query_projection),
        )
    )

    for _ in range(512):
        stack = sample_connected_cube_stack(
            rng,
            width_min=int(width_min),
            width_max=int(width_max),
            depth_min=int(depth_min),
            depth_max=int(depth_max),
            total_cubes_min=int(total_cubes_min),
            total_cubes_max=int(total_cubes_max),
            max_height=int(max_height),
        )
        if int(stack.max_height) < 2 or len(stack.heights) < 2:
            continue
        visible_counts_by_query = {
            TOP_VIEW_QUERY: len(projected_view_cells(stack, query_id=TOP_VIEW_QUERY)),
            FRONT_VIEW_QUERY: len(projected_view_cells(stack, query_id=FRONT_VIEW_QUERY)),
            RIGHT_VIEW_QUERY: len(projected_view_cells(stack, query_id=RIGHT_VIEW_QUERY)),
        }
        if int(visible_counts_by_query[str(query_id)]) != int(target_count):
            continue
        query_grid_dims = view_grid_dimensions(stack, query_id=str(query_id))
        if (not allow_full_query_projection) and (
            int(visible_counts_by_query[str(query_id)]) >= int(query_grid_dims[0]) * int(query_grid_dims[1])
        ):
            continue
        if len(set(int(value) for value in visible_counts_by_query.values())) < int(min_distinct_view_counts):
            continue
        return stack, {str(key): int(value) for key, value in visible_counts_by_query.items()}
    raise RuntimeError("failed to sample a cube stack matching the requested solid-view target count")


def _sample_consistency_stack(rng, *, params: Mapping[str, Any]) -> Tuple[CubeStack, Dict[str, int]]:
    """Sample a stack suitable for projection consistency questions."""

    width_min = int(params.get("footprint_width_min", group_default(_GEN_DEFAULTS, "footprint_width_min", _DEFAULTS.footprint_width_min)))
    width_max = int(params.get("footprint_width_max", group_default(_GEN_DEFAULTS, "footprint_width_max", _DEFAULTS.footprint_width_max)))
    depth_min = int(params.get("footprint_depth_min", group_default(_GEN_DEFAULTS, "footprint_depth_min", _DEFAULTS.footprint_depth_min)))
    depth_max = int(params.get("footprint_depth_max", group_default(_GEN_DEFAULTS, "footprint_depth_max", _DEFAULTS.footprint_depth_max)))
    total_cubes_min = int(params.get("total_cubes_min", group_default(_GEN_DEFAULTS, "total_cubes_min", _DEFAULTS.total_cubes_min)))
    total_cubes_max = int(params.get("total_cubes_max", group_default(_GEN_DEFAULTS, "total_cubes_max", _DEFAULTS.total_cubes_max)))
    max_height = int(params.get("max_height", group_default(_GEN_DEFAULTS, "max_height", _DEFAULTS.max_height)))
    min_distinct_view_counts = int(
        params.get(
            "min_distinct_view_counts",
            group_default(_GEN_DEFAULTS, "min_distinct_view_counts", _DEFAULTS.min_distinct_view_counts),
        )
    )

    for _ in range(512):
        stack = sample_connected_cube_stack(
            rng,
            width_min=int(width_min),
            width_max=int(width_max),
            depth_min=int(depth_min),
            depth_max=int(depth_max),
            total_cubes_min=int(total_cubes_min),
            total_cubes_max=int(total_cubes_max),
            max_height=int(max_height),
        )
        if int(stack.max_height) < 2 or len(stack.heights) < 3:
            continue
        visible_counts_by_query = {
            TOP_VIEW_QUERY: len(projected_view_cells(stack, query_id=TOP_VIEW_QUERY)),
            FRONT_VIEW_QUERY: len(projected_view_cells(stack, query_id=FRONT_VIEW_QUERY)),
            RIGHT_VIEW_QUERY: len(projected_view_cells(stack, query_id=RIGHT_VIEW_QUERY)),
        }
        if len(set(int(value) for value in visible_counts_by_query.values())) < int(min_distinct_view_counts):
            continue
        try:
            for query_id in SUPPORTED_QUERY_IDS:
                _projection_distractor_sets(
                    rng,
                    correct_cells=projected_view_cells(stack, query_id=str(query_id)),
                    grid_dims=view_grid_dimensions(stack, query_id=str(query_id)),
                    option_count=2,
                )
        except RuntimeError:
            continue
        return stack, {str(key): int(value) for key, value in visible_counts_by_query.items()}
    raise RuntimeError("failed to sample a cube stack suitable for projection consistency")


def _stack_projection_signature(stack: CubeStack) -> Tuple[Tuple[str, Tuple[int, int], Tuple[ViewCell, ...]], ...]:
    """Return a canonical top/front/right projection signature for one stack."""

    return tuple(
        (
            str(query_id),
            tuple(int(value) for value in view_grid_dimensions(stack, query_id=str(query_id))),
            _projection_cell_key(projected_view_cells(stack, query_id=str(query_id))),
        )
        for query_id in SUPPORTED_QUERY_IDS
    )


def _sample_projection_distractor_stacks(
    rng,
    *,
    correct_stack: CubeStack,
    option_count: int,
    params: Mapping[str, Any],
) -> List[CubeStack]:
    """Sample candidate stacks whose complete projection signatures differ from the reference."""

    correct_signature = _stack_projection_signature(correct_stack)
    seen = {correct_signature}
    distractors: List[CubeStack] = []
    for _ in range(1500):
        candidate, _visible_counts = _sample_consistency_stack(rng, params=params)
        signature = _stack_projection_signature(candidate)
        if signature in seen:
            continue
        seen.add(signature)
        distractors.append(candidate)
        if len(distractors) >= max(0, int(option_count) - 1):
            return list(distractors)
    raise RuntimeError("failed to sample enough unique projection-consistency distractor stacks")


def _resolve_canvas_size(rng, *, params: Mapping[str, Any]) -> int:
    """Resolve one square canvas size for the solid-view scene."""

    return int(
        resolve_square_canvas_size(
            rng,
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_min=_DEFAULTS.canvas_size_min,
            fallback_max=_DEFAULTS.canvas_size_max,
        )
    )


def _panel_layout(
    *,
    canvas_size: int,
    scene_scale: int,
    params: Mapping[str, Any],
) -> Tuple[Tuple[float, float, float, float], Tuple[float, float, float, float]]:
    """Resolve left stack-panel and right query-panel bounding boxes."""

    outer_margin_px = float(params.get("outer_margin_px", group_default(_RENDER_DEFAULTS, "outer_margin_px", _DEFAULTS.outer_margin_px)))
    panel_gap_px = float(params.get("panel_gap_px", group_default(_RENDER_DEFAULTS, "panel_gap_px", _DEFAULTS.panel_gap_px)))
    stack_ratio = float(params.get("stack_panel_ratio", group_default(_RENDER_DEFAULTS, "stack_panel_ratio", _DEFAULTS.stack_panel_ratio)))

    full_size = float(canvas_size * scene_scale)
    margin = float(outer_margin_px * scene_scale)
    gap = float(panel_gap_px * scene_scale)
    usable_width = max(160.0, float(full_size - (2.0 * margin) - gap))
    usable_height = max(160.0, float(full_size - (2.0 * margin)))
    stack_width = float(round(usable_width * stack_ratio))
    query_width = float(usable_width - stack_width)
    left = float(margin)
    top = float(margin)
    stack_bbox = (
        float(left),
        float(top),
        float(left + stack_width),
        float(top + usable_height),
    )
    query_left = float(stack_bbox[2] + gap)
    query_bbox = (
        float(query_left),
        float(top),
        float(query_left + query_width),
        float(top + usable_height),
    )
    return stack_bbox, query_bbox


def _sample_panel_title_font_size(
    rng,
    *,
    params: Mapping[str, Any],
) -> int:
    """Resolve one panel-title font size in final-image pixels."""

    explicit = params.get("panel_title_font_size_px")
    if explicit is not None:
        return max(10, int(explicit))
    minimum = int(group_default(_RENDER_DEFAULTS, "panel_title_font_size_min", _DEFAULTS.panel_title_font_size_min))
    maximum = int(group_default(_RENDER_DEFAULTS, "panel_title_font_size_max", _DEFAULTS.panel_title_font_size_max))
    return max(10, int(rng.randint(int(minimum), int(maximum))))


def _sample_voxel_scale_percent(rng, *, params: Mapping[str, Any]) -> int:
    """Resolve a render-only voxel-scale jitter percentage."""

    return int(
        sample_int_render_param(
            rng,
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            key="voxel_scale_percent",
            fallback=100,
            minimum_value=50,
        )
    )


def _voxel_scale_from_percent(value: int) -> float:
    """Convert a jitter percent to the bounded scale consumed by stack panels."""

    return float(max(0.50, min(1.00, float(value) / 100.0)))


def _render_scene(
    rng,
    *,
    query: _ResolvedQuery,
    canvas_size: int,
    scene_scale: int,
    line_width: int,
    panel_title_font_size_px: int,
    params: Mapping[str, Any],
    background_meta: Mapping[str, Any],
    shape_style,
    draw: ImageDraw.ImageDraw,
) -> _RenderedSolidScene:
    """Sample one stack matching the target count and render both panels."""

    stack, visible_counts_by_query = _sample_stack_matching_target(
        rng,
        query_id=str(query.query_id),
        target_count=int(query.target_count),
        params=params,
    )
    style = build_solid_render_style(shape_style=shape_style, background_meta=background_meta)
    stack_voxel_scale_percent = _sample_voxel_scale_percent(rng, params=params)
    stack_panel_bbox, query_panel_bbox = _panel_layout(
        canvas_size=int(canvas_size),
        scene_scale=int(scene_scale),
        params=params,
    )
    stack_panel_meta = draw_cube_stack_panel(
        draw,
        panel_bbox=stack_panel_bbox,
        stack=stack,
        scene_scale=int(scene_scale),
        line_width=int(line_width) * int(scene_scale),
        title_text="Cube stack",
        title_font_size_px=int(panel_title_font_size_px) * int(scene_scale),
        style=style,
        voxel_scale=_voxel_scale_from_percent(int(stack_voxel_scale_percent)),
    )

    projection_cells = projected_view_cells(stack, query_id=str(query.query_id))
    query_panel_meta = draw_query_view_panel(
        draw,
        panel_bbox=query_panel_bbox,
        grid_dims=view_grid_dimensions(stack, query_id=str(query.query_id)),
        occupied_cells=projection_cells,
        scene_scale=int(scene_scale),
        line_width=int(max(1, line_width - 1)) * int(scene_scale),
        title_text=view_title_for_query(str(query.query_id)),
        title_font_size_px=int(panel_title_font_size_px) * int(scene_scale),
        style=style,
    )

    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": f"cube_{index:02d}",
            "type": "cube",
            "cell": [int(cell_x), int(cell_y), int(cell_z)],
        }
        for index, (cell_x, cell_y, cell_z) in enumerate(
            sorted(
                [
                    (x_value, y_value, z_value)
                    for (x_value, y_value), height in stack.heights.items()
                    for z_value in range(int(height))
                ],
                key=lambda item: (int(item[2]), int(item[1]), int(item[0])),
            )
        )
    ]
    scene_entities.append(
        {
            "entity_id": "query_panel",
            "type": "projection_panel",
            "bbox": list(query_panel_meta["panel_bbox"]),
            "query_id": str(query.query_id),
            "grid_dimensions": [int(view_grid_dimensions(stack, query_id=str(query.query_id))[0]), int(view_grid_dimensions(stack, query_id=str(query.query_id))[1])],
        }
    )

    annotation_bboxes = [list(bbox) for bbox in query_panel_meta["occupied_bboxes"]]
    projection_cells_out = [[int(col), int(row)] for col, row in projection_cells]
    render_map = {
        "image_id": "img0",
        "stack_panel_bbox": list(stack_panel_meta["panel_bbox"]),
        "query_panel_bbox": list(query_panel_meta["panel_bbox"]),
        "query_grid_bbox": list(query_panel_meta["grid_bbox"]),
        "query_grid_dimensions": list(view_grid_dimensions(stack, query_id=str(query.query_id))),
        "query_view_title": str(view_title_for_query(str(query.query_id))),
        "stack_voxel_scale_percent": int(stack_voxel_scale_percent),
        "projection_cells": list(projection_cells_out),
        "projection_cell_bboxes": list(annotation_bboxes),
        "stack_width": int(stack.width),
        "stack_depth": int(stack.depth),
        "stack_heights": [
            {"x": int(x_value), "y": int(y_value), "height": int(height)}
            for (x_value, y_value), height in sorted(stack.heights.items())
        ],
    }
    return _RenderedSolidScene(
        stack=stack,
        answer_value=int(len(annotation_bboxes)),
        annotation_bboxes=list(annotation_bboxes),
        query_panel_bbox=list(query_panel_meta["panel_bbox"]),
        stack_panel_bbox=list(stack_panel_meta["panel_bbox"]),
        query_grid_bbox=list(query_panel_meta["grid_bbox"]),
        query_grid_dims=tuple(int(value) for value in view_grid_dimensions(stack, query_id=str(query.query_id))),
        projection_cells=list(projection_cells_out),
        visible_counts_by_query={str(key): int(value) for key, value in visible_counts_by_query.items()},
        scene_entities=scene_entities,
        render_map=render_map,
    )


def _solid_view_reasoning_score(*, query_id: str, max_height: int) -> float:
    """Return normalized reasoning load for one solid-view query."""

    normalized_query = str(query_id).strip().lower()
    base_by_query = {
        TOP_VIEW_QUERY: 0.34,
        FRONT_VIEW_QUERY: 0.56,
        RIGHT_VIEW_QUERY: 0.58,
    }
    if normalized_query not in base_by_query:
        raise ValueError(f"unsupported puzzle solid-view query_id: {query_id}")
    height_bonus = normalize_int_with_bounds(int(max_height), [2, 3]) * 0.12
    return clamp_unit_interval(float(base_by_query[normalized_query]) + float(height_bonus))


def _build_solid_view_complexity(
    *,
    query_id: str,
    cube_count: int,
    max_height: int,
    target_count: int,
    annotation_count: int,
):
    """Build one normalized complexity payload for cube-stack view counting."""

    visual_scan = clamp_unit_interval(
        (0.65 * normalize_int_with_bounds(int(cube_count), [4, 8]))
        + (0.35 * normalize_int_with_bounds(int(max_height), [2, 3]))
    )
    ambiguity = clamp_unit_interval(
        (0.50 * normalize_int_with_bounds(int(target_count), [2, 7]))
        + (0.30 * normalize_int_with_bounds(int(cube_count - target_count), [0, 5]))
        + (0.12 if str(query_id) != TOP_VIEW_QUERY else 0.0)
    )
    output_burden = normalize_int_with_bounds(int(annotation_count), [2, 7])
    return build_puzzle_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "visual_scan": float(visual_scan),
            "projection_reasoning": _solid_view_reasoning_score(
                query_id=str(query_id),
                max_height=int(max_height),
            ),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


@dataclass(frozen=True)
class _ProjectionMatchRenderedScene:
    """Rendered projection-option scene payload."""

    stack: CubeStack
    answer_label: str
    answer_index: int
    annotation_bboxes: List[List[float]]
    stack_panel_bbox: List[float]
    option_panel_bboxes: Dict[str, List[float]]
    option_grid_bboxes: Dict[str, List[float]]
    option_cells: Dict[str, List[List[int]]]
    correct_projection_cells: List[List[int]]
    visible_counts_by_query: Dict[str, int]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


def _resolve_projection_match_option_count(rng, *, params: Mapping[str, Any]) -> int:
    minimum = int(params.get("projection_match_option_count_min", group_default(_GEN_DEFAULTS, "projection_match_option_count_min", 5)))
    maximum = int(params.get("projection_match_option_count_max", group_default(_GEN_DEFAULTS, "projection_match_option_count_max", 6)))
    minimum = max(2, min(int(minimum), len(PROJECTION_MATCH_OPTION_LABELS)))
    maximum = max(int(minimum), min(int(maximum), len(PROJECTION_MATCH_OPTION_LABELS)))
    return int(rng.randint(int(minimum), int(maximum)))


def _projection_cell_key(cells: Sequence[ViewCell]) -> Tuple[ViewCell, ...]:
    return tuple(sorted(((int(col), int(row)) for col, row in cells), key=lambda item: (int(item[1]), int(item[0]))))


def _projection_distractor_sets(
    rng,
    *,
    correct_cells: Sequence[ViewCell],
    grid_dims: Tuple[int, int],
    option_count: int,
) -> List[Tuple[ViewCell, ...]]:
    correct_key = _projection_cell_key(correct_cells)
    all_cells = {
        (int(col), int(row))
        for col in range(int(grid_dims[0]))
        for row in range(int(grid_dims[1]))
    }
    occupied = set(correct_key)
    empty = sorted(all_cells - occupied, key=lambda item: (int(item[1]), int(item[0])))
    raw_candidates: List[Tuple[ViewCell, ...]] = []

    for old_cell in sorted(occupied, key=lambda item: (int(item[1]), int(item[0]))):
        for new_cell in empty:
            candidate = set(occupied)
            candidate.remove(old_cell)
            candidate.add(new_cell)
            raw_candidates.append(_projection_cell_key(candidate))

    if len(occupied) > 1:
        for old_cell in sorted(occupied, key=lambda item: (int(item[1]), int(item[0]))):
            candidate = set(occupied)
            candidate.remove(old_cell)
            raw_candidates.append(_projection_cell_key(candidate))
    if empty:
        for new_cell in empty:
            candidate = set(occupied)
            candidate.add(new_cell)
            raw_candidates.append(_projection_cell_key(candidate))

    unique_candidates = sorted(
        {candidate for candidate in raw_candidates if candidate and candidate != correct_key},
        key=lambda item: (len(item), item),
    )
    rng.shuffle(unique_candidates)
    if len(unique_candidates) < int(option_count) - 1:
        raise RuntimeError("not enough unique projection distractors for option set")
    selected = [correct_key] + list(unique_candidates[: int(option_count) - 1])
    rng.shuffle(selected)
    return [tuple((int(col), int(row)) for col, row in candidate) for candidate in selected]


def _projection_answer_index(*, instance_seed: int, params: Mapping[str, Any], option_count: int) -> int:
    """Resolve the correct option slot from the instance seed."""

    _ = params
    return int(abs(int(hash64(int(instance_seed), f"{TASK_ID}.projection_match.answer_slot", 26557))) % max(1, int(option_count)))


def _draw_projection_option_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Tuple[float, float, float, float],
    grid_dims: Tuple[int, int],
    filled_cells: Sequence[ViewCell],
    label: str,
    scene_scale: int,
    line_width: int,
    title_font_size_px: int,
    style: SolidRenderStyle,
) -> Dict[str, object]:
    left, top, right, bottom = [float(value) for value in panel_bbox]
    outline_width = max(1, int(line_width))
    draw_rounded_rect(
        draw,
        (left, top, right, bottom),
        radius=max(8, int(round(10 * int(scene_scale)))),
        fill=style.panel_fill,
        outline=style.panel_outline_color,
        width=int(outline_width),
    )
    label_font = load_font(int(title_font_size_px), bold=True)
    label_bbox = draw_centered_text(
        draw,
        text=str(label),
        center=((left + right) * 0.5, top + (18.0 * float(scene_scale))),
        font=label_font,
        fill=style.panel_title_color,
        stroke_fill=style.panel_title_stroke_color,
        stroke_width=max(1, int(scene_scale)),
    )

    cols, rows = int(grid_dims[0]), int(grid_dims[1])
    if int(cols) <= 0 or int(rows) <= 0:
        raise ValueError("projection option grid dimensions must be positive")
    inner_padding = 14.0 * float(scene_scale)
    grid_top = float(label_bbox[3] + (9.0 * float(scene_scale)))
    grid_left = float(left + inner_padding)
    grid_right = float(right - inner_padding)
    grid_bottom = float(bottom - inner_padding)
    usable_width = max(20.0, float(grid_right - grid_left))
    usable_height = max(20.0, float(grid_bottom - grid_top))
    cell_side = min(float(usable_width / cols), float(usable_height / rows))
    grid_width = float(cell_side * cols)
    grid_height = float(cell_side * rows)
    grid_left = float(grid_left + ((usable_width - grid_width) * 0.5))
    grid_top = float(grid_top + ((usable_height - grid_height) * 0.5))
    filled = {(int(col), int(row)) for col, row in filled_cells}
    filled_bboxes: List[List[float]] = []

    for col in range(int(cols)):
        for row in range(int(rows)):
            x0 = float(grid_left + (float(col) * cell_side))
            y0 = float(grid_top + (float(row) * cell_side))
            x1 = float(x0 + cell_side)
            y1 = float(y0 + cell_side)
            is_filled = (int(col), int(row)) in filled
            draw.rectangle(
                (x0, y0, x1, y1),
                fill=style.right_fill if bool(is_filled) else style.panel_fill,
                outline=style.panel_grid_color,
                width=max(1, int(outline_width)),
            )
            if bool(is_filled):
                filled_bboxes.append(
                    [
                        round(float(x0) / float(scene_scale), 3),
                        round(float(y0) / float(scene_scale), 3),
                        round(float(x1) / float(scene_scale), 3),
                        round(float(y1) / float(scene_scale), 3),
                    ]
                )

    return {
        "panel_bbox": [
            round(float(left) / float(scene_scale), 3),
            round(float(top) / float(scene_scale), 3),
            round(float(right) / float(scene_scale), 3),
            round(float(bottom) / float(scene_scale), 3),
        ],
        "grid_bbox": [
            round(float(grid_left) / float(scene_scale), 3),
            round(float(grid_top) / float(scene_scale), 3),
            round(float(grid_left + grid_width) / float(scene_scale), 3),
            round(float(grid_top + grid_height) / float(scene_scale), 3),
        ],
        "filled_bboxes": list(filled_bboxes),
    }


def _projection_match_panel_layout(
    *,
    canvas_width: int,
    canvas_height: int,
    scene_scale: int,
    option_count: int,
    params: Mapping[str, Any],
) -> Tuple[Tuple[float, float, float, float], Dict[str, Tuple[float, float, float, float]]]:
    margin_px = float(params.get("outer_margin_px", group_default(_RENDER_DEFAULTS, "outer_margin_px", _DEFAULTS.outer_margin_px)))
    gap_px = float(params.get("panel_gap_px", group_default(_RENDER_DEFAULTS, "panel_gap_px", _DEFAULTS.panel_gap_px)))
    margin = float(margin_px * scene_scale)
    gap = float(gap_px * scene_scale)
    full_width = float(canvas_width * scene_scale)
    full_height = float(canvas_height * scene_scale)
    stack_width = float(round((full_width - (2.0 * margin) - gap) * 0.42))
    stack_panel = (
        float(margin),
        float(margin),
        float(margin + stack_width),
        float(full_height - margin),
    )
    option_left = float(stack_panel[2] + gap)
    option_right = float(full_width - margin)
    option_top = float(margin)
    option_bottom = float(full_height - margin)
    option_cols = 2
    option_rows = int((int(option_count) + int(option_cols) - 1) // int(option_cols))
    option_gap = float(14 * int(scene_scale))
    option_width = float((option_right - option_left - (option_gap * (option_cols - 1))) / option_cols)
    option_height = float((option_bottom - option_top - (option_gap * (option_rows - 1))) / option_rows)
    option_bboxes: Dict[str, Tuple[float, float, float, float]] = {}
    for index, label in enumerate(PROJECTION_MATCH_OPTION_LABELS[: int(option_count)]):
        row = int(index // option_cols)
        col = int(index % option_cols)
        x0 = float(option_left + (float(col) * (option_width + option_gap)))
        y0 = float(option_top + (float(row) * (option_height + option_gap)))
        option_bboxes[str(label)] = (
            float(x0),
            float(y0),
            float(x0 + option_width),
            float(y0 + option_height),
        )
    return stack_panel, dict(option_bboxes)


def _render_projection_match_scene(
    rng,
    *,
    instance_seed: int,
    query: _ResolvedQuery,
    canvas_width: int,
    canvas_height: int,
    scene_scale: int,
    line_width: int,
    panel_title_font_size_px: int,
    params: Mapping[str, Any],
    background_meta: Mapping[str, Any],
    shape_style,
    draw: ImageDraw.ImageDraw,
) -> _ProjectionMatchRenderedScene:
    stack, visible_counts_by_query = _sample_stack_matching_target(
        rng,
        query_id=str(query.query_id),
        target_count=int(query.target_count),
        params=params,
    )
    option_count = _resolve_projection_match_option_count(rng, params=params)
    correct_cells = projected_view_cells(stack, query_id=str(query.query_id))
    grid_dims = view_grid_dimensions(stack, query_id=str(query.query_id))
    candidate_sets = _projection_distractor_sets(
        rng,
        correct_cells=correct_cells,
        grid_dims=grid_dims,
        option_count=int(option_count),
    )
    correct_key = _projection_cell_key(correct_cells)
    labels = list(PROJECTION_MATCH_OPTION_LABELS[: int(option_count)])
    distractors = [cells for cells in candidate_sets if _projection_cell_key(cells) != correct_key]
    answer_index = _projection_answer_index(instance_seed=int(instance_seed), params=params, option_count=int(option_count))
    candidate_sets = list(distractors[: int(option_count) - 1])
    candidate_sets.insert(int(answer_index), correct_key)
    answer_label = str(labels[int(answer_index)])
    style = build_solid_render_style(shape_style=shape_style, background_meta=background_meta)
    stack_voxel_scale_percent = _sample_voxel_scale_percent(rng, params=params)
    stack_panel_bbox, option_panel_layout = _projection_match_panel_layout(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        scene_scale=int(scene_scale),
        option_count=int(option_count),
        params=params,
    )
    stack_panel_meta = draw_cube_stack_panel(
        draw,
        panel_bbox=stack_panel_bbox,
        stack=stack,
        scene_scale=int(scene_scale),
        line_width=int(line_width) * int(scene_scale),
        title_text="Cube stack",
        title_font_size_px=int(panel_title_font_size_px) * int(scene_scale),
        style=style,
        voxel_scale=_voxel_scale_from_percent(int(stack_voxel_scale_percent)),
    )
    option_panel_bboxes: Dict[str, List[float]] = {}
    option_grid_bboxes: Dict[str, List[float]] = {}
    option_cells: Dict[str, List[List[int]]] = {}
    for index, label in enumerate(labels):
        option_meta = _draw_projection_option_panel(
            draw,
            panel_bbox=option_panel_layout[str(label)],
            grid_dims=grid_dims,
            filled_cells=candidate_sets[int(index)],
            label=str(label),
            scene_scale=int(scene_scale),
            line_width=int(max(1, line_width - 1)) * int(scene_scale),
            title_font_size_px=int(panel_title_font_size_px) * int(scene_scale),
            style=style,
        )
        option_panel_bboxes[str(label)] = list(option_meta["panel_bbox"])
        option_grid_bboxes[str(label)] = list(option_meta["grid_bbox"])
        option_cells[str(label)] = [[int(col), int(row)] for col, row in candidate_sets[int(index)]]

    annotation_bboxes = [list(option_panel_bboxes[str(answer_label)])]
    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": f"cube_{index:02d}",
            "type": "cube",
            "cell": [int(cell_x), int(cell_y), int(cell_z)],
        }
        for index, (cell_x, cell_y, cell_z) in enumerate(
            sorted(
                [
                    (x_value, y_value, z_value)
                    for (x_value, y_value), height in stack.heights.items()
                    for z_value in range(int(height))
                ],
                key=lambda item: (int(item[2]), int(item[1]), int(item[0])),
            )
        )
    ]
    for label in labels:
        scene_entities.append(
            {
                "entity_id": f"projection_option_{str(label)}",
                "type": "projection_option",
                "bbox": list(option_panel_bboxes[str(label)]),
                "label": str(label),
                "grid_dimensions": [int(grid_dims[0]), int(grid_dims[1])],
                "cells": list(option_cells[str(label)]),
            }
        )

    correct_projection_cells = [[int(col), int(row)] for col, row in correct_key]
    render_map = {
        "image_id": "img0",
        "stack_panel_bbox": list(stack_panel_meta["panel_bbox"]),
        "option_panel_bboxes": dict(option_panel_bboxes),
        "option_grid_bboxes": dict(option_grid_bboxes),
        "option_cells": dict(option_cells),
        "correct_option_label": str(answer_label),
        "stack_voxel_scale_percent": int(stack_voxel_scale_percent),
        "correct_projection_cells": list(correct_projection_cells),
        "query_view_title": str(view_title_for_query(str(query.query_id))),
        "query_grid_dimensions": [int(grid_dims[0]), int(grid_dims[1])],
        "stack_width": int(stack.width),
        "stack_depth": int(stack.depth),
        "stack_heights": [
            {"x": int(x_value), "y": int(y_value), "height": int(height)}
            for (x_value, y_value), height in sorted(stack.heights.items())
        ],
    }
    return _ProjectionMatchRenderedScene(
        stack=stack,
        answer_label=str(answer_label),
        answer_index=int(answer_index),
        annotation_bboxes=list(annotation_bboxes),
        stack_panel_bbox=list(stack_panel_meta["panel_bbox"]),
        option_panel_bboxes=dict(option_panel_bboxes),
        option_grid_bboxes=dict(option_grid_bboxes),
        option_cells=dict(option_cells),
        correct_projection_cells=list(correct_projection_cells),
        visible_counts_by_query={str(key): int(value) for key, value in visible_counts_by_query.items()},
        scene_entities=list(scene_entities),
        render_map=dict(render_map),
    )


def _build_projection_match_complexity(
    *,
    query_id: str,
    cube_count: int,
    max_height: int,
    option_count: int,
    target_count: int,
):
    visual_scan = clamp_unit_interval(
        (0.60 * normalize_int_with_bounds(int(cube_count), [4, 9]))
        + (0.25 * normalize_int_with_bounds(int(option_count), [4, 6]))
        + (0.15 * normalize_int_with_bounds(int(max_height), [2, 3]))
    )
    reasoning_load = clamp_unit_interval(_solid_view_reasoning_score(query_id=str(query_id), max_height=int(max_height)) + 0.08)
    ambiguity = clamp_unit_interval(normalize_int_with_bounds(int(target_count), [3, 7]))
    return build_puzzle_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "visual_scan": float(visual_scan),
            "projection_reasoning": float(reasoning_load),
            "ambiguity": float(ambiguity),
            "output_burden": 0.20,
        },
    )


@dataclass(frozen=True)
class _ProjectionConsistencyRenderedScene:
    """Rendered projection-consistency scene payload."""

    answer_label: str
    answer_index: int
    consistency_query: str
    annotation_bboxes: List[List[float]]
    reference_stack: CubeStack
    visible_counts_by_query: Dict[str, int]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]
    option_count: int


def _resolve_projection_consistency_option_count(rng, *, params: Mapping[str, Any]) -> int:
    minimum = int(params.get("projection_consistency_option_count_min", group_default(_GEN_DEFAULTS, "projection_consistency_option_count_min", 4)))
    maximum = int(params.get("projection_consistency_option_count_max", group_default(_GEN_DEFAULTS, "projection_consistency_option_count_max", 5)))
    minimum = max(3, min(int(minimum), len(PROJECTION_MATCH_OPTION_LABELS)))
    maximum = max(int(minimum), min(int(maximum), len(PROJECTION_MATCH_OPTION_LABELS)))
    return int(rng.randint(int(minimum), int(maximum)))


def _projection_consistency_answer_index(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    option_count: int,
    query_id: str,
) -> int:
    """Resolve the correct option slot from the instance seed."""

    _ = params
    return int(
        abs(int(hash64(int(instance_seed), f"{TASK_ID}.{query_id}.answer_slot", 30491)))
        % max(1, int(option_count))
    )


def _projection_consistency_panel_layout(
    *,
    canvas_width: int,
    canvas_height: int,
    scene_scale: int,
    option_count: int,
    mode: str,
    params: Mapping[str, Any],
) -> Tuple[Dict[str, Tuple[float, float, float, float]], Dict[str, Tuple[float, float, float, float]]]:
    """Resolve projection/reference and option panel boxes for consistency scenes."""

    margin_px = float(params.get("outer_margin_px", group_default(_RENDER_DEFAULTS, "outer_margin_px", _DEFAULTS.outer_margin_px)))
    gap_px = float(params.get("panel_gap_px", group_default(_RENDER_DEFAULTS, "panel_gap_px", _DEFAULTS.panel_gap_px)))
    margin = float(margin_px * int(scene_scale))
    gap = float(gap_px * int(scene_scale))
    small_gap = float(14 * int(scene_scale))
    full_width = float(canvas_width * int(scene_scale))
    full_height = float(canvas_height * int(scene_scale))
    usable_width = float(full_width - (2.0 * margin))
    usable_height = float(full_height - (2.0 * margin))

    if str(mode) == "inconsistent_projection_label":
        stack_width = float(round((usable_width - gap) * 0.43))
        reference_bboxes = {
            "stack": (
                float(margin),
                float(margin),
                float(margin + stack_width),
                float(full_height - margin),
            )
        }
        option_left = float(reference_bboxes["stack"][2] + gap)
        option_right = float(full_width - margin)
        option_cols = 2
        option_rows = int((int(option_count) + int(option_cols) - 1) // int(option_cols))
        option_width = float((option_right - option_left - (small_gap * (option_cols - 1))) / option_cols)
        option_height = float((usable_height - (small_gap * (option_rows - 1))) / option_rows)
        option_bboxes = {}
        for index, label in enumerate(PROJECTION_MATCH_OPTION_LABELS[: int(option_count)]):
            row = int(index // option_cols)
            col = int(index % option_cols)
            x0 = float(option_left + (float(col) * (option_width + small_gap)))
            y0 = float(margin + (float(row) * (option_height + small_gap)))
            option_bboxes[str(label)] = (
                float(x0),
                float(y0),
                float(x0 + option_width),
                float(y0 + option_height),
            )
        return dict(reference_bboxes), dict(option_bboxes)

    reference_width = float(round((usable_width - gap) * 0.34))
    reference_bboxes = {}
    view_height = float((usable_height - (2.0 * small_gap)) / 3.0)
    for index, query_id in enumerate(SUPPORTED_QUERY_IDS):
        y0 = float(margin + (float(index) * (view_height + small_gap)))
        reference_bboxes[str(query_id)] = (
            float(margin),
            float(y0),
            float(margin + reference_width),
            float(y0 + view_height),
        )
    option_left = float(margin + reference_width + gap)
    option_right = float(full_width - margin)
    option_cols = 2
    option_rows = int((int(option_count) + int(option_cols) - 1) // int(option_cols))
    option_width = float((option_right - option_left - (small_gap * (option_cols - 1))) / option_cols)
    option_height = float((usable_height - (small_gap * (option_rows - 1))) / option_rows)
    option_bboxes = {}
    for index, label in enumerate(PROJECTION_MATCH_OPTION_LABELS[: int(option_count)]):
        row = int(index // option_cols)
        col = int(index % option_cols)
        x0 = float(option_left + (float(col) * (option_width + small_gap)))
        y0 = float(margin + (float(row) * (option_height + small_gap)))
        option_bboxes[str(label)] = (
            float(x0),
            float(y0),
            float(x0 + option_width),
            float(y0 + option_height),
        )
    return dict(reference_bboxes), dict(option_bboxes)


def _corrupt_projection_cells(
    rng,
    *,
    correct_cells: Sequence[ViewCell],
    grid_dims: Tuple[int, int],
) -> Tuple[ViewCell, ...]:
    """Return one valid projection-grid distractor for an inconsistent panel."""

    candidates = _projection_distractor_sets(
        rng,
        correct_cells=correct_cells,
        grid_dims=grid_dims,
        option_count=2,
    )
    correct_key = _projection_cell_key(correct_cells)
    for candidate in candidates:
        if _projection_cell_key(candidate) != correct_key:
            return tuple((int(col), int(row)) for col, row in candidate)
    raise RuntimeError("failed to build an inconsistent projection distractor")


def _render_inconsistent_projection_scene(
    rng,
    *,
    instance_seed: int,
    canvas_width: int,
    canvas_height: int,
    scene_scale: int,
    line_width: int,
    panel_title_font_size_px: int,
    params: Mapping[str, Any],
    background_meta: Mapping[str, Any],
    shape_style,
    draw: ImageDraw.ImageDraw,
) -> _ProjectionConsistencyRenderedScene:
    stack, visible_counts_by_query = _sample_consistency_stack(rng, params=params)
    option_count = _resolve_projection_consistency_option_count(rng, params=params)
    answer_index = _projection_consistency_answer_index(
        instance_seed=int(instance_seed),
        params=params,
        option_count=int(option_count),
        query_id="inconsistent_projection_label",
    )
    answer_label = str(PROJECTION_MATCH_OPTION_LABELS[int(answer_index)])
    style = build_solid_render_style(shape_style=shape_style, background_meta=background_meta)
    reference_bboxes, option_bboxes_scaled = _projection_consistency_panel_layout(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        scene_scale=int(scene_scale),
        option_count=int(option_count),
        mode="inconsistent_projection_label",
        params=params,
    )
    panel_queries = [
        str(SUPPORTED_QUERY_IDS[int(index) % len(SUPPORTED_QUERY_IDS)])
        for index in range(int(option_count))
    ]
    corrupt_query = str(panel_queries[int(answer_index)])
    stack_voxel_scale_percent = _sample_voxel_scale_percent(rng, params=params)
    stack_meta = draw_cube_stack_panel(
        draw,
        panel_bbox=reference_bboxes["stack"],
        stack=stack,
        scene_scale=int(scene_scale),
        line_width=int(line_width) * int(scene_scale),
        title_text="Cube stack",
        title_font_size_px=int(panel_title_font_size_px) * int(scene_scale),
        style=style,
        voxel_scale=_voxel_scale_from_percent(int(stack_voxel_scale_percent)),
    )
    option_panel_bboxes: Dict[str, List[float]] = {}
    option_grid_bboxes: Dict[str, List[float]] = {}
    option_cells: Dict[str, List[List[int]]] = {}
    panel_query_by_label: Dict[str, str] = {}

    for index, query_id in enumerate(panel_queries):
        label = str(PROJECTION_MATCH_OPTION_LABELS[int(index)])
        correct_cells = projected_view_cells(stack, query_id=str(query_id))
        grid_dims = view_grid_dimensions(stack, query_id=str(query_id))
        shown_cells: Sequence[ViewCell]
        if str(query_id) == str(corrupt_query):
            shown_cells = _corrupt_projection_cells(rng, correct_cells=correct_cells, grid_dims=grid_dims)
        else:
            shown_cells = correct_cells
        option_meta = _draw_projection_option_panel(
            draw,
            panel_bbox=option_bboxes_scaled[str(label)],
            grid_dims=grid_dims,
            filled_cells=shown_cells,
            label=f"{label} {view_title_for_query(str(query_id))}",
            scene_scale=int(scene_scale),
            line_width=int(max(1, line_width - 1)) * int(scene_scale),
            title_font_size_px=int(max(12, panel_title_font_size_px - 2)) * int(scene_scale),
            style=style,
        )
        option_panel_bboxes[str(label)] = list(option_meta["panel_bbox"])
        option_grid_bboxes[str(label)] = list(option_meta["grid_bbox"])
        option_cells[str(label)] = [[int(col), int(row)] for col, row in shown_cells]
        panel_query_by_label[str(label)] = str(query_id)

    annotation_bboxes = [list(option_panel_bboxes[str(answer_label)])]
    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": f"cube_{index:02d}",
            "type": "cube",
            "cell": [int(cell_x), int(cell_y), int(cell_z)],
        }
        for index, (cell_x, cell_y, cell_z) in enumerate(
            sorted(
                [
                    (x_value, y_value, z_value)
                    for (x_value, y_value), height in stack.heights.items()
                    for z_value in range(int(height))
                ],
                key=lambda item: (int(item[2]), int(item[1]), int(item[0])),
            )
        )
    ]
    for label in PROJECTION_MATCH_OPTION_LABELS[: int(option_count)]:
        scene_entities.append(
            {
                "entity_id": f"projection_panel_{label}",
                "type": "projection_panel",
                "bbox": list(option_panel_bboxes[str(label)]),
                "label": str(label),
                "query_id": str(panel_query_by_label[str(label)]),
                "is_inconsistent": bool(str(label) == str(answer_label)),
                "cells": list(option_cells[str(label)]),
            }
        )

    render_map = {
        "image_id": "img0",
        "stack_panel_bbox": list(stack_meta["panel_bbox"]),
        "option_panel_bboxes": dict(option_panel_bboxes),
        "option_grid_bboxes": dict(option_grid_bboxes),
        "option_cells": dict(option_cells),
        "panel_query_by_label": dict(panel_query_by_label),
        "correct_option_label": str(answer_label),
        "stack_voxel_scale_percent": int(stack_voxel_scale_percent),
        "inconsistent_query_id": str(corrupt_query),
        "stack_width": int(stack.width),
        "stack_depth": int(stack.depth),
        "stack_heights": [
            {"x": int(x_value), "y": int(y_value), "height": int(height)}
            for (x_value, y_value), height in sorted(stack.heights.items())
        ],
    }
    return _ProjectionConsistencyRenderedScene(
        answer_label=str(answer_label),
        answer_index=int(answer_index),
        consistency_query="inconsistent_projection_label",
        annotation_bboxes=list(annotation_bboxes),
        reference_stack=stack,
        visible_counts_by_query={str(key): int(value) for key, value in visible_counts_by_query.items()},
        scene_entities=list(scene_entities),
        render_map=dict(render_map),
        option_count=int(option_count),
    )


def _render_candidate_stack_from_views_scene(
    rng,
    *,
    instance_seed: int,
    canvas_width: int,
    canvas_height: int,
    scene_scale: int,
    line_width: int,
    panel_title_font_size_px: int,
    params: Mapping[str, Any],
    background_meta: Mapping[str, Any],
    shape_style,
    draw: ImageDraw.ImageDraw,
) -> _ProjectionConsistencyRenderedScene:
    reference_stack, visible_counts_by_query = _sample_consistency_stack(rng, params=params)
    option_count = _resolve_projection_consistency_option_count(rng, params=params)
    answer_index = _projection_consistency_answer_index(
        instance_seed=int(instance_seed),
        params=params,
        option_count=int(option_count),
        query_id="candidate_stack_from_views_label",
    )
    answer_label = str(PROJECTION_MATCH_OPTION_LABELS[int(answer_index)])
    distractor_stacks = _sample_projection_distractor_stacks(
        rng,
        correct_stack=reference_stack,
        option_count=int(option_count),
        params=params,
    )
    candidate_stacks = list(distractor_stacks[: int(option_count) - 1])
    candidate_stacks.insert(int(answer_index), reference_stack)
    style = build_solid_render_style(shape_style=shape_style, background_meta=background_meta)
    reference_bboxes, option_bboxes_scaled = _projection_consistency_panel_layout(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        scene_scale=int(scene_scale),
        option_count=int(option_count),
        mode="candidate_stack_from_views_label",
        params=params,
    )
    reference_panel_bboxes: Dict[str, List[float]] = {}
    reference_grid_bboxes: Dict[str, List[float]] = {}
    reference_cells: Dict[str, List[List[int]]] = {}
    for query_id in SUPPORTED_QUERY_IDS:
        cells = projected_view_cells(reference_stack, query_id=str(query_id))
        grid_dims = view_grid_dimensions(reference_stack, query_id=str(query_id))
        panel_meta = _draw_projection_option_panel(
            draw,
            panel_bbox=reference_bboxes[str(query_id)],
            grid_dims=grid_dims,
            filled_cells=cells,
            label=view_title_for_query(str(query_id)),
            scene_scale=int(scene_scale),
            line_width=int(max(1, line_width - 1)) * int(scene_scale),
            title_font_size_px=int(max(12, panel_title_font_size_px - 2)) * int(scene_scale),
            style=style,
        )
        reference_panel_bboxes[str(query_id)] = list(panel_meta["panel_bbox"])
        reference_grid_bboxes[str(query_id)] = list(panel_meta["grid_bbox"])
        reference_cells[str(query_id)] = [[int(col), int(row)] for col, row in cells]

    option_panel_bboxes: Dict[str, List[float]] = {}
    option_stack_heights: Dict[str, List[Dict[str, int]]] = {}
    option_voxel_scale_percent: Dict[str, int] = {}
    labels = list(PROJECTION_MATCH_OPTION_LABELS[: int(option_count)])
    for index, label in enumerate(labels):
        voxel_scale_percent = _sample_voxel_scale_percent(rng, params=params)
        stack_meta = draw_cube_stack_panel(
            draw,
            panel_bbox=option_bboxes_scaled[str(label)],
            stack=candidate_stacks[int(index)],
            scene_scale=int(scene_scale),
            line_width=int(line_width) * int(scene_scale),
            title_text=str(label),
            title_font_size_px=int(panel_title_font_size_px) * int(scene_scale),
            style=style,
            voxel_scale=_voxel_scale_from_percent(int(voxel_scale_percent)),
        )
        option_panel_bboxes[str(label)] = list(stack_meta["panel_bbox"])
        option_voxel_scale_percent[str(label)] = int(voxel_scale_percent)
        option_stack_heights[str(label)] = [
            {"x": int(x_value), "y": int(y_value), "height": int(height)}
            for (x_value, y_value), height in sorted(candidate_stacks[int(index)].heights.items())
        ]

    annotation_bboxes = [list(option_panel_bboxes[str(answer_label)])]
    scene_entities: List[Dict[str, Any]] = []
    for query_id in SUPPORTED_QUERY_IDS:
        scene_entities.append(
            {
                "entity_id": f"reference_projection_{str(query_id)}",
                "type": "projection_panel",
                "bbox": list(reference_panel_bboxes[str(query_id)]),
                "query_id": str(query_id),
                "cells": list(reference_cells[str(query_id)]),
            }
        )
    for index, label in enumerate(labels):
        scene_entities.append(
            {
                "entity_id": f"candidate_stack_{label}",
                "type": "candidate_stack",
                "bbox": list(option_panel_bboxes[str(label)]),
                "label": str(label),
                "is_correct": bool(str(label) == str(answer_label)),
                "stack_heights": list(option_stack_heights[str(label)]),
                "voxel_scale_percent": int(option_voxel_scale_percent[str(label)]),
            }
        )

    render_map = {
        "image_id": "img0",
        "reference_projection_panel_bboxes": dict(reference_panel_bboxes),
        "reference_projection_grid_bboxes": dict(reference_grid_bboxes),
        "reference_projection_cells": dict(reference_cells),
        "option_panel_bboxes": dict(option_panel_bboxes),
        "option_stack_heights": dict(option_stack_heights),
        "option_voxel_scale_percent": dict(option_voxel_scale_percent),
        "correct_option_label": str(answer_label),
        "reference_stack_heights": [
            {"x": int(x_value), "y": int(y_value), "height": int(height)}
            for (x_value, y_value), height in sorted(reference_stack.heights.items())
        ],
        "stack_width": int(reference_stack.width),
        "stack_depth": int(reference_stack.depth),
    }
    return _ProjectionConsistencyRenderedScene(
        answer_label=str(answer_label),
        answer_index=int(answer_index),
        consistency_query="candidate_stack_from_views_label",
        annotation_bboxes=list(annotation_bboxes),
        reference_stack=reference_stack,
        visible_counts_by_query={str(key): int(value) for key, value in visible_counts_by_query.items()},
        scene_entities=list(scene_entities),
        render_map=dict(render_map),
        option_count=int(option_count),
    )


def _build_projection_consistency_complexity(
    *,
    consistency_query: str,
    cube_count: int,
    max_height: int,
    option_count: int,
):
    visual_scan = clamp_unit_interval(
        (0.54 * normalize_int_with_bounds(int(cube_count), [4, 9]))
        + (0.28 * normalize_int_with_bounds(int(option_count), [3, 5]))
        + (0.18 * normalize_int_with_bounds(int(max_height), [2, 3]))
    )
    query_bonus = 0.18 if str(consistency_query) == "candidate_stack_from_views_label" else 0.08
    return build_puzzle_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "visual_scan": float(visual_scan),
            "projection_reasoning": clamp_unit_interval(0.58 + float(query_bonus)),
            "ambiguity": clamp_unit_interval(0.42 + (0.10 * normalize_int_with_bounds(int(option_count), [3, 5]))),
            "output_burden": 0.20,
        },
    )


class SolidViewCountGenerator:
    """Generate the visible-cube-count branch for the merged cube-structure task."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "spatial"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query = _resolve_axes(int(instance_seed), params=params)
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.scene")

        last_error: Exception | None = None
        canvas_size = None
        scene_scale = None
        line_width = None
        panel_title_font_size_px = None
        image = None
        background_meta = None
        shape_style = None
        rendered_scene = None

        for _ in range(max(1, int(max_attempts))):
            try:
                canvas_size_attempt = _resolve_canvas_size(rng, params=params)
                scene_scale_attempt = max(
                    1,
                    int(
                        params.get(
                            "scene_supersample_scale",
                            group_default(_RENDER_DEFAULTS, "scene_supersample_scale", _DEFAULTS.scene_supersample_scale),
                        )
                    ),
                )
                render_canvas_size = int(canvas_size_attempt) * int(scene_scale_attempt)
                line_width_attempt = sample_int_render_param(
                    rng,
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    key="line_width",
                    fallback=_DEFAULTS.line_width,
                    minimum_value=1,
                )
                panel_title_font_size_px_attempt = _sample_panel_title_font_size(rng, params=params)
                scene_style_attempt, scene_style_meta_attempt = resolve_puzzle_scene_style(
                    instance_seed=int(instance_seed),
                    namespace=f"{self.task_id}.solid_view_background",
                )
                image_attempt, background_meta_attempt = make_puzzle_scene_background(
                    canvas_width=int(render_canvas_size),
                    canvas_height=int(render_canvas_size),
                    style=scene_style_attempt,
                )
                background_meta_attempt["scene_style"] = dict(scene_style_meta_attempt)
                draw_attempt = ImageDraw.Draw(image_attempt)
                shape_style_attempt = sample_geometry_shape_style(
                    rng,
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    anchor_colors=extract_background_anchor_colors(background_meta_attempt),
                )
                rendered_scene_attempt = _render_scene(
                    rng,
                    query=query,
                    canvas_size=int(canvas_size_attempt),
                    scene_scale=int(scene_scale_attempt),
                    line_width=int(line_width_attempt),
                    panel_title_font_size_px=int(panel_title_font_size_px_attempt),
                    params=params,
                    background_meta=background_meta_attempt,
                    shape_style=shape_style_attempt,
                    draw=draw_attempt,
                )
                canvas_size = int(canvas_size_attempt)
                scene_scale = int(scene_scale_attempt)
                line_width = int(line_width_attempt)
                panel_title_font_size_px = int(panel_title_font_size_px_attempt)
                image = image_attempt
                background_meta = dict(background_meta_attempt)
                shape_style = shape_style_attempt
                rendered_scene = rendered_scene_attempt
                break
            except Exception as exc:
                last_error = exc
                continue

        if (
            rendered_scene is None
            or image is None
            or background_meta is None
            or shape_style is None
            or canvas_size is None
            or scene_scale is None
            or line_width is None
            or panel_title_font_size_px is None
        ):
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        out_image = image
        if int(scene_scale) > 1:
            out_image = out_image.resize((int(canvas_size), int(canvas_size)), resample=Image.Resampling.LANCZOS)
        out_image, post_noise_meta = apply_post_image_noise(
            out_image,
            instance_seed=int(instance_seed),
            params=dict(params),
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        background_meta_final = dict(background_meta)
        background_meta_final["render_scale"] = int(scene_scale)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description_visible_cube_count",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_integer",
                "annotation_hint_visible_cube_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = build_prompt_json_examples(
            annotation_value=rendered_scene.annotation_bboxes,
            answer_type="integer",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.public_query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_visible_cube_count"]),
                "view_direction": str(query.view_direction).title(),
                "view_direction_description": str(_view_direction_description(str(query.view_direction))),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_visible_cube_count"]),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(rendered_scene.answer_value))
        annotation_gt = TypedValue(type="bbox_set", value=list(rendered_scene.annotation_bboxes))

        query_params = {
            "scene_variant": str(query.scene_variant),
            "query_id": str(query.public_query_id),
            "internal_query_id": str(query.query_id),
            "view_direction": str(query.view_direction),
            "query_id_probabilities": dict(query.query_id_probabilities),
            "scene_variant_probabilities": dict(query.scene_variant_probabilities),
            "view_direction_probabilities": dict(query.view_direction_probabilities),
            "target_count": int(query.target_count),
            "target_count_probabilities": dict(query.target_count_probabilities),
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "puzzles_spatial_cube_structure_visible_count",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(query.scene_variant),
                    "query_id": str(query.public_query_id),
                    "internal_query_id": str(query.query_id),
                    "view_direction": str(query.view_direction),
                    "visible_counts_by_query": dict(rendered_scene.visible_counts_by_query),
                    "target_count": int(query.target_count),
                },
            },
            "query_spec": {
                "query_id": str(query.public_query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": int(canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "scene_scale": int(scene_scale),
                "line_width_px": int(line_width),
                "panel_title_font_size_px": int(panel_title_font_size_px),
                "scene_variant": str(query.scene_variant),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(query.scene_variant),
                "query_id": str(query.public_query_id),
                "internal_query_id": str(query.query_id),
                "view_direction": str(query.view_direction),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "view_direction_probabilities": dict(query.view_direction_probabilities),
                "target_count": int(query.target_count),
                "target_count_probabilities": dict(query.target_count_probabilities),
                "cube_count": int(rendered_scene.stack.cube_count),
                "stack_width": int(rendered_scene.stack.width),
                "stack_depth": int(rendered_scene.stack.depth),
                "stack_max_height": int(rendered_scene.stack.max_height),
                "stack_heights": [
                    {"x": int(x_value), "y": int(y_value), "height": int(height)}
                    for (x_value, y_value), height in sorted(rendered_scene.stack.heights.items())
                ],
                "visible_counts_by_query": dict(rendered_scene.visible_counts_by_query),
                "projection_cells": list(rendered_scene.projection_cells),
                "question_format": "count_projection_cells",
            },
            "witness_symbolic": {
                "type": "projection_cell_set",
                "cells": list(rendered_scene.projection_cells),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "pixel_bbox_set": list(rendered_scene.annotation_bboxes),
                "projection_cells": list(rendered_scene.projection_cells),
                "query_panel_bbox": list(rendered_scene.query_panel_bbox),
                "query_grid_bbox": list(rendered_scene.query_grid_bbox),
                "query_grid_dimensions": [int(rendered_scene.query_grid_dims[0]), int(rendered_scene.query_grid_dims[1])],
            },
        }

        complexity = _build_solid_view_complexity(
            query_id=str(query.query_id),
            cube_count=int(rendered_scene.stack.cube_count),
            max_height=int(rendered_scene.stack.max_height),
            target_count=int(query.target_count),
            annotation_count=len(rendered_scene.annotation_bboxes),
        )
        trace_payload["answer_gt"] = answer_gt.to_dict()
        trace_payload["annotation_gt"] = annotation_gt.to_dict()
        trace_payload["complexity"] = complexity.to_dict()

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=out_image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(query.public_query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class SolidViewProjectionMatchGenerator:
    """Generate a cube-stack orthographic projection multiple-choice task."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "spatial"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query = _resolve_projection_match_axes(int(instance_seed), params=params)
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.projection_match_scene")

        last_error: Exception | None = None
        canvas_width = None
        canvas_height = None
        scene_scale = None
        line_width = None
        panel_title_font_size_px = None
        image = None
        background_meta = None
        shape_style = None
        rendered_scene = None

        for _ in range(max(1, int(max_attempts))):
            try:
                canvas_width_attempt = int(
                    params.get(
                        "projection_match_canvas_width",
                        group_default(_RENDER_DEFAULTS, "projection_match_canvas_width", 1120),
                    )
                )
                canvas_height_attempt = int(
                    params.get(
                        "projection_match_canvas_height",
                        group_default(_RENDER_DEFAULTS, "projection_match_canvas_height", 860),
                    )
                )
                scene_scale_attempt = max(
                    1,
                    int(
                        params.get(
                            "scene_supersample_scale",
                            group_default(_RENDER_DEFAULTS, "scene_supersample_scale", _DEFAULTS.scene_supersample_scale),
                        )
                    ),
                )
                render_canvas_width = int(canvas_width_attempt) * int(scene_scale_attempt)
                render_canvas_height = int(canvas_height_attempt) * int(scene_scale_attempt)
                line_width_attempt = sample_int_render_param(
                    rng,
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    key="line_width",
                    fallback=_DEFAULTS.line_width,
                    minimum_value=1,
                )
                panel_title_font_size_px_attempt = _sample_panel_title_font_size(rng, params=params)
                scene_style_attempt, scene_style_meta_attempt = resolve_puzzle_scene_style(
                    instance_seed=int(instance_seed),
                    namespace=f"{self.task_id}.projection_match_background",
                )
                image_attempt, background_meta_attempt = make_puzzle_scene_background(
                    canvas_width=int(render_canvas_width),
                    canvas_height=int(render_canvas_height),
                    style=scene_style_attempt,
                )
                background_meta_attempt["scene_style"] = dict(scene_style_meta_attempt)
                draw_attempt = ImageDraw.Draw(image_attempt)
                shape_style_attempt = sample_geometry_shape_style(
                    rng,
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    anchor_colors=extract_background_anchor_colors(background_meta_attempt),
                )
                rendered_scene_attempt = _render_projection_match_scene(
                    rng,
                    instance_seed=int(instance_seed),
                    query=query,
                    canvas_width=int(canvas_width_attempt),
                    canvas_height=int(canvas_height_attempt),
                    scene_scale=int(scene_scale_attempt),
                    line_width=int(line_width_attempt),
                    panel_title_font_size_px=int(panel_title_font_size_px_attempt),
                    params=params,
                    background_meta=background_meta_attempt,
                    shape_style=shape_style_attempt,
                    draw=draw_attempt,
                )
                canvas_width = int(canvas_width_attempt)
                canvas_height = int(canvas_height_attempt)
                scene_scale = int(scene_scale_attempt)
                line_width = int(line_width_attempt)
                panel_title_font_size_px = int(panel_title_font_size_px_attempt)
                image = image_attempt
                background_meta = dict(background_meta_attempt)
                shape_style = shape_style_attempt
                rendered_scene = rendered_scene_attempt
                break
            except Exception as exc:
                last_error = exc
                continue

        if (
            rendered_scene is None
            or image is None
            or background_meta is None
            or shape_style is None
            or canvas_width is None
            or canvas_height is None
            or scene_scale is None
            or line_width is None
            or panel_title_font_size_px is None
        ):
            raise RuntimeError(f"failed to generate {self.task_id} projection-match instance") from last_error

        out_image = image
        if int(scene_scale) > 1:
            out_image = out_image.resize((int(canvas_width), int(canvas_height)), resample=Image.Resampling.LANCZOS)
        out_image, post_noise_meta = apply_post_image_noise(
            out_image,
            instance_seed=int(instance_seed),
            params=dict(params),
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        background_meta_final = dict(background_meta)
        background_meta_final["render_scale"] = int(scene_scale)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description_projection_match_label",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_option_letter",
                "annotation_hint_projection_match_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = build_prompt_json_examples(
            annotation_value=rendered_scene.annotation_bboxes,
            answer_type="option_letter",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=PROJECTION_MATCH_QUERY,
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_projection_match_label"]),
                "view_direction": str(query.view_direction).title(),
                "view_direction_description": str(_view_direction_description(str(query.view_direction))),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_projection_match_label"]),
                "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="string", value=str(rendered_scene.answer_label))
        annotation_gt = TypedValue(type="bbox_set", value=list(rendered_scene.annotation_bboxes))
        query_params = {
            "scene_variant": str(query.scene_variant),
            "query_id": PROJECTION_MATCH_QUERY,
            "internal_query_id": str(query.query_id),
            "view_direction": str(query.view_direction),
            "query_id_probabilities": {PROJECTION_MATCH_QUERY: 1.0},
            "scene_variant_probabilities": dict(query.scene_variant_probabilities),
            "view_direction_probabilities": dict(query.view_direction_probabilities),
            "target_count": int(query.target_count),
            "target_count_probabilities": dict(query.target_count_probabilities),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "puzzles_spatial_cube_projection_match",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(query.scene_variant),
                    "query_id": PROJECTION_MATCH_QUERY,
                    "internal_query_id": str(query.query_id),
                    "view_direction": str(query.view_direction),
                    "visible_counts_by_query": dict(rendered_scene.visible_counts_by_query),
                    "answer_label": str(rendered_scene.answer_label),
                },
            },
            "query_spec": {
                "query_id": PROJECTION_MATCH_QUERY,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_width": int(canvas_width),
                "canvas_height": int(canvas_height),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "scene_scale": int(scene_scale),
                "line_width_px": int(line_width),
                "panel_title_font_size_px": int(panel_title_font_size_px),
                "scene_variant": str(query.scene_variant),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(query.scene_variant),
                "query_id": PROJECTION_MATCH_QUERY,
                "internal_query_id": str(query.query_id),
                "view_direction": str(query.view_direction),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "query_id_probabilities": {PROJECTION_MATCH_QUERY: 1.0},
                "view_direction_probabilities": dict(query.view_direction_probabilities),
                "target_count": int(query.target_count),
                "target_count_probabilities": dict(query.target_count_probabilities),
                "cube_count": int(rendered_scene.stack.cube_count),
                "stack_width": int(rendered_scene.stack.width),
                "stack_depth": int(rendered_scene.stack.depth),
                "stack_max_height": int(rendered_scene.stack.max_height),
                "stack_heights": [
                    {"x": int(x_value), "y": int(y_value), "height": int(height)}
                    for (x_value, y_value), height in sorted(rendered_scene.stack.heights.items())
                ],
                "visible_counts_by_query": dict(rendered_scene.visible_counts_by_query),
                "correct_projection_cells": list(rendered_scene.correct_projection_cells),
                "option_cells": dict(rendered_scene.option_cells),
                "answer_label": str(rendered_scene.answer_label),
                "question_format": "projection_match_label",
            },
            "witness_symbolic": {
                "type": "option_label",
                "label": str(rendered_scene.answer_label),
                "correct_projection_cells": list(rendered_scene.correct_projection_cells),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "pixel_bbox_set": list(rendered_scene.annotation_bboxes),
                "selected_option_label": str(rendered_scene.answer_label),
                "selected_option_bbox": list(rendered_scene.annotation_bboxes[0]),
            },
        }
        complexity = _build_projection_match_complexity(
            query_id=str(query.query_id),
            cube_count=int(rendered_scene.stack.cube_count),
            max_height=int(rendered_scene.stack.max_height),
            option_count=len(rendered_scene.option_panel_bboxes),
            target_count=int(query.target_count),
        )
        trace_payload["answer_gt"] = answer_gt.to_dict()
        trace_payload["annotation_gt"] = annotation_gt.to_dict()
        trace_payload["complexity"] = complexity.to_dict()

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=out_image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=PROJECTION_MATCH_QUERY,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


class SolidViewProjectionConsistencyGenerator:
    """Generate a cube-stack projection consistency option-label task."""

    task_id = TASK_ID
    domain = "puzzles"
    task_group = "spatial"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        consistency_query, consistency_query_probabilities = _resolve_projection_consistency_query(
            int(instance_seed),
            params=params,
        )
        rng = spawn_rng(int(instance_seed), f"{self.task_id}.projection_consistency_scene")

        last_error: Exception | None = None
        canvas_width = None
        canvas_height = None
        scene_scale = None
        line_width = None
        panel_title_font_size_px = None
        image = None
        background_meta = None
        shape_style = None
        rendered_scene = None

        for _ in range(max(1, int(max_attempts))):
            try:
                canvas_width_attempt = int(
                    params.get(
                        "projection_consistency_canvas_width",
                        group_default(_RENDER_DEFAULTS, "projection_consistency_canvas_width", 1120),
                    )
                )
                canvas_height_attempt = int(
                    params.get(
                        "projection_consistency_canvas_height",
                        group_default(_RENDER_DEFAULTS, "projection_consistency_canvas_height", 900),
                    )
                )
                scene_scale_attempt = max(
                    1,
                    int(
                        params.get(
                            "scene_supersample_scale",
                            group_default(_RENDER_DEFAULTS, "scene_supersample_scale", _DEFAULTS.scene_supersample_scale),
                        )
                    ),
                )
                render_canvas_width = int(canvas_width_attempt) * int(scene_scale_attempt)
                render_canvas_height = int(canvas_height_attempt) * int(scene_scale_attempt)
                line_width_attempt = sample_int_render_param(
                    rng,
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    key="line_width",
                    fallback=_DEFAULTS.line_width,
                    minimum_value=1,
                )
                panel_title_font_size_px_attempt = _sample_panel_title_font_size(rng, params=params)
                scene_style_attempt, scene_style_meta_attempt = resolve_puzzle_scene_style(
                    instance_seed=int(instance_seed),
                    namespace=f"{self.task_id}.projection_consistency_background",
                )
                image_attempt, background_meta_attempt = make_puzzle_scene_background(
                    canvas_width=int(render_canvas_width),
                    canvas_height=int(render_canvas_height),
                    style=scene_style_attempt,
                )
                background_meta_attempt["scene_style"] = dict(scene_style_meta_attempt)
                draw_attempt = ImageDraw.Draw(image_attempt)
                shape_style_attempt = sample_geometry_shape_style(
                    rng,
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    anchor_colors=extract_background_anchor_colors(background_meta_attempt),
                )
                if str(consistency_query) == "candidate_stack_from_views_label":
                    rendered_scene_attempt = _render_candidate_stack_from_views_scene(
                        rng,
                        instance_seed=int(instance_seed),
                        canvas_width=int(canvas_width_attempt),
                        canvas_height=int(canvas_height_attempt),
                        scene_scale=int(scene_scale_attempt),
                        line_width=int(line_width_attempt),
                        panel_title_font_size_px=int(panel_title_font_size_px_attempt),
                        params=params,
                        background_meta=background_meta_attempt,
                        shape_style=shape_style_attempt,
                        draw=draw_attempt,
                    )
                else:
                    rendered_scene_attempt = _render_inconsistent_projection_scene(
                        rng,
                        instance_seed=int(instance_seed),
                        canvas_width=int(canvas_width_attempt),
                        canvas_height=int(canvas_height_attempt),
                        scene_scale=int(scene_scale_attempt),
                        line_width=int(line_width_attempt),
                        panel_title_font_size_px=int(panel_title_font_size_px_attempt),
                        params=params,
                        background_meta=background_meta_attempt,
                        shape_style=shape_style_attempt,
                        draw=draw_attempt,
                    )
                canvas_width = int(canvas_width_attempt)
                canvas_height = int(canvas_height_attempt)
                scene_scale = int(scene_scale_attempt)
                line_width = int(line_width_attempt)
                panel_title_font_size_px = int(panel_title_font_size_px_attempt)
                image = image_attempt
                background_meta = dict(background_meta_attempt)
                shape_style = shape_style_attempt
                rendered_scene = rendered_scene_attempt
                break
            except Exception as exc:
                last_error = exc
                continue

        if (
            rendered_scene is None
            or image is None
            or background_meta is None
            or shape_style is None
            or canvas_width is None
            or canvas_height is None
            or scene_scale is None
            or line_width is None
            or panel_title_font_size_px is None
        ):
            raise RuntimeError(f"failed to generate {self.task_id} projection-consistency instance") from last_error

        out_image = image
        if int(scene_scale) > 1:
            out_image = out_image.resize((int(canvas_width), int(canvas_height)), resample=Image.Resampling.LANCZOS)
        out_image, post_noise_meta = apply_post_image_noise(
            out_image,
            instance_seed=int(instance_seed),
            params=dict(params),
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        background_meta_final = dict(background_meta)
        background_meta_final["render_scale"] = int(scene_scale)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description_projection_consistency_label",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_option_letter",
                "annotation_hint_projection_consistency_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = build_prompt_json_examples(
            annotation_value=rendered_scene.annotation_bboxes,
            answer_type="option_letter",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(rendered_scene.consistency_query),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_projection_consistency_label"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_projection_consistency_label"]),
                "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="string", value=str(rendered_scene.answer_label))
        annotation_gt = TypedValue(type="bbox_set", value=list(rendered_scene.annotation_bboxes))
        query_params = {
            "query_id": PROJECTION_CONSISTENCY_QUERY,
            "consistency_query": str(rendered_scene.consistency_query),
            "consistency_query_probabilities": dict(consistency_query_probabilities),
            "query_id_probabilities": {PROJECTION_CONSISTENCY_QUERY: 1.0},
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "puzzles_spatial_cube_projection_consistency",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "query_id": PROJECTION_CONSISTENCY_QUERY,
                    "consistency_query": str(rendered_scene.consistency_query),
                    "visible_counts_by_query": dict(rendered_scene.visible_counts_by_query),
                    "answer_label": str(rendered_scene.answer_label),
                },
            },
            "query_spec": {
                "query_id": PROJECTION_CONSISTENCY_QUERY,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_width": int(canvas_width),
                "canvas_height": int(canvas_height),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "scene_scale": int(scene_scale),
                "line_width_px": int(line_width),
                "panel_title_font_size_px": int(panel_title_font_size_px),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "query_id": PROJECTION_CONSISTENCY_QUERY,
                "consistency_query": str(rendered_scene.consistency_query),
                "consistency_query_probabilities": dict(consistency_query_probabilities),
                "query_id_probabilities": {PROJECTION_CONSISTENCY_QUERY: 1.0},
                "cube_count": int(rendered_scene.reference_stack.cube_count),
                "stack_width": int(rendered_scene.reference_stack.width),
                "stack_depth": int(rendered_scene.reference_stack.depth),
                "stack_max_height": int(rendered_scene.reference_stack.max_height),
                "reference_stack_heights": [
                    {"x": int(x_value), "y": int(y_value), "height": int(height)}
                    for (x_value, y_value), height in sorted(rendered_scene.reference_stack.heights.items())
                ],
                "visible_counts_by_query": dict(rendered_scene.visible_counts_by_query),
                "answer_label": str(rendered_scene.answer_label),
                "option_count": int(rendered_scene.option_count),
                "question_format": str(rendered_scene.consistency_query),
            },
            "witness_symbolic": {
                "type": "option_label",
                "label": str(rendered_scene.answer_label),
                "consistency_query": str(rendered_scene.consistency_query),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "pixel_bbox_set": list(rendered_scene.annotation_bboxes),
                "selected_option_label": str(rendered_scene.answer_label),
                "selected_option_bbox": list(rendered_scene.annotation_bboxes[0]),
            },
        }
        complexity = _build_projection_consistency_complexity(
            consistency_query=str(rendered_scene.consistency_query),
            cube_count=int(rendered_scene.reference_stack.cube_count),
            max_height=int(rendered_scene.reference_stack.max_height),
            option_count=int(rendered_scene.option_count),
        )
        trace_payload["answer_gt"] = answer_gt.to_dict()
        trace_payload["annotation_gt"] = annotation_gt.to_dict()
        trace_payload["complexity"] = complexity.to_dict()

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=out_image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=PROJECTION_CONSISTENCY_QUERY,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = [
    "FRONT_VIEW_QUERY",
    "RIGHT_VIEW_QUERY",
    "TOP_VIEW_QUERY",
    "SolidViewCountGenerator",
    "SolidViewProjectionConsistencyGenerator",
    "SolidViewProjectionMatchGenerator",
    "_resolve_axes",
]
