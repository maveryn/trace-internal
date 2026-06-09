#!/usr/bin/env python3
"""Build curated pages-domain decorative visual assets.

The output is intentionally separate from `assets/icons`: pages renderers use
these as non-answer visual anchors, section illustrations, and badge spots.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import tempfile
import urllib.request
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import cairosvg
from PIL import Image, ImageDraw, ImageFont, ImageOps


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = REPO_ROOT / "assets" / "pages" / "visual_assets"
RAW_ROOT = ASSET_ROOT / "raw"
NORMALIZED_ROOT = ASSET_ROOT / "normalized"
REVIEW_ROOT = ASSET_ROOT / "review"
LICENSE_ROOT = ASSET_ROOT / "licenses"
MANIFEST_PATH = ASSET_ROOT / "manifest.jsonl"
SOURCES_PATH = ASSET_ROOT / "sources.json"

NORM_SIZE_PX = 512
SCRIPT_VERSION = "pages_visual_assets_v1"
MIN_ROLE_COUNTS = {
    "hero_anchor": 100,
    "section_illustration": 100,
    "badge_spot": 100,
}
MAX_ROLE_COUNTS = {
    "hero_anchor": 500,
    "section_illustration": 500,
    "badge_spot": 500,
}

NISBN = "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/svg/emoji_u{codepoint}.svg"
MATERIAL_CONTENTS = "https://api.github.com/repos/google/material-design-icons/contents/src/{category}?ref=master"
MATERIAL_RAW = "https://raw.githubusercontent.com/google/material-design-icons/master/{path}"

FORBIDDEN_SVG_MARKERS = (
    "<script",
    "javascript:",
    "<foreignObject",
)

SOURCE_METADATA = {
    "noto_emoji": {
        "description": "Google Noto Emoji SVG image resources selected for page decorative assets.",
        "repository_url": "https://github.com/googlefonts/noto-emoji",
        "license": "Apache-2.0",
        "license_url": "https://www.apache.org/licenses/LICENSE-2.0",
        "local_license": "licenses/APACHE-2.0.txt",
        "source_revision": "main",
    },
    "material_design_icons": {
        "description": "Google Material Design Icons SVGs selected for page badges and section illustrations.",
        "repository_url": "https://github.com/google/material-design-icons",
        "license": "Apache-2.0",
        "license_url": "https://www.apache.org/licenses/LICENSE-2.0",
        "local_license": "licenses/APACHE-2.0.txt",
        "source_revision": "master",
    },
}

APACHE_LICENSE_TEXT = """Apache License
Version 2.0, January 2004
https://www.apache.org/licenses/

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


@dataclass(frozen=True)
class AssetSpec:
    asset_id: str
    source_id: str
    source_url: str
    category: str
    allowed_roles: tuple[str, ...]
    style: str
    render_mode: str
    source_label: str


HERO_CATEGORIES = {
    "people",
    "devices",
    "globe_map",
    "buildings_places",
    "finance_shopping",
    "education_documents",
    "health_science",
    "transport_travel",
    "sports_awards",
    "food_lifestyle",
    "tools_objects",
    "nature_weather",
}


def _slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        raise ValueError(f"invalid slug source: {value!r}")
    return text


def _noto_role_tuple(category: str) -> tuple[str, ...]:
    if str(category) in HERO_CATEGORIES:
        return ("hero_anchor", "section_illustration", "badge_spot")
    return ("section_illustration", "badge_spot")


def _noto_spec(codepoint: str, label: str, category: str) -> AssetSpec:
    clean_codepoint = str(codepoint).lower()
    return AssetSpec(
        asset_id=f"noto_{_slug(label)}",
        source_id="noto_emoji",
        source_url=NISBN.format(codepoint=clean_codepoint),
        category=str(category),
        allowed_roles=_noto_role_tuple(str(category)),
        style="color_emoji_flat",
        render_mode="color",
        source_label=str(label),
    )


NOTO_ASSETS: tuple[tuple[str, str, str], ...] = (
    # People and character-like anchors.
    ("1f600", "grinning_face", "people"),
    ("1f642", "slight_smile", "people"),
    ("1f464", "person_bust", "people"),
    ("1f465", "people_busts", "people"),
    ("1f9d2", "child", "people"),
    ("1f466", "boy", "people"),
    ("1f467", "girl", "people"),
    ("1f9d1", "adult", "people"),
    ("1f468", "man", "people"),
    ("1f469", "woman", "people"),
    ("1f9d3", "older_person", "people"),
    ("1f474", "older_man", "people"),
    ("1f475", "older_woman", "people"),
    ("1f477", "construction_worker", "people"),
    ("1f46e", "police_officer", "people"),
    ("1f575", "detective", "people"),
    ("1f482", "guard", "people"),
    ("1f9d1_200d_2695_fe0f", "health_worker", "people"),
    ("1f9d1_200d_1f393", "student", "people"),
    ("1f9d1_200d_1f3eb", "teacher", "people"),
    ("1f9d1_200d_1f4bb", "technologist", "people"),
    ("1f9d1_200d_1f52c", "scientist", "people"),
    ("1f9d1_200d_1f527", "mechanic", "people"),
    ("1f9d1_200d_1f3ed", "factory_worker", "people"),
    ("1f9d1_200d_1f4bc", "office_worker", "people"),
    ("1f9d1_200d_1f680", "astronaut", "people"),
    ("1f9d1_200d_1f692", "firefighter", "people"),
    ("1f9d1_200d_1f3a8", "artist", "people"),
    ("1f9d1_200d_2696_fe0f", "judge", "people"),
    ("1f483", "dancer", "people"),
    ("1f57a", "person_dancing", "people"),
    ("1f9cd", "standing_person", "people"),
    ("1f9ce", "kneeling_person", "people"),
    ("1f6b6", "pedestrian", "people"),
    ("1f3c3", "runner", "people"),
    ("1f9d8", "meditation_person", "people"),
    # Devices and office objects.
    ("1f4bb", "laptop", "devices"),
    ("1f5a5", "desktop_computer", "devices"),
    ("1f5a8", "printer", "devices"),
    ("1f4f1", "mobile_phone", "devices"),
    ("1f4de", "telephone_receiver", "devices"),
    ("260e", "telephone", "devices"),
    ("1f4df", "pager", "devices"),
    ("1f4e0", "fax_machine", "devices"),
    ("1f4f7", "camera", "devices"),
    ("1f4f9", "video_camera", "devices"),
    ("1f4fa", "television", "devices"),
    ("1f4fb", "radio", "devices"),
    ("1f399", "studio_microphone", "devices"),
    ("1f3a7", "headphones", "devices"),
    ("1f50b", "battery", "devices"),
    ("1f50c", "electric_plug", "devices"),
    ("1f4a1", "light_bulb", "devices"),
    ("1f4e1", "satellite_antenna", "devices"),
    ("1f5dc", "compression", "devices"),
    ("1f579", "joystick", "devices"),
    # Globe, map, and geography.
    ("1f30d", "globe_europe_africa", "globe_map"),
    ("1f30e", "globe_americas", "globe_map"),
    ("1f30f", "globe_asia_australia", "globe_map"),
    ("1f310", "globe_meridians", "globe_map"),
    ("1f5fa", "world_map", "globe_map"),
    ("1f9ed", "compass", "globe_map"),
    ("1f4cd", "round_pushpin", "globe_map"),
    ("1f4cc", "pushpin", "globe_map"),
    ("1f5ff", "moai", "globe_map"),
    ("26f2", "fountain", "globe_map"),
    # Buildings and places.
    ("1f3e0", "house", "buildings_places"),
    ("1f3e1", "house_with_garden", "buildings_places"),
    ("1f3e2", "office_building", "buildings_places"),
    ("1f3e3", "post_office", "buildings_places"),
    ("1f3e5", "hospital", "buildings_places"),
    ("1f3e6", "bank", "buildings_places"),
    ("1f3e8", "hotel", "buildings_places"),
    ("1f3e9", "love_hotel", "buildings_places"),
    ("1f3ea", "convenience_store", "buildings_places"),
    ("1f3eb", "school", "buildings_places"),
    ("1f3ec", "department_store", "buildings_places"),
    ("1f3ed", "factory", "buildings_places"),
    ("1f3db", "classical_building", "buildings_places"),
    ("1f3df", "stadium", "buildings_places"),
    ("1f3d7", "building_construction", "buildings_places"),
    ("1f3d8", "houses", "buildings_places"),
    ("1f3d9", "cityscape", "buildings_places"),
    ("1f3da", "derelict_house", "buildings_places"),
    ("26ea", "church", "buildings_places"),
    ("1f54c", "mosque", "buildings_places"),
    ("1f6d5", "hindu_temple", "buildings_places"),
    ("1f54d", "synagogue", "buildings_places"),
    ("1f6d6", "hut", "buildings_places"),
    # Finance, commerce, and shopping.
    ("1f4b0", "money_bag", "finance_shopping"),
    ("1f4b3", "credit_card", "finance_shopping"),
    ("1f4b5", "dollar_banknote", "finance_shopping"),
    ("1f4b6", "euro_banknote", "finance_shopping"),
    ("1f4b7", "pound_banknote", "finance_shopping"),
    ("1f4b8", "money_with_wings", "finance_shopping"),
    ("1f4c8", "chart_increasing", "finance_shopping"),
    ("1f4c9", "chart_decreasing", "finance_shopping"),
    ("1f9fe", "receipt", "finance_shopping"),
    ("1f6d2", "shopping_cart", "finance_shopping"),
    ("1f6cd", "shopping_bags", "finance_shopping"),
    ("1f381", "gift", "finance_shopping"),
    ("1f4e6", "package", "finance_shopping"),
    ("1f3f7", "label_tag", "finance_shopping"),
    ("1f4ca", "bar_chart", "finance_shopping"),
    # Education and documents.
    ("1f393", "graduation_cap", "education_documents"),
    ("1f4da", "books", "education_documents"),
    ("1f4d6", "open_book", "education_documents"),
    ("1f4d3", "notebook", "education_documents"),
    ("1f4d4", "notebook_decorative", "education_documents"),
    ("1f4d5", "closed_book", "education_documents"),
    ("1f4d7", "green_book", "education_documents"),
    ("1f4d8", "blue_book", "education_documents"),
    ("1f4d9", "orange_book", "education_documents"),
    ("1f4cb", "clipboard", "education_documents"),
    ("1f4c4", "document", "education_documents"),
    ("1f4c3", "page_with_curl", "education_documents"),
    ("1f4c1", "file_folder", "education_documents"),
    ("1f4c2", "open_file_folder", "education_documents"),
    ("1f5c2", "card_index_dividers", "education_documents"),
    ("1f5c3", "card_file_box", "education_documents"),
    ("1f5c4", "file_cabinet", "education_documents"),
    ("1f4dd", "memo", "education_documents"),
    ("270f", "pencil", "education_documents"),
    ("1f58a", "pen", "education_documents"),
    ("1f4cf", "straight_ruler", "education_documents"),
    ("1f4d0", "triangular_ruler", "education_documents"),
    ("1f4c5", "calendar", "education_documents"),
    ("1f4c6", "tear_off_calendar", "education_documents"),
    # Health and science.
    ("1f52c", "microscope", "health_science"),
    ("1f52d", "telescope", "health_science"),
    ("1f9ea", "test_tube", "health_science"),
    ("1f9eb", "petri_dish", "health_science"),
    ("1f9ec", "dna", "health_science"),
    ("1fa7a", "stethoscope", "health_science"),
    ("1f48a", "pill", "health_science"),
    ("1f489", "syringe", "health_science"),
    ("1fa79", "adhesive_bandage", "health_science"),
    ("1fa78", "drop_of_blood", "health_science"),
    ("1f321", "thermometer", "health_science"),
    ("1f9af", "white_cane", "health_science"),
    ("1f9bd", "manual_wheelchair", "health_science"),
    ("1f9bc", "motorized_wheelchair", "health_science"),
    ("2695", "medical_symbol", "health_science"),
    # Transport and travel.
    ("1f697", "automobile", "transport_travel"),
    ("1f695", "taxi", "transport_travel"),
    ("1f699", "sport_utility_vehicle", "transport_travel"),
    ("1f68c", "bus", "transport_travel"),
    ("1f69a", "delivery_truck", "transport_travel"),
    ("1f691", "ambulance", "transport_travel"),
    ("1f692", "fire_engine", "transport_travel"),
    ("1f693", "police_car", "transport_travel"),
    ("1f6b2", "bicycle", "transport_travel"),
    ("1f6f4", "kick_scooter", "transport_travel"),
    ("1f3cd", "motorcycle", "transport_travel"),
    ("1f686", "train", "transport_travel"),
    ("1f687", "metro", "transport_travel"),
    ("1f68a", "tram", "transport_travel"),
    ("2708", "airplane", "transport_travel"),
    ("1f6e9", "small_airplane", "transport_travel"),
    ("1f680", "rocket", "transport_travel"),
    ("1f6a2", "ship", "transport_travel"),
    ("26f5", "sailboat", "transport_travel"),
    ("1f6f3", "passenger_ship", "transport_travel"),
    ("1f6eb", "airplane_departure", "transport_travel"),
    ("1f6ec", "airplane_arrival", "transport_travel"),
    # Sports and awards.
    ("1f3c6", "trophy", "sports_awards"),
    ("1f947", "gold_medal", "sports_awards"),
    ("1f948", "silver_medal", "sports_awards"),
    ("1f949", "bronze_medal", "sports_awards"),
    ("1f3c5", "sports_medal", "sports_awards"),
    ("26bd", "soccer_ball", "sports_awards"),
    ("1f3c0", "basketball", "sports_awards"),
    ("1f3c8", "american_football", "sports_awards"),
    ("26be", "baseball", "sports_awards"),
    ("1f3be", "tennis", "sports_awards"),
    ("1f3af", "bullseye", "sports_awards"),
    ("1f3b2", "game_die", "sports_awards"),
    ("1f3ae", "video_game", "sports_awards"),
    ("1f3b8", "guitar", "sports_awards"),
    ("1f3a8", "artist_palette", "sports_awards"),
    # Food and lifestyle.
    ("1f34e", "red_apple", "food_lifestyle"),
    ("1f34c", "banana", "food_lifestyle"),
    ("1f347", "grapes", "food_lifestyle"),
    ("1f353", "strawberry", "food_lifestyle"),
    ("1f955", "carrot", "food_lifestyle"),
    ("1f35e", "bread", "food_lifestyle"),
    ("1f9c0", "cheese", "food_lifestyle"),
    ("1f355", "pizza", "food_lifestyle"),
    ("1f354", "hamburger", "food_lifestyle"),
    ("1f35f", "fries", "food_lifestyle"),
    ("1f37d", "fork_knife_plate", "food_lifestyle"),
    ("2615", "coffee", "food_lifestyle"),
    ("1f375", "tea", "food_lifestyle"),
    ("1f9cb", "bubble_tea", "food_lifestyle"),
    ("1f9f3", "luggage", "food_lifestyle"),
    ("1f45f", "running_shoe", "food_lifestyle"),
    ("1f451", "crown", "food_lifestyle"),
    ("1f48d", "ring", "food_lifestyle"),
    # Tools and tangible objects.
    ("1f528", "hammer", "tools_objects"),
    ("1f527", "wrench", "tools_objects"),
    ("2699", "gear", "tools_objects"),
    ("1f6e0", "hammer_wrench", "tools_objects"),
    ("1f9f0", "toolbox", "tools_objects"),
    ("1f9f2", "magnet", "tools_objects"),
    ("1f9f1", "brick", "tools_objects"),
    ("1fa9c", "ladder", "tools_objects"),
    ("1f513", "unlocked", "tools_objects"),
    ("1f512", "locked", "tools_objects"),
    ("1f511", "key", "tools_objects"),
    ("2702", "scissors", "tools_objects"),
    ("1f9f5", "thread", "tools_objects"),
    ("1f9f6", "yarn", "tools_objects"),
    ("1f9fa", "basket", "tools_objects"),
    ("1f9fb", "roll_of_paper", "tools_objects"),
    ("1f9fc", "soap", "tools_objects"),
    ("1faa3", "bucket", "tools_objects"),
    ("1fa91", "chair", "tools_objects"),
    ("1f6aa", "door", "tools_objects"),
    ("1f6cf", "bed", "tools_objects"),
    ("1f6cb", "couch_lamp", "tools_objects"),
    # Nature and weather.
    ("1f331", "seedling", "nature_weather"),
    ("1f332", "evergreen_tree", "nature_weather"),
    ("1f333", "deciduous_tree", "nature_weather"),
    ("1f334", "palm_tree", "nature_weather"),
    ("1f335", "cactus", "nature_weather"),
    ("1f33b", "sunflower", "nature_weather"),
    ("1f33f", "herb", "nature_weather"),
    ("1f342", "fallen_leaf", "nature_weather"),
    ("2600", "sun", "nature_weather"),
    ("2601", "cloud", "nature_weather"),
    ("1f327", "rain_cloud", "nature_weather"),
    ("1f308", "rainbow", "nature_weather"),
    ("26a1", "high_voltage", "nature_weather"),
    ("2744", "snowflake", "nature_weather"),
    ("1f525", "fire", "nature_weather"),
    ("1f4a7", "droplet", "nature_weather"),
    # Badge/status symbols.
    ("2b50", "star", "status_badges"),
    ("1f31f", "glowing_star", "status_badges"),
    ("2728", "sparkles", "status_badges"),
    ("26a0", "warning", "status_badges"),
    ("2705", "check_mark_button", "status_badges"),
    ("274c", "cross_mark", "status_badges"),
    ("2753", "question_mark", "status_badges"),
    ("2757", "exclamation_mark", "status_badges"),
    ("1f514", "bell", "status_badges"),
    ("1f4e3", "megaphone", "status_badges"),
    ("1f4e2", "loudspeaker", "status_badges"),
    ("1f6a9", "triangular_flag", "status_badges"),
    ("1f4a0", "diamond_shape", "status_badges"),
    ("1f539", "small_blue_diamond", "status_badges"),
    ("1f536", "large_orange_diamond", "status_badges"),
    ("1f7e2", "green_circle", "status_badges"),
    ("1f7e1", "yellow_circle", "status_badges"),
    ("1f7e0", "orange_circle", "status_badges"),
    ("1f7e3", "purple_circle", "status_badges"),
)

MATERIAL_DIR_CAPS = {
    "action": 44,
    "alert": 14,
    "av": 20,
    "communication": 26,
    "content": 18,
    "device": 28,
    "editor": 20,
    "file": 18,
    "hardware": 18,
    "home": 28,
    "image": 22,
    "maps": 34,
    "navigation": 16,
    "notification": 16,
    "places": 24,
    "social": 18,
}
MATERIAL_TOTAL_CAP = 240
MATERIAL_NAME_KEYWORDS = (
    "account",
    "analytics",
    "archive",
    "assessment",
    "badge",
    "bar_chart",
    "book",
    "business",
    "calendar",
    "camera",
    "category",
    "chat",
    "check",
    "cloud",
    "code",
    "contact",
    "credit",
    "dashboard",
    "data",
    "description",
    "device",
    "domain",
    "draft",
    "event",
    "factory",
    "folder",
    "group",
    "health",
    "home",
    "info",
    "insert_chart",
    "inventory",
    "key",
    "label",
    "language",
    "lightbulb",
    "local",
    "location",
    "mail",
    "map",
    "medical",
    "monitor",
    "note",
    "notification",
    "paid",
    "palette",
    "person",
    "phone",
    "place",
    "print",
    "receipt",
    "school",
    "science",
    "search",
    "security",
    "settings",
    "shield",
    "shopping",
    "star",
    "store",
    "support",
    "terminal",
    "timeline",
    "travel",
    "verified",
    "warning",
    "work",
)
MATERIAL_NAME_REJECT_PARTS = (
    "1x_mobiledata",
    "3g_mobiledata",
    "4g_mobiledata",
    "5g",
    "6_ft_apart",
    "abc",
    "ad_units",
    "counter_",
    "format_size",
    "format_text",
    "hdr_",
    "looks_",
    "mobiledata",
    "network_cell",
    "numbers",
    "signal_cellular",
    "signal_wifi",
    "text_",
)


def _fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        str(url),
        headers={
            "User-Agent": "trace-pages-visual-asset-builder/1.0",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _svg_is_safe(data: bytes) -> bool:
    text = data[:200000].decode("utf-8", errors="ignore").lower()
    return not any(marker.lower() in text for marker in FORBIDDEN_SVG_MARKERS)


def _render_svg_to_normalized_png(svg_bytes: bytes) -> tuple[Image.Image, dict[str, Any]]:
    png_bytes = cairosvg.svg2png(bytestring=svg_bytes, output_width=NORM_SIZE_PX, output_height=NORM_SIZE_PX)
    image = Image.open(BytesIO(png_bytes)).convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("rendered asset has empty alpha")
    cropped = image.crop(bbox)
    max_dim = max(cropped.size)
    if max_dim > NORM_SIZE_PX:
        cropped = ImageOps.contain(cropped, (NORM_SIZE_PX, NORM_SIZE_PX), method=Image.Resampling.LANCZOS)
    pad = max(8, int(math.ceil(max(cropped.size) * 0.08)))
    out_w = min(NORM_SIZE_PX, cropped.width + 2 * pad)
    out_h = min(NORM_SIZE_PX, cropped.height + 2 * pad)
    if cropped.width > out_w or cropped.height > out_h:
        cropped = ImageOps.contain(cropped, (out_w - 2 * pad, out_h - 2 * pad), method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (out_w, out_h), (0, 0, 0, 0))
    canvas.alpha_composite(cropped, ((out_w - cropped.width) // 2, (out_h - cropped.height) // 2))
    out_alpha = canvas.getchannel("A")
    out_bbox = out_alpha.getbbox()
    if out_bbox is None:
        raise ValueError("normalized asset has empty alpha")
    nonzero = sum(1 for value in out_alpha.getdata() if int(value) > 0)
    coverage = float(nonzero) / float(canvas.width * canvas.height)
    if coverage < 0.01 or coverage > 0.96:
        raise ValueError(f"unusable alpha coverage: {coverage:.4f}")
    meta = {
        "width_px": int(canvas.width),
        "height_px": int(canvas.height),
        "alpha_bbox_px": [int(value) for value in out_bbox],
        "alpha_coverage": round(float(coverage), 6),
    }
    return canvas, meta


def _write_license_files() -> None:
    LICENSE_ROOT.mkdir(parents=True, exist_ok=True)
    (LICENSE_ROOT / "APACHE-2.0.txt").write_text(APACHE_LICENSE_TEXT, encoding="utf-8")


def _noto_specs() -> list[AssetSpec]:
    return [_noto_spec(codepoint, label, category) for codepoint, label, category in NOTO_ASSETS]


def _material_category_for_path(path: str) -> str:
    parts = str(path).split("/")
    return str(parts[1]) if len(parts) > 2 else "unknown"


def _material_icon_name(path: str) -> str:
    parts = str(path).split("/")
    return str(parts[2]) if len(parts) > 3 else Path(path).stem


def _material_theme(category: str, name: str) -> str:
    text = f"{category} {name}"
    if any(token in text for token in ("paid", "credit", "receipt", "shopping", "store", "account_balance", "wallet")):
        return "finance_shopping"
    if any(token in text for token in ("medical", "health", "science", "biotech", "vaccines", "medication")):
        return "health_science"
    if any(token in text for token in ("school", "book", "edit", "description", "note", "folder", "article")):
        return "education_documents"
    if any(token in text for token in ("map", "place", "location", "travel", "local", "flight", "train", "directions")):
        return "globe_map"
    if any(token in text for token in ("person", "group", "face", "diversity", "social")):
        return "people"
    if any(token in text for token in ("home", "domain", "business", "factory", "warehouse", "apartment")):
        return "buildings_places"
    if any(token in text for token in ("phone", "computer", "device", "monitor", "terminal", "memory", "print")):
        return "devices"
    if any(token in text for token in ("warning", "check", "star", "verified", "info", "notification", "badge", "shield")):
        return "status_badges"
    return "tools_objects"


def _material_name_allowed(name: str) -> bool:
    """Reject icons that render as mostly text or telecom notation."""

    normalized = str(name).strip().lower()
    if not normalized:
        return False
    if normalized[0].isdigit():
        return False
    return not any(part in normalized for part in MATERIAL_NAME_REJECT_PARTS)


def _material_specs() -> list[AssetSpec]:
    selected: list[str] = []
    category_counts: dict[str, int] = {key: 0 for key in MATERIAL_DIR_CAPS}
    for category in sorted(MATERIAL_DIR_CAPS):
        if len(selected) >= MATERIAL_TOTAL_CAP:
            break
        payload = json.loads(_fetch_bytes(MATERIAL_CONTENTS.format(category=category)).decode("utf-8"))
        for row in sorted(payload, key=lambda item: str(item.get("name", ""))):
            if category_counts[str(category)] >= int(MATERIAL_DIR_CAPS[str(category)]):
                break
            name = str(row.get("name", ""))
            if not name or str(row.get("type", "")) != "dir":
                continue
            if not _material_name_allowed(name):
                continue
            if not any(keyword in str(name) for keyword in MATERIAL_NAME_KEYWORDS):
                continue
            path = f"src/{category}/{name}/materialicons/24px.svg"
            selected.append(path)
            category_counts[str(category)] += 1
            if len(selected) >= MATERIAL_TOTAL_CAP:
                break
    specs: list[AssetSpec] = []
    for path in selected:
        category = _material_category_for_path(path)
        name = _material_icon_name(path)
        specs.append(
            AssetSpec(
                asset_id=f"material_{_slug(name)}",
                source_id="material_design_icons",
                source_url=MATERIAL_RAW.format(path=path),
                category=_material_theme(category, name),
                allowed_roles=("section_illustration", "badge_spot"),
                style="monochrome_symbol",
                render_mode="monochrome",
                source_label=name,
            )
        )
    return specs


def _specs_from_existing_manifest(path: Path = MANIFEST_PATH) -> list[AssetSpec]:
    """Rebuild asset specs from an already-vetted manifest.

    This recovery path avoids source directory API calls when regenerating
    local normalized files from a manifest that has already passed review.
    """

    specs: list[AssetSpec] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, Mapping):
            raise ValueError(f"manifest line {line_no} must be a mapping")
        categories = tuple(str(category) for category in row.get("categories", ()))
        specs.append(
            AssetSpec(
                asset_id=str(row["asset_id"]),
                source_id=str(row["source_id"]),
                source_url=str(row["source_url"]),
                category=str(categories[0] if categories else "tools_objects"),
                allowed_roles=tuple(str(role) for role in row["allowed_roles"]),
                style=str(row["style"]),
                render_mode=str(row["render_mode"]),
                source_label=str(row.get("source_label", row["asset_id"])),
            )
        )
    if not specs:
        raise ValueError(f"manifest contains no asset specs: {path}")
    return specs


def _source_dir_name(spec: AssetSpec) -> str:
    return str(spec.source_id)


def _process_asset(spec: AssetSpec, *, raw_root: Path, normalized_root: Path) -> dict[str, Any] | None:
    try:
        svg_bytes = _fetch_bytes(spec.source_url)
    except Exception as exc:
        return {"asset_id": spec.asset_id, "rejected": True, "reason": f"download_failed:{exc}"}
    if not _svg_is_safe(svg_bytes):
        return {"asset_id": spec.asset_id, "rejected": True, "reason": "unsafe_svg_marker"}
    try:
        image, norm_meta = _render_svg_to_normalized_png(svg_bytes)
    except Exception as exc:
        return {"asset_id": spec.asset_id, "rejected": True, "reason": f"render_failed:{exc}"}

    raw_rel = Path("raw") / _source_dir_name(spec) / f"{spec.asset_id}.svg"
    norm_rel = Path("normalized") / f"{spec.asset_id}.png"
    raw_path = raw_root / _source_dir_name(spec) / f"{spec.asset_id}.svg"
    norm_path = normalized_root / f"{spec.asset_id}.png"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    norm_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(svg_bytes)
    image.save(norm_path)
    png_bytes = norm_path.read_bytes()
    source_meta = SOURCE_METADATA[str(spec.source_id)]
    return {
        "asset_id": str(spec.asset_id),
        "source_id": str(spec.source_id),
        "source_label": str(spec.source_label),
        "source_url": str(spec.source_url),
        "source_revision": str(source_meta["source_revision"]),
        "license_spdx": str(source_meta["license"]),
        "local_license": str(source_meta["local_license"]),
        "checksum_sha256": _sha256(svg_bytes),
        "normalized_checksum_sha256": _sha256(png_bytes),
        "raw_path": raw_rel.as_posix(),
        "normalized_path": norm_rel.as_posix(),
        "categories": [str(spec.category)],
        "allowed_roles": list(spec.allowed_roles),
        "style": str(spec.style),
        "render_mode": str(spec.render_mode),
        "semantic_policy": "non_answer_visual_context",
        "recommended_min_px": 28 if "badge_spot" in spec.allowed_roles else 96,
        "recommended_max_px": 520 if "hero_anchor" in spec.allowed_roles else 260,
        **norm_meta,
    }


def _role_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {role: 0 for role in MIN_ROLE_COUNTS}
    for row in rows:
        for role in row.get("allowed_roles", []):
            if str(role) in counts:
                counts[str(role)] += 1
    return counts


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_sources(rows: Sequence[Mapping[str, Any]]) -> None:
    source_counts: dict[str, int] = {}
    for row in rows:
        source_counts[str(row["source_id"])] = source_counts.get(str(row["source_id"]), 0) + 1
    role_counts = _role_counts(rows)
    payload = {
        "asset_version": SCRIPT_VERSION,
        "generated_by": "scripts/build_pages_visual_assets.py",
        "source_policy": (
            "Pages visual assets are vendored from allowlisted permissive sources, "
            "used as non-answer decorative/context visuals, and sampled only from local manifests at runtime."
        ),
        "allowed_licenses": ["CC0-1.0", "Apache-2.0", "MIT"],
        "asset_count": len(rows),
        "sources": SOURCE_METADATA,
        "source_counts": source_counts,
        "role_counts": role_counts,
        "role_minimums": MIN_ROLE_COUNTS,
        "role_maximums": MAX_ROLE_COUNTS,
    }
    SOURCES_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_readme(rows: Sequence[Mapping[str, Any]]) -> None:
    counts = _role_counts(rows)
    lines = [
        "# Pages Visual Asset Pool",
        "",
        "This folder contains curated visual assets for pages-domain renderers.",
        "They are non-answer decorative or layout-context assets by default.",
        "",
        "Runtime generation must load only local files through",
        "`trace.tasks.pages.shared.page_visual_assets`.",
        "",
        "## Role Counts",
        "",
    ]
    for role, count in sorted(counts.items()):
        lines.append(f"- `{role}`: {count}")
    lines.extend(
        [
            "",
            "## Contents",
            "",
            "- `manifest.jsonl`: accepted asset metadata and role/category tags.",
            "- `sources.json`: source, license, count, and policy metadata.",
            "- `raw/`: vendored source SVGs.",
            "- `normalized/`: transparent PNGs used by renderers.",
            "- `licenses/`: local license notes.",
            "- `review/contact_sheets/`: generated contact sheets for manual review.",
            "",
            "Assets must not be used as public annotation or answer-bearing content unless a future task explicitly promotes them into the task contract.",
        ]
    )
    (ASSET_ROOT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _preview_font() -> ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(path, 13)
        except Exception:
            pass
    return ImageFont.load_default()


def _make_contact_sheet(rows: Sequence[Mapping[str, Any]], *, role: str) -> None:
    role_rows = [row for row in rows if str(role) in {str(item) for item in row.get("allowed_roles", [])}]
    if not role_rows:
        return
    out_dir = REVIEW_ROOT / "contact_sheets"
    out_dir.mkdir(parents=True, exist_ok=True)
    font = _preview_font()
    cols = 10
    thumb = 74
    label_h = 34
    margin = 12
    rows_per_sheet = int(math.ceil(len(role_rows) / cols))
    sheet = Image.new("RGB", (cols * (thumb + margin) + margin, rows_per_sheet * (thumb + label_h + margin) + margin), (248, 248, 248))
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(role_rows):
        x = margin + (index % cols) * (thumb + margin)
        y = margin + (index // cols) * (thumb + label_h + margin)
        image = Image.open(ASSET_ROOT / str(row["normalized_path"])).convert("RGBA")
        image = ImageOps.contain(image, (thumb, thumb), method=Image.Resampling.LANCZOS)
        cell = Image.new("RGBA", (thumb, thumb), (255, 255, 255, 255))
        cell.alpha_composite(image, ((thumb - image.width) // 2, (thumb - image.height) // 2))
        sheet.paste(cell.convert("RGB"), (x, y))
        draw.rectangle((x, y, x + thumb, y + thumb), outline=(210, 210, 210), width=1)
        text = str(row["asset_id"]).replace("material_", "m_").replace("noto_", "n_")[:18]
        draw.text((x, y + thumb + 3), text, fill=(40, 40, 40), font=font)
        category = str(row.get("categories", [""])[0])[:18]
        draw.text((x, y + thumb + 18), category, fill=(90, 90, 90), font=font)
    sheet.save(out_dir / f"{role}.jpg", quality=90)


def _clean_output() -> None:
    if ASSET_ROOT.exists():
        for child in (RAW_ROOT, NORMALIZED_ROOT, REVIEW_ROOT):
            if child.exists():
                shutil.rmtree(child)
    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    NORMALIZED_ROOT.mkdir(parents=True, exist_ok=True)


def build(*, from_existing_manifest: bool = False) -> None:
    specs = _specs_from_existing_manifest() if from_existing_manifest else _noto_specs() + _material_specs()
    seen: set[str] = set()
    unique_specs: list[AssetSpec] = []
    for spec in specs:
        if spec.asset_id in seen:
            continue
        seen.add(spec.asset_id)
        unique_specs.append(spec)

    _clean_output()
    _write_license_files()
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="trace-pages-assets-") as tmp:
        del tmp
        for spec in unique_specs:
            row = _process_asset(spec, raw_root=RAW_ROOT, normalized_root=NORMALIZED_ROOT)
            if row is None:
                continue
            if row.get("rejected"):
                rejected.append(dict(row))
            else:
                accepted.append(dict(row))

    accepted.sort(key=lambda row: str(row["asset_id"]))
    role_counts = _role_counts(accepted)
    for role, minimum in MIN_ROLE_COUNTS.items():
        if int(role_counts.get(role, 0)) < int(minimum):
            raise RuntimeError(f"role {role} has {role_counts.get(role, 0)} accepted assets, below minimum {minimum}")
    for role, maximum in MAX_ROLE_COUNTS.items():
        if int(role_counts.get(role, 0)) > int(maximum):
            raise RuntimeError(f"role {role} has {role_counts.get(role, 0)} accepted assets, above maximum {maximum}")

    _write_jsonl(MANIFEST_PATH, accepted)
    _write_jsonl(REVIEW_ROOT / "rejected_assets.jsonl", rejected)
    _write_sources(accepted)
    _write_readme(accepted)
    for role in sorted(MIN_ROLE_COUNTS):
        _make_contact_sheet(accepted, role=role)
    print(json.dumps({"accepted": len(accepted), "rejected": len(rejected), "role_counts": role_counts}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-existing-manifest",
        action="store_true",
        help="Regenerate files from the existing manifest source URLs instead of discovering upstream candidates.",
    )
    args = parser.parse_args()
    build(from_existing_manifest=bool(args.from_existing_manifest))
