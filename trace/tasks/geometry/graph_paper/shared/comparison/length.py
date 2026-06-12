"""Graph-paper geometry comparison task over multiple labeled line segments."""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple
from PIL import ImageDraw
from ......core.seed import spawn_rng
from ......core.scene_config import get_scene_defaults
from ......core.types import TypedValue
from ..source_output import SourceTaskOutput
from .....shared.comparison_sampling import (
    ComparisonGapMetrics,
    comparison_gap_is_valid,
    compute_comparison_gap_metrics,
)
from .....shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from .....shared.geometry_primitives import Point, point_inside_square_canvas
from .....shared.output_metadata import default_task_versions
from .....shared.prompt_json_example import build_prompt_json_examples
from .....shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from .....shared.text_rendering import (
    draw_text_centered,
    load_font,
    resolve_scene_label_font_size_px,
    resolve_text_label_center,
)
from ....shared.background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from ....shared.graph_rendering import graph_paper_grid_from_frame, scale_point
from ....shared.labeled_point_annotation import graph_point_set_annotation_artifacts
from ....shared.length_geometry import integer_length_vectors
from ....shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ....shared.render_variation import sample_int_render_param
from ....shared.shape_style import (
    GeometryShapeStyle,
    extract_background_anchor_colors,
    sample_geometry_shape_style,
)
from ....shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from .defaults import COMPARISON_SHARED_DEFAULTS
from .shared import (
    COMPARISON_ANSWER_LABEL_POOL,
    COMPARISON_QUERY_TYPES,
    apply_balanced_comparison_axes,
    graph_units_to_pixel,
    resolve_comparison_object_count,
    resolve_comparison_query_type,
    resolve_comparison_winner_label,
    slot_centers_graph_units,
)

@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for length-comparison generation."""
    canvas_size_min: int = COMPARISON_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = COMPARISON_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = COMPARISON_SHARED_DEFAULTS.graph_cells_min
    graph_cells_max: int = COMPARISON_SHARED_DEFAULTS.graph_cells_max
    line_width: int = COMPARISON_SHARED_DEFAULTS.line_width
    label_font_size_min: int = COMPARISON_SHARED_DEFAULTS.label_font_size_min
    label_font_size_max: int = COMPARISON_SHARED_DEFAULTS.label_font_size_max
    label_stroke_width: int = COMPARISON_SHARED_DEFAULTS.label_stroke_width
    object_count_min: int = COMPARISON_SHARED_DEFAULTS.object_count_min
    object_count_max: int = COMPARISON_SHARED_DEFAULTS.object_count_max
    min_normalized_gap: float = COMPARISON_SHARED_DEFAULTS.min_normalized_gap
    object_label_offset_px: float = COMPARISON_SHARED_DEFAULTS.object_label_offset_px
    min_segment_length: int = 2
    max_segment_length: int = 10
    max_abs_vector_component: int = 10
    min_absolute_gap_units: float = 2.0

@dataclass(frozen=True)
class _SegmentObject:
    """One labeled segment object rendered in the comparison scene."""
    label: str
    endpoint_a: Point
    endpoint_b: Point
    length_units: int

@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready scene payload for one multi-segment comparison instance."""
    query_type: str
    object_count: int
    objects: Tuple[_SegmentObject, ...]
    winner_metrics: ComparisonGapMetrics
    winner_label: str
    annotation_points_by_label: Dict[str, Point]
    object_label_centers: Dict[str, List[float]]
    render_anchor: Dict[str, Any]

_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("geometry", "graph_paper")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id="source_geometry_comparison_length",
)

def _length_vectors_by_length(
    *,
    min_segment_length: int,
    max_segment_length: int,
    max_abs_vector_component: int,
) -> Dict[int, List[Tuple[int, int]]]:
    """Group feasible integer-length lattice vectors by segment length."""
    grouped: Dict[int, List[Tuple[int, int]]] = {}
    for dx, dy, length in integer_length_vectors(
        max_abs_component=int(max_abs_vector_component),
        min_edge_length=int(min_segment_length),
        max_edge_length=int(max_segment_length),
    ):
        grouped.setdefault(int(length), []).append((int(dx), int(dy)))
    return grouped

def _sample_target_lengths(
    rng,
    *,
    candidate_lengths: Sequence[int],
    object_count: int,
    query_type: str,
    min_normalized_gap: float,
    min_absolute_gap_units: float,
) -> List[int]:
    """Sample distinct target lengths whose winner gap is visually meaningful."""
    candidates = [int(value) for value in candidate_lengths]
    if len(candidates) < int(object_count):
        raise ValueError("not enough feasible length candidates for requested object_count")
    for _ in range(800):
        selected = [int(value) for value in rng.sample(candidates, int(object_count))]
        if comparison_gap_is_valid(
            [float(value) for value in selected],
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap=float(min_absolute_gap_units),
        ):
            return selected
    raise ValueError("failed to sample comparison lengths with the configured gap rule")

def _segment_points_from_slot(
    slot_units: Tuple[int, int],
    *,
    dx: int,
    dy: int,
    graph_origin: Point,
    graph_spacing: int,
) -> Tuple[Point, Point]:
    """Return pixel-space segment endpoints centered near one slot."""
    base_x = int(slot_units[0]) - int(dx // 2)
    base_y = int(slot_units[1]) - int(dy // 2)
    endpoint_a_units = (int(base_x), int(base_y))
    endpoint_b_units = (int(base_x + dx), int(base_y + dy))
    return (
        graph_units_to_pixel(
            endpoint_a_units,
            graph_origin=(float(graph_origin[0]), float(graph_origin[1])),
            spacing=int(graph_spacing),
        ),
        graph_units_to_pixel(
            endpoint_b_units,
            graph_origin=(float(graph_origin[0]), float(graph_origin[1])),
            spacing=int(graph_spacing),
        ),
    )

def _draw_segment_scene(
    draw: ImageDraw.ImageDraw,
    *,
    objects: Sequence[_SegmentObject],
    scene_scale: int,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    render_canvas_size: int,
    shape_style: GeometryShapeStyle,
) -> Dict[str, List[float]]:
    """Draw all compared segments plus object labels and return label centers."""
    scaled_objects = [
        {
            "label": str(obj.label),
            "endpoint_a": scale_point(obj.endpoint_a, int(scene_scale)),
            "endpoint_b": scale_point(obj.endpoint_b, int(scene_scale)),
            "raw": obj,
        }
        for obj in objects
    ]
    blocked_segments: List[Tuple[Point, Point]] = []
    line_color = tuple(int(value) for value in shape_style.line_color)
    for scaled in scaled_objects:
        endpoint_a = scaled["endpoint_a"]
        endpoint_b = scaled["endpoint_b"]
        draw.line(
            [endpoint_a[0], endpoint_a[1], endpoint_b[0], endpoint_b[1]],
            fill=line_color,
            width=max(1, int(line_width)),
        )
        blocked_segments.append(
            (
                (float(endpoint_a[0]), float(endpoint_a[1])),
                (float(endpoint_b[0]), float(endpoint_b[1])),
            )
        )
    font = load_font(int(label_font_size_px), bold=True)
    occupied_boxes: List[Tuple[float, float, float, float]] = []
    label_centers: Dict[str, List[float]] = {}
    label_offset_scaled = max(
        float(object_label_offset_px) * float(scene_scale),
        0.65 * float(max(8, int(label_font_size_px))),
    )
    line_clearance_px = max(
        6.0,
        0.45 * float(max(8, int(label_font_size_px))),
        1.4 * float(max(1, int(line_width))),
    )
    for scaled in scaled_objects:
        endpoint_a = scaled["endpoint_a"]
        endpoint_b = scaled["endpoint_b"]
        midpoint = (
            0.5 * (float(endpoint_a[0]) + float(endpoint_b[0])),
            0.5 * (float(endpoint_a[1]) + float(endpoint_b[1])),
        )
        dx = float(endpoint_b[0]) - float(endpoint_a[0])
        dy = float(endpoint_b[1]) - float(endpoint_a[1])
        perpendicular = (-float(dy), float(dx))
        if math.hypot(float(perpendicular[0]), float(perpendicular[1])) <= 1e-9:
            perpendicular = (0.0, -1.0)
        center, bbox = resolve_text_label_center(
            draw,
            text=str(scaled["label"]),
            anchor=midpoint,
            base_direction=(float(perpendicular[0]), float(perpendicular[1])),
            offset_px=float(label_offset_scaled),
            font=font,
            blocked_segments=blocked_segments,
            occupied_boxes=occupied_boxes,
            stroke_width=int(label_stroke_width),
            line_clearance_px=float(line_clearance_px),
            canvas_size=int(render_canvas_size),
        )
        draw_text_centered(
            draw,
            text=str(scaled["label"]),
            center=(float(center[0]), float(center[1])),
            font=font,
            fill=tuple(int(value) for value in shape_style.label_color),
            stroke_fill=tuple(int(value) for value in shape_style.label_stroke_color),
            stroke_width=int(label_stroke_width),
        )
        occupied_boxes.append(bbox)
        label_centers[str(scaled["label"])] = [
            float(center[0]) / float(max(1, int(scene_scale))),
            float(center[1]) / float(max(1, int(scene_scale))),
        ]
    return label_centers

def _sample_scene(
    rng,
    *,
    winner_label: str,
    context: GraphSceneContext,
    query_type: str,
    object_count: int,
    min_segment_length: int,
    max_segment_length: int,
    max_abs_vector_component: int,
    min_normalized_gap: float,
    min_absolute_gap_units: float,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    object_label_offset_px: float,
    draw: ImageDraw.ImageDraw,
    shape_style: GeometryShapeStyle,
) -> _ScenePayload:
    """Sample and draw one multi-segment comparison scene."""
    vectors_by_length = _length_vectors_by_length(
        min_segment_length=int(min_segment_length),
        max_segment_length=int(max_segment_length),
        max_abs_vector_component=int(max_abs_vector_component),
    )
    candidate_lengths = [int(value) for value in sorted(vectors_by_length.keys())]
    render_canvas_size = int(context.canvas_size) * int(context.scene_scale)
    endpoint_padding_px = max(3.0, 0.75 * float(context.graph_spacing) * float(context.scene_scale))
    last_error: Exception | None = None
    for _ in range(700):
        labels = [
            str(label)
            for label in COMPARISON_ANSWER_LABEL_POOL
            if str(label) != str(winner_label)
        ]
        rng.shuffle(labels)
        selected_labels = [str(winner_label), *labels[: max(0, int(object_count) - 1)]]
        rng.shuffle(selected_labels)
        slots = slot_centers_graph_units(
            object_count=int(object_count),
            graph_cells=int(context.graph_cells),
            rng=rng,
        )
        sampled_target_lengths = _sample_target_lengths(
            rng,
            candidate_lengths=candidate_lengths,
            object_count=int(object_count),
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap_units=float(min_absolute_gap_units),
        )
        winner_target_length = (
            int(max(sampled_target_lengths))
            if str(query_type) == "largest"
            else int(min(sampled_target_lengths))
        )
        other_target_lengths = [
            int(value) for value in sampled_target_lengths if int(value) != int(winner_target_length)
        ]
        rng.shuffle(other_target_lengths)
        objects: List[_SegmentObject] = []
        try:
            for label, slot_units in zip(selected_labels, slots):
                target_length = (
                    int(winner_target_length)
                    if str(label) == str(winner_label)
                    else int(other_target_lengths.pop())
                )
                candidates = list(vectors_by_length[int(target_length)])
                rng.shuffle(candidates)
                selected_object: _SegmentObject | None = None
                for dx, dy in candidates:
                    endpoint_a, endpoint_b = _segment_points_from_slot(
                        slot_units,
                        dx=int(dx),
                        dy=int(dy),
                        graph_origin=context.graph_origin,
                        graph_spacing=int(context.graph_spacing),
                    )
                    scaled_point_a = scale_point(endpoint_a, int(context.scene_scale))
                    scaled_point_b = scale_point(endpoint_b, int(context.scene_scale))
                    if not (
                        point_inside_square_canvas(
                            scaled_point_a,
                            canvas_size=int(render_canvas_size),
                            padding=float(endpoint_padding_px),
                        )
                        and point_inside_square_canvas(
                            scaled_point_b,
                            canvas_size=int(render_canvas_size),
                            padding=float(endpoint_padding_px),
                        )
                    ):
                        continue
                    selected_object = _SegmentObject(
                        label=str(label),
                        endpoint_a=(float(endpoint_a[0]), float(endpoint_a[1])),
                        endpoint_b=(float(endpoint_b[0]), float(endpoint_b[1])),
                        length_units=int(target_length),
                    )
                    break
                if selected_object is None:
                    raise ValueError(f"no feasible segment geometry for target {target_length}")
                objects.append(selected_object)
        except Exception as exc:
            last_error = exc
            continue
        values = [float(obj.length_units) for obj in objects]
        metrics = compute_comparison_gap_metrics(values, query_type=str(query_type))
        if str(objects[int(metrics.winner_index)].label) != str(winner_label):
            continue
        if not comparison_gap_is_valid(
            values,
            query_type=str(query_type),
            min_normalized_gap=float(min_normalized_gap),
            min_absolute_gap=float(min_absolute_gap_units),
        ):
            continue
        label_centers = _draw_segment_scene(
            draw,
            objects=tuple(objects),
            scene_scale=int(context.scene_scale),
            line_width=int(line_width) * int(context.scene_scale),
            label_font_size_px=int(label_font_size_px),
            label_stroke_width=int(label_stroke_width),
            object_label_offset_px=float(object_label_offset_px),
            render_canvas_size=int(render_canvas_size),
            shape_style=shape_style,
        )
        winner = objects[int(metrics.winner_index)]
        midpoint = (
            0.5 * (float(winner.endpoint_a[0]) + float(winner.endpoint_b[0])),
            0.5 * (float(winner.endpoint_a[1]) + float(winner.endpoint_b[1])),
        )
        return _ScenePayload(
            query_type=str(query_type),
            object_count=int(object_count),
            objects=tuple(objects),
            winner_metrics=metrics,
            winner_label=str(winner.label),
            annotation_points_by_label={
                "endpoint_a": (float(winner.endpoint_a[0]), float(winner.endpoint_a[1])),
                "endpoint_b": (float(winner.endpoint_b[0]), float(winner.endpoint_b[1])),
            },
            object_label_centers=label_centers,
            render_anchor={
                "winner_label": str(winner.label),
                "winner_midpoint": [float(midpoint[0]), float(midpoint[1])],
                "winner_segment": [
                    [float(winner.endpoint_a[0]), float(winner.endpoint_a[1])],
                    [float(winner.endpoint_b[0]), float(winner.endpoint_b[1])],
                ],
            },
        )
    raise RuntimeError("failed to sample length-comparison scene") from last_error

class GeometryComparisonLengthTask:
    """Compare multiple labeled segments and choose the longest/shortest one."""
    task_id = "source_geometry_comparison_length"
    domain = "geometry"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> SourceTaskOutput:
        """Generate one deterministic multi-segment comparison instance."""
        scene_rng = spawn_rng(int(instance_seed), "scene")
        query_type, query_type_probabilities = resolve_comparison_query_type(
            scene_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
        )
        object_count, object_count_probabilities = resolve_comparison_object_count(
            scene_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            fallback_min=_DEFAULTS.object_count_min,
            fallback_max=_DEFAULTS.object_count_max,
        )
        winner_label, winner_label_probabilities = resolve_comparison_winner_label(
            scene_rng,
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            label_pool=COMPARISON_ANSWER_LABEL_POOL,
        )
        query_type, query_type_probabilities, object_count, object_count_probabilities = apply_balanced_comparison_axes(
            instance_seed=int(instance_seed),
            params=params,
            query_type=str(query_type),
            query_type_probabilities=query_type_probabilities,
            object_count=int(object_count),
            object_count_probabilities=object_count_probabilities,
            query_types=COMPARISON_QUERY_TYPES,
        )
        min_segment_length = int(
            params.get(
                "min_segment_length",
                group_default(_GEN_DEFAULTS, "min_segment_length", _DEFAULTS.min_segment_length),
            )
        )
        max_segment_length = int(
            params.get(
                "max_segment_length",
                group_default(_GEN_DEFAULTS, "max_segment_length", _DEFAULTS.max_segment_length),
            )
        )
        max_abs_vector_component = int(
            params.get(
                "max_abs_vector_component",
                group_default(
                    _GEN_DEFAULTS,
                    "max_abs_vector_component",
                    _DEFAULTS.max_abs_vector_component,
                ),
            )
        )
        min_normalized_gap = float(
            params.get(
                "min_normalized_gap",
                group_default(_GEN_DEFAULTS, "min_normalized_gap", _DEFAULTS.min_normalized_gap),
            )
        )
        min_absolute_gap_units = float(
            params.get(
                "min_absolute_gap_units",
                group_default(_GEN_DEFAULTS, "min_absolute_gap_units", _DEFAULTS.min_absolute_gap_units),
            )
        )
        if int(min_segment_length) >= int(max_segment_length):
            raise ValueError("min_segment_length must be < max_segment_length for comparison length task")
        if int(max_abs_vector_component) <= 0:
            raise ValueError("max_abs_vector_component must be > 0")
        if float(min_normalized_gap) < 0.0:
            raise ValueError("min_normalized_gap must be >= 0")
        if float(min_absolute_gap_units) < 0.0:
            raise ValueError("min_absolute_gap_units must be >= 0")
        context_params = dict(params)
        context = None
        image = None
        background_meta = None
        shape_style = None
        label_font_size_px = None
        label_stroke_width_scene = None
        line_width = None
        scene_payload: _ScenePayload | None = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            context_attempt = resolve_graph_scene_context(
                scene_rng,
                instance_seed=int(instance_seed),
                params=context_params,
                render_defaults=_RENDER_DEFAULTS,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
                fallback_canvas_min=_DEFAULTS.canvas_size_min,
                fallback_canvas_max=_DEFAULTS.canvas_size_max,
                fallback_cells_min=_DEFAULTS.graph_cells_min,
                fallback_cells_max=_DEFAULTS.graph_cells_max,
            )
            line_width_attempt = sample_int_render_param(
                scene_rng,
                params=context_params,
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
                        min_px=int(
                            group_default(
                                _RENDER_DEFAULTS,
                                "label_font_size_min",
                                _DEFAULTS.label_font_size_min,
                            )
                        ),
                        max_px=int(
                            group_default(
                                _RENDER_DEFAULTS,
                                "label_font_size_max",
                                _DEFAULTS.label_font_size_max,
                            )
                        ),
                    ),
                )
            )
            if int(label_font_size_px_attempt) < 6:
                raise ValueError("label_font_size_px must be >= 6")
            label_stroke_width_attempt = sample_int_render_param(
                scene_rng,
                params=context_params,
                render_defaults=_RENDER_DEFAULTS,
                key="label_stroke_width",
                fallback=_DEFAULTS.label_stroke_width,
                minimum_value=1,
            )
            label_stroke_width_scene_attempt = int(
                max(1, int(label_stroke_width_attempt) * int(context_attempt.scene_scale))
            )
            object_label_offset_px = float(
                context_params.get(
                    "object_label_offset_px",
                    group_default(_RENDER_DEFAULTS, "object_label_offset_px", _DEFAULTS.object_label_offset_px),
                )
            )
            image_attempt, draw_attempt, background_meta_attempt = make_graph_scene_canvas(
                instance_seed=int(instance_seed),
                context=context_attempt,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            shape_style_attempt = sample_geometry_shape_style(
                scene_rng,
                params=context_params,
                render_defaults=_RENDER_DEFAULTS,
                anchor_colors=extract_background_anchor_colors(background_meta_attempt),
            )
            try:
                scene_payload_attempt = _sample_scene(
                    scene_rng,
                    winner_label=str(winner_label),
                    context=context_attempt,
                    query_type=str(query_type),
                    object_count=int(object_count),
                    min_segment_length=int(min_segment_length),
                    max_segment_length=int(max_segment_length),
                    max_abs_vector_component=int(max_abs_vector_component),
                    min_normalized_gap=float(min_normalized_gap),
                    min_absolute_gap_units=float(min_absolute_gap_units),
                    line_width=int(line_width_attempt),
                    label_font_size_px=int(label_font_size_px_attempt),
                    label_stroke_width=int(label_stroke_width_scene_attempt),
                    object_label_offset_px=float(object_label_offset_px),
                    draw=draw_attempt,
                    shape_style=shape_style_attempt,
                )
                context = context_attempt
                image = image_attempt
                background_meta = background_meta_attempt
                shape_style = shape_style_attempt
                label_font_size_px = int(label_font_size_px_attempt)
                label_stroke_width_scene = int(label_stroke_width_scene_attempt)
                line_width = int(line_width_attempt)
                scene_payload = scene_payload_attempt
                break
            except Exception as exc:
                last_error = exc
                continue
        if (
            scene_payload is None
            or context is None
            or image is None
            or background_meta is None
            or shape_style is None
            or label_font_size_px is None
            or label_stroke_width_scene is None
            or line_width is None
        ):
            raise RuntimeError("failed to generate source_geometry_comparison_length instance") from last_error
        annotation = graph_point_set_annotation_artifacts(
            points_by_label=scene_payload.annotation_points_by_label,
            graph_origin=context.graph_origin,
            graph_spacing=int(context.graph_spacing),
            witness_type="winning_segment_endpoints",
            ordered_labels=("endpoint_a", "endpoint_b"),
        )
        annotation_value = annotation.get("annotation_value", [])
        if (
            not isinstance(annotation_value, list)
            or len(annotation_value) != 2
            or any(not isinstance(point, list) or len(point) != 2 for point in annotation_value)
            or any(not isinstance(coord, (int, float)) for point in annotation_value for coord in point)
        ):
            raise RuntimeError("comparison-length annotation must include two pixel points")
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
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text_largest",
                "question_text_smallest",
                "annotation_hint",
                "answer_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_text_key = "question_text_largest" if str(query_type) == "largest" else "question_text_smallest"
        question_text = str(prompt_defaults[str(question_text_key)])
        json_example, json_example_answer_only = build_prompt_json_examples(
            annotation_value=annotation_value,
            answer_type="option_letter",
        )
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=str(getattr(self, "scene_id", "") or getattr(self, "public_scene_id", "") or globals().get("SCENE_ID", "")),
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(question_text),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        winner_label = str(scene_payload.winner_label)
        answer_gt = TypedValue(type="option_letter", value=str(winner_label))
        annotation_gt = TypedValue(type=str(annotation["annotation_type"]), value=list(annotation_value))
        values_by_label = {
            str(obj.label): int(obj.length_units)
            for obj in scene_payload.objects
        }
        query_params = {
            "query_type": str(query_type),
            "query_type_probabilities": dict(query_type_probabilities),
            "object_count": int(object_count),
            "object_count_probabilities": dict(object_count_probabilities),
            "winner_label": str(winner_label),
            "winner_label_probabilities": dict(winner_label_probabilities),
            "min_segment_length": int(min_segment_length),
            "max_segment_length": int(max_segment_length),
            "max_abs_vector_component": int(max_abs_vector_component),
            "min_normalized_gap": float(min_normalized_gap),
            "min_absolute_gap_units": float(min_absolute_gap_units),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_2d_length_comparison",
                "entities": [
                    {
                        "entity_id": f"segment_{str(obj.label)}",
                        "entity_type": "segment",
                        "attrs": {
                            "label": str(obj.label),
                            "length_units": int(obj.length_units),
                            "points": {
                                "endpoint_a": [float(obj.endpoint_a[0]), float(obj.endpoint_a[1])],
                                "endpoint_b": [float(obj.endpoint_b[0]), float(obj.endpoint_b[1])],
                            },
                        },
                    }
                    for obj in scene_payload.objects
                ],
                "relations": {
                    "comparison_target": "segment_length",
                    "query_type": str(query_type),
                    "winner_label": str(winner_label),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "graph_unit": {
                        "origin_pixel": list(context.graph_frame["origin_pixel"]),
                        "spacing_px": int(context.graph_frame["spacing_px"]),
                        "x_positive": str(context.graph_frame["x_positive"]),
                        "y_positive": str(context.graph_frame["y_positive"]),
                    },
                },
            },
            "query_spec": {
                "query_id": "segment_set",
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
                **dict(context.graph_layout_metadata),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {"winner": dict(scene_payload.render_anchor)},
                "object_label_centers": dict(scene_payload.object_label_centers),
            },
            "execution_trace": {
                "scene_variant": "segment_set",
                "query_type": str(query_type),
                "query_type_probabilities": dict(query_type_probabilities),
                "object_count": int(object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "winner_label_target": str(winner_label),
                "winner_label_probabilities": dict(winner_label_probabilities),
                "object_labels": [str(obj.label) for obj in scene_payload.objects],
                "values_by_label": dict(values_by_label),
                "winner_label": str(winner_label),
                "winner_value": float(scene_payload.winner_metrics.winner_value),
                "runner_up_value": float(scene_payload.winner_metrics.runner_up_value),
                "winner_gap_abs": float(scene_payload.winner_metrics.gap_abs),
                "winner_gap_normalized": float(scene_payload.winner_metrics.gap_normalized),
                "required_annotation_labels": ["endpoint_a", "endpoint_b"],
                "question_format": "label_choice_no_text_options",
            },
            "witness_symbolic": {
                **dict(annotation["witness_symbolic"]),
                "winner_label": str(winner_label),
            },
            "projected_annotation": dict(annotation["projected_annotation"]),
        }
        return SourceTaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id="segment_set",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
