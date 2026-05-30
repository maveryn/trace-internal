"""Count connected components or strongly connected components from adjacency panels."""

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
    SUPPORTED_ADJACENCY_REPRESENTATION_VARIANTS,
    render_adjacency_list_panel,
    render_adjacency_matrix_panel,
    resolve_adjacency_labels,
    sample_component_adjacency,
)
from ..shared.complexity import build_graph_complexity, normalize_int_with_bounds, resolve_graph_complexity_weights
from ..shared.graph_sampling import SUPPORTED_NODE_LINK_LABEL_VARIANTS
from ..shared.task_support import graph_int_support, resolve_graph_named_variant
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__adjacency__component_count"
SUPPORTED_ADJACENCY_COMPONENT_QUERY_IDS: Tuple[str, ...] = (
    "undirected_component_count",
    "directed_strong_component_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for adjacency component-count tasks."""

    node_count_min: int = 6
    node_count_max: int = 9
    component_count_min: int = 2
    component_count_max: int = 6
    extra_edge_count_min: int = 1
    extra_edge_count_max: int = 3
    label_max_chars: int = 5
    label_variant: str = "letters"
    scene_variant: str = "adjacency_list_panel"
    canvas_width: int = 900
    canvas_height: int = 640
    label_font_size_px: int = 19


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved support axes for one adjacency component-count instance."""

    query_id: str
    scene_variant: str
    node_count: int
    component_count: int
    extra_edge_count: int
    label_variant: str
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    component_count_probabilities: Dict[str, float]
    extra_edge_count_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="counting")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="counting", apply_prob=0.5)
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
        supported=SUPPORTED_ADJACENCY_COMPONENT_QUERY_IDS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="query_id",
    )
    scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.scene_variant")
    scene_variant, scene_probs = resolve_graph_named_variant(
        scene_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_ADJACENCY_REPRESENTATION_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="scene_variant",
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

    component_max = min(
        int(node_count),
        int(params.get("component_count_max", group_default(_GEN_DEFAULTS, "component_count_max", _DEFAULTS.component_count_max))),
    )
    component_min = int(params.get("component_count_min", group_default(_GEN_DEFAULTS, "component_count_min", _DEFAULTS.component_count_min)))
    component_support = tuple(range(int(component_min), int(component_max) + 1))
    if not component_support:
        raise ValueError("component_count support is empty")
    explicit_component = params.get("component_count")
    if explicit_component is not None:
        component_count = int(explicit_component)
        if int(component_count) not in set(component_support):
            raise ValueError("component_count is outside configured support")
    else:
        component_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:component_count")
        component_count = int(component_support[int(component_index % len(component_support))])

    extra_support = graph_int_support(params, _GEN_DEFAULTS, "extra_edge_count", _DEFAULTS.extra_edge_count_min, _DEFAULTS.extra_edge_count_max)
    explicit_extra = params.get("extra_edge_count")
    if explicit_extra is not None:
        extra_edge_count = int(explicit_extra)
        if int(extra_edge_count) not in set(extra_support):
            raise ValueError("extra_edge_count is outside configured support")
    else:
        extra_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:extra_edge_count")
        extra_edge_count = int(extra_support[int(extra_index % len(extra_support))])

    return _ResolvedQuery(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        node_count=int(node_count),
        component_count=int(component_count),
        extra_edge_count=int(extra_edge_count),
        label_variant=str(label_variant),
        query_id_probabilities=dict(query_probs),
        scene_variant_probabilities=dict(scene_probs),
        node_count_probabilities=uniform_probability_map(node_support, selected=int(node_count) if explicit_node is not None else None),
        component_count_probabilities=uniform_probability_map(
            component_support,
            selected=int(component_count) if explicit_component is not None else None,
        ),
        extra_edge_count_probabilities=uniform_probability_map(
            extra_support,
            selected=int(extra_edge_count) if explicit_extra is not None else None,
        ),
        label_variant_probabilities=dict(label_probs),
    )


def _build_prompt_json_examples() -> Tuple[str, str]:
    return (
        json.dumps({"evidence": [[70, 126, 158, 158], [70, 318, 158, 350]], "answer": 2}, separators=(",", ":")),
        json.dumps({"answer": 2}, separators=(",", ":")),
    )


def _object_description_key(*, directed: bool, scene_variant: str) -> str:
    direction = "directed" if bool(directed) else "undirected"
    representation = "matrix" if str(scene_variant) == "adjacency_matrix_panel" else "list"
    return f"object_description_{direction}_{representation}"


def _component_representatives(labels: Tuple[str, ...], components: Tuple[Tuple[str, ...], ...]) -> Tuple[str, ...]:
    order = {str(label): int(index) for index, label in enumerate(labels)}
    sorted_components = sorted(components, key=lambda component: min(order[str(label)] for label in component))
    return tuple(min((str(label) for label in component), key=lambda label: order[str(label)]) for component in sorted_components)


def _build_complexity(*, node_count: int, edge_count: int, component_count: int) -> Any:
    node_norm = normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max))
    answer_norm = normalize_int_with_bounds(int(component_count), (_DEFAULTS.component_count_min, _DEFAULTS.component_count_max))
    edge_norm = normalize_int_with_bounds(int(edge_count), (int(node_count) - int(component_count), int(node_count) + _DEFAULTS.extra_edge_count_max))
    return build_graph_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "topology_reasoning": (0.40 * node_norm) + (0.35 * edge_norm) + (0.25 * answer_norm),
            "visual_scan": (0.70 * node_norm) + (0.30 * edge_norm),
            "ambiguity": (0.55 * answer_norm) + (0.45 * edge_norm),
            "clutter": (0.60 * node_norm) + (0.40 * edge_norm),
        },
    )


@register_task
class GraphCountingAdjacencyComponentCountTask:
    """Count components from an adjacency-list or adjacency-matrix representation."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query = _resolve_query(int(instance_seed), params=params)
        labels = resolve_adjacency_labels(
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            label_variant=str(query.label_variant),
            node_count=int(query.node_count),
            max_chars=int(group_default(_GEN_DEFAULTS, "label_max_chars", _DEFAULTS.label_max_chars)),
        )
        directed = str(query.query_id) == "directed_strong_component_count"
        sample = sample_component_adjacency(
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            labels=labels.labels,
            component_count=int(query.component_count),
            directed=bool(directed),
            extra_edge_count=int(query.extra_edge_count),
        )
        representatives = _component_representatives(tuple(sample.labels), tuple(sample.components))

        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
        base_image, background_meta = make_background_canvas(
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        graph_kind = "Directed" if bool(directed) else "Undirected"
        if str(query.scene_variant) == "adjacency_matrix_panel":
            rendered = render_adjacency_matrix_panel(
                sample=sample,
                base_image=base_image,
                title=f"{graph_kind} Adjacency Matrix",
                subtitle="Rows point to columns." if bool(directed) else "The matrix is symmetric.",
                weighted=False,
                font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
                layout_seed=int(instance_seed),
                font_family=params.get("font_family"),
                context_text_probability=float(
                    params.get("context_text_probability", group_default(_RENDER_DEFAULTS, "context_text_probability", 0.35))
                ),
            )
        else:
            rendered = render_adjacency_list_panel(
                sample=sample,
                base_image=base_image,
                title=f"{graph_kind} Adjacency List",
                subtitle="Rows list outgoing neighbors." if bool(directed) else "Rows list adjacent nodes.",
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
        evidence_bboxes = [[round(float(value), 3) for value in rendered.row_label_bboxes[str(label)]] for label in representatives]
        answer_gt = TypedValue(type="integer", value=int(len(sample.components)))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        prompt_defaults = dict(_PROMPT_DEFAULTS)
        json_example, json_example_answer_only = _build_prompt_json_examples()
        evidence_hint_key = f"evidence_hint_{query.query_id}"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(
                    prompt_defaults[
                        _object_description_key(
                            directed=bool(directed),
                            scene_variant=str(query.scene_variant),
                        )
                    ]
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[evidence_hint_key]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        representative_set = set(representatives)
        node_entities = [
            {
                "entity_id": f"node_{label}",
                "entity_kind": "adjacency_row_label",
                "label": str(label),
                "neighbors": list(sample.adjacency.get(str(label), ())),
                "bbox_xyxy": list(rendered.row_label_bboxes[str(label)]),
                "is_component_representative": bool(str(label) in representative_set),
            }
            for label in sample.labels
        ]
        edge_entities = [
            {
                "entity_id": f"edge_{left}_{right}",
                "entity_kind": "adjacency_edge",
                "source_label": str(left),
                "target_label": str(right),
                "directed": bool(directed),
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
                    "directed": bool(directed),
                    "components": [list(component) for component in sample.components],
                    "component_representatives": list(representatives),
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
                    "scene_variant": str(query.scene_variant),
                    "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                    "node_count": int(query.node_count),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "component_count": int(len(sample.components)),
                    "component_count_probabilities": dict(query.component_count_probabilities),
                    "extra_edge_count": int(query.extra_edge_count),
                    "extra_edge_count_probabilities": dict(query.extra_edge_count_probabilities),
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
                "answer": int(len(sample.components)),
                "component_representatives": list(representatives),
                "components": [list(component) for component in sample.components],
                "node_count": int(query.node_count),
                "edge_count": int(len(sample.edges)),
                "directed": bool(directed),
                "label_variant": str(labels.label_variant),
            },
            "witness_symbolic": {
                "type": "component_representative_set",
                "labels": list(representatives),
                "components": [list(component) for component in sample.components],
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
                component_count=int(len(sample.components)),
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphCountingAdjacencyComponentCountTask"]
