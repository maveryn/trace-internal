#!/usr/bin/env python3
"""Generate review spritesheets for icon-domain resource pools."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import types
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image, ImageDraw


def _install_trace_tasks_namespace() -> None:
    """Avoid importing the repo-wide task registry for review-asset generation."""

    if "trace.tasks" in sys.modules:
        return
    repo_root = Path(__file__).resolve().parents[1]
    tasks_module = types.ModuleType("trace.tasks")
    tasks_module.__path__ = [str(repo_root / "trace" / "tasks")]  # type: ignore[attr-defined]
    sys.modules["trace.tasks"] = tasks_module


_install_trace_tasks_namespace()

from trace.tasks.icons.shared.icon_assets import render_icon_rgba, resolve_icon_pool
from trace.tasks.icons.shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    procedural_named_icon_fill_style_display_name,
    render_procedural_named_icon_rgba,
)
from trace.tasks.shared.text_rendering import load_font


OUT_ROOT = Path("review/task-reviews/assets/icons")
BG = (247, 249, 252)
PANEL_BG = (255, 255, 255)
PANEL_OUTLINE = (205, 214, 225)
TEXT = (31, 42, 56)
MUTED = (93, 104, 119)
ICON_TINT = (35, 49, 68)
PROCEDURAL_TINT = (41, 92, 148)
ACCENT_TINT = (194, 101, 72)


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
    size: int = 11,
    fill: tuple[int, int, int] = TEXT,
    bold: bool = False,
) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    label = _ellipsize(draw, str(text), max(4.0, x1 - x0 - 8.0), size=size, bold=bold)
    tw, th = _text_size(draw, label, size=size, bold=bold)
    _draw_text(draw, (x0 + (x1 - x0 - tw) * 0.5, y0 + (y1 - y0 - th) * 0.5), label, size=size, fill=fill, bold=bold)


def _paste_centered(canvas: Image.Image, sprite: Image.Image, bbox: Sequence[float]) -> None:
    x0, y0, x1, y1 = [int(round(float(value))) for value in bbox]
    max_w = max(1, x1 - x0)
    max_h = max(1, y1 - y0)
    image = sprite.convert("RGBA")
    scale = min(float(max_w) / float(max(1, image.width)), float(max_h) / float(max(1, image.height)), 1.0)
    if scale < 1.0:
        image = image.resize((max(1, int(round(image.width * scale))), max(1, int(round(image.height * scale)))), Image.Resampling.LANCZOS)
    px = x0 + (max_w - image.width) // 2
    py = y0 + (max_h - image.height) // 2
    canvas.alpha_composite(image, (px, py))


def _chunks(values: Sequence[str], size: int) -> Iterable[tuple[int, tuple[str, ...]]]:
    for start in range(0, len(values), int(size)):
        yield start // int(size), tuple(values[start : start + int(size)])


def _make_icon_sheet(
    output_path: Path,
    *,
    title: str,
    subtitle: str,
    items: Sequence[Mapping[str, Any]],
    cols: int,
    tile_w: int,
    tile_h: int,
    icon_size: int,
) -> dict[str, Any]:
    header_h = 82
    rows = max(1, (len(items) + int(cols) - 1) // int(cols))
    width = int(cols) * int(tile_w)
    height = int(header_h) + rows * int(tile_h)
    canvas = Image.new("RGBA", (width, height), BG + (255,))
    draw = ImageDraw.Draw(canvas)
    _draw_text(draw, (22, 15), title, size=23, bold=True)
    _draw_text(draw, (22, 48), subtitle, size=12, fill=MUTED)

    rendered = 0
    failures: list[dict[str, str]] = []
    for index, item in enumerate(items):
        col = index % int(cols)
        row = index // int(cols)
        x = col * int(tile_w)
        y = int(header_h) + row * int(tile_h)
        panel = (x + 8, y + 8, x + int(tile_w) - 8, y + int(tile_h) - 8)
        draw.rounded_rectangle(panel, radius=8, fill=PANEL_BG, outline=PANEL_OUTLINE, width=1)
        try:
            sprite = item["render"](int(icon_size))
        except Exception as exc:  # pragma: no cover - review asset fallback
            failures.append({"id": str(item.get("id", "")), "error": str(exc), "error_type": type(exc).__name__})
            continue
        _paste_centered(canvas, sprite, (panel[0] + 20, panel[1] + 16, panel[2] - 20, panel[1] + 16 + int(icon_size)))
        _center_text(draw, (panel[0] + 5, panel[3] - 39, panel[2] - 5, panel[3] - 22), str(item.get("name", item.get("id", ""))), size=10, bold=True)
        if str(item.get("id", "")) != str(item.get("name", "")):
            _center_text(draw, (panel[0] + 5, panel[3] - 22, panel[2] - 5, panel[3] - 6), str(item.get("id", "")), size=8, fill=MUTED)
        rendered += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output_path)
    return {
        "file": output_path.as_posix(),
        "title": title,
        "item_count": len(items),
        "rendered_count": rendered,
        "failure_count": len(failures),
        "failures": failures,
    }


def _procedural_items(fill_style: str) -> list[dict[str, Any]]:
    items = []
    for shape_id in PROCEDURAL_NAMED_ICON_SHAPES:
        items.append(
            {
                "id": str(shape_id),
                "name": procedural_named_icon_display_name(str(shape_id)),
                "fill_style": str(fill_style),
                "render": lambda size_px, shape_id=shape_id, fill_style=fill_style: render_procedural_named_icon_rgba(
                    shape_id=str(shape_id),
                    size_px=int(size_px),
                    tint_rgb=PROCEDURAL_TINT if str(fill_style) != "half_filled" else ACCENT_TINT,
                    fill_style=str(fill_style),
                ),
            }
        )
    return items


def _curated_items(icon_ids: Sequence[str]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(icon_id),
            "name": str(icon_id).replace("gi-", "").replace("tabler-", "").replace("hero-", "").replace("-", " "),
            "render": lambda size_px, icon_id=icon_id: render_icon_rgba(icon_id=str(icon_id), size_px=int(size_px), tint_rgb=ICON_TINT),
        }
        for icon_id in icon_ids
    ]


def _clear_collection(path: Path) -> None:
    if not path.exists():
        return
    for candidate in path.glob("*.png"):
        candidate.unlink()
    for candidate in path.glob("*.json"):
        candidate.unlink()
    readme = path / "README.md"
    if readme.exists():
        readme.unlink()


def _write_collection_readme(path: Path, *, title: str, records: Sequence[Mapping[str, Any]]) -> None:
    lines = [
        f"# {title}",
        "",
        "Generated review resource spritesheets for the TRACE review app.",
        "",
        "| File | Items | Rendered |",
        "|---|---:|---:|",
    ]
    for record in records:
        file_name = Path(str(record["file"])).name
        lines.append(f"| [{file_name}]({file_name}) | {record['item_count']} | {record['rendered_count']} |")
    path.mkdir(parents=True, exist_ok=True)
    (path / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _generate_procedural_named() -> list[dict[str, Any]]:
    output_dir = OUT_ROOT / "procedural_named"
    _clear_collection(output_dir)
    records = []
    for fill_style in PROCEDURAL_NAMED_ICON_FILL_STYLES:
        title = f"Procedural Named Icons: {procedural_named_icon_fill_style_display_name(str(fill_style)).title()}"
        records.append(
            _make_icon_sheet(
                output_dir / f"procedural_named_{fill_style}.png",
                title=title,
                subtitle=f"All {len(PROCEDURAL_NAMED_ICON_SHAPES)} procedural named icon shapes rendered with {fill_style.replace('_', ' ')} fill.",
                items=_procedural_items(str(fill_style)),
                cols=8,
                tile_w=156,
                tile_h=142,
                icon_size=70,
            )
        )
    manifest = {
        "category": "icons",
        "collection": "procedural_named",
        "shape_count": len(PROCEDURAL_NAMED_ICON_SHAPES),
        "fill_styles": list(PROCEDURAL_NAMED_ICON_FILL_STYLES),
        "sheets": records,
        "icons": [
            {"id": str(shape_id), "display_name": procedural_named_icon_display_name(str(shape_id))}
            for shape_id in PROCEDURAL_NAMED_ICON_SHAPES
        ],
    }
    (output_dir / "procedural_named_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_collection_readme(output_dir, title="Procedural Named Icons", records=records)
    return records


def _generate_curated_manifest(manifest_name: str, *, title: str, chunk_size: int = 120) -> list[dict[str, Any]]:
    icon_ids = tuple(resolve_icon_pool(str(manifest_name)))
    output_dir = OUT_ROOT / f"curated_{manifest_name}"
    _clear_collection(output_dir)
    records = []
    for chunk_index, chunk in _chunks(icon_ids, int(chunk_size)):
        records.append(
            _make_icon_sheet(
                output_dir / f"curated_{manifest_name}_{chunk_index + 1:02d}.png",
                title=f"{title} {chunk_index + 1:02d}",
                subtitle=f"{len(chunk)} icons from {manifest_name}; global indices {chunk_index * int(chunk_size)}-{chunk_index * int(chunk_size) + len(chunk) - 1}.",
                items=_curated_items(chunk),
                cols=10,
                tile_w=148,
                tile_h=134,
                icon_size=64,
            )
        )
    manifest = {
        "category": "icons",
        "collection": f"curated_{manifest_name}",
        "manifest_name": str(manifest_name),
        "icon_count": len(icon_ids),
        "chunk_size": int(chunk_size),
        "sheets": records,
        "icons": list(icon_ids),
    }
    (output_dir / f"curated_{manifest_name}_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_collection_readme(output_dir, title=title, records=records)
    return records


def main() -> int:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    records = []
    records.extend(_generate_procedural_named())
    records.extend(_generate_curated_manifest("symmetry", title="Curated Symmetric SVG Icons"))
    records.extend(_generate_curated_manifest("non_symmetry", title="Curated Asymmetric SVG Icons"))
    all_failures = [failure for record in records for failure in record.get("failures", [])]
    index = {
        "category": "icons",
        "sheet_count": len(records),
        "failure_count": len(all_failures),
        "sheets": records,
        "failures": all_failures,
    }
    (OUT_ROOT / "icon_resource_manifest.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for record in records:
        print(f"[wrote] {record['file']} ({record['rendered_count']}/{record['item_count']} icons)")
    if all_failures:
        print(f"[warning] {len(all_failures)} icon render failure(s)")
    return 1 if all_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
