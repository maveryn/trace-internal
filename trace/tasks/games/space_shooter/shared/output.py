"""Objective-neutral trace serialization for space-shooter scenes."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.annotation_artifacts import AnnotationArtifacts

from .rendering import RenderedSpaceShooterScene
from .state import SpaceShooterSample


def enemy_specs(sample: SpaceShooterSample) -> list[dict[str, Any]]:
    """Serialize enemies with labels, scores, and logical positions."""

    return [
        {
            "enemy_id": str(enemy.enemy_id),
            "label": str(enemy.label),
            "score_value": None if enemy.score_value is None else int(enemy.score_value),
            "display_text": str(int(enemy.score_value)) if enemy.score_value is not None else str(enemy.label),
            "lane": int(enemy.lane),
            "y_slot": int(enemy.y_slot),
        }
        for enemy in sample.enemies
    ]


def projectile_specs(sample: SpaceShooterSample) -> list[dict[str, Any]]:
    """Serialize enemy projectiles with lane positions."""

    return [
        {
            "projectile_id": str(projectile.projectile_id),
            "lane": int(projectile.lane),
            "y_slot": int(projectile.y_slot),
        }
        for projectile in sample.projectiles
    ]


def blocker_specs(sample: SpaceShooterSample) -> list[dict[str, Any]]:
    """Serialize shields and asteroids with lane positions."""

    return [
        {
            "blocker_id": str(blocker.blocker_id),
            "lane": int(blocker.lane),
            "y_slot": int(blocker.y_slot),
            "blocker_type": str(blocker.blocker_type),
        }
        for blocker in sample.blockers
    ]


def space_shooter_trace_params(
    *,
    sample: SpaceShooterSample,
    prompt_query_key: str,
    scene_variant_probabilities: Mapping[str, float],
    style_variant: str,
    style_variant_probabilities: Mapping[str, float],
    lane_count_probabilities: Mapping[str, float],
    enemy_count_probabilities: Mapping[str, float],
    public_query_probabilities: Mapping[str, float],
) -> dict[str, Any]:
    """Return common query params plus task-owned sampling metadata."""

    return {
        "scene_variant": str(sample.scene_variant),
        "scene_variant_probabilities": dict(scene_variant_probabilities),
        "prompt_query_key": str(prompt_query_key),
        "style_variant": str(style_variant),
        "style_variant_probabilities": dict(style_variant_probabilities),
        "lane_count": int(sample.lane_count),
        "lane_count_probabilities": dict(lane_count_probabilities),
        "enemy_count": len(sample.enemies),
        "enemy_count_probabilities": dict(enemy_count_probabilities),
        "projectile_count": len(sample.projectiles),
        "blocker_count": len(sample.blockers),
        "public_query_probabilities": dict(public_query_probabilities),
        **dict(sample.metadata),
    }


def build_space_shooter_trace_payload(
    *,
    sample: SpaceShooterSample,
    rendered: RenderedSpaceShooterScene,
    prompt_query_key: str,
    style_variant: str,
    annotation_artifacts: AnnotationArtifacts,
    background_meta: Mapping[str, Any],
    post_noise_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble space-shooter trace sections after task-specific binding."""

    return {
        "scene_ir": {
            "scene_kind": f"games_space_shooter_{str(sample.scene_variant)}",
            "entities": [dict(entity) for entity in rendered.scene_entities],
            "relations": {
                "scene_variant": str(sample.scene_variant),
                "prompt_query_key": str(prompt_query_key),
                "style_variant": str(style_variant),
                "lane_count": int(sample.lane_count),
                "player_lane": int(sample.player_lane),
                "target_answer": sample.target_answer,
                "annotation_entity_ids": [str(entity_id) for entity_id in sample.annotation_entity_ids],
            },
        },
        "render_spec": {
            "scene_variant": str(sample.scene_variant),
            "style_variant": str(style_variant),
            "canvas_width": int(rendered.image.size[0]),
            "canvas_height": int(rendered.image.size[1]),
            "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(rendered.render_map.get("panel_scene_style", {}) or {}),
            "text_style": dict(rendered.render_map.get("text_style", {}) or {}),
        },
        "render_map": dict(rendered.render_map),
        "execution_trace": {
            "scene_variant": str(sample.scene_variant),
            "prompt_query_key": str(prompt_query_key),
            "style_variant": str(style_variant),
            "lane_count": int(sample.lane_count),
            "player_lane": int(sample.player_lane),
            "target_answer": sample.target_answer,
            "enemies": enemy_specs(sample),
            "projectiles": projectile_specs(sample),
            "blockers": blocker_specs(sample),
            "clear_enemy_ids": [str(value) for value in sample.clear_enemy_ids],
            "intercept_projectile_ids": [str(value) for value in sample.intercept_projectile_ids],
            "lowest_enemy_id": str(sample.lowest_enemy_id),
            "lowest_enemy_label": str(sample.lowest_enemy_label),
            "safe_lane_indices": [int(value) for value in sample.safe_lane_indices],
            "annotation_entity_ids": [str(entity_id) for entity_id in sample.annotation_entity_ids],
            "construction_mode": str(sample.construction_mode),
            **dict(sample.metadata),
        },
        "witness_symbolic": {
            "type": "object_set" if annotation_artifacts.annotation_type.endswith("_set") else "object",
            "ids": [str(entity_id) for entity_id in sample.annotation_entity_ids],
        },
        "projected_annotation": dict(annotation_artifacts.projected_annotation),
        "background": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
    }
