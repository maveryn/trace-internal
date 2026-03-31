"""Games dots-and-boxes task for forced-turn capture counting."""

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
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import build_games_dots_and_boxes_capture_complexity
from ..shared.dots_boxes_common import (
    SUPPORTED_DOTS_AND_BOXES_QUERY_VARIANTS,
    SUPPORTED_DOTS_AND_BOXES_SCENE_VARIANTS,
    DotsAndBoxesBoardState,
    build_dots_and_boxes_board_state,
    evidence_box_ids,
)
from ..shared.dots_boxes_scene import DotsAndBoxesRenderParams, render_dots_and_boxes_scene
from ..shared.style import SUPPORTED_GAMES_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "task_games_dots_and_boxes_capture_count"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible dots-and-boxes capture scenes."""

    capture_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    box_rows: int = 3
    box_cols: int = 4
    canvas_width: int = 1180
    canvas_height: int = 820
    board_width_px: int = 880
    board_height_px: int = 640
    board_corner_radius_px: int = 24
    panel_margin_px: int = 56
    title_font_size_px: int = 34
    title_band_height_px: int = 62
    board_padding_px: int = 62
    dot_radius_px: int = 7
    dash_length_px: int = 30
    dash_gap_px: int = 18


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one dots-and-boxes scene."""

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
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "dots_and_boxes")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="dots_and_boxes")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="dots_and_boxes", apply_prob=0.0)


def _resolve_query_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced dots-and-boxes semantic variant."""

    alias_params = dict(params)
    if alias_params.get("query_variant") is None and alias_params.get("task_variant") is not None:
        alias_params["query_variant"] = alias_params["task_variant"]
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_variant")
    selected, probabilities = resolve_variant(
        rng,
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_DOTS_AND_BOXES_QUERY_VARIANTS,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_DOTS_AND_BOXES_QUERY_VARIANTS,
        balance_flag_key="balanced_query_variant_sampling",
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        sampling_namespace=f"{TASK_ID}.query_variant",
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
    """Resolve one balanced named axis for the dots-and-boxes task."""

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


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic/visual axes plus one target answer for the dots-and-boxes task."""

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
        supported=SUPPORTED_DOTS_AND_BOXES_SCENE_VARIANTS,
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
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="capture_count_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.capture_count_support,
        namespace=f"{TASK_ID}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_explicit_sampling_index=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="capture_count_support",
        fallback=_DEFAULTS.capture_count_support,
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


def _render_params(params: Mapping[str, Any]) -> DotsAndBoxesRenderParams:
    """Resolve stable render parameters for one dots-and-boxes scene."""

    return DotsAndBoxesRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        board_width_px=int(params.get("board_width_px", group_default(_RENDER_DEFAULTS, "board_width_px", _DEFAULTS.board_width_px))),
        board_height_px=int(
            params.get("board_height_px", group_default(_RENDER_DEFAULTS, "board_height_px", _DEFAULTS.board_height_px))
        ),
        board_corner_radius_px=int(
            params.get(
                "board_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "board_corner_radius_px", _DEFAULTS.board_corner_radius_px),
            )
        ),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        title_font_size_px=int(
            params.get("title_font_size_px", group_default(_RENDER_DEFAULTS, "title_font_size_px", _DEFAULTS.title_font_size_px))
        ),
        title_band_height_px=int(
            params.get(
                "title_band_height_px",
                group_default(_RENDER_DEFAULTS, "title_band_height_px", _DEFAULTS.title_band_height_px),
            )
        ),
        board_padding_px=int(
            params.get("board_padding_px", group_default(_RENDER_DEFAULTS, "board_padding_px", _DEFAULTS.board_padding_px))
        ),
        dot_radius_px=int(params.get("dot_radius_px", group_default(_RENDER_DEFAULTS, "dot_radius_px", _DEFAULTS.dot_radius_px))),
        dash_length_px=int(
            params.get("dash_length_px", group_default(_RENDER_DEFAULTS, "dash_length_px", _DEFAULTS.dash_length_px))
        ),
        dash_gap_px=int(params.get("dash_gap_px", group_default(_RENDER_DEFAULTS, "dash_gap_px", _DEFAULTS.dash_gap_px))),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return answer+evidence and answer-only JSON examples for the dots-and-boxes task."""

    json_example = json.dumps(
        {
            "evidence": [
                [180, 220, 300, 340],
                [310, 220, 430, 340],
            ],
            "answer": 2,
        },
        ensure_ascii=True,
    )
    json_example_answer_only = json.dumps({"answer": 2}, ensure_ascii=True)
    return json_example, json_example_answer_only


@register_task
class GamesDotsAndBoxesCaptureCountTask:
    """Return one grounded dots-and-boxes forced-turn capture count."""

    task_id = TASK_ID
    domain = "games"
    task_group = "dots_and_boxes"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params)
        box_rows = int(params.get("box_rows", group_default(_GEN_DEFAULTS, "box_rows", _DEFAULTS.box_rows)))
        box_cols = int(params.get("box_cols", group_default(_GEN_DEFAULTS, "box_cols", _DEFAULTS.box_cols)))

        board_state: DotsAndBoxesBoardState | None = None
        rendered_scene = None
        background_meta: Dict[str, Any] | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            board_state = build_dots_and_boxes_board_state(
                rng=attempt_rng,
                target_answer=int(axes.target_answer),
                box_rows=int(box_rows),
                box_cols=int(box_cols),
            )
            background, background_meta = make_background_canvas(
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            rendered_scene = render_dots_and_boxes_scene(
                board_state=board_state,
                background=background,
                scene_variant=str(axes.scene_variant),
                style_variant=str(axes.style_variant),
                params=render_params,
            )
            break

        if board_state is None or rendered_scene is None or background_meta is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        evidence_ids = evidence_box_ids(board_state)
        evidence_bboxes = [list(rendered_scene.render_map["box_bboxes_px"][str(box_id)]) for box_id in evidence_ids]
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
                "object_description_single_board",
                "forced_turn_rule_text",
                "answer_hint_forced_turn_capture_count",
                "evidence_hint_forced_turn_capture_count",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(axes.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_single_board"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint_forced_turn_capture_count"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_forced_turn_capture_count"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "forced_turn_rule_text": str(prompt_defaults["forced_turn_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_dots_and_boxes_capture_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            box_rows=int(board_state.box_rows),
            box_cols=int(board_state.box_cols),
            drawn_edge_count=len(board_state.drawn_edge_ids),
            target_answer=int(axes.target_answer),
            path_turn_count=int(board_state.path_turn_count),
            evidence_count=len(evidence_ids),
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_dots_and_boxes_single_board",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "target_answer": int(axes.target_answer),
                    "evidence_entity_ids": list(evidence_ids),
                    "highlighted_edge_id": str(board_state.highlighted_edge_id),
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
                "box_rows": int(board_state.box_rows),
                "box_cols": int(board_state.box_cols),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_variant": str(axes.query_variant),
                "task_variant": str(axes.query_variant),
                "style_variant": str(axes.style_variant),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "box_rows": int(board_state.box_rows),
                "box_cols": int(board_state.box_cols),
                "highlighted_edge_id": str(board_state.highlighted_edge_id),
                "drawn_edge_ids": [str(edge_id) for edge_id in board_state.drawn_edge_ids],
                "captured_box_ids": [str(box_id) for box_id in board_state.captured_box_ids],
                "path_box_ids": [str(box_id) for box_id in board_state.path_box_ids],
                "move_edge_sequence": [str(edge_id) for edge_id in board_state.move_edge_sequence],
                "branching_edge_ids": [str(edge_id) for edge_id in board_state.branching_edge_ids],
                "path_turn_count": int(board_state.path_turn_count),
                "edge_specs": [
                    {
                        "edge_id": str(edge.edge_id),
                        "orientation": str(edge.orientation),
                        "dot_start": [int(value) for value in edge.dot_start],
                        "dot_end": [int(value) for value in edge.dot_end],
                        "is_drawn": bool(edge.is_drawn),
                        "is_highlighted": bool(edge.is_highlighted),
                    }
                    for edge in board_state.edges
                ],
                "box_specs": [
                    {
                        "box_id": str(box.box_id),
                        "row_index": int(box.row_index),
                        "column_index": int(box.column_index),
                        "edge_ids": [str(edge_id) for edge_id in box.edge_ids],
                    }
                    for box in board_state.boxes
                ],
                "evidence_entity_ids": [str(box_id) for box_id in evidence_ids],
            },
            "witness_symbolic": {
                "type": "id_set",
                "ids": [str(box_id) for box_id in evidence_ids],
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


__all__ = ["GamesDotsAndBoxesCaptureCountTask"]
