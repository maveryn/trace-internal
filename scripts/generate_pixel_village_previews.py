#!/usr/bin/env python3
"""Generate procedural pixel-village prototype scenes for review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import types
from typing import Sequence

from PIL import Image, ImageDraw


def _install_trace_tasks_namespace() -> None:
    if "trace.tasks" in sys.modules:
        return
    repo_root = Path(__file__).resolve().parents[1]
    tasks_module = types.ModuleType("trace.tasks")
    tasks_module.__path__ = [str(repo_root / "trace" / "tasks")]  # type: ignore[attr-defined]
    sys.modules["trace.tasks"] = tasks_module


_install_trace_tasks_namespace()

from trace.tasks.illustrations.shared.pixel_village_rendering import (  # noqa: E402
    draw_pixel_village_debug_overlay,
    render_pixel_village_map,
)


DEFAULT_OUT_DIR = Path("review/task-reviews/assets/illustrations/pixel_village_map")


def _fit(image: Image.Image, *, max_w: int, max_h: int) -> Image.Image:
    fitted = image.copy()
    fitted.thumbnail((int(max_w), int(max_h)), Image.Resampling.NEAREST)
    return fitted


def _make_contact_sheet(image_paths: Sequence[Path], output_path: Path, *, columns: int = 3) -> None:
    thumbs: list[Image.Image] = []
    for path in image_paths:
        thumbs.append(_fit(Image.open(path).convert("RGB"), max_w=360, max_h=270))
    if not thumbs:
        return
    tile_w = 380
    tile_h = 306
    rows = (len(thumbs) + int(columns) - 1) // int(columns)
    sheet = Image.new("RGB", (int(columns) * tile_w, rows * tile_h), (238, 238, 222))
    draw = ImageDraw.Draw(sheet)
    for index, thumb in enumerate(thumbs):
        row, col = divmod(index, int(columns))
        x = col * tile_w
        y = row * tile_h
        draw.rectangle((x + 8, y + 8, x + tile_w - 8, y + tile_h - 8), fill=(255, 255, 238), outline=(190, 190, 174))
        sheet.paste(thumb, (x + (tile_w - thumb.width) // 2, y + 16))
        draw.text((x + 16, y + tile_h - 26), f"pixel village {index:02d}", fill=(45, 48, 54))
    sheet.save(output_path)


def _make_theme_comparison_sheet(image_paths: Sequence[Path], output_path: Path) -> None:
    thumbs: list[Image.Image] = []
    for path in image_paths:
        thumbs.append(_fit(Image.open(path).convert("RGB"), max_w=760, max_h=300))
    if not thumbs:
        return
    tile_w = 800
    tile_h = 340
    sheet = Image.new("RGB", (tile_w, len(thumbs) * tile_h), (238, 238, 222))
    draw = ImageDraw.Draw(sheet)
    for index, thumb in enumerate(thumbs):
        y = index * tile_h
        draw.rectangle((8, y + 8, tile_w - 8, y + tile_h - 8), fill=(255, 255, 238), outline=(190, 190, 174))
        sheet.paste(thumb, ((tile_w - thumb.width) // 2, y + 16))
        draw.text((18, y + tile_h - 26), f"season comparison {index:02d}", fill=(45, 48, 54))
    sheet.save(output_path)


def _side_by_side(left: Image.Image, right: Image.Image, *, label_left: str, label_right: str) -> Image.Image:
    gap = 20
    label_h = 22
    width = left.width + right.width + gap
    height = max(left.height, right.height) + label_h
    image = Image.new("RGB", (width, height), (238, 238, 222))
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), label_left, fill=(45, 48, 54))
    draw.text((left.width + gap, 0), label_right, fill=(45, 48, 54))
    image.paste(left.convert("RGB"), (0, label_h))
    image.paste(right.convert("RGB"), (left.width + gap, label_h))
    return image


def _theme_strip(items: Sequence[tuple[str, Image.Image]]) -> Image.Image:
    gap = 18
    label_h = 22
    width = sum(image.width for _, image in items) + gap * max(0, len(items) - 1)
    height = max(image.height for _, image in items) + label_h
    strip = Image.new("RGB", (width, height), (238, 238, 222))
    draw = ImageDraw.Draw(strip)
    x = 0
    for label, image in items:
        draw.text((x, 0), str(label), fill=(45, 48, 54))
        strip.paste(image.convert("RGB"), (x, label_h))
        x += image.width + gap
    return strip


def generate_previews(*, out_dir: Path, count: int, seed: int, width: int, height: int) -> None:
    images_dir = out_dir / "images"
    overlays_dir = out_dir / "overlays"
    data_dir = out_dir / "data"
    for directory in (images_dir, overlays_dir, data_dir):
        directory.mkdir(parents=True, exist_ok=True)

    image_paths: list[Path] = []
    overlay_paths: list[Path] = []
    records: list[dict] = []
    territory_modes = [
        ("force", "none", "none"),
        ("none", "force", "none"),
        ("none", "none", "force"),
        ("force", "force", "force"),
        ("none", "none", "none"),
    ]
    for index in range(int(count)):
        scene_seed = int(seed) + index
        cemetery_mode, orchard_mode, windmill_mode = territory_modes[index % len(territory_modes)]
        scene = render_pixel_village_map(
            scene_seed,
            width=int(width),
            height=int(height),
            cemetery_mode=cemetery_mode,
            orchard_mode=orchard_mode,
            windmill_mode=windmill_mode,
        )
        image_path = images_dir / f"{index:04d}.png"
        overlay_path = overlays_dir / f"{index:04d}_overlay.png"
        data_path = data_dir / f"{index:04d}.json"
        scene.image.save(image_path)
        draw_pixel_village_debug_overlay(scene).save(overlay_path)
        data_path.write_text(json.dumps(scene.trace, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        image_paths.append(image_path)
        overlay_paths.append(overlay_path)
        records.append(
            {
                "index": int(index),
                "seed": int(scene_seed),
                "image": str(image_path),
                "overlay": str(overlay_path),
                "data": str(data_path),
                "grid_cols": int(scene.trace["grid_cols"]),
                "grid_rows": int(scene.trace["grid_rows"]),
                "tile_px": int(scene.trace["tile_px"]),
                "map_size_px": list(scene.trace["map_size_px"]),
                "entity_count": int(scene.trace["entity_count"]),
                "territory_count": int(scene.trace["territory_count"]),
                "cemetery_mode": str(scene.trace["cemetery_mode"]),
                "cemetery_present": bool(scene.trace["cemetery_present"]),
                "cemetery_grave_marker_count": int(scene.trace["cemetery_grave_marker_count"]),
                "orchard_mode": str(scene.trace["orchard_mode"]),
                "orchard_present": bool(scene.trace["orchard_present"]),
                "orchard_tree_count": int(scene.trace["orchard_tree_count"]),
                "windmill_mode": str(scene.trace["windmill_mode"]),
                "windmill_present": bool(scene.trace["windmill_present"]),
                "theme_mode": str(scene.trace["theme_mode"]),
                "theme_id": str(scene.trace["theme_id"]),
                "snow_intensity": str(scene.trace["snow_intensity"]),
                "autumn_intensity": str(scene.trace["autumn_intensity"]),
                "category_counts": dict(scene.trace["category_counts"]),
                "public_name_counts": dict(scene.trace["public_name_counts"]),
                "territory_type_counts": dict(scene.trace["territory_type_counts"]),
            }
        )
    _make_contact_sheet(image_paths, out_dir / "scene_contact_sheet.png")
    _make_contact_sheet(overlay_paths, out_dir / "overlay_contact_sheet.png")
    manifest = {
        "renderer_id": "pixel_village_map_v0",
        "count": int(count),
        "base_seed": int(seed),
        "width": int(width),
        "height": int(height),
        "records": records,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme = [
        "# Pixel Village Map Prototype",
        "",
        "Generated review scenes for a procedural old-school pixel RPG village renderer.",
        "",
        "- `images/`: original scene renders",
        "- `overlays/`: debug renders with metadata bboxes and public names",
        "- `data/`: per-scene trace metadata",
        "- `scene_contact_sheet.png`: original scene overview",
        "- `overlay_contact_sheet.png`: bbox/debug overview",
        "",
        "The renderer uses no external sprites. Kenney Tiny Town, Kenney Roguelike/RPG, Kenney RPG Urban Pack, and graveyard pixel references are visual references only.",
        "Each scene samples its own grid dimensions and renders logical tiles at 32px by default.",
        "Preview generation cycles cemetery-only, orchard-only, windmill-only, all large optional features, and no-feature states.",
        "Tree entities keep public name `tree` while sampling oak, pine, maple, or fruit_tree visual styles.",
        "Orchard is a reusable variable-size territory with rows of fruit-tree entities and a low hedge/post boundary.",
        "Farm plots are intentionally left to dedicated farm scenes rather than the village renderer.",
        "Regular village houses, shops, and inns are front-facing and sample roof, wall, and door-state variants.",
        "The current reusable pixel-world object set also includes castle, church, windmill, round well, market stall, wagon, statue, gazebo, woodpile, variable pond, barrel, bench, lamp post, notice board, cart, flower, grave marker, and dead-tree templates.",
        "Dirt paths use connectivity-aware horizontal, vertical, corner, T-junction, and crossing tile pieces.",
        "Season comparison previews are optional and render the same seed as temperate, autumn, and winter for visual inspection.",
        "Cemetery is recorded as a village `territory`, not as a separate public scene prototype.",
    ]
    (out_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(f"[done] wrote {count} pixel-village previews to {out_dir}")


def generate_theme_comparisons(*, out_dir: Path, count: int, seed: int, width: int, height: int) -> None:
    compare_dir = out_dir / "theme_comparison"
    images_dir = compare_dir / "images"
    data_dir = compare_dir / "data"
    for directory in (images_dir, data_dir):
        directory.mkdir(parents=True, exist_ok=True)

    territory_modes = [
        ("force", "none", "none"),
        ("none", "force", "none"),
        ("none", "none", "force"),
        ("force", "force", "force"),
        ("none", "none", "none"),
    ]
    comparison_paths: list[Path] = []
    records: list[dict] = []
    for index in range(int(count)):
        scene_seed = int(seed) + index
        cemetery_mode, orchard_mode, windmill_mode = territory_modes[index % len(territory_modes)]
        common_kwargs = {
            "width": int(width),
            "height": int(height),
            "cemetery_mode": cemetery_mode,
            "orchard_mode": orchard_mode,
            "windmill_mode": windmill_mode,
        }
        temperate = render_pixel_village_map(scene_seed, theme_mode="temperate", **common_kwargs)
        autumn = render_pixel_village_map(scene_seed, theme_mode="autumn", **common_kwargs)
        winter = render_pixel_village_map(scene_seed, theme_mode="winter", **common_kwargs)
        temperate_path = images_dir / f"{index:04d}_temperate.png"
        autumn_path = images_dir / f"{index:04d}_autumn.png"
        winter_path = images_dir / f"{index:04d}_winter.png"
        comparison_path = images_dir / f"{index:04d}_season_comparison.png"
        temperate.image.save(temperate_path)
        autumn.image.save(autumn_path)
        winter.image.save(winter_path)
        _theme_strip(
            [
                ("temperate", _fit(temperate.image, max_w=250, max_h=220)),
                (f"autumn/{autumn.trace['autumn_intensity']}", _fit(autumn.image, max_w=250, max_h=220)),
                (f"winter/{winter.trace['snow_intensity']}", _fit(winter.image, max_w=250, max_h=220)),
            ]
        ).save(comparison_path)
        data_path = data_dir / f"{index:04d}.json"
        data_path.write_text(
            json.dumps({"temperate": temperate.trace, "autumn": autumn.trace, "winter": winter.trace}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        comparison_paths.append(comparison_path)
        records.append(
            {
                "index": int(index),
                "seed": int(scene_seed),
                "temperate_image": str(temperate_path),
                "autumn_image": str(autumn_path),
                "winter_image": str(winter_path),
                "comparison_image": str(comparison_path),
                "data": str(data_path),
                "autumn_intensity": str(autumn.trace["autumn_intensity"]),
                "snow_intensity": str(winter.trace["snow_intensity"]),
                "temperate_entity_count": int(temperate.trace["entity_count"]),
                "autumn_entity_count": int(autumn.trace["entity_count"]),
                "winter_entity_count": int(winter.trace["entity_count"]),
            }
        )
    _make_theme_comparison_sheet(comparison_paths, compare_dir / "season_comparison_sheet.png")
    manifest = {
        "renderer_id": "pixel_village_map_v0",
        "asset_id": "pixel_village_theme_comparison_v0",
        "count": int(count),
        "base_seed": int(seed),
        "width": int(width),
        "height": int(height),
        "contact_sheet": str(compare_dir / "season_comparison_sheet.png"),
        "records": records,
    }
    (compare_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[done] wrote {count} theme comparison previews to {compare_dir}")


def generate_winter_comparisons(*, out_dir: Path, count: int, seed: int, width: int, height: int) -> None:
    generate_theme_comparisons(out_dir=out_dir, count=count, seed=seed, width=width, height=height)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--count", type=int, default=18)
    parser.add_argument("--seed", type=int, default=20260604)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--theme-compare", action="store_true", help="Also generate side-by-side temperate/autumn/winter previews.")
    parser.add_argument("--winter-compare", action="store_true", help="Legacy alias for --theme-compare.")
    args = parser.parse_args()
    generate_previews(out_dir=args.out_dir, count=args.count, seed=args.seed, width=args.width, height=args.height)
    if args.theme_compare or args.winter_compare:
        generate_theme_comparisons(out_dir=args.out_dir, count=args.count, seed=args.seed, width=args.width, height=args.height)


if __name__ == "__main__":
    main()
