"""Games bingo task for grounded completed-line counting queries."""

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
from ..shared.bingo_common import (
    SUPPORTED_BINGO_QUERY_VARIANTS,
    SUPPORTED_BINGO_SCENE_VARIANTS,
    BingoCardState,
    build_bingo_card_state,
    evidence_cell_ids_for_query,
)
from ..shared.bingo_scene import BingoRenderParams, render_bingo_card_scene
from ..shared.complexity import build_games_bingo_completed_line_complexity
from ..shared.style import SUPPORTED_GAMES_STYLE_VARIANTS
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "task_games_bingo_completed_line_count"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible bingo-card scenes."""

    completed_row_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    completed_column_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    completed_straight_line_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8)
    canvas_width: int = 1180
    canvas_height: int = 760
    card_width_px: int = 760
    card_height_px: int = 620
    card_corner_radius_px: int = 24
    panel_margin_px: int = 56
    title_font_size_px: int = 34
    title_band_height_px: int = 62
    header_font_size_px: int = 28
    header_height_px: int = 42
    grid_gap_px: int = 18
    number_font_size_px: int = 28
    cell_corner_radius_px: int = 14
    cell_gap_px: int = 10
    mark_inset_px: int = 12


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one bingo-card scene."""

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
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "bingo")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="bingo")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="bingo", apply_prob=0.0)


def _resolve_query_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced semantic query variant, honoring `task_variant` as an alias."""

    alias_params = dict(params)
    if alias_params.get("query_variant") is None and alias_params.get("task_variant") is not None:
        alias_params["query_variant"] = alias_params["task_variant"]
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_variant")
    selected, probabilities = resolve_variant(
        rng,
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_BINGO_QUERY_VARIANTS,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=alias_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_BINGO_QUERY_VARIANTS,
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
    """Resolve one balanced named axis for the bingo task."""

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


def _target_support_key(query_variant: str) -> str:
    """Return the configured target-support key for one bingo query variant."""

    return {
        "completed_row_count": "completed_row_count_support",
        "completed_column_count": "completed_column_count_support",
        "completed_straight_line_count": "completed_straight_line_count_support",
    }[str(query_variant)]


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve semantic/visual axes plus one target answer for the bingo task."""

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
        supported=SUPPORTED_BINGO_SCENE_VARIANTS,
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


def _render_params(params: Mapping[str, Any]) -> BingoRenderParams:
    """Resolve stable render parameters for one bingo scene."""

    return BingoRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        card_width_px=int(params.get("card_width_px", group_default(_RENDER_DEFAULTS, "card_width_px", _DEFAULTS.card_width_px))),
        card_height_px=int(params.get("card_height_px", group_default(_RENDER_DEFAULTS, "card_height_px", _DEFAULTS.card_height_px))),
        card_corner_radius_px=int(
            params.get(
                "card_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "card_corner_radius_px", _DEFAULTS.card_corner_radius_px),
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
        header_font_size_px=int(
            params.get(
                "header_font_size_px",
                group_default(_RENDER_DEFAULTS, "header_font_size_px", _DEFAULTS.header_font_size_px),
            )
        ),
        header_height_px=int(
            params.get("header_height_px", group_default(_RENDER_DEFAULTS, "header_height_px", _DEFAULTS.header_height_px))
        ),
        grid_gap_px=int(params.get("grid_gap_px", group_default(_RENDER_DEFAULTS, "grid_gap_px", _DEFAULTS.grid_gap_px))),
        number_font_size_px=int(
            params.get(
                "number_font_size_px",
                group_default(_RENDER_DEFAULTS, "number_font_size_px", _DEFAULTS.number_font_size_px),
            )
        ),
        cell_corner_radius_px=int(
            params.get(
                "cell_corner_radius_px",
                group_default(_RENDER_DEFAULTS, "cell_corner_radius_px", _DEFAULTS.cell_corner_radius_px),
            )
        ),
        cell_gap_px=int(params.get("cell_gap_px", group_default(_RENDER_DEFAULTS, "cell_gap_px", _DEFAULTS.cell_gap_px))),
        mark_inset_px=int(params.get("mark_inset_px", group_default(_RENDER_DEFAULTS, "mark_inset_px", _DEFAULTS.mark_inset_px))),
    )


def _build_prompt_json_examples(*, query_variant: str) -> Tuple[str, str]:
    """Return answer+evidence and answer-only JSON examples for the bingo task."""

    sample_answer = 2 if str(query_variant) != "completed_straight_line_count" else 3
    json_example = json.dumps(
        {
            "evidence": [
                [120, 220, 220, 320],
                [230, 220, 330, 320],
            ],
            "answer": int(sample_answer),
        },
        ensure_ascii=True,
    )
    json_example_answer_only = json.dumps({"answer": int(sample_answer)}, ensure_ascii=True)
    return json_example, json_example_answer_only


@register_task
class GamesBingoCompletedLineCountTask:
    """Return one grounded completed-line count over a visible bingo card."""

    task_id = TASK_ID
    domain = "games"
    task_group = "bingo"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_params = _render_params(params)

        sampled_card: BingoCardState | None = None
        rendered_scene = None
        background_meta: Dict[str, Any] | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            sampled_card = build_bingo_card_state(
                rng=attempt_rng,
                query_variant=str(axes.query_variant),
                target_answer=int(axes.target_answer),
            )
            background, background_meta = make_background_canvas(
                canvas_width=int(render_params.canvas_width),
                canvas_height=int(render_params.canvas_height),
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            rendered_scene = render_bingo_card_scene(
                cells=list(sampled_card.cells),
                background=background,
                scene_variant=str(axes.scene_variant),
                style_variant=str(axes.style_variant),
                params=render_params,
            )
            break

        if sampled_card is None or rendered_scene is None or background_meta is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        evidence_cell_ids = evidence_cell_ids_for_query(
            card_state=sampled_card,
            query_variant=str(axes.query_variant),
        )
        evidence_bboxes = [
            list(rendered_scene.render_map["cell_bboxes_px"][str(cell_id)])
            for cell_id in evidence_cell_ids
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
                "object_description_single_card",
                "completed_row_rule_text",
                "completed_column_rule_text",
                "completed_straight_line_rule_text",
                "answer_hint_completed_row_count",
                "answer_hint_completed_column_count",
                "answer_hint_completed_straight_line_count",
                "evidence_hint_completed_row_count",
                "evidence_hint_completed_column_count",
                "evidence_hint_completed_straight_line_count",
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
                "object_description": str(prompt_defaults["object_description_single_card"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_variant)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
                "completed_row_rule_text": str(prompt_defaults["completed_row_rule_text"]),
                "completed_column_rule_text": str(prompt_defaults["completed_column_rule_text"]),
                "completed_straight_line_rule_text": str(prompt_defaults["completed_straight_line_rule_text"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        marked_cell_count = sum(1 for cell in sampled_card.cells if bool(cell.is_marked))
        complexity = build_games_bingo_completed_line_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            query_variant=str(axes.query_variant),
            marked_cell_count=int(marked_cell_count),
            target_answer=int(axes.target_answer),
            evidence_count=len(evidence_cell_ids),
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "games_bingo_single_card",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "target_answer": int(axes.target_answer),
                    "evidence_entity_ids": list(evidence_cell_ids),
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
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_variant": str(axes.query_variant),
                "task_variant": str(axes.query_variant),
                "style_variant": str(axes.style_variant),
                "target_answer": int(axes.target_answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "numbers_grid": [[int(value) for value in row] for row in sampled_card.numbers_grid],
                "mark_grid": [[bool(value) for value in row] for row in sampled_card.mark_grid],
                "completed_row_indices": [int(value) for value in sampled_card.completed_row_indices],
                "completed_column_indices": [int(value) for value in sampled_card.completed_column_indices],
                "cell_specs": [
                    {
                        "cell_id": str(spec.cell_id),
                        "row_index": int(spec.row_index),
                        "column_index": int(spec.column_index),
                        "column_label": str(spec.column_label),
                        "number": int(spec.number),
                        "is_marked": bool(spec.is_marked),
                    }
                    for spec in rendered_scene.cell_specs
                ],
                "evidence_entity_ids": [str(cell_id) for cell_id in evidence_cell_ids],
            },
            "witness_symbolic": {
                "type": "id_set",
                "ids": [str(cell_id) for cell_id in evidence_cell_ids],
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


__all__ = ["GamesBingoCompletedLineCountTask"]
