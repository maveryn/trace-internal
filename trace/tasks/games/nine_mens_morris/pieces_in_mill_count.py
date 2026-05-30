"""Games nine-men's-morris task for counting pieces that belong to mills."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import build_games_nine_mens_morris_pieces_in_mill_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.morris_common import (
    SUPPORTED_NINE_MENS_MORRIS_QUERY_IDS,
    SUPPORTED_NINE_MENS_MORRIS_SCENE_VARIANTS,
    NineMensMorrisBoardState,
    build_nine_mens_morris_board_state,
    evidence_piece_ids,
    supported_targets_for_query,
)
from ..shared.morris_scene import NineMensMorrisRenderParams, render_nine_mens_morris_scene
from ..shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.style import SUPPORTED_NINE_MENS_MORRIS_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_noise_defaults


TASK_ID = "games_nine_mens_morris_pieces_in_mill_count_base"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible nine-men's-morris scenes."""

    all_pieces_in_mill_count_support: Tuple[int, ...] = (0, 3, 5, 6, 7, 8, 9)
    canvas_width: int = 1180
    canvas_height: int = 820
    board_width_px: int = 860
    board_height_px: int = 660
    board_corner_radius_px: int = 24
    panel_margin_px: int = 56
    title_font_size_px: int = 34
    title_band_height_px: int = 62
    board_padding_px: int = 72
    piece_radius_px: int = 22
    node_radius_px: int = 5


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one nine-men's-morris scene."""

    query_id: str
    player_color: str | None
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    player_color_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "nine_mens_morris")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="nine_mens_morris", apply_prob=0.5)

def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query id, honoring `query_id` as an alias."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_id")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_NINE_MENS_MORRIS_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_NINE_MENS_MORRIS_QUERY_IDS,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_ID}.query_id",
    )
    return str(selected), dict(probabilities)


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
    """Resolve one balanced named axis for the nine-men's-morris task."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported,
        explicit_key=explicit_key,
        weights_key=weights_key,
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=supported,
        balance_flag_key=balance_flag_key,
        explicit_key=explicit_key,
        weights_key=weights_key,
        sampling_namespace=f"{TASK_ID}.{namespace}",
    )
    return str(selected), dict(probabilities)


def _uses_uniform_query_cycle(params: Mapping[str, Any], probabilities: Mapping[str, float]) -> bool:
    """Return true when the query axis is using the default balanced cycle."""

    if params.get("query_id") is not None or params.get("query_id") is not None:
        return False
    enabled = bool(
        params.get(
            "balanced_query_id_sampling",
            group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True),
        )
    )
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(SUPPORTED_NINE_MENS_MORRIS_QUERY_IDS):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for axes balanced under the query cycle."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(params, query_id_probabilities):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(SUPPORTED_NINE_MENS_MORRIS_QUERY_IDS))
    return cycle_params


def _style_variant_params_for_query_cycle(
    params: Mapping[str, Any],
    *,
    query_id_probabilities: Mapping[str, float],
) -> Dict[str, Any]:
    """Decorrelate balanced style cycling from balanced query cycling."""

    if params.get("style_variant") is not None:
        return dict(params)
    enabled = bool(
        params.get(
            "balanced_style_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_style_variant_sampling", True),
        )
    )
    if not enabled:
        return dict(params)
    raw_weights = params.get(
        "style_variant_weights",
        group_default(
            _GEN_DEFAULTS,
            "style_variant_weights",
            {key: 1.0 for key in SUPPORTED_NINE_MENS_MORRIS_STYLE_VARIANTS},
        ),
    )
    if not isinstance(raw_weights, Mapping):
        return dict(params)
    positives = [
        float(raw_weights.get(str(value), 0.0))
        for value in SUPPORTED_NINE_MENS_MORRIS_STYLE_VARIANTS
        if float(raw_weights.get(str(value), 0.0)) > 0.0
    ]
    if len(positives) != len(SUPPORTED_NINE_MENS_MORRIS_STYLE_VARIANTS):
        return dict(params)
    if max(positives) - min(positives) > 1e-9:
        return dict(params)
    return _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    )


def _target_support_key(query_id: str) -> str:
    """Return the configured target-support key for one Morris query id."""

    return {
        "all_pieces_in_mill_count": "all_pieces_in_mill_count_support",
    }[str(query_id)]


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic/visual axes plus one target answer for the Morris task."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
    )
    player_color = None
    player_color_probabilities: Dict[str, float] = {}
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_NINE_MENS_MORRIS_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=_style_variant_params_for_query_cycle(
            params,
            query_id_probabilities=query_id_probabilities,
        ),
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_NINE_MENS_MORRIS_STYLE_VARIANTS,
    )

    target_support_key = _target_support_key(str(query_id))
    target_params = _params_for_query_occurrence_cycle(
        params,
        query_id_probabilities=query_id_probabilities,
    )
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(target_support_key),
        explicit_key="target_answer",
        fallback_support=supported_targets_for_query(str(query_id), player_color=player_color),
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(target_support_key),
        fallback=supported_targets_for_query(str(query_id), player_color=player_color),
    )
    return _ResolvedAxes(
        query_id=str(query_id),
        player_color=str(player_color) if player_color is not None else None,
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        player_color_probabilities=dict(player_color_probabilities),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> NineMensMorrisRenderParams:
    """Resolve stable render parameters for one Morris scene."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.nine_mens_morris.unit_size",
        fallback_min=0.55,
        fallback_max=1.10,
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.nine_mens_morris.layout",
        ),
        unit_scale_meta,
    )
    board_width_px = scale_games_px(
        params.get("board_width_px", group_default(_RENDER_DEFAULTS, "board_width_px", _DEFAULTS.board_width_px)),
        unit_scale,
        min_px=470,
    )
    board_height_px = scale_games_px(
        params.get("board_height_px", group_default(_RENDER_DEFAULTS, "board_height_px", _DEFAULTS.board_height_px)),
        unit_scale,
        min_px=360,
    )
    default_canvas_width = int(group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))
    default_canvas_height = int(group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))
    canvas_width = int(max(620, min(default_canvas_width, int(board_width_px) + 250)))
    canvas_height = int(max(500, min(default_canvas_height, int(board_height_px) + 190)))
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace="games.nine_mens_morris.font_family",
        params=params,
    )
    return NineMensMorrisRenderParams(
        canvas_width=int(params.get("canvas_width", canvas_width)),
        canvas_height=int(params.get("canvas_height", canvas_height)),
        board_width_px=int(board_width_px),
        board_height_px=int(board_height_px),
        board_corner_radius_px=scale_games_px(
            params.get("board_corner_radius_px", group_default(_RENDER_DEFAULTS, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px)),
            unit_scale,
            min_px=12,
        ),
        panel_margin_px=scale_games_px(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px)), unit_scale, min_px=30),
        title_font_size_px=scale_games_px(
            params.get("title_font_size_px", group_default(_RENDER_DEFAULTS, "title_font_size_px", _DEFAULTS.title_font_size_px)),
            unit_scale,
            min_px=18,
        ),
        title_band_height_px=scale_games_px(
            params.get("title_band_height_px", group_default(_RENDER_DEFAULTS, "title_band_height_px", _DEFAULTS.title_band_height_px)),
            unit_scale,
            min_px=38,
        ),
        board_padding_px=scale_games_px(params.get("board_padding_px", group_default(_RENDER_DEFAULTS, "board_padding_px", _DEFAULTS.board_padding_px)), unit_scale, min_px=38),
        piece_radius_px=scale_games_px(params.get("piece_radius_px", group_default(_RENDER_DEFAULTS, "piece_radius_px", _DEFAULTS.piece_radius_px)), unit_scale, min_px=13),
        node_radius_px=scale_games_px(params.get("node_radius_px", group_default(_RENDER_DEFAULTS, "node_radius_px", _DEFAULTS.node_radius_px)), unit_scale, min_px=3),
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return answer+evidence and answer-only JSON examples for the Morris task."""

    json_example = json.dumps(
        {
            "evidence": [
                [202, 242],
                [362, 242],
            ],
            "answer": 5,
        },
        ensure_ascii=True,
    )
    json_example_answer_only = json.dumps({"answer": 5}, ensure_ascii=True)
    return json_example, json_example_answer_only


class GamesNineMensMorrisPiecesInMillCountTask:
    """Return one grounded count of pieces that belong to mills on a visible Morris board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "nine_mens_morris"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params, instance_seed=int(instance_seed))

        board_state: NineMensMorrisBoardState | None = None
        rendered_scene = None
        background_meta: Dict[str, Any] | None = None
        panel_style_meta: Dict[str, Any] | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            board_state = build_nine_mens_morris_board_state(
                rng=attempt_rng,
                query_id=str(axes.query_id),
                player_color=axes.player_color,
                target_answer=int(axes.target_answer),
            )
            panel_style, panel_style_meta = resolve_game_panel_scene_style(
                instance_seed=int(instance_seed),
                namespace="games.nine_mens_morris.panel_scene_style",
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
            rendered_scene = render_nine_mens_morris_scene(
                board_state=board_state,
                background=background,
                scene_variant=str(axes.scene_variant),
                style_variant=str(axes.style_variant),
                params=render_params,
                panel_style=panel_style,
            )
            break

        if board_state is None or rendered_scene is None or background_meta is None or panel_style_meta is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        evidence_ids = evidence_piece_ids(
            board_state,
            query_id=str(axes.query_id),
            player_color=axes.player_color,
        )
        evidence_points = [
            list(rendered_scene.render_map["piece_centers_px"][str(piece_id)])
            for piece_id in evidence_ids
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
                "object_description_single_board",
                "mill_rule_text",
                "answer_hint_all_pieces_in_mill_count",
                "evidence_hint_all_pieces_in_mill_count",
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
                "object_description": str(prompt_defaults["object_description_single_board"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]).format(
                    player_color=str(axes.player_color or "white")
                ),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]).format(
                    player_color=str(axes.player_color or "white")
                ),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "mill_rule_text": str(prompt_defaults["mill_rule_text"]),
                "player_color": str(axes.player_color or "white"),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        evidence_gt = TypedValue(type="point_set", value=[list(point) for point in evidence_points])
        text_style_meta = {
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        }
        total_piece_count = len(board_state.piece_specs)
        complexity = build_games_nine_mens_morris_pieces_in_mill_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            query_id=str(axes.query_id),
            total_piece_count=int(total_piece_count),
            target_answer=int(axes.target_answer),
            overlapping_piece_count=len(board_state.overlapping_piece_ids),
            evidence_count=len(evidence_ids),
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_nine_mens_morris_single_board",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "player_color": axes.player_color,
                    "style_variant": str(axes.style_variant),
                    "target_answer": int(axes.target_answer),
                    "evidence_entity_ids": list(evidence_ids),
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
                    "player_color": axes.player_color,
                    "style_variant": str(axes.style_variant),
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
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(panel_style_meta),
                "text_style": dict(text_style_meta),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "player_color": axes.player_color,
                "style_variant": str(axes.style_variant),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "piece_specs": [
                    {
                        "piece_id": str(spec.piece_id),
                        "node_index": int(spec.node_index),
                        "node_label": str(spec.node_label),
                        "color": str(spec.color),
                    }
                    for spec in board_state.piece_specs
                ],
                "white_piece_ids_in_mill": [str(value) for value in board_state.white_piece_ids_in_mill],
                "black_piece_ids_in_mill": [str(value) for value in board_state.black_piece_ids_in_mill],
                "all_piece_ids_in_mill": [str(value) for value in board_state.all_piece_ids_in_mill],
                "white_mill_ids": [str(value) for value in board_state.white_mill_ids],
                "black_mill_ids": [str(value) for value in board_state.black_mill_ids],
                "overlapping_piece_ids": [str(value) for value in board_state.overlapping_piece_ids],
                "evidence_entity_ids": [str(value) for value in evidence_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(value) for value in evidence_ids],
            },
            "projected_evidence": {
                "type": "point_set",
                "point_set": [list(point) for point in evidence_points],
                "pixel_point_set": [list(point) for point in evidence_points],
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
            query_id=str(axes.query_id),
            scene_id="nine_mens_morris",
        )


@register_task
class GamesNineMensMorrisAllPiecesInMillCountTask(
    FixedQueryVariantTaskMixin,
    GamesNineMensMorrisPiecesInMillCountTask,
):
    """Count all pieces that belong to at least one mill."""

    task_id = "task_games__nine_mens_morris__pieces_in_mill_count"
    fixed_query_id = "all_pieces_in_mill_count"


__all__ = [
    "GamesNineMensMorrisAllPiecesInMillCountTask",
]
