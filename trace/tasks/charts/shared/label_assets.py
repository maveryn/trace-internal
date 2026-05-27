"""Chart-domain label pools backed by shared repo-wide label assets."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping, Sequence, Tuple

from ....core.sampling import normalize_positive_weights, weighted_choice
from ...shared.labeling import LABEL_POOL_SAFE_UPPER, assign_random_shuffled_labels
from ...shared.name_assets import load_label_manifest


CHART_LABEL_POOL_UP_TO_25: Tuple[str, ...] = tuple("ABCDEFGHIJKLMNPQRSTUVWXYZ")
CHART_NAMED_LABEL_MIN_BUCKET_SIZE = 20

CHART_ENTITY_LABEL_BUCKET_MANIFESTS: Mapping[str, str] = {
    "people_first": "people/first_names_ssa.txt",
    "people_surnames": "people/surnames_census_2010.txt",
    "places_countries": "places/countries_natural_earth.txt",
    "places_cities": "places/cities_natural_earth.txt",
    "organizations_tickers": "organizations/company_tickers_sec.txt",
    "organizations_terms": "organizations/company_terms_sec.txt",
    "occupations": "occupations/occupations_bls_oews.txt",
    "industries": "industries/industries_bls_qcew.txt",
    "mixed_proper": "mixed/proper_labels.txt",
    "mixed_compact": "mixed/compact_labels.txt",
}

CHART_CATEGORY_LABEL_BUCKET_MANIFESTS: Mapping[str, str] = {
    "categories_abstract": "categories/abstract_group_labels.txt",
    "categories_priority": "categories/priority_labels.txt",
    "categories_product": "categories/product_labels.txt",
    "categories_status": "categories/status_labels.txt",
}

CHART_ALL_LABEL_BUCKET_MANIFESTS: Mapping[str, str] = {
    **CHART_ENTITY_LABEL_BUCKET_MANIFESTS,
    **CHART_CATEGORY_LABEL_BUCKET_MANIFESTS,
}

SUPPORTED_CHART_LABEL_VARIANTS: Tuple[str, ...] = ("letters", "named")
SUPPORTED_CHART_LABEL_POOL_KINDS: Tuple[str, ...] = ("all", "entity", "category")


@dataclass(frozen=True)
class ResolvedChartLabels:
    """Resolved visible chart labels plus traceable asset metadata."""

    labels: Tuple[str, ...]
    label_variant: str
    label_pool_kind: str
    label_source_kind: str
    label_bucket: str
    label_manifest: str
    label_filter: Mapping[str, Any]
    label_bucket_probabilities: Mapping[str, float]


def _bucket_manifests_for_kind(label_pool_kind: str) -> Mapping[str, str]:
    kind = str(label_pool_kind).strip().lower()
    if kind == "all":
        return CHART_ALL_LABEL_BUCKET_MANIFESTS
    if kind == "entity":
        return CHART_ENTITY_LABEL_BUCKET_MANIFESTS
    if kind == "category":
        return CHART_CATEGORY_LABEL_BUCKET_MANIFESTS
    raise ValueError(f"unsupported chart label_pool_kind: {label_pool_kind}")


def default_chart_label_bucket_weights(label_pool_kind: str = "all") -> Mapping[str, float]:
    """Return equal default weights over eligible chart label buckets."""

    return {str(bucket): 1.0 for bucket in _bucket_manifests_for_kind(str(label_pool_kind))}


def _dedupe_preserve_order(values: Sequence[str], *, lowercase: bool) -> Tuple[str, ...]:
    labels: list[str] = []
    seen: set[str] = set()
    for value in values:
        label = str(value).strip()
        if bool(lowercase):
            label = str(label).lower()
        if not label or label in seen:
            continue
        seen.add(label)
        labels.append(label)
    return tuple(labels)


@lru_cache(maxsize=512)
def _chart_label_bucket_pool(
    manifest_name: str,
    *,
    min_chars: int | None,
    max_chars: int | None,
    allow_spaces: bool,
    allow_punctuation: bool,
    compact_length: bool,
    lowercase: bool,
) -> Tuple[str, ...]:
    labels = load_label_manifest(
        str(manifest_name),
        min_chars=min_chars,
        max_chars=max_chars,
        allow_spaces=bool(allow_spaces),
        allow_punctuation=bool(allow_punctuation),
        ascii_only=True,
        compact_length=bool(compact_length),
    )
    return _dedupe_preserve_order(labels, lowercase=bool(lowercase))


def _eligible_chart_label_buckets(
    *,
    bucket_manifests: Mapping[str, str],
    object_count: int,
    min_chars: int | None,
    max_chars: int | None,
    allow_spaces: bool,
    allow_punctuation: bool,
    compact_length: bool,
    lowercase: bool,
    min_bucket_size: int,
) -> Mapping[str, Tuple[str, ...]]:
    required_count = max(int(object_count), int(min_bucket_size))
    eligible: dict[str, Tuple[str, ...]] = {}
    for bucket, manifest_name in bucket_manifests.items():
        try:
            labels = _chart_label_bucket_pool(
                str(manifest_name),
                min_chars=min_chars,
                max_chars=max_chars,
                allow_spaces=bool(allow_spaces),
                allow_punctuation=bool(allow_punctuation),
                compact_length=bool(compact_length),
                lowercase=bool(lowercase),
            )
        except Exception:
            continue
        if len(labels) >= int(required_count):
            eligible[str(bucket)] = tuple(str(label) for label in labels)
    return dict(eligible)


def _resolve_bucket_probabilities(
    *,
    eligible_buckets: Sequence[str],
    bucket_weights: Mapping[str, float] | None,
    label_pool_kind: str,
) -> Mapping[str, float]:
    eligible = tuple(str(bucket) for bucket in eligible_buckets)
    raw_weights = (
        {str(key): float(value) for key, value in bucket_weights.items()}
        if isinstance(bucket_weights, Mapping)
        else default_chart_label_bucket_weights(str(label_pool_kind))
    )
    candidate_weights = {str(bucket): float(raw_weights.get(str(bucket), 1.0)) for bucket in eligible}
    return normalize_positive_weights(candidate_weights, default_keys=eligible)


def resolve_chart_text_labels(
    rng: random.Random,
    *,
    count: int,
    label_variant: str = "named",
    label_pool_kind: str = "all",
    min_chars: int | None = None,
    max_chars: int = 12,
    allow_spaces: bool = True,
    allow_punctuation: bool = False,
    compact_length: bool = True,
    lowercase: bool = False,
    bucket_weights: Mapping[str, float] | None = None,
    min_bucket_size: int = CHART_NAMED_LABEL_MIN_BUCKET_SIZE,
) -> ResolvedChartLabels:
    """Resolve visible chart labels from letters or shared named-label assets."""

    count = int(count)
    if count <= 0:
        raise ValueError("count must be positive")
    variant = str(label_variant).strip().lower()
    if variant not in set(SUPPORTED_CHART_LABEL_VARIANTS):
        raise ValueError(f"unsupported chart label_variant: {label_variant}")
    pool_kind = str(label_pool_kind).strip().lower()
    label_filter = {
        "min_chars": min_chars,
        "max_chars": int(max_chars),
        "allow_spaces": bool(allow_spaces),
        "allow_punctuation": bool(allow_punctuation),
        "ascii_only": True,
        "compact_length": bool(compact_length),
        "lowercase": bool(lowercase),
        "min_bucket_size": int(min_bucket_size),
    }
    if variant == "letters":
        label_pool = LABEL_POOL_SAFE_UPPER if count <= len(LABEL_POOL_SAFE_UPPER) else CHART_LABEL_POOL_UP_TO_25
        labels = assign_random_shuffled_labels(rng, object_count=count, label_pool=label_pool)
        return ResolvedChartLabels(
            labels=tuple(str(label) for label in labels),
            label_variant="letters",
            label_pool_kind=pool_kind,
            label_source_kind="letters",
            label_bucket="",
            label_manifest="",
            label_filter=dict(label_filter),
            label_bucket_probabilities={},
        )

    bucket_manifests = _bucket_manifests_for_kind(pool_kind)
    eligible = _eligible_chart_label_buckets(
        bucket_manifests=bucket_manifests,
        object_count=count,
        min_chars=min_chars,
        max_chars=int(max_chars),
        allow_spaces=bool(allow_spaces),
        allow_punctuation=bool(allow_punctuation),
        compact_length=bool(compact_length),
        lowercase=bool(lowercase),
        min_bucket_size=int(min_bucket_size),
    )
    if not eligible:
        raise ValueError("no chart label bucket satisfies the requested constraints")
    probabilities = _resolve_bucket_probabilities(
        eligible_buckets=tuple(eligible.keys()),
        bucket_weights=bucket_weights,
        label_pool_kind=pool_kind,
    )
    bucket = weighted_choice(rng, probabilities, sort_keys=True)
    pool = tuple(str(label) for label in eligible[str(bucket)])
    labels = tuple(str(label) for label in rng.sample(list(pool), k=count))
    return ResolvedChartLabels(
        labels=tuple(str(label) for label in labels),
        label_variant="named",
        label_pool_kind=pool_kind,
        label_source_kind="shared_label_manifest",
        label_bucket=str(bucket),
        label_manifest=str(bucket_manifests[str(bucket)]),
        label_filter=dict(label_filter),
        label_bucket_probabilities=dict(probabilities),
    )


def resolve_chart_category_labels(
    rng: random.Random,
    *,
    count: int,
    max_chars: int = 14,
    min_chars: int | None = 3,
    allow_spaces: bool = True,
    bucket_weights: Mapping[str, float] | None = None,
) -> ResolvedChartLabels:
    """Resolve semantic category labels for chart legends and class bins."""

    return resolve_chart_text_labels(
        rng,
        count=int(count),
        label_variant="named",
        label_pool_kind="category",
        min_chars=min_chars,
        max_chars=int(max_chars),
        allow_spaces=bool(allow_spaces),
        allow_punctuation=False,
        compact_length=True,
        bucket_weights=bucket_weights,
    )


def resolve_chart_entity_labels(
    rng: random.Random,
    *,
    count: int,
    max_chars: int = 12,
    min_chars: int | None = 2,
    allow_spaces: bool = True,
    bucket_weights: Mapping[str, float] | None = None,
) -> ResolvedChartLabels:
    """Resolve entity-style labels for chart axes, row labels, and series names."""

    return resolve_chart_text_labels(
        rng,
        count=int(count),
        label_variant="named",
        label_pool_kind="entity",
        min_chars=min_chars,
        max_chars=int(max_chars),
        allow_spaces=bool(allow_spaces),
        allow_punctuation=False,
        compact_length=True,
        bucket_weights=bucket_weights,
    )


__all__ = [
    "CHART_ALL_LABEL_BUCKET_MANIFESTS",
    "CHART_CATEGORY_LABEL_BUCKET_MANIFESTS",
    "CHART_ENTITY_LABEL_BUCKET_MANIFESTS",
    "CHART_LABEL_POOL_UP_TO_25",
    "CHART_NAMED_LABEL_MIN_BUCKET_SIZE",
    "ResolvedChartLabels",
    "SUPPORTED_CHART_LABEL_POOL_KINDS",
    "SUPPORTED_CHART_LABEL_VARIANTS",
    "default_chart_label_bucket_weights",
    "resolve_chart_category_labels",
    "resolve_chart_entity_labels",
    "resolve_chart_text_labels",
]
