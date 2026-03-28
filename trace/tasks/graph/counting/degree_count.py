"""Count labeled graph nodes with a specified degree."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import (
    build_graph_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.graph_sampling import (
    SUPPORTED_LABEL_VARIANTS,
    SUPPORTED_LAYOUT_VARIANTS,
    SUPPORTED_TOPOLOGY_PROFILES,
    feasible_node_counts_for_degree_count,
    graph_label_sort_key,
    sample_degree_count_graph,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    SUPPORTED_NODE_SHAPE_VARIANTS,
    render_graph_scene,
)
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES, build_graph_named_color_theme
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph_counting_degree_count"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for graph degree-count scenes."""

    node_count_min: int = 5
    node_count_max: int = 10
    query_degree_min: int = 0
    query_degree_max: int = 4
    target_count_min: int = 0
    target_count_max: int = 5
    degree_sequence_max_degree: int = 5
    graph_search_attempts: int = 600
    canvas_width: int = 864
    canvas_height: int = 640
    outer_margin_px: int = 28
    panel_padding_px: int = 24
    panel_corner_radius_px: int = 20
    panel_title_font_size_px: int = 24
    node_shape_variant: str = "circle"
    node_radius_min_px: int = 18
    node_radius_max_px: int = 24
    edge_width_px: int = 4
    node_border_width_px: int = 2
    label_font_size_px: int = 20
    label_variant: str = "letters"
    layout_transform_variant: str = "identity"
    node_color_name: str = "blue"
    background_color_rgb: Tuple[int, int, int] = (247, 248, 251)
    panel_fill_rgb: Tuple[int, int, int] = (255, 255, 255)
    panel_border_rgb: Tuple[int, int, int] = (205, 212, 224)
    title_color_rgb: Tuple[int, int, int] = (70, 78, 96)
    edge_color_rgb: Tuple[int, int, int] = (118, 128, 145)
    node_fill_rgb: Tuple[int, int, int] = (92, 124, 250)
    node_border_rgb: Tuple[int, int, int] = (52, 73, 144)
    label_text_rgb: Tuple[int, int, int] = (255, 255, 255)
    label_stroke_rgb: Tuple[int, int, int] = (52, 73, 144)


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved graph-query support for one degree-count instance."""

    node_count: int
    query_degree: int
    target_count: int
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    node_color_name: str
    node_count_probabilities: Dict[str, float]
    query_degree_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    topology_profile_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="counting")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="counting", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _resolve_named_variant(
    rng,
    *,
    params: Mapping[str, Any],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
    instance_seed: int,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named variant axis for the graph task."""

    selected_variant, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    variant = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected_variant),
        variant_probabilities=probabilities,
        supported_variants=supported,
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{TASK_ID}:{str(namespace)}",
    )
    return str(variant), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve balanced node-count / degree-query support for one instance."""

    node_count_min = int(params.get("node_count_min", group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max = int(params.get("node_count_max", group_default(_GEN_DEFAULTS, "node_count_max", _DEFAULTS.node_count_max)))
    query_degree_min = int(
        params.get("query_degree_min", group_default(_GEN_DEFAULTS, "query_degree_min", _DEFAULTS.query_degree_min))
    )
    query_degree_max = int(
        params.get("query_degree_max", group_default(_GEN_DEFAULTS, "query_degree_max", _DEFAULTS.query_degree_max))
    )
    target_count_min = int(
        params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min))
    )
    target_count_max = int(
        params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max))
    )
    max_degree = int(
        params.get("degree_sequence_max_degree", group_default(_GEN_DEFAULTS, "degree_sequence_max_degree", _DEFAULTS.degree_sequence_max_degree))
    )

    target_support = tuple(range(int(target_count_min), int(target_count_max) + 1))
    degree_support = tuple(range(int(query_degree_min), int(query_degree_max) + 1))
    if not target_support:
        raise ValueError("target_count support is empty for graph degree counting")
    if not degree_support:
        raise ValueError("query_degree support is empty for graph degree counting")

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:query_support",
        )
    )
    explicit_target = params.get("target_count")
    if explicit_target is not None:
        target_count = int(explicit_target)
    else:
        target_count = int(target_support[int(selection_index % len(target_support))])
    if target_count not in target_support:
        raise ValueError("target_count is outside configured support")

    explicit_query_degree = params.get("query_degree")
    degree_index = int(selection_index // len(target_support))
    if explicit_query_degree is not None:
        query_degree = int(explicit_query_degree)
    else:
        query_degree = int(degree_support[int(degree_index % len(degree_support))])
    if query_degree not in degree_support:
        raise ValueError("query_degree is outside configured support")

    feasible_node_support = feasible_node_counts_for_degree_count(
        query_degree=int(query_degree),
        target_count=int(target_count),
        node_count_min=int(node_count_min),
        node_count_max=int(node_count_max),
        max_degree=int(max_degree),
    )
    if not feasible_node_support:
        raise ValueError("no feasible node counts exist for the configured graph degree-count support")
    explicit_node_count = params.get("node_count")
    node_index = int(degree_index // len(degree_support))
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
    else:
        node_count = int(feasible_node_support[int(node_index % len(feasible_node_support))])
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested graph degree-count query")

    topology_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.topology_profile")
    topology_profile, topology_probabilities = _resolve_named_variant(
        topology_rng,
        params=params,
        explicit_key="topology_profile",
        weights_key="topology_profile_weights",
        balance_flag_key="balanced_topology_profile_sampling",
        supported=SUPPORTED_TOPOLOGY_PROFILES,
        instance_seed=int(instance_seed),
        namespace="topology_profile",
    )
    layout_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.layout_variant")
    layout_variant, layout_probabilities = _resolve_named_variant(
        layout_rng,
        params=params,
        explicit_key="layout_variant",
        weights_key="layout_variant_weights",
        balance_flag_key="balanced_layout_variant_sampling",
        supported=SUPPORTED_LAYOUT_VARIANTS,
        instance_seed=int(instance_seed),
        namespace="layout_variant",
    )
    label_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.label_variant")
    label_variant, label_variant_probabilities = _resolve_named_variant(
        label_rng,
        params=params,
        explicit_key="label_variant",
        weights_key="label_variant_weights",
        balance_flag_key="balanced_label_variant_sampling",
        supported=SUPPORTED_LABEL_VARIANTS,
        instance_seed=int(instance_seed),
        namespace="label_variant",
    )
    shape_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_shape_variant")
    node_shape_variant, node_shape_variant_probabilities = _resolve_named_variant(
        shape_rng,
        params=params,
        explicit_key="node_shape_variant",
        weights_key="node_shape_variant_weights",
        balance_flag_key="balanced_node_shape_variant_sampling",
        supported=SUPPORTED_NODE_SHAPE_VARIANTS,
        instance_seed=int(instance_seed),
        namespace="node_shape_variant",
    )
    transform_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.layout_transform_variant")
    layout_transform_variant, layout_transform_variant_probabilities = _resolve_named_variant(
        transform_rng,
        params=params,
        explicit_key="layout_transform_variant",
        weights_key="layout_transform_variant_weights",
        balance_flag_key="balanced_layout_transform_variant_sampling",
        supported=SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
        instance_seed=int(instance_seed),
        namespace="layout_transform_variant",
    )
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_color_name")
    node_color_name, node_color_name_probabilities = _resolve_named_variant(
        color_rng,
        params=params,
        explicit_key="node_color_name",
        weights_key="node_color_name_weights",
        balance_flag_key="balanced_node_color_name_sampling",
        supported=SUPPORTED_NODE_COLOR_NAMES,
        instance_seed=int(instance_seed),
        namespace="node_color_name",
    )

    return _ResolvedQuery(
        node_count=int(node_count),
        query_degree=int(query_degree),
        target_count=int(target_count),
        topology_profile=str(topology_profile),
        layout_variant=str(layout_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        layout_transform_variant=str(layout_transform_variant),
        node_color_name=str(node_color_name),
        node_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_node_support),
                selected=int(node_count) if explicit_node_count is not None else None,
            )
        ),
        query_degree_probabilities=dict(
            uniform_probability_map(tuple(int(value) for value in degree_support), selected=int(query_degree) if explicit_query_degree is not None else None)
        ),
        target_count_probabilities=dict(
            uniform_probability_map(tuple(int(value) for value in target_support), selected=int(target_count) if explicit_target is not None else None)
        ),
        topology_profile_probabilities=dict(topology_probabilities),
        layout_variant_probabilities=dict(layout_probabilities),
        label_variant_probabilities=dict(label_variant_probabilities),
        node_shape_variant_probabilities=dict(node_shape_variant_probabilities),
        layout_transform_variant_probabilities=dict(layout_transform_variant_probabilities),
        node_color_name_probabilities=dict(node_color_name_probabilities),
    )


def _resolve_render_params(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    node_color_name: str,
    node_shape_variant: str,
) -> GraphRenderParams:
    """Resolve one concrete graph render-parameter set for this instance."""

    radius_min = int(params.get("node_radius_min_px", group_default(_RENDER_DEFAULTS, "node_radius_min_px", _DEFAULTS.node_radius_min_px)))
    radius_max = int(params.get("node_radius_max_px", group_default(_RENDER_DEFAULTS, "node_radius_max_px", _DEFAULTS.node_radius_max_px)))
    render_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.render")
    node_radius = int(render_rng.randint(int(radius_min), int(max(radius_min, radius_max))))
    try:
        color_theme = build_graph_named_color_theme(str(node_color_name))
    except Exception:
        color_theme = None
    return GraphRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        outer_margin_px=int(params.get("outer_margin_px", group_default(_RENDER_DEFAULTS, "outer_margin_px", _DEFAULTS.outer_margin_px))),
        panel_padding_px=int(params.get("panel_padding_px", group_default(_RENDER_DEFAULTS, "panel_padding_px", _DEFAULTS.panel_padding_px))),
        panel_corner_radius_px=int(
            params.get("panel_corner_radius_px", group_default(_RENDER_DEFAULTS, "panel_corner_radius_px", _DEFAULTS.panel_corner_radius_px))
        ),
        panel_title_font_size_px=int(
            params.get(
                "panel_title_font_size_px",
                group_default(_RENDER_DEFAULTS, "panel_title_font_size_px", _DEFAULTS.panel_title_font_size_px),
            )
        ),
        node_shape_variant=str(node_shape_variant),
        node_radius_px=int(node_radius),
        edge_width_px=int(params.get("edge_width_px", group_default(_RENDER_DEFAULTS, "edge_width_px", _DEFAULTS.edge_width_px))),
        node_border_width_px=int(
            params.get("node_border_width_px", group_default(_RENDER_DEFAULTS, "node_border_width_px", _DEFAULTS.node_border_width_px))
        ),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
        background_color_rgb=tuple(
            int(value) for value in (
                color_theme.background_color_rgb
                if color_theme is not None
                else params.get("background_color_rgb", group_default(_RENDER_DEFAULTS, "background_color_rgb", _DEFAULTS.background_color_rgb))
            )
        ),
        panel_fill_rgb=tuple(
            int(value) for value in (
                color_theme.panel_fill_rgb
                if color_theme is not None
                else params.get("panel_fill_rgb", group_default(_RENDER_DEFAULTS, "panel_fill_rgb", _DEFAULTS.panel_fill_rgb))
            )
        ),
        panel_border_rgb=tuple(
            int(value) for value in (
                color_theme.panel_border_rgb
                if color_theme is not None
                else params.get("panel_border_rgb", group_default(_RENDER_DEFAULTS, "panel_border_rgb", _DEFAULTS.panel_border_rgb))
            )
        ),
        title_color_rgb=tuple(
            int(value) for value in (
                color_theme.title_color_rgb
                if color_theme is not None
                else params.get("title_color_rgb", group_default(_RENDER_DEFAULTS, "title_color_rgb", _DEFAULTS.title_color_rgb))
            )
        ),
        edge_color_rgb=tuple(
            int(value) for value in (
                color_theme.edge_color_rgb
                if color_theme is not None
                else params.get("edge_color_rgb", group_default(_RENDER_DEFAULTS, "edge_color_rgb", _DEFAULTS.edge_color_rgb))
            )
        ),
        node_fill_rgb=tuple(
            int(value) for value in (
                color_theme.node_fill_rgb
                if color_theme is not None
                else params.get("node_fill_rgb", group_default(_RENDER_DEFAULTS, "node_fill_rgb", _DEFAULTS.node_fill_rgb))
            )
        ),
        node_border_rgb=tuple(
            int(value) for value in (
                color_theme.node_border_rgb
                if color_theme is not None
                else params.get("node_border_rgb", group_default(_RENDER_DEFAULTS, "node_border_rgb", _DEFAULTS.node_border_rgb))
            )
        ),
        label_text_rgb=tuple(
            int(value) for value in (
                color_theme.label_text_rgb
                if color_theme is not None
                else params.get("label_text_rgb", group_default(_RENDER_DEFAULTS, "label_text_rgb", _DEFAULTS.label_text_rgb))
            )
        ),
        label_stroke_rgb=tuple(
            int(value) for value in (
                color_theme.label_stroke_rgb
                if color_theme is not None
                else params.get("label_stroke_rgb", group_default(_RENDER_DEFAULTS, "label_stroke_rgb", _DEFAULTS.label_stroke_rgb))
            )
        ),
    )


def _build_complexity(
    *,
    graph_sample,
    query: _ResolvedQuery,
    render_params: GraphRenderParams,
    rendered_scene,
) -> Any:
    """Build one within-task normalized complexity record."""

    node_count = int(query.node_count)
    edge_count = int(graph_sample.edge_count)
    max_edges = int(node_count * (node_count - 1) // 2)
    degree_support = (group_default(_GEN_DEFAULTS, "query_degree_min", _DEFAULTS.query_degree_min), group_default(_GEN_DEFAULTS, "query_degree_max", _DEFAULTS.query_degree_max))
    degree_values = list(int(value) for value in graph_sample.degrees_by_label.values())
    near_miss_count = sum(1 for degree in degree_values if abs(int(degree) - int(query.query_degree)) == 1)
    edge_density = 0.0 if int(max_edges) <= 0 else float(edge_count) / float(max_edges)
    crossing_norm = normalize_float_with_bounds(float(rendered_scene.crossing_count), (0.0, max(1.0, float(max_edges))))

    components = {
        "visual_scan": (0.6 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max)))
        + (0.4 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0))),
        "topology_reasoning": (0.7 * normalize_int_with_bounds(int(query.query_degree), degree_support))
        + (0.3 * normalize_int_with_bounds(len(set(degree_values)), (1, min(node_count, _DEFAULTS.degree_sequence_max_degree + 1)))),
        "ambiguity": (0.6 * normalize_int_with_bounds(int(near_miss_count), (0, int(node_count))))
        + (0.4 * normalize_int_with_bounds(int(query.target_count), (_DEFAULTS.target_count_min, _DEFAULTS.target_count_max))),
        "clutter": (0.55 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.25 * crossing_norm)
        + (0.20 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px))),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


@register_task
class GraphCountingDegreeCountTask:
    """Count graph nodes that have one specified degree."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic graph degree-count instance."""

        query = _resolve_query(int(instance_seed), params=params)
        render_params = _resolve_render_params(
            params,
            instance_seed=int(instance_seed),
            node_color_name=str(query.node_color_name),
            node_shape_variant=str(query.node_shape_variant),
        )
        max_degree = int(
            params.get("degree_sequence_max_degree", group_default(_GEN_DEFAULTS, "degree_sequence_max_degree", _DEFAULTS.degree_sequence_max_degree))
        )
        search_attempts = int(params.get("graph_search_attempts", group_default(_GEN_DEFAULTS, "graph_search_attempts", _DEFAULTS.graph_search_attempts)))

        graph_rng = spawn_rng(int(instance_seed), "graph_structure")
        last_error: Exception | None = None
        graph_sample = None
        rendered_scene = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                graph_sample = sample_degree_count_graph(
                    graph_rng,
                    node_count=int(query.node_count),
                    query_degree=int(query.query_degree),
                    target_count=int(query.target_count),
                    max_degree=int(max_degree),
                    topology_profile=str(query.topology_profile),
                    label_variant=str(query.label_variant),
                    search_attempts=max(100, int(search_attempts) // max(1, int(max_attempts)) + 100),
                )
                background, background_meta = make_background_canvas(
                    canvas_width=int(render_params.canvas_width),
                    canvas_height=int(render_params.canvas_height),
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
                )
                rendered_scene = render_graph_scene(
                    graph_sample=graph_sample,
                    layout_variant=str(query.layout_variant),
                    layout_transform_variant=str(query.layout_transform_variant),
                    render_params=render_params,
                    layout_seed=int(instance_seed + attempt),
                    scene_title="Graph",
                    base_image=background,
                )
                image, post_noise_meta = apply_post_image_noise(
                    rendered_scene.image,
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_NOISE_DEFAULTS,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through retry loop
                last_error = exc
                continue
        else:
            raise RuntimeError("failed to generate task_graph_counting_degree_count instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
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
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text"]).format(query_degree=int(query.query_degree)),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_labels = tuple(sorted((str(label) for label in graph_sample.target_labels), key=graph_label_sort_key))
        answer_gt = TypedValue(type="integer", value=int(len(evidence_labels)))
        evidence_gt = TypedValue(type="label_set", value=list(evidence_labels))
        node_entities = [
            {
                "entity_id": f"node_{node.label}",
                "entity_kind": "graph_node",
                "label": str(node.label),
                "degree": int(node.degree),
                "neighbors": list(node.neighbors),
                "center_px": list(node.center_xy),
                "bbox_xyxy": list(node.bbox_xyxy),
            }
            for node in rendered_scene.nodes
        ]
        edge_entities = [
            {
                "entity_id": str(edge.edge_id),
                "entity_kind": "graph_edge",
                "node_u_label": str(edge.node_u_label),
                "node_v_label": str(edge.node_v_label),
                "segment_px": [list(edge.segment_px[0]), list(edge.segment_px[1])],
            }
            for edge in rendered_scene.edges
        ]
        evidence_node_bboxes = [
            list(next(node.bbox_xyxy for node in rendered_scene.nodes if str(node.label) == str(label)))
            for label in evidence_labels
        ]
        evidence_node_centers = [
            list(next(node.center_xy for node in rendered_scene.nodes if str(node.label) == str(label)))
            for label in evidence_labels
        ]
        complexity = _build_complexity(
            graph_sample=graph_sample,
            query=query,
            render_params=render_params,
            rendered_scene=rendered_scene,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "graph_degree_counting",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "counting_rule": "node_degree_equals_query_degree",
                    "query_degree": int(query.query_degree),
                    "matching_labels": list(evidence_labels),
                    "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                    "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                    "edge_labels": [list(edge) for edge in graph_sample.edge_labels],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                "task_variant": "degree_count",
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "query_degree": int(query.query_degree),
                    "target_count": int(query.target_count),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "query_degree_probabilities": dict(query.query_degree_probabilities),
                    "target_count_probabilities": dict(query.target_count_probabilities),
                    "topology_profile": str(query.topology_profile),
                    "topology_profile_probabilities": dict(query.topology_profile_probabilities),
                    "layout_variant": str(query.layout_variant),
                    "layout_variant_probabilities": dict(query.layout_variant_probabilities),
                    "label_variant": str(query.label_variant),
                    "label_variant_probabilities": dict(query.label_variant_probabilities),
                    "node_shape_variant": str(query.node_shape_variant),
                    "node_shape_variant_probabilities": dict(query.node_shape_variant_probabilities),
                    "layout_transform_variant": str(query.layout_transform_variant),
                    "layout_transform_variant_probabilities": dict(query.layout_transform_variant_probabilities),
                    "node_color_name": str(query.node_color_name),
                    "node_color_name_probabilities": dict(query.node_color_name_probabilities),
                    "degree_sequence_max_degree": int(max_degree),
                },
            },
            "render_spec": {
                "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(rendered_scene.panel_geometry),
                "style": {
                    "node_color_name": str(query.node_color_name),
                    "background_color_rgb": list(render_params.background_color_rgb),
                    "panel_fill_rgb": list(render_params.panel_fill_rgb),
                    "panel_border_rgb": list(render_params.panel_border_rgb),
                    "title_color_rgb": list(render_params.title_color_rgb),
                    "edge_color_rgb": list(render_params.edge_color_rgb),
                    "node_fill_rgb": list(render_params.node_fill_rgb),
                    "node_border_rgb": list(render_params.node_border_rgb),
                    "label_text_rgb": list(render_params.label_text_rgb),
                    "label_stroke_rgb": list(render_params.label_stroke_rgb),
                    "node_shape_variant": str(render_params.node_shape_variant),
                    "node_radius_px": int(render_params.node_radius_px),
                    "edge_width_px": int(render_params.edge_width_px),
                    "node_border_width_px": int(render_params.node_border_width_px),
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                },
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {},
            },
            "execution_trace": {
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": "count_nodes_with_degree",
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "query_degree": int(query.query_degree),
                "target_count": int(query.target_count),
                "matching_labels": list(evidence_labels),
                "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                "degree_sequence": list(graph_sample.degree_sequence),
                "topology_profile": str(graph_sample.topology_profile),
                "label_variant": str(graph_sample.label_variant),
                "node_shape_variant": str(render_params.node_shape_variant),
                "layout_variant_requested": str(query.layout_variant),
                "layout_variant_used": str(rendered_scene.layout_variant),
                "layout_transform_variant": str(rendered_scene.layout_transform_variant),
                "node_color_name": str(query.node_color_name),
                "crossing_count": int(rendered_scene.crossing_count),
            },
            "witness_symbolic": {
                "type": "label_set",
                "label_set": list(evidence_labels),
                "query_degree": int(query.query_degree),
            },
            "projected_evidence": {
                "type": "label_set",
                "label_set": list(evidence_labels),
                "pixel_point_set": list(evidence_node_centers),
                "pixel_bbox_set": list(evidence_node_bboxes),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant="degree_count",
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
