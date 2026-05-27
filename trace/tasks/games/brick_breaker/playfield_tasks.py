"""Games Brick-breaker tasks over ball motion, bricks, and catch lanes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
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
from ...shared.support_sampling import resolve_integer_choice
from ..shared.brick_breaker_common import (
    SUPPORTED_BRICK_BREAKER_QUERY_VARIANTS,
    SUPPORTED_BRICK_BREAKER_SCENE_VARIANTS,
    SUPPORTED_BRICK_BREAKER_STYLE_VARIANTS,
    BrickBreakerBrick,
    BrickBreakerSample,
    brick_entity_id,
    lane_entity_id,
    lane_label,
    validate_brick_breaker_sample,
)
from ..shared.brick_breaker_scene import BrickBreakerRenderParams, render_brick_breaker_scene
from ..shared.complexity import build_games_brick_breaker_complexity
from ..shared.fixed_query_task import rewrite_public_query_output
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_variant
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_brick_breaker_playfield_base"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Brick-breaker scenes."""

    brick_row_count_support: Tuple[int, ...] = (4, 5)
    brick_col_count_support: Tuple[int, ...] = (5, 6)
    catch_lane_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    row_remaining_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    canvas_width: int = 980
    canvas_height: int = 740
    panel_margin_px: int = 38
    playfield_width_px: int = 860
    playfield_height_px: int = 640
    playfield_border_width_px: int = 5
    brick_wall_top_px: int = 46
    brick_wall_height_px: int = 270
    brick_gap_px: int = 8
    lane_pad_height_px: int = 42
    lane_pad_gap_px: int = 8
    ball_radius_px: int = 16
    path_width_px: int = 5
    label_font_size_px: int = 24


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Brick-breaker instance."""

    query_variant: str
    scene_variant: str
    style_variant: str
    brick_rows: int
    brick_cols: int
    lane_count: int
    row_remaining_count: int
    query_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    brick_rows_probabilities: Dict[str, float]
    brick_cols_probabilities: Dict[str, float]
    lane_count_probabilities: Dict[str, float]
    row_remaining_count_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "brick_breaker")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="brick_breaker")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="brick_breaker", apply_prob=0.5)


def _resolve_query_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_query_variants: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Brick-breaker query variant."""

    return resolve_games_query_variant(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=tuple(str(value) for value in supported_query_variants),
    )


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
    """Resolve one balanced named Brick-breaker axis."""

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


def _resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    supported_query_variants: Sequence[str],
) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Brick-breaker instance."""

    query_variant, query_variant_probabilities = _resolve_query_variant(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_variants=tuple(str(value) for value in supported_query_variants),
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_BRICK_BREAKER_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_BRICK_BREAKER_STYLE_VARIANTS,
    )
    brick_rows, brick_rows_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="brick_row_count_support",
        explicit_key="brick_rows",
        fallback_support=_DEFAULTS.brick_row_count_support,
        namespace=f"{TASK_ID}.brick_rows",
        balanced_flag_key="balanced_brick_row_sampling",
        namespace_support_permutation=True,
    )
    brick_cols, brick_cols_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="brick_col_count_support",
        explicit_key="brick_cols",
        fallback_support=_DEFAULTS.brick_col_count_support,
        namespace=f"{TASK_ID}.brick_cols",
        balanced_flag_key="balanced_brick_col_sampling",
        namespace_support_permutation=True,
    )
    lane_count, lane_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="catch_lane_count_support",
        explicit_key="lane_count",
        fallback_support=_DEFAULTS.catch_lane_count_support,
        namespace=f"{TASK_ID}.lane_count",
        balanced_flag_key="balanced_lane_count_sampling",
        namespace_support_permutation=True,
    )
    row_remaining_count, row_remaining_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="row_remaining_count_support",
        explicit_key="row_remaining_count",
        fallback_support=_DEFAULTS.row_remaining_count_support,
        namespace=f"{TASK_ID}.row_remaining_count",
        balanced_flag_key="balanced_row_remaining_count_sampling",
        namespace_support_permutation=True,
    )
    if str(query_variant) == "hit_row_remaining_count" and int(brick_cols) <= int(row_remaining_count):
        brick_cols = int(row_remaining_count) + 1
        brick_cols_probabilities = {str(brick_cols): 1.0}
    return _ResolvedAxes(
        query_variant=str(query_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        brick_rows=int(brick_rows),
        brick_cols=int(brick_cols),
        lane_count=int(lane_count),
        row_remaining_count=int(row_remaining_count),
        query_variant_probabilities=dict(query_variant_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        brick_rows_probabilities=dict(brick_rows_probabilities),
        brick_cols_probabilities=dict(brick_cols_probabilities),
        lane_count_probabilities=dict(lane_count_probabilities),
        row_remaining_count_probabilities=dict(row_remaining_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> BrickBreakerRenderParams:
    """Resolve Brick-breaker rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.brick_breaker.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.brick_breaker.layout",
        ),
        unit_scale_meta,
    )
    return BrickBreakerRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        playfield_width_px=scale_games_px(params.get("playfield_width_px", group_default(_RENDER_DEFAULTS, "playfield_width_px", _DEFAULTS.playfield_width_px)), unit_scale, min_px=430),
        playfield_height_px=scale_games_px(params.get("playfield_height_px", group_default(_RENDER_DEFAULTS, "playfield_height_px", _DEFAULTS.playfield_height_px)), unit_scale, min_px=320),
        playfield_border_width_px=scale_games_px(params.get("playfield_border_width_px", group_default(_RENDER_DEFAULTS, "playfield_border_width_px", _DEFAULTS.playfield_border_width_px)), unit_scale, min_px=2),
        brick_wall_top_px=scale_games_px(params.get("brick_wall_top_px", group_default(_RENDER_DEFAULTS, "brick_wall_top_px", _DEFAULTS.brick_wall_top_px)), unit_scale, min_px=23),
        brick_wall_height_px=scale_games_px(params.get("brick_wall_height_px", group_default(_RENDER_DEFAULTS, "brick_wall_height_px", _DEFAULTS.brick_wall_height_px)), unit_scale, min_px=135),
        brick_gap_px=scale_games_px(params.get("brick_gap_px", group_default(_RENDER_DEFAULTS, "brick_gap_px", _DEFAULTS.brick_gap_px)), unit_scale, min_px=4),
        lane_pad_height_px=scale_games_px(params.get("lane_pad_height_px", group_default(_RENDER_DEFAULTS, "lane_pad_height_px", _DEFAULTS.lane_pad_height_px)), unit_scale, min_px=21),
        lane_pad_gap_px=scale_games_px(params.get("lane_pad_gap_px", group_default(_RENDER_DEFAULTS, "lane_pad_gap_px", _DEFAULTS.lane_pad_gap_px)), unit_scale, min_px=4),
        ball_radius_px=scale_games_px(params.get("ball_radius_px", group_default(_RENDER_DEFAULTS, "ball_radius_px", _DEFAULTS.ball_radius_px)), unit_scale, min_px=8),
        path_width_px=scale_games_px(params.get("path_width_px", group_default(_RENDER_DEFAULTS, "path_width_px", _DEFAULTS.path_width_px)), unit_scale, min_px=2),
        label_font_size_px=scale_games_px(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px)), unit_scale, min_px=12),
        layout_jitter_meta=layout_jitter,
    )


def _label_pool(count: int) -> list[str]:
    """Return enough short unique uppercase labels for visible bricks."""

    if int(count) > 26:
        raise ValueError("brick breaker scenes must keep visible brick labels to A..Z")
    labels = [chr(ord("A") + index) for index in range(26)]
    return labels[: int(count)]


def _cap_cells_for_single_letter_labels(
    *,
    cells: Sequence[Tuple[int, int]],
    rng,
    protected_cells: Sequence[Tuple[int, int]] = (),
) -> list[Tuple[int, int]]:
    """Remove non-critical bricks until the scene can use only `A` through `Z` labels."""

    keep = set((int(row), int(col)) for row, col in cells)
    protected = set((int(row), int(col)) for row, col in protected_cells)
    removable = [cell for cell in keep if cell not in protected]
    rng.shuffle(removable)
    for cell in removable:
        if len(keep) <= 26:
            break
        keep.remove(cell)
    if len(keep) > 26:
        raise ValueError("not enough removable bricks to keep labels single-letter")
    return sorted(keep)


def _make_bricks(*, cells: Sequence[Tuple[int, int]], rng) -> Tuple[BrickBreakerBrick, ...]:
    """Create labeled bricks from row/column cells."""

    labels = _label_pool(len(cells))
    rng.shuffle(labels)
    bricks: list[BrickBreakerBrick] = []
    for index, (row, col) in enumerate(cells):
        bricks.append(
            BrickBreakerBrick(
                brick_id=brick_entity_id(int(row), int(col)),
                label=str(labels[index]),
                row=int(row),
                col=int(col),
                color_index=int((int(row) + int(col) + index) % 5),
            )
        )
    return tuple(bricks)


def _sample_next_hit_scene(*, rng, axes: _ResolvedAxes) -> BrickBreakerSample:
    """Construct a scene where the motion path first reaches one labeled brick."""

    rows = int(axes.brick_rows)
    cols = int(axes.brick_cols)
    target_row = rows - 1
    target_col = int(rng.randrange(cols))
    cells: list[Tuple[int, int]] = []
    for row in range(rows):
        for col in range(cols):
            if int(row) != int(target_row) or int(col) != int(target_col):
                if int(row) == int(target_row) and abs(int(col) - int(target_col)) == 1 and rng.random() < 0.55:
                    continue
                if rng.random() < 0.18:
                    continue
            cells.append((int(row), int(col)))
    if (target_row, target_col) not in set(cells):
        cells.append((target_row, target_col))
    cells = _cap_cells_for_single_letter_labels(
        cells=sorted(set(cells)),
        rng=rng,
        protected_cells=((target_row, target_col),),
    )
    bricks = _make_bricks(cells=cells, rng=rng)
    target_brick_id = brick_entity_id(target_row, target_col)
    target_brick = next(brick for brick in bricks if str(brick.brick_id) == str(target_brick_id))
    lane_count = int(axes.lane_count)
    target_lane_hint = int(round((((float(target_col) + 0.5) / float(cols)) * float(lane_count)) - 0.5))
    target_lane_hint = max(0, min(lane_count - 1, int(target_lane_hint)))
    start_lane_candidates = [
        lane
        for lane in (target_lane_hint - 1, target_lane_hint + 1)
        if 0 <= int(lane) < lane_count
    ]
    if not start_lane_candidates:
        start_lane_candidates = [lane for lane in range(lane_count) if int(lane) != int(target_lane_hint)] or [target_lane_hint]
    ball_start_lane = int(rng.choice(start_lane_candidates))
    sample = BrickBreakerSample(
        brick_rows=rows,
        brick_cols=cols,
        lane_count=lane_count,
        query_variant=str(axes.query_variant),
        scene_variant=str(axes.scene_variant),
        answer=str(target_brick.label),
        bricks=bricks,
        target_brick_id=str(target_brick.brick_id),
        target_brick_label=str(target_brick.label),
        target_row_remaining_brick_ids=(),
        target_row_remaining_count=None,
        target_lane_index=None,
        target_lane_label=None,
        ball_start_lane_index=ball_start_lane,
        evidence_entity_ids=(str(target_brick.brick_id),),
        construction_mode="angled_path_first_lower_row_brick",
    )
    validate_brick_breaker_sample(sample)
    return sample


def _sample_paddle_catch_scene(*, rng, axes: _ResolvedAxes) -> BrickBreakerSample:
    """Construct a scene where the ball path ends in one bottom catch lane."""

    rows = int(axes.brick_rows)
    cols = int(axes.brick_cols)
    cells = [
        (row, col)
        for row in range(rows)
        for col in range(cols)
        if rng.random() >= 0.10
    ]
    if len(cells) < max(8, cols * 2):
        cells = [(row, col) for row in range(rows) for col in range(cols)]
    cells = _cap_cells_for_single_letter_labels(cells=sorted(cells), rng=rng)
    bricks = _make_bricks(cells=sorted(cells), rng=rng)
    lane_count = int(axes.lane_count)
    target_lane = int(rng.randrange(lane_count))
    candidate_starts = [
        lane
        for lane in range(lane_count)
        if abs(int(lane) - int(target_lane)) <= 2
    ]
    start_lane = int(rng.choice(candidate_starts))
    sample = BrickBreakerSample(
        brick_rows=rows,
        brick_cols=cols,
        lane_count=lane_count,
        query_variant=str(axes.query_variant),
        scene_variant=str(axes.scene_variant),
        answer=lane_label(target_lane),
        bricks=bricks,
        target_brick_id=None,
        target_brick_label=None,
        target_row_remaining_brick_ids=(),
        target_row_remaining_count=None,
        target_lane_index=int(target_lane),
        target_lane_label=lane_label(target_lane),
        ball_start_lane_index=int(start_lane),
        evidence_entity_ids=(lane_entity_id(target_lane),),
        construction_mode="straight_path_to_catch_lane",
    )
    validate_brick_breaker_sample(sample)
    return sample


def _sample_hit_row_remaining_scene(*, rng, axes: _ResolvedAxes) -> BrickBreakerSample:
    """Construct a scene where a shot removes one brick, then count row survivors."""

    rows = int(axes.brick_rows)
    cols = int(axes.brick_cols)
    target_row = rows - 1
    target_col = int(rng.randrange(cols))
    possible_remaining_cols = [col for col in range(cols) if int(col) != int(target_col)]
    rng.shuffle(possible_remaining_cols)
    remaining_count = int(axes.row_remaining_count)
    if int(remaining_count) > len(possible_remaining_cols):
        raise ValueError("row_remaining_count requires more same-row bricks than this grid can support")
    remaining_cols = sorted(possible_remaining_cols[:remaining_count])
    protected_cells = [(target_row, target_col)] + [(target_row, col) for col in remaining_cols]
    cells: list[Tuple[int, int]] = list(protected_cells)
    for row in range(rows - 1):
        for col in range(cols):
            if rng.random() < 0.24:
                continue
            cells.append((int(row), int(col)))
    cells = _cap_cells_for_single_letter_labels(
        cells=sorted(set(cells)),
        rng=rng,
        protected_cells=protected_cells,
    )
    bricks = _make_bricks(cells=cells, rng=rng)
    target_brick_id = brick_entity_id(target_row, target_col)
    target_brick = next(brick for brick in bricks if str(brick.brick_id) == str(target_brick_id))
    remaining_ids = tuple(brick_entity_id(target_row, col) for col in remaining_cols)
    lane_count = int(axes.lane_count)
    target_lane_hint = int(round((((float(target_col) + 0.5) / float(cols)) * float(lane_count)) - 0.5))
    target_lane_hint = max(0, min(lane_count - 1, int(target_lane_hint)))
    start_lane_candidates = [
        lane
        for lane in (target_lane_hint - 1, target_lane_hint + 1)
        if 0 <= int(lane) < lane_count
    ]
    if not start_lane_candidates:
        start_lane_candidates = [lane for lane in range(lane_count) if int(lane) != int(target_lane_hint)] or [target_lane_hint]
    ball_start_lane = int(rng.choice(start_lane_candidates))
    sample = BrickBreakerSample(
        brick_rows=rows,
        brick_cols=cols,
        lane_count=lane_count,
        query_variant=str(axes.query_variant),
        scene_variant=str(axes.scene_variant),
        answer=int(len(remaining_ids)),
        bricks=bricks,
        target_brick_id=str(target_brick.brick_id),
        target_brick_label=str(target_brick.label),
        target_row_remaining_brick_ids=remaining_ids,
        target_row_remaining_count=int(len(remaining_ids)),
        target_lane_index=None,
        target_lane_label=None,
        ball_start_lane_index=ball_start_lane,
        evidence_entity_ids=remaining_ids,
        construction_mode="brick_hit_then_same_row_remaining_count",
    )
    validate_brick_breaker_sample(sample)
    return sample


def _sample_scene(*, rng, axes: _ResolvedAxes) -> BrickBreakerSample:
    """Construct one Brick-breaker scene for the requested query."""

    query = str(axes.query_variant)
    if query == "next_hit_label":
        return _sample_next_hit_scene(rng=rng, axes=axes)
    if query == "paddle_catch_label":
        return _sample_paddle_catch_scene(rng=rng, axes=axes)
    if query == "hit_row_remaining_count":
        return _sample_hit_row_remaining_scene(rng=rng, axes=axes)
    raise ValueError(f"unsupported Brick-breaker query_variant: {query}")


def _build_prompt_json_examples(query_variant: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Brick-breaker JSON output."""

    if str(query_variant) == "paddle_catch_label":
        answer_value = "C"
        evidence_value = [[375, 650, 475, 692]]
    elif str(query_variant) == "hit_row_remaining_count":
        answer_value = 4
        evidence_value = [[120, 255, 220, 302], [230, 255, 330, 302], [340, 255, 440, 302], [450, 255, 550, 302]]
    else:
        answer_value = "H"
        evidence_value = [[438, 186, 514, 228]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesBrickBreakerPlayfieldTask:
    """Return one grounded query over a visible Brick-breaker playfield."""

    task_id = TASK_ID
    domain = "games"
    task_group = "brick_breaker"
    supported_query_variants: Tuple[str, ...] = SUPPORTED_BRICK_BREAKER_QUERY_VARIANTS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(
            int(instance_seed),
            params=params,
            supported_query_variants=tuple(str(value) for value in self.supported_query_variants),
        )
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: BrickBreakerSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_brick_breaker_scene(
            brick_rows=int(sampled_scene.brick_rows),
            brick_cols=int(sampled_scene.brick_cols),
            lane_count=int(sampled_scene.lane_count),
            bricks=sampled_scene.bricks,
            query_variant=str(sampled_scene.query_variant),
            target_brick_id=sampled_scene.target_brick_id,
            target_lane_index=sampled_scene.target_lane_index,
            ball_start_lane_index=sampled_scene.ball_start_lane_index,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
        )
        evidence_bboxes = [
            list(rendered_scene.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evidence_entity_ids
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
                "object_description_brick_wall",
                "brick_breaker_motion_rule_text",
                "answer_hint_next_hit_label",
                "evidence_hint_next_hit_label",
                "answer_hint_paddle_catch_label",
                "evidence_hint_paddle_catch_label",
                "answer_hint_hit_row_remaining_count",
                "evidence_hint_hit_row_remaining_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_variant))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "brick_breaker_motion_rule_text": str(prompt_defaults["brick_breaker_motion_rule_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_variant)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(
            type="integer" if isinstance(sampled_scene.answer, int) else "string",
            value=int(sampled_scene.answer) if isinstance(sampled_scene.answer, int) else str(sampled_scene.answer),
        )
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_brick_breaker_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
            brick_count=len(sampled_scene.bricks),
            lane_count=int(sampled_scene.lane_count),
            evidence_count=len(sampled_scene.evidence_entity_ids),
        )
        brick_trace = [
            {
                "brick_id": str(brick.brick_id),
                "label": str(brick.label),
                "row": int(brick.row),
                "col": int(brick.col),
            }
            for brick in sampled_scene.bricks
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_brick_breaker_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "query_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "brick_rows": int(sampled_scene.brick_rows),
                    "brick_cols": int(sampled_scene.brick_cols),
                    "lane_count": int(sampled_scene.lane_count),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                },
            },
            "query_spec": {
                "query_variant": str(axes.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "query_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "brick_rows": int(sampled_scene.brick_rows),
                    "brick_cols": int(sampled_scene.brick_cols),
                    "brick_count": len(sampled_scene.bricks),
                    "lane_count": int(sampled_scene.lane_count),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "brick_rows_probabilities": dict(axes.brick_rows_probabilities),
                    "brick_cols_probabilities": dict(axes.brick_cols_probabilities),
                    "lane_count_probabilities": dict(axes.lane_count_probabilities),
                    "row_remaining_count_probabilities": dict(axes.row_remaining_count_probabilities),
                    "target_brick_id": sampled_scene.target_brick_id,
                    "target_brick_label": sampled_scene.target_brick_label,
                    "target_row_remaining_brick_ids": list(sampled_scene.target_row_remaining_brick_ids),
                    "target_row_remaining_count": sampled_scene.target_row_remaining_count,
                    "target_lane_index": sampled_scene.target_lane_index,
                    "target_lane_label": sampled_scene.target_lane_label,
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_variant": str(axes.query_variant),
                "query_variant": str(axes.query_variant),
                "style_variant": str(axes.style_variant),
                "brick_rows": int(sampled_scene.brick_rows),
                "brick_cols": int(sampled_scene.brick_cols),
                "lane_count": int(sampled_scene.lane_count),
                "bricks": brick_trace,
                "target_brick_id": sampled_scene.target_brick_id,
                "target_brick_label": sampled_scene.target_brick_label,
                "target_row_remaining_brick_ids": list(sampled_scene.target_row_remaining_brick_ids),
                "target_row_remaining_count": sampled_scene.target_row_remaining_count,
                "target_lane_index": sampled_scene.target_lane_index,
                "target_lane_label": sampled_scene.target_lane_label,
                "ball_start_lane_index": sampled_scene.ball_start_lane_index,
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
            },
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(axes.query_variant),
            scene_id="brick_breaker",
            query_id=str(axes.query_variant),
        )
        return rewrite_public_query_output(
            output,
            query_id=str(axes.query_variant),
            query_variant_probabilities=axes.query_variant_probabilities,
        )


@register_task
class GamesBrickBreakerTrajectoryTargetLabelTask(GamesBrickBreakerPlayfieldTask):
    """Identify the labeled target reached by the visible ball trajectory."""

    task_id = "task_games__brick_breaker__trajectory_target_label"
    supported_query_variants = ("next_hit_label", "paddle_catch_label")


@register_task
class GamesBrickBreakerHitRowRemainingCountTask(GamesBrickBreakerPlayfieldTask):
    """Count bricks remaining in the row after the shown shot removes one brick."""

    task_id = "task_games__brick_breaker__hit_row_remaining_count"
    supported_query_variants = ("hit_row_remaining_count",)


__all__ = [
    "GamesBrickBreakerHitRowRemainingCountTask",
    "GamesBrickBreakerPlayfieldTask",
    "GamesBrickBreakerTrajectoryTargetLabelTask",
]
