"""Identity-free semantic sampling primitives for dots-and-boxes scene tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.tasks.games.shared.layout import (
    attach_games_unit_size_jitter,
    resolve_games_layout_jitter,
    resolve_games_unit_size_scale,
    scale_games_px,
)
from trace.tasks.games.shared.style import SUPPORTED_DOTS_AND_BOXES_STYLE_VARIANTS
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.font_assets import sample_font_family
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support
from trace.tasks.shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant

from .defaults import (
    DEFAULTS,
    DOTS_AND_BOXES_NAMESPACE,
    SUPPORTED_DOTS_AND_BOXES_SCENE_VARIANTS,
)
from .rendering import DotsAndBoxesRenderParams
from .state import (
    DotsAndBoxesBoardShapeAxis,
    DotsAndBoxesIntegerAxis,
    DotsAndBoxesSceneAxes,
)


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one named scene or visual axis without public-task identity."""

    rng = spawn_rng(int(instance_seed), f"{DOTS_AND_BOXES_NAMESPACE}.{str(namespace)}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=[str(item) for item in supported],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(item) for item in supported],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{DOTS_AND_BOXES_NAMESPACE}.{str(namespace)}",
    )
    return str(selected), dict(probabilities)


def resolve_dots_and_boxes_scene_axes(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> DotsAndBoxesSceneAxes:
    """Resolve scene and style axes reused by dots-and-boxes tasks."""

    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_DOTS_AND_BOXES_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_DOTS_AND_BOXES_STYLE_VARIANTS,
    )
    return DotsAndBoxesSceneAxes(
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
    )


def resolve_dots_and_boxes_integer_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    namespace: str,
    balanced_flag_key: str,
) -> DotsAndBoxesIntegerAxis:
    """Resolve one task-owned integer axis."""

    support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key=str(support_key),
        fallback=tuple(int(value) for value in fallback_support),
    )
    value, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=str(support_key),
        explicit_key=str(explicit_key),
        fallback_support=support,
        namespace=f"{DOTS_AND_BOXES_NAMESPACE}.{str(namespace)}",
        balanced_flag_key=str(balanced_flag_key),
        namespace_support_permutation=True,
    )
    return DotsAndBoxesIntegerAxis(
        value=int(value),
        support=tuple(int(item) for item in support),
        probabilities=dict(probabilities),
    )


def resolve_dots_and_boxes_target_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    support_key: str,
    fallback_support: Sequence[int],
    namespace: str,
) -> DotsAndBoxesIntegerAxis:
    """Resolve one answer-count target axis."""

    return resolve_dots_and_boxes_integer_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=tuple(int(value) for value in fallback_support),
        namespace=str(namespace),
        balanced_flag_key="balanced_target_answer_sampling",
    )


def resolve_dots_and_boxes_candidate_edge_count_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> DotsAndBoxesIntegerAxis:
    """Resolve highlighted candidate-edge count for candidate-scope capture tasks."""

    return resolve_dots_and_boxes_integer_axis(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="candidate_edge_count_support",
        explicit_key="candidate_edge_count",
        fallback_support=DEFAULTS.candidate_edge_count_support,
        namespace="candidate_edge_count",
        balanced_flag_key="balanced_candidate_edge_count_sampling",
    )


def resolve_dots_and_boxes_board_shape_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> DotsAndBoxesBoardShapeAxis:
    """Resolve one rows/columns board shape from scene-level support."""

    rows_explicit = params.get("box_rows")
    cols_explicit = params.get("box_cols")
    if rows_explicit is not None or cols_explicit is not None or "box_rows" in gen_defaults or "box_cols" in gen_defaults:
        if rows_explicit is not None or "box_rows" in gen_defaults:
            box_rows = int(params.get("box_rows", group_default(gen_defaults, "box_rows", DEFAULTS.box_rows_support[0])))
        else:
            box_rows = resolve_dots_and_boxes_integer_axis(
                instance_seed=int(instance_seed),
                params=params,
                gen_defaults=gen_defaults,
                support_key="box_rows_support",
                explicit_key="box_rows",
                fallback_support=DEFAULTS.box_rows_support,
                namespace="box_rows",
                balanced_flag_key="balanced_board_shape_sampling",
            ).value
        if cols_explicit is not None or "box_cols" in gen_defaults:
            box_cols = int(params.get("box_cols", group_default(gen_defaults, "box_cols", DEFAULTS.box_cols_support[0])))
        else:
            box_cols = resolve_dots_and_boxes_integer_axis(
                instance_seed=int(instance_seed),
                params=params,
                gen_defaults=gen_defaults,
                support_key="box_cols_support",
                explicit_key="box_cols",
                fallback_support=DEFAULTS.box_cols_support,
                namespace="box_cols",
                balanced_flag_key="balanced_board_shape_sampling",
            ).value
        return DotsAndBoxesBoardShapeAxis(
            box_rows=int(box_rows),
            box_cols=int(box_cols),
            probabilities={f"{int(box_rows)}x{int(box_cols)}": 1.0},
        )

    row_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="box_rows_support",
        fallback=DEFAULTS.box_rows_support,
    )
    col_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="box_cols_support",
        fallback=DEFAULTS.box_cols_support,
    )
    shapes = tuple((int(row), int(col)) for row in row_support for col in col_support)
    if not shapes:
        raise ValueError("box_rows_support and box_cols_support must define at least one board shape")
    balanced_enabled = bool(params.get("balanced_board_shape_sampling", group_default(gen_defaults, "balanced_board_shape_sampling", True)))
    if bool(balanced_enabled):
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{DOTS_AND_BOXES_NAMESPACE}.board_shape",
        )
    else:
        selection_index = int(spawn_rng(int(instance_seed), f"{DOTS_AND_BOXES_NAMESPACE}.board_shape").randrange(len(shapes)))
    box_rows, box_cols = shapes[int(selection_index) % len(shapes)]
    probability = 1.0 / float(len(shapes))
    return DotsAndBoxesBoardShapeAxis(
        box_rows=int(box_rows),
        box_cols=int(box_cols),
        probabilities={f"{int(row)}x{int(col)}": float(probability) for row, col in shapes},
    )


def resolve_dots_and_boxes_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> DotsAndBoxesRenderParams:
    """Resolve stable render parameters for one dots-and-boxes scene."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{DOTS_AND_BOXES_NAMESPACE}.text_font",
        params=params,
    )
    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{DOTS_AND_BOXES_NAMESPACE}.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            render_defaults,
            instance_seed=int(instance_seed),
            namespace=f"{DOTS_AND_BOXES_NAMESPACE}.layout",
        ),
        unit_scale_meta,
    )
    base_canvas_width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", DEFAULTS.canvas_width)))
    base_canvas_height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", DEFAULTS.canvas_height)))
    board_width_px = scale_games_px(
        params.get("board_width_px", group_default(render_defaults, "board_width_px", DEFAULTS.board_width_px)),
        unit_scale,
        min_px=440,
    )
    board_height_px = scale_games_px(
        params.get("board_height_px", group_default(render_defaults, "board_height_px", DEFAULTS.board_height_px)),
        unit_scale,
        min_px=320,
    )
    dynamic_canvas_enabled = bool(
        params.get(
            "dynamic_canvas_size_enabled",
            group_default(render_defaults, "dynamic_canvas_size_enabled", DEFAULTS.dynamic_canvas_size_enabled),
        )
    )
    canvas_width = int(base_canvas_width)
    canvas_height = int(base_canvas_height)
    if dynamic_canvas_enabled and params.get("canvas_width") is None:
        canvas_width = min(
            int(base_canvas_width),
            max(
                int(params.get("canvas_min_width_px", group_default(render_defaults, "canvas_min_width_px", DEFAULTS.canvas_min_width_px))),
                int(
                    round(
                        float(board_width_px)
                        + (
                            2.0
                            * float(
                                params.get(
                                    "canvas_side_padding_px",
                                    group_default(render_defaults, "canvas_side_padding_px", DEFAULTS.canvas_side_padding_px),
                                )
                            )
                        )
                    )
                ),
            ),
        )
    if dynamic_canvas_enabled and params.get("canvas_height") is None:
        canvas_height = min(
            int(base_canvas_height),
            max(
                int(params.get("canvas_min_height_px", group_default(render_defaults, "canvas_min_height_px", DEFAULTS.canvas_min_height_px))),
                int(
                    round(
                        float(board_height_px)
                        + (
                            2.0
                            * float(
                                params.get(
                                    "canvas_vertical_padding_px",
                                    group_default(render_defaults, "canvas_vertical_padding_px", DEFAULTS.canvas_vertical_padding_px),
                                )
                            )
                        )
                    )
                ),
            ),
        )
    return DotsAndBoxesRenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        board_width_px=int(board_width_px),
        board_height_px=int(board_height_px),
        board_corner_radius_px=scale_games_px(
            params.get("board_corner_radius_px", group_default(render_defaults, "board_corner_radius_px", DEFAULTS.board_corner_radius_px)),
            unit_scale,
            min_px=10,
        ),
        panel_margin_px=scale_games_px(
            params.get("panel_margin_px", group_default(render_defaults, "panel_margin_px", DEFAULTS.panel_margin_px)),
            unit_scale,
            min_px=28,
        ),
        title_font_size_px=scale_games_px(
            params.get("title_font_size_px", group_default(render_defaults, "title_font_size_px", DEFAULTS.title_font_size_px)),
            unit_scale,
            min_px=18,
        ),
        title_band_height_px=scale_games_px(
            params.get("title_band_height_px", group_default(render_defaults, "title_band_height_px", DEFAULTS.title_band_height_px)),
            unit_scale,
            min_px=34,
        ),
        board_padding_px=scale_games_px(
            params.get("board_padding_px", group_default(render_defaults, "board_padding_px", DEFAULTS.board_padding_px)),
            unit_scale,
            min_px=31,
        ),
        dot_radius_px=scale_games_px(
            params.get("dot_radius_px", group_default(render_defaults, "dot_radius_px", DEFAULTS.dot_radius_px)),
            unit_scale,
            min_px=3,
        ),
        dash_length_px=scale_games_px(
            params.get("dash_length_px", group_default(render_defaults, "dash_length_px", DEFAULTS.dash_length_px)),
            unit_scale,
            min_px=14,
        ),
        dash_gap_px=scale_games_px(
            params.get("dash_gap_px", group_default(render_defaults, "dash_gap_px", DEFAULTS.dash_gap_px)),
            unit_scale,
            min_px=8,
        ),
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
    )


__all__ = [
    "resolve_dots_and_boxes_board_shape_axis",
    "resolve_dots_and_boxes_candidate_edge_count_axis",
    "resolve_dots_and_boxes_integer_axis",
    "resolve_dots_and_boxes_render_params",
    "resolve_dots_and_boxes_scene_axes",
    "resolve_dots_and_boxes_target_axis",
]
