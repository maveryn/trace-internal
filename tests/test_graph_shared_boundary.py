"""Regression checks for graph-domain shared helper boundaries."""

from __future__ import annotations

from pathlib import Path


def test_non_node_link_graph_scenes_do_not_import_graph_sampling_facade() -> None:
    """The graph sampling facade is a temporary node-link migration surface only."""

    graph_root = Path("trace/tasks/graph")
    facade_import_patterns = (
        "trace.tasks.graph.shared.graph_sampling",
        "from ..shared.graph_sampling",
        "from ...shared.graph_sampling",
        "from .graph_sampling",
    )
    offenders: list[str] = []
    for path in graph_root.rglob("*.py"):
        relative = path.relative_to(graph_root)
        if relative.parts[0] == "node_link":
            continue
        if relative == Path("shared/graph_sampling.py"):
            continue
        text = path.read_text(encoding="utf-8")
        if any(pattern in text for pattern in facade_import_patterns):
            offenders.append(str(path))

    assert offenders == []
