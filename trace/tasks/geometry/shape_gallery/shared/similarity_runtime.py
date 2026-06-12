"""Geometry similarity counting task on one shared graph-paper scene."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from trace.core.sampling import normalize_positive_weights, weighted_choice
from trace.core.seed import hash64, spawn_rng
from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.deterministic_sampling import uniform_probability_map
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_json_example import resolve_prompt_json_examples
from trace.tasks.shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from trace.tasks.shared.text_rendering import resolve_scene_label_font_size_px
from trace.tasks.shared.variant_sampling import (
    apply_balanced_variant_sampling,
    has_non_null_param,
    is_uniform_probability_map,
    resolve_variant,
)

SCENE_ID = "shape_gallery"
from trace.tasks.geometry.shared.background_defaults import load_geometry_background_defaults
from trace.tasks.geometry.shared.graph_rendering import graph_paper_grid_from_frame
from trace.tasks.geometry.shared.multi_polygon_scene import PolygonSceneObject, draw_polygon_objects
from trace.tasks.geometry.shared.noise_defaults import load_geometry_noise_defaults
from trace.tasks.geometry.shared.polygon_scene_helpers import (
    draw_reference_polygon,
    graph_polygon_inside_canvas,
    pixel_point_from_graph_units,
    pixel_polygon_from_graph_units,
    polygon_bbox,
)
from trace.tasks.geometry.shared.polygon_transformations import (
    Polygon,
    RIGID_TRANSFORM_RECIPE_IDS,
    apply_rigid_transform_recipe,
    polygons_are_congruent,
    polygons_are_similar,
    sample_asymmetric_polygon_template,
    scale_polygon,
    scale_polygon_non_uniform,
    translate_polygon,
)
from trace.tasks.geometry.shared.render_variation import sample_int_render_param
from trace.tasks.geometry.shared.shape_style import extract_background_anchor_colors, sample_geometry_shape_style
from trace.tasks.geometry.shared.single_object_scene import (
    GraphSceneContext,
    finalize_graph_scene_image,
    make_graph_scene_canvas,
    resolve_graph_scene_context,
)

SCENE_NAMESPACE = "shape_gallery_similarity_count"

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("triangle", "quadrilateral")
SIMILARITY_RELATIONS: Tuple[str, ...] = ("congruent_count", "similar_count")
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "triangle": SIMILARITY_RELATIONS,
    "quadrilateral": SIMILARITY_RELATIONS,
}

POST_IMAGE_BACKGROUND_DEFAULTS = load_geometry_background_defaults(scene_id="similarity")
POST_IMAGE_NOISE_DEFAULTS = load_geometry_noise_defaults(scene_id="similarity")

_RIGID_RECIPES: Tuple[str, ...] = tuple(RIGID_TRANSFORM_RECIPE_IDS)



@dataclass(frozen=True)
class SimilarityCountArtifact:
    """Generated data needed by a public shape relation-count task."""

    prompt: str
    answer_type: str
    answer_value: Any
    annotation_type: str
    annotation_value: Any
    image: Any
    trace_payload: Dict[str, Any]
    task_versions: Dict[str, Any]
    query_id: str
    prompt_variants: Dict[str, Any]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for geometry similarity scenes."""

    canvas_size_min: int = 680
    canvas_size_max: int = 760
    graph_cells_min: int = 40
    graph_cells_max: int = 44
    line_width: int = 4
    line_width_min: int = 3
    line_width_max: int = 5
    label_font_size_min: int = 16
    label_font_size_max: int = 28
    label_stroke_width: int = 1
    label_stroke_width_min: int = 1
    label_stroke_width_max: int = 1
    object_label_offset_px: int = 14
    reference_label_gap_px: int = 20
    cue_line_padding_px: int = 18
    reference_center: Tuple[int, int] = (-11, 1)
    candidate_label_pool: Tuple[str, ...] = ("A", "B", "C", "D", "E")
    candidate_slots: Tuple[Tuple[int, int], ...] = (
        (4, 7),
        (10, 7),
        (16, 7),
        (7, -3),
        (13, -3),
    )
    target_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    similar_scale_support: Tuple[int, ...] = (1, 2)
    distractor_non_uniform_pairs: Tuple[Tuple[int, int], ...] = (
        (2, 1),
        (1, 2),
    )


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved scene/query axes plus target-count support for one instance."""

    scene_variant: str
    query_id: str
    target_count: int
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    candidate_label_pool: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderedSimilarityScene:
    """Task-local scene package with all rendered polygons and trace artifacts."""

    reference_vertices_graph: Polygon
    reference_vertices_px: Polygon
    candidate_vertices_graph_by_label: Dict[str, Polygon]
    candidate_vertices_px_by_label: Dict[str, Polygon]
    candidate_centers_graph_by_label: Dict[str, Tuple[float, float]]
    candidate_centers_px_by_label: Dict[str, Tuple[float, float]]
    candidate_bboxes_px_by_label: Dict[str, List[float]]
    matching_labels: Tuple[str, ...]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]
    object_label_centers: Dict[str, List[float]]


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("geometry", "shape_gallery")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=SCENE_NAMESPACE,
)
_TARGET_COUNT_BALANCE_SALT = 29017


def _full_probability_map(supported: Sequence[str], probabilities: Mapping[str, float]) -> Dict[str, float]:
    """Expand one restricted probability map over the full supported variant domain."""

    positive = {str(key): float(value) for key, value in probabilities.items()}
    return {
        str(key): float(positive.get(str(key), 0.0))
        for key in supported
    }


def _candidate_slot_support(params: Mapping[str, Any]) -> Tuple[Tuple[int, int], ...]:
    """Resolve the candidate slot centers used by the similarity scene."""

    raw_support = params.get("candidate_slots", group_default(_GEN_DEFAULTS, "candidate_slots", _DEFAULTS.candidate_slots))
    slots: List[Tuple[int, int]] = []
    for value in raw_support:
        if not isinstance(value, Sequence) or len(value) != 2:
            raise ValueError("candidate_slots entries must be [x, y] graph-unit pairs")
        slot = (int(value[0]), int(value[1]))
        if slot not in slots:
            slots.append(slot)
    if len(slots) != 5:
        raise ValueError("geometry similarity currently requires exactly five candidate slots")
    return tuple(slots)


def _target_count_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve the supported candidate-match counts for similarity counting."""

    raw_support = params.get(
        "target_count_support",
        group_default(_GEN_DEFAULTS, "target_count_support", _DEFAULTS.target_count_support),
    )
    support = []
    for value in raw_support:
        normalized = int(value)
        if 0 <= normalized <= 5 and normalized not in support:
            support.append(normalized)
    if not support:
        raise ValueError("target_count_support must contain at least one value in 0..5")
    return tuple(sorted(int(value) for value in support))


def _resolve_target_count(
    rng,
    *,
    instance_seed: int,
    scene_variant: str,
    query_id: str,
    params: Mapping[str, Any],
    selection_namespace: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve the supported answer count with deterministic balanced defaults."""

    support = _target_count_support(params)
    explicit = params.get("target_count")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"unsupported target_count: {selected}")
        return int(selected), uniform_probability_map(support, selected=int(selected))

    raw_weights = params.get(
        "target_count_weights",
        {str(value): 1.0 for value in support},
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError("target_count_weights must be a mapping when provided")
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if int(key) in set(support)
    }
    probabilities = normalize_positive_weights(weights, default_keys=[str(value) for value in support])
    selected = int(weighted_choice(rng, probabilities, sort_keys=True))

    balanced_enabled = bool(params.get("balanced_sampling", group_default(_GEN_DEFAULTS, "balanced_sampling", True)))
    overridden = any(has_non_null_param(params, key) for key in ("target_count", "target_count_weights"))
    if bool(balanced_enabled) and (not overridden) and is_uniform_probability_map(probabilities):
        ordered_support = [int(value) for value in support]
        selection_index = abs(int(hash64(int(instance_seed), str(selection_namespace), _TARGET_COUNT_BALANCE_SALT)))
        selected = int(ordered_support[int(selection_index) % len(ordered_support)])
    return int(selected), {
        str(key): float(value)
        for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))
    }


def _decoupled_scene_sampling_params(*, params: Mapping[str, Any], target_count_support: Sequence[int]) -> Mapping[str, Any]:
    """No-op hook for scene-cycling call sites."""

    _ = target_count_support
    return params


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve scene/query axes plus balanced target-count support."""

    axis_rng = spawn_rng(int(instance_seed), f"{SCENE_NAMESPACE}.axes")
    scene_supported = [str(value) for value in SUPPORTED_SCENE_VARIANTS]
    query_supported = [str(value) for value in SIMILARITY_RELATIONS]
    compatibility_map = {
        str(scene): tuple(str(query) for query in queries)
        for scene, queries in COMPATIBILITY.items()
    }
    explicit_scene = params.get("scene_variant")
    explicit_query = params.get("query_id")
    if explicit_scene is not None and str(explicit_scene) not in set(scene_supported):
        raise ValueError(f"unsupported scene_variant: {explicit_scene}")
    if explicit_query is not None and str(explicit_query) not in set(query_supported):
        raise ValueError(f"unsupported query_id: {explicit_query}")

    if explicit_query is None:
        raise ValueError("shape-gallery relation mode must be resolved by the public task")
    query_id = str(explicit_query)
    query_probs = _full_probability_map(query_supported, {query_id: 1.0})

    target_count, target_count_probs = _resolve_target_count(
        axis_rng,
        instance_seed=int(instance_seed),
        scene_variant=str(explicit_scene) if explicit_scene is not None else "",
        query_id=str(query_id),
        params=params,
        selection_namespace=f"{SCENE_NAMESPACE}.target_count.{query_id}",
    )

    if explicit_scene is not None:
        scene_variant = str(explicit_scene)
        if str(query_id) not in set(compatibility_map.get(scene_variant, ())):
            raise ValueError(f"incompatible scene/query combination: {scene_variant} + {query_id}")
        scene_probs = _full_probability_map(scene_supported, {scene_variant: 1.0})
    else:
        allowed_scenes = [
            scene
            for scene in scene_supported
            if str(query_id) in set(compatibility_map.get(scene, ()))
        ]
        selected_scene, restricted_scene_probs = resolve_variant(
            axis_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            supported_variants=allowed_scenes,
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
        )
        scene_sampling_params = _decoupled_scene_sampling_params(
            params=params,
            target_count_support=_target_count_support(params),
        )
        scene_variant = apply_balanced_variant_sampling(
            instance_seed=int(instance_seed),
            params=scene_sampling_params,
            gen_defaults=_GEN_DEFAULTS,
            selected_variant=str(selected_scene),
            variant_probabilities=restricted_scene_probs,
            supported_variants=allowed_scenes,
            balance_flag_key="balanced_scene_variant_sampling",
            explicit_key="scene_variant",
            weights_key="scene_variant_weights",
            sampling_namespace=f"{SCENE_NAMESPACE}.scene_variant.{query_id}.{target_count}",
        )
        scene_probs = _full_probability_map(scene_supported, restricted_scene_probs)

    label_pool = tuple(
        str(label).upper()
        for label in params.get(
            "candidate_label_pool",
            group_default(_GEN_DEFAULTS, "candidate_label_pool", _DEFAULTS.candidate_label_pool),
        )
    )
    if len(label_pool) != 5 or len(set(label_pool)) != 5:
        raise ValueError("geometry similarity requires exactly five unique candidate labels")
    return _ResolvedQuery(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        target_count=int(target_count),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(query_probs),
        target_count_probabilities=dict(target_count_probs),
        candidate_label_pool=tuple(label_pool),
    )


def _candidate_is_match(
    *,
    query_id: str,
    reference_vertices_graph: Sequence[Tuple[float, float]],
    candidate_vertices_graph: Sequence[Tuple[float, float]],
) -> bool:
    """Return whether one candidate satisfies the requested similarity predicate."""

    if str(query_id) == "congruent_count":
        return bool(polygons_are_congruent(reference_vertices_graph, candidate_vertices_graph))
    if str(query_id) == "similar_count":
        return bool(polygons_are_similar(reference_vertices_graph, candidate_vertices_graph))
    raise ValueError(f"unsupported similarity query_id: {query_id}")


def _sample_match_labels(rng, *, label_pool: Sequence[str], target_count: int) -> Tuple[str, ...]:
    """Sample the candidate labels that should satisfy the requested predicate."""

    labels = [str(label) for label in label_pool]
    rng.shuffle(labels)
    return tuple(sorted(labels[: int(target_count)]))


def _build_matching_candidate(
    rng,
    *,
    query_id: str,
    template: Polygon,
    slot_center: Tuple[int, int],
    force_large_scale: bool,
    similar_scale_support: Sequence[int],
) -> Polygon:
    """Build one matching candidate polygon by construction."""

    scale_factor = 1
    if str(query_id) == "similar_count":
        allowed_scales = [int(value) for value in similar_scale_support if int(value) > 0]
        if not allowed_scales:
            raise ValueError("similar_scale_support must be non-empty")
        if bool(force_large_scale) and 2 in allowed_scales:
            scale_factor = 2
        else:
            scale_factor = int(rng.choice(list(allowed_scales)))
    base_vertices = scale_polygon(template, factor=int(scale_factor))
    rigid_recipe = str(rng.choice(list(_RIGID_RECIPES)))
    transformed = apply_rigid_transform_recipe(base_vertices, recipe=str(rigid_recipe))
    return translate_polygon(transformed, dx=int(slot_center[0]), dy=int(slot_center[1]))


def _build_distractor_candidate(
    rng,
    *,
    query_id: str,
    template: Polygon,
    slot_center: Tuple[int, int],
    non_uniform_pairs: Sequence[Tuple[int, int]],
) -> Polygon:
    """Build one distractor candidate polygon."""

    if str(query_id) == "congruent_count" and bool(rng.randint(0, 1)):
        base_vertices = scale_polygon(template, factor=2)
    else:
        scale_x, scale_y = rng.choice(list(non_uniform_pairs))
        base_vertices = scale_polygon_non_uniform(template, scale_x=int(scale_x), scale_y=int(scale_y))
    rigid_recipe = str(rng.choice(list(_RIGID_RECIPES)))
    transformed = apply_rigid_transform_recipe(base_vertices, recipe=str(rigid_recipe))
    return translate_polygon(transformed, dx=int(slot_center[0]), dy=int(slot_center[1]))


def _sample_similarity_scene(
    rng,
    *,
    query: _ResolvedQuery,
    context: GraphSceneContext,
    padding_px: float,
    line_width: int,
    label_font_size_px: int,
    label_stroke_width: int,
    reference_label_gap_px: int,
    object_label_offset_px: float,
    draw,
    shape_style,
    render_canvas_size: int,
    params: Mapping[str, Any],
) -> _RenderedSimilarityScene:
    """Sample and render one full similarity-count scene."""

    template = sample_asymmetric_polygon_template(str(query.scene_variant), rng, profile="compact")
    reference_center = tuple(
        int(value)
        for value in params.get("reference_center", group_default(_GEN_DEFAULTS, "reference_center", _DEFAULTS.reference_center))
    )
    reference_vertices_graph = translate_polygon(template, dx=int(reference_center[0]), dy=int(reference_center[1]))
    if not graph_polygon_inside_canvas(reference_vertices_graph, context=context, padding_px=float(padding_px)):
        raise ValueError("reference polygon fell outside the graph-paper canvas")
    reference_vertices_px = pixel_polygon_from_graph_units(reference_vertices_graph, context=context)

    candidate_slots = _candidate_slot_support(params)
    matching_labels = _sample_match_labels(
        rng,
        label_pool=query.candidate_label_pool,
        target_count=int(query.target_count),
    )
    matching_label_set = set(matching_labels)
    highlight_large_label: str | None = None
    if str(query.query_id) == "similar_count" and matching_labels:
        highlight_large_label = str(rng.choice(list(matching_labels)))

    candidate_vertices_graph_by_label: Dict[str, Polygon] = {}
    candidate_vertices_px_by_label: Dict[str, Polygon] = {}
    candidate_centers_graph_by_label: Dict[str, Tuple[float, float]] = {}
    candidate_centers_px_by_label: Dict[str, Tuple[float, float]] = {}
    candidate_bboxes_px_by_label: Dict[str, List[float]] = {}
    objects: List[PolygonSceneObject] = []
    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": "reference_polygon",
            "entity_type": "reference_polygon",
            "scene_variant": str(query.scene_variant),
            "vertices_graph": [[int(round(point[0])), int(round(point[1]))] for point in reference_vertices_graph],
            "center_graph": [int(reference_center[0]), int(reference_center[1])],
        }
    ]

    similar_scale_support = tuple(
        int(value)
        for value in params.get(
            "similar_scale_support",
            group_default(_GEN_DEFAULTS, "similar_scale_support", _DEFAULTS.similar_scale_support),
        )
    )
    non_uniform_pairs = tuple(
        (int(value[0]), int(value[1]))
        for value in params.get(
            "distractor_non_uniform_pairs",
            group_default(_GEN_DEFAULTS, "distractor_non_uniform_pairs", _DEFAULTS.distractor_non_uniform_pairs),
        )
    )

    for label, slot_center in zip(query.candidate_label_pool, candidate_slots):
        is_match = bool(str(label) in matching_label_set)
        candidate_vertices_graph: Polygon | None = None
        for _ in range(24):
            if is_match:
                candidate_vertices_graph = _build_matching_candidate(
                    rng,
                    query_id=str(query.query_id),
                    template=template,
                    slot_center=slot_center,
                    force_large_scale=bool(str(label) == str(highlight_large_label)),
                    similar_scale_support=similar_scale_support,
                )
                if not _candidate_is_match(
                    query_id=str(query.query_id),
                    reference_vertices_graph=reference_vertices_graph,
                    candidate_vertices_graph=candidate_vertices_graph,
                ):
                    candidate_vertices_graph = None
                    continue
            else:
                candidate_vertices_graph = _build_distractor_candidate(
                    rng,
                    query_id=str(query.query_id),
                    template=template,
                    slot_center=slot_center,
                    non_uniform_pairs=non_uniform_pairs,
                )
                if _candidate_is_match(
                    query_id=str(query.query_id),
                    reference_vertices_graph=reference_vertices_graph,
                    candidate_vertices_graph=candidate_vertices_graph,
                ):
                    candidate_vertices_graph = None
                    continue
            if graph_polygon_inside_canvas(candidate_vertices_graph, context=context, padding_px=float(padding_px)):
                break
            candidate_vertices_graph = None
        if candidate_vertices_graph is None:
            raise ValueError("failed to place a similarity candidate inside the graph-paper canvas")

        candidate_vertices_px = pixel_polygon_from_graph_units(candidate_vertices_graph, context=context)
        candidate_vertices_graph_by_label[str(label)] = tuple(candidate_vertices_graph)
        candidate_vertices_px_by_label[str(label)] = tuple(candidate_vertices_px)
        candidate_centers_graph_by_label[str(label)] = (float(slot_center[0]), float(slot_center[1]))
        candidate_centers_px_by_label[str(label)] = pixel_point_from_graph_units(slot_center, context=context)
        candidate_bboxes_px_by_label[str(label)] = polygon_bbox(candidate_vertices_px)
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
                "matches_query": bool(is_match),
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
        "object_label_centers": dict(object_label_centers),
        "matching_labels": list(matching_labels),
    }

    return _RenderedSimilarityScene(
        reference_vertices_graph=tuple(reference_vertices_graph),
        reference_vertices_px=tuple(reference_vertices_px),
        candidate_vertices_graph_by_label=dict(candidate_vertices_graph_by_label),
        candidate_vertices_px_by_label=dict(candidate_vertices_px_by_label),
        candidate_centers_graph_by_label=dict(candidate_centers_graph_by_label),
        candidate_centers_px_by_label=dict(candidate_centers_px_by_label),
        candidate_bboxes_px_by_label=dict(candidate_bboxes_px_by_label),
        matching_labels=tuple(sorted(matching_labels)),
        scene_entities=list(scene_entities),
        render_map=render_map,
        object_label_centers=dict(object_label_centers),
    )


class SimilarityCountRuntime:
    """Generate shape-gallery relation-count artifacts for one resolved objective."""

    domain = "geometry"

    def generate_artifact(
        self,
        instance_seed: int,
        *,
        params: Dict[str, Any],
        max_attempts: int,
        runtime_namespace: str,
        query_id: str,
    ) -> SimilarityCountArtifact:
        runtime_params = dict(params)
        runtime_params["query_id"] = str(query_id)
        query = _resolve_axes(int(instance_seed), params=runtime_params)
        scene_rng = spawn_rng(int(instance_seed), f"{runtime_namespace}.scene")

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
                instance_seed=int(instance_seed),
                params=runtime_params,
                render_defaults=_RENDER_DEFAULTS,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
                fallback_canvas_min=_DEFAULTS.canvas_size_min,
                fallback_canvas_max=_DEFAULTS.canvas_size_max,
                fallback_cells_min=_DEFAULTS.graph_cells_min,
                fallback_cells_max=_DEFAULTS.graph_cells_max,
            )
            line_width_attempt = sample_int_render_param(
                scene_rng,
                params=runtime_params,
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
                params=runtime_params,
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
                params=runtime_params,
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
                rendered_scene_attempt = _sample_similarity_scene(
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
                    object_label_offset_px=float(
                        params.get(
                            "object_label_offset_px",
                            group_default(_RENDER_DEFAULTS, "object_label_offset_px", _DEFAULTS.object_label_offset_px),
                        )
                    ),
                    draw=draw_attempt,
                    shape_style=shape_style_attempt,
                    render_canvas_size=int(context_attempt.canvas_size) * int(context_attempt.scene_scale),
                    params=runtime_params,
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
            raise RuntimeError(f"failed to generate {runtime_namespace} instance") from last_error

        image, background_meta_final, post_noise_meta = finalize_graph_scene_image(
            image,
            instance_seed=int(instance_seed),
            context=context,
            background_meta=background_meta,
            noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
        )

        annotation_labels = list(rendered_scene.matching_labels)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint_template",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {runtime_namespace}",
        )
        json_example, json_example_answer_only = resolve_prompt_json_examples(
            prompt_defaults,
            annotation_value=[list(rendered_scene.candidate_bboxes_px_by_label[str(label)]) for label in annotation_labels],
            answer_type="integer",
        )
        annotation_hint = str(prompt_defaults["annotation_hint_template"]).format(
            label_count=len(query.candidate_label_pool),
        )
        prompt_selection = render_scene_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(annotation_hint),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value = int(len(annotation_labels))

        annotation_bboxes = [list(rendered_scene.candidate_bboxes_px_by_label[str(label)]) for label in annotation_labels]
        annotation_centers = [list(rendered_scene.candidate_centers_px_by_label[str(label)]) for label in annotation_labels]
        query_params = {
            "scene_variant": str(query.scene_variant),
            "query_id": str(query.query_id),
            "query_id_probabilities": dict(query.query_id_probabilities),
            "scene_variant_probabilities": dict(query.scene_variant_probabilities),
            "target_count": int(query.target_count),
            "target_count_probabilities": dict(query.target_count_probabilities),
            "candidate_label_pool": list(query.candidate_label_pool),
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "geometry_similarity_count",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(query.scene_variant),
                    "matching_labels": list(annotation_labels),
                    "target_count": int(query.target_count),
                    "query_id": str(query.query_id),
                },
            },
            "query_spec": {
                "query_id": str(query.query_id),
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
                "scene_variant": str(query.scene_variant),
            },
            "render_map": {
                **dict(rendered_scene.render_map),
                "image_id": "img0",
            },
            "execution_trace": {
                "scene_variant": str(query.scene_variant),
                "query_id": str(query.query_id),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "target_count": int(query.target_count),
                "target_count_probabilities": dict(query.target_count_probabilities),
                "matching_labels": list(annotation_labels),
                "reference_center_graph": list(group_default(_GEN_DEFAULTS, "reference_center", _DEFAULTS.reference_center)),
                "question_format": "count_matching_labels",
            },
            "witness_symbolic": {
                "type": "geometry_similarity_matching_polygons",
                "source_witness_type": "object_set",
                "original_annotation_value": list(annotation_labels),
                "labels": list(annotation_labels),
                "label_set": list(annotation_labels),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": list(annotation_bboxes),
                "pixel_bbox_set": list(annotation_bboxes),
                "pixel_point_set": list(annotation_centers),
            },
        }


        return SimilarityCountArtifact(
            prompt=str(prompt_artifacts.prompt),
            answer_type="integer",
            answer_value=int(answer_value),
            annotation_type="bbox_set",
            annotation_value=list(annotation_bboxes),
            image=image,
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


