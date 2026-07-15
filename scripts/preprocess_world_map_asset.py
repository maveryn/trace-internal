#!/usr/bin/env python3
"""Preprocess Natural Earth country polygons into a compact Trace map asset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.request import urlopen


SOURCE_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
ASSET_ID = "natural_earth_admin0_world_110m_v0"
LAT_BOUNDS = (-58.0, 84.0)
MIN_RING_AREA_SQDEG = 0.01
QUESTION_MIN_AREA_SQDEG = 20.0
QUESTION_MAX_LON_SPAN_DEG = 75.0
QUESTION_MAX_LAT_SPAN_DEG = 45.0


def _iter_outer_rings(geometry: dict[str, Any]) -> Iterable[list[list[float]]]:
    if geometry.get("type") == "Polygon":
        coords = geometry.get("coordinates") or []
        if coords:
            yield coords[0]
    elif geometry.get("type") == "MultiPolygon":
        for polygon in geometry.get("coordinates") or []:
            if polygon:
                yield polygon[0]


def _ring_area_sqdeg(ring: list[list[float]]) -> float:
    points = [(float(lon), float(lat)) for lon, lat, *_ in ring if LAT_BOUNDS[0] <= float(lat) <= LAT_BOUNDS[1]]
    if len(points) < 3:
        return 0.0
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        total += (x1 * y2) - (x2 * y1)
    return abs(total) / 2.0


def _clean_ring(ring: list[list[float]]) -> list[list[float]]:
    cleaned: list[list[float]] = []
    last: tuple[float, float] | None = None
    for lon, lat, *_ in ring:
        lon_value = round(float(lon), 3)
        lat_value = round(float(lat), 3)
        if lat_value < LAT_BOUNDS[0] or lat_value > LAT_BOUNDS[1]:
            continue
        point = (lon_value, lat_value)
        if point == last:
            continue
        cleaned.append([lon_value, lat_value])
        last = point
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1]:
        cleaned.pop()
    return cleaned if len(cleaned) >= 3 else []


def build_asset(raw: dict[str, Any]) -> dict[str, Any]:
    regions: list[dict[str, Any]] = []
    for feature in raw.get("features", []):
        props = dict(feature.get("properties") or {})
        if props.get("CONTINENT") == "Antarctica":
            continue
        rings: list[list[list[float]]] = []
        total_area = 0.0
        for ring in _iter_outer_rings(dict(feature.get("geometry") or {})):
            area = _ring_area_sqdeg(ring)
            if area < MIN_RING_AREA_SQDEG:
                continue
            cleaned = _clean_ring(ring)
            if not cleaned:
                continue
            rings.append(cleaned)
            total_area += float(area)
        if not rings:
            continue
        lon_values = [point[0] for ring in rings for point in ring]
        lat_values = [point[1] for ring in rings for point in ring]
        lon_span = max(lon_values) - min(lon_values)
        lat_span = max(lat_values) - min(lat_values)
        region_id = str(props.get("ADM0_A3") or props.get("ISO_A3") or props.get("NAME")).strip()
        if not region_id or region_id == "-99":
            region_id = str(props.get("NAME") or props.get("ADMIN")).upper().replace(" ", "_")[:12]
        regions.append(
            {
                "region_id": region_id,
                "display_name": str(props.get("NAME_LONG") or props.get("NAME") or props.get("ADMIN") or region_id),
                "continent": str(props.get("CONTINENT") or ""),
                "subregion": str(props.get("SUBREGION") or ""),
                "bbox_lonlat": [
                    round(min(lon_values), 3),
                    round(min(lat_values), 3),
                    round(max(lon_values), 3),
                    round(max(lat_values), 3),
                ],
                "area_sqdeg": round(float(total_area), 3),
                "question_eligible": bool(
                    float(total_area) >= QUESTION_MIN_AREA_SQDEG
                    and float(lon_span) <= QUESTION_MAX_LON_SPAN_DEG
                    and float(lat_span) <= QUESTION_MAX_LAT_SPAN_DEG
                ),
                "rings": rings,
            }
        )
    regions.sort(key=lambda item: str(item["display_name"]))
    return {
        "asset_id": ASSET_ID,
        "map_variant": "world_countries",
        "display_name": "World",
        "region_noun": "countries",
        "region_prefix": "country",
        "title_options": [
            "World Indicator Map",
            "Global Country Map",
            "World Regional Value Map",
            "Global Metric Map",
            "Country Value Overview",
        ],
        "object_description": "a world map with selected countries colored by value and a color legend",
        "source": {
            "name": "Natural Earth Admin 0 Countries 110m",
            "url": SOURCE_URL,
            "license": "public domain",
            "license_file": "assets/charts/maps/licenses/NATURAL_EARTH_PUBLIC_DOMAIN.md",
        },
        "projection": "equirectangular_lonlat",
        "lon_bounds": [-180.0, 180.0],
        "lat_bounds": [float(LAT_BOUNDS[0]), float(LAT_BOUNDS[1])],
        "preprocess": {
            "min_ring_area_sqdeg": MIN_RING_AREA_SQDEG,
            "question_min_area_sqdeg": QUESTION_MIN_AREA_SQDEG,
            "question_max_lon_span_deg": QUESTION_MAX_LON_SPAN_DEG,
            "question_max_lat_span_deg": QUESTION_MAX_LAT_SPAN_DEG,
            "coordinate_rounding_decimals": 3,
            "antarctica_excluded": True,
        },
        "regions": regions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="assets/charts/maps/natural_earth_admin0_world_110m_v0.json",
        help="Output Trace asset JSON path.",
    )
    args = parser.parse_args()
    with urlopen(SOURCE_URL, timeout=30) as response:
        raw = json.loads(response.read().decode("utf-8"))
    asset = build_asset(raw)
    output = Path(str(args.output))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asset, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    eligible_count = sum(1 for region in asset["regions"] if region["question_eligible"])
    print(f"wrote {output} with {len(asset['regions'])} regions; {eligible_count} question eligible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
