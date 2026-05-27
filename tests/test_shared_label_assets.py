"""Tests for repo-wide shared label/name assets."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_NAME_ASSETS_PATH = Path("trace/tasks/shared/name_assets.py")
_SPEC = importlib.util.spec_from_file_location("trace_shared_name_assets_test", _NAME_ASSETS_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_NAME_ASSETS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_NAME_ASSETS)

asset_root = _NAME_ASSETS.asset_root
filter_label_values = _NAME_ASSETS.filter_label_values
load_label_manifest = _NAME_ASSETS.load_label_manifest
load_label_sources = _NAME_ASSETS.load_label_sources


def test_shared_label_sources_cover_manifest_files_and_licenses() -> None:
    root = asset_root() / "labels"
    metadata = load_label_sources()
    manifests = metadata["manifests"]
    sources = metadata["sources"]

    assert metadata["asset_version"] == "labels_v0"
    assert "people/first_names_ssa.txt" in manifests
    assert "places/cities_natural_earth.txt" in manifests
    assert "organizations/company_terms_sec.txt" in manifests
    assert "categories/abstract_group_labels.txt" in manifests
    assert "categories/priority_labels.txt" in manifests
    assert "categories/product_labels.txt" in manifests
    assert "categories/status_labels.txt" in manifests
    assert "occupations/occupations_bls_oews.txt" in manifests
    assert "industries/industries_bls_qcew.txt" in manifests
    assert "mixed/compact_labels.txt" in manifests

    for relative_path, manifest_info in manifests.items():
        path = root / str(relative_path)
        assert path.exists(), relative_path
        count = len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])
        assert count == int(manifest_info["count"])
        for source_id in manifest_info["sources"]:
            source_info = sources[str(source_id)]
            assert (root / str(source_info["local_license"])).exists()
            assert str(source_info["license"])


def test_load_label_manifest_filters_task_local_render_constraints() -> None:
    labels = load_label_manifest(
        "mixed/compact_labels.txt",
        min_chars=5,
        max_chars=10,
        allow_spaces=False,
        allow_punctuation=False,
    )

    assert len(labels) > 1000
    assert "James" in labels
    assert "New York" not in labels
    assert all(5 <= len(label) <= 10 for label in labels[:500])
    assert all(label.isascii() and label.isalnum() for label in labels[:500])


def test_filter_label_values_handles_spacing_and_punctuation() -> None:
    labels = filter_label_values(
        ("Alpha", "New York", "Beta-2", "Delta", "x"),
        min_chars=4,
        max_chars=8,
        allow_spaces=False,
        allow_punctuation=False,
    )

    assert labels == ("Alpha", "Delta")

    compact = filter_label_values(
        ("New York", "Los Angeles", "Delta"),
        min_chars=7,
        max_chars=8,
        allow_spaces=True,
        allow_punctuation=False,
        compact_length=True,
    )
    assert compact == ("New York",)


def test_label_asset_docs_exist() -> None:
    assert Path("assets/labels/README.md").exists()
    assert Path("docs/workflows/SHARED_LABEL_ASSETS.md").exists()
