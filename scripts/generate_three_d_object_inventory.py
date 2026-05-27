#!/usr/bin/env python
"""Generate TRACE three_d named-object inventory sheets."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from trace.tasks.three_d.shared.object_inventory_preview import render_three_d_object_profile_preview
from trace.tasks.three_d.shared.object_resources import THREE_D_OBJECT_PROFILES, ThreeDObjectProfile


DEFAULT_OUTPUT_DIR = Path("plans/task-reviews/three_d/named_object_inventory")
DEFAULT_COLUMNS = 8
DEFAULT_SHEET_WIDTH = 3026


def _load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    font_name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/{font_name}", int(size))
    except OSError:
        return ImageFont.load_default()


def _fit_image(image: Image.Image, *, max_width: int, max_height: int) -> Image.Image:
    scale = min(
        float(max_width) / float(max(1, image.width)),
        float(max_height) / float(max(1, image.height)),
        2.8,
    )
    size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def _wrapped_lines(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = str(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= int(max_width):
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines[:2]


def _profile_dict(profile: ThreeDObjectProfile) -> dict[str, Any]:
    data = asdict(profile)
    if data.get("dimensions_xyz") is not None:
        data["dimensions_xyz"] = [float(value) for value in data["dimensions_xyz"]]
    return data


def _fallback_preview(error: str, *, width: int = 420, height: int = 330) -> Image.Image:
    image = Image.new("RGB", (int(width), int(height)), (248, 241, 235))
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        (70, 72, int(width) - 70, int(height) - 92),
        fill=(210, 218, 225),
        outline=(86, 96, 110),
        width=3,
    )
    draw.line((90, 92, int(width) - 90, int(height) - 112), fill=(120, 130, 144), width=2)
    font = _load_font(16, bold=True)
    draw.text((28, int(height) - 54), "render error", fill=(96, 42, 42), font=font)
    draw.text((28, int(height) - 34), str(error)[:48], fill=(96, 42, 42), font=_load_font(12))
    return image


def _render_preview_for_sheet(
    profile: ThreeDObjectProfile,
    *,
    canvas_width: int,
    canvas_height: int,
    instance_seed: int,
) -> tuple[Image.Image, dict[str, Any], str | None]:
    try:
        preview = render_three_d_object_profile_preview(
            profile,
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            instance_seed=int(instance_seed),
            crop_to_object=True,
            crop_padding_px=18,
        )
        return preview.image, dict(preview.metadata), None
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        return _fallback_preview(error, width=int(canvas_width), height=int(canvas_height)), {}, error


def _make_sheet(
    *,
    title: str,
    profiles: Sequence[ThreeDObjectProfile],
    path: Path,
    columns: int,
    sheet_width: int,
    instance_seed: int,
    canvas_width: int,
    canvas_height: int,
) -> dict[str, Any]:
    title_height = 68
    margin = 18
    gutter = 10
    width = int(sheet_width)
    cell_width = max(180, int((int(width) - margin * 2 - (int(columns) - 1) * gutter) / int(columns)))
    cell_height = max(224, int(round(float(cell_width) * 0.84)))
    preview_height = max(154, int(cell_height) - 70)
    rows = max(1, math.ceil(len(profiles) / int(columns)))
    height = title_height + margin + rows * cell_height + (rows - 1) * gutter
    sheet = Image.new("RGB", (width, height), (252, 252, 250))
    draw = ImageDraw.Draw(sheet)
    title_font = _load_font(28, bold=True)
    label_font = _load_font(16, bold=True)
    meta_font = _load_font(12)
    draw.text((margin, 20), str(title), fill=(28, 34, 44), font=title_font)
    draw.text((margin, 48), f"{len(profiles)} profiles | {int(columns)} per row", fill=(80, 88, 98), font=meta_font)

    errors: list[dict[str, str]] = []
    profile_previews: dict[str, dict[str, Any]] = {}
    for index, profile in enumerate(profiles):
        row, col = divmod(int(index), int(columns))
        x = margin + col * (cell_width + gutter)
        y = title_height + row * (cell_height + gutter)
        draw.rounded_rectangle(
            (x, y, x + cell_width, y + cell_height),
            radius=8,
            fill=(244, 246, 245),
            outline=(204, 210, 216),
            width=1,
        )
        preview_image, preview_metadata, error = _render_preview_for_sheet(
            profile,
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            instance_seed=int(instance_seed),
        )
        if error is not None:
            errors.append({"profile_id": str(profile.profile_id), "error": str(error)})
        profile_previews[str(profile.profile_id)] = dict(preview_metadata)
        preview_image = _fit_image(preview_image, max_width=cell_width - 34, max_height=preview_height - 12)
        px = x + (cell_width - preview_image.width) // 2
        py = y + 12 + (preview_height - preview_image.height) // 2
        sheet.paste(preview_image, (px, py))

        label_y = y + preview_height + 12
        for line in _wrapped_lines(profile.display_name, label_font, cell_width - 20, draw):
            text_width = draw.textbbox((0, 0), line, font=label_font)[2]
            draw.text((x + (cell_width - text_width) / 2, label_y), line, fill=(24, 30, 38), font=label_font)
            label_y += 18

        meta = f"{profile.object_type} | {profile.source_scene.replace('_3d', '')}"
        if len(meta) > 36:
            meta = f"{meta[:33]}..."
        meta_width = draw.textbbox((0, 0), meta, font=meta_font)[2]
        draw.text((x + (cell_width - meta_width) / 2, y + cell_height - 24), meta, fill=(90, 98, 108), font=meta_font)

    sheet.save(path)
    return {
        "title": str(title),
        "path": str(path),
        "columns": int(columns),
        "rows": int(rows),
        "width": int(width),
        "height": int(height),
        "cell_width": int(cell_width),
        "cell_height": int(cell_height),
        "preview_height": int(preview_height),
        "profile_count": int(len(profiles)),
        "render_error_count": int(len(errors)),
        "render_errors": list(errors),
        "profile_previews": dict(profile_previews),
    }


def _sorted_profiles(profiles: Iterable[ThreeDObjectProfile]) -> list[ThreeDObjectProfile]:
    return sorted(
        list(profiles),
        key=lambda profile: (
            profile.size_class != "small",
            profile.display_name.lower(),
            profile.source_scene,
            profile.role,
            profile.object_type,
        ),
    )


def _write_manifest(path: Path, *, profiles: Sequence[ThreeDObjectProfile], sheets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    render_errors = [error for sheet in sheets for error in sheet.get("render_errors", [])]
    manifest = {
        "profile_count": int(len(profiles)),
        "counts_by_size_class": dict(Counter(profile.size_class for profile in profiles)),
        "counts_by_resource_kind": dict(Counter(profile.resource_kind for profile in profiles)),
        "counts_by_source_scene": dict(Counter(profile.source_scene for profile in profiles)),
        "counts_by_renderer": dict(Counter(profile.renderer for profile in profiles)),
        "render_error_count": int(len(render_errors)),
        "render_errors": list(render_errors),
        "profiles": [_profile_dict(profile) for profile in _sorted_profiles(profiles)],
        "sheets": [dict(sheet) for sheet in sheets],
    }
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def generate_inventory(
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    columns: int = DEFAULT_COLUMNS,
    sheet_width: int = DEFAULT_SHEET_WIDTH,
    instance_seed: int = 0,
    canvas_width: int = 420,
    canvas_height: int = 330,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    profiles = list(THREE_D_OBJECT_PROFILES)
    sorted_profiles = _sorted_profiles(profiles)
    small_profiles = [profile for profile in sorted_profiles if profile.size_class == "small"]
    large_profiles = [profile for profile in sorted_profiles if profile.size_class == "large"]
    special_profiles = [profile for profile in sorted_profiles if profile.resource_kind != "standalone"]
    sheets = [
        _make_sheet(
            title="TRACE 3D Named Small Objects",
            profiles=small_profiles,
            path=output_dir / "three_d_named_small_objects.png",
            columns=int(columns),
            sheet_width=int(sheet_width),
            instance_seed=int(instance_seed),
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
        ),
        _make_sheet(
            title="TRACE 3D Named Large Objects",
            profiles=large_profiles,
            path=output_dir / "three_d_named_large_objects.png",
            columns=int(columns),
            sheet_width=int(sheet_width),
            instance_seed=int(instance_seed),
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
        ),
        _make_sheet(
            title="TRACE 3D Mounted, Composite, Variant, and Reference Objects",
            profiles=special_profiles,
            path=output_dir / "three_d_named_mounted_composite_variant_objects.png",
            columns=int(columns),
            sheet_width=int(sheet_width),
            instance_seed=int(instance_seed),
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
        ),
    ]
    return _write_manifest(output_dir / "manifest.json", profiles=profiles, sheets=sheets)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--columns", type=int, default=DEFAULT_COLUMNS)
    parser.add_argument("--sheet-width", type=int, default=DEFAULT_SHEET_WIDTH)
    parser.add_argument("--instance-seed", type=int, default=0)
    parser.add_argument("--canvas-width", type=int, default=420)
    parser.add_argument("--canvas-height", type=int, default=330)
    parser.add_argument("--fail-on-render-error", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    manifest = generate_inventory(
        output_dir=Path(args.output_dir),
        columns=int(args.columns),
        sheet_width=int(args.sheet_width),
        instance_seed=int(args.instance_seed),
        canvas_width=int(args.canvas_width),
        canvas_height=int(args.canvas_height),
    )
    print(
        json.dumps(
            {
                "profile_count": manifest["profile_count"],
                "counts_by_size_class": manifest["counts_by_size_class"],
                "render_error_count": manifest["render_error_count"],
                "sheets": [
                    {
                        "path": sheet["path"],
                        "columns": sheet["columns"],
                        "rows": sheet["rows"],
                        "width": sheet["width"],
                        "height": sheet["height"],
                        "cell_width": sheet["cell_width"],
                        "cell_height": sheet["cell_height"],
                        "profile_count": sheet["profile_count"],
                        "render_error_count": sheet["render_error_count"],
                    }
                    for sheet in manifest["sheets"]
                ],
            },
            indent=2,
        )
    )
    if bool(args.fail_on_render_error) and int(manifest["render_error_count"]) > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
