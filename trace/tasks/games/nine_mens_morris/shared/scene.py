"""Scene-local primitives for nine-men's-morris tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.games.shared.layout import (
    attach_games_unit_size_jitter,
    resolve_games_layout_jitter,
    resolve_games_unit_size_scale,
    scale_games_px,
)
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.style import SUPPORTED_NINE_MENS_MORRIS_STYLE_VARIANTS
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults
from trace.tasks.shared.config_defaults import group_default, required_group_defaults
from trace.tasks.shared.font_assets import get_font_family_record, sample_font_family
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support

from .common import (
    SUPPORTED_NINE_MENS_MORRIS_SCENE_VARIANTS,
    NineMensMorrisBoardState,
    annotation_piece_ids,
    build_nine_mens_morris_board_state,
)
from .rendering import NineMensMorrisRenderParams, render_nine_mens_morris_scene


SCENE_ID = "nine_mens_morris"
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


@dataclass(frozen=True)
class _RenderDefaults:
    """Stable rendering fallback defaults for nine-men's-morris scenes."""

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
class ResolvedAxes:
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


@dataclass(frozen=True)
class GeneratedComponents:
    """Rendered and prompted scene components before public output wrapping."""

    prompt: str
    prompt_variants: Dict[str, str]
    answer_gt: TypedValue
    annotation_gt: TypedValue
    image: Any
    trace_payload: Dict[str, Any]
    query_id: str


_DEFAULTS = _RenderDefaults()


def _resolve_named_axis(
    *,
    gen_defaults: Mapping[str, Any],
    namespace_root: str,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named axis."""

    return resolve_games_named_axis(
        task_id=str(namespace_root),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace=f"{namespace_root}.{namespace}",
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=tuple(str(value) for value in supported),
    )


def resolve_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    target_support_key: str,
    target_fallback_support: Sequence[int],
) -> ResolvedAxes:
    """Resolve semantic/visual axes plus one target answer."""

    player_color = {
        "white_mill_completion_point_count": "white",
        "black_mill_completion_point_count": "black",
    }.get(str(query_id))
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_NINE_MENS_MORRIS_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_NINE_MENS_MORRIS_STYLE_VARIANTS,
    )
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key=str(target_support_key),
        explicit_key="target_answer",
        fallback_support=tuple(int(value) for value in target_fallback_support),
        namespace=f"{namespace}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key=str(target_support_key),
        fallback=tuple(int(value) for value in target_fallback_support),
    )
    return ResolvedAxes(
        query_id=str(query_id),
        player_color=str(player_color) if player_color is not None else None,
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        player_color_probabilities={},
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def resolve_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    namespace: str,
    instance_seed: int,
) -> NineMensMorrisRenderParams:
    """Resolve stable render parameters for one Morris scene."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.unit_size",
        fallback_min=0.55,
        fallback_max=1.10,
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            render_defaults,
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.layout",
        ),
        unit_scale_meta,
    )
    board_width_px = scale_games_px(
        params.get("board_width_px", group_default(render_defaults, "board_width_px", _DEFAULTS.board_width_px)),
        unit_scale,
        min_px=470,
    )
    board_height_px = scale_games_px(
        params.get("board_height_px", group_default(render_defaults, "board_height_px", _DEFAULTS.board_height_px)),
        unit_scale,
        min_px=360,
    )
    default_canvas_width = int(group_default(render_defaults, "canvas_width", _DEFAULTS.canvas_width))
    default_canvas_height = int(group_default(render_defaults, "canvas_height", _DEFAULTS.canvas_height))
    canvas_width = int(max(620, min(default_canvas_width, int(board_width_px) + 250)))
    canvas_height = int(max(500, min(default_canvas_height, int(board_height_px) + 190)))
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.font_family",
        params=params,
    )
    return NineMensMorrisRenderParams(
        canvas_width=int(params.get("canvas_width", canvas_width)),
        canvas_height=int(params.get("canvas_height", canvas_height)),
        board_width_px=int(board_width_px),
        board_height_px=int(board_height_px),
        board_corner_radius_px=scale_games_px(
            params.get("board_corner_radius_px", group_default(render_defaults, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px)),
            unit_scale,
            min_px=12,
        ),
        panel_margin_px=scale_games_px(params.get("panel_margin_px", group_default(render_defaults, "panel_margin_px", _DEFAULTS.panel_margin_px)), unit_scale, min_px=30),
        title_font_size_px=scale_games_px(
            params.get("title_font_size_px", group_default(render_defaults, "title_font_size_px", _DEFAULTS.title_font_size_px)),
            unit_scale,
            min_px=18,
        ),
        title_band_height_px=scale_games_px(
            params.get("title_band_height_px", group_default(render_defaults, "title_band_height_px", _DEFAULTS.title_band_height_px)),
            unit_scale,
            min_px=38,
        ),
        board_padding_px=scale_games_px(params.get("board_padding_px", group_default(render_defaults, "board_padding_px", _DEFAULTS.board_padding_px)), unit_scale, min_px=38),
        piece_radius_px=scale_games_px(params.get("piece_radius_px", group_default(render_defaults, "piece_radius_px", _DEFAULTS.piece_radius_px)), unit_scale, min_px=13),
        node_radius_px=scale_games_px(params.get("node_radius_px", group_default(render_defaults, "node_radius_px", _DEFAULTS.node_radius_px)), unit_scale, min_px=3),
        font_family=str(font_family),
        layout_jitter_meta=layout_jitter,
    )


def sample_scene(*, rng: Any, axes: ResolvedAxes) -> NineMensMorrisBoardState:
    """Construct one board state for the requested axes."""

    return build_nine_mens_morris_board_state(
        rng=rng,
        mode=str(axes.query_id),
        player_color=axes.player_color,
        target_answer=int(axes.target_answer),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return answer+annotation and answer-only JSON examples."""

    json_example = json.dumps({"annotation": [[202, 242], [362, 242]], "answer": 5}, ensure_ascii=True)
    json_example_answer_only = json.dumps({"answer": 5}, ensure_ascii=True)
    return json_example, json_example_answer_only


def build_components(
    *,
    board_state: NineMensMorrisBoardState,
    axes: ResolvedAxes,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    namespace: str,
) -> GeneratedComponents:
    """Render, prompt, annotate, and trace one Morris board state."""

    render_params = resolve_render_params(
        params,
        render_defaults=render_defaults,
        namespace=str(namespace),
        instance_seed=int(instance_seed),
    )
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.panel_scene_style",
        treatment_weights=params.get("panel_scene_treatment_weights", group_default(render_defaults, "panel_scene_treatment_weights", None)),
        palette_weights=params.get("panel_scene_palette_weights", group_default(render_defaults, "panel_scene_palette_weights", None)),
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
    annotation_ids = annotation_piece_ids(board_state, mode=str(axes.query_id), player_color=axes.player_color)
    annotation_map_key = (
        "node_centers_px"
        if str(axes.query_id) in {"white_mill_completion_point_count", "black_mill_completion_point_count"}
        else "piece_centers_px"
    )
    annotation_points = [
        list(rendered_scene.render_map[str(annotation_map_key)][str(entity_id)])
        for entity_id in annotation_ids
    ]
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    resolved_prompt_defaults = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_single_board",
            "mill_rule_text",
            "answer_hint_all_pieces_in_mill_count",
            "answer_hint_white_mill_completion_point_count",
            "answer_hint_black_mill_completion_point_count",
            "annotation_hint_all_pieces_in_mill_count",
            "annotation_hint_white_mill_completion_point_count",
            "annotation_hint_black_mill_completion_point_count",
        ),
        context=f"prompt defaults for {namespace}",
    )
    json_example, json_example_answer_only = _build_prompt_json_examples()
    prompt_selection = render_scene_prompt_variants(
        domain="games",
        scene_id=SCENE_ID,
        bundle_id=str(resolved_prompt_defaults["bundle_id"]),
        scene_key=str(resolved_prompt_defaults["scene_key"]),
        task_key=str(resolved_prompt_defaults["task_key"]),
        query_key=str(axes.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "object_description": str(resolved_prompt_defaults["object_description_single_board"]),
            "json_output_contract": str(resolved_prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(resolved_prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(resolved_prompt_defaults[f"answer_hint_{str(axes.query_id)}"]).format(player_color=str(axes.player_color or "white")),
            "annotation_hint": str(resolved_prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]).format(player_color=str(axes.player_color or "white")),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
            "mill_rule_text": str(resolved_prompt_defaults["mill_rule_text"]),
            "player_color": str(axes.player_color or "white"),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
    annotation_gt = TypedValue(type="point_set", value=[list(point) for point in annotation_points])
    text_style_meta = {
        "font_family": str(render_params.font_family),
        "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
    }
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
                "annotation_entity_ids": list(annotation_ids),
            },
        },
        "query_spec": {
            "query_id": str(axes.query_id),
            "template_id": str(resolved_prompt_defaults["bundle_id"]),
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
            "white_mill_completion_node_labels": [str(value) for value in board_state.white_mill_completion_node_labels],
            "black_mill_completion_node_labels": [str(value) for value in board_state.black_mill_completion_node_labels],
            "overlapping_piece_ids": [str(value) for value in board_state.overlapping_piece_ids],
            "annotation_map_key": str(annotation_map_key),
            "annotation_entity_ids": [str(value) for value in annotation_ids],
        },
        "witness_symbolic": {"type": "object_set", "ids": [str(value) for value in annotation_ids]},
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
        query_id=str(axes.query_id),
    )


__all__ = [
    "GeneratedComponents",
    "POST_IMAGE_NOISE_DEFAULTS",
    "ResolvedAxes",
    "SCENE_ID",
    "build_components",
    "resolve_axes",
    "resolve_render_params",
    "sample_scene",
]
