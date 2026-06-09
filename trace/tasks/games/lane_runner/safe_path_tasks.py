"""Lane-runner safe-path selection tasks for the games domain."""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.complexity import build_games_complexity, normalize_linear, resolve_games_complexity_weights
from ..shared.lane_runner_common import (
    SUPPORTED_LANE_RUNNER_SAFE_PATH_QUERY_IDS,
    SUPPORTED_LANE_RUNNER_SCENE_VARIANTS,
    SUPPORTED_LANE_RUNNER_STYLE_VARIANTS,
    LaneRunnerHazard,
    LaneRunnerPathOption,
    LaneRunnerSafePathSample,
    cell_entity_id,
    hazard_entity_id,
    path_hits_hazard,
    path_option_entity_id,
    validate_lane_runner_safe_path_sample,
    visible_hazard_trace,
    visible_path_option_trace,
)
from ..shared.lane_runner_scene import LaneRunnerRenderParams, render_lane_runner_scene
from ..shared.layout import resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_lane_runner_safe_path_base"
PUBLIC_TASK_ID = "task_games__lane_runner__safe_path_label"
SAFE_PATH_QUERY_ID = "safe_path_label"
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for lane-runner safe-path scenes."""

    row_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    start_lane_support: Tuple[int, ...] = (0, 1)
    option_count_support: Tuple[int, ...] = (4, 6)
    answer_option_index_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    lane_count: int = 2
    cell_size_px: int = 80
    cell_gap_px: int = 7
    panel_margin_px: int = 28
    start_band_height_px: int = 44
    finish_band_height_px: int = 42
    runner_radius_px: int = 20
    grid_line_width_px: int = 3
    label_font_size_px: int = 20
    hazard_radius_px: int = 18
    path_line_width_px: int = 7
    path_label_font_size_px: int = 18
    option_card_cell_size_px: int = 80
    option_card_gap_px: int = 7
    option_card_margin_px: int = 10
    option_card_area_gap_px: int = 28
    canvas_outer_margin_px: int = 72
    canvas_min_width: int = 360
    canvas_min_height: int = 430


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one lane-runner safe-path instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    row_count: int
    lane_count: int
    start_lane: int
    option_count: int
    answer_option_index: int
    row_count_support: Tuple[int, ...]
    start_lane_support: Tuple[int, ...]
    option_count_support: Tuple[int, ...]
    answer_option_index_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    row_count_probabilities: Dict[str, float]
    start_lane_probabilities: Dict[str, float]
    option_count_probabilities: Dict[str, float]
    answer_option_index_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "lane_runner")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="lane_runner", apply_prob=0.5)


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named lane-runner safe-path axis."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(value) for value in supported],
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic and visual axes for one lane-runner safe-path instance."""

    query_id, query_id_probabilities = resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_LANE_RUNNER_SAFE_PATH_QUERY_IDS,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_LANE_RUNNER_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_LANE_RUNNER_STYLE_VARIANTS,
    )
    row_count, row_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="row_count_support",
        explicit_key="row_count",
        fallback_support=_DEFAULTS.row_count_support,
        namespace=f"{TASK_ID}.row_count",
        balanced_flag_key="balanced_row_count_sampling",
        namespace_support_permutation=True,
    )
    start_lane, start_lane_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="start_lane_support",
        explicit_key="start_lane",
        fallback_support=_DEFAULTS.start_lane_support,
        namespace=f"{TASK_ID}.start_lane",
        balanced_flag_key="balanced_start_lane_sampling",
        namespace_support_permutation=True,
    )
    option_count, option_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="option_count_support",
        explicit_key="option_count",
        fallback_support=_DEFAULTS.option_count_support,
        namespace=f"{TASK_ID}.option_count",
        balanced_flag_key="balanced_option_count_sampling",
        namespace_support_permutation=True,
    )
    raw_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="answer_option_index_support",
        fallback=_DEFAULTS.answer_option_index_support,
    )
    explicit_answer = params.get("answer_option_index")
    if explicit_answer is not None and int(explicit_answer) >= int(option_count):
        raise ValueError("answer_option_index must be less than option_count")
    feasible_answer_support = tuple(int(value) for value in raw_answer_support if 0 <= int(value) < int(option_count))
    if not feasible_answer_support:
        raise ValueError("lane-runner answer_option_index_support has no feasible values for option_count")
    answer_params = dict(params)
    answer_params["answer_option_index_support"] = list(feasible_answer_support)
    answer_index, answer_index_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=answer_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="answer_option_index_support",
        explicit_key="answer_option_index",
        fallback_support=feasible_answer_support,
        namespace=f"{TASK_ID}.answer_option_index.option_count_{int(option_count)}",
        balanced_flag_key="balanced_answer_option_index_sampling",
        namespace_support_permutation=True,
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        row_count=int(row_count),
        lane_count=int(_DEFAULTS.lane_count),
        start_lane=int(start_lane),
        option_count=int(option_count),
        answer_option_index=int(answer_index),
        row_count_support=resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="row_count_support",
            fallback=_DEFAULTS.row_count_support,
        ),
        start_lane_support=resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="start_lane_support",
            fallback=_DEFAULTS.start_lane_support,
        ),
        option_count_support=resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="option_count_support",
            fallback=_DEFAULTS.option_count_support,
        ),
        answer_option_index_support=tuple(int(value) for value in feasible_answer_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        row_count_probabilities=dict(row_count_probabilities),
        start_lane_probabilities=dict(start_lane_probabilities),
        option_count_probabilities=dict(option_count_probabilities),
        answer_option_index_probabilities=dict(answer_index_probabilities),
    )


def _render_params(
    params: Mapping[str, Any],
    *,
    axes: _ResolvedAxes,
    instance_seed: int,
    font_family: str,
) -> LaneRunnerRenderParams:
    """Resolve lane-runner safe-path rendering parameters."""

    unit_scale, unit_size_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.lane_runner.safe_path.unit_size",
        fallback_min=0.5,
        fallback_max=1.0,
    )
    cell_size = scale_games_px(
        params.get("cell_size_px", group_default(_RENDER_DEFAULTS, "cell_size_px", _DEFAULTS.cell_size_px)),
        unit_scale,
        min_px=28,
    )
    cell_gap = scale_games_px(
        params.get("cell_gap_px", group_default(_RENDER_DEFAULTS, "cell_gap_px", _DEFAULTS.cell_gap_px)),
        unit_scale,
        min_px=3,
    )
    panel_margin = scale_games_px(
        params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px)),
        unit_scale,
        min_px=14,
    )
    start_height = scale_games_px(
        params.get("start_band_height_px", group_default(_RENDER_DEFAULTS, "start_band_height_px", _DEFAULTS.start_band_height_px)),
        unit_scale,
        min_px=24,
    )
    finish_height = scale_games_px(
        params.get("finish_band_height_px", group_default(_RENDER_DEFAULTS, "finish_band_height_px", _DEFAULTS.finish_band_height_px)),
        unit_scale,
        min_px=24,
    )
    board_w = (int(axes.lane_count) * int(cell_size)) + ((int(axes.lane_count) - 1) * int(cell_gap))
    board_h = (int(axes.row_count) * int(cell_size)) + ((int(axes.row_count) - 1) * int(cell_gap))
    option_card_cell = scale_games_px(
        params.get("option_card_cell_size_px", group_default(_RENDER_DEFAULTS, "option_card_cell_size_px", _DEFAULTS.option_card_cell_size_px)),
        unit_scale,
        min_px=28,
    )
    option_card_gap = scale_games_px(
        params.get("option_card_gap_px", group_default(_RENDER_DEFAULTS, "option_card_gap_px", _DEFAULTS.option_card_gap_px)),
        unit_scale,
        min_px=3,
    )
    option_card_margin = scale_games_px(
        params.get("option_card_margin_px", group_default(_RENDER_DEFAULTS, "option_card_margin_px", _DEFAULTS.option_card_margin_px)),
        unit_scale,
        min_px=6,
    )
    option_area_gap = scale_games_px(
        params.get("option_card_area_gap_px", group_default(_RENDER_DEFAULTS, "option_card_area_gap_px", _DEFAULTS.option_card_area_gap_px)),
        unit_scale,
        min_px=14,
    )
    path_label_font_size = scale_games_px(
        params.get("path_label_font_size_px", group_default(_RENDER_DEFAULTS, "path_label_font_size_px", _DEFAULTS.path_label_font_size_px)),
        unit_scale,
        min_px=11,
    )
    option_cols = int(axes.option_count) if int(axes.option_count) <= 4 else 3
    option_rows = (int(axes.option_count) + option_cols - 1) // option_cols
    option_card_w = (int(axes.lane_count) * int(option_card_cell)) + ((int(axes.lane_count) - 1) * int(option_card_gap)) + (2 * int(option_card_margin))
    option_card_h = (
        (int(axes.row_count) * int(option_card_cell))
        + ((int(axes.row_count) - 1) * int(option_card_gap))
        + (4 * int(option_card_margin))
        + (2 * max(10, int(round(float(path_label_font_size) * 0.72))))
    )
    option_area_w = (int(option_cols) * int(option_card_w)) + ((int(option_cols) - 1) * 10)
    option_area_h = (int(option_rows) * int(option_card_h)) + ((int(option_rows) - 1) * 10)
    content_w = option_area_w + (2 * int(panel_margin))
    content_h = option_area_h + (2 * int(panel_margin))
    outer_margin = int(params.get("canvas_outer_margin_px", group_default(_RENDER_DEFAULTS, "canvas_outer_margin_px", _DEFAULTS.canvas_outer_margin_px)))
    dynamic_canvas = bool(params.get("dynamic_canvas_size_enabled", group_default(_RENDER_DEFAULTS, "dynamic_canvas_size_enabled", True)))
    if dynamic_canvas:
        canvas_width = max(
            int(params.get("canvas_min_width", group_default(_RENDER_DEFAULTS, "canvas_min_width", _DEFAULTS.canvas_min_width))),
            int(content_w + (2 * outer_margin)),
        )
        canvas_height = max(
            int(params.get("canvas_min_height", group_default(_RENDER_DEFAULTS, "canvas_min_height", _DEFAULTS.canvas_min_height))),
            int(content_h + (2 * outer_margin)),
        )
    else:
        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 520)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 780)))
    return LaneRunnerRenderParams(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        row_count=int(axes.row_count),
        lane_count=int(axes.lane_count),
        cell_size_px=int(cell_size),
        cell_gap_px=int(cell_gap),
        panel_margin_px=int(panel_margin),
        start_band_height_px=int(start_height),
        finish_band_height_px=int(finish_height),
        coin_radius_px=scale_games_px(
            params.get("coin_radius_px", group_default(_RENDER_DEFAULTS, "coin_radius_px", 17)),
            unit_scale,
            min_px=8,
        ),
        runner_radius_px=scale_games_px(
            params.get("runner_radius_px", group_default(_RENDER_DEFAULTS, "runner_radius_px", _DEFAULTS.runner_radius_px)),
            unit_scale,
            min_px=10,
        ),
        grid_line_width_px=scale_games_px(
            params.get("grid_line_width_px", group_default(_RENDER_DEFAULTS, "grid_line_width_px", _DEFAULTS.grid_line_width_px)),
            unit_scale,
            min_px=1,
        ),
        label_font_size_px=scale_games_px(
            params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px)),
            unit_scale,
            min_px=12,
        ),
        hazard_radius_px=scale_games_px(
            params.get("hazard_radius_px", group_default(_RENDER_DEFAULTS, "hazard_radius_px", _DEFAULTS.hazard_radius_px)),
            unit_scale,
            min_px=10,
        ),
        path_line_width_px=scale_games_px(
            params.get("path_line_width_px", group_default(_RENDER_DEFAULTS, "path_line_width_px", _DEFAULTS.path_line_width_px)),
            unit_scale,
            min_px=3,
        ),
        path_label_font_size_px=int(path_label_font_size),
        option_card_cell_size_px=int(option_card_cell),
        option_card_gap_px=int(option_card_gap),
        option_card_margin_px=int(option_card_margin),
        option_card_area_gap_px=int(option_area_gap),
        font_family=str(font_family),
        instance_seed=int(instance_seed),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.lane_runner.safe_path.layout_jitter",
        ),
        unit_size_meta=dict(unit_size_meta),
    )


def _candidate_distractor_paths(*, safe_lanes: Tuple[int, ...], hazard_rows: Sequence[int]) -> Tuple[Tuple[int, ...], ...]:
    """Return deterministic distractor paths that differ from safe route and hit a hazard."""

    rows = len(safe_lanes)
    hazard_set = {int(row) for row in hazard_rows}
    candidates: list[Tuple[int, ...]] = []
    for diff_count in range(2, rows + 1):
        for diff_rows in combinations(range(rows), diff_count):
            if not any(int(row) in hazard_set for row in diff_rows):
                continue
            path = list(safe_lanes)
            for row in diff_rows:
                path[int(row)] = 1 - int(path[int(row)])
            candidate = tuple(int(value) for value in path)
            if candidate != safe_lanes and candidate not in candidates:
                candidates.append(candidate)
    return tuple(candidates)


def _sample_scene(*, rng, axes: _ResolvedAxes) -> LaneRunnerSafePathSample:
    """Construct one exact-answer lane-runner safe-path scene."""

    labels = OPTION_LABELS[: int(axes.option_count)]
    answer_label = labels[int(axes.answer_option_index)]
    safe_lanes = tuple(int(rng.randrange(int(axes.lane_count))) for _ in range(int(axes.row_count)))
    hazard_count = int(rng.randint(2, min(4, int(axes.row_count))))
    hazard_rows = tuple(sorted(rng.sample(range(int(axes.row_count)), hazard_count)))
    hazards = tuple(
        LaneRunnerHazard(
            hazard_id=hazard_entity_id(row, 1 - int(safe_lanes[int(row)])),
            row=int(row),
            lane=1 - int(safe_lanes[int(row)]),
        )
        for row in hazard_rows
    )

    distractor_pool = list(_candidate_distractor_paths(safe_lanes=safe_lanes, hazard_rows=hazard_rows))
    rng.shuffle(distractor_pool)
    needed_distractors = int(axes.option_count) - 1
    if len(distractor_pool) < needed_distractors:
        raise ValueError("not enough unique safe-path distractors")

    options: list[LaneRunnerPathOption] = []
    distractor_index = 0
    for label in labels:
        if str(label) == str(answer_label):
            lanes = safe_lanes
        else:
            lanes = distractor_pool[distractor_index]
            distractor_index += 1
        options.append(LaneRunnerPathOption(label=str(label), lanes_by_row=tuple(int(value) for value in lanes)))

    for option in options:
        if str(option.label) != str(answer_label) and not path_hits_hazard(lanes_by_row=option.lanes_by_row, hazards=hazards):
            raise ValueError("lane-runner distractor path did not hit a hazard")

    sample = LaneRunnerSafePathSample(
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        row_count=int(axes.row_count),
        lane_count=int(axes.lane_count),
        start_lane=int(axes.start_lane),
        hazards=tuple(hazards),
        path_options=tuple(options),
        answer_label=str(answer_label),
        annotation_cell_ids=tuple(cell_entity_id(row, lane) for row, lane in enumerate(safe_lanes)),
        construction_mode="safe_path_with_off_route_hazards_and_invalid_distractors",
    )
    validate_lane_runner_safe_path_sample(sample)
    return sample


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return prompt examples for lane-runner safe-path JSON output."""

    answer_value = "C"
    annotation_value = [[314, 128, 392, 310]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def _build_complexity(*, row_count: int, option_count: int, hazard_count: int) -> Any:
    """Build normalized complexity for lane-runner safe-path scenes."""

    weights = resolve_games_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
    visual_scan = normalize_linear(float(row_count), min_value=5.0, max_value=8.0)
    path_planning = 0.42 + (0.20 * normalize_linear(float(option_count), min_value=4.0, max_value=6.0))
    ambiguity = 0.18 + (0.12 * normalize_linear(float(hazard_count), min_value=2.0, max_value=4.0))
    output_burden = normalize_linear(float(row_count), min_value=5.0, max_value=8.0)
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": float(visual_scan),
            "path_planning": float(path_planning),
            "ambiguity": float(ambiguity),
            "output_burden": float(output_burden),
        },
    )


@register_task
class GamesLaneRunnerSafePathLabelTask:
    """Select the only displayed lane-runner route that avoids hazards."""

    task_id = PUBLIC_TASK_ID
    domain = "games"
    task_group = "lane_runner"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        task_params = dict(params)
        axes = _resolve_axes(int(instance_seed), params=task_params)
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace="games.lane_runner.safe_path.font",
            params=task_params,
        )
        render_params = _render_params(
            task_params,
            axes=axes,
            instance_seed=int(instance_seed),
            font_family=str(font_family),
        )

        sampled_scene: LaneRunnerSafePathSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid lane-runner safe-path scene after {max_attempts} attempts")

        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.lane_runner.safe_path.panel_scene_style",
            treatment_weights=task_params.get(
                "panel_scene_treatment_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_treatment_weights", None),
            ),
            palette_weights=task_params.get(
                "panel_scene_palette_weights",
                group_default(_RENDER_DEFAULTS, "panel_scene_palette_weights", None),
            ),
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        rendered_scene = render_lane_runner_scene(
            coins=(),
            hazards=sampled_scene.hazards,
            path_options=sampled_scene.path_options,
            start_lane=int(sampled_scene.start_lane),
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            panel_style=panel_style,
            show_board=False,
        )
        answer_entity_id = path_option_entity_id(str(sampled_scene.answer_label))
        answer_option_render = dict(rendered_scene.render_map["path_options_px"][str(sampled_scene.answer_label)])
        annotation_bboxes = [list(answer_option_render["card_bbox_px"])]
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=task_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        object_description_key = f"object_description_{str(axes.scene_variant)}_safe_path"
        answer_hint_key = f"answer_hint_{str(axes.query_id)}"
        annotation_hint_key = f"annotation_hint_{str(axes.query_id)}"
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                object_description_key,
                "safe_path_rule_text",
                answer_hint_key,
                annotation_hint_key,
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[object_description_key]),
                "safe_path_rule_text": str(prompt_defaults["safe_path_rule_text"]),
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

        answer_gt = TypedValue(type="option_letter", value=str(sampled_scene.answer_label))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        font_record = get_font_family_record(str(font_family)).to_trace()
        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_lane_runner_safe_path_option_cards",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "row_count": int(sampled_scene.row_count),
                    "lane_count": int(sampled_scene.lane_count),
                    "start_lane": int(sampled_scene.start_lane),
                    "answer_label": str(sampled_scene.answer_label),
                    "annotation_entity_ids": [str(answer_entity_id)],
                    "safe_path_cell_ids": [str(entity_id) for entity_id in sampled_scene.annotation_cell_ids],
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
                    "row_count": int(axes.row_count),
                    "lane_count": int(axes.lane_count),
                    "start_lane": int(axes.start_lane),
                    "option_count": int(axes.option_count),
                    "answer_option_index": int(axes.answer_option_index),
                    "row_count_support": [int(value) for value in axes.row_count_support],
                    "start_lane_support": [int(value) for value in axes.start_lane_support],
                    "option_count_support": [int(value) for value in axes.option_count_support],
                    "answer_option_index_support": [int(value) for value in axes.answer_option_index_support],
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "row_count_probabilities": dict(axes.row_count_probabilities),
                    "start_lane_probabilities": dict(axes.start_lane_probabilities),
                    "option_count_probabilities": dict(axes.option_count_probabilities),
                    "answer_option_index_probabilities": dict(axes.answer_option_index_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "row_count": int(sampled_scene.row_count),
                "lane_count": int(sampled_scene.lane_count),
                "cell_size_px": int(render_params.cell_size_px),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "lane_runner_style": dict(rendered_scene.render_map.get("lane_runner_style", {})),
                "font_assets": {
                    "readout_font_family": {
                        **dict(font_record),
                        "font_role": "readout",
                    },
                },
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "row_count": int(sampled_scene.row_count),
                "lane_count": int(sampled_scene.lane_count),
                "start_lane": int(sampled_scene.start_lane),
                "hazards": list(visible_hazard_trace(sampled_scene.hazards)),
                "path_options": list(visible_path_option_trace(sampled_scene.path_options)),
                "answer": str(sampled_scene.answer_label),
                "answer_entity_id": str(answer_entity_id),
                "annotation_entity_ids": [str(answer_entity_id)],
                "annotation_bboxes_px": [list(bbox) for bbox in annotation_bboxes],
                "safe_path_cell_ids": [str(entity_id) for entity_id in sampled_scene.annotation_cell_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(answer_entity_id)],
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_bboxes],
            },
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
            complexity=_build_complexity(
                row_count=int(sampled_scene.row_count),
                option_count=len(sampled_scene.path_options),
                hazard_count=len(sampled_scene.hazards),
            ),
            task_versions=default_task_versions(),
            scene_id="lane_runner",
            query_id=str(axes.query_id),
        )


__all__ = ["GamesLaneRunnerSafePathLabelTask"]
