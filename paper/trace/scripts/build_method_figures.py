#!/usr/bin/env python3
"""Build deterministic Trace method and taxonomy assets from canonical reviews."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from PIL import Image, ImageDraw, ImageFont, ImageOps, __version__ as pillow_version


REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_DEFAULT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_DEFAULT))

from trace.core.reasoning_operations import (  # noqa: E402
    REASONING_OPERATION_KEYS,
    REASONING_OPERATION_SCHEMA_VERSION,
    parse_reasoning_operations,
    program_contract_sha256,
)
from trace.tasks.registry import task_reasoning_operations  # noqa: E402


FONT_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")

INK = (31, 41, 55)
MUTED = (88, 98, 112)
PAPER = (248, 248, 246)
CARD = (255, 255, 255)
LINE = (205, 211, 219)
BLUE = (42, 111, 181)
ORANGE = (215, 111, 44)
GREEN = (40, 143, 89)
PURPLE = (111, 78, 159)
TEAL = (26, 137, 145)

DOMAIN_COLORS: dict[str, tuple[int, int, int]] = {
    "charts": (46, 112, 184),
    "games": (221, 124, 47),
    "geometry": (46, 145, 93),
    "graph": (116, 83, 164),
    "icons": (30, 145, 151),
    "illustrations": (181, 72, 91),
    "pages": (191, 143, 35),
    "physics": (44, 126, 172),
    "puzzles": (204, 79, 71),
    "symbolic": (98, 105, 116),
    "three_d": (73, 88, 166),
}


@dataclass(frozen=True)
class SampleSpec:
    label: str
    domain: str
    scene_id: str
    task_id: str
    query_id: str
    index: int
    instance_seed: int
    image_sha256: str
    data_sha256: str


@dataclass(frozen=True)
class LoadedSample:
    spec: SampleSpec
    image_path: Path
    data_path: Path
    payload: dict[str, Any]
    image: Image.Image


MONTAGE_SPECS = (
    SampleSpec("Charts", "charts", "multiseries", "task_charts__multiseries__category_total_extremum_label", "largest_category_total_label", 0, 6971963630053741, "c745587a933839e2925d0e091e0876ba624594066a573fc279d85831e6d94f0c", "9e541ddfe6194e8973ea16457d2e8e36fd593e2a209df5b24f8ea2439fab8de1"),
    SampleSpec("Games", "games", "space_shooter", "task_games__space_shooter__enemy_ship_count", "single", 0, 2618255346746328, "63fde69d84c704c212f2f438a3ad41dc489b2bc93ac1db3c3f17ba381815ef49", "722c72183b3d9b29972aa435a1427e35d2baa4ad3261b3fd0e4cb12ef0b3ac6f"),
    SampleSpec("Geometry", "geometry", "angle_relations", "task_geometry__angle_relations__algebraic_angle_value", "single", 0, 6685141427653421, "1dc26906e16ee63df8b78347348cd47e766e40248a9272926c8af62cf98329b0", "c3b12e974c3a3543e84f785061e9da09b35fa55dd8b94fff827a26fdd7df44fb"),
    SampleSpec("Graphs", "graph", "node_link", "task_graph__node_link__shortest_path_length", "directed_shortest_path_length", 0, 2481365412104608, "c5aaa80bb5f3cd91d01b347908459482f8eb7f7e8727634ba5c26977da431251", "fb10fe9fe7dc784b7025a49ce16b8e28b2fc5e19b182d00d7726cc67916a6da5"),
    SampleSpec("Icons", "icons", "icon_field", "task_icons__icon_field__most_frequent_type_count", "single", 0, 8191844928700627, "d5c5bfb8d3a3a78dcff81e1119f1e887f6177ee61484a717c3c2fd08859ef441", "d9ee0d8eee20037a8534516f682a5de0cdf72c9bbf40cc0c04f58f8e75b03210"),
    SampleSpec("Illustrations", "illustrations", "rpg_tactical_map", "task_illustrations__rpg_tactical_map__movement_reachable_tile_count", "single", 0, 5683608548028481, "2f125d2b64a93d70c185940a7076d22136b4dcea46d0cb3940a5fa1ba818e5ff", "efae17e75e550f2992594aa9788c3f70e555c6224219cd6969210758a3f47496"),
    SampleSpec("Pages", "pages", "record_table", "task_pages__record_table__value_threshold_in_group_count", "single", 0, 3621091651242047, "d87de3758165fbf155a48331e80554a8e5e48fd077b577dc7f4edcad61a14354", "f24b689deda9fe25df892144af49f65378acf7b1e1c27f7fa3fc0a45d20f2507"),
    SampleSpec("Physics", "physics", "free_body_forces", "task_physics__free_body_forces__net_force_direction_choice", "single", 0, 8791560635313457, "85f979e35f6958b51e8a778824daa429773dccc0c83da0ff65816ae5d23b1723", "1520372de7b82f2d2906c9ded390b3b54e50ce9734555cf01e40fbd49c23813d"),
    SampleSpec("Puzzles", "puzzles", "raven_matrix", "task_puzzles__raven_matrix__raven_count_progression_label", "single", 0, 8979951069889835, "1979f2ce6e43ada5fd4dbea3f736863e29fd07b2915d12c6825b12c3b684e7e6", "a6ee8053568831f93bca60caa872ee6516a66d2a7b992faf97fd0a32549e4f78"),
    SampleSpec("Symbolic", "symbolic", "clock", "task_symbolic__clock__equivalent_time_label", "analog_reference_digital_options", 0, 5401932260136482, "cdf577e8d8c9f870c4c958aa3638837ea26991185b28aef5108df3642027f7e2", "2ae221be0ee613e217216ccf87fd35ab109b6d9b092d13df6a3fd186053cf447"),
    SampleSpec("3D scenes", "three_d", "object_scene", "task_three_d__object_scene__camera_depth_relation_count", "closer_to_camera_than_reference_count", 0, 948033558578505, "59e5c8a206c0932509134b16bdf750a33e7c73409b3eb04d7557ed6656bf77ee", "07e12ddee020980e4460ee9eab63aea827cd7346cb39bcda9817d56fc6bca6aa"),
)

BOUNDARY_SPECS = (
    SampleSpec("Largest IQR", "charts", "boxplot", "task_charts__boxplot__iqr_extremum_label", "largest_iqr_label", 0, 4037236735245413, "55a29f9765aa08f9c13a12e18e046a22b50e2de4a699d841e6bddd41a63b9f8e", "9bf6cd7967e4537642165df55cd076d08faeeec56bd9b1f7cd7a6c3c3d326b63"),
    SampleSpec("Smallest IQR", "charts", "boxplot", "task_charts__boxplot__iqr_extremum_label", "smallest_iqr_label", 0, 5160289026271840, "8ab2a5471ab3a0b16f071dc4af2ea9a293bedb8291d528e29b6d4c9aa7475ac2", "505279f0d47fe1099f8ff1c328a2be12e93b2f432717c2eced453ae4092c15ee"),
    SampleSpec("Shape", "icons", "named_field", "task_icons__named_field__single_attribute_membership_count", "single", 0, 2106328256058390, "b83094bb90359fd80fe6f518e8d2776d0944484dccb68c551c5ad8fb235520f7", "5e989e9fcfb4d1519669fcf7ca261a19b1666e28826ed6af0b079c6f9f7302e6"),
    SampleSpec("Shape AND color", "icons", "named_field", "task_icons__named_field__multi_attribute_and_count", "single", 0, 6380339362641116, "7b9b2f2b1f7145ed02569ff7c4b2c5b799412c06f3307408c9ec4d3afa07a12b", "a7ac4576bad74b2ce558a12f69708e6eae1213c3fbdd500a767323e480852d73"),
    SampleSpec("Style A", "puzzles", "cell_board", "task_puzzles__cell_board__reachable_region_size", "single", 0, 6228739918347647, "302a68c52a7fbc6e3bc6de43d5b68275ce5c9bfe2733678e4257a92742d87303", "03b05ef853f2afe85471715c70e752aeef4a83da55cc59fd3b95dcffb195c6a2"),
    SampleSpec("Style B", "puzzles", "cell_board", "task_puzzles__cell_board__reachable_region_size", "single", 1, 1003906358904027, "28845c64facf8c01e0b87cb7ae3ec28b5e604c9b9b2a4e3931622297f7b7eb91", "cf09426d1599052d730a4e6d245364b63c66838faa83285517ebe6836ae676f1"),
)

RUNNING_SPEC = BOUNDARY_SPECS[4]


@dataclass(frozen=True)
class RenderVariationProfile:
    """One explicitly controlled realization of a fixed semantic instance."""

    label: str
    slug: str
    controlled_axis: str
    realization_summary: str
    params_override: dict[str, Any]


RENDER_VARIATION_TASK_ID = "task_graph__node_link__shortest_path_length"
RENDER_VARIATION_QUERY_ID = "undirected_shortest_path_length"
RENDER_VARIATION_INSTANCE_SEED = 2026071401
RENDER_VARIATION_BASE_PARAMS: dict[str, Any] = {
    "query_id": RENDER_VARIATION_QUERY_ID,
    "node_count": 8,
    "target_shortest_path_length": 3,
    "topology_profile": "balanced",
    "label_variant": "numbers",
    "layout_variant": "spring",
    "layout_transform_variant": "identity",
    "node_shape_variant": "circle",
    "edge_routing_variant": "straight",
    "node_color_name": "blue",
    "node_radius_min_px": 28,
    "node_radius_max_px": 28,
    "label_font_size_px": 24,
    "theme_tone": "standard",
    "panel_style_variant": "default",
    "information_scene_treatments": ["clean_default"],
    "information_scene_palettes": ["neutral_report"],
    "information_scene_chrome_modes": ["none"],
    "font_family": "source_sans_3",
    "content_jitter_max_px": 0,
    "context_text_probability": 0.0,
    "context_text_max_elements": 0,
    "context_block_probability": 0.0,
    "context_block_max_elements": 0,
    "visual": {"noise": {"apply_prob": 0.0}},
}
RENDER_VARIATION_PROFILES = (
    RenderVariationProfile(
        "Baseline",
        "baseline",
        "Reference",
        "Light neutral theme, sans-serif type, fixed layout, no context or noise",
        {},
    ),
    RenderVariationProfile(
        "Color palette",
        "color_palette",
        "Palette",
        "Warm editorial palette; graph topology and layout retained",
        {"information_scene_palettes": ["warm_editorial"]},
    ),
    RenderVariationProfile(
        "Typeface",
        "typeface",
        "Typography",
        "EB Garamond node-label typeface; baseline palette and layout retained",
        {"font_family": "eb_garamond"},
    ),
    RenderVariationProfile(
        "Layout",
        "layout",
        "Structure",
        "Circular node placement replaces the baseline spring layout",
        {"layout_variant": "circular"},
    ),
    RenderVariationProfile(
        "Report context",
        "report_context",
        "Non-answer context",
        "Curated paragraph context in reserved non-answer panel space",
        {
            "context_block_probability": 1.0,
            "context_block_max_elements": 1,
            "context_block_position_weights": {"bottom": 1.0},
            "context_block_clutter_level_weights": {"medium": 1.0},
        },
    ),
    RenderVariationProfile(
        "Raster noise",
        "raster_noise",
        "Post-render",
        "Gaussian noise with fixed sigma; coordinate geometry retained",
        {
            "visual": {
                "noise": {
                    "apply_prob": 1.0,
                    "edit_types": ["gaussian_noise"],
                    "edit_count_range": [1, 1],
                    "value_ranges": {"gaussian_noise": {"sigma": [8.0, 8.0]}},
                }
            }
        },
    ),
)


PROGRAM_OPERATION_COLUMNS = (
    ("direct_retrieval", "Direct\nretrieval"),
    ("filtering", "Filtering"),
    ("counting", "Counting"),
    ("comparison", "Comparison"),
    ("ranking", "Ranking"),
    ("aggregation", "Aggregation"),
    ("logical_composition", "Logical\ncomposition"),
    ("spatial_relations", "Spatial\nrelations"),
    ("topology", "Topology"),
    ("transformation", "Transformation"),
    ("state_update", "State\nupdate"),
    ("formula_evaluation", "Formula\nevaluation"),
    ("matching", "Matching"),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    if not path.exists():
        raise FileNotFoundError(f"required paper font is missing: {path}")
    return ImageFont.truetype(str(path), size=size)


def _sample_paths(repo_root: Path, spec: SampleSpec) -> tuple[Path, Path]:
    base = repo_root / "review" / "task-reviews" / spec.domain / spec.scene_id / spec.task_id
    stem = f"{spec.index:04d}"
    return base / "images" / spec.query_id / f"{stem}.png", base / "data" / spec.query_id / f"{stem}.json"


def _load_sample(repo_root: Path, spec: SampleSpec) -> LoadedSample:
    image_path, data_path = _sample_paths(repo_root, spec)
    if not image_path.exists() or not data_path.exists():
        raise FileNotFoundError(f"missing pinned review artifact for {spec.task_id}/{spec.query_id}/{spec.index}")
    if _sha256(image_path) != spec.image_sha256:
        raise RuntimeError(f"image hash changed for {image_path}; review and repin the paper sample")
    if _sha256(data_path) != spec.data_sha256:
        raise RuntimeError(f"data hash changed for {data_path}; review and repin the paper sample")
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    task_id = payload.get("task_id", payload.get("task"))
    if task_id != spec.task_id or payload.get("query_id") != spec.query_id:
        raise RuntimeError(f"taxonomy mismatch in {data_path}")
    if int(payload.get("instance_seed")) != spec.instance_seed:
        raise RuntimeError(f"seed mismatch in {data_path}")
    image = Image.open(image_path).convert("RGB")
    return LoadedSample(spec, image_path, data_path, payload, image)


def _rounded_card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], *, fill: tuple[int, int, int] = CARD, outline: tuple[int, int, int] = LINE, radius: int = 24, width: int = 3) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return right - left, bottom - top


def _center_text(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], text: str, font: ImageFont.FreeTypeFont, *, fill: tuple[int, int, int] = INK) -> None:
    width, height = _text_size(draw, text, font)
    x0, y0, x1, y1 = box
    draw.text((x0 + (x1 - x0 - width) / 2, y0 + (y1 - y0 - height) / 2), text, font=font, fill=fill)


def _fit_image(image: Image.Image, size: tuple[int, int], *, fill: tuple[int, int, int] = CARD) -> tuple[Image.Image, tuple[int, int], float]:
    contained = ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)
    panel = Image.new("RGB", size, fill)
    offset = ((size[0] - contained.width) // 2, (size[1] - contained.height) // 2)
    panel.paste(contained, offset)
    scale = contained.width / image.width
    return panel, offset, scale


def _draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], *, fill: tuple[int, int, int] = MUTED, width: int = 8) -> None:
    draw.line((start, end), fill=fill, width=width)
    ex, ey = end
    sx, sy = start
    if abs(ex - sx) >= abs(ey - sy):
        direction = 1 if ex > sx else -1
        points = [(ex, ey), (ex - 24 * direction, ey - 16), (ex - 24 * direction, ey + 16)]
    else:
        direction = 1 if ey > sy else -1
        points = [(ex, ey), (ex - 16, ey - 24 * direction), (ex + 16, ey - 24 * direction)]
    draw.polygon(points, fill=fill)


def _draw_wrapped(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont, *, max_width: int, fill: tuple[int, int, int] = INK, line_gap: int = 10) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        proposed = word if not current else f"{current} {word}"
        if _text_size(draw, proposed, font)[0] <= max_width:
            current = proposed
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    line_height = _text_size(draw, "Ag", font)[1]
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height + line_gap
    return y


def _tex_escape(text: str) -> str:
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(character, character) for character in text)


def _compile_standalone_pdf(
    *,
    source: str,
    output: Path,
    basename: str,
    temporary_prefix: str,
) -> None:
    """Compile one deterministic standalone TeX asset."""

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=str(temporary_prefix)) as temporary_directory:
        build_dir = Path(temporary_directory)
        tex_path = build_dir / f"{basename}.tex"
        tex_path.write_text(source, encoding="utf-8")
        environment = os.environ.copy()
        environment.update({"SOURCE_DATE_EPOCH": "0", "FORCE_SOURCE_DATE": "1", "TZ": "UTC"})
        completed = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=build_dir,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"failed to build {basename} PDF:\n{completed.stdout}\n{completed.stderr}"
            )
        shutil.copyfile(build_dir / f"{basename}.pdf", output)


def _build_domain_montage(samples: list[LoadedSample], output: Path) -> None:
    row_counts = (4, 4, 3)
    if len(samples) != sum(row_counts):
        raise RuntimeError(f"domain montage expects {sum(row_counts)} samples, received {len(samples)}")

    rows: list[str] = []
    sample_index = 0
    for row_count in row_counts:
        tiles: list[str] = []
        for _ in range(row_count):
            sample = samples[sample_index]
            sample_index += 1
            image_path = sample.image_path.resolve().as_posix()
            tiles.append(
                rf"\montagetile{{\detokenize{{{image_path}}}}}{{{_tex_escape(sample.spec.label)}}}"
            )
        rows.append(r"\noindent\makebox[\linewidth][c]{" + r"\hspace{0.08in}".join(tiles) + "}")

    source = "\n".join(
        (
            r"\documentclass[border=8pt]{standalone}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{graphicx}",
            r"\usepackage{xcolor}",
            r"\pdfinfoomitdate=1",
            r"\pdftrailerid{}",
            r"\pdfsuppressptexinfo=-1",
            r"\definecolor{tileborder}{RGB}{205,211,219}",
            r"\setlength{\fboxsep}{4pt}",
            r"\setlength{\fboxrule}{0.5pt}",
            r"\newcommand{\montagetile}[2]{%",
            r"  \fcolorbox{tileborder}{white}{%",
            r"    \begin{minipage}[t]{2.52in}%",
            r"      \centering",
            r"      \parbox[c][1.35in][c]{2.48in}{\centering\includegraphics[width=2.48in,height=1.35in,keepaspectratio]{#1}}%",
            r"      \par\vspace{1pt}{\sffamily\bfseries\fontsize{14}{15}\selectfont #2}\vspace{2pt}%",
            r"    \end{minipage}%",
            r"  }%",
            r"}",
            r"\begin{document}",
            r"\begin{minipage}{11.1in}",
            r"\centering",
            rows[0] + r"\par\vspace{0.08in}",
            rows[1] + r"\par\vspace{0.08in}",
            rows[2],
            r"\end{minipage}",
            r"\end{document}",
            "",
        )
    )

    _compile_standalone_pdf(
        source=source,
        output=output,
        basename="domain_montage",
        temporary_prefix="trace-domain-montage-",
    )


def _build_reachable_pipeline(sample: LoadedSample, output: Path) -> None:
    canvas = Image.new("RGB", (3200, 900), PAPER)
    draw = ImageDraw.Draw(canvas)
    headings = _font(40, bold=True)
    body = _font(34)
    small = _font(30)
    mono_like = _font(32, bold=True)
    boxes = ((40, 55, 760, 845), (850, 55, 1520, 845), (1610, 55, 2330, 845), (2420, 55, 3160, 845))
    titles = ("1  Scene instance", "2  Execute task program", "3  Validate generated instance", "4  Package RLVR instance")
    for box, title in zip(boxes, titles):
        _rounded_card(draw, box, radius=26, width=3)
        draw.text((box[0] + 30, box[1] + 24), title, font=headings, fill=INK)
    for left, right in zip(boxes, boxes[1:]):
        _draw_arrow(draw, (left[2] + 15, 450), (right[0] - 15, 450), fill=PURPLE, width=9)

    base, _, _ = _fit_image(sample.image, (640, 515), fill=(245, 246, 247))
    canvas.paste(base, (80, 155))
    _center_text(draw, (80, 690, 720, 790), "Cell states and start S", body, fill=MUTED)

    x0, y0, x1, _ = boxes[1]
    y = y0 + 155
    draw.text((x0 + 42, y), "P_t(x, q)", font=_font(46, bold=True), fill=PURPLE)
    y += 85
    for line in ("4-neighbor flood fill", "start at S", "light cells are passable", "dark cells block movement"):
        draw.ellipse((x0 + 48, y + 11, x0 + 62, y + 25), fill=PURPLE)
        draw.text((x0 + 82, y), line, font=body, fill=INK)
        y += 63
    y += 34
    draw.rounded_rectangle((x0 + 42, y, x1 - 42, y + 155), radius=18, fill=(244, 239, 250), outline=(194, 178, 216), width=3)
    draw.text((x0 + 70, y + 24), "v = {c1, c2, c3, c4}", font=mono_like, fill=INK)
    draw.text((x0 + 70, y + 85), "y = |v| = 4", font=mono_like, fill=INK)

    x0, y0, x1, _ = boxes[2]
    y = y0 + 150
    checks = (
        ("program constraints", "satisfied", GREEN),
        ("answer uniqueness", "one valid result", BLUE),
        ("render validity", "scene checks pass", ORANGE),
        ("replay state", "seed + parameters", PURPLE),
    )
    for name, value, color in checks:
        draw.rounded_rectangle((x0 + 42, y, x1 - 42, y + 125), radius=16, fill=(249, 250, 251), outline=LINE, width=3)
        draw.text((x0 + 68, y + 22), name, font=small, fill=MUTED)
        draw.text((x0 + 68, y + 65), value, font=mono_like, fill=color)
        y += 145

    x0, y0, x1, _ = boxes[3]
    y = y0 + 150
    entries = (
        ("prompt", "versioned template", ORANGE),
        ("answer", "integer(4)", BLUE),
        ("reward", "typed exact match", GREEN),
        ("trace_ref", "sidecar execution record", PURPLE),
    )
    for name, value, color in entries:
        draw.rounded_rectangle((x0 + 42, y, x1 - 42, y + 125), radius=16, fill=(249, 250, 251), outline=LINE, width=3)
        draw.text((x0 + 68, y + 22), name, font=small, fill=MUTED)
        draw.text((x0 + 68, y + 65), value, font=mono_like, fill=color)
        y += 145

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", dpi=(300, 300), optimize=True)


def _draw_image_pair(draw: ImageDraw.ImageDraw, canvas: Image.Image, panel: tuple[int, int, int, int], samples: tuple[LoadedSample, LoadedSample], *, image_size: tuple[int, int], accent: tuple[int, int, int]) -> int:
    x0, y0, x1, _ = panel
    gap = 24
    pair_width = image_size[0] * 2 + gap
    start_x = x0 + (x1 - x0 - pair_width) // 2
    y = y0 + 135
    for index, sample in enumerate(samples):
        x = start_x + index * (image_size[0] + gap)
        fitted, _, _ = _fit_image(sample.image, image_size, fill=(245, 246, 247))
        canvas.paste(fitted, (x, y))
        draw.rounded_rectangle((x, y, x + image_size[0], y + image_size[1]), radius=12, outline=accent, width=5)
        _center_text(draw, (x, y + image_size[1] + 8, x + image_size[0], y + image_size[1] + 62), sample.spec.label, _font(31, bold=True), fill=INK)
    return y + image_size[1] + 78


def _build_taxonomy_boundaries(samples: list[LoadedSample], output: Path) -> None:
    by_label = {sample.spec.label: sample for sample in samples}
    canvas = Image.new("RGB", (3200, 1370), PAPER)
    draw = ImageDraw.Draw(canvas)
    title = _font(45, bold=True)
    body = _font(34)
    small = _font(30)

    _rounded_card(draw, (40, 35, 3160, 470), radius=28, width=3)
    draw.text((80, 65), "Public hierarchy: visual grammar first, objective contract second", font=title, fill=INK)
    hierarchy_y = 225
    domain_box = (120, hierarchy_y - 55, 520, hierarchy_y + 70)
    scene_box = (700, hierarchy_y - 55, 1160, hierarchy_y + 70)
    _rounded_card(draw, domain_box, fill=(235, 243, 252), outline=BLUE, radius=18, width=4)
    _rounded_card(draw, scene_box, fill=(240, 237, 248), outline=PURPLE, radius=18, width=4)
    _center_text(draw, domain_box, "domain: puzzles", _font(36, bold=True), fill=BLUE)
    _center_text(draw, scene_box, "scene: cell board", _font(36, bold=True), fill=PURPLE)
    _draw_arrow(draw, (domain_box[2] + 24, hierarchy_y + 5), (scene_box[0] - 24, hierarchy_y + 5), fill=MUTED, width=7)
    task_names = ("reachable region", "shortest path", "largest component", "symmetry violation")
    task_x = 1380
    task_w, task_h, task_gap = 390, 105, 32
    for index, task_name in enumerate(task_names):
        x = task_x + index * (task_w + task_gap)
        box = (x, hierarchy_y - 45, x + task_w, hierarchy_y + 60)
        is_selected = index == 0
        _rounded_card(draw, box, fill=(239, 249, 244) if is_selected else (249, 250, 251), outline=GREEN if is_selected else LINE, radius=16, width=4 if is_selected else 3)
        _center_text(draw, box, task_name, _font(29, bold=is_selected), fill=GREEN if is_selected else INK)
    _draw_arrow(draw, (scene_box[2] + 24, hierarchy_y + 5), (task_x - 24, hierarchy_y + 5), fill=MUTED, width=7)
    draw.text((1380, 365), "Each task fixes a concrete program and output contract.", font=small, fill=MUTED)

    panel_y0, panel_y1 = 520, 1325
    panel_gap = 30
    panel_w = (3120 - 2 * panel_gap) // 3
    panels = tuple((40 + i * (panel_w + panel_gap), panel_y0, 40 + i * (panel_w + panel_gap) + panel_w, panel_y1) for i in range(3))
    accents = (BLUE, ORANGE, GREEN)
    headings = ("Query variation", "Public task split", "Generation variation")
    for panel, accent, heading in zip(panels, accents, headings):
        _rounded_card(draw, panel, radius=24, width=4, outline=accent)
        _center_text(draw, (panel[0] + 20, panel[1] + 20, panel[2] - 20, panel[1] + 100), heading, title, fill=accent)

    y = _draw_image_pair(draw, canvas, panels[0], (by_label["Largest IQR"], by_label["Smallest IQR"]), image_size=(445, 330), accent=BLUE)
    _center_text(draw, (panels[0][0] + 40, y, panels[0][2] - 40, y + 75), "one task: direction in {largest, smallest}", body, fill=INK)
    _draw_wrapped(draw, (panels[0][0] + 58, y + 100), "Candidate boxes, IQR computation, answer type, and verifier contract remain unchanged.", small, max_width=panel_w - 116, fill=MUTED, line_gap=8)

    y = _draw_image_pair(draw, canvas, panels[1], (by_label["Shape"], by_label["Shape AND color"]), image_size=(445, 330), accent=ORANGE)
    _center_text(draw, (panels[1][0] + 40, y, panels[1][2] - 40, y + 75), "two tasks: membership vs conjunction", body, fill=INK)
    _draw_wrapped(draw, (panels[1][0] + 58, y + 100), "Adding a second attribute changes predicate arity and the visual filtering program.", small, max_width=panel_w - 116, fill=MUTED, line_gap=8)

    y = _draw_image_pair(draw, canvas, panels[2], (by_label["Style A"], by_label["Style B"]), image_size=(445, 330), accent=GREEN)
    _center_text(draw, (panels[2][0] + 40, y, panels[2][2] - 40, y + 75), "one task: rendering parameters vary", body, fill=INK)
    _draw_wrapped(draw, (panels[2][0] + 58, y + 100), "Palette, board dimensions, and layout vary without changing the reachability program.", small, max_width=panel_w - 116, fill=MUTED, line_gap=8)

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", dpi=(300, 300), optimize=True)


def _load_environment_coverage(repo_root: Path) -> dict[str, Any]:
    """Load environment counts from the generated inventory and task contracts."""

    column_keys = tuple(key for key, _ in PROGRAM_OPERATION_COLUMNS)
    if column_keys != REASONING_OPERATION_KEYS:
        raise RuntimeError("paper operation columns drifted from the canonical order")

    inventory_path = repo_root / "docs" / "ACTIVE_TASK_INVENTORY.md"
    inventory_text = inventory_path.read_text(encoding="utf-8")
    domain_rows: list[dict[str, Any]] = []
    in_domain_summary = False
    for line in inventory_text.splitlines():
        if line == "## Domain Summary":
            in_domain_summary = True
            continue
        if in_domain_summary and line.startswith("## "):
            break
        match = re.fullmatch(r"\| ([a-z_]+) \| ([0-9]+) \| ([0-9]+) \|", line)
        if match is not None:
            domain_rows.append(
                {
                    "domain": match.group(1),
                    "scenes": int(match.group(2)),
                    "tasks": int(match.group(3)),
                }
            )

    task_ids = re.findall(r"^- `(task_[a-z0-9_]+__[^`]+)`$", inventory_text, flags=re.MULTILINE)
    if len(task_ids) != 1000:
        raise RuntimeError(f"expected 1,000 active tasks in inventory, found {len(task_ids)}")
    if sum(int(row["tasks"]) for row in domain_rows) != len(task_ids):
        raise RuntimeError("domain task counts do not match active inventory")

    answer_types: Counter[str] = Counter()
    operation_counts_by_domain: dict[str, Counter[str]] = {
        str(row["domain"]): Counter() for row in domain_rows
    }
    operation_task_ids: dict[str, dict[str, list[str]]] = {
        str(row["domain"]): {
            key: [] for key, _ in PROGRAM_OPERATION_COLUMNS
        }
        for row in domain_rows
    }
    operation_assignments: dict[str, list[str]] = {}
    program_contract_hashes: dict[str, str] = {}
    operation_source_paths: dict[str, str] = {}
    operation_source_hashes: dict[str, str] = {}
    query_counts: Counter[int] = Counter()
    tasks_per_scene: Counter[tuple[str, str]] = Counter()
    for task_id in task_ids:
        task_prefix, scene_id, objective = task_id.split("__", maxsplit=2)
        domain = task_prefix.removeprefix("task_")
        tasks_per_scene[(domain, scene_id)] += 1
        task_doc = repo_root / "docs" / "tasks" / domain / scene_id / f"{task_id}.md"
        if not task_doc.exists():
            raise RuntimeError(f"missing task documentation for {task_id}")
        task_doc_text = task_doc.read_text(encoding="utf-8")
        if "## Program Contract" not in task_doc_text:
            raise RuntimeError(f"missing concrete program contract for {task_id}")
        try:
            operations = task_reasoning_operations(task_id)
            documented_operations = parse_reasoning_operations(task_doc_text)
            program_hash = program_contract_sha256(task_doc_text)
        except ValueError as exc:
            raise RuntimeError(f"invalid task reasoning metadata for {task_id}: {exc}") from exc
        if documented_operations != operations:
            raise RuntimeError(
                f"task reasoning-operation doc drift for {task_id}: "
                f"code={operations!r}, docs={documented_operations!r}"
            )
        source_path = (
            repo_root / "trace" / "tasks" / domain / scene_id / f"{objective}.py"
        )
        if not source_path.is_file():
            raise RuntimeError(f"missing public task source for {task_id}")
        operation_assignments[task_id] = list(operations)
        program_contract_hashes[task_id] = program_hash
        operation_source_paths[task_id] = str(source_path.relative_to(repo_root))
        operation_source_hashes[task_id] = _sha256(source_path)
        for operation in operations:
            operation_counts_by_domain[domain][operation] += 1
            operation_task_ids[domain][operation].append(task_id)
        task_root = repo_root / "review" / "task-reviews" / domain / scene_id / task_id
        data_root = task_root / "data"
        query_dirs = [path for path in sorted(data_root.iterdir()) if path.is_dir() and next(path.glob("*.json"), None) is not None]
        if not query_dirs:
            raise RuntimeError(f"missing current review data for {task_id}")
        query_counts[len(query_dirs)] += 1
        sample_path = next(query_dirs[0].glob("*.json"))
        payload = json.loads(sample_path.read_text(encoding="utf-8"))
        answer_type = str(payload.get("answer_gt", {}).get("type", ""))
        if not answer_type:
            raise RuntimeError(f"missing answer type in {sample_path}")
        answer_types[answer_type] += 1

    task_counts_by_scene = sorted(tasks_per_scene.values())
    return {
        "inventory_path": str(inventory_path.relative_to(repo_root)),
        "domains": domain_rows,
        "task_count": len(task_ids),
        "scene_count": len(tasks_per_scene),
        "answer_types": dict(sorted(answer_types.items())),
        "operation_metadata_schema": REASONING_OPERATION_SCHEMA_VERSION,
        "operation_assignment_source": "public_task_class.reasoning_operations",
        "operation_columns": [
            {"key": key, "label": label.replace("\n", " ")}
            for key, label in PROGRAM_OPERATION_COLUMNS
        ],
        "operation_matrix": {
            str(row["domain"]): {
                key: int(operation_counts_by_domain[str(row["domain"])][key])
                for key, _ in PROGRAM_OPERATION_COLUMNS
            }
            for row in domain_rows
        },
        "operation_task_ids": operation_task_ids,
        "operation_assignments": operation_assignments,
        "operation_source_paths": operation_source_paths,
        "operation_source_sha256": operation_source_hashes,
        "program_contract_sha256": program_contract_hashes,
        "operation_unclassified_task_ids": [],
        "query_branch_counts": {str(key): value for key, value in sorted(query_counts.items())},
        "multi_query_tasks": sum(value for key, value in query_counts.items() if key > 1),
        "total_query_branches": sum(key * value for key, value in query_counts.items()),
        "tasks_per_scene": {
            "minimum": min(task_counts_by_scene),
            "median": task_counts_by_scene[len(task_counts_by_scene) // 2],
            "maximum": max(task_counts_by_scene),
            "mean": sum(task_counts_by_scene) / len(task_counts_by_scene),
        },
    }


def _draw_bar(
    draw: ImageDraw.ImageDraw,
    *,
    label: str,
    value: int,
    maximum: int,
    x: int,
    y: int,
    width: int,
    height: int,
    color: tuple[int, int, int],
    label_width: int,
    value_suffix: str = "",
    label_font_size: int = 28,
    value_font_size: int = 27,
) -> None:
    label_font = _font(label_font_size)
    value_font = _font(value_font_size, bold=True)
    draw.text((x, y + 5), label, font=label_font, fill=INK)
    bar_x = x + label_width
    bar_width = max(4, int(round(width * value / maximum)))
    draw.rounded_rectangle((bar_x, y, bar_x + width, y + height), radius=height // 2, fill=(232, 235, 239))
    draw.rounded_rectangle((bar_x, y, bar_x + bar_width, y + height), radius=height // 2, fill=color)
    draw.text((bar_x + width + 16, y + 5), f"{value}{value_suffix}", font=value_font, fill=INK)


def _build_domain_landscape(coverage: dict[str, Any], output: Path) -> None:
    """Render scene and task coverage as paired radial bars by visual domain."""

    domains = list(coverage["domains"])
    domain_keys = tuple(str(row["domain"]) for row in domains)
    if set(domain_keys) != set(DOMAIN_COLORS):
        missing = sorted(set(domain_keys) - set(DOMAIN_COLORS))
        stale = sorted(set(DOMAIN_COLORS) - set(domain_keys))
        raise RuntimeError(f"domain color inventory drift: missing={missing}, stale={stale}")
    if len(domains) != 11 or int(coverage["task_count"]) != 1000 or int(coverage["scene_count"]) != 277:
        raise RuntimeError("domain landscape requires the frozen 11-domain, 1,000-task, 277-scene inventory")

    canvas = Image.new("RGB", (3200, 1900), PAPER)
    draw = ImageDraw.Draw(canvas)
    title_font = _font(58, bold=True)
    subtitle_font = _font(31)
    domain_font = _font(34, bold=True)
    count_font = _font(27)
    center_title_font = _font(70, bold=True)
    center_value_font = _font(42, bold=True)
    center_label_font = _font(29)
    legend_font = _font(27)

    draw.text((55, 42), "Visual-domain coverage", font=title_font, fill=INK)
    draw.text(
        (55, 118),
        "Equal-angle sectors compare independently scaled task and scene counts; exact values are printed.",
        font=subtitle_font,
        fill=MUTED,
    )

    task_max = max(int(row["tasks"]) for row in domains)
    scene_max = max(int(row["scenes"]) for row in domains)
    legend_x = 2440
    draw.rounded_rectangle((legend_x, 48, legend_x + 34, 82), radius=5, fill=BLUE)
    draw.text((legend_x + 48, 49), f"Tasks (0-{task_max})", font=legend_font, fill=INK)
    draw.rounded_rectangle(
        (legend_x, 98, legend_x + 34, 132),
        radius=5,
        fill=_interpolate_rgb(BLUE, PAPER, 0.48),
        outline=(166, 179, 198),
        width=2,
    )
    draw.text((legend_x + 48, 99), f"Scenes (0-{scene_max})", font=legend_font, fill=INK)

    center_x, center_y = 1600, 1020
    inner_radius = 245
    radial_span = 410
    outer_radius = inner_radius + radial_span
    label_radius = 805
    sector_angle = 360.0 / float(len(domains))
    bar_width = 11.8
    bar_offset = 6.9
    track_fill = (231, 234, 238)
    track_outline = (218, 223, 229)

    def radial_bbox(radius: float) -> tuple[float, float, float, float]:
        return (
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
        )

    for index, row in enumerate(domains):
        domain = str(row["domain"])
        domain_color = DOMAIN_COLORS[domain]
        scene_color = _interpolate_rgb(domain_color, PAPER, 0.48)
        center_angle = -90.0 + float(index) * sector_angle
        task_start = center_angle - bar_offset - bar_width / 2.0
        task_end = task_start + bar_width
        scene_start = center_angle + bar_offset - bar_width / 2.0
        scene_end = scene_start + bar_width

        for start, end in ((task_start, task_end), (scene_start, scene_end)):
            draw.pieslice(
                radial_bbox(outer_radius),
                start=start,
                end=end,
                fill=track_fill,
                outline=track_outline,
                width=2,
            )

        task_radius = inner_radius + radial_span * int(row["tasks"]) / float(task_max)
        scene_radius = inner_radius + radial_span * int(row["scenes"]) / float(scene_max)
        draw.pieslice(
            radial_bbox(task_radius),
            start=task_start,
            end=task_end,
            fill=domain_color,
        )
        draw.pieslice(
            radial_bbox(scene_radius),
            start=scene_start,
            end=scene_end,
            fill=scene_color,
            outline=domain_color,
            width=2,
        )

        radians = math.radians(center_angle)
        line_start = (
            center_x + math.cos(radians) * (outer_radius + 12),
            center_y + math.sin(radians) * (outer_radius + 12),
        )
        line_end = (
            center_x + math.cos(radians) * (label_radius - 70),
            center_y + math.sin(radians) * (label_radius - 70),
        )
        draw.line((line_start, line_end), fill=_interpolate_rgb(domain_color, PAPER, 0.35), width=3)
        label_x = center_x + math.cos(radians) * label_radius
        label_y = center_y + math.sin(radians) * label_radius
        domain_label = "3D" if domain == "three_d" else domain.replace("_", " ").title()
        draw.text((label_x, label_y - 17), domain_label, font=domain_font, fill=domain_color, anchor="mm")
        draw.text(
            (label_x, label_y + 25),
            f"{int(row['tasks'])} tasks / {int(row['scenes'])} scenes",
            font=count_font,
            fill=INK,
            anchor="mm",
        )

    draw.ellipse(
        radial_bbox(inner_radius - 4),
        fill=PAPER,
        outline=(198, 205, 214),
        width=4,
    )
    draw.text((center_x, center_y - 105), "Trace", font=center_title_font, fill=INK, anchor="mm")
    center_rows = (("1,000", "tasks", BLUE), ("277", "scenes", PURPLE), ("11", "domains", TEAL))
    row_y = center_y - 28
    for value, label, color in center_rows:
        draw.text((center_x - 8, row_y), value, font=center_value_font, fill=color, anchor="rm")
        draw.text((center_x + 8, row_y + 1), label, font=center_label_font, fill=MUTED, anchor="lm")
        row_y += 65

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", dpi=(300, 300), optimize=True)


def _build_answer_reward_summary(coverage: dict[str, Any], output: Path) -> None:
    """Render the typed answer interfaces governed by one exact-match reward."""

    canvas = Image.new("RGB", (1900, 1050), PAPER)
    draw = ImageDraw.Draw(canvas)
    answer_order = ("integer", "option_letter", "string", "number")
    answer_labels = {
        "integer": "Integer",
        "option_letter": "Option letter",
        "string": "String",
        "number": "Numeric",
    }
    answer_colors = (BLUE, ORANGE, GREEN, PURPLE)
    values = [int(coverage["answer_types"][key]) for key in answer_order]
    total = sum(values)
    if total != int(coverage["task_count"]):
        raise RuntimeError("answer-interface counts do not match the active task count")

    center = (520, 525)
    outer_radius = 400
    inner_radius = 240
    outer_bbox = (
        center[0] - outer_radius,
        center[1] - outer_radius,
        center[0] + outer_radius,
        center[1] + outer_radius,
    )
    angle = -90.0
    for value, color in zip(values, answer_colors):
        extent = 360.0 * value / total
        draw.pieslice(
            outer_bbox,
            start=angle,
            end=angle + extent,
            fill=color,
            outline=PAPER,
            width=8,
        )
        angle += extent
    draw.ellipse(
        (
            center[0] - inner_radius,
            center[1] - inner_radius,
            center[0] + inner_radius,
            center[1] + inner_radius,
        ),
        fill=PAPER,
    )

    draw.text(center, "1,000", font=_font(96, bold=True), fill=INK, anchor="ms")
    draw.text(
        (center[0], center[1] + 52),
        "tasks",
        font=_font(42, bold=True),
        fill=MUTED,
        anchor="mm",
    )
    draw.text(
        (center[0], center[1] + 120),
        "one exact-match reward",
        font=_font(31, bold=True),
        fill=INK,
        anchor="mm",
    )
    draw.text((center[0], center[1] + 166), "no LLM judge", font=_font(29), fill=MUTED, anchor="mm")

    legend_x = 1070
    legend_y = 220
    label_font = _font(46, bold=True)
    value_font = _font(41)
    for key, value, color in zip(answer_order, values, answer_colors):
        draw.rounded_rectangle(
            (legend_x, legend_y + 5, legend_x + 54, legend_y + 59),
            radius=10,
            fill=color,
        )
        draw.text((legend_x + 82, legend_y), answer_labels[key], font=label_font, fill=INK)
        percentage = 100.0 * value / total
        draw.text(
            (legend_x + 82, legend_y + 61),
            f"{value:,} tasks  |  {percentage:.1f}%",
            font=value_font,
            fill=MUTED,
        )
        legend_y += 190

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", dpi=(300, 300), optimize=True)


def _interpolate_rgb(
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    amount: float,
) -> tuple[int, int, int]:
    amount = max(0.0, min(1.0, amount))
    return tuple(
        int(round(left + (right - left) * amount))
        for left, right in zip(start, end)
    )


def _build_domain_operation_matrix(coverage: dict[str, Any], output: Path) -> None:
    """Render the selected multi-label operation families by domain."""

    canvas = Image.new("RGB", (3400, 1820), PAPER)
    draw = ImageDraw.Draw(canvas)
    title_font = _font(54, bold=True)
    subtitle_font = _font(31)
    header_font = _font(28, bold=True)
    domain_font = _font(39, bold=True)
    total_font = _font(27)
    count_font = _font(43, bold=True)
    legend_font = _font(29)

    domains = coverage["domains"]
    operation_matrix = coverage["operation_matrix"]
    grid_left = 450
    grid_right = 3320
    grid_top = 315
    row_height = 102
    row_gap = 8
    column_gap = 8
    column_width = (grid_right - grid_left - column_gap * (len(PROGRAM_OPERATION_COLUMNS) - 1)) // len(PROGRAM_OPERATION_COLUMNS)

    shares = [
        int(operation_matrix[str(row["domain"])][key]) / int(row["tasks"])
        for row in domains
        for key, _ in PROGRAM_OPERATION_COLUMNS
    ]
    max_share = max(shares)
    if max_share <= 0:
        raise RuntimeError("operation matrix contains no classified tasks")

    draw.text((55, 42), "Reasoning-operation coverage", font=title_font, fill=INK)
    draw.text(
        (55, 112),
        "Cell labels are task counts; color is the operation's share of tasks in that domain.",
        font=subtitle_font,
        fill=MUTED,
    )
    draw.text((55, 210), "Domain", font=header_font, fill=MUTED)

    for column_index, (_, label) in enumerate(PROGRAM_OPERATION_COLUMNS):
        x0 = grid_left + column_index * (column_width + column_gap)
        x1 = x0 + column_width
        lines = label.split("\n")
        line_height = _text_size(draw, "Ag", header_font)[1]
        block_height = len(lines) * line_height + (len(lines) - 1) * 5
        y = 210 - block_height / 2
        for line in lines:
            width, _ = _text_size(draw, line, header_font)
            draw.text((x0 + (x1 - x0 - width) / 2, y), line, font=header_font, fill=MUTED)
            y += line_height + 5

    low_color = (239, 245, 246)
    high_color = (14, 100, 108)
    for row_index, row in enumerate(domains):
        domain = str(row["domain"])
        task_total = int(row["tasks"])
        y0 = grid_top + row_index * (row_height + row_gap)
        y1 = y0 + row_height
        domain_label = "3D" if domain == "three_d" else domain.replace("_", " ").title()
        draw.text((55, y0 + 13), domain_label, font=domain_font, fill=INK)
        total_label = f"n = {task_total}"
        total_width, _ = _text_size(draw, total_label, total_font)
        draw.text((grid_left - 35 - total_width, y0 + 56), total_label, font=total_font, fill=MUTED)

        for column_index, (key, _) in enumerate(PROGRAM_OPERATION_COLUMNS):
            count = int(operation_matrix[domain][key])
            share = count / task_total
            intensity = share / max_share
            fill = _interpolate_rgb(low_color, high_color, intensity)
            x0 = grid_left + column_index * (column_width + column_gap)
            x1 = x0 + column_width
            draw.rounded_rectangle(
                (x0, y0, x1, y1),
                radius=8,
                fill=fill,
                outline=(225, 232, 234),
                width=2,
            )
            text_fill = CARD if intensity >= 0.52 else INK
            _center_text(draw, (x0, y0, x1, y1), str(count), count_font, fill=text_fill)

    legend_y = 1643
    legend_x = 450
    legend_width = 690
    legend_height = 30
    for offset in range(legend_width):
        fill = _interpolate_rgb(low_color, high_color, offset / (legend_width - 1))
        draw.line(
            (legend_x + offset, legend_y, legend_x + offset, legend_y + legend_height),
            fill=fill,
            width=1,
        )
    draw.rectangle(
        (legend_x, legend_y, legend_x + legend_width, legend_y + legend_height),
        outline=(210, 220, 222),
        width=2,
    )
    draw.text((legend_x, legend_y + 46), "0%", font=legend_font, fill=MUTED)
    max_label = f"{max_share:.0%} (matrix maximum)"
    max_label_width, _ = _text_size(draw, max_label, legend_font)
    draw.text(
        (legend_x + legend_width - max_label_width, legend_y + 46),
        max_label,
        font=legend_font,
        fill=MUTED,
    )
    draw.text(
        (1320, legend_y + 1),
        "Multi-label: a task can contribute to several operation families.",
        font=_font(33, bold=True),
        fill=INK,
    )
    draw.text(
        (1320, legend_y + 53),
        "Exhaustive: every task has at least one family; direct retrieval is an exclusive fallback.",
        font=subtitle_font,
        fill=MUTED,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", dpi=(300, 300), optimize=True)


def _deep_merge_mapping(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Return a recursive mapping merge without mutating either input."""

    merged = dict(base)
    for key, value in override.items():
        current = merged.get(str(key))
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged[str(key)] = _deep_merge_mapping(current, value)
        else:
            merged[str(key)] = value
    return merged


def _json_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _render_variation_semantic_record(output: Any) -> dict[str, Any]:
    trace_payload = output.trace_payload
    if not isinstance(trace_payload, Mapping):
        raise RuntimeError("rendering-variation task did not return a trace payload")
    execution_trace = trace_payload.get("execution_trace")
    scene_ir = trace_payload.get("scene_ir")
    if not isinstance(execution_trace, Mapping) or not isinstance(scene_ir, Mapping):
        raise RuntimeError("rendering-variation task is missing semantic trace sections")
    render_only_execution_fields = {
        "edge_routing_variant",
        "layout_transform_variant",
        "layout_variant_requested",
        "layout_variant_used",
        "node_color_name",
        "node_shape_variant",
    }
    semantic_execution = {
        str(key): value
        for key, value in execution_trace.items()
        if str(key) not in render_only_execution_fields
    }
    return {
        "task_id": RENDER_VARIATION_TASK_ID,
        "query_id": str(output.query_id),
        "prompt": str(output.prompt),
        "answer_gt": {
            "type": str(output.answer_gt.type),
            "value": output.answer_gt.value,
        },
        "execution_trace": semantic_execution,
        "scene_ir": {
            "scene_kind": scene_ir.get("scene_kind"),
            "relations": scene_ir.get("relations"),
        },
    }


def _validate_render_variation_profile(
    *,
    profile: RenderVariationProfile,
    render_spec: Mapping[str, Any],
    execution_trace: Mapping[str, Any],
) -> None:
    panel_geometry = render_spec.get("panel_geometry")
    surface_style = render_spec.get("style")
    if not isinstance(panel_geometry, Mapping) or not isinstance(surface_style, Mapping):
        raise RuntimeError(f"{profile.label} is missing required render metadata")
    information_style = panel_geometry.get("information_scene_style")
    noise = surface_style.get("post_image_noise_meta")
    if not isinstance(information_style, Mapping) or not isinstance(noise, Mapping):
        raise RuntimeError(f"{profile.label} is missing required style or noise metadata")
    context_elements = panel_geometry.get("context_text_elements", [])
    if not isinstance(context_elements, list):
        raise RuntimeError(f"{profile.label} has malformed context metadata")

    if profile.slug == "baseline":
        if information_style.get("style_pack") != "clean_default:neutral_report:none":
            raise RuntimeError("baseline rendering profile did not resolve to the pinned style pack")
        if str(execution_trace.get("layout_variant_used")) != "spring":
            raise RuntimeError("baseline rendering profile did not use the pinned spring layout")
        if context_elements:
            raise RuntimeError("baseline rendering profile unexpectedly added context")
        if bool(noise.get("applied")):
            raise RuntimeError("baseline rendering profile unexpectedly applied raster noise")
    elif profile.slug == "color_palette":
        if information_style.get("style_pack") != "clean_default:warm_editorial:none":
            raise RuntimeError("palette rendering profile did not resolve to the pinned style pack")
    elif profile.slug == "typeface":
        if panel_geometry.get("font_family") != "eb_garamond":
            raise RuntimeError("typeface rendering profile did not use the pinned font")
    elif profile.slug == "layout":
        if str(execution_trace.get("layout_variant_used")) != "circular":
            raise RuntimeError("layout rendering profile did not use the pinned circular layout")
    elif profile.slug == "report_context":
        if not context_elements:
            raise RuntimeError("report-context profile did not render any context elements")
    elif profile.slug == "raster_noise":
        edits = noise.get("edits")
        if not bool(noise.get("applied")) or not isinstance(edits, list):
            raise RuntimeError("raster-noise profile did not apply its pinned edit")
        if [str(edit.get("type")) for edit in edits if isinstance(edit, Mapping)] != ["gaussian_noise"]:
            raise RuntimeError("raster-noise profile applied an unexpected edit")


def _build_rendering_variation_examples(repo_root: Path, output: Path) -> dict[str, Any]:
    """Render one semantic node-link instance under six controlled visual profiles."""

    repo_root_text = str(repo_root)
    if repo_root_text not in sys.path:
        sys.path.insert(0, repo_root_text)
    from trace.tasks.registry import create_task

    semantic_hashes: set[str] = set()
    prompt_hashes: set[str] = set()
    answer_records: set[str] = set()
    image_hashes: set[str] = set()
    profile_records: list[dict[str, Any]] = []
    baseline_size: tuple[int, int] | None = None
    baseline_content_bbox: list[Any] | None = None
    baseline_layout_variant: str | None = None

    with tempfile.TemporaryDirectory(prefix="trace-render-variation-sources-") as temporary_directory:
        source_dir = Path(temporary_directory)
        tiles: list[str] = []
        for index, profile in enumerate(RENDER_VARIATION_PROFILES):
            params = _deep_merge_mapping(RENDER_VARIATION_BASE_PARAMS, profile.params_override)
            task = create_task(RENDER_VARIATION_TASK_ID)
            generated = task.generate(
                RENDER_VARIATION_INSTANCE_SEED,
                params=params,
                max_attempts=100,
            )
            if str(generated.query_id) != RENDER_VARIATION_QUERY_ID:
                raise RuntimeError(
                    f"{profile.label} selected query {generated.query_id!r}; expected {RENDER_VARIATION_QUERY_ID!r}"
                )

            semantic_record = _render_variation_semantic_record(generated)
            semantic_hash = _json_sha256(semantic_record)
            prompt_hash = hashlib.sha256(str(generated.prompt).encode("utf-8")).hexdigest()
            answer_record = json.dumps(
                {"type": str(generated.answer_gt.type), "value": generated.answer_gt.value},
                sort_keys=True,
                separators=(",", ":"),
            )
            semantic_hashes.add(str(semantic_hash))
            prompt_hashes.add(str(prompt_hash))
            answer_records.add(str(answer_record))

            image_path = source_dir / f"{index:02d}_{profile.slug}.png"
            generated.image.convert("RGB").save(
                image_path,
                format="PNG",
                dpi=(300, 300),
                optimize=True,
            )
            image_hash = _sha256(image_path)
            image_hashes.add(str(image_hash))

            render_spec = generated.trace_payload.get("render_spec")
            if not isinstance(render_spec, Mapping):
                raise RuntimeError(f"{profile.label} is missing render_spec")
            execution_trace = generated.trace_payload.get("execution_trace")
            if not isinstance(execution_trace, Mapping):
                raise RuntimeError(f"{profile.label} is missing execution_trace")
            _validate_render_variation_profile(
                profile=profile,
                render_spec=render_spec,
                execution_trace=execution_trace,
            )
            image_size = tuple(int(value) for value in generated.image.size)
            panel_geometry = render_spec.get("panel_geometry")
            surface_style = render_spec.get("style")
            if not isinstance(panel_geometry, Mapping) or not isinstance(surface_style, Mapping):
                raise RuntimeError(f"{profile.label} is missing graph render metadata")
            content_bbox = list(panel_geometry.get("scene_content_xyxy", []))
            layout_variant = str(execution_trace.get("layout_variant_used", ""))
            if profile.slug == "baseline":
                baseline_size = image_size
                baseline_content_bbox = list(content_bbox)
                baseline_layout_variant = str(layout_variant)
            elif image_size != baseline_size:
                raise RuntimeError(f"{profile.label} changed the fixed canvas dimensions")
            if profile.slug == "layout" and layout_variant == baseline_layout_variant:
                raise RuntimeError("layout profile did not change the graph layout")

            information_style = panel_geometry.get("information_scene_style")
            noise = surface_style.get("post_image_noise_meta")
            if not isinstance(information_style, Mapping) or not isinstance(noise, Mapping):
                raise RuntimeError(f"{profile.label} is missing graph style metadata")
            context_elements = panel_geometry.get("context_text_elements", [])
            profile_records.append(
                {
                    "label": str(profile.label),
                    "slug": str(profile.slug),
                    "controlled_axis": str(profile.controlled_axis),
                    "realization_summary": str(profile.realization_summary),
                    "params_override": profile.params_override,
                    "image_sha256": str(image_hash),
                    "image_size": list(image_size),
                    "semantic_sha256": str(semantic_hash),
                    "prompt_sha256": str(prompt_hash),
                    "answer_gt": json.loads(answer_record),
                    "render_metadata": {
                        "style_pack": information_style.get("style_pack"),
                        "treatment": information_style.get("treatment"),
                        "palette_id": information_style.get("palette_id"),
                        "font_family": panel_geometry.get("font_family"),
                        "content_bbox_px": list(content_bbox),
                        "baseline_content_bbox_px": list(baseline_content_bbox or []),
                        "layout_variant": str(layout_variant),
                        "layout_transform_variant": execution_trace.get("layout_transform_variant"),
                        "context_element_count": len(context_elements) if isinstance(context_elements, list) else 0,
                        "context_block_reservation": panel_geometry.get("context_block_reservation"),
                        "post_image_noise": dict(noise),
                    },
                }
            )
            tiles.append(
                rf"\variationtile{{\detokenize{{{image_path.resolve().as_posix()}}}}}"
                rf"{{{chr(65 + index)}}}{{{_tex_escape(profile.label)}}}"
            )

        if len(semantic_hashes) != 1 or len(prompt_hashes) != 1 or len(answer_records) != 1:
            raise RuntimeError("rendering profiles changed the fixed task semantics, prompt, or typed answer")
        if len(image_hashes) != len(RENDER_VARIATION_PROFILES):
            raise RuntimeError("two rendering profiles produced identical images")

        source = "\n".join(
            (
                r"\documentclass[border=8pt]{standalone}",
                r"\usepackage[T1]{fontenc}",
                r"\usepackage{graphicx}",
                r"\usepackage{xcolor}",
                r"\pdfinfoomitdate=1",
                r"\pdftrailerid{}",
                r"\pdfsuppressptexinfo=-1",
                r"\definecolor{tileborder}{RGB}{190,198,208}",
                r"\setlength{\fboxsep}{3pt}",
                r"\setlength{\fboxrule}{0.5pt}",
                r"\newcommand{\variationtile}[3]{%",
                r"  \begin{minipage}[t]{3.48in}%",
                r"    \centering",
                r"    \fcolorbox{tileborder}{white}{\parbox[c][2.18in][c]{3.40in}{\centering\includegraphics[width=3.38in,height=2.14in,keepaspectratio]{#1}}}%",
                r"    \par\vspace{2pt}{\sffamily\bfseries\fontsize{14}{15}\selectfont #2. #3}\vspace{2pt}%",
                r"  \end{minipage}%",
                r"}",
                r"\begin{document}",
                r"\begin{minipage}{10.75in}",
                r"\centering",
                r"\noindent\makebox[\linewidth][c]{" + r"\hspace{0.08in}".join(tiles[:3]) + r"}\par\vspace{0.09in}",
                r"\noindent\makebox[\linewidth][c]{" + r"\hspace{0.08in}".join(tiles[3:]) + r"}",
                r"\end{minipage}",
                r"\end{document}",
                "",
            )
        )
        _compile_standalone_pdf(
            source=source,
            output=output,
            basename="rendering_variation_examples",
            temporary_prefix="trace-render-variation-pdf-",
        )

    return {
        "task_id": RENDER_VARIATION_TASK_ID,
        "query_id": RENDER_VARIATION_QUERY_ID,
        "instance_seed": int(RENDER_VARIATION_INSTANCE_SEED),
        "base_params": RENDER_VARIATION_BASE_PARAMS,
        "semantic_sha256": next(iter(semantic_hashes)),
        "prompt_sha256": next(iter(prompt_hashes)),
        "answer_gt": json.loads(next(iter(answer_records))),
        "profiles": profile_records,
    }


def _build_rendering_variation_profile_table(
    rendering_variation: Mapping[str, Any],
    output: Path,
) -> None:
    """Write the compact appendix table paired with the rendering sweep."""

    profiles = rendering_variation.get("profiles")
    if not isinstance(profiles, list) or len(profiles) != len(RENDER_VARIATION_PROFILES):
        raise RuntimeError("rendering-variation provenance has an unexpected profile inventory")
    rows = [
        "    "
        + f"{_tex_escape(str(profile['label']))} & "
        + f"{_tex_escape(str(profile['controlled_axis']))} & "
        + f"{_tex_escape(str(profile['realization_summary']))} "
        + r"\\"
        for profile in profiles
    ]
    source = "\n".join(
        (
            "% Generated by paper/trace/scripts/build_method_figures.py; do not edit manually.",
            r"\begin{table}[h]",
            r"  \centering",
            r"  \scriptsize",
            r"  \setlength{\tabcolsep}{4pt}",
            r"  \renewcommand{\arraystretch}{1.08}",
            r"  \caption{Controlled profiles in the fixed-instance rendering sweep.}",
            r"  \label{tab:rendering-variation-profiles}",
            r"  \begin{tabular}{@{}p{0.18\linewidth}p{0.18\linewidth}p{0.53\linewidth}@{}}",
            r"    \toprule",
            r"    Profile & Controlled axis & Realization \\",
            r"    \midrule",
            *rows,
            r"    \bottomrule",
            r"  \end{tabular}",
            r"\end{table}",
            "",
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source, encoding="utf-8")


def _build_rendering_variation_pipeline(output: Path) -> None:
    canvas = Image.new("RGB", (3000, 1800), PAPER)
    draw = ImageDraw.Draw(canvas)
    heading = _font(48, bold=True)
    body = _font(40)
    small = _font(30)
    stages = (
        ("1  Semantic state", (40, 45, 910, 665), BLUE, ("objects and values", "relations and operands", "answer-bearing placement")),
        ("2  Render profile", (1065, 45, 1935, 665), PURPLE, ("canvas and background", "palette and typography", "materials and scene skin")),
        ("3  Layout realization", (2090, 45, 2960, 665), TEAL, ("panels and spacing", "camera and framing", "unit, offset, scale jitter")),
        ("4  Draw scene content", (2090, 760, 2960, 1380), ORANGE, ("marks, objects, text", "options and legends", "scene-local context")),
        ("5  Project and check", (1065, 760, 1935, 1380), GREEN, ("final coordinates", "visibility and contrast", "collision and fit checks")),
        ("6  Optional finishing", (40, 760, 910, 1380), (176, 75, 87), ("non-answer context", "tone and compression", "noise and texture")),
    )
    for title, box, color, lines in stages:
        _rounded_card(draw, box, radius=22, width=4, outline=color)
        draw.rounded_rectangle((box[0], box[1], box[2], box[1] + 96), radius=22, fill=color)
        draw.rectangle((box[0], box[1] + 70, box[2], box[1] + 96), fill=color)
        _center_text(draw, (box[0] + 10, box[1] + 10, box[2] - 10, box[1] + 88), title, heading, fill=(255, 255, 255))
        y = box[1] + 155
        for line in lines:
            draw.ellipse((box[0] + 35, y + 9, box[0] + 49, y + 23), fill=color)
            draw.text((box[0] + 67, y), line, font=body, fill=INK)
            y += 105
        if title.startswith("1"):
            label = "Can change task result"
        elif title.startswith("5"):
            label = "Uses final geometry"
        elif title.startswith("6"):
            label = "Answer contract preserved"
        else:
            label = "Render-only if unqueried"
        draw.rounded_rectangle((box[0] + 38, box[3] - 120, box[2] - 38, box[3] - 42), radius=15, fill=(246, 247, 249), outline=LINE, width=2)
        _center_text(draw, (box[0] + 46, box[3] - 116, box[2] - 46, box[3] - 44), label, small, fill=color)

    for left_index, right_index in ((0, 1), (1, 2)):
        left = stages[left_index][1]
        right = stages[right_index][1]
        _draw_arrow(draw, (left[2] + 18, 355), (right[0] - 18, 355), fill=MUTED, width=9)
    stage_three = stages[2][1]
    stage_four = stages[3][1]
    _draw_arrow(draw, ((stage_three[0] + stage_three[2]) // 2, stage_three[3] + 18), ((stage_four[0] + stage_four[2]) // 2, stage_four[1] - 18), fill=MUTED, width=9)
    for start_index, end_index in ((3, 4), (4, 5)):
        start_box = stages[start_index][1]
        end_box = stages[end_index][1]
        _draw_arrow(draw, (start_box[0] - 18, 1070), (end_box[2] + 18, 1070), fill=MUTED, width=9)

    draw.rounded_rectangle((40, 1460, 2960, 1755), radius=24, fill=(240, 244, 248), outline=(189, 202, 216), width=3)
    draw.line((1510, 1485, 1510, 1730), fill=(189, 202, 216), width=3)
    draw.text((82, 1500), "Semantic placement vs. render placement", font=heading, fill=BLUE)
    _draw_wrapped(
        draw,
        (82, 1575),
        "Placement that determines a spatial answer belongs to scene state; harmless translation, spacing, scale, and camera jitter belong to visual realization.",
        body,
        max_width=1350,
        fill=INK,
        line_gap=8,
    )
    draw.text((1580, 1500), "Deterministic realization", font=heading, fill=PURPLE)
    _draw_wrapped(
        draw,
        (1580, 1575),
        "Scene-specific finishing order may differ, but every enabled choice derives from the instance seed and is recorded in trace metadata.",
        body,
        max_width=1280,
        fill=INK,
        line_gap=8,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", dpi=(300, 300), optimize=True)


def _git_head(repo_root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_root, text=True).strip()


def _source_record(sample: LoadedSample, repo_root: Path) -> dict[str, Any]:
    record = asdict(sample.spec)
    record["image_path"] = str(sample.image_path.relative_to(repo_root))
    record["data_path"] = str(sample.data_path.relative_to(repo_root))
    record["image_size"] = list(sample.image.size)
    return record


def _output_record(path: Path, paper_root: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".pdf":
        info = subprocess.check_output(["pdfinfo", str(path)], text=True)
        match = re.search(r"^Page size:\s+([0-9.]+) x ([0-9.]+) pts", info, flags=re.MULTILINE)
        if match is None:
            raise RuntimeError(f"could not read PDF page size for {path}")
        return {
            "path": str(path.relative_to(paper_root)),
            "sha256": _sha256(path),
            "media_type": "application/pdf",
            "page_size_points": [float(match.group(1)), float(match.group(2))],
        }
    if path.suffix.lower() == ".tex":
        return {
            "path": str(path.relative_to(paper_root)),
            "sha256": _sha256(path),
            "media_type": "application/x-tex",
            "line_count": len(path.read_text(encoding="utf-8").splitlines()),
        }
    with Image.open(path) as image:
        size = list(image.size)
    return {
        "path": str(path.relative_to(paper_root)),
        "sha256": _sha256(path),
        "media_type": "image/png",
        "image_size": size,
    }


def _unique_specs(groups: Iterable[Iterable[SampleSpec]]) -> list[SampleSpec]:
    seen: set[tuple[str, str, int]] = set()
    result: list[SampleSpec] = []
    for group in groups:
        for spec in group:
            key = (spec.task_id, spec.query_id, spec.index)
            if key not in seen:
                seen.add(key)
                result.append(spec)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--paper-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    paper_root = args.paper_root.resolve()

    all_specs = _unique_specs((MONTAGE_SPECS, BOUNDARY_SPECS))
    source_samples = [_load_sample(repo_root, spec) for spec in all_specs]
    montage_samples = [_load_sample(repo_root, spec) for spec in MONTAGE_SPECS]
    boundary_samples = [_load_sample(repo_root, spec) for spec in BOUNDARY_SPECS]
    running_sample = _load_sample(repo_root, RUNNING_SPEC)
    coverage = _load_environment_coverage(repo_root)
    figures_dir = paper_root / "figures"
    tables_dir = paper_root / "tables"
    outputs = (
        figures_dir / "domain_montage.pdf",
        figures_dir / "reachable_region_pipeline.png",
        figures_dir / "taxonomy_boundaries.png",
        figures_dir / "answer_reward_summary.png",
        figures_dir / "rendering_variation_pipeline.png",
        figures_dir / "rendering_variation_examples.pdf",
        figures_dir / "domain_operation_matrix.png",
        figures_dir / "domain_landscape.png",
        tables_dir / "rendering_variation_profiles.tex",
    )
    _build_domain_montage(montage_samples, outputs[0])
    _build_reachable_pipeline(running_sample, outputs[1])
    _build_taxonomy_boundaries(boundary_samples, outputs[2])
    _build_answer_reward_summary(coverage, outputs[3])
    _build_rendering_variation_pipeline(outputs[4])
    rendering_variation = _build_rendering_variation_examples(repo_root, outputs[5])
    _build_domain_operation_matrix(coverage, outputs[6])
    _build_domain_landscape(coverage, outputs[7])
    _build_rendering_variation_profile_table(rendering_variation, outputs[8])

    manifest = {
        "schema_version": "trace_paper_method_figures_v9",
        "source_repository_head": _git_head(repo_root),
        "pillow_version": pillow_version,
        "fonts": {
            "regular_sha256": _sha256(FONT_REGULAR),
            "bold_sha256": _sha256(FONT_BOLD),
        },
        "sources": [_source_record(sample, repo_root) for sample in source_samples],
        "environment_coverage": coverage,
        "rendering_variation": rendering_variation,
        "outputs": [_output_record(path, paper_root) for path in outputs],
    }
    manifest_path = paper_root / "provenance" / "method_figures.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for path in outputs:
        print(f"[ok] wrote {path}")
    print(f"[ok] wrote {manifest_path}")


if __name__ == "__main__":
    main()
