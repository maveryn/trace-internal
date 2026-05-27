"""Games Go task for counting properties of one highlighted group on a visible board."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

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
from ..shared.complexity import build_games_go_group_property_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, QuerySubsetTaskMixin
from ..shared.go_common import (
    BOARD_SIZE,
    SUPPORTED_GO_PLAYER_COLORS,
    GoBoardState,
    build_go_board_state,
    color_name,
    liberty_point_ids,
    stone_ids_for_coords,
    supported_targets_for_query,
)
from ..shared.go_scene import GoRenderParams, render_go_board_scene
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.style import SUPPORTED_GO_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_go_group_property_count_base"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "open_board",
    "crowded_board",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "marked_group_liberty_count",
    "marked_group_adjacent_enemy_count",
    "marked_group_shared_liberty_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Go group-property scenes."""

    liberty_count_support: Tuple[int, ...] = (1, 2, 3, 4, 6)
    adjacent_enemy_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    shared_liberty_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    board_size_support: Tuple[int, ...] = (6, 7, 8)
    canvas_width: int = 920
    canvas_height: int = 920
    panel_margin_px: int = 48
    max_board_size_px: int = 760
    board_padding_px: int = 78
    board_corner_radius_px: int = 24
    board_frame_width_px: int = 12
    line_width_px: int = 4
    point_radius_px: int = 4
    stone_radius_fraction: float = 0.34
    highlight_outline_width_px: int = 10
    liberty_bbox_fraction: float = 0.72


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Go group-property scene."""

    query_id: str
    player_color: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    board_size: int
    board_size_probabilities: Dict[str, float]
    player_color_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "go")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="go")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="go", apply_prob=0.0)

_SOURCE_QUERY_ID_PLAYER_COLORS: Dict[str, str] = {
    "marked_black_group_liberty_count": "black",
    "marked_white_group_liberty_count": "white",
}


def _params_with_source_query_aliases(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Map old black/white query ids to canonical query plus `player_color`."""

    alias_params = dict(params)
    explicit_query = alias_params.get("query_id")
    if explicit_query is None and alias_params.get("query_id") is not None:
        explicit_query = alias_params.get("query_id")
        alias_params["query_id"] = explicit_query
    if explicit_query is None:
        return alias_params
    source_color = _SOURCE_QUERY_ID_PLAYER_COLORS.get(str(explicit_query))
    if source_color is None:
        return alias_params
    explicit_color = alias_params.get("player_color")
    if explicit_color is not None and str(explicit_color) != str(source_color):
        raise ValueError(f"conflicting player_color={explicit_color!r} for source query_id={explicit_query!r}")
    alias_params["query_id"] = "marked_group_liberty_count"
    alias_params["player_color"] = str(source_color)
    return alias_params


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query id, honoring `query_id` as an alias."""

    alias_params = _params_with_source_query_aliases(params)
    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_IDS,
    )


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
    """Resolve one balanced named axis for the Go liberty-count task."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=supported,
    )


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
    if len(positives) != len(SUPPORTED_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _target_answer_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced target-answer cycling."""

    target_params = _params_with_source_query_aliases(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return target_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return target_params
    target_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return target_params


def _support_key_for_query_id(query_id: str) -> str:
    """Return the config support key for one Go query id."""

    variant = str(query_id)
    if variant == "marked_group_liberty_count":
        return "liberty_count_support"
    if variant == "marked_group_adjacent_enemy_count":
        return "adjacent_enemy_count_support"
    if variant == "marked_group_shared_liberty_count":
        return "shared_liberty_count_support"
    raise ValueError(f"unsupported Go query id: {query_id}")


def _scene_variant_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Decorrelate balanced scene cycling from balanced query cycling."""

    scene_params = _params_with_source_query_aliases(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return scene_params
    if params.get("scene_variant") is not None:
        return scene_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return scene_params
    enabled = bool(
        params.get(
            "balanced_scene_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_scene_variant_sampling", True),
        )
    )
    if not enabled:
        return scene_params
    raw_weights = params.get(
        "scene_variant_weights",
        group_default(_GEN_DEFAULTS, "scene_variant_weights", {key: 1.0 for key in SUPPORTED_SCENE_VARIANTS}),
    )
    if not isinstance(raw_weights, Mapping):
        return scene_params
    positives = [
        float(raw_weights.get(str(value), 0.0))
        for value in SUPPORTED_SCENE_VARIANTS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_SCENE_VARIANTS):
        return scene_params
    if max(positives) - min(positives) > 1e-9:
        return scene_params
    scene_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return scene_params


def _style_variant_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Decorrelate balanced style cycling from balanced query cycling."""

    style_params = _params_with_source_query_aliases(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return style_params
    if params.get("style_variant") is not None:
        return style_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return style_params
    enabled = bool(
        params.get(
            "balanced_style_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_style_variant_sampling", True),
        )
    )
    if not enabled:
        return style_params
    raw_weights = params.get(
        "style_variant_weights",
        group_default(_GEN_DEFAULTS, "style_variant_weights", {key: 1.0 for key in SUPPORTED_GO_STYLE_VARIANTS}),
    )
    if not isinstance(raw_weights, Mapping):
        return style_params
    positives = [
        float(raw_weights.get(str(value), 0.0))
        for value in SUPPORTED_GO_STYLE_VARIANTS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_GO_STYLE_VARIANTS):
        return style_params
    if max(positives) - min(positives) > 1e-9:
        return style_params
    style_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_QUERY_IDS))
    return style_params


def _uses_uniform_player_color_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when player-color cycling is enabled and uniformly balanced."""

    normalized_params = _params_with_source_query_aliases(params)
    if normalized_params.get("player_color") is not None:
        return False
    enabled = bool(
        normalized_params.get(
            "balanced_player_color_sampling",
            group_default(_GEN_DEFAULTS, "balanced_player_color_sampling", True),
        )
    )
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_GO_PLAYER_COLORS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_player_color_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    player_color_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-player-color occurrence index for axes below the color cycle."""

    cycle_params = _params_with_source_query_aliases(params)
    sampling_index = cycle_params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_player_color_cycle(cycle_params, player_color_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_GO_PLAYER_COLORS))
    return cycle_params


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic/visual axes plus one target answer for the Go task."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
    )
    player_color, player_color_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_target_answer_params_for_query_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
        ),
        namespace="player_color",
        explicit_key="player_color",
        weights_key="player_color_weights",
        balance_flag_key="balanced_player_color_sampling",
        supported=SUPPORTED_GO_PLAYER_COLORS,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_params_for_player_color_occurrence_cycle(
            _scene_variant_params_for_query_cycle(
                params,
                query_id_probabilities=query_id_probabilities,
            ),
            player_color_probabilities=player_color_probabilities,
        ),
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_params_for_player_color_occurrence_cycle(
            _style_variant_params_for_query_cycle(
                params,
                query_id_probabilities=query_id_probabilities,
            ),
            player_color_probabilities=player_color_probabilities,
        ),
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_GO_STYLE_VARIANTS,
    )
    target_params = _params_for_player_color_occurrence_cycle(
        _target_answer_params_for_query_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
        ),
        player_color_probabilities=player_color_probabilities,
    )
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=_support_key_for_query_id(str(query_id)),
        explicit_key="target_answer",
        fallback_support=supported_targets_for_query(str(query_id)),
        namespace=f"{TASK_ID}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=_support_key_for_query_id(str(query_id)),
        fallback=supported_targets_for_query(str(query_id)),
    )
    board_params = _params_for_player_color_occurrence_cycle(
        _target_answer_params_for_query_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
        ),
        player_color_probabilities=player_color_probabilities,
    )
    board_size, board_size_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=board_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="board_size_support",
        explicit_key="board_size",
        fallback_support=_DEFAULTS.board_size_support,
        namespace=f"{TASK_ID}.board_size",
        balanced_flag_key="balanced_board_size_sampling",
        namespace_support_permutation=True,
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        player_color=str(player_color),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        board_size=int(board_size),
        board_size_probabilities=dict(board_size_probabilities),
        player_color_probabilities=dict(player_color_probabilities),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> GoRenderParams:
    """Resolve Go rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.go.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.go.layout",
        ),
        unit_scale_meta,
    )
    return GoRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        max_board_size_px=scale_games_px(
            params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px)),
            unit_scale,
            min_px=380,
        ),
        board_padding_px=scale_games_px(
            params.get("board_padding_px", group_default(_RENDER_DEFAULTS, "board_padding_px", _DEFAULTS.board_padding_px)),
            unit_scale,
            min_px=38,
        ),
        board_corner_radius_px=scale_games_px(
            params.get(
                "board_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px),
            ),
            unit_scale,
            min_px=10,
        ),
        board_frame_width_px=scale_games_px(
            params.get(
                "board_frame_width_px",
                group_default(_RENDER_DEFAULTS, "board_frame_width_px", _DEFAULTS.board_frame_width_px),
            ),
            unit_scale,
            min_px=6,
        ),
        line_width_px=scale_games_px(params.get("line_width_px", group_default(_RENDER_DEFAULTS, "line_width_px", _DEFAULTS.line_width_px)), unit_scale, min_px=2),
        point_radius_px=scale_games_px(
            params.get("point_radius_px", group_default(_RENDER_DEFAULTS, "point_radius_px", _DEFAULTS.point_radius_px)),
            unit_scale,
            min_px=2,
        ),
        stone_radius_fraction=float(
            params.get(
                "stone_radius_fraction",
                group_default(_RENDER_DEFAULTS, "stone_radius_fraction", _DEFAULTS.stone_radius_fraction),
            )
        ),
        highlight_outline_width_px=scale_games_px(
            params.get(
                "highlight_outline_width_px",
                group_default(_RENDER_DEFAULTS, "highlight_outline_width_px", _DEFAULTS.highlight_outline_width_px),
            ),
            unit_scale,
            min_px=5,
        ),
        liberty_bbox_fraction=float(
            params.get(
                "liberty_bbox_fraction",
                group_default(_RENDER_DEFAULTS, "liberty_bbox_fraction", _DEFAULTS.liberty_bbox_fraction),
            )
        ),
        layout_jitter_meta=layout_jitter,
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return answer+evidence and answer-only JSON examples for the Go task."""

    json_example = json.dumps(
        {
            "evidence": [
                [312, 284, 374, 346],
                [386, 358, 448, 420],
            ],
            "answer": 4,
        },
        ensure_ascii=True,
    )
    json_example_answer_only = json.dumps({"answer": 4}, ensure_ascii=True)
    return json_example, json_example_answer_only


class GamesGoGroupPropertyCountTask:
    """Return one grounded count for a highlighted group on a visible Go board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "go"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        board_state: GoBoardState | None = None
        rendered_scene = None
        background_meta: Dict[str, Any] | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            board_state = build_go_board_state(
                rng=attempt_rng,
                query_id=str(axes.query_id),
                player_color=str(axes.player_color),
                scene_variant=str(axes.scene_variant),
                target_answer=int(axes.target_answer),
                board_size=int(axes.board_size),
            )
            background, background_meta = make_background_canvas(
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            rendered_scene = render_go_board_scene(
                board=board_state.board,
                background=background,
                scene_variant=str(axes.scene_variant),
                style_variant=str(axes.style_variant),
                marked_group_coords=board_state.marked_group_coords,
                liberty_coords=board_state.liberty_coords,
                params=render_params,
            )
            break

        if board_state is None or rendered_scene is None or background_meta is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid Go board after {max_attempts} attempts")

        if str(axes.query_id) == "marked_group_liberty_count":
            evidence_ids = liberty_point_ids(board_state.liberty_coords)
            evidence_bboxes = [list(rendered_scene.render_map["point_bboxes_px"][str(point_id)]) for point_id in evidence_ids]
        elif str(axes.query_id) == "marked_group_adjacent_enemy_count":
            evidence_ids = stone_ids_for_coords(board_state.adjacent_enemy_coords)
            evidence_bboxes = [list(rendered_scene.render_map["stone_bboxes_px"][str(stone_id)]) for stone_id in evidence_ids]
        elif str(axes.query_id) == "marked_group_shared_liberty_count":
            evidence_ids = liberty_point_ids(board_state.shared_liberty_coords)
            evidence_bboxes = [list(rendered_scene.render_map["point_bboxes_px"][str(point_id)]) for point_id in evidence_ids]
        else:
            raise ValueError(f"unsupported Go query id: {axes.query_id}")
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
                "object_description_open_board",
                "object_description_crowded_board",
                "group_rule_text",
                "liberty_rule_text",
                "adjacent_enemy_rule_text",
                "shared_liberty_rule_text",
                "marked_group_rule_text",
                "answer_hint_marked_group_liberty_count",
                "evidence_hint_marked_group_liberty_count",
                "answer_hint_marked_group_adjacent_enemy_count",
                "evidence_hint_marked_group_adjacent_enemy_count",
                "answer_hint_marked_group_shared_liberty_count",
                "evidence_hint_marked_group_shared_liberty_count",
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
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]).format(
                    player_color=str(axes.player_color)
                ),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]).format(
                    player_color=str(axes.player_color)
                ),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "player_color": str(axes.player_color),
                "group_rule_text": str(prompt_defaults["group_rule_text"]),
                "liberty_rule_text": str(prompt_defaults["liberty_rule_text"]),
                "adjacent_enemy_rule_text": str(prompt_defaults["adjacent_enemy_rule_text"]),
                "shared_liberty_rule_text": str(prompt_defaults["shared_liberty_rule_text"]),
                "marked_group_rule_text": str(prompt_defaults["marked_group_rule_text"]).format(
                    player_color=str(axes.player_color)
                ),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        occupied_count = sum(
            1
            for row in board_state.board
            for cell in row
            if int(cell) != 0
        )
        complexity = build_games_go_group_property_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            occupied_count=int(occupied_count),
            marked_group_size=len(board_state.marked_group_coords),
            target_answer=int(axes.target_answer),
            evidence_count=len(evidence_ids),
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_go_single_board",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "player_color": str(axes.player_color),
                    "style_variant": str(axes.style_variant),
                    "target_answer": int(axes.target_answer),
                    "evidence_entity_ids": list(evidence_ids),
                    "board_size": int(axes.board_size),
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
                    "player_color": str(axes.player_color),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(axes.board_size),
                    "board_size_probabilities": dict(axes.board_size_probabilities),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "player_color_probabilities": dict(axes.player_color_probabilities),
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
                "board_size": int(axes.board_size),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "player_color": str(axes.player_color),
                "style_variant": str(axes.style_variant),
                "board_size": int(axes.board_size),
                "marked_group_color": str(color_name(board_state.marked_group_color).lower()),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "stone_specs": [
                    {
                        "stone_id": str(spec.stone_id),
                        "point_id": str(spec.point_id),
                        "row": int(spec.row),
                        "col": int(spec.col),
                        "color": str(spec.color),
                        "is_marked_group": bool(spec.is_marked_group),
                    }
                    for spec in board_state.stone_specs
                ],
                "marked_group_coords": [[int(row), int(col)] for row, col in board_state.marked_group_coords],
                "marked_group_point_ids": [f"point_r{int(row)}_c{int(col)}" for row, col in board_state.marked_group_coords],
                "liberty_coords": [[int(row), int(col)] for row, col in board_state.liberty_coords],
                "adjacent_enemy_coords": [[int(row), int(col)] for row, col in board_state.adjacent_enemy_coords],
                "shared_liberty_coords": [[int(row), int(col)] for row, col in board_state.shared_liberty_coords],
                "evidence_entity_ids": [str(value) for value in evidence_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(value) for value in evidence_ids],
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
            scene_id="go",
            query_id=str(axes.query_id),
        )


@register_task
class GamesGoGroupLibertyConditionCountTask(QuerySubsetTaskMixin, GamesGoGroupPropertyCountTask):
    """Count marked-group liberties matching a sampled liberty condition."""

    task_id = "task_games__go__group_liberty_count"
    supported_query_ids = (
        "marked_group_liberty_count",
        "marked_group_shared_liberty_count",
    )


@register_task
class GamesGoGroupAdjacentEnemyCountTask(FixedQueryVariantTaskMixin, GamesGoGroupPropertyCountTask):
    """Count adjacent enemy stones touching the marked Go group."""

    task_id = "task_games__go__group_adjacent_enemy_count"
    fixed_query_id = "marked_group_adjacent_enemy_count"


__all__ = [
    "GamesGoGroupAdjacentEnemyCountTask",
    "GamesGoGroupLibertyConditionCountTask",
]
