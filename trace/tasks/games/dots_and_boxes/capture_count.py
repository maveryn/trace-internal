"""Games dots-and-boxes task for grounded board-state counting."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.fixed_query import normalize_query_id_params
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import build_games_dots_and_boxes_capture_complexity
from ..shared.dots_boxes_common import (
    SUPPORTED_DOTS_AND_BOXES_QUERY_IDS,
    SUPPORTED_DOTS_AND_BOXES_SCENE_VARIANTS,
    DotsAndBoxesBoardState,
    box_drawn_side_counts,
    build_dots_and_boxes_count_board_state,
    immediate_capture_edge_ids,
)
from ..shared.dots_boxes_scene import DotsAndBoxesRenderParams, render_dots_and_boxes_scene
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, QuerySubsetTaskMixin, forced_query_params, rewrite_fixed_query_output
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.style import SUPPORTED_DOTS_AND_BOXES_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_dots_and_boxes_capture_count_base"
_CAPTURE_MOVE_QUERY_IDS: Tuple[str, ...] = (
    "capture_move_count",
    "highlighted_candidate_capture_count",
)
_OWNED_BOX_QUERY_IDS: Tuple[str, ...] = (
    "player_a_owned_box_count",
    "player_b_owned_box_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible dots-and-boxes count scenes."""

    three_sided_box_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    capture_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    highlighted_candidate_capture_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    owned_box_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8)
    candidate_edge_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    box_rows_support: Tuple[int, ...] = (3, 4)
    box_cols_support: Tuple[int, ...] = (3, 4)
    canvas_width: int = 1180
    canvas_height: int = 820
    board_width_px: int = 880
    board_height_px: int = 640
    board_corner_radius_px: int = 24
    panel_margin_px: int = 56
    title_font_size_px: int = 34
    title_band_height_px: int = 62
    board_padding_px: int = 62
    dot_radius_px: int = 7
    dash_length_px: int = 30
    dash_gap_px: int = 18
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 620
    canvas_min_height_px: int = 520
    canvas_side_padding_px: int = 150
    canvas_vertical_padding_px: int = 110


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one dots-and-boxes scene."""

    query_id: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "dots_and_boxes")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="dots_and_boxes", apply_prob=0.0)


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced dots-and-boxes semantic variant."""

    alias_params = normalize_query_id_params(params)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_id")
    selected, probabilities = resolve_variant(
        rng,
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_DOTS_AND_BOXES_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_DOTS_AND_BOXES_QUERY_IDS,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_ID}.query_id",
    )
    return str(selected), dict(probabilities)


def _has_explicit_query_axis(params: Mapping[str, Any]) -> bool:
    """Return true when a caller forces one concrete internal query branch."""

    for key in ("query_id", "query_variant"):
        value = params.get(str(key))
        if value is not None and str(value).strip() and str(value) != "default":
            return True
    return False


def _resolve_public_capture_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve the internal capture-query branch for the merged public task."""

    allowed = tuple(str(value) for value in _CAPTURE_MOVE_QUERY_IDS)
    allowed_set = set(allowed)
    alias_params = dict(params)
    explicit_values = []
    for key in ("query_id", "query_variant"):
        value = alias_params.get(str(key))
        if value is not None and str(value).strip() and str(value) != "default":
            explicit_values.append(str(value))
    if len(set(explicit_values)) > 1:
        raise ValueError("query_id and query_variant must not disagree")
    if explicit_values:
        selected = str(explicit_values[0])
        if selected not in allowed_set:
            raise ValueError(f"unsupported capture-move query id: {selected}")
        alias_params["query_id"] = selected

    raw_weights = alias_params.get("capture_move_query_id_weights")
    if isinstance(raw_weights, Mapping):
        positive = {str(key) for key, value in raw_weights.items() if float(value) > 0.0}
        invalid = sorted(positive.difference(allowed_set))
        if invalid:
            raise ValueError(f"unsupported positive capture-move query weights: {invalid}")
    elif raw_weights is not None:
        raise ValueError("capture_move_query_id_weights must be a mapping when provided")

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.public_capture_query_id")
    selected, probabilities = resolve_variant(
        rng,
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=allowed,
        explicit_key="query_id",
        weights_key="capture_move_query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=allowed,
        balance_flag_key="balanced_capture_move_query_id_sampling",
        explicit_key="query_id",
        weights_key="capture_move_query_id_weights",
        sampling_namespace=f"{TASK_ID}.public_capture_query_id",
    )
    return str(selected), dict(probabilities)


def _params_for_public_capture_occurrence_cycle(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Advance secondary balanced axes by occurrence count inside the merged capture task."""

    if _has_explicit_query_axis(params) or params.get("_sample_cursor") is None:
        return dict(params)
    cycle_params = dict(params)
    cycle_params["_sample_cursor"] = abs(int(params["_sample_cursor"])) // max(1, len(_CAPTURE_MOVE_QUERY_IDS))
    return cycle_params


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named axis for the dots-and-boxes task."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported,
        explicit_key=explicit_key,
        weights_key=weights_key,
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=supported,
        balance_flag_key=balance_flag_key,
        explicit_key=explicit_key,
        weights_key=weights_key,
        sampling_namespace=f"{TASK_ID}.{namespace}",
    )
    return str(selected), dict(probabilities)


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_variant") is not None:
        return False
    enabled = bool(
        params.get(
            "balanced_query_id_sampling",
            group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True),
        )
    )
    if not enabled:
        return False
    raw_weights = params.get(
        "query_id_weights",
        group_default(_GEN_DEFAULTS, "query_id_weights", {key: 1.0 for key in SUPPORTED_DOTS_AND_BOXES_QUERY_IDS}),
    )
    if not isinstance(raw_weights, Mapping):
        return False
    positives = [
        str(value)
        for value in SUPPORTED_DOTS_AND_BOXES_QUERY_IDS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_DOTS_AND_BOXES_QUERY_IDS):
        return False
    positive_probs = [float(probabilities.get(str(value), 0.0)) for value in SUPPORTED_DOTS_AND_BOXES_QUERY_IDS]
    return max(positive_probs) - min(positive_probs) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Cycle secondary balanced axes by per-query occurrence index."""

    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return dict(params)
    cycle_params = dict(params)
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_DOTS_AND_BOXES_QUERY_IDS))
    return cycle_params


def _resolve_count_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Tuple[int, ...],
    namespace: str,
    balanced_flag_key: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve a small integer count support while preserving exact overrides."""

    return resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key=str(explicit_key),
        fallback_support=tuple(int(value) for value in fallback_support),
        namespace=f"{TASK_ID}.{namespace}",
        balanced_flag_key=str(balanced_flag_key),
        namespace_support_permutation=True,
    )


def _resolve_board_shape(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[int, int, Dict[str, float]]:
    """Resolve one rows/columns pair from the configured board shape support."""

    rows_explicit = params.get("box_rows")
    cols_explicit = params.get("box_cols")
    if rows_explicit is not None or cols_explicit is not None or "box_rows" in _GEN_DEFAULTS or "box_cols" in _GEN_DEFAULTS:
        if rows_explicit is not None or "box_rows" in _GEN_DEFAULTS:
            box_rows = int(params.get("box_rows", group_default(_GEN_DEFAULTS, "box_rows", _DEFAULTS.box_rows_support[0])))
        else:
            box_rows, _row_probs = _resolve_count_axis(
                instance_seed=int(instance_seed),
                params=params,
                support_key="box_rows_support",
                explicit_key="box_rows",
                fallback_support=_DEFAULTS.box_rows_support,
                namespace="box_rows",
                balanced_flag_key="balanced_board_shape_sampling",
            )
        if cols_explicit is not None or "box_cols" in _GEN_DEFAULTS:
            box_cols = int(params.get("box_cols", group_default(_GEN_DEFAULTS, "box_cols", _DEFAULTS.box_cols_support[0])))
        else:
            box_cols, _col_probs = _resolve_count_axis(
                instance_seed=int(instance_seed),
                params=params,
                support_key="box_cols_support",
                explicit_key="box_cols",
                fallback_support=_DEFAULTS.box_cols_support,
                namespace="box_cols",
                balanced_flag_key="balanced_board_shape_sampling",
            )
        return int(box_rows), int(box_cols), {f"{int(box_rows)}x{int(box_cols)}": 1.0}

    row_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="box_rows_support",
        fallback=_DEFAULTS.box_rows_support,
    )
    col_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="box_cols_support",
        fallback=_DEFAULTS.box_cols_support,
    )
    shapes = tuple((int(row), int(col)) for row in row_support for col in col_support)
    if not shapes:
        raise ValueError("box_rows_support and box_cols_support must define at least one board shape")
    balanced_enabled = bool(params.get("balanced_board_shape_sampling", group_default(_GEN_DEFAULTS, "balanced_board_shape_sampling", True)))
    if bool(balanced_enabled):
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.board_shape",
        )
    else:
        selection_index = int(spawn_rng(int(instance_seed), f"{TASK_ID}.board_shape").randrange(len(shapes)))
    box_rows, box_cols = shapes[int(selection_index) % len(shapes)]
    probability = 1.0 / float(len(shapes))
    return int(box_rows), int(box_cols), {f"{int(row)}x{int(col)}": float(probability) for row, col in shapes}


def _target_support_key(query_id: str) -> str:
    """Return the answer-support config key for one dots-and-boxes query id."""

    return {
        "three_sided_box_count": "three_sided_box_count_support",
        "capture_move_count": "capture_move_count_support",
        "highlighted_candidate_capture_count": "highlighted_candidate_capture_count_support",
        "player_a_owned_box_count": "owned_box_count_support",
        "player_b_owned_box_count": "owned_box_count_support",
    }[str(query_id)]


def _fallback_support(query_id: str) -> Tuple[int, ...]:
    """Return the fallback support for one dots-and-boxes query id."""

    return {
        "three_sided_box_count": _DEFAULTS.three_sided_box_count_support,
        "capture_move_count": _DEFAULTS.capture_move_count_support,
        "highlighted_candidate_capture_count": _DEFAULTS.highlighted_candidate_capture_count_support,
        "player_a_owned_box_count": _DEFAULTS.owned_box_count_support,
        "player_b_owned_box_count": _DEFAULTS.owned_box_count_support,
    }[str(query_id)]


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic/visual axes plus one target answer for the dots-and-boxes task."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_DOTS_AND_BOXES_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_params_for_query_occurrence_cycle(params, query_id_probabilities=query_id_probabilities),
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_DOTS_AND_BOXES_STYLE_VARIANTS,
    )
    target_support_key = _target_support_key(str(query_id))
    target_params = _params_for_query_occurrence_cycle(params, query_id_probabilities=query_id_probabilities)
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(target_support_key),
        explicit_key="target_answer",
        fallback_support=_fallback_support(str(query_id)),
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        target_params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(target_support_key),
        fallback=_fallback_support(str(query_id)),
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> DotsAndBoxesRenderParams:
    """Resolve stable render parameters for one dots-and-boxes scene."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.dots_and_boxes.text_font",
        params=params,
    )
    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.dots_and_boxes.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.dots_and_boxes.layout",
        ),
        unit_scale_meta,
    )
    base_canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
    base_canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
    board_width_px = scale_games_px(
        params.get("board_width_px", group_default(_RENDER_DEFAULTS, "board_width_px", _DEFAULTS.board_width_px)),
        unit_scale,
        min_px=440,
    )
    board_height_px = scale_games_px(
        params.get("board_height_px", group_default(_RENDER_DEFAULTS, "board_height_px", _DEFAULTS.board_height_px)),
        unit_scale,
        min_px=320,
    )
    dynamic_canvas_enabled = bool(
        params.get(
            "dynamic_canvas_size_enabled",
            group_default(_RENDER_DEFAULTS, "dynamic_canvas_size_enabled", _DEFAULTS.dynamic_canvas_size_enabled),
        )
    )
    canvas_width = int(base_canvas_width)
    canvas_height = int(base_canvas_height)
    if dynamic_canvas_enabled and params.get("canvas_width") is None:
        canvas_width = min(
            int(base_canvas_width),
            max(
                int(params.get("canvas_min_width_px", group_default(_RENDER_DEFAULTS, "canvas_min_width_px", _DEFAULTS.canvas_min_width_px))),
                int(
                    round(
                        float(board_width_px)
                        + (
                            2.0
                            * float(
                                params.get(
                                    "canvas_side_padding_px",
                                    group_default(_RENDER_DEFAULTS, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px),
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
                int(params.get("canvas_min_height_px", group_default(_RENDER_DEFAULTS, "canvas_min_height_px", _DEFAULTS.canvas_min_height_px))),
                int(
                    round(
                        float(board_height_px)
                        + (
                            2.0
                            * float(
                                params.get(
                                    "canvas_vertical_padding_px",
                                    group_default(_RENDER_DEFAULTS, "canvas_vertical_padding_px", _DEFAULTS.canvas_vertical_padding_px),
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
            params.get(
                "board_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px),
            ),
            unit_scale,
            min_px=10,
        ),
        panel_margin_px=scale_games_px(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px)), unit_scale, min_px=28),
        title_font_size_px=scale_games_px(
            params.get("title_font_size_px", group_default(_RENDER_DEFAULTS, "title_font_size_px", _DEFAULTS.title_font_size_px)),
            unit_scale,
            min_px=18,
        ),
        title_band_height_px=scale_games_px(
            params.get(
                "title_band_height_px",
                group_default(_RENDER_DEFAULTS, "title_band_height_px", _DEFAULTS.title_band_height_px),
            ),
            unit_scale,
            min_px=34,
        ),
        board_padding_px=scale_games_px(
            params.get("board_padding_px", group_default(_RENDER_DEFAULTS, "board_padding_px", _DEFAULTS.board_padding_px)),
            unit_scale,
            min_px=31,
        ),
        dot_radius_px=scale_games_px(params.get("dot_radius_px", group_default(_RENDER_DEFAULTS, "dot_radius_px", _DEFAULTS.dot_radius_px)), unit_scale, min_px=3),
        dash_length_px=scale_games_px(
            params.get("dash_length_px", group_default(_RENDER_DEFAULTS, "dash_length_px", _DEFAULTS.dash_length_px)),
            unit_scale,
            min_px=14,
        ),
        dash_gap_px=scale_games_px(params.get("dash_gap_px", group_default(_RENDER_DEFAULTS, "dash_gap_px", _DEFAULTS.dash_gap_px)), unit_scale, min_px=8),
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
    )


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return answer+annotation and answer-only JSON examples for the dots-and-boxes task."""

    answer_value = 2
    if str(query_id) in _CAPTURE_MOVE_QUERY_IDS:
        annotation_value = [
            [[180, 220], [300, 220]],
            [[310, 340], [430, 340]],
        ]
    else:
        annotation_value = [
            [180, 220, 300, 340],
            [310, 220, 430, 340],
        ]
    json_example = json.dumps(
        {
            "annotation": annotation_value,
            "answer": int(answer_value),
        },
        ensure_ascii=True,
    )
    json_example_answer_only = json.dumps({"answer": int(answer_value)}, ensure_ascii=True)
    return json_example, json_example_answer_only


def _annotation_ids_type_and_value(
    *,
    board_state: DotsAndBoxesBoardState,
    rendered_scene,
    query_id: str,
) -> Tuple[Tuple[str, ...], str, list[Any]]:
    """Return query-specific symbolic annotation ids, public type, and pixel value."""

    if str(query_id) == "three_sided_box_count" or str(query_id) in _OWNED_BOX_QUERY_IDS:
        annotation_ids = tuple(str(box_id) for box_id in board_state.counted_box_ids)
        return (
            annotation_ids,
            "bbox_set",
            [list(rendered_scene.render_map["box_bboxes_px"][str(box_id)]) for box_id in annotation_ids],
        )
    annotation_ids = tuple(str(edge_id) for edge_id in board_state.counted_edge_ids)
    return (
        annotation_ids,
        "point_pair_set",
        [
            [list(point) for point in rendered_scene.render_map["edge_point_pairs_px"][str(edge_id)]]
            for edge_id in annotation_ids
        ],
    )


class GamesDotsAndBoxesCaptureCountTask:
    """Return one grounded dots-and-boxes board-state count."""

    task_id = TASK_ID
    domain = "games"
    task_group = "dots_and_boxes"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))
        allowed_panel_treatments_raw = params.get(
            "panel_scene_treatments",
            group_default(_RENDER_DEFAULTS, "panel_scene_treatments", None),
        )
        if isinstance(allowed_panel_treatments_raw, str):
            allowed_panel_treatments = (str(allowed_panel_treatments_raw),)
        elif allowed_panel_treatments_raw is None:
            allowed_panel_treatments = None
        else:
            allowed_panel_treatments = tuple(str(item) for item in allowed_panel_treatments_raw)
        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.dots_and_boxes.panel_scene_style",
            treatments=allowed_panel_treatments,
            treatment_weights=params.get(
                "panel_scene_treatment_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_treatment_weights", None),
            ),
            palette_weights=params.get(
                "panel_scene_palette_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_palette_weights", None),
            ),
        )
        count_params = _params_for_query_occurrence_cycle(params, query_id_probabilities=axes.query_id_probabilities)
        box_rows, box_cols, board_shape_probabilities = _resolve_board_shape(
            int(instance_seed),
            params=count_params,
        )
        candidate_edge_count, candidate_edge_count_probabilities = _resolve_count_axis(
            instance_seed=int(instance_seed),
            params=count_params,
            support_key="candidate_edge_count_support",
            explicit_key="candidate_edge_count",
            fallback_support=_DEFAULTS.candidate_edge_count_support,
            namespace="candidate_edge_count",
            balanced_flag_key="balanced_candidate_edge_count_sampling",
        )

        board_state: DotsAndBoxesBoardState | None = None
        rendered_scene = None
        background_meta: Dict[str, Any] | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            board_state = build_dots_and_boxes_count_board_state(
                rng=attempt_rng,
                query_id=str(axes.query_id),
                target_answer=int(axes.target_answer),
                box_rows=int(box_rows),
                box_cols=int(box_cols),
                candidate_edge_count=int(candidate_edge_count),
            )
            background, background_meta = make_panel_scene_background(
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
                style=panel_style,
            )
            rendered_scene = render_dots_and_boxes_scene(
                board_state=board_state,
                background=background,
                scene_variant=str(axes.scene_variant),
                style_variant=str(axes.style_variant),
                params=render_params,
                panel_style=panel_style,
            )
            break

        if board_state is None or rendered_scene is None or background_meta is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        annotation_ids, annotation_type, annotation_value = _annotation_ids_type_and_value(
            board_state=board_state,
            rendered_scene=rendered_scene,
            query_id=str(axes.query_id),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_single_board",
                f"answer_hint_{str(axes.query_id)}",
                f"annotation_hint_{str(axes.query_id)}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_single_board"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        annotation_gt = TypedValue(type=str(annotation_type), value=list(annotation_value))
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }
        complexity = build_games_dots_and_boxes_capture_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            query_id=str(axes.query_id),
            box_rows=int(board_state.box_rows),
            box_cols=int(board_state.box_cols),
            drawn_edge_count=len(board_state.drawn_edge_ids),
            target_answer=int(axes.target_answer),
            path_turn_count=int(board_state.path_turn_count),
            annotation_count=len(annotation_ids),
        )

        box_edge_map = {str(box.box_id): tuple(str(edge_id) for edge_id in box.edge_ids) for box in board_state.boxes}
        side_counts = box_drawn_side_counts(
            drawn_edge_ids=tuple(str(edge_id) for edge_id in board_state.drawn_edge_ids),
            box_edges=box_edge_map,
        )
        immediate_edges = immediate_capture_edge_ids(
            drawn_edge_ids=tuple(str(edge_id) for edge_id in board_state.drawn_edge_ids),
            box_edges=box_edge_map,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_dots_and_boxes_single_board",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "target_answer": int(axes.target_answer),
                    "annotation_entity_ids": list(annotation_ids),
                    "box_rows": int(board_state.box_rows),
                    "box_cols": int(board_state.box_cols),
                    "candidate_edge_count": int(candidate_edge_count),
                    "highlighted_edge_id": str(board_state.highlighted_edge_id),
                    "highlighted_edge_ids": [str(edge_id) for edge_id in board_state.highlighted_edge_ids],
                },
            },
            "query_spec": {
                "query_id": str(axes.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "box_rows": int(board_state.box_rows),
                    "box_cols": int(board_state.box_cols),
                    "board_shape_probabilities": dict(board_shape_probabilities),
                    "candidate_edge_count": int(candidate_edge_count),
                    "candidate_edge_count_probabilities": dict(candidate_edge_count_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "box_rows": int(board_state.box_rows),
                "box_cols": int(board_state.box_cols),
                "candidate_edge_count": int(candidate_edge_count),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "box_rows": int(board_state.box_rows),
                "box_cols": int(board_state.box_cols),
                "candidate_edge_count": int(candidate_edge_count),
                "highlighted_edge_id": str(board_state.highlighted_edge_id),
                "highlighted_edge_ids": [str(edge_id) for edge_id in board_state.highlighted_edge_ids],
                "drawn_edge_ids": [str(edge_id) for edge_id in board_state.drawn_edge_ids],
                "captured_box_ids": [str(box_id) for box_id in board_state.captured_box_ids],
                "counted_box_ids": [str(box_id) for box_id in board_state.counted_box_ids],
                "counted_edge_ids": [str(edge_id) for edge_id in board_state.counted_edge_ids],
                "candidate_edge_ids": [str(edge_id) for edge_id in board_state.candidate_edge_ids],
                "box_owner_by_id": dict(rendered_scene.render_map.get("box_owner_by_id", {})),
                "immediate_capture_edge_ids": [str(edge_id) for edge_id in immediate_edges],
                "box_drawn_side_counts": {str(box_id): int(count) for box_id, count in sorted(side_counts.items())},
                "path_box_ids": [str(box_id) for box_id in board_state.path_box_ids],
                "move_edge_sequence": [str(edge_id) for edge_id in board_state.move_edge_sequence],
                "branching_edge_ids": [str(edge_id) for edge_id in board_state.branching_edge_ids],
                "path_turn_count": int(board_state.path_turn_count),
                "edge_specs": [
                    {
                        "edge_id": str(edge.edge_id),
                        "orientation": str(edge.orientation),
                        "dot_start": [int(value) for value in edge.dot_start],
                        "dot_end": [int(value) for value in edge.dot_end],
                        "is_drawn": bool(edge.is_drawn),
                        "is_highlighted": bool(edge.is_highlighted),
                    }
                    for edge in board_state.edges
                ],
                "box_specs": [
                    {
                        "box_id": str(box.box_id),
                        "row_index": int(box.row_index),
                        "column_index": int(box.column_index),
                        "edge_ids": [str(edge_id) for edge_id in box.edge_ids],
                    }
                    for box in board_state.boxes
                ],
                "annotation_entity_ids": [str(box_id) for box_id in annotation_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(box_id) for box_id in annotation_ids],
            },
            "projected_annotation": (
                {
                    "type": "bbox_set",
                    "bbox_set": [list(bbox) for bbox in annotation_value],
                    "pixel_bbox_set": [list(bbox) for bbox in annotation_value],
                }
                if str(annotation_type) == "bbox_set"
                else {
                    "type": "point_pair_set",
                    "point_pair_set": [[list(point) for point in pair] for pair in annotation_value],
                }
            ),
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_id=str(axes.query_id),
            scene_id="dots_and_boxes",
        )


@register_task
class GamesDotsAndBoxesThreeSidedBoxCountTask(FixedQueryVariantTaskMixin, GamesDotsAndBoxesCaptureCountTask):
    """Count boxes that currently have exactly three drawn sides."""

    task_id = "task_games__dots_and_boxes__three_sided_box_count"
    fixed_query_id = "three_sided_box_count"


@register_task
class GamesDotsAndBoxesCaptureMoveCountTask(GamesDotsAndBoxesCaptureCountTask):
    """Count missing-edge or highlighted-candidate moves that would complete a box."""

    task_id = "task_games__dots_and_boxes__capture_move_count"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities = _resolve_public_capture_query_id(
            instance_seed=int(instance_seed),
            params=params,
        )
        occurrence_params = _params_for_public_capture_occurrence_cycle(params)
        output = super().generate(
            int(instance_seed),
            params=forced_query_params(occurrence_params, query_id=str(query_id)),
            max_attempts=int(max_attempts),
        )
        return rewrite_fixed_query_output(
            output,
            query_id=str(query_id),
            query_id_probabilities=query_probabilities,
        )


@register_task
class GamesDotsAndBoxesOwnedBoxCountTask(QuerySubsetTaskMixin, GamesDotsAndBoxesCaptureCountTask):
    """Count completed boxes owned by one player marker."""

    task_id = "task_games__dots_and_boxes__owned_box_count"
    supported_query_ids = _OWNED_BOX_QUERY_IDS


__all__ = [
    "GamesDotsAndBoxesCaptureMoveCountTask",
    "GamesDotsAndBoxesOwnedBoxCountTask",
    "GamesDotsAndBoxesThreeSidedBoxCountTask",
]
