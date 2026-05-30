"""Behavior tests for graph structure-option matching tasks."""

from __future__ import annotations

from trace.core.seed import hash64
from trace.tasks import create_task


def _has_antiparallel_edges(edges: list[list[str]]) -> bool:
    directed_edges = {tuple(str(value) for value in edge) for edge in edges}
    return any((target, source) in directed_edges for source, target in directed_edges)


def test_graph_options_directed_samples_avoid_overlapped_reverse_arrows() -> None:
    """Directed option graphs should not draw opposite arrows on the same segment."""

    task = create_task("task_graph__graph_options__structure_match_label")
    for query_id in ("same_structure_label", "contained_subgraph_label"):
        for index in range(20):
            out = task.generate(
                int(hash64(19244, f"graph_options_directed_no_antiparallel:{query_id}", index)),
                params={"query_id": query_id, "edge_mode": "directed"},
                max_attempts=240,
            )
            execution = out.trace_payload["execution_trace"]
            specs = [execution["query_structure_spec"], *[option["structure_spec"] for option in execution["option_specs"]]]
            assert all(not _has_antiparallel_edges(spec["edges"]) for spec in specs)
