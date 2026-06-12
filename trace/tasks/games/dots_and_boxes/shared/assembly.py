"""Identity-free render and trace assembly for dots-and-boxes tasks."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults
from trace.tasks.shared.annotation_artifacts import bbox_set_annotation_artifacts, point_pair_set_annotation_artifacts
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.font_assets import get_font_family_record
from trace.tasks.shared.prompt_variants import build_prompt_query_spec

from .mechanics import DotsAndBoxesBoardState, box_drawn_side_counts, immediate_capture_edge_ids
from .prompts import build_dots_and_boxes_prompt_artifacts
from .rendering import render_dots_and_boxes_scene
from .sampling import resolve_dots_and_boxes_render_params
from .state import (
    DOTS_AND_BOXES_NAMESPACE,
    SCENE_ID,
    DotsAndBoxesBoardShapeAxis,
    DotsAndBoxesGeneratedComponents,
    DotsAndBoxesIntegerAxis,
    DotsAndBoxesSceneAxes,
)


POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


def _allowed_panel_treatments(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> tuple[str, ...] | None:
    raw = params.get("panel_scene_treatments", group_default(render_defaults, "panel_scene_treatments", None))
    if isinstance(raw, str):
        return (str(raw),)
    if raw is None:
        return None
    return tuple(str(item) for item in raw)


def _edge_specs_for_trace(board_state: DotsAndBoxesBoardState) -> list[dict[str, Any]]:
    return [
        {
            "edge_id": str(edge.edge_id),
            "orientation": str(edge.orientation),
            "dot_start": [int(value) for value in edge.dot_start],
            "dot_end": [int(value) for value in edge.dot_end],
            "is_drawn": bool(edge.is_drawn),
            "is_highlighted": bool(edge.is_highlighted),
        }
        for edge in board_state.edges
    ]


def _box_specs_for_trace(board_state: DotsAndBoxesBoardState) -> list[dict[str, Any]]:
    return [
        {
            "box_id": str(box.box_id),
            "row_index": int(box.row_index),
            "column_index": int(box.column_index),
            "edge_ids": [str(edge_id) for edge_id in box.edge_ids],
            "owner": str(getattr(box, "owner", "") or ""),
        }
        for box in board_state.boxes
    ]


def _annotation_artifacts(
    *,
    annotation_kind: str,
    annotation_entity_ids: Sequence[str],
    render_map: Mapping[str, Any],
) -> Any:
    if str(annotation_kind) == "box":
        bboxes = [
            list(render_map["box_bboxes_px"][str(box_id)])
            for box_id in annotation_entity_ids
        ]
        return bbox_set_annotation_artifacts(bboxes)
    if str(annotation_kind) == "edge_point_pair":
        point_pairs = [
            [list(point) for point in render_map["edge_point_pairs_px"][str(edge_id)]]
            for edge_id in annotation_entity_ids
        ]
        return point_pair_set_annotation_artifacts(point_pairs)
    raise ValueError(f"unsupported dots-and-boxes annotation kind: {annotation_kind}")


def build_dots_and_boxes_components(
    *,
    domain: str,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
    scene_axes: DotsAndBoxesSceneAxes,
    board_shape: DotsAndBoxesBoardShapeAxis,
    board_state: DotsAndBoxesBoardState,
    answer_value: int,
    annotation_kind: str,
    annotation_entity_ids: Sequence[str],
    prompt_query_key: str,
    query_params: Mapping[str, Any],
    candidate_edge_count_axis: DotsAndBoxesIntegerAxis | None = None,
) -> DotsAndBoxesGeneratedComponents:
    """Render one dots-and-boxes scene and build trace components."""

    render_params = resolve_dots_and_boxes_render_params(
        params,
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
    )
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{DOTS_AND_BOXES_NAMESPACE}.panel_scene_style",
        treatments=_allowed_panel_treatments(params, render_defaults),
        treatment_weights=params.get("panel_scene_treatment_weights", group_default(render_defaults, "panel_scene_treatment_weights", None)),
        palette_weights=params.get("panel_scene_palette_weights", group_default(render_defaults, "panel_scene_palette_weights", None)),
    )
    background, background_meta = make_panel_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=panel_style,
    )
    rendered_scene = render_dots_and_boxes_scene(
        board_state=board_state,
        background=background,
        scene_variant=str(scene_axes.scene_variant),
        style_variant=str(scene_axes.style_variant),
        params=render_params,
        panel_style=panel_style,
    )
    annotation_ids = tuple(str(item) for item in annotation_entity_ids)
    annotation_artifacts = _annotation_artifacts(
        annotation_kind=str(annotation_kind),
        annotation_entity_ids=annotation_ids,
        render_map=rendered_scene.render_map,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    prompt_defaults, prompt_artifacts = build_dots_and_boxes_prompt_artifacts(
        domain=str(domain),
        scene_variant=str(scene_axes.scene_variant),
        prompt_query_key=str(prompt_query_key),
        instance_seed=int(instance_seed),
    )
    text_style_meta = {
        "font_family": str(render_params.font_family),
        "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
    }
    box_edge_map = {str(box.box_id): tuple(str(edge_id) for edge_id in box.edge_ids) for box in board_state.boxes}
    side_counts = box_drawn_side_counts(
        drawn_edge_ids=tuple(str(edge_id) for edge_id in board_state.drawn_edge_ids),
        box_edges=box_edge_map,
    )
    immediate_edges = immediate_capture_edge_ids(
        drawn_edge_ids=tuple(str(edge_id) for edge_id in board_state.drawn_edge_ids),
        box_edges=box_edge_map,
    )
    candidate_edge_count = None if candidate_edge_count_axis is None else int(candidate_edge_count_axis.value)
    base_query_params = {
        "scene_variant": str(scene_axes.scene_variant),
        "query_id": str(query_id),
        "style_variant": str(scene_axes.style_variant),
        "scene_variant_probabilities": dict(scene_axes.scene_variant_probabilities),
        "query_id_probabilities": {str(key): float(value) for key, value in dict(query_id_probabilities).items()},
        "style_variant_probabilities": dict(scene_axes.style_variant_probabilities),
        "box_rows": int(board_shape.box_rows),
        "box_cols": int(board_shape.box_cols),
        "board_shape_probabilities": dict(board_shape.probabilities),
    }
    if candidate_edge_count_axis is not None:
        base_query_params.update(
            {
                "candidate_edge_count": int(candidate_edge_count_axis.value),
                "candidate_edge_count_support": [int(value) for value in candidate_edge_count_axis.support],
                "candidate_edge_count_probabilities": dict(candidate_edge_count_axis.probabilities),
            }
        )
    base_query_params.update(dict(query_params))
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        params=base_query_params,
    )
    execution_trace = {
        "scene_variant": str(scene_axes.scene_variant),
        "query_id": str(query_id),
        "style_variant": str(scene_axes.style_variant),
        "target_answer": int(answer_value),
        "box_rows": int(board_state.box_rows),
        "box_cols": int(board_state.box_cols),
        "candidate_edge_count": candidate_edge_count,
        "highlighted_edge_id": str(board_state.highlighted_edge_id),
        "highlighted_edge_ids": [str(edge_id) for edge_id in board_state.highlighted_edge_ids],
        "drawn_edge_ids": [str(edge_id) for edge_id in board_state.drawn_edge_ids],
        "captured_box_ids": [str(box_id) for box_id in board_state.captured_box_ids],
        "counted_box_ids": [str(box_id) for box_id in board_state.counted_box_ids],
        "counted_edge_ids": [str(edge_id) for edge_id in board_state.counted_edge_ids],
        "candidate_edge_ids": [str(edge_id) for edge_id in board_state.candidate_edge_ids],
        "box_owner_by_id": dict(rendered_scene.render_map.get("box_owner_by_id", {})),
        "immediate_capture_edge_ids": [str(edge_id) for edge_id in immediate_edges],
        "box_drawn_side_counts": {str(box_id): int(count) for box_id, count in sorted(side_counts.items())},
        "path_box_ids": [str(box_id) for box_id in board_state.path_box_ids],
        "move_edge_sequence": [str(edge_id) for edge_id in board_state.move_edge_sequence],
        "branching_edge_ids": [str(edge_id) for edge_id in board_state.branching_edge_ids],
        "path_turn_count": int(board_state.path_turn_count),
        "edge_specs": _edge_specs_for_trace(board_state),
        "box_specs": _box_specs_for_trace(board_state),
        "annotation_entity_ids": [str(entity_id) for entity_id in annotation_ids],
        **dict(query_params),
    }
    trace_payload = {
        "scene_ir": {
            "scene_kind": f"games_dots_and_boxes_{str(scene_axes.scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.scene_entities],
            "relations": {
                "scene_variant": str(scene_axes.scene_variant),
                "query_id": str(query_id),
                "style_variant": str(scene_axes.style_variant),
                "target_answer": int(answer_value),
                "annotation_entity_ids": [str(entity_id) for entity_id in annotation_ids],
                "box_rows": int(board_state.box_rows),
                "box_cols": int(board_state.box_cols),
                "candidate_edge_count": candidate_edge_count,
                "highlighted_edge_id": str(board_state.highlighted_edge_id),
                "highlighted_edge_ids": [str(edge_id) for edge_id in board_state.highlighted_edge_ids],
            },
        },
        "query_spec": dict(query_spec),
        "render_spec": {
            "scene_variant": str(scene_axes.scene_variant),
            "style_variant": str(scene_axes.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "box_rows": int(board_state.box_rows),
            "box_cols": int(board_state.box_cols),
            "candidate_edge_count": candidate_edge_count,
            "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(panel_style_meta),
            "text_style": dict(text_style_meta),
        },
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": dict(execution_trace),
        "witness_symbolic": {
            "type": "object_set",
            "ids": [str(entity_id) for entity_id in annotation_ids],
        },
        "projected_annotation": dict(annotation_artifacts.projected_annotation),
        "background": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
        "prompt_metadata": {"bundle_id": str(prompt_defaults["bundle_id"])},
    }
    return DotsAndBoxesGeneratedComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_type="integer",
        answer_value=int(answer_value),
        annotation_type=str(annotation_artifacts.annotation_type),
        annotation_value=annotation_artifacts.value,
        image=image,
        trace_payload=trace_payload,
        query_id=str(query_id),
    )


__all__ = ["build_dots_and_boxes_components"]
