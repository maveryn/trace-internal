"""Games Backgammon tasks over visible numbered boards."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

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
from ..shared.backgammon_common import (
    BACKGAMMON_QUERY_VARIANTS,
    BACKGAMMON_STYLE_VARIANTS,
    PLAYER_BLACK,
    PLAYER_WHITE,
    POINT_IDS,
    BackgammonPoint,
    BackgammonSample,
    compute_black_single_die_destinations,
    empty_points,
    point_entity_id,
    stack_at,
    target_destinations_for_query,
    validate_backgammon_sample,
)
from ..shared.backgammon_scene import BackgammonRenderParams, render_backgammon_scene
from ..shared.complexity import build_games_backgammon_board_complexity
from ..shared.fixed_query_task import QuerySubsetTaskMixin
from ..shared.layout import resolve_games_layout_jitter
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_variant
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_backgammon_board_base"
_BACKGAMMON_SCENE_VARIANTS: Tuple[str, ...] = ("standard_board",)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Backgammon board scenes."""

    legal_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    hit_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    blocked_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    canvas_width: int = 1000
    canvas_height: int = 720
    board_width_px: int = 900
    board_height_px: int = 560
    board_margin_px: int = 50
    board_border_width_px: int = 5
    point_label_font_size_px: int = 18
    header_font_size_px: int = 20
    checker_radius_px: int = 21
    die_size_px: int = 44


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Backgammon instance."""

    query_variant: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "backgammon")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="backgammon", apply_prob=0.5)


def _resolve_query_variant(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Backgammon query variant."""

    return resolve_games_query_variant(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=BACKGAMMON_QUERY_VARIANTS,
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
    """Resolve one balanced named Backgammon axis."""

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


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_variant") is not None or params.get("query_variant") is not None:
        return False
    enabled = bool(params.get("balanced_query_variant_sampling", group_default(_GEN_DEFAULTS, "balanced_query_variant_sampling", True)))
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(BACKGAMMON_QUERY_VARIANTS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_variant_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced answer axes."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(params, query_variant_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(BACKGAMMON_QUERY_VARIANTS))
    return cycle_params


def _support_key_for_query(query_variant: str) -> Tuple[str, Tuple[int, ...]]:
    """Return the answer-support key and fallback for one query."""

    query = str(query_variant)
    if query == "legal_move_count":
        return "legal_count_support", tuple(_DEFAULTS.legal_count_support)
    if query == "hit_move_count":
        return "hit_count_support", tuple(_DEFAULTS.hit_count_support)
    if query == "blocked_destination_count":
        return "blocked_count_support", tuple(_DEFAULTS.blocked_count_support)
    raise ValueError(f"unsupported Backgammon query_variant: {query}")


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Backgammon instance."""

    query_variant, query_variant_probabilities = _resolve_query_variant(instance_seed=int(instance_seed), params=params)
    answer_cycle_params = _params_for_query_occurrence_cycle(
        params,
        query_variant_probabilities=query_variant_probabilities,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=_BACKGAMMON_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=BACKGAMMON_STYLE_VARIANTS,
    )
    support_key, fallback_support = _support_key_for_query(str(query_variant))
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=answer_cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=support_key,
        explicit_key="target_answer",
        fallback_support=fallback_support,
        namespace=f"target_answer.{str(query_variant)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        answer_cycle_params,
        gen_defaults=_GEN_DEFAULTS,
        key=support_key,
        fallback=fallback_support,
    )
    return _ResolvedAxes(
        query_variant=str(query_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        query_variant_probabilities=dict(query_variant_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> BackgammonRenderParams:
    """Resolve renderer parameters."""

    return BackgammonRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        board_width_px=int(params.get("board_width_px", group_default(_RENDER_DEFAULTS, "board_width_px", _DEFAULTS.board_width_px))),
        board_height_px=int(params.get("board_height_px", group_default(_RENDER_DEFAULTS, "board_height_px", _DEFAULTS.board_height_px))),
        board_margin_px=int(params.get("board_margin_px", group_default(_RENDER_DEFAULTS, "board_margin_px", _DEFAULTS.board_margin_px))),
        board_border_width_px=int(params.get("board_border_width_px", group_default(_RENDER_DEFAULTS, "board_border_width_px", _DEFAULTS.board_border_width_px))),
        point_label_font_size_px=int(params.get("point_label_font_size_px", group_default(_RENDER_DEFAULTS, "point_label_font_size_px", _DEFAULTS.point_label_font_size_px))),
        header_font_size_px=int(params.get("header_font_size_px", group_default(_RENDER_DEFAULTS, "header_font_size_px", _DEFAULTS.header_font_size_px))),
        checker_radius_px=int(params.get("checker_radius_px", group_default(_RENDER_DEFAULTS, "checker_radius_px", _DEFAULTS.checker_radius_px))),
        die_size_px=int(params.get("die_size_px", group_default(_RENDER_DEFAULTS, "die_size_px", _DEFAULTS.die_size_px))),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.backgammon.layout",
        ),
    )


def _choose_dice(rng: Any) -> Tuple[int, int]:
    """Choose two non-double dice values."""

    values = list(range(1, 7))
    rng.shuffle(values)
    return int(values[0]), int(values[1])


def _choose_source_points(rng: Any, *, dice: Tuple[int, int], source_count: int) -> Tuple[int, ...]:
    """Choose black source points whose single-die destinations are not other sources."""

    candidates = [point for point in POINT_IDS if int(point) > max(int(value) for value in dice)]
    rng.shuffle(candidates)
    selected: list[int] = []
    for candidate in candidates:
        blocked_by_source_conflict = False
        for existing in selected:
            for die in dice:
                if int(candidate) - int(die) == int(existing):
                    blocked_by_source_conflict = True
                if int(existing) - int(die) == int(candidate):
                    blocked_by_source_conflict = True
        if blocked_by_source_conflict:
            continue
        selected.append(int(candidate))
        if len(selected) >= int(source_count):
            return tuple(sorted(selected))
    raise ValueError("could not choose enough Backgammon black source points")


def _candidate_destinations(*, sources: Sequence[int], dice: Tuple[int, int]) -> Tuple[int, ...]:
    """Return distinct single-die destination points for black sources."""

    destinations = {
        int(source) - int(die)
        for source in sources
        for die in dice
        if int(source) - int(die) in POINT_IDS
    }
    return tuple(sorted(destinations))


def _target_state_for_query(rng: Any, *, query_variant: str, is_target: bool) -> BackgammonPoint:
    """Return the stack state to place on a candidate destination."""

    query = str(query_variant)
    if query == "legal_move_count":
        if bool(is_target):
            return BackgammonPoint(owner=None, count=0)
        return BackgammonPoint(owner=PLAYER_WHITE, count=int(rng.randint(2, 4)))
    if query == "hit_move_count":
        if bool(is_target):
            return BackgammonPoint(owner=PLAYER_WHITE, count=1)
        if float(rng.random()) < 0.48:
            return BackgammonPoint(owner=PLAYER_WHITE, count=int(rng.randint(2, 4)))
        return BackgammonPoint(owner=None, count=0)
    if query == "blocked_destination_count":
        if bool(is_target):
            return BackgammonPoint(owner=PLAYER_WHITE, count=int(rng.randint(2, 4)))
        if float(rng.random()) < 0.38:
            return BackgammonPoint(owner=PLAYER_WHITE, count=1)
        return BackgammonPoint(owner=None, count=0)
    raise ValueError(f"unsupported Backgammon query_variant: {query}")


def _sample_scene(rng: Any, *, axes: _ResolvedAxes) -> BackgammonSample:
    """Construct one exact-answer Backgammon position."""

    query = str(axes.query_variant)
    target_answer = int(axes.target_answer)
    for _inner_attempt in range(1500):
        dice = _choose_dice(rng)
        min_sources = max(2, int((target_answer + 1) // 2))
        max_sources = min(8, max(min_sources, int(target_answer) + 2))
        source_count = int(rng.randint(int(min_sources), int(max_sources)))
        try:
            sources = _choose_source_points(rng, dice=dice, source_count=source_count)
        except ValueError:
            continue
        candidates = _candidate_destinations(sources=sources, dice=dice)
        if len(candidates) < int(target_answer):
            continue
        target_destinations = tuple(sorted(rng.sample(list(candidates), int(target_answer))))
        target_set = set(int(point) for point in target_destinations)

        points = empty_points()
        for source in sources:
            points[int(source)] = BackgammonPoint(owner=PLAYER_BLACK, count=int(rng.randint(1, 4)))
        for destination in candidates:
            points[int(destination)] = _target_state_for_query(
                rng,
                query_variant=query,
                is_target=int(destination) in target_set,
            )

        protected_points = set(int(point) for point in sources) | set(int(point) for point in candidates)
        for point in POINT_IDS:
            if int(point) in protected_points:
                continue
            if float(rng.random()) < 0.20:
                points[int(point)] = BackgammonPoint(owner=PLAYER_WHITE, count=int(rng.randint(1, 4)))

        outcome = compute_black_single_die_destinations(points, dice=dice)
        expected_targets = target_destinations_for_query(outcome, query_variant=query)
        if tuple(expected_targets) != tuple(target_destinations):
            continue
        sample = BackgammonSample(
            points=dict(points),
            dice=(int(dice[0]), int(dice[1])),
            query_variant=query,
            answer=int(target_answer),
            target_destinations=tuple(int(point) for point in target_destinations),
            outcome=outcome,
            style_variant=str(axes.style_variant),
            target_answer=int(target_answer),
        )
        validate_backgammon_sample(sample)
        return sample
    raise ValueError(f"could not construct Backgammon sample for {query} answer {target_answer}")


def _build_prompt_json_examples(query_variant: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Backgammon JSON output."""

    if str(query_variant) == "hit_move_count":
        answer_value = 2
        evidence_value = [[410, 104, 475, 316], [608, 104, 673, 316]]
    elif str(query_variant) == "blocked_destination_count":
        answer_value = 3
        evidence_value = [[276, 400, 341, 612], [342, 400, 407, 612], [608, 400, 673, 612]]
    else:
        answer_value = 3
        evidence_value = [[144, 104, 209, 316], [210, 104, 275, 316], [608, 104, 673, 316]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesBackgammonBoardTask:
    """Return one grounded query over a visible Backgammon board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "backgammon"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: BackgammonSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid Backgammon scene after {max_attempts} attempts")

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
            namespace="games.backgammon_board.panel_scene_style",
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
        rendered_scene = render_backgammon_scene(
            points=sampled_scene.points,
            dice=sampled_scene.dice,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            panel_style=panel_style,
        )
        evidence_entity_ids = [point_entity_id(point) for point in sampled_scene.target_destinations]
        evidence_bboxes = [
            list(rendered_scene.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in evidence_entity_ids
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
                "object_description_standard_board",
                "backgammon_rule_text",
                "answer_hint_legal_move_count",
                "evidence_hint_legal_move_count",
                "answer_hint_hit_move_count",
                "evidence_hint_hit_move_count",
                "answer_hint_blocked_destination_count",
                "evidence_hint_blocked_destination_count",
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
                "backgammon_rule_text": str(prompt_defaults["backgammon_rule_text"]),
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

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        black_source_count = sum(
            1
            for point in POINT_IDS
            if str(stack_at(sampled_scene.points, int(point)).owner) == PLAYER_BLACK
        )
        occupied_count = sum(
            1
            for point in POINT_IDS
            if stack_at(sampled_scene.points, int(point)).owner is not None
        )
        complexity = build_games_backgammon_board_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
            occupied_point_count=int(occupied_count),
            black_source_count=int(black_source_count),
            target_answer=int(sampled_scene.answer),
            evidence_count=len(evidence_entity_ids),
        )
        point_trace = [
            {
                "point_id": int(point),
                "owner": stack_at(sampled_scene.points, int(point)).owner,
                "count": int(stack_at(sampled_scene.points, int(point)).count),
                "entity_id": point_entity_id(point),
            }
            for point in POINT_IDS
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_backgammon_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "query_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "dice": [int(value) for value in sampled_scene.dice],
                    "target_destinations": [int(point) for point in sampled_scene.target_destinations],
                    "evidence_entity_ids": [str(entity_id) for entity_id in evidence_entity_ids],
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
                    "dice": [int(value) for value in sampled_scene.dice],
                    "target_answer": int(sampled_scene.answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_variant": str(axes.query_variant),
                "query_variant": str(axes.query_variant),
                "style_variant": str(axes.style_variant),
                "points": point_trace,
                "dice": [int(value) for value in sampled_scene.dice],
                "outcome": {
                    "legal_destinations": [int(point) for point in sampled_scene.outcome.legal_destinations],
                    "hit_destinations": [int(point) for point in sampled_scene.outcome.hit_destinations],
                    "blocked_destinations": [int(point) for point in sampled_scene.outcome.blocked_destinations],
                },
                "target_destinations": [int(point) for point in sampled_scene.target_destinations],
                "evidence_entity_ids": [str(entity_id) for entity_id in evidence_entity_ids],
                "construction_mode": "exact_destination_count",
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in evidence_entity_ids],
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
            query_variant=str(axes.query_variant),
            scene_id="backgammon",
            query_id=str(axes.query_variant),
        )


@register_task
class GamesBackgammonDestinationCountTask(QuerySubsetTaskMixin, GamesBackgammonBoardTask):
    """Count Backgammon destination points matching one sampled query condition."""

    task_id = "task_games__backgammon__destination_count"
    supported_query_variants = (
        "legal_move_count",
        "hit_move_count",
        "blocked_destination_count",
    )


__all__ = [
    "GamesBackgammonBoardTask",
    "GamesBackgammonDestinationCountTask",
]
