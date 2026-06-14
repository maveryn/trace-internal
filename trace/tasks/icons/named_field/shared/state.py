"""Passive state objects for named-field icon tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from PIL import Image

from .....core.types import TypedValue


@dataclass(frozen=True)
class MaterializedNamedFieldTask:
    """Rendered task payload ready for public ``TaskOutput`` construction."""

    prompt: str
    answer_gt: TypedValue
    annotation_gt: TypedValue
    image: Image.Image
    trace_payload: Dict[str, Any]
    selected_public_query: str
    prompt_variants: Dict[str, str]


@dataclass(frozen=True)
class NamedColorEntry:
    """One semantic color available to named-field queries."""

    name: str
    rgb: Tuple[int, int, int]
    label: str


@dataclass(frozen=True)
class BooleanIconSemanticSpec:
    """One target-relative icon before projection to pixels."""

    shape_id: str
    color_name: str
    fill_style: str
    partition: str


@dataclass(frozen=True)
class BooleanSampleSpec:
    """Fully sampled symbolic plan for one Boolean named-field count."""

    selected_query_id: str
    internal_query_id: str
    predicate_kind: str
    target_shape_id: str
    target_shape_name: str
    target_attribute_axis: str
    target_attribute_value: str
    target_attribute_label: str
    target_color: NamedColorEntry | None
    target_fill_style: str
    target_fill_style_label: str
    target_answer: int
    object_count: int
    object_count_max_answer_offset: int
    arrangement_mode: str
    partition_counts: Dict[str, int]
    semantic_specs: Tuple[BooleanIconSemanticSpec, ...]
    public_query_probabilities: Dict[str, float]
    internal_query_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    color_probabilities: Dict[str, float]
    fill_style_probabilities: Dict[str, float]
    attribute_axis_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]
    arrangement_mode_probabilities: Dict[str, float]


@dataclass(frozen=True)
class CounterfactualIconSemanticSpec:
    """One icon role for a hypothetical named-field edit."""

    shape_id: str
    counterfactual_role: str
    counted_after_edit: bool


@dataclass(frozen=True)
class CounterfactualSampleSpec:
    """Fully sampled symbolic plan for one counterfactual count."""

    selected_query_id: str
    internal_query_id: str
    edit_kind: str
    target_answer: int
    object_count: int
    target_shape_id: str
    target_shape_name: str
    source_shape_id: str
    source_shape_name: str
    remove_shape_id: str
    remove_shape_name: str
    source_count: int
    existing_target_count: int
    removal_count: int
    distractor_count: int
    arrangement_mode: str
    semantic_specs: Tuple[CounterfactualIconSemanticSpec, ...]
    public_query_probabilities: Dict[str, float]
    internal_query_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    removal_count_probabilities: Dict[str, float]
    distractor_count_probabilities: Dict[str, float]
    arrangement_mode_probabilities: Dict[str, float]
    fill_style_support: Tuple[str, ...]
    fill_style_probabilities: Dict[str, float]


__all__ = [
    "BooleanIconSemanticSpec",
    "BooleanSampleSpec",
    "CounterfactualIconSemanticSpec",
    "CounterfactualSampleSpec",
    "MaterializedNamedFieldTask",
    "NamedColorEntry",
]
