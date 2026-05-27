"""Games Battleship-grid tasks over placed fleet ships and hit markers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

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
from ..shared.battleship_common import (
    FLEET_SHAPES,
    SUPPORTED_BATTLESHIP_QUERY_VARIANTS,
    SUPPORTED_BATTLESHIP_SCENE_VARIANTS,
    BattleshipSample,
    BattleshipShipPlacement,
    Coord,
    all_coords,
    coord_to_cell_id,
    shape_orientations,
    sorted_coords,
    validate_battleship_sample,
)
from ..shared.battleship_scene import BattleshipRenderParams, render_battleship_grid_scene
from ..shared.complexity import build_games_battleship_grid_complexity
from ..shared.fixed_query_task import QuerySubsetTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_variant
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.style import SUPPORTED_BATTLESHIP_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_battleship_grid_base"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Battleship tracking-grid scenes."""

    sunk_ship_count_support: Tuple[int, ...] = (1, 2, 3, 4)
    partial_ship_count_support: Tuple[int, ...] = (1, 2, 3, 4)
    board_size_support: Tuple[int, ...] = (8, 9, 10)
    min_partial_ship_count: int = 2
    max_partial_ship_count: int = 4
    min_miss_count: int = 7
    max_miss_count: int = 16
    canvas_width: int = 1100
    canvas_height: int = 820
    panel_margin_px: int = 48
    max_board_size_px: int = 650
    board_border_width_px: int = 5
    grid_line_width_px: int = 2
    cell_padding_px: int = 7
    fleet_panel_width_px: int = 310
    board_panel_gap_px: int = 34
    fleet_icon_cell_px: int = 18
    label_font_size_px: int = 22


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Battleship instance."""

    query_variant: str
    scene_variant: str
    style_variant: str
    board_size: int
    target_answer: int | None
    target_answer_support: Tuple[int, ...]
    query_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    board_size_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "battleship")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="battleship", apply_prob=0.0)


def _target_support_key(query_variant: str) -> str:
    """Return the configured answer-support key for one Battleship query."""

    return {
        "sunk_ship_count": "sunk_ship_count_support",
        "partial_ship_count": "partial_ship_count_support",
    }[str(query_variant)]


def _resolve_query_variant(*, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Battleship query variant."""

    return resolve_games_query_variant(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_BATTLESHIP_QUERY_VARIANTS,
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
    """Resolve one balanced named Battleship axis."""

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


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Battleship instance."""

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
        supported=SUPPORTED_BATTLESHIP_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_BATTLESHIP_STYLE_VARIANTS,
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
    support_key = _target_support_key(str(query_variant))
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=getattr(_DEFAULTS, support_key),
        namespace=f"{TASK_ID}.target_answer.{str(query_variant)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(support_key),
        fallback=getattr(_DEFAULTS, support_key),
    )
    return _ResolvedAxes(
        query_variant=str(query_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        board_size=int(board_size),
        target_answer=None if target_answer is None else int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        query_variant_probabilities=dict(query_variant_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        board_size_probabilities=dict(board_size_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> BattleshipRenderParams:
    """Resolve Battleship rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.battleship.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.battleship.layout",
        ),
        unit_scale_meta,
    )
    return BattleshipRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        max_board_size_px=scale_games_px(params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px)), unit_scale, min_px=320),
        board_border_width_px=scale_games_px(params.get("board_border_width_px", group_default(_RENDER_DEFAULTS, "board_border_width_px", _DEFAULTS.board_border_width_px)), unit_scale, min_px=2),
        grid_line_width_px=scale_games_px(params.get("grid_line_width_px", group_default(_RENDER_DEFAULTS, "grid_line_width_px", _DEFAULTS.grid_line_width_px)), unit_scale, min_px=1),
        cell_padding_px=scale_games_px(params.get("cell_padding_px", group_default(_RENDER_DEFAULTS, "cell_padding_px", _DEFAULTS.cell_padding_px)), unit_scale, min_px=3),
        fleet_panel_width_px=int(params.get("fleet_panel_width_px", group_default(_RENDER_DEFAULTS, "fleet_panel_width_px", _DEFAULTS.fleet_panel_width_px))),
        board_panel_gap_px=int(params.get("board_panel_gap_px", group_default(_RENDER_DEFAULTS, "board_panel_gap_px", _DEFAULTS.board_panel_gap_px))),
        fleet_icon_cell_px=scale_games_px(params.get("fleet_icon_cell_px", group_default(_RENDER_DEFAULTS, "fleet_icon_cell_px", _DEFAULTS.fleet_icon_cell_px)), unit_scale, min_px=9),
        label_font_size_px=scale_games_px(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px)), unit_scale, min_px=12),
        layout_jitter_meta=layout_jitter,
    )


def _inflated_cells(coords: Iterable[Coord], *, board_size: int) -> set[Coord]:
    """Return a one-cell Chebyshev margin around a ship."""

    inflated: set[Coord] = set()
    for row, col in coords:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr = int(row) + int(dr)
                nc = int(col) + int(dc)
                if 0 <= nr < int(board_size) and 0 <= nc < int(board_size):
                    inflated.add((nr, nc))
    return inflated


def _place_offsets(
    *,
    rng,
    board_size: int,
    offsets: Sequence[Coord],
    forbidden: set[Coord],
) -> Tuple[Coord, ...]:
    """Place one ship on the board without touching existing ships."""

    orientations = list(shape_orientations(offsets))
    rng.shuffle(orientations)
    for oriented in orientations:
        max_row = max(row for row, _col in oriented)
        max_col = max(col for _row, col in oriented)
        starts = [
            (row, col)
            for row in range(0, int(board_size) - int(max_row))
            for col in range(0, int(board_size) - int(max_col))
        ]
        rng.shuffle(starts)
        for start_row, start_col in starts:
            candidate = tuple((int(start_row) + int(row), int(start_col) + int(col)) for row, col in oriented)
            if not (set(candidate) & forbidden):
                return sorted_coords(candidate)
    raise ValueError("failed to place Battleship ship")


def _miss_count_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve miss-marker count bounds."""

    low = int(params.get("min_miss_count", group_default(_GEN_DEFAULTS, "min_miss_count", _DEFAULTS.min_miss_count)))
    high = int(params.get("max_miss_count", group_default(_GEN_DEFAULTS, "max_miss_count", _DEFAULTS.max_miss_count)))
    if low > high:
        raise ValueError("min_miss_count must be <= max_miss_count")
    return max(0, int(low)), max(0, int(high))


def _partial_ship_count_bounds(params: Mapping[str, Any]) -> Tuple[int, int]:
    """Resolve partially hit ship count bounds."""

    low = int(
        params.get(
            "min_partial_ship_count",
            group_default(_GEN_DEFAULTS, "min_partial_ship_count", _DEFAULTS.min_partial_ship_count),
        )
    )
    high = int(
        params.get(
            "max_partial_ship_count",
            group_default(_GEN_DEFAULTS, "max_partial_ship_count", _DEFAULTS.max_partial_ship_count),
        )
    )
    if low > high:
        raise ValueError("min_partial_ship_count must be <= max_partial_ship_count")
    return max(0, int(low)), max(0, int(high))


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> BattleshipSample:
    """Construct one Battleship tracking-grid scene for the requested axes."""

    if str(axes.query_variant) not in SUPPORTED_BATTLESHIP_QUERY_VARIANTS:
        raise ValueError(f"unsupported Battleship query_variant: {axes.query_variant}")

    board_size = int(axes.board_size)
    target_answer = int(axes.target_answer or 1)
    if target_answer < 1 or target_answer > len(FLEET_SHAPES):
        raise ValueError(f"unsupported Battleship target_answer: {target_answer}")
    fleet_size = len(FLEET_SHAPES)
    if str(axes.query_variant) == "sunk_ship_count":
        sunk_count = int(target_answer)
        partial_low, partial_high = _partial_ship_count_bounds(params)
        partial_count = min(
            int(fleet_size) - int(sunk_count),
            int(rng.randint(int(partial_low), int(partial_high))),
        )
    else:
        partial_count = int(target_answer)
        sunk_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="sunk_ship_count_support",
            fallback=_DEFAULTS.sunk_ship_count_support,
        )
        sunk_candidates = [
            int(value)
            for value in sunk_support
            if 0 < int(value) <= int(fleet_size) - int(partial_count)
        ]
        if not sunk_candidates:
            sunk_candidates = [0]
        sunk_count = int(rng.choice(sunk_candidates))

    forbidden: set[Coord] = set()
    ship_coords_by_shape_id: dict[str, Tuple[Coord, ...]] = {}
    for shape in FLEET_SHAPES:
        coords = _place_offsets(
            rng=rng,
            board_size=int(board_size),
            offsets=shape.offsets,
            forbidden=forbidden,
        )
        ship_coords_by_shape_id[str(shape.shape_id)] = tuple(coords)
        forbidden.update(_inflated_cells(coords, board_size=int(board_size)))

    fleet_shapes = list(FLEET_SHAPES)
    rng.shuffle(fleet_shapes)
    sunk_shape_ids = {str(shape.shape_id) for shape in fleet_shapes[:sunk_count]}
    remaining_shape_ids = [str(shape.shape_id) for shape in fleet_shapes[sunk_count:]]
    partial_shape_ids = set(remaining_shape_ids[:partial_count])

    placements: list[BattleshipShipPlacement] = []
    for shape in FLEET_SHAPES:
        coords = tuple(ship_coords_by_shape_id[str(shape.shape_id)])
        if str(shape.shape_id) in sunk_shape_ids:
            ship_hit_coords = coords
            is_sunk = True
        elif str(shape.shape_id) in partial_shape_ids:
            shuffled = list(coords)
            rng.shuffle(shuffled)
            hit_count = int(rng.randint(1, max(1, len(coords) - 1)))
            ship_hit_coords = sorted_coords(shuffled[:hit_count])
            is_sunk = False
        else:
            ship_hit_coords = tuple()
            is_sunk = False
        placements.append(
            BattleshipShipPlacement(
                ship_id=str(shape.shape_id),
                shape_id=str(shape.shape_id),
                display_name=str(shape.display_name),
                coords=coords,
                hit_coords=tuple(ship_hit_coords),
                is_sunk=bool(is_sunk),
            )
        )

    hit_coords = sorted_coords(coord for ship in placements for coord in ship.hit_coords)
    ship_cells = {coord for ship in placements for coord in ship.coords}
    available_for_misses = [
        coord
        for coord in all_coords(int(board_size))
        if coord not in ship_cells
    ]
    rng.shuffle(available_for_misses)
    miss_low, miss_high = _miss_count_bounds(params)
    miss_count = min(len(available_for_misses), int(rng.randint(int(miss_low), int(miss_high))))
    miss_coords = sorted_coords(available_for_misses[:miss_count])
    if str(axes.query_variant) == "sunk_ship_count":
        evidence_coords = sorted_coords(coord for ship in placements if ship.is_sunk for coord in ship.coords)
        answer = int(sunk_count)
    else:
        evidence_coords = sorted_coords(
            coord
            for ship in placements
            if bool(ship.hit_coords) and not bool(ship.is_sunk)
            for coord in ship.coords
        )
        answer = int(partial_count)
    sample = BattleshipSample(
        board_size=int(board_size),
        query_variant=str(axes.query_variant),
        scene_variant=str(axes.scene_variant),
        answer=int(answer),
        ship_placements=tuple(placements),
        hit_coords=hit_coords,
        miss_coords=miss_coords,
        evidence_coords=evidence_coords,
        target_answer=int(target_answer),
        sunk_ship_count=int(sunk_count),
        partial_ship_count=int(partial_count),
        untouched_ship_count=int(fleet_size - int(sunk_count) - int(partial_count)),
        construction_mode="placed_fleet_with_full_partial_and_missed_shots",
    )
    validate_battleship_sample(sample)
    return sample


def _build_prompt_json_examples(query_variant: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Battleship JSON output."""

    answer_value = 2
    evidence_value = [[120, 190, 180, 250], [180, 190, 240, 250], [240, 190, 300, 250]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesBattleshipGridTask:
    """Return one grounded query over a visible Battleship tracking grid."""

    task_id = TASK_ID
    domain = "games"
    task_group = "battleship"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: BattleshipSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes, params=params)
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
            namespace="games.battleship_grid.panel_scene_style",
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
        rendered_scene = render_battleship_grid_scene(
            board_size=int(sampled_scene.board_size),
            ship_cells_by_id={
                str(ship.ship_id): tuple(ship.coords)
                for ship in sampled_scene.ship_placements
            },
            sunk_ship_ids=[
                str(ship.ship_id)
                for ship in sampled_scene.ship_placements
                if bool(ship.is_sunk)
            ],
            hit_coords=sampled_scene.hit_coords,
            miss_coords=sampled_scene.miss_coords,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
            panel_style=panel_style,
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
                "object_description_standard_fleet",
                "battleship_rule_text",
                "answer_hint_sunk_ship_count",
                "evidence_hint_sunk_ship_count",
                "answer_hint_partial_ship_count",
                "evidence_hint_partial_ship_count",
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
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_variant)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "battleship_rule_text": str(prompt_defaults["battleship_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_battleship_grid_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
            board_size=int(sampled_scene.board_size),
            hit_count=len(sampled_scene.hit_coords),
            miss_count=len(sampled_scene.miss_coords),
            target_answer=int(sampled_scene.target_answer),
            evidence_count=len(evidence_entity_ids),
        )

        ship_trace = [
            {
                "ship_id": str(ship.ship_id),
                "shape_id": str(ship.shape_id),
                "display_name": str(ship.display_name),
                "coords": [[int(row), int(col)] for row, col in ship.coords],
                "hit_coords": [[int(row), int(col)] for row, col in ship.hit_coords],
                "is_sunk": bool(ship.is_sunk),
            }
            for ship in sampled_scene.ship_placements
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_battleship_grid_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "query_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "board_size": int(sampled_scene.board_size),
                    "target_answer": int(sampled_scene.target_answer),
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
                    "board_size": int(sampled_scene.board_size),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "board_size_probabilities": dict(axes.board_size_probabilities),
                    "target_answer": int(sampled_scene.target_answer),
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "hit_count": len(sampled_scene.hit_coords),
                    "miss_count": len(sampled_scene.miss_coords),
                    "sunk_ship_count": int(sampled_scene.sunk_ship_count),
                    "partial_ship_count": int(sampled_scene.partial_ship_count),
                    "untouched_ship_count": int(sampled_scene.untouched_ship_count),
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
                "board_size": int(sampled_scene.board_size),
                "target_answer": int(sampled_scene.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "hit_coords": [[int(row), int(col)] for row, col in sampled_scene.hit_coords],
                "miss_coords": [[int(row), int(col)] for row, col in sampled_scene.miss_coords],
                "evidence_coords": [[int(row), int(col)] for row, col in sampled_scene.evidence_coords],
                "evidence_entity_ids": [str(entity_id) for entity_id in evidence_entity_ids],
                "ship_placements": ship_trace,
                "fleet_shapes": [
                    {
                        "shape_id": str(shape.shape_id),
                        "display_name": str(shape.display_name),
                        "offsets": [[int(row), int(col)] for row, col in shape.offsets],
                    }
                    for shape in FLEET_SHAPES
                ],
                "sunk_ship_count": int(sampled_scene.sunk_ship_count),
                "partial_ship_count": int(sampled_scene.partial_ship_count),
                "untouched_ship_count": int(sampled_scene.untouched_ship_count),
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
            query_variant=str(axes.query_variant),
            scene_id="battleship",
            query_id=str(axes.query_variant),
        )


@register_task
class GamesBattleshipShipStatusCountTask(QuerySubsetTaskMixin, GamesBattleshipGridTask):
    """Count fleet ships matching one sampled hit-status condition."""

    task_id = "task_games__battleship__ship_status_count"
    supported_query_variants = (
        "sunk_ship_count",
        "partial_ship_count",
    )


__all__ = [
    "GamesBattleshipGridTask",
    "GamesBattleshipShipStatusCountTask",
]
