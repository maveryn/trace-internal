"""Semantic taxonomy helpers for task-boundary audit review."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class SemanticTaxonomyPath:
    """One semantic taxonomy placement for a proposed task unit."""

    root: str
    family: str
    leaf: str

    @property
    def path(self) -> str:
        return "/".join([self.root, self.family, self.leaf])


def classify_objective(
    objective: str,
    *,
    answer_types: str = "",
    annotation_types: str = "",
    domain: str = "",
    scene_id: str = "",
) -> SemanticTaxonomyPath:
    """Return the semantic taxonomy path for one proposed objective.

    This is intentionally explicit and conservative: the leaf remains the
    proposed objective contract, while the root/family provide a reviewable
    semantic grouping across domains.
    """

    leaf = _clean_id(objective) or "unknown_objective"
    text = " ".join(
        [
            leaf,
            str(answer_types or ""),
            str(annotation_types or ""),
            str(domain or ""),
            str(scene_id or ""),
        ]
    ).lower()
    answer = str(answer_types or "").lower()

    if _has(text, "probability", "odds", "expected_value", "event_value"):
        return SemanticTaxonomyPath("numeric_reasoning", "probability_value", leaf)

    if _has(text, "path", "route", "traversal", "navigation", "flow", "bottleneck"):
        if _has(text, "count"):
            return SemanticTaxonomyPath("path_sequence_reasoning", "path_condition_count", leaf)
        if _has(text, "label"):
            return SemanticTaxonomyPath("path_sequence_reasoning", "path_selection", leaf)
        return SemanticTaxonomyPath("path_sequence_reasoning", "path_value", leaf)

    if _has(text, "counterfactual", "after_removal", "remove_", "reverse_", "baseline_from", "remaining_"):
        return SemanticTaxonomyPath("numeric_reasoning", "counterfactual_value", leaf)

    if leaf.endswith("_count") or "_count_" in leaf or _has(text, "count"):
        return SemanticTaxonomyPath("counting", _count_family(text), leaf)

    if _has(text, "label", "option_letter", "string"):
        if "option_letter" in answer or _has(text, "option", "choice"):
            return SemanticTaxonomyPath("selection", "visual_option_selection", leaf)
        if _has(text, "extremum", "largest", "smallest", "maximum", "minimum", "highest", "lowest", "nearest", "widest", "narrowest", "top_", "bottom_"):
            return SemanticTaxonomyPath("selection", "ranked_extremum_selection", leaf)
        if _has(text, "rank", "kth", "ordinal", "order_statistic", "nth"):
            return SemanticTaxonomyPath("selection", "ranked_order_selection", leaf)
        if _has(text, "relation", "adjacent", "same_", "between", "side", "left", "right", "above", "below", "overlap", "neighbor"):
            return SemanticTaxonomyPath("selection", "relation_selection", leaf)
        if _has(text, "valid", "violation", "acceptance", "winner", "result", "match"):
            return SemanticTaxonomyPath("selection", "rule_result_selection", leaf)
        return SemanticTaxonomyPath("selection", "direct_label_lookup", leaf)

    if leaf.endswith("_value") or _has(text, "value", "total", "sum", "mean", "median", "average", "difference", "gap", "delta", "change", "rate", "area", "angle", "length", "perimeter", "volume", "score", "distance"):
        return SemanticTaxonomyPath("numeric_reasoning", _value_family(text), leaf)

    if _has(text, "boolean", "valid", "acceptance", "property", "violation"):
        return SemanticTaxonomyPath("rule_state_reasoning", "predicate_evaluation", leaf)

    return SemanticTaxonomyPath("other_reasoning", "uncategorized_objective", leaf)


def _count_family(text: str) -> str:
    if _has(text, "threshold", "above", "below", "greater", "less"):
        return "threshold_predicate_count"
    if _has(text, "interval", "range", "between"):
        return "range_predicate_count"
    if _has(text, "condition", "filtered", "predicate", "matching", "category", "attribute", "color", "shape"):
        return "attribute_predicate_count"
    if _has(text, "relation", "adjacent", "neighbor", "same_", "side", "overlap", "crossing"):
        return "relation_predicate_count"
    if _has(text, "component", "region", "cell", "node", "edge", "line", "segment", "leaf", "panel", "group"):
        return "structural_element_count"
    if _has(text, "valid", "violation", "forced", "legal"):
        return "rule_validity_count"
    return "direct_cardinality_count"


def _value_family(text: str) -> str:
    if _has(text, "sum", "total", "mean", "median", "average", "aggregate"):
        return "aggregate_value"
    if _has(text, "difference", "gap", "delta", "change", "shift", "minus"):
        return "difference_value"
    if _has(text, "rate", "ratio", "percent", "share", "proportion"):
        return "ratio_rate_value"
    if _has(text, "area", "angle", "length", "perimeter", "volume", "distance", "bearing"):
        return "measurement_value"
    if _has(text, "score", "payoff"):
        return "score_value"
    return "derived_numeric_value"


def _has(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def _clean_id(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text
