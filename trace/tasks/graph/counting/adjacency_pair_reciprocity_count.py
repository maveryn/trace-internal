"""Count directed reciprocal-pair states from an adjacency matrix."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.adjacency_representation_scene import (
    SCENE_ID,
    AdjacencyGraphSample,
    matrix_cell_key,
    render_adjacency_matrix_panel,
    resolve_adjacency_labels,
)
from ..shared.complexity import build_graph_complexity, normalize_float_with_bounds, normalize_int_with_bounds, resolve_graph_complexity_weights
from ..shared.graph_sampling import SUPPORTED_NODE_LINK_LABEL_VARIANTS
from ..shared.task_support import graph_int_support, resolve_graph_named_variant
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__adjacency__directed_pair_reciprocity_count"
SUPPORTED_ADJACENCY_PAIR_RECIPROCITY_QUERY_IDS: Tuple[str, ...] = (
    "one_way_pair_count",
    "mutual_pair_count",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for directed adjacency-matrix reciprocity counts."""

    node_count_min: int = 5
    node_count_max: int = 7
    target_count_min: int = 0
    target_count_max: int = 6
    label_max_chars: int = 5
    label_variant: str = "letters"
    canvas_width: int = 900
    canvas_height: int = 640
    label_font_size_px: int = 19


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved support axes for one adjacency reciprocity-count instance."""

    query_id: str
    node_count: int
    target_count: int
    label_variant: str
    query_id_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _PairState:
    """Directed state for one unordered off-diagonal node pair."""

    left: str
    right: str
    forward: bool
    reverse: bool
    state: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="counting")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="counting", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _query_state(query_id: str) -> str:
    if str(query_id) == "one_way_pair_count":
        return "one_way"
    if str(query_id) == "mutual_pair_count":
        return "mutual"
    raise ValueError(f"unsupported reciprocity query_id: {query_id}")


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    variant_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_id")
    query_id, query_probs = resolve_graph_named_variant(
        variant_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        supported=SUPPORTED_ADJACENCY_PAIR_RECIPROCITY_QUERY_IDS,
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
        node_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_count")
        node_count = int(node_rng.choice(tuple(int(value) for value in node_support)))

    max_pairs = (int(node_count) * (int(node_count) - 1)) // 2
    configured_target_support = graph_int_support(
        params,
        _GEN_DEFAULTS,
        "target_count",
        _DEFAULTS.target_count_min,
        _DEFAULTS.target_count_max,
    )
    target_support = tuple(int(value) for value in configured_target_support if int(value) <= int(max_pairs))
    if not target_support:
        raise ValueError("target_count support is empty for adjacency reciprocal-pair count")
    explicit_target = params.get("target_count")
    if explicit_target is not None:
        target_count = int(explicit_target)
        if int(target_count) not in set(target_support):
            raise ValueError("target_count is outside feasible support")
    else:
        target_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.target_count")
        target_count = int(target_rng.choice(tuple(int(value) for value in target_support)))

    return _ResolvedQuery(
        query_id=str(query_id),
        node_count=int(node_count),
        target_count=int(target_count),
        label_variant=str(label_variant),
        query_id_probabilities=dict(query_probs),
        node_count_probabilities=uniform_probability_map(node_support, selected=int(node_count) if explicit_node is not None else None),
        target_count_probabilities=uniform_probability_map(
            target_support,
            selected=int(target_count) if explicit_target is not None else None,
        ),
        label_variant_probabilities=dict(label_probs),
    )


def _sample_reciprocity_matrix(
    *,
    instance_seed: int,
    labels: Tuple[str, ...],
    query_id: str,
    target_count: int,
) -> Tuple[AdjacencyGraphSample, Tuple[_PairState, ...], Tuple[Tuple[str, str], ...]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.reciprocity_matrix.{str(query_id)}.{int(target_count)}")
    label_order = tuple(str(label) for label in labels)
    pairs = [(label_order[i], label_order[j]) for i in range(len(label_order)) for j in range(i + 1, len(label_order))]
    rng.shuffle(pairs)
    target_state = _query_state(str(query_id))
    target_pairs = set(tuple(pair) for pair in pairs[: int(target_count)])
    edges: set[Tuple[str, str]] = set()
    states: List[_PairState] = []

    for pair in pairs:
        left, right = str(pair[0]), str(pair[1])
        if tuple(pair) in target_pairs:
            if target_state == "mutual":
                forward = True
                reverse = True
                state = "mutual"
            else:
                forward = bool(rng.randint(0, 1))
                reverse = not forward
                state = "one_way"
        else:
            if target_state == "mutual":
                state = str(rng.choice(("one_way", "absent")))
                if state == "one_way":
                    forward = bool(rng.randint(0, 1))
                    reverse = not forward
                else:
                    forward = False
                    reverse = False
            else:
                state = str(rng.choice(("mutual", "absent")))
                forward = state == "mutual"
                reverse = state == "mutual"
        if forward:
            edges.add((left, right))
        if reverse:
            edges.add((right, left))
        states.append(_PairState(left=left, right=right, forward=bool(forward), reverse=bool(reverse), state=str(state)))

    adjacency_lists: Dict[str, List[str]] = {label: [] for label in label_order}
    label_index = {label: index for index, label in enumerate(label_order)}
    for source, target in sorted(edges, key=lambda edge: (label_index[str(edge[0])], label_index[str(edge[1])])):
        adjacency_lists[str(source)].append(str(target))

    sample = AdjacencyGraphSample(
        labels=label_order,
        directed=True,
        adjacency={label: tuple(targets) for label, targets in adjacency_lists.items()},
        edges=tuple(sorted(edges, key=lambda edge: (label_index[str(edge[0])], label_index[str(edge[1])]))),
        weights={},
    )
    ordered_states = tuple(sorted(states, key=lambda state: (label_index[str(state.left)], label_index[str(state.right)])))
    counted_pairs = tuple((state.left, state.right) for state in ordered_states if state.state == target_state)
    return sample, ordered_states, counted_pairs


def _build_prompt_json_examples() -> Tuple[str, str]:
    return (
        json.dumps({"annotation": [[278, 182, 328, 232], [328, 132, 378, 182]], "answer": 1}, separators=(",", ":")),
        json.dumps({"answer": 1}, separators=(",", ":")),
    )


def _build_complexity(*, node_count: int, edge_count: int, target_count: int) -> Any:
    max_edges = max(1, int(node_count) * (int(node_count) - 1))
    max_pairs = max(1, (int(node_count) * (int(node_count) - 1)) // 2)
    node_norm = normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max))
    target_norm = normalize_int_with_bounds(int(target_count), (_DEFAULTS.target_count_min, _DEFAULTS.target_count_max))
    density_norm = normalize_float_with_bounds(float(edge_count) / float(max_edges), (0.0, 1.0))
    pair_scan_norm = normalize_float_with_bounds(float(max_pairs) / 21.0, (0.0, 1.0))
    return build_graph_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "topology_reasoning": (0.35 * node_norm) + (0.35 * target_norm) + (0.30 * density_norm),
            "visual_scan": (0.65 * pair_scan_norm) + (0.35 * node_norm),
            "ambiguity": (0.55 * density_norm) + (0.45 * target_norm),
            "clutter": (0.65 * node_norm) + (0.35 * density_norm),
        },
    )


@register_task
class GraphCountingAdjacencyDirectedPairReciprocityCountTask:
    """Count one-way or mutual unordered node pairs in a directed adjacency matrix."""

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
        sample, pair_states, counted_pairs = _sample_reciprocity_matrix(
            instance_seed=int(instance_seed),
            labels=tuple(labels.labels),
            query_id=str(query.query_id),
            target_count=int(query.target_count),
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
            title="Directed Adjacency Matrix",
            subtitle="Rows point to columns.",
            weighted=False,
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

        annotation_bboxes: List[List[float]] = []
        annotation_cell_keys: List[str] = []
        for left, right in counted_pairs:
            forward_key = matrix_cell_key(str(left), str(right))
            reverse_key = matrix_cell_key(str(right), str(left))
            annotation_cell_keys.extend([forward_key, reverse_key])
            annotation_bboxes.append([round(float(value), 3) for value in rendered.cell_bboxes[forward_key]])
            annotation_bboxes.append([round(float(value), 3) for value in rendered.cell_bboxes[reverse_key]])

        answer_gt = TypedValue(type="integer", value=int(len(counted_pairs)))
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

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
                "object_description": str(prompt_defaults["object_description_directed_matrix"]),
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
        pair_state_records = [
            {
                "left_label": str(state.left),
                "right_label": str(state.right),
                "forward_cell_key": matrix_cell_key(str(state.left), str(state.right)),
                "reverse_cell_key": matrix_cell_key(str(state.right), str(state.left)),
                "forward_edge_present": bool(state.forward),
                "reverse_edge_present": bool(state.reverse),
                "pair_state": str(state.state),
                "is_counted": bool((str(state.left), str(state.right)) in set(counted_pairs)),
            }
            for state in pair_states
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
                    "directed": True,
                    "adjacency": {str(key): list(values) for key, values in sample.adjacency.items()},
                    "pair_states": list(pair_state_records),
                    "counted_pairs": [list(pair) for pair in counted_pairs],
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
                    "target_count": int(query.target_count),
                    "target_count_probabilities": dict(query.target_count_probabilities),
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
                "answer": int(len(counted_pairs)),
                "node_count": int(query.node_count),
                "edge_count": int(len(sample.edges)),
                "directed": True,
                "label_variant": str(labels.label_variant),
                "target_pair_state": _query_state(str(query.query_id)),
                "counted_pairs": [list(pair) for pair in counted_pairs],
                "annotation_cell_keys": list(annotation_cell_keys),
                "pair_states": list(pair_state_records),
                "adjacency": {str(key): list(values) for key, values in sample.adjacency.items()},
            },
            "witness_symbolic": {
                "type": "directed_pair_reciprocity_set",
                "target_pair_state": _query_state(str(query.query_id)),
                "pairs": [list(pair) for pair in counted_pairs],
                "cell_keys": list(annotation_cell_keys),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": list(annotation_bboxes),
                "pixel_bbox_set": list(annotation_bboxes),
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
                target_count=int(len(counted_pairs)),
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphCountingAdjacencyDirectedPairReciprocityCountTask"]
