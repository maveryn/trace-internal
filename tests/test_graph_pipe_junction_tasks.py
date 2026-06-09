from __future__ import annotations

import networkx as nx

from trace.tasks.graph.counting.pipe_bridge_count import GraphCountingPipeBridgeCountTask
from trace.tasks.graph.path.pipe_shortest_path_length import GraphPathPipeShortestPathLengthTask
from trace.tasks.graph.relation.junction_path_count import (
    GraphRelationPipeExactDistanceCountTask,
    GraphRelationPipeReachableJunctionCountTask,
)


def _open_graph_from_trace(trace_payload: dict) -> nx.Graph:
    adjacency = trace_payload["scene_ir"]["relations"]["open_adjacency_by_label"]
    graph = nx.Graph()
    for label, neighbors in adjacency.items():
        graph.add_node(str(label))
        for neighbor in neighbors:
            graph.add_edge(str(label), str(neighbor))
    return graph


def test_pipe_shortest_path_contract() -> None:
    out = GraphPathPipeShortestPathLengthTask().generate(2026051901, params={}, max_attempts=200)
    graph = _open_graph_from_trace(out.trace_payload)
    trace = out.trace_payload["execution_trace"]
    source = str(trace["source_label"])
    goal = str(trace["goal_label"])
    paths = list(nx.all_shortest_paths(graph, source=source, target=goal))
    assert out.scene_id == "pipe_network"
    assert out.query_id == "pipe_shortest_path_length"
    assert len(paths) == 1
    assert out.answer_gt.value == len(paths[0]) - 1
    assert out.annotation_gt.type == "point_sequence"
    assert len(out.annotation_gt.value) == len(paths[0])
    assert "blocked pipes" in out.prompt


def test_pipe_reachable_count_contract() -> None:
    out = GraphRelationPipeReachableJunctionCountTask().generate(
        2026051902,
        params={},
        max_attempts=200,
    )
    graph = _open_graph_from_trace(out.trace_payload)
    query_label = str(out.trace_payload["execution_trace"]["query_label"])
    reachable = nx.node_connected_component(graph, query_label)
    assert out.scene_id == "pipe_network"
    assert out.query_id == "pipe_reachable_junction_count"
    assert 1 <= int(out.answer_gt.value) <= 5
    assert out.answer_gt.value == len(reachable)
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == len(reachable)


def test_pipe_bridge_count_contract() -> None:
    out = GraphCountingPipeBridgeCountTask().generate(2026051903, params={}, max_attempts=300)
    graph = _open_graph_from_trace(out.trace_payload)
    bridge_count = len(list(nx.bridges(graph)))
    assert out.scene_id == "pipe_network"
    assert out.query_id == "pipe_bridge_count"
    assert 0 <= int(out.answer_gt.value) <= 5
    assert out.answer_gt.value == bridge_count
    assert out.annotation_gt.type == "point_pair_set"
    assert len(out.annotation_gt.value) == bridge_count


def test_pipe_exact_distance_count_contract() -> None:
    out = GraphRelationPipeExactDistanceCountTask().generate(
        2026051904,
        params={},
        max_attempts=300,
    )
    graph = _open_graph_from_trace(out.trace_payload)
    trace = out.trace_payload["execution_trace"]
    query_label = str(trace["query_label"])
    query_distance = int(trace["query_distance"])
    distances = nx.single_source_shortest_path_length(graph, query_label)
    exact_count = sum(1 for distance in distances.values() if int(distance) == query_distance)
    assert out.scene_id == "pipe_network"
    assert out.query_id == "pipe_exact_distance_count"
    assert out.answer_gt.value == exact_count
    assert out.annotation_gt.type == "point_set"
    assert len(out.annotation_gt.value) == exact_count
