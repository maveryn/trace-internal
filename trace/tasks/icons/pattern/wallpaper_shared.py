"""Shared wallpaper-pattern rendering helpers for icon pattern tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Tuple

from PIL import Image

from ..shared.icon_assets import render_icon_rgba, resolve_icon_pool
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import RenderedIconInstance, serialize_rendered_icon_instance
from ..shared.icon_task_rendering import sample_icon_instance_noise


OPTION_LABELS: Tuple[str, ...] = tuple("ABCDEF")
LATTICE_ROWS = 4
LATTICE_COLS = 4
WALLPAPER_GROUP_IDS: Tuple[str, ...] = ("p1", "p2", "pm", "pg", "cm", "pmm", "p4", "p3")
SAFE_WALLPAPER_CANVAS_TREATMENTS: Tuple[str, ...] = (
    "bare_canvas",
    "plain_sheet",
    "matte_sheet",
    "thin_frame",
    "soft_panel",
)
WALLPAPER_PANEL_CHROME_POLICY = "quiet_canvas_no_ruled_motif_area"


@dataclass(frozen=True)
class WallpaperElementSpec:
    """One motif instance in an invisible wallpaper lattice."""

    element_index: int
    lattice_row: int
    lattice_col: int
    local_index: int
    u: float
    v: float
    rotation_degrees: int
    mirror_x: bool
    group_role: str


def uniform_str_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(selected): 1.0}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def resolve_wallpaper_group_support(raw: Any, *, fallback: Sequence[str] = WALLPAPER_GROUP_IDS) -> Tuple[str, ...]:
    if raw is None:
        raw = list(fallback)
    if not isinstance(raw, (list, tuple)):
        raise ValueError("wallpaper_group_ids must be a sequence")
    allowed = set(WALLPAPER_GROUP_IDS)
    support = tuple(str(value).strip() for value in raw if str(value).strip() in allowed)
    if len(support) < 2:
        raise ValueError("wallpaper_group_ids must contain at least two supported group ids")
    return support


def wallpaper_safe_canvas_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Return params constrained to wallpaper-safe non-ruled canvas treatments."""

    resolved = dict(params)
    safe_set = set(SAFE_WALLPAPER_CANVAS_TREATMENTS)
    explicit_treatment = str(resolved.get("icon_canvas_treatment", "")).strip()
    if explicit_treatment and explicit_treatment not in safe_set:
        raise ValueError(
            "wallpaper panel tasks only support quiet canvas treatments; "
            f"got icon_canvas_treatment={explicit_treatment!r}"
        )
    explicit_treatments = resolved.get("icon_canvas_treatments")
    if explicit_treatments is not None:
        if isinstance(explicit_treatments, (str, bytes)) or not isinstance(explicit_treatments, Sequence):
            raise ValueError("icon_canvas_treatments must be a sequence for wallpaper panel tasks")
        requested = tuple(str(value).strip() for value in explicit_treatments if str(value).strip())
        unsupported = tuple(value for value in requested if value not in safe_set)
        if unsupported:
            raise ValueError(
                "wallpaper panel tasks only support quiet canvas treatments; "
                f"got icon_canvas_treatments={list(unsupported)!r}"
            )
    resolved["icon_canvas_treatments"] = list(SAFE_WALLPAPER_CANVAS_TREATMENTS)
    resolved["icon_canvas_treatment_weights"] = {
        str(treatment): 1.0 for treatment in SAFE_WALLPAPER_CANVAS_TREATMENTS
    }
    return resolved


def wallpaper_chrome_policy_trace() -> Dict[str, Any]:
    """Return trace metadata for wallpaper-panel chrome constraints."""

    return {
        "wallpaper_panel_chrome_policy": WALLPAPER_PANEL_CHROME_POLICY,
        "safe_canvas_treatments": list(SAFE_WALLPAPER_CANVAS_TREATMENTS),
    }


def local_elements_for_group(group_id: str, *, row: int) -> Tuple[Tuple[float, float, int, bool, str], ...]:
    """Return motif placements for one visually distinct wallpaper-group approximation."""

    group = str(group_id)
    if group == "p1":
        return ((0.50, 0.50, 0, False, "translation"),)
    if group == "p2":
        return (
            (0.34, 0.34, 0, False, "twofold_rotation_a"),
            (0.66, 0.66, 180, False, "twofold_rotation_b"),
        )
    if group == "pm":
        return (
            (0.30, 0.50, 0, False, "mirror_left"),
            (0.70, 0.50, 0, True, "mirror_right"),
        )
    if group == "pg":
        row_shift = 0.08 if int(row) % 2 else -0.08
        return (
            (0.34 + row_shift, 0.34, 0, False, "glide_source"),
            (0.66 + row_shift, 0.66, 0, True, "glide_reflection"),
        )
    if group == "cm":
        row_shift = 0.10 if int(row) % 2 else -0.10
        return (
            (0.36 + row_shift, 0.32, 0, False, "centered_mirror_a"),
            (0.64 + row_shift, 0.68, 0, True, "centered_mirror_b"),
        )
    if group == "pmm":
        return (
            (0.30, 0.30, 0, False, "mirror_quadrant_a"),
            (0.70, 0.30, 0, True, "mirror_quadrant_b"),
            (0.30, 0.70, 180, False, "mirror_quadrant_c"),
            (0.70, 0.70, 180, True, "mirror_quadrant_d"),
        )
    if group == "p4":
        return (
            (0.34, 0.34, 0, False, "quarter_turn_0"),
            (0.66, 0.34, 90, False, "quarter_turn_90"),
            (0.66, 0.66, 180, False, "quarter_turn_180"),
            (0.34, 0.66, 270, False, "quarter_turn_270"),
        )
    if group == "p3":
        return (
            (0.50, 0.26, 0, False, "third_turn_0"),
            (0.28, 0.66, 120, False, "third_turn_120"),
            (0.72, 0.66, 240, False, "third_turn_240"),
        )
    raise ValueError(f"unsupported wallpaper group id: {group_id}")


def elements_for_group(*, group_id: str, rows: int, cols: int) -> Tuple[WallpaperElementSpec, ...]:
    elements: List[WallpaperElementSpec] = []
    for row in range(int(rows)):
        for col in range(int(cols)):
            for local_index, (u, v, rotation, mirror_x, role) in enumerate(local_elements_for_group(str(group_id), row=row)):
                elements.append(
                    WallpaperElementSpec(
                        element_index=len(elements),
                        lattice_row=int(row),
                        lattice_col=int(col),
                        local_index=int(local_index),
                        u=float(u),
                        v=float(v),
                        rotation_degrees=int(rotation) % 360,
                        mirror_x=bool(mirror_x),
                        group_role=str(role),
                    )
                )
    return tuple(elements)


def element_to_trace(element: WallpaperElementSpec) -> Dict[str, Any]:
    return {
        "element_index": int(element.element_index),
        "lattice_row": int(element.lattice_row),
        "lattice_col": int(element.lattice_col),
        "local_index": int(element.local_index),
        "u": round(float(element.u), 4),
        "v": round(float(element.v), 4),
        "rotation_degrees": int(element.rotation_degrees),
        "mirror_x": bool(element.mirror_x),
        "group_role": str(element.group_role),
    }


def element_center_xy(
    *,
    content_bbox: Sequence[int | float],
    element: WallpaperElementSpec,
    lattice_rows: int,
    lattice_cols: int,
) -> Tuple[float, float]:
    x0, y0, x1, y1 = [float(value) for value in content_bbox]
    cell_w = max(1.0, float(x1 - x0) / float(max(1, int(lattice_cols))))
    cell_h = max(1.0, float(y1 - y0) / float(max(1, int(lattice_rows))))
    cx = x0 + ((float(element.lattice_col) + float(element.u)) * cell_w)
    cy = y0 + ((float(element.lattice_row) + float(element.v)) * cell_h)
    return float(cx), float(cy)


def centered_sprite_bbox(
    *,
    sprite_size: Tuple[int, int],
    center_xy: Tuple[float, float],
    content_bbox: Sequence[int | float],
) -> Tuple[int, int, int, int]:
    content_x0, content_y0, content_x1, content_y1 = [int(round(float(value))) for value in content_bbox]
    sprite_w, sprite_h = int(sprite_size[0]), int(sprite_size[1])
    if sprite_w <= 0 or sprite_h <= 0:
        raise ValueError("sprite size must be positive")
    margin = 1
    min_x0 = int(content_x0 + margin)
    max_x0 = int(content_x1 - margin - sprite_w)
    min_y0 = int(content_y0 + margin)
    max_y0 = int(content_y1 - margin - sprite_h)
    if min_x0 > max_x0 or min_y0 > max_y0:
        raise ValueError("wallpaper icon sprite does not fit inside content panel")
    paste_x0 = int(round(float(center_xy[0]) - (float(sprite_w) / 2.0)))
    paste_y0 = int(round(float(center_xy[1]) - (float(sprite_h) / 2.0)))
    paste_x0 = int(max(min_x0, min(max_x0, paste_x0)))
    paste_y0 = int(max(min_y0, min(max_y0, paste_y0)))
    return (int(paste_x0), int(paste_y0), int(paste_x0 + sprite_w), int(paste_y0 + sprite_h))


def select_distinct_icon_ids(rng: Any, *, pool_manifest: str, labels: Sequence[str]) -> Dict[str, str]:
    pool = list(resolve_icon_pool(str(pool_manifest)))
    if len(pool) < len(labels):
        raise ValueError("wallpaper icon pool must contain at least one unique icon per labeled panel")
    rng.shuffle(pool)
    return {str(label): str(icon_id) for label, icon_id in zip(labels, pool[: len(labels)])}


def draw_wallpaper_motifs(
    image: Image.Image,
    *,
    task_id: str,
    instance_seed: int,
    panel_label: str,
    group_id: str,
    icon_id: str,
    tint_rgb: Sequence[int],
    nominal_icon_size_px: int,
    content_bbox: Sequence[int | float],
    render_params: Mapping[str, Any],
    sprite_cache: MutableMapping[Tuple[str, int, bool], Image.Image],
    entity_kind_prefix: str = "wallpaper",
    is_answer_panel: bool = False,
) -> Tuple[Tuple[Dict[str, Any], ...], Tuple[Dict[str, Any], ...]]:
    scene_elements: List[Dict[str, Any]] = []
    scene_icon_instances: List[Dict[str, Any]] = []
    elements = elements_for_group(
        group_id=str(group_id),
        rows=int(render_params["lattice_rows"]),
        cols=int(render_params["lattice_cols"]),
    )
    for element in elements:
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:panel_{str(panel_label)}_element_{int(element.element_index)}",
            render_params=render_params,
        )
        cache_key = (str(icon_id), int(element.rotation_degrees) % 360, bool(element.mirror_x))
        if cache_key not in sprite_cache or noise_edits:
            sprite = render_icon_rgba(
                icon_id=str(icon_id),
                size_px=int(nominal_icon_size_px),
                tint_rgb=tuple(int(v) for v in tint_rgb),
                rotation_degrees=int(element.rotation_degrees),
                mirror_x=bool(element.mirror_x),
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
            if not noise_edits:
                sprite_cache[cache_key] = sprite
        else:
            sprite = sprite_cache[cache_key]
        center_xy = element_center_xy(
            content_bbox=content_bbox,
            element=element,
            lattice_rows=int(render_params["lattice_rows"]),
            lattice_cols=int(render_params["lattice_cols"]),
        )
        paste_bbox = centered_sprite_bbox(sprite_size=sprite.size, center_xy=center_xy, content_bbox=content_bbox)
        image.alpha_composite(sprite, (int(paste_bbox[0]), int(paste_bbox[1])))
        rendered_instance = RenderedIconInstance(
            instance_id=f"panel_{str(panel_label)}_element_{int(element.element_index)}",
            icon_id=str(icon_id),
            panel=str(panel_label),
            bbox_xyxy=tuple(int(value) for value in paste_bbox),
            nominal_size_px=int(nominal_icon_size_px),
            rotation_degrees=int(element.rotation_degrees) % 360,
            mirror_x=bool(element.mirror_x),
            tint_rgb=tuple(int(value) for value in tint_rgb),
            noise_edits=serialize_icon_noise_edits(tuple(noise_edits)),
            noise_seed=int(noise_seed),
        )
        element_trace = element_to_trace(element)
        scene_elements.append(
            {
                "entity_kind": f"{entity_kind_prefix}_motif_element",
                "panel_label": str(panel_label),
                "wallpaper_group_id": str(group_id),
                "is_answer_panel": bool(is_answer_panel),
                "element_bbox_xyxy": [int(value) for value in paste_bbox],
                **element_trace,
            }
        )
        scene_icon_instances.append(
            serialize_rendered_icon_instance(
                rendered_instance,
                entity_kind=f"{entity_kind_prefix}_motif_icon",
                extra_fields={
                    "panel_label": str(panel_label),
                    "wallpaper_group_id": str(group_id),
                    "is_answer_panel": bool(is_answer_panel),
                    **element_trace,
                },
            )
        )
    return tuple(scene_elements), tuple(scene_icon_instances)


__all__ = [
    "LATTICE_COLS",
    "LATTICE_ROWS",
    "OPTION_LABELS",
    "SAFE_WALLPAPER_CANVAS_TREATMENTS",
    "WALLPAPER_PANEL_CHROME_POLICY",
    "WALLPAPER_GROUP_IDS",
    "WallpaperElementSpec",
    "centered_sprite_bbox",
    "draw_wallpaper_motifs",
    "element_center_xy",
    "element_to_trace",
    "elements_for_group",
    "resolve_wallpaper_group_support",
    "select_distinct_icon_ids",
    "uniform_str_probability_map",
    "wallpaper_chrome_policy_trace",
    "wallpaper_safe_canvas_params",
]
