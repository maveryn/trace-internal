"""Games Mancala task for grounded move-count queries."""

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
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.complexity import build_games_mancala_move_complexity
from ..shared.mancala_common import (
    BOTTOM,
    MancalaMoveOutcome,
    MancalaState,
    evaluate_bottom_moves,
    pit_entity_id,
    player_name,
    total_stones,
)
from ..shared.mancala_scene import MancalaRenderParams, render_mancala_scene
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_variant
from ..shared.style import SUPPORTED_GAMES_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "task_games_mancala_move_count"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "midgame_board",
    "crowded_board",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "extra_turn_move_count",
    "capture_move_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Mancala move-count scenes."""

    extra_turn_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    capture_move_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    midgame_min_total_stones: int = 18
    midgame_max_total_stones: int = 36
    crowded_min_total_stones: int = 37
    crowded_max_total_stones: int = 58
    pit_max_stones: int = 8
    top_pit_max_stones: int = 7
    store_max_stones: int = 18
    canvas_width: int = 1120
    canvas_height: int = 760
    panel_margin_px: int = 40
    player_badge_height_px: int = 50
    player_badge_width_px: int = 220
    header_gap_px: int = 16
    board_width_px: int = 980
    board_height_px: int = 520
    board_corner_radius_px: int = 34
    board_frame_width_px: int = 14
    pit_gap_px: int = 16
    store_width_px: int = 110
    pit_corner_radius_px: int = 28
    count_font_size_px: int = 34
    side_label_font_size_px: int = 24
    player_badge_font_size_px: int = 22


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Mancala scene."""

    query_variant: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    query_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SceneEvaluation:
    """Query-specific evaluation payload derived from one finalized board."""

    answer: int
    move_outcomes: Tuple[MancalaMoveOutcome, ...]
    qualifying_start_indices: Tuple[int, ...]
    evidence_entity_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _SampledMancalaScene:
    """One sampled Mancala scene plus query-specific witness metadata."""

    state: MancalaState
    evaluation: _SceneEvaluation
    total_stones: int
    construction_mode: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "mancala")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="mancala")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="mancala", apply_prob=0.0)


def _target_support_key(query_variant: str) -> str:
    """Return the configured answer-support key for one query variant."""

    return {
        "extra_turn_move_count": "extra_turn_move_count_support",
        "capture_move_count": "capture_move_count_support",
    }[str(query_variant)]


def _resolve_query_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query variant, honoring `task_variant` as an alias."""

    alias_params = dict(params)
    if alias_params.get("query_variant") is None and alias_params.get("task_variant") is not None:
        alias_params["query_variant"] = alias_params["task_variant"]
    return resolve_games_query_variant(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_VARIANTS,
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
    """Resolve one balanced named axis for the Mancala task."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(item) for item in supported],
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual sampling axes for one Mancala instance."""

    query_variant, query_variant_probabilities = _resolve_query_variant(
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
        supported=SUPPORTED_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_GAMES_STYLE_VARIANTS,
    )
    target_support_key = _target_support_key(str(query_variant))
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(target_support_key),
        explicit_key="target_answer",
        fallback_support=getattr(_DEFAULTS, target_support_key),
        namespace=f"{TASK_ID}.target_answer.{str(query_variant)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_explicit_sampling_index=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(target_support_key),
        fallback=getattr(_DEFAULTS, target_support_key),
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


def _render_params(params: Mapping[str, Any]) -> MancalaRenderParams:
    """Resolve Mancala rendering parameters from config/defaults."""

    return MancalaRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        player_badge_height_px=int(
            params.get(
                "player_badge_height_px",
                group_default(_RENDER_DEFAULTS, "player_badge_height_px", _DEFAULTS.player_badge_height_px),
            )
        ),
        player_badge_width_px=int(
            params.get(
                "player_badge_width_px",
                group_default(_RENDER_DEFAULTS, "player_badge_width_px", _DEFAULTS.player_badge_width_px),
            )
        ),
        header_gap_px=int(params.get("header_gap_px", group_default(_RENDER_DEFAULTS, "header_gap_px", _DEFAULTS.header_gap_px))),
        board_width_px=int(params.get("board_width_px", group_default(_RENDER_DEFAULTS, "board_width_px", _DEFAULTS.board_width_px))),
        board_height_px=int(params.get("board_height_px", group_default(_RENDER_DEFAULTS, "board_height_px", _DEFAULTS.board_height_px))),
        board_corner_radius_px=int(
            params.get(
                "board_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px),
            )
        ),
        board_frame_width_px=int(
            params.get(
                "board_frame_width_px",
                group_default(_RENDER_DEFAULTS, "board_frame_width_px", _DEFAULTS.board_frame_width_px),
            )
        ),
        pit_gap_px=int(params.get("pit_gap_px", group_default(_RENDER_DEFAULTS, "pit_gap_px", _DEFAULTS.pit_gap_px))),
        store_width_px=int(params.get("store_width_px", group_default(_RENDER_DEFAULTS, "store_width_px", _DEFAULTS.store_width_px))),
        pit_corner_radius_px=int(
            params.get(
                "pit_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "pit_corner_radius_px", _DEFAULTS.pit_corner_radius_px),
            )
        ),
        count_font_size_px=int(
            params.get("count_font_size_px", group_default(_RENDER_DEFAULTS, "count_font_size_px", _DEFAULTS.count_font_size_px))
        ),
        side_label_font_size_px=int(
            params.get(
                "side_label_font_size_px",
                group_default(_RENDER_DEFAULTS, "side_label_font_size_px", _DEFAULTS.side_label_font_size_px),
            )
        ),
        player_badge_font_size_px=int(
            params.get(
                "player_badge_font_size_px",
                group_default(_RENDER_DEFAULTS, "player_badge_font_size_px", _DEFAULTS.player_badge_font_size_px),
            )
        ),
    )


def _scene_total_range(scene_variant: str) -> Tuple[int, int]:
    """Return the target total-stone range for one scene family."""

    if str(scene_variant) == "crowded_board":
        return (int(_DEFAULTS.crowded_min_total_stones), int(_DEFAULTS.crowded_max_total_stones))
    return (int(_DEFAULTS.midgame_min_total_stones), int(_DEFAULTS.midgame_max_total_stones))


def _evaluate_state(*, state: MancalaState, query_variant: str) -> _SceneEvaluation:
    """Evaluate one Mancala state for the active query semantics."""

    move_outcomes = tuple(evaluate_bottom_moves(state))
    if str(query_variant) == "extra_turn_move_count":
        qualifying = tuple(int(outcome.start_index) for outcome in move_outcomes if bool(outcome.grants_extra_turn))
    else:
        qualifying = tuple(int(outcome.start_index) for outcome in move_outcomes if bool(outcome.causes_capture))
    return _SceneEvaluation(
        answer=int(len(qualifying)),
        move_outcomes=move_outcomes,
        qualifying_start_indices=qualifying,
        evidence_entity_ids=tuple(pit_entity_id(side="bottom", index=index) for index in qualifying),
    )


def _state_with_total_range(
    *,
    rng,
    bottom_pits: Sequence[int],
    top_pits: Sequence[int],
    scene_variant: str,
) -> MancalaState | None:
    """Attach store counts so the final state lands in the requested total-stone range."""

    minimum, maximum = _scene_total_range(str(scene_variant))
    base_total = int(sum(int(value) for value in bottom_pits) + sum(int(value) for value in top_pits))
    extra_min = max(0, int(minimum) - int(base_total))
    extra_max = min(int(_DEFAULTS.store_max_stones * 2), int(maximum) - int(base_total))
    if int(extra_max) < int(extra_min):
        return None
    total_store_stones = int(rng.randint(int(extra_min), int(extra_max)))
    top_store = int(rng.randint(0, min(int(_DEFAULTS.store_max_stones), int(total_store_stones))))
    bottom_store = int(total_store_stones - top_store)
    if int(bottom_store) > int(_DEFAULTS.store_max_stones):
        return None
    return MancalaState(
        top_pits=tuple(int(value) for value in top_pits),
        bottom_pits=tuple(int(value) for value in bottom_pits),
        top_store=int(top_store),
        bottom_store=int(bottom_store),
    )


def _construct_extra_turn_state(*, rng, target_answer: int, scene_variant: str) -> _SampledMancalaScene:
    """Construct one Mancala state with an exact number of extra-turn starting pits."""

    qualifying = set(rng.sample(range(6), k=int(target_answer))) if int(target_answer) > 0 else set()
    bottom_pits = []
    for index in range(6):
        distance_to_store = int(6 - index)
        if int(index) in qualifying:
            bottom_pits.append(int(distance_to_store))
            continue
        allowed = [value for value in range(0, int(_DEFAULTS.pit_max_stones) + 1) if int(value) != int(distance_to_store)]
        bottom_pits.append(int(allowed[int(rng.randrange(len(allowed)))]))
    for _ in range(256):
        top_pits = [int(rng.randint(0, int(_DEFAULTS.top_pit_max_stones))) for _ in range(6)]
        state = _state_with_total_range(rng=rng, bottom_pits=bottom_pits, top_pits=top_pits, scene_variant=str(scene_variant))
        if state is None:
            continue
        evaluation = _evaluate_state(state=state, query_variant="extra_turn_move_count")
        if int(evaluation.answer) != int(target_answer):
            continue
        return _SampledMancalaScene(
            state=state,
            evaluation=evaluation,
            total_stones=int(total_stones(state)),
            construction_mode="distance_to_store",
        )
    raise ValueError("failed to construct Mancala extra-turn scene")


def _construct_capture_state(*, rng, target_answer: int, scene_variant: str) -> _SampledMancalaScene:
    """Search for one Mancala state with an exact number of capture starting pits."""

    for _ in range(4096):
        bottom_pits = [int(rng.randint(0, 5)) for _ in range(6)]
        top_pits = [int(rng.randint(0, int(_DEFAULTS.top_pit_max_stones))) for _ in range(6)]
        state = _state_with_total_range(rng=rng, bottom_pits=bottom_pits, top_pits=top_pits, scene_variant=str(scene_variant))
        if state is None:
            continue
        evaluation = _evaluate_state(state=state, query_variant="capture_move_count")
        if int(evaluation.answer) != int(target_answer):
            continue
        return _SampledMancalaScene(
            state=state,
            evaluation=evaluation,
            total_stones=int(total_stones(state)),
            construction_mode="random_capture_search",
        )
    raise ValueError("failed to construct Mancala capture scene")


def _sample_scene(*, rng, axes: _ResolvedAxes) -> _SampledMancalaScene:
    """Construct one Mancala scene consistent with the requested axes."""

    if str(axes.query_variant) == "extra_turn_move_count":
        return _construct_extra_turn_state(
            rng=rng,
            target_answer=int(axes.target_answer),
            scene_variant=str(axes.scene_variant),
        )
    return _construct_capture_state(
        rng=rng,
        target_answer=int(axes.target_answer),
        scene_variant=str(axes.scene_variant),
    )


def _build_prompt_json_examples(*, query_variant: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for the active Mancala query variant."""

    answer_value = 2
    evidence_value = [[140, 236, 242, 360], [262, 236, 364, 360]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


@register_task
class GamesMancalaMoveCountTask:
    """Return one grounded counting query over a visible Mancala board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "mancala"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params)

        sampled_scene: _SampledMancalaScene | None = None
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
        current_player_name = player_name(int(BOTTOM))
        rendered_scene = render_mancala_scene(
            state=sampled_scene.state,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            current_player_name=str(current_player_name),
            params=render_params,
        )
        evidence_bboxes = [
            list(rendered_scene.render_map["pit_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evaluation.evidence_entity_ids
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
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_midgame_board",
                "object_description_crowded_board",
                "turn_rule_text",
                "extra_turn_rule_text",
                "capture_rule_text",
                "evidence_hint_extra_turn_move_count",
                "evidence_hint_capture_move_count",
                "answer_hint_extra_turn_move_count",
                "answer_hint_capture_move_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(query_variant=str(axes.query_variant))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(axes.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_variant)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "current_player_name": str(current_player_name),
                "turn_rule_text": str(prompt_defaults["turn_rule_text"]),
                "extra_turn_rule_text": str(prompt_defaults["extra_turn_rule_text"]),
                "capture_rule_text": str(prompt_defaults["capture_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_mancala_move_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
            total_stones=int(sampled_scene.total_stones),
            target_answer=int(axes.target_answer),
            evidence_count=len(sampled_scene.evaluation.evidence_entity_ids),
        )

        move_specs = [
            {
                "start_index": int(outcome.start_index),
                "pit_entity_id": str(pit_entity_id(side="bottom", index=int(outcome.start_index))),
                "stones": int(outcome.stones),
                "last_cup_kind": str(outcome.last_cup_kind),
                "last_cup_index": None if outcome.last_cup_index is None else int(outcome.last_cup_index),
                "grants_extra_turn": bool(outcome.grants_extra_turn),
                "causes_capture": bool(outcome.causes_capture),
                "captured_opposite_index": None
                if outcome.captured_opposite_index is None
                else int(outcome.captured_opposite_index),
            }
            for outcome in sampled_scene.evaluation.move_outcomes
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_mancala_board_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "current_player": str(current_player_name),
                    "target_answer": int(axes.target_answer),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evaluation.evidence_entity_ids],
                },
            },
            "query_spec": {
                "task_variant": str(axes.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "current_player": str(current_player_name),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "task_variant_probabilities": dict(axes.query_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_variant": str(axes.query_variant),
                "task_variant": str(axes.query_variant),
                "style_variant": str(axes.style_variant),
                "current_player": str(current_player_name),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "top_pits": [int(value) for value in sampled_scene.state.top_pits],
                "bottom_pits": [int(value) for value in sampled_scene.state.bottom_pits],
                "top_store": int(sampled_scene.state.top_store),
                "bottom_store": int(sampled_scene.state.bottom_store),
                "total_stones": int(sampled_scene.total_stones),
                "construction_mode": str(sampled_scene.construction_mode),
                "move_specs": move_specs,
                "qualifying_start_indices": [int(index) for index in sampled_scene.evaluation.qualifying_start_indices],
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evaluation.evidence_entity_ids],
            },
            "witness_symbolic": {
                "type": "id_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evaluation.evidence_entity_ids],
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
            task_variant=str(axes.query_variant),
        )


__all__ = ["GamesMancalaMoveCountTask"]
