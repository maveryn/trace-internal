"""Rendering primitives for coordinate-composite diagrams."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from PIL import ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.geometry.shared.graph_rendering import graph_paper_grid_from_frame, graph_units_to_pixel, scale_point
from trace.tasks.geometry.shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from trace.tasks.geometry.shared.single_object_scene import finalize_graph_scene_image, make_graph_scene_canvas, resolve_graph_scene_context
from trace.tasks.geometry.shared.vector2d import point_to_list
from trace.tasks.shared.config_defaults import group_default

from .relations import filtered_intersections, object_to_trace
from .state import CircleObject, Color, LineObject, PairFilter, PolygonObject, RenderedScene, SceneObject


def _draw_object(
    draw: ImageDraw.ImageDraw,
    obj: SceneObject,
    *,
    color: Color,
    context: Any,
    width_px: int,
) -> Dict[str, Any]:
    """Draw one graph-space object and return its pixel-space render metadata."""

    scale = int(context.scene_scale)
    width_render = max(1, int(width_px) * int(scale))
    if isinstance(obj, LineObject):
        p0 = scale_point(
            graph_units_to_pixel(obj.p0, origin=context.graph_origin, spacing=int(context.graph_spacing)),
            int(scale),
        )
        p1 = scale_point(
            graph_units_to_pixel(obj.p1, origin=context.graph_origin, spacing=int(context.graph_spacing)),
            int(scale),
        )
        draw.line([p0, p1], fill=color, width=width_render)
        return {"id": str(obj.object_id), "kind": "line_segment", "p0_px": point_to_list(p0), "p1_px": point_to_list(p1)}
    if isinstance(obj, CircleObject):
        center_px = scale_point(
            graph_units_to_pixel(obj.center, origin=context.graph_origin, spacing=int(context.graph_spacing)),
            int(scale),
        )
        radius_px = float(obj.radius) * float(context.graph_spacing) * float(scale)
        bbox = [
            float(center_px[0]) - radius_px,
            float(center_px[1]) - radius_px,
            float(center_px[0]) + radius_px,
            float(center_px[1]) + radius_px,
        ]
        draw.ellipse(bbox, outline=color, width=width_render)
        return {
            "id": str(obj.object_id),
            "kind": "circle",
            "center_px": point_to_list(center_px),
            "radius_px": round(float(radius_px), 3),
        }
    vertices = [
        scale_point(
            graph_units_to_pixel(point, origin=context.graph_origin, spacing=int(context.graph_spacing)),
            int(scale),
        )
        for point in obj.vertices
    ]
    draw.line([*vertices, vertices[0]], fill=color, width=width_render, joint="curve")
    return {"id": str(obj.object_id), "kind": "polygon", "vertices_px": [point_to_list(point) for point in vertices]}


def _sample_object_colors(rng: Any, *, shape_color: Color) -> Tuple[Color, ...]:
    base = tuple(int(value) for value in shape_color)
    palette: Tuple[Color, ...] = (
        base,
        (max(24, min(210, base[2] + 35)), max(24, min(175, base[0] + 12)), max(24, min(190, base[1] - 18))),
        (max(24, min(190, base[1] + 24)), max(24, min(190, base[2] - 8)), max(24, min(190, base[0] + 40))),
        (max(24, min(200, base[0] - 20)), max(24, min(190, base[1] + 30)), max(24, min(200, base[2] + 20))),
    )
    offset = int(rng.randrange(len(palette)))
    return tuple(palette[(offset + index) % len(palette)] for index in range(len(palette)))


def render_coordinate_composite_scene(
    *,
    instance_seed: int,
    objects: Tuple[SceneObject, ...],
    pair_filter: PairFilter,
    transform: str,
    expected_count: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    background_defaults: Mapping[str, Any],
    noise_defaults: Mapping[str, Any],
    random_namespace: str,
) -> RenderedScene:
    """Render a coordinate diagram after public task code selects the objects."""

    rng = spawn_rng(int(instance_seed), str(random_namespace))
    context = resolve_graph_scene_context(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        render_defaults=render_defaults,
        background_defaults=background_defaults,
        fallback_canvas_min=int(group_default(render_defaults, "coordinate_composite_canvas_size_min", 660)),
        fallback_canvas_max=int(group_default(render_defaults, "coordinate_composite_canvas_size_max", 740)),
        fallback_cells_min=int(group_default(render_defaults, "coordinate_composite_graph_cells_min", 18)),
        fallback_cells_max=int(group_default(render_defaults, "coordinate_composite_graph_cells_max", 20)),
        graph_style_overrides={
            "axis_scale_labels_enabled": False,
            "origin_label_enabled": False,
            "axis_arrows_enabled": True,
        },
    )
    image, draw, background_meta = make_graph_scene_canvas(
        instance_seed=int(instance_seed),
        context=context,
        background_defaults=background_defaults,
        require_graph_paper=True,
    )
    shape_style = sample_geometry_shape_style(
        rng,
        params=params,
        render_defaults=render_defaults,
        anchor_colors=extract_background_anchor_colors(background_meta),
    )
    intersections = filtered_intersections(objects, pair_filter)
    if len(intersections) != int(expected_count):
        raise RuntimeError(
            f"coordinate-composite case expected {int(expected_count)} intersections, got {len(intersections)}"
        )

    line_width = int(
        rng.randint(
            int(group_default(render_defaults, "coordinate_composite_line_width_min", 3)),
            int(group_default(render_defaults, "coordinate_composite_line_width_max", 5)),
        )
    )
    object_colors = _sample_object_colors(rng, shape_color=shape_style.line_color)
    drawn_objects: List[Dict[str, Any]] = []
    for index, obj in enumerate(objects):
        object_color = tuple(int(value) for value in object_colors[int(index) % len(object_colors)])
        drawn = _draw_object(
            draw,
            obj,
            color=object_color,
            context=context,
            width_px=int(line_width),
        )
        drawn["graph"] = object_to_trace(obj)
        drawn["color"] = [int(value) for value in object_color]
        drawn_objects.append(drawn)

    intersections_px = tuple(
        graph_units_to_pixel(point, origin=context.graph_origin, spacing=int(context.graph_spacing))
        for point in intersections
    )
    final_image, final_background_meta, post_noise_meta = finalize_graph_scene_image(
        image,
        instance_seed=int(instance_seed),
        context=context,
        background_meta=background_meta,
        noise_defaults=noise_defaults,
    )
    render_spec_extra = {
        "graph_coordinate_frame": dict(context.graph_frame),
        "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
        "graph_layout": dict(context.graph_layout_metadata),
        "shape_style": dict(shape_style.to_trace_dict()),
        "object_colors": [[int(channel) for channel in color] for color in object_colors],
        "line_width_px": int(line_width),
    }
    render_map = {
        "objects": [dict(obj) for obj in drawn_objects],
        "intersection_points_graph": [point_to_list(point) for point in intersections],
        "intersection_points_px": [point_to_list(point) for point in intersections_px],
        "transform": str(transform),
    }
    return RenderedScene(
        image=final_image,
        intersection_points_px=tuple((float(point[0]), float(point[1])) for point in intersections_px),
        intersection_points_graph=tuple((float(point[0]), float(point[1])) for point in intersections),
        object_specs=tuple(object_to_trace(obj) for obj in objects),
        render_map=render_map,
        background_meta=dict(final_background_meta),
        post_noise_meta=dict(post_noise_meta),
        render_spec_extra=render_spec_extra,
    )


__all__ = ["render_coordinate_composite_scene"]
