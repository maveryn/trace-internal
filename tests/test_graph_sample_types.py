"""Regression tests for graph sample type re-exports."""

from __future__ import annotations

from trace.tasks.graph.shared import graph_sample_types
from trace.tasks.graph.shared import graph_sampling


def test_graph_sampling_reexports_sample_types_and_constants() -> None:
    assert graph_sampling.GraphTopologySample is graph_sample_types.GraphTopologySample
    assert graph_sampling.GraphCountSample is graph_sample_types.GraphCountSample
    assert graph_sampling.SUPPORTED_LAYOUT_VARIANTS == graph_sample_types.SUPPORTED_LAYOUT_VARIANTS
    assert graph_sampling.SUPPORTED_NODE_LINK_LABEL_VARIANTS == graph_sample_types.SUPPORTED_NODE_LINK_LABEL_VARIANTS


def test_graph_edge_label_helpers_remain_compatible() -> None:
    assert graph_sampling.graph_label_sort_key("10") == (0, 10)
    assert graph_sampling.graph_label_sort_key("A") == (1, "A")
    assert graph_sampling.canonicalize_graph_edge_label("10", "2") == ("2", "10")
    assert graph_sampling.canonicalize_graph_edge_label("10", "2", directed=True) == ("10", "2")
    assert graph_sampling.sort_graph_edge_labels([("B", "A"), ("10", "2")]) == (("2", "10"), ("A", "B"))
