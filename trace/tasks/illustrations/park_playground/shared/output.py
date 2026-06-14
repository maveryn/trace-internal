"""Output trace fragments shared by park/playground public tasks."""

from __future__ import annotations

from typing import Any, Dict, Mapping


def park_render_spec(scene: Any) -> Dict[str, Any]:
    """Return the common render-spec fragment for a park scene."""

    return {
        "canvas_size": [int(scene.canvas_width), int(scene.canvas_height)],
        "coord_space": "pixel",
        "scene_id": "park_playground",
        "style": {
            "setting_id": str(scene.setting_id),
            "style_id": str(scene.style_id),
            "render_scale": int(scene.render_scale),
            "layout": dict(scene.layout),
        },
    }


def park_scene_ir(
    *,
    domain: str,
    scene_id: str,
    entities: list[dict[str, Any]],
    relations: Mapping[str, Any],
) -> Dict[str, Any]:
    """Return the common scene-IR fragment for a park scene."""

    return {
        "domain": str(domain),
        "scene_id": str(scene_id),
        "entities": list(entities),
        "relations": dict(relations),
    }


__all__ = ["park_render_spec", "park_scene_ir"]
