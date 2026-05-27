"""Games Hex-board tasks for winning move selection and connection-gap counting."""

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
from ..shared.complexity import build_games_hex_board_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin
from ..shared.hex_common import (
    BLUE,
    EMPTY,
    HEX_CANDIDATE_LABELS,
    RED,
    SUPPORTED_HEX_PLAYER_COLORS,
    SUPPORTED_HEX_QUERY_IDS,
    SUPPORTED_HEX_SCENE_VARIANTS,
    Coord,
    HexCandidateSpec,
    HexSample,
    all_coords,
    board_from_rows,
    color_name,
    color_value,
    coord_to_cell_id,
    immediate_winning_moves,
    make_connection_path,
    minimum_connection_gap_sets,
    minimum_connection_path,
    sorted_coords,
    validate_hex_sample,
    winning_path_after_move,
)
from ..shared.hex_scene import HexRenderParams, render_hex_board_scene
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.style import SUPPORTED_HEX_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_hex_board_base"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Hex-board tasks."""

    board_size_support: Tuple[int, ...] = (5, 6, 7, 8)
    connection_gap_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    candidate_count_support: Tuple[int, ...] = (4, 5, 6, 7, 8)
    winning_move_label_support: Tuple[str, ...] = HEX_CANDIDATE_LABELS
    min_extra_own_stones: int = 2
    max_extra_own_stones: int = 7
    min_extra_opponent_stones: int = 5
    max_extra_opponent_stones: int = 14
    canvas_width: int = 980
    canvas_height: int = 900
    panel_margin_px: int = 54
    max_board_width_px: int = 820
    max_board_height_px: int = 760
    hex_border_width_px: int = 3
    stone_radius_fraction: float = 0.46
    candidate_label_font_size_px: int = 30
    side_band_width_px: int = 8


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Hex instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    player_color: str
    board_size: int
    target_answer: int | None
    target_label: str | None
    target_answer_support: Tuple[int, ...]
    target_label_support: Tuple[str, ...]
    candidate_count: int
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    player_color_probabilities: Dict[str, float]
    board_size_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    target_label_probabilities: Dict[str, float]
    candidate_count_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "hex")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="hex")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="hex", apply_prob=0.0)


def _resolve_query_id(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Hex query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_HEX_QUERY_IDS,
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
    """Resolve one balanced named Hex axis."""

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


def _string_support(
    params: Mapping[str, Any],
    *,
    key: str,
    fallback: Sequence[str],
) -> Tuple[str, ...]:
    """Resolve a string support list from params/defaults."""

    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), tuple(fallback)))
    if raw is None:
        raw = tuple(fallback)
    if isinstance(raw, str):
        values = (raw,)
    else:
        values = tuple(str(value) for value in raw)
    values = tuple(value for value in values if value)
    if not values:
        raise ValueError(f"{key} must contain at least one label")
    return values


def _resolve_label_choice(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[str],
    namespace: str,
    balanced_flag_key: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one string-valued support choice with optional balanced cycling."""

    support = _string_support(params, key=str(support_key), fallback=fallback_support)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = str(explicit)
        if value not in support:
            raise ValueError(f"{explicit_key}={value!r} is not in {support_key}")
        return value, {str(item): (1.0 if str(item) == value else 0.0) for item in support}

    probabilities = {str(item): 1.0 / float(len(support)) for item in support}
    sampling_index = params.get("_sample_cursor")
    balanced = bool(params.get(str(balanced_flag_key), group_default(_GEN_DEFAULTS, str(balanced_flag_key), True)))
    if balanced and sampling_index is not None:
        return str(support[abs(int(sampling_index)) % len(support)]), probabilities
    rng = spawn_rng(int(instance_seed), str(namespace))
    return str(rng.choice(tuple(support))), probabilities


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_id") is not None:
        return False
    enabled = bool(params.get("balanced_query_id_sampling", group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True)))
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_HEX_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced inner answer axes."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_HEX_QUERY_IDS))
    return cycle_params


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Hex instance."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
    )
    answer_cycle_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_HEX_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_HEX_STYLE_VARIANTS,
    )
    player_color, player_color_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="player_color",
        explicit_key="player_color",
        weights_key="player_color_weights",
        balance_flag_key="balanced_player_color_sampling",
        supported=SUPPORTED_HEX_PLAYER_COLORS,
    )
    board_size, board_size_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="board_size_support",
        explicit_key="board_size",
        fallback_support=_DEFAULTS.board_size_support,
        namespace=f"{TASK_ID}.board_size",
        balanced_flag_key="balanced_board_size_sampling",
        namespace_support_permutation=True,
    )
    candidate_count = 0
    candidate_count_probabilities: Dict[str, float] = {}
    target_answer = None
    target_answer_probabilities: Dict[str, float] = {}
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="connection_gap_count_support",
        fallback=_DEFAULTS.connection_gap_count_support,
    )
    target_label = None
    target_label_probabilities: Dict[str, float] = {}
    target_label_support = _string_support(
        params,
        key="winning_move_label_support",
        fallback=_DEFAULTS.winning_move_label_support,
    )
    if str(query_id) == "connection_gap_count":
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="connection_gap_count_support",
            explicit_key="target_answer",
            fallback_support=_DEFAULTS.connection_gap_count_support,
            namespace=f"{TASK_ID}.target_answer.connection_gap_count",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
    else:
        candidate_count, candidate_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="candidate_count_support",
            explicit_key="candidate_count",
            fallback_support=_DEFAULTS.candidate_count_support,
            namespace=f"{TASK_ID}.candidate_count",
            balanced_flag_key="balanced_candidate_count_sampling",
            namespace_support_permutation=True,
        )
        target_label, target_label_probabilities = _resolve_label_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            support_key="winning_move_label_support",
            explicit_key="target_label",
            fallback_support=_DEFAULTS.winning_move_label_support,
            namespace=f"{TASK_ID}.target_label.winning_move_cell_label",
            balanced_flag_key="balanced_target_label_sampling",
        )
        target_index = HEX_CANDIDATE_LABELS.index(str(target_label))
        candidate_count = max(int(candidate_count), int(target_index) + 1)

    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        player_color=str(player_color),
        board_size=int(board_size),
        target_answer=None if target_answer is None else int(target_answer),
        target_label=None if target_label is None else str(target_label),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        target_label_support=tuple(str(value) for value in target_label_support),
        candidate_count=int(candidate_count),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        player_color_probabilities=dict(player_color_probabilities),
        board_size_probabilities=dict(board_size_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        target_label_probabilities=dict(target_label_probabilities),
        candidate_count_probabilities=dict(candidate_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> HexRenderParams:
    """Resolve Hex rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.hex.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.hex.layout",
        ),
        unit_scale_meta,
    )
    return HexRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        max_board_width_px=scale_games_px(params.get("max_board_width_px", group_default(_RENDER_DEFAULTS, "max_board_width_px", _DEFAULTS.max_board_width_px)), unit_scale, min_px=410),
        max_board_height_px=scale_games_px(params.get("max_board_height_px", group_default(_RENDER_DEFAULTS, "max_board_height_px", _DEFAULTS.max_board_height_px)), unit_scale, min_px=380),
        hex_border_width_px=scale_games_px(params.get("hex_border_width_px", group_default(_RENDER_DEFAULTS, "hex_border_width_px", _DEFAULTS.hex_border_width_px)), unit_scale, min_px=1),
        stone_radius_fraction=float(params.get("stone_radius_fraction", group_default(_RENDER_DEFAULTS, "stone_radius_fraction", _DEFAULTS.stone_radius_fraction))),
        candidate_label_font_size_px=scale_games_px(params.get("candidate_label_font_size_px", group_default(_RENDER_DEFAULTS, "candidate_label_font_size_px", _DEFAULTS.candidate_label_font_size_px)), unit_scale, min_px=15),
        side_band_width_px=scale_games_px(params.get("side_band_width_px", group_default(_RENDER_DEFAULTS, "side_band_width_px", _DEFAULTS.side_band_width_px)), unit_scale, min_px=4),
        layout_jitter_meta=layout_jitter,
    )


def _extra_count_bounds(params: Mapping[str, Any], *, own: bool) -> Tuple[int, int]:
    """Resolve extra-stone bounds for Hex scene clutter."""

    if bool(own):
        low_key, high_key = "min_extra_own_stones", "max_extra_own_stones"
        fallback_low, fallback_high = _DEFAULTS.min_extra_own_stones, _DEFAULTS.max_extra_own_stones
    else:
        low_key, high_key = "min_extra_opponent_stones", "max_extra_opponent_stones"
        fallback_low, fallback_high = _DEFAULTS.min_extra_opponent_stones, _DEFAULTS.max_extra_opponent_stones
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, fallback_high)))
    if low > high:
        raise ValueError(f"{low_key} must be <= {high_key}")
    return max(0, low), max(0, high)


def _add_scene_clutter(
    *,
    rng,
    rows: list[list[int]],
    player_value: int,
    protected: set[Coord],
    params: Mapping[str, Any],
    scene_variant: str,
) -> None:
    """Add non-answer stones without touching protected path cells."""

    size = len(rows)
    empties = [coord for coord in all_coords(size) if coord not in protected and rows[coord[0]][coord[1]] == EMPTY]
    rng.shuffle(empties)
    own_low, own_high = _extra_count_bounds(params, own=True)
    opp_low, opp_high = _extra_count_bounds(params, own=False)
    own_count = int(rng.randint(own_low, own_high))
    opp_count = int(rng.randint(opp_low, opp_high))
    if str(scene_variant) == "open_board":
        own_count = max(0, int(round(0.65 * own_count)))
        opp_count = max(0, int(round(0.65 * opp_count)))
    for coord in empties[:own_count]:
        rows[coord[0]][coord[1]] = int(player_value)
    for coord in empties[own_count:own_count + opp_count]:
        rows[coord[0]][coord[1]] = int(BLUE if int(player_value) == int(RED) else RED)


def _sample_winning_move_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> HexSample:
    """Sample a Hex position with exactly one immediate winning move."""

    size = int(axes.board_size)
    player_value = int(color_value(axes.player_color))
    target_label = str(axes.target_label or "A")
    candidate_count = int(axes.candidate_count)
    target_index = HEX_CANDIDATE_LABELS.index(target_label)
    candidate_count = max(candidate_count, int(target_index) + 1)
    for _attempt in range(240):
        path = tuple(make_connection_path(rng=rng, board_size=size, player_value=player_value))
        gap_candidates = list(path)
        rng.shuffle(gap_candidates)
        winning_coord = gap_candidates[0]
        rows = [[EMPTY for _col in range(size)] for _row in range(size)]
        for coord in path:
            if coord != winning_coord:
                rows[coord[0]][coord[1]] = int(player_value)
        _add_scene_clutter(
            rng=rng,
            rows=rows,
            player_value=player_value,
            protected=set(path),
            params=params,
            scene_variant=str(axes.scene_variant),
        )
        board = board_from_rows(rows)
        winning_moves = immediate_winning_moves(board, player_value=player_value)
        if tuple(winning_moves) != (tuple(winning_coord),):
            continue
        empty_distractors = [
            coord
            for coord in all_coords(size)
            if coord != winning_coord and int(board[coord[0]][coord[1]]) == EMPTY
        ]
        if len(empty_distractors) < candidate_count - 1:
            continue
        rng.shuffle(empty_distractors)
        candidate_coords = list(empty_distractors[:candidate_count - 1])
        candidate_coords.insert(target_index, winning_coord)
        candidate_specs = tuple(
            HexCandidateSpec(
                label=str(HEX_CANDIDATE_LABELS[index]),
                coord=tuple(coord),
                is_answer=bool(tuple(coord) == tuple(winning_coord)),
            )
            for index, coord in enumerate(candidate_coords)
        )
        evidence_coords = winning_path_after_move(
            board,
            player_value=player_value,
            move_coord=winning_coord,
        )
        sample = HexSample(
            board_size=size,
            query_id=str(axes.query_id),
            scene_variant=str(axes.scene_variant),
            player_color=str(axes.player_color),
            player_value=player_value,
            board=board,
            answer=str(target_label),
            target_answer=str(target_label),
            candidate_specs=candidate_specs,
            evidence_coords=tuple(evidence_coords),
            winning_move_coord=tuple(winning_coord),
            min_gap_path=tuple(),
            min_gap_empty_coords=tuple(),
            construction_mode="one_empty_cell_completes_player_connection",
        )
        validate_hex_sample(sample)
        return sample
    raise ValueError("failed to sample Hex winning move scene")


def _sample_gap_count_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> HexSample:
    """Sample a Hex position whose shortest connection gap equals target_answer."""

    size = int(axes.board_size)
    player_value = int(color_value(axes.player_color))
    target = int(axes.target_answer or 1)
    if target > size:
        raise ValueError("Hex connection gap target cannot exceed board size")
    for _attempt in range(260):
        path = tuple(make_connection_path(rng=rng, board_size=size, player_value=player_value))
        rows = [[EMPTY for _col in range(size)] for _row in range(size)]
        gap_coords = list(path)
        rng.shuffle(gap_coords)
        gap_set = set(gap_coords[:target])
        for coord in path:
            if coord not in gap_set:
                rows[coord[0]][coord[1]] = int(player_value)
        _add_scene_clutter(
            rng=rng,
            rows=rows,
            player_value=player_value,
            protected=set(path),
            params=params,
            scene_variant=str(axes.scene_variant),
        )
        board = board_from_rows(rows)
        gap_count, min_path = minimum_connection_path(board, player_value=player_value)
        if int(gap_count) != int(target):
            continue
        empty_on_path = tuple(coord for coord in min_path if int(board[coord[0]][coord[1]]) == EMPTY)
        gap_search = minimum_connection_gap_sets(board, player_value=player_value, max_sets=2)
        if not bool(gap_search.exhaustive):
            continue
        if int(gap_search.gap_count) != int(target) or len(gap_search.gap_sets) != 1:
            continue
        if tuple(gap_search.gap_sets[0]) != sorted_coords(empty_on_path):
            continue
        sample = HexSample(
            board_size=size,
            query_id=str(axes.query_id),
            scene_variant=str(axes.scene_variant),
            player_color=str(axes.player_color),
            player_value=player_value,
            board=board,
            answer=int(target),
            target_answer=int(target),
            candidate_specs=tuple(),
            evidence_coords=tuple(gap_search.gap_sets[0]),
            winning_move_coord=None,
            min_gap_path=tuple(min_path),
            min_gap_empty_coords=tuple(gap_search.gap_sets[0]),
            construction_mode="unique_minimum_gap_empty_cell_set",
        )
        validate_hex_sample(sample)
        return sample
    raise ValueError("failed to sample Hex connection gap scene")


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> HexSample:
    """Construct one Hex scene for the requested axes."""

    if str(axes.query_id) == "winning_move_cell_label":
        return _sample_winning_move_scene(rng=rng, axes=axes, params=params)
    if str(axes.query_id) == "connection_gap_count":
        return _sample_gap_count_scene(rng=rng, axes=axes, params=params)
    raise ValueError(f"unsupported Hex query_id: {axes.query_id}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Hex JSON output."""

    if str(query_id) == "winning_move_cell_label":
        answer_value: str | int = "C"
    else:
        answer_value = 3
    evidence_value = [[120, 190, 180, 250], [180, 220, 240, 280], [240, 250, 300, 310]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesHexBoardTask:
    """Return one grounded query over a visible Hex board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "hex"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: HexSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes, params=params)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid Hex scene after {max_attempts} attempts")

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_hex_board_scene(
            board=sampled_scene.board,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            player_color=str(axes.player_color),
            candidate_labels_by_coord={
                tuple(spec.coord): str(spec.label)
                for spec in sampled_scene.candidate_specs
            },
            params=render_params,
        )
        evidence_entity_ids = [coord_to_cell_id(coord) for coord in sampled_scene.evidence_coords]
        evidence_bboxes = [
            list(rendered_scene.render_map["cell_bboxes_px"][str(entity_id)])
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
                "object_description_open_board",
                "object_description_crowded_board",
                "hex_rule_text",
                "red_goal_text",
                "blue_goal_text",
                "answer_hint_winning_move_cell_label",
                "evidence_hint_winning_move_cell_label",
                "answer_hint_connection_gap_count",
                "evidence_hint_connection_gap_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        query_player = color_name(sampled_scene.player_value)
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        answer_hint = str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]).format(query_player=query_player)
        evidence_hint = str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]).format(query_player=query_player)
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
                "answer_hint": str(answer_hint),
                "evidence_hint": str(evidence_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "hex_rule_text": str(prompt_defaults["hex_rule_text"]),
                "red_goal_text": str(prompt_defaults["red_goal_text"]),
                "blue_goal_text": str(prompt_defaults["blue_goal_text"]),
                "query_player": str(query_player),
                "query_player_lower": str(query_player).lower(),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        if str(axes.query_id) == "winning_move_cell_label":
            answer_gt = TypedValue(type="string", value=str(sampled_scene.answer))
        else:
            answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        occupied_count = sum(1 for coord in all_coords(sampled_scene.board_size) if sampled_scene.board[coord[0]][coord[1]] != EMPTY)
        complexity = build_games_hex_board_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            board_size=int(sampled_scene.board_size),
            occupied_count=int(occupied_count),
            target_answer=sampled_scene.target_answer,
            evidence_count=len(evidence_entity_ids),
            candidate_count=len(sampled_scene.candidate_specs),
        )
        candidate_trace = [
            {
                "label": str(spec.label),
                "coord": [int(spec.coord[0]), int(spec.coord[1])],
                "cell_id": coord_to_cell_id(spec.coord),
                "is_answer": bool(spec.is_answer),
            }
            for spec in sampled_scene.candidate_specs
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_hex_board_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "player_color": str(axes.player_color),
                    "board_size": int(sampled_scene.board_size),
                    "evidence_entity_ids": [str(entity_id) for entity_id in evidence_entity_ids],
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
                    "player_color": str(axes.player_color),
                    "board_size": int(sampled_scene.board_size),
                    "candidate_count": int(len(sampled_scene.candidate_specs)),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "player_color_probabilities": dict(axes.player_color_probabilities),
                    "board_size_probabilities": dict(axes.board_size_probabilities),
                    "target_answer": sampled_scene.target_answer,
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "target_label": axes.target_label,
                    "target_label_support": [str(value) for value in axes.target_label_support],
                    "target_label_probabilities": dict(axes.target_label_probabilities),
                    "candidate_count_probabilities": dict(axes.candidate_count_probabilities),
                    "occupied_count": int(occupied_count),
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
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "player_color": str(axes.player_color),
                "player_value": int(sampled_scene.player_value),
                "board_size": int(sampled_scene.board_size),
                "board_rows": [[int(value) for value in row] for row in sampled_scene.board],
                "target_answer": sampled_scene.target_answer,
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "target_label": axes.target_label,
                "target_label_support": [str(value) for value in axes.target_label_support],
                "candidate_specs": candidate_trace,
                "winning_move_coord": None if sampled_scene.winning_move_coord is None else [int(sampled_scene.winning_move_coord[0]), int(sampled_scene.winning_move_coord[1])],
                "min_gap_path": [[int(row), int(col)] for row, col in sampled_scene.min_gap_path],
                "min_gap_empty_coords": [[int(row), int(col)] for row, col in sampled_scene.min_gap_empty_coords],
                "evidence_coords": [[int(row), int(col)] for row, col in sampled_scene.evidence_coords],
                "evidence_entity_ids": [str(entity_id) for entity_id in evidence_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
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
            scene_id="hex",
            query_id=str(axes.query_id),
        )


@register_task
class GamesHexWinningMoveCellLabelTask(FixedQueryVariantTaskMixin, GamesHexBoardTask):
    """Choose the labeled empty cell that gives the queried Hex player an immediate win."""

    task_id = "task_games__hex__winning_move_cell_label"
    fixed_query_id = "winning_move_cell_label"


@register_task
class GamesHexConnectionGapCountTask(FixedQueryVariantTaskMixin, GamesHexBoardTask):
    """Count minimum empty cells needed for the queried Hex player to connect sides."""

    task_id = "task_games__hex__connection_gap_count"
    fixed_query_id = "connection_gap_count"


__all__ = [
    "GamesHexBoardTask",
    "GamesHexConnectionGapCountTask",
    "GamesHexWinningMoveCellLabelTask",
]
