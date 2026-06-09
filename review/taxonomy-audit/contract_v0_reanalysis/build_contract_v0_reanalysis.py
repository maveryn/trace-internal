#!/usr/bin/env python3
"""Build the contract-v0 TRACE taxonomy reanalysis package.

This package is a fresh contract-v0 view over the live task inventory.  It
uses the current taxonomy docs' task-contract fields:

    scene_contract + answer_schema + annotation_schema + program_schema

The source seed files provide hand-authored task/query boundary coverage.  This
script normalizes that coverage into the current contract vocabulary and writes
reviewable CSV/Markdown artifacts.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from trace.core.taxonomy import TASK_TAXONOMY
from trace.tasks.registry import TASK_REGISTRY, list_default_task_ids


AUDIT_ROOT = Path("review/taxonomy-audit")
OUT_ROOT = AUDIT_ROOT / "contract_v0_reanalysis"
SOURCE_ROOT = OUT_ROOT / "source"
LIVE_INVENTORY_SEED = SOURCE_ROOT / "live_task_inventory_seed.csv"
MANUAL_BOUNDARY_SEED = SOURCE_ROOT / "manual_query_boundary_seed.csv"
PROGRAM_ARGUMENT_OVERRIDES = SOURCE_ROOT / "program_argument_overrides.json"
APPROVED_CURRENT_TASK_MERGES = SOURCE_ROOT / "approved_current_task_merges.csv"
REVIEW_ROOT = Path("review/task-reviews")
PROGRAM_ARGUMENT_SCHEMA_VERSION = "program_arguments_v0"


ACTIVE_DOMAIN_ORDER = (
    "charts",
    "games",
    "geometry",
    "graph",
    "icons",
    "illustrations",
    "misc",
    "pages",
    "physics",
    "puzzles",
    "three_d",
)

CANONICAL_PROPOSED_TASK_OVERRIDES = {
    "task_charts__bar_3d__series_interval_total_value": "series_category_scope_total_value",
    "task_charts__bar_3d__series_total_value": "series_category_scope_total_value",
    "task_geometry__coordinate_panels__quadrilateral_shape_match_label_parallelogram_shape_match_label": "quadrilateral_shape_match_label",
    "task_geometry__coordinate_panels__quadrilateral_shape_match_label_rhombus_shape_match_label": "quadrilateral_shape_match_label",
    "task_geometry__coordinate_panels__quadrilateral_shape_match_label_square_shape_match_label": "quadrilateral_shape_match_label",
    "task_geometry__coordinate_plane__quadrilateral_completion_label_parallelogram_completion_label": "quadrilateral_completion_label",
    "task_geometry__coordinate_plane__quadrilateral_completion_label_rhombus_completion_label": "quadrilateral_completion_label",
    "task_geometry__coordinate_plane__quadrilateral_completion_label_square_completion_label": "quadrilateral_completion_label",
}


@dataclass(frozen=True)
class ObservedSchema:
    answer_types: tuple[str, ...]
    annotation_types: tuple[str, ...]
    sample_count: int
    example_json_paths: tuple[str, ...]
    example_image_paths: tuple[str, ...]


@dataclass(frozen=True)
class ProgramSignature:
    signature_id: str
    program_schema: str
    definition: str
    do_not_merge_when: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: Iterable[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(fieldnames or (rows[0].keys() if rows else []))
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=names)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in names})


def task_parts(task_id: str) -> tuple[str, str, str]:
    head, scene_id, task_slug = task_id.split("__", 2)
    return head.removeprefix("task_"), scene_id, task_slug


def proposed_task_id(domain: str, scene_id: str, slug: str) -> str:
    return f"task_{domain}__{scene_id}__{slug}"


def split_pipe(value: str) -> list[str]:
    return [part for part in str(value or "").split("|") if part]


def norm_text(value: Any) -> str:
    return str(value or "").strip()


def unique_join(values: Iterable[str], sep: str = " | ") -> str:
    out: list[str] = []
    for value in values:
        text = str(value)
        if text and text not in out:
            out.append(text)
    return sep.join(out)


def load_inventory_seed() -> dict[str, dict[str, str]]:
    rows = read_csv(LIVE_INVENTORY_SEED)
    return {row["task_id"]: row for row in rows}


def load_boundary_seed_rows() -> dict[tuple[str, str], list[dict[str, str]]]:
    rows = read_csv(MANUAL_BOUNDARY_SEED)
    by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_key[(row["current_task_id"], row["query_id"])].append(row)
    return dict(by_key)


def load_approved_current_task_merges() -> dict[str, set[str]]:
    """Return proposed task ids whose multi-current-task merge is intentional."""

    if not APPROVED_CURRENT_TASK_MERGES.exists():
        return {}
    approved: dict[str, set[str]] = {}
    for row in read_csv(APPROVED_CURRENT_TASK_MERGES):
        proposed_task_id = norm_text(row.get("proposed_task_id", ""))
        current_task_ids = set(split_pipe(row.get("current_task_ids", "")))
        if proposed_task_id and current_task_ids:
            approved[proposed_task_id] = current_task_ids
    return approved


def collect_observed_query_ids_by_task() -> dict[str, tuple[str, ...]]:
    """Return query ids observed in review artifacts, keyed by task id."""

    observed: dict[str, set[str]] = defaultdict(set)
    for path in REVIEW_ROOT.glob("*/*/*/data/**/*.json"):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        task_id = norm_text(data.get("task"))
        query_id = norm_text(data.get("query_id")) or "default"
        if task_id:
            observed[task_id].add(query_id)
    return {task_id: tuple(sorted(query_ids)) for task_id, query_ids in observed.items()}


def load_program_argument_overrides() -> dict[str, Any]:
    """Load optional hand-authored taxonomy argument metadata overrides."""

    if not PROGRAM_ARGUMENT_OVERRIDES.exists():
        return {}
    try:
        payload = json.loads(PROGRAM_ARGUMENT_OVERRIDES.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid program argument override JSON: {exc}") from exc
    if isinstance(payload, Mapping):
        overrides = payload.get("overrides", payload)
        if isinstance(overrides, Mapping):
            return dict(overrides)
    raise SystemExit("program argument override file must contain a JSON object")


def collect_observed_schemas() -> dict[tuple[str, str], ObservedSchema]:
    answer_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    annotation_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    examples_json: dict[tuple[str, str], list[str]] = defaultdict(list)
    examples_img: dict[tuple[str, str], list[str]] = defaultdict(list)
    for path in REVIEW_ROOT.glob("*/*/*/data/**/*.json"):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        task_id = norm_text(data.get("task"))
        query_id = norm_text(data.get("query_id")) or "default"
        if not task_id:
            continue
        key = (task_id, query_id)
        answer_type = norm_text((data.get("answer_gt") or {}).get("type"))
        annotation_type = norm_text((data.get("annotation_gt") or {}).get("type"))
        if answer_type:
            answer_counts[key][answer_type] += 1
        if annotation_type:
            annotation_counts[key][annotation_type] += 1
        if len(examples_json[key]) < 5:
            examples_json[key].append(str(path))
            image_path = (data.get("image") or {}).get("path")
            if image_path:
                examples_img[key].append(str(image_path))
    observed: dict[tuple[str, str], ObservedSchema] = {}
    for key in sorted(set(answer_counts) | set(annotation_counts)):
        observed[key] = ObservedSchema(
            answer_types=tuple(sorted(answer_counts[key])),
            annotation_types=tuple(sorted(annotation_counts[key])),
            sample_count=sum(answer_counts[key].values()),
            example_json_paths=tuple(examples_json.get(key, ())),
            example_image_paths=tuple(examples_img.get(key, ())),
        )
    return observed


def read_nested_value(payload: Mapping[str, Any], dotted_path: str) -> Any:
    """Return a dotted-path value from a review JSON payload."""

    current: Any = payload
    for part in str(dotted_path or "").split("."):
        if not part:
            continue
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def observed_schema_for_boundary_row(
    *,
    item: Mapping[str, Any],
    query_id: str,
    prior: Mapping[str, str] | None,
    fallback: ObservedSchema | None,
) -> ObservedSchema | None:
    """Return observed schema/examples, optionally filtered by trace metadata.

    Manual taxonomy rows may split one existing query_id into multiple proposed
    contracts.  In those cases the seed can provide trace_filter_path and
    trace_filter_value so the examples in the review app stay tied to the
    concrete branch being reviewed.
    """

    if prior is None:
        return fallback
    filter_path = norm_text(prior.get("trace_filter_path", ""))
    filter_value = norm_text(prior.get("trace_filter_value", ""))
    if not filter_path:
        return fallback

    data_root = (
        REVIEW_ROOT
        / str(item["domain"])
        / str(item["scene_id"])
        / str(item["task_id"])
        / "data"
        / str(query_id)
    )
    answer_counts: Counter[str] = Counter()
    annotation_counts: Counter[str] = Counter()
    examples_json: list[str] = []
    examples_img: list[str] = []
    if not data_root.exists():
        return fallback

    for path in sorted(data_root.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        if norm_text(read_nested_value(data, filter_path)) != filter_value:
            continue
        answer_type = norm_text((data.get("answer_gt") or {}).get("type"))
        annotation_type = norm_text((data.get("annotation_gt") or {}).get("type"))
        if answer_type:
            answer_counts[answer_type] += 1
        if annotation_type:
            annotation_counts[annotation_type] += 1
        if len(examples_json) < 5:
            examples_json.append(str(path))
            image_path = (data.get("image") or {}).get("path")
            if image_path:
                examples_img.append(str(image_path))

    if not answer_counts and not annotation_counts:
        return fallback
    return ObservedSchema(
        answer_types=tuple(sorted(answer_counts)),
        annotation_types=tuple(sorted(annotation_counts)),
        sample_count=sum(answer_counts.values()),
        example_json_paths=tuple(examples_json),
        example_image_paths=tuple(examples_img),
    )


def build_live_inventory() -> list[dict[str, Any]]:
    seed_inventory = load_inventory_seed()
    observed_query_ids_by_task = collect_observed_query_ids_by_task()
    live_ids = list_default_task_ids()
    rows: list[dict[str, Any]] = []
    for task_id in live_ids:
        id_domain, id_scene_id, task_slug = task_parts(task_id)
        cls = TASK_REGISTRY[task_id]
        taxonomy = TASK_TAXONOMY.get(task_id)
        domain = norm_text(getattr(taxonomy, "domain", id_domain)) if taxonomy else id_domain
        scene_id = norm_text(getattr(taxonomy, "scene_id", id_scene_id)) if taxonomy else id_scene_id
        old = seed_inventory.get(task_id, {})
        if domain in {"graph", "misc", "pages", "puzzles"} and task_id in observed_query_ids_by_task:
            query_ids = list(observed_query_ids_by_task[task_id])
        else:
            query_ids = split_pipe(old.get("query_ids", "")) or [task_slug]
        module_file = Path(__import__(cls.__module__, fromlist=[cls.__name__]).__file__)
        try:
            source_file = str(module_file.relative_to(Path.cwd()))
        except ValueError:
            source_file = str(module_file)
        rows.append(
            {
                "task_id": task_id,
                "domain": domain,
                "scene_id": scene_id,
                "task_slug": task_slug,
                "task_group": norm_text(getattr(cls, "task_group", "")),
                "source_domain": norm_text(getattr(taxonomy, "source_domain", domain)) if taxonomy else domain,
                "source_task_group": norm_text(getattr(taxonomy, "source_task_group", getattr(cls, "task_group", ""))) if taxonomy else norm_text(getattr(cls, "task_group", "")),
                "module": norm_text(cls.__module__),
                "class_name": norm_text(cls.__name__),
                "source_file": source_file,
                "doc_path": old.get("doc_path", f"docs/tasks/{task_id}.md"),
                "query_ids": "|".join(query_ids),
                "answer_types": old.get("answer_types", old.get("answer_types", "")),
                "annotation_types": old.get("annotation_types", old.get("annotation_types", "")),
                "generation_failures": old.get("generation_failures", ""),
            }
        )
    return rows


def normalize_answer_schema(answer_types: Iterable[str], *, task_slug: str, query_id: str, domain: str, scene_id: str) -> str:
    types = [norm_text(item) for item in answer_types if norm_text(item)]
    text = " ".join([task_slug, query_id, domain, scene_id]).lower()
    tokens = set(re.split(r"[_\s]+", text))
    has_count_token = "count" in tokens or any(token.endswith("count") for token in tokens)
    if len(set(types)) > 1:
        if has_count_token and "label" not in tokens:
            return "integer_count"
        return "mixed_answer_schema:" + "|".join(sorted(set(types)))
    answer_type = types[0] if types else ""
    if answer_type == "option_letter":
        return "option_letter"
    if answer_type == "boolean":
        return "boolean_label"
    if answer_type == "string":
        if any(token in text for token in ("probability", "fraction")):
            return "reduced_fraction"
        if any(token in text for token in ("list_of_labels", "label_list")):
            return "list_of_labels"
        return "string_label"
    if answer_type == "integer":
        if has_count_token:
            return "integer_count"
        return "integer_value"
    if answer_type == "number":
        return "decimal_value_1dp"
    if answer_type == "pi_expression":
        return "symbolic_expression"
    if answer_type:
        return answer_type
    if has_count_token:
        return "integer_count"
    if "label" in text:
        return "string_label"
    if "value" in text or "length" in text:
        return "integer_value"
    return "unknown_answer_schema"


def normalize_annotation_schema(annotation_types: Iterable[str]) -> tuple[str, str]:
    raw = [norm_text(item) for item in annotation_types if norm_text(item)]
    if not raw:
        return "unknown_annotation_schema", ""
    expanded: list[str] = []
    notes: list[str] = []
    modifiers = {"one", "unordered", "role"}
    for value in raw:
        parts = split_pipe(value)
        if len(parts) > 1 and all(part in modifiers or index == 0 for index, part in enumerate(parts)):
            expanded.append(parts[0])
            notes.extend(part for part in parts[1:] if part in modifiers)
        else:
            expanded.extend(parts)
    expanded = [item for item in expanded if item not in modifiers]
    unique = sorted(set(expanded))
    if len(unique) == 1:
        return unique[0], unique_join(notes)
    return "mixed_annotation_schema:" + "|".join(unique), unique_join(notes)


def signature_from_slug(slug: str, *, query_id: str, domain: str, scene_id: str) -> ProgramSignature:
    text = f"{slug} {query_id} {domain} {scene_id}".lower()
    tokens = set(re.split(r"[_\s]+", text))
    has_count_token = "count" in tokens or any(token.endswith("count") for token in tokens)

    def sig(signature_id: str, program_schema: str, definition: str, do_not_merge_when: str) -> ProgramSignature:
        return ProgramSignature(signature_id, program_schema, definition, do_not_merge_when)

    if "entity_count" in text:
        return sig(
            "count.entity",
            "count(candidate_entities)",
            "Count all visible candidate entities in the task support set.",
            "Do not merge with attribute-filtered, scoped, relation, rule-derived, or counterfactual counts.",
        )
    if "single_attribute_membership_count" in text:
        return sig(
            "count.single_attribute_membership",
            "count(filter(candidate_entities, attribute_value(entity, attribute_axis) in target_values))",
            "Count visible entities selected by membership on one attribute axis.",
            "Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs.",
        )
    if "multi_attribute_and_count" in text:
        return sig(
            "count.multi_attribute_and",
            "count(filter(candidate_entities, all(attribute_predicate(entity, predicate) for predicate in attribute_predicates)))",
            "Count visible entities satisfying multiple attribute predicates conjunctively.",
            "Do not merge with one-attribute membership, OR, XOR, exclusion, complement, scoped, or arithmetic counts.",
        )
    if "multi_attribute_or_count" in text:
        return sig(
            "count.multi_attribute_or",
            "count(filter(candidate_entities, any(attribute_predicate(entity, predicate) for predicate in attribute_predicates)))",
            "Count visible entities satisfying an inclusive OR across multiple attribute predicates.",
            "Do not merge with single-axis set membership or arithmetic sums of separate counts.",
        )
    if "multi_attribute_xor_count" in text:
        return sig(
            "count.multi_attribute_xor",
            "count(filter(candidate_entities, exactly_one(attribute_predicate(entity, predicate) for predicate in attribute_predicates)))",
            "Count visible entities satisfying exactly one of multiple attribute predicates.",
            "Do not merge with inclusive OR or exclusion/complement counts.",
        )
    if "multi_attribute_exclusion_count" in text:
        return sig(
            "count.multi_attribute_exclusion",
            "count(filter(candidate_entities, included_attribute_predicate(entity) and not excluded_attribute_predicate(entity)))",
            "Count visible entities satisfying one attribute predicate while excluding another.",
            "Do not merge with AND, OR, XOR, or complement counts.",
        )
    if "multi_attribute_complement_count" in text:
        return sig(
            "count.multi_attribute_complement",
            "count(filter(candidate_entities, not any(attribute_predicate(entity, predicate) for predicate in attribute_predicates)))",
            "Count visible entities satisfying none of a fixed set of attribute predicates.",
            "Do not merge with exclusion or XOR counts.",
        )
    if "scoped_attribute_count" in text:
        return sig(
            "count.scoped_attribute",
            "count(filter(select_scope(candidate_entities, scope_selector), attribute_value(entity, attribute_axis) in target_values))",
            "Count visible entities after selecting a spatial or structural scope, then applying an attribute selector.",
            "Do not merge with unscoped attribute counts or group-level predicate counts.",
        )
    if "relation_attribute_count" in text:
        return sig(
            "count.relation_attribute",
            "count(filter(candidate_entities, relation(entity, reference_or_region)=relation_mode and optional_attribute_predicate(entity)))",
            "Count entities selected by a visible relation to another entity, region, path, or support object.",
            "Do not merge with unscoped attribute counts or metric-reference comparisons.",
        )
    if "group_predicate_count" in text:
        return sig(
            "count.group_predicate",
            "count(filter(groups, group_predicate(group, query_parameters)))",
            "Count groups whose visible aggregate/member predicate satisfies the query condition.",
            "Do not merge with scoped object counts inside one group or direct entity counts.",
        )
    if "reference_attribute_match_count" in text:
        return sig(
            "count.reference_attribute_match",
            "count(filter(candidate_entities, attributes_match(entity, reference_entity, attribute_set)))",
            "Count entities matching a reference entity on one or more named attributes.",
            "Do not merge with reference metric relation counts.",
        )
    if "reference_metric_relation_count" in text:
        return sig(
            "count.reference_metric_relation",
            "count(filter(candidate_entities, compare(metric(entity), metric(reference_entity), relation_direction)))",
            "Count entities whose numeric/metric attribute has a relation to a reference entity.",
            "Do not merge with exact attribute-match reference counts.",
        )
    if "count_arithmetic" in text:
        return sig(
            "numeric.count_arithmetic",
            "combine(count(selector_a), count(selector_b), arithmetic_op)",
            "Combine two selector counts with a sampled arithmetic operation.",
            "Do not merge with Boolean OR, direct single-selector counts, or counterfactual counts.",
        )
    if "counterfactual_count" in text:
        return sig(
            "count.counterfactual",
            "count(filter(apply_edits(scene_entities, edit_sequence), result_selector))",
            "Apply a specified edit to the scene, then count entities selected from the edited state.",
            "Do not merge with static attribute, scoped, relation, or arithmetic counts.",
        )
    if "change_relation_count" in text:
        return sig(
            "count.change_relation",
            "count(filter(entities, visual_change_relation(entity, state_a, state_b)))",
            "Count visible entities selected by a before/after visual change relation.",
            "Do not merge with static object counts or counterfactual edits.",
        )

    if domain == "misc" and scene_id in {"abacus_match_panel", "clock_match_panel"}:
        return sig(
            "selection.option_match",
            "select_option(reference_or_rule, candidate_options)",
            "Choose an option panel/label matching a visual rule or transformation.",
            "Do not merge with free string-label lookup tasks.",
        )

    if domain == "graph" and scene_id == "binary_tree" and "lowest_common_ancestor" in text:
        return sig(
            "selection.direct_label",
            "select_label(selected_visible_support, query_parameters)",
            "Return a label selected from visible support by a stable query rule.",
            "Do not merge with numeric or count answers.",
        )
    if domain == "graph" and scene_id == "binary_tree" and "bst_path_operation_label" in text:
        return sig(
            "graph.bst_path_terminal_label",
            "label(follow_bst_path(binary_search_tree, query_key, operation_mode).terminal_node)",
            "Follow BST comparison decisions from the root to the terminal node for a search or insert-position query.",
            "Do not merge with traversal order, local relation lookup, or heap-property violation tasks.",
        )
    if domain == "graph" and scene_id == "node_link" and "common_related_node_count" in text:
        return sig(
            "graph.common_related_node_count",
            "count(intersection(relation_set(graph, reference_a, relation_mode), relation_set(graph, reference_b, relation_mode)))",
            "Count nodes in the intersection of two relation sets: common neighbors, common successors, or common predecessors for two queried nodes.",
            "Do not merge with single-reference adjacency counts, degree counts, or path-derived relation tasks.",
        )
    if domain == "graph" and scene_id == "node_link" and "unique_related_node_label" in text:
        return sig(
            "selection.adjacency_relation_label",
            "label(single(filter(nodes, relation_to_reference(node, reference_node, relation_mode))))",
            "Select the single node satisfying a visible adjacency/predecessor/successor relation to a reference node.",
            "Do not merge with adjacency-relation counts or path-derived label selection.",
        )
    if domain == "graph" and scene_id == "node_link" and "named_node_degree_value" in text:
        return sig(
            "numeric.direct_or_derived_value",
            "compute_value(selected_support, query_parameters)",
            "Return a numeric value computed from selected visible support.",
            "Do not merge with counting or label-selection tasks.",
        )
    if domain == "graph":
        if any(token in text for token in ("node_color_count", "edge_color_count", "edge_text_count", "station_membership_count")):
            return sig(
                "count.single_attribute_membership",
                "count(filter(candidate_entities, attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities selected by membership on one attribute axis.",
                "Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs.",
            )
        if "cross_color_edge_count" in text:
            return sig(
                "count.multi_attribute_and",
                "count(filter(candidate_entities, all(attribute_predicate(entity, predicate) for predicate in attribute_predicates)))",
                "Count visible entities satisfying multiple attribute predicates conjunctively.",
                "Do not merge with one-attribute membership, OR, XOR, exclusion, complement, scoped, or arithmetic counts.",
            )
        if any(token in text for token in ("component_count", "component_size", "same_component_count")):
            return sig(
                "graph.component_count_or_size",
                "component_analysis(graph, component_scope).count_or_size()",
                "Construct connected components before returning a component count or size.",
                "Do not merge with local degree, path, cut-structure, or simple attribute-count programs.",
            )
        if any(token in text for token in ("articulation_point_count", "bridge_count", "min_cut_edge_count")):
            return sig(
                "graph.cut_structure_count",
                "count(cut_structures(graph, cut_structure_kind))",
                "Count graph structures whose removal or cut property changes connectivity/flow.",
                "Do not merge with component counting, degree filters, or simple attribute counts.",
            )
        if any(token in text for token in ("degree_value_filter_count", "degree_after_removal_filter_count")):
            return sig(
                "graph.degree_filter_count",
                "count(filter(nodes(transform_optional(graph, edit)), compare(degree_metric(node), degree_target, comparator)))",
                "Count nodes satisfying a degree predicate, optionally after a graph edit.",
                "Do not merge with direct attribute counts, component analysis, or reachability programs.",
            )
        if scene_id == "binary_tree" and any(token in text for token in ("child_structure_node_count", "depth_level_node_count")):
            return sig(
                "graph.node_property_count",
                "count(filter(tree_nodes, tree_node_property(node)=target_property_value))",
                "Count tree nodes by a structural node property such as depth or child structure.",
                "Do not merge with visual node color/text counts or traversal/path programs.",
            )
        if any(token in text for token in ("exact_distance_station_count", "pipe_exact_distance_count")):
            return sig(
                "graph.path_distance_filter_count",
                "count(filter(nodes, shortest_path_length(graph, reference_node, node)=target_distance))",
                "Count graph nodes at an exact path distance from a reference node.",
                "Do not merge with simple route membership counts or shortest-path value tasks.",
            )
        if "transfer_count" in text:
            return sig(
                "graph.transfer_count",
                "count(transfers(shortest_transfer_path(route_network, source, via, target)))",
                "Count transfer events along a constrained route path.",
                "Do not merge with membership, exact-distance, or shortest-path length counts.",
            )
    if domain == "icons":
        if "single_attribute_membership_count" in text:
            return sig(
                "count.single_attribute_membership",
                "count(filter(candidate_objects, attribute_value(object, attribute_axis) in target_values))",
                "Count visible objects selected by membership on one attribute axis.",
                "Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs.",
            )
        if "multi_attribute_and_count" in text:
            return sig(
                "count.multi_attribute_and",
                "count(filter(candidate_objects, all(attribute_predicate(object, predicate) for predicate in attribute_predicates)))",
                "Count visible objects satisfying multiple attribute predicates conjunctively.",
                "Do not merge with one-attribute membership, OR, XOR, exclusion, complement, scoped, or arithmetic counts.",
            )
        if "multi_attribute_or_count" in text:
            return sig(
                "count.multi_attribute_or",
                "count(filter(candidate_objects, any(attribute_predicate(object, predicate) for predicate in attribute_predicates)))",
                "Count visible objects satisfying an inclusive OR across multiple attribute predicates.",
                "Do not merge with single-axis set membership or arithmetic sums of separate counts.",
            )
        if "multi_attribute_xor_count" in text:
            return sig(
                "count.multi_attribute_xor",
                "count(filter(candidate_objects, exactly_one(attribute_predicate(object, predicate) for predicate in attribute_predicates)))",
                "Count visible objects satisfying exactly one of multiple attribute predicates.",
                "Do not merge with inclusive OR or exclusion/complement counts.",
            )
        if "multi_attribute_exclusion_count" in text:
            return sig(
                "count.multi_attribute_exclusion",
                "count(filter(candidate_objects, included_attribute_predicate(object) and not excluded_attribute_predicate(object)))",
                "Count visible objects satisfying one attribute predicate while excluding another.",
                "Do not merge with AND, OR, XOR, or complement counts.",
            )
        if "multi_attribute_complement_count" in text:
            return sig(
                "count.multi_attribute_complement",
                "count(filter(candidate_objects, not any(attribute_predicate(object, predicate) for predicate in attribute_predicates)))",
                "Count visible objects satisfying none of a fixed set of attribute predicates.",
                "Do not merge with exclusion or XOR counts.",
            )
        if "scoped_attribute_count" in text:
            return sig(
                "count.scoped_attribute",
                "count(filter(select_scope(candidate_objects, scope_selector), attribute_value(object, attribute_axis) in target_values))",
                "Count visible objects after selecting a spatial or structural scope, then applying an attribute selector.",
                "Do not merge with unscoped attribute counts or group-level predicate counts.",
            )
        if "counterfactual_attribute_count" in text or "counterfactual_total_count" in text:
            return sig(
                "count.counterfactual",
                "count(filter(apply_edits(scene_objects, edit_sequence), result_selector))",
                "Apply a specified edit to the scene, then count objects selected from the edited state.",
                "Do not merge with static attribute, scoped, relation, or arithmetic counts.",
            )
        if "count_arithmetic" in text:
            return sig(
                "numeric.count_arithmetic",
                "combine(count(selector_a), count(selector_b), arithmetic_op)",
                "Combine two selector counts with a sampled arithmetic operation.",
                "Do not merge with Boolean OR, direct single-selector counts, or counterfactual counts.",
            )
        if "reference_metric_relation_count" in text:
            return sig(
                "count.reference_metric_relation",
                "count(filter(candidate_objects, compare(metric(object), metric(reference_object), relation_direction)))",
                "Count objects whose numeric/metric attribute has a relation to a reference object.",
                "Do not merge with exact attribute-match reference counts.",
            )
        if "reference_attribute_match_count" in text:
            return sig(
                "count.reference_attribute_match",
                "count(filter(candidate_objects, attributes_match(object, reference_object, attribute_set)))",
                "Count objects matching a reference object on one or more named attributes.",
                "Do not merge with reference metric relation counts.",
            )
        if "group_predicate_count" in text:
            return sig(
                "count.group_predicate",
                "count(filter(groups, compare(count(filter(members(group), member_selector)), threshold, comparator)))",
                "Count groups whose member count satisfies a predicate.",
                "Do not merge with scoped object counts inside one group.",
            )
        if scene_id == "icon_field" and (
            "type_frequency" in text or "most_frequent_type_count" in text or "singleton_type_count" in text
        ):
            return sig(
                "count.group_frequency",
                "count(filter(instances, frequency(group_key(instance)) satisfies frequency_role))",
                "Count icon instances selected by an icon-type frequency role.",
                "Do not merge with direct shape/type counting that does not construct type frequencies.",
            )
        if scene_id == "pair_grid" and "attribute_delta_pair_count" in text:
            return sig(
                "count.attribute_delta_pair",
                "count(filter(pair_cells, attribute_delta(pair_cell) == target_delta))",
                "Count pair-grid cells whose before-to-after pair has a named attribute-delta predicate.",
                "Do not merge with reference-transform matching against a full example pair.",
            )
        if scene_id == "pair_grid" and "reference_transform_match_count" in text:
            return sig(
                "count.reference_transform_match",
                "count(filter(pair_cells, transform_relation(pair_cell) == reference_transform_relation))",
                "Count pair-grid cells whose before-to-after transform relation matches a visible reference pair.",
                "Do not merge with named color/size attribute-delta predicates.",
            )
        if scene_id == "pair_grid" and "pair_relation_count" in text:
            return sig(
                "count.relation_match",
                "count(filter(pair_cells, relation(pair_cell) == target_relation))",
                "Count pair-grid cells whose pair relation matches a target relation.",
                "Do not merge with single-icon attribute changes outside pair cells.",
            )
        if scene_id == "paired_canvas" and "panel_set_relation_count" in text:
            return sig(
                "count.set_relation",
                "count(filter(panel_icons, set_relation(left_panel, right_panel, icon) == relation_mode))",
                "Count icons by their set relation across paired panels.",
                "Do not merge with tracked-identity attribute or movement change counts.",
            )
        if scene_id == "named_path" and "path_neighbor_label" in text:
            return sig(
                "selection.adjacency_relation_label",
                "label(select_option(candidate_icons, neighbor(path_occurrence(target_shape, occurrence_rank), direction)))",
                "Select an option label by local predecessor/successor relation on a visible path.",
                "Do not merge with adjacency-relation counts.",
            )
    if domain == "illustrations":
        if scene_id == "source_scene_edit" and "object_count_after_edit" in text:
            return sig(
                "count.counterfactual",
                "count(filter(apply_edits(scene_entities, edit_sequence), result_selector))",
                "Apply a specified edit to the scene, then count entities selected from the edited state.",
                "Do not merge with static attribute, scoped, relation, or arithmetic counts.",
            )
        if any(
            token in text
            for token in (
                "equipment_zone_count",
                "surface_object_count",
                "books_in_section_count",
                "filtered_book_in_section_count",
                "area_person_count",
                "luggage_in_boarding_area_count",
                "person_in_boarding_area_count",
            )
        ):
            return sig(
                "count.scoped_attribute",
                "count(filter(select_scope(candidate_entities, scope_selector), attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities after selecting a spatial or structural scope, then applying an attribute selector.",
                "Do not merge with unscoped attribute counts or group-level predicate counts.",
            )
        if any(
            token in text
            for token in (
                "feature_side_object_count",
                "crossing_feature_count",
                "on_feature_object_count",
                "furniture_side_count",
                "named_object_side_count",
                "equipment_use_person_count",
                "person_in_queue_count",
            )
        ):
            return sig(
                "count.relation_attribute",
                "count(filter(candidate_entities, relation(entity, reference_or_region)=relation_mode and optional_attribute_predicate(entity)))",
                "Count entities selected by a visible relation to another entity, region, path, or support object.",
                "Do not merge with unscoped attribute counts or metric-reference comparisons.",
            )
        if any(
            token in text
            for token in (
                "worker_attribute_count",
                "lit_window_count",
                "object_type_count",
                "activity_person_count",
                "playground_equipment_count",
            )
        ):
            return sig(
                "count.single_attribute_membership",
                "count(filter(candidate_entities, attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities selected by membership on one attribute axis.",
                "Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs.",
            )
        if "visible_part_count" in text:
            return sig(
                "count.entity",
                "count(candidate_entities)",
                "Count all visible candidate entities in the task support set.",
                "Do not merge with attribute-filtered, scoped, relation, rule-derived, or counterfactual counts.",
            )
        if scene_id == "image_cutout_board" and "jigsaw_piece_order" in text:
            return sig(
                "sequence.reconstruction_order",
                "sequence(order_pieces_by_reconstruction(piece_options, completed_image_layout))",
                "Return an ordered sequence of piece labels by reconstructing the source image layout.",
                "Do not merge with single-label option matching or static direct-label selection.",
            )
        if scene_id == "missing_patch" and "missing_patch_label" in text:
            return sig(
                "selection.option_match",
                "select_option(reference_or_rule, candidate_options)",
                "Choose an option panel/label matching a visual rule or transformation.",
                "Do not merge with free string-label lookup tasks.",
            )
    if domain == "pages":
        if any(
            token in text
            for token in (
                "marked_day_class_count",
                "selected_enabled_controls_in_group_count",
                "enabled_action_for_type_count",
                "selected_rows_with_status_count",
            )
        ):
            return sig(
                "count.multi_attribute_and",
                "count(filter(candidate_entities, all(attribute_predicate(entity, predicate) for predicate in attribute_predicates)))",
                "Count visible entities satisfying multiple attribute predicates conjunctively.",
                "Do not merge with one-attribute membership, OR, XOR, exclusion, complement, scoped, or arithmetic counts.",
            )
        if any(
            token in text
            for token in (
                "branch_child_count",
                "relationship_count",
            )
        ):
            return sig(
                "count.entity",
                "count(candidate_entities)",
                "Count all visible candidate entities in the task support set.",
                "Do not merge with attribute-filtered, scoped, relation, rule-derived, or counterfactual counts.",
            )
        if any(
            token in text
            for token in (
                "marked_child_count",
                "disabled_controls_in_group_count",
                "value_threshold_in_group_count",
                "subtree_descendant_count",
                "subtree_leaf_count",
            )
        ):
            return sig(
                "count.scoped_attribute",
                "count(filter(select_scope(candidate_entities, scope_selector), attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities after selecting a spatial or structural scope, then applying an attribute selector.",
                "Do not merge with unscoped attribute counts or group-level predicate counts.",
            )
        if any(
            token in text
            for token in (
                "all_cross_lane_handoff_count",
                "lane_filtered_handoff_count",
                "overlap_count",
            )
        ):
            return sig(
                "count.relation_attribute",
                "count(filter(candidate_entities, relation(entity, reference_or_region)=relation_mode and optional_attribute_predicate(entity)))",
                "Count entities selected by a visible relation to another entity, region, path, or support object.",
                "Do not merge with unscoped attribute counts or metric-reference comparisons.",
            )
        if any(token in text for token in ("filtered_node_count", "field_role_count")):
            return sig(
                "count.single_attribute_membership",
                "count(filter(candidate_entities, attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities selected by membership on one attribute axis.",
                "Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs.",
            )
        if "longer_than_reference_count" in text:
            return sig(
                "count.reference_metric_relation",
                "count(filter(candidate_entities, compare(metric(entity), metric(reference_entity), relation_direction)))",
                "Count entities whose numeric/metric attribute has a relation to a reference entity.",
                "Do not merge with exact attribute-match reference counts.",
            )
        if scene_id == "hierarchy" and "path_length_count" in text:
            return sig(
                "path.path_length_count",
                "count(edges(path_between(source_node, target_node)))",
                "Count edge steps along a visible hierarchy/tree path between two nodes.",
                "Do not merge with entity counting or maximum non-overlap scheduling.",
            )
        if scene_id == "schedule" and "maximum_non_overlapping_count" in text:
            return sig(
                "optimization.maximum_nonoverlap_count",
                "count(maximum_non_overlapping_events(schedule_events))",
                "Compute the size of a maximum non-overlapping event subset.",
                "Do not merge with direct schedule event counts or pairwise overlap counts.",
            )
        if scene_id == "form_section" and "sum_two_amounts" in text:
            return sig(
                "numeric.aggregate_sum",
                "sum(values(selected_support))",
                "Sum or total values over a selected support set.",
                "Do not merge with difference, ratio, or counterfactual programs.",
            )
        if scene_id == "form_section" and (
            "difference_two_amounts" in text or "sum_minus_amount" in text
        ):
            return sig(
                "numeric.difference_or_change",
                "difference(value(source_a), value(source_b), mode)",
                "Compute a numeric difference/change between two selected supports.",
                "Do not merge with aggregate totals or ratio/rate programs.",
            )
        if scene_id in {"profile_card_grid", "step_list", "ranked_list"} and (
            "lookup" in text
            or "entry_after" in text
            or "step_after" in text
            or "field_value" in text
            or "named_profile" in text
        ):
            return sig(
                "lookup.role_bound_label",
                "lookup_label(role_bound_visible_record, requested_field_or_target)",
                "Read a role-bound label from a visible structured record.",
                "Do not merge with ranked selection or option-image matching.",
            )
        if scene_id == "infographic" and (
            "section_total_extrema_difference" in text
            or "section_icon_total_difference" in text
        ):
            return sig(
                "numeric.difference_or_change",
                "difference(value(source_a), value(source_b), mode)",
                "Compute a numeric difference/change between two selected supports.",
                "Do not merge with aggregate totals or ratio/rate programs.",
            )
        if scene_id == "infographic" and "section_extrema_arithmetic" in text:
            return sig(
                "numeric.derived_metric",
                "derive_metric(values(selected_support), operation)",
                "Compute a derived arithmetic metric from selected visible values.",
                "Do not merge with direct value lookup or simple sum.",
            )
        if scene_id == "infographic" and (
            "value_for_named_item" in text
            or "item_for_named_value" in text
            or "detail_for_named_item" in text
        ):
            return sig(
                "lookup.role_bound_label",
                "lookup_label(role_bound_visible_record, requested_field_or_target)",
                "Read a role-bound label from a visible structured record.",
                "Do not merge with ranked selection or option-image matching.",
            )
    if domain == "geometry":
        if scene_id == "triangle_relations" and "angle_from_" in text:
            return sig(
                "formula.solve_unknown",
                "solve_formula(scene_measurements, unknown_role, formula_schema)",
                "Use a domain formula/rule schema to solve a numeric unknown.",
                "Do not merge across formula schemas that require different intermediate geometric/physical quantities.",
            )
        if scene_id in {"area_partition", "paper_fold"}:
            return sig(
                "formula.solve_unknown",
                "solve_formula(scene_measurements, unknown_role, formula_schema)",
                "Use a domain formula/rule schema to solve a numeric unknown.",
                "Do not merge across formula schemas that require different intermediate geometric/physical quantities.",
            )
        if scene_id == "graph_paper" and any(
            token in text
            for token in (
                "angle_type_count",
                "polygon_convexity_count",
                "quadrilateral_type_count",
                "shape_type_count",
                "triangle_type_count",
            )
        ):
            return sig(
                "geometry.classified_entity_count",
                "count(filter(geometric_entities, classification(entity, classification_axis)=target_class))",
                "Count visible geometric entities after applying a geometry-specific classification rule.",
                "Do not merge with raw object-type counts or formula-solving tasks.",
            )
        if scene_id == "function_graph" and "extremum_count" in text:
            return sig(
                "geometry.function_feature_count",
                "count(filter(function_graph_features, feature_type=target_feature_type))",
                "Count qualitative feature points on a visible function graph.",
                "Do not merge with generic object counts or formula-solving tasks.",
            )
        if scene_id == "coordinate_plane" and "segment_relation_count" in text:
            return sig(
                "geometry.relation_count",
                "count(filter(geometric_entity_pairs, relation(pair)=target_relation))",
                "Count visible geometric entities or pairs satisfying a geometric relation.",
                "Do not merge with raw object-type counts or formula-solving tasks.",
            )
        if scene_id == "coordinate_plane" and "collinear_point_count" in text:
            return sig(
                "geometry.relation_count",
                "count(filter(geometric_entities, relation(entity, reference_geometry)=target_relation))",
                "Count visible geometric entities satisfying a geometric relation to a reference object.",
                "Do not merge with raw object-type counts or formula-solving tasks.",
            )
        if scene_id == "coordinate_plane" and "point_in_polygon_count" in text:
            return sig(
                "geometry.region_membership_count",
                "count(filter(points, region_membership(point, target_region)=target_membership))",
                "Count points satisfying a visible geometric region-membership predicate.",
                "Do not merge with line/segment relation counts or formula-solving tasks.",
            )
        if scene_id == "coordinate_plane" and "same_quadrant_point_count" in text:
            return sig(
                "count.scoped_attribute",
                "count(filter(select_scope(candidate_entities, scope_selector), attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities after selecting a spatial or structural scope, then applying an attribute selector.",
                "Do not merge with unscoped attribute counts or group-level predicate counts.",
            )
        if scene_id == "shape_gallery" and any(token in text for token in ("congruent_count", "similar_count")):
            return sig(
                "geometry.relation_count",
                "count(filter(geometric_entities, relation(entity, reference_geometry)=target_relation))",
                "Count visible geometric entities satisfying a geometric relation to a reference object.",
                "Do not merge with raw object-type counts or formula-solving tasks.",
            )
    if domain == "physics":
        if scene_id == "circuit_equivalent":
            return sig(
                "physics.equivalent_circuit_value",
                "equivalent_component_value(component_network, component_kind, topology)",
                "Compute an equivalent resistor/capacitor value from a visible series-parallel circuit topology.",
                "Do not merge resistance and capacitance public tasks unless the formula schema, answer/annotation contract, and component kind stay identical.",
            )
        if scene_id == "collision" and "direction" in text:
            return sig(
                "physics.momentum_direction_choice",
                "option_letter(direction(momentum_conservation(inputs), output_role))",
                "Use conservation of momentum to choose the final sticky-collision direction.",
                "Do not merge with numeric velocity-component solving.",
            )
        if scene_id == "collision" and "velocity_component" in text:
            return sig(
                "physics.momentum_component_value",
                "component(final_velocity(momentum_conservation(inputs)), axis)",
                "Use conservation of momentum to compute one signed final-velocity component.",
                "Do not merge with direction-choice tasks or non-sticky collision formulas.",
            )
        if scene_id == "electrostatic_field" and "field_direction" in text:
            return sig(
                "physics.electric_field_direction_choice",
                "option_letter(direction(net_electric_field(charges, point), mode))",
                "Compute a net electric-field or force direction at a marked point.",
                "Do not merge with scalar potential or zero-field candidate selection.",
            )
        if scene_id == "electrostatic_field" and "potential_value" in text:
            return sig(
                "physics.electric_potential_value",
                "sum(point_charge_potential(charges, point, constant_policy))",
                "Compute scalar electric potential at a marked point from visible point charges.",
                "Do not merge with vector field direction or zero-field selection.",
            )
        if scene_id == "electrostatic_field" and "zero_field" in text:
            return sig(
                "physics.electric_zero_field_selection",
                "option_letter(select(candidate_points, net_electric_field(charges, candidate)=zero))",
                "Select the candidate point where the net electric field is zero.",
                "Do not merge with scalar potential or field-direction tasks.",
            )
        if scene_id == "hydraulic":
            return sig(
                "physics.pascal_law_solve",
                "solve_pascal_law(force_a, area_a, force_b, area_b, unknown_slot)",
                "Solve one missing force or piston area from Pascal-law proportionality.",
                "Do not merge with unrelated missing-value formulas just because the answer is numeric.",
            )
        if scene_id == "fluid_flow" and "continuity_speed" in text:
            return sig(
                "physics.fluid_flow_continuity_speed",
                "solve_continuity_speed(area_1, speed_1, area_2, speed_2, unknown_speed_slot)",
                "Solve one missing flow speed from visible two-station area and speed labels using A1*v1 = A2*v2.",
                "Do not merge with Bernoulli pressure-speed tasks or unrelated missing-value formulas.",
            )
        if scene_id == "lever" and "side_torque" in text:
            return sig(
                "physics.torque_sum_value",
                "sum(weight_i * distance_i for supports_on_side)",
                "Compute total torque contributed by visible weights on one side of a lever.",
                "Do not merge with balance-equation missing-weight solving.",
            )
        if scene_id == "lever" and "missing_weight" in text:
            return sig(
                "physics.torque_balance_solve",
                "solve_torque_balance(left_terms, right_terms, unknown_weight)",
                "Solve a missing lever weight by equating left and right torques.",
                "Do not merge with direct side-torque summation.",
            )
        if scene_id == "magnetic_force":
            return sig(
                "physics.lorentz_force_direction_choice",
                "option_letter(direction(charge_sign * cross(velocity, magnetic_field)))",
                "Apply the Lorentz-force right-hand-rule with charge sign to choose a force direction.",
                "Do not merge with generic option selection or unrelated direction rules.",
            )
        if scene_id == "motion_graph" and "velocity_sign" in text:
            return sig(
                "physics.motion_graph_velocity_sign_choice",
                "option_letter(classify_velocity_sign(marked_position_time_graph_interval))",
                "Classify motion direction or stationarity from the slope of a marked position-time graph interval.",
                "Do not merge with velocity-time speed-change classification or numeric graph-area computation.",
            )
        if scene_id == "motion_graph" and "speed_change" in text:
            return sig(
                "physics.motion_graph_speed_change_state_choice",
                "option_letter(classify_speed_change(marked_velocity_time_graph_interval))",
                "Classify speeding up, slowing down, or constant speed from a marked velocity-time graph interval.",
                "Do not merge with position-time velocity-sign classification or numeric graph-area computation.",
            )
        if scene_id == "pulley":
            return sig(
                "physics.pulley_force_solve",
                "solve_ideal_pulley(load_force, effort_force, support_strand_count, unknown_slot)",
                "Solve an ideal pulley load/effort force from support-strand mechanical advantage.",
                "Do not merge with other missing-value formulas that do not count supporting strands.",
            )
        if scene_id == "pv_diagram" and "work" in text:
            return sig(
                "physics.pv_work_value",
                "pressure * (final_volume - initial_volume)",
                "Compute signed work from a visible pressure-volume process.",
                "Do not merge with PV sign-choice tasks or non-PV area arithmetic.",
            )
        if scene_id == "pv_diagram" and "process_sign" in text:
            return sig(
                "physics.pv_process_sign_choice",
                "option_letter(select(processes, sign(volume_change(process))=target_sign))",
                "Choose the PV process matching an expansion/compression/no-change sign condition.",
                "Do not merge with numeric PV work computation.",
            )
        if scene_id == "ray_optics":
            return sig(
                "physics.ray_path_event_count",
                "count(filter(ray_path_events, event_role))",
                "Trace a hidden reflection path and count selected ray-path events.",
                "Do not merge with graph reachability or path-length tasks.",
            )
        if scene_id == "spring" and "missing" in text:
            return sig(
                "physics.hooke_law_solve",
                "solve_hooke_ratio(reference_weight, reference_extension, query_weight, query_extension, unknown_slot)",
                "Solve a missing spring weight or extension using proportional Hooke-law behavior.",
                "Do not merge with direct extension-difference arithmetic.",
            )
        if scene_id == "spring" and "extension_difference" in text:
            return sig(
                "physics.extension_difference_value",
                "abs(extension_a - extension_b)",
                "Compute an absolute difference between two visible spring extensions.",
                "Do not merge with missing-value Hooke-law solving.",
            )
        if scene_id == "signal_transform" and "sinusoid_component" in text:
            return sig(
                "physics.sinusoid_component_spectrum_match",
                "option_letter(select(spectrum_options, spike_components=sinusoid_components(input_waveform)))",
                "Match a sinusoidal input waveform to the one-sided magnitude spectrum with the corresponding frequency spike components.",
                "Do not merge with periodic-wave harmonic-pattern matching or pulse-width lobe matching.",
            )
        if scene_id == "signal_transform" and "periodic_harmonic" in text:
            return sig(
                "physics.periodic_harmonic_spectrum_match",
                "option_letter(select(spectrum_options, harmonic_pattern=periodic_wave_harmonics(input_waveform)))",
                "Match a periodic square, triangle, or sawtooth waveform to its harmonic support and decay pattern.",
                "Do not merge with sinusoid-component spike matching or pulse-width lobe matching.",
            )
        if scene_id == "signal_transform" and "pulse_width" in text:
            return sig(
                "physics.pulse_width_spectrum_match",
                "option_letter(select(spectrum_options, spectrum_lobe_width=inverse_pulse_width(input_waveform)))",
                "Match a rectangular pulse to the magnitude spectrum whose lobe width corresponds to the visible pulse width.",
                "Do not merge with sinusoid-component spike matching or periodic-wave harmonic-pattern matching.",
            )
        if scene_id == "wave_interference" and "interference_point" in text:
            return sig(
                "physics.wave_interference_condition_choice",
                "option_letter(select(candidate_points, interference_condition(path_difference, phase_relation)=target_condition))",
                "Choose a candidate point by applying wave-interference phase/path rules.",
                "Do not merge with numeric path-difference computation.",
            )
        if scene_id == "wave_interference" and "path_difference" in text:
            return sig(
                "physics.wave_path_difference_value",
                "abs(distance(source_a, point) - distance(source_b, point)) / unit_step",
                "Compute a visible two-source path-difference value in wave-spacing units.",
                "Do not merge with interference-condition option selection.",
            )
    if "shortest_path" in text:
        return sig(
            "path.shortest_path_value",
            "shortest_path(scene_graph, source, target)",
            "Find an optimal shortest path or its length over an explicit graph-like scene.",
            "Do not merge with reachability, longest path, route-following, or arbitrary ordered-path lookup.",
        )
    if "longest_path" in text:
        return sig(
            "path.longest_path_value",
            "longest_path(scene_graph, source, target)",
            "Find an optimal longest path under the scene's constraints.",
            "Do not merge with shortest path; the optimization objective differs.",
        )
    if any(token in text for token in ("mst", "minimum_spanning")):
        return sig("graph.minimum_spanning_tree", "minimum_spanning_tree(weighted_graph)", "Construct or score a minimum spanning tree.", "Do not merge with shortest path or flow/cut programs.")
    if "max_flow" in text:
        return sig("graph.maximum_flow", "max_flow(flow_network, source, sink)", "Compute maximum feasible source-sink flow.", "Do not merge with path-total or cut-count tasks.")
    if "min_cut" in text or "minimum_cut" in text:
        return sig("graph.minimum_cut", "minimum_cut(flow_network, source, sink)", "Find source-sink cut capacity or cut witnesses.", "Do not merge with maximum-flow value unless the answer/annotation contract is identical.")
    if "topological" in text:
        return sig("graph.topological_order", "topological_order(directed_acyclic_graph)", "Reason over a valid topological ordering.", "Do not merge with reachability or path traversal.")
    if "traversal" in text or "bfs_" in text or "dfs_" in text:
        return sig("graph.traversal_order", "traverse(graph, start, traversal_rule)", "Follow a specified graph traversal order.", "Do not merge BFS and DFS if the traversal rule is not a parameter inside one task.")
    if "component" in text and ("largest" in text or "same_component" in text or "membership" in text or "size" in text or "color_components" in text):
        return sig("graph.component_membership_or_size", "connected_components(graph, edit_or_scope).select(component_property)", "Construct connected components before selecting or counting a component property.", "Do not merge with local degree or path programs.")
    if "cycle_size" in text or "unique_cycle" in text:
        return sig("graph.cycle_structure_size", "cycle_structure(graph, query_scope).size()", "Identify a graph cycle structure and return its size.", "Do not merge with generic connected-component size or path-length programs.")
    if scene_id == "voxel_ladder" and "reachable_checkpoint_count" in text:
        return sig(
            "topology.reachable_subset_count",
            "count(filter(nodes, reachable_from(start, graph)=target_reachability))",
            "Construct a reachable subset under movement rules, then return its cardinality.",
            "Do not merge with reachability-filtered label selection; answer schema and output operation differ.",
        )
    if scene_id == "voxel_ladder" and "unreachable_checkpoint_label" in text:
        return sig(
            "topology.reachability_filtered_label",
            "label(select_node(nodes, reachable_from(start, graph)=target_reachability))",
            "Construct a reachable/unreachable subset under movement rules, then return one selected node label.",
            "Do not merge with reachable subset counts; answer schema and output operation differ.",
        )
    if "reachab" in text or "reachable" in text:
        return sig("topology.reachable_set", "reachable_set(topology, start, constraints)", "Construct the set of reachable nodes/cells/regions under movement rules.", "Do not merge with shortest path, longest path, or unconstrained direct counts.")
    if "resource_route_cost" in text:
        return sig("path.route_cost", "route_cost(path, terrain_or_resource_weights)", "Trace a visible route and aggregate its movement/resource cost.", "Do not merge with shortest-path optimization or unweighted route endpoint lookup.")
    if any(token in text for token in ("destination_after_directions", "landmark_after_route_step", "directions", "route_step")):
        return sig("path.route_following_label", "follow_route(scene_map, start, instruction_sequence).select_label(role)", "Follow an explicit visible route/instruction sequence and return a label.", "Do not merge with graph shortest-path or free nearest-object selection.")
    if "path_distance" in text or "min_distance" in text:
        return sig("path.distance_value", "distance(path_or_grid, source, target, metric)", "Compute a distance under the scene's path/grid metric.", "Do not merge with reachability count or path-option selection.")

    if "automaton" in text or "final_pose" in text or "rule_final_pose" in text:
        return sig("simulation.discrete_state_update", "simulate(discrete_state, visible_rules, steps).select(final_state_property)", "Simulate a discrete state-update system under visible rules.", "Do not merge with static lookup or single-step counterfactual edits.")

    if "minutes_after" in text or "minutes_before" in text or "offset_readout" in text:
        return sig("temporal.offset_readout", "apply_time_offset(clock_readout, offset, direction)", "Read a time display and apply a before/after offset.", "Do not merge with direct clock readout or clock comparison.")
    if "weekday_occurrence" in text or "date_of_weekday" in text:
        return sig("temporal.calendar_ordinal_lookup", "select_calendar_date(weekday, ordinal, month_grid)", "Find the date for an ordinal weekday occurrence in a visible calendar.", "Do not merge with marked-day counting.")

    if "direction_choice" in text or "force_direction" in text or "field_direction" in text or "process_sign" in text:
        return sig("physics.direction_or_sign_rule", "apply_physics_direction_rule(diagram, queried_location_or_process)", "Use a physics sign/direction rule over the diagram.", "Do not merge with numeric formula solving.")

    if "probability" in text or "event_value" in text:
        return sig("probability.event_fraction", "probability(event, visible_sample_space)", "Compute a reduced fraction from a visible finite sample space.", "Do not merge if the sample-space product/conditioning schema changes.")

    if domain == "charts":
        if scene_id == "area" and "interval_area_value" in text:
            return sig(
                "numeric.aggregate_sum",
                "sum(values(selected_support))",
                "Sum or total values over a selected support set.",
                "Do not merge with difference, ratio, or counterfactual programs.",
            )
        if scene_id == "bar_3d" and "category_extremum_gap_value" in text:
            return sig(
                "numeric.ranked_difference",
                "difference(select_by_rank(items, metric, rank_a), select_by_rank(items, metric, rank_b))",
                "Rank items by a metric, then compute a difference between selected ranked items.",
                "Do not merge with direct extremum label selection.",
            )
        if (
            (scene_id == "bar_3d" and "pairwise_comparison_count" in text)
            or (scene_id == "dumbbell" and "side_winner_count" in text)
            or (scene_id == "multiseries" and "series_comparison_count" in text)
            or (scene_id == "radar" and "profile_advantage_count" in text)
        ):
            return sig(
                "count.pairwise_comparison",
                "count(filter(items, compare(value(left, item), value(right, item), direction)))",
                "Count aligned items where one visible value/series/profile wins against another.",
                "Do not merge with one-bound threshold counts against a fixed threshold/reference value.",
            )
        if scene_id == "boxplot" and (
            "paired_median_shift_label" in text or "median_reference_label" in text
        ):
            return sig(
                "selection.extreme_metric_label",
                "label(arg_extreme(items, metric, direction))",
                "Select the label of an item with an extreme metric.",
                "Do not merge with ranked non-extreme or threshold-count tasks.",
            )
        if scene_id == "combo_mark" and "interval_threshold_condition_count" in text:
            return sig(
                "count.interval_threshold_predicate",
                "count(filter(units, interval(value(interval_series, unit), lower, upper) and compare(value(threshold_series, unit), threshold, direction)))",
                "Count units satisfying one interval predicate and one one-bound threshold predicate.",
                "Do not merge with plain interval counts or dual one-bound threshold counts.",
            )
        if scene_id == "combo_mark" and (
            "dual_threshold_condition_count" in text or "dual_condition_count" in text
        ):
            return sig(
                "count.group_predicate",
                "count(filter(groups, group_predicate(group, query_parameters)))",
                "Count groups whose visible aggregate/member predicate satisfies the query condition.",
                "Do not merge with scoped object counts inside one group or direct entity counts.",
            )
        if scene_id == "dashboard" and "source_rank_target_value" in text:
            return sig(
                "numeric.direct_or_derived_value",
                "compute_value(selected_support, query_parameters)",
                "Return a numeric value computed from selected visible support.",
                "Do not merge with counting or label-selection tasks.",
            )
        if scene_id == "dashboard" and (
            "category_panel_condition_count" in text or "dual_condition_count" in text
        ):
            return sig(
                "count.group_predicate",
                "count(filter(groups, group_predicate(group, query_parameters)))",
                "Count groups whose visible aggregate/member predicate satisfies the query condition.",
                "Do not merge with scoped object counts inside one group or direct entity counts.",
            )
        if scene_id == "dashboard" and "top_k_overlap_count" in text:
            return sig(
                "count.set_overlap_cardinality",
                "count(intersection(select_top_k(set_a, metric_a, k), select_top_k(set_b, metric_b, k)))",
                "Construct two ranked/filtered sets and count their overlap.",
                "Do not merge with direct single-set counts or aggregate-value tasks.",
            )
        if scene_id == "dumbbell" and "gap_rank_row_label" in text:
            return sig(
                "selection.ranked_item",
                "select_by_rank(items, metric, rank)",
                "Select a label/item by rank under a metric or order.",
                "Do not merge with direct lookup or unordered predicate count.",
            )
        if scene_id == "histogram" and "bin_count_between_values" in text:
            return sig(
                "count.interval_predicate",
                "count(filter(units, lower <= metric(unit) <= upper))",
                "Count visible units satisfying a two-bound interval predicate.",
                "Do not merge with one-bound threshold or categorical equality counts.",
            )
        if scene_id == "histogram" and "cumulative_rank_bin_label" in text:
            return sig(
                "numeric.ranked_value",
                "value(select_by_rank(items, metric, rank))",
                "Select an item by rank under a metric/order and return its numeric value.",
                "Do not merge with label-returning ranked selection when answer schema differs.",
            )
        if scene_id == "matrix" and "off_diagonal_confusion_label" in text:
            return sig(
                "selection.extreme_metric_label",
                "label(arg_extreme(items, metric, direction))",
                "Select the label of an item with an extreme metric.",
                "Do not merge with ranked non-extreme or threshold-count tasks.",
            )
        if scene_id == "parallel_coords" and "axis_condition_count" in text:
            return sig(
                "count.group_predicate",
                "count(filter(groups, group_predicate(group, query_parameters)))",
                "Count groups whose visible aggregate/member predicate satisfies the query condition.",
                "Do not merge with scoped object counts inside one group or direct entity counts.",
            )
        if scene_id == "table" and (
            "column_summary_value" in text or "filtered_column_mean" in text
        ):
            return sig(
                "numeric.summary_statistic",
                "summary_statistic(values(selected_support), statistic)",
                "Apply a sampled summary/aggregate statistic such as sum, mean, or median over selected visible values.",
                "Do not merge with tasks that add a different selection, filter, or nested aggregation stage.",
            )
        if scene_id == "treemap" and "repeated_leaf_aggregate_value" in text:
            return sig(
                "numeric.summary_statistic",
                "summary_statistic(values(selected_support), statistic)",
                "Apply a sampled summary/aggregate statistic such as sum or mean over selected visible values.",
                "Do not merge with tasks that aggregate a different support set or add another operation stage.",
            )
        if scene_id == "parallel_coords" and "crossing" in text:
            return sig(
                "count.intersection_or_crossing",
                "count(intersections_or_crossings(visible_primitives, scope))",
                "Count geometric or chart-primitive intersections/crossings.",
                "Do not merge with threshold or category counts.",
            )
        if scene_id == "part_whole" and "adjacent_transfer_gap" in text:
            return sig(
                "numeric.difference_or_change",
                "difference(value(source_a), value(source_b), mode)",
                "Compute a numeric difference/change between two selected supports.",
                "Do not merge with aggregate totals or ratio/rate programs.",
            )
        if scene_id == "part_whole" and "chart_order_share_to_count" in text:
            return sig(
                "numeric.derived_metric",
                "derive_metric(values(selected_support), operation)",
                "Compute a derived metric such as ratio, rate, percent/share conversion, or angle conversion.",
                "Do not merge with direct value lookup or simple sum.",
            )
        if scene_id == "region_map" and "group_filtered_region_value" in text:
            return sig(
                "numeric.aggregate_sum",
                "sum(values(selected_support))",
                "Sum or total values over a selected support set.",
                "Do not merge with difference, ratio, or counterfactual programs.",
            )
        if scene_id == "region_map" and (
            "continent_region_count" in text
            or "continent_category_region_count" in text
        ):
            return sig(
                "count.scoped_attribute",
                "count(filter(select_scope(candidate_entities, scope_selector), attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities after selecting a spatial or structural scope, then applying an attribute selector.",
                "Do not merge with unscoped attribute counts or group-level predicate counts.",
            )
        if scene_id == "region_map" and "categorical_region_count" in text:
            return sig(
                "count.single_attribute_membership",
                "count(filter(candidate_entities, attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities selected by membership on one attribute axis.",
                "Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs.",
            )
        if scene_id == "region_map" and "adjacent_numeric_threshold_count" in text:
            return sig(
                "count.adjacency_relation",
                "count(filter(units, adjacent(reference, unit) and predicate(unit)))",
                "Count units related to a reference by adjacency/neighborhood.",
                "Do not merge with unscoped predicate counts.",
            )
        if scene_id == "sankey" and "path_bottleneck_value" in text:
            return sig(
                "numeric.extreme_metric_value",
                "value(arg_extreme(items, metric, direction))",
                "Select an extreme item and return its numeric metric.",
                "Do not merge with label-returning extremum tasks when answer schema differs.",
            )
        if scene_id == "scatter_cluster" and "cluster_trend_direction_label" in text:
            return sig(
                "selection.extreme_metric_label",
                "label(arg_extreme(items, metric, direction))",
                "Select the label of an item with an extreme metric.",
                "Do not merge with ranked non-extreme or threshold-count tasks.",
            )
        if scene_id == "single_series" and (
            "projected_threshold_crossing" in text or "linear_projection" in text
        ):
            return sig(
                "sequence.projected_threshold_crossing_label",
                "select_first(project_linear_sequence(sequence, future_slots), predicate)",
                "Infer a linear step from an ordered sequence and return the first future label satisfying a threshold predicate.",
                "Do not merge with direct observed threshold scans that require no extrapolation.",
            )
        if scene_id == "single_series" and (
            "threshold_crossing" in text or "first_satisfying_threshold" in text
        ):
            return sig(
                "sequence.threshold_crossing_label",
                "select_first(sequence, predicate)",
                "Scan an ordered sequence and return the first label satisfying a threshold predicate.",
                "Do not merge with unordered threshold counts or extremum selection.",
            )
        if scene_id == "single_series" and "turning_point_count" in text:
            return sig(
                "count.sequence_or_line_pattern",
                "count(sequence_or_line_patterns(board_or_series, rule))",
                "Count contiguous runs, lines, streaks, or pattern instances.",
                "Do not merge with unordered object counts.",
            )
        if scene_id == "single_series" and (
            "monotone_streak_length" in text or "longest_monotone_streak" in text
        ):
            return sig(
                "sequence.longest_run_length",
                "max(lengths(sequence_runs(sequence, rule)))",
                "Find contiguous runs under a sequence rule and return the longest run length.",
                "Do not merge with counting run instances or direct value lookup.",
            )
        if scene_id == "single_series" and "order_statistic_value" in text:
            return sig(
                "numeric.ranked_value",
                "value(select_by_rank(items, metric, rank))",
                "Select an item by rank under a metric/order and return its numeric value.",
                "Do not merge with label-returning ranked selection when answer schema differs.",
            )
        if scene_id == "size_encoding" and "reference_size_neighbor_label" in text:
            return sig(
                "selection.nearest_label",
                "label(arg_min_distance(reference, candidates, distance_metric))",
                "Select the visible candidate nearest to a reference under a scene metric.",
                "Do not merge with generic extremum unless the metric is explicitly distance-to-reference.",
            )
        if scene_id == "small_multiple" and "top_k_by_segment_then_sum_other_segment_count" in text:
            return sig(
                "numeric.aggregate_sum",
                "sum(values(selected_support))",
                "Sum or total values over a selected support set.",
                "Do not merge with difference, ratio, or counterfactual programs.",
            )
        if scene_id == "radar" and "matching_condition_panel_count" in text:
            return sig(
                "count.group_predicate",
                "count(filter(groups, group_predicate(group, query_parameters)))",
                "Count groups whose visible aggregate/member predicate satisfies the query condition.",
                "Do not merge with scoped object counts inside one group or direct entity counts.",
            )
        if scene_id == "sunburst" and "leaf_range_count_under_parent" in text:
            return sig(
                "count.interval_predicate",
                "count(filter(units, lower <= metric(unit) <= upper))",
                "Count visible units satisfying a two-bound interval predicate.",
                "Do not merge with one-bound threshold or categorical equality counts.",
            )
        if scene_id == "table" and "categorical_value_count" in text:
            return sig(
                "count.single_attribute_membership",
                "count(filter(candidate_entities, attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities selected by membership on one attribute axis.",
                "Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs.",
            )
        if scene_id == "surface_3d" and (
            "panel_variation_label" in text or "series_trend_label" in text
        ):
            return sig(
                "selection.extreme_metric_label",
                "label(arg_extreme(items, metric, direction))",
                "Select the label of an item with an extreme metric.",
                "Do not merge with ranked non-extreme or threshold-count tasks.",
            )
        if scene_id == "waterfall" and (
            "threshold_crossing" in text
            or "first_total_at_least_threshold" in text
            or "first_total_at_most_threshold" in text
        ):
            return sig(
                "sequence.threshold_crossing_label",
                "select_first(sequence, predicate)",
                "Scan an ordered sequence and return the first label satisfying a threshold predicate.",
                "Do not merge with unordered threshold counts or extremum selection.",
            )

    if domain == "charts" and scene_id == "area" and "stacked_dominance_label" in text:
        return sig(
            "selection.extreme_metric_label",
            "label(arg_extreme(items, metric, direction))",
            "Select the label of an item with an extreme metric.",
            "Do not merge with ranked non-extreme or threshold-count tasks.",
        )

    if domain == "games":
        if scene_id == "2048" and "move_result_board_label" in text:
            return sig(
                "selection.option_match",
                "select_option(reference_or_rule, candidate_options)",
                "Choose an option panel/label matching a visual rule or transformation.",
                "Do not merge with free string-label lookup tasks.",
            )
        if scene_id == "darts" and "total_score_option_label" in text:
            return sig(
                "selection.option_value_match",
                "label(select_option(candidate_options, option_value = computed_value))",
                "Compute a scene value, then select the visible option label whose option value matches it.",
                "Do not merge with free-form numeric answers or option tasks that match only a visual pattern.",
            )
        if scene_id in {"marble_chain", "match3"} and any(
            token in text for token in ("target_pop_direction_label", "target_clear_swap_label")
        ):
            return sig(
                "selection.option_value_match",
                "label(select_option(candidate_options, option_value = computed_value))",
                "Compute a scene value, then select the visible option label whose option value matches it.",
                "Do not merge with free-form numeric answers or option tasks that match only a visual pattern.",
            )
        if scene_id in {"bowling", "minigolf"} and any(
            token in text for token in ("spare_path_label", "shot_path_label")
        ):
            return sig(
                "selection.option_match",
                "select_option(reference_or_rule, candidate_options)",
                "Choose an option panel/label matching a visual rule or transformation.",
                "Do not merge with free string-label lookup tasks.",
            )
        if any(
            token in text
            for token in (
                "blackjack_best_hand_label",
                "poker_best_hand_label",
                "trick_taking_winner_label",
                "max_pop_direction_label",
                "max_clear_swap_label",
            )
        ):
            return sig(
                "selection.extreme_metric_label",
                "label(arg_extreme(items, metric, direction))",
                "Select the label of an item with an extreme metric.",
                "Do not merge with ranked non-extreme or threshold-count tasks.",
            )
        if scene_id == "rhythm" and any(token in text for token in ("lane_choice_value", "earliest_hit_lane_label", "most_hits_lane_label")):
            return sig(
                "numeric.selected_label_value",
                "integer_label(select_item(items, selection_rule))",
                "Select a visible item or group by rule and return its numeric label/index.",
                "Do not merge with tasks returning the selected metric itself or a string label.",
            )
        if scene_id == "2048" and any(token in text for token in ("move_result", "max_tile_value", "merge_count", "score_value")):
            return sig(
                "simulation.discrete_state_update",
                "simulate(discrete_state, visible_rules, steps).select(final_state_property)",
                "Simulate a discrete state-update system under visible rules.",
                "Do not merge with static lookup or single-step counterfactual edits.",
            )
        if scene_id == "cards" and "longest_run_length" in text:
            return sig(
                "sequence.longest_run_length",
                "max(lengths(sequence_runs(sequence, rule)))",
                "Find contiguous runs under a sequence rule and return the longest run length.",
                "Do not merge with counting run instances or direct value lookup.",
            )
        if scene_id == "checkers" and "max_capture_chain_length" in text:
            return sig(
                "path.longest_path_value",
                "longest_path(scene_graph, source, target)",
                "Find an optimal longest path under the scene's constraints.",
                "Do not merge with shortest path; the optimization objective differs.",
            )
        if scene_id == "snakes_ladders" and "best_roll_value" in text:
            return sig(
                "optimization.max_reachable_value",
                "argmax_value(action_sequence, transition_rule, objective)",
                "Choose actions under visible transition rules to maximize a reachable numeric outcome.",
                "Do not merge with direct one-step transition readout.",
            )
        if scene_id == "snakes_ladders" and "move_outcome_value" in text:
            return sig(
                "simulation.discrete_state_update",
                "simulate(discrete_state, visible_rules, steps).select(final_state_property)",
                "Simulate a discrete state-update system under visible rules.",
                "Do not merge with static lookup or single-step counterfactual edits.",
            )
        if scene_id == "sudoku" and "marked_cell_value" in text:
            return sig(
                "constraint.solve_unknown_value",
                "solve_constraint(scene_state, unknown_role, rule_schema)",
                "Use visible constraint rules to solve one unknown value.",
                "Do not merge with candidate counting or rule-violation counting.",
            )
        if scene_id == "tetris" and "line_clear_count" in text:
            return sig(
                "numeric.extreme_metric_value",
                "value(arg_extreme(items, metric, direction))",
                "Select an extreme item and return its numeric metric.",
                "Do not merge with label-returning extremum tasks when answer schema differs.",
            )
        if any(token in text for token in ("higher_than_reference_count", "higher_sum_than_reference_count", "threshold_score_count")):
            return sig(
                "count.one_bound_threshold",
                "count(filter(units, compare(metric(unit), reference_or_threshold, direction)))",
                "Count visible units satisfying a one-bound comparison predicate.",
                "Do not merge with interval predicates or multi-condition predicates.",
            )
        if any(token in text for token in ("colored_piece_kind_count", "lane_color_hit_count")):
            return sig(
                "count.multi_attribute_and",
                "count(filter(candidate_entities, all(attribute_predicate(entity, predicate) for predicate in attribute_predicates)))",
                "Count visible entities satisfying multiple attribute predicates conjunctively.",
                "Do not merge with one-attribute membership, OR, XOR, exclusion, complement, scoped, or arithmetic counts.",
            )
        if any(
            token in text
            for token in (
                "piece_kind_count",
                "ring_count",
                "lane_hit_count",
                "ship_status_count",
                "moving_object_count",
                "ore_block_count",
                "group_ball_count",
                "small_board_status_count",
                "collectible_count",
            )
        ):
            return sig(
                "count.single_attribute_membership",
                "count(filter(candidate_entities, attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities selected by membership on one attribute axis.",
                "Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs.",
            )
        if any(
            token in text
            for token in (
                "legal_move_count",
                "legal_destination_count",
                "marked_piece_destination_count",
                "king_escape_square_count",
                "safe_move_count",
                "winning_move_count",
                "foundation_ready_count",
                "clear_shot_count",
                "safe_direction_count",
                "blocked_destination_count",
                "capture_move_count",
                "player_capture_piece_count",
                "extendable_first_play_count",
                "matching_end_count",
                "second_play_candidate_count",
            )
        ):
            return sig(
                "game.legal_or_safe_action_count",
                "count(filter(candidate_actions, game_rule_allows_or_satisfies(action, rule_mode)))",
                "Count visible candidate actions/moves satisfying a game legality, safety, or immediate-tactic rule.",
                "Do not merge with static piece/object attribute counts or simulated board-effect counts.",
            )
        if any(
            token in text
            for token in (
                "merge_count",
                "drop_count",
                "pop_count",
                "marked_move_flip_count",
                "shot_effect_value",
            )
        ):
            return sig(
                "game.simulated_effect_count",
                "count(effect_events(simulate(game_state, marked_action)))",
                "Simulate a marked game action and count the resulting effect events.",
                "Do not merge with static counts or legal-action counting.",
            )
        if any(
            token in text
            for token in (
                "completed_line_count",
                "exact_triple_count",
                "three_sided_box_count",
                "pieces_in_mill_count",
                "tableau_sequence_count",
                "line_result_count",
                "piece_result_count",
                "hit_row_remaining_count",
                "double_count",
                "sum_to_target_count",
                "connection_gap_count",
                "safe_lane_count",
            )
        ):
            return sig(
                "game.pattern_or_state_count",
                "count(filter(game_units, game_pattern_or_state(unit)=target_rule_state))",
                "Count game units satisfying a board/card/rule pattern or state predicate.",
                "Do not merge with legal-action or simulated-effect counts.",
            )
        if any(
            token in text
            for token in (
                "same_suit_as_reference_count",
                "blocking_ball_count",
                "group_adjacent_enemy_count",
                "path_pellet_count",
                "pellet_count_before_ghost",
                "check_attacker_count",
                "group_liberty_count",
                "projectile_intercept_count",
            )
        ):
            return sig(
                "game.reference_or_route_relation_count",
                "count(filter(game_units, relation_to_reference_or_route(unit, reference_or_route)=target_relation))",
                "Count game units selected by relation to a reference item, marked group, shot line, or route.",
                "Do not merge with unreferenced attribute counts or legal-action counts.",
            )
        if any(
            token in text
            for token in (
                "marked_cell_candidate_count",
                "repeated_digit_count",
                "unit_missing_digits_count",
                "forced_cell_count",
                "satisfied_clue_count",
            )
        ):
            return sig(
                "game.constraint_candidate_count",
                "count(filter(candidate_values_or_cells, satisfies_game_constraint(candidate, puzzle_state)))",
                "Count candidates or constraint-derived values in a rule-constrained game board.",
                "Do not merge with static attribute counts or legal move counts.",
            )

    if domain == "puzzles":
        if "single_attribute_membership_count" in text:
            return sig(
                "count.single_attribute_membership",
                "count(filter(candidate_entities, attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities selected by membership on one attribute axis.",
                "Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs.",
            )
        if "scoped_attribute_count" in text:
            return sig(
                "count.scoped_attribute",
                "count(filter(select_scope(candidate_entities, scope_selector), attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities after selecting a spatial or structural scope, then applying an attribute selector.",
                "Do not merge with unscoped attribute counts or group-level predicate counts.",
            )
        if any(token in text for token in ("bar_count_value", "cube_count")):
            return sig(
                "count.entity",
                "count(candidate_entities)",
                "Count all visible candidate entities in the task support set.",
                "Do not merge with attribute-filtered, scoped, relation, rule-derived, or counterfactual counts.",
            )
        if any(
            token in text
            for token in (
                "dominant_chord_count",
                "string_component_count",
                "cube_painted_face_count",
                "search_letter_count_value",
            )
        ):
            return sig(
                "count.single_attribute_membership",
                "count(filter(candidate_entities, attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities selected by membership on one attribute axis.",
                "Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs.",
            )
        if any(token in text for token in ("cube_visible_projection_count", "life_population_count")):
            return sig(
                "count.scoped_attribute",
                "count(filter(select_scope(candidate_entities, scope_selector), attribute_value(entity, attribute_axis) in target_values))",
                "Count visible entities after selecting a spatial or structural scope, then applying an attribute selector.",
                "Do not merge with unscoped attribute counts or group-level predicate counts.",
            )
        if "tangram_contact_count" in text:
            return sig(
                "count.relation_attribute",
                "count(filter(candidate_entities, relation(entity, reference_or_region)=relation_mode and optional_attribute_predicate(entity)))",
                "Count entities selected by a visible relation to another entity, region, path, or support object.",
                "Do not merge with unscoped attribute counts or metric-reference comparisons.",
            )
        if "cube_structure_change_count" in text:
            return sig(
                "count.counterfactual",
                "count(filter(apply_edits(scene_entities, edit_sequence), result_selector))",
                "Apply a specified edit to the scene, then count entities selected from the edited state.",
                "Do not merge with static attribute, scoped, relation, or arithmetic counts.",
            )
        if "symmetry_violation_count" in text:
            return sig(
                "puzzle.rule_violation_count",
                "count(filter(puzzle_units, violates_rule(unit, rule_schema)))",
                "Count puzzle units that violate a visible or implicit rule.",
                "Do not merge with valid-candidate counts or static attribute counts.",
            )
        if any(token in text for token in ("sliding_block_blocker_count", "tangram_contact_count")):
            return sig(
                "count.relation_attribute",
                "count(filter(candidate_entities, relation(entity, reference_or_region)=relation_mode and optional_attribute_predicate(entity)))",
                "Count entities selected by a visible relation to another entity, region, path, or support object.",
                "Do not merge with unscoped attribute counts or metric-reference comparisons.",
            )
        if any(token in text for token in ("tents_valid_candidate_count", "search_present_word_count")):
            return sig(
                "puzzle.valid_candidate_count",
                "count(filter(candidate_items, satisfies_puzzle_rule(candidate, puzzle_state)))",
                "Count candidates satisfying the puzzle's rule constraints or search rule.",
                "Do not merge with static attribute counts or rule-violation counts.",
            )
        if "turing_written_symbol_count" in text:
            return sig(
                "puzzle.simulated_attribute_count",
                "count(filter(units(simulate(puzzle_state, rule_table, steps)), attribute(unit)=target_value))",
                "Simulate a puzzle state update, then count units by an attribute in the final state.",
                "Do not merge with static attribute counts or simple counterfactual edits.",
            )
        if scene_id == "rubiks_net" and "face_color_count_label" in text:
            return sig(
                "selection.option_value_match",
                "label(select_option(candidate_options, option_value = computed_value))",
                "Compute a scene value, then select the visible option label whose option value matches it.",
                "Do not merge with free-form numeric answers or option tasks that match only a visual pattern.",
            )
        if (
            (scene_id == "cube_net" and "folded_path_face_sequence_label" in text)
            or (scene_id == "cyclic_order" and "cyclic_order_equivalent_label" in text)
            or (scene_id == "logic_grid" and "king_non_touch" in text)
            or (scene_id == "nonogram" and "candidate_solution_label" in text)
            or (scene_id == "pipe_flow" and "repair_tile" in text)
            or (scene_id == "polyomino_missing" and "marked_region_piece_label" in text)
            or (scene_id == "sokoban" and "path_validity_sequence_label" in text)
            or (scene_id == "star_battle" and "valid_cell" in text)
            or (scene_id == "tangram" and "missing_piece_label" in text)
            or (scene_id == "tents" and "missing_tent_cell_label" in text)
            or (scene_id == "toggle_grid" and "repair_switch_label" in text)
            or (scene_id == "voxel_ladder" and "checkpoint_sequence_label" in text)
            or (scene_id == "word_search" and "search_location_label" in text)
        ):
            return sig(
                "selection.option_match",
                "select_option(reference_or_rule, candidate_options)",
                "Choose an option panel/label matching a visual rule or transformation.",
                "Do not merge with free string-label lookup tasks.",
            )
        if scene_id == "cube_net" and "cube_net_face_relation_label" in text:
            return sig(
                "selection.direct_label",
                "select_label(selected_visible_support, query_parameters)",
                "Return a label selected from visible support by a stable query rule.",
                "Do not merge with numeric or count answers.",
            )
        if scene_id == "matchstick" and "matchstick_number_transform_label" in text:
            return sig(
                "selection.option_match",
                "select_option(reference_or_rule, candidate_options)",
                "Choose an option panel/label matching a visual rule or transformation.",
                "Do not merge with free string-label lookup tasks.",
            )
        if scene_id in {"polyomino_missing", "raven_matrix"} and (
            "rectangle_complement_piece" in text
            or "raven_" in text
            or "progression_matrix" in text
            or "transform_matrix" in text
            or "set_operation_matrix" in text
        ):
            return sig(
                "selection.option_match",
                "select_option(reference_or_rule, candidate_options)",
                "Choose an option panel/label matching a visual rule or transformation.",
                "Do not merge with free string-label lookup tasks.",
            )

    if domain == "three_d":
        if "single_attribute_membership_count" in text:
            return sig(
                "count.single_attribute_membership",
                "count(filter(candidate_objects, attribute_value(object, attribute_axis) in target_values))",
                "Count visible objects selected by membership on one attribute axis.",
                "Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs.",
            )
        if "multi_attribute_and_count" in text:
            return sig(
                "count.multi_attribute_and",
                "count(filter(candidate_objects, all(attribute_predicate(object, predicate) for predicate in attribute_predicates)))",
                "Count visible objects satisfying multiple attribute predicates conjunctively.",
                "Do not merge with one-attribute membership, OR, XOR, exclusion, complement, scoped, or arithmetic counts.",
            )
        if "multi_attribute_or_count" in text:
            return sig(
                "count.multi_attribute_or",
                "count(filter(candidate_objects, any(attribute_predicate(object, predicate) for predicate in attribute_predicates)))",
                "Count visible objects satisfying an inclusive OR across multiple attribute predicates.",
                "Do not merge with single-axis set membership or arithmetic sums of separate counts.",
            )
        if "multi_attribute_xor_count" in text:
            return sig(
                "count.multi_attribute_xor",
                "count(filter(candidate_objects, exactly_one(attribute_predicate(object, predicate) for predicate in attribute_predicates)))",
                "Count visible objects satisfying exactly one of multiple attribute predicates.",
                "Do not merge with inclusive OR or exclusion/complement counts.",
            )
        if "multi_attribute_exclusion_count" in text:
            return sig(
                "count.multi_attribute_exclusion",
                "count(filter(candidate_objects, included_attribute_predicate(object) and not excluded_attribute_predicate(object)))",
                "Count visible objects satisfying one attribute predicate while excluding another.",
                "Do not merge with AND, OR, XOR, or complement counts.",
            )
        if "scoped_attribute_count" in text:
            return sig(
                "count.scoped_attribute",
                "count(filter(select_scope(candidate_objects, scope_selector), attribute_value(object, attribute_axis) in target_values))",
                "Count visible objects after selecting a spatial or structural scope, then applying an attribute selector.",
                "Do not merge with unscoped attribute counts or group-level predicate counts.",
            )
        if "counterfactual_count" in text:
            return sig(
                "count.counterfactual",
                "count(filter(apply_edits(scene_objects, edit_sequence), result_selector))",
                "Apply a specified edit to the scene, then count objects selected from the edited state.",
                "Do not merge with static attribute, scoped, relation, or arithmetic counts.",
            )
        if "relation_attribute_count" in text:
            return sig(
                "count.relation_attribute",
                "count(filter(candidate_objects, relation(candidate_object, reference_object_or_region)=relation_mode))",
                "Count visible objects selected by a relation to a reference object, prop, or region.",
                "Do not merge with unreferenced attribute counts or view-metric reference comparisons.",
            )
        if scene_id == "object_cluster" and "instance_count" in text:
            return sig(
                "three_d.object_type_count",
                "count(filter(visible_3d_objects, object_type in target_object_types))",
                "Count visible 3D objects selected by prompt-facing object type.",
                "Do not merge with relation-filtered, Boolean-attribute, scoped shelf/wall, or counterfactual count programs.",
            )
        if scene_id == "object_scene":
            if "logical_predicate" in text or any(
                token in text
                for token in (
                    "attribute_conjunction_count",
                    "attribute_exclusion_count",
                    "attribute_union_count",
                    "attribute_xor_count",
                )
            ):
                return sig(
                    "three_d.boolean_attribute_count",
                    "count(filter(candidate_objects, boolean_attribute_expression(object_type, color, operator)))",
                    "Count visible 3D objects satisfying a Boolean expression over object type and/or color.",
                    "Do not merge with single-attribute counts, relation counts, or counterfactual counts.",
                )
            if "counterfactual_attribute_count" in text:
                return sig(
                    "three_d.counterfactual_attribute_count",
                    "count(filter(apply_text_edits(initial_objects, edits), selector))",
                    "Apply textual add/remove edits to a 3D object set, then count objects matching a selector.",
                    "Do not merge with static predicate counts.",
                )
            if "view_relation_count" in text or "camera_depth_relation_count" in text or "image_plane_lateral_relation_count" in text:
                return sig(
                    "three_d.reference_relation_count",
                    "count(filter(candidate_objects, compare(metric(object), metric(reference_object), relation_direction)))",
                    "Count objects satisfying a relation to a named reference object under a 3D or projected-view metric.",
                    "Do not merge with unreferenced object counts or object/proposition relation counts.",
                )
            if "spatial_relation_count" in text:
                return sig(
                    "three_d.object_prop_relation_count",
                    "count(filter(candidate_objects, relation(candidate_object, reference_prop)=relation_mode))",
                    "Count 3D objects satisfying a support/containment relation to a named prop.",
                    "Do not merge with view-relative or camera-depth reference counts.",
                )
            if "named_object_count" in text:
                return sig(
                    "three_d.object_type_count",
                    "count(filter(visible_3d_objects, object_type in target_object_types))",
                    "Count visible 3D objects selected by prompt-facing object type.",
                    "Do not merge with relation-filtered, Boolean-attribute, scoped shelf/wall, or counterfactual count programs.",
                )
            if "camera_distance_extremum" in text:
                return sig(
                    "three_d.object_camera_distance_extremum_label",
                    "option_letter(label(arg_extreme(candidate_objects, camera_distance, direction)))",
                    "Select the option label for the candidate object closest/farthest from the camera.",
                    "Do not merge with height extrema, marked-point depth extrema, or reference-nearest tasks.",
                )
            if "height_extremum" in text:
                return sig(
                    "three_d.object_height_extremum_label",
                    "option_letter(label(arg_extreme(candidate_objects, world_height, direction)))",
                    "Select the option label for the candidate object highest/lowest above the floor.",
                    "Do not merge with camera-distance extrema.",
                )
            if "marked_point_depth_extremum" in text:
                return sig(
                    "three_d.marked_point_depth_extremum_label",
                    "option_letter(label(arg_extreme(marked_points, camera_distance, direction)))",
                    "Select the visible marked point closest/farthest from the camera.",
                    "Do not merge with object extrema; the candidate set and annotation witness are point markers.",
                )
            if "marked_point_vertical_relation" in text:
                return sig(
                    "three_d.marked_point_vertical_relation_label",
                    "option_letter(label(select(marked_points, vertical_projection_matches(reference_object, marked_point))))",
                    "Select the point marker vertically aligned above a named 3D object.",
                    "Do not merge with depth-extremum point selection.",
                )
            if "landmark_correspondence" in text:
                return sig(
                    "three_d.landmark_correspondence_label",
                    "option_letter(label(select(right_view_candidate_points, landmark_id = source_landmark_id)))",
                    "Match a marked landmark on one 3D object view to the corresponding candidate point in another view.",
                    "Do not merge with whole-object multiview matching.",
                )
            if "multiview_object_match" in text:
                return sig(
                    "three_d.multiview_object_match_label",
                    "option_letter(label(select(right_view_objects, canonical_object_id = source_object_id)))",
                    "Match a boxed source object in one camera view to the same object in a second camera view.",
                    "Do not merge with landmark-level correspondence.",
                )
            if "between_references" in text:
                return sig(
                    "three_d.between_references_label",
                    "option_letter(label(select(candidate_objects, between_floor_references(candidate, reference_a, reference_b))))",
                    "Select the candidate object located in the floor-plane corridor between two named references.",
                    "Do not merge with nearest-reference or support/containment relation selection.",
                )
            if "reference_nearest" in text:
                return sig(
                    "three_d.reference_nearest_label",
                    "option_letter(label(arg_min_distance(reference_object, candidate_objects, floor_distance)))",
                    "Select the candidate object nearest to a named 3D reference object.",
                    "Do not merge with camera-distance extrema or relation selection.",
                )
            if "object_relation_label" in text:
                return sig(
                    "three_d.object_prop_relation_label",
                    "option_letter(label(select(candidate_objects, relation(candidate_object, reference_prop)=relation_mode)))",
                    "Select the candidate object satisfying a support/containment relation to a named prop.",
                    "Do not merge with count versions or view-relative relation tasks.",
                )
            if "occlusion_order" in text:
                return sig(
                    "three_d.occlusion_order_label",
                    "option_letter(label(select(candidate_objects, projected_overlap(candidate, reference) and in_front(candidate, reference))))",
                    "Select the candidate object visually in front of a named reference object.",
                    "Do not merge with floor-plane or support-relation selection.",
                )
        if scene_id == "room":
            if "wall_mounted_object_count" in text:
                return sig(
                    "three_d.wall_mounted_object_count",
                    "count(filter(room_objects, object_type=target_object_type and mounting=wall_mounted))",
                    "Count room objects of a target type that are mounted on a wall.",
                    "Do not merge with unscoped object-type counts or wall-relation label tasks.",
                )
            if "camera_distance" in text:
                return sig(
                    "three_d.wall_object_camera_distance_label",
                    "option_letter(label(arg_min_distance(camera, wall_object_candidates, camera_distance)))",
                    "Select the wall-mounted object candidate nearest to the camera.",
                    "Do not merge with same-wall or wall-side relation selection.",
                )
            if "same_wall" in text:
                return sig(
                    "three_d.same_wall_reference_label",
                    "option_letter(label(select(wall_object_candidates, wall(candidate)=wall(reference_object))))",
                    "Select the wall-mounted object sharing the named reference object's wall.",
                    "Do not merge with wall-side coordinate selection.",
                )
            if "side_relation" in text:
                return sig(
                    "three_d.wall_side_relation_label",
                    "option_letter(label(select(wall_object_candidates, same_wall(candidate, reference_object) and compare(wall_axis(candidate), wall_axis(reference_object), direction))))",
                    "Select the wall-mounted object left/right of a named reference on the same wall plane.",
                    "Do not merge with same-wall membership selection.",
                )
        if scene_id == "street":
            if "intersection_nearest" in text:
                return sig(
                    "three_d.intersection_nearest_label",
                    "option_letter(label(arg_min_distance(intersection_center, street_object_candidates, ground_distance)))",
                    "Select the street object closest to the intersection center.",
                    "Do not merge with lane-forward or road-arm membership selection.",
                )
            if "lane_ahead" in text:
                return sig(
                    "three_d.lane_forward_path_label",
                    "option_letter(label(arg_min(filter(candidate_objects, ahead_in_lane(reference_vehicle, object)), forward_distance)))",
                    "Select the nearest object ahead of a reference vehicle in its lane corridor.",
                    "Do not merge with generic nearest-reference selection.",
                )
            if "same_road_arm" in text:
                return sig(
                    "three_d.same_road_arm_reference_label",
                    "option_letter(label(select(street_object_candidates, road_arm(candidate)=road_arm(reference_object))))",
                    "Select the street object sharing the reference object's road arm.",
                    "Do not merge with distance-to-intersection or lane-forward tasks.",
                )
        if scene_id == "warehouse":
            if "robot_forward_path" in text:
                return sig(
                    "three_d.robot_forward_path_label",
                    "option_letter(label(arg_min(filter(warehouse_objects, ahead_in_robot_path(robot, object)), forward_distance)))",
                    "Select the first object in the robot's forward path corridor.",
                    "Do not merge with nearest-reference robot/object selection.",
                )
            if "nearest_candidate_to_reference" in text or "closest_object_to_robot" in text or "closest_robot_to_reference" in text:
                return sig(
                    "three_d.nearest_candidate_to_reference_label",
                    "option_letter(label(arg_min_distance(reference_entity, candidate_entities, floor_gap)))",
                    "Select the candidate entity nearest to the reference entity in the warehouse floor plane.",
                    "Do not merge with path-corridor or shelf-level tasks.",
                )
            if "shelf_level_object_count" in text:
                return sig(
                    "three_d.shelf_level_object_count",
                    "count(filter(shelf_items, rack_color=target_rack_color and shelf_level=target_shelf_level))",
                    "Count shelf items on a named colored rack and shelf level.",
                    "Do not merge with unscoped warehouse object counts.",
                )

    if "counterfactual" in text or "after_added" in text or "after_removed" in text or "remove_" in text or "reverse_" in text or "after_" in text and "count" in text:
        return sig("counterfactual.transform_then_answer", "answer(transform(scene_state, edit), query)", "Apply a specified hypothetical edit before computing the answer.", "Do not merge with direct readout/count tasks without a scene transform.")

    if ("interval" in text or "in_interval" in text) and has_count_token:
        return sig("count.interval_predicate", "count(filter(units, lower <= metric(unit) <= upper))", "Count visible units satisfying a two-bound interval predicate.", "Do not merge with one-bound threshold or categorical equality counts.")
    if "in_interval" in text:
        return sig("count.interval_predicate", "count(filter(units, lower <= metric(unit) <= upper))", "Count visible units satisfying a two-bound interval predicate.", "Do not merge with one-bound threshold or categorical equality counts.")
    if "threshold" in text and has_count_token:
        return sig("count.one_bound_threshold", "count(filter(units, compare(metric(unit), threshold, direction)))", "Count visible units satisfying a one-bound threshold predicate.", "Do not merge with interval predicates or multi-condition predicates.")
    if any(token in text for token in ("smaller", "larger", "greater", "less")) and has_count_token:
        return sig("count.one_bound_threshold", "count(filter(units, compare(metric(unit), reference_or_threshold, direction)))", "Count visible units satisfying a one-bound comparison predicate.", "Do not merge with interval predicates or multi-condition predicates.")
    if any(token in text for token in ("condition_count", "filtered_count", "predicate_count", "conjunction_count", "union_count", "xor_count", "exclusion_count", "dual_condition_count")):
        return sig("count.composite_predicate", "count(filter(units, predicate_set(unit, query_parameters)))", "Count units satisfying a compound or attribute-binding predicate.", "Do not merge with single-attribute counts if the program must bind multiple attributes or roles.")
    if "adjacent" in text or "neighbor" in text:
        return sig("count.adjacency_relation", "count(filter(units, adjacent(reference, unit) and predicate(unit)))", "Count units related to a reference by adjacency/neighborhood.", "Do not merge with unscoped predicate counts.")
    if "intersection_count" in text or "crossing_count" in text or "crossings_" in text:
        return sig("count.intersection_or_crossing", "count(intersections_or_crossings(visible_primitives, scope))", "Count geometric or chart-primitive intersections/crossings.", "Do not merge with threshold or category counts.")
    if "line_count" in text or "streak" in text or "run_count" in text:
        return sig("count.sequence_or_line_pattern", "count(sequence_or_line_patterns(board_or_series, rule))", "Count contiguous runs, lines, streaks, or pattern instances.", "Do not merge with unordered object counts.")
    if any(token in text for token in ("smaller", "larger", "greater", "less")):
        return sig("count.one_bound_threshold", "count(filter(units, compare(metric(unit), reference_or_threshold, direction)))", "Count visible units satisfying a one-bound comparison predicate.", "Do not merge with interval predicates or multi-condition predicates.")
    if has_count_token:
        return sig("count.direct_cardinality", "count(filter(units, query_attribute_or_role))", "Count visible units selected by a single role, attribute, or narrow predicate.", "Do not merge with interval, path, counterfactual, or multi-step derived counts.")

    if "arithmetic" in text:
        return sig("numeric.derived_metric", "derive_metric(values(selected_support), operation)", "Compute a derived arithmetic metric from selected visible values.", "Do not merge with direct value lookup or simple sum.")
    if "rank" in text or "order_statistic" in text or "ordinal" in text or "nth_" in text:
        if "difference" in text or "gap" in text or "delta" in text:
            return sig("numeric.ranked_difference", "difference(select_by_rank(items, metric, rank_a), select_by_rank(items, metric, rank_b))", "Rank items by a metric, then compute a difference between selected ranked items.", "Do not merge with direct extremum label selection.")
        return sig("selection.ranked_item", "select_by_rank(items, metric, rank)", "Select a label/item by rank under a metric or order.", "Do not merge with direct lookup or unordered predicate count.")
    if "extremum" in text or "extrema" in text or "highest" in text or "lowest" in text or "maximum" in text or "minimum" in text or "fewest" in text or "most" in text:
        if "value" in text and not "label" in text:
            return sig("numeric.extreme_metric_value", "value(arg_extreme(items, metric, direction))", "Select an extreme item and return its numeric metric.", "Do not merge with label-returning extremum tasks when answer schema differs.")
        return sig("selection.extreme_metric_label", "label(arg_extreme(items, metric, direction))", "Select the label of an item with an extreme metric.", "Do not merge with ranked non-extreme or threshold-count tasks.")

    if "region_point" in text or "annulus" in text or "half_plane" in text or "vertical_strip" in text:
        return sig("geometry.region_membership_selection", "select_point_satisfying_region_predicate(point_options, geometric_region_rule)", "Choose a point/label satisfying a visible geometric region predicate.", "Do not merge with formula-derived coordinate computation.")
    if "nearest" in text or "closest" in text:
        return sig("selection.nearest_label", "label(arg_min_distance(reference, candidates, distance_metric))", "Select the visible candidate nearest to a reference under a scene metric.", "Do not merge with generic extremum unless the metric is explicitly distance-to-reference.")
    if "violation" in text:
        return sig("selection.rule_violation", "select_rule_violation(sequence_or_grid, rule)", "Find the visible item/cell/index that violates a displayed or implicit rule.", "Do not merge with completion or valid-option selection.")
    if "same_pair_transform" in text or "pair_transform" in text or "reference_transform_match" in text:
        return sig("relation.pair_transform_match", "select_pair_matching_transform(reference_pair, candidate_pairs, transform_rule)", "Select or count pairs matching a transformation relation.", "Do not merge with single-object attribute matching.")

    if any(token in text for token in ("difference", "gap", "delta", "change", "shift")):
        return sig("numeric.difference_or_change", "difference(value(source_a), value(source_b), mode)", "Compute a numeric difference/change between two selected supports.", "Do not merge with aggregate totals or ratio/rate programs.")
    if any(token in text for token in ("sum", "total", "aggregate", "mean", "median", "average")):
        if "mean" in text or "median" in text or "average" in text:
            return sig("numeric.summary_statistic", "summary_statistic(values(selected_support), statistic)", "Apply a sampled summary/aggregate statistic such as sum, mean, median, or average over selected visible values.", "Do not merge with tasks that add a different selection, filter, or nested aggregation stage.")
        return sig("numeric.aggregate_sum", "sum(values(selected_support))", "Sum or total values over a selected support set.", "Do not merge with difference, ratio, or counterfactual programs.")
    if "interval_mass" in text or "mass" in tokens:
        return sig("numeric.aggregate_sum", "sum(values(selected_support))", "Sum or total values over a selected support set.", "Do not merge with difference, ratio, or counterfactual programs.")
    if any(token in tokens for token in ("ratio", "rate", "percent", "share", "angle")):
        return sig("numeric.derived_metric", "derive_metric(values(selected_support), operation)", "Compute a derived metric such as ratio, rate, percent/share conversion, or angle conversion.", "Do not merge with direct value lookup or simple sum.")
    if "value" in text or "length" in text or "area" in text or "volume" in text or "perimeter" in text or "bearing" in text or "radius_from_chord" in text or "mechanical_advantage" in text:
        if domain in {"geometry", "physics"}:
            return sig("formula.solve_unknown", "solve_formula(scene_measurements, unknown_role, formula_schema)", "Use a domain formula/rule schema to solve a numeric unknown.", "Do not merge across formula schemas that require different intermediate geometric/physical quantities.")
        return sig("numeric.direct_or_derived_value", "compute_value(selected_support, query_parameters)", "Return a numeric value computed from selected visible support.", "Do not merge with counting or label-selection tasks.")

    if any(token in text for token in ("lookup", "field", "detail", "target_label", "entry_label", "step_detail", "after_named_step")):
        return sig("lookup.role_bound_label", "lookup_label(role_bound_visible_record, requested_field_or_target)", "Read a role-bound label from a visible structured record.", "Do not merge with ranked selection or option-image matching.")
    if "interference_point" in text:
        return sig("physics.interference_rule_choice", "apply_wave_interference_rule(diagram, candidate_points)", "Choose a point using wave-interference path/phase rules.", "Do not merge with numeric path-difference computation.")
    if "match" in text or "option" in text or "result_label" in text or "completion_label" in text:
        return sig("selection.option_match", "select_option(reference_or_rule, candidate_options)", "Choose an option panel/label matching a visual rule or transformation.", "Do not merge with free string-label lookup tasks.")
    if "label" in text:
        return sig("selection.direct_label", "select_label(selected_visible_support, query_parameters)", "Return a label selected from visible support by a stable query rule.", "Do not merge with numeric or count answers.")

    return sig("program.unclassified_direct", f"direct_answer({slug})", "Fallback direct-answer program; review manually if this appears often.", "Do not merge without manual inspection.")


def detailed_program_schema(signature: ProgramSignature, *, slug: str, query_id: str, domain: str, scene_id: str) -> str:
    """Return the exact task-contract program schema.

    `ProgramSignature` is the reusable canonical family.  This detail string is
    the task-contract program field and keeps operand/scope differences visible
    so canonical terminology reuse does not accidentally imply public merges.
    """

    scope = sanitize_slug(slug)
    query = sanitize_slug(query_id)
    program_schema = signature.program_schema
    three_d_schema = (
        _three_d_detailed_program_schema(scene_id=scene_id, scope=scope, query=query)
        if domain == "three_d"
        else ""
    )
    if three_d_schema:
        program_schema = three_d_schema
    elif domain == "charts" and scene_id == "area" and scope == "interval_area_value":
        program_schema = "sum(pair_mean(adjacent_values(series, x_interval_start_label, x_interval_end_label)))"
    elif domain == "charts" and scene_id == "area" and scope == "stacked_band_interval_sum_value":
        program_schema = "sum(values(category, x_interval_start_label, x_interval_end_label))"
    elif domain == "charts" and scene_id == "area" and scope == "stacked_band_dominance_label":
        program_schema = (
            "label(arg_extreme(categories, "
            "sum(values(category, x_interval_start_label, x_interval_end_label)), "
            "direction=highest))"
        )
    elif domain == "charts" and scene_id == "annotated_series" and scope == "callout_endpoint_change_value":
        program_schema = "difference(value(callout_mark), value(endpoint_mark), mode=absolute)"
    elif domain == "charts" and scene_id == "bar_3d" and scope == "pairwise_comparison_count":
        program_schema = "count(filter(categories, compare(value(series_a, category), value(series_b, category), direction)))"
    elif domain == "charts" and scene_id == "bar_3d" and scope in {"series_total_value", "series_category_scope_total_value"}:
        program_schema = "sum(values(series, category_scope))"
    elif domain == "charts" and scene_id == "bar_3d" and scope == "category_total_value":
        program_schema = "sum(values(category, all_displayed_series))"
    elif domain == "charts" and scene_id == "bar_3d" and scope == "series_interval_total_value":
        program_schema = "sum(values(series, category_scope))"
    elif domain == "charts" and scene_id == "bar_3d" and scope == "category_extremum_gap_value":
        program_schema = "difference(max(values(category, all_displayed_series)), min(values(category, all_displayed_series)), mode=absolute)"
    elif domain == "charts" and scene_id == "bar_3d" and scope == "category_total_gap_value":
        program_schema = "difference(sum(values(category_a, all_displayed_series)), sum(values(category_b, all_displayed_series)), mode=absolute)"
    elif domain == "charts" and scene_id == "bar_3d" and scope == "series_total_gap_value":
        program_schema = "difference(sum(values(series_a, all_displayed_categories)), sum(values(series_b, all_displayed_categories)), mode=absolute)"
    elif domain == "charts" and scene_id == "boxplot" and scope == "paired_median_shift_label":
        program_schema = "label(arg_extreme(matched_labels, median(after_label)-median(before_label), direction))"
    elif domain == "charts" and scene_id == "boxplot" and scope == "median_reference_label":
        program_schema = "label(arg_extreme(boxplots, distance(median(boxplot), reference_quartile), direction=furthest))"
    elif domain == "charts" and scene_id == "boxplot" and scope == "median_rank_difference_value":
        program_schema = "difference(value(select_by_rank(boxplots, metric=median, rank_a)), value(select_by_rank(boxplots, metric=median, rank_b)), mode=absolute)"
    elif domain == "charts" and scene_id == "candlestick" and scope == "counterfactual_close_value":
        program_schema = "value(transform(candle(target_period), body_size_delta, keep_open=True, keep_direction=True).close)"
    elif domain == "charts" and scene_id == "candlestick" and scope == "range_extremum_label":
        program_schema = "label(arg_extreme(candles, range_metric, direction))"
    elif domain == "charts" and scene_id == "combo_mark" and scope == "dual_threshold_condition_count":
        program_schema = "count(filter(categories, compare(value(primary_series, category), primary_threshold, primary_direction) and compare(value(line_series, category), line_threshold_or_bounds, line_direction)))"
    elif domain == "charts" and scene_id == "combo_mark" and scope == "interval_threshold_condition_count":
        program_schema = "count(filter(categories, interval(value(interval_series, category), lower_bound, upper_bound) and compare(value(threshold_series, category), threshold, direction)))"
    elif domain == "charts" and scene_id == "combo_mark" and scope == "cross_mark_difference_value":
        program_schema = "difference(value(series_a, target_category), value(series_b, target_category), mode=series_order)"
    elif domain == "charts" and scene_id == "curve_panels" and scope == "curve_intersection_count":
        program_schema = "count(intersections(series_a, series_b, subplot))"
    elif domain == "charts" and scene_id == "density_curve" and scope == "mean_extremum_label":
        program_schema = "label(arg_extreme(curves, metric=mean_x(curve), direction))"
    elif domain == "charts" and scene_id == "density_curve" and scope == "mode_location_extremum_label":
        program_schema = "label(arg_extreme(curves, metric=mode_x(curve), direction))"
    elif domain == "charts" and scene_id == "density_curve" and scope == "interval_mass_extremum_label":
        program_schema = "label(arg_extreme(curves, metric=integral(density(curve), interval), direction))"
    elif domain == "charts" and scene_id == "density_curve" and scope == "density_at_x_extremum_label":
        program_schema = "label(arg_extreme(curves, metric=density_at(curve, reference_x), direction))"
    elif domain == "charts" and scene_id == "dashboard" and scope == "dual_condition_count":
        program_schema = "count(filter(categories, compare(value(panel_a, category), threshold_a, direction_a) and compare(value(panel_b, category), threshold_b, direction_b)))"
    elif domain == "charts" and scene_id == "dashboard" and scope == "category_panel_condition_count":
        program_schema = "count(filter(panels, compare(value(panel, category), threshold, direction)))"
    elif domain == "charts" and scene_id == "dashboard" and scope == "top_k_overlap_count":
        program_schema = "count(intersection(select_top_k(categories, value(panel_a, category), k, rank_direction), select_top_k(categories, value(panel_b, category), k, rank_direction)))"
    elif domain == "charts" and scene_id == "dashboard" and scope == "dual_source_target_sum_value":
        program_schema = "sum(values(target_panel, categories=[select_by_rank(source_panel_a, rank_a), select_by_rank(source_panel_b, rank_b)]))"
    elif domain == "charts" and scene_id == "dashboard" and scope == "source_rank_target_value":
        program_schema = "value(target_panel, category=select_by_rank(source_panel, rank))"
    elif domain == "charts" and scene_id == "dashboard" and scope == "source_rank_difference_value":
        program_schema = "difference(value(source_panel, category=select_by_rank(source_panel, rank)), value(target_panel, category=select_by_rank(source_panel, rank)), mode=absolute)"
    elif domain == "charts" and scene_id == "dumbbell" and scope == "gap_rank_row_label":
        program_schema = "label(select_by_rank(rows, metric=abs(value_a(row)-value_b(row)), rank))"
    elif domain == "charts" and scene_id == "dumbbell" and scope == "side_winner_count":
        program_schema = "count(filter(rows, compare(value_a(row)-value_b(row), minimum_gap, side_direction)))"
    elif domain == "charts" and scene_id == "histogram" and scope == "bin_count_between_values":
        program_schema = "count(filter(bins, lower <= x_axis_value(bin) <= upper))"
    elif domain == "charts" and scene_id == "histogram" and scope == "cumulative_rank_bin_label":
        program_schema = "x_axis_value(bin_containing_rank(cumulative_counts, rank))"
    elif domain == "charts" and scene_id == "matrix" and scope == "off_diagonal_confusion_label":
        program_schema = "label(arg_extreme(off_diagonal_cells(actual_row), cell_value, direction=highest))"
    elif domain == "charts" and scene_id == "multiseries" and scope == "series_comparison_count":
        program_schema = "count(filter(categories, compare(value(series_a, category), value(series_b, category), direction)))"
    elif domain == "charts" and scene_id == "parallel_coords" and scope == "axis_condition_count":
        program_schema = "count(filter(profiles, compare(value(axis_a, profile), threshold, direction_a) and compare(value(axis_b, profile), threshold, direction_b)))"
    elif domain == "charts" and scene_id == "parallel_coords" and scope == "all_crossings_between_adjacent_axes":
        program_schema = "count(order_reversal_pairs(profiles, adjacent_axis_a, adjacent_axis_b))"
    elif domain == "charts" and scene_id == "scatter_cluster" and scope == "cluster_area_rank_label":
        program_schema = "label(select_by_rank(clusters, metric=displayed_shaded_footprint_area(cluster), rank))"
    elif domain == "charts" and scene_id == "scatter_facet_grid" and scope == "region_density_extremum_label":
        program_schema = "label(arg_extreme(panels, metric=local_point_density(panel, region), direction=highest))"
    elif domain == "charts" and scene_id == "radar" and scope == "matching_condition_panel_count":
        program_schema = "count(filter(panels, count(filter(spokes, compare(value(panel, spoke), threshold, direction))) >= minimum_spoke_count))"
    elif domain == "charts" and scene_id == "radar" and scope == "profile_advantage_count":
        program_schema = "count(filter(spokes, compare(value(profile_a, spoke), value(profile_b, spoke), direction)))"
    elif domain == "charts" and scene_id == "part_whole" and scope == "adjacent_transfer_gap_value":
        program_schema = "difference(value(source_category)-transfer_amount, value(adjacent_category)+transfer_amount, mode=absolute)"
    elif domain == "charts" and scene_id == "part_whole" and scope == "contiguous_chart_order_sum":
        program_schema = "sum(values(categories_between(chart_order, start_category, end_category, direction)))"
    elif domain == "charts" and scene_id == "part_whole" and scope == "positional_segment_share_sum":
        program_schema = "sum(values(positional_segments(anchor_category, positions)))"
    elif domain == "charts" and scene_id == "part_whole" and scope == "chart_order_share_to_count":
        program_schema = "round(total_count * sum(values(categories_between(chart_order, start_category, end_category, direction))) / 100)"
    elif domain == "charts" and scene_id == "part_whole" and scope == "sector_share_to_angle":
        program_schema = "round(360 * sum(values(categories_between(chart_order, start_category, end_category, direction))) / 100)"
    elif domain == "charts" and scene_id == "pictogram" and scope == "group_difference_value":
        program_schema = "difference(unit_scale * mark_count(category_a), unit_scale * mark_count(category_b), mode=absolute)"
    elif domain == "charts" and scene_id == "region_map" and scope == "group_filtered_region_value":
        program_schema = "sum(values(filter(regions, geographic_group and compare(value(region), threshold, direction))))"
    elif domain == "charts" and scene_id == "region_map" and scope == "named_region_set_total_value":
        program_schema = "sum(values(named_region_set))"
    elif domain == "charts" and scene_id == "region_map" and scope == "adjacent_numeric_threshold_count":
        program_schema = "count(filter(neighbor_regions(reference_region), compare(value(region), threshold, direction)))"
    elif domain == "charts" and scene_id == "region_map" and scope == "adjacent_category_count":
        program_schema = "count(filter(neighbor_regions(reference_region), category(region)=target_category))"
    elif domain == "charts" and scene_id == "region_map" and scope == "adjacent_same_category_count":
        program_schema = "count(filter(neighbor_regions(reference_region), category(region)=category(reference_region)))"
    elif domain == "charts" and scene_id == "region_map" and scope == "continent_region_count":
        program_schema = "count(filter(regions, continent=target_continent))"
    elif domain == "charts" and scene_id == "region_map" and scope.startswith("continent_predicate_region_count"):
        program_schema = "count(filter(regions, continent=target_continent and predicate(region)))"
    elif domain == "charts" and scene_id == "region_map" and scope == "categorical_region_count":
        program_schema = "count(filter(regions, category(region)=target_category))"
    elif domain == "charts" and scene_id == "sankey" and scope == "path_bottleneck_value":
        program_schema = "min(values(path_edges(source_node, middle_node, target_node)))"
    elif domain == "charts" and scene_id == "sankey" and scope == "path_flow_difference":
        program_schema = "difference(value(path_edge_a), value(path_edge_b), mode=absolute)"
    elif domain == "charts" and scene_id == "scatter_readout" and scope == "series_y_anchor_other_series_value":
        program_schema = "value(comparison_series, x_axis_label=lookup_x(target_series, target_y_value))"
    elif domain == "charts" and scene_id == "scatter_readout" and scope == "series_pair_value_gap_at_x":
        program_schema = "difference(value(series_a, x_axis_label), value(series_b, x_axis_label), mode=absolute)"
    elif domain == "charts" and scene_id == "single_series" and scope == "monotone_streak_length":
        program_schema = "max(lengths(monotone_runs(series, direction)))"
    elif domain == "charts" and scene_id == "single_series" and scope == "turning_point_count":
        program_schema = "count(turning_points(ordered_series, kind))"
    elif domain == "charts" and scene_id == "single_series" and scope == "remaining_mean_after_removal":
        program_schema = "mean(values(filter(labels, label not in removed_labels)))"
    elif domain == "charts" and scene_id == "single_series" and scope == "target_share_after_removal":
        program_schema = "round(100 * value(target_label) / sum(values(filter(labels, label not in removed_labels))))"
    elif domain == "charts" and scene_id == "single_series" and scope == "baseline_from_aggregate_percent_change":
        program_schema = "baseline_from_percent_change(sum(values(aggregate_labels)), percent_change)"
    elif domain == "charts" and scene_id == "single_series" and scope == "endpoint_change_value":
        program_schema = "difference(value(end_label), value(start_label), mode=absolute_difference)"
    elif domain == "charts" and scene_id == "single_series" and scope == "interval_rate_value":
        program_schema = "round((value(end_label)-value(start_label)) / (index(end_label)-index(start_label)))"
    elif domain == "charts" and scene_id == "single_series" and scope == "order_statistic_value":
        program_schema = "value(select_by_rank(ordered_marks, metric=value, rank))"
    elif domain == "charts" and scene_id == "single_series" and scope == "observed_threshold_crossing_label":
        program_schema = "select_first_label(ordered_marks, compare(value(mark), threshold, direction))"
    elif domain == "charts" and scene_id == "single_series" and scope == "projected_threshold_crossing_label":
        program_schema = "select_first_label(project_linear_sequence(ordered_marks, future_slots), compare(projected_value(label), threshold, direction))"
    elif domain == "charts" and scene_id == "size_encoding" and scope == "reference_size_neighbor_label":
        program_schema = "label(arg_min_distance(reference_item, filter(items, category=same_category), metric=size_value_difference))"
    elif domain == "charts" and scene_id == "small_multiple" and scope == "conditioned_panel_sum_from_percent":
        program_schema = "sum(percent_to_count(value(panel, target_segment), panel_total) for panel in filter(panels, compare(value(panel, condition_segment), threshold, direction)))"
    elif domain == "charts" and scene_id == "small_multiple" and scope == "top_k_by_segment_then_sum_other_segment_count":
        program_schema = "sum(percent_to_count(value(panel, target_segment), panel_total) for panel in select_top_k(panels, value(panel, rank_segment), k, rank_direction))"
    elif domain == "charts" and scene_id == "small_multiple" and scope == "average_top_k_minus_average_bottom_k":
        program_schema = "difference(mean(values(select_top_k(panels, rank_segment, k, highest), target_segment)), mean(values(select_top_k(panels, rank_segment, k, lowest), target_segment)), mode=signed)"
    elif domain == "charts" and scene_id == "small_multiple" and scope == "composition_shift_l1_distance":
        program_schema = "sum_absolute(difference(value(start_panel, segment), value(end_panel, segment), mode=signed) for segment in shared_segments)"
    elif domain == "charts" and scene_id == "sunburst" and scope == "leaf_range_count_under_parent":
        program_schema = "count(filter(leaves_under_parent(parent_category), lower <= value(leaf) <= upper))"
    elif domain == "charts" and scene_id == "sunburst" and scope == "parent_total_value":
        program_schema = "sum(values(leaves_under_parent(parent_category)))"
    elif domain == "charts" and scene_id == "surface_3d" and scope == "panel_variation_label":
        program_schema = "label(arg_extreme(panels, vertical_range(panel), direction=highest))"
    elif domain == "charts" and scene_id == "surface_3d" and scope == "series_trend_label":
        program_schema = "label(arg_extreme(series, endpoint_change(series), direction))"
    elif domain == "charts" and scene_id == "table" and scope == "column_summary_value":
        program_schema = "summary_statistic(values(numeric_column), statistic)"
    elif domain == "charts" and scene_id == "table" and scope == "filtered_column_mean":
        program_schema = "mean(values(filter(rows, categorical_column=filter_value), numeric_column))"
    elif domain == "charts" and scene_id == "table" and scope == "categorical_value_count":
        program_schema = "count(filter(rows, value(category_column, row)=target_category))"
    elif domain == "charts" and scene_id == "table" and scope == "absolute_difference_between_rows_over_year_interval":
        program_schema = "difference(sum(values(row_a, year_interval)), sum(values(row_b, year_interval)), mode=absolute)"
    elif domain == "charts" and scene_id == "table" and scope == "sum_absolute_differences_between_rows_over_year_interval":
        program_schema = "sum_absolute(difference(value(row_a, year), value(row_b, year), mode=absolute) for year in year_interval)"
    elif domain == "charts" and scene_id == "treemap" and scope == "group_total_value":
        program_schema = "sum(values(children_under_parent(parent_category)))"
    elif domain == "charts" and scene_id == "treemap" and scope == "repeated_leaf_aggregate_value":
        program_schema = "summary_statistic(values(child_label_across_parents(child_label)), statistic)"
    elif domain == "charts" and scene_id == "violin" and scope == "modality_label":
        program_schema = "label(filter(distributions, modality=two_clear_bulges))"
    elif domain == "charts" and scene_id == "waterfall" and scope == "remove_step_final_total":
        program_schema = "final_total(transform(contributions, remove_step=target_step))"
    elif domain == "charts" and scene_id == "waterfall" and scope == "reverse_step_final_total":
        program_schema = "final_total(transform(contributions, reverse_sign_step=target_step))"
    elif domain == "charts" and scene_id == "waterfall" and scope == "running_total_value":
        program_schema = "start_value + sum(contributions_through(target_step))"
    elif domain == "charts" and scene_id == "waterfall" and scope.startswith("threshold_crossing_label"):
        program_schema = "select_first_step(running_totals, threshold, direction)"
    chart_schema = _chart_detailed_program_schema(scene_id=scene_id, scope=scope, query=query) if domain == "charts" else ""
    if chart_schema:
        program_schema = chart_schema
    game_schema = _game_detailed_program_schema(scene_id=scene_id, scope=scope, query=query) if domain == "games" else ""
    if game_schema:
        program_schema = game_schema
    puzzle_schema = (
        _puzzle_detailed_program_schema(scene_id=scene_id, scope=scope, query=query)
        if domain == "puzzles"
        else ""
    )
    if puzzle_schema:
        program_schema = puzzle_schema
    if (
        signature.signature_id == "formula.solve_unknown"
        and domain == "geometry"
        and scene_id == "triangle_relations"
        and query.startswith("angle_from_")
    ):
        formula_schema = _right_triangle_inverse_trig_formula(query)
        if formula_schema:
            program_schema = (
                "solve_formula(scene_measurements, unknown_role=angle, "
                f"formula_schema={formula_schema})"
            )
    geometry_schema = (
        _geometry_detailed_program_schema(
            scene_id=scene_id,
            scope=scope,
            query=query,
            signature_id=signature.signature_id,
        )
        if domain == "geometry"
        else ""
    )
    if geometry_schema:
        program_schema = geometry_schema
    graph_schema = (
        _graph_detailed_program_schema(
            scene_id=scene_id,
            scope=scope,
            query=query,
            signature_id=signature.signature_id,
        )
        if domain == "graph"
        else ""
    )
    if graph_schema:
        program_schema = graph_schema
    icon_schema = _icon_detailed_program_schema(scene_id=scene_id, scope=scope, query=query) if domain == "icons" else ""
    if icon_schema:
        program_schema = icon_schema
    illustration_schema = (
        _illustration_detailed_program_schema(scene_id=scene_id, scope=scope, query=query)
        if domain == "illustrations"
        else ""
    )
    if illustration_schema:
        program_schema = illustration_schema
    pages_schema = _pages_detailed_program_schema(scene_id=scene_id, scope=scope, query=query) if domain == "pages" else ""
    if pages_schema:
        program_schema = pages_schema
    physics_schema = (
        _physics_detailed_program_schema(scene_id=scene_id, scope=scope, query=query)
        if domain == "physics"
        else ""
    )
    if physics_schema:
        program_schema = physics_schema
    if query and query != scope:
        return f"{program_schema}; scene={scene_id}; scope={scope}; query_branch={query}"
    return f"{program_schema}; scene={scene_id}; scope={scope}"


def _geometry_region_rule_family(text: str) -> str:
    if "annulus" in text:
        return "annulus_between_two_radii"
    if "circle" in text:
        return "circle_inequality"
    if "horizontal" in text:
        return "horizontal_half_plane"
    if "half_plane" in text or "halfplane" in text or "two_inequality" in text:
        return "intersection_of_linear_half_planes"
    if "vertical_strip" in text:
        return "vertical_strip_between_x_bounds"
    return sanitize_slug(text) or "geometric_region_rule"


def _geometry_unknown_role(scope: str, query: str) -> str:
    """Return the output role for a geometry program branch.

    Use query/output wording before support wording.  This avoids bugs like
    treating ``triangle`` as an angle query or assigning ``angle_measure`` to a
    length task because the givens include an angle.
    """

    query_text = sanitize_slug(query)
    scope_text = sanitize_slug(scope)
    text = f"{query_text} {scope_text}".lower()
    tokens = set(re.split(r"[_\s]+", text))
    if query_text.startswith("angle_from"):
        return "angle_measure"
    if query_text.startswith("centroid") or "median_segment" in scope_text:
        return "length_measure"
    if "arc_measure" in query_text or "arc_measure" in scope_text:
        return "arc_measure"
    if "arc_length" in query_text or scope_text.startswith("arc_length_value"):
        return "arc_length"
    if (
        query_text.startswith(("base_radius", "inner_radius", "inradius"))
        or "radius_from" in query_text
        or query_text.endswith("_radius")
        or scope_text.endswith("_radius_value")
    ):
        return "radius_length"
    if query_text.startswith("height") or "_height_from_" in query_text or scope_text.endswith("_height_value"):
        return "height_length"
    if query_text.startswith("width") or "missing_width" in query_text or "_width_from_" in query_text:
        return "width_length"
    if (
        query_text.startswith(("ground", "hypotenuse", "extension"))
        or ("angle_bisector" in query_text and "length" in query_text)
        or "chord_length" in query_text
        or "side_length" in query_text
        or "surface_path_length" in query_text
        or "parallel_section" in query_text
        or "similar_triangles_side" in query_text
        or "diagonal_length" in query_text
        or "side_from" in query_text
        or "length_from" in query_text
        or "length_value" in scope_text
    ):
        return "length_measure"
    if "side" in tokens:
        return "side_length"
    if "perimeter" in tokens or "circumference" in tokens or query_text.endswith("_perimeter"):
        return "perimeter_measure"
    if (
        "area" in tokens
        or query_text.endswith("_area")
        or "area_from" in query_text
        or "surface_area" in query_text
        or "projection_surface_area" in query_text
        or "square_area" in query_text
    ):
        return "area_measure"
    if query_text.endswith("_volume") or "volume_value" in scope_text or query_text.startswith(("cone_volume", "cylinder_volume", "double_cone_volume", "frustum_volume")):
        return "volume_measure"
    if "slope" in tokens or "rate" in tokens:
        return "slope_or_rate"
    if "label" in tokens or "match" in tokens or "position" in tokens:
        return "selected_label"
    if (
        "angle" in tokens
        or query_text.startswith(("central_angle", "inscribed_angle", "tangent_chord_angle"))
        or query_text.startswith(("complement_angle", "remaining_angle", "supplement_angle"))
        or query_text in {"final_bearing_value"}
        or "bearing" in tokens
    ):
        return "angle_measure"
    return "geometry_measure"


def _three_d_detailed_program_schema(*, scene_id: str, scope: str, query: str) -> str:
    """Exact three_d-domain task-contract programs for taxonomy review."""

    by_scope: dict[tuple[str, str], str] = {
        (
            "object_cluster",
            "single_attribute_membership_count",
        ): "count(filter(cluster_objects, object_type in target_object_types))",
        (
            "object_scene",
            "single_attribute_membership_count",
        ): "count(filter(candidate_objects, attribute_value(candidate_object, attribute_axis) in target_values))",
        (
            "object_scene",
            "counterfactual_count",
        ): "count(filter(apply_text_edits(initial_objects, edit_sequence), object_selector=target_selector))",
        (
            "object_scene",
            "multi_attribute_and_count",
        ): "count(filter(candidate_objects, all(attribute_predicate(candidate_object, predicate) for predicate in attribute_predicates)))",
        (
            "object_scene",
            "multi_attribute_exclusion_count",
        ): "count(filter(candidate_objects, included_attribute_predicate(candidate_object) and not excluded_attribute_predicate(candidate_object)))",
        (
            "object_scene",
            "multi_attribute_or_count",
        ): "count(filter(candidate_objects, any(attribute_predicate(candidate_object, predicate) for predicate in attribute_predicates)))",
        (
            "object_scene",
            "multi_attribute_xor_count",
        ): "count(filter(candidate_objects, exactly_one(attribute_predicate(candidate_object, predicate) for predicate in attribute_predicates)))",
        (
            "object_scene",
            "relation_attribute_count",
        ): "count(filter(candidate_objects, relation(candidate_object, reference_prop)=relation_mode))",
        (
            "object_scene",
            "camera_depth_relation_count",
        ): "count(filter(candidate_objects, compare(camera_distance(candidate_object), camera_distance(reference_object), depth_relation_direction)))",
        (
            "object_scene",
            "image_plane_lateral_relation_count",
        ): "count(filter(candidate_objects, compare(projected_x(candidate_object), projected_x(reference_object), lateral_relation_direction)))",
        (
            "object_scene",
            "camera_distance_extremum_label",
        ): "option_letter(label(arg_extreme(candidate_objects, camera_distance, extremum_direction)))",
        (
            "object_scene",
            "height_extremum_label",
        ): "option_letter(label(arg_extreme(candidate_objects, world_base_height, extremum_direction)))",
        (
            "object_scene",
            "marked_point_depth_extremum_label",
        ): "option_letter(label(arg_extreme(marked_points, camera_distance, extremum_direction)))",
        (
            "object_scene",
            "marked_point_vertical_relation_label",
        ): "option_letter(label(select(marked_points, vertical_projection_matches(reference_object, marked_point))))",
        (
            "object_scene",
            "landmark_correspondence_label",
        ): "option_letter(label(select(right_view_candidate_points, landmark_id = source_landmark_id)))",
        (
            "object_scene",
            "multiview_object_match_label",
        ): "option_letter(label(select(right_view_objects, canonical_object_id = source_object_id)))",
        (
            "object_scene",
            "between_references_label",
        ): "option_letter(label(select(candidate_objects, between_floor_references(candidate_object, reference_a, reference_b))))",
        (
            "object_scene",
            "reference_nearest_label",
        ): "option_letter(label(arg_min_distance(reference_object, candidate_objects, floor_plane_distance)))",
        (
            "object_scene",
            "object_relation_label",
        ): "option_letter(label(select(candidate_objects, relation(candidate_object, reference_prop)=relation_mode)))",
        (
            "object_scene",
            "occlusion_order_label",
        ): "option_letter(label(select(candidate_objects, projected_overlap(candidate_object, reference_object) and camera_distance(candidate_object) < camera_distance(reference_object))))",
        (
            "room",
            "multi_attribute_and_count",
        ): "count(filter(room_objects, object_type=target_object_type and mounting=wall_mounted))",
        (
            "room",
            "wall_object_camera_distance_label",
        ): "option_letter(label(arg_min_distance(camera_position, wall_object_candidates, camera_distance)))",
        (
            "room",
            "wall_object_same_wall_reference_label",
        ): "option_letter(label(select(wall_object_candidates, wall(candidate_object)=wall(reference_object))))",
        (
            "room",
            "wall_object_side_relation_label",
        ): "option_letter(label(select(wall_object_candidates, same_wall(candidate_object, reference_object) and compare(wall_axis(candidate_object), wall_axis(reference_object), lateral_relation_direction))))",
        (
            "street",
            "intersection_nearest_label",
        ): "option_letter(label(arg_min_distance(intersection_center, street_object_candidates, ground_plane_distance)))",
        (
            "street",
            "lane_ahead_object_label",
        ): "option_letter(label(arg_min(filter(street_object_candidates, ahead_in_lane(reference_vehicle, candidate_object)), forward_distance)))",
        (
            "street",
            "same_road_arm_reference_label",
        ): "option_letter(label(select(street_object_candidates, road_arm(candidate_object)=road_arm(reference_object))))",
        (
            "warehouse",
            "robot_forward_path_label",
        ): "option_letter(label(arg_min(filter(warehouse_object_candidates, ahead_in_robot_path(reference_robot, candidate_object)), forward_distance)))",
        (
            "warehouse",
            "nearest_candidate_to_reference_label",
        ): "option_letter(label(arg_min_distance(reference_entity, candidate_entities, floor_gap_distance)))",
        (
            "warehouse",
            "scoped_attribute_count",
        ): "count(filter(shelf_items, rack_color=target_rack_color and shelf_level=target_shelf_level))",
    }
    return by_scope.get((str(scene_id), str(scope)), "")


def _physics_detailed_program_schema(*, scene_id: str, scope: str, query: str) -> str:
    """Exact physics-domain task-contract programs for taxonomy review."""

    by_scope: dict[tuple[str, str], str] = {
        (
            "circuit_equivalent",
            "total_resistance_value",
        ): "equivalent_resistance(components=resistor_components_between_terminals, topology=series_parallel_network)",
        (
            "circuit_equivalent",
            "total_capacitance_value",
        ): "equivalent_capacitance(components=capacitor_components_between_terminals, topology=series_parallel_network)",
        (
            "collision",
            "sticky_collision_direction_choice",
        ): "option_letter(direction(momentum_sum(pucks_a_b), mode=final_sticky_velocity))",
        (
            "collision",
            "sticky_collision_velocity_component_value",
        ): "component(final_velocity(momentum_sum(pucks_a_b), combined_mass), axis=component_axis)",
        (
            "electrostatic_field",
            "field_direction_choice",
        ): "option_letter(direction(net_field(charges_q1_q2_q3, point_p), mode=direction_mode))",
        (
            "electrostatic_field",
            "potential_value",
        ): "sum(point_charge_potential(charges_q1_q2_q3, point_p, k=1))",
        (
            "electrostatic_field",
            "zero_field_point_label",
        ): "option_letter(select(candidate_points, net_field(charges_q1_q2, candidate_point)=zero_field))",
        (
            "hydraulic",
            "hydraulic_missing_value",
        ): "solve_pascal_law(input_force, input_area, output_force, output_area, unknown_slot)",
        (
            "fluid_flow",
            "continuity_speed_value",
        ): "solve_continuity_speed(area_1, speed_1, area_2, speed_2, unknown_speed_slot)",
        (
            "lever",
            "side_torque_value",
        ): "sum(weight_i * distance_i for weight_i in weights_on_queried_side)",
        (
            "lever",
            "missing_weight_balance_value",
        ): "solve_torque_balance(left_weight_distance_terms, right_weight_distance_terms, unknown_weight)",
        (
            "magnetic_force",
            "force_direction_choice",
        ): "option_letter(direction(charge_sign * cross_product(velocity_vector, magnetic_field_orientation)))",
        (
            "motion_graph",
            "velocity_sign_choice",
        ): "option_letter(classify_velocity_sign(marked_position_time_graph_interval))",
        (
            "motion_graph",
            "speed_change_state_choice",
        ): "option_letter(classify_speed_change(marked_velocity_time_graph_interval))",
        (
            "pulley",
            "pulley_mechanical_advantage",
        ): "solve_ideal_pulley(load_force, effort_force, support_strand_count, unknown_slot)",
        (
            "pv_diagram",
            "pv_work_value",
        ): "pressure * (final_volume - initial_volume)",
        (
            "pv_diagram",
            "pv_process_sign_choice",
        ): "option_letter(select(candidate_processes, sign(volume_change(process))=target_sign))",
        (
            "ray_optics",
            "ray_bounce_count",
        ): "count(reflection_points(hidden_ray_path))",
        (
            "ray_optics",
            "ray_target_hit_count",
        ): "count(filter(target_points, intersects(hidden_ray_path, target_point)))",
        (
            "spring",
            "spring_missing_value",
        ): "solve_hooke_ratio(reference_weight, reference_extension, query_weight, query_extension, unknown_slot)",
        (
            "spring",
            "spring_extension_difference",
        ): "abs(extension_a - extension_b)",
        (
            "signal_transform",
            "sinusoid_component_spectrum_match_label",
        ): "option_letter(select(spectrum_options, spike_components=sinusoid_components(input_waveform)))",
        (
            "signal_transform",
            "periodic_harmonic_spectrum_match_label",
        ): "option_letter(select(spectrum_options, harmonic_pattern=periodic_wave_harmonics(input_waveform)))",
        (
            "signal_transform",
            "pulse_width_spectrum_match_label",
        ): "option_letter(select(spectrum_options, spectrum_lobe_width=inverse_pulse_width(input_waveform)))",
        (
            "wave_interference",
            "interference_point_choice",
        ): "option_letter(select(candidate_points, interference_condition(path_difference_parity, phase_relation)=target_condition))",
        (
            "wave_interference",
            "path_difference_value",
        ): "abs(distance(source_s1, point_p) - distance(source_s2, point_p)) / lambda_half_step",
    }
    return by_scope.get((scene_id, scope), "")


def _graph_detailed_program_schema(*, scene_id: str, scope: str, query: str, signature_id: str) -> str:
    """Exact graph-domain task-contract programs for taxonomy review."""

    del signature_id
    by_scope: dict[tuple[str, str], str] = {
        ("adjacency", "directed_strong_component_count"): "count(strongly_connected_components(adjacency_representation))",
        ("adjacency", "undirected_component_count"): "count(connected_components(adjacency_representation))",
        ("adjacency", "mst_weight"): "sum(weights(minimum_spanning_tree(weighted_adjacency_matrix)))",
        ("adjacency", "traversal_kth_label"): "label(select_by_index(traverse(adjacency_representation, start_node, traversal_rule), visit_index))",
        ("adjacency", "bfs_kth_visit_label"): "label(select_by_index(traverse(adjacency_representation, start_node, traversal_rule=bfs), visit_index))",
        ("adjacency", "dfs_kth_visit_label"): "label(select_by_index(traverse(adjacency_representation, start_node, traversal_rule=dfs), visit_index))",
        ("automaton", "dfa_accepted_string_label"): "label(select_option(candidate_strings, accepted_by(automaton_type=deterministic, transition_graph, start_state, accepting_states)))",
        ("automaton", "nfa_accepted_string_label"): "label(select_option(candidate_strings, accepted_by(automaton_type=nondeterministic, transition_graph, start_state, accepting_states)))",
        ("automaton", "state_after_input_label"): "label(simulate(transition_graph, start_state, input_string).state_at(target_step))",
        ("binary_tree", "bst_path_operation_label"): "label(follow_bst_path(binary_search_tree, query_key, operation_mode).terminal_node)",
        ("binary_tree", "heap_property_violation_label"): "label(select_rule_violation(binary_tree_nodes, heap_order_rule))",
        ("binary_tree", "child_structure_node_count"): "count(filter(tree_nodes, child_structure = target_child_structure))",
        ("binary_tree", "depth_level_node_count"): "count(filter(tree_nodes, depth = target_depth))",
        ("binary_tree", "local_relative_node_label"): "label(resolve_tree_relation(binary_tree, anchor_node, relation_role))",
        ("binary_tree", "lowest_common_ancestor_label"): "label(lowest_common_ancestor(binary_tree, node_a, node_b))",
        ("binary_tree", "traversal_kth_label"): "label(select_by_index(traverse_tree(binary_tree, traversal_rule), visit_index))",
        ("binary_tree", "inorder_kth_node_label"): "label(select_by_index(traverse_tree(binary_tree, traversal_rule=inorder), visit_index))",
        ("binary_tree", "level_order_kth_node_label"): "label(select_by_index(traverse_tree(binary_tree, traversal_rule=level_order), visit_index))",
        ("binary_tree", "postorder_kth_node_label"): "label(select_by_index(traverse_tree(binary_tree, traversal_rule=postorder), visit_index))",
        ("binary_tree", "preorder_kth_node_label"): "label(select_by_index(traverse_tree(binary_tree, traversal_rule=preorder), visit_index))",
        ("flow_network", "max_flow_value"): "value(max_flow(capacity_network, source=S, sink=T))",
        ("flow_network", "min_cut_edge_count"): "count(edges(min_cut(capacity_network, source=S, sink=T)))",
        ("graph_options", "contained_subgraph_label"): "label(select_option(candidate_graphs, contains_subgraph(reference_graph)))",
        ("graph_options", "same_structure_label"): "label(select_option(candidate_graphs, is_isomorphic_to(reference_graph)))",
        ("metro", "exact_distance_station_count"): "count(filter(stations, shortest_path_length(route_network, reference_station, station)=target_distance))",
        ("metro", "shortest_path_length"): "length(shortest_path(route_network, source_station, target_station))",
        ("metro", "station_membership_count"): "count(filter(stations, route_membership = membership_mode))",
        ("metro", "transfer_count"): "count(transfers(shortest_transfer_path(route_network, source_station, via_station, target_station)))",
        ("node_link", "articulation_point_count"): "count(articulation_points(graph))",
        ("node_link", "bridge_count"): "count(bridges(graph))",
        ("node_link", "common_related_node_count"): "count(intersection(relation_set(graph, reference_a, relation_mode), relation_set(graph, reference_b, relation_mode)))",
        ("node_link", "component_size_after_edge_edit"): "count(component_containing(reference_node, transform(graph, edge_edit)))",
        ("node_link", "largest_component_size"): "max(size(component) for component in connected_components(graph))",
        ("node_link", "same_component_count"): "count(component_containing(reference_node, graph))",
        ("node_link", "cross_color_edge_count"): "count(filter(edges, endpoint_colors(edge)=target_color_pair and edge_direction=direction_mode))",
        ("node_link", "degree_extremum_value"): "value(arg_extreme(nodes, metric=degree_metric, direction))",
        ("node_link", "degree_value_filter_count"): "count(filter(nodes, compare(degree_metric(node), target_degree, comparator=equal)))",
        ("node_link", "degree_after_removal_filter_count"): "count(filter(nodes(transform(graph, remove_node)), compare(degree_metric(node), target_degree, comparator=equal)))",
        ("node_link", "edge_between_nodes_label"): "label(edge_between(graph, node_a, node_b).text_label)",
        ("node_link", "shortest_path_first_edge_label"): "label(first_edge(shortest_path(graph, source, target)).text_label)",
        ("node_link", "edge_color_count"): "count(filter(edges, edge_color=target_edge_color))",
        ("node_link", "edge_text_count"): "count(filter(edge_labels, text_label=target_text))",
        ("node_link", "isolated_after_removal_count"): "count(filter(nodes(transform(graph, remove_node)), degree(node)=0))",
        ("node_link", "longest_path_length"): "length(longest_simple_path(directed_graph, source, target))",
        ("node_link", "mst_weight"): "sum(weights(minimum_spanning_tree(weighted_graph)))",
        ("node_link", "named_node_degree_value"): "value(degree_metric(named_node))",
        ("node_link", "node_color_count"): "count(filter(nodes, node_color=target_node_color))",
        ("node_link", "reachable_count"): "count(reachable_nodes(directed_graph, start_node, include_start=True))",
        ("node_link", "reachable_count_after_edge_edit"): "count(reachable_nodes(transform(directed_graph, edge_edit), start_node, include_start=True))",
        ("node_link", "shortest_path_length"): "length(shortest_path(graph, source, target))",
        ("node_link", "topological_position_value"): "position_in_order(unique_topological_order(dag), target_node)",
        ("node_link", "unique_cycle_size"): "size(unique_cycle(graph))",
        ("node_link", "unique_related_node_label"): "label(single(filter(nodes, relation_to_reference(node, reference_node, relation_mode))))",
        ("pipe_network", "bridge_count"): "count(bridges(open_pipe_graph))",
        ("pipe_network", "pipe_exact_distance_count"): "count(filter(junctions, shortest_path_length(open_pipe_graph, reference_junction, junction)=target_distance))",
        ("pipe_network", "pipe_reachable_junction_count"): "count(reachable_nodes(open_pipe_graph, start_junction))",
        ("pipe_network", "shortest_path_length"): "length(shortest_path(open_pipe_graph, source_junction, target_junction))",
    }
    return by_scope.get((scene_id, scope), "")


def _icon_detailed_program_schema(*, scene_id: str, scope: str, query: str) -> str:
    """Exact icons-domain task-contract programs for taxonomy review."""

    del query
    by_scope: dict[tuple[str, str], str] = {
        ("icon_cutout", "partial_match_label"): "label(select_option(candidate_full_icons, matches_partial_fragment(partial_fragment)))",
        ("icon_field", "type_frequency_count"): "count(filter(icon_instances, frequency_role(icon_type(instance), all_icon_instances)=target_frequency_role))",
        ("mirror_grid", "mirror_symmetry_count"): "count(filter(scene_cells, mirror_match(cell, reference_cell, mirror_axis)))",
        ("named_field", "closer_to_reference_count"): "count(filter(target_shape_icons, distance(icon, queried_reference) < distance(icon, other_reference)))",
        ("named_field", "reference_distance_rank_label"): "label(select_option(candidate_icons, rank_by(distance(candidate, reference_icon), rank_order)))",
        ("named_field", "scoped_attribute_count"): "count(filter(select_scope(icon_instances, scope_selector), shape(icon)=target_shape))",
        ("named_field", "single_attribute_membership_count"): "count(filter(icon_instances, shape(icon) in target_shapes))",
        ("named_field", "multi_attribute_and_count"): "count(filter(icon_instances, shape(icon)=target_shape and secondary_attribute(icon, attribute_axis)=target_attribute_value))",
        ("named_field", "multi_attribute_or_count"): "count(filter(icon_instances, shape(icon)=target_shape or secondary_attribute(icon, attribute_axis)=target_attribute_value))",
        ("named_field", "multi_attribute_xor_count"): "count(filter(icon_instances, exactly_one(shape(icon)=target_shape, secondary_attribute(icon, attribute_axis)=target_attribute_value)))",
        ("named_field", "multi_attribute_exclusion_count"): "count(filter(icon_instances, included_attribute_predicate(icon) and not excluded_attribute_predicate(icon)))",
        ("named_field", "multi_attribute_complement_count"): "count(filter(icon_instances, not shape(icon)=target_shape and not secondary_attribute(icon, attribute_axis)=target_attribute_value))",
        ("named_field", "counterfactual_attribute_count"): "count(filter(apply_icon_edits(icon_instances, edit_sequence), shape(icon)=target_shape))",
        ("named_field", "counterfactual_total_count"): "count(apply_icon_edits(icon_instances, remove_shape=target_shape))",
        ("named_field", "count_arithmetic"): "combine(count(filter(icon_instances, operand_selector_a)), count(filter(icon_instances, operand_selector_b)), arithmetic_op)",
        ("named_grid", "group_predicate_count"): "count(filter(lines(line_axis), compare(count(filter(cells(line), shape(icon)=target_shape)), threshold, comparator)))",
        ("named_grid", "scoped_attribute_count"): "count(filter(cells(line_axis, line_index), shape(icon)=target_shape))",
        ("named_grid", "row_column_shape_extreme_number"): "number(arg_extreme(lines(line_axis), count(filter(cells(line), shape(icon)=target_shape)), direction))",
        ("named_path", "path_neighbor_label"): "label(select_option(candidate_icons, neighbor(path_occurrence(target_shape, occurrence_rank), neighbor_direction)))",
        ("named_ring", "scoped_attribute_count"): "count(filter(icons_on_arc(marker_a, marker_b, arc_direction), shape(icon)=target_shape))",
        ("named_strip", "shape_run_length"): "length(arg_extreme(contiguous_runs(icon_sequence, shape=target_shape), run_length, direction))",
        ("overlap_grid", "occlusion_order_count"): "count(filter(scene_cells, front_to_back_order(cell)=reference_order))",
        ("pair_grid", "attribute_delta_pair_count"): "count(filter(pair_cells, attribute_delta(pair_cell)=target_delta_predicate))",
        ("pair_grid", "reference_transform_match_count"): "count(filter(pair_cells, transform_relation(pair_cell)=reference_transform_relation))",
        ("pair_grid", "pair_relation_count"): "count(filter(pair_cells, pair_relation(pair_cell)=target_pair_relation(reference_pair, relation_mode)))",
        ("paired_canvas", "original_attribute_label"): "label(select_option(right_panel_candidates, matches_original_attribute(original_icon, attribute_selector)))",
        ("paired_canvas", "panel_attribute_change_count"): "count(filter(tracked_right_icons, changed_attribute(original_icon, right_icon)=target_attribute))",
        ("paired_canvas", "panel_movement_direction_count"): "count(filter(tracked_right_icons, movement_direction(left_icon, right_icon)=target_direction))",
        ("paired_canvas", "panel_set_relation_count"): "count(filter(panel_icons(left_panel, right_panel), set_relation(icon)=relation_mode))",
        ("pattern_grid", "attribute_pattern_violation_index"): "index(select_rule_violation(grid_cells, attribute_progression_rule(attribute_axis)))",
        ("reference_canvas", "anchor_position_count"): "count(filter(scene_icons, spatial_relation(icon, anchor_icon)=direction))",
        ("reference_canvas", "reference_attribute_match_count"): "count(filter(scene_icons, attributes_match(icon, reference_icon, attribute_set)))",
        ("reference_canvas", "reference_metric_relation_count"): "count(filter(scene_icons, compare(size(icon), size(reference_icon), direction)))",
        ("sequence_strip", "missing_count_value"): "value(solve_missing_count(arithmetic_progression(count_sequence)))",
        ("sequence_strip", "rotation_sequence_violation_index"): "index(select_rule_violation(sequence_cells, rotation_progression_rule))",
        ("two_anchor", "between_anchors_count"): "count(filter(scene_icons, inside_anchor_strip(icon, anchor_a, anchor_b, strip_axis)))",
        ("venn_field", "scoped_attribute_count"): "count(filter(icon_instances, shape(icon)=target_shape and venn_region(center(icon), region_mode)))",
    }
    return by_scope.get((scene_id, scope), "")


def _illustration_detailed_program_schema(*, scene_id: str, scope: str, query: str) -> str:
    """Exact illustrations-domain task-contract programs for taxonomy review."""

    text = f"{scene_id} {scope} {query}".lower()
    if scene_id == "construction_site" and scope == "equipment_zone_count":
        return "count(filter(construction_vehicles, zone(vehicle)=target_zone))"
    if scene_id == "construction_site" and scope == "worker_attribute_count":
        return "count(filter(workers, worker_selector(worker, target_attribute, target_attribute_value)))"
    if scene_id == "environment" and scope == "crossing_feature_count":
        return "count(filter(environment_features, crosses(feature, target_linear_feature)))"
    if scene_id == "environment" and scope == "feature_side_object_count":
        return "count(filter(scene_objects, side_of_feature(object, target_linear_feature)=target_side))"
    if scene_id == "environment" and scope == "lit_window_count":
        return "count(filter(building_windows, is_lit(window)))"
    if scene_id == "environment" and scope == "on_feature_object_count":
        return "count(filter(scene_objects, on_feature(object, target_feature)))"
    if scene_id == "image_cutout_board" and scope == "jigsaw_piece_order":
        return "sequence(order_pieces_by_reconstruction(piece_options, completed_image_layout, anchor_position))"
    if scene_id == "image_cutout_board" and scope == "rotated_tile_label":
        return "label(select_tile(grid_tiles, tile_rotation_mismatch(tile)=target_rotation))"
    if scene_id == "indoor_room" and scope == "furniture_side_count":
        return "count(filter(furniture_items, side_relation(item, room_reference)=target_side))"
    if scene_id == "indoor_room" and scope == "surface_object_count":
        return "count(filter(room_objects, object_type(object)=target_object_type and on_surface(object, target_surface)))"
    if scene_id == "library" and scope == "books_in_section_count":
        return "count(filter(books, section(book)=target_section))"
    if scene_id == "library" and scope == "filtered_book_in_section_count":
        return "count(filter(books, section(book)=target_section and book_attribute(book)=target_attribute_value))"
    if scene_id == "missing_patch" and scope == "missing_patch_label":
        return "label(select_option(candidate_patches, fills_missing_region(candidate_patch, source_image_with_hole, transform_mode)))"
    if scene_id == "park_playground" and scope == "activity_person_count":
        return "count(filter(people, activity(person)=target_activity))"
    if scene_id == "park_playground" and scope == "area_person_count":
        return "count(filter(people, area(person)=target_area))"
    if scene_id == "park_playground" and scope == "equipment_use_person_count":
        return "count(filter(people, uses_equipment(person, target_equipment)))"
    if scene_id == "park_playground" and scope == "playground_equipment_count":
        return "count(filter(playground_equipment, equipment_type(equipment)=target_equipment))"
    if scene_id == "single_object_figure" and scope == "visible_part_count":
        return "count(visible_parts(target_object, part_type))"
    if scene_id == "source_scene_edit" and scope == "object_count_after_edit":
        return "count(filter(apply_scene_edit(scene_objects, edit_operation, edit_count), object_type(object)=target_object_type))"
    if scene_id == "transit_terminal" and scope == "luggage_in_boarding_area_count":
        return "count(filter(luggage_items, area(luggage)=boarding_area))"
    if scene_id == "transit_terminal" and scope == "person_in_boarding_area_count":
        return "count(filter(people, area(person)=boarding_area))"
    if scene_id == "transit_terminal" and scope == "person_in_queue_count":
        return "count(filter(people, in_queue(person)))"
    return ""


def _pages_detailed_program_schema(*, scene_id: str, scope: str, query: str) -> str:
    """Exact pages-domain task-contract programs for taxonomy review."""

    text = f"{scene_id} {scope} {query}".lower()
    if scene_id == "calendar" and scope == "marked_day_class_count":
        return "count(filter(calendar_cells, marked(cell)=True and day_class(cell)=target_day_class))"
    if scene_id == "calendar" and scope == "weekday_occurrence_date":
        return "date(select_calendar_date(weekday, ordinal, month_grid))"
    if scene_id == "command_matrix" and scope == "command_intent_target_label":
        return "label(select_command_cell(command_matrix, action_cue, object_row))"
    if scene_id == "command_matrix" and scope == "dual_guide_command_label":
        return "label(select_command_cell(command_matrix, action_guide, object_guide, object_row))"
    if scene_id == "concept_map" and scope == "branch_child_count":
        return "count(children(parent_branch))"
    if scene_id == "concept_map" and scope == "marked_child_count":
        return "count(filter(children(parent_branch), marked(child)=True))"
    if scene_id == "concept_map" and scope == "ordered_child_label":
        return "label(select_by_rank(children(parent_branch), sibling_order, rank))"
    if scene_id == "control_board" and scope == "disabled_controls_in_group_count":
        return "count(filter(controls(control_group), control_state(control)=disabled))"
    if scene_id == "control_board" and scope == "selected_enabled_controls_in_group_count":
        return "count(filter(controls(control_group), selected(control)=True and enabled(control)=True))"
    if scene_id == "cycle" and scope == "offset_stage_label":
        return "label(follow_cycle(stage_ring, start_stage, offset_steps, direction))"
    if scene_id == "data_table" and scope == "enabled_action_for_type_count":
        return "count(filter(table_rows, row_type(row)=target_type and action_enabled(row)=True))"
    if scene_id == "data_table" and scope == "selected_rows_with_status_count":
        return "count(filter(table_rows, selected(row)=True and status(row)=target_status))"
    if scene_id == "data_table" and scope == "value_threshold_in_group_count":
        return "count(filter(table_rows, group(row)=target_group and compare(value(row), threshold, direction)))"
    if scene_id == "form_section" and scope == "sum_two_amounts_in_section_value":
        return "sum(values(operand_value_boxes))"
    if scene_id == "form_section" and scope == "difference_two_amounts_in_section_value":
        return "difference(value(first_operand), value(second_operand), mode=absolute)"
    if scene_id == "form_section" and scope == "sum_minus_amount_in_section_value":
        return "difference(sum(values(addend_operand_boxes)), value(subtrahend_operand), mode=signed)"
    if scene_id == "hierarchy" and scope == "path_length_count":
        return "count(edges(path_between(source_node, target_node)))"
    if scene_id == "hierarchy" and scope == "subtree_descendant_count":
        return "count(descendants(parent_node))"
    if scene_id == "hierarchy" and scope == "subtree_leaf_count":
        return "count(filter(descendants(parent_node), is_leaf(node)=True))"
    if scene_id == "infographic" and scope == "sum_named_metrics_value":
        return "sum(values(named_metric_cards))"
    if scene_id == "infographic" and scope == "section_extrema_arithmetic_value":
        return "combine(values(arg_extreme(metric_cards_by_section, metric_value, direction)), arithmetic_op)"
    if scene_id == "infographic" and scope == "section_total_extrema_difference_value":
        return "difference(sum(values(section_a_metric_cards)), sum(values(section_b_metric_cards)), mode=absolute)"
    if scene_id == "infographic" and scope == "section_total_except_named_value":
        return "sum(values(filter(metric_cards_in_section, label(card) != excluded_metric_label)))"
    if scene_id == "infographic" and scope == "section_icon_total_value":
        return "sum(values(filter(metric_cards_in_section, icon_type(card)=target_icon_type)))"
    if scene_id == "infographic" and scope == "section_icon_total_difference_value":
        return "difference(sum(values(filter(metric_cards_in_section_a, icon_type(card)=target_icon_type))), sum(values(filter(metric_cards_in_section_b, icon_type(card)=target_icon_type))), mode=absolute)"
    if scene_id == "infographic" and scope == "section_ranked_total_label":
        return "label(select_by_rank(sections, sum(values(metric_cards_in_section)), rank))"
    if scene_id == "infographic" and scope == "section_icon_extremum_label":
        return "label(arg_extreme(sections, sum(values(filter(metric_cards_in_section, icon_type(card)=target_icon_type))), direction))"
    if scene_id == "infographic" and scope == "detail_for_named_item":
        return "lookup_label(metric_card(named_item), requested_field=detail_text)"
    if scene_id == "infographic" and scope == "item_for_named_value":
        return "lookup_label(filter(metric_cards, value(card)=target_value), requested_field=item_label)"
    if scene_id == "infographic" and scope == "value_for_named_item":
        return "lookup_label(metric_card(named_item), requested_field=value_text)"
    if scene_id == "map" and scope == "destination_after_directions_label":
        return "label(follow_route(static_map, start_landmark, direction_sequence).destination)"
    if scene_id == "map" and scope == "landmark_after_route_step_label":
        return "label(follow_route(static_map, start_landmark, route_steps).landmark_at_step)"
    if scene_id == "navigation_flow" and scope == "menu_path_target_label":
        return "label(lookup_navigation_target(menu_tree, menu_path))"
    if scene_id == "navigation_flow" and scope == "sidebar_tree_target_label":
        return "label(lookup_navigation_target(sidebar_tree, tree_path))"
    if scene_id == "navigation_flow" and scope == "ribbon_group_command_label":
        return "label(select_command(ribbon_groups, group_name, command_cue))"
    if scene_id == "paired_forms" and scope == "shortfall_minus_overage_value":
        return "difference(sum(values(shortfall_rows)), sum(values(overage_rows)), mode=signed)"
    if scene_id == "paired_forms" and scope == "sum_absolute_quantity_differences_value":
        return "sum_absolute(difference(value(purchase_row), value(receiving_row), mode=absolute) for row_pair in mismatched_rows)"
    if scene_id == "paired_forms" and scope == "total_amount_delta_value":
        return "difference(sum(values(receiving_rows)), sum(values(purchase_rows)), mode=signed)"
    if scene_id == "process_flow" and scope == "all_cross_lane_handoff_count":
        return "count(filter(process_edges, lane(source_node) != lane(target_node)))"
    if scene_id == "process_flow" and scope == "lane_filtered_handoff_count":
        return "count(filter(process_edges, handoff_relation(edge, target_lane, direction_mode)))"
    if scene_id == "process_flow" and scope == "condition_path_endpoint_label":
        return "label(follow_condition_path(process_flow, start_step, decision_label).endpoint_step)"
    if scene_id == "process_flow" and scope == "filtered_node_count":
        return "count(filter(process_nodes, node_attribute(node, target_attribute)=target_value))"
    if scene_id == "profile_card_grid" and scope == "profile_for_field_value":
        return "lookup_label(filter(profile_cards, field_value(profile, field_name)=target_field_value), requested_field=profile_name)"
    if scene_id == "profile_card_grid" and scope == "value_for_named_profile_field":
        return "lookup_label(profile_card(named_profile), requested_field=field_value)"
    if scene_id == "ranked_list" and scope == "entry_after_named_entry_label":
        return "lookup_label(ranked_list, requested_field=entry_after_named_entry)"
    if scene_id == "ranked_list" and scope == "entry_after_named_entry":
        return "lookup_label(ranked_list, requested_field=entry_after_named_entry)"
    if scene_id == "ranked_list" and scope == "ordinal_entry_label":
        return "label(select_by_rank(ranked_entries, list_order, rank))"
    if scene_id == "schedule" and scope == "maximum_non_overlapping_count":
        return "count(maximum_non_overlapping_events(schedule_events))"
    if scene_id == "schedule" and scope == "longer_than_reference_count":
        return "count(filter(schedule_events, duration(event) > duration(reference_event)))"
    if scene_id == "schedule" and scope == "overlap_count":
        return "count(filter(schedule_events, overlaps(event, reference_event)))"
    if scene_id == "schema" and scope == "field_role_count":
        return "count(filter(schema_fields, field_role(field)=target_role))"
    if scene_id == "schema" and scope == "relationship_count":
        return "count(schema_relationship_edges)"
    if scene_id == "step_list" and scope in {"nth_step_lookup_label", "nth_step_title_label"}:
        return "lookup_label(select_by_rank(steps, step_order, rank), requested_field=step_title)"
    if scene_id == "step_list" and scope == "nth_step_detail_label":
        return "lookup_label(select_by_rank(steps, step_order, rank), requested_field=step_detail)"
    if scene_id == "step_list" and scope in {"step_after_named_step", "step_after_named_step_label"}:
        return "lookup_label(step_list, requested_field=step_after_named_step)"
    if scene_id == "timeline" and scope == "interval_membership_count":
        return "count(filter(timeline_events, interval_membership(event, reference_event_a, reference_event_b, membership_mode)))"
    if scene_id == "web_action" and scope == "click_target_label":
        return "label(select_web_control(web_page, instruction_cue, target_action=click))"
    if scene_id == "web_action" and scope == "select_option_label":
        return "label(select_web_control(web_page, instruction_cue, target_action=select_option))"
    if scene_id == "web_action" and scope == "type_field_label":
        return "label(select_web_control(web_page, instruction_cue, target_action=type_text))"
    if scene_id == "workspace" and scope.endswith("_control_label"):
        return "label(select_workspace_control(workspace_surface, context_cue, control_family))"
    return ""


def _geometry_detailed_program_schema(*, scene_id: str, scope: str, query: str, signature_id: str) -> str:
    """Exact geometry-domain task-contract programs for taxonomy review."""

    text = f"{scope} {query}".lower()
    scene_measurements = f"visible_{scene_id}_measurements"
    scene_support = f"visible_{scene_id}_support"
    unknown_role = _geometry_unknown_role(scope, query)

    if scene_id == "area_partition" and scope == "total_area_value":
        return "solve_formula(visible_area_partition_measurements, unknown_role=area_measure, formula_schema=shaded_unit_fraction_area_to_total_area, partition_rule=visible_fraction_partition_rule)"
    if scene_id == "composite_shape" and scope == "composite_area_value":
        return "solve_formula(visible_composite_shape_measurements, unknown_role=area_measure, formula_schema=composite_area_decomposition, decomposition_rule=visible_component_decomposition_rule)"
    if scene_id == "circle_theorem" and scope == "secant_secant_length_value":
        return "solve_formula(visible_circle_theorem_measurements, unknown_role=length_measure, formula_schema=secant_secant_length)"
    if scene_id == "paper_fold" and scope == "paper_fold_angle_value":
        return "solve_formula(visible_paper_fold_measurements, unknown_role=angle_measure, formula_schema=fold_crease_bisects_total_angle)"
    if signature_id == "geometry.region_membership_selection":
        rule_family = _geometry_region_rule_family(query or scope)
        if scope == "locus_panel_match_label" or "panel_match" in query:
            return "label(select_panel(candidate_region_panels, condition_box, region_rule_family))"
        if scope == "locus_point_label":
            return "label(select_point(lettered_candidate_points, predicate=inside_shaded_region, region_rule_family))"
        return f"label(select_point(candidate_points, region_rule_family={rule_family}, predicate=inside_shaded_region))"
    if signature_id == "selection.option_match":
        if scene_id == "coordinate_plane" and scope == "locus_panel_match_label":
            return "label(select_panel(candidate_region_panels, condition_box, region_rule_family))"
        if scene_id == "coordinate_plane" and "completion" in scope:
            return "label(select_candidate_point(candidate_points, quadrilateral_completion_rule=quadrilateral_type))"
        if scene_id == "coordinate_panels":
            return "label(select_panel(candidate_coordinate_panels, quadrilateral_type))"
        if scene_id == "shape_gallery":
            return f"label(select_option(candidate_shapes, transform_rule={sanitize_slug(query)}))"
        if scene_id == "function_panels":
            if scope == "intersection_property_label":
                return "label(select_panel(candidate_function_panels, primitive_pair_type, intersection_condition))"
            if scope == "sign_interval_label":
                return "label(select_panel(candidate_function_panels, sign_interval_property, sign_direction))"
            return f"label(select_panel(candidate_function_panels, property_rule={sanitize_slug(query)}))"
        return f"label(select_option(visible_{scene_id}_options, matching_rule={sanitize_slug(query or scope)}))"
    if signature_id == "selection.direct_label":
        if scene_id == "coordinate_plane":
            if scope == "missing_endpoint_label":
                return "label(select_candidate_point(candidate_points, coordinate_rule=midpoint_inverse_endpoint, unknown_endpoint_role=endpoint_role))"
            if scope == "section_point_label":
                return "label(select_candidate_point(candidate_points, coordinate_rule=section_formula, section_ratio=ratio_from_p_to_q))"
            if scope == "reflected_point_label":
                return "label(select_candidate_point(candidate_points, coordinate_rule=reflection_across_reference_line, reflection_axis))"
            if scope == "rotated_point_label":
                return "label(select_candidate_point(candidate_points, coordinate_rule=rotation_about_marked_center, rotation_rule))"
            if scope == "translated_point_label":
                return "label(select_candidate_point(candidate_points, coordinate_rule=translation, translation_rule))"
            return f"label(select_candidate_point(candidate_points, coordinate_rule={sanitize_slug(query)}))"
        if scene_id == "function_panels":
            if scope == "intersection_property_label":
                return "label(select_panel(candidate_function_panels, primitive_pair_type, intersection_condition))"
            if scope == "sign_interval_label":
                return "label(select_panel(candidate_function_panels, sign_interval_property, sign_direction))"
            return f"label(select_panel(candidate_function_panels, function_property_rule={sanitize_slug(query)}))"
        if scene_id == "cylinder_wrap":
            return "label(select_rim_candidate(rim_positions, unwrap_mapping(strip_mark)))"
        return f"label(select_visible_support({scene_support}, selection_rule={sanitize_slug(query or scope)}))"
    if signature_id == "selection.extreme_metric_label":
        return f"label(arg_extreme(visible_{scene_id}_items, metric={sanitize_slug(scope)}_metric, direction))"
    if scene_id == "function_graph" and "extremum_count" in scope:
        extremum_kind = "local_extremum" if "local_extremum" in text else "turning_point"
        return f"count(filter(function_graph_feature_points, feature_type={extremum_kind}))"
    if scene_id == "graph_paper" and scope == "angle_type_count":
        return "count(filter(graph_paper_angles, angle_type(angle)=target_angle_type))"
    if scene_id == "graph_paper" and scope == "quadrilateral_type_count":
        return "count(filter(graph_paper_quadrilaterals, quadrilateral_type(shape)=target_quadrilateral_type))"
    if scene_id == "graph_paper" and scope == "triangle_type_count":
        return "count(filter(graph_paper_triangles, triangle_type(shape)=target_triangle_type))"
    if scene_id == "graph_paper" and scope == "shape_type_count":
        return "count(filter(graph_paper_shapes, shape_type(shape)=target_shape_type))"
    if scene_id == "graph_paper" and scope == "polygon_convexity_count":
        return "count(filter(graph_paper_polygons, polygon_convexity(shape)=target_convexity_class))"
    if scene_id == "coordinate_plane" and scope == "segment_relation_count":
        return "count(filter(coordinate_plane_segment_pairs, segment_relation(pair)=target_segment_relation))"
    if scene_id == "coordinate_plane" and scope == "collinear_point_count":
        return "count(filter(candidate_points, collinear_with_reference_line(point, reference_line)))"
    if scene_id == "coordinate_plane" and scope == "point_in_polygon_count":
        return "count(filter(candidate_points, inside_polygon(point, target_polygon)))"
    if scene_id == "coordinate_plane" and scope == "same_quadrant_point_count":
        return "count(filter(points, quadrant(point)=quadrant(reference_point)))"
    if scene_id == "shape_gallery" and scope in {"congruent_count", "similar_count"}:
        relation = "congruent_to_reference" if scope == "congruent_count" else "similar_to_reference"
        return f"count(filter(candidate_shapes, shape_relation(shape, reference_shape)={relation}))"
    if signature_id == "count.direct_cardinality":
        return f"count(filter(visible_{scene_id}_units, predicate={sanitize_slug(query or scope)}))"
    if signature_id == "count.intersection_or_crossing":
        return f"count(intersections(visible_{scene_id}_primitives, crossing_rule={sanitize_slug(query or scope)}))"
    if signature_id == "numeric.summary_statistic":
        return f"summary_statistic(values({scene_support}), statistic_schema={sanitize_slug(query or scope)})"
    if signature_id == "numeric.difference_or_change":
        return f"difference(value({sanitize_slug(query or scope)}_source_a), value({sanitize_slug(query or scope)}_source_b), mode=absolute)"
    if signature_id == "numeric.derived_metric":
        return f"derive_geometry_metric({scene_measurements}, derivation_rule={sanitize_slug(query or scope)}, output_role={unknown_role})"
    if signature_id == "formula.solve_unknown":
        formula_schema = _right_triangle_inverse_trig_formula(query) or sanitize_slug(query or scope)
        return f"solve_formula({scene_measurements}, unknown_role={unknown_role}, formula_schema={formula_schema})"
    return ""


def _chart_detailed_program_schema(*, scene_id: str, scope: str, query: str) -> str:
    """Concrete chart-domain task-contract programs for taxonomy review."""

    del query
    by_scope: dict[tuple[str, str], str] = {
        ("annotated_series", "callout_endpoint_change_value"): "difference(value(callout_mark), value(endpoint_mark), mode=absolute)",
        ("annotated_series", "event_window_extremum_label"): "label(arg_extreme(marks_in_annotated_window, value(mark), direction))",
        ("annotated_series", "event_window_threshold_count"): "count(filter(marks_in_annotated_window, compare(value(mark), threshold, direction)))",
        ("area", "interval_area_value"): "sum(pair_mean(adjacent_values(area_series, x_interval_start_label, x_interval_end_label)))",
        ("area", "stacked_band_interval_sum_value"): "sum(values(stacked_area_category, x_interval_start_label, x_interval_end_label))",
        ("area", "stacked_band_dominance_label"): "label(arg_extreme(stacked_area_categories, sum(values(category, x_interval_start_label, x_interval_end_label)), direction=highest))",
        ("bar_3d", "category_extremum_gap_value"): "difference(value(select_by_rank(displayed_series, value(series, category), rank_a)), value(select_by_rank(displayed_series, value(series, category), rank_b)), mode=absolute)",
        ("bar_3d", "category_total_gap_value"): "difference(sum(values(category_a, displayed_series)), sum(values(category_b, displayed_series)), mode=absolute)",
        ("bar_3d", "series_total_gap_value"): "difference(sum(values(series_a, displayed_categories)), sum(values(series_b, displayed_categories)), mode=absolute)",
        ("bar_3d", "category_total_value"): "sum(values(category, displayed_series))",
        ("bar_3d", "series_category_scope_total_value"): "sum(values(series, category_scope))",
        ("bar_3d", "pairwise_comparison_count"): "count(filter(categories, compare(value(series_a, category), value(series_b, category), direction)))",
        ("bar_3d", "category_threshold_count"): "count(filter(categories, compare(sum(values(category, displayed_series)), threshold, direction)))",
        ("bar_3d", "series_threshold_count"): "count(filter(series_labels, compare(sum(values(series, displayed_categories)), threshold, direction)))",
        ("boxplot", "median_rank_difference_value"): "difference(value(select_by_rank(boxplots, median(boxplot), rank_a)), value(select_by_rank(boxplots, median(boxplot), rank_b)), mode=absolute)",
        ("boxplot", "paired_median_shift_label"): "label(arg_extreme(matched_boxplot_labels, median(after_boxplot)-median(before_boxplot), direction))",
        ("boxplot", "iqr_extremum_label"): "label(arg_extreme(boxplots, upper_quartile(boxplot)-lower_quartile(boxplot), direction))",
        ("boxplot", "median_reference_label"): "label(arg_extreme(boxplots, distance(median(boxplot), reference_quartile), direction))",
        ("candlestick", "counterfactual_close_value"): "value(transform(candle(target_period), body_size_delta, keep_open=True, keep_direction=True).close)",
        ("candlestick", "range_extremum_label"): "label(arg_extreme(candles, candle_range(candle, range_mode), direction))",
        ("combo_mark", "conditioned_line_extremum_label"): "label(arg_extreme(filter(categories, compare(value(primary_series, category), primary_threshold, primary_direction)), value(line_series, category), direction))",
        ("combo_mark", "conditioned_primary_extremum_label"): "label(arg_extreme(filter(categories, compare(value(line_series, category), line_threshold, line_direction)), value(primary_series, category), direction))",
        ("combo_mark", "cross_mark_difference_value"): "difference(value(series_a, target_category), value(series_b, target_category), mode=series_order)",
        ("combo_mark", "dual_threshold_condition_count"): "count(filter(categories, compare(value(primary_series, category), primary_threshold, primary_direction) and compare(value(line_series, category), line_threshold, line_direction)))",
        ("combo_mark", "interval_threshold_condition_count"): "count(filter(categories, interval(value(interval_series, category), lower_bound, upper_bound) and compare(value(threshold_series, category), threshold, direction)))",
        ("combo_mark", "absolute_gap_extremum_label"): "label(arg_extreme(categories, abs(value(primary_series, category)-value(line_series, category)), direction))",
        ("combo_mark", "directional_gap_extremum_label"): "label(arg_extreme(categories, value(higher_role_series, category)-value(lower_role_series, category), direction=largest))",
        ("combo_mark", "series_threshold_crossing_label"): "select_first_label(ordered_categories, compare(value(target_series, category), threshold, direction))",
        ("contour_density", "density_extremum_region_label"): "label(arg_extreme(density_regions, density_value(region), direction))",
        ("contour_density", "density_threshold_region_count"): "count(filter(density_regions, compare(density_value(region), threshold, direction)))",
        ("contour_density", "reference_distance_extremum_label"): "label(arg_extreme(density_regions, distance(region_center(region), reference_point), direction))",
        ("contour_density", "spread_extremum_region_label"): "label(arg_extreme(density_regions, spatial_spread(region), direction))",
        ("curve_panels", "cross_panel_delta_extremum_label"): "label(arg_extreme(shared_x_labels, abs(value(panel_a, x_label)-value(panel_b, x_label)), direction))",
        ("curve_panels", "cross_panel_threshold_earliest_label"): "label(select_by_rank(filter(panels, crosses_threshold(value(target_curve, x_label), threshold, direction)), panel_order(panel), rank=earliest))",
        ("curve_panels", "curve_at_x_extremum_label"): "label(arg_extreme(curves_in_panel, value(curve, target_x_label), direction))",
        ("curve_panels", "curve_intersection_count"): "count(intersections(series_a, series_b, subplot))",
        ("curve_panels", "earliest_maximum_panel_label"): "label(select_by_rank(panels, x_position(argmax(values(panel_series))), rank=earliest))",
        ("curve_panels", "panel_curve_threshold_crossing_count"): "count(filter(curves_in_panel, crosses_threshold(ordered_values(curve), threshold, direction)))",
        ("curve_panels", "panel_point_threshold_count"): "count(filter(points_in_panel, compare(value(point), threshold, direction)))",
        ("curve_panels", "threshold_series_count"): "count(filter(curves_in_panel, compare(value(curve, target_x_label), threshold, direction)))",
        ("dashboard", "category_panel_condition_count"): "count(filter(panels, compare(value(panel, target_category), threshold, direction)))",
        ("dashboard", "dual_condition_count"): "count(filter(categories, compare(value(panel_a, category), threshold_a, direction_a) and compare(value(panel_b, category), threshold_b, direction_b)))",
        ("dashboard", "dual_source_target_sum_value"): "sum(values(target_panel, categories=[select_by_rank(categories, value(source_panel_a, category), rank_a), select_by_rank(categories, value(source_panel_b, category), rank_b)]))",
        ("dashboard", "panel_gap_extremum_category_label"): "label(arg_extreme(categories, abs(value(panel_a, category)-value(panel_b, category)), direction))",
        ("dashboard", "source_rank_difference_value"): "difference(value(source_panel, category=select_by_rank(categories, value(source_panel, category), rank)), value(target_panel, category=select_by_rank(categories, value(source_panel, category), rank)), mode=absolute)",
        ("dashboard", "source_rank_target_value"): "value(target_panel, category=select_by_rank(categories, value(source_panel, category), rank))",
        ("dashboard", "shared_label_rank_gap_extremum"): "label(arg_extreme(categories, abs(rank(category, panel_a, rank_direction)-rank(category, panel_b, rank_direction)), gap_direction))",
        ("dashboard", "top_k_overlap_count"): "count(intersection(select_top_k(categories, value(panel_a, category), k, rank_direction), select_top_k(categories, value(panel_b, category), k, rank_direction)))",
        ("dumbbell", "gap_rank_row_label"): "label(select_by_rank(rows, abs(value_a(row)-value_b(row)), rank))",
        ("dumbbell", "absolute_gap_threshold_count"): "count(filter(rows, compare(abs(value_a(row)-value_b(row)), threshold, direction)))",
        ("dumbbell", "side_winner_count"): "count(filter(rows, compare(value_a(row)-value_b(row), minimum_gap, side_direction)))",
        ("error_interval", "interval_width_rank_label"): "label(select_by_rank(intervals, upper_bound(interval)-lower_bound(interval), rank))",
        ("error_interval", "reference_containment_count"): "count(filter(intervals, lower_bound(interval) <= reference_value <= upper_bound(interval)))",
        ("error_interval", "reference_exclusion_side_count"): "count(filter(intervals, interval_side(interval, reference_value)=exclusion_side))",
        ("errorbar_series", "bound_extremum_x_label"): "x_label(arg_extreme(errorbars, errorbar_bound(errorbar, bound_role), direction))",
        ("errorbar_series", "same_x_interval_overlap_count"): "count(filter(errorbars_at_x_label, intervals_overlap(errorbar_interval(errorbar), errorbar_interval(target_errorbar))))",
        ("errorbar_series", "threshold_support_count"): "count(filter(errorbars, interval_supports_threshold(errorbar_interval(errorbar), threshold, support_relation)))",
        ("heatmap", "axis_cell_extremum_label"): "label(arg_extreme(cells_in_axis_scope, value(cell), direction))",
        ("heatmap", "axis_condition_extremum_label"): "label(arg_extreme(axis_labels, count(filter(cells(axis_label), intensity_class=target_intensity_class)), direction))",
        ("heatmap", "colorbar_interval_cell_count"): "count(filter(heatmap_cells, lower <= colorbar_value(cell) <= upper))",
        ("heatmap", "colorbar_threshold_cell_count"): "count(filter(heatmap_cells, compare(colorbar_value(cell), threshold, direction)))",
        ("heatmap", "condition_run_extremum_label"): "label(arg_extreme(axis_labels, max(lengths(contiguous_runs(cells(axis_label), intensity_class=target_intensity_class))), direction))",
        ("hexbin_density", "threshold_bin_count"): "count(filter(hex_bins, compare(density_level(bin), threshold_level, direction)))",
        ("histogram", "cumulative_rank_bin_label"): "x_axis_value(bin_containing_rank(cumulative_counts, rank))",
        ("histogram", "bin_count_between_values"): "count(filter(bins, lower <= x_axis_value(bin) <= upper))",
        ("histogram", "interval_mass"): "sum(count(bin) for bin in filter(bins, lower <= x_axis_value(bin) <= upper))",
        ("marker_map", "marker_region_extremum_label"): "label(arg_extreme(map_regions_with_markers, marker_value(region), direction))",
        ("marker_map", "marker_region_threshold_count"): "count(filter(map_regions_with_markers, compare(marker_value(region), threshold, direction)))",
        ("matrix", "axis_extremum_label"): "label(arg_extreme(axis_labels, aggregate(values(cells_in_axis(axis_label)), axis_aggregate), direction))",
        ("matrix", "off_diagonal_confusion_label"): "label(arg_extreme(off_diagonal_cells(actual_row), cell_value, direction=highest))",
        ("matrix", "threshold_cell_count"): "count(filter(matrix_cells, compare(value(cell), threshold, direction)))",
        ("multiseries", "category_total_extremum_label"): "label(arg_extreme(categories, sum(values(displayed_series, category)), direction))",
        ("multiseries", "pair_equality_label"): "label(filter(categories, value(series_a, category)=value(series_b, category)))",
        ("multiseries", "ranked_change_extremum_label"): "label(select_by_rank(categories, change_metric(value(series_a, category), value(series_b, category), mode=change_measure), rank))",
        ("multiseries", "ranked_series_share_extremum_label"): "label(select_by_rank(categories, value(target_series, category) / sum(values(displayed_series, category)), rank))",
        ("multiseries", "ranked_pair_ratio_extremum_label"): "label(select_by_rank(categories, value(numerator_series, category) / value(denominator_series, category), rank))",
        ("multiseries", "series_comparison_count"): "count(filter(categories, compare(value(series_a, category), value(series_b, category), direction)))",
        ("multiseries", "series_rank_at_category_label"): "label(select_by_rank(series_labels, value(series, target_category), rank))",
        ("parallel_coords", "axis_condition_count"): "count(filter(profiles, compare(value(axis_a, profile), threshold, direction_a) and compare(value(axis_b, profile), threshold, direction_b)))",
        ("parallel_coords", "axis_delta_extremum_label"): "label(arg_extreme(profiles, delta(value(axis_b, profile), value(axis_a, profile), mode=delta_mode), direction))",
        ("parallel_coords", "all_crossings_between_adjacent_axes"): "count(order_reversal_pairs(profiles, adjacent_axis_a, adjacent_axis_b))",
        ("parallel_coords", "crossings_involving_profile_between_axes"): "count(order_reversal_pairs(reference_profile, other_profiles, adjacent_axis_a, adjacent_axis_b))",
        ("part_whole", "adjacent_transfer_gap_value"): "difference(value(source_category)-transfer_amount, value(adjacent_category)+transfer_amount, mode=absolute)",
        ("part_whole", "chart_order_share_to_count"): "round(total_count * sum(values(categories_between(chart_order, start_category, end_category, direction))) / 100)",
        ("part_whole", "contiguous_chart_order_sum"): "sum(values(categories_between(chart_order, start_category, end_category, direction)))",
        ("part_whole", "positional_segment_share_sum"): "sum(values(positional_segments(anchor_category, positions)))",
        ("part_whole", "sector_share_to_angle"): "round(360 * sum(values(categories_between(chart_order, start_category, end_category, direction))) / 100)",
        ("pictogram", "category_total_value"): "unit_scale * mark_count(category)",
        ("pictogram", "group_difference_value"): "difference(unit_scale * mark_count(category_a), unit_scale * mark_count(category_b), mode=absolute)",
        ("pictogram", "threshold_count"): "count(filter(categories, compare(unit_scale * mark_count(category), threshold, direction)))",
        ("population_pyramid", "age_group_threshold_count"): "count(filter(age_groups, compare(population_value(side_or_combined, age_group), threshold, direction)))",
        ("population_pyramid", "side_gap_extremum_label"): "label(arg_extreme(age_groups, abs(value(left_side, age_group)-value(right_side, age_group)), direction))",
        ("radar", "profile_advantage_count"): "count(filter(spokes, compare(value(profile_a, spoke), value(profile_b, spoke), direction)))",
        ("radar", "threshold_metric_count_for_panel"): "count(filter(spokes, compare(value(target_panel, spoke), threshold, direction)))",
        ("radar", "highlighted_metric_threshold_panel_count"): "count(filter(panels, compare(value(panel, highlighted_spoke), threshold, direction)))",
        ("radar", "matching_condition_panel_count"): "count(filter(panels, count(filter(spokes, compare(value(panel, spoke), threshold, direction))) >= minimum_spoke_count))",
        ("radial_progress", "progress_threshold_count"): "count(filter(progress_bars, compare(progress_value(bar), threshold, direction)))",
        ("radial_progress", "remaining_threshold_count"): "count(filter(progress_bars, compare(100-progress_value(bar), threshold, direction)))",
        ("radial_progress", "progress_interval_count"): "count(filter(progress_bars, lower <= progress_value(bar) <= upper))",
        ("radial_progress", "extremum_remaining_label"): "label(arg_extreme(progress_bars, 100-progress_value(bar), direction))",
        ("radial_sankey", "dominant_endpoint_label"): "label(select_by_rank(connected_opposite_endpoints(fixed_endpoint, endpoint_role), transfer_value(edge), rank_position=first, rank_order=largest))",
        ("radial_sankey", "transfer_total_value"): "sum(values(flows_matching_endpoint_role(endpoint_node, endpoint_role)))",
        ("region_map", "adjacent_category_count"): "count(filter(neighbor_regions(reference_region), category(region)=target_category))",
        ("region_map", "adjacent_numeric_threshold_count"): "count(filter(neighbor_regions(reference_region), compare(value(region), threshold, direction)))",
        ("region_map", "adjacent_same_category_count"): "count(filter(neighbor_regions(reference_region), category(region)=category(reference_region)))",
        ("region_map", "continent_category_region_count"): "count(filter(regions, continent=target_continent and category(region)=target_category))",
        ("region_map", "continent_threshold_region_count"): "count(filter(regions, continent=target_continent and compare(value(region), threshold, direction)))",
        ("region_map", "continent_region_count"): "count(filter(regions, continent=target_continent))",
        ("region_map", "group_filtered_region_value"): "sum(values(filter(regions, geographic_group and compare(value(region), threshold, direction))))",
        ("region_map", "categorical_region_count"): "count(filter(regions, category(region)=target_category))",
        ("region_map", "numeric_interval_region_count"): "count(filter(regions, lower <= value(region) <= upper))",
        ("region_map", "numeric_threshold_region_count"): "count(filter(regions, compare(value(region), threshold, direction)))",
        ("region_map", "named_region_set_total_value"): "sum(values(named_region_set))",
        ("sankey", "node_side_total_value"): "sum(values(flows_touching_endpoint_role(endpoint_node, endpoint_role)))",
        ("sankey", "path_bottleneck_value"): "min(values(path_edges(source_node, middle_node, target_node)))",
        ("sankey", "path_flow_difference"): "difference(value(path_edge_a), value(path_edge_b), mode=absolute)",
        ("sankey", "source_to_target_total_flow"): "sum(min(values(path_edges(source_node, middle_node, target_node))) for path in paths_between(source_node, target_node))",
        ("scatter_cluster", "cluster_separation_extremum_label"): "label(arg_extreme(clusters, nearest_centroid_distance(cluster), direction))",
        ("scatter_cluster", "cluster_spread_extremum_label"): "label(arg_extreme(clusters, within_cluster_spread(cluster), direction))",
        ("scatter_cluster", "cluster_trend_direction_label"): "label(arg_extreme(clusters, trend_slope(cluster), direction))",
        ("scatter_points", "axis_threshold_point_count"): "count(filter(scatter_points, compare(axis_value(point, axis), threshold, direction)))",
        ("scatter_points", "category_axis_mean_extremum_label"): "label(arg_extreme(categories, mean(axis_value(points_in_category, axis)), direction))",
        ("scatter_points", "category_threshold_point_count"): "count(filter(points_in_category(target_category), compare(axis_value(point, axis), threshold, direction)))",
        ("scatter_readout", "series_pair_value_gap_at_x"): "difference(value(series_a, x_axis_label), value(series_b, x_axis_label), mode=absolute)",
        ("scatter_readout", "series_y_anchor_other_series_value"): "value(comparison_series, x_axis_label=lookup_x(target_series, target_y_value))",
        ("scatter_readout", "series_x_extremum_label"): "label(arg_extreme(series_points, x_coordinate(point), direction))",
        ("scientific_axis_frame", "axis_span_value"): "difference(max_tick(axis), min_tick(axis), mode=axis_span)",
        ("scientific_axis_frame", "tick_spacing_value"): "difference(value(next_tick(axis)), value(first_tick(axis)), mode=tick_spacing)",
        ("single_series", "baseline_from_aggregate_percent_change"): "baseline_from_percent_change(sum(values(aggregate_labels)), percent_change)",
        ("single_series", "remaining_mean_after_removal"): "mean(values(filter(labels, label not in removed_labels)))",
        ("single_series", "target_share_after_removal"): "round(100 * value(target_label) / sum(values(filter(labels, label not in removed_labels))))",
        ("single_series", "endpoint_change_value"): "difference(value(end_label), value(start_label), mode=absolute_difference)",
        ("single_series", "interval_rate_value"): "round((value(end_label)-value(start_label)) / (index(end_label)-index(start_label)))",
        ("single_series", "monotone_streak_length"): "max(lengths(monotone_runs(series, direction)))",
        ("single_series", "order_statistic_label"): "label(select_by_rank(ordered_marks, value(mark), rank))",
        ("single_series", "order_statistic_value"): "value(select_by_rank(ordered_marks, value(mark), rank))",
        ("single_series", "observed_threshold_crossing_label"): "select_first_label(ordered_marks, compare(value(mark), threshold, direction))",
        ("single_series", "projected_threshold_crossing_label"): "select_first_label(project_linear_sequence(ordered_marks, future_slots), compare(projected_value(label), threshold, direction))",
        ("single_series", "turning_point_count"): "count(turning_points(ordered_series, kind))",
        ("single_series", "interval_value_count"): "count(filter(ordered_marks, lower <= value(mark) <= upper))",
        ("single_series", "threshold_value_count"): "count(filter(ordered_marks, compare(value(mark), threshold, direction)))",
        ("size_encoding", "category_total_extremum_label"): "label(arg_extreme(categories, sum(size_value(mark) for mark in filter(encoded_marks, category(mark)=category)), direction))",
        ("size_encoding", "filtered_item_extremum_label"): "label(arg_extreme(filter(encoded_marks, category(mark)=target_category), size_value(mark), direction))",
        ("size_encoding", "reference_size_neighbor_label"): "label(arg_min_distance(reference_mark, filter(encoded_marks, category(mark)=category(reference_mark)), metric=size_value_difference))",
        ("small_multiple", "conditioned_panel_sum_from_percent"): "sum(percent_to_count(value(panel, target_segment), panel_total) for panel in filter(panels, compare(value(panel, condition_segment), threshold, direction)))",
        ("small_multiple", "top_k_by_segment_then_sum_other_segment_count"): "sum(percent_to_count(value(panel, target_segment), panel_total) for panel in select_top_k(panels, value(panel, rank_segment), k, rank_direction))",
        ("small_multiple", "average_top_k_minus_average_bottom_k"): "difference(mean(values(select_top_k(panels, rank_segment, k, highest), target_segment)), mean(values(select_top_k(panels, rank_segment, k, lowest), target_segment)), mode=signed)",
        ("small_multiple", "composition_shift_l1_distance"): "sum_absolute(difference(value(start_panel, segment), value(end_panel, segment), mode=signed) for segment in shared_segments)",
        ("style_legend", "threshold_series_count"): "count(filter(styled_series, compare(value(series, target_x_position), threshold, direction)))",
        ("style_legend", "x_position_extremum_series_label"): "label(arg_extreme(styled_series, value(series, target_x_position), direction))",
        ("sunburst", "leaf_range_count_under_parent"): "count(filter(leaves_under_parent(parent_category), lower <= value(leaf) <= upper))",
        ("sunburst", "leaf_threshold_count_under_parent"): "count(filter(leaves_under_parent(parent_category), compare(value(leaf), threshold, predicate_direction)))",
        ("sunburst", "parent_total_extremum_label"): "label(arg_extreme(parent_categories, sum(values(leaves_under_parent(parent_category))), direction))",
        ("sunburst", "parent_total_value"): "sum(values(leaves_under_parent(parent_category)))",
        ("surface_3d", "panel_variation_label"): "label(arg_extreme(panels, vertical_range(panel), direction=highest))",
        ("surface_3d", "reference_nearest_label"): "label(arg_min_distance(reference_surface_point, candidate_surface_points, distance_metric))",
        ("surface_3d", "series_trend_label"): "label(arg_extreme(surface_series, endpoint_change(series), direction))",
        ("surface_3d", "surface_extremum_label"): "label(arg_extreme(surface_points, z_value(point), direction))",
        ("table", "column_rank_label"): "label(select_by_rank(rows, value(numeric_column, row), rank))",
        ("table", "column_summary_value"): "summary_statistic(values(numeric_column), statistic)",
        ("table", "filtered_column_mean"): "mean(values(filter(rows, categorical_column=filter_value), numeric_column))",
        ("table", "categorical_value_count"): "count(filter(rows, value(category_column, row)=target_category))",
        ("table", "interval_value_count"): "count(filter(rows, lower <= value(numeric_column, row) <= upper))",
        ("table", "threshold_count"): "count(filter(rows, compare(value(numeric_column, row), threshold, direction)))",
        ("table", "absolute_difference_between_rows_over_year_interval"): "difference(sum(values(row_a, year_interval)), sum(values(row_b, year_interval)), mode=absolute)",
        ("table", "sum_absolute_differences_between_rows_over_year_interval"): "sum_absolute(difference(value(row_a, year), value(row_b, year), mode=absolute) for year in year_interval)",
        ("treemap", "group_total_value"): "sum(values(children_under_parent(parent_category)))",
        ("treemap", "repeated_leaf_aggregate_value"): "summary_statistic(values(child_label_across_parents(child_label)), statistic)",
        ("uncertainty_band", "band_overlap_count"): "count(filter(x_axis_labels, intervals_overlap(band_interval(series_a, x_label), band_interval(series_b, x_label))))",
        ("uncertainty_band", "band_width_extremum_x_label"): "x_label(arg_extreme(x_axis_labels, upper_bound(target_series, x_label)-lower_bound(target_series, x_label), direction))",
        ("violin", "modality_label"): "label(filter(distributions, modality=two_clear_bulges))",
        ("violin", "mode_extremum_label"): "label(arg_extreme(distributions, mode_location(distribution), direction))",
        ("violin", "support_width_extremum_label"): "label(arg_extreme(distributions, support_width(distribution), direction))",
        ("waterfall", "remove_step_final_total"): "final_total(transform(contributions, remove_step=target_step))",
        ("waterfall", "reverse_step_final_total"): "final_total(transform(contributions, reverse_sign_step=target_step))",
        ("waterfall", "running_total_value"): "start_value + sum(contributions_through(target_step))",
        ("waterfall", "threshold_crossing_label"): "select_first_step(running_totals, threshold, direction)",
    }
    return by_scope.get((scene_id, scope), "")


def _game_detailed_program_schema(*, scene_id: str, scope: str, query: str) -> str:
    """Exact game-domain task-contract programs for taxonomy review.

    These schemas intentionally use the same compact program vocabulary as the
    chart review pass: count/filter/select/arg_extreme/value/sum/transform.
    Scene-specific names appear only as operands or rule names.
    """

    by_scope: dict[tuple[str, str], str] = {
        ("2048", "move_result_board_label"): "label(select_option(candidate_result_boards, option_board = simulate(board, rules=slide_merge_2048, action=move_direction).final_board))",
        ("backgammon", "blocked_destination_count"): "count(filter(candidate_destinations(dice_rolls), destination_status=blocked))",
        ("backgammon", "legal_move_count"): "count(filter(legal_moves(dice_rolls, board_state), move_filter))",
        ("backgammon", "point_state_count"): "count(filter(numbered_backgammon_points(board_state), checker_color=target_color, stack_state=target_stack_state))",
        ("battleship", "ship_status_count"): "count(filter(ships, ship_status=target_status))",
        ("bingo", "completed_line_count"): "count(completed_lines(board, axis_scope))",
        ("bingo", "line_sum_extremum_value"): "value(arg_extreme(lines, metric=sum(values(line)), direction=direction))",
        ("bowling", "first_pin_hit_label"): "label(first_collision(ball_path, pins))",
        ("bowling", "spare_path_label"): "label(select_option(shot_paths, option_rule=clears_remaining_pins))",
        ("brick_breaker", "hit_row_remaining_count"): "count(filter(bricks_in_hit_row, state=remaining_after_marked_hit))",
        ("brick_breaker", "next_hit_label"): "label(first_collision(ball_trajectory, bricks))",
        ("brick_breaker", "paddle_catch_label"): "label(paddle_zone_intersected_by(ball_trajectory))",
        ("bubble_shooter", "pop_color_label"): "label(color(inserted_group(marked_shot)))",
        ("bubble_shooter", "drop_count"): "count(disconnected_bubbles_after_pop(marked_shot))",
        ("bubble_shooter", "pop_count"): "count(popped_bubbles_after_marked_shot)",
        ("cards", "blackjack_best_hand_label"): "label(arg_extreme(hands, metric=blackjack_score(hand), direction=highest_valid))",
        ("cards", "exact_triple_count"): "count(filter(ranks, count(cards_of_rank(rank)) = 3))",
        ("cards", "longest_run_length"): "max(lengths(consecutive_rank_runs(cards_in_display_order)))",
        ("cards", "poker_best_hand_label"): "label(arg_extreme(hands, metric=poker_hand_rank(hand), direction=best))",
        ("cards", "higher_than_reference_count"): "count(filter(cards, compare(rank(card), rank(reference_card), direction=greater_than)))",
        ("cards", "same_suit_as_reference_count"): "count(filter(cards, suit(card) = suit(reference_card)))",
        ("cards", "trick_taking_winner_label"): "label(arg_extreme(played_cards, metric=trick_order_metric(card, lead_suit, trump_suit), direction=winning))",
        ("checkers", "max_capture_chain_length"): "longest_path(capture_state_graph(marked_king, board_state), source=marked_king, target=terminal_no_capture_state)",
        ("checkers", "move_count"): "count(filter(legal_moves(current_player), move_filter))",
        ("checkers", "piece_state_count"): "count(filter(checkers_pieces(board_state), piece_color=target_color, board_edge_state=target_edge_state))",
        ("chess", "check_attacker_count"): "count(attackers(target_king, opponent_pieces))",
        ("chess", "king_escape_square_count"): "count(legal_escape_squares(king))",
        ("chess", "marked_piece_destination_count"): "count(filter(legal_destinations(marked_piece), destination_filter))",
        ("chess", "colored_piece_kind_count"): "count(filter(pieces, piece_kind=target_kind and piece_color=target_color))",
        ("chess", "piece_kind_count"): "count(filter(pieces, piece_kind=target_kind))",
        ("chess", "player_capture_piece_count"): "count(filter(legal_moves(current_player), move_type=capture))",
        ("chess_variant", "marked_piece_destination_count"): "count(filter(legal_destinations(marked_piece), destination_filter))",
        ("connect_four", "safe_move_count"): "count(filter(legal_columns, opponent_wins_next=False))",
        ("connect_four", "winning_move_count"): "count(filter(legal_columns, move_result=win_for_current_player))",
        ("crossing", "moving_object_count"): "count(moving_objects)",
        ("darts", "ring_count"): "count(filter(darts, dart_ring=target_ring))",
        ("darts", "threshold_score_count"): "count(filter(darts, compare(score(dart), threshold, direction)))",
        ("darts", "total_score_option_label"): "label(select_option(score_options, option_score = score(marked_dart)))",
        ("dominoes", "extendable_first_play_count"): "count(filter(domino_tiles, can_extend_chain_after_first_play(tile)=True))",
        ("dominoes", "matching_end_count"): "count(filter(domino_tiles, matches_open_chain_end(tile)=True))",
        ("dominoes", "second_play_candidate_count"): "count(filter(domino_tiles, can_play_second_after_marked_first(tile)=True))",
        ("dominoes", "double_count"): "count(filter(domino_tiles, left_pips(tile) = right_pips(tile)))",
        ("dominoes", "higher_sum_than_reference_count"): "count(filter(domino_tiles, compare(sum(pips(tile)), sum(pips(reference_tile)), direction=greater_than)))",
        ("dominoes", "sum_to_target_count"): "count(filter(domino_tiles, sum(pips(tile)) = target_sum))",
        ("dots_and_boxes", "capture_move_count"): "count(filter(select(candidate_edges, edge_scope), completes_at_least_one_box(edge)=True))",
        ("dots_and_boxes", "three_sided_box_count"): "count(filter(boxes, drawn_side_count(box) = 3))",
        ("go", "group_adjacent_enemy_count"): "count(filter(stones, adjacent_to_group(stone, marked_group) and stone_color=opponent_color))",
        ("go", "group_liberty_count"): "count(filter(liberties(marked_group), liberty_filter))",
        ("hex", "connection_gap_count"): "count(connection_gap_cells(player, board_state))",
        ("hex", "winning_move_cell_label"): "label(filter(empty_cells, move_result=connects_player_sides))",
        ("marble_chain", "max_pop_direction_label"): "label(arg_extreme(shot_options, metric=pop_count_after_shot(option), direction=highest))",
        ("marble_chain", "target_pop_direction_label"): "label(select_option(shot_options, option_value=target_pop_count, option_metric=pop_count_after_shot(option)))",
        ("marble_chain", "shot_effect_value"): "count(popped_chain_marbles(transform(chain, marked_shot)))",
        ("match3", "max_clear_swap_label"): "label(arg_extreme(swap_options, metric=cleared_count_after_swap(option), direction=highest))",
        ("match3", "gem_count"): "count(filter(gems(scope), color_name=target_color))",
        ("match3", "target_clear_swap_label"): "label(select_option(swap_options, option_value=target_clear_count, option_metric=cleared_count_after_swap(option)))",
        ("minecraft", "ore_block_count"): "count(filter(blocks, block_type=target_ore_type))",
        ("minecraft", "resource_route_cost"): "sum(values(route_blocks, metric=resource_cost))",
        ("minesweeper", "forced_cell_count"): "count(filter(hidden_cells, forced_status=forced_cell_status))",
        ("minesweeper", "satisfied_clue_count"): "count(filter(numbered_clues, adjacent_flag_count(clue)=clue_value))",
        ("minigolf", "first_obstacle_label"): "label(first_collision(shot_path, obstacles))",
        ("minigolf", "shot_path_label"): "label(select_option(shot_paths, option_rule=path_satisfies_target))",
        ("nine_mens_morris", "pieces_in_mill_count"): "count(filter(pieces, participates_in_mill(piece)=True))",
        ("pacman", "next_item_label"): "label(first_item_on_route(route, items))",
        ("pacman", "path_pellet_count"): "count(filter(route_cells, contains_pellet=True))",
        ("pacman", "pellet_count_before_ghost"): "count(filter(prefix(route_cells, before=first(route_cell where contains_ghost=True)), contains_normal_pellet=True))",
        ("platformer", "collectible_count"): "count(filter(collectibles, collected_by_route=True))",
        ("platformer", "jump_landing_label"): "label(landing_platform(marked_jump))",
        ("pool", "blocking_ball_count"): "count(filter(balls, blocks_shot_line(ball, cue_ball, target_pocket)=True))",
        ("pool", "group_ball_count"): "count(filter(balls, ball_group=current_player_group))",
        ("reversi", "legal_destination_count"): "count(filter(legal_moves(current_player), destination_filter))",
        ("reversi", "marked_move_flip_count"): "count(flipped_discs(transform(board, marked_move)))",
        ("rhythm", "lane_color_hit_count"): "count(filter(notes, lane=target_lane and note_color=target_color and note_in_hit_window(note, beat_window)=True))",
        ("rhythm", "lane_hit_count"): "count(filter(notes, lane=target_lane and note_in_hit_window(note, beat_window)=True))",
        ("rhythm", "earliest_hit_lane_label"): "integer_label(arg_extreme(filter(notes, note_in_hit_window(note, beat_window)=True), metric=bottom_distance_to_hit_line, direction=lowest).lane)",
        ("rhythm", "most_hits_lane_label"): "integer_label(arg_extreme(lanes, metric=count(filter(notes, lane=lane and note_in_hit_window(note, beat_window)=True)), direction=highest))",
        ("rule_override_board", "line_result_count"): "count(filter(lines, result_after_rule_override(line)=override_result))",
        ("rule_override_board", "piece_result_count"): "count(filter(pieces, result_after_rule_override(piece)=override_result))",
        ("snake", "path_outcome_option_label"): "label(select_option(path_options, option_path_result = simulate_path(snake_state, path_option)))",
        ("snake", "safe_direction_count"): "count(filter(directions, move_collision(direction)=False))",
        ("snakes_ladders", "best_roll_value"): "argmax_value(roll_plans, transition_rule=jumps, objective=final_square_after_roll_plan(start_square, jumps, horizon_roll_count))",
        ("snakes_ladders", "move_outcome_value"): "value(simulate(start_square, rules=jumps, action=die_value).final_square)",
        ("solitaire", "foundation_ready_count"): "count(filter(cards, can_move_to_foundation(card)=True))",
        ("solitaire", "move_legality_label"): "label(move_legality(marked_move))",
        ("solitaire", "tableau_sequence_count"): "count(tableau_descending_alternating_sequences(tableau_columns))",
        ("space_shooter", "clear_shot_count"): "count(filter(enemy_targets, shot_line_blocked(target)=False))",
        ("space_shooter", "highest_threat_label"): "label(arg_extreme(enemies, metric=threat_score(enemy), direction=highest))",
        ("space_shooter", "projectile_intercept_count"): "count(filter(projectiles, intersects_player_zone(projectile)=True))",
        ("space_shooter", "safe_lane_count"): "count(filter(lanes, lane_threat_count(lane)=0))",
        ("sudoku", "marked_cell_candidate_count"): "count(candidate_digits(marked_cell, board_state))",
        ("sudoku", "marked_cell_value"): "value(single(candidate_digits(marked_cell, board_state)))",
        ("sudoku", "repeated_digit_count"): "count(repeated_digits(selected_unit))",
        ("sudoku", "unit_missing_digits_count"): "count(missing_digits(selected_unit))",
        ("tetris", "drop_result_label"): "label(select_option(drop_options, option_result = simulate_drop(board, piece, option)))",
        ("tetris", "line_clear_count"): "value(arg_extreme(drop_options, metric=cleared_line_count(simulate_drop(board, next_piece, option)), direction=highest))",
        ("ultimate_tictactoe", "line_completion_move_label"): "label(filter(local_board_cells, local_line_completion_rule(player, cell, tactic_kind)=True))",
        ("ultimate_tictactoe", "small_board_status_count"): "count(filter(local_boards, board_status=target_status))",
    }
    if scene_id == "2048" and scope == "max_tile_value":
        return "value(simulate(board, rules=slide_merge_2048, action=move_direction).final_board, property=max_tile_value)"
    if scene_id == "2048" and scope == "merge_count":
        return "count(simulate(board, rules=slide_merge_2048, action=move_direction).merge_events)"
    if scene_id == "2048" and scope == "score_value":
        return "sum(values(simulate(board, rules=slide_merge_2048, action=move_direction).merge_events, metric=created_tile_value))"
    return by_scope.get((scene_id, scope), "")


def _puzzle_detailed_program_schema(*, scene_id: str, scope: str, query: str) -> str:
    """Exact puzzle-domain task-contract programs for taxonomy review."""

    del query
    by_scope: dict[tuple[str, str], str] = {
        ("agent_automaton", "agent_cell_flip_count"): "count(filter(cells(marked_region), final_state(simulate(agent_grid, automaton_rule_table, step_count), cell) != initial_state(agent_grid, cell)))",
        ("agent_automaton", "agent_final_pose_label"): "label(select_option(candidate_pose_boards, pose=final_pose(simulate(agent_grid, automaton_rule_table, step_count))))",
        ("analog_clock", "offset_readout"): "read_time(apply_time_offset(clock_hands, offset_minutes, offset_direction))",
        ("arithmetic_constraint", "consecutive_window_sum_value"): "solve_window_sum(number_sequence, window_length, target_window)",
        ("arithmetic_constraint", "equal_sum_line_constraint_value"): "solve_equal_sum_line(line_grid, equal_sum_constraint, target_cell)",
        ("arithmetic_constraint", "paired_cluster_sum_relation_value"): "solve_cluster_sum_relation(cluster_grid, paired_cluster_rule, target_cell)",
        ("arithmetic_constraint", "vertical_arithmetic_hidden_digit_value"): "solve_vertical_arithmetic(equation_grid, operation=addition_or_subtraction, target_hidden_digit)",
        ("arithmetic_constraint", "letter_digit_value"): "solve_cryptarithm_symbol_mapping(equation_grid, target_symbol)",
        ("arithmetic_constraint", "number_wall_value"): "solve_number_wall(wall_grid, recurrence_operation, target_cell)",
        ("arithmetic_constraint", "operation_table_cell_value"): "value(apply_operation_table(row_header, column_header, operation_rule))",
        ("arithmetic_constraint", "row_column_total_missing_value"): "solve_missing_cell(row_column_total_grid, target_cell)",
        ("cell_board", "attribute_count"): "count(filter(cells(board_scope), cell_attribute=target_attribute))",
        ("cell_board", "single_attribute_membership_count"): "count(filter(cells(board), color(cell)=target_color))",
        ("cell_board", "scoped_attribute_count"): "count(filter(cells(select_scope(board, scope_selector)), color(cell)=target_color))",
        ("cell_board", "color_component_count"): "count(connected_components(filter(cells, color=target_color), adjacency=orthogonal))",
        ("cell_board", "largest_component_size"): "max(size(component) for component in connected_components(filter(cells, color=target_color), adjacency=orthogonal))",
        ("cell_board", "minimum_color_set_distance_value"): "min(manhattan_distance(cell_a, cell_b) for cell_a in color_set_a for cell_b in color_set_b)",
        ("cell_board", "shortest_path_length_value"): "length(shortest_path(grid_graph(open_cells), source_cell, target_cell))",
        ("cell_board", "reachable_target_count"): "count(filter(target_cells, reachable_from(start_cell, movement_rule)=reachability_flag))",
        ("cell_board", "reachable_region_size"): "count(reachable_cells(grid_graph(open_cells), start_cell, movement_rule))",
        ("cell_board", "symmetry_violation_count"): "count(filter(cells, violates_symmetry(cell, symmetry_axis)))",
        ("clock_collection", "compare"): "label(arg_extreme(clocks, read_time(clock), direction))",
        ("color_gradient", "color_gradient_completion_label"): "label(select_option(candidate_cells, completes_linear_gradient(blank_position)))",
        ("color_gradient", "color_gradient_violation_cell_label"): "label(select_rule_violation(gradient_cells, gradient_rule))",
        ("counterfactual_board", "board_dimension_count"): "count(board_dimension(transform(board_grid, counterfactual_edit), dimension_axis))",
        ("counterfactual_board", "board_line_count"): "count(board_lines(transform(line_board, counterfactual_edit), line_orientation))",
        ("cube_net", "cube_net_face_relation_label"): "label(resolve_cube_face_relation(cube_net, reference_face_or_edge, relation_mode))",
        ("cube_net", "cube_rolling_result_label"): "label(select_option(candidate_faces, final_face_after_roll(cube_net, roll_sequence, queried_face_position)))",
        ("cube_net", "folded_path_endpoint_label"): "label(folded_path(cube_net, path_marks).endpoint_face)",
        ("cube_net", "folded_path_face_sequence_label"): "label(select_option(candidate_sequences, equals(folded_path(cube_net, path_marks).face_sequence)))",
        ("cyclic_order", "cyclic_order_equivalent_label"): "label(select_option(candidate_loops, cyclic_order_equivalent(reference_loop, allow_rotation=True, allow_reflection=False)))",
        ("dice_probability", "dice_conditional_event_value"): "reduced_fraction(count(filter(die_faces, condition_selector(face) and target_selector(face))) / count(filter(die_faces, condition_selector(face))))",
        ("dice_probability", "pair_attribute_combo_probability"): "reduced_fraction(count(pair_outcomes(die_a, die_b) where paired_attribute_event) / count(pair_outcomes(die_a, die_b)))",
        ("dice_probability", "pair_difference_probability"): "reduced_fraction(count(pair_outcomes(die_a, die_b) where abs(value(die_a)-value(die_b))=target_difference) / count(pair_outcomes(die_a, die_b)))",
        ("dice_probability", "pair_sum_probability"): "reduced_fraction(count(pair_outcomes(die_a, die_b) where value(die_a)+value(die_b)=target_sum) / count(pair_outcomes(die_a, die_b)))",
        ("dice_probability", "pair_sum_threshold_probability"): "reduced_fraction(count(pair_outcomes(die_a, die_b) where compare(value(die_a)+value(die_b), threshold, direction)) / count(pair_outcomes(die_a, die_b)))",
        ("dice_probability", "single_attribute_probability"): "reduced_fraction(count(outcomes(die) where single_die_attribute_event) / count(outcomes(die)))",
        ("dice_probability", "single_threshold_probability"): "reduced_fraction(count(outcomes(die) where compare(value(die), threshold, direction)) / count(outcomes(die)))",
        ("life_automaton", "life_future_grid_label"): "label(select_option(candidate_grids, equals(simulate_life(initial_grid, step_count))))",
        ("life_automaton", "life_population_count"): "count(filter(cells(marked_line), state(simulate_life(initial_grid, step_count), cell)=alive))",
        ("logic_grid", "grid_king_non_touch_label"): "label(select_option(candidate_cells, satisfies_non_touching_kings_rule(grid_state, candidate_cell)))",
        ("logic_grid", "grid_uniqueness_completion_label"): "label(select_option(candidate_grids, satisfies_row_column_uniqueness(grid_state)))",
        ("matchstick", "matchstick_loose_endpoint_extremum_label"): "label(arg_extreme(candidate_matchstick_figures, loose_endpoint_count(figure), direction))",
        ("matchstick", "matchstick_number_transform_label"): "label(select_option(candidate_numbers, reachable_by_matchstick_edit(source_number, edit_direction)))",
        ("maze", "exit_reachability_label"): "label(select_exit(boundary_exits, reachable_from(start_cell, maze_graph)=target_reachability))",
        ("maze", "reachable_exit_count"): "count(filter(boundary_exits, reachable_from(start_cell, maze_graph)=True))",
        ("music_staff", "bar_count_value"): "count(measures(staff_excerpt))",
        ("music_staff", "chord_harmony_label"): "label(read_chord_property(staff_excerpt, target_chord, harmony_label_type))",
        ("music_staff", "dominant_chord_count"): "count(filter(chords(staff_excerpt), harmonic_function=dominant))",
        ("music_staff", "duration_equivalence_label"): "label(compare_note_durations(marked_note_group, duration_relation))",
        ("music_staff", "key_signature_label"): "label(read_key_signature(staff_excerpt))",
        ("music_staff", "scale_degree_function_label"): "label(read_scale_degree_function(staff_excerpt, marked_note))",
        ("music_staff", "scale_validation_truth_label"): "label(validate_scale_membership(staff_excerpt, marked_notes))",
        ("music_staff", "time_signature_label"): "label(read_time_signature(staff_excerpt))",
        ("music_staff", "meter_type_label"): "label(classify_meter(staff_excerpt))",
        ("music_staff", "articulation_symbol_label"): "label(read_articulation_symbol(marked_note))",
        ("music_staff", "note_name_label"): "label(read_pitch_name(marked_note))",
        ("music_staff", "interval_name_label"): "label(read_pitch_interval(marked_note_pair))",
        ("music_staff", "same_pitch_truth_label"): "label(compare_pitch_equivalence(marked_note_pair))",
        ("music_staff", "transposed_pitch_truth_label"): "label(validate_transposed_pitch(marked_note_pair, transposition_interval))",
        ("nonogram", "nonogram_candidate_solution_label"): "label(select_option(candidate_grids, satisfies_nonogram_clues(row_clues, column_clues)))",
        ("nonogram", "nonogram_line_completion_label"): "label(select_option(candidate_lines, satisfies_line_clue(marked_line_clue)))",
        ("overlay", "overlay_result_label"): "label(select_option(candidate_panels, equals(overlay_layers(layer_a, layer_b))))",
        ("paper_fold", "paper_fold_result_label"): "label(select_option(candidate_panels, equals(fold_transform(sheet, fold_sequence))))",
        ("paper_fold_cut", "paper_fold_cut_result_label"): "label(select_option(candidate_panels, equals(unfold_after_cuts(fold_sequence, cut_marks))))",
        ("pipe_flow", "pipe_flow_repair_tile_label"): "label(select_option(candidate_tiles, makes_pipe_network_connected(pipe_grid, blank_cell, tile)))",
        ("polyomino_missing", "marked_region_piece_label"): "label(select_option(candidate_pieces, matches_marked_missing_region(board, marked_region)))",
        ("polyomino_missing", "rectangle_complement_piece"): "label(select_option(candidate_pieces, completes_rectangle_complement(polyomino_board)))",
        ("raven_matrix", "raven_analogical_transform_label"): "label(select_option(candidate_panels, completes_raven_matrix(matrix_context, rule=analogical_transform)))",
        ("raven_matrix", "raven_count_progression_label"): "label(select_option(candidate_panels, completes_raven_matrix(matrix_context, rule=count_progression)))",
        ("raven_matrix", "raven_position_progression_label"): "label(select_option(candidate_panels, completes_raven_matrix(matrix_context, rule=position_progression)))",
        ("raven_matrix", "raven_set_operation_label"): "label(select_option(candidate_panels, completes_raven_matrix(matrix_context, rule=set_operation)))",
        ("raven_matrix", "raven_spatial_transform_label"): "label(select_option(candidate_panels, completes_raven_matrix(matrix_context, rule=spatial_transform)))",
        ("rubiks_net", "post_move_face_color_count_label"): "label(select_option(count_options, option_value=count_face_colors(apply_cube_moves(cube_net, move_sequence), target_face)))",
        ("rubiks_net", "static_face_color_count_label"): "label(select_option(count_options, option_value=count_face_colors(cube_net, target_face)))",
        ("rubiks_net", "rubiks_move_result_label"): "label(select_option(candidate_nets, equals(apply_cube_moves(cube_net, move_sequence))))",
        ("rubiks_net", "post_move_sticker_color_label"): "label(read_sticker_color(apply_cube_moves(cube_net, move_sequence), target_sticker))",
        ("rubiks_net", "static_sticker_color_label"): "label(read_sticker_color(cube_net, target_sticker))",
        ("sliding_block", "sliding_block_blocker_count"): "count(blockers_on_slide_path(board_state, marked_block, move_direction))",
        ("sliding_block", "movable_block_count"): "count(filter(blocks(board_state), has_legal_slide(block, distance>=1)))",
        ("sliding_block", "sliding_block_move_result_label"): "label(select_option(candidate_boards, equals(apply_slide_move(board_state, marked_block, move_direction))))",
        ("sokoban", "nearest_counterpart_label"): "label(arg_min_distance(reference_entity, counterpart_candidates, metric=manhattan_distance))",
        ("sokoban", "box_target_manhattan_rank_label"): "label(select_by_rank(box_target_pairs, manhattan_distance(box, target), rank))",
        ("sokoban", "path_validity_sequence_label"): "label(select_option(candidate_paths, path_validity(path, sokoban_board)=target_validity))",
        ("sokoban", "shortest_path_sequence_label"): "label(select_option(candidate_paths, equals(shortest_path(sokoban_board, source, target))))",
        ("spinner_probability", "single_attribute_probability"): "reduced_fraction(count(filter(outcomes(spinner), attribute_value(sector, attribute_axis) in target_values)) / count(outcomes(spinner)))",
        ("spinner_probability", "multi_attribute_and_probability"): "reduced_fraction(count(filter(outcomes(spinner), all(attribute_predicate(sector, predicate) for predicate in attribute_predicates))) / count(outcomes(spinner)))",
        ("spinner_probability", "multi_attribute_or_probability"): "reduced_fraction(count(filter(outcomes(spinner), any(attribute_predicate(sector, predicate) for predicate in attribute_predicates))) / count(outcomes(spinner)))",
        ("spinner_probability", "spinner_pair_event_value"): "reduced_fraction(count(pair_outcomes(spinner_a, spinner_b) where pair_event_schema) / count(pair_outcomes(spinner_a, spinner_b)))",
        ("star_battle", "star_battle_remaining_count"): "count(filter(candidate_cells(scoped_unit), satisfies_star_battle_constraints(cell)))",
        ("star_battle", "valid_cell_anywhere_label"): "label(select_option(candidate_cells(scope=all_visible_grid_cells), satisfies_star_battle_constraints(cell)))",
        ("star_battle", "scoped_valid_cell_label"): "label(select_option(candidate_cells(scope=marked_scope), satisfies_star_battle_constraints(cell)))",
        ("string_topology", "string_component_count"): "count(filter(string_components, component_type=target_component_type))",
        ("tangram", "tangram_contact_count"): "count(filter(tangram_pieces, touches(marked_piece)))",
        ("tangram", "tangram_missing_piece_label"): "label(select_option(candidate_pieces, fits_tangram_gap(marked_gap)))",
        ("tents", "tents_missing_tent_cell_label"): "label(select_option(candidate_cells, legal_tent_for_marked_tree(tents_grid, cell)))",
        ("tents", "tents_valid_candidate_count"): "count(filter(candidate_cells, legal_tent_for_marked_tree(tents_grid, cell)))",
        ("toggle_grid", "toggle_repair_switch_label"): "label(select_option(candidate_switches, transform(start_grid, switch)=target_grid))",
        ("toggle_grid", "toggle_result_label"): "label(select_option(candidate_grids, equals(transform(start_grid, switch_sequence))))",
        ("turing_tape", "turing_written_symbol_count"): "count(filter(tape_cells(simulate_turing(tape, transition_table, step_count)), written_symbol=target_symbol))",
        ("voxel_cube", "cube_count"): "count(voxels(structure))",
        ("voxel_cube", "cube_painted_face_count"): "count(filter(voxels_or_faces(structure), painted_face_predicate))",
        ("voxel_cube", "cube_projection_consistency_label"): "label(check_projection_consistency(voxel_structure, projection_views))",
        ("voxel_cube", "cube_projection_match_label"): "label(select_option(candidate_projections, equals(project(voxel_structure, view_axis))))",
        ("voxel_cube", "cube_structure_change_count"): "count(changed_voxels(transform(voxel_structure, edit)))",
        ("voxel_cube", "cube_visible_projection_count"): "count(visible_voxels(project(voxel_structure, view_axis)))",
        ("voxel_ladder", "reachable_checkpoint_count"): "count(filter(checkpoints, reachable_from(start_checkpoint, ladder_graph)=True))",
        ("voxel_ladder", "unreachable_checkpoint_label"): "label(select_checkpoint(checkpoints, reachable_from(start_checkpoint, ladder_graph)=False))",
        ("voxel_ladder", "checkpoint_sequence_label"): "label(select_option(candidate_sequences, valid_route_sequence(ladder_graph, checkpoints)))",
        ("word_search", "search_letter_count_value"): "count(filter(cells(word_grid), letter=target_letter))",
        ("word_search", "search_location_label"): "label(select_option(candidate_paths, spells_word(word_grid, target_word)))",
        ("word_search", "search_present_word_count"): "count(filter(word_bank, present_in_grid(word_grid, word)))",
    }
    return by_scope.get((scene_id, scope), "")


def _right_triangle_inverse_trig_formula(query_id: str) -> str:
    formulas = {
        "angle_from_adjacent_hypotenuse": "inverse_cos_adjacent_hypotenuse",
        "angle_from_opposite_hypotenuse": "inverse_sin_opposite_hypotenuse",
        "angle_from_opposite_adjacent": "inverse_tan_opposite_adjacent",
    }
    return formulas.get(query_id, "")


def base_program_contract(program_schema: str) -> str:
    return str(program_schema or "").split("; query_branch=", 1)[0].strip()


def refresh_program_contract(row: dict[str, Any]) -> dict[str, Any]:
    signature = signature_from_slug(
        str(row["proposed_task_slug"]),
        query_id=str(row["current_query_id"]),
        domain=str(row["domain"]),
        scene_id=str(row["scene_id"]),
    )
    row["program_signature_id"] = signature.signature_id
    row["program_schema"] = detailed_program_schema(
        signature,
        slug=str(row["proposed_task_slug"]),
        query_id=str(row["current_query_id"]),
        domain=str(row["domain"]),
        scene_id=str(row["scene_id"]),
    )
    row["base_program_contract"] = base_program_contract(str(row["program_schema"]))
    return row


def build_analysis_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, ProgramSignature]]:
    live_inventory = build_live_inventory()
    boundary_seed = load_boundary_seed_rows()
    argument_overrides = load_program_argument_overrides()
    observed = collect_observed_schemas()
    program_catalog: dict[str, ProgramSignature] = {}
    rows: list[dict[str, Any]] = []

    for item in live_inventory:
        query_ids = split_pipe(item["query_ids"]) or [item["task_slug"]]
        for query_id in query_ids:
            key = (item["task_id"], query_id)
            prior_rows = boundary_seed.get(key) or [None]
            for prior in prior_rows:
                proposed_slug = prior["proposed_task_slug"] if prior else item["task_slug"]
                proposed_id = prior["proposed_task_id"] if prior else proposed_task_id(item["domain"], item["scene_id"], proposed_slug)
                obs = observed_schema_for_boundary_row(
                    item=item,
                    query_id=str(query_id),
                    prior=prior,
                    fallback=observed.get(key),
                )
                seed_answer_types = tuple(split_pipe(prior.get("answer_types", ""))) if prior else ()
                seed_annotation_types = tuple(split_pipe(prior.get("annotation_types", ""))) if prior else ()
                answer_types = (
                    seed_answer_types
                    or (obs.answer_types if obs and obs.answer_types else tuple(split_pipe(item["answer_types"])))
                )
                annotation_types = (
                    seed_annotation_types
                    or (obs.annotation_types if obs and obs.annotation_types else tuple(split_pipe(item["annotation_types"])))
                )
                answer_schema = normalize_answer_schema(
                    answer_types,
                    task_slug=str(proposed_slug),
                    query_id=str(query_id),
                    domain=str(item["domain"]),
                    scene_id=str(item["scene_id"]),
                )
                annotation_schema, annotation_notes = normalize_annotation_schema(annotation_types)
                signature = signature_from_slug(
                    str(proposed_slug),
                    query_id=str(query_id),
                    domain=str(item["domain"]),
                    scene_id=str(item["scene_id"]),
                )
                program_schema = detailed_program_schema(
                    signature,
                    slug=str(proposed_slug),
                    query_id=str(query_id),
                    domain=str(item["domain"]),
                    scene_id=str(item["scene_id"]),
                )
                program_catalog.setdefault(signature.signature_id, signature)
                scene_contract = f"{item['domain']}/{item['scene_id']} renderer grammar with stable public scene_id={item['scene_id']}"
                view_contract = f"{item['scene_id']}.default_view"
                decision_source = "manual_boundary_seed" if prior else "current_inventory_fallback"
                if prior and norm_text(prior.get("trace_filter_path", "")):
                    decision_source += "+trace_filter"
                rows.append(
                    {
                        "domain": item["domain"],
                        "scene_id": item["scene_id"],
                        "current_task_id": item["task_id"],
                        "current_query_id": query_id,
                        "current_task_slug": item["task_slug"],
                        "proposed_task_id": proposed_id,
                        "proposed_task_slug": proposed_slug,
                        "scene_contract": scene_contract,
                        "view_contract": view_contract,
                        "answer_schema": answer_schema,
                        "answer_type_observed": unique_join(answer_types),
                        "annotation_schema": annotation_schema,
                        "annotation_type_observed": unique_join(annotation_types),
                        "annotation_schema_notes": annotation_notes,
                        "program_signature_id": signature.signature_id,
                        "program_schema": program_schema,
                        "base_program_contract": base_program_contract(program_schema),
                        "parameter_axes": infer_parameter_axes(str(proposed_slug), str(query_id)),
                        "decision_source": decision_source,
                        "rationale": contract_rationale(prior, signature, answer_schema, annotation_schema),
                        "generation_failures": item.get("generation_failures", ""),
                        "source_file": item.get("source_file", ""),
                        "doc_path": item.get("doc_path", ""),
                        "sample_count": obs.sample_count if obs else 0,
                        "example_json_paths": unique_join(obs.example_json_paths if obs else ()),
                        "example_image_paths": unique_join(obs.example_image_paths if obs else ()),
                    }
                )

    rows = enforce_contract_splits(rows)
    rows = apply_base_contract_refinements(rows)
    rows = [attach_program_arguments(row, argument_overrides) for row in rows]
    summary_rows = build_task_summary(rows)
    decision_by_task = {str(row["current_task_id"]): str(row["decision"]) for row in summary_rows}
    proposed_count_by_task = {str(row["current_task_id"]): int(row["proposed_task_count"]) for row in summary_rows}
    for row in rows:
        current_task_id = str(row["current_task_id"])
        row["decision"] = decision_by_task.get(current_task_id, "blocked_needs_inspection")
        row["split_from"] = current_task_id if row["decision"] == "split" else ""
        row["merge_with"] = ""
        row["proposed_task_group_size"] = proposed_count_by_task.get(current_task_id, 1)
    return rows, summary_rows, program_catalog


def apply_base_contract_refinements(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge proposed task units that differ only by approved parameter axes."""

    adjusted: list[dict[str, Any]] = []
    for row in rows:
        proposed_id = str(row["proposed_task_id"])
        canonical_slug = CANONICAL_PROPOSED_TASK_OVERRIDES.get(proposed_id)
        if not canonical_slug:
            adjusted.append(row)
            continue
        row = dict(row)
        row["proposed_task_slug"] = canonical_slug
        row["proposed_task_id"] = proposed_task_id(str(row["domain"]), str(row["scene_id"]), canonical_slug)
        row = refresh_program_contract(row)
        if "base_contract_merge" not in str(row["decision_source"]):
            row["decision_source"] = f"{row['decision_source']}+base_contract_merge"
        row["rationale"] = (
            str(row["rationale"])
            + " Contract-v0 base-contract refinement merged this branch as a parameterized query inside the canonical proposed task."
        )
        adjusted.append(row)
    return sorted(adjusted, key=lambda r: (str(r["domain"]), str(r["scene_id"]), str(r["current_task_id"]), str(r["current_query_id"])))


def infer_parameter_axes(slug: str, query_id: str) -> str:
    text = f"{slug} {query_id}".lower()
    axes: list[str] = []
    if any(token in text for token in ("highest", "lowest", "maximum", "minimum", "max_", "min_")):
        axes.append("extremum_direction")
    if any(token in text for token in ("above", "below", "greater", "less", "threshold")):
        axes.append("predicate_direction")
    if "interval" in text or "between" in text or "range" in text:
        axes.append("interval_bounds")
    if any(token in text for token in ("rank", "nth", "ordinal", "top_k")):
        axes.append("rank_position")
    if any(token in text for token in ("attribute", "color", "shape", "type", "status", "category")):
        axes.append("target_attribute")
    if any(token in text for token in ("source", "target", "reference", "anchor")):
        axes.append("role_selection")
    if not axes:
        axes.append("sampled_scene_values")
    return "|".join(axes)


def attach_program_arguments(row: dict[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(row)
    payload = infer_program_arguments(row, overrides)
    row["program_arguments_json"] = json.dumps(payload, sort_keys=True)
    return row


def infer_program_arguments(row: Mapping[str, Any], overrides: Mapping[str, Any]) -> dict[str, Any]:
    """Infer review-facing argument/variant metadata for one query row.

    These arguments explain allowed variation inside a task. They are not used
    as hard task-boundary fields.
    """

    override = _program_argument_override(row, overrides)
    if override:
        return _normalize_program_argument_payload(override, default_status="curated")

    signature_id = str(row.get("program_signature_id", ""))
    slug = str(row.get("proposed_task_slug") or row.get("current_task_slug") or "")
    query_id = str(row.get("current_query_id") or "")
    domain = str(row.get("domain", ""))
    scene_id = str(row.get("scene_id", ""))
    text = f"{slug} {query_id}".lower()
    axes = split_pipe(str(row.get("parameter_axes", "")).replace("|", "|"))
    base_schema = str(row.get("base_program_contract") or row.get("program_schema") or "").split("; scene=", 1)[0]
    is_concrete_chart = domain == "charts" and _is_concrete_chart_contract(base_schema)
    is_concrete_game = domain == "games" and _is_concrete_game_contract(base_schema)
    is_concrete_geometry = domain == "geometry" and _is_concrete_geometry_contract(base_schema)
    is_concrete_graph = domain == "graph" and _is_concrete_graph_contract(base_schema)
    is_concrete_icons = domain == "icons" and _is_concrete_icon_contract(base_schema)
    is_concrete_illustrations = domain == "illustrations" and _is_concrete_illustration_contract(base_schema)
    is_concrete_pages = domain == "pages" and _is_concrete_pages_contract(base_schema)
    is_concrete_physics = domain == "physics" and _is_concrete_physics_contract(base_schema)
    is_concrete_puzzle = domain == "puzzles" and _is_concrete_puzzle_contract(base_schema)
    is_concrete_three_d = domain == "three_d" and _is_concrete_three_d_contract(base_schema)
    is_concrete_finalized_domain = (
        is_concrete_chart
        or is_concrete_game
        or is_concrete_geometry
        or is_concrete_graph
        or is_concrete_icons
        or is_concrete_illustrations
        or is_concrete_pages
        or is_concrete_physics
        or is_concrete_puzzle
        or is_concrete_three_d
    )

    arguments: dict[str, dict[str, Any]] = {}

    def add(
        name: str,
        *,
        value_type: str,
        allowed_values: Iterable[str],
        source: str,
        notes: str = "",
    ) -> None:
        values = [str(value) for value in allowed_values if str(value)]
        if not values:
            return
        existing = arguments.get(name)
        if existing:
            if (
                is_concrete_finalized_domain
                and "program_schema_concrete" in str(existing.get("source", ""))
                and source != "program_schema_concrete"
            ):
                existing["source"] = unique_join([existing.get("source", ""), source], sep="|")
                if notes:
                    existing["notes"] = unique_join([existing.get("notes", ""), notes], sep=" ")
                return
            existing_values = set(existing["allowed_values"])
            if source != "program_schema":
                existing_values.discard(_default_placeholder_value(name))
                if existing.get("notes") == "Generic program placeholder; refine with a manual override when concrete values are known.":
                    existing["notes"] = ""
            existing["allowed_values"] = sorted(existing_values | set(values))
            existing["source"] = unique_join([existing.get("source", ""), source], sep="|")
            if notes:
                existing["notes"] = unique_join([existing.get("notes", ""), notes], sep=" ")
            return
        arguments[name] = {
            "value_type": value_type,
            "allowed_values": sorted(set(values)),
            "source": source,
            "notes": notes,
        }

    use_generic_signature_defaults = not is_concrete_finalized_domain

    for placeholder in _program_placeholders(base_schema):
        values = [_default_placeholder_value(placeholder)]
        if is_concrete_game:
            values = _game_placeholder_allowed_values(
                placeholder,
                scene_id=scene_id,
                slug=slug,
                query_id=query_id,
            )
        elif is_concrete_physics:
            values = _physics_placeholder_allowed_values(
                placeholder,
                scene_id=scene_id,
                slug=slug,
                query_id=query_id,
            )
        elif is_concrete_puzzle:
            values = _puzzle_placeholder_allowed_values(
                placeholder,
                scene_id=scene_id,
                slug=slug,
                query_id=query_id,
            )
        elif is_concrete_icons:
            values = _icon_placeholder_allowed_values(
                placeholder,
                scene_id=scene_id,
                slug=slug,
                query_id=query_id,
            )
        elif is_concrete_illustrations:
            values = _illustration_placeholder_allowed_values(
                placeholder,
                scene_id=scene_id,
                slug=slug,
                query_id=query_id,
            )
        elif is_concrete_pages:
            values = _pages_placeholder_allowed_values(
                placeholder,
                scene_id=scene_id,
                slug=slug,
                query_id=query_id,
            )
        elif is_concrete_three_d:
            values = _three_d_placeholder_allowed_values(
                placeholder,
                scene_id=scene_id,
                slug=slug,
                query_id=query_id,
            )
        add(
            placeholder,
            value_type=_placeholder_value_type(placeholder),
            allowed_values=values,
            source="program_schema_concrete" if is_concrete_finalized_domain else "program_schema",
            notes="" if is_concrete_finalized_domain else "Generic program placeholder; refine with a manual override when concrete values are known.",
        )

    if "extremum_direction" in axes or signature_id in {"selection.extreme_metric_label", "numeric.extreme_metric_value"}:
        add("direction", value_type="enum", allowed_values=_direction_values(text, default=("highest", "lowest")), source="query_id|signature_defaults")
    if "predicate_direction" in axes or signature_id in {"count.one_bound_threshold", "count.pairwise_comparison"}:
        add("direction", value_type="enum", allowed_values=_predicate_direction_values(text), source="query_id|signature_defaults")
    if "interval_bounds" in axes or signature_id == "count.interval_predicate":
        add("lower", value_type="numeric_bound", allowed_values=["sampled_lower_bound"], source="signature_defaults")
        add("upper", value_type="numeric_bound", allowed_values=["sampled_upper_bound"], source="signature_defaults")
    if "rank_position" in axes or signature_id in {"selection.ranked_item", "numeric.ranked_difference"}:
        rank_values = _rank_values(text)
        if is_concrete_puzzle and scene_id == "sokoban" and rank_values == ["ranked_position"]:
            rank_values = ["sampled_manhattan_rank"]
        add("rank", value_type="enum", allowed_values=rank_values, source="query_id|signature_defaults")
    if "target_attribute" in axes:
        add("target_attribute", value_type="object_attribute", allowed_values=_target_attribute_values(text), source="query_id|parameter_axes")
    if "role_selection" in axes:
        add("role", value_type="semantic_role", allowed_values=_role_values(text), source="query_id|parameter_axes")

    if use_generic_signature_defaults and signature_id == "numeric.difference_or_change":
        add("source_a", value_type="semantic_role", allowed_values=_source_role_values(text, first=True), source="signature_defaults|query_id")
        add("source_b", value_type="semantic_role", allowed_values=_source_role_values(text, first=False), source="signature_defaults|query_id")
        add("mode", value_type="enum", allowed_values=_difference_mode_values(text), source="signature_defaults|query_id")
    elif use_generic_signature_defaults and signature_id == "numeric.ranked_difference":
        add("rank_a", value_type="enum", allowed_values=_rank_pair_values(text, first=True), source="signature_defaults|query_id")
        add("rank_b", value_type="enum", allowed_values=_rank_pair_values(text, first=False), source="signature_defaults|query_id")
        add("metric", value_type="semantic_role", allowed_values=_metric_values(text), source="signature_defaults|query_id")
    elif use_generic_signature_defaults and signature_id == "numeric.summary_statistic":
        add("statistic", value_type="enum", allowed_values=_statistic_values(text), source="signature_defaults|query_id")
    elif use_generic_signature_defaults and signature_id == "numeric.derived_metric":
        add("operation", value_type="enum", allowed_values=_operation_values(text), source="signature_defaults|query_id")
    elif use_generic_signature_defaults and signature_id == "formula.solve_unknown":
        formula_schema = _formula_schema_from_contract(str(row.get("base_program_contract") or row.get("program_schema") or ""))
        add("unknown_role", value_type="semantic_role", allowed_values=[_unknown_role_value(text)], source="signature_defaults|program_schema")
        if formula_schema:
            add("formula_schema", value_type="enum", allowed_values=[formula_schema], source="program_schema")
        else:
            add("formula_schema", value_type="semantic_role", allowed_values=["task_formula_schema"], source="signature_defaults", notes="Exact formula schema needs manual review.")
    elif use_generic_signature_defaults and signature_id == "constraint.solve_unknown_value":
        add("scene_state", value_type="semantic_role", allowed_values=["visible_constraint_state"], source="signature_defaults")
        add("unknown_role", value_type="semantic_role", allowed_values=["queried_unknown_value"], source="signature_defaults")
        add("rule_schema", value_type="enum", allowed_values=["visible_constraint_rules"], source="signature_defaults")
    elif use_generic_signature_defaults and signature_id == "simulation.discrete_state_update":
        add("discrete_state", value_type="semantic_role", allowed_values=["visible_initial_state"], source="signature_defaults")
        add("visible_rules", value_type="enum", allowed_values=["scene_update_rules"], source="signature_defaults")
        add("final_state_property", value_type="semantic_role", allowed_values=["queried_result_property"], source="signature_defaults|query_id")
    elif use_generic_signature_defaults and signature_id == "optimization.max_reachable_value":
        add("action_sequence", value_type="semantic_role", allowed_values=["visible_or_allowed_actions"], source="signature_defaults")
        add("transition_rule", value_type="enum", allowed_values=["scene_transition_rule"], source="signature_defaults")
        add("objective", value_type="semantic_role", allowed_values=["maximum_reachable_value"], source="signature_defaults|query_id")
    elif use_generic_signature_defaults and signature_id == "numeric.selected_label_value":
        add("items", value_type="semantic_role", allowed_values=["visible_labeled_items_or_groups"], source="signature_defaults")
        add("selection_rule", value_type="semantic_role", allowed_values=["query_selection_rule"], source="signature_defaults|query_id")
        add("label_field", value_type="semantic_role", allowed_values=["integer_visible_label"], source="signature_defaults")
    elif use_generic_signature_defaults and signature_id == "selection.option_value_match":
        add("computed_value", value_type="semantic_role", allowed_values=["computed_scene_value"], source="signature_defaults|query_id")
        add("candidate_options", value_type="semantic_role", allowed_values=["visible_value_options"], source="signature_defaults")
        add("option_label", value_type="semantic_role", allowed_values=["matching_option_letter"], source="signature_defaults")
    elif use_generic_signature_defaults and signature_id == "sequence.longest_run_length":
        add("sequence", value_type="semantic_role", allowed_values=["visible_ordered_sequence"], source="signature_defaults")
        add("rule", value_type="enum", allowed_values=["query_run_rule"], source="signature_defaults|query_id")
    elif use_generic_signature_defaults and signature_id == "path.longest_path_value":
        add("scene_graph", value_type="semantic_role", allowed_values=["visible_state_graph_or_path_options"], source="signature_defaults")
        add("source", value_type="semantic_role", allowed_values=["start_state"], source="signature_defaults")
        add("target", value_type="semantic_role", allowed_values=["terminal_or_stopping_condition"], source="signature_defaults")
    elif use_generic_signature_defaults and signature_id == "count.sequence_or_line_pattern":
        add("board_or_series", value_type="semantic_role", allowed_values=["visible_board_or_sequence"], source="signature_defaults")
        add("rule", value_type="enum", allowed_values=["query_line_or_pattern_rule"], source="signature_defaults|query_id")
    elif use_generic_signature_defaults and signature_id == "count.adjacency_relation":
        add("reference", value_type="semantic_role", allowed_values=["query_reference_item_or_group"], source="signature_defaults|query_id")
        add("relation", value_type="enum", allowed_values=["adjacent_or_neighboring"], source="signature_defaults")
        add("predicate", value_type="object_attribute", allowed_values=["query_neighbor_predicate"], source="signature_defaults|query_id")
    elif use_generic_signature_defaults and signature_id == "count.pairwise_comparison":
        add("left", value_type="semantic_role", allowed_values=["first_visible_series_or_group"], source="signature_defaults|query_id")
        add("right", value_type="semantic_role", allowed_values=["second_visible_series_or_group"], source="signature_defaults|query_id")
        add("item", value_type="semantic_role", allowed_values=["aligned_visible_item"], source="signature_defaults")
        add("metric", value_type="semantic_role", allowed_values=["visible_value_metric"], source="signature_defaults")
    elif use_generic_signature_defaults and signature_id == "counterfactual.transform_then_answer":
        add("scene_state", value_type="semantic_role", allowed_values=["visible_initial_scene_state"], source="signature_defaults")
        add("edit", value_type="semantic_role", allowed_values=["specified_visible_transform"], source="signature_defaults|query_id")
        add("query", value_type="semantic_role", allowed_values=["post_transform_answer_query"], source="signature_defaults|query_id")
    elif use_generic_signature_defaults and signature_id == "selection.option_match":
        add("reference_or_rule", value_type="semantic_role", allowed_values=["reference_or_rule"], source="signature_defaults")
        add("candidate_options", value_type="semantic_role", allowed_values=["visible_candidate_options"], source="signature_defaults")
    elif use_generic_signature_defaults and signature_id == "selection.direct_label":
        add("selection_rule", value_type="semantic_role", allowed_values=["query_selected_visible_support"], source="signature_defaults")
    elif use_generic_signature_defaults and signature_id == "count.direct_cardinality":
        add("query_attribute_or_role", value_type="semantic_role", allowed_values=_target_attribute_values(text), source="signature_defaults|query_id")

    if is_concrete_finalized_domain:
        axes = _refine_finalized_parameter_axes(axes, arguments)

    status = _program_argument_status(arguments, axes)
    if is_concrete_finalized_domain:
        status = "curated"
    return {
        "schema_version": PROGRAM_ARGUMENT_SCHEMA_VERSION,
        "status": status,
        "parameter_axes": axes or ["sampled_scene_values"],
        "arguments": {name: arguments[name] for name in sorted(arguments)},
        "constraints": [],
    }


def _program_argument_override(row: Mapping[str, Any], overrides: Mapping[str, Any]) -> Any:
    keys = [
        str(row.get("proposed_task_id", "")),
        f"{row.get('current_task_id', '')}::{row.get('current_query_id', '')}::{row.get('proposed_task_slug', '')}",
        f"{row.get('current_task_id', '')}::{row.get('current_query_id', '')}",
        str(row.get("current_task_id", "")),
    ]
    for key in keys:
        if key and key in overrides:
            return overrides[key]
    return None


def _normalize_program_argument_payload(payload: Any, *, default_status: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise SystemExit("program argument override payloads must be JSON objects")
    data = dict(payload)
    arguments = data.get("arguments", {})
    if not isinstance(arguments, Mapping):
        raise SystemExit("program argument override 'arguments' must be an object")
    normalized_arguments: dict[str, dict[str, Any]] = {}
    for name, entry in arguments.items():
        if not isinstance(entry, Mapping):
            raise SystemExit(f"program argument override for {name!r} must be an object")
        values = entry.get("allowed_values", [])
        if isinstance(values, str):
            values = [values]
        normalized_arguments[str(name)] = {
            "value_type": str(entry.get("value_type", "semantic_role")),
            "allowed_values": sorted({str(value) for value in values if str(value)}),
            "source": str(entry.get("source", "manual_override")),
            "notes": str(entry.get("notes", "")),
        }
    axes = data.get("parameter_axes", [])
    if isinstance(axes, str):
        axes = split_pipe(axes.replace("|", "|"))
    return {
        "schema_version": str(data.get("schema_version", PROGRAM_ARGUMENT_SCHEMA_VERSION)),
        "status": str(data.get("status", default_status)),
        "parameter_axes": [str(axis) for axis in axes if str(axis)] or ["manual_override"],
        "arguments": normalized_arguments,
        "constraints": list(data.get("constraints", [])) if isinstance(data.get("constraints", []), list) else [],
    }


def _program_argument_status(arguments: Mapping[str, Mapping[str, Any]], axes: list[str]) -> str:
    if not arguments:
        return "needs_review"
    concrete_sources = {
        str(entry.get("source", ""))
        for entry in arguments.values()
        if str(entry.get("source", "")) != "program_schema"
    }
    if concrete_sources:
        return "inferred"
    if axes and axes != ["sampled_scene_values"]:
        return "inferred"
    return "needs_review"


def _refine_finalized_parameter_axes(
    axes: list[str],
    arguments: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Replace draft-only axes with concrete argument names for finalized domains."""

    if axes != ["sampled_scene_values"]:
        return axes
    preferred_names = {
        "axis_aggregate",
        "arc_direction",
        "attribute_axis",
        "attribute_selector",
        "attribute_set",
        "arithmetic_op",
        "boolean_operator",
        "change_direction",
        "change_measure",
        "comparator",
        "delta_mode",
        "destination_filter",
        "direction",
        "drop_result_branch",
        "edge_scope",
        "endpoint_role",
        "extremum_direction",
        "liberty_filter",
        "line_axis",
        "membership_mode",
        "metric",
        "mode",
        "component_axis",
        "direction_mode",
        "edit_sequence",
        "frequency_role",
        "mirror_axis",
        "neighbor_direction",
        "occurrence_rank",
        "phase_relation",
        "region_kind",
        "region_membership",
        "region_mode",
        "relation_mode",
        "target_condition",
        "target_sign",
        "target_attribute",
        "target_direction",
        "target_pair_relation",
        "unknown_slot",
        "move_filter",
        "operation",
        "player",
        "predicate_direction",
        "rank",
        "rank_direction",
        "rank_order",
        "rank_position",
        "range_metric",
        "role",
        "series_order",
        "forced_cell_status",
        "override_result",
        "target_status",
        "target_clear_count",
        "tactic_kind",
    }
    stable_role_names = {
        "board",
        "board_state",
        "candidate_edges",
        "candidate_options",
        "categories",
        "cells",
        "drop_options",
        "hidden_cells",
        "items",
        "line",
        "lines",
        "marked_group",
        "marked_piece",
        "option",
        "piece",
        "pieces",
        "rows",
        "source",
        "target",
        "units",
    }
    refined: list[str] = []
    for name, entry in sorted(arguments.items()):
        values = {str(value) for value in entry.get("allowed_values", [])}
        if name in preferred_names or (len(values) > 1 and name not in stable_role_names):
            refined.append(str(name))
    return refined or ["fixed_query"]


GENERIC_CHART_CONTRACT_SNIPPETS = (
    "label(arg_extreme(items, metric, direction))",
    "select_by_rank(items, metric, rank)",
    "count(filter(units, compare(metric(unit), threshold, direction)))",
    "count(filter(units, lower <= metric(unit) <= upper))",
    "sum(values(selected_support))",
    "select_label(selected_visible_support, query_parameters)",
    "compute_value(selected_support, query_parameters)",
    "predicate(region)",
    "visible_primitives, scope",
)


def _is_concrete_chart_contract(program_schema: str) -> bool:
    text = str(program_schema or "")
    return bool(text.strip()) and not any(snippet in text for snippet in GENERIC_CHART_CONTRACT_SNIPPETS)


GENERIC_GAME_CONTRACT_SNIPPETS = (
    "count(filter(units, predicate(unit, query_parameters)))",
    "count(filter(units, predicate_set(unit, query_parameters)))",
    "label(arg_extreme(items, metric, direction))",
    "sum(values(selected_support))",
    "select_label(selected_visible_support, query_parameters)",
    "compute_value(selected_support, query_parameters)",
    "direct_answer(",
)


def _is_concrete_game_contract(program_schema: str) -> bool:
    text = str(program_schema or "")
    return bool(text.strip()) and not any(snippet in text for snippet in GENERIC_GAME_CONTRACT_SNIPPETS)


GENERIC_GEOMETRY_CONTRACT_SNIPPETS = (
    "solve_formula(scene_measurements, unknown_role, formula_schema)",
    "solve_formula(scene_measurements,",
    "derive_metric(values(selected_support), operation)",
    "sum(values(selected_support))",
    "select_label(selected_visible_support, query_parameters)",
    "select_option(reference_or_rule, candidate_options)",
    "count(filter(units, query_attribute_or_role))",
    "label(arg_extreme(items, metric, direction))",
)


def _is_concrete_geometry_contract(program_schema: str) -> bool:
    text = str(program_schema or "")
    return bool(text.strip()) and not any(snippet in text for snippet in GENERIC_GEOMETRY_CONTRACT_SNIPPETS)


GENERIC_PHYSICS_CONTRACT_SNIPPETS = (
    "apply_physics_direction_rule(diagram, queried_location_or_process)",
    "apply_wave_interference_rule(diagram, candidate_points)",
    "solve_formula(scene_measurements, unknown_role, formula_schema)",
    "solve_formula(scene_measurements,",
    "sum(values(selected_support))",
    "count(filter(units, query_attribute_or_role))",
    "lookup_label(role_bound_visible_record, requested_field_or_target)",
)


def _is_concrete_physics_contract(program_schema: str) -> bool:
    text = str(program_schema or "")
    return bool(text.strip()) and not any(snippet in text for snippet in GENERIC_PHYSICS_CONTRACT_SNIPPETS)


GENERIC_GRAPH_CONTRACT_SNIPPETS = (
    "count(filter(units, query_attribute_or_role))",
    "connected_components(graph, edit_or_scope).select(component_property)",
    "reachable_set(topology, start, constraints)",
    "select_label(selected_visible_support, query_parameters)",
    "select_option(reference_or_rule, candidate_options)",
    "shortest_path(scene_graph, source, target)",
    "traverse(graph, start, traversal_rule)",
)


def _is_concrete_graph_contract(program_schema: str) -> bool:
    text = str(program_schema or "")
    return bool(text.strip()) and not any(snippet in text for snippet in GENERIC_GRAPH_CONTRACT_SNIPPETS)


GENERIC_ICON_CONTRACT_SNIPPETS = (
    "count(filter(units, query_attribute_or_role))",
    "count(filter(units, predicate_set(unit, query_parameters)))",
    "count(filter(units, adjacent(reference, unit) and predicate(unit)))",
    "select_by_rank(items, metric, rank)",
    "select_label(selected_visible_support, query_parameters)",
    "select_option(reference_or_rule, candidate_options)",
    "compute_value(selected_support, query_parameters)",
    "answer(transform(scene_state, edit), query)",
)


def _is_concrete_icon_contract(program_schema: str) -> bool:
    text = str(program_schema or "")
    return bool(text.strip()) and not any(snippet in text for snippet in GENERIC_ICON_CONTRACT_SNIPPETS)


GENERIC_ILLUSTRATION_CONTRACT_SNIPPETS = (
    "count(filter(units, query_attribute_or_role))",
    "select_label(selected_visible_support, query_parameters)",
    "select_option(reference_or_rule, candidate_options)",
    "direct_answer(",
)


def _is_concrete_illustration_contract(program_schema: str) -> bool:
    text = str(program_schema or "")
    return bool(text.strip()) and not any(snippet in text for snippet in GENERIC_ILLUSTRATION_CONTRACT_SNIPPETS)


GENERIC_PAGES_CONTRACT_SNIPPETS = (
    "count(filter(units, query_attribute_or_role))",
    "select_label(selected_visible_support, query_parameters)",
    "select_option(reference_or_rule, candidate_options)",
    "lookup_label(role_bound_visible_record, requested_field_or_target)",
    "sum(values(selected_support))",
    "compute_value(selected_support, query_parameters)",
    "derive_metric(values(selected_support), operation)",
    "difference(value(source_a), value(source_b), mode)",
    "direct_answer(",
)


def _is_concrete_pages_contract(program_schema: str) -> bool:
    text = str(program_schema or "")
    return bool(text.strip()) and not any(snippet in text for snippet in GENERIC_PAGES_CONTRACT_SNIPPETS)


GENERIC_THREE_D_CONTRACT_SNIPPETS = (
    "count(filter(units, query_attribute_or_role))",
    "count(filter(candidate_objects, predicate_set(unit, query_parameters)))",
    "count(filter(candidate_objects, boolean_attribute_expression(object_type, color, operator)))",
    "count(filter(candidate_objects, compare(metric(object), metric(reference_object), relation_direction)))",
    "select_label(selected_visible_support, query_parameters)",
    "label(arg_extreme(items, metric, direction))",
    "label(arg_min_distance(reference, candidates, distance_metric))",
    "label(arg_min_distance(reference_entity, candidate_objects, distance_metric))",
    "select_option(reference_or_rule, candidate_options)",
    "answer(transform(scene_state, edit), query)",
)


def _is_concrete_three_d_contract(program_schema: str) -> bool:
    text = str(program_schema or "")
    return bool(text.strip()) and not any(snippet in text for snippet in GENERIC_THREE_D_CONTRACT_SNIPPETS)


GENERIC_PUZZLE_CONTRACT_SNIPPETS = (
    "simulate(discrete_state, visible_rules, steps).select(final_state_property)",
    "apply_time_offset(clock_readout, offset, direction)",
    "derive_metric(values(selected_support), operation)",
    "count(filter(units, query_attribute_or_role))",
    "connected_components(graph, edit_or_scope).select(component_property)",
    "distance(path_or_grid, source, target, metric)",
    "shortest_path(scene_graph, source, target)",
    "reachable_set(topology, start, constraints)",
    "select_label(selected_visible_support, query_parameters)",
    "select_option(reference_or_rule, candidate_options)",
    "probability(event, visible_sample_space)",
    "direct_answer(",
)


def _is_concrete_puzzle_contract(program_schema: str) -> bool:
    text = str(program_schema or "")
    return bool(text.strip()) and not any(snippet in text for snippet in GENERIC_PUZZLE_CONTRACT_SNIPPETS)


GENERIC_FINALIZED_ARGUMENT_VALUES = {
    "query_attribute_or_role",
    "query_change_kind",
    "query_parameters",
    "query_selected_visible_support",
    "query_selection_rule",
    "ranked_position",
    "sampled_rank_position",
    "sampled_scene_values",
}

GENERIC_FINALIZED_PARAMETER_AXES = {
    "manual_override",
    "sampled_scene_values",
}


def _is_generic_finalized_argument_value(value: Any) -> bool:
    text = str(value or "")
    return text in GENERIC_FINALIZED_ARGUMENT_VALUES or text.startswith("query_")


def _illustration_placeholder_allowed_values(name: str, *, scene_id: str, slug: str, query_id: str) -> list[str]:
    text = f"{scene_id} {slug} {query_id}".lower()
    values_by_name = {
        "after_panel": ["after_panel"],
        "anchor_position": ["left_anchor" if "1x3" in text else "top_left_anchor" if "2x2" in text else "sampled_anchor_position"],
        "before_panel": ["before_panel"],
        "boarding_area": ["visible_boarding_area"],
        "book": ["book_instance"],
        "book_attribute": ["color" if "color" in text else "orientation" if ("upright" in text or "horizontal" in text) else "sampled_book_attribute"],
        "books": ["visible_books"],
        "building_windows": ["visible_building_windows"],
        "candidate_patch": ["candidate_patch_option"],
        "candidate_patches": ["visible_patch_options"],
        "completed_image_layout": ["completed_illustration_layout"],
        "construction_vehicles": ["visible_construction_vehicles"],
        "edit_count": ["sampled_edit_count"],
        "edit_operation": ["add_objects" if "added" in text else "remove_objects" if "removed" in text else "sampled_add_or_remove"],
        "environment_features": ["visible_environment_features"],
        "equipment": ["playground_equipment_instance"],
        "feature": ["environment_feature_instance"],
        "furniture_items": ["visible_furniture_items"],
        "grid_tiles": ["visible_labeled_grid_tiles"],
        "item": ["furniture_item"],
        "luggage": ["luggage_item"],
        "luggage_items": ["visible_luggage_items"],
        "named_objects": ["visible_named_objects"],
        "object": ["scene_object"],
        "objects": ["visible_room_objects"],
        "part_type": _illustration_part_type_values(text),
        "people": ["visible_people"],
        "person": ["person_instance"],
        "piece_options": ["visible_labeled_piece_options"],
        "playground_equipment": ["visible_playground_equipment"],
        "reference_object": ["prompt_named_reference_object"],
        "room_objects": ["visible_room_objects"],
        "room_reference": ["room_side_reference"],
        "scene_objects": ["visible_scene_objects"],
        "source_image_with_hole": ["source_image_with_missing_region"],
        "target_activity": _illustration_activity_values(text),
        "target_area": _illustration_area_values(text),
        "target_attribute": _illustration_worker_attribute_values(text),
        "target_attribute_value": _illustration_attribute_value_values(text),
        "target_equipment": _illustration_equipment_values(text),
        "target_feature": ["visible_feature_named_in_prompt"],
        "target_linear_feature": ["visible_linear_feature"],
        "target_object": _illustration_target_object_values(text),
        "target_object_type": ["sampled_object_type"],
        "target_rotation": _illustration_rotation_values(text),
        "target_section": ["sampled_library_section"],
        "target_side": _illustration_side_values(text),
        "target_surface": ["sampled_surface"],
        "target_zone": _illustration_zone_values(text),
        "tile": ["grid_tile"],
        "transform_mode": _illustration_patch_mode_values(text),
        "vehicle": ["construction_vehicle_instance"],
        "window": ["window_instance"],
        "worker": ["worker_instance"],
        "workers": ["visible_workers"],
    }
    if name in values_by_name:
        return list(values_by_name[name])
    return [_default_placeholder_value(name)]


def _illustration_zone_values(text: str) -> list[str]:
    if "excavation" in text:
        return ["excavation_zone"]
    if "loading" in text:
        return ["loading_zone"]
    if "roadwork" in text:
        return ["roadwork_zone"]
    return ["sampled_construction_zone"]


def _illustration_worker_attribute_values(text: str) -> list[str]:
    if "hard_hat" in text:
        return ["hard_hat_color"]
    if "tool" in text:
        return ["held_tool"]
    if "vest" in text:
        return ["vest_color"]
    return ["sampled_worker_attribute"]


def _illustration_attribute_value_values(text: str) -> list[str]:
    if "hard_hat" in text or "vest" in text or "color" in text:
        return ["sampled_color"]
    if "tool" in text:
        return ["sampled_tool_type"]
    if "upright" in text:
        return ["upright"]
    if "horizontal" in text:
        return ["horizontal"]
    return ["sampled_attribute_value"]


def _illustration_side_values(text: str) -> list[str]:
    if "left" in text:
        return ["left"]
    if "right" in text:
        return ["right"]
    if "above" in text:
        return ["above"]
    if "below" in text:
        return ["below"]
    return ["sampled_side"]


def _illustration_patch_mode_values(text: str) -> list[str]:
    if "irregular" in text:
        return ["irregular_cutout"]
    if "transformed" in text:
        return ["transformed_patch"]
    if "plain" in text:
        return ["plain_patch"]
    return ["sampled_patch_mode"]


def _illustration_rotation_values(text: str) -> list[str]:
    if "90" in text:
        return ["90_degrees"]
    if "180" in text:
        return ["180_degrees"]
    if "270" in text:
        return ["270_degrees"]
    return ["sampled_rotation_degrees"]


def _illustration_activity_values(text: str) -> list[str]:
    if "sitting" in text:
        return ["sitting"]
    if "walking" in text:
        return ["walking"]
    if "standing" in text:
        return ["standing"]
    if "playing_ball" in text:
        return ["playing_ball"]
    return ["sampled_activity"]


def _illustration_area_values(text: str) -> list[str]:
    if "garden" in text:
        return ["garden_area"]
    if "picnic" in text:
        return ["picnic_area"]
    if "playground_area" in text:
        return ["playground_area"]
    return ["sampled_area"]


def _illustration_equipment_values(text: str) -> list[str]:
    if "swing_set" in text:
        return ["swing_set"]
    if "seesaw" in text:
        return ["seesaw"]
    if "slide" in text:
        return ["slide"]
    if "climbing_frame" in text:
        return ["climbing_frame"]
    return ["sampled_equipment_type"]


def _illustration_part_type_values(text: str) -> list[str]:
    if "wing" in text:
        return ["wing"]
    if "leg" in text:
        return ["leg"]
    if "wheel" in text:
        return ["wheel"]
    if "leaf" in text:
        return ["leaf"]
    if "tine" in text:
        return ["tine"]
    if "finger" in text:
        return ["finger"]
    if "arm" in text:
        return ["arm"]
    if "point" in text:
        return ["point"]
    if "lens" in text:
        return ["lens"]
    return ["sampled_part_type"]


def _illustration_target_object_values(text: str) -> list[str]:
    for object_name in (
        "airplane",
        "bicycle",
        "bird",
        "butterfly",
        "chair",
        "clover",
        "fork",
        "glove",
        "quadruped",
        "snowflake",
        "star",
        "traffic_light",
    ):
        if object_name in text:
            return [object_name]
    return ["sampled_target_object"]


def _pages_placeholder_allowed_values(name: str, *, scene_id: str, slug: str, query_id: str) -> list[str]:
    text = f"{scene_id} {slug} {query_id}".lower()
    values_by_name = {
        "action_cue": ["visible_action_cue"],
        "action_guide": ["visible_action_guide"],
        "addend_operand_boxes": ["visible_addend_amount_boxes"],
        "arithmetic_op": ["sampled_arithmetic_operation"],
        "calendar_cells": ["visible_calendar_cells"],
        "card": ["metric_card"],
        "child": ["concept_child_node"],
        "command_matrix": ["visible_command_matrix"],
        "comparison_icon_kind": ["sampled_comparison_icon_kind"],
        "context_cue": ["visible_context_cue"],
        "control": ["page_control"],
        "control_family": _pages_control_family_values(text),
        "control_group": ["sampled_control_group"],
        "direction": _pages_direction_values(text),
        "direction_mode": ["outgoing" if "outgoing" in text else "involved" if "involved" in text else "sampled_handoff_direction_mode"],
        "direction_sequence": ["visible_direction_sequence"],
        "event": ["timeline_or_schedule_event"],
        "field_name": ["sampled_field_name"],
        "field_value": ["visible_profile_field_value"],
        "first_operand": ["first_visible_operand_value"],
        "group_name": ["visible_group_name"],
        "instruction_cue": ["visible_instruction_cue"],
        "list_order": ["visible_rank_order"],
        "membership_mode": ["outside" if "outside" in text else "between" if "between" in text else "sampled_interval_membership"],
        "menu_path": ["visible_menu_path"],
        "menu_tree": ["visible_menu_tree"],
        "metric_card": ["metric_card"],
        "metric_cards": ["visible_metric_cards"],
        "metric_cards_by_section": ["visible_metric_cards_grouped_by_section"],
        "metric_cards_in_section": ["visible_metric_cards_in_target_section"],
        "metric_cards_in_section_a": ["visible_metric_cards_in_first_section"],
        "metric_cards_in_section_b": ["visible_metric_cards_in_second_section"],
        "mismatched_rows": ["visible_mismatched_row_pairs"],
        "month_grid": ["visible_month_grid"],
        "named_item": ["prompt_named_metric_item"],
        "named_metric_cards": ["prompt_named_metric_cards"],
        "named_profile": ["prompt_named_profile"],
        "object_guide": ["visible_object_guide"],
        "object_row": ["visible_object_row"],
        "operand_value_boxes": ["visible_operand_value_boxes"],
        "ordinal": ["sampled_weekday_occurrence_ordinal"],
        "parent_branch": ["prompt_named_parent_branch"],
        "parent_node": ["prompt_named_hierarchy_node"],
        "profile": ["profile_card"],
        "profile_cards": ["visible_profile_cards"],
        "purchase_row": ["purchase_form_row"],
        "purchase_rows": ["visible_purchase_rows"],
        "rank": _pages_rank_values(text),
        "ranked_entries": ["visible_ranked_entries"],
        "ranked_list": ["visible_ranked_list"],
        "receiving_row": ["receiving_form_row"],
        "receiving_rows": ["visible_receiving_rows"],
        "reference_event": ["prompt_named_reference_event"],
        "reference_event_a": ["first_reference_event"],
        "reference_event_b": ["second_reference_event"],
        "requested_field": _pages_requested_field_values(text),
        "ribbon_groups": ["visible_ribbon_groups"],
        "route_steps": ["visible_route_steps"],
        "row": ["table_row"],
        "row_pair": ["matched_form_row_pair"],
        "schedule_events": ["visible_schedule_events"],
        "schema_fields": ["visible_schema_fields"],
        "schema_relationship_edges": ["visible_schema_relationship_edges"],
        "second_operand": ["second_visible_operand_value"],
        "section_a_metric_cards": ["metric_cards_in_first_extreme_section"],
        "section_b_metric_cards": ["metric_cards_in_second_extreme_section"],
        "sections": ["visible_infographic_sections"],
        "shortfall_rows": ["visible_shortfall_rows"],
        "sidebar_tree": ["visible_sidebar_tree"],
        "sibling_order": ["visible_sibling_order"],
        "stage_ring": ["visible_cycle_stage_ring"],
        "start_landmark": ["visible_start_landmark"],
        "start_stage": ["visible_start_stage"],
        "static_map": ["visible_static_map"],
        "status": ["visible_status"],
        "step_list": ["visible_step_list"],
        "step_order": ["visible_step_order"],
        "steps": ["visible_steps"],
        "subtrahend_operand": ["visible_subtrahend_amount_box"],
        "table_rows": ["visible_table_rows"],
        "target_action": _pages_target_action_values(text),
        "target_day_class": ["weekend" if "weekend" in text else "weekday" if "weekday" in text else "sampled_day_class"],
        "target_field_value": ["sampled_field_value"],
        "target_group": ["sampled_table_group"],
        "target_icon_type": ["sampled_icon_type"],
        "target_lane": ["sampled_process_lane"],
        "target_role": ["sampled_role"],
        "target_shape": ["sampled_shape"],
        "target_status": ["sampled_status"],
        "target_type": ["sampled_row_type"],
        "target_value": ["sampled_target_value"],
        "threshold": ["sampled_threshold"],
        "tree_path": ["visible_tree_path"],
        "value": ["visible_value"],
        "web_page": ["visible_web_page"],
        "weekday": ["sampled_weekday"],
        "workspace_surface": ["visible_workspace_surface"],
    }
    if name in values_by_name:
        return list(values_by_name[name])
    return [f"pages_{name}"]


def _pages_direction_values(text: str) -> list[str]:
    if "before" in text:
        return ["before"]
    if "after" in text:
        return ["after"]
    if "longer" in text or "threshold" in text:
        return _predicate_direction_values(text)
    if "highest" in text or "extrema" in text or "ranked" in text:
        return ["highest", "lowest"]
    return ["sampled_direction"]


def _pages_rank_values(text: str) -> list[str]:
    if "from_end" in text:
        return ["last", "second_from_last", "third_from_last"]
    if "section_ranked" in text or "ranked_total" in text:
        return ["highest_total", "second_highest_total", "lowest_total"]
    if "nth" in text or "ordinal" in text:
        return ["first", "second", "third", "sampled_ordinal_position"]
    return ["sampled_page_rank"]


def _pages_requested_field_values(text: str) -> list[str]:
    if "detail" in text:
        return ["detail_text"]
    if "title" in text:
        return ["step_title"]
    if "profile_for" in text or "profile_name" in text:
        return ["profile_name"]
    if "value_for" in text or "field_value" in text or "named_item" in text:
        return ["value_text"]
    if "entry_after" in text:
        return ["entry_after_named_entry"]
    if "step_after" in text:
        return ["step_after_named_step"]
    return ["sampled_requested_field"]


def _pages_target_action_values(text: str) -> list[str]:
    if "click" in text:
        return ["click"]
    if "select_option" in text:
        return ["select_option"]
    if "type_field" in text:
        return ["type_text"]
    return ["sampled_target_action"]


def _pages_control_family_values(text: str) -> list[str]:
    if "toolbar_palette" in text:
        return ["toolbar_palette"]
    if "property_panel" in text:
        return ["property_panel"]
    if "canvas_workspace" in text:
        return ["canvas_workspace"]
    if "code_workspace" in text:
        return ["code_workspace"]
    if "file_dialog" in text:
        return ["file_dialog"]
    return ["sampled_control_family"]


def _icon_placeholder_allowed_values(name: str, *, scene_id: str, slug: str, query_id: str) -> list[str]:
    text = f"{scene_id} {slug} {query_id}".lower()
    values_by_name = {
        "anchor_a": ["visible_anchor_a"],
        "anchor_b": ["visible_anchor_b"],
        "anchor_icon": ["visible_anchor_icon"],
        "arc_direction": ["clockwise" if "clockwise" in text and "counter" not in text else "counterclockwise" if "counterclockwise" in text else "sampled_arc_direction"],
        "arithmetic_progression": ["visible_count_sequence_progression"],
        "attribute_axis": ["color" if "color" in text else "size" if "size" in text else "rotation" if "rotation" in text else "sampled_attribute_axis"],
        "attribute_progression_rule": ["color_ladder" if "color" in text else "size_ladder" if "size" in text else "sampled_attribute_progression_rule"],
        "attribute_selector": ["color_and_shape" if "color_shape" in text else "fill_and_shape" if "fill_shape" in text else "shape"],
        "attribute_set": ["type_color_rotation" if "type_color_rotation" in text else "color" if "match_color" in text else "rotation" if "rotation" in text else "type"],
        "boolean_operator": [
            "and_not" if "and_not" in text else
            "exactly_one" if "exactly_one" in text else
            "neither" if "neither" in text else
            "or" if "_or_" in text else
            "and"
        ],
        "candidate_full_icons": ["visible_full_icon_options"],
        "candidate_icons": ["visible_candidate_icons"],
        "center": ["icon_center_point"],
        "cells": ["visible_grid_cells"],
        "comparator": [
            "at_least" if "at_least" in text else
            "exactly" if "exactly" in text else
            "equals_zero" if "_no_" in text or "no_shape" in text else
            "sampled_comparator"
        ],
        "count_sequence": ["visible_count_sequence"],
        "direction": _icon_direction_values(text),
        "distance": ["euclidean_distance"],
        "edit_sequence": [
            "remove_and_replace_shape" if "remove_and_replace" in text else
            "replace_shape" if "replacement" in text else
            "remove_shape"
        ],
        "frequency": ["type_frequency"],
        "frequency_role": ["most_frequent_type" if "most_frequent" in text else "singleton_type"],
        "grid_cells": ["visible_numbered_grid_cells"],
        "icon": ["icon_instance"],
        "icon_instances": ["visible_icon_instances"],
        "icon_sequence": ["visible_icon_sequence"],
        "left_panel": ["left_panel_icons"],
        "line_axis": ["column" if "column" in text else "row" if "row" in text else "sampled_line_axis"],
        "line_index": ["sampled_line_number"],
        "lines": ["visible_rows_or_columns"],
        "marker_a": ["arc_start_marker_a"],
        "marker_b": ["arc_end_marker_b"],
        "mirror_axis": _icon_mirror_axis_values(text),
        "neighbor_direction": ["after" if "after" in text else "before" if "before" in text else "sampled_neighbor_direction"],
        "occurrence_rank": [
            "second" if "second" in text else
            "last" if "last" in text else
            "first"
        ],
        "operand_selector_a": ["left_count_selector"],
        "operand_selector_b": ["right_count_selector"],
        "original_icon": ["visible_original_icon"],
        "other_reference": ["other_prompt_named_reference"],
        "pair_cell": ["visible_pair_cell"],
        "pair_cells": ["visible_pair_grid_cells"],
        "panel_icons": ["icons_from_left_or_right_panel_by_relation_mode"],
        "partial_fragment": ["visible_partial_icon_fragment"],
        "queried_reference": ["reference_a" if "_a_" in text else "reference_b" if "_b_" in text else "sampled_reference"],
        "rank_order": [
            "second_closest" if "second_closest" in text else
            "farthest" if "farthest" in text else
            "closest"
        ],
        "reference_cell": ["visible_reference_cell"],
        "reference_icon": ["visible_reference_icon"],
        "reference_order": ["visible_reference_front_to_back_order"],
        "reference_pair": ["visible_reference_pair"],
        "reference_transform_relation": ["same_transform_as_reference_pair"],
        "region_membership": ["outside" if "outside" in text else "inside"],
        "region_mode": _icon_venn_region_values(text),
        "relation_mode": _icon_relation_mode_values(text),
        "right_icon": ["tracked_right_panel_icon"],
        "right_panel": ["right_panel_icons"],
        "right_panel_candidates": ["visible_right_panel_options"],
        "rotation_progression_rule": ["visible_rotation_progression_rule"],
        "scene_cells": ["visible_scene_cells"],
        "scene_icons": ["visible_scene_icons"],
        "sequence_cells": ["visible_sequence_cells"],
        "set_relation": ["panel_set_relation"],
        "shape": ["icon_shape"],
        "strip_axis": ["horizontal" if "horizontal" in text else "vertical" if "vertical" in text else "sampled_strip_axis"],
        "target_attribute": _icon_target_attribute_values(text),
        "target_attribute_value": ["sampled_target_attribute_value"],
        "target_direction": _icon_movement_direction_values(text),
        "target_pair_relation": _icon_pair_relation_values(text),
        "target_delta_predicate": _icon_pair_relation_values(text),
        "transform_relation": _icon_pair_relation_values(text),
        "target_shape": ["sampled_target_shape"],
        "threshold": ["sampled_line_threshold"],
        "tracked_right_icons": ["right_panel_icons_with_tracked_left_match"],
        "visible_region": _icon_region_kind_values(text),
    }
    if name in values_by_name:
        return list(values_by_name[name])
    return [_default_placeholder_value(name)]


def _icon_direction_values(text: str) -> list[str]:
    if "below" in text:
        return ["below"]
    if "above" in text:
        return ["above"]
    if "left" in text:
        return ["left"]
    if "right" in text:
        return ["right"]
    if "larger" in text:
        return ["larger_than_reference"]
    if "smaller" in text:
        return ["smaller_than_reference"]
    if "longest" in text or "most" in text:
        return ["highest"]
    if "shortest" in text or "fewest" in text:
        return ["lowest"]
    return ["sampled_direction"]


def _icon_mirror_axis_values(text: str) -> list[str]:
    if "both_axes" in text:
        return ["horizontal_and_vertical"]
    if "diagonal_anti" in text:
        return ["anti_diagonal"]
    if "diagonal_main" in text:
        return ["main_diagonal"]
    if "horizontal" in text:
        return ["horizontal"]
    if "vertical" in text:
        return ["vertical"]
    return ["sampled_mirror_axis"]


def _icon_movement_direction_values(text: str) -> list[str]:
    if "moved_down" in text:
        return ["down"]
    if "moved_up" in text:
        return ["up"]
    if "moved_left" in text:
        return ["left"]
    if "moved_right" in text:
        return ["right"]
    return ["sampled_movement_direction"]


def _icon_pair_relation_values(text: str) -> list[str]:
    if "same_pair_transform" in text:
        return ["same_transform_as_reference_pair"]
    if "color_and_size" in text:
        return ["color_and_size_change"]
    if "color_only" in text:
        return ["color_only_change"]
    if "size_only" in text:
        return ["size_only_change"]
    return ["sampled_pair_relation"]


def _icon_region_kind_values(text: str) -> list[str]:
    if "band" in text:
        return ["visible_band_region"]
    if "quadrant" in text:
        return ["visible_quadrant_region"]
    if "shelf" in text:
        return ["visible_shelf_region"]
    if "venn" in text:
        return ["visible_venn_region"]
    return ["visible_closed_shape_region"]


def _icon_relation_mode_values(text: str) -> list[str]:
    if "added_in_right" in text:
        return ["right_only_added"]
    if "missing_from_right" in text:
        return ["left_only_missing"]
    if "right_exact_match" in text:
        return ["right_exact_match"]
    return _icon_pair_relation_values(text)


def _icon_target_attribute_values(text: str) -> list[str]:
    values: list[str] = []
    if "shape" in text or "type" in text:
        values.append("shape")
    if "color" in text:
        values.append("color")
    if "fill" in text:
        values.append("fill_style")
    if "rotation" in text:
        values.append("rotation")
    if "size" in text:
        values.append("size")
    return values or ["sampled_icon_attribute"]


def _icon_venn_region_values(text: str) -> list[str]:
    if "outside_both" in text:
        return ["outside_both"]
    if "both_circles" in text:
        return ["inside_both"]
    if "either_circle" in text:
        return ["inside_either"]
    if "exactly_one" in text:
        return ["inside_exactly_one"]
    return ["sampled_venn_region"]


def _game_placeholder_allowed_values(name: str, *, scene_id: str, slug: str, query_id: str) -> list[str]:
    text = f"{scene_id} {slug} {query_id}".lower()
    values_by_name = {
        "slide_merge_2048": ["slide_merge_2048"],
        "board_state": ["visible_board_state"],
        "board": ["visible_board"],
        "dice_rolls": ["visible_dice_rolls"],
        "current_player": ["current_player"],
        "marked_piece": ["marked_piece"],
        "marked_group": ["marked_group"],
        "marked_shot": ["marked_shot"],
        "reference_card": ["reference_card"],
        "reference_tile": ["reference_tile"],
        "lead_suit": ["visible_lead_suit"],
        "trump_suit": ["visible_trump_suit"],
        "target_sum": ["sampled_target_sum"],
        "target_ring": ["sampled_target_ring"],
        "threshold": ["sampled_threshold"],
        "target_lane": ["sampled_lane"],
        "target_color": ["sampled_color"],
        "target_ore_type": ["sampled_ore_type"],
        "target_pocket": ["target_pocket"],
        "cue_ball": ["cue_ball"],
        "current_player_group": ["current_player_group"],
        "selected_unit": ["sampled_row_column_or_box"],
        "target_king": ["target_king"],
        "opponent_pieces": ["opponent_pieces"],
        "king": ["marked_king"],
        "marked_king": ["marked_king"],
        "beat_window": ["visible_hit_window"],
        "horizon_roll_count": ["visible_roll_horizon"],
        "die_value": ["sampled_die_value"],
        "jumps": ["visible_snake_ladder_jumps"],
        "start_square": ["visible_start_square"],
        "path_option": ["visible_path_option"],
        "snake_state": ["visible_snake_state"],
        "next_piece": ["visible_next_piece"],
        "piece": ["visible_current_piece"],
        "option": ["visible_option"],
        "rank": ["card_rank"],
        "card": ["card"],
        "tile": ["domino_tile"],
        "edge": ["candidate_edge"],
        "cell": ["candidate_cell"],
        "line": ["candidate_line"],
        "piece_kind": ["sampled_piece_kind"],
        "piece_color": ["sampled_piece_color"],
        "block_type": ["sampled_block_type"],
        "resource_cost": ["resource_cost"],
        "axis_scope": ["sampled_axis_scope"],
        "query_direction": _direction_values(text, default=("highest", "lowest")),
        "direction": _direction_values(text, default=("highest", "lowest")),
    }
    if name in values_by_name:
        return list(values_by_name[name])
    if name == "move_direction":
        return ["sampled_move_direction"]
    if name == "move_filter":
        if "hit_move" in text:
            return ["hits_opponent_blot"]
        if "capture_move" in text:
            return ["capture"]
        if "legal_move" in text or slug == "move_count":
            return ["any_legal"]
        return ["sampled_move_filter"]
    if name == "destination_filter":
        if "capture" in text:
            return ["occupied_by_opponent"]
        if "corner" in text:
            return ["corner"]
        if "legal" in text or "move" in text:
            return ["any_legal_destination"]
        return ["sampled_destination_filter"]
    if name == "edge_scope":
        return ["highlighted_candidate_edges"] if "highlighted" in text else ["all_candidate_edges"]
    if name == "liberty_filter":
        return ["touches_enemy_group"] if "shared" in text else ["all_liberties"]
    if name == "tactic_kind":
        if "blocking" in text:
            return ["block_opponent_win"]
        if "winning" in text:
            return ["win_local_board"]
        return ["sampled_line_completion_tactic"]
    if name == "player":
        if query_id.startswith("x_"):
            return ["x"]
        if query_id.startswith("o_"):
            return ["o"]
        return ["current_player"]
    if name in {"query_status", "target_status", "forced_cell_status"}:
        if "sunk" in text:
            return ["sunk"]
        if "partial" in text:
            return ["partially_hit"]
        if "forced_mine" in text:
            return ["forced_mine"]
        if "forced_safe" in text:
            return ["forced_safe"]
        if "x_won" in text:
            return ["x_won"]
        if "o_won" in text:
            return ["o_won"]
        if "drawn" in text:
            return ["drawn"]
        if "neither" in text:
            return ["neither_won"]
        return ["sampled_status"]
    if name in {"query_result", "override_result"}:
        if "loss" in text:
            return ["loss"]
        if "win" in text:
            return ["win"]
        return ["sampled_result"]
    return [_default_placeholder_value(name)]


def _three_d_placeholder_allowed_values(name: str, *, scene_id: str, slug: str, query_id: str) -> list[str]:
    text = f"{scene_id} {slug} {query_id}".lower()
    values_by_name = {
        "attribute_a": ["object_type" if "object_type" in text else "color"],
        "attribute_b": ["color" if "object_type" in text else "object_type"],
        "candidate_object": ["candidate_3d_object"],
        "candidate_objects": ["visible_answer_candidate_objects"],
        "camera_distance": ["camera_space_depth_distance"],
        "camera_position": ["rendered_camera_position"],
        "cluster_objects": ["visible_cluster_objects"],
        "color": ["prompt_color_name"],
        "depth_relation_direction": _three_d_depth_relation_values(text),
        "edit_sequence": ["textual_add_remove_object_edits"],
        "excluded_attribute": ["color" if "not_color" in text else "object_type" if "not_object_type" in text else "sampled_excluded_attribute"],
        "excluded_attribute_values": ["excluded_prompt_color" if "not_color" in text else "excluded_prompt_object_type" if "not_object_type" in text else "sampled_excluded_attribute_values"],
        "floor_gap_distance": ["floor_plane_surface_gap"],
        "floor_plane_distance": ["floor_plane_center_distance"],
        "forward_distance": ["positive_forward_path_distance"],
        "ground_plane_distance": ["ground_plane_center_distance"],
        "included_attribute": ["object_type" if "object_type" in text else "color"],
        "included_attribute_values": ["included_prompt_object_type" if "object_type" in text else "included_prompt_color"],
        "initial_objects": ["visible_initial_3d_objects"],
        "intersection_center": ["visible_intersection_center_metadata"],
        "landmark_id": ["stable_landmark_id"],
        "lateral_relation_direction": _three_d_lateral_relation_values(text),
        "marked_point": ["candidate_marked_point"],
        "marked_points": ["visible_marked_points"],
        "mounting": ["wall_mounted"],
        "object_type": ["prompt_object_type"],
        "rack_color": ["visible_rack_color"],
        "reference_a": ["first_named_reference_object"],
        "reference_b": ["second_named_reference_object"],
        "reference_object": ["prompt_named_reference_object"],
        "reference_prop": ["prompt_named_reference_prop"],
        "reference_robot": ["red_boxed_reference_robot"],
        "reference_vehicle": ["red_boxed_reference_vehicle"],
        "right_view_candidate_points": ["right_view_labeled_candidate_points"],
        "right_view_objects": ["right_view_labeled_candidate_objects"],
        "robot_candidates": ["visible_candidate_robots"],
        "room_objects": ["visible_room_objects"],
        "shelf_items": ["visible_shelf_items"],
        "shelf_level": ["visible_shelf_level"],
        "source_landmark_id": ["left_view_marked_source_landmark_id"],
        "source_object_id": ["left_view_boxed_source_object_id"],
        "street_object_candidates": ["visible_street_object_candidates"],
        "target_attribute_values_a": ["target_prompt_object_types" if "object_type" in text else "target_prompt_colors"],
        "target_attribute_values_b": ["target_prompt_colors" if "object_type" in text else "target_prompt_object_types"],
        "target_colors": ["target_prompt_colors"],
        "target_object_type": _three_d_target_object_type_values(text),
        "target_object_types": _three_d_target_object_type_values(text),
        "target_rack_color": ["sampled_visible_rack_color"],
        "target_selector": ["object_type_selector", "color_selector", "color_and_object_type_selector"],
        "target_shelf_level": _three_d_shelf_level_values(text),
        "warehouse_object_candidates": ["visible_warehouse_object_candidates"],
        "wall_mounted": ["wall_mounted"],
        "wall_object_candidates": ["visible_wall_mounted_candidate_objects"],
        "world_base_height": ["metadata_world_base_height"],
    }
    if name == "extremum_direction":
        return _three_d_extremum_direction_values(text)
    if name == "relation_mode":
        return _three_d_relation_mode_values(text)
    return values_by_name.get(name, [_default_placeholder_value(name)])


def _three_d_target_object_type_values(text: str) -> list[str]:
    wall_types = {
        "air_conditioner": "air_conditioner",
        "clock": "clock",
        "hanging_coat": "hanging_coat",
        "mirror": "mirror",
        "picture_frame": "picture_frame",
        "tv": "tv",
        "wall_fan": "wall_fan",
        "wall_shelf": "wall_shelf",
    }
    for token, value in wall_types.items():
        if token in text:
            return [value]
    return ["sampled_prompt_object_type"]


def _three_d_shelf_level_values(text: str) -> list[str]:
    if "top" in text:
        return ["top"]
    if "middle" in text:
        return ["middle"]
    if "bottom" in text:
        return ["bottom"]
    return ["top", "middle", "bottom"]


def _three_d_extremum_direction_values(text: str) -> list[str]:
    if "closest" in text:
        return ["closest"]
    if "farthest" in text:
        return ["farthest"]
    if "highest" in text:
        return ["highest"]
    if "lowest" in text:
        return ["lowest"]
    return ["closest", "farthest", "highest", "lowest"]


def _three_d_depth_relation_values(text: str) -> list[str]:
    if "closer" in text:
        return ["closer_to_camera"]
    if "farther" in text:
        return ["farther_from_camera"]
    return ["closer_to_camera", "farther_from_camera"]


def _three_d_lateral_relation_values(text: str) -> list[str]:
    if "left" in text:
        return ["left_of_reference"]
    if "right" in text:
        return ["right_of_reference"]
    return ["left_of_reference", "right_of_reference"]


def _three_d_relation_mode_values(text: str) -> list[str]:
    if "on_top" in text:
        return ["on_top_of"]
    if "under" in text:
        return ["under"]
    if "inside" in text:
        return ["inside"]
    return ["on_top_of", "under", "inside"]


def _physics_placeholder_allowed_values(name: str, *, scene_id: str, slug: str, query_id: str) -> list[str]:
    text = f"{scene_id} {slug} {query_id}".lower()
    values_by_name = {
        "area_1": ["visible_station_1_area_label"],
        "area_2": ["visible_station_2_area_label"],
        "capacitor_components_between_terminals": ["visible_capacitors_between_A_B"],
        "candidate_point": ["sampled_candidate_point"],
        "candidate_points": ["visible_candidate_points"],
        "candidate_processes": ["visible_mini_pv_processes"],
        "charge_sign": ["positive_charge", "negative_charge"],
        "charges_q1_q2": ["fixed_same_sign_charge_pair"],
        "charges_q1_q2_q3": ["visible_point_charges_Q1_Q2_Q3"],
        "combined_mass": ["mass_A_plus_mass_B"],
        "direction_mode": ["electric_field_direction", "force_on_positive_charge", "force_on_negative_charge"],
        "distance_i": ["visible_distance_from_fulcrum"],
        "effort_force": ["visible_or_unknown_effort_force"],
        "extension_a": ["first_visible_extension_marker"],
        "extension_b": ["second_visible_extension_marker"],
        "final_sticky_velocity": ["velocity_after_sticky_collision"],
        "final_volume": ["visible_final_volume"],
        "hidden_ray_path": ["trace_solved_ray_path"],
        "harmonic_pattern": ["visible_harmonic_support_and_decay_pattern"],
        "input_area": ["visible_input_piston_area"],
        "input_force": ["visible_or_unknown_input_force"],
        "input_waveform": ["visible_time_domain_waveform_panel"],
        "initial_volume": ["visible_initial_volume"],
        "lambda_half_step": ["visible_lambda_over_two_unit"],
        "left_weight_distance_terms": ["visible_left_weight_distance_terms"],
        "load_force": ["visible_or_unknown_load_force"],
        "magnetic_field_orientation": ["into_page", "out_of_page"],
        "marked_position_time_graph_interval": ["highlighted_position_time_interval_with_local_curve_segment"],
        "marked_velocity_time_graph_interval": ["highlighted_velocity_time_interval_with_local_curve_segment"],
        "output_area": ["visible_or_unknown_output_piston_area"],
        "output_force": ["visible_or_unknown_output_force"],
        "path_difference_parity": ["candidate_path_difference_parity"],
        "phase_relation": ["in_phase", "opposite_phase"],
        "point_p": ["visible_point_P"],
        "pressure": ["visible_process_pressure"],
        "process": ["candidate_pv_process"],
        "pucks_a_b": ["visible_input_pucks_A_B"],
        "query_extension": ["right_spring_extension"],
        "query_weight": ["right_spring_weight"],
        "reference_extension": ["reference_spring_extension"],
        "reference_weight": ["reference_spring_weight"],
        "resistor_components_between_terminals": ["visible_resistors_between_A_B"],
        "right_weight_distance_terms": ["visible_right_weight_distance_terms"],
        "series_parallel_network": ["mixed_series_parallel_topology"],
        "source_s1": ["visible_source_S1"],
        "source_s2": ["visible_source_S2"],
        "spectrum_lobe_width": ["visible_main_lobe_width"],
        "spectrum_options": ["visible_labeled_one_sided_magnitude_spectra"],
        "spike_components": ["visible_frequency_spike_components"],
        "support_strand_count": ["counted_full_supporting_strands"],
        "speed_1": ["visible_or_unknown_station_1_speed_label"],
        "speed_2": ["visible_or_unknown_station_2_speed_label"],
        "target_condition": ["constructive", "destructive"],
        "target_points": ["visible_target_points"],
        "target_sign": ["positive", "negative", "zero"],
        "unknown_weight": ["marked_missing_weight"],
        "unknown_speed_slot": ["station_1_speed", "station_2_speed"],
        "velocity_vector": ["visible_velocity_arrow"],
        "weight_i": ["visible_weight_block"],
        "weights_on_queried_side": ["visible_weights_on_queried_side"],
    }
    if name == "component_axis":
        return ["x", "y"]
    if name == "unknown_slot":
        if "hydraulic" in text:
            if query_id == "missing_input_force":
                return ["input_force"]
            if query_id == "missing_output_force":
                return ["output_force"]
            if query_id == "missing_piston_area":
                return ["output_area"]
            if query_id == "missing_input_area":
                return ["input_area"]
            return ["input_force", "input_area", "output_force", "output_area"]
        if "pulley" in text:
            return ["effort_force", "load_force"]
        if "spring" in text:
            return ["missing_weight", "missing_extension"]
        return ["sampled_unknown_slot"]
    return values_by_name.get(name, [_default_placeholder_value(name)])


def _puzzle_placeholder_allowed_values(name: str, *, scene_id: str, slug: str, query_id: str) -> list[str]:
    text = f"{scene_id} {slug} {query_id}".lower()
    values_by_name = {
        "adjacency": ["orthogonal_grid_adjacency"],
        "agent_grid": ["visible_agent_grid"],
        "all": ["all_visible_candidates"],
        "automaton_rule_table": ["visible_automaton_rule_table"],
        "blank_cell": ["marked_blank_cell"],
        "blank_position": ["marked_blank_position"],
        "board": ["visible_board"],
        "board_grid": ["visible_board_grid"],
        "board_scope": ["visible_board_scope"],
        "board_state": ["visible_board_state"],
        "boundary_exits": ["visible_boundary_exits"],
        "candidate_boards": ["visible_candidate_boards"],
        "candidate_cells": ["visible_candidate_cells"],
        "candidate_faces": ["visible_candidate_faces"],
        "candidate_grids": ["visible_candidate_grids"],
        "candidate_lines": ["visible_candidate_lines"],
        "candidate_loops": ["visible_candidate_loops"],
        "candidate_matchstick_figures": ["visible_candidate_matchstick_figures"],
        "candidate_nets": ["visible_candidate_cube_nets"],
        "candidate_numbers": ["visible_candidate_numbers"],
        "candidate_panels": ["visible_candidate_panels"],
        "candidate_paths": ["visible_candidate_paths"],
        "candidate_pieces": ["visible_candidate_pieces"],
        "candidate_pose_boards": ["visible_candidate_pose_boards"],
        "candidate_projections": ["visible_candidate_projections"],
        "candidate_sequences": ["visible_candidate_sequences"],
        "candidate_switches": ["visible_candidate_switches"],
        "candidate_tiles": ["visible_candidate_tiles"],
        "checkpoints": ["visible_checkpoints"],
        "chords": ["visible_chords"],
        "clock": ["visible_clock"],
        "clock_hands": ["visible_clock_hands"],
        "color": ["sampled_color"],
        "condition_event": ["sampled_condition_event"],
        "counterfactual_edit": ["specified_counterfactual_edit"],
        "cube_net": ["visible_cube_net"],
        "die": ["visible_die"],
        "die_a": ["visible_first_die"],
        "die_b": ["visible_second_die"],
        "dimension_axis": ["row_count", "column_count"],
        "duration_relation": ["same_duration", "different_duration"],
        "edit": ["specified_edit"],
        "edit_direction": ["add_one_stick", "remove_one_stick"],
        "equal_sum_constraint": ["visible_equal_sum_constraint"],
        "event": ["sampled_event"],
        "fold_sequence": ["visible_fold_sequence"],
        "grid_state": ["visible_grid_state"],
        "harmony_label_type": ["chord_quality", "chord_inversion", "roman_numeral"],
        "initial_grid": ["visible_initial_grid"],
        "ladder_graph": ["visible_voxel_ladder_graph"],
        "layer_a": ["visible_layer_a"],
        "layer_b": ["visible_layer_b"],
        "line_grid": ["visible_line_grid"],
        "line_orientation": ["horizontal", "vertical"],
        "marked_block": ["marked_block"],
        "marked_cell": ["marked_cell"],
        "marked_gap": ["marked_gap"],
        "marked_group": ["marked_group"],
        "marked_line": ["marked_line"],
        "marked_line_clue": ["marked_line_clue"],
        "marked_note": ["marked_note"],
        "marked_note_group": ["marked_note_group"],
        "marked_note_pair": ["marked_note_pair"],
        "marked_notes": ["marked_notes"],
        "marked_piece": ["marked_piece"],
        "marked_region": ["marked_region"],
        "marked_tree": ["marked_tree"],
        "matrix_context": ["visible_raven_matrix_context"],
        "maze_graph": ["visible_maze_graph"],
        "move_sequence": ["sampled_move_sequence"],
        "number_sequence": ["visible_number_sequence"],
        "operation": ["addition", "subtraction", "multiplication"],
        "operation_rule": ["visible_operation_rule"],
        "pair_event_schema": ["at_least_one_target_color", "both_target_color", "same_color"],
        "paired_cluster_rule": ["visible_paired_cluster_rule"],
        "path_marks": ["visible_path_marks"],
        "pipe_grid": ["visible_pipe_grid"],
        "projection_views": ["visible_projection_views"],
        "query": ["post_transform_query"],
        "queried_face_position": ["front", "right", "top"],
        "reference_entity": ["marked_box", "marked_target"],
        "reference_face_or_edge": ["marked_face_or_edge"],
        "reference_loop": ["visible_reference_loop"],
        "recurrence_operation": ["addition", "difference", "multiplication"],
        "relation_mode": ["opposite_face", "edge_neighbor_face"],
        "roll_sequence": ["visible_roll_sequence"],
        "row_clues": ["visible_row_clues"],
        "rule": ["sampled_rule"],
        "scale_membership": ["scale_membership_truth"],
        "sheet": ["visible_fold_sheet"],
        "sokoban_board": ["visible_sokoban_board"],
        "source": ["source_cell"],
        "source_cell": ["source_cell"],
        "source_number": ["visible_source_number"],
        "spells_word": ["target_word_path_rule"],
        "spinner": ["visible_spinner"],
        "spinner_a": ["visible_first_spinner"],
        "spinner_b": ["visible_second_spinner"],
        "staff_excerpt": ["visible_staff_excerpt"],
        "start_cell": ["visible_start_cell"],
        "start_checkpoint": ["visible_start_checkpoint"],
        "start_grid": ["visible_start_grid"],
        "state": ["cell_state"],
        "switch": ["candidate_switch"],
        "switch_sequence": ["visible_switch_sequence"],
        "symmetry_axis": ["sampled_symmetry_axis"],
        "target": ["target_cell"],
        "target_attribute": ["sampled_target_attribute"],
        "target_cell": ["marked_target_cell"],
        "target_chord": ["marked_chord"],
        "target_color": ["sampled_target_color"],
        "target_component_type": ["open_rope", "closed_loop", "knotted_component"],
        "target_difference": ["sampled_difference"],
        "target_event": ["sampled_target_event"],
        "target_face": ["sampled_cube_face"],
        "target_hidden_digit": ["marked_hidden_digit"],
        "target_letter": ["sampled_target_letter"],
        "target_reachability": ["reachable", "unreachable"],
        "target_sticker": ["marked_sticker"],
        "target_sum": ["sampled_target_sum"],
        "target_symbol": ["sampled_target_symbol"],
        "target_validity": ["valid", "blocked"],
        "target_word": ["sampled_target_word"],
        "tents_grid": ["visible_tents_grid"],
        "threshold": ["sampled_threshold"],
        "tile": ["candidate_tile"],
        "turing": ["visible_turing_machine"],
        "unknown": ["marked_unknown"],
        "view_axis": ["front", "side", "top"],
        "voxel_structure": ["visible_voxel_structure"],
        "wall_grid": ["visible_number_wall_grid"],
        "window_length": ["sampled_window_length"],
    }
    if name == "direction":
        return _direction_values(text, default=("highest", "lowest"))
    if name == "offset_direction":
        if "before" in text:
            return ["before"]
        if "after" in text:
            return ["after"]
        return ["before", "after"]
    if name == "offset_minutes":
        return ["sampled_offset_minutes"]
    if name == "step_count":
        if "one_step" in text:
            return ["1"]
        if "two_step" in text:
            return ["2"]
        return ["sampled_step_count"]
    if name == "rank":
        if scene_id == "sokoban" and "manhattan_rank" in text:
            return ["sampled_manhattan_rank"]
        return _rank_values(text)
    if name == "direction" or name == "offset_direction":
        return ["before", "after"] if "clock" in text else _direction_values(text, default=("highest", "lowest"))
    return values_by_name.get(name, [_default_placeholder_value(name)])


def _program_placeholders(program_schema: str) -> list[str]:
    function_names = {
        "answer",
        "apply_physics_direction_rule",
        "apply_time_offset",
        "abs",
        "baseline_from_percent_change",
        "can_connect",
        "category",
        "change",
        "compare",
        "compute_value",
        "connected_components",
        "count",
        "cycle_structure",
        "derive_metric",
        "difference",
        "direct_answer",
        "distance",
        "filter",
        "follow_route",
        "index",
        "label",
        "lookup_label",
        "lookup_x",
        "mark_count",
        "arg_extreme",
        "arg_min_distance",
        "adjacent_values",
        "bin_containing_rank",
        "categories_between",
        "cell_value",
        "contributions_through",
        "cumulative_counts",
        "endpoint_change",
        "final_total",
        "intersections",
        "intersection",
        "leaves_under_parent",
        "lengths",
        "max",
        "mean",
        "median",
        "min",
        "monotone_runs",
        "neighbor_regions",
        "off_diagonal_cells",
        "order_reversal_pairs",
        "pair_mean",
        "path_edges",
        "percent_to_count",
        "positional_segments",
        "max_flow",
        "min_cut",
        "minimum_cut",
        "minimum_spanning_tree",
        "probability",
        "reachable_set",
        "route_cost",
        "round",
        "select",
        "select_by_rank",
        "select_calendar_date",
        "select_first",
        "select_first_label",
        "select_first_step",
        "select_label",
        "select_option",
        "select_pair_matching_transform",
        "select_top_k",
        "select_point_satisfying_region_predicate",
        "select_rule_violation",
        "shortest_path",
        "simulate",
        "solve_formula",
        "sum",
        "summary_statistic",
        "sum_absolute",
        "topological_order",
        "transform",
        "traverse",
        "turning_points",
        "vertical_range",
        "value",
        "value_a",
        "value_b",
        "values",
        "x_axis_value",
    }
    syntax_words = {
        "and",
        "absolute",
        "or",
        "not",
        "where",
        "lower",
        "upper",
        "for",
        "in",
        "true",
        "false",
        "none",
        "highest",
        "lowest",
        "best",
        "winning",
        "highest_valid",
        "signed",
        "blocked",
        "capture",
        "click",
        "destination",
        "detail_text",
        "disabled",
        "enabled",
        "entry_after_named_entry",
        "field_value",
        "item_label",
        "profile_name",
        "select_option",
        "step_after_named_step",
        "step_detail",
        "step_title",
        "type_text",
        "value_text",
    }
    called_names = set(re.findall(r"\b([a-z][a-z0-9_]*)\s*\(", program_schema))
    keyword_names = set(re.findall(r"\b([a-z][a-z0-9_]*)\s*=", program_schema))
    names = re.findall(r"\b[a-z][a-z0-9_]*\b", program_schema)
    placeholders: list[str] = []
    for name in names:
        if name in function_names or name in called_names or name in keyword_names or name in syntax_words:
            continue
        if name in {"scene", "scope"}:
            continue
        if name not in placeholders:
            placeholders.append(name)
    return placeholders


def _placeholder_value_type(name: str) -> str:
    if name in {"direction", "mode", "rank", "rank_a", "rank_b", "statistic", "operation", "formula_schema"}:
        return "enum"
    if name in {"threshold", "lower", "upper", "k", "steps"}:
        return "numeric_bound"
    if "attribute" in name or "predicate" in name:
        return "object_attribute"
    return "semantic_role"


def _default_placeholder_value(name: str) -> str:
    defaults = {
        "units": "visible_units",
        "items": "visible_items",
        "selected_support": "selected_visible_support",
        "selected_visible_support": "selected_visible_support",
        "scene_measurements": "visible_scene_measurements",
        "candidate_options": "visible_candidate_options",
        "reference_or_rule": "reference_or_rule",
        "query_parameters": "query_parameters",
        "query_attribute_or_role": "query_attribute_or_role",
    }
    return defaults.get(name, name)


def _direction_values(text: str, *, default: tuple[str, ...]) -> list[str]:
    if any(token in text for token in ("highest", "maximum", "max_", "most", "largest", "greatest")):
        return ["highest"]
    if any(token in text for token in ("lowest", "minimum", "min_", "fewest", "smallest", "least")):
        return ["lowest"]
    return list(default)


def _predicate_direction_values(text: str) -> list[str]:
    values: list[str] = []
    if any(token in text for token in ("above", "greater", "higher", "over", "exceed")):
        values.append("above")
    if any(token in text for token in ("below", "less", "lower", "under")):
        values.append("below")
    return values or ["above", "below"]


def _rank_values(text: str) -> list[str]:
    values: list[str] = []
    if "second_closest" in text:
        values.append("second_closest")
    elif "closest" in text or "nearest" in text:
        values.append("closest")
    if "farthest" in text or "furthest" in text:
        values.append("farthest")
    for token, value in (
        ("first", "first"),
        ("second", "second"),
        ("third", "third"),
        ("fourth", "fourth"),
        ("top", "top"),
        ("bottom", "bottom"),
        ("nth", "nth"),
    ):
        if token in text:
            values.append(value)
    if "rank" in text and not values:
        values.append("ranked_position")
    return values or ["sampled_rank_position"]


def _rank_pair_values(text: str, *, first: bool) -> list[str]:
    if first:
        if "bottom" in text:
            return ["bottom"]
        return ["top"]
    if "second" in text:
        return ["second"]
    if "third" in text:
        return ["third"]
    if "bottom" in text:
        return ["bottom"]
    return ["sampled_rank_position"]


def _target_attribute_values(text: str) -> list[str]:
    values: list[str] = []
    for token, value in (
        ("color", "color"),
        ("shape", "shape"),
        ("type", "type"),
        ("status", "status"),
        ("category", "category"),
        ("attribute", "attribute"),
        ("label", "label"),
        ("piece", "piece_kind"),
    ):
        if token in text:
            values.append(value)
    return values or ["query_attribute_or_role"]


def _role_values(text: str) -> list[str]:
    values: list[str] = []
    for token, value in (
        ("source", "source"),
        ("target", "target"),
        ("reference", "reference"),
        ("anchor", "anchor"),
        ("neighbor", "neighbor"),
        ("predecessor", "predecessor"),
        ("successor", "successor"),
    ):
        if token in text:
            values.append(value)
    return values or ["sampled_role"]


def _source_role_values(text: str, *, first: bool) -> list[str]:
    if "callout" in text and first:
        return ["callout_mark"]
    if "endpoint" in text and not first:
        return ["endpoint_mark"]
    if "reference" in text and not first:
        return ["reference_value"]
    if "baseline" in text and first:
        return ["baseline_value"]
    if "selected" in text:
        return ["selected_support_value"]
    return ["source_a" if first else "source_b"]


def _difference_mode_values(text: str) -> list[str]:
    if "percent" in text or "percentage" in text:
        return ["percent_change"]
    if "ratio" in text:
        return ["ratio_difference"]
    if "shift" in text:
        return ["signed_change"]
    if any(token in text for token in ("difference", "gap", "delta", "change")):
        return ["absolute_difference"]
    return ["difference_mode"]


def _metric_values(text: str) -> list[str]:
    if "median" in text:
        return ["median"]
    if "mean" in text or "average" in text:
        return ["mean"]
    if "total" in text or "sum" in text:
        return ["total"]
    if "value" in text:
        return ["value"]
    return ["queried_metric"]


def _statistic_values(text: str) -> list[str]:
    values: list[str] = []
    if "sum" in text or "total" in text:
        values.append("sum")
    if "median" in text:
        values.append("median")
    if "mean" in text or "average" in text:
        values.append("mean")
    return values or ["summary_statistic"]


def _operation_values(text: str) -> list[str]:
    values: list[str] = []
    for token, value in (
        ("ratio", "ratio"),
        ("rate", "rate"),
        ("percent", "percent"),
        ("share", "share"),
        ("angle", "angle"),
        ("area", "area"),
        ("perimeter", "perimeter"),
        ("volume", "volume"),
        ("bearing", "bearing"),
    ):
        if token in text:
            values.append(value)
    return values or ["derived_metric_operation"]


def _formula_schema_from_contract(contract: str) -> str:
    match = re.search(r"formula_schema=([a-z0-9_]+)", contract)
    return match.group(1) if match else ""


def _unknown_role_value(text: str) -> str:
    if "angle" in text:
        return "angle"
    if "length" in text or "side" in text:
        return "length"
    if "area" in text:
        return "area"
    if "volume" in text:
        return "volume"
    return "numeric_unknown"


def aggregate_program_arguments(rows: list[dict[str, Any]]) -> dict[str, Any]:
    payloads = [parse_program_arguments(row.get("program_arguments_json", "")) for row in rows]
    status_counts: Counter[str] = Counter(str(payload.get("status", "needs_review")) for payload in payloads)
    parameter_axes: set[str] = set()
    arguments: dict[str, dict[str, Any]] = {}
    constraints: list[Any] = []
    for payload in payloads:
        parameter_axes.update(str(axis) for axis in payload.get("parameter_axes", []) if str(axis))
        for constraint in payload.get("constraints", []):
            if constraint not in constraints:
                constraints.append(constraint)
        for name, entry in payload.get("arguments", {}).items():
            if not isinstance(entry, Mapping):
                continue
            existing = arguments.setdefault(
                str(name),
                {
                    "value_type": str(entry.get("value_type", "semantic_role")),
                    "allowed_values": [],
                    "source": "",
                    "notes": "",
                },
            )
            existing["allowed_values"] = sorted(
                set(existing.get("allowed_values", []))
                | {str(value) for value in entry.get("allowed_values", []) if str(value)}
            )
            existing["source"] = unique_join([existing.get("source", ""), str(entry.get("source", ""))], sep="|")
            existing["notes"] = unique_join([existing.get("notes", ""), str(entry.get("notes", ""))], sep=" ")
    if status_counts.get("needs_review"):
        status = "needs_review"
    elif status_counts.get("inferred"):
        status = "inferred"
    else:
        status = "curated"
    return {
        "schema_version": PROGRAM_ARGUMENT_SCHEMA_VERSION,
        "status": status,
        "status_counts": dict(sorted(status_counts.items())),
        "query_count": len(payloads),
        "parameter_axes": sorted(parameter_axes) or ["sampled_scene_values"],
        "arguments": {name: arguments[name] for name in sorted(arguments)},
        "constraints": constraints,
    }


def parse_program_arguments(value: Any) -> dict[str, Any]:
    try:
        payload = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {
            "schema_version": PROGRAM_ARGUMENT_SCHEMA_VERSION,
            "status": "needs_review",
            "parameter_axes": ["invalid_json"],
            "arguments": {},
            "constraints": ["invalid_json"],
        }
    if not isinstance(payload, Mapping):
        return {
            "schema_version": PROGRAM_ARGUMENT_SCHEMA_VERSION,
            "status": "needs_review",
            "parameter_axes": ["invalid_json"],
            "arguments": {},
            "constraints": ["non_object_json"],
        }
    return dict(payload)


def contract_rationale(prior: Mapping[str, str] | None, signature: ProgramSignature, answer_schema: str, annotation_schema: str) -> str:
    bits: list[str] = []
    if prior:
        bits.append("Manual boundary seed provided the proposed task mapping.")
    else:
        bits.append("No manual boundary seed row was available; current task inventory supplied the proposed task mapping.")
    bits.append(f"Contract-v0 program schema: {signature.signature_id}.")
    bits.append(f"Answer/annotation schemas: {answer_schema} / {annotation_schema}.")
    return " ".join(bits)


def enforce_contract_splits(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Split proposed groups that still mix hard task-contract fields."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["proposed_task_id"])].append(row)

    adjusted: list[dict[str, Any]] = []
    for proposed_id, items in grouped.items():
        contract_keys = {
            (
                str(row["answer_schema"]),
                str(row["annotation_schema"]),
                str(row["base_program_contract"]),
                str(row["view_contract"]),
            )
            for row in items
        }
        if len(contract_keys) <= 1:
            adjusted.extend(items)
            continue
        for row in items:
            suffix = str(row["current_query_id"])
            if suffix == str(row["proposed_task_slug"]):
                suffix = str(row["program_signature_id"]).replace(".", "_")
            new_slug = sanitize_slug(f"{row['proposed_task_slug']}__{suffix}")
            row = dict(row)
            row["proposed_task_slug"] = new_slug
            row["proposed_task_id"] = proposed_task_id(str(row["domain"]), str(row["scene_id"]), new_slug)
            row = refresh_program_contract(row)
            row["decision_source"] = f"{row['decision_source']}+hard_contract_split"
            row["rationale"] = (
                str(row["rationale"])
                + " Contract-v0 hard split applied because the proposed group mixed answer, annotation, program, or view schemas."
            )
            adjusted.append(row)
    return sorted(adjusted, key=lambda r: (str(r["domain"]), str(r["scene_id"]), str(r["current_task_id"]), str(r["current_query_id"])))


def sanitize_slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9_]+", "_", value.lower())
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def build_task_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_current: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_current[str(row["current_task_id"])].append(row)

    out: list[dict[str, Any]] = []
    for task_id, items in sorted(by_current.items()):
        proposed_ids = sorted({str(row["proposed_task_id"]) for row in items})
        current_id = str(task_id)
        if len(proposed_ids) > 1:
            decision = "split"
        elif proposed_ids[0] == current_id:
            decision = "keep"
        else:
            decision = "rename"
        first = items[0]
        out.append(
            {
                "domain": first["domain"],
                "scene_id": first["scene_id"],
                "current_task_id": current_id,
                "decision": decision,
                "proposed_task_count": len(proposed_ids),
                "proposed_task_ids": " | ".join(proposed_ids),
                "query_ids": " | ".join(sorted({str(row["current_query_id"]) for row in items})),
                "program_signature_ids": " | ".join(sorted({str(row["program_signature_id"]) for row in items})),
                "base_program_contracts": " | ".join(sorted({str(row["base_program_contract"]) for row in items})),
                "program_argument_axes_json": json.dumps(aggregate_program_arguments(items), sort_keys=True),
                "answer_schemas": " | ".join(sorted({str(row["answer_schema"]) for row in items})),
                "annotation_schemas": " | ".join(sorted({str(row["annotation_schema"]) for row in items})),
                "rationale": unique_join(row["rationale"] for row in items),
            }
        )
    return out


def build_canonical_program_rows(
    rows: list[dict[str, Any]],
    catalog: Mapping[str, ProgramSignature],
) -> list[dict[str, Any]]:
    uses: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        uses[str(row["program_signature_id"])].append(row)
    out: list[dict[str, Any]] = []
    for signature_id in sorted(catalog):
        signature = catalog[signature_id]
        items = uses.get(signature_id, [])
        domains = sorted({str(row["domain"]) for row in items})
        scenes = sorted({f"{row['domain']}/{row['scene_id']}" for row in items})
        proposed = sorted({str(row["proposed_task_id"]) for row in items})
        out.append(
            {
                "program_signature_id": signature.signature_id,
                "program_schema": signature.program_schema,
                "definition": signature.definition,
                "do_not_merge_when": signature.do_not_merge_when,
                "domain_count": len(domains),
                "domains": " | ".join(domains),
                "scene_count": len(scenes),
                "scenes": " | ".join(scenes[:40]) + (" | ..." if len(scenes) > 40 else ""),
                "proposed_task_count": len(proposed),
                "example_proposed_task_ids": " | ".join(proposed[:40]) + (" | ..." if len(proposed) > 40 else ""),
            }
        )
    return out


def detect_exact_merge_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find same-scene proposed tasks with identical hard contract signatures."""

    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[str(row["proposed_task_id"])].append(row)
    task_contracts: list[dict[str, Any]] = []
    for task_id, items in by_task.items():
        first = items[0]
        key = (
            str(first["domain"]),
            str(first["scene_id"]),
            str(first["view_contract"]),
            str(first["answer_schema"]),
            str(first["annotation_schema"]),
            str(first["base_program_contract"]),
        )
        task_contracts.append(
            {
                "proposed_task_id": task_id,
                "key": key,
                "domain": first["domain"],
                "scene_id": first["scene_id"],
                "answer_schema": first["answer_schema"],
                "annotation_schema": first["annotation_schema"],
                "program_signature_id": first["program_signature_id"],
                "base_program_contract": first["base_program_contract"],
            }
        )
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for item in task_contracts:
        grouped[item["key"]].append(item)
    out: list[dict[str, Any]] = []
    for key, items in sorted(grouped.items()):
        ids = sorted({str(item["proposed_task_id"]) for item in items})
        if len(ids) <= 1:
            continue
        out.append(
            {
                "domain": key[0],
                "scene_id": key[1],
                "view_contract": key[2],
                "answer_schema": key[3],
                "annotation_schema": key[4],
                "program_signature_id": key[5],
                "base_program_contract": key[6],
                "candidate_task_ids": " | ".join(ids),
                "candidate_count": len(ids),
                "note": "Exact same-scene contract candidate. Inspect before refactoring; public merge still requires human approval.",
            }
        )
    return out


def write_domain_markdowns(summary_rows: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in summary_rows:
        by_domain[str(row["domain"])].append(row)
    proposed_by_domain: dict[str, set[str]] = defaultdict(set)
    current_by_domain: dict[str, set[str]] = defaultdict(set)
    signature_by_domain: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        proposed_by_domain[str(row["domain"])].add(str(row["proposed_task_id"]))
        current_by_domain[str(row["domain"])].add(str(row["current_task_id"]))
        signature_by_domain[str(row["domain"])].add(str(row["program_signature_id"]))
    domain_dir = OUT_ROOT / "domain_taxonomies"
    domain_dir.mkdir(parents=True, exist_ok=True)
    for domain in ACTIVE_DOMAIN_ORDER:
        items = sorted(by_domain.get(domain, []), key=lambda r: (str(r["scene_id"]), str(r["current_task_id"])))
        split_count = sum(1 for row in items if row["decision"] == "split")
        rename_count = sum(1 for row in items if row["decision"] == "rename")
        lines = [
            f"# {domain} Contract-v0 Taxonomy Reanalysis",
            "",
            f"- Current tasks: {len(current_by_domain.get(domain, set()))}",
            f"- Proposed task units: {len(proposed_by_domain.get(domain, set()))}",
            f"- Split tasks: {split_count}",
            f"- Rename-only tasks: {rename_count}",
            f"- Canonical program signatures used: {len(signature_by_domain.get(domain, set()))}",
            "",
            "| Current task | Decision | Proposed task ids | Program signatures | Rationale |",
            "| --- | --- | --- | --- | --- |",
        ]
        for row in items:
            proposed = "<br>".join(f"`{part}`" for part in str(row["proposed_task_ids"]).split(" | "))
            signatures = "<br>".join(f"`{part}`" for part in str(row["program_signature_ids"]).split(" | "))
            rationale = str(row["rationale"]).replace("\n", " ").replace("|", "\\|")
            lines.append(
                f"| `{row['current_task_id']}` | {row['decision']} | {proposed} | {signatures} | {rationale} |"
            )
        (domain_dir / f"{domain}.md").write_text("\n".join(lines) + "\n")


def write_summary(
    rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    program_rows: list[dict[str, Any]],
    merge_candidates: list[dict[str, Any]],
) -> None:
    approved_current_task_merges = load_approved_current_task_merges()
    current_by_domain: dict[str, set[str]] = defaultdict(set)
    proposed_by_domain: dict[str, set[str]] = defaultdict(set)
    split_by_domain: Counter[str] = Counter()
    rename_by_domain: Counter[str] = Counter()
    for row in summary_rows:
        domain = str(row["domain"])
        current_by_domain[domain].add(str(row["current_task_id"]))
        if row["decision"] == "split":
            split_by_domain[domain] += 1
        if row["decision"] == "rename":
            rename_by_domain[domain] += 1
    for row in rows:
        proposed_by_domain[str(row["domain"])].add(str(row["proposed_task_id"]))
    base_contracts_by_task: dict[str, set[str]] = defaultdict(set)
    tasks_by_base_contract: dict[str, set[str]] = defaultdict(set)
    argument_status_counts: Counter[str] = Counter()
    for row in rows:
        task_id = str(row["proposed_task_id"])
        contract = str(row["base_program_contract"])
        base_contracts_by_task[task_id].add(contract)
        tasks_by_base_contract[contract].add(task_id)
        argument_status_counts[str(parse_program_arguments(row.get("program_arguments_json", "")).get("status", "needs_review"))] += 1
    duplicate_base_contract_count = sum(1 for task_ids in tasks_by_base_contract.values() if len(task_ids) > 1)

    lines = [
        "# Contract-v0 TRACE Taxonomy Reanalysis",
        "",
        "This package applies the current scene-contract plus task-contract rule to the live default task inventory.",
        "The source seed files provide hand-authored task/query boundary coverage; this package is the current contract-v0 reanalysis output.",
        "",
        "## Totals",
        "",
        f"- Live tasks audited: {len({row['current_task_id'] for row in rows})}",
        f"- Live task/query rows audited: {len(rows)}",
        f"- Proposed task units: {len({row['proposed_task_id'] for row in rows})}",
        f"- Base program contracts: {len(tasks_by_base_contract)}",
        f"- Duplicate base program contracts: {duplicate_base_contract_count}",
        f"- Program argument metadata rows: {sum(argument_status_counts.values())}",
        f"- Program argument rows needing review: {argument_status_counts.get('needs_review', 0)}",
        f"- Canonical program signatures: {len(program_rows)}",
        f"- Current tasks with split recommendation: {sum(1 for row in summary_rows if row['decision'] == 'split')}",
        f"- Current tasks with rename-only recommendation: {sum(1 for row in summary_rows if row['decision'] == 'rename')}",
        f"- Approved current-task merges: {len(approved_current_task_merges)}",
        f"- Exact same-scene merge candidates requiring human review: {len(merge_candidates)}",
        "",
        "## Domain Summary",
        "",
        "| Domain | Current tasks | Proposed task units | Split tasks | Rename-only | Delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for domain in ACTIVE_DOMAIN_ORDER:
        current_count = len(current_by_domain.get(domain, set()))
        proposed_count = len(proposed_by_domain.get(domain, set()))
        lines.append(
            f"| {domain} | {current_count} | {proposed_count} | {split_by_domain[domain]} | {rename_by_domain[domain]} | {proposed_count - current_count:+d} |"
        )
    lines.extend(
        [
            "",
            "## Output Files",
            "",
            "- `task_query_analysis.csv` is the row-level source of truth for proposed task units; count unique `proposed_task_id` values there for final unit counts.",
            "- `proposed_task_summary.csv` is grouped by current live task id. Split rows list multiple proposed task ids in `proposed_task_ids`; the file is not one row per proposed task.",
            "- `canonical_program_schemas.csv` tracks reusable program signatures. Reuse of a signature does not imply public task merging.",
            "",
            "## Validation Notes",
            "",
            "- Every active default task from the registry is represented.",
            "- Every query id from the live audit inventory is represented.",
            "- Per-query observed review samples are preferred for answer/annotation schema; inventory strings are fallback only.",
            "- Program names are canonicalized through `canonical_program_schemas.csv`; reuse across domains canonicalizes terminology but does not merge public tasks.",
            "- Approved current-task merges are listed in `source/approved_current_task_merges.csv`; unapproved proposed-task-id collisions are validation failures.",
            "- Exact same-scene merge candidates are listed separately and must be manually approved before any code refactor.",
        ]
    )
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "README.md").write_text("\n".join(lines) + "\n")
    (OUT_ROOT / "summary.md").write_text("\n".join(lines) + "\n")
    summary_json = {
        "live_task_count": len({row["current_task_id"] for row in rows}),
        "query_row_count": len(rows),
        "proposed_task_count": len({row["proposed_task_id"] for row in rows}),
        "base_program_contract_count": len(tasks_by_base_contract),
        "duplicate_base_program_contract_count": duplicate_base_contract_count,
        "program_argument_row_count": sum(argument_status_counts.values()),
        "program_argument_status_counts": dict(sorted(argument_status_counts.items())),
        "proposed_tasks_with_multiple_base_program_contracts": sum(
            1 for contracts in base_contracts_by_task.values() if len(contracts) > 1
        ),
        "program_signature_count": len(program_rows),
        "split_task_count": sum(1 for row in summary_rows if row["decision"] == "split"),
        "rename_task_count": sum(1 for row in summary_rows if row["decision"] == "rename"),
        "approved_current_task_merge_count": len(approved_current_task_merges),
        "merge_candidate_count": len(merge_candidates),
        "domains": {
            domain: {
                "current_tasks": len(current_by_domain.get(domain, set())),
                "proposed_tasks": len(proposed_by_domain.get(domain, set())),
                "split_tasks": split_by_domain[domain],
                "rename_tasks": rename_by_domain[domain],
                "delta": len(proposed_by_domain.get(domain, set())) - len(current_by_domain.get(domain, set())),
            }
            for domain in ACTIVE_DOMAIN_ORDER
        },
    }
    (OUT_ROOT / "summary.json").write_text(json.dumps(summary_json, indent=2, sort_keys=True) + "\n")


def write_cross_domain_reconciliation(program_rows: list[dict[str, Any]]) -> None:
    reused = [row for row in program_rows if int(row["domain_count"]) > 1 or int(row["scene_count"]) > 1]
    lines = [
        "# Cross-Domain Program-Schema Reconciliation",
        "",
        "This file lists canonical program signatures reused across scenes/domains.",
        "Reuse here means taxonomy terminology has been merged; it does not merge public tasks across scenes.",
        "",
        f"- Canonical signatures: {len(program_rows)}",
        f"- Reused in multiple scenes/domains: {len(reused)}",
        "",
        "| Program signature | Domains | Scene count | Definition | Do-not-merge boundary |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in sorted(reused, key=lambda r: (-int(r["scene_count"]), str(r["program_signature_id"]))):
        lines.append(
            f"| `{row['program_signature_id']}` | {row['domains']} | {row['scene_count']} | {str(row['definition']).replace('|', '/')} | {str(row['do_not_merge_when']).replace('|', '/')} |"
        )
    (OUT_ROOT / "cross_domain_reconciliation.md").write_text("\n".join(lines) + "\n")


def validate(rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]], merge_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    live_ids = set(list_default_task_ids())
    covered_ids = {str(row["current_task_id"]) for row in rows}
    proposed_ids = [str(row["proposed_task_id"]) for row in rows]
    approved_current_task_merges = load_approved_current_task_merges()
    collisions = {
        proposed_id: sorted({str(row["current_task_id"]) for row in rows if str(row["proposed_task_id"]) == proposed_id})
        for proposed_id in sorted(set(proposed_ids))
    }
    approved_collisions: dict[str, list[str]] = {}
    true_collisions: dict[str, list[str]] = {}
    for proposed_task_id, current_task_ids in collisions.items():
        if len(current_task_ids) <= 1:
            continue
        approved_ids = approved_current_task_merges.get(proposed_task_id, set())
        if set(current_task_ids).issubset(approved_ids):
            approved_collisions[proposed_task_id] = current_task_ids
        else:
            true_collisions[proposed_task_id] = current_task_ids
    missing_fields = [
        {
            "current_task_id": row["current_task_id"],
            "current_query_id": row["current_query_id"],
            "missing": ",".join(
                field
                for field in ("answer_schema", "annotation_schema", "program_schema")
                if not str(row.get(field, "")).strip() or str(row.get(field, "")).startswith("unknown_")
            ),
        }
        for row in rows
        if any(
            not str(row.get(field, "")).strip() or str(row.get(field, "")).startswith("unknown_")
            for field in ("answer_schema", "annotation_schema", "program_schema")
        )
    ]
    base_contracts_by_task: dict[str, set[str]] = defaultdict(set)
    tasks_by_base_contract: dict[str, set[str]] = defaultdict(set)
    row_counts_by_proposed_task: Counter[str] = Counter(str(row["proposed_task_id"]) for row in rows)
    for row in rows:
        task_id = str(row["proposed_task_id"])
        contract = str(row.get("base_program_contract", ""))
        base_contracts_by_task[task_id].add(contract)
        tasks_by_base_contract[contract].add(task_id)
    duplicate_base_contracts = {
        contract: sorted(task_ids)
        for contract, task_ids in sorted(tasks_by_base_contract.items())
        if contract and len(task_ids) > 1
    }
    multiple_base_contract_tasks = {
        task_id: sorted(contracts)
        for task_id, contracts in sorted(base_contracts_by_task.items())
        if len(contracts) > 1
    }
    argument_status_counts: Counter[str] = Counter()
    invalid_argument_rows: list[dict[str, str]] = []
    generic_chart_contract_rows: list[dict[str, str]] = []
    non_curated_chart_argument_rows: list[dict[str, str]] = []
    generic_chart_argument_rows: list[dict[str, str]] = []
    generic_game_contract_rows: list[dict[str, str]] = []
    non_curated_game_argument_rows: list[dict[str, str]] = []
    generic_game_argument_rows: list[dict[str, str]] = []
    generic_geometry_contract_rows: list[dict[str, str]] = []
    non_curated_geometry_argument_rows: list[dict[str, str]] = []
    generic_geometry_argument_rows: list[dict[str, str]] = []
    generic_graph_contract_rows: list[dict[str, str]] = []
    non_curated_graph_argument_rows: list[dict[str, str]] = []
    generic_graph_argument_rows: list[dict[str, str]] = []
    generic_icon_contract_rows: list[dict[str, str]] = []
    non_curated_icon_argument_rows: list[dict[str, str]] = []
    generic_icon_argument_rows: list[dict[str, str]] = []
    generic_illustration_contract_rows: list[dict[str, str]] = []
    non_curated_illustration_argument_rows: list[dict[str, str]] = []
    generic_illustration_argument_rows: list[dict[str, str]] = []
    generic_pages_contract_rows: list[dict[str, str]] = []
    non_curated_pages_argument_rows: list[dict[str, str]] = []
    generic_pages_argument_rows: list[dict[str, str]] = []
    generic_physics_contract_rows: list[dict[str, str]] = []
    non_curated_physics_argument_rows: list[dict[str, str]] = []
    generic_physics_argument_rows: list[dict[str, str]] = []
    generic_puzzle_contract_rows: list[dict[str, str]] = []
    non_curated_puzzle_argument_rows: list[dict[str, str]] = []
    generic_puzzle_argument_rows: list[dict[str, str]] = []
    generic_three_d_contract_rows: list[dict[str, str]] = []
    non_curated_three_d_argument_rows: list[dict[str, str]] = []
    generic_three_d_argument_rows: list[dict[str, str]] = []
    for row in rows:
        raw = str(row.get("program_arguments_json", ""))
        is_chart = str(row.get("domain", "")) == "charts"
        is_game = str(row.get("domain", "")) == "games"
        is_geometry = str(row.get("domain", "")) == "geometry"
        is_graph = str(row.get("domain", "")) == "graph"
        is_icons = str(row.get("domain", "")) == "icons"
        is_illustrations = str(row.get("domain", "")) == "illustrations"
        is_pages = str(row.get("domain", "")) == "pages"
        is_physics = str(row.get("domain", "")) == "physics"
        is_puzzle = str(row.get("domain", "")) == "puzzles"
        is_three_d = str(row.get("domain", "")) == "three_d"
        if is_chart and not _is_concrete_chart_contract(str(row.get("base_program_contract", ""))):
            generic_chart_contract_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "base_program_contract": str(row.get("base_program_contract", "")),
                }
            )
        if is_game and not _is_concrete_game_contract(str(row.get("base_program_contract", ""))):
            generic_game_contract_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "base_program_contract": str(row.get("base_program_contract", "")),
                }
            )
        if is_geometry and not _is_concrete_geometry_contract(str(row.get("base_program_contract", ""))):
            generic_geometry_contract_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "base_program_contract": str(row.get("base_program_contract", "")),
                }
            )
        if is_graph and not _is_concrete_graph_contract(str(row.get("base_program_contract", ""))):
            generic_graph_contract_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "base_program_contract": str(row.get("base_program_contract", "")),
                }
            )
        if is_icons and not _is_concrete_icon_contract(str(row.get("base_program_contract", ""))):
            generic_icon_contract_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "base_program_contract": str(row.get("base_program_contract", "")),
                }
            )
        if is_illustrations and not _is_concrete_illustration_contract(str(row.get("base_program_contract", ""))):
            generic_illustration_contract_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "base_program_contract": str(row.get("base_program_contract", "")),
                }
            )
        if is_pages and not _is_concrete_pages_contract(str(row.get("base_program_contract", ""))):
            generic_pages_contract_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "base_program_contract": str(row.get("base_program_contract", "")),
                }
            )
        if is_physics and not _is_concrete_physics_contract(str(row.get("base_program_contract", ""))):
            generic_physics_contract_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "base_program_contract": str(row.get("base_program_contract", "")),
                }
            )
        if is_puzzle and not _is_concrete_puzzle_contract(str(row.get("base_program_contract", ""))):
            generic_puzzle_contract_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "base_program_contract": str(row.get("base_program_contract", "")),
                }
            )
        if is_three_d and not _is_concrete_three_d_contract(str(row.get("base_program_contract", ""))):
            generic_three_d_contract_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "base_program_contract": str(row.get("base_program_contract", "")),
                }
            )
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            invalid_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "error": str(exc),
                }
            )
            continue
        if not isinstance(payload, Mapping):
            invalid_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "error": "payload is not an object",
                }
            )
            continue
        status = str(payload.get("status", ""))
        if is_chart and status != "curated":
            non_curated_chart_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "status": status,
                }
            )
        if is_game and status != "curated":
            non_curated_game_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "status": status,
                }
            )
        if is_geometry and status != "curated":
            non_curated_geometry_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "status": status,
                }
            )
        if is_graph and status != "curated":
            non_curated_graph_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "status": status,
                }
            )
        if is_icons and status != "curated":
            non_curated_icon_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "status": status,
                }
            )
        if is_illustrations and status != "curated":
            non_curated_illustration_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "status": status,
                }
            )
        if is_pages and status != "curated":
            non_curated_pages_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "status": status,
                }
            )
        if is_physics and status != "curated":
            non_curated_physics_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "status": status,
                }
            )
        if is_puzzle and status != "curated":
            non_curated_puzzle_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "status": status,
                }
            )
        if is_three_d and status != "curated":
            non_curated_three_d_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "proposed_task_id": str(row.get("proposed_task_id", "")),
                    "status": status,
                }
            )
        if payload.get("schema_version") != PROGRAM_ARGUMENT_SCHEMA_VERSION or status not in {"curated", "inferred", "needs_review"}:
            invalid_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "error": "missing/invalid schema_version or status",
                }
            )
            continue
        arguments_payload = payload.get("arguments", {})
        if not isinstance(arguments_payload, Mapping):
            invalid_argument_rows.append(
                {
                    "current_task_id": str(row.get("current_task_id", "")),
                    "current_query_id": str(row.get("current_query_id", "")),
                    "error": "arguments is not an object",
                }
            )
            continue
        if is_chart or is_game or is_geometry or is_graph or is_icons or is_illustrations or is_pages or is_physics or is_puzzle or is_three_d:
            if is_chart:
                generic_argument_rows = generic_chart_argument_rows
            elif is_game:
                generic_argument_rows = generic_game_argument_rows
            elif is_geometry:
                generic_argument_rows = generic_geometry_argument_rows
            elif is_graph:
                generic_argument_rows = generic_graph_argument_rows
            elif is_icons:
                generic_argument_rows = generic_icon_argument_rows
            elif is_illustrations:
                generic_argument_rows = generic_illustration_argument_rows
            elif is_pages:
                generic_argument_rows = generic_pages_argument_rows
            elif is_physics:
                generic_argument_rows = generic_physics_argument_rows
            elif is_puzzle:
                generic_argument_rows = generic_puzzle_argument_rows
            else:
                generic_argument_rows = generic_three_d_argument_rows
            axes_payload = payload.get("parameter_axes", [])
            if isinstance(axes_payload, list) and row_counts_by_proposed_task[str(row.get("proposed_task_id", ""))] > 1:
                for axis in axes_payload:
                    axis_text = str(axis)
                    if axis_text in GENERIC_FINALIZED_PARAMETER_AXES or axis_text.startswith("query_"):
                        generic_argument_rows.append(
                            {
                                "current_task_id": str(row.get("current_task_id", "")),
                                "current_query_id": str(row.get("current_query_id", "")),
                                "proposed_task_id": str(row.get("proposed_task_id", "")),
                                "argument": "parameter_axes",
                                "source": f"generic_axis:{axis_text}",
                            }
                        )
            for name, entry in arguments_payload.items():
                if not isinstance(entry, Mapping):
                    generic_argument_rows.append(
                        {
                            "current_task_id": str(row.get("current_task_id", "")),
                            "current_query_id": str(row.get("current_query_id", "")),
                            "proposed_task_id": str(row.get("proposed_task_id", "")),
                            "argument": str(name),
                            "source": "invalid_argument_entry",
                        }
                    )
                    continue
                note = str(entry.get("notes", ""))
                source = str(entry.get("source", ""))
                if "Generic program placeholder" in note or source == "program_schema":
                    generic_argument_rows.append(
                        {
                            "current_task_id": str(row.get("current_task_id", "")),
                            "current_query_id": str(row.get("current_query_id", "")),
                            "proposed_task_id": str(row.get("proposed_task_id", "")),
                            "argument": str(name),
                            "source": source,
                        }
                    )
                for value in entry.get("allowed_values", []):
                    if _is_generic_finalized_argument_value(value):
                        generic_argument_rows.append(
                            {
                                "current_task_id": str(row.get("current_task_id", "")),
                                "current_query_id": str(row.get("current_query_id", "")),
                                "proposed_task_id": str(row.get("proposed_task_id", "")),
                                "argument": str(name),
                                "source": f"generic_value:{value}",
                            }
                        )
        argument_status_counts[status] += 1
    result = {
        "missing_live_tasks": sorted(live_ids - covered_ids),
        "extra_tasks": sorted(covered_ids - live_ids),
        "proposed_task_id_collisions": true_collisions,
        "approved_current_task_merges": approved_collisions,
        "duplicate_base_program_contracts": duplicate_base_contracts,
        "proposed_tasks_with_multiple_base_program_contracts": multiple_base_contract_tasks,
        "base_program_contract_count": len(tasks_by_base_contract),
        "program_argument_status_counts": dict(sorted(argument_status_counts.items())),
        "invalid_program_argument_rows": invalid_argument_rows,
        "generic_chart_contract_rows": generic_chart_contract_rows,
        "generic_chart_argument_rows": generic_chart_argument_rows,
        "non_curated_chart_argument_rows": non_curated_chart_argument_rows,
        "generic_game_contract_rows": generic_game_contract_rows,
        "generic_game_argument_rows": generic_game_argument_rows,
        "non_curated_game_argument_rows": non_curated_game_argument_rows,
        "generic_geometry_contract_rows": generic_geometry_contract_rows,
        "generic_geometry_argument_rows": generic_geometry_argument_rows,
        "non_curated_geometry_argument_rows": non_curated_geometry_argument_rows,
        "generic_graph_contract_rows": generic_graph_contract_rows,
        "generic_graph_argument_rows": generic_graph_argument_rows,
        "non_curated_graph_argument_rows": non_curated_graph_argument_rows,
        "generic_icon_contract_rows": generic_icon_contract_rows,
        "generic_icon_argument_rows": generic_icon_argument_rows,
        "non_curated_icon_argument_rows": non_curated_icon_argument_rows,
        "generic_illustration_contract_rows": generic_illustration_contract_rows,
        "generic_illustration_argument_rows": generic_illustration_argument_rows,
        "non_curated_illustration_argument_rows": non_curated_illustration_argument_rows,
        "generic_pages_contract_rows": generic_pages_contract_rows,
        "generic_pages_argument_rows": generic_pages_argument_rows,
        "non_curated_pages_argument_rows": non_curated_pages_argument_rows,
        "generic_physics_contract_rows": generic_physics_contract_rows,
        "generic_physics_argument_rows": generic_physics_argument_rows,
        "non_curated_physics_argument_rows": non_curated_physics_argument_rows,
        "generic_puzzle_contract_rows": generic_puzzle_contract_rows,
        "generic_puzzle_argument_rows": generic_puzzle_argument_rows,
        "non_curated_puzzle_argument_rows": non_curated_puzzle_argument_rows,
        "generic_three_d_contract_rows": generic_three_d_contract_rows,
        "generic_three_d_argument_rows": generic_three_d_argument_rows,
        "non_curated_three_d_argument_rows": non_curated_three_d_argument_rows,
        "missing_required_contract_fields": missing_fields,
        "merge_candidate_count": len(merge_candidates),
        "summary_row_count": len(summary_rows),
        "query_row_count": len(rows),
    }
    (OUT_ROOT / "validation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (OUT_ROOT / "proposed_task_id_collisions.json").write_text(
        json.dumps(true_collisions, indent=2, sort_keys=True) + "\n"
    )
    return result


def main() -> None:
    rows, summary_rows, program_catalog = build_analysis_rows()
    program_rows = build_canonical_program_rows(rows, program_catalog)
    merge_candidates = detect_exact_merge_candidates(rows)

    inventory_rows = build_live_inventory()
    write_csv(OUT_ROOT / "inventory" / "default_tasks.csv", inventory_rows)
    branch_rows: list[dict[str, Any]] = []
    for item in inventory_rows:
        for query_id in split_pipe(item["query_ids"]) or [item["task_slug"]]:
            branch_rows.append({**item, "query_id": query_id})
    write_csv(OUT_ROOT / "inventory" / "task_query_branches.csv", branch_rows)

    write_csv(OUT_ROOT / "task_query_analysis.csv", rows)
    write_csv(OUT_ROOT / "proposed_task_summary.csv", summary_rows)
    write_csv(OUT_ROOT / "canonical_program_schemas.csv", program_rows)
    write_csv(
        OUT_ROOT / "same_scene_exact_merge_candidates.csv",
        merge_candidates,
        fieldnames=[
            "domain",
            "scene_id",
            "view_contract",
            "answer_schema",
            "annotation_schema",
            "program_signature_id",
            "base_program_contract",
            "candidate_task_ids",
            "candidate_count",
            "note",
        ],
    )
    write_domain_markdowns(summary_rows, rows)
    write_cross_domain_reconciliation(program_rows)
    write_summary(rows, summary_rows, program_rows, merge_candidates)
    validation = validate(rows, summary_rows, merge_candidates)
    if (
        validation["missing_live_tasks"]
        or validation["extra_tasks"]
        or validation["missing_required_contract_fields"]
        or validation["invalid_program_argument_rows"]
        or validation["generic_chart_contract_rows"]
        or validation["generic_chart_argument_rows"]
        or validation["non_curated_chart_argument_rows"]
        or validation["generic_game_contract_rows"]
        or validation["generic_game_argument_rows"]
        or validation["non_curated_game_argument_rows"]
        or validation["generic_geometry_contract_rows"]
        or validation["generic_geometry_argument_rows"]
        or validation["non_curated_geometry_argument_rows"]
        or validation["generic_graph_contract_rows"]
        or validation["generic_graph_argument_rows"]
        or validation["non_curated_graph_argument_rows"]
        or validation["generic_icon_contract_rows"]
        or validation["generic_icon_argument_rows"]
        or validation["non_curated_icon_argument_rows"]
        or validation["generic_illustration_contract_rows"]
        or validation["generic_illustration_argument_rows"]
        or validation["non_curated_illustration_argument_rows"]
        or validation["generic_pages_contract_rows"]
        or validation["generic_pages_argument_rows"]
        or validation["non_curated_pages_argument_rows"]
        or validation["generic_physics_contract_rows"]
        or validation["generic_physics_argument_rows"]
        or validation["non_curated_physics_argument_rows"]
        or validation["generic_puzzle_contract_rows"]
        or validation["generic_puzzle_argument_rows"]
        or validation["non_curated_puzzle_argument_rows"]
        or validation["generic_three_d_contract_rows"]
        or validation["generic_three_d_argument_rows"]
        or validation["non_curated_three_d_argument_rows"]
        or validation["proposed_task_id_collisions"]
        or validation["duplicate_base_program_contracts"]
        or validation["proposed_tasks_with_multiple_base_program_contracts"]
    ):
        raise SystemExit(f"validation failed: {json.dumps(validation, indent=2)}")


if __name__ == "__main__":
    main()
