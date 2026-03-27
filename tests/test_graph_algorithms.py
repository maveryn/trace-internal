"""Unit tests for shared graph-algorithm helpers."""

from __future__ import annotations

from trace.tasks.shared.graph_algorithms import connected_components_by_adjacency
from trace.tasks.tile.shared.grid_graph import degree_by_active_coord


def test_connected_components_by_adjacency_respects_node_order() -> None:
    adjacency = {
        "b": ["a"],
        "a": ["b"],
        "d": ["c"],
        "c": ["d"],
        "z": [],
    }
    components = connected_components_by_adjacency(
        adjacency,
        node_order=["z", "a", "b", "c", "d"],
    )
    assert components == [["z"], ["a", "b"], ["c", "d"]]


def test_degree_by_active_coord_counts_four_neighbors() -> None:
    degree_map = degree_by_active_coord([(0, 0), (0, 1), (1, 1), (2, 1)])
    assert degree_map == {
        (0, 0): 1,
        (0, 1): 2,
        (1, 1): 2,
        (2, 1): 1,
    }
