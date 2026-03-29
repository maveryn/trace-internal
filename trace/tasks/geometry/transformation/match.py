"""Geometry transformation matching task on one shared graph-paper scene."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import draw_text_centered, load_font, resolve_scene_label_font_size_px
from ...shared.geometry_primitives import Point, point_inside_square_canvas
from ...shared.drawing import draw_arrow, draw_dashed_line
from ..comparison.shared import COMPARISON_ANSWER_LABEL_POOL, resolve_comparison_winner_label
from ..shared.background_defaults import load_geometry_background_defaults
from ..shared.complexity import build_geometry_transformation_complexity
from ..shared.graph_rendering import graph_paper_grid_from_frame, scale_point
from ..shared.labeled_point_evidence import graph_point_set_evidence_artifacts
from ..shared.multi_polygon_scene import PolygonSceneObject, draw_polygon_objects
from ..shared.noise_defaults import load_geometry_noise_defaults
from ..shared.point_labels import draw_labeled_points
from ..shared.polygon_scene_helpers import (
    draw_reference_polygon,
    graph_polygon_inside_canvas,
    pixel_point_from_graph_units,
    pixel_polygon_from_graph_units,
)
from ..shared.polygon_transformations import (
    Polygon,
    RIGID_TRANSFORM_RECIPE_IDS,
    apply_rigid_transform_recipe,
    ordered_vertex_label_map,
    sample_asymmetric_polygon_template,
    translate_polygon,
)
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from ..shared.consolidated_sampling import resolve_compatible_scene_query_variants


TASK_ID = "task_geometry_transformation_match"

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("triangle", "quadrilateral")
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = ("translation_match", "reflection_match", "rotation_match")
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "triangle": SUPPORTED_QUERY_VARIANTS,
    "quadrilateral": SUPPORTED_QUERY_VARIANTS,
}

POST_IMAGE_BACKGROUND_DEFAULTS = load_geometry_background_defaults(task_group="transformation")
POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(task_group="transformation")

_TRANSFORM_RECIPE_IDENTITY = "identity"
_TRANSFORM_RECIPE_REFLECT_VERTICAL = "reflect_vertical"
_TRANSFORM_RECIPE_REFLECT_HORIZONTAL = "reflect_horizontal"
_TRANSFORM_RECIPE_ROTATE_90_CW = "rotate_90_cw"
_TRANSFORM_RECIPE_ROTATE_90_CCW = "rotate_90_ccw"
_TRANSFORM_RECIPE_ROTATE_180 = "rotate_180"

_LOCAL_TRANSFORM_RECIPES: Tuple[str, ...] = tuple(RIGID_TRANSFORM_RECIPE_IDS)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for geometry transformation scenes."""

    canvas_size_min: int = 640
    canvas_size_max: int = 720
    graph_cells_min: int = 24
    graph_cells_max: int = 28
    line_width: int = 4
    line_width_min: int = 3
    line_width_max: int = 5
    label_font_size_min: int = 16
    label_font_size_max: int = 28
    label_stroke_width: int = 1
    label_stroke_width_min: int = 1
    label_stroke_width_max: int = 2
    object_label_offset_px: int = 14
    reference_label_gap_px: int = 20
    cue_label_gap_px: int = 18
    cue_dash_px: int = 10
    cue_gap_px: int = 8
    cue_arrow_head_length_px: int = 18
    cue_arrow_head_width_px: int = 14
    cue_point_radius_px: int = 4
    cue_line_padding_px: int = 18
    candidate_label_pool: Tuple[str, ...] = COMPARISON_ANSWER_LABEL_POOL
    translation_vectors: Tuple[Tuple[int, int], ...] = (
        (8, 0),
        (8, 3),
        (8, -3),
        (12, 0),
        (12, 3),
        (12, -3),
    )
    candidate_slots: Tuple[Tuple[int, int], ...] = (
        (4, 4),
        (8, 4),
        (4, 0),
        (8, 0),
        (4, -4),
        (8, -4),
    )
    translation_vector_anchor: Tuple[int, int] = (-10, 7)
    reflection_axis_x: int = 0
    reflection_line_y_min: int = -9
    reflection_line_y_max: int = 9


@dataclass(frozen=True)
class _RotationMode:
    """One supported rotation query flavor."""

    mode_id: str
    quarter_turns: int
    prompt_label: str
    allowed_slot_indices: Tuple[int, ...]


_ROTATION_MODES: Tuple[_RotationMode, ...] = (
    _RotationMode(
        mode_id="quarter_turn_clockwise",
        quarter_turns=1,
        prompt_label="90° clockwise rotation",
        allowed_slot_indices=(0, 1),
    ),
    _RotationMode(
        mode_id="half_turn",
        quarter_turns=2,
        prompt_label="180° rotation",
        allowed_slot_indices=(0, 1, 2, 3, 4, 5),
    ),
    _RotationMode(
        mode_id="quarter_turn_counterclockwise",
        quarter_turns=3,
        prompt_label="90° counterclockwise rotation",
        allowed_slot_indices=(4, 5),
    ),
)


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved scene/query axes and answer-label support for one instance."""

    scene_variant: str
    query_variant: str
    winner_label: str
    scene_variant_probabilities: Dict[str, float]
    query_variant_probabilities: Dict[str, float]
    winner_label_probabilities: Dict[str, float]
    candidate_label_pool: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderedTransformationScene:
    """Task-local scene package with geometry, cues, and trace payloads."""

    reference_vertices_graph: Polygon
    winner_vertices_graph: Polygon
    reference_vertices_px: Polygon
    winner_vertices_px: Polygon
    candidate_vertices_graph_by_label: Dict[str, Polygon]
    candidate_vertices_px_by_label: Dict[str, Polygon]
    candidate_centers_graph_by_label: Dict[str, Point]
    candidate_centers_px_by_label: Dict[str, Point]
    winner_label: str
    reference_center_graph: Point
    cue_kind: str
    cue_trace: Dict[str, Any]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]
    evidence: Dict[str, Any]
    answer_value: str
    object_label_centers: Dict[str, List[float]]
    required_evidence_labels: List[str]
    rotation_mode: str | None
    rotation_prompt_label: str | None
    translation_vector: Tuple[int, int] | None


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "transformation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _apply_local_transform(template: Polygon, *, recipe: str) -> Polygon:
    """Apply one local rigid transform recipe around the origin."""
    return apply_rigid_transform_recipe(template, recipe=str(recipe))


def _winner_recipe_for_query(*, query_variant: str, rotation_mode: _RotationMode | None) -> str:
    """Return the correct local transform recipe for the requested query."""

    normalized_query = str(query_variant)
    if normalized_query == "translation_match":
        return _TRANSFORM_RECIPE_IDENTITY
    if normalized_query == "reflection_match":
        return _TRANSFORM_RECIPE_REFLECT_VERTICAL
    if normalized_query == "rotation_match":
        if rotation_mode is None:
            raise ValueError("rotation_match requires one resolved rotation_mode")
        quarter_turns = int(rotation_mode.quarter_turns) % 4
        if quarter_turns == 1:
            return _TRANSFORM_RECIPE_ROTATE_90_CW
        if quarter_turns == 2:
            return _TRANSFORM_RECIPE_ROTATE_180
        if quarter_turns == 3:
            return _TRANSFORM_RECIPE_ROTATE_90_CCW
    raise ValueError(f"unsupported transformation query_variant: {query_variant}")


def _local_distractor_recipes(*, winner_recipe: str) -> Tuple[str, ...]:
    """Return the five distractor transform recipes for the non-winning candidates."""

    return tuple(recipe for recipe in _LOCAL_TRANSFORM_RECIPES if str(recipe) != str(winner_recipe))


def _reference_center_for_rotation(slot_center: Point, *, rotation_mode: _RotationMode) -> Point:
    """Return the inverse-rotated reference center for one winner slot."""

    if int(rotation_mode.quarter_turns) % 4 == 1:
        return (-float(slot_center[1]), float(slot_center[0]))
    if int(rotation_mode.quarter_turns) % 4 == 2:
        return (-float(slot_center[0]), -float(slot_center[1]))
    if int(rotation_mode.quarter_turns) % 4 == 3:
        return (float(slot_center[1]), -float(slot_center[0]))
    raise ValueError("rotation transformation requires a non-zero quarter turn")


def _translation_vector_support(params: Mapping[str, Any]) -> Tuple[Tuple[int, int], ...]:
    """Resolve the supported translation vectors from params/defaults."""

    raw_support = params.get("translation_vectors", group_default(_GEN_DEFAULTS, "translation_vectors", _DEFAULTS.translation_vectors))
    support: List[Tuple[int, int]] = []
    for value in raw_support:
        if not isinstance(value, Sequence) or len(value) != 2:
            raise ValueError("translation_vectors entries must be [dx, dy] pairs")
        support.append((int(value[0]), int(value[1])))
    if not support:
        raise ValueError("translation_vectors support must be non-empty")
    return tuple(support)


def _candidate_slot_support(params: Mapping[str, Any]) -> Tuple[Tuple[int, int], ...]:
    """Resolve the six candidate slot centers used by the transformation scene."""

    raw_support = params.get("candidate_slots", group_default(_GEN_DEFAULTS, "candidate_slots", _DEFAULTS.candidate_slots))
    slots: List[Tuple[int, int]] = []
    for value in raw_support:
        if not isinstance(value, Sequence) or len(value) != 2:
            raise ValueError("candidate_slots entries must be [x, y] graph-unit pairs")
        slot = (int(value[0]), int(value[1]))
        if slot not in slots:
            slots.append(slot)
    if len(slots) != 6:
        raise ValueError("geometry transformation currently requires exactly six candidate slots")
    return tuple(slots)


def _draw_translation_cue(
    draw,
    *,
    context: GraphSceneContext,
    line_width: int,
    head_length_px: int,
    head_width_px: int,
    vector_anchor: Tuple[int, int],
    translation_vector: Tuple[int, int],
    color: Sequence[int],
) -> Dict[str, Any]:
    """Draw the translation vector cue and return trace metadata."""

    start_graph = (int(vector_anchor[0]), int(vector_anchor[1]))
    end_graph = (
        int(vector_anchor[0]) + int(translation_vector[0]),
        int(vector_anchor[1]) + int(translation_vector[1]),
    )
    start_px = scale_point(pixel_point_from_graph_units(start_graph, context=context), int(context.scene_scale))
    end_px = scale_point(pixel_point_from_graph_units(end_graph, context=context), int(context.scene_scale))
    draw_arrow(
        draw,
        start=start_px,
        end=end_px,
        fill=tuple(int(value) for value in color),
        width=int(line_width),
        head_length_px=float(head_length_px),
        head_width_px=float(head_width_px),
    )
    return {
        "type": "translation_vector",
        "start_graph": [int(start_graph[0]), int(start_graph[1])],
        "end_graph": [int(end_graph[0]), int(end_graph[1])],
        "vector_graph": [int(translation_vector[0]), int(translation_vector[1])],
        "start_px": [round(float(start_px[0]) / float(max(1, int(context.scene_scale))), 3), round(float(start_px[1]) / float(max(1, int(context.scene_scale))), 3)],
        "end_px": [round(float(end_px[0]) / float(max(1, int(context.scene_scale))), 3), round(float(end_px[1]) / float(max(1, int(context.scene_scale))), 3)],
    }


def _draw_reflection_cue(
    draw,
    *,
    context: GraphSceneContext,
    line_width: int,
    dash_px: int,
    gap_px: int,
    label_font_size_px: int,
    label_stroke_width: int,
    cue_label_gap_px: int,
    axis_x: int,
    y_min: int,
    y_max: int,
    color: Sequence[int],
    label_color: Sequence[int],
    label_stroke_color: Sequence[int],
) -> Dict[str, Any]:
    """Draw the vertical reflection line `l` and return trace metadata."""

    start_graph = (int(axis_x), int(y_min))
    end_graph = (int(axis_x), int(y_max))
    start_px = scale_point(pixel_point_from_graph_units(start_graph, context=context), int(context.scene_scale))
    end_px = scale_point(pixel_point_from_graph_units(end_graph, context=context), int(context.scene_scale))
    draw_dashed_line(
        draw,
        start=start_px,
        end=end_px,
        fill=tuple(int(value) for value in color),
        width=max(1, int(line_width)),
        dash_px=float(dash_px),
        gap_px=float(gap_px),
    )
    label_center = (
        float(start_px[0]) + float(cue_label_gap_px),
        float(min(start_px[1], end_px[1])) + float(label_font_size_px),
    )
    font = load_font(int(label_font_size_px), bold=True)
    draw_text_centered(
        draw,
        text="l",
        center=label_center,
        font=font,
        fill=tuple(int(value) for value in label_color),
        stroke_fill=tuple(int(value) for value in label_stroke_color),
        stroke_width=int(label_stroke_width),
    )
    return {
        "type": "reflection_line",
        "axis_kind": "vertical",
        "line_label": "l",
        "x_graph": int(axis_x),
        "y_graph_range": [int(y_min), int(y_max)],
        "start_px": [round(float(start_px[0]) / float(max(1, int(context.scene_scale))), 3), round(float(start_px[1]) / float(max(1, int(context.scene_scale))), 3)],
        "end_px": [round(float(end_px[0]) / float(max(1, int(context.scene_scale))), 3), round(float(end_px[1]) / float(max(1, int(context.scene_scale))), 3)],
    }


def _draw_rotation_cue(
    draw,
    *,
    context: GraphSceneContext,
    label_font_size_px: int,
    label_stroke_width: int,
    point_radius_px: int,
    color: Sequence[int],
    label_color: Sequence[int],
    label_stroke_color: Sequence[int],
) -> Dict[str, Any]:
    """Draw the rotation-center point `O` and return trace metadata."""

    center_graph = (0, 0)
    center_px = pixel_point_from_graph_units(center_graph, context=context)
    scaled_center = scale_point(center_px, int(context.scene_scale))
    draw_labeled_points(
        draw,
        points=[scaled_center],
        labels=["O"],
        label_offset_px=float(max(12, int(label_font_size_px))),
        font_size_px=int(label_font_size_px),
        text_stroke_width=int(label_stroke_width),
        marker_radius_px=max(1, int(point_radius_px)),
        marker_color=tuple(int(value) for value in color),
        label_color=tuple(int(value) for value in label_color),
        label_stroke_color=tuple(int(value) for value in label_stroke_color),
        canvas_size=int(context.canvas_size) * int(context.scene_scale),
    )
    return {
        "type": "rotation_center",
        "point_label": "O",
        "center_graph": [0, 0],
        "center_px": [round(float(center_px[0]), 3), round(float(center_px[1]), 3)],
    }


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve scene/query axes plus balanced answer-label support."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    scene_variant, scene_probs, query_variant, query_probs = resolve_compatible_scene_query_variants(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_scene_variants=SUPPORTED_SCENE_VARIANTS,
        supported_query_variants=SUPPORTED_QUERY_VARIANTS,
        compatibility=COMPATIBILITY,
        scene_sampling_namespace=f"{TASK_ID}.scene_variant",
        query_sampling_namespace=f"{TASK_ID}.query_variant",
    )
    label_pool = tuple(
        str(label).upper()
        for label in params.get(
            "candidate_label_pool",
            group_default(_GEN_DEFAULTS, "candidate_label_pool", _DEFAULTS.candidate_label_pool),
        )
    )
    if len(label_pool) != 6 or len(set(label_pool)) != 6:
        raise ValueError("geometry transformation requires exactly six unique candidate labels")
    winner_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.winner_label")
    winner_label, winner_probs = resolve_comparison_winner_label(
        winner_rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        label_pool=label_pool,
        selection_namespace=(
            f"{TASK_ID}.winner_label.{str(scene_variant)}.{str(query_variant)}"
        ),
    )
    return _ResolvedQuery(
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
        winner_label=str(winner_label),
        scene_variant_probabilities=dict(scene_probs),
        query_variant_probabilities=dict(query_probs),
        winner_label_probabilities=dict(winner_probs),
        candidate_label_pool=tuple(label_pool),
    )


def _sample_transformation_scene(
    rng,
    *,
    query: _ResolvedQuery,
    context: GraphSceneContext,
    padding_px: float,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    reference_label_gap_px: int,
    cue_label_gap_px: int,
    cue_dash_px: int,
    cue_gap_px: int,
    cue_arrow_head_length_px: int,
    cue_arrow_head_width_px: int,
    cue_point_radius_px: int,
    object_label_offset_px: float,
    draw,
    shape_style,
    render_canvas_size: int,
    params: Mapping[str, Any],
) -> _RenderedTransformationScene:
    """Sample and render one full transformation-match scene."""

    template = sample_asymmetric_polygon_template(str(query.scene_variant), rng)
    slots = _candidate_slot_support(params)
    translation_vectors = _translation_vector_support(params)

    winner_slot_index: int | None = None
    reference_center_graph: Point | None = None
    rotation_mode: _RotationMode | None = None
    translation_vector: Tuple[int, int] | None = None

    slot_indices = list(range(len(slots)))
    rng.shuffle(slot_indices)
    if str(query.query_variant) == "translation_match":
        candidate_pairs: List[Tuple[int, Tuple[int, int], Point]] = []
        for slot_index in slot_indices:
            slot_center = slots[int(slot_index)]
            for dx, dy in translation_vectors:
                candidate_reference = (
                    float(slot_center[0]) - float(dx),
                    float(slot_center[1]) - float(dy),
                )
                if float(candidate_reference[0]) > -2.0:
                    continue
                if not graph_polygon_inside_canvas(
                    translate_polygon(template, dx=int(candidate_reference[0]), dy=int(candidate_reference[1])),
                    context=context,
                    padding_px=float(padding_px),
                ):
                    continue
                cue_start = tuple(
                    int(value)
                    for value in params.get(
                        "translation_vector_anchor",
                        group_default(_GEN_DEFAULTS, "translation_vector_anchor", _DEFAULTS.translation_vector_anchor),
                    )
                )
                cue_end = (int(cue_start[0]) + int(dx), int(cue_start[1]) + int(dy))
                cue_points_ok = all(
                    point_inside_square_canvas(
                        pixel_point_from_graph_units(point, context=context),
                        canvas_size=int(context.canvas_size),
                        padding=float(padding_px),
                    )
                    for point in (cue_start, cue_end)
                )
                if not cue_points_ok:
                    continue
                candidate_pairs.append((int(slot_index), (int(dx), int(dy)), candidate_reference))
        if not candidate_pairs:
            raise ValueError("no feasible translation slot/vector pair for current scene context")
        winner_slot_index, translation_vector, reference_center_graph = rng.choice(candidate_pairs)
    elif str(query.query_variant) == "reflection_match":
        axis_x = int(params.get("reflection_axis_x", group_default(_GEN_DEFAULTS, "reflection_axis_x", _DEFAULTS.reflection_axis_x)))
        for slot_index in slot_indices:
            slot_center = slots[int(slot_index)]
            candidate_reference = (
                float((2 * int(axis_x)) - int(slot_center[0])),
                float(slot_center[1]),
            )
            if float(candidate_reference[0]) >= float(axis_x):
                continue
            reference_vertices_graph = translate_polygon(
                template,
                dx=int(candidate_reference[0]),
                dy=int(candidate_reference[1]),
            )
            if graph_polygon_inside_canvas(reference_vertices_graph, context=context, padding_px=float(padding_px)):
                winner_slot_index = int(slot_index)
                reference_center_graph = candidate_reference
                break
        if winner_slot_index is None or reference_center_graph is None:
            raise ValueError("no feasible reflection slot for current scene context")
    else:
        rotation_modes = list(_ROTATION_MODES)
        rng.shuffle(rotation_modes)
        for mode in rotation_modes:
            allowed = list(mode.allowed_slot_indices)
            rng.shuffle(allowed)
            for slot_index in allowed:
                slot_center = slots[int(slot_index)]
                candidate_reference = _reference_center_for_rotation(slot_center, rotation_mode=mode)
                if float(candidate_reference[0]) > -2.0:
                    continue
                reference_vertices_graph = translate_polygon(
                    template,
                    dx=int(candidate_reference[0]),
                    dy=int(candidate_reference[1]),
                )
                if graph_polygon_inside_canvas(reference_vertices_graph, context=context, padding_px=float(padding_px)):
                    winner_slot_index = int(slot_index)
                    reference_center_graph = candidate_reference
                    rotation_mode = mode
                    break
            if winner_slot_index is not None:
                break
        if winner_slot_index is None or reference_center_graph is None or rotation_mode is None:
            raise ValueError("no feasible rotation slot for current scene context")

    reference_vertices_graph = translate_polygon(
        template,
        dx=int(reference_center_graph[0]),
        dy=int(reference_center_graph[1]),
    )
    reference_vertices_px = pixel_polygon_from_graph_units(reference_vertices_graph, context=context)

    winner_recipe = _winner_recipe_for_query(query_variant=str(query.query_variant), rotation_mode=rotation_mode)
    distractor_recipes = list(_local_distractor_recipes(winner_recipe=str(winner_recipe)))
    rng.shuffle(distractor_recipes)

    labels = list(query.candidate_label_pool)
    other_labels = [label for label in labels if str(label) != str(query.winner_label)]
    rng.shuffle(other_labels)

    candidate_vertices_graph_by_label: Dict[str, Polygon] = {}
    candidate_vertices_px_by_label: Dict[str, Polygon] = {}
    candidate_centers_graph_by_label: Dict[str, Point] = {}
    candidate_centers_px_by_label: Dict[str, Point] = {}
    objects: List[PolygonSceneObject] = []
    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": "reference_polygon",
            "entity_type": "reference_polygon",
            "scene_variant": str(query.scene_variant),
            "vertices_graph": [[int(round(point[0])), int(round(point[1]))] for point in reference_vertices_graph],
            "center_graph": [round(float(reference_center_graph[0]), 3), round(float(reference_center_graph[1]), 3)],
        }
    ]

    label_by_slot_index: Dict[int, str] = {}
    for slot_index in range(len(slots)):
        if int(slot_index) == int(winner_slot_index):
            label_by_slot_index[int(slot_index)] = str(query.winner_label)
        else:
            label_by_slot_index[int(slot_index)] = str(other_labels.pop())

    for slot_index, slot_center in enumerate(slots):
        label = str(label_by_slot_index[int(slot_index)])
        if int(slot_index) == int(winner_slot_index):
            local_vertices = _apply_local_transform(template, recipe=str(winner_recipe))
        else:
            local_vertices = _apply_local_transform(template, recipe=str(distractor_recipes.pop()))
        candidate_vertices_graph = translate_polygon(
            local_vertices,
            dx=int(slot_center[0]),
            dy=int(slot_center[1]),
        )
        if not graph_polygon_inside_canvas(candidate_vertices_graph, context=context, padding_px=float(padding_px)):
            raise ValueError("candidate polygon fell outside the graph-paper canvas")
        candidate_vertices_px = pixel_polygon_from_graph_units(candidate_vertices_graph, context=context)
        candidate_vertices_graph_by_label[str(label)] = tuple(candidate_vertices_graph)
        candidate_vertices_px_by_label[str(label)] = tuple(candidate_vertices_px)
        candidate_centers_graph_by_label[str(label)] = (float(slot_center[0]), float(slot_center[1]))
        candidate_centers_px_by_label[str(label)] = pixel_point_from_graph_units(slot_center, context=context)
        objects.append(
            PolygonSceneObject(
                label=str(label),
                vertices=tuple(candidate_vertices_px),
                center=pixel_point_from_graph_units(slot_center, context=context),
            )
        )
        scene_entities.append(
            {
                "entity_id": f"candidate_{label}",
                "entity_type": "candidate_polygon",
                "label": str(label),
                "scene_variant": str(query.scene_variant),
                "vertices_graph": [[int(round(point[0])), int(round(point[1]))] for point in candidate_vertices_graph],
                "center_graph": [int(slot_center[0]), int(slot_center[1])],
            }
        )

    object_label_centers = draw_polygon_objects(
        draw,
        objects=objects,
        scene_scale=int(context.scene_scale),
        line_width=int(line_width),
        label_font_size_px=int(label_font_size_px),
        label_stroke_width=int(label_stroke_width),
        object_label_offset_px=float(object_label_offset_px),
        render_canvas_size=int(render_canvas_size),
        shape_style=shape_style,
    )
    draw_reference_polygon(
        draw,
        vertices_px=reference_vertices_px,
        scene_scale=int(context.scene_scale),
        line_width=int(line_width),
        label_font_size_px=int(label_font_size_px),
        label_stroke_width=int(label_stroke_width),
        label_gap_px=float(reference_label_gap_px),
        line_color=shape_style.line_color,
        label_color=shape_style.label_color,
        label_stroke_color=shape_style.label_stroke_color,
    )

    if str(query.query_variant) == "translation_match":
        cue_trace = _draw_translation_cue(
            draw,
            context=context,
            line_width=int(line_width),
            head_length_px=int(cue_arrow_head_length_px),
            head_width_px=int(cue_arrow_head_width_px),
            vector_anchor=tuple(
                int(value)
                for value in params.get(
                    "translation_vector_anchor",
                    group_default(_GEN_DEFAULTS, "translation_vector_anchor", _DEFAULTS.translation_vector_anchor),
                )
            ),
            translation_vector=translation_vector if translation_vector is not None else (0, 0),
            color=shape_style.line_color,
        )
    elif str(query.query_variant) == "reflection_match":
        cue_trace = _draw_reflection_cue(
            draw,
            context=context,
            line_width=int(line_width),
            dash_px=int(cue_dash_px) * int(context.scene_scale),
            gap_px=int(cue_gap_px) * int(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            cue_label_gap_px=int(cue_label_gap_px) * int(context.scene_scale),
            axis_x=int(params.get("reflection_axis_x", group_default(_GEN_DEFAULTS, "reflection_axis_x", _DEFAULTS.reflection_axis_x))),
            y_min=int(params.get("reflection_line_y_min", group_default(_GEN_DEFAULTS, "reflection_line_y_min", _DEFAULTS.reflection_line_y_min))),
            y_max=int(params.get("reflection_line_y_max", group_default(_GEN_DEFAULTS, "reflection_line_y_max", _DEFAULTS.reflection_line_y_max))),
            color=shape_style.line_color,
            label_color=shape_style.label_color,
            label_stroke_color=shape_style.label_stroke_color,
        )
    else:
        cue_trace = _draw_rotation_cue(
            draw,
            context=context,
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            point_radius_px=max(1, int(cue_point_radius_px) * int(context.scene_scale)),
            color=shape_style.line_color,
            label_color=shape_style.label_color,
            label_stroke_color=shape_style.label_stroke_color,
        )
        cue_trace["rotation_mode"] = str(rotation_mode.mode_id) if rotation_mode is not None else None
        cue_trace["rotation_instruction"] = str(rotation_mode.prompt_label) if rotation_mode is not None else None

    scene_entities.append(dict(cue_trace))

    winner_vertices_px = candidate_vertices_px_by_label[str(query.winner_label)]
    evidence = graph_point_set_evidence_artifacts(
        points_by_label=ordered_vertex_label_map(winner_vertices_px),
        graph_origin=context.graph_origin,
        graph_spacing=int(context.graph_spacing),
        witness_type="winning_transformed_polygon_vertices",
    )
    required_labels = list(evidence.get("required_labels", []))

    render_map = {
        "image_id": "img0",
        "reference_vertices_graph": [[int(round(point[0])), int(round(point[1]))] for point in reference_vertices_graph],
        "candidate_vertices_graph_by_label": {
            str(label): [[int(round(point[0])), int(round(point[1]))] for point in vertices]
            for label, vertices in candidate_vertices_graph_by_label.items()
        },
        "candidate_centers_graph_by_label": {
            str(label): [round(float(center[0]), 3), round(float(center[1]), 3)]
            for label, center in candidate_centers_graph_by_label.items()
        },
        "winner_label": str(query.winner_label),
        "object_label_centers": dict(object_label_centers),
        "cue": dict(cue_trace),
    }
    if translation_vector is not None:
        render_map["translation_vector_graph"] = [int(translation_vector[0]), int(translation_vector[1])]

    return _RenderedTransformationScene(
        reference_vertices_graph=tuple(reference_vertices_graph),
        winner_vertices_graph=tuple(candidate_vertices_graph_by_label[str(query.winner_label)]),
        reference_vertices_px=tuple(reference_vertices_px),
        winner_vertices_px=tuple(winner_vertices_px),
        candidate_vertices_graph_by_label=dict(candidate_vertices_graph_by_label),
        candidate_vertices_px_by_label=dict(candidate_vertices_px_by_label),
        candidate_centers_graph_by_label=dict(candidate_centers_graph_by_label),
        candidate_centers_px_by_label=dict(candidate_centers_px_by_label),
        winner_label=str(query.winner_label),
        reference_center_graph=(float(reference_center_graph[0]), float(reference_center_graph[1])),
        cue_kind=str(cue_trace["type"]),
        cue_trace=dict(cue_trace),
        scene_entities=scene_entities,
        render_map=render_map,
        evidence=evidence,
        answer_value=str(query.winner_label),
        object_label_centers=dict(object_label_centers),
        required_evidence_labels=required_labels,
        rotation_mode=(str(rotation_mode.mode_id) if rotation_mode is not None else None),
        rotation_prompt_label=(str(rotation_mode.prompt_label) if rotation_mode is not None else None),
        translation_vector=translation_vector,
    )


@register_task
class GeometryTransformationMatchTask:
    """Match the labeled polygon that satisfies the shown transformation cue."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = "transformation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query = _resolve_axes(int(instance_seed), params=params)
        scene_rng = spawn_rng(int(instance_seed), f"{self.task_id}.scene")

        line_width = None
        label_font_size_px = None
        label_stroke_width_scene = None
        context = None
        image = None
        background_meta = None
        shape_style = None
        rendered_scene = None
        last_error: Exception | None = None

        for _ in range(max(1, int(max_attempts))):
            context_attempt = resolve_graph_scene_context(
                scene_rng,
                params=params,
                render_defaults=_RENDER_DEFAULTS,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
                fallback_canvas_min=_DEFAULTS.canvas_size_min,
                fallback_canvas_max=_DEFAULTS.canvas_size_max,
                fallback_cells_min=_DEFAULTS.graph_cells_min,
                fallback_cells_max=_DEFAULTS.graph_cells_max,
            )
            line_width_attempt = sample_int_render_param(
                scene_rng,
                params=params,
                render_defaults=_RENDER_DEFAULTS,
                key="line_width",
                fallback=_DEFAULTS.line_width,
                minimum_value=1,
            )
            label_font_size_px_attempt = int(
                params.get(
                    "label_font_size_px",
                    resolve_scene_label_font_size_px(
                        canvas_size=int(context_attempt.canvas_size),
                        graph_spacing=int(context_attempt.graph_spacing),
                        scene_scale=int(context_attempt.scene_scale),
                        min_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_min", _DEFAULTS.label_font_size_min)),
                        max_px=int(group_default(_RENDER_DEFAULTS, "label_font_size_max", _DEFAULTS.label_font_size_max)),
                    ),
                )
            )
            label_stroke_width_attempt = sample_int_render_param(
                scene_rng,
                params=params,
                render_defaults=_RENDER_DEFAULTS,
                key="label_stroke_width",
                fallback=_DEFAULTS.label_stroke_width,
                minimum_value=1,
            )
            label_stroke_width_scene_attempt = max(1, int(label_stroke_width_attempt) * int(context_attempt.scene_scale))
            image_attempt, draw_attempt, background_meta_attempt = make_graph_scene_canvas(
                instance_seed=int(instance_seed),
                context=context_attempt,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            shape_style_attempt = sample_geometry_shape_style(
                scene_rng,
                params=params,
                render_defaults=_RENDER_DEFAULTS,
                anchor_colors=extract_background_anchor_colors(background_meta_attempt),
            )
            padding_px = float(
                params.get(
                    "cue_line_padding_px",
                    group_default(_RENDER_DEFAULTS, "cue_line_padding_px", _DEFAULTS.cue_line_padding_px),
                )
            )
            try:
                rendered_scene_attempt = _sample_transformation_scene(
                    scene_rng,
                    query=query,
                    context=context_attempt,
                    padding_px=float(padding_px),
                    line_width=int(line_width_attempt) * int(context_attempt.scene_scale),
                    label_font_size_px=int(label_font_size_px_attempt),
                    label_stroke_width=int(label_stroke_width_scene_attempt),
                    reference_label_gap_px=int(
                        params.get(
                            "reference_label_gap_px",
                            group_default(_RENDER_DEFAULTS, "reference_label_gap_px", _DEFAULTS.reference_label_gap_px),
                        )
                    ),
                    cue_label_gap_px=int(
                        params.get(
                            "cue_label_gap_px",
                            group_default(_RENDER_DEFAULTS, "cue_label_gap_px", _DEFAULTS.cue_label_gap_px),
                        )
                    ),
                    cue_dash_px=int(params.get("cue_dash_px", group_default(_RENDER_DEFAULTS, "cue_dash_px", _DEFAULTS.cue_dash_px))),
                    cue_gap_px=int(params.get("cue_gap_px", group_default(_RENDER_DEFAULTS, "cue_gap_px", _DEFAULTS.cue_gap_px))),
                    cue_arrow_head_length_px=int(
                        params.get(
                            "cue_arrow_head_length_px",
                            group_default(_RENDER_DEFAULTS, "cue_arrow_head_length_px", _DEFAULTS.cue_arrow_head_length_px),
                        )
                    )
                    * int(context_attempt.scene_scale),
                    cue_arrow_head_width_px=int(
                        params.get(
                            "cue_arrow_head_width_px",
                            group_default(_RENDER_DEFAULTS, "cue_arrow_head_width_px", _DEFAULTS.cue_arrow_head_width_px),
                        )
                    )
                    * int(context_attempt.scene_scale),
                    cue_point_radius_px=int(
                        params.get(
                            "cue_point_radius_px",
                            group_default(_RENDER_DEFAULTS, "cue_point_radius_px", _DEFAULTS.cue_point_radius_px),
                        )
                    ),
                    object_label_offset_px=float(
                        params.get(
                            "object_label_offset_px",
                            group_default(_RENDER_DEFAULTS, "object_label_offset_px", _DEFAULTS.object_label_offset_px),
                        )
                    ),
                    draw=draw_attempt,
                    shape_style=shape_style_attempt,
                    render_canvas_size=int(context_attempt.canvas_size) * int(context_attempt.scene_scale),
                    params=params,
                )
                context = context_attempt
                image = image_attempt
                background_meta = background_meta_attempt
                shape_style = shape_style_attempt
                rendered_scene = rendered_scene_attempt
                line_width = int(line_width_attempt)
                label_font_size_px = int(label_font_size_px_attempt)
                label_stroke_width_scene = int(label_stroke_width_scene_attempt)
                break
            except Exception as exc:
                last_error = exc
                continue

        if (
            rendered_scene is None
            or context is None
            or image is None
            or background_meta is None
            or shape_style is None
            or line_width is None
            or label_font_size_px is None
            or label_stroke_width_scene is None
        ):
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        evidence_value = rendered_scene.evidence.get("evidence_value", [])
        if not isinstance(evidence_value, list) or not evidence_value:
            raise RuntimeError("geometry transformation evidence must include winning polygon graph points")

        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "evidence_hint_template",
                "answer_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = build_prompt_json_examples(
            evidence_value=evidence_value,
            answer_type="option_letter",
        )
        evidence_hint = str(prompt_defaults["evidence_hint_template"]).format(
            vertex_count=len(rendered_scene.required_evidence_labels),
        )
        prompt_slots = {
            "object_description": str(prompt_defaults["object_description"]),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "evidence_hint": str(evidence_hint),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        }
        if str(query.query_variant) == "rotation_match":
            prompt_slots["rotation_instruction"] = str(rendered_scene.rotation_prompt_label or "180° rotation")
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(query.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=prompt_slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="option_letter", value=str(rendered_scene.answer_value))
        evidence_gt = TypedValue(type="graph_point_set", value=[list(point) for point in evidence_value])

        query_params: Dict[str, Any] = {
            "scene_variant": str(query.scene_variant),
            "query_variant": str(query.query_variant),
            "task_variant": str(query.query_variant),
            "variant_probabilities": dict(query.query_variant_probabilities),
            "scene_variant_probabilities": dict(query.scene_variant_probabilities),
            "query_variant_probabilities": dict(query.query_variant_probabilities),
            "winner_label_probabilities": dict(query.winner_label_probabilities),
            "candidate_label_pool": list(query.candidate_label_pool),
        }
        if rendered_scene.translation_vector is not None:
            query_params["translation_vector"] = [int(rendered_scene.translation_vector[0]), int(rendered_scene.translation_vector[1])]
        if rendered_scene.rotation_mode is not None:
            query_params["rotation_mode"] = str(rendered_scene.rotation_mode)
            query_params["rotation_instruction"] = str(rendered_scene.rotation_prompt_label)

        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_transformation_match",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(query.scene_variant),
                    "query_variant": str(query.query_variant),
                    "winner_label": str(rendered_scene.winner_label),
                    "cue_kind": str(rendered_scene.cue_kind),
                    "task_variant": str(query.query_variant),
                },
            },
            "query_spec": {
                "task_variant": str(query.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_size": int(context.canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "text_style": {
                    "font_size_px": int(label_font_size_px),
                    "stroke_width_px": int(label_stroke_width_scene),
                },
                "graph_coordinate_frame": dict(context.graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
                "scene_variant": str(query.scene_variant),
            },
            "render_map": {
                **dict(rendered_scene.render_map),
                "image_id": "img0",
                "winner_label": str(rendered_scene.winner_label),
            },
            "execution_trace": {
                "scene_variant": str(query.scene_variant),
                "query_variant": str(query.query_variant),
                "task_variant": str(query.query_variant),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "query_variant_probabilities": dict(query.query_variant_probabilities),
                "task_variant_probabilities": dict(query.query_variant_probabilities),
                "winner_label": str(rendered_scene.winner_label),
                "winner_label_probabilities": dict(query.winner_label_probabilities),
                "cue_kind": str(rendered_scene.cue_kind),
                "required_evidence_labels": list(rendered_scene.required_evidence_labels),
                "question_format": "label_choice_no_text_options",
                "rotation_mode": (str(rendered_scene.rotation_mode) if rendered_scene.rotation_mode is not None else None),
                "rotation_instruction": (str(rendered_scene.rotation_prompt_label) if rendered_scene.rotation_prompt_label is not None else None),
                "translation_vector": (
                    [int(rendered_scene.translation_vector[0]), int(rendered_scene.translation_vector[1])]
                    if rendered_scene.translation_vector is not None
                    else None
                ),
            },
            "witness_symbolic": {
                **dict(rendered_scene.evidence["witness_symbolic"]),
                "winner_label": str(rendered_scene.winner_label),
            },
            "projected_evidence": dict(rendered_scene.evidence["projected_evidence"]),
        }

        scene_bonus = 0.08 if str(query.scene_variant) == "quadrilateral" else 0.0
        visual_scan = 0.56 + scene_bonus
        ambiguity = {
            "translation_match": 0.32,
            "reflection_match": 0.45,
            "rotation_match": 0.62,
        }[str(query.query_variant)]
        if str(query.scene_variant) == "quadrilateral":
            ambiguity = min(1.0, float(ambiguity + 0.05))
        complexity = build_geometry_transformation_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            visual_scan=float(visual_scan),
            query_variant=str(query.query_variant),
            scene_variant=str(query.scene_variant),
            ambiguity=float(ambiguity),
            evidence_point_count=len(rendered_scene.required_evidence_labels),
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(query.query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
