"""Shortest open-route length in a pipe-junction graph."""

from __future__ import annotations

from ...registry import register_task
from ..shared.pipe_junction_task import PipeJunctionGraphTaskBase


@register_task
class GraphPathPipeShortestPathLengthTask(PipeJunctionGraphTaskBase):
    """Count open pipe segments in a unique shortest route between two junctions."""

    task_id = "task_graph__pipe_network__shortest_path_length"
    task_group = "path"
    query_id = "pipe_shortest_path_length"
    prompt_question_key = "question_text_shortest_path_length"
    prompt_annotation_key = "annotation_hint"
    prompt_task_key_fallback = "shortest_path_length_query"


__all__ = ["GraphPathPipeShortestPathLengthTask"]
