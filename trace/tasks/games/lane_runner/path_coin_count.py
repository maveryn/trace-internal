"""Lane-runner path-planning tasks for the games domain."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    load_scene_generation_rendering_prompt_defaults,
    required_group_defaults,
)
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ...shared.fixed_query import select_task_query_id
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from .shared.common import (
    SUPPORTED_LANE_RUNNER_SCENE_VARIANTS,
    SUPPORTED_LANE_RUNNER_STYLE_VARIANTS,
    LaneRunnerCoin,
    LaneRunnerSample,
    coin_entity_id,
    path_coin_collection,
    validate_lane_runner_sample,
    visible_coin_trace,
)
from .shared.rendering import LaneRunnerRenderParams, render_lane_runner_scene
from ..shared.layout import resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "lane_runner"
PATH_COIN_TASK_ID = "task_games__lane_runner__path_coin_count"
PATH_COIN_QUERY_ID = "path_coin_count"
SUPPORTED_QUERY_IDS = (PATH_COIN_QUERY_ID,)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for lane-runner scenes."""

    row_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    start_lane_support: Tuple[int, ...] = (0, 1)
    target_answer_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    lane_count: int = 2
    cell_size_px: int = 80
    cell_gap_px: int = 7
    panel_margin_px: int = 28
    start_band_height_px: int = 44
    finish_band_height_px: int = 42
    coin_radius_px: int = 17
    runner_radius_px: int = 20
    grid_line_width_px: int = 3
    label_font_size_px: int = 20
    canvas_outer_margin_px: int = 72
    canvas_min_width: int = 360
    canvas_min_height: int = 430


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one lane-runner instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    row_count: int
    lane_count: int
    start_lane: int
    target_answer: int
    row_count_support: Tuple[int, ...]
    start_lane_support: Tuple[int, ...]
    target_answer_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    row_count_probabilities: Dict[str, float]
    start_lane_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_PATH_GEN_DEFAULTS, _PATH_RENDER_DEFAULTS, _PATH_PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=PATH_COIN_TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _resolve_named_axis(
    *,
    task_id: str,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named lane-runner axis."""

    return resolve_games_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(value) for value in supported],
    )


def _resolve_axes_for_task(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    task_id: str,
    gen_defaults: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> _ResolvedAxes:
    """Resolve semantic and visual axes for one lane-runner instance."""

    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        task_id=str(task_id),
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_LANE_RUNNER_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        task_id=str(task_id),
        gen_defaults=gen_defaults,
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
        gen_defaults=gen_defaults,
        support_key="row_count_support",
        explicit_key="row_count",
        fallback_support=_DEFAULTS.row_count_support,
        namespace=f"{str(task_id)}.row_count",
        balanced_flag_key="balanced_row_count_sampling",
        namespace_support_permutation=True,
    )
    start_lane, start_lane_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="start_lane_support",
        explicit_key="start_lane",
        fallback_support=_DEFAULTS.start_lane_support,
        namespace=f"{str(task_id)}.start_lane",
        balanced_flag_key="balanced_start_lane_sampling",
        namespace_support_permutation=True,
    )
    raw_target_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="target_answer_support",
        fallback=_DEFAULTS.target_answer_support,
    )
    explicit_target = params.get("target_answer")
    if explicit_target is not None and int(explicit_target) > int(row_count):
        raise ValueError("target_answer must be no greater than row_count")
    feasible_target_support = tuple(int(value) for value in raw_target_support if 1 <= int(value) <= int(row_count))
    if not feasible_target_support:
        raise ValueError("lane-runner target_answer_support has no feasible values for row_count")
    target_params = dict(params)
    target_params["target_answer_support"] = list(feasible_target_support)
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=gen_defaults,
        support_key="target_answer_support",
        explicit_key="target_answer",
        fallback_support=feasible_target_support,
        namespace=f"{str(task_id)}.target_answer.row_count_{int(row_count)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        row_count=int(row_count),
        lane_count=int(_DEFAULTS.lane_count),
        start_lane=int(start_lane),
        target_answer=int(target_answer),
        row_count_support=resolve_integer_support(
            params,
            gen_defaults=gen_defaults,
            key="row_count_support",
            fallback=_DEFAULTS.row_count_support,
        ),
        start_lane_support=resolve_integer_support(
            params,
            gen_defaults=gen_defaults,
            key="start_lane_support",
            fallback=_DEFAULTS.start_lane_support,
        ),
        target_answer_support=tuple(int(value) for value in feasible_target_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        row_count_probabilities=dict(row_count_probabilities),
        start_lane_probabilities=dict(start_lane_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _resolve_path_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> _ResolvedAxes:
    """Resolve semantic and visual axes for the shown-path coin task."""

    return _resolve_axes_for_task(
        int(instance_seed),
        params=params,
        task_id=PATH_COIN_TASK_ID,
        gen_defaults=_PATH_GEN_DEFAULTS,
        query_id=str(query_id),
        query_id_probabilities=query_id_probabilities,
    )


def _render_params(
    params: Mapping[str, Any],
    *,
    axes: _ResolvedAxes,
    instance_seed: int,
    font_family: str,
    render_defaults: Mapping[str, Any] | None = None,
    namespace: str = "games.lane_runner",
) -> LaneRunnerRenderParams:
    """Resolve lane-runner rendering parameters."""

    defaults = render_defaults if render_defaults is not None else _PATH_RENDER_DEFAULTS
    unit_scale, unit_size_meta = resolve_games_unit_size_scale(
        params,
        defaults,
        instance_seed=int(instance_seed),
        namespace=f"{str(namespace)}.unit_size",
        fallback_min=0.5,
        fallback_max=1.0,
    )
    cell_size = scale_games_px(
        params.get("cell_size_px", group_default(defaults, "cell_size_px", _DEFAULTS.cell_size_px)),
        unit_scale,
        min_px=28,
    )
    cell_gap = scale_games_px(
        params.get("cell_gap_px", group_default(defaults, "cell_gap_px", _DEFAULTS.cell_gap_px)),
        unit_scale,
        min_px=3,
    )
    panel_margin = scale_games_px(
        params.get("panel_margin_px", group_default(defaults, "panel_margin_px", _DEFAULTS.panel_margin_px)),
        unit_scale,
        min_px=14,
    )
    start_height = scale_games_px(
        params.get("start_band_height_px", group_default(defaults, "start_band_height_px", _DEFAULTS.start_band_height_px)),
        unit_scale,
        min_px=24,
    )
    finish_height = scale_games_px(
        params.get("finish_band_height_px", group_default(defaults, "finish_band_height_px", _DEFAULTS.finish_band_height_px)),
        unit_scale,
        min_px=24,
    )
    board_w = (int(axes.lane_count) * int(cell_size)) + ((int(axes.lane_count) - 1) * int(cell_gap))
    board_h = (int(axes.row_count) * int(cell_size)) + ((int(axes.row_count) - 1) * int(cell_gap))
    content_w = board_w + (2 * int(panel_margin))
    content_h = int(finish_height) + int(cell_gap) + board_h + int(cell_gap) + int(start_height) + (2 * int(panel_margin))
    outer_margin = int(params.get("canvas_outer_margin_px", group_default(defaults, "canvas_outer_margin_px", _DEFAULTS.canvas_outer_margin_px)))
    dynamic_canvas = bool(params.get("dynamic_canvas_size_enabled", group_default(defaults, "dynamic_canvas_size_enabled", True)))
    if dynamic_canvas:
        canvas_width = max(
            int(params.get("canvas_min_width", group_default(defaults, "canvas_min_width", _DEFAULTS.canvas_min_width))),
            int(content_w + (2 * outer_margin)),
        )
        canvas_height = max(
            int(params.get("canvas_min_height", group_default(defaults, "canvas_min_height", _DEFAULTS.canvas_min_height))),
            int(content_h + (2 * outer_margin)),
        )
    else:
        canvas_width = int(params.get("canvas_width", group_default(defaults, "canvas_width", 520)))
        canvas_height = int(params.get("canvas_height", group_default(defaults, "canvas_height", 780)))
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
            params.get("coin_radius_px", group_default(defaults, "coin_radius_px", _DEFAULTS.coin_radius_px)),
            unit_scale,
            min_px=8,
        ),
        runner_radius_px=scale_games_px(
            params.get("runner_radius_px", group_default(defaults, "runner_radius_px", _DEFAULTS.runner_radius_px)),
            unit_scale,
            min_px=10,
        ),
        grid_line_width_px=scale_games_px(
            params.get("grid_line_width_px", group_default(defaults, "grid_line_width_px", _DEFAULTS.grid_line_width_px)),
            unit_scale,
            min_px=1,
        ),
        label_font_size_px=scale_games_px(
            params.get("label_font_size_px", group_default(defaults, "label_font_size_px", _DEFAULTS.label_font_size_px)),
            unit_scale,
            min_px=12,
        ),
        font_family=str(font_family),
        instance_seed=int(instance_seed),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            defaults,
            instance_seed=int(instance_seed),
            namespace=f"{str(namespace)}.layout_jitter",
        ),
        unit_size_meta=dict(unit_size_meta),
    )


def _sample_path_coin_scene(*, rng, axes: _ResolvedAxes) -> LaneRunnerSample:
    """Construct one shown-path coin-count scene with off-path distractors."""

    rows = int(axes.row_count)
    lanes = int(axes.lane_count)
    if lanes != 2:
        raise ValueError("lane-runner path-coin task requires two lanes")
    if int(axes.target_answer) > rows:
        raise ValueError("target_answer must be no greater than row_count")

    path: list[int] = []
    previous = int(axes.start_lane)
    for _row in range(rows):
        if rng.random() < 0.42:
            lane = 1 - int(previous)
        else:
            lane = int(previous)
        path.append(int(lane))
        previous = int(lane)

    collected_rows = sorted(rng.sample(range(rows), int(axes.target_answer)))
    coin_cells: set[Tuple[int, int]] = {(int(row), int(path[row])) for row in collected_rows}

    off_path_cells = [(row, 1 - int(path[row])) for row in range(rows)]
    parallel_rows = [row for row in collected_rows if (row, 1 - int(path[row])) in off_path_cells]
    if not parallel_rows:
        raise ValueError("path-coin task requires at least one collected row")
    parallel_row = int(rng.choice(parallel_rows))
    coin_cells.add((parallel_row, 1 - int(path[parallel_row])))

    min_total = int(axes.target_answer) + 1
    max_extra = max(1, min(rows - int(axes.target_answer), 3))
    extra_count = int(rng.randint(1, max_extra))
    rng.shuffle(off_path_cells)
    for cell in off_path_cells:
        if len(coin_cells) >= min(rows * lanes, int(axes.target_answer) + extra_count):
            break
        coin_cells.add((int(cell[0]), int(cell[1])))
    if len(coin_cells) <= int(axes.target_answer):
        raise ValueError("path-coin task failed to add off-path coin distractors")

    coins = tuple(
        LaneRunnerCoin(coin_id=coin_entity_id(row, lane), row=int(row), lane=int(lane))
        for row, lane in sorted(coin_cells)
    )
    answer, annotation_ids = path_coin_collection(
        coins=coins,
        shown_path_lanes=tuple(path),
        row_count=rows,
        lane_count=lanes,
        start_lane=int(axes.start_lane),
    )
    if int(answer) != int(axes.target_answer):
        raise ValueError("path-coin sampled answer does not match target")
    sample = LaneRunnerSample(
        mode=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        row_count=rows,
        lane_count=lanes,
        start_lane=int(axes.start_lane),
        coins=coins,
        optimal_route_lanes=tuple(int(value) for value in path),
        answer=int(answer),
        annotation_entity_ids=tuple(str(value) for value in annotation_ids),
        construction_mode="sample_shown_path_with_parallel_coin_distractors",
    )
    validate_lane_runner_sample(sample)
    return sample


def _build_prompt_json_examples(query_id: str = PATH_COIN_QUERY_ID) -> Tuple[str, str]:
    """Return prompt examples for lane-runner JSON output."""

    answer_value = 2
    annotation_value = [[176, 412], [176, 240]]
    if str(query_id) == PATH_COIN_QUERY_ID:
        annotation_value = [[176, 412], [176, 240]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


@register_task
class GamesLaneRunnerPathCoinCountTask:
    """Count coins collected by a displayed two-lane runner path."""

    task_id = PATH_COIN_TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=PATH_COIN_QUERY_ID,
            task_id=PATH_COIN_TASK_ID,
            namespace=f"{PATH_COIN_TASK_ID}.query",
        )
        axes = _resolve_path_axes(
            int(instance_seed),
            params=task_params,
            query_id=str(query_id),
            query_id_probabilities=query_id_probabilities,
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace="games.lane_runner.path_coin.font",
            params=task_params,
        )
        render_params = _render_params(
            task_params,
            axes=axes,
            instance_seed=int(instance_seed),
            font_family=str(font_family),
            render_defaults=_PATH_RENDER_DEFAULTS,
            namespace="games.lane_runner.path_coin",
        )

        sampled_scene: LaneRunnerSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{PATH_COIN_TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_path_coin_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid lane-runner path-coin scene after {max_attempts} attempts")

        panel_style, panel_style_meta = resolve_game_panel_scene_style(
            instance_seed=int(instance_seed),
            namespace="games.lane_runner.path_coin.panel_scene_style",
            treatment_weights=task_params.get(
                "panel_scene_treatment_weights",
                group_default(_PATH_RENDER_DEFAULTS, "panel_scene_treatment_weights", None),
            ),
            palette_weights=task_params.get(
                "panel_scene_palette_weights",
                group_default(_PATH_RENDER_DEFAULTS, "panel_scene_palette_weights", None),
            ),
        )
        background, background_meta = make_panel_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=panel_style,
        )
        rendered_scene = render_lane_runner_scene(
            coins=sampled_scene.coins,
            shown_path_lanes=sampled_scene.optimal_route_lanes,
            start_lane=int(sampled_scene.start_lane),
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            panel_style=panel_style,
        )
        annotation_points = [
            list(rendered_scene.render_map["entity_points_px"][str(entity_id)])
            for entity_id in sampled_scene.annotation_entity_ids
        ]
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=task_params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        object_description_key = f"object_description_{str(axes.scene_variant)}_path_coin"
        answer_hint_key = f"answer_hint_{str(axes.query_id)}"
        annotation_hint_key = f"annotation_hint_{str(axes.query_id)}"
        prompt_defaults = required_group_defaults(
            _PATH_PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                object_description_key,
                "lane_runner_path_rule_text",
                answer_hint_key,
                annotation_hint_key,
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "object_description": str(prompt_defaults[object_description_key]),
                "lane_runner_path_rule_text": str(prompt_defaults["lane_runner_path_rule_text"]),
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

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        annotation_gt = TypedValue(type="point_set", value=[list(point) for point in annotation_points])
        font_record = get_font_family_record(str(font_family)).to_trace()
        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_lane_runner_two_lane_track",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "row_count": int(sampled_scene.row_count),
                    "lane_count": int(sampled_scene.lane_count),
                    "start_lane": int(sampled_scene.start_lane),
                    "shown_path_lanes": [int(value) for value in sampled_scene.optimal_route_lanes],
                    "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
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
                    "target_answer": int(axes.target_answer),
                    "row_count_support": [int(value) for value in axes.row_count_support],
                    "start_lane_support": [int(value) for value in axes.start_lane_support],
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "row_count_probabilities": dict(axes.row_count_probabilities),
                    "start_lane_probabilities": dict(axes.start_lane_probabilities),
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
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
                "coins": list(visible_coin_trace(sampled_scene.coins)),
                "shown_path_lanes": [int(value) for value in sampled_scene.optimal_route_lanes],
                "answer": int(sampled_scene.answer),
                "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
            },
            "projected_annotation": {
                "type": "point_set",
                "point_set": [list(point) for point in annotation_points],
                "pixel_point_set": [list(point) for point in annotation_points],
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
            task_versions=default_task_versions(),
            scene_id="lane_runner",
            query_id=str(axes.query_id),
        )


__all__ = ["GamesLaneRunnerPathCoinCountTask"]
