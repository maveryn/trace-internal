"""Return the label at a position in BFS or DFS order from an adjacency list."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.adjacency_representation_scene import (
    SCENE_ID,
    bfs_visit_order,
    dfs_visit_order,
    render_adjacency_list_panel,
    resolve_adjacency_labels,
    sample_reachable_directed_adjacency,
)
from ..shared.complexity import build_graph_complexity, normalize_int_with_bounds, resolve_graph_complexity_weights
from ..shared.graph_sampling import SUPPORTED_NODE_LINK_LABEL_VARIANTS
from ..shared.task_support import format_graph_prompt_label, graph_int_support, resolve_graph_named_variant
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__adjacency__traversal_kth_label"
SUPPORTED_ADJACENCY_TRAVERSAL_QUERY_IDS: Tuple[str, ...] = (
    "bfs_kth_visit_label",
    "dfs_kth_visit_label",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for adjacency-list traversal tasks."""

    node_count_min: int = 5
    node_count_max: int = 8
    traversal_position_min: int = 2
    traversal_position_max: int = 8
    extra_edge_count_min: int = 1
    extra_edge_count_max: int = 4
    label_max_chars: int = 5
    label_variant: str = "letters"
    canvas_width: int = 900
    canvas_height: int = 640
    label_font_size_px: int = 20


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved support axes for one adjacency traversal instance."""

    query_id: str
    node_count: int
    traversal_position: int
    extra_edge_count: int
    label_variant: str
    source_index: int
    query_id_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    traversal_position_probabilities: Dict[str, float]
    extra_edge_count_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "order")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="order")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="order", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)



def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    variant_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_id")
    query_id, query_probs = resolve_graph_named_variant(
        variant_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        supported=SUPPORTED_ADJACENCY_TRAVERSAL_QUERY_IDS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="query_id",
    )
    label_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.label_variant")
    label_variant, label_probs = resolve_graph_named_variant(
        label_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="label_variant",
        weights_key="label_variant_weights",
        balance_flag_key="balanced_label_variant_sampling",
        supported=SUPPORTED_NODE_LINK_LABEL_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="label_variant",
    )
    node_support = graph_int_support(params, _GEN_DEFAULTS, "node_count", _DEFAULTS.node_count_min, _DEFAULTS.node_count_max)
    explicit_node = params.get("node_count")
    if explicit_node is not None:
        node_count = int(explicit_node)
        if int(node_count) not in set(node_support):
            raise ValueError("node_count is outside configured support")
    else:
        node_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:node_count")
        node_count = int(node_support[int(node_index % len(node_support))])

    position_max = min(
        int(node_count),
        int(params.get("traversal_position_max", group_default(_GEN_DEFAULTS, "traversal_position_max", _DEFAULTS.traversal_position_max))),
    )
    position_min = int(params.get("traversal_position_min", group_default(_GEN_DEFAULTS, "traversal_position_min", _DEFAULTS.traversal_position_min)))
    position_support = tuple(range(int(position_min), int(position_max) + 1))
    if not position_support:
        raise ValueError("traversal_position support is empty")
    explicit_position = params.get("traversal_position")
    if explicit_position is not None:
        traversal_position = int(explicit_position)
        if int(traversal_position) not in set(position_support):
            raise ValueError("traversal_position is outside configured support")
    else:
        position_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:traversal_position")
        traversal_position = int(position_support[int(position_index % len(position_support))])

    extra_support = graph_int_support(params, _GEN_DEFAULTS, "extra_edge_count", _DEFAULTS.extra_edge_count_min, _DEFAULTS.extra_edge_count_max)
    explicit_extra = params.get("extra_edge_count")
    if explicit_extra is not None:
        extra_edge_count = int(explicit_extra)
        if int(extra_edge_count) not in set(extra_support):
            raise ValueError("extra_edge_count is outside configured support")
    else:
        extra_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:extra_edge_count")
        extra_edge_count = int(extra_support[int(extra_index % len(extra_support))])

    explicit_source = params.get("source_index")
    if explicit_source is not None:
        source_index = int(explicit_source) % int(node_count)
    else:
        source_selection = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:source_index")
        source_index = int(source_selection % int(node_count))

    return _ResolvedQuery(
        query_id=str(query_id),
        node_count=int(node_count),
        traversal_position=int(traversal_position),
        extra_edge_count=int(extra_edge_count),
        label_variant=str(label_variant),
        source_index=int(source_index),
        query_id_probabilities=dict(query_probs),
        node_count_probabilities=uniform_probability_map(node_support, selected=int(node_count) if explicit_node is not None else None),
        traversal_position_probabilities=uniform_probability_map(
            position_support,
            selected=int(traversal_position) if explicit_position is not None else None,
        ),
        extra_edge_count_probabilities=uniform_probability_map(
            extra_support,
            selected=int(extra_edge_count) if explicit_extra is not None else None,
        ),
        label_variant_probabilities=dict(label_probs),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    return (
        json.dumps({"annotation": [[70, 126, 158, 158], [70, 174, 158, 206], [70, 222, 158, 254]], "answer": "M"}, separators=(",", ":")),
        json.dumps({"answer": "M"}, separators=(",", ":")),
    )


def _build_complexity(*, node_count: int, edge_count: int, traversal_position: int) -> Any:
    node_norm = normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max))
    edge_norm = normalize_int_with_bounds(int(edge_count), (int(node_count) - 1, int(node_count) + _DEFAULTS.extra_edge_count_max))
    position_norm = normalize_int_with_bounds(
        int(traversal_position),
        (_DEFAULTS.traversal_position_min, _DEFAULTS.traversal_position_max),
    )
    return build_graph_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "topology_reasoning": (0.55 * position_norm) + (0.25 * edge_norm) + (0.20 * node_norm),
            "visual_scan": (0.65 * node_norm) + (0.35 * edge_norm),
            "ambiguity": (0.65 * position_norm) + (0.35 * edge_norm),
            "clutter": (0.60 * node_norm) + (0.40 * edge_norm),
        },
    )


@register_task
class GraphOrderAdjacencyTraversalLabelTask:
    """Return the label at a requested BFS or DFS visit position."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "order"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query = _resolve_query(int(instance_seed), params=params)
        labels = resolve_adjacency_labels(
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            label_variant=str(query.label_variant),
            node_count=int(query.node_count),
            max_chars=int(group_default(_GEN_DEFAULTS, "label_max_chars", _DEFAULTS.label_max_chars)),
        )
        source_label = str(labels.labels[int(query.source_index)])
        sample = sample_reachable_directed_adjacency(
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            labels=labels.labels,
            source_label=source_label,
            extra_edge_count=int(query.extra_edge_count),
        )
        visit_order = (
            bfs_visit_order(sample.adjacency, source_label)
            if str(query.query_id) == "bfs_kth_visit_label"
            else dfs_visit_order(sample.adjacency, source_label)
        )
        if int(query.traversal_position) > len(visit_order):
            raise ValueError("traversal_position exceeds visited node count")
        answer_value = str(visit_order[int(query.traversal_position) - 1])
        annotation_labels = tuple(str(label) for label in visit_order[: int(query.traversal_position)])

        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
        base_image, background_meta = make_background_canvas(
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = render_adjacency_list_panel(
            sample=sample,
            base_image=base_image,
            title="Adjacency List",
            subtitle="Directed graph; read neighbors left to right.",
            font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
            layout_seed=int(instance_seed),
            font_family=params.get("font_family"),
            context_text_probability=float(
                params.get("context_text_probability", group_default(_RENDER_DEFAULTS, "context_text_probability", 0.35))
            ),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        annotation_bboxes = [[round(float(value), 3) for value in rendered.row_label_bboxes[str(label)]] for label in annotation_labels]
        answer_gt = TypedValue(type="string", value=str(answer_value))
        annotation_gt = TypedValue(type="bbox_sequence", value=list(annotation_bboxes))

        prompt_defaults = dict(_PROMPT_DEFAULTS)
        json_example, json_example_answer_only = _build_prompt_json_examples()
        annotation_hint_key = f"annotation_hint_{query.query_id}"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "source_label": format_graph_prompt_label(source_label, label_variant=str(labels.label_variant)),
                "traversal_position": str(query.traversal_position),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[annotation_hint_key]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        node_entities = [
            {
                "entity_id": f"node_{label}",
                "entity_kind": "adjacency_row_label",
                "label": str(label),
                "neighbors": list(sample.adjacency.get(str(label), ())),
                "bbox_xyxy": list(rendered.row_label_bboxes[str(label)]),
                "is_source": bool(str(label) == source_label),
                "is_answer": bool(str(label) == answer_value),
                "is_in_annotation_prefix": bool(str(label) in set(annotation_labels)),
            }
            for label in sample.labels
        ]
        edge_entities = [
            {
                "entity_id": f"edge_{left}_{right}",
                "entity_kind": "adjacency_edge",
                "source_label": str(left),
                "target_label": str(right),
                "directed": True,
            }
            for left, right in sample.edges
        ]
        trace_payload = {
            "scene_ir": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "scene_kind": "adjacency",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "representation_variant": str(rendered.representation_variant),
                    "query_id": str(query.query_id),
                    "source_label": str(source_label),
                    "visit_order": list(visit_order),
                    "answer_label": str(answer_value),
                    "adjacency": {str(key): list(values) for key, values in sample.adjacency.items()},
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered.panel_geometry),
                },
            },
            "query_spec": {
                "task_id": TASK_ID,
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id_probabilities": dict(query.query_id_probabilities),
                    "node_count": int(query.node_count),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "traversal_position": int(query.traversal_position),
                    "traversal_position_probabilities": dict(query.traversal_position_probabilities),
                    "extra_edge_count": int(query.extra_edge_count),
                    "extra_edge_count_probabilities": dict(query.extra_edge_count_probabilities),
                    "source_label": str(source_label),
                    "label_variant": str(labels.label_variant),
                    "label_variant_probabilities": dict(query.label_variant_probabilities),
                    "label_source_kind": str(labels.label_source_kind),
                    "label_bucket": str(labels.label_bucket),
                    "label_manifest": str(labels.label_manifest),
                    "label_filter": dict(labels.label_filter),
                    "label_bucket_probabilities": dict(labels.label_bucket_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(canvas_width), int(canvas_height)],
                "coord_space": "pixel",
                "panel_geometry": dict(rendered.panel_geometry),
                "style": {
                    "representation_variant": str(rendered.representation_variant),
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                    **dict(rendered.style_meta),
                },
            },
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {
                "task_id": TASK_ID,
                "scene_id": SCENE_ID,
                "query_id": str(query.query_id),
                "representation_variant": str(rendered.representation_variant),
                "source_label": str(source_label),
                "answer": str(answer_value),
                "annotation_labels": list(annotation_labels),
                "visit_order": list(visit_order),
                "node_count": int(query.node_count),
                "edge_count": int(len(sample.edges)),
                "label_variant": str(labels.label_variant),
            },
            "witness_symbolic": {
                "type": "adjacency_traversal_prefix",
                "labels": list(annotation_labels),
                "answer_label": str(answer_value),
            },
            "projected_annotation": {
                "type": "bbox_sequence",
                "bbox_sequence": list(annotation_bboxes),
                "pixel_bbox_sequence": list(annotation_bboxes),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(
                node_count=int(query.node_count),
                edge_count=int(len(sample.edges)),
                traversal_position=int(query.traversal_position),
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphOrderAdjacencyTraversalLabelTask"]
