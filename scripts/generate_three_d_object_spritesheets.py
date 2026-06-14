#!/usr/bin/env python3
"""Generate review spritesheets for three_d-domain object profiles."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Sequence

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from trace.tasks.shared.text_rendering import load_font
from trace.tasks.three_d.shared.object_inventory_preview import (
    ObjectProfilePreview,
    render_three_d_object_profile_preview,
)
from trace.tasks.three_d.shared.object_resources import (
    OBJECT_CLUSTER_EXTRA_SHAPE_TYPES,
    ThreeDObjectProfile,
    object_profiles,
)


OUT_DIR = Path("review/task-reviews/assets/three_d/object_spritesheets")
TILE_W = 268
TILE_H = 242
HEADER_H = 84
PREVIEW_W = 218
PREVIEW_H = 142
CANVAS_BG = (244, 246, 245)
PANEL_BG = (255, 255, 252)
PANEL_OUTLINE = (203, 210, 211)
TEXT = (35, 42, 48)
MUTED = (91, 103, 111)
BADGE_BG = (231, 238, 239)
BADGE_OUTLINE = (180, 194, 199)


def _font(size: int, *, bold: bool = False):
    return load_font(int(size), bold=bool(bold))


def _text_size(draw: ImageDraw.ImageDraw, text: str, *, size: int, bold: bool = False) -> tuple[float, float]:
    bbox = draw.textbbox((0, 0), str(text), font=_font(size, bold=bold))
    return float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])


def _ellipsize(draw: ImageDraw.ImageDraw, text: str, max_width: float, *, size: int, bold: bool = False) -> str:
    value = str(text)
    if _text_size(draw, value, size=size, bold=bold)[0] <= float(max_width):
        return value
    suffix = "..."
    trimmed = value
    while trimmed and _text_size(draw, trimmed + suffix, size=size, bold=bold)[0] > float(max_width):
        trimmed = trimmed[:-1]
    return (trimmed or value[:1]) + suffix


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: Sequence[float],
    text: str,
    *,
    size: int = 12,
    fill: tuple[int, int, int] = TEXT,
    bold: bool = False,
) -> None:
    draw.text((float(xy[0]), float(xy[1])), str(text), font=_font(size, bold=bold), fill=fill)


def _center_text(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    text: str,
    *,
    size: int = 12,
    fill: tuple[int, int, int] = TEXT,
    bold: bool = False,
) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    label = _ellipsize(draw, str(text), max(4.0, x1 - x0 - 8.0), size=size, bold=bold)
    text_w, text_h = _text_size(draw, label, size=size, bold=bold)
    _draw_text(
        draw,
        (x0 + (x1 - x0 - text_w) * 0.5, y0 + (y1 - y0 - text_h) * 0.5),
        label,
        size=size,
        fill=fill,
        bold=bold,
    )


def _fit_image(image: Image.Image, *, max_width: int, max_height: int) -> Image.Image:
    copy = image.convert("RGB")
    scale = min(float(max_width) / float(max(1, copy.width)), float(max_height) / float(max(1, copy.height)))
    width = max(1, int(round(float(copy.width) * float(scale))))
    height = max(1, int(round(float(copy.height) * float(scale))))
    return copy.resize((width, height), Image.Resampling.LANCZOS)


def _render_preview(profile: ThreeDObjectProfile, *, index: int, crop_to_object: bool = True) -> ObjectProfilePreview:
    return render_three_d_object_profile_preview(
        profile,
        canvas_width=440,
        canvas_height=340,
        instance_seed=9173 + int(index) * 37,
        crop_to_object=bool(crop_to_object),
        crop_padding_px=24,
    )


def _draw_profile_tile(
    draw: ImageDraw.ImageDraw,
    canvas: Image.Image,
    *,
    profile: ThreeDObjectProfile,
    preview: ObjectProfilePreview,
    index: int,
    col: int,
    row: int,
) -> None:
    x = int(col) * TILE_W
    y = HEADER_H + int(row) * TILE_H
    panel = (x + 10, y + 10, x + TILE_W - 10, y + TILE_H - 10)
    draw.rounded_rectangle(panel, radius=9, fill=PANEL_BG, outline=PANEL_OUTLINE, width=1)

    badge_text = f"{profile.source_scene} / {profile.size_class}"
    badge = (panel[0] + 10, panel[1] + 9, panel[2] - 10, panel[1] + 31)
    draw.rounded_rectangle(badge, radius=5, fill=BADGE_BG, outline=BADGE_OUTLINE, width=1)
    _center_text(draw, badge, badge_text, size=10, fill=(49, 66, 74), bold=True)

    image_area = (panel[0] + 15, panel[1] + 39, panel[2] - 15, panel[1] + 39 + PREVIEW_H)
    fitted = _fit_image(preview.image, max_width=PREVIEW_W, max_height=PREVIEW_H)
    px = int(round((image_area[0] + image_area[2] - fitted.width) * 0.5))
    py = int(round((image_area[1] + image_area[3] - fitted.height) * 0.5))
    canvas.paste(fitted, (px, py))

    draw.rectangle((image_area[0], image_area[1], image_area[2], image_area[3]), outline=(226, 230, 230), width=1)
    _center_text(draw, (panel[0] + 8, panel[3] - 50, panel[2] - 8, panel[3] - 31), profile.display_name, size=13, fill=TEXT, bold=True)
    _center_text(draw, (panel[0] + 8, panel[3] - 31, panel[2] - 8, panel[3] - 15), profile.object_type, size=10, fill=MUTED)
    _center_text(draw, (panel[0] + 8, panel[3] - 16, panel[2] - 8, panel[3] - 3), profile.role, size=8, fill=(111, 122, 130))


def _make_sheet(
    filename: str,
    *,
    title: str,
    subtitle: str,
    profiles: Sequence[ThreeDObjectProfile],
    cols: int,
    start_index: int,
) -> Dict[str, Any]:
    rows = max(1, (len(profiles) + int(cols) - 1) // int(cols))
    width = int(cols) * TILE_W
    height = HEADER_H + rows * TILE_H
    canvas = Image.new("RGB", (width, height), CANVAS_BG)
    draw = ImageDraw.Draw(canvas)
    _draw_text(draw, (22, 16), title, size=24, fill=TEXT, bold=True)
    _draw_text(draw, (22, 49), subtitle, size=12, fill=MUTED)

    profile_records: List[Dict[str, Any]] = []
    failures: List[Dict[str, str]] = []
    for local_index, profile in enumerate(profiles):
        global_index = int(start_index) + int(local_index)
        try:
            preview = _render_preview(profile, index=global_index)
        except Exception as exc:  # pragma: no cover - review asset fallback
            failures.append(
                {
                    "profile_id": str(profile.profile_id),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            continue
        col = local_index % int(cols)
        row = local_index // int(cols)
        _draw_profile_tile(draw, canvas, profile=profile, preview=preview, index=global_index, col=col, row=row)
        profile_records.append(
            {
                "profile_id": str(profile.profile_id),
                "canonical_id": str(profile.canonical_id),
                "source_scene": str(profile.source_scene),
                "role": str(profile.role),
                "object_type": str(profile.object_type),
                "display_name": str(profile.display_name),
                "size_class": str(profile.size_class),
                "renderer": str(profile.renderer),
                "resource_kind": str(profile.resource_kind),
                "support_required": bool(profile.support_required),
                "mounting": profile.mounting,
                "dimensions_xyz": list(profile.dimensions_xyz or ()),
                "preview_metadata": dict(preview.metadata),
            }
        )

    output_path = OUT_DIR / filename
    canvas.save(output_path)
    return {
        "file": str(output_path.as_posix()),
        "title": str(title),
        "item_count": int(len(profiles)),
        "rendered_count": int(len(profile_records)),
        "failure_count": int(len(failures)),
        "profiles": profile_records,
        "failures": failures,
    }


def _scene_profiles(scene_id: str) -> List[ThreeDObjectProfile]:
    return sorted(object_profiles(source_scene=str(scene_id)), key=lambda profile: (profile.role, profile.display_name, profile.object_type))


def _build_sheet_specs() -> List[Dict[str, Any]]:
    object_small = sorted(
        object_profiles(source_scene="object_scene", role="spatial_small_shape"),
        key=lambda profile: (profile.display_name, profile.object_type),
    )
    object_context = sorted(
        object_profiles(source_scene="object_scene", role="spatial_context_shape"),
        key=lambda profile: (profile.display_name, profile.object_type),
    )
    cluster_pool = sorted(
        object_profiles(source_scene="object_cluster", role="cluster_small_shape"),
        key=lambda profile: (profile.display_name, profile.object_type),
    )
    cluster_extra_types = {str(value) for value in OBJECT_CLUSTER_EXTRA_SHAPE_TYPES}
    cluster_extra = tuple(profile for profile in cluster_pool if str(profile.object_type) in cluster_extra_types)
    room_profiles = _scene_profiles("room")
    room_wall = tuple(profile for profile in room_profiles if profile.role == "room_wall_object")
    room_surface = tuple(profile for profile in room_profiles if profile.role == "room_surface_variant")
    room_floor_props = tuple(profile for profile in room_profiles if profile.role == "room_floor_prop")
    room_floor_variants = tuple(profile for profile in room_profiles if profile.role == "room_floor_variant")
    street_profiles = _scene_profiles("street")
    street_candidates = tuple(profile for profile in street_profiles if profile.role == "street_candidate")
    street_context = tuple(profile for profile in street_profiles if profile.role == "street_context")
    surface_fixture_profiles = _scene_profiles("surface_fixture")
    warehouse_profiles = _scene_profiles("warehouse")
    start_index = 0
    specs: List[Dict[str, Any]] = [
        {
            "filename": "00_object_scene_all_small_shapes.png",
            "title": "Object Scene Small Object Pool",
            "subtitle": f"All {len(object_small)} small candidate/profile objects, sorted by display name.",
            "profiles": tuple(object_small),
            "cols": 8,
            "start_index": start_index,
        }
    ]
    start_index += len(object_small)

    grouped_specs: List[tuple[str, str, str, Sequence[ThreeDObjectProfile], int]] = [
        (
            "01_object_scene_large_context_shapes.png",
            "Object Scene Large Context Object Pool",
            "Large/reference/support objects for object_scene tasks.",
            object_context,
            4,
        ),
        (
            "02_object_cluster_all_countable_objects.png",
            "Object Cluster Countable Object Pool",
            f"All {len(cluster_pool)} object types sampled by object_cluster instance-count tasks.",
            cluster_pool,
            8,
        ),
        (
            "03_object_cluster_extra_countqa_objects.png",
            "Object Cluster CountQA Additions",
            f"The {len(cluster_extra)} cluster-specific object types added for dense counting coverage.",
            cluster_extra,
            5,
        ),
        (
            "04_room_wall_objects.png",
            "Room Wall Object Pool",
            "Wall-mounted room objects and wall decor variants.",
            room_wall,
            4,
        ),
        (
            "05_room_surface_variants.png",
            "Room Surface Object Variants",
            "Small room objects rendered on furniture supports.",
            room_surface,
            4,
        ),
        (
            "06_room_floor_props.png",
            "Room Floor Prop Pool",
            "Furniture and large floor props used by room scenes.",
            room_floor_props,
            4,
        ),
        (
            "07_room_floor_variants.png",
            "Room Floor Object Variants",
            "Floor-standing variants of normally wall-mounted room objects.",
            room_floor_variants,
            4,
        ),
        (
            "08_street_candidate_objects.png",
            "Street Candidate Object Pool",
            "Answerable street objects that may be lettered or queried; excludes scene context such as buildings and greenery.",
            street_candidates,
            4,
        ),
        (
            "09_street_context_objects.png",
            "Street Context Object Pool",
            "Non-answerable street scene context such as buildings, signs, benches, traffic lights, trees, and shrubs.",
            street_context,
            4,
        ),
        (
            "10_warehouse_objects.png",
            "Warehouse Object Pool",
            "Robots, racks, reference objects, and warehouse equipment.",
            warehouse_profiles,
            4,
        ),
        (
            "11_surface_fixture_variants.png",
            "Surface Fixture Variant Pool",
            "Repeated mounted surface elements and panel variants used by surface_fixture tasks.",
            surface_fixture_profiles,
            5,
        ),
    ]
    for filename, title, subtitle, selected, cols in grouped_specs:
        specs.append(
            {
                "filename": filename,
                "title": title,
                "subtitle": subtitle,
                "profiles": tuple(selected),
                "cols": cols,
                "start_index": start_index,
            }
        )
        start_index += len(tuple(selected))
    return specs


def _write_readme(sheet_records: Sequence[Mapping[str, Any]]) -> None:
    lines = [
        "# Three-D Object Spritesheets",
        "",
        "Generated review previews for canonical `three_d` object profiles.",
        "",
        "Each tile shows one object rendered through its native scene adapter, with the source scene, size class, display name, object type, and profile role.",
        "",
        "Files:",
    ]
    for record in sheet_records:
        lines.append(f"- `{Path(str(record['file'])).name}`: {record['rendered_count']} rendered profiles")
    lines.extend(
        [
            "",
            "Manifest: `object_profile_preview_manifest.json`.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def _clear_existing_outputs() -> None:
    for path in OUT_DIR.glob("*.png"):
        path.unlink()
    for filename in ("README.md", "object_profile_preview_manifest.json"):
        path = OUT_DIR / filename
        if path.exists():
            path.unlink()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _clear_existing_outputs()
    sheet_records = [_make_sheet(**spec) for spec in _build_sheet_specs()]
    all_failures = [failure for record in sheet_records for failure in record.get("failures", [])]
    manifest = {
        "domain": "three_d",
        "profile_count": int(len(object_profiles())),
        "sheet_count": int(len(sheet_records)),
        "rendered_count": int(sum(int(record.get("rendered_count", 0)) for record in sheet_records)),
        "failure_count": int(len(all_failures)),
        "sheets": sheet_records,
        "failures": all_failures,
    }
    (OUT_DIR / "object_profile_preview_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    _write_readme(sheet_records)
    for record in sheet_records:
        print(f"[wrote] {record['file']} ({record['rendered_count']} profiles)")
    print(f"[done] wrote {OUT_DIR / 'object_profile_preview_manifest.json'}")
    if all_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
