"""Neutral rendering and prompt plumbing for logic-grid public tasks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Dict, Mapping

from PIL import Image

from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.base import TaskOutput
from trace.tasks.puzzles.shared.scene_style import (
    make_puzzle_scene_background,
    resolve_puzzle_scene_style,
)
from trace.tasks.puzzles.shared.unit_size_jitter import with_puzzle_unit_size_jitter
from trace.tasks.puzzles.shared.visual_defaults import load_puzzle_noise_defaults
from trace.tasks.shared.font_assets import (
    font_asset_version,
    get_font_family_record,
    sample_font_family,
)
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec
from trace.tasks.shared.text_rendering import temporary_default_font_family

from .shared.defaults import resolve_render_params, sample_scene_variant
from .shared.annotations import selected_option_annotation
from .shared.output import build_trace_payload
from .shared.prompts import build_logic_grid_prompt_artifacts
from .shared.rendering import render_logic_grid_scene
from .shared.state import DOMAIN, SCENE_ID, LogicGridDataset


_NOISE_DEFAULTS = load_puzzle_noise_defaults(scene_id=SCENE_ID, apply_prob=0.15)


def sample_logic_grid_font(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    namespace: str,
) -> str:
    """Sample one global font family for grid marks and option labels."""

    return sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.label_font",
        params={**dict(rendering_defaults), **dict(params)},
    )


def font_trace_record(font_family: str) -> Dict[str, Any]:
    """Build trace metadata for the sampled logic-grid font."""

    return {
        **get_font_family_record(str(font_family)).to_trace(),
        "source": "global_font_pool",
        "font_asset_version": font_asset_version(),
        "scope": "logic_grid_missing_marker_and_option_labels",
    }


def prepare_logic_grid_visual_case(
    *,
    dataset: LogicGridDataset,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    prompt_task_key: str,
    prompt_query_key: str,
    prompt_dynamic_slots: Mapping[str, Any],
) -> Dict[str, Any]:
    """Render a sampled dataset and matching prompt artifacts."""

    scene_variant, scene_probabilities = sample_scene_variant(
        params=params,
        generation_defaults=generation_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.scene_variant",
    )
    render_params = resolve_render_params(
        params,
        rendering_defaults=rendering_defaults,
        instance_seed=int(instance_seed),
    )
    scene_style, scene_style_meta = resolve_puzzle_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.background",
    )
    render_params = replace(
        render_params,
        panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
        cell_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
        unknown_cell_fill_rgb=tuple(int(value) for value in scene_style.panel_accent_rgb),
        option_panel_fill_rgb=tuple(int(value) for value in scene_style.panel_fill_rgb),
        option_symbol_fill_rgb=tuple(int(value) for value in scene_style.option_fill_rgb),
        border_color_rgb=tuple(int(value) for value in scene_style.panel_border_rgb),
        text_color_rgb=tuple(int(value) for value in scene_style.text_rgb),
        text_stroke_rgb=tuple(int(value) for value in scene_style.text_stroke_rgb),
        accent_color_rgb=tuple(int(value) for value in scene_style.mark_rgb),
    )
    font_family = sample_logic_grid_font(
        instance_seed=int(instance_seed),
        params=params,
        rendering_defaults=rendering_defaults,
        namespace=namespace,
    )
    background, background_meta = make_puzzle_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=scene_style,
    )
    with temporary_default_font_family(str(font_family)):
        rendered_scene = render_logic_grid_scene(
            background,
            scene_variant=str(scene_variant),
            grid_rows=list(dataset.grid_rows),
            option_specs=list(dataset.option_specs),
            render_params=render_params,
        )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=_NOISE_DEFAULTS,
    )
    prompt_slots = dict(prompt_dynamic_slots)
    prompt_slots.setdefault("object_description", object_description_for_scene(str(scene_variant)))
    prompt_defaults, prompt_artifacts = build_logic_grid_prompt_artifacts(
        prompt_task_key=str(prompt_task_key),
        prompt_query_key=str(prompt_query_key),
        dynamic_slots=prompt_slots,
        instance_seed=int(instance_seed),
    )
    return {
        "image": image,
        "rendered_scene": rendered_scene,
        "render_params": render_params,
        "scene_variant": str(scene_variant),
        "scene_variant_probabilities": dict(scene_probabilities),
        "background_meta": dict(background_meta),
        "scene_style_meta": dict(scene_style_meta),
        "post_noise_meta": dict(post_noise_meta),
        "font_family": str(font_family),
        "prompt_defaults": dict(prompt_defaults),
        "prompt_artifacts": prompt_artifacts,
    }


def object_description_for_scene(scene_variant: str) -> str:
    """Return concise scene wording for one logic-grid visual treatment."""

    descriptions = {
        "logic_strip": "a shape grid with one ? cell and six labeled shape options",
        "logic_card": "a card-framed shape grid with one ? cell and six labeled shape options",
        "logic_outline": "an outlined shape grid with one ? cell and six labeled shape options",
    }
    return descriptions.get(str(scene_variant), descriptions["logic_strip"])


def render_spec_from_visual(visual: Mapping[str, Any]) -> Dict[str, Any]:
    """Build the common render-spec trace section from rendered visual metadata."""

    render_params = visual["render_params"]
    rendered_scene = visual["rendered_scene"]
    return {
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "scene_variant": str(visual["scene_variant"]),
        "background_style": dict(visual["background_meta"]),
        "scene_style": dict(visual["scene_style_meta"]),
        "post_image_noise": dict(visual["post_noise_meta"]),
        "scene_bbox_px": list(rendered_scene.scene_bbox_px),
        "board_bbox_px": list(rendered_scene.board_bbox_px),
        "text_style": {
            "value_font_size_px": int(render_params.value_font_size_px),
            "option_label_font_size_px": int(render_params.option_label_font_size_px),
            "font": font_trace_record(str(visual["font_family"])),
        },
        "unit_size_jitter": dict(render_params.unit_size_jitter),
    }


def logic_grid_render_map(*, rendered_scene: Any, render_params: Any) -> Dict[str, Any]:
    """Build the common pixel render map for a rendered logic-grid scene."""

    return with_puzzle_unit_size_jitter(
        {
            "image_id": "img0",
            "scene_bbox_px": list(rendered_scene.scene_bbox_px),
            "board_bbox_px": list(rendered_scene.board_bbox_px),
            "cell_bboxes_px": {
                str(key): list(value)
                for key, value in rendered_scene.cell_bbox_map.items()
            },
            "option_panel_bboxes_px": {
                str(key): list(value)
                for key, value in rendered_scene.option_panel_bbox_map.items()
            },
            "item_bboxes_px": {
                "source_grid": list(rendered_scene.board_bbox_px),
                **{
                    str(key): list(value)
                    for key, value in rendered_scene.option_panel_bbox_map.items()
                },
            },
            "annotation_source": "keyed_source_grid_and_option_bboxes_px",
        },
        render_params.unit_size_jitter,
    )


def build_logic_grid_task_output(
    *,
    dataset: LogicGridDataset,
    visual: Mapping[str, Any],
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
    semantic_rule: str,
    semantic_params: Mapping[str, Any],
    relation_fields: Mapping[str, Any],
    execution_fields: Mapping[str, Any],
) -> TaskOutput:
    """Assemble a TaskOutput for one option-based logic-grid objective."""

    rendered_scene = visual["rendered_scene"]
    prompt_artifacts = visual["prompt_artifacts"]
    scene_variant = str(visual["scene_variant"])
    answer_gt = TypedValue(type="option_letter", value=str(dataset.answer_option_label))
    annotation_gt, witness_symbolic, projected_annotation = selected_option_annotation(
        board_bbox_px=rendered_scene.board_bbox_px,
        option_panel_bbox_map=rendered_scene.option_panel_bbox_map,
        selected_option_panel_id=str(dataset.correct_option_panel_id),
    )
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(selected_branch),
        params={
            "query_id_probabilities": dict(branch_probabilities),
            "semantic_rule": str(semantic_rule),
            "scene_variant": scene_variant,
            "scene_variant_probabilities": dict(visual["scene_variant_probabilities"]),
            "board_size": int(dataset.board_size),
            "board_size_range": list(dataset.board_size_range),
            "cell_count": int(dataset.cell_count),
            "cell_count_range": list(dataset.cell_count_range),
            "option_count": int(dataset.option_count),
            "answer_option_index_probabilities": dict(
                dataset.extra_trace["answer_option_index_probabilities"]
            ),
            **dict(semantic_params),
        },
    )
    render_map = logic_grid_render_map(
        rendered_scene=rendered_scene,
        render_params=visual["render_params"],
    )
    trace_payload = build_trace_payload(
        scene_ir={
            "scene_kind": f"puzzle_logic_grid_{scene_variant}",
            "entities": [dict(entity) for entity in rendered_scene.entities],
            "relations": {
                "selected_branch": str(selected_branch),
                "semantic_rule": str(semantic_rule),
                "scene_variant": scene_variant,
                "answer_option_label": str(dataset.answer_option_label),
                "marked_cell_id": str(dataset.marked_cell_id),
                "correct_option_panel_id": str(dataset.correct_option_panel_id),
                **dict(relation_fields),
            },
        },
        semantic_spec=query_spec,
        render_spec=render_spec_from_visual(visual),
        render_map=render_map,
        execution_trace={
            "query_id": str(selected_branch),
            "semantic_rule": str(semantic_rule),
            "scene_variant": scene_variant,
            "marked_cell_id": str(dataset.marked_cell_id),
            "query_cell_id": str(dataset.marked_cell_id),
            "query_row_index": int(dataset.marked_row_index),
            "query_col_index": int(dataset.marked_col_index),
            "board_size": int(dataset.board_size),
            "board_size_range": list(dataset.board_size_range),
            "cell_count": int(dataset.cell_count),
            "cell_count_range": list(dataset.cell_count_range),
            "board_values": [[str(value) for value in row] for row in dataset.board_values],
            "grid_rows": [[dict(cell) for cell in row] for row in dataset.grid_rows],
            "symbol_pool": [str(value) for value in dataset.symbol_pool],
            "answer_object_type": str(dataset.answer_object_type),
            "answer_option_label": str(dataset.answer_option_label),
            "correct_option_index": int(dataset.correct_option_index),
            "correct_option_panel_id": str(dataset.correct_option_panel_id),
            "option_count": int(dataset.option_count),
            "option_specs": [dict(option) for option in dataset.option_specs],
            "solver_trace": dict(dataset.solver_trace),
            "query_id_probabilities": dict(branch_probabilities),
            "scene_variant_probabilities": dict(visual["scene_variant_probabilities"]),
            "answer_option_index_probabilities": dict(
                dataset.extra_trace["answer_option_index_probabilities"]
            ),
            "supporting_option_panel_ids": [str(dataset.correct_option_panel_id)],
            "annotation_role_item_ids": {
                "source_grid": "source_grid",
                "selected_option": str(dataset.correct_option_panel_id),
            },
            "question_format": "logic_grid_mcq",
            **dict(execution_fields),
        },
        witness_symbolic=witness_symbolic,
        projected_annotation=projected_annotation,
        answer_gt=answer_gt.to_dict(),
        annotation_gt=annotation_gt.to_dict(),
        prompt_defaults=visual["prompt_defaults"],
        prompt_artifacts=prompt_artifacts,
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=visual["image"],
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(selected_branch),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


__all__ = [
    "build_logic_grid_task_output",
    "font_trace_record",
    "logic_grid_render_map",
    "object_description_for_scene",
    "prepare_logic_grid_visual_case",
    "render_spec_from_visual",
    "sample_logic_grid_font",
]
