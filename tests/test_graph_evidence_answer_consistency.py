"""Graph-domain evidence/answer consistency guardrails."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from trace.core.seed import hash64
from trace.core.taxonomy import TASK_TAXONOMY
from trace.tasks import TASK_REGISTRY, create_task

LEN_EQ_ANSWER_TASKS = {
    "task_graph__adjacency__component_count",
    "task_graph__binary_tree__node_property_count",
    "task_graph__flow_network__min_cut_edge_count",
    "task_graph__metro__exact_distance_station_count",
    "task_graph__metro__station_membership_count",
    "task_graph__node_link__articulation_point_count",
    "task_graph__node_link__bridge_count",
    "task_graph__node_link__common_neighbor_count",
    "task_graph__node_link__component_membership_count",
    "task_graph__node_link__cross_color_edge_count",
    "task_graph__node_link__degree_predicate_count",
    "task_graph__node_link__edge_color_count",
    "task_graph__node_link__edge_text_count",
    "task_graph__node_link__isolated_after_removal_count",
    "task_graph__node_link__named_node_degree_value",
    "task_graph__node_link__node_color_count",
    "task_graph__node_link__reachable_node_count",
    "task_graph__node_link__unique_cycle_size",
    "task_graph__pipe_network__bridge_count",
    "task_graph__pipe_network__junction_path_count",
}

PATH_LEN_EQ_ANSWER_PLUS_ONE_TASKS = {
    "task_graph__node_link__shortest_path_length",
    "task_graph__node_link__longest_path_length",
    "task_graph__metro__shortest_path_length",
    "task_graph__pipe_network__shortest_path_length",
}

SINGLE_EVIDENCE_LABEL_TASKS = {
    "task_graph__node_link__edge_attribute_label",
    "task_graph__node_link__unique_node_label",
    "task_graph__graph_options__structure_match_label",
}

GRAPH_QUERY_IDS = {
    "task_graph__adjacency__component_count": (
        "directed_strong_component_count",
        "undirected_component_count",
    ),
    "task_graph__adjacency__mst_weight": ("weighted_matrix_mst_weight",),
    "task_graph__adjacency__traversal_kth_label": (
        "bfs_kth_visit_label",
        "dfs_kth_visit_label",
    ),
    "task_graph__automaton__accepted_string_label": (
        "dfa_accepted_string_label",
        "nfa_accepted_string_label",
    ),
    "task_graph__automaton__state_after_input_label": (
        "final_state_label",
        "transition_step_state_label",
    ),
    "task_graph__binary_tree__bst_path_operation_label": (
        "bst_insert_parent_label",
        "bst_search_terminal_label",
    ),
    "task_graph__binary_tree__heap_property_violation_label": (
        "heap_property_violation_label",
    ),
    "task_graph__binary_tree__node_property_count": (
        "depth_level_node_count",
        "internal_node_count",
        "leaf_node_count",
        "single_child_node_count",
        "two_child_node_count",
    ),
    "task_graph__binary_tree__node_relation_label": (
        "left_child_label",
        "lowest_common_ancestor_label",
        "parent_label",
        "right_child_label",
        "sibling_label",
    ),
    "task_graph__binary_tree__traversal_kth_label": (
        "inorder_kth_node_label",
        "level_order_kth_node_label",
        "postorder_kth_node_label",
        "preorder_kth_node_label",
    ),
    "task_graph__flow_network__max_flow_value": ("max_flow_value",),
    "task_graph__flow_network__min_cut_edge_count": ("minimum_cut_edge_count",),
    "task_graph__graph_options__structure_match_label": (
        "contained_subgraph_label",
        "same_structure_label",
    ),
    "task_graph__metro__exact_distance_station_count": ("metro_exact_distance_count",),
    "task_graph__metro__shortest_path_length": ("metro_shortest_path_length",),
    "task_graph__metro__station_membership_count": (
        "metro_single_route_station_count",
        "metro_transfer_station_count",
    ),
    "task_graph__metro__transfer_count": ("metro_transfer_count",),
    "task_graph__node_link__articulation_point_count": ("articulation_point_count",),
    "task_graph__node_link__bridge_count": ("bridge_count",),
    "task_graph__node_link__common_neighbor_count": (
        "directed_common_predecessor_count",
        "directed_common_successor_count",
        "undirected_common_neighbor_count",
    ),
    "task_graph__node_link__component_membership_count": (
        "component_size_after_edge_addition",
        "component_size_after_edge_removal",
        "largest_component_size",
        "same_component_count",
    ),
    "task_graph__node_link__cross_color_edge_count": (
        "cross_color_edge_count",
        "directed_cross_color_edge_count",
    ),
    "task_graph__node_link__degree_extremum_value": (
        "directed_max_in_degree_value",
        "directed_max_out_degree_value",
        "directed_max_total_degree_value",
        "directed_min_in_degree_value",
        "directed_min_out_degree_value",
        "directed_min_total_degree_value",
        "undirected_max_degree_value",
        "undirected_min_degree_value",
    ),
    "task_graph__node_link__degree_predicate_count": (
        "directed_in_degree_count",
        "directed_in_degree_one_filter_remaining_count",
        "directed_out_degree_count",
        "directed_out_degree_one_filter_remaining_count",
        "directed_sink_count",
        "directed_source_count",
        "undirected_degree_count",
        "undirected_degree_one_filter_remaining_count",
    ),
    "task_graph__node_link__edge_attribute_label": (
        "directed_edge_between_nodes_label",
        "edge_between_nodes_label",
        "shortest_path_first_edge_label",
    ),
    "task_graph__node_link__edge_color_count": ("edge_color_count",),
    "task_graph__node_link__edge_text_count": ("edge_text_label_count",),
    "task_graph__node_link__isolated_after_removal_count": (
        "isolated_node_count_after_node_removal",
    ),
    "task_graph__node_link__longest_path_length": ("directed_longest_path_length",),
    "task_graph__node_link__mst_weight": ("minimum_spanning_tree_weight",),
    "task_graph__node_link__named_node_degree_value": (
        "directed_named_node_in_degree_value",
        "directed_named_node_out_degree_value",
        "directed_named_node_total_degree_value",
        "undirected_named_node_degree_value",
    ),
    "task_graph__node_link__node_color_count": ("node_color_count",),
    "task_graph__node_link__reachable_node_count": (
        "reachable_count",
        "reachable_count_after_edge_addition",
        "reachable_count_after_edge_removal",
    ),
    "task_graph__node_link__shortest_path_length": (
        "directed_shortest_path_length",
        "undirected_shortest_path_length",
    ),
    "task_graph__node_link__topological_position_value": ("topological_position",),
    "task_graph__node_link__unique_cycle_size": ("unique_cycle_size",),
    "task_graph__node_link__unique_node_label": (
        "unique_neighbor_label",
        "unique_predecessor_label",
        "unique_successor_label",
    ),
    "task_graph__pipe_network__bridge_count": ("pipe_bridge_count",),
    "task_graph__pipe_network__junction_path_count": (
        "pipe_exact_distance_count",
        "pipe_reachable_junction_count",
    ),
    "task_graph__pipe_network__shortest_path_length": ("pipe_shortest_path_length",),
}


def _is_num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _values_equal(left: Any, right: Any) -> bool:
    if _is_num(left) and _is_num(right):
        return abs(float(left) - float(right)) < 1e-9
    return str(left) == str(right)


def _canonical_edge(edge: Any) -> tuple[str, ...]:
    return tuple(sorted(str(value) for value in edge))


def _directed_edge(edge: Any) -> tuple[str, ...]:
    return tuple(str(value) for value in edge)


def _check_evidence_shape(evidence_type: str, evidence_value: Any) -> list[str]:
    errors: list[str] = []
    if evidence_type in {"point_set", "point_sequence"}:
        if not isinstance(evidence_value, list):
            return [f"{evidence_type} value is not a list"]
        for index, point in enumerate(evidence_value):
            if not (
                isinstance(point, list)
                and len(point) == 2
                and all(_is_num(component) for component in point)
            ):
                errors.append(f"{evidence_type}[{index}] is not [x,y]: {point!r}")
                break
    elif evidence_type in {"bbox_set", "bbox_sequence"}:
        if not isinstance(evidence_value, list):
            return [f"{evidence_type} value is not a list"]
        for index, bbox in enumerate(evidence_value):
            if not (
                isinstance(bbox, list)
                and len(bbox) == 4
                and all(_is_num(component) for component in bbox)
            ):
                errors.append(
                    f"{evidence_type}[{index}] is not [x0,y0,x1,y1]: {bbox!r}"
                )
                break
            if not (
                float(bbox[2]) > float(bbox[0]) and float(bbox[3]) > float(bbox[1])
            ):
                errors.append(
                    f"{evidence_type}[{index}] has non-positive extent: {bbox!r}"
                )
                break
    elif evidence_type == "point_pair_set":
        if not isinstance(evidence_value, list):
            return [f"{evidence_type} value is not a list"]
        for index, pair in enumerate(evidence_value):
            if not (
                isinstance(pair, list)
                and len(pair) == 2
                and all(
                    isinstance(point, list)
                    and len(point) == 2
                    and all(_is_num(component) for component in point)
                    for point in pair
                )
            ):
                errors.append(f"{evidence_type}[{index}] is not a point pair: {pair!r}")
                break
    elif evidence_type == "keyed_point_map":
        if not isinstance(evidence_value, Mapping):
            return [f"{evidence_type} value is not an object"]
        for key, point in evidence_value.items():
            if not (
                isinstance(key, str)
                and isinstance(point, list)
                and len(point) == 2
                and all(_is_num(component) for component in point)
            ):
                errors.append(f"{evidence_type}[{key!r}] is not [x,y]: {point!r}")
                break
    elif evidence_type == "keyed_bbox_map":
        if not isinstance(evidence_value, Mapping):
            return [f"{evidence_type} value is not an object"]
        for key, bbox in evidence_value.items():
            if not (
                isinstance(key, str)
                and isinstance(bbox, list)
                and len(bbox) == 4
                and all(_is_num(component) for component in bbox)
            ):
                errors.append(
                    f"{evidence_type}[{key!r}] is not [x0,y0,x1,y1]: {bbox!r}"
                )
                break
            if not (
                float(bbox[2]) > float(bbox[0]) and float(bbox[3]) > float(bbox[1])
            ):
                errors.append(
                    f"{evidence_type}[{key!r}] has non-positive extent: {bbox!r}"
                )
                break
    else:
        errors.append(f"unhandled evidence type: {evidence_type!r}")
    return errors


def _check_len(
    errors: list[str], *, name: str, evidence_len: int | None, values: Any
) -> None:
    if isinstance(values, list) and evidence_len != len(values):
        errors.append(f"evidence length {evidence_len} != {name} length {len(values)}")


def _audit_graph_sample(row: Mapping[str, Any]) -> list[str]:
    task_id = str(row["task_id"])
    query_id = str(row["query_id"])
    answer_type = str(row["answer_type"])
    answer_value = row["answer_value"]
    evidence_type = str(row["evidence_type"])
    evidence_value = row["evidence_value"]
    execution_trace = row["execution_trace"]
    projected_evidence = row["projected_evidence"]
    evidence_len = (
        len(evidence_value) if isinstance(evidence_value, (list, Mapping)) else None
    )

    errors = _check_evidence_shape(evidence_type, evidence_value)
    if isinstance(execution_trace, Mapping) and "answer" in execution_trace:
        if not _values_equal(answer_value, execution_trace["answer"]):
            errors.append(
                f"answer_gt {answer_value!r} != execution_trace.answer {execution_trace['answer']!r}"
            )
    if isinstance(projected_evidence, Mapping) and projected_evidence.get("type"):
        if str(projected_evidence["type"]) != evidence_type:
            errors.append(
                f"evidence_gt.type {evidence_type!r} != projected_evidence.type "
                f"{projected_evidence['type']!r}"
            )
        if (
            evidence_type == "keyed_bbox_map"
            and projected_evidence.get("keyed_bbox_map") != evidence_value
        ):
            errors.append(
                "keyed_bbox_map evidence does not match projected_evidence.keyed_bbox_map"
            )
        if (
            evidence_type == "keyed_point_map"
            and projected_evidence.get("keyed_point_map") != evidence_value
        ):
            errors.append(
                "keyed_point_map evidence does not match projected_evidence.keyed_point_map"
            )

    if task_id in LEN_EQ_ANSWER_TASKS:
        if answer_type != "integer":
            errors.append(f"count task expected integer answer, got {answer_type!r}")
        elif evidence_len != int(answer_value):
            errors.append(
                f"count evidence length {evidence_len} != answer {answer_value}"
            )

    if task_id in PATH_LEN_EQ_ANSWER_PLUS_ONE_TASKS:
        if evidence_len != int(answer_value) + 1:
            errors.append(
                f"path evidence length {evidence_len} != answer+1 {int(answer_value) + 1}"
            )
        _check_len(
            errors,
            name="trace path labels",
            evidence_len=evidence_len,
            values=execution_trace.get("matching_labels")
            or execution_trace.get("shortest_path_labels")
            or execution_trace.get("longest_path_labels"),
        )

    if task_id in SINGLE_EVIDENCE_LABEL_TASKS and evidence_len != 1:
        errors.append(f"single-label evidence length {evidence_len} != 1")

    if "matching_labels" in execution_trace and evidence_type in {
        "point_set",
        "point_sequence",
        "bbox_set",
        "bbox_sequence",
    }:
        _check_len(
            errors,
            name="matching_labels",
            evidence_len=evidence_len,
            values=execution_trace.get("matching_labels"),
        )
    if "matching_edges" in execution_trace and evidence_type == "point_pair_set":
        _check_len(
            errors,
            name="matching_edges",
            evidence_len=evidence_len,
            values=execution_trace.get("matching_edges"),
        )
    if "counted_edges" in execution_trace and evidence_type == "point_pair_set":
        _check_len(
            errors,
            name="counted_edges",
            evidence_len=evidence_len,
            values=execution_trace.get("counted_edges"),
        )
    if "evidence_edges" in execution_trace and evidence_type == "point_pair_set":
        _check_len(
            errors,
            name="evidence_edges",
            evidence_len=evidence_len,
            values=execution_trace.get("evidence_edges"),
        )
    if "evidence_cell_edges" in execution_trace and evidence_type == "bbox_set":
        _check_len(
            errors,
            name="evidence_cell_edges",
            evidence_len=evidence_len,
            values=execution_trace.get("evidence_cell_edges"),
        )
    if "evidence_labels" in execution_trace and evidence_type in {
        "bbox_set",
        "bbox_sequence",
    }:
        _check_len(
            errors,
            name="evidence_labels",
            evidence_len=evidence_len,
            values=execution_trace.get("evidence_labels"),
        )

    if task_id == "task_graph__node_link__degree_extremum_value":
        labels = execution_trace.get("matching_labels") or []
        if execution_trace.get("target_degree") is not None and int(
            answer_value
        ) != int(execution_trace["target_degree"]):
            errors.append(
                f"degree-extremum answer {answer_value} != target_degree "
                f"{execution_trace['target_degree']}"
            )
        queried_degrees = execution_trace.get("queried_degrees_by_label") or {}
        mismatched = [
            label
            for label in labels
            if str(label) in queried_degrees
            and int(queried_degrees[str(label)]) != int(answer_value)
        ]
        if mismatched:
            errors.append(
                f"degree-extremum labels do not match answer: {mismatched[:3]!r}"
            )

    if task_id == "task_graph__node_link__topological_position_value":
        order = execution_trace.get("topological_order_labels") or []
        _check_len(
            errors,
            name="topological_order_labels",
            evidence_len=evidence_len,
            values=order,
        )
        if execution_trace.get("target_position") is not None and int(
            answer_value
        ) != int(execution_trace["target_position"]):
            errors.append(
                f"topological answer {answer_value} != target_position "
                f"{execution_trace['target_position']}"
            )
        if order and 1 <= int(answer_value) <= len(order):
            if str(order[int(answer_value) - 1]) != str(
                execution_trace.get("query_label")
            ):
                errors.append("topological answer index does not identify query_label")

    if task_id == "task_graph__node_link__mst_weight":
        mst_edges = execution_trace.get("minimum_spanning_tree_edges") or []
        _check_len(
            errors,
            name="minimum_spanning_tree_edges",
            evidence_len=evidence_len,
            values=mst_edges,
        )
        if execution_trace.get("minimum_spanning_tree_total_weight") is not None:
            if int(answer_value) != int(
                execution_trace["minimum_spanning_tree_total_weight"]
            ):
                errors.append("MST answer does not match trace total weight")
        weights = {
            _canonical_edge(item["endpoints"]): int(item["weight"])
            for item in execution_trace.get("edge_weights_by_label", [])
            if isinstance(item, Mapping)
        }
        if mst_edges and weights:
            total = sum(weights.get(_canonical_edge(edge), 0) for edge in mst_edges)
            if total != int(answer_value):
                errors.append(
                    f"MST selected edge weights sum {total} != answer {answer_value}"
                )

    if task_id == "task_graph__adjacency__mst_weight":
        mst_edges = execution_trace.get("minimum_spanning_tree_edges") or []
        _check_len(
            errors,
            name="minimum_spanning_tree_edges",
            evidence_len=evidence_len,
            values=mst_edges,
        )
        if evidence_len != int(execution_trace.get("node_count", 0)) - 1:
            errors.append("adjacency MST evidence length does not equal node_count-1")

    if task_id == "task_graph__flow_network__max_flow_value":
        cut_edges = execution_trace.get("original_min_cut_edges") or []
        _check_len(
            errors,
            name="original_min_cut_edges",
            evidence_len=evidence_len,
            values=cut_edges,
        )
        if int(answer_value) != int(execution_trace.get("original_max_flow_value")):
            errors.append("max-flow answer does not match trace max flow")
        capacities = {
            _directed_edge(item["edge"]): int(item["capacity"])
            for item in execution_trace.get("capacity_by_edge", [])
            if isinstance(item, Mapping)
        }
        if capacities:
            cut_capacity = sum(
                capacities.get(_directed_edge(edge), 0)
                for edge in execution_trace.get("evidence_edges", []) or []
            )
            if cut_capacity != int(answer_value):
                errors.append(
                    f"max-flow evidence cut capacity {cut_capacity} != answer {answer_value}"
                )

    if task_id == "task_graph__metro__transfer_count":
        if int(answer_value) != len(
            execution_trace.get("route_change_station_labels") or []
        ):
            errors.append(
                "metro transfer answer does not match route_change_station_labels length"
            )
        _check_len(
            errors,
            name="matching_labels",
            evidence_len=evidence_len,
            values=execution_trace.get("matching_labels"),
        )

    if task_id in {
        "task_graph__binary_tree__traversal_kth_label",
        "task_graph__adjacency__traversal_kth_label",
        "task_graph__binary_tree__bst_path_operation_label",
        "task_graph__binary_tree__heap_property_violation_label",
    }:
        evidence_labels = execution_trace.get("evidence_labels") or []
        _check_len(
            errors,
            name="evidence_labels",
            evidence_len=evidence_len,
            values=evidence_labels,
        )
        if evidence_labels and str(evidence_labels[-1]) != str(answer_value):
            errors.append(
                f"last evidence label {evidence_labels[-1]!r} != answer {answer_value!r}"
            )
        if task_id == "task_graph__binary_tree__traversal_kth_label":
            if evidence_len != int(execution_trace.get("traversal_position")):
                errors.append(
                    "binary-tree traversal evidence length != traversal_position"
                )
        if task_id == "task_graph__adjacency__traversal_kth_label":
            visit_order = execution_trace.get("visit_order") or []
            if (
                evidence_labels
                and visit_order[: len(evidence_labels)] != evidence_labels
            ):
                errors.append(
                    "adjacency traversal evidence_labels is not a visit_order prefix"
                )
        if (
            task_id == "task_graph__binary_tree__heap_property_violation_label"
            and evidence_len != 2
        ):
            errors.append("heap-property violation evidence length != 2")

    if task_id == "task_graph__binary_tree__node_relation_label":
        if str(answer_value) != str(execution_trace.get("answer_label")):
            errors.append("binary-tree relation answer does not match answer_label")
        if evidence_type != "keyed_bbox_map":
            errors.append("binary-tree relation evidence must be keyed_bbox_map")
        role_to_label = execution_trace.get("evidence_role_to_label") or {}
        if not isinstance(role_to_label, Mapping):
            errors.append("binary-tree relation evidence_role_to_label is not a map")
        elif not isinstance(evidence_value, Mapping):
            errors.append("binary-tree relation evidence value is not a map")
        elif set(role_to_label) != set(evidence_value):
            errors.append(
                "binary-tree relation evidence keys do not match evidence_role_to_label keys"
            )
        if (
            evidence_len is not None
            and evidence_len < len(execution_trace.get("query_labels") or []) + 1
        ):
            errors.append("binary-tree relation evidence omits a query or answer node")

    if task_id == "task_graph__automaton__state_after_input_label":
        state_path = execution_trace.get("evidence_state_path_labels") or []
        _check_len(
            errors,
            name="evidence_state_path_labels",
            evidence_len=evidence_len,
            values=state_path,
        )
        if state_path and str(state_path[-1]) != str(answer_value):
            errors.append(
                f"automaton state path ends at {state_path[-1]!r}, not answer {answer_value!r}"
            )
        expected_len = (
            int(execution_trace.get("input_length")) + 1
            if query_id == "final_state_label"
            else int(execution_trace.get("transition_step_count")) + 1
        )
        if evidence_len != expected_len:
            errors.append(
                f"automaton state path length {evidence_len} != expected {expected_len}"
            )

    if task_id == "task_graph__automaton__accepted_string_label":
        _check_len(
            errors,
            name="accepting_path_labels",
            evidence_len=evidence_len,
            values=execution_trace.get("accepting_path_labels"),
        )
        if evidence_len != int(execution_trace.get("input_length")) + 1:
            errors.append("accepted-string path length != input_length+1")
        if str(answer_value) != str(execution_trace.get("answer_option_label")):
            errors.append("accepted-string answer does not match answer_option_label")

    if task_id == "task_graph__node_link__edge_attribute_label":
        if str(answer_value) != str(execution_trace.get("target_edge_label")):
            errors.append("edge-attribute answer does not match target_edge_label")
    if task_id == "task_graph__node_link__unique_node_label":
        if str(answer_value) != str(execution_trace.get("answer_label")):
            errors.append("unique-node answer does not match answer_label")
    if task_id == "task_graph__graph_options__structure_match_label":
        if str(answer_value) != str(execution_trace.get("answer_option_label")):
            errors.append("structure-match answer does not match answer_option_label")
    return errors


def _collect_sample(output: Any, seed: int) -> dict[str, Any]:
    return {
        "task_id": str(
            output.trace_payload.get("query_spec", {}).get("task_id")
            or output.trace_payload.get("execution_trace", {}).get("task_id")
            or ""
        ),
        "query_id": str(output.query_id),
        "seed": int(seed),
        "answer_type": output.answer_gt.type,
        "answer_value": output.answer_gt.value,
        "evidence_type": output.evidence_gt.type,
        "evidence_value": output.evidence_gt.value,
        "execution_trace": output.trace_payload.get("execution_trace", {}),
        "projected_evidence": output.trace_payload.get("projected_evidence", {}),
    }


def test_graph_evidence_matches_answer_contracts() -> None:
    """Every graph query branch should keep answer, evidence, and trace aligned."""

    failures: list[tuple[str, str, int, list[str]]] = []
    graph_task_ids = sorted(
        task_id
        for task_id, taxonomy in TASK_TAXONOMY.items()
        if taxonomy.domain == "graph" and task_id in TASK_REGISTRY
    )
    assert len(graph_task_ids) == 40
    assert sorted(GRAPH_QUERY_IDS) == graph_task_ids
    assert sum(len(query_ids) for query_ids in GRAPH_QUERY_IDS.values()) == 89

    total_samples = 0
    query_bucket_counts: Counter[tuple[str, str]] = Counter()
    for task_id in graph_task_ids:
        task = create_task(task_id)
        for query_id in GRAPH_QUERY_IDS[task_id]:
            for sample_index in range(2):
                seed = hash64(
                    20260528,
                    f"graph_evidence_contract:{task_id}:{query_id}",
                    sample_index,
                )
                output = task.generate(
                    seed, params={"query_id": query_id}, max_attempts=300
                )
                row = _collect_sample(output, seed)
                if not row["task_id"]:
                    row["task_id"] = task_id
                total_samples += 1
                query_bucket_counts[(task_id, str(query_id))] += 1
                errors = _audit_graph_sample(row)
                if errors:
                    failures.append((task_id, str(query_id), int(row["seed"]), errors))

    assert total_samples == 178
    assert len(query_bucket_counts) == 89
    assert failures == []
