"""Neutral output-part assembly for racing-track scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Tuple

from PIL import Image

from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults
from trace.tasks.shared.config_defaults import group_default, required_group_defaults
from trace.tasks.shared.font_assets import get_font_family_record
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_query_spec,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)

from .common import RacingTrackAheadSample, RacingTrackSample, visible_car_trace
from .rendering import RacingTrackRenderParams, render_racing_track_scene


POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id="racing_track", apply_prob=0.5)


@dataclass(frozen=True)
class RacingTrackOutputParts:
    """Rendered image, prompt, annotation projection, and trace payload."""

    prompt: str
    prompt_variants: Mapping[str, Any]
    image: Image.Image
    annotation_points: Tuple[Tuple[float, float], ...]
    trace_payload: Mapping[str, Any]


def build_racing_track_output_parts(
    *,
    domain: str,
    scene_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    render_params: RacingTrackRenderParams,
    sampled_scene: RacingTrackSample | RacingTrackAheadSample,
    query_id: str,
    object_description_key: str,
    rule_text_key: str,
    answer_hint_key: str,
    annotation_hint_key: str,
    json_examples: tuple[str, str],
    query_params: Mapping[str, Any],
    relation_extra: Mapping[str, Any] | None = None,
    execution_extra: Mapping[str, Any] | None = None,
    witness_type: str = "object_set",
    marked_car_id: str | None = None,
) -> RacingTrackOutputParts:
    """Render one racing-track sample and assemble prompt-backed trace sections."""

    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"games.{scene_id}.{query_id}.panel_scene_style",
        treatment_weights=params.get(
            "panel_scene_treatment_weights",
            group_default(render_defaults, "panel_scene_treatment_weights", None),
        ),
        palette_weights=params.get(
            "panel_scene_palette_weights",
            group_default(render_defaults, "panel_scene_palette_weights", None),
        ),
    )
    background, background_meta = make_panel_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=panel_style,
    )
    rendered_scene = render_racing_track_scene(
        centerline_points_px=sampled_scene.centerline_points_px,
        finish_point_px=sampled_scene.finish_point_px,
        finish_tangent_px=sampled_scene.finish_tangent_px,
        cars=sampled_scene.cars,
        background=background,
        style_variant=str(sampled_scene.style_variant),
        params=render_params,
        panel_style=panel_style,
        marked_car_id=marked_car_id,
    )
    annotation_points = tuple(
        tuple(float(value) for value in rendered_scene.render_map["entity_points_px"][str(entity_id)])
        for entity_id in sampled_scene.annotation_entity_ids
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        str(object_description_key),
        str(rule_text_key),
        str(answer_hint_key),
        str(annotation_hint_key),
    )
    resolved_prompt_defaults = required_group_defaults(
        prompt_defaults,
        required_keys,
        context=f"prompt defaults for {scene_id}",
    )
    json_example, json_example_answer_only = json_examples
    prompt_selection = render_scene_prompt_variants(
        domain=str(domain),
        scene_id=str(scene_id),
        bundle_id=str(resolved_prompt_defaults["bundle_id"]),
        scene_key=str(resolved_prompt_defaults["scene_key"]),
        task_key=str(resolved_prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "object_description": str(resolved_prompt_defaults[str(object_description_key)]),
            str(rule_text_key): str(resolved_prompt_defaults[str(rule_text_key)]),
            "json_output_contract": str(resolved_prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(resolved_prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(resolved_prompt_defaults[str(answer_hint_key)]),
            "annotation_hint": str(resolved_prompt_defaults[str(annotation_hint_key)]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(query_id),
        params=dict(query_params),
    )
    font_record = get_font_family_record(str(render_params.font_family)).to_trace()
    relation_map = {
        "scene_variant": str(sampled_scene.scene_variant),
        "query_id": str(query_id),
        "style_variant": str(sampled_scene.style_variant),
        "car_count": len(sampled_scene.cars),
        "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
    }
    relation_map.update(dict(relation_extra or {}))
    execution_trace = {
        "scene_variant": str(sampled_scene.scene_variant),
        "query_id": str(query_id),
        "style_variant": str(sampled_scene.style_variant),
        "track_width_px": int(sampled_scene.track_width_px),
        "track_height_px": int(sampled_scene.track_height_px),
        "centerline_points_px_local": [
            [round(float(point[0]), 3), round(float(point[1]), 3)]
            for point in sampled_scene.centerline_points_px
        ],
        "finish_point_px_local": [
            round(float(sampled_scene.finish_point_px[0]), 3),
            round(float(sampled_scene.finish_point_px[1]), 3),
        ],
        "finish_tangent_px": [
            round(float(sampled_scene.finish_tangent_px[0]), 6),
            round(float(sampled_scene.finish_tangent_px[1]), 6),
        ],
        "cars": list(visible_car_trace(sampled_scene.cars)),
        "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
        "construction_mode": str(sampled_scene.construction_mode),
    }
    execution_trace.update(dict(execution_extra or {}))
    trace_payload = {
        "scene_ir": {
            "scene_kind": f"games_racing_track_{str(sampled_scene.scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.scene_entities],
            "relations": relation_map,
        },
        "query_spec": query_spec,
        "render_spec": {
            "scene_variant": str(sampled_scene.scene_variant),
            "style_variant": str(sampled_scene.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "track_width_px": int(sampled_scene.track_width_px),
            "track_height_px": int(sampled_scene.track_height_px),
            "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(panel_style_meta),
            "racing_track_style": dict(rendered_scene.render_map.get("racing_track_style", {})),
            "font_assets": {
                "readout_font_family": {
                    **dict(font_record),
                    "font_role": "readout",
                },
            },
        },
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": execution_trace,
        "witness_symbolic": {
            "type": str(witness_type),
            "ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
        },
        "projected_annotation": {
            "type": "point_set",
            "point_set": [list(point) for point in annotation_points],
            "pixel_point_set": [list(point) for point in annotation_points],
        },
        "background": background_meta,
        "post_image_noise": post_noise_meta,
    }
    return RacingTrackOutputParts(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        image=image,
        annotation_points=annotation_points,
        trace_payload=trace_payload,
    )


__all__ = ["RacingTrackOutputParts", "build_racing_track_output_parts"]
