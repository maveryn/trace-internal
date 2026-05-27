"""Single-object geometry slope measurement task."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple
from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.background_defaults import POST_IMAGE_BACKGROUND_DEFAULTS
from ..shared.complexity import build_geometry_measurement_complexity, geometry_measurement_output_burden
from ..shared.graph_rendering import graph_paper_grid_from_frame, scale_point
from ..shared.labeled_point_evidence import graph_point_evidence_artifacts
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ..shared.render_variation import sample_int_render_param
from ..shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from ..shared.single_object_scene import (
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)
from ..shared.slope_geometry import (
    graph_unit_bounds_for_canvas,
    has_feasible_slope_on_bounds,
    sample_slope_line_on_graph_paper,
)
from .defaults import MEASUREMENT_SHARED_DEFAULTS

@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for graph-paper slope measurement."""
    canvas_size_min: int = MEASUREMENT_SHARED_DEFAULTS.canvas_size_min
    canvas_size_max: int = MEASUREMENT_SHARED_DEFAULTS.canvas_size_max
    graph_cells_min: int = MEASUREMENT_SHARED_DEFAULTS.graph_cells_min
    graph_cells_max: int = MEASUREMENT_SHARED_DEFAULTS.graph_cells_max
    line_width: int = MEASUREMENT_SHARED_DEFAULTS.line_width
    slope_tenths_min: int = -40
    slope_tenths_max: int = 40

_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", "measurement")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="source_geometry_measurement_slope",
)

def _slope_candidates(*, slope_tenths_min: int, slope_tenths_max: int) -> List[int]:
    """Return sorted non-zero slope candidates in tenths."""
    lo = int(slope_tenths_min)
    hi = int(slope_tenths_max)
    if int(lo) > int(hi):
        raise ValueError("slope_tenths_min must be <= slope_tenths_max")
    candidates = [int(value) for value in range(int(lo), int(hi) + 1) if int(value) != 0]
    if not candidates:
        raise ValueError("slope candidate range must include at least one non-zero value")
    return candidates

def _is_uniform_probability_map(probabilities: Mapping[str, float], *, tol: float = 1e-9) -> bool:
    """Return true when all positive probabilities are approximately equal."""
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if not positives:
        return False
    return max(positives) - min(positives) <= float(tol)

def _resolve_slope_tenths(
    rng,
    *,
    params: Mapping[str, Any],
    candidates: Sequence[int],
) -> Tuple[int, Dict[str, float]]:
    """Resolve slope target in tenths with uniform-by-default weighted sampling."""
    slope_values = [int(value) for value in candidates]
    explicit = params.get("target_slope_tenths")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(slope_values):
            raise ValueError("target_slope_tenths is outside configured slope range")
        return int(selected), {str(value): (1.0 if int(value) == int(selected) else 0.0) for value in slope_values}
    raw_weights = params.get(
        "target_slope_tenths_weights",
        group_default(_GEN_DEFAULTS, "target_slope_tenths_weights", {str(value): 1.0 for value in slope_values}),
    )
    weights: Dict[str, float] = {}
    if isinstance(raw_weights, Mapping):
        slope_set = set(slope_values)
        for key, value in raw_weights.items():
            try:
                parsed = int(str(key))
            except Exception:
                continue
            if int(parsed) in slope_set:
                weights[str(parsed)] = float(value)
    probabilities = normalize_positive_weights(weights, default_keys=[str(value) for value in slope_values])
    selected_key = weighted_choice(rng, probabilities, sort_keys=True)
    return int(selected_key), {str(key): float(value) for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))}

def _resolve_balanced_slope_tenths(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    selected_slope_tenths: int,
    probabilities: Mapping[str, float],
    candidates: Sequence[int],
) -> int:
    """Apply deterministic balance over slope targets when defaults are fully uniform."""
    enabled = bool(params.get("balanced_sampling", group_default(_GEN_DEFAULTS, "balanced_sampling", True)))
    if not bool(enabled):
        return int(selected_slope_tenths)
    if "target_slope_tenths" in params and params.get("target_slope_tenths") is not None:
        return int(selected_slope_tenths)
    if "target_slope_tenths_weights" in params and params.get("target_slope_tenths_weights") is not None:
        return int(selected_slope_tenths)
    if not _is_uniform_probability_map(probabilities):
        return int(selected_slope_tenths)
    ordered = [int(value) for value in sorted({int(value) for value in candidates})]
    if not ordered:
        return int(selected_slope_tenths)
    selected = int(ordered[abs(int(instance_seed)) % len(ordered)])
    return int(selected)

def _measurement_complexity_components(slope_value: float) -> Dict[str, float]:
    """Return normalized measurement complexity components for slope measurement."""
    normalized_abs = min(1.0, abs(float(slope_value)) / 4.0)
    near_horizontal = 1.0 - float(normalized_abs)
    return {
        "visual_scan": 0.38,
        "measurement_precision": min(1.0, 0.34 + (0.46 * float(normalized_abs))),
        "ambiguity": min(1.0, 0.24 + (0.30 * float(near_horizontal))),
    }

class GeometrySlopeMeasureTask:
    """Measure one line slope on graph paper."""
    task_id = "source_geometry_measurement_slope"
    domain = "geometry"
    task_group = "measurement"
    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic slope-measurement instance."""
        scene_rng = spawn_rng(instance_seed, "scene")
        slope_tenths_min = int(
            params.get(
                "slope_tenths_min",
                group_default(_GEN_DEFAULTS, "slope_tenths_min", _DEFAULTS.slope_tenths_min),
            )
        )
        slope_tenths_max = int(
            params.get(
                "slope_tenths_max",
                group_default(_GEN_DEFAULTS, "slope_tenths_max", _DEFAULTS.slope_tenths_max),
            )
        )
        slope_candidates = _slope_candidates(
            slope_tenths_min=int(slope_tenths_min),
            slope_tenths_max=int(slope_tenths_max),
        )
        explicit_target_slope = params.get("target_slope_tenths")
        if explicit_target_slope is not None and int(explicit_target_slope) not in set(slope_candidates):
            raise ValueError("target_slope_tenths is outside configured slope range")
        line_width = sample_int_render_param(
            scene_rng,
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            key="line_width",
            fallback=int(_DEFAULTS.line_width),
            min_key="line_width_min",
            max_key="line_width_max",
            minimum_value=1,
        )
        context_params = dict(params)
        context = None
        image = None
        background_meta = None
        shape_style = None
        sample = None
        selected_slope_tenths = None
        slope_tenths_probabilities: Dict[str, float] = {}
        feasible_slope_candidates: List[int] = []
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
                bounds = graph_unit_bounds_for_canvas(
                    canvas_size=int(context_attempt.canvas_size),
                    graph_origin=(float(context_attempt.graph_origin[0]), float(context_attempt.graph_origin[1])),
                    graph_spacing=int(context_attempt.graph_spacing),
                    outer_margin_px=int(context_attempt.graph_frame.get("outer_margin_px", 0)),
                )
                feasible_for_context = [
                    int(candidate)
                    for candidate in slope_candidates
                    if has_feasible_slope_on_bounds(
                        slope_tenths=int(candidate),
                        bounds=tuple(int(value) for value in bounds),
                    )
                ]
                if not feasible_for_context:
                    raise ValueError("no feasible slope candidates for current graph-paper bounds")
                slope_tenths_attempt, slope_probabilities_attempt = _resolve_slope_tenths(
                    scene_rng,
                    params=params,
                    candidates=feasible_for_context,
                )
                slope_tenths_attempt = _resolve_balanced_slope_tenths(
                    instance_seed=int(instance_seed),
                    params=params,
                    selected_slope_tenths=int(slope_tenths_attempt),
                    probabilities=slope_probabilities_attempt,
                    candidates=feasible_for_context,
                )
                sample_attempt = sample_slope_line_on_graph_paper(
                    scene_rng,
                    canvas_size=int(context_attempt.canvas_size),
                    graph_origin=(float(context_attempt.graph_origin[0]), float(context_attempt.graph_origin[1])),
                    graph_spacing=int(context_attempt.graph_spacing),
                    outer_margin_px=int(context_attempt.graph_frame.get("outer_margin_px", 0)),
                    slope_tenths=int(slope_tenths_attempt),
                )
                draw_attempt.line(
                    [
                        scale_point(sample_attempt.endpoint_a_pixel, int(context_attempt.scene_scale)),
                        scale_point(sample_attempt.endpoint_b_pixel, int(context_attempt.scene_scale)),
                    ],
                    fill=tuple(int(value) for value in shape_style_attempt.line_color),
                    width=max(1, int(line_width) * int(context_attempt.scene_scale)),
                )
                context = context_attempt
                image = image_attempt
                background_meta = background_meta_attempt
                shape_style = shape_style_attempt
                sample = sample_attempt
                selected_slope_tenths = int(slope_tenths_attempt)
                feasible_slope_candidates = [int(value) for value in sorted(set(feasible_for_context))]
                slope_tenths_probabilities = {
                    str(value): (1.0 if int(value) == int(selected_slope_tenths) else 0.0)
                    for value in slope_candidates
                }
                break
            except Exception as exc:
                last_error = exc
                continue
        if (
            context is None
            or image is None
            or background_meta is None
            or shape_style is None
            or sample is None
            or selected_slope_tenths is None
            or not slope_tenths_probabilities
        ):
            raise RuntimeError("failed to generate source_geometry_measurement_slope instance") from last_error
        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
        )
        axis_label = "X"
        evidence = graph_point_evidence_artifacts(
            points_by_label={str(axis_label): sample.axis_crossing_pixel},
            graph_origin=context.graph_origin,
            graph_spacing=int(context.graph_spacing),
            witness_type="x_axis_crossing",
            ordered_labels=[str(axis_label)],
        )
        evidence_value = evidence.get("evidence_value", [])
        if (
            not isinstance(evidence_value, list)
            or len(evidence_value) != 1
            or not isinstance(evidence_value[0], list)
            or len(evidence_value[0]) != 2
            or any(not isinstance(coord, (int, float)) for coord in evidence_value[0])
        ):
            raise RuntimeError("slope evidence must be one pixel point")
        original_evidence_value = [int(sample.axis_crossing_graph[0]), int(sample.axis_crossing_graph[1])]
        if int(original_evidence_value[1]) != 0:
            raise RuntimeError("x-axis crossing evidence must have y=0 in graph units")
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_bundle_id = str(prompt_defaults["bundle_id"])
        prompt_scene_key = str(prompt_defaults["scene_key"])
        prompt_task_key = str(prompt_defaults["task_key"])
        question_text = str(prompt_defaults["question_text"])
        object_description = str(prompt_defaults["object_description"])
        json_output_contract = str(prompt_defaults["json_output_contract"])
        json_output_contract_answer_only = str(prompt_defaults["json_output_contract_answer_only"])
        evidence_hint = str(prompt_defaults["evidence_hint"])
        answer_hint = str(prompt_defaults["answer_hint"])
        json_example = str(prompt_defaults["json_example"])
        json_example_answer_only = str(prompt_defaults["json_example_answer_only"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=prompt_bundle_id,
            scene_key=prompt_scene_key,
            task_key=prompt_task_key,
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "question_text": str(question_text),
                "json_output_contract": str(json_output_contract),
                "json_output_contract_answer_only": str(json_output_contract_answer_only),
                "evidence_hint": str(evidence_hint),
                "answer_hint": str(answer_hint),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        slope_value = float(int(sample.slope_tenths) / 10.0)
        x_min, x_max, y_min, y_max = graph_unit_bounds_for_canvas(
            canvas_size=int(context.canvas_size),
            graph_origin=(float(context.graph_origin[0]), float(context.graph_origin[1])),
            graph_spacing=int(context.graph_spacing),
            outer_margin_px=int(context.graph_frame.get("outer_margin_px", 0)),
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_2d_slope_measurement",
                "entities": [
                    {
                        "entity_id": "line_1",
                        "entity_type": "line",
                        "attrs": {
                            "slope_tenths": int(sample.slope_tenths),
                            "slope_value": float(sample.slope_value),
                            "slope_vector": [int(sample.slope_vector[0]), int(sample.slope_vector[1])],
                            "axis_crossing_graph": [int(sample.axis_crossing_graph[0]), int(sample.axis_crossing_graph[1])],
                            "lattice_point_graph": [int(sample.lattice_point_graph[0]), int(sample.lattice_point_graph[1])],
                            "line_endpoints_graph": [
                                [float(sample.endpoint_a_graph[0]), float(sample.endpoint_a_graph[1])],
                                [float(sample.endpoint_b_graph[0]), float(sample.endpoint_b_graph[1])],
                            ],
                            "line_endpoints_pixel": [
                                [float(sample.endpoint_a_pixel[0]), float(sample.endpoint_a_pixel[1])],
                                [float(sample.endpoint_b_pixel[0]), float(sample.endpoint_b_pixel[1])],
                            ],
                        },
                    }
                ],
                "relations": {},
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
                "query_id": "line_slope",
                "template_id": str(prompt_bundle_id),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "slope_tenths": int(selected_slope_tenths),
                    "slope_tenths_probabilities": dict(slope_tenths_probabilities),
                    "slope_tenths_min": int(slope_tenths_min),
                    "slope_tenths_max": int(slope_tenths_max),
                    "answer_rounding": "one_decimal",
                },
            },
            "render_spec": {
                "canvas_size": int(context.canvas_size),
                "coord_space": "pixel",
                "background_style": dict(background_meta_final),
                "post_image_noise": dict(post_noise_meta),
                "shape_style": dict(shape_style.to_trace_dict()),
                "line_style": {
                    "line_width_px": int(line_width),
                },
                "graph_coordinate_frame": dict(context.graph_frame),
                "graph_paper_grid": graph_paper_grid_from_frame(context.graph_frame),
                **dict(context.graph_layout_metadata),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "target_line": {
                        "point": [float(sample.axis_crossing_pixel[0]), float(sample.axis_crossing_pixel[1])],
                        "polyline": [
                            [float(sample.endpoint_a_pixel[0]), float(sample.endpoint_a_pixel[1])],
                            [float(sample.endpoint_b_pixel[0]), float(sample.endpoint_b_pixel[1])],
                        ],
                        "coord_space": "pixel",
                    }
                },
            },
            "execution_trace": {
                "query_id": "line_slope",
                "answer_value": float(slope_value),
                "slope_tenths": int(sample.slope_tenths),
                "slope_value": float(sample.slope_value),
                "x_axis_crossing_graph": [int(sample.axis_crossing_graph[0]), int(sample.axis_crossing_graph[1])],
                "lattice_point_graph": [int(sample.lattice_point_graph[0]), int(sample.lattice_point_graph[1])],
                "required_evidence_labels": [str(axis_label)],
                "question_format": "numeric_open",
                "feasible_answer_values": [float(int(value) / 10.0) for value in feasible_slope_candidates],
                "query_id_probabilities": {"line_slope": 1.0},
                "graph_unit_bounds": {
                    "x_min": int(x_min),
                    "x_max": int(x_max),
                    "y_min": int(y_min),
                    "y_max": int(y_max),
                },
            },
            "witness_symbolic": dict(evidence["witness_symbolic"]),
            "projected_evidence": dict(evidence["projected_evidence"]),
        }
        complexity_components = _measurement_complexity_components(float(slope_value))
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="number", value=float(slope_value)),
            evidence_gt=TypedValue(type=str(evidence["evidence_type"]), value=evidence_value),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=build_geometry_measurement_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=self.task_id,
                visual_scan=float(complexity_components["visual_scan"]),
                measurement_precision=float(complexity_components["measurement_precision"]),
                ambiguity=float(complexity_components["ambiguity"]),
                output_burden=geometry_measurement_output_burden(
                    answer_format="number",
                    evidence_point_count=1,
                ),
            ),
            task_versions=default_task_versions(),
            query_id="line_slope",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
