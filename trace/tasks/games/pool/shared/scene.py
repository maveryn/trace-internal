"""Scene-local primitives for pool games tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import group_default, required_group_defaults
from trace.tasks.shared.font_assets import get_font_family_record, sample_font_family
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support
from .common import (
    POOL_BALL_NUMBERS,
    POOL_POCKETS,
    SUPPORTED_POOL_SCENE_VARIANTS,
    PoolBall,
    PoolSample,
    ball_entity_id,
    ball_group,
    balls_on_segment,
    object_balls,
    point_distance,
    sorted_ids,
    validate_pool_sample,
)
from .rendering import PoolRenderParams, render_pool_table_scene
from trace.tasks.games.shared.layout import resolve_games_layout_jitter
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.style import SUPPORTED_POOL_STYLE_VARIANTS
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "pool"
GROUP_BALL_COUNT_QUERY_ID = "current_group_ball_count"
BLOCKING_BALL_COUNT_QUERY_ID = "blocking_ball_count"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Pool-table scenes."""

    current_group_ball_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    blocking_ball_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    object_ball_count_support: Tuple[int, ...] = (7, 8, 9, 10)
    line_clearance: float = 0.055
    min_ball_distance: float = 0.075
    canvas_width: int = 1120
    canvas_height: int = 760
    panel_margin_px: int = 42
    table_width_px: int = 940
    table_height_px: int = 520
    rail_width_px: int = 44
    pocket_radius_px: int = 24
    ball_radius_px: int = 18
    ball_number_font_size_px: int = 15
    badge_font_size_px: int = 22


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Pool-table instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    object_ball_count: int
    target_answer: int
    target_answer_support: Tuple[int, ...]
    line_clearance: float
    min_ball_distance: float
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    object_ball_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class GeneratedComponents:
    """Prompt, answer, annotation, image, and trace payload for one pool sample."""

    prompt: str
    prompt_variants: Dict[str, Any]
    answer_gt: TypedValue
    annotation_gt: TypedValue
    image: Image.Image
    trace_payload: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def _target_support_key(query_id: str) -> str:
    """Return the configured answer-support key for one Pool query."""

    return {
        "current_group_ball_count": "current_group_ball_count_support",
        "blocking_ball_count": "blocking_ball_count_support",
    }[str(query_id)]


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    namespace_root: str,
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named Pool axis."""

    return resolve_games_named_axis(
        task_id=str(namespace_root),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(item) for item in supported],
    )


def resolve_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Pool-table instance."""

    cycle_params = dict(params)
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_POOL_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=cycle_params,
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_POOL_STYLE_VARIANTS,
    )
    object_ball_count, object_ball_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=cycle_params,
        gen_defaults=gen_defaults,
        support_key="object_ball_count_support",
        explicit_key="object_ball_count",
        fallback_support=_DEFAULTS.object_ball_count_support,
        namespace=f"{str(namespace)}.object_ball_count.{str(query_id)}",
        balanced_flag_key="balanced_object_ball_count_sampling",
        namespace_support_permutation=True,
    )
    support_key = _target_support_key(str(query_id))
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=cycle_params,
        gen_defaults=gen_defaults,
        support_key=support_key,
        explicit_key="target_answer",
        fallback_support=getattr(_DEFAULTS, support_key),
        namespace=f"{str(namespace)}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        cycle_params,
        gen_defaults=gen_defaults,
        key=support_key,
        fallback=getattr(_DEFAULTS, support_key),
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        object_ball_count=int(object_ball_count),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        line_clearance=float(params.get("line_clearance", group_default(gen_defaults, "line_clearance", _DEFAULTS.line_clearance))),
        min_ball_distance=float(params.get("min_ball_distance", group_default(gen_defaults, "min_ball_distance", _DEFAULTS.min_ball_distance))),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        object_ball_count_probabilities=dict(object_ball_count_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    namespace: str,
    instance_seed: int,
) -> PoolRenderParams:
    """Resolve Pool rendering parameters from config/defaults."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{str(namespace)}.font_family",
        params=params,
    )
    return PoolRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(render_defaults, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(render_defaults, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(render_defaults, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        table_width_px=int(params.get("table_width_px", group_default(render_defaults, "table_width_px", _DEFAULTS.table_width_px))),
        table_height_px=int(params.get("table_height_px", group_default(render_defaults, "table_height_px", _DEFAULTS.table_height_px))),
        rail_width_px=int(params.get("rail_width_px", group_default(render_defaults, "rail_width_px", _DEFAULTS.rail_width_px))),
        pocket_radius_px=int(params.get("pocket_radius_px", group_default(render_defaults, "pocket_radius_px", _DEFAULTS.pocket_radius_px))),
        ball_radius_px=int(params.get("ball_radius_px", group_default(render_defaults, "ball_radius_px", _DEFAULTS.ball_radius_px))),
        ball_number_font_size_px=int(params.get("ball_number_font_size_px", group_default(render_defaults, "ball_number_font_size_px", _DEFAULTS.ball_number_font_size_px))),
        badge_font_size_px=int(params.get("badge_font_size_px", group_default(render_defaults, "badge_font_size_px", _DEFAULTS.badge_font_size_px))),
        font_family=str(font_family),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            render_defaults,
            instance_seed=int(instance_seed),
            namespace=f"{str(namespace)}.layout",
        ),
    )


def _is_inside_table(point: Tuple[float, float]) -> bool:
    """Return whether a normalized point is inside the playable table area."""

    x, y = point
    return 0.075 <= float(x) <= 0.925 and 0.095 <= float(y) <= 0.905


def _add_ball(
    balls: list[PoolBall],
    *,
    number: int,
    center: Tuple[float, float],
    is_marked: bool = False,
) -> None:
    """Append one ball to the generated layout."""

    balls.append(
        PoolBall(
            ball_id=ball_entity_id(int(number)),
            number=int(number),
            group=ball_group(int(number)),
            center=(round(float(center[0]), 5), round(float(center[1]), 5)),
            is_cue=bool(int(number) == 0),
            is_marked=bool(is_marked),
        )
    )


def _position_available(center: Tuple[float, float], balls: Sequence[PoolBall], *, min_distance: float) -> bool:
    """Return whether a new ball can be placed at a center."""

    return _is_inside_table(center) and all(point_distance(center, ball.center) >= float(min_distance) for ball in balls)


def _sample_free_position(rng, balls: Sequence[PoolBall], *, min_distance: float) -> Tuple[float, float]:
    """Sample one non-overlapping object-ball position."""

    for _ in range(800):
        center = (float(rng.uniform(0.10, 0.90)), float(rng.uniform(0.13, 0.87)))
        if _position_available(center, balls, min_distance=float(min_distance)):
            return center
    raise ValueError("failed to sample non-overlapping pool ball")


def _group_display_name(group: str) -> str:
    """Return prompt-facing pool group text."""

    return "solids" if str(group) == "solid" else "stripes"


def _current_group_layout(
    *,
    rng,
    object_ball_count: int,
    target_answer: int,
    params: Mapping[str, Any],
    min_ball_distance: float,
) -> PoolSample:
    """Construct a pool layout with a controlled current-group ball count."""

    group = str(params.get("current_player_group", rng.choice(("solid", "stripe"))))
    if group not in {"solid", "stripe"}:
        raise ValueError(f"unsupported current_player_group={group!r}")
    group_numbers = tuple(range(1, 8)) if group == "solid" else tuple(range(9, 16))
    distractor_numbers = (tuple(range(9, 16)) if group == "solid" else tuple(range(1, 8))) + (8,)
    if int(target_answer) > len(group_numbers):
        raise ValueError("pool current-group answer exceeds group size")
    distractor_count = int(object_ball_count) - int(target_answer)
    if int(distractor_count) < 0 or int(distractor_count) > len(distractor_numbers):
        raise ValueError("pool current-group distractor count is infeasible")

    selected_group = list(rng.sample(group_numbers, int(target_answer)))
    selected_distractors = list(rng.sample(distractor_numbers, int(distractor_count)))
    selected = selected_group + selected_distractors
    rng.shuffle(selected)

    balls: list[PoolBall] = []
    cue_center = (float(rng.uniform(0.135, 0.235)), float(rng.uniform(0.42, 0.58)))
    _add_ball(balls, number=0, center=cue_center)
    for number in selected:
        _add_ball(
            balls,
            number=int(number),
            center=_sample_free_position(rng, balls, min_distance=float(min_ball_distance)),
        )

    annotation_ids = sorted_ids(ball_entity_id(int(number)) for number in selected_group)
    sample = PoolSample(
        mode="current_group_ball_count",
        scene_variant="standard_table",
        answer=int(target_answer),
        balls=tuple(balls),
        pockets=POOL_POCKETS,
        cue_ball_id="cue_ball",
        marked_ball_id=None,
        marked_pocket_id=None,
        current_player_group=str(group),
        annotation_ball_ids=annotation_ids,
        annotation_pocket_ids=tuple(),
        blocking_ball_ids=tuple(),
        target_answer=int(target_answer),
        construction_mode=f"current_group_{group}_visible_count",
    )
    validate_pool_sample(sample)
    return sample


def _point_on_segment(
    start: Tuple[float, float],
    end: Tuple[float, float],
    *,
    t: float,
    offset: float,
) -> Tuple[float, float]:
    """Return one point near a shot segment."""

    sx, sy = start
    ex, ey = end
    vx = float(ex - sx)
    vy = float(ey - sy)
    length = max(1e-6, (vx * vx + vy * vy) ** 0.5)
    nx = -vy / length
    ny = vx / length
    return (float(sx + (t * vx) + (offset * nx)), float(sy + (t * vy) + (offset * ny)))


def _blocking_layout(
    *,
    rng,
    target_answer: int,
    params: Mapping[str, Any],
    min_ball_distance: float,
    line_clearance: float,
) -> PoolSample:
    """Construct a marked two-segment shot with a controlled blocker count."""

    min_distance = float(min_ball_distance)
    clearance = float(line_clearance)
    cue_center = (float(rng.uniform(0.145, 0.185)), float(rng.uniform(0.48, 0.56)))
    target_center = (float(rng.uniform(0.48, 0.56)), float(rng.uniform(0.36, 0.46)))
    pocket = POOL_POCKETS[2] if target_center[1] < 0.50 else POOL_POCKETS[5]
    target_number = int(rng.choice([2, 3, 4, 5, 6, 9, 10, 11, 12, 13]))
    balls: list[PoolBall] = []
    _add_ball(balls, number=0, center=cue_center)
    _add_ball(balls, number=target_number, center=target_center, is_marked=True)

    used_numbers = {0, target_number}
    blocker_ids: list[str] = []
    blocker_ts = [0.34, 0.54, 0.72, 0.86]
    for index in range(int(target_answer)):
        segment_start, segment_end = (cue_center, target_center) if index % 2 == 0 else (target_center, pocket.center)
        center = _point_on_segment(
            segment_start,
            segment_end,
            t=blocker_ts[index % len(blocker_ts)],
            offset=float(rng.uniform(-0.010, 0.010)),
        )
        if not _position_available(center, balls, min_distance=float(min_distance) * 0.70):
            raise ValueError("failed to place pool blocker")
        number = next(value for value in POOL_BALL_NUMBERS if value not in used_numbers)
        used_numbers.add(int(number))
        _add_ball(balls, number=int(number), center=center)
        blocker_ids.append(ball_entity_id(int(number)))

    foil_count = int(rng.randint(5, 8))
    for _ in range(foil_count):
        number = next(value for value in POOL_BALL_NUMBERS if value not in used_numbers)
        used_numbers.add(int(number))
        for _attempt in range(400):
            center = _sample_free_position(rng, balls, min_distance=float(min_distance))
            if (
                point_distance(center, cue_center) > 0.11
                and point_distance(center, target_center) > 0.11
                and point_distance(center, pocket.center) > 0.11
                and not balls_on_segment(
                    balls=[PoolBall("candidate", number, ball_group(number), center)],
                    start=cue_center,
                    end=target_center,
                    ignore_ball_ids=(),
                    clearance=float(clearance),
                )
                and not balls_on_segment(
                    balls=[PoolBall("candidate", number, ball_group(number), center)],
                    start=target_center,
                    end=pocket.center,
                    ignore_ball_ids=(),
                    clearance=float(clearance),
                )
            ):
                _add_ball(balls, number=int(number), center=center)
                break
        else:
            raise ValueError("failed to place pool foil")

    target_id = ball_entity_id(target_number)
    segment_a = balls_on_segment(
        balls=balls,
        start=cue_center,
        end=target_center,
        ignore_ball_ids=("cue_ball", target_id),
        clearance=float(clearance),
    )
    segment_b = balls_on_segment(
        balls=balls,
        start=target_center,
        end=pocket.center,
        ignore_ball_ids=(target_id,),
        clearance=float(clearance),
    )
    actual_blockers = sorted_ids(ball.ball_id for ball in (*segment_a, *segment_b))
    if len(actual_blockers) != int(target_answer):
        raise ValueError("constructed pool blocker count did not match target")
    sample = PoolSample(
        mode="blocking_ball_count",
        scene_variant="standard_table",
        answer=int(target_answer),
        balls=tuple(balls),
        pockets=POOL_POCKETS,
        cue_ball_id="cue_ball",
        marked_ball_id=str(target_id),
        marked_pocket_id=str(pocket.pocket_id),
        current_player_group=None,
        annotation_ball_ids=actual_blockers,
        annotation_pocket_ids=tuple(),
        blocking_ball_ids=actual_blockers,
        target_answer=int(target_answer),
        construction_mode="marked_two_segment_shot_with_controlled_blockers",
    )
    validate_pool_sample(sample)
    return sample


def sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> PoolSample:
    """Construct one Pool-table scene for the requested axes."""

    if str(axes.query_id) == "blocking_ball_count":
        sample = _blocking_layout(
            rng=rng,
            target_answer=int(axes.target_answer),
            params=params,
            min_ball_distance=float(axes.min_ball_distance),
            line_clearance=float(axes.line_clearance),
        )
        return replace(sample, scene_variant=str(axes.scene_variant))
    if str(axes.query_id) == "current_group_ball_count":
        sample = _current_group_layout(
            rng=rng,
            object_ball_count=int(axes.object_ball_count),
            target_answer=int(axes.target_answer),
            params=params,
            min_ball_distance=float(axes.min_ball_distance),
        )
        return replace(sample, scene_variant=str(axes.scene_variant))

    raise ValueError(f"unsupported Pool query_id: {axes.query_id}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Pool JSON output."""

    answer_value = 2 if str(query_id) == "blocking_ball_count" else 3
    annotation_value = [[200, 240], [540, 330]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def build_components(
    *,
    sampled_scene: PoolSample,
    axes: _ResolvedAxes,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    namespace: str,
) -> GeneratedComponents:
    """Render and package one pool sample without public task identity."""

    render_params = _render_params(
        params,
        render_defaults=render_defaults,
        namespace=str(namespace),
        instance_seed=int(instance_seed),
    )
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{str(namespace)}.panel_scene_style",
        treatment_weights=params.get(
            "panel_scene_treatment_weights",
            group_default(render_defaults, "panel_scene_treatment_weights", None),
        ),
        palette_weights=params.get(
            "panel_scene_palette_weights",
            group_default(render_defaults, "panel_scene_palette_weights", None),
        ),
    )
    background, background_meta = make_panel_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=panel_style,
    )
    badge_text = ""
    if sampled_scene.current_player_group:
        badge_text = f"Current player: {_group_display_name(str(sampled_scene.current_player_group)).upper()}"
    rendered_scene = render_pool_table_scene(
        balls=sampled_scene.balls,
        pockets=sampled_scene.pockets,
        background=background,
        style_variant=str(axes.style_variant),
        badge_text=badge_text,
        marked_ball_id=sampled_scene.marked_ball_id,
        marked_pocket_id=sampled_scene.marked_pocket_id,
        shot_path_ball_id=sampled_scene.marked_ball_id if str(axes.query_id) == BLOCKING_BALL_COUNT_QUERY_ID else None,
        shot_path_pocket_id=sampled_scene.marked_pocket_id if str(axes.query_id) == BLOCKING_BALL_COUNT_QUERY_ID else None,
        params=render_params,
        panel_style=panel_style,
    )
    annotation_entity_ids = [*sampled_scene.annotation_ball_ids, *sampled_scene.annotation_pocket_ids]
    annotation_points = [
        list(rendered_scene.render_map["ball_points_px"][entity_id])
        if entity_id in rendered_scene.render_map["ball_points_px"]
        else list(rendered_scene.render_map["pocket_points_px"][entity_id])
        for entity_id in annotation_entity_ids
    ]
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    prompt_defaults_checked = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_standard_table",
            "marked_shot_rule_text",
            "answer_hint_current_group_ball_count",
            "answer_hint_blocking_ball_count",
            "annotation_hint_current_group_ball_count",
            "annotation_hint_blocking_ball_count",
        ),
        context=f"prompt defaults for {SCENE_ID}.{axes.query_id}",
    )
    json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
    group_text = _group_display_name(str(sampled_scene.current_player_group)) if sampled_scene.current_player_group else ""
    prompt_selection = render_scene_prompt_variants(
        domain="games",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults_checked["bundle_id"]),
        scene_key=str(prompt_defaults_checked["scene_key"]),
        task_key=str(prompt_defaults_checked["task_key"]),
        query_key=str(axes.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "object_description": str(prompt_defaults_checked[f"object_description_{str(axes.scene_variant)}"]),
            "json_output_contract": str(prompt_defaults_checked["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults_checked["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults_checked[f"answer_hint_{str(axes.query_id)}"]),
            "annotation_hint": str(prompt_defaults_checked[f"annotation_hint_{str(axes.query_id)}"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            "marked_shot_rule_text": str(prompt_defaults_checked["marked_shot_rule_text"]),
            "current_player_group": str(group_text),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
    annotation_gt = TypedValue(type="point_set", value=[list(point) for point in annotation_points])
    text_style_meta = {
        "font_family": str(render_params.font_family),
        "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
    }
    ball_trace = [
        {
            "ball_id": str(ball.ball_id),
            "number": int(ball.number),
            "group": str(ball.group),
            "center": [float(ball.center[0]), float(ball.center[1])],
            "is_cue": bool(ball.is_cue),
            "is_marked": bool(ball.is_marked),
        }
        for ball in sampled_scene.balls
    ]
    trace_payload = {
        "scene_ir": {
            "scene_kind": f"games_pool_table_{str(axes.scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.scene_entities],
            "relations": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "target_answer": int(sampled_scene.target_answer),
                "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
            },
        },
        "query_spec": {
            "query_id": str(axes.query_id),
            "template_id": str(prompt_defaults_checked["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "object_ball_count": int(axes.object_ball_count),
                "current_player_group": sampled_scene.current_player_group,
                "marked_ball_id": sampled_scene.marked_ball_id,
                "marked_pocket_id": sampled_scene.marked_pocket_id,
                "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                "query_id_probabilities": dict(axes.query_id_probabilities),
                "style_variant_probabilities": dict(axes.style_variant_probabilities),
                "object_ball_count_probabilities": dict(axes.object_ball_count_probabilities),
                "target_answer": int(sampled_scene.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "target_answer_probabilities": dict(axes.target_answer_probabilities),
                "line_clearance": float(axes.line_clearance),
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
            "object_ball_count": len(object_balls(sampled_scene.balls)),
            "target_answer": int(sampled_scene.target_answer),
            "target_answer_support": [int(value) for value in axes.target_answer_support],
            "balls": ball_trace,
            "pockets": [
                {
                    "pocket_id": str(pocket.pocket_id),
                    "display_name": str(pocket.display_name),
                    "center": [float(pocket.center[0]), float(pocket.center[1])],
                }
                for pocket in sampled_scene.pockets
            ],
            "cue_ball_id": str(sampled_scene.cue_ball_id),
            "marked_ball_id": sampled_scene.marked_ball_id,
            "marked_pocket_id": sampled_scene.marked_pocket_id,
            "current_player_group": sampled_scene.current_player_group,
            "blocking_ball_ids": [str(value) for value in sampled_scene.blocking_ball_ids],
            "annotation_ball_ids": [str(value) for value in sampled_scene.annotation_ball_ids],
            "annotation_pocket_ids": [str(value) for value in sampled_scene.annotation_pocket_ids],
            "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
            "construction_mode": str(sampled_scene.construction_mode),
        },
        "witness_symbolic": {
            "type": "object_set",
            "ids": [str(entity_id) for entity_id in annotation_entity_ids],
        },
        "projected_annotation": {
            "type": "point_set",
            "point_set": [list(point) for point in annotation_points],
            "pixel_point_set": [list(point) for point in annotation_points],
        },
        "background": background_meta,
        "post_image_noise": post_noise_meta,
    }
    return GeneratedComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        trace_payload=trace_payload,
    )


__all__ = [
    "BLOCKING_BALL_COUNT_QUERY_ID",
    "GROUP_BALL_COUNT_QUERY_ID",
    "SCENE_ID",
    "GeneratedComponents",
    "build_components",
    "resolve_axes",
    "sample_scene",
]
