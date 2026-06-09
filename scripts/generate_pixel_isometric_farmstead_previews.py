#!/usr/bin/env python3
"""Generate procedural isometric pixel-farmstead prototype scenes for review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import types
from typing import Sequence

from PIL import Image, ImageDraw


def _install_trace_tasks_namespace() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    trace_module = sys.modules.get("trace")
    if trace_module is None or not hasattr(trace_module, "__path__"):
        trace_module = types.ModuleType("trace")
        trace_module.__path__ = [str(repo_root / "trace")]  # type: ignore[attr-defined]
        sys.modules["trace"] = trace_module
    if "trace.tasks" in sys.modules:
        return
    tasks_module = types.ModuleType("trace.tasks")
    tasks_module.__path__ = [str(repo_root / "trace" / "tasks")]  # type: ignore[attr-defined]
    sys.modules["trace.tasks"] = tasks_module
    setattr(trace_module, "tasks", tasks_module)


_install_trace_tasks_namespace()

from trace.tasks.illustrations.shared.pixel_isometric_farmstead_rendering import (  # noqa: E402
    draw_pixel_isometric_farmstead_debug_overlay,
    render_pixel_isometric_farmstead,
)


DEFAULT_OUT_DIR = Path("review/task-reviews/assets/illustrations/pixel_isometric_farmstead")


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
        draw.text((x + 16, y + tile_h - 26), f"isometric farmstead {index:02d}", fill=(45, 48, 54))
    sheet.save(output_path)


def generate_previews(*, out_dir: Path, count: int, seed: int, width: int, height: int, scale: int) -> None:
    images_dir = out_dir / "images"
    overlays_dir = out_dir / "overlays"
    data_dir = out_dir / "data"
    for directory in (images_dir, overlays_dir, data_dir):
        directory.mkdir(parents=True, exist_ok=True)

    image_paths: list[Path] = []
    overlay_paths: list[Path] = []
    records: list[dict] = []
    for index in range(int(count)):
        scene_seed = int(seed) + index
        scene = render_pixel_isometric_farmstead(
            scene_seed,
            width=int(width),
            height=int(height),
            scale=int(scale),
        )
        image_path = images_dir / f"{index:04d}.png"
        overlay_path = overlays_dir / f"{index:04d}_overlay.png"
        data_path = data_dir / f"{index:04d}.json"
        scene.image.save(image_path)
        draw_pixel_isometric_farmstead_debug_overlay(scene).save(overlay_path)
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
                "scale": int(scene.trace["scale"]),
                "levels": list(scene.trace["levels"]),
                "elevation_depth": int(scene.trace["elevation_depth"]),
                "upper_level": int(scene.trace["upper_level"]),
                "level_tile_counts": dict(scene.trace["level_tile_counts"]),
                "entity_count": int(scene.trace["entity_count"]),
                "animal_count": int(scene.trace["animal_count"]),
                "inside_pen_animal_count": int(scene.trace["inside_pen_animal_count"]),
                "outside_pen_animal_count": int(scene.trace["outside_pen_animal_count"]),
                "transition_count": int(scene.trace["transition_count"]),
                "category_counts": dict(scene.trace["category_counts"]),
                "public_name_counts": dict(scene.trace["public_name_counts"]),
            }
        )
    _make_contact_sheet(image_paths, out_dir / "scene_contact_sheet.png")
    _make_contact_sheet(overlay_paths, out_dir / "overlay_contact_sheet.png")
    manifest = {
        "renderer_id": "pixel_isometric_farmstead_v0",
        "count": int(count),
        "base_seed": int(seed),
        "width": int(width),
        "height": int(height),
        "scale": int(scale),
        "records": records,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme = [
        "# Pixel Isometric Farmstead Prototype",
        "",
        "Generated review scenes for a procedural old-school isometric pixel RPG farmstead renderer.",
        "",
        "- `images/`: original scene renders",
        "- `overlays/`: debug renders with projected regions, entity bboxes, transition polygons, and level labels",
        "- `data/`: per-scene trace metadata",
        "- `scene_contact_sheet.png`: original scene overview",
        "- `overlay_contact_sheet.png`: bbox/debug overview",
        "",
        "The renderer uses no external sprites. Kenney isometric farm/building packs are visual references only.",
        "Scenes use a 2:1 isometric projection with a lower field, raised barn terrace, ramp, stair, and fenced pens at different levels.",
        "The raised terrace samples an elevation depth of one or two level units above the lower field.",
        "The object vocabulary matches the top-down pixel farm prototype: barn, chicken coop, hay bales, crates, troughs, trees, flowers, people, and domestic animals.",
        "Hay bales, crates, troughs, trees, flowers, people, and domestic animals render through the shared illustration object renderer and expose normalized object records.",
        "No public TRACE task is registered for this prototype yet.",
    ]
    (out_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    print(f"[done] wrote {count} isometric-farmstead previews to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--count", type=int, default=18)
    parser.add_argument("--seed", type=int, default=20260604)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--scale", type=int, default=2)
    args = parser.parse_args()
    generate_previews(
        out_dir=args.out_dir,
        count=args.count,
        seed=args.seed,
        width=args.width,
        height=args.height,
        scale=args.scale,
    )


if __name__ == "__main__":
    main()
