"""Games Go task for counting liberties of one highlighted group on a visible 7x7 board."""

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
from ..shared.complexity import build_games_go_group_liberty_complexity
from ..shared.go_common import (
    BOARD_SIZE,
    GoBoardState,
    build_go_board_state,
    color_name,
    liberty_point_ids,
    supported_targets_for_query,
)
from ..shared.go_scene import GoRenderParams, render_go_board_scene
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_variant
from ..shared.style import SUPPORTED_GAMES_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "task_games_go_group_liberty_count"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "open_board",
    "crowded_board",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "marked_black_group_liberty_count",
    "marked_white_group_liberty_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Go liberty-count scenes."""

    liberty_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)
    board_size: int = BOARD_SIZE
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
    highlight_outline_width_px: int = 6
    liberty_bbox_fraction: float = 0.72


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Go liberty-count scene."""

    query_variant: str
    scene_variant: str
    style_variant: str
    target_answer: int
    target_answer_support: Tuple[int, ...]
    board_size: int
    query_variant_probabilities: Dict[str, float]
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


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic/visual axes plus one target answer for the Go task."""

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
    target_answer, target_answer_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="liberty_count_support",
        explicit_key="target_answer",
        fallback_support=supported_targets_for_query(),
        namespace=f"{TASK_ID}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_explicit_sampling_index=True,
    )
    target_answer_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="liberty_count_support",
        fallback=supported_targets_for_query(),
    )
    return _ResolvedAxes(
        query_variant=str(query_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        board_size=int(_DEFAULTS.board_size),
        query_variant_probabilities=dict(query_variant_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _render_params(params: Mapping[str, Any]) -> GoRenderParams:
    """Resolve Go rendering parameters from config/defaults."""

    return GoRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        max_board_size_px=int(
            params.get("max_board_size_px", group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px))
        ),
        board_padding_px=int(
            params.get("board_padding_px", group_default(_RENDER_DEFAULTS, "board_padding_px", _DEFAULTS.board_padding_px))
        ),
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
        line_width_px=int(params.get("line_width_px", group_default(_RENDER_DEFAULTS, "line_width_px", _DEFAULTS.line_width_px))),
        point_radius_px=int(
            params.get("point_radius_px", group_default(_RENDER_DEFAULTS, "point_radius_px", _DEFAULTS.point_radius_px))
        ),
        stone_radius_fraction=float(
            params.get(
                "stone_radius_fraction",
                group_default(_RENDER_DEFAULTS, "stone_radius_fraction", _DEFAULTS.stone_radius_fraction),
            )
        ),
        highlight_outline_width_px=int(
            params.get(
                "highlight_outline_width_px",
                group_default(_RENDER_DEFAULTS, "highlight_outline_width_px", _DEFAULTS.highlight_outline_width_px),
            )
        ),
        liberty_bbox_fraction=float(
            params.get(
                "liberty_bbox_fraction",
                group_default(_RENDER_DEFAULTS, "liberty_bbox_fraction", _DEFAULTS.liberty_bbox_fraction),
            )
        ),
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


@register_task
class GamesGoGroupLibertyCountTask:
    """Return one grounded count of liberties for a highlighted group on a visible 7x7 Go board."""

    task_id = TASK_ID
    domain = "games"
    task_group = "go"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params)

        board_state: GoBoardState | None = None
        rendered_scene = None
        background_meta: Dict[str, Any] | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            board_state = build_go_board_state(
                rng=attempt_rng,
                query_variant=str(axes.query_variant),
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

        evidence_ids = liberty_point_ids(board_state.liberty_coords)
        evidence_bboxes = [
            list(rendered_scene.render_map["point_bboxes_px"][str(point_id)])
            for point_id in evidence_ids
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
                "object_description_open_board",
                "object_description_crowded_board",
                "group_rule_text",
                "liberty_rule_text",
                "marked_group_rule_text_marked_black_group_liberty_count",
                "marked_group_rule_text_marked_white_group_liberty_count",
                "answer_hint_marked_black_group_liberty_count",
                "answer_hint_marked_white_group_liberty_count",
                "evidence_hint_marked_black_group_liberty_count",
                "evidence_hint_marked_white_group_liberty_count",
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
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_variant)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "group_rule_text": str(prompt_defaults["group_rule_text"]),
                "liberty_rule_text": str(prompt_defaults["liberty_rule_text"]),
                "marked_group_rule_text": str(prompt_defaults[f"marked_group_rule_text_{str(axes.query_variant)}"]),
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
        complexity = build_games_go_group_liberty_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
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
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "target_answer": int(axes.target_answer),
                    "evidence_entity_ids": list(evidence_ids),
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
                    "board_size": int(axes.board_size),
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
                "board_size": int(axes.board_size),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_variant": str(axes.query_variant),
                "task_variant": str(axes.query_variant),
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
                "evidence_entity_ids": [str(value) for value in evidence_ids],
            },
            "witness_symbolic": {
                "type": "id_set",
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
            task_variant=str(axes.query_variant),
        )


__all__ = ["GamesGoGroupLibertyCountTask"]
