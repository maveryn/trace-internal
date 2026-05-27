"""Return MST total weight from a weighted adjacency matrix."""

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
    matrix_cell_key,
    render_adjacency_matrix_panel,
    resolve_adjacency_labels,
    sample_weighted_matrix_mst_adjacency,
)
from ..shared.complexity import build_graph_complexity, normalize_int_with_bounds, resolve_graph_complexity_weights
from ..shared.graph_sampling import SUPPORTED_NODE_LINK_LABEL_VARIANTS
from ..shared.task_support import graph_int_support, resolve_graph_named_variant
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__adjacency__mst_weight"
SUPPORTED_ADJACENCY_MATRIX_MST_QUERY_VARIANTS: Tuple[str, ...] = ("weighted_matrix_mst_weight",)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for weighted adjacency-matrix MST tasks."""

    node_count_min: int = 4
    node_count_max: int = 7
    extra_edge_count_min: int = 1
    extra_edge_count_max: int = 3
    edge_weight_min: int = 1
    edge_weight_max: int = 12
    label_max_chars: int = 5
    label_variant: str = "letters"
    canvas_width: int = 900
    canvas_height: int = 640
    label_font_size_px: int = 19


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved support axes for one weighted adjacency-matrix MST instance."""

    query_variant: str
    node_count: int
    extra_edge_count: int
    edge_weight_min: int
    edge_weight_max: int
    label_variant: str
    query_variant_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    extra_edge_count_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "optimization")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="optimization")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="optimization", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)



def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    variant_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_variant")
    query_variant, query_probs = resolve_graph_named_variant(
        variant_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        supported=SUPPORTED_ADJACENCY_MATRIX_MST_QUERY_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="query_variant",
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

    max_possible_extra = ((int(node_count) * (int(node_count) - 1)) // 2) - (int(node_count) - 1)
    configured_extra = graph_int_support(params, _GEN_DEFAULTS, "extra_edge_count", _DEFAULTS.extra_edge_count_min, _DEFAULTS.extra_edge_count_max)
    extra_support = tuple(value for value in configured_extra if int(value) <= int(max_possible_extra))
    if not extra_support:
        raise ValueError("extra_edge_count support is empty")
    explicit_extra = params.get("extra_edge_count")
    if explicit_extra is not None:
        extra_edge_count = int(explicit_extra)
        if int(extra_edge_count) not in set(extra_support):
            raise ValueError("extra_edge_count is outside configured support")
    else:
        extra_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:extra_edge_count")
        extra_edge_count = int(extra_support[int(extra_index % len(extra_support))])

    edge_weight_min = int(params.get("edge_weight_min", group_default(_GEN_DEFAULTS, "edge_weight_min", _DEFAULTS.edge_weight_min)))
    edge_weight_max = int(params.get("edge_weight_max", group_default(_GEN_DEFAULTS, "edge_weight_max", _DEFAULTS.edge_weight_max)))
    if int(edge_weight_max) < int(edge_weight_min) + 2:
        raise ValueError("edge_weight_max must leave room for non-MST distractor weights")

    return _ResolvedQuery(
        query_variant=str(query_variant),
        node_count=int(node_count),
        extra_edge_count=int(extra_edge_count),
        edge_weight_min=int(edge_weight_min),
        edge_weight_max=int(edge_weight_max),
        label_variant=str(label_variant),
        query_variant_probabilities=dict(query_probs),
        node_count_probabilities=uniform_probability_map(node_support, selected=int(node_count) if explicit_node is not None else None),
        extra_edge_count_probabilities=uniform_probability_map(
            extra_support,
            selected=int(extra_edge_count) if explicit_extra is not None else None,
        ),
        label_variant_probabilities=dict(label_probs),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    return (
        json.dumps({"evidence": [[278, 182, 328, 232], [328, 282, 378, 332], [378, 332, 428, 382]], "answer": 12}, separators=(",", ":")),
        json.dumps({"answer": 12}, separators=(",", ":")),
    )


def _mst_cell_bboxes(sample, rendered) -> Tuple[list[list[float]], Tuple[Tuple[str, str], ...]]:
    order = {str(label): int(index) for index, label in enumerate(sample.labels)}
    cells: list[list[float]] = []
    cell_edges: list[Tuple[str, str]] = []
    for left, right in sample.mst_edges:
        if order[str(left)] <= order[str(right)]:
            row_label, column_label = str(left), str(right)
        else:
            row_label, column_label = str(right), str(left)
        cells.append([round(float(value), 3) for value in rendered.cell_bboxes[matrix_cell_key(row_label, column_label)]])
        cell_edges.append((str(row_label), str(column_label)))
    return cells, tuple(cell_edges)


def _build_complexity(*, node_count: int, edge_count: int, extra_edge_count: int) -> Any:
    node_norm = normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max))
    edge_norm = normalize_int_with_bounds(int(edge_count), (int(node_count) - 1, ((int(node_count) * (int(node_count) - 1)) // 2)))
    extra_norm = normalize_int_with_bounds(int(extra_edge_count), (_DEFAULTS.extra_edge_count_min, _DEFAULTS.extra_edge_count_max))
    return build_graph_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "topology_reasoning": (0.45 * node_norm) + (0.35 * edge_norm) + (0.20 * extra_norm),
            "visual_scan": (0.70 * node_norm) + (0.30 * edge_norm),
            "ambiguity": (0.45 * extra_norm) + (0.35 * edge_norm) + (0.20 * node_norm),
            "clutter": (0.60 * node_norm) + (0.40 * edge_norm),
        },
    )


@register_task
class GraphOptimizationAdjacencyMatrixMSTWeightTask:
    """Return the unique minimum-spanning-tree weight from a weighted adjacency matrix."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "optimization"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query = _resolve_query(int(instance_seed), params=params)
        labels = resolve_adjacency_labels(
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            label_variant=str(query.label_variant),
            node_count=int(query.node_count),
            max_chars=int(group_default(_GEN_DEFAULTS, "label_max_chars", _DEFAULTS.label_max_chars)),
        )
        sample = sample_weighted_matrix_mst_adjacency(
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            labels=labels.labels,
            extra_edge_count=int(query.extra_edge_count),
            edge_weight_min=int(query.edge_weight_min),
            edge_weight_max=int(query.edge_weight_max),
        )
        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
        base_image, background_meta = make_background_canvas(
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered = render_adjacency_matrix_panel(
            sample=sample,
            base_image=base_image,
            title="Weighted Adjacency Matrix",
            subtitle="Undirected graph; blank cells mean no edge.",
            weighted=True,
            font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        evidence_bboxes, evidence_cell_edges = _mst_cell_bboxes(sample, rendered)
        answer_gt = TypedValue(type="integer", value=int(sample.mst_weight))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        prompt_defaults = dict(_PROMPT_DEFAULTS)
        json_example, json_example_answer_only = _build_prompt_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        mst_edge_set = {tuple(edge) for edge in sample.mst_edges}
        node_entities = [
            {
                "entity_id": f"node_{label}",
                "entity_kind": "adjacency_matrix_label",
                "label": str(label),
                "row_bbox_xyxy": list(rendered.row_label_bboxes[str(label)]),
                "column_bbox_xyxy": list(rendered.column_label_bboxes[str(label)]),
            }
            for label in sample.labels
        ]
        edge_entities = [
            {
                "entity_id": f"edge_{left}_{right}",
                "entity_kind": "weighted_adjacency_matrix_edge",
                "node_u_label": str(left),
                "node_v_label": str(right),
                "weight": int(sample.weights[(str(left), str(right))]),
                "is_in_minimum_spanning_tree": bool((str(left), str(right)) in mst_edge_set),
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
                    "query_variant": str(query.query_variant),
                    "directed": False,
                    "weights": [{"edge": [str(left), str(right)], "weight": int(weight)} for (left, right), weight in sorted(sample.weights.items())],
                    "minimum_spanning_tree_edges": [list(edge) for edge in sample.mst_edges],
                    "minimum_spanning_tree_total_weight": int(sample.mst_weight),
                    "adjacency": {str(key): list(values) for key, values in sample.adjacency.items()},
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered.panel_geometry),
                },
            },
            "query_spec": {
                "task_id": TASK_ID,
                "query_id": str(query.query_variant),
                "query_variant": str(query.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant_probabilities": dict(query.query_variant_probabilities),
                    "node_count": int(query.node_count),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "extra_edge_count": int(query.extra_edge_count),
                    "extra_edge_count_probabilities": dict(query.extra_edge_count_probabilities),
                    "edge_weight_min": int(query.edge_weight_min),
                    "edge_weight_max": int(query.edge_weight_max),
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
                "query_id": str(query.query_variant),
                "query_variant": str(query.query_variant),
                "representation_variant": str(rendered.representation_variant),
                "answer": int(sample.mst_weight),
                "node_count": int(query.node_count),
                "edge_count": int(len(sample.edges)),
                "extra_edge_count": int(query.extra_edge_count),
                "minimum_spanning_tree_edges": [list(edge) for edge in sample.mst_edges],
                "evidence_cell_edges": [list(edge) for edge in evidence_cell_edges],
                "label_variant": str(labels.label_variant),
            },
            "witness_symbolic": {
                "type": "weighted_matrix_cell_set",
                "edges": [list(edge) for edge in evidence_cell_edges],
                "mst_weight": int(sample.mst_weight),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "pixel_bbox_set": list(evidence_bboxes),
            },
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(
                node_count=int(query.node_count),
                edge_count=int(len(sample.edges)),
                extra_edge_count=int(query.extra_edge_count),
            ),
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(query.query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphOptimizationAdjacencyMatrixMSTWeightTask"]
