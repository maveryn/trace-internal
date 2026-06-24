"""Scene-local sampling primitives for space-shooter tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence, Tuple

from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support

from .defaults import DEFAULTS, GEN_DEFAULTS
from .rules import clear_shot_enemy_ids, enemy_projectile_ids_in_lane
from .state import (
    ENEMY_LABELS,
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_STYLE_VARIANTS,
    SceneAxes,
    SpaceEnemy,
    SpaceProjectile,
    SpaceShooterSample,
    lane_entity_id,
    validate_basic_space_shooter_sample,
)


def resolve_scene_axes(*, namespace: str, instance_seed: int, params: Mapping[str, Any]) -> SceneAxes:
    """Resolve visual and count axes shared by all space-shooter objectives."""

    from trace.tasks.games.shared.sampling import resolve_games_named_axis

    scene_variant, scene_variant_probabilities = resolve_games_named_axis(
        task_id=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=GEN_DEFAULTS,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported_variants=SUPPORTED_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = resolve_games_named_axis(
        task_id=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=GEN_DEFAULTS,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported_variants=SUPPORTED_STYLE_VARIANTS,
    )
    lane_count, lane_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=GEN_DEFAULTS,
        support_key="lane_count_support",
        explicit_key="lane_count",
        fallback_support=DEFAULTS.lane_count_support,
        namespace=f"{namespace}.lane_count",
        balanced_flag_key="balanced_lane_count_sampling",
        namespace_support_permutation=True,
    )
    enemy_count, enemy_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=GEN_DEFAULTS,
        support_key="enemy_count_support",
        explicit_key="enemy_count",
        fallback_support=DEFAULTS.enemy_count_support,
        namespace=f"{namespace}.enemy_count",
        balanced_flag_key="balanced_enemy_count_sampling",
        namespace_support_permutation=True,
    )
    score_support = resolve_integer_support(
        params,
        gen_defaults=GEN_DEFAULTS,
        key="clear_shot_score_value_support",
        fallback=DEFAULTS.clear_shot_score_value_support,
    )
    return SceneAxes(
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        lane_count=int(lane_count),
        enemy_count=int(enemy_count),
        clear_shot_score_value_support=score_support,
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        lane_count_probabilities=dict(lane_count_probabilities),
        enemy_count_probabilities=dict(enemy_count_probabilities),
    )


def resolve_target_answer(
    *,
    namespace: str,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    fallback_support: Sequence[int],
) -> tuple[int, tuple[int, ...], dict[str, float]]:
    """Resolve one balanced integer target answer for controlled count tasks."""

    target_answer, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=tuple(int(value) for value in fallback_support),
        namespace=f"{namespace}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    support = resolve_integer_support(
        params,
        gen_defaults=GEN_DEFAULTS,
        key=str(support_key),
        fallback=tuple(int(value) for value in fallback_support),
    )
    return int(target_answer), tuple(int(value) for value in support), dict(probabilities)


def _entity_dx(rng) -> float:
    return float(rng.uniform(-0.20, 0.20))


def _entity_dy(rng) -> float:
    return float(rng.uniform(-8.0, 8.0))


def _make_enemy(*, enemy_index: int, lane: int, y_slot: int, rng, score_value: int | None = None) -> SpaceEnemy:
    return SpaceEnemy(
        enemy_id=f"enemy_{int(enemy_index)}",
        label=str(ENEMY_LABELS[int(enemy_index) % len(ENEMY_LABELS)]),
        lane=int(lane),
        y_slot=int(y_slot),
        dx_frac=_entity_dx(rng),
        dy_px=_entity_dy(rng),
        score_value=None if score_value is None else int(score_value),
    )


def _make_projectile(
    *,
    projectile_index: int,
    lane: int,
    y_slot: int,
    owner: str,
    rng,
    centered: bool = False,
) -> SpaceProjectile:
    return SpaceProjectile(
        projectile_id=f"{str(owner)}_projectile_{int(projectile_index)}",
        owner=str(owner),
        lane=int(lane),
        y_slot=int(y_slot),
        dx_frac=0.0 if bool(centered) else float(rng.uniform(-0.08, 0.08)),
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


def sample_clear_shot_scene(
    *,
    rng,
    axes: SceneAxes,
    target_answer: int,
    score_query: bool,
) -> SpaceShooterSample:
    """Construct a clear-front-enemy count or score scene."""

    required_lanes = int(target_answer) + 1 if bool(score_query) else int(target_answer)
    lane_count = max(required_lanes, int(axes.lane_count))
    target = min(int(target_answer), lane_count)
    lanes = list(range(lane_count))
    rng.shuffle(lanes)
    clear_lanes = set(lanes[:target])
    blocked_lanes = [lane for lane in lanes[target:]]
    enemies: list[SpaceEnemy] = []
    projectiles: list[SpaceProjectile] = []
    occupied: set[Tuple[int, int]] = set()

    for lane in range(lane_count):
        if lane in clear_lanes:
            _, slot = _claim_position(rng=rng, occupied=occupied, lane_candidates=(lane,), slot_candidates=(3, 4, 5))
            enemies.append(
                _make_enemy(
                    enemy_index=len(enemies),
                    lane=lane,
                    y_slot=slot,
                    rng=rng,
                    score_value=int(rng.choice(axes.clear_shot_score_value_support)) if score_query else None,
                )
            )
        else:
            _, player_shot_slot = _claim_position(rng=rng, occupied=occupied, lane_candidates=(lane,), slot_candidates=(4, 5))
            projectiles.append(
                _make_projectile(
                    projectile_index=len(projectiles),
                    lane=lane,
                    y_slot=player_shot_slot,
                    owner="player",
                    rng=rng,
                    centered=True,
                )
            )
            upper_slots = tuple(slot for slot in (1, 2, 3) if int(slot) < int(player_shot_slot))
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
        projectiles.append(
            _make_projectile(
                projectile_index=len(projectiles),
                lane=lane,
                y_slot=slot,
                owner="enemy",
                rng=rng,
            )
        )

    clear_ids = clear_shot_enemy_ids(tuple(enemies), tuple(projectiles))
    clear_id_set = set(clear_ids)
    answer = (
        sum(int(enemy.score_value or 0) for enemy in enemies if str(enemy.enemy_id) in clear_id_set)
        if bool(score_query)
        else int(len(clear_ids))
    )
    sample = SpaceShooterSample(
        lane_count=lane_count,
        scene_variant=str(axes.scene_variant),
        answer=int(answer),
        player_lane=int(rng.randrange(lane_count)),
        enemies=tuple(enemies),
        projectiles=tuple(projectiles),
        clear_enemy_ids=tuple(clear_ids),
        intercept_projectile_ids=tuple(),
        lowest_enemy_id=str(enemies[0].enemy_id),
        lowest_enemy_label=str(enemies[0].label),
        safe_lane_indices=tuple(),
        annotation_entity_ids=tuple(clear_ids),
        target_answer=int(target),
        construction_mode="front_enemy_clear_shot_score_sum" if bool(score_query) else "front_enemy_clear_shot_lanes",
        metadata={
            "score_query": bool(score_query),
            "target_answer": int(target),
            "target_answer_support": list(DEFAULTS.clear_shot_score_enemy_count_support if bool(score_query) else DEFAULTS.clear_shot_count_support),
        },
    )
    validate_basic_space_shooter_sample(sample)
    if len(clear_ids) != int(target):
        raise ValueError("clear-shot sample did not achieve target count")
    if bool(score_query) and not any(
        str(enemy.enemy_id) not in clear_id_set and enemy.score_value is not None for enemy in enemies
    ):
        raise ValueError("clear-shot score scene requires scored blocked enemies as distractors")
    return sample


def sample_projectile_intercept_scene(
    *,
    rng,
    axes: SceneAxes,
    target_answer: int,
) -> SpaceShooterSample:
    """Construct a scene where target projectiles share the player lane."""

    lane_count = int(axes.lane_count)
    target = int(target_answer)
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
                owner="enemy",
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
            projectiles.append(
                _make_projectile(
                    projectile_index=len(projectiles),
                    lane=lane,
                    y_slot=slot,
                    owner="enemy",
                    rng=rng,
                )
            )
    non_player_lanes = tuple(lane for lane in range(lane_count) if int(lane) != int(player_lane))
    for _ in range(max(1, lane_count // 4)):
        try:
            lane, slot = _claim_position(
                rng=rng,
                occupied=occupied,
                lane_candidates=non_player_lanes,
                slot_candidates=(4, 5),
            )
        except ValueError:
            continue
        projectiles.append(
            _make_projectile(
                projectile_index=len(projectiles),
                lane=lane,
                y_slot=slot,
                owner="player",
                rng=rng,
            )
        )
    intercept_ids = enemy_projectile_ids_in_lane(tuple(projectiles), int(player_lane))
    sample = SpaceShooterSample(
        lane_count=lane_count,
        scene_variant=str(axes.scene_variant),
        answer=int(len(intercept_ids)),
        player_lane=int(player_lane),
        enemies=tuple(enemies),
        projectiles=tuple(projectiles),
        clear_enemy_ids=tuple(),
        intercept_projectile_ids=intercept_ids,
        lowest_enemy_id=str(enemies[0].enemy_id),
        lowest_enemy_label=str(enemies[0].label),
        safe_lane_indices=tuple(),
        annotation_entity_ids=intercept_ids,
        target_answer=int(target),
        construction_mode="player_lane_projectile_intercepts",
        metadata={
            "target_answer": int(target),
            "target_answer_support": list(DEFAULTS.projectile_intercept_count_support),
        },
    )
    validate_basic_space_shooter_sample(sample)
    if len(intercept_ids) != int(target):
        raise ValueError("projectile scene did not achieve target count")
    return sample


def sample_unique_lowest_enemy_scene(*, rng, axes: SceneAxes) -> SpaceShooterSample:
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
    projectiles: list[SpaceProjectile] = []
    for _ in range(max(2, lane_count // 2)):
        try:
            lane, slot = _claim_position(rng=rng, occupied=occupied, lane_candidates=range(lane_count), slot_candidates=(3, 4, 5))
        except ValueError:
            continue
        projectiles.append(
            _make_projectile(
                projectile_index=len(projectiles),
                lane=lane,
                y_slot=slot,
                owner="enemy" if rng.random() < 0.65 else "player",
                rng=rng,
            )
        )
    target_enemy = enemies[target_index]
    sample = SpaceShooterSample(
        lane_count=lane_count,
        scene_variant=str(axes.scene_variant),
        answer=str(target_enemy.label),
        player_lane=int(rng.randrange(lane_count)),
        enemies=tuple(enemies),
        projectiles=tuple(projectiles),
        clear_enemy_ids=tuple(),
        intercept_projectile_ids=tuple(),
        lowest_enemy_id=str(target_enemy.enemy_id),
        lowest_enemy_label=str(target_enemy.label),
        safe_lane_indices=tuple(),
        annotation_entity_ids=(str(target_enemy.enemy_id),),
        target_answer=None,
        construction_mode="unique_lowest_enemy_threat",
        metadata={"target_answer": None},
    )
    validate_basic_space_shooter_sample(sample)
    return sample


def sample_safe_lane_scene(*, rng, axes: SceneAxes, target_answer: int) -> SpaceShooterSample:
    """Construct a scene where target answer is the number of safe bottom lanes."""

    lane_count = max(int(target_answer), int(axes.lane_count))
    target = min(int(target_answer), lane_count)
    lanes = list(range(lane_count))
    rng.shuffle(lanes)
    safe_lanes = tuple(sorted(lanes[:target]))
    unsafe_lanes = [lane for lane in range(lane_count) if lane not in set(safe_lanes)]
    occupied: set[Tuple[int, int]] = set()
    projectiles: list[SpaceProjectile] = []
    for lane in unsafe_lanes:
        _, slot = _claim_position(rng=rng, occupied=occupied, lane_candidates=(lane,), slot_candidates=(3, 4, 5))
        projectiles.append(
            _make_projectile(
                projectile_index=len(projectiles),
                lane=lane,
                y_slot=slot,
                owner="enemy",
                rng=rng,
            )
        )
    for lane in safe_lanes:
        if rng.random() < 0.45:
            try:
                _, slot = _claim_position(rng=rng, occupied=occupied, lane_candidates=(lane,), slot_candidates=(4, 5))
            except ValueError:
                continue
            projectiles.append(
                _make_projectile(
                    projectile_index=len(projectiles),
                    lane=lane,
                    y_slot=slot,
                    owner="player",
                    rng=rng,
                )
            )
    enemies: list[SpaceEnemy] = []
    enemy_target = min(int(axes.enemy_count), lane_count + int(rng.randrange(0, 3)))
    while len(enemies) < enemy_target:
        lane, slot = _claim_position(rng=rng, occupied=occupied, lane_candidates=range(lane_count), slot_candidates=(0, 1, 2))
        enemies.append(_make_enemy(enemy_index=len(enemies), lane=lane, y_slot=slot, rng=rng))
    annotation_ids = tuple(lane_entity_id(lane) for lane in safe_lanes)
    sample = SpaceShooterSample(
        lane_count=lane_count,
        scene_variant=str(axes.scene_variant),
        answer=int(len(safe_lanes)),
        player_lane=int(rng.randrange(lane_count)),
        enemies=tuple(enemies),
        projectiles=tuple(projectiles),
        clear_enemy_ids=tuple(),
        intercept_projectile_ids=tuple(),
        lowest_enemy_id=str(enemies[0].enemy_id),
        lowest_enemy_label=str(enemies[0].label),
        safe_lane_indices=safe_lanes,
        annotation_entity_ids=annotation_ids,
        target_answer=int(target),
        construction_mode="safe_bottom_lane_count",
        metadata={
            "target_answer": int(target),
            "target_answer_support": list(DEFAULTS.safe_lane_count_support),
        },
    )
    validate_basic_space_shooter_sample(sample)
    return sample
