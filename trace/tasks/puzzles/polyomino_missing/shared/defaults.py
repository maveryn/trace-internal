"""Default and axis resolution helpers for polyomino missing-piece puzzles."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.core.sampling import integer_range_choice, uniform_choice_with_probabilities
from trace.tasks.puzzles.shared.unit_size_jitter import (
    resolve_puzzle_unit_size_scale,
    scale_puzzle_px,
)
from trace.tasks.shared.config_defaults import (
    group_default,
    resolve_required_int_bounds,
)
from trace.tasks.shared.render_variation import resolve_render_int, resolve_render_rgb
from trace.tasks.shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant

from .state import (
    DEFAULTS,
    SCENE_VARIANTS,
    CustomRenderParams,
    PolyominoOptionRenderDefaults,
    PolyominoOptionRenderParams,
)


def resolve_axis_variant(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    instance_seed: int,
    supported: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_key: str,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one scene or style axis from explicit values or uniform weights."""

    rng = spawn_rng(int(instance_seed), str(namespace))
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=generation_defaults,
        supported_variants=tuple(str(value) for value in supported),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=generation_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=tuple(str(value) for value in supported),
        balance_flag_key=str(balance_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{str(namespace)}.balanced",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def resolve_scene_variant(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace_base: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the scene presentation variant."""

    return resolve_axis_variant(
        params=params,
        generation_defaults=generation_defaults,
        instance_seed=int(instance_seed),
        supported=SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_key="balanced_scene_variant_sampling",
        namespace=f"{str(namespace_base)}.scene_variant",
    )


def resolve_count_from_bounds(
    rng,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    context: str,
) -> Tuple[int, Tuple[int, int], Dict[str, float]]:
    """Sample one integer from an inclusive configured support using RNG."""

    lower, upper = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=str(context),
    )
    selected, probabilities = integer_range_choice(rng, int(lower), int(upper))
    return int(selected), (int(lower), int(upper)), dict(probabilities)


def resolve_option_count(
    rng,
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    context: str,
    choices_key: str | None = None,
) -> Tuple[int, Tuple[int, int], Dict[str, float]]:
    """Resolve the visible option count for one option-image task."""

    if choices_key is not None:
        raw_choices = params.get(
            str(choices_key),
            group_default(generation_defaults, str(choices_key), None),
        )
        if raw_choices is not None:
            support = tuple(sorted({int(value) for value in raw_choices}))
            if not support:
                raise ValueError(f"{choices_key} must contain at least one option count")
            explicit = params.get("option_count")
            if explicit is not None:
                selected = int(explicit)
                if selected not in set(support):
                    raise ValueError(f"unsupported {context}: {explicit}")
                return (
                    int(selected),
                    (int(min(support)), int(max(support))),
                    {str(value): (1.0 if int(value) == int(selected) else 0.0) for value in support},
                )
            selected, probabilities = uniform_choice_with_probabilities(
                rng,
                support,
                sort_keys=True,
            )
            return int(selected), (int(min(support)), int(max(support))), dict(probabilities)

    return resolve_count_from_bounds(
        rng,
        params=params,
        generation_defaults=generation_defaults,
        min_key=str(min_key),
        max_key=str(max_key),
        fallback_min=int(fallback_min),
        fallback_max=int(fallback_max),
        context=str(context),
    )


def resolve_answer_label(
    rng,
    *,
    labels: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Sample the correct option label from the visible option support."""

    return uniform_choice_with_probabilities(
        rng,
        tuple(str(label) for label in labels),
        sort_keys=False,
    )


def resolve_render_params(
    params: Mapping[str, Any],
    *,
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
):
    """Resolve the polyomino option-panel rendering parameters."""

    defaults = PolyominoOptionRenderDefaults()

    def _int(key: str, fallback: int) -> int:
        return int(
            resolve_render_int(
                params,
                rendering_defaults,
                str(key),
                int(fallback),
                instance_seed=int(instance_seed),
                namespace="polyomino_missing_render",
            )
        )

    def _rgb(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return tuple(
            int(value)
            for value in resolve_render_rgb(
                params,
                rendering_defaults,
                str(key),
                fallback,
                instance_seed=int(instance_seed),
                namespace="polyomino_missing_render",
            )
        )

    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        rendering_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.polyomino_missing.option_unit_size",
    )

    return PolyominoOptionRenderParams(
        canvas_width=_int("canvas_width", defaults.canvas_width),
        canvas_height=_int("canvas_height", defaults.canvas_height),
        scene_margin_left_px=_int(
            "scene_margin_left_px",
            defaults.scene_margin_left_px,
        ),
        scene_margin_right_px=_int(
            "scene_margin_right_px",
            defaults.scene_margin_right_px,
        ),
        scene_margin_top_px=_int(
            "scene_margin_top_px",
            defaults.scene_margin_top_px,
        ),
        scene_margin_bottom_px=_int(
            "scene_margin_bottom_px",
            defaults.scene_margin_bottom_px,
        ),
        piece_to_options_gap_px=scale_puzzle_px(
            _int("piece_to_options_gap_px", defaults.piece_to_options_gap_px),
            unit_scale,
            min_px=24,
        ),
        piece_panel_padding_px=scale_puzzle_px(
            _int("piece_panel_padding_px", defaults.piece_panel_padding_px),
            unit_scale,
            min_px=10,
        ),
        option_panel_width_px=_int(
            "option_panel_width_px",
            defaults.option_panel_width_px,
        ),
        option_panel_height_px=_int(
            "option_panel_height_px",
            defaults.option_panel_height_px,
        ),
        option_gap_px=scale_puzzle_px(
            _int("option_gap_px", defaults.option_gap_px),
            unit_scale,
            min_px=9,
        ),
        option_row_gap_px=scale_puzzle_px(
            _int("option_row_gap_px", defaults.option_row_gap_px),
            unit_scale,
            min_px=9,
        ),
        option_shape_box_size_px=scale_puzzle_px(
            _int("option_shape_box_size_px", defaults.option_shape_box_size_px),
            unit_scale,
            min_px=64,
        ),
        option_label_gap_px=scale_puzzle_px(
            _int("option_label_gap_px", defaults.option_label_gap_px),
            unit_scale,
            min_px=7,
        ),
        shape_cell_size_px=scale_puzzle_px(
            _int("shape_cell_size_px", defaults.shape_cell_size_px),
            unit_scale,
            min_px=10,
        ),
        shape_cell_gap_px=scale_puzzle_px(
            _int("shape_cell_gap_px", defaults.shape_cell_gap_px),
            unit_scale,
            min_px=1,
        ),
        panel_corner_radius_px=scale_puzzle_px(
            _int("panel_corner_radius_px", defaults.panel_corner_radius_px),
            unit_scale,
            min_px=9,
        ),
        cell_corner_radius_px=scale_puzzle_px(
            _int("cell_corner_radius_px", defaults.cell_corner_radius_px),
            unit_scale,
            min_px=3,
        ),
        border_width_px=scale_puzzle_px(
            _int("border_width_px", defaults.border_width_px),
            unit_scale,
            min_px=1,
        ),
        option_label_font_size_px=_int(
            "option_label_font_size_px",
            defaults.option_label_font_size_px,
        ),
        panel_fill_rgb=_rgb("panel_fill_rgb", (248, 249, 252)),
        option_panel_fill_rgb=_rgb("option_panel_fill_rgb", (251, 251, 255)),
        option_shape_fill_rgb=_rgb("option_shape_fill_rgb", (252, 252, 255)),
        shape_fill_rgb=_rgb("shape_fill_rgb", (66, 97, 148)),
        border_color_rgb=_rgb("border_color_rgb", (86, 94, 108)),
        text_color_rgb=_rgb("text_color_rgb", (30, 34, 40)),
        text_stroke_rgb=_rgb("text_stroke_rgb", (255, 255, 255)),
        unit_size_jitter=dict(unit_meta),
    )


def resolve_custom_render_params(
    params: Mapping[str, Any],
    *,
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
) -> CustomRenderParams:
    """Resolve target-grid rendering knobs not covered by option panels."""

    def _int(key: str, fallback: int) -> int:
        return int(
            resolve_render_int(
                params,
                rendering_defaults,
                str(key),
                int(fallback),
                instance_seed=int(instance_seed),
                namespace="polyomino_missing_render",
            )
        )

    def _rgb(key: str, fallback: Sequence[int]) -> Tuple[int, int, int]:
        return tuple(
            int(value)
            for value in resolve_render_rgb(
                params,
                rendering_defaults,
                str(key),
                fallback,
                instance_seed=int(instance_seed),
                namespace="polyomino_missing_render",
            )
        )

    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        rendering_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.polyomino_missing.unit_size",
    )
    return CustomRenderParams(
        board_cell_size_px=scale_puzzle_px(
            _int("board_cell_size_px", DEFAULTS.board_cell_size_px),
            unit_scale,
            min_px=16,
        ),
        board_cell_gap_px=scale_puzzle_px(
            _int("board_cell_gap_px", DEFAULTS.board_cell_gap_px),
            unit_scale,
            min_px=1,
        ),
        target_cell_size_px=scale_puzzle_px(
            _int("target_cell_size_px", DEFAULTS.target_cell_size_px),
            unit_scale,
            min_px=16,
        ),
        target_cell_gap_px=scale_puzzle_px(
            _int("target_cell_gap_px", DEFAULTS.target_cell_gap_px),
            unit_scale,
            min_px=2,
        ),
        unit_size_jitter=dict(unit_meta),
        highlight_fill_rgb=_rgb("highlight_fill_rgb", (255, 239, 164)),
        empty_cell_rgb=_rgb("empty_cell_rgb", (251, 252, 255)),
        board_grid_rgb=_rgb("board_grid_rgb", (92, 101, 116)),
        marked_cell_rgb=_rgb("marked_cell_rgb", (236, 96, 78)),
        target_cell_rgb=_rgb("target_cell_rgb", (207, 219, 236)),
        missing_cell_rgb=_rgb("missing_cell_rgb", (22, 24, 28)),
    )


def complement_generation_param_map(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Translate complement-prefixed config keys into generic local keys."""

    mapping = {
        "target_width_min": ("complement_target_width_min", DEFAULTS.complement_target_width_min),
        "target_width_max": ("complement_target_width_max", DEFAULTS.complement_target_width_max),
        "target_height_min": ("complement_target_height_min", DEFAULTS.complement_target_height_min),
        "target_height_max": ("complement_target_height_max", DEFAULTS.complement_target_height_max),
        "cutout_cell_count_min": (
            "complement_cutout_cell_count_min",
            DEFAULTS.complement_cutout_cell_count_min,
        ),
        "cutout_cell_count_max": (
            "complement_cutout_cell_count_max",
            DEFAULTS.complement_cutout_cell_count_max,
        ),
        "transform_allowed_cutout_cell_count_min": (
            "complement_transform_allowed_cutout_cell_count_min",
            DEFAULTS.complement_transform_allowed_cutout_cell_count_min,
        ),
        "shape_bbox_max_dim": (
            "complement_shape_bbox_max_dim",
            DEFAULTS.complement_shape_bbox_max_dim,
        ),
    }
    resolved = dict(params)
    for helper_key, (config_key, fallback) in mapping.items():
        if str(helper_key) in resolved:
            continue
        resolved[str(helper_key)] = params.get(str(config_key), fallback)
    return resolved


__all__ = [
    "complement_generation_param_map",
    "resolve_answer_label",
    "resolve_axis_variant",
    "resolve_count_from_bounds",
    "resolve_custom_render_params",
    "resolve_option_count",
    "resolve_render_params",
    "resolve_scene_variant",
]
