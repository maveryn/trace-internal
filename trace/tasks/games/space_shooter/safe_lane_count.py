"""Games Space-shooter tasks over enemies, shots, and safe lanes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from trace.tasks.shared.fixed_query import FixedQueryVariantTaskMixin
from ..shared.layout import resolve_games_layout_jitter
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from .shared.common import (
    SUPPORTED_SPACE_SHOOTER_QUERY_IDS,
    SUPPORTED_SPACE_SHOOTER_SCENE_VARIANTS,
    SUPPORTED_SPACE_SHOOTER_STYLE_VARIANTS,
    SpaceBlocker,
    SpaceEnemy,
    SpaceProjectile,
    SpaceShooterSample,
    lane_entity_id,
    validate_space_shooter_sample,
)
from .shared.rendering import SpaceShooterRenderParams, render_space_shooter_scene
from ..shared.visual_defaults import load_games_scene_noise_defaults


TASK_ID = "games_space_shooter_playfield_base"
SCENE_ID = "space_shooter"

_ENEMY_LABELS: Tuple[str, ...] = tuple(chr(ord("A") + index) for index in range(26))


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Space-shooter scenes."""

    clear_shot_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    clear_shot_score_enemy_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    clear_shot_score_value_support: Tuple[int, ...] = (1, 2, 3, 5, 10)
    projectile_intercept_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    safe_lane_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    lane_count_support: Tuple[int, ...] = (4, 5, 6, 7, 8)
    enemy_count_support: Tuple[int, ...] = (10, 11, 12, 13, 14, 15, 16)
    canvas_width: int = 1060
    canvas_height: int = 820
    panel_margin_px: int = 42
    playfield_width_px: int = 940
    playfield_height_px: int = 720
    playfield_border_width_px: int = 5
    lane_pad_height_px: int = 38
    lane_pad_gap_px: int = 10
    enemy_width_px: int = 62
    enemy_height_px: int = 48
    projectile_width_px: int = 18
    projectile_height_px: int = 42
    blocker_width_px: int = 70
    blocker_height_px: int = 42
    player_ship_width_px: int = 72
    player_ship_height_px: int = 58
    label_font_size_px: int = 24


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Space-shooter instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    lane_count: int
    enemy_count: int
    target_answer: int | None
    target_answer_support: Tuple[int, ...] | None
    clear_shot_score_value_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    lane_count_probabilities: Dict[str, float]
    enemy_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float] | None


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("games", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id="space_shooter", apply_prob=0.0)


def _target_support_key(query_id: str) -> str | None:
    """Return the configured answer-support key for one query."""

    return {
        "clear_shot_count": "clear_shot_count_support",
        "clear_shot_score_value": "clear_shot_score_enemy_count_support",
        "projectile_intercept_count": "projectile_intercept_count_support",
        "safe_lane_count": "safe_lane_count_support",
    }.get(str(query_id))


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Space-shooter query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_SPACE_SHOOTER_QUERY_IDS,
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
    """Resolve one balanced named Space-shooter axis."""

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
    """Resolve all semantic and visual axes for one Space-shooter instance."""

    query_id, query_id_probabilities = _resolve_query_id(instance_seed=int(instance_seed), params=params)
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SPACE_SHOOTER_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_SPACE_SHOOTER_STYLE_VARIANTS,
    )
    lane_count, lane_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="lane_count_support",
        explicit_key="lane_count",
        fallback_support=_DEFAULTS.lane_count_support,
        namespace=f"{TASK_ID}.lane_count",
        balanced_flag_key="balanced_lane_count_sampling",
        namespace_support_permutation=True,
    )
    enemy_count, enemy_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="enemy_count_support",
        explicit_key="enemy_count",
        fallback_support=_DEFAULTS.enemy_count_support,
        namespace=f"{TASK_ID}.enemy_count",
        balanced_flag_key="balanced_enemy_count_sampling",
        namespace_support_permutation=True,
    )
    target_answer: int | None = None
    target_answer_support: Tuple[int, ...] | None = None
    target_answer_probabilities: Dict[str, float] | None = None
    support_key = _target_support_key(str(query_id))
    if support_key is not None:
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            support_key=str(support_key),
            explicit_key="target_answer",
            fallback_support=getattr(_DEFAULTS, support_key),
            namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
        target_answer_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key=str(support_key),
            fallback=getattr(_DEFAULTS, support_key),
        )
        if str(query_id) in {"clear_shot_count", "clear_shot_score_value", "safe_lane_count"} and int(target_answer) > int(lane_count):
            if "lane_count" in params and params.get("lane_count") is not None:
                raise ValueError("target_answer cannot exceed lane_count for lane-count Space-shooter queries")
            lane_count = int(target_answer)
    clear_shot_score_value_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="clear_shot_score_value_support",
        fallback=_DEFAULTS.clear_shot_score_value_support,
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        lane_count=int(lane_count),
        enemy_count=int(enemy_count),
        target_answer=None if target_answer is None else int(target_answer),
        target_answer_support=target_answer_support,
        clear_shot_score_value_support=clear_shot_score_value_support,
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        lane_count_probabilities=dict(lane_count_probabilities),
        enemy_count_probabilities=dict(enemy_count_probabilities),
        target_answer_probabilities=None if target_answer_probabilities is None else dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> SpaceShooterRenderParams:
    """Resolve Space-shooter rendering parameters from config/defaults."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.space_shooter.font_family",
        params=params,
    )
    return SpaceShooterRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        playfield_width_px=int(params.get("playfield_width_px", group_default(_RENDER_DEFAULTS, "playfield_width_px", _DEFAULTS.playfield_width_px))),
        playfield_height_px=int(params.get("playfield_height_px", group_default(_RENDER_DEFAULTS, "playfield_height_px", _DEFAULTS.playfield_height_px))),
        playfield_border_width_px=int(params.get("playfield_border_width_px", group_default(_RENDER_DEFAULTS, "playfield_border_width_px", _DEFAULTS.playfield_border_width_px))),
        lane_pad_height_px=int(params.get("lane_pad_height_px", group_default(_RENDER_DEFAULTS, "lane_pad_height_px", _DEFAULTS.lane_pad_height_px))),
        lane_pad_gap_px=int(params.get("lane_pad_gap_px", group_default(_RENDER_DEFAULTS, "lane_pad_gap_px", _DEFAULTS.lane_pad_gap_px))),
        enemy_width_px=int(params.get("enemy_width_px", group_default(_RENDER_DEFAULTS, "enemy_width_px", _DEFAULTS.enemy_width_px))),
        enemy_height_px=int(params.get("enemy_height_px", group_default(_RENDER_DEFAULTS, "enemy_height_px", _DEFAULTS.enemy_height_px))),
        projectile_width_px=int(params.get("projectile_width_px", group_default(_RENDER_DEFAULTS, "projectile_width_px", _DEFAULTS.projectile_width_px))),
        projectile_height_px=int(params.get("projectile_height_px", group_default(_RENDER_DEFAULTS, "projectile_height_px", _DEFAULTS.projectile_height_px))),
        blocker_width_px=int(params.get("blocker_width_px", group_default(_RENDER_DEFAULTS, "blocker_width_px", _DEFAULTS.blocker_width_px))),
        blocker_height_px=int(params.get("blocker_height_px", group_default(_RENDER_DEFAULTS, "blocker_height_px", _DEFAULTS.blocker_height_px))),
        player_ship_width_px=int(params.get("player_ship_width_px", group_default(_RENDER_DEFAULTS, "player_ship_width_px", _DEFAULTS.player_ship_width_px))),
        player_ship_height_px=int(params.get("player_ship_height_px", group_default(_RENDER_DEFAULTS, "player_ship_height_px", _DEFAULTS.player_ship_height_px))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
        font_family=str(font_family),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.space_shooter.layout",
        ),
    )


def _entity_dx(rng) -> float:
    """Sample a small within-lane horizontal offset."""

    return float(rng.uniform(-0.20, 0.20))


def _entity_dy(rng) -> float:
    """Sample a small vertical offset."""

    return float(rng.uniform(-8.0, 8.0))


def _make_enemy(*, enemy_index: int, lane: int, y_slot: int, rng, score_value: int | None = None) -> SpaceEnemy:
    """Create one labeled enemy."""

    return SpaceEnemy(
        enemy_id=f"enemy_{int(enemy_index)}",
        label=str(_ENEMY_LABELS[int(enemy_index) % len(_ENEMY_LABELS)]),
        lane=int(lane),
        y_slot=int(y_slot),
        dx_frac=_entity_dx(rng),
        dy_px=_entity_dy(rng),
        score_value=None if score_value is None else int(score_value),
    )


def _make_projectile(*, projectile_index: int, lane: int, y_slot: int, rng, centered: bool = False) -> SpaceProjectile:
    """Create one enemy projectile."""

    return SpaceProjectile(
        projectile_id=f"projectile_{int(projectile_index)}",
        lane=int(lane),
        y_slot=int(y_slot),
        dx_frac=0.0 if bool(centered) else float(rng.uniform(-0.08, 0.08)),
        dy_px=_entity_dy(rng),
    )


def _make_blocker(*, blocker_index: int, lane: int, y_slot: int, rng, blocker_type: str | None = None) -> SpaceBlocker:
    """Create one shield/asteroid blocker."""

    return SpaceBlocker(
        blocker_id=f"blocker_{int(blocker_index)}",
        lane=int(lane),
        y_slot=int(y_slot),
        blocker_type=str(blocker_type or rng.choice(("shield", "asteroid"))),
        dx_frac=float(rng.uniform(-0.12, 0.12)),
        dy_px=_entity_dy(rng),
    )


def _claim_position(
    *,
    rng,
    occupied: set[Tuple[int, int]],
    lane_candidates: Sequence[int],
    slot_candidates: Sequence[int],
) -> Tuple[int, int]:
    """Claim one lane/vertical-slot pair so visible objects do not stack."""

    candidates = [
        (int(lane), int(slot))
        for lane in lane_candidates
        for slot in slot_candidates
        if (int(lane), int(slot)) not in occupied
    ]
    if not candidates:
        raise ValueError("no free space-shooter lane/slot position remains")
    lane, slot = rng.choice(candidates)
    occupied.add((int(lane), int(slot)))
    return int(lane), int(slot)


def _sample_clear_shot_scene(*, rng, axes: _ResolvedAxes) -> SpaceShooterSample:
    """Construct a clear-front-enemy count or score scene."""

    lane_count = int(axes.lane_count)
    target = min(int(axes.target_answer or 1), lane_count)
    score_query = str(axes.query_id) == "clear_shot_score_value"
    lanes = list(range(lane_count))
    rng.shuffle(lanes)
    clear_lanes = set(lanes[:target])
    blocked_lanes = [lane for lane in lanes[target:]]
    enemies: list[SpaceEnemy] = []
    blockers: list[SpaceBlocker] = []
    projectiles: list[SpaceProjectile] = []
    clear_enemy_ids: list[str] = []
    occupied: set[Tuple[int, int]] = set()

    for lane in range(lane_count):
        if lane in clear_lanes:
            _, slot = _claim_position(rng=rng, occupied=occupied, lane_candidates=(lane,), slot_candidates=(3, 4, 5))
            enemy = _make_enemy(
                enemy_index=len(enemies),
                lane=lane,
                y_slot=slot,
                rng=rng,
                score_value=int(rng.choice(axes.clear_shot_score_value_support)) if score_query else None,
            )
            enemies.append(enemy)
            clear_enemy_ids.append(str(enemy.enemy_id))
        else:
            _, blocker_slot = _claim_position(
                rng=rng,
                occupied=occupied,
                lane_candidates=(lane,),
                slot_candidates=(4, 5),
            )
            blockers.append(_make_blocker(blocker_index=len(blockers), lane=lane, y_slot=blocker_slot, rng=rng))
            upper_slots = tuple(slot for slot in (1, 2, 3) if int(slot) < int(blocker_slot))
            _, slot = _claim_position(rng=rng, occupied=occupied, lane_candidates=(lane,), slot_candidates=upper_slots)
            enemies.append(
                _make_enemy(
                    enemy_index=len(enemies),
                    lane=lane,
                    y_slot=slot,
                    rng=rng,
                    score_value=int(rng.choice(axes.clear_shot_score_value_support)) if score_query else None,
                )
            )
    for _ in range(max(1, lane_count // 3)):
        lane = int(rng.randrange(lane_count))
        if lane not in clear_lanes and rng.random() < 0.70:
            try:
                _, slot = _claim_position(rng=rng, occupied=occupied, lane_candidates=(lane,), slot_candidates=(3, 4, 5))
            except ValueError:
                continue
            blockers.append(_make_blocker(blocker_index=len(blockers), lane=lane, y_slot=slot, rng=rng))
    for index in range(max(1, lane_count // 4)):
        try:
            lane, slot = _claim_position(
                rng=rng,
                occupied=occupied,
                lane_candidates=blocked_lanes or range(lane_count),
                slot_candidates=(3, 4, 5),
            )
        except ValueError:
            continue
        projectiles.append(_make_projectile(projectile_index=index, lane=lane, y_slot=slot, rng=rng))
    highest_enemy = enemies[0]
    clear_id_set = set(clear_enemy_ids)
    answer = (
        sum(int(enemy.score_value or 0) for enemy in enemies if str(enemy.enemy_id) in clear_id_set)
        if score_query
        else int(len(clear_enemy_ids))
    )

    sample = SpaceShooterSample(
        lane_count=lane_count,
        mode=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        answer=int(answer),
        player_lane=int(rng.randrange(lane_count)),
        enemies=tuple(enemies),
        projectiles=tuple(projectiles),
        blockers=tuple(blockers),
        clear_enemy_ids=tuple(clear_enemy_ids),
        intercept_projectile_ids=tuple(),
        highest_threat_enemy_id=str(highest_enemy.enemy_id),
        highest_threat_label=str(highest_enemy.label),
        safe_lane_indices=tuple(),
        annotation_entity_ids=tuple(clear_enemy_ids),
        target_answer=int(target),
        construction_mode="front_enemy_clear_shot_score_sum" if score_query else "front_enemy_clear_shot_lanes",
    )
    validate_space_shooter_sample(sample)
    return sample


def _sample_projectile_scene(*, rng, axes: _ResolvedAxes) -> SpaceShooterSample:
    """Construct a scene where the target answer is projectiles aligned with the player."""

    lane_count = int(axes.lane_count)
    target = int(axes.target_answer or 1)
    player_lane = int(rng.randrange(lane_count))
    occupied: set[Tuple[int, int]] = set()
    projectiles: list[SpaceProjectile] = []
    target_slots = list(range(1, 6))
    rng.shuffle(target_slots)
    for slot in target_slots[:target]:
        occupied.add((int(player_lane), int(slot)))
        projectiles.append(
            _make_projectile(
                projectile_index=len(projectiles),
                lane=player_lane,
                y_slot=int(slot),
                rng=rng,
                centered=True,
            )
        )
    enemies: list[SpaceEnemy] = []
    while len(enemies) < int(axes.enemy_count):
        lane, slot = _claim_position(
            rng=rng,
            occupied=occupied,
            lane_candidates=range(lane_count),
            slot_candidates=(0, 1, 2, 3, 4, 5),
        )
        enemies.append(_make_enemy(enemy_index=len(enemies), lane=lane, y_slot=slot, rng=rng))
    for lane in range(lane_count):
        if lane == player_lane:
            continue
        if rng.random() < 0.45:
            try:
                _, slot = _claim_position(rng=rng, occupied=occupied, lane_candidates=(lane,), slot_candidates=(2, 3, 4, 5))
            except ValueError:
                continue
            projectiles.append(_make_projectile(projectile_index=len(projectiles), lane=lane, y_slot=slot, rng=rng))
    blockers: list[SpaceBlocker] = []
    non_player_lanes = tuple(lane for lane in range(lane_count) if int(lane) != int(player_lane))
    for _ in range(max(1, lane_count // 3)):
        try:
            lane, slot = _claim_position(
                rng=rng,
                occupied=occupied,
                lane_candidates=non_player_lanes,
                slot_candidates=(3, 4, 5),
            )
        except ValueError:
            continue
        blockers.append(_make_blocker(blocker_index=len(blockers), lane=lane, y_slot=slot, rng=rng))
    intercept_ids = tuple(str(projectile.projectile_id) for projectile in projectiles if int(projectile.lane) == int(player_lane))
    sample = SpaceShooterSample(
        lane_count=lane_count,
        mode=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        answer=int(len(intercept_ids)),
        player_lane=int(player_lane),
        enemies=tuple(enemies),
        projectiles=tuple(projectiles),
        blockers=tuple(blockers),
        clear_enemy_ids=tuple(),
        intercept_projectile_ids=intercept_ids,
        highest_threat_enemy_id=str(enemies[0].enemy_id),
        highest_threat_label=str(enemies[0].label),
        safe_lane_indices=tuple(),
        annotation_entity_ids=intercept_ids,
        target_answer=int(target),
        construction_mode="player_lane_projectile_intercepts",
    )
    validate_space_shooter_sample(sample)
    return sample


def _sample_highest_threat_scene(*, rng, axes: _ResolvedAxes) -> SpaceShooterSample:
    """Construct a scene with a unique lowest enemy."""

    lane_count = int(axes.lane_count)
    enemy_count = int(axes.enemy_count)
    target_index = int(rng.randrange(enemy_count))
    occupied: set[Tuple[int, int]] = set()
    enemies: list[SpaceEnemy] = []
    target_lane, target_slot = _claim_position(
        rng=rng,
        occupied=occupied,
        lane_candidates=range(lane_count),
        slot_candidates=(5,),
    )
    for index in range(enemy_count):
        if index == target_index:
            lane, y_slot = target_lane, target_slot
        else:
            lane, y_slot = _claim_position(
                rng=rng,
                occupied=occupied,
                lane_candidates=range(lane_count),
                slot_candidates=(0, 1, 2, 3, 4),
            )
        enemies.append(_make_enemy(enemy_index=index, lane=lane, y_slot=y_slot, rng=rng))
    blockers: list[SpaceBlocker] = []
    for _ in range(max(1, lane_count // 3)):
        try:
            lane, slot = _claim_position(
                rng=rng,
                occupied=occupied,
                lane_candidates=range(lane_count),
                slot_candidates=(3, 4),
            )
        except ValueError:
            continue
        blockers.append(_make_blocker(blocker_index=len(blockers), lane=lane, y_slot=slot, rng=rng))
    projectiles: list[SpaceProjectile] = []
    for _ in range(max(2, lane_count // 2)):
        try:
            lane, slot = _claim_position(
                rng=rng,
                occupied=occupied,
                lane_candidates=range(lane_count),
                slot_candidates=(3, 4, 5),
            )
        except ValueError:
            continue
        projectiles.append(_make_projectile(projectile_index=len(projectiles), lane=lane, y_slot=slot, rng=rng))
    target_enemy = enemies[target_index]
    sample = SpaceShooterSample(
        lane_count=lane_count,
        mode=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        answer=str(target_enemy.label),
        player_lane=int(rng.randrange(lane_count)),
        enemies=tuple(enemies),
        projectiles=tuple(projectiles),
        blockers=tuple(blockers),
        clear_enemy_ids=tuple(),
        intercept_projectile_ids=tuple(),
        highest_threat_enemy_id=str(target_enemy.enemy_id),
        highest_threat_label=str(target_enemy.label),
        safe_lane_indices=tuple(),
        annotation_entity_ids=(str(target_enemy.enemy_id),),
        target_answer=None,
        construction_mode="unique_lowest_enemy_threat",
    )
    validate_space_shooter_sample(sample)
    return sample


def _sample_safe_lane_scene(*, rng, axes: _ResolvedAxes) -> SpaceShooterSample:
    """Construct a scene where the target answer is the number of safe bottom lanes."""

    lane_count = int(axes.lane_count)
    target = min(int(axes.target_answer or 1), lane_count)
    lanes = list(range(lane_count))
    rng.shuffle(lanes)
    safe_lanes = tuple(sorted(lanes[:target]))
    unsafe_lanes = [lane for lane in range(lane_count) if lane not in set(safe_lanes)]
    occupied: set[Tuple[int, int]] = set()
    projectiles: list[SpaceProjectile] = []
    blockers: list[SpaceBlocker] = []
    for lane in unsafe_lanes:
        if rng.random() < 0.70:
            _, slot = _claim_position(rng=rng, occupied=occupied, lane_candidates=(lane,), slot_candidates=(3, 4, 5))
            projectiles.append(_make_projectile(projectile_index=len(projectiles), lane=lane, y_slot=slot, rng=rng))
        else:
            occupied.add((int(lane), 6))
            blockers.append(_make_blocker(blocker_index=len(blockers), lane=lane, y_slot=6, rng=rng, blocker_type="asteroid"))
    enemies: list[SpaceEnemy] = []
    enemy_target = min(int(axes.enemy_count), lane_count + int(rng.randrange(0, 3)))
    while len(enemies) < enemy_target:
        lane, slot = _claim_position(
            rng=rng,
            occupied=occupied,
            lane_candidates=range(lane_count),
            slot_candidates=(0, 1, 2),
        )
        enemies.append(_make_enemy(enemy_index=len(enemies), lane=lane, y_slot=slot, rng=rng))
    annotation_ids = tuple(lane_entity_id(lane) for lane in safe_lanes)
    sample = SpaceShooterSample(
        lane_count=lane_count,
        mode=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        answer=int(len(safe_lanes)),
        player_lane=int(rng.randrange(lane_count)),
        enemies=tuple(enemies),
        projectiles=tuple(projectiles),
        blockers=tuple(blockers),
        clear_enemy_ids=tuple(),
        intercept_projectile_ids=tuple(),
        highest_threat_enemy_id=str(enemies[0].enemy_id),
        highest_threat_label=str(enemies[0].label),
        safe_lane_indices=safe_lanes,
        annotation_entity_ids=annotation_ids,
        target_answer=int(target),
        construction_mode="safe_bottom_lane_count",
    )
    validate_space_shooter_sample(sample)
    return sample


def _sample_scene(*, rng, axes: _ResolvedAxes) -> SpaceShooterSample:
    """Construct one Space-shooter scene for the requested query."""

    query = str(axes.query_id)
    if query == "clear_shot_count":
        return _sample_clear_shot_scene(rng=rng, axes=axes)
    if query == "clear_shot_score_value":
        return _sample_clear_shot_scene(rng=rng, axes=axes)
    if query == "projectile_intercept_count":
        return _sample_projectile_scene(rng=rng, axes=axes)
    if query == "highest_threat_label":
        return _sample_highest_threat_scene(rng=rng, axes=axes)
    if query == "safe_lane_count":
        return _sample_safe_lane_scene(rng=rng, axes=axes)
    raise ValueError(f"unsupported Space-shooter query_id: {query}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Space-shooter JSON output."""

    if str(query_id) == "highest_threat_label":
        answer_value: int | str = "C"
        annotation_value = [[420, 260, 482, 308]]
    elif str(query_id) == "safe_lane_count":
        answer_value = 3
        annotation_value = [[115, 695, 205, 733], [360, 695, 450, 733], [610, 695, 700, 733]]
    elif str(query_id) == "clear_shot_score_value":
        answer_value = 8
        annotation_value = [[210, 180, 272, 228], [480, 260, 542, 308]]
    else:
        answer_value = 2
        annotation_value = [[210, 180, 272, 228], [480, 260, 542, 308]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesSpaceShooterPlayfieldTask:
    """Return one grounded query over a visible Space-shooter playfield."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: SpaceShooterSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

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
            namespace="games.space_shooter.panel_scene_style",
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
        rendered_scene = render_space_shooter_scene(
            lane_count=int(sampled_scene.lane_count),
            player_lane=int(sampled_scene.player_lane),
            enemies=sampled_scene.enemies,
            projectiles=sampled_scene.projectiles,
            blockers=sampled_scene.blockers,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            highlight_player_lane=str(axes.query_id) == "projectile_intercept_count",
            panel_style=panel_style,
        )
        annotation_bboxes = [
            list(rendered_scene.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.annotation_entity_ids
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
                "object_description_defense_wave",
                "space_shooter_lane_rule_text",
                "answer_hint_clear_shot_score_value",
                "annotation_hint_clear_shot_score_value",
                "answer_hint_clear_shot_count",
                "annotation_hint_clear_shot_count",
                "answer_hint_projectile_intercept_count",
                "annotation_hint_projectile_intercept_count",
                "answer_hint_highest_threat_label",
                "annotation_hint_highest_threat_label",
                "answer_hint_safe_lane_count",
                "annotation_hint_safe_lane_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            dynamic_slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "space_shooter_lane_rule_text": str(prompt_defaults["space_shooter_lane_rule_text"]),
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

        answer_gt = TypedValue(
            type="string" if str(axes.query_id) == "highest_threat_label" else "integer",
            value=sampled_scene.answer,
        )
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }

        enemy_trace = [
            {
                "enemy_id": str(enemy.enemy_id),
                "label": str(enemy.label),
                "score_value": None if enemy.score_value is None else int(enemy.score_value),
                "display_text": str(int(enemy.score_value)) if enemy.score_value is not None else str(enemy.label),
                "lane": int(enemy.lane),
                "y_slot": int(enemy.y_slot),
            }
            for enemy in sampled_scene.enemies
        ]
        projectile_trace = [
            {
                "projectile_id": str(projectile.projectile_id),
                "lane": int(projectile.lane),
                "y_slot": int(projectile.y_slot),
            }
            for projectile in sampled_scene.projectiles
        ]
        blocker_trace = [
            {
                "blocker_id": str(blocker.blocker_id),
                "lane": int(blocker.lane),
                "y_slot": int(blocker.y_slot),
                "blocker_type": str(blocker.blocker_type),
            }
            for blocker in sampled_scene.blockers
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_space_shooter_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "lane_count": int(sampled_scene.lane_count),
                    "player_lane": int(sampled_scene.player_lane),
                    "target_answer": sampled_scene.target_answer,
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
                    "lane_count": int(sampled_scene.lane_count),
                    "enemy_count": int(axes.enemy_count),
                    "projectile_count": len(sampled_scene.projectiles),
                    "blocker_count": len(sampled_scene.blockers),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "lane_count_probabilities": dict(axes.lane_count_probabilities),
                    "enemy_count_probabilities": dict(axes.enemy_count_probabilities),
                    "target_answer": sampled_scene.target_answer,
                    "target_answer_support": None
                    if axes.target_answer_support is None
                    else [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": axes.target_answer_probabilities,
                    "clear_shot_score_value_support": [int(value) for value in axes.clear_shot_score_value_support],
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "lane_count": int(sampled_scene.lane_count),
                "player_lane": int(sampled_scene.player_lane),
                "target_answer": sampled_scene.target_answer,
                "enemies": enemy_trace,
                "projectiles": projectile_trace,
                "blockers": blocker_trace,
                "clear_enemy_ids": [str(value) for value in sampled_scene.clear_enemy_ids],
                "intercept_projectile_ids": [str(value) for value in sampled_scene.intercept_projectile_ids],
                "highest_threat_enemy_id": str(sampled_scene.highest_threat_enemy_id),
                "highest_threat_label": str(sampled_scene.highest_threat_label),
                "safe_lane_indices": [int(value) for value in sampled_scene.safe_lane_indices],
                "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
            },
            "projected_annotation": {
                "bbox_set": [list(bbox) for bbox in annotation_bboxes],
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
            scene_id="space_shooter",
            query_id=str(axes.query_id),
        )


class GamesSpaceShooterClearShotCountTask(FixedQueryVariantTaskMixin, GamesSpaceShooterPlayfieldTask):
    """Count enemy ships with clear vertical shot lanes from the bottom pads."""

    task_id = "task_games__space_shooter__clear_shot_count"
    fixed_query_id = "clear_shot_count"


class GamesSpaceShooterClearShotScoreValueTask(FixedQueryVariantTaskMixin, GamesSpaceShooterPlayfieldTask):
    """Sum printed scores for enemy ships with clear vertical shot lanes."""

    task_id = "task_games__space_shooter__clear_shot_score_value"
    fixed_query_id = "clear_shot_score_value"


class GamesSpaceShooterProjectileInterceptCountTask(FixedQueryVariantTaskMixin, GamesSpaceShooterPlayfieldTask):
    """Count enemy projectiles aligned with the player ship."""

    task_id = "task_games__space_shooter__projectile_intercept_count"
    fixed_query_id = "projectile_intercept_count"


class GamesSpaceShooterHighestThreatLabelTask(FixedQueryVariantTaskMixin, GamesSpaceShooterPlayfieldTask):
    """Identify the labeled enemy closest to the bottom player baseline."""

    task_id = "task_games__space_shooter__highest_threat_label"
    fixed_query_id = "highest_threat_label"


@register_task
class GamesSpaceShooterSafeLaneCountTask(FixedQueryVariantTaskMixin, GamesSpaceShooterPlayfieldTask):
    """Count safe bottom lane pads."""

    task_id = "task_games__space_shooter__safe_lane_count"
    fixed_query_id = "safe_lane_count"


__all__ = [
    "GamesSpaceShooterClearShotCountTask",
    "GamesSpaceShooterClearShotScoreValueTask",
    "GamesSpaceShooterHighestThreatLabelTask",
    "GamesSpaceShooterPlayfieldTask",
    "GamesSpaceShooterProjectileInterceptCountTask",
    "GamesSpaceShooterSafeLaneCountTask",
]
