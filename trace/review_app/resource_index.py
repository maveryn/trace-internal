"""Index non-task review resources under review/task-reviews/assets."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path


IMAGE_SUFFIXES = {".gif", ".jpg", ".jpeg", ".png", ".svg", ".webp"}
MANIFEST_SUFFIXES = {".json"}


@dataclass(frozen=True)
class ResourceAsset:
    """One resource file under the review asset root."""

    id: str
    category: str
    collection: str
    rel_path: str
    file_name: str
    kind: str
    path: Path


@dataclass
class ResourceCollection:
    """A folder of related review resources."""

    category: str
    collection: str
    rel_dir: str
    assets: list[ResourceAsset] = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.collection.replace("/", " / ").replace("_", " ")

    @property
    def image_assets(self) -> list[ResourceAsset]:
        return [asset for asset in self.assets if asset.kind == "image"]

    @property
    def manifest_assets(self) -> list[ResourceAsset]:
        return [asset for asset in self.assets if asset.kind == "manifest"]


@dataclass
class ResourceIndex:
    """Resource review index separate from domain task reviews."""

    root: Path
    assets_root: Path
    collections: list[ResourceCollection] = field(default_factory=list)
    assets: dict[str, ResourceAsset] = field(default_factory=dict)


def build_resource_index(review_root: Path | str) -> ResourceIndex:
    """Build a resource index from ``review/task-reviews/assets``."""

    root = Path(review_root).resolve()
    assets_root = root / "assets"
    index = ResourceIndex(root=root, assets_root=assets_root)
    if not assets_root.exists():
        return index

    collections: dict[tuple[str, str], ResourceCollection] = {}
    for path in sorted(candidate for candidate in assets_root.rglob("*") if candidate.is_file()):
        rel = path.relative_to(assets_root)
        if _is_hidden_path(rel):
            continue
        kind = _resource_kind(path)
        if kind is None:
            continue
        category, collection = _resource_group(rel)
        collection_key = (category, collection)
        record = collections.setdefault(
            collection_key,
            ResourceCollection(
                category=category,
                collection=collection,
                rel_dir=_collection_rel_dir(category, collection),
            ),
        )
        asset = ResourceAsset(
            id=_asset_id(rel.as_posix()),
            category=category,
            collection=collection,
            rel_path=rel.as_posix(),
            file_name=path.name,
            kind=kind,
            path=path,
        )
        record.assets.append(asset)
        index.assets[asset.id] = asset

    index.collections = [collections[key] for key in sorted(collections)]
    return index


def _resource_kind(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in MANIFEST_SUFFIXES:
        return "manifest"
    return None


def _resource_group(rel_path: Path) -> tuple[str, str]:
    parts = rel_path.parts
    category = parts[0] if parts else "uncategorized"
    collection_parts = parts[1:-1]
    collection = "/".join(collection_parts) if collection_parts else "root"
    return str(category), str(collection)


def _collection_rel_dir(category: str, collection: str) -> str:
    if collection == "root":
        return category
    return f"{category}/{collection}"


def _is_hidden_path(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def _asset_id(rel_path: str) -> str:
    return hashlib.sha256(f"resource:{rel_path}".encode("utf-8")).hexdigest()[:24]
