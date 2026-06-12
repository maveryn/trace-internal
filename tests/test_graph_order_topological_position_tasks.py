"""Behavior tests for graph topological-position task."""
from __future__ import annotations
import json
from collections import Counter
from trace.core.seed import hash64
from trace.tasks.graph.order.topological_position import GraphOrderTopologicalPositionTask
from trace.tasks.graph.shared.graph_sample_types import SUPPORTED_LAYOUT_VARIANTS
from trace.tasks.shared.graph_algorithms import unique_topological_order_by_adjacency
from trace.tasks.shared.named_colors import named_color

def _extract_prompt_json_example(prompt: str) -> dict:
    marker = 'Example JSON:\n'
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)

def test_graph_order_topological_position_contract_matches_trace() -> None:
    task = GraphOrderTopologicalPositionTask()
    out = task.generate(19640, params={'node_count': 7, 'target_position': 4, 'layout_variant': 'shell', 'topology_profile': 'balanced', 'label_variant': 'letters'}, max_attempts=80)
    trace = out.trace_payload
    execution = trace['execution_trace']
    scene_entities = trace['scene_ir']['entities']
    node_entities = [entity for entity in scene_entities if entity['entity_kind'] == 'graph_node']
    edge_entities = [entity for entity in scene_entities if entity['entity_kind'] == 'graph_edge']
    assert out.answer_gt.type == 'integer'
    assert out.annotation_gt.type == 'point_sequence'
    assert trace['scene_ir']['scene_kind'] == 'graph_topological_position'
    assert execution['question_format'] == 'query_topological_position_of_node'
    assert execution['graph_directionality'] == 'directed'
    assert int(execution['node_count']) == 7
    assert len(node_entities) == 7
    assert len(edge_entities) == int(execution['edge_count'])
    assert sorted(out.prompt_variants.keys()) == ['answer_and_annotation', 'answer_only']
    successors_by_label = {str(key): tuple((str(value) for value in values)) for key, values in trace['execution_trace']['successors_by_label'].items()}
    annotation_labels = tuple((str(label) for label in execution['topological_order_labels']))
    annotation_path = list(out.annotation_gt.value)
    verified_order = unique_topological_order_by_adjacency(successors_by_label, node_order=annotation_labels)
    assert verified_order is not None
    assert tuple((str(label) for label in verified_order)) == annotation_labels
    assert int(out.answer_gt.value) == int(annotation_labels.index(str(execution['query_label'])) + 1)
    assert int(out.answer_gt.value) == int(execution['target_position'])
    assert trace['witness_symbolic']['type'] == 'node_sequence'
    assert trace['witness_symbolic']['nodes'] == list(annotation_labels)
    assert 'label_sequence' not in trace['projected_annotation']
    assert trace['projected_annotation']['type'] == 'point_sequence'
    assert trace['projected_annotation']['point_sequence'] == annotation_path
    assert trace['projected_annotation']['pixel_point_sequence'] == annotation_path
    assert len(trace['projected_annotation']['pixel_bbox_set']) == len(annotation_path)
    width, height = trace['render_spec']['canvas_size']
    assert all((0 <= float(point[0]) <= float(width) and 0 <= float(point[1]) <= float(height) for point in annotation_path))
    assert sum((1 for node in node_entities if bool(node['is_query_node']))) == 1

def test_graph_order_topological_position_prompt_examples_follow_label_variant() -> None:
    task = GraphOrderTopologicalPositionTask()
    letters = task.generate(19641, params={'label_variant': 'letters', 'node_count': 7, 'target_position': 3}, max_attempts=80)
    numbers = task.generate(19642, params={'label_variant': 'numbers', 'node_count': 7, 'target_position': 3}, max_attempts=80)
    letters_example = _extract_prompt_json_example(letters.prompt_variants['answer_and_annotation'])
    numbers_example = _extract_prompt_json_example(numbers.prompt_variants['answer_and_annotation'])
    expected_example = {'annotation': [[140, 220], [260, 180], [380, 240], [500, 300], [620, 260]], 'answer': 3}
    assert letters_example == expected_example
    assert numbers_example == expected_example

def test_graph_order_topological_position_supports_numeric_labels_and_named_colors() -> None:
    task = GraphOrderTopologicalPositionTask()
    out = task.generate(19643, params={'node_count': 7, 'target_position': 5, 'label_variant': 'numbers', 'node_shape_variant': 'hexagon', 'layout_transform_variant': 'rotate_90', 'node_color_name': 'orange'}, max_attempts=80)
    trace = out.trace_payload
    execution = trace['execution_trace']
    labels = [entity['label'] for entity in trace['scene_ir']['entities'] if entity['entity_kind'] == 'graph_node']
    assert all((str(label).isdigit() for label in labels))
    assert execution['label_variant'] == 'numbers'
    assert execution['node_shape_variant'] == 'hexagon'
    assert execution['layout_transform_variant'] == 'rotate_90'
    assert execution['node_color_name'] == 'orange'
    assert tuple(trace['render_spec']['style']['node_fill_rgb']) == tuple(named_color('orange'))

def test_graph_order_topological_position_balanced_sampling_defaults() -> None:
    task = GraphOrderTopologicalPositionTask()
    node_counts: Counter[int] = Counter()
    target_positions: Counter[int] = Counter()
    label_variants: Counter[str] = Counter()
    node_shape_variants: Counter[str] = Counter()
    layout_variants: Counter[str] = Counter()
    topology_profiles: Counter[str] = Counter()
    node_colors: Counter[str] = Counter()
    for index in range(54):
        out = task.generate(hash64(19644, 'graph_order_topological_position', index), params={}, max_attempts=80)
        execution = out.trace_payload['execution_trace']
        node_counts[int(execution['node_count'])] += 1
        target_positions[int(execution['target_position'])] += 1
        label_variants[str(execution['label_variant'])] += 1
        node_shape_variants[str(execution['node_shape_variant'])] += 1
        layout_variants[str(execution['layout_variant_requested'])] += 1
        topology_profiles[str(execution['topology_profile'])] += 1
        node_colors[str(execution['node_color_name'])] += 1
        assert 3 <= int(execution['node_count']) <= 7
        assert 1 <= int(execution['target_position']) <= int(execution['node_count'])
    assert set(node_counts.keys()) == {3, 4, 5, 6, 7}
    assert set(label_variants.keys()) == {'letters', 'numbers', 'named'}
    assert set(node_shape_variants.keys()) == {'circle', 'rounded_square', 'hexagon'}
    assert set(layout_variants.keys()) == set(SUPPORTED_LAYOUT_VARIANTS)
    assert set(topology_profiles.keys()) == {'balanced', 'hub_heavy', 'low_degree'}
    assert set(node_colors.keys()) == {'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'brown', 'cyan', 'magenta', 'maroon'}
    assert min(target_positions.keys()) == 1
