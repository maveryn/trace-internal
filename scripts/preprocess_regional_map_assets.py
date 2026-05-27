#!/usr/bin/env python3
"""Preprocess Natural Earth regional polygons into compact TRACE map assets."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.request import urlopen


ADMIN0_110M_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
ADMIN1_110M_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_1_states_provinces.geojson"
ADMIN1_50M_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_1_states_provinces.geojson"

EU_MEMBER_A3 = {
    "AUT",
    "BEL",
    "BGR",
    "HRV",
    "CYP",
    "CZE",
    "DNK",
    "EST",
    "FIN",
    "FRA",
    "DEU",
    "GRC",
    "HUN",
    "IRL",
    "ITA",
    "LVA",
    "LTU",
    "LUX",
    "MLT",
    "NLD",
    "POL",
    "PRT",
    "ROU",
    "SVK",
    "SVN",
    "ESP",
    "SWE",
}


def _fetch_json(url: str) -> dict[str, Any]:
    with urlopen(str(url), timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def _iter_outer_rings(geometry: dict[str, Any]) -> Iterable[list[list[float]]]:
    if geometry.get("type") == "Polygon":
        coords = geometry.get("coordinates") or []
        if coords:
            yield coords[0]
    elif geometry.get("type") == "MultiPolygon":
        for polygon in geometry.get("coordinates") or []:
            if polygon:
                yield polygon[0]


def _point_in_bounds(point: Sequence[float], bounds: Sequence[float]) -> bool:
    lon, lat = float(point[0]), float(point[1])
    return float(bounds[0]) <= lon <= float(bounds[2]) and float(bounds[1]) <= lat <= float(bounds[3])


def _ring_area_sqdeg(ring: Sequence[Sequence[float]]) -> float:
    points = [(float(point[0]), float(point[1])) for point in ring if len(point) >= 2]
    if len(points) < 3:
        return 0.0
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        total += (x1 * y2) - (x2 * y1)
    return abs(total) / 2.0


def _point_line_distance(point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]) -> float:
    if start == end:
        return math.hypot(float(point[0] - start[0]), float(point[1] - start[1]))
    px, py = point
    sx, sy = start
    ex, ey = end
    dx = ex - sx
    dy = ey - sy
    t = max(0.0, min(1.0, (((px - sx) * dx) + ((py - sy) * dy)) / ((dx * dx) + (dy * dy))))
    nearest = (sx + (t * dx), sy + (t * dy))
    return math.hypot(float(px - nearest[0]), float(py - nearest[1]))


def _rdp(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    if len(points) <= 2:
        return list(points)
    start = points[0]
    end = points[-1]
    max_distance = -1.0
    split_index = 0
    for index, point in enumerate(points[1:-1], start=1):
        distance = _point_line_distance(point, start, end)
        if distance > max_distance:
            max_distance = float(distance)
            split_index = int(index)
    if max_distance <= float(tolerance):
        return [start, end]
    left = _rdp(points[: split_index + 1], tolerance)
    right = _rdp(points[split_index:], tolerance)
    return left[:-1] + right


def _clean_ring(
    ring: Sequence[Sequence[float]],
    *,
    crop_bounds: Sequence[float] | None,
    simplify_tolerance_deg: float,
    coordinate_rounding_decimals: int,
) -> list[list[float]]:
    cleaned: list[tuple[float, float]] = []
    last: tuple[float, float] | None = None
    for raw_point in ring:
        if len(raw_point) < 2:
            continue
        lon_value = float(raw_point[0])
        lat_value = float(raw_point[1])
        if crop_bounds is not None and not _point_in_bounds((lon_value, lat_value), crop_bounds):
            continue
        point = (
            round(lon_value, int(coordinate_rounding_decimals)),
            round(lat_value, int(coordinate_rounding_decimals)),
        )
        if point == last:
            continue
        cleaned.append(point)
        last = point
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1]:
        cleaned.pop()
    if len(cleaned) < 3:
        return []
    simplified = _rdp(cleaned, float(simplify_tolerance_deg)) if float(simplify_tolerance_deg) > 0.0 else cleaned
    if len(simplified) < 3:
        simplified = cleaned
    return [[float(lon), float(lat)] for lon, lat in simplified]


def _props_code(props: dict[str, Any]) -> str:
    return str(props.get("adm0_a3") or props.get("ADM0_A3") or props.get("sov_a3") or props.get("ISO_A3") or "").strip()


def _region_id(props: dict[str, Any], fallback_name: str) -> str:
    raw = str(
        props.get("adm1_code")
        or props.get("iso_3166_2")
        or props.get("gn_a1_code")
        or props.get("ADM0_A3")
        or props.get("ISO_A3")
        or fallback_name
    ).strip()
    return raw.replace(".", "_").replace("-", "_").replace(" ", "_")[:32]


def _display_name(props: dict[str, Any], fallback: str) -> str:
    return str(props.get("name") or props.get("NAME_LONG") or props.get("NAME") or props.get("ADMIN") or fallback)


def _build_asset(
    *,
    raw: dict[str, Any],
    asset_id: str,
    source_name: str,
    source_url: str,
    map_variant: str,
    display_name: str,
    region_noun: str,
    region_prefix: str,
    title_options: Sequence[str],
    object_description: str,
    include_feature,
    exclude_names: set[str] | None = None,
    crop_bounds: Sequence[float] | None = None,
    min_ring_area_sqdeg: float = 0.002,
    question_min_area_sqdeg: float = 0.01,
    simplify_tolerance_deg: float = 0.03,
    coordinate_rounding_decimals: int = 3,
) -> dict[str, Any]:
    exclude_names = set(exclude_names or set())
    regions: list[dict[str, Any]] = []
    for feature in raw.get("features", []):
        props = dict(feature.get("properties") or {})
        name = _display_name(props, "")
        if str(name) in exclude_names:
            continue
        if not include_feature(props):
            continue

        rings: list[list[list[float]]] = []
        total_area = 0.0
        for raw_ring in _iter_outer_rings(dict(feature.get("geometry") or {})):
            ring = _clean_ring(
                raw_ring,
                crop_bounds=crop_bounds,
                simplify_tolerance_deg=float(simplify_tolerance_deg),
                coordinate_rounding_decimals=int(coordinate_rounding_decimals),
            )
            if not ring:
                continue
            area = _ring_area_sqdeg(ring)
            if area < float(min_ring_area_sqdeg):
                continue
            rings.append(ring)
            total_area += float(area)
        if not rings:
            continue
        lon_values = [point[0] for ring in rings for point in ring]
        lat_values = [point[1] for ring in rings for point in ring]
        fallback = f"{region_prefix}_{len(regions):03d}"
        region_id = _region_id(props, fallback)
        regions.append(
            {
                "region_id": str(region_id),
                "display_name": _display_name(props, str(region_id)),
                "admin0_a3": _props_code(props),
                "bbox_lonlat": [
                    round(min(lon_values), 3),
                    round(min(lat_values), 3),
                    round(max(lon_values), 3),
                    round(max(lat_values), 3),
                ],
                "area_sqdeg": round(float(total_area), 3),
                "question_eligible": bool(float(total_area) >= float(question_min_area_sqdeg)),
                "rings": rings,
            }
        )

    regions.sort(key=lambda item: str(item["display_name"]))
    if not regions:
        raise ValueError(f"asset {asset_id} has no regions")
    lon_values = [point[0] for region in regions for ring in region["rings"] for point in ring]
    lat_values = [point[1] for region in regions for ring in region["rings"] for point in ring]
    lon_pad = max(0.25, (max(lon_values) - min(lon_values)) * 0.035)
    lat_pad = max(0.25, (max(lat_values) - min(lat_values)) * 0.035)
    return {
        "asset_id": str(asset_id),
        "map_variant": str(map_variant),
        "display_name": str(display_name),
        "region_noun": str(region_noun),
        "region_prefix": str(region_prefix),
        "title_options": [str(item) for item in title_options],
        "object_description": str(object_description),
        "source": {
            "name": str(source_name),
            "url": str(source_url),
            "license": "public domain",
            "license_file": "assets/charts/maps/licenses/NATURAL_EARTH_PUBLIC_DOMAIN.md",
        },
        "projection": "equirectangular_lonlat",
        "lon_bounds": [round(min(lon_values) - lon_pad, 3), round(max(lon_values) + lon_pad, 3)],
        "lat_bounds": [round(min(lat_values) - lat_pad, 3), round(max(lat_values) + lat_pad, 3)],
        "preprocess": {
            "min_ring_area_sqdeg": float(min_ring_area_sqdeg),
            "question_min_area_sqdeg": float(question_min_area_sqdeg),
            "simplify_tolerance_deg": float(simplify_tolerance_deg),
            "coordinate_rounding_decimals": int(coordinate_rounding_decimals),
            "crop_bounds": list(crop_bounds) if crop_bounds is not None else None,
            "excluded_names": sorted(exclude_names),
        },
        "regions": regions,
    }


def _write_asset(asset: dict[str, Any], output_dir: Path) -> Path:
    path = Path(output_dir) / f"{asset['asset_id']}.json"
    path.write_text(json.dumps(asset, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    eligible = sum(1 for region in asset["regions"] if bool(region["question_eligible"]))
    print(f"wrote {path} with {len(asset['regions'])} regions; {eligible} question eligible")
    return path


def build_assets(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    admin0_110m = _fetch_json(ADMIN0_110M_URL)
    admin1_110m = _fetch_json(ADMIN1_110M_URL)
    admin1_50m = _fetch_json(ADMIN1_50M_URL)
    assets = [
        _build_asset(
            raw=admin0_110m,
            asset_id="natural_earth_admin0_eu_110m_v0",
            source_name="Natural Earth Admin 0 Countries 110m",
            source_url=ADMIN0_110M_URL,
            map_variant="eu_countries",
            display_name="European Union",
            region_noun="countries",
            region_prefix="eu_country",
            title_options=(
                "EU Country Value Map",
                "European Union Map",
                "EU Member State Indicator Map",
                "EU Regional Value Overview",
            ),
            object_description="an EU country map with selected countries colored by value and a color legend",
            include_feature=lambda props: _props_code(props) in EU_MEMBER_A3,
            crop_bounds=(-25.0, 34.0, 36.5, 72.5),
            min_ring_area_sqdeg=0.002,
            question_min_area_sqdeg=0.01,
            simplify_tolerance_deg=0.035,
        ),
        _build_asset(
            raw=admin1_110m,
            asset_id="natural_earth_admin1_usa_contiguous_110m_v0",
            source_name="Natural Earth Admin 1 States/Provinces 110m",
            source_url=ADMIN1_110M_URL,
            map_variant="usa_states",
            display_name="United States",
            region_noun="states",
            region_prefix="usa_state",
            title_options=(
                "United States State Value Map",
                "USA State Map",
                "US State Indicator Map",
                "State Value Overview",
            ),
            object_description="a USA state map with selected states colored by value and a color legend",
            include_feature=lambda props: _props_code(props) == "USA",
            exclude_names={"Alaska", "Hawaii"},
            crop_bounds=(-125.5, 24.0, -66.0, 50.5),
            min_ring_area_sqdeg=0.002,
            question_min_area_sqdeg=0.02,
            simplify_tolerance_deg=0.02,
        ),
        _build_asset(
            raw=admin1_50m,
            asset_id="natural_earth_admin1_china_50m_v0",
            source_name="Natural Earth Admin 1 States/Provinces 50m",
            source_url=ADMIN1_50M_URL,
            map_variant="china_provinces",
            display_name="China",
            region_noun="provinces",
            region_prefix="china_province",
            title_options=(
                "China Province Value Map",
                "China Province Map",
                "Province Indicator Map",
                "China Regional Value Overview",
            ),
            object_description="a China province map with selected provinces colored by value and a color legend",
            include_feature=lambda props: _props_code(props) == "CHN",
            crop_bounds=(72.0, 17.0, 136.0, 55.0),
            min_ring_area_sqdeg=0.002,
            question_min_area_sqdeg=0.02,
            simplify_tolerance_deg=0.025,
        ),
    ]
    return [_write_asset(asset, output_dir) for asset in assets]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="assets/charts/maps",
        help="Directory where TRACE map asset JSON files are written.",
    )
    args = parser.parse_args()
    build_assets(Path(str(args.output_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
