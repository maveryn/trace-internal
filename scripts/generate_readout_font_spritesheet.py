#!/usr/bin/env python3
"""Generate a visual review sheet for the TRACE readout font pool."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
FONT_ROOT = REPO_ROOT / "assets" / "fonts"
DEFAULT_POOL_PATH = FONT_ROOT / "readout_pool_v0.json"
DEFAULT_SOURCE_PATH = FONT_ROOT / "sources.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "review" / "task-reviews" / "assets" / "fonts" / "readout_pool_v0"

SAMPLE_ROWS = (
    ("compact", 31, "A   10   Q   K"),
    ("short", 30, "A K Q 10"),
    ("numeric", 22, "100  -12  12.5  C=35  h=24"),
    ("labels", 20, "Hand A   Option F   Column 10"),
)
WIDTH_COMPARISON_TEXT = "Hand A   Option F   Column 10   Start   Goal   Total   C=35   h=24   100   12.5"
WIDTH_COMPARISON_SIZE_PX = 22
WIDTH_REFERENCE_FONTS = (
    ("system_dejavu_sans_bold", "DejaVuSans-Bold.ttf", "prior bold fallback"),
    ("system_dejavu_sans_regular", "DejaVuSans.ttf", "prior regular fallback"),
    ("system_liberation_sans_bold", "LiberationSans-Bold.ttf", "fallback candidate"),
    ("system_liberation_sans_regular", "LiberationSans-Regular.ttf", "fallback candidate"),
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _fallback_font(size_px: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "DejaVuSans.ttf")
        if bold
        else ("DejaVuSans.ttf", "LiberationSans-Regular.ttf")
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size=int(size_px))
        except Exception:
            continue
    return ImageFont.load_default()


def _named_system_font(name: str, size_px: int) -> ImageFont.ImageFont | None:
    try:
        return ImageFont.truetype(str(name), size=int(size_px))
    except Exception:
        return None


def _font_path(record: dict[str, Any], *, bold: bool) -> Path:
    rel = str(record.get("bold_path" if bold else "regular_path") or record.get("regular_path") or "")
    if not rel:
        raise ValueError(f"font record is missing a path: {record}")
    path = FONT_ROOT / rel
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def _load_family_font(record: dict[str, Any], size_px: int, *, bold: bool) -> ImageFont.ImageFont:
    primary = _font_path(record, bold=bold)
    try:
        return ImageFont.truetype(str(primary), size=int(size_px))
    except Exception:
        fallback = _font_path(record, bold=False)
        return ImageFont.truetype(str(fallback), size=int(size_px))


def _text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
) -> tuple[float, float, float, float]:
    try:
        bbox = draw.textbbox(tuple(xy), str(text), font=font)
        return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        x, y = float(xy[0]), float(xy[1])
        return (x, y, x + float(width), y + float(height))


def _draw_clipped_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    *,
    fill: tuple[int, int, int],
    max_width: int,
) -> None:
    rendered = str(text)
    while rendered:
        bbox = _text_bbox(draw, xy, rendered, font)
        if bbox[2] - bbox[0] <= max_width:
            break
        rendered = rendered[:-1]
    if rendered != str(text) and len(rendered) > 1:
        rendered = rendered[:-1] + "..."
    draw.text(xy, rendered, font=font, fill=fill)


def _validate_pool(pool: dict[str, Any], sources: dict[str, Any]) -> list[str]:
    families = pool.get("font_families")
    if not isinstance(families, list):
        raise ValueError("readout pool must contain a font_families list")
    keys = [str(key) for key in families]
    if len(keys) != 100:
        raise ValueError(f"readout pool must contain exactly 100 fonts; found {len(keys)}")
    if len(set(keys)) != len(keys):
        raise ValueError("readout pool contains duplicate font keys")
    source_families = sources.get("families", {})
    if not isinstance(source_families, dict):
        raise ValueError("font sources payload must contain a families object")
    missing = [key for key in keys if key not in source_families]
    if missing:
        raise ValueError(f"readout pool contains unknown font keys: {missing}")
    for key in keys:
        _font_path(source_families[key], bold=False)
        _font_path(source_families[key], bold=True)
    return keys


def _measure_family(
    draw: ImageDraw.ImageDraw,
    record: dict[str, Any],
) -> dict[str, Any]:
    row_metrics: list[dict[str, Any]] = []
    for label, size_px, sample in SAMPLE_ROWS:
        font = _load_family_font(record, size_px, bold=True)
        bbox = _text_bbox(draw, (0, 0), sample, font)
        row_metrics.append(
            {
                "label": str(label),
                "font_size_px": int(size_px),
                "sample": str(sample),
                "width_px": round(float(bbox[2] - bbox[0]), 3),
                "height_px": round(float(bbox[3] - bbox[1]), 3),
            }
        )
    compact_font = _load_family_font(record, 31, bold=True)
    compact: list[dict[str, Any]] = []
    for sample in ("A", "K", "Q", "10"):
        bbox = _text_bbox(draw, (0, 0), sample, compact_font)
        compact.append(
            {
                "sample": str(sample),
                "width_px": round(float(bbox[2] - bbox[0]), 3),
                "height_px": round(float(bbox[3] - bbox[1]), 3),
                "fits_62x56": bool((bbox[2] - bbox[0]) <= 62 and (bbox[3] - bbox[1]) <= 56),
            }
        )
    return {"sample_rows": row_metrics, "compact_card_samples": compact}


def _draw_width_comparison_sheet(
    *,
    output_path: Path,
    family_keys: list[str],
    source_families: dict[str, Any],
) -> list[dict[str, Any]]:
    """Draw one aligned sample line per font to make width differences obvious."""

    row_h = 48
    header_h = 96
    left_pad = 24
    label_w = 390
    sample_x = left_pad + label_w
    right_pad = 40
    width = 1900
    reference_fonts = [
        (key, font, note)
        for key, font_name, note in WIDTH_REFERENCE_FONTS
        if (font := _named_system_font(font_name, WIDTH_COMPARISON_SIZE_PX)) is not None
    ]
    reference_h = 0 if not reference_fonts else (len(reference_fonts) * row_h) + 20
    pool_start_y = header_h + reference_h
    height = pool_start_y + (len(family_keys) * row_h) + 24
    guide_color = (224, 229, 236)
    sample_fill = (19, 26, 37)

    image = Image.new("RGB", (width, height), (249, 250, 252))
    draw = ImageDraw.Draw(image)
    title_font = _fallback_font(22, bold=True)
    label_font = _fallback_font(15, bold=True)
    small_font = _fallback_font(12, bold=False)

    draw.text((left_pad, 18), "Readout pool width comparison", font=title_font, fill=(25, 31, 43))
    draw.text(
        (left_pad, 52),
        f"Every row draws the same text at {WIDTH_COMPARISON_SIZE_PX}px bold. Vertical guides are 100px apart from the shared start x.",
        font=small_font,
        fill=(84, 95, 112),
    )
    draw.text((sample_x, 76), WIDTH_COMPARISON_TEXT, font=small_font, fill=(84, 95, 112))

    for offset in range(0, width - sample_x - right_pad + 1, 100):
        x = sample_x + offset
        draw.line((x, header_h - 10, x, height - 14), fill=guide_color, width=1)
        if offset:
            draw.text((x + 3, header_h - 26), str(offset), font=small_font, fill=(126, 137, 153))

    metrics: list[dict[str, Any]] = []
    if reference_fonts:
        draw.text((left_pad, header_h + 4), "System fallback reference rows (not in 100-font pool)", font=label_font, fill=(95, 62, 18))
    for ref_idx, (key, ref_font, note) in enumerate(reference_fonts):
        y0 = header_h + 22 + (ref_idx * row_h)
        y_mid = y0 + (row_h // 2)
        draw.rectangle((8, y0, width - 8, y0 + row_h), fill=(255, 249, 232))
        draw.line((8, y0 + row_h, width - 8, y0 + row_h), fill=(231, 211, 158), width=1)
        _draw_clipped_text(draw, (left_pad, y0 + 8), key, label_font, fill=(72, 50, 16), max_width=label_w - 24)
        _draw_clipped_text(draw, (left_pad, y0 + 28), note, small_font, fill=(121, 89, 36), max_width=label_w - 24)
        bbox = _text_bbox(draw, (sample_x, y0 + 10), WIDTH_COMPARISON_TEXT, ref_font)
        text_w = float(bbox[2] - bbox[0])
        text_h = float(bbox[3] - bbox[1])
        draw.text((sample_x, y0 + 10), WIDTH_COMPARISON_TEXT, font=ref_font, fill=(64, 45, 16))
        end_x = int(round(sample_x + text_w))
        draw.line((end_x, y0 + 6, end_x, y0 + row_h - 6), fill=(190, 121, 24), width=2)
        draw.text((min(end_x + 6, width - 80), y_mid - 7), f"{int(round(text_w))}px", font=small_font, fill=(153, 93, 21))
        metrics.append(
            {
                "index": None,
                "font_family": key,
                "family_name": key,
                "sample": WIDTH_COMPARISON_TEXT,
                "font_size_px": WIDTH_COMPARISON_SIZE_PX,
                "width_px": round(text_w, 3),
                "height_px": round(text_h, 3),
                "reference_only": True,
            }
        )

    for idx, key in enumerate(family_keys):
        record = source_families[key]
        y0 = pool_start_y + (idx * row_h)
        y_mid = y0 + (row_h // 2)
        row_fill = (255, 255, 255) if idx % 2 == 0 else (244, 247, 250)
        draw.rectangle((8, y0, width - 8, y0 + row_h), fill=row_fill)
        draw.line((8, y0 + row_h, width - 8, y0 + row_h), fill=(232, 236, 242), width=1)

        family_name = str(record.get("family_name", key))
        label = f"{idx + 1:03d}. {key}"
        _draw_clipped_text(draw, (left_pad, y0 + 8), label, label_font, fill=(32, 39, 52), max_width=label_w - 24)
        _draw_clipped_text(draw, (left_pad, y0 + 28), family_name, small_font, fill=(92, 103, 119), max_width=label_w - 24)

        family_font = _load_family_font(record, WIDTH_COMPARISON_SIZE_PX, bold=True)
        bbox = _text_bbox(draw, (sample_x, y0 + 10), WIDTH_COMPARISON_TEXT, family_font)
        text_w = float(bbox[2] - bbox[0])
        text_h = float(bbox[3] - bbox[1])
        draw.text((sample_x, y0 + 10), WIDTH_COMPARISON_TEXT, font=family_font, fill=sample_fill)
        end_x = int(round(sample_x + text_w))
        draw.line((end_x, y0 + 6, end_x, y0 + row_h - 6), fill=(65, 112, 209), width=2)
        draw.text((min(end_x + 6, width - 80), y_mid - 7), f"{int(round(text_w))}px", font=small_font, fill=(65, 112, 209))

        metrics.append(
            {
                "index": idx + 1,
                "font_family": key,
                "family_name": family_name,
                "sample": WIDTH_COMPARISON_TEXT,
                "font_size_px": WIDTH_COMPARISON_SIZE_PX,
                "width_px": round(text_w, 3),
                "height_px": round(text_h, 3),
                "reference_only": False,
            }
        )

    image.save(output_path)
    return metrics


def generate(pool_path: Path, sources_path: Path, output_dir: Path) -> tuple[Path, Path]:
    pool = _load_json(pool_path)
    sources = _load_json(sources_path)
    family_keys = _validate_pool(pool, sources)
    source_families = sources["families"]

    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / "readout_pool_v0_spritesheet.png"
    width_lines_path = output_dir / "readout_pool_v0_width_lines.png"
    manifest_path = output_dir / "readout_pool_v0_spritesheet_manifest.json"

    cols = 5
    rows = 20
    tile_w = 470
    tile_h = 260
    pad = 18
    width = cols * tile_w
    height = rows * tile_h

    image = Image.new("RGB", (width, height), (247, 248, 250))
    draw = ImageDraw.Draw(image)
    label_font = _fallback_font(15, bold=False)
    label_font_bold = _fallback_font(16, bold=True)
    small_font = _fallback_font(12, bold=False)

    manifest: dict[str, Any] = {
        "pool_id": pool.get("pool_id"),
        "source_font_manifest": str(sources_path.relative_to(REPO_ROOT)),
        "source_font_asset_version": sources.get("asset_version"),
        "pool_font_count": len(family_keys),
        "spritesheet": str(png_path.relative_to(REPO_ROOT)),
        "width_comparison_sheet": str(width_lines_path.relative_to(REPO_ROOT)),
        "layout": {"columns": cols, "rows": rows, "tile_width_px": tile_w, "tile_height_px": tile_h},
        "families": [],
    }

    measure_canvas = Image.new("RGB", (10, 10), (255, 255, 255))
    measure_draw = ImageDraw.Draw(measure_canvas)

    for idx, key in enumerate(family_keys):
        record = source_families[key]
        col = idx % cols
        row = idx // cols
        x0 = col * tile_w
        y0 = row * tile_h
        x1 = x0 + tile_w
        y1 = y0 + tile_h

        panel_fill = (255, 255, 255) if (row + col) % 2 == 0 else (252, 253, 254)
        draw.rectangle((x0 + 8, y0 + 8, x1 - 8, y1 - 8), fill=panel_fill, outline=(205, 211, 219), width=1)

        title = f"{idx + 1:03d}. {key}"
        family_name = str(record.get("family_name", key))
        _draw_clipped_text(draw, (x0 + pad, y0 + 18), title, label_font_bold, fill=(26, 32, 44), max_width=tile_w - 2 * pad)
        _draw_clipped_text(draw, (x0 + pad, y0 + 42), family_name, label_font, fill=(78, 88, 105), max_width=tile_w - 2 * pad)

        sample_y = y0 + 74
        for row_label, size_px, sample in SAMPLE_ROWS:
            box = (x0 + pad, sample_y - 2, x1 - pad, sample_y + 38)
            draw.rectangle(box, outline=(226, 230, 236), width=1)
            draw.text((x0 + pad + 6, sample_y + 3), row_label, font=small_font, fill=(112, 122, 138))
            family_font = _load_family_font(record, size_px, bold=True)
            draw.text((x0 + pad + 86, sample_y + 1), sample, font=family_font, fill=(22, 27, 36))
            sample_y += 43

        metrics = _measure_family(measure_draw, record)
        manifest["families"].append(
            {
                "index": idx + 1,
                "font_family": key,
                "family_name": family_name,
                "license": str(record.get("license", "")),
                "tags": [str(tag) for tag in record.get("tags", [])],
                "regular_path": str(record.get("regular_path", "")),
                "bold_path": str(record.get("bold_path", "")),
                "metrics": metrics,
            }
        )

    image.save(png_path)
    manifest["width_comparison_metrics"] = _draw_width_comparison_sheet(
        output_path=width_lines_path,
        family_keys=family_keys,
        source_families=source_families,
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return png_path, manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, default=DEFAULT_POOL_PATH)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCE_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    png_path, manifest_path = generate(args.pool, args.sources, args.output_dir)
    print(f"spritesheet: {png_path}")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
