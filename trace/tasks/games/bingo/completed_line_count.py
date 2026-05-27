"""Games bingo task for grounded completed-line counting queries."""

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
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.bingo_common import (
    SUPPORTED_BINGO_EXTREMA,
    SUPPORTED_BINGO_LINE_AXES,
    SUPPORTED_BINGO_QUERY_IDS,
    SUPPORTED_BINGO_SCENE_VARIANTS,
    BingoCardState,
    build_bingo_card_state,
    evidence_cell_ids_for_query,
)
from ..shared.bingo_scene import (
    SUPPORTED_BINGO_CELL_FILL_PATTERNS,
    SUPPORTED_BINGO_MARK_SHAPES,
    BingoRenderParams,
    render_bingo_card_scene,
)
from ..shared.complexity import build_games_bingo_completed_line_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.style import SUPPORTED_BINGO_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_bingo_completed_line_count_base"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible bingo-card scenes."""

    completed_axis_line_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    line_sum_completed_line_count_support: Tuple[int, ...] = (2, 3, 4, 5)
    balanced_target_answer_within_line_axis: bool = False
    axis_distractor_mark_prob: float = 0.45
    line_sum_distractor_mark_prob: float = 0.20
    canvas_width: int = 1180
    canvas_height: int = 760
    card_width_px: int = 760
    card_height_px: int = 620
    card_corner_radius_px: int = 24
    panel_margin_px: int = 56
    title_font_size_px: int = 34
    title_band_height_px: int = 62
    header_font_size_px: int = 28
    header_height_px: int = 42
    grid_gap_px: int = 18
    number_font_size_px: int = 28
    cell_corner_radius_px: int = 14
    cell_gap_px: int = 10
    mark_inset_px: int = 12
    mark_shape: str = "ellipse"
    cell_fill_pattern: str = "solid"


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one bingo-card scene."""

    query_id: str
    line_axis: str | None
    extremum: str | None
    scene_variant: str
    style_variant: str
    mark_shape: str
    cell_fill_pattern: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    line_axis_probabilities: Dict[str, float]
    extremum_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    mark_shape_probabilities: Dict[str, float]
    cell_fill_pattern_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "bingo")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="bingo", apply_prob=0.0)

_SOURCE_QUERY_ID_LINE_AXES: Dict[str, str] = {
    "completed_row_count": "row",
    "completed_column_count": "column",
}


def _params_with_source_query_aliases(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Map old row/column query ids to the canonical axis query plus `line_axis`."""

    alias_params = dict(params)
    explicit_query = alias_params.get("query_id")
    if explicit_query is None and alias_params.get("query_id") is not None:
        explicit_query = alias_params.get("query_id")
        alias_params["query_id"] = explicit_query
    if explicit_query is None:
        return alias_params
    source_axis = _SOURCE_QUERY_ID_LINE_AXES.get(str(explicit_query))
    if source_axis is None:
        return alias_params
    explicit_axis = alias_params.get("line_axis")
    if explicit_axis is not None and str(explicit_axis) != str(source_axis):
        raise ValueError(f"conflicting line_axis={explicit_axis!r} for source query_id={explicit_query!r}")
    alias_params["query_id"] = "completed_axis_line_count"
    alias_params["line_axis"] = str(source_axis)
    return alias_params


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query id, honoring `query_id` as an alias."""

    alias_params = _params_with_source_query_aliases(params)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_id")
    selected, probabilities = resolve_variant(
        rng,
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_BINGO_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_BINGO_QUERY_IDS,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_ID}.query_id",
    )
    return str(selected), dict(probabilities)


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    normalized_params = _params_with_source_query_aliases(params)
    if normalized_params.get("query_id") is not None or normalized_params.get("query_id") is not None:
        return False
    enabled = bool(
        normalized_params.get(
            "balanced_query_id_sampling",
            group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True),
        )
    )
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_BINGO_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for axes balanced below the query cycle."""

    cycle_params = _params_with_source_query_aliases(params)
    sampling_index = cycle_params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(cycle_params, query_id_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_BINGO_QUERY_IDS))
    return cycle_params


def _uses_uniform_line_axis_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when line-axis cycling is enabled and uniformly balanced."""

    if params.get("line_axis") is not None:
        return False
    enabled = bool(
        params.get(
            "balanced_line_axis_sampling",
            group_default(_GEN_DEFAULTS, "balanced_line_axis_sampling", True),
        )
    )
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_BINGO_LINE_AXES):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_line_axis_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    line_axis_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-line-axis occurrence index below the query cycle."""

    cycle_params = dict(params)
    sampling_index = cycle_params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_line_axis_cycle(cycle_params, line_axis_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_BINGO_LINE_AXES))
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
    """Resolve one balanced named axis for the bingo task."""

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


def _target_support_key(query_id: str) -> str:
    """Return the configured target-support key for one bingo query id."""

    return {
        "completed_axis_line_count": "completed_axis_line_count_support",
        "line_sum_extremum_value": "line_sum_completed_line_count_support",
    }[str(query_id)]


def _cross_line_axis_target_cycle(
    params: Mapping[str, Any],
    *,
    target_answer_support: Tuple[int, ...],
) -> int | None:
    """Return an answer cycle that is balanced across alternating row/column axes."""

    sampling_index = params.get("_sample_cursor")
    if sampling_index is None or len(target_answer_support) % 2 != 0:
        return None
    block = tuple(int(value) for value in target_answer_support) + tuple(
        int(value) for value in reversed(target_answer_support)
    )
    return int(block[abs(int(sampling_index)) % len(block)])


def _configured_target_answer_cycle(
    params: Mapping[str, Any],
    *,
    target_support_key: str,
    target_answer_support: Tuple[int, ...],
) -> Tuple[int, Dict[str, float]] | None:
    """Return a configured target-answer cycle and its empirical probabilities."""

    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return None
    cycle_base_key = str(target_support_key).removesuffix("_support")
    cycle_key = f"{cycle_base_key}_balanced_cycle"
    raw_cycle = params.get(str(cycle_key), group_default(_GEN_DEFAULTS, str(cycle_key), ()))
    if not raw_cycle:
        return None
    support = set(int(value) for value in target_answer_support)
    cycle = tuple(int(value) for value in raw_cycle)
    unsupported = sorted({int(value) for value in cycle if int(value) not in support})
    if unsupported:
        raise ValueError(f"{cycle_key} contains unsupported target answers: {unsupported}")
    if not cycle:
        raise ValueError(f"{cycle_key} must contain at least one target answer")
    counts: Dict[str, int] = {}
    for value in cycle:
        counts[str(int(value))] = int(counts.get(str(int(value)), 0)) + 1
    total = float(len(cycle))
    probabilities = {
        str(int(value)): float(counts.get(str(int(value)), 0)) / total
        for value in target_answer_support
    }
    selected = int(cycle[abs(int(sampling_index)) % len(cycle)])
    return int(selected), probabilities


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic/visual axes plus one target answer for the bingo task."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
    )
    line_axis = None
    line_axis_probabilities: Dict[str, float] = {}
    if str(query_id) in {"completed_axis_line_count", "line_sum_extremum_value"}:
        line_axis, line_axis_probabilities = _resolve_named_axis(
            instance_seed=int(instance_seed),
            params=_params_for_query_occurrence_cycle(
                params,
                query_id_probabilities=query_id_probabilities,
            ),
            namespace="line_axis",
            explicit_key="line_axis",
            weights_key="line_axis_weights",
            balance_flag_key="balanced_line_axis_sampling",
            supported=SUPPORTED_BINGO_LINE_AXES,
        )
    extremum = None
    extremum_probabilities: Dict[str, float] = {}
    if str(query_id) == "line_sum_extremum_value":
        extremum, extremum_probabilities = _resolve_named_axis(
            instance_seed=int(instance_seed),
            params=_params_for_query_occurrence_cycle(
                params,
                query_id_probabilities=query_id_probabilities,
            ),
            namespace="extremum",
            explicit_key="extremum",
            weights_key="extremum_weights",
            balance_flag_key="balanced_extremum_sampling",
            supported=SUPPORTED_BINGO_EXTREMA,
        )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_BINGO_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_BINGO_STYLE_VARIANTS,
    )
    mark_shape, mark_shape_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="mark_shape",
        explicit_key="mark_shape",
        weights_key="mark_shape_weights",
        balance_flag_key="balanced_mark_shape_sampling",
        supported=SUPPORTED_BINGO_MARK_SHAPES,
    )
    cell_fill_pattern, cell_fill_pattern_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="cell_fill_pattern",
        explicit_key="cell_fill_pattern",
        weights_key="cell_fill_pattern_weights",
        balance_flag_key="balanced_cell_fill_pattern_sampling",
        supported=SUPPORTED_BINGO_CELL_FILL_PATTERNS,
    )

    target_support_key = _target_support_key(str(query_id))
    target_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    )
    if str(query_id) == "line_sum_extremum_value" and target_params.get("completed_line_count_target") is not None:
        target_params = dict(target_params)
        target_params["target_answer"] = int(target_params["completed_line_count_target"])
    balance_target_within_line_axis = bool(
        params.get(
            "balanced_target_answer_within_line_axis",
            group_default(_GEN_DEFAULTS, "balanced_target_answer_within_line_axis", _DEFAULTS.balanced_target_answer_within_line_axis),
        )
    )
    if str(query_id) in {"completed_axis_line_count", "line_sum_extremum_value"} and bool(balance_target_within_line_axis):
        target_params = _params_for_line_axis_occurrence_cycle(
            target_params,
            line_axis_probabilities=line_axis_probabilities,
        )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(target_support_key),
        fallback=getattr(_DEFAULTS, target_support_key),
    )
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(target_support_key),
        explicit_key="target_answer",
        fallback_support=getattr(_DEFAULTS, target_support_key),
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    configured_cycle = _configured_target_answer_cycle(
        target_params,
        target_support_key=str(target_support_key),
        target_answer_support=tuple(int(value) for value in target_answer_support),
    )
    if params.get("target_answer") is None and configured_cycle is not None:
        target_answer, target_answer_probabilities = configured_cycle
    elif (
        str(query_id) == "completed_axis_line_count"
        and not bool(balance_target_within_line_axis)
        and params.get("target_answer") is None
    ):
        cycled_answer = _cross_line_axis_target_cycle(
            target_params,
            target_answer_support=tuple(int(value) for value in target_answer_support),
        )
        if cycled_answer is not None:
            target_answer = int(cycled_answer)
    return _ResolvedAxes(
        query_id=str(query_id),
        line_axis=str(line_axis) if line_axis is not None else None,
        extremum=str(extremum) if extremum is not None else None,
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        mark_shape=str(mark_shape),
        cell_fill_pattern=str(cell_fill_pattern),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        line_axis_probabilities=dict(line_axis_probabilities),
        extremum_probabilities=dict(extremum_probabilities),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        mark_shape_probabilities=dict(mark_shape_probabilities),
        cell_fill_pattern_probabilities=dict(cell_fill_pattern_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    mark_shape: str,
    cell_fill_pattern: str,
) -> BingoRenderParams:
    """Resolve stable render parameters for one bingo scene."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.bingo.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.bingo.layout",
        ),
        unit_scale_meta,
    )
    return BingoRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        card_width_px=scale_games_px(params.get("card_width_px", group_default(_RENDER_DEFAULTS, "card_width_px", _DEFAULTS.card_width_px)), unit_scale, min_px=380),
        card_height_px=scale_games_px(params.get("card_height_px", group_default(_RENDER_DEFAULTS, "card_height_px", _DEFAULTS.card_height_px)), unit_scale, min_px=310),
        card_corner_radius_px=scale_games_px(
            params.get(
                "card_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "card_corner_radius_px", _DEFAULTS.card_corner_radius_px),
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
        header_font_size_px=scale_games_px(
            params.get(
                "header_font_size_px",
                group_default(_RENDER_DEFAULTS, "header_font_size_px", _DEFAULTS.header_font_size_px),
            ),
            unit_scale,
            min_px=15,
        ),
        header_height_px=scale_games_px(
            params.get("header_height_px", group_default(_RENDER_DEFAULTS, "header_height_px", _DEFAULTS.header_height_px)),
            unit_scale,
            min_px=24,
        ),
        grid_gap_px=scale_games_px(params.get("grid_gap_px", group_default(_RENDER_DEFAULTS, "grid_gap_px", _DEFAULTS.grid_gap_px)), unit_scale, min_px=8),
        number_font_size_px=scale_games_px(
            params.get(
                "number_font_size_px",
                group_default(_RENDER_DEFAULTS, "number_font_size_px", _DEFAULTS.number_font_size_px),
            ),
            unit_scale,
            min_px=15,
        ),
        cell_corner_radius_px=scale_games_px(
            params.get(
                "cell_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "cell_corner_radius_px", _DEFAULTS.cell_corner_radius_px),
            ),
            unit_scale,
            min_px=6,
        ),
        cell_gap_px=scale_games_px(params.get("cell_gap_px", group_default(_RENDER_DEFAULTS, "cell_gap_px", _DEFAULTS.cell_gap_px)), unit_scale, min_px=4),
        mark_inset_px=scale_games_px(params.get("mark_inset_px", group_default(_RENDER_DEFAULTS, "mark_inset_px", _DEFAULTS.mark_inset_px)), unit_scale, min_px=5),
        mark_shape=str(mark_shape or params.get("mark_shape", group_default(_RENDER_DEFAULTS, "mark_shape", _DEFAULTS.mark_shape))),
        cell_fill_pattern=str(
            cell_fill_pattern
            or params.get(
                "cell_fill_pattern",
                group_default(_RENDER_DEFAULTS, "cell_fill_pattern", _DEFAULTS.cell_fill_pattern),
            )
        ),
        layout_jitter_meta=layout_jitter,
    )


def _build_prompt_json_examples(*, query_id: str) -> Tuple[str, str]:
    """Return answer+evidence and answer-only JSON examples for the bingo task."""

    if str(query_id) == "line_sum_extremum_value":
        json_example = json.dumps(
            {
                "evidence": [
                    [120, 220, 220, 320],
                    [230, 220, 330, 320],
                    [340, 220, 440, 320],
                    [450, 220, 550, 320],
                    [560, 220, 660, 320],
                ],
                "answer": 184,
            },
            ensure_ascii=True,
        )
        json_example_answer_only = json.dumps({"answer": 184}, ensure_ascii=True)
        return json_example, json_example_answer_only

    sample_answer = 2
    json_example = json.dumps(
        {
            "evidence": [
                [120, 220, 220, 320],
                [230, 220, 330, 320],
            ],
            "answer": int(sample_answer),
        },
        ensure_ascii=True,
    )
    json_example_answer_only = json.dumps({"answer": int(sample_answer)}, ensure_ascii=True)
    return json_example, json_example_answer_only


class GamesBingoCompletedLineCountTask:
    """Return one grounded completed-line count over a visible bingo card."""

    task_id = TASK_ID
    domain = "games"
    task_group = "bingo"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(
            params,
            instance_seed=int(instance_seed),
            mark_shape=str(axes.mark_shape),
            cell_fill_pattern=str(axes.cell_fill_pattern),
        )
        axis_distractor_mark_prob = float(
            params.get(
                "axis_distractor_mark_prob",
                group_default(_GEN_DEFAULTS, "axis_distractor_mark_prob", _DEFAULTS.axis_distractor_mark_prob),
            )
        )
        line_sum_distractor_mark_prob = float(
            params.get(
                "line_sum_distractor_mark_prob",
                group_default(
                    _GEN_DEFAULTS,
                    "line_sum_distractor_mark_prob",
                    _DEFAULTS.line_sum_distractor_mark_prob,
                ),
            )
        )

        sampled_card: BingoCardState | None = None
        rendered_scene = None
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
            namespace="games.bingo_board.panel_scene_style",
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
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )

        last_generation_error: ValueError | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            if str(axes.query_id) == "line_sum_extremum_value":
                distractor_mark_prob = float(line_sum_distractor_mark_prob)
            else:
                distractor_mark_prob = float(axis_distractor_mark_prob)
            try:
                sampled_card = build_bingo_card_state(
                    rng=attempt_rng,
                    query_id=str(axes.query_id),
                    line_axis=axes.line_axis,
                    extremum=axes.extremum,
                    target_answer=int(axes.target_answer),
                    distractor_mark_prob=float(distractor_mark_prob),
                )
            except ValueError as exc:
                last_generation_error = exc
                continue
            rendered_scene = render_bingo_card_scene(
                cells=list(sampled_card.cells),
                background=background,
                scene_variant=str(axes.scene_variant),
                style_variant=str(axes.style_variant),
                params=render_params,
                panel_style=panel_style,
            )
            break

        if sampled_card is None or rendered_scene is None or background_meta is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts") from last_generation_error

        evidence_cell_ids = evidence_cell_ids_for_query(
            card_state=sampled_card,
            query_id=str(axes.query_id),
            line_axis=axes.line_axis,
        )
        evidence_bboxes = [
            list(rendered_scene.render_map["cell_bboxes_px"][str(cell_id)])
            for cell_id in evidence_cell_ids
        ]
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
                "object_description_single_card",
                "completed_axis_rule_text",
                "line_sum_extremum_rule_text",
                "answer_hint_completed_axis_line_count",
                "answer_hint_line_sum_extremum_value",
                "evidence_hint_completed_axis_line_count",
                "evidence_hint_line_sum_extremum_value",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_id=str(axes.query_id))
        extremum_text = "maximum" if str(axes.extremum or "max") == "max" else "minimum"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_single_card"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]).format(
                    line_axis=str(axes.line_axis or "row"),
                    extremum=str(extremum_text),
                ),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]).format(
                    line_axis=str(axes.line_axis or "row"),
                    extremum=str(extremum_text),
                ),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "line_axis": str(axes.line_axis or "row"),
                "extremum": str(extremum_text),
                "completed_axis_rule_text": str(prompt_defaults["completed_axis_rule_text"]).format(
                    line_axis=str(axes.line_axis or "row")
                ),
                "line_sum_extremum_rule_text": str(prompt_defaults["line_sum_extremum_rule_text"]).format(
                    line_axis=str(axes.line_axis or "row"),
                    extremum=str(extremum_text),
                ),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        if str(axes.query_id) == "line_sum_extremum_value" and sampled_card.line_sum_target_value is not None:
            answer_value = int(sampled_card.line_sum_target_value)
        else:
            answer_value = int(axes.target_answer)
        answer_gt = TypedValue(type="integer", value=int(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        marked_cell_count = sum(1 for cell in sampled_card.cells if bool(cell.is_marked))
        complexity = build_games_bingo_completed_line_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            query_id=str(axes.query_id),
            marked_cell_count=int(marked_cell_count),
            target_answer=(
                int(answer_value)
                if str(axes.query_id) == "line_sum_extremum_value"
                else int(axes.target_answer)
            ),
            evidence_count=len(evidence_cell_ids),
        )
        target_answer_support_for_trace = (
            []
            if str(axes.query_id) == "line_sum_extremum_value"
            else [int(value) for value in axes.target_answer_support]
        )
        target_answer_probabilities_for_trace = (
            {}
            if str(axes.query_id) == "line_sum_extremum_value"
            else dict(axes.target_answer_probabilities)
        )
        completed_line_count_target = (
            int(axes.target_answer)
            if str(axes.query_id) == "line_sum_extremum_value"
            else None
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_bingo_single_card",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "line_axis": axes.line_axis,
                    "extremum": axes.extremum,
                    "style_variant": str(axes.style_variant),
                    "mark_shape": str(render_params.mark_shape),
                    "cell_fill_pattern": str(render_params.cell_fill_pattern),
                    "target_answer": int(answer_value),
                    "completed_line_count_target": completed_line_count_target,
                    "axis_distractor_mark_prob": float(axis_distractor_mark_prob),
                    "line_sum_distractor_mark_prob": float(line_sum_distractor_mark_prob),
                    "line_sum_extremum": sampled_card.line_sum_extremum,
                    "line_sum_target_axis": sampled_card.line_sum_target_axis,
                    "line_sum_target_line_index": sampled_card.line_sum_target_line_index,
                    "line_sum_target_cell_ids": list(sampled_card.line_sum_target_cell_ids),
                    "line_sum_target_value": sampled_card.line_sum_target_value,
                    "completed_line_sums": [
                        {
                            "axis": str(axis_name),
                            "line_index": int(line_index),
                            "sum": int(value),
                        }
                        for axis_name, line_index, value in sampled_card.completed_line_sums
                    ],
                    "evidence_entity_ids": list(evidence_cell_ids),
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
                    "line_axis": axes.line_axis,
                    "extremum": axes.extremum,
                    "style_variant": str(axes.style_variant),
                    "mark_shape": str(render_params.mark_shape),
                    "cell_fill_pattern": str(render_params.cell_fill_pattern),
                    "axis_distractor_mark_prob": float(axis_distractor_mark_prob),
                    "line_sum_distractor_mark_prob": float(line_sum_distractor_mark_prob),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "line_axis_probabilities": dict(axes.line_axis_probabilities),
                    "extremum_probabilities": dict(axes.extremum_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "mark_shape_probabilities": dict(axes.mark_shape_probabilities),
                    "cell_fill_pattern_probabilities": dict(axes.cell_fill_pattern_probabilities),
                    "target_answer": int(answer_value),
                    "target_answer_support": list(target_answer_support_for_trace),
                    "target_answer_probabilities": dict(target_answer_probabilities_for_trace),
                    "completed_line_count_target": completed_line_count_target,
                    "completed_line_count_support": [int(value) for value in axes.target_answer_support],
                    "completed_line_count_probabilities": (
                        dict(axes.target_answer_probabilities)
                        if str(axes.query_id) == "line_sum_extremum_value"
                        else {}
                    ),
                    "line_sum_extremum": sampled_card.line_sum_extremum,
                    "line_sum_target_axis": sampled_card.line_sum_target_axis,
                    "line_sum_target_line_index": sampled_card.line_sum_target_line_index,
                    "line_sum_target_cell_ids": list(sampled_card.line_sum_target_cell_ids),
                    "line_sum_target_value": sampled_card.line_sum_target_value,
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "mark_shape": str(render_params.mark_shape),
                "cell_fill_pattern": str(render_params.cell_fill_pattern),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "line_axis": axes.line_axis,
                "extremum": axes.extremum,
                "style_variant": str(axes.style_variant),
                "mark_shape": str(render_params.mark_shape),
                "cell_fill_pattern": str(render_params.cell_fill_pattern),
                "target_answer": int(answer_value),
                "completed_line_count_target": completed_line_count_target,
                "axis_distractor_mark_prob": float(axis_distractor_mark_prob),
                "line_sum_distractor_mark_prob": float(line_sum_distractor_mark_prob),
                "target_answer_support": list(target_answer_support_for_trace),
                "completed_line_count_support": [int(value) for value in axes.target_answer_support],
                "numbers_grid": [[int(value) for value in row] for row in sampled_card.numbers_grid],
                "mark_grid": [[bool(value) for value in row] for row in sampled_card.mark_grid],
                "completed_row_indices": [int(value) for value in sampled_card.completed_row_indices],
                "completed_column_indices": [int(value) for value in sampled_card.completed_column_indices],
                "line_sum_extremum": sampled_card.line_sum_extremum,
                "line_sum_target_axis": sampled_card.line_sum_target_axis,
                "line_sum_target_line_index": sampled_card.line_sum_target_line_index,
                "line_sum_target_cell_ids": list(sampled_card.line_sum_target_cell_ids),
                "line_sum_target_value": sampled_card.line_sum_target_value,
                "completed_line_sums": [
                    {
                        "axis": str(axis_name),
                        "line_index": int(line_index),
                        "sum": int(value),
                    }
                    for axis_name, line_index, value in sampled_card.completed_line_sums
                ],
                "cell_specs": [
                    {
                        "cell_id": str(spec.cell_id),
                        "row_index": int(spec.row_index),
                        "column_index": int(spec.column_index),
                        "column_label": str(spec.column_label),
                        "number": int(spec.number),
                        "is_marked": bool(spec.is_marked),
                    }
                    for spec in rendered_scene.cell_specs
                ],
                "evidence_entity_ids": [str(cell_id) for cell_id in evidence_cell_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(cell_id) for cell_id in evidence_cell_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
            },
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id="bingo",
            query_id=str(axes.query_id),
        )


@register_task
class GamesBingoAxisCompletedLineCountTask(FixedQueryVariantTaskMixin, GamesBingoCompletedLineCountTask):
    """Count completed bingo lines along one sampled board axis."""

    task_id = "task_games__bingo__completed_line_count"
    fixed_query_id = "completed_axis_line_count"


@register_task
class GamesBingoLineSumExtremumValueTask(FixedQueryVariantTaskMixin, GamesBingoCompletedLineCountTask):
    """Return the unique min/max sum among completed bingo rows or columns."""

    task_id = "task_games__bingo__line_sum_extremum_value"
    fixed_query_id = "line_sum_extremum_value"


__all__ = [
    "GamesBingoAxisCompletedLineCountTask",
    "GamesBingoLineSumExtremumValueTask",
]
