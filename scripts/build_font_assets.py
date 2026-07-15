#!/usr/bin/env python3
"""Build shared Trace font assets from permissively licensed font sources."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
FONT_ROOT = REPO_ROOT / "assets" / "fonts"

GOOGLE_FONTS_RAW_BASE = "https://raw.githubusercontent.com/google/fonts/main"
GOOGLE_FONTS_TREE_URL = "https://api.github.com/repos/google/fonts/git/trees/main?recursive=1"
GOOGLE_FONTS_CATALOG_URL = "https://fonts.google.com/metadata/fonts"
SCRIPT_VERSION = "font_assets_v0"
TARGET_FAMILY_COUNT = 500

SAFE_LICENSE_DIRS = {
    "ofl": ("OFL-1.1", "OFL.txt"),
    "apache": ("Apache-2.0", "APACHE2.txt"),
}

CATEGORY_TARGETS = {
    "Sans Serif": 190,
    "Serif": 105,
    "Display": 110,
    "Handwriting": 65,
    "Monospace": 30,
}

MAX_CATALOG_SIZE_BYTES = 2_000_000

_EXCLUDED_FAMILY_PATTERNS = (
    "emoji",
    "symbol",
    "icons",
    "icon",
    "material",
    "math",
    "music",
    "braille",
    "morse",
    "hieroglyph",
    "cuneiform",
    "mayan",
    "barcode",
    "flow block",
    "flow circular",
    "flow rounded",
    "nabla",
    "frijole",
    "nosifer",
    "butcherman",
    "creepster",
    "eater",
    "rubik beastly",
    "rubik broken fax",
    "rubik bubbles",
    "rubik burned",
    "rubik dirt",
    "rubik doodle",
    "rubik gemstones",
    "rubik glitch",
    "rubik iso",
    "rubik lines",
    "rubik maps",
    "rubik marker hatch",
    "rubik maze",
    "rubik microbe",
    "rubik moonrocks",
    "rubik puddles",
    "rubik scribble",
    "rubik spray paint",
    "rubik vinyl",
    "rubik wet paint",
)


@dataclass(frozen=True)
class FontFamilySpec:
    key: str
    family_name: str
    source_dir: str
    tags: tuple[str, ...]
    license: str = "OFL-1.1"


PREFERRED_FONT_FAMILIES: tuple[FontFamilySpec, ...] = (
    FontFamilySpec("roboto", "Roboto", "ofl/roboto", ("sans", "ui", "neutral", "variable")),
    FontFamilySpec("open_sans", "Open Sans", "ofl/opensans", ("sans", "ui", "neutral", "variable")),
    FontFamilySpec("lato", "Lato", "ofl/lato", ("sans", "humanist", "static")),
    FontFamilySpec("montserrat", "Montserrat", "ofl/montserrat", ("sans", "geometric", "variable")),
    FontFamilySpec("source_sans_3", "Source Sans 3", "ofl/sourcesans3", ("sans", "humanist", "variable")),
    FontFamilySpec("inter", "Inter", "ofl/inter", ("sans", "ui", "neutral", "variable")),
    FontFamilySpec("nunito", "Nunito", "ofl/nunito", ("sans", "rounded", "variable")),
    FontFamilySpec("work_sans", "Work Sans", "ofl/worksans", ("sans", "ui", "variable")),
    FontFamilySpec("ibm_plex_sans", "IBM Plex Sans", "ofl/ibmplexsans", ("sans", "technical", "variable")),
    FontFamilySpec("atkinson_hyperlegible", "Atkinson Hyperlegible", "ofl/atkinsonhyperlegible", ("sans", "accessible", "static")),
    FontFamilySpec("public_sans", "Public Sans", "ofl/publicsans", ("sans", "ui", "variable")),
    FontFamilySpec("karla", "Karla", "ofl/karla", ("sans", "humanist", "variable")),
    FontFamilySpec("rubik", "Rubik", "ofl/rubik", ("sans", "rounded", "variable")),
    FontFamilySpec("barlow", "Barlow", "ofl/barlow", ("sans", "technical", "static")),
    FontFamilySpec("barlow_condensed", "Barlow Condensed", "ofl/barlowcondensed", ("sans", "condensed", "static")),
    FontFamilySpec("oswald", "Oswald", "ofl/oswald", ("sans", "condensed", "variable")),
    FontFamilySpec("merriweather", "Merriweather", "ofl/merriweather", ("serif", "readable", "variable")),
    FontFamilySpec("lora", "Lora", "ofl/lora", ("serif", "readable", "variable")),
    FontFamilySpec("bitter", "Bitter", "ofl/bitter", ("serif", "slab", "variable")),
    FontFamilySpec("source_serif_4", "Source Serif 4", "ofl/sourceserif4", ("serif", "readable", "variable")),
    FontFamilySpec("roboto_serif", "Roboto Serif", "ofl/robotoserif", ("serif", "technical", "variable")),
    FontFamilySpec("playfair_display", "Playfair Display", "ofl/playfairdisplay", ("serif", "display", "variable")),
    FontFamilySpec("crimson_pro", "Crimson Pro", "ofl/crimsonpro", ("serif", "book", "variable")),
    FontFamilySpec("libre_franklin", "Libre Franklin", "ofl/librefranklin", ("sans", "news", "variable")),
    FontFamilySpec("roboto_mono", "Roboto Mono", "ofl/robotomono", ("mono", "technical", "variable")),
    FontFamilySpec("source_code_pro", "Source Code Pro", "ofl/sourcecodepro", ("mono", "technical", "variable")),
    FontFamilySpec("ibm_plex_mono", "IBM Plex Mono", "ofl/ibmplexmono", ("mono", "technical", "variable")),
    FontFamilySpec("jetbrains_mono", "JetBrains Mono", "ofl/jetbrainsmono", ("mono", "technical", "variable")),
    FontFamilySpec("inconsolata", "Inconsolata", "ofl/inconsolata", ("mono", "technical", "variable")),
    FontFamilySpec("noto_sans_mono", "Noto Sans Mono", "ofl/notosansmono", ("mono", "technical", "variable")),
    FontFamilySpec("noto_sans", "Noto Sans", "ofl/notosans", ("sans", "ui", "neutral", "variable")),
    FontFamilySpec("dm_sans", "DM Sans", "ofl/dmsans", ("sans", "ui", "geometric", "variable")),
    FontFamilySpec("poppins", "Poppins", "ofl/poppins", ("sans", "geometric", "variable")),
    FontFamilySpec("raleway", "Raleway", "ofl/raleway", ("sans", "elegant", "variable")),
    FontFamilySpec("quicksand", "Quicksand", "ofl/quicksand", ("sans", "rounded", "variable")),
    FontFamilySpec("comfortaa", "Comfortaa", "ofl/comfortaa", ("sans", "rounded", "variable")),
    FontFamilySpec("lexend", "Lexend", "ofl/lexend", ("sans", "accessible", "variable")),
    FontFamilySpec("figtree", "Figtree", "ofl/figtree", ("sans", "ui", "variable")),
    FontFamilySpec("manrope", "Manrope", "ofl/manrope", ("sans", "ui", "variable")),
    FontFamilySpec("mulish", "Mulish", "ofl/mulish", ("sans", "humanist", "variable")),
    FontFamilySpec("urbanist", "Urbanist", "ofl/urbanist", ("sans", "geometric", "variable")),
    FontFamilySpec("outfit", "Outfit", "ofl/outfit", ("sans", "geometric", "variable")),
    FontFamilySpec("fira_sans", "Fira Sans", "ofl/firasans", ("sans", "humanist", "variable")),
    FontFamilySpec("titillium_web", "Titillium Web", "ofl/titilliumweb", ("sans", "technical", "variable")),
    FontFamilySpec("archivo", "Archivo", "ofl/archivo", ("sans", "technical", "variable")),
    FontFamilySpec("josefin_sans", "Josefin Sans", "ofl/josefinsans", ("sans", "geometric", "variable")),
    FontFamilySpec("heebo", "Heebo", "ofl/heebo", ("sans", "ui", "variable")),
    FontFamilySpec("kanit", "Kanit", "ofl/kanit", ("sans", "technical", "variable")),
    FontFamilySpec("exo_2", "Exo 2", "ofl/exo2", ("sans", "technical", "variable")),
    FontFamilySpec("space_grotesk", "Space Grotesk", "ofl/spacegrotesk", ("sans", "technical", "variable")),
    FontFamilySpec("noto_serif", "Noto Serif", "ofl/notoserif", ("serif", "readable", "variable")),
    FontFamilySpec("pt_serif", "PT Serif", "ofl/ptserif", ("serif", "readable", "static")),
    FontFamilySpec("eb_garamond", "EB Garamond", "ofl/ebgaramond", ("serif", "book", "variable")),
    FontFamilySpec("libre_baskerville", "Libre Baskerville", "ofl/librebaskerville", ("serif", "book", "static")),
    FontFamilySpec("vollkorn", "Vollkorn", "ofl/vollkorn", ("serif", "readable", "variable")),
    FontFamilySpec("spectral", "Spectral", "ofl/spectral", ("serif", "editorial", "variable")),
    FontFamilySpec("cardo", "Cardo", "ofl/cardo", ("serif", "book", "static")),
    FontFamilySpec("cormorant_garamond", "Cormorant Garamond", "ofl/cormorantgaramond", ("serif", "editorial", "variable")),
    FontFamilySpec("domine", "Domine", "ofl/domine", ("serif", "readable", "variable")),
    FontFamilySpec("zilla_slab", "Zilla Slab", "ofl/zillaslab", ("serif", "slab", "static")),
    FontFamilySpec("alegreya", "Alegreya", "ofl/alegreya", ("serif", "book", "variable")),
    FontFamilySpec("fira_mono", "Fira Mono", "ofl/firamono", ("mono", "technical", "static")),
    FontFamilySpec("space_mono", "Space Mono", "ofl/spacemono", ("mono", "technical", "static")),
    FontFamilySpec("courier_prime", "Courier Prime", "ofl/courierprime", ("mono", "typewriter", "static")),
    FontFamilySpec("red_hat_mono", "Red Hat Mono", "ofl/redhatmono", ("mono", "technical", "variable")),
    FontFamilySpec("oxygen_mono", "Oxygen Mono", "ofl/oxygenmono", ("mono", "technical", "static")),
    FontFamilySpec("cousine", "Cousine", "ofl/cousine", ("mono", "technical", "static")),
    FontFamilySpec("bebas_neue", "Bebas Neue", "ofl/bebasneue", ("sans", "condensed", "display", "static")),
    FontFamilySpec("anton", "Anton", "ofl/anton", ("sans", "condensed", "display", "static")),
    FontFamilySpec("archivo_black", "Archivo Black", "ofl/archivoblack", ("sans", "display", "static")),
    FontFamilySpec("abril_fatface", "Abril Fatface", "ofl/abrilfatface", ("serif", "display", "static")),
    FontFamilySpec("alfa_slab_one", "Alfa Slab One", "ofl/alfaslabone", ("serif", "slab", "display", "static")),
    FontFamilySpec("righteous", "Righteous", "ofl/righteous", ("sans", "display", "static")),
    FontFamilySpec("fredoka", "Fredoka", "ofl/fredoka", ("sans", "rounded", "display", "variable")),
    FontFamilySpec("baloo_2", "Baloo 2", "ofl/baloo2", ("sans", "rounded", "display", "variable")),
    FontFamilySpec("boogaloo", "Boogaloo", "ofl/boogaloo", ("sans", "display", "playful", "static")),
    FontFamilySpec("bangers", "Bangers", "ofl/bangers", ("sans", "display", "comic", "static")),
    FontFamilySpec("graduate", "Graduate", "ofl/graduate", ("serif", "slab", "display", "static")),
    FontFamilySpec("press_start_2p", "Press Start 2P", "ofl/pressstart2p", ("mono", "pixel", "display", "static")),
    FontFamilySpec("audiowide", "Audiowide", "ofl/audiowide", ("sans", "technical", "display", "static")),
    FontFamilySpec("black_ops_one", "Black Ops One", "ofl/blackopsone", ("sans", "stencil", "display", "static")),
    FontFamilySpec("orbitron", "Orbitron", "ofl/orbitron", ("sans", "technical", "display", "variable")),
    FontFamilySpec("caveat", "Caveat", "ofl/caveat", ("handwriting", "casual", "variable")),
    FontFamilySpec("kalam", "Kalam", "ofl/kalam", ("handwriting", "casual", "static")),
    FontFamilySpec("patrick_hand", "Patrick Hand", "ofl/patrickhand", ("handwriting", "casual", "static")),
    FontFamilySpec("architects_daughter", "Architects Daughter", "ofl/architectsdaughter", ("handwriting", "casual", "static")),
    FontFamilySpec("handlee", "Handlee", "ofl/handlee", ("handwriting", "casual", "static")),
    FontFamilySpec("gaegu", "Gaegu", "ofl/gaegu", ("handwriting", "casual", "static")),
    FontFamilySpec("gloria_hallelujah", "Gloria Hallelujah", "ofl/gloriahallelujah", ("handwriting", "casual", "static")),
    FontFamilySpec("indie_flower", "Indie Flower", "ofl/indieflower", ("handwriting", "casual", "static")),
    FontFamilySpec("covered_by_your_grace", "Covered By Your Grace", "ofl/coveredbyyourgrace", ("handwriting", "casual", "static")),
    FontFamilySpec("neucha", "Neucha", "ofl/neucha", ("handwriting", "casual", "static")),
    FontFamilySpec("dancing_script", "Dancing Script", "ofl/dancingscript", ("script", "handwriting", "variable")),
    FontFamilySpec("pacifico", "Pacifico", "ofl/pacifico", ("script", "display", "static")),
    FontFamilySpec("lobster", "Lobster", "ofl/lobster", ("script", "display", "static")),
    FontFamilySpec("lobster_two", "Lobster Two", "ofl/lobstertwo", ("script", "display", "static")),
    FontFamilySpec("courgette", "Courgette", "ofl/courgette", ("script", "display", "static")),
    FontFamilySpec("kaushan_script", "Kaushan Script", "ofl/kaushanscript", ("script", "display", "static")),
    FontFamilySpec("cookie", "Cookie", "ofl/cookie", ("script", "display", "static")),
    FontFamilySpec("merienda", "Merienda", "ofl/merienda", ("script", "handwriting", "variable")),
)


def _url_for_parts(*parts: str) -> str:
    quoted = "/".join(urllib.parse.quote(str(part), safe="") for part in parts)
    return f"{GOOGLE_FONTS_RAW_BASE}/{quoted}"


def _family_key(value: str) -> str:
    key = re.sub(r"[^0-9a-z]+", "_", str(value).strip().casefold())
    return re.sub(r"_+", "_", key).strip("_")


def _source_dir_key(value: str) -> str:
    return re.sub(r"[^0-9a-z]+", "", str(value).strip().casefold())


def _fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        str(url),
        headers={
            "User-Agent": "trace-font-asset-builder/1.0",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        dest.write_bytes(response.read())


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(
        str(url),
        headers={
            "User-Agent": "trace-font-asset-builder/1.0",
            "Accept": "text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read().decode("utf-8")


def _fetch_json(url: str) -> Mapping[str, object]:
    request = urllib.request.Request(
        str(url),
        headers={
            "User-Agent": "trace-font-asset-builder/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        text = response.read().decode("utf-8")
    if text.startswith(")]}'"):
        text = text.split("\n", 1)[1]
    payload = json.loads(text)
    if not isinstance(payload, Mapping):
        raise ValueError(f"expected mapping JSON from {url}")
    return payload


def _fetch_google_font_source_dirs() -> dict[str, tuple[str, str]]:
    payload = _fetch_json(GOOGLE_FONTS_TREE_URL)
    tree = payload.get("tree", [])
    if not isinstance(tree, Sequence):
        raise ValueError("Google Fonts tree response is missing tree list")
    files_by_dir: dict[tuple[str, str], set[str]] = {}
    source_dirs: dict[str, tuple[str, str]] = {}
    for item in tree:
        if not isinstance(item, Mapping):
            continue
        path = str(item.get("path", ""))
        parts = path.split("/")
        if len(parts) != 3:
            continue
        license_dir, family_dir, filename = parts
        if license_dir not in SAFE_LICENSE_DIRS:
            continue
        files_by_dir.setdefault((str(license_dir), str(family_dir)), set()).add(str(filename))
    license_filenames = {"OFL.txt", "APACHE2.txt", "LICENSE.txt", "UFL.txt"}
    for (license_dir, family_dir), filenames in files_by_dir.items():
        if "METADATA.pb" not in filenames:
            continue
        if not bool(filenames & license_filenames):
            continue
        source_dirs[_source_dir_key(family_dir)] = (str(license_dir), str(family_dir))
    return source_dirs


def _fetch_google_font_catalog() -> list[Mapping[str, object]]:
    payload = _fetch_json(GOOGLE_FONTS_CATALOG_URL)
    families = payload.get("familyMetadataList", [])
    if not isinstance(families, Sequence):
        raise ValueError("Google Fonts catalog response is missing familyMetadataList")
    return [record for record in families if isinstance(record, Mapping)]


def _catalog_sort_key(record: Mapping[str, object]) -> tuple[int, int, str]:
    def _int_value(key: str, default: int) -> int:
        try:
            return int(record.get(key, default))
        except Exception:
            return int(default)

    return (
        _int_value("popularity", 999999),
        _int_value("defaultSort", 999999),
        str(record.get("family", "")),
    )


def _catalog_family_allowed(record: Mapping[str, object], source_dirs: Mapping[str, tuple[str, str]]) -> bool:
    family = str(record.get("family", "")).strip()
    if not family:
        return False
    if _source_dir_key(family) not in source_dirs:
        return False
    if str(record.get("category", "")) not in CATEGORY_TARGETS:
        return False
    subsets = {str(value).casefold() for value in record.get("subsets", ())}
    if "latin" not in subsets:
        return False
    primary_script = str(record.get("primaryScript", "") or "")
    if primary_script and primary_script != "Latn":
        return False
    if bool(record.get("isBrandFont", False)):
        return False
    color_capabilities = record.get("colorCapabilities", [])
    if isinstance(color_capabilities, Sequence) and len(color_capabilities) > 0:
        return False
    if bool(record.get("isNoto", False)) and _family_key(family) not in {
        "noto_sans",
        "noto_serif",
        "noto_sans_mono",
    }:
        return False
    try:
        size = int(record.get("size", 0) or 0)
    except Exception:
        size = 0
    if size > MAX_CATALOG_SIZE_BYTES:
        return False
    lowered = family.casefold()
    return not any(pattern in lowered for pattern in _EXCLUDED_FAMILY_PATTERNS)


def _auto_tags_for_record(record: Mapping[str, object]) -> tuple[str, ...]:
    category = str(record.get("category", ""))
    tags: list[str] = []
    if category == "Sans Serif":
        tags.append("sans")
    elif category == "Serif":
        tags.append("serif")
    elif category == "Monospace":
        tags.append("mono")
    elif category == "Display":
        tags.append("display")
    elif category == "Handwriting":
        tags.append("handwriting")
    family = str(record.get("family", "")).casefold()
    if "script" in family or any(token in family for token in ("lobster", "pacifico", "cookie", "courgette")):
        tags.append("script")
    axes = record.get("axes", [])
    tags.append("variable" if isinstance(axes, Sequence) and len(axes) > 0 else "static")
    tags.append("google_auto")
    return tuple(dict.fromkeys(tags))


def _resolve_font_family_specs() -> tuple[FontFamilySpec, ...]:
    """Return the deterministic Trace font subset to vendor.

    The first families are the hand-curated stable core. The remainder are
    filled from the live Google Fonts catalog using conservative filters:
    permissive license dirs, Latin coverage, no color/symbol/emoji/icon/math
    families, bounded catalog size, and category quotas for visual variety.
    """

    selected: dict[str, FontFamilySpec] = {spec.key: spec for spec in PREFERRED_FONT_FAMILIES}
    source_dirs = _fetch_google_font_source_dirs()
    catalog = _fetch_google_font_catalog()
    by_key = {_family_key(str(record.get("family", ""))): record for record in catalog}

    category_counts: dict[str, int] = {category: 0 for category in CATEGORY_TARGETS}
    for spec in selected.values():
        record = by_key.get(_family_key(spec.family_name))
        category = str(record.get("category", "")) if record else ""
        if category in category_counts:
            category_counts[category] += 1

    candidates = [
        record
        for record in catalog
        if _catalog_family_allowed(record, source_dirs)
        and _family_key(str(record.get("family", ""))) not in selected
    ]
    candidates.sort(key=_catalog_sort_key)

    for category, target in CATEGORY_TARGETS.items():
        for record in candidates:
            if len(selected) >= TARGET_FAMILY_COUNT:
                break
            if category_counts.get(category, 0) >= int(target):
                break
            if str(record.get("category", "")) != category:
                continue
            family = str(record.get("family", ""))
            key = _family_key(family)
            if key in selected:
                continue
            license_dir, family_dir = source_dirs[_source_dir_key(family)]
            license_name = SAFE_LICENSE_DIRS[license_dir][0]
            selected[key] = FontFamilySpec(
                key=key,
                family_name=family,
                source_dir=f"{license_dir}/{family_dir}",
                tags=_auto_tags_for_record(record),
                license=license_name,
            )
            category_counts[category] = category_counts.get(category, 0) + 1

    for record in candidates:
        if len(selected) >= TARGET_FAMILY_COUNT:
            break
        family = str(record.get("family", ""))
        key = _family_key(family)
        if key in selected:
            continue
        license_dir, family_dir = source_dirs[_source_dir_key(family)]
        license_name = SAFE_LICENSE_DIRS[license_dir][0]
        selected[key] = FontFamilySpec(
            key=key,
            family_name=family,
            source_dir=f"{license_dir}/{family_dir}",
            tags=_auto_tags_for_record(record),
            license=license_name,
        )

    if len(selected) < TARGET_FAMILY_COUNT:
        raise RuntimeError(f"only selected {len(selected)} font families; target is {TARGET_FAMILY_COUNT}")
    return tuple(selected[key] for key in sorted(selected))


def _parse_metadata_fonts(metadata_text: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for block in re.findall(r"fonts\s*\{(.*?)\n\}", str(metadata_text), flags=re.DOTALL):
        filename_match = re.search(r'filename:\s*"([^"]+)"', block)
        style_match = re.search(r'style:\s*"([^"]+)"', block)
        weight_match = re.search(r"weight:\s*(\d+)", block)
        if not filename_match:
            continue
        records.append(
            {
                "filename": str(filename_match.group(1)),
                "style": str(style_match.group(1) if style_match else "normal"),
                "weight": int(weight_match.group(1) if weight_match else 400),
            }
        )
    return records


def _font_record_sort_key(record: Mapping[str, object], *, target_weight: int) -> tuple[int, int, str]:
    style = str(record.get("style", "normal"))
    weight = int(record.get("weight", 400))
    return (
        0 if style == "normal" else 1,
        abs(int(weight) - int(target_weight)),
        str(record.get("filename", "")),
    )


def _select_font_files(records: Sequence[Mapping[str, object]]) -> tuple[str, str]:
    normal_records = [record for record in records if str(record.get("style", "normal")) == "normal"]
    if not normal_records:
        normal_records = list(records)
    if not normal_records:
        raise ValueError("metadata has no font files")
    regular = sorted(normal_records, key=lambda record: _font_record_sort_key(record, target_weight=400))[0]
    bold = sorted(normal_records, key=lambda record: _font_record_sort_key(record, target_weight=700))[0]
    return str(regular["filename"]), str(bold["filename"])


def _download_license_file(*, license_dir: str, family_dir: str, dest_dir: Path) -> Path:
    preferred = SAFE_LICENSE_DIRS.get(str(license_dir), ("", "OFL.txt"))[1]
    candidates = [preferred, "OFL.txt", "APACHE2.txt", "LICENSE.txt", "UFL.txt"]
    tried: set[str] = set()
    last_error: Exception | None = None
    for filename in candidates:
        if filename in tried:
            continue
        tried.add(filename)
        dest = dest_dir / str(filename)
        try:
            _fetch(_url_for_parts(str(license_dir), str(family_dir), str(filename)), dest)
            return dest
        except Exception as exc:
            last_error = exc
            if dest.exists():
                dest.unlink()
    raise RuntimeError(f"could not fetch license for {license_dir}/{family_dir}") from last_error


def _write_readme() -> None:
    (FONT_ROOT / "README.md").write_text(
        "# Shared Font Assets\n\n"
        "This directory stores a curated Trace-vendored subset of permissively\n"
        "licensed fonts for deterministic visual variation in generated tasks.\n"
        "The current subset is downloaded from the Google Fonts GitHub repository\n"
        "and uses family-local license files recorded in `sources.json`.\n\n"
        "Task renderers should sample font families through\n"
        "`trace/tasks/shared/font_assets.py` and render them through\n"
        "`trace/tasks/shared/text_rendering.py`. Do not download font files at\n"
        "runtime generation time.\n\n"
        "Run:\n\n"
        "```bash\n"
        "python scripts/build_font_assets.py\n"
        "```\n",
        encoding="utf-8",
    )


def _source_metadata(family_records: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    return {
        "asset_version": SCRIPT_VERSION,
        "generated_by": "scripts/build_font_assets.py",
        "source_policy": (
            "Shared font assets are vendored from permissively licensed font repositories. "
            "Runtime generation must use local files and deterministic font-family sampling."
        ),
        "sources": {
            "google_fonts": {
                "description": "Google Fonts repository containing binary font files served by Google Fonts.",
                "repository_url": "https://github.com/google/fonts",
                "metadata_url": "https://github.com/google/fonts",
                "license_policy": "Each family directory contains its own license file; selected Trace families use SIL Open Font License 1.1.",
            }
        },
        "families": dict(sorted(family_records.items())),
    }


def main() -> None:
    if FONT_ROOT.exists():
        shutil.rmtree(FONT_ROOT)
    specs = _resolve_font_family_specs()
    family_records: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory(prefix="trace-font-assets-"):
        for spec in specs:
            source_parts = str(spec.source_dir).split("/")
            if len(source_parts) != 2:
                raise ValueError(f"expected license/family source dir: {spec.source_dir}")
            license_dir, family_dir = source_parts
            metadata_url = _url_for_parts(license_dir, family_dir, "METADATA.pb")
            metadata_text = _fetch_text(metadata_url)
            records = _parse_metadata_fonts(metadata_text)
            regular_filename, bold_filename = _select_font_files(records)
            dest_dir = FONT_ROOT / "google_fonts" / str(spec.key)
            metadata_path = dest_dir / "METADATA.pb"
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(metadata_text, encoding="utf-8")
            license_path = _download_license_file(
                license_dir=str(license_dir),
                family_dir=str(family_dir),
                dest_dir=dest_dir,
            )
            downloaded_files: dict[str, str] = {}
            for role, filename in (("regular", regular_filename), ("bold", bold_filename)):
                dest = dest_dir / str(filename)
                if not dest.exists():
                    _fetch(_url_for_parts(license_dir, family_dir, str(filename)), dest)
                downloaded_files[str(role)] = str(dest.relative_to(FONT_ROOT))
            family_records[str(spec.key)] = {
                "family_name": str(spec.family_name),
                "source_id": "google_fonts",
                "source_dir": str(spec.source_dir),
                "source_url": f"https://github.com/google/fonts/tree/main/{spec.source_dir}",
                "license": str(spec.license),
                "license_path": str(license_path.relative_to(FONT_ROOT)),
                "metadata_path": str(metadata_path.relative_to(FONT_ROOT)),
                "regular_path": str(downloaded_files["regular"]),
                "bold_path": str(downloaded_files["bold"]),
                "tags": list(spec.tags),
            }
    _write_readme()
    (FONT_ROOT / "sources.json").write_text(
        json.dumps(_source_metadata(family_records), indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"family_count": len(family_records), "families": sorted(family_records)}, indent=2))


if __name__ == "__main__":
    main()
