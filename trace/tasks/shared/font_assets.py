"""Shared loader and deterministic sampler for vendored TRACE font assets."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence, Tuple

from ...core.seed import spawn_rng


REPO_ROOT = Path(__file__).resolve().parents[3]
FONT_ASSET_ROOT = REPO_ROOT / "assets" / "fonts"
SOURCES_PATH = FONT_ASSET_ROOT / "sources.json"


@dataclass(frozen=True)
class FontFamilyRecord:
    """One vendored font family and its regular/bold paths."""

    key: str
    family_name: str
    regular_path: str
    bold_path: str
    license: str
    license_path: str
    source_id: str
    source_url: str
    tags: Tuple[str, ...]

    def to_trace(self) -> dict[str, Any]:
        return {
            "font_family": str(self.key),
            "family_name": str(self.family_name),
            "license": str(self.license),
            "source_id": str(self.source_id),
            "source_url": str(self.source_url),
            "tags": [str(tag) for tag in self.tags],
        }


def _normalize_family_key(value: str) -> str:
    key = str(value).strip().casefold().replace("-", "_").replace(" ", "_")
    while "__" in key:
        key = key.replace("__", "_")
    return key.strip("_")


@lru_cache(maxsize=1)
def load_font_sources() -> Mapping[str, Any]:
    """Return the font source metadata payload."""

    payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"font source metadata must be a mapping: {SOURCES_PATH}")
    return payload


@lru_cache(maxsize=1)
def load_font_family_records() -> Mapping[str, FontFamilyRecord]:
    """Return all vendored font family records keyed by normalized family id."""

    payload = load_font_sources()
    families = payload.get("families", {})
    if not isinstance(families, Mapping):
        raise ValueError("font sources payload must contain a family mapping")
    records: dict[str, FontFamilyRecord] = {}
    for raw_key, raw_record in families.items():
        if not isinstance(raw_record, Mapping):
            continue
        key = _normalize_family_key(str(raw_key))
        regular_path = str(raw_record.get("regular_path", ""))
        bold_path = str(raw_record.get("bold_path", regular_path))
        if not regular_path:
            continue
        records[key] = FontFamilyRecord(
            key=str(key),
            family_name=str(raw_record.get("family_name", key)),
            regular_path=str(regular_path),
            bold_path=str(bold_path or regular_path),
            license=str(raw_record.get("license", "")),
            license_path=str(raw_record.get("license_path", "")),
            source_id=str(raw_record.get("source_id", "")),
            source_url=str(raw_record.get("source_url", "")),
            tags=tuple(str(tag) for tag in raw_record.get("tags", ())),
        )
    if not records:
        raise ValueError(f"no font family records found in {SOURCES_PATH}")
    return records


def list_font_families(
    *,
    include_tags: Sequence[str] | None = None,
    exclude_tags: Sequence[str] | None = None,
) -> Tuple[str, ...]:
    """Return font family keys filtered by optional tag constraints."""

    include = {str(tag) for tag in include_tags or ()}
    exclude = {str(tag) for tag in exclude_tags or ()}
    candidates: list[str] = []
    for key, record in load_font_family_records().items():
        tags = set(record.tags)
        if include and not bool(tags & include):
            continue
        if exclude and bool(tags & exclude):
            continue
        candidates.append(str(key))
    return tuple(sorted(candidates))


def get_font_family_record(font_family: str) -> FontFamilyRecord:
    """Return one font family record by normalized key."""

    key = _normalize_family_key(str(font_family))
    records = load_font_family_records()
    if key not in records:
        raise KeyError(f"unknown font family: {font_family!r}")
    return records[key]


def resolve_font_paths(font_family: str, *, bold: bool) -> Tuple[Path, ...]:
    """Return preferred local font paths for one family/style."""

    record = get_font_family_record(str(font_family))
    primary = record.bold_path if bool(bold) else record.regular_path
    fallback = record.regular_path if bool(bold) else record.bold_path
    paths = []
    for relative_path in (primary, fallback):
        if not relative_path:
            continue
        full_path = FONT_ASSET_ROOT / str(relative_path)
        if full_path.exists() and full_path not in paths:
            paths.append(full_path)
    return tuple(paths)


def _weighted_choice(rng: random.Random, weighted: Mapping[str, float], *, fallback: Sequence[str]) -> str:
    candidates: list[tuple[str, float]] = []
    for key, value in weighted.items():
        try:
            weight = float(value)
        except Exception:
            continue
        if weight > 0:
            candidates.append((str(key), float(weight)))
    if not candidates:
        candidates = [(str(key), 1.0) for key in fallback]
    total = sum(weight for _, weight in candidates)
    cursor = rng.random() * float(total)
    running = 0.0
    for key, weight in candidates:
        running += float(weight)
        if cursor <= running:
            return str(key)
    return str(candidates[-1][0])


def sample_font_family(
    *,
    instance_seed: int,
    namespace: str,
    params: Mapping[str, Any] | None = None,
    include_tags: Sequence[str] | None = None,
    exclude_tags: Sequence[str] | None = None,
    explicit_key: str = "font_family",
    weights_key: str = "font_family_weights",
) -> str:
    """Sample one vendored font family deterministically from seed/namespace.

    The selected family is a render-style decision and must be recorded by the
    caller in trace metadata for any answer-bearing text.
    """

    resolved_params = params or {}
    explicit = resolved_params.get(str(explicit_key))
    candidates = list_font_families(include_tags=include_tags, exclude_tags=exclude_tags)
    if not candidates:
        candidates = list_font_families()
    candidate_set = set(candidates)
    if explicit is not None:
        key = _normalize_family_key(str(explicit))
        if key not in candidate_set:
            raise ValueError(f"font family {explicit!r} is not available for this text role")
        return str(key)
    raw_weights = resolved_params.get(str(weights_key), {})
    weights: dict[str, float] = {}
    if isinstance(raw_weights, Mapping):
        for key, value in raw_weights.items():
            normalized = _normalize_family_key(str(key))
            if normalized in candidate_set:
                try:
                    weights[str(normalized)] = float(value)
                except Exception:
                    continue
    rng = spawn_rng(int(instance_seed), str(namespace))
    return _weighted_choice(rng, weights, fallback=tuple(candidates))


def font_asset_version() -> str:
    """Return the current font asset version string."""

    payload = load_font_sources()
    return str(payload.get("asset_version", ""))


__all__ = [
    "FONT_ASSET_ROOT",
    "FontFamilyRecord",
    "font_asset_version",
    "get_font_family_record",
    "list_font_families",
    "load_font_family_records",
    "load_font_sources",
    "resolve_font_paths",
    "sample_font_family",
]
