"""Tests for chart-domain label asset adapters."""

from __future__ import annotations

import random

from trace.tasks.charts.shared.label_assets import (
    CHART_CATEGORY_LABEL_BUCKET_MANIFESTS,
    resolve_chart_category_labels,
    resolve_chart_entity_labels,
    resolve_chart_text_labels,
)
from trace.tasks.shared.name_assets import load_label_manifest


def test_chart_category_labels_use_category_manifests() -> None:
    resolved = resolve_chart_category_labels(random.Random(17), count=6, max_chars=14)

    assert len(resolved.labels) == 6
    assert len(set(resolved.labels)) == 6
    assert resolved.label_pool_kind == "category"
    assert resolved.label_bucket in CHART_CATEGORY_LABEL_BUCKET_MANIFESTS
    assert resolved.label_manifest == CHART_CATEGORY_LABEL_BUCKET_MANIFESTS[resolved.label_bucket]
    assert all(label.isascii() for label in resolved.labels)
    assert all(len(label.replace(" ", "")) <= 14 for label in resolved.labels)


def test_chart_entity_labels_can_force_one_shared_manifest_bucket() -> None:
    resolved = resolve_chart_entity_labels(
        random.Random(23),
        count=5,
        max_chars=10,
        allow_spaces=False,
        bucket_weights={"places_countries": 1.0},
    )

    countries = set(
        load_label_manifest(
            "places/countries_natural_earth.txt",
            min_chars=2,
            max_chars=10,
            allow_spaces=False,
            allow_punctuation=False,
            compact_length=True,
        )
    )
    assert resolved.label_bucket == "places_countries"
    assert set(resolved.labels).issubset(countries)


def test_chart_text_labels_still_support_compact_letters() -> None:
    resolved = resolve_chart_text_labels(random.Random(31), count=12, label_variant="letters")

    assert len(resolved.labels) == 12
    assert len(set(resolved.labels)) == 12
    assert resolved.label_source_kind == "letters"
    assert all(len(label) == 1 and label.isalpha() for label in resolved.labels)
