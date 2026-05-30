"""Canonical task-review artifact path helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .taxonomy import TaxonomyEntry, resolve_task_taxonomy


_PUBLIC_TASK_ID_RE = re.compile(r"^task_(?P<domain>[a-z0-9_]+?)__(?P<scene>[a-z0-9_]+?)__")
_LEGACY_TASK_DOMAIN_RE = re.compile(r"^task_(?P<domain>[a-z0-9]+)_")


def _source_domain(task_obj: Any | None, source_domain: str = "") -> str:
    if task_obj is None:
        return str(source_domain or "")
    return str(source_domain or getattr(task_obj, "domain", "") or "")


def _source_task_group(task_obj: Any | None, source_task_group: str = "") -> str:
    if task_obj is None:
        return str(source_task_group or "")
    return str(source_task_group or getattr(task_obj, "task_group", "") or "")


def _public_task_id_parts(task_id: str) -> tuple[str, str] | None:
    match = _PUBLIC_TASK_ID_RE.match(str(task_id).strip())
    if match is None:
        return None
    return str(match.group("domain")), str(match.group("scene"))


def resolve_review_task_taxonomy(
    task_id: str,
    *,
    task_obj: Any | None = None,
    source_domain: str = "",
    source_task_group: str = "",
) -> TaxonomyEntry:
    """Resolve review-facing taxonomy for one task id.

    Known public task ids use the canonical taxonomy table. Unknown/test task
    ids may still follow ``task_<domain>__<scene>__...``; those are routed by
    their public id parts so review artifacts do not collapse under
    ``unknown/unknown``.
    """

    resolved = resolve_task_taxonomy(
        str(task_id),
        source_domain=_source_domain(task_obj, source_domain),
        source_task_group=_source_task_group(task_obj, source_task_group),
    )
    if resolved.domain != "unknown" and resolved.scene_id != "unknown":
        return resolved

    public_parts = _public_task_id_parts(str(task_id))
    if public_parts is None:
        return resolved

    public_domain, public_scene = public_parts
    domain = str(resolved.domain if resolved.domain != "unknown" else public_domain)
    scene_id = str(resolved.scene_id if resolved.scene_id != "unknown" else public_scene)
    source_domain_value = str(resolved.source_domain if resolved.source_domain != "unknown" else domain)
    source_group_value = str(resolved.source_task_group if resolved.source_task_group != "unknown" else scene_id)
    return TaxonomyEntry(
        domain=domain,
        scene_id=scene_id,
        source_domain=source_domain_value,
        source_task_group=source_group_value,
    )


def infer_task_domain(task_id: str, *, task_obj: Any | None = None) -> str:
    """Infer one task domain for review-artifact routing."""

    taxonomy = resolve_review_task_taxonomy(str(task_id), task_obj=task_obj)
    if taxonomy.domain != "unknown":
        return str(taxonomy.domain)
    legacy_match = _LEGACY_TASK_DOMAIN_RE.match(str(task_id).strip())
    if legacy_match is not None:
        return str(legacy_match.group("domain"))
    return "unknown"


def resolve_task_review_dir(*, out_root: Path, task_id: str, task_obj: Any | None = None) -> Path:
    """Return the canonical ``domain/scene/task_id`` review directory."""

    taxonomy = resolve_review_task_taxonomy(str(task_id), task_obj=task_obj)
    return Path(out_root) / str(taxonomy.domain) / str(taxonomy.scene_id) / str(task_id)


def task_review_dir(
    *,
    out_root: Path,
    task_id: str,
    domain: str = "",
    scene_id: str = "",
    task_obj: Any | None = None,
) -> Path:
    """Return the review directory for one task with optional source hints."""

    taxonomy = resolve_review_task_taxonomy(
        str(task_id),
        task_obj=task_obj,
        source_domain=str(domain),
        source_task_group=str(scene_id),
    )
    return Path(out_root) / str(taxonomy.domain) / str(taxonomy.scene_id) / str(task_id)


__all__ = [
    "infer_task_domain",
    "resolve_review_task_taxonomy",
    "resolve_task_review_dir",
    "task_review_dir",
]
