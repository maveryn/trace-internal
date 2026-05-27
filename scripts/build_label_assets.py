#!/usr/bin/env python3
"""Build shared label/name manifests from permissively licensed sources."""

from __future__ import annotations

import csv
import json
import re
import shutil
import tempfile
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = REPO_ROOT / "assets"
LABEL_ROOT = ASSET_ROOT / "labels"

SSA_NAMES_URL = "https://www.ssa.gov/oact/babynames/names.zip"
CENSUS_SURNAMES_URL = "https://www2.census.gov/topics/genealogy/2010surnames/names.zip"
NATURAL_EARTH_CITIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
    "ne_10m_populated_places.geojson"
)
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
BLS_OCCUPATIONS_URL = "https://download.bls.gov/pub/time.series/oe/oe.occupation"
BLS_INDUSTRIES_URL = "https://www.bls.gov/cew/classifications/industry/industry-titles.csv"

WORD_RE = re.compile(r"[A-Za-z]+")
CORPORATE_STOPWORDS = {
    "A",
    "AND",
    "ADR",
    "ADS",
    "AG",
    "B",
    "CO",
    "COM",
    "COMPANY",
    "CORP",
    "CORPORATION",
    "DE",
    "ETF",
    "ETN",
    "FUND",
    "FUNDS",
    "GROUP",
    "HOLDING",
    "HOLDINGS",
    "INC",
    "INCORPORATED",
    "LP",
    "LTD",
    "LLC",
    "LPLC",
    "NA",
    "NEW",
    "NV",
    "OF",
    "OLD",
    "PLC",
    "SA",
    "THE",
    "TRUST",
}

SYNTHETIC_CATEGORY_MANIFESTS = {
    "categories/abstract_group_labels.txt": [
        "Amber",
        "Atlas",
        "Azure",
        "Beacon",
        "Birch",
        "Bronze",
        "Cedar",
        "Cobalt",
        "Comet",
        "Coral",
        "Crimson",
        "Delta",
        "Echo",
        "Flint",
        "Grove",
        "Harbor",
        "Hazel",
        "Indigo",
        "Ivory",
        "Jade",
        "Maple",
        "Meadow",
        "Nimbus",
        "Nova",
        "Olive",
        "Orchid",
        "Pearl",
        "Quartz",
        "River",
        "Ruby",
        "Saffron",
        "Sierra",
        "Silver",
        "Slate",
        "Summit",
        "Teal",
        "Umber",
        "Valley",
        "Violet",
        "Zenith",
    ],
    "categories/priority_labels.txt": [
        "Alert",
        "Backlog",
        "Critical",
        "Deferred",
        "Elevated",
        "High",
        "Immediate",
        "Low",
        "Major",
        "Medium",
        "Minor",
        "Normal",
        "Optional",
        "Required",
        "Routine",
        "Severe",
        "Stable",
        "Urgent",
        "Watch",
        "Review",
    ],
    "categories/product_labels.txt": [
        "Accessories",
        "Apparel",
        "Automotive",
        "Bakery",
        "Beauty",
        "Beverage",
        "Books",
        "Cloud",
        "Devices",
        "Dining",
        "Education",
        "Electronics",
        "Energy",
        "Finance",
        "Footwear",
        "Furniture",
        "Gaming",
        "Garden",
        "Grocery",
        "Hardware",
        "Health",
        "Insurance",
        "Kitchen",
        "Logistics",
        "Media",
        "Music",
        "Outdoor",
        "Pharmacy",
        "Security",
        "Services",
        "Software",
        "Sports",
        "Stationery",
        "Storage",
        "Supplies",
        "Support",
        "Telecom",
        "Tickets",
        "Tools",
        "Travel",
    ],
    "categories/status_labels.txt": [
        "Active",
        "Approved",
        "Archived",
        "Assigned",
        "Blocked",
        "Cancelled",
        "Closed",
        "Complete",
        "Delayed",
        "Draft",
        "Escalated",
        "Hold",
        "In Progress",
        "Open",
        "Paused",
        "Pending",
        "Ready",
        "Rejected",
        "Review",
        "Scheduled",
        "Waiting",
    ],
}


def _fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    user_agent = (
        "trace-label-asset-builder/1.0 contact@example.com"
        if "sec.gov" in url or "bls.gov" in url
        else "Mozilla/5.0 trace-label-asset-builder/1.0"
    )
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        dest.write_bytes(response.read())


def _write_manifest(path: Path, values: Iterable[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        label = re.sub(r"\s+", " ", str(value)).strip()
        if not label or not label.isascii():
            continue
        key = label.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(label)
    path.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
    return len(cleaned)


def _title_name(value: str) -> str:
    return " ".join(part.capitalize() for part in str(value).split())


def _read_ssa_first_names(zip_path: Path) -> list[str]:
    counts: Counter[str] = Counter()
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if not name.startswith("yob") or not name.endswith(".txt"):
                continue
            with archive.open(name) as handle:
                for raw_line in handle.read().decode("utf-8").splitlines():
                    first_name, _sex, count = raw_line.split(",")
                    if first_name.isascii() and first_name.isalpha():
                        counts[_title_name(first_name)] += int(count)
    return [name for name, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def _read_census_surnames(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as archive:
        csv_name = next(name for name in archive.namelist() if name.lower().endswith(".csv"))
        with archive.open(csv_name) as handle:
            rows = csv.DictReader(line.decode("latin-1") for line in handle)
            names = []
            for row in rows:
                raw = str(row.get("name") or row.get("NAME") or "").strip()
                if raw.isascii() and raw.replace(" ", "").replace("-", "").isalpha():
                    names.append(_title_name(raw.replace("-", " ")))
    return names


def _read_natural_earth_countries() -> list[str]:
    path = ASSET_ROOT / "charts" / "maps" / "natural_earth_admin0_world_110m_v0.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    names = [str(region["display_name"]) for region in payload["regions"]]
    return sorted(names, key=lambda value: value.casefold())


def _read_natural_earth_cities(geojson_path: Path) -> list[str]:
    payload = json.loads(geojson_path.read_text(encoding="utf-8"))
    ranked: list[tuple[int, str]] = []
    for feature in payload["features"]:
        props = feature["properties"]
        name = str(props.get("NAME") or "").strip()
        pop_max = int(float(props.get("POP_MAX") or 0))
        if name.isascii() and WORD_RE.search(name):
            ranked.append((pop_max, name))
    return [name for _pop, name in sorted(ranked, key=lambda item: (-item[0], item[1].casefold()))]


def _read_sec_company_labels(json_path: Path) -> tuple[list[str], list[str]]:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    fields = [str(field).lower() for field in payload["fields"]]
    ticker_index = fields.index("ticker")
    title_index = fields.index("name")
    tickers: list[str] = []
    terms: Counter[str] = Counter()
    for row in payload["data"]:
        ticker = str(row[ticker_index]).strip().upper()
        if ticker.isascii() and ticker.isalpha() and 1 <= len(ticker) <= 6:
            tickers.append(ticker)
        title = str(row[title_index])
        for token in WORD_RE.findall(title.upper()):
            if 3 <= len(token) <= 16 and token not in CORPORATE_STOPWORDS:
                terms[_title_name(token)] += 1
    company_terms = [
        term for term, count in sorted(terms.items(), key=lambda item: (-item[1], item[0].casefold()))
        if count >= 3
    ]
    return tickers, company_terms


def _read_bls_occupations(tsv_path: Path) -> list[str]:
    titles: list[tuple[int, str]] = []
    with tsv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        for row in rows:
            raw_title = re.sub(r"\s+", " ", str(row.get("occupation_name") or "")).strip()
            if not raw_title or raw_title == "All Occupations" or not raw_title.isascii():
                continue
            if not any(ch.isalpha() for ch in raw_title):
                continue
            sort_value = int(row.get("sort_sequence") or len(titles))
            titles.append((sort_value, raw_title))
    return [title for _sort, title in sorted(titles, key=lambda item: (item[0], item[1].casefold()))]


def _read_bls_industries(csv_path: Path) -> list[str]:
    industries: list[tuple[int, str]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        for row in rows:
            raw_title = re.sub(r"\s+", " ", str(row.get("industry_title") or "")).strip()
            code = str(row.get("industry_code") or "").strip()
            if not raw_title or raw_title == "10 Total, all industries" or not raw_title.isascii():
                continue
            title = re.sub(r"^(?:NAICS(?:\d+)?\s+)?\d+\s+", "", raw_title).strip()
            if not title or title.lower() in {"goods-producing", "service-providing", "unclassified"}:
                continue
            if not any(ch.isalpha() for ch in title):
                continue
            sort_value = int(code) if code.isdigit() else len(industries)
            industries.append((sort_value, title))
    return [title for _sort, title in sorted(industries, key=lambda item: (item[0], item[1].casefold()))]


def main() -> None:
    if LABEL_ROOT.exists():
        shutil.rmtree(LABEL_ROOT)
    with tempfile.TemporaryDirectory(prefix="trace-label-assets-") as tmp_raw:
        tmp = Path(tmp_raw)
        ssa_zip = tmp / "ssa_names.zip"
        census_zip = tmp / "census_surnames.zip"
        city_geojson = tmp / "natural_earth_populated_places.geojson"
        sec_json = tmp / "company_tickers_exchange.json"
        occupations_tsv = tmp / "bls_oe_occupation.tsv"
        industries_csv = tmp / "bls_qcew_industries.csv"
        _fetch(SSA_NAMES_URL, ssa_zip)
        _fetch(CENSUS_SURNAMES_URL, census_zip)
        _fetch(NATURAL_EARTH_CITIES_URL, city_geojson)
        _fetch(SEC_TICKERS_URL, sec_json)
        _fetch(BLS_OCCUPATIONS_URL, occupations_tsv)
        _fetch(BLS_INDUSTRIES_URL, industries_csv)

        first_names = _read_ssa_first_names(ssa_zip)
        surnames = _read_census_surnames(census_zip)
        countries = _read_natural_earth_countries()
        cities = _read_natural_earth_cities(city_geojson)
        company_tickers, company_terms = _read_sec_company_labels(sec_json)
        occupation_titles = _read_bls_occupations(occupations_tsv)
        industry_titles = _read_bls_industries(industries_csv)

    manifest_counts: dict[str, int] = {}
    manifests = {
        "people/first_names_ssa.txt": first_names,
        "people/surnames_census_2010.txt": surnames,
        "places/countries_natural_earth.txt": countries,
        "places/cities_natural_earth.txt": cities,
        "organizations/company_tickers_sec.txt": company_tickers,
        "organizations/company_terms_sec.txt": company_terms,
        "occupations/occupations_bls_oews.txt": occupation_titles,
        "industries/industries_bls_qcew.txt": industry_titles,
        **SYNTHETIC_CATEGORY_MANIFESTS,
    }

    for relative_path, values in manifests.items():
        manifest_counts[relative_path] = _write_manifest(LABEL_ROOT / relative_path, values)

    proper_labels = (
        first_names
        + surnames
        + countries
        + cities
        + company_terms
        + occupation_titles
        + industry_titles
    )
    compact_labels = [
        value
        for value in proper_labels
        if value.replace(" ", "").isalpha() and 2 <= len(value.replace(" ", "")) <= 14
    ]
    manifest_counts["mixed/proper_labels.txt"] = _write_manifest(
        LABEL_ROOT / "mixed" / "proper_labels.txt",
        proper_labels,
    )
    manifest_counts["mixed/compact_labels.txt"] = _write_manifest(
        LABEL_ROOT / "mixed" / "compact_labels.txt",
        compact_labels,
    )

    license_dir = LABEL_ROOT / "licenses"
    license_dir.mkdir(parents=True, exist_ok=True)
    (license_dir / "CC0-1.0.txt").write_text(
        "Creative Commons CC0 1.0 Universal public domain dedication.\n"
        "License URL: https://creativecommons.org/publicdomain/zero/1.0/\n",
        encoding="utf-8",
    )
    (license_dir / "US-GOV-PUBLIC-DOMAIN.txt").write_text(
        "U.S. federal government source data is treated as public domain for TRACE label assets.\n"
        "Reference: 17 U.S.C. 105, U.S. government works.\n",
        encoding="utf-8",
    )
    (license_dir / "NATURAL-EARTH-PUBLIC-DOMAIN.txt").write_text(
        "Natural Earth vector and raster map data is public domain.\n"
        "Source terms: https://www.naturalearthdata.com/about/terms-of-use/\n",
        encoding="utf-8",
    )
    (license_dir / "TRACE-SYNTHETIC.txt").write_text(
        "TRACE synthetic label assets.\n\n"
        "These labels were authored for TRACE synthetic task generation and are\n"
        "included as project-local assets. They are not copied from an external\n"
        "upstream dataset.\n",
        encoding="utf-8",
    )

    sources = {
        "asset_version": "labels_v0",
        "generated_by": "scripts/build_label_assets.py",
        "source_policy": (
            "Shared label/name manifests are normalized from permissively licensed, public-domain, "
            "or project-local synthetic sources. Task modules should load these manifests and apply "
            "task-local length/style filters."
        ),
        "sources": {
            "ssa_baby_names": {
                "description": "U.S. Social Security card application baby-name counts.",
                "source_url": SSA_NAMES_URL,
                "metadata_url": "https://catalog.data.gov/dataset/baby-names-from-social-security-card-applications-national-data",
                "license": "CC0-1.0",
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "local_license": "licenses/CC0-1.0.txt",
            },
            "census_surnames_2010": {
                "description": "Frequently occurring surnames from the 2010 U.S. Census.",
                "source_url": CENSUS_SURNAMES_URL,
                "metadata_url": "https://www.census.gov/data/developers/data-sets/surnames/2010.html",
                "license": "U.S. government public domain",
                "license_url": "https://www.law.cornell.edu/uscode/text/17/105",
                "local_license": "licenses/US-GOV-PUBLIC-DOMAIN.txt",
            },
            "natural_earth": {
                "description": "Natural Earth country and populated-place names.",
                "source_url": NATURAL_EARTH_CITIES_URL,
                "metadata_url": "https://www.naturalearthdata.com/about/terms-of-use/",
                "license": "public domain",
                "license_url": "https://www.naturalearthdata.com/about/terms-of-use/",
                "local_license": "licenses/NATURAL-EARTH-PUBLIC-DOMAIN.txt",
            },
            "sec_company_tickers": {
                "description": "SEC company ticker exchange file; TRACE uses tickers and generic terms extracted from company names.",
                "source_url": SEC_TICKERS_URL,
                "metadata_url": "https://www.sec.gov/file/company-tickers-exchange",
                "license": "U.S. government public domain / factual identifiers",
                "license_url": "https://www.law.cornell.edu/uscode/text/17/105",
                "local_license": "licenses/US-GOV-PUBLIC-DOMAIN.txt",
            },
            "bls_occupations_oews": {
                "description": "BLS OEWS occupation titles.",
                "source_url": BLS_OCCUPATIONS_URL,
                "metadata_url": "https://www.bls.gov/oes/tables.htm",
                "license": "U.S. government public domain",
                "license_url": "https://www.bls.gov/bls/linksite.htm",
                "local_license": "licenses/US-GOV-PUBLIC-DOMAIN.txt",
            },
            "bls_industries_qcew": {
                "description": "BLS QCEW NAICS industry titles.",
                "source_url": BLS_INDUSTRIES_URL,
                "metadata_url": "https://www.bls.gov/cew/classifications/industry/industry-titles.htm",
                "license": "U.S. government public domain",
                "license_url": "https://www.bls.gov/bls/linksite.htm",
                "local_license": "licenses/US-GOV-PUBLIC-DOMAIN.txt",
            },
            "trace_synthetic_categories": {
                "description": "Project-local synthetic category labels authored for TRACE task generation.",
                "source_url": "",
                "metadata_url": "",
                "license": "TRACE synthetic label assets",
                "license_url": "",
                "local_license": "licenses/TRACE-SYNTHETIC.txt",
            },
        },
        "manifests": {
            "people/first_names_ssa.txt": {
                "sources": ["ssa_baby_names"],
                "count": manifest_counts["people/first_names_ssa.txt"],
                "description": "Given names sorted by aggregate SSA frequency descending.",
            },
            "people/surnames_census_2010.txt": {
                "sources": ["census_surnames_2010"],
                "count": manifest_counts["people/surnames_census_2010.txt"],
                "description": "Surnames in Census rank order.",
            },
            "places/countries_natural_earth.txt": {
                "sources": ["natural_earth"],
                "count": manifest_counts["places/countries_natural_earth.txt"],
                "description": "Country/region display names from the bundled Natural Earth admin-0 map asset.",
            },
            "places/cities_natural_earth.txt": {
                "sources": ["natural_earth"],
                "count": manifest_counts["places/cities_natural_earth.txt"],
                "description": "Populated-place names sorted by Natural Earth population rank.",
            },
            "organizations/company_tickers_sec.txt": {
                "sources": ["sec_company_tickers"],
                "count": manifest_counts["organizations/company_tickers_sec.txt"],
                "description": "Alphabetic exchange ticker labels from the SEC static file.",
            },
            "organizations/company_terms_sec.txt": {
                "sources": ["sec_company_tickers"],
                "count": manifest_counts["organizations/company_terms_sec.txt"],
                "description": "Common generic organization terms extracted from SEC company names after suffix removal.",
            },
            "categories/abstract_group_labels.txt": {
                "sources": ["trace_synthetic_categories"],
                "count": manifest_counts["categories/abstract_group_labels.txt"],
                "description": "Synthetic short neutral category labels for charts, maps, legends, and compact panels.",
            },
            "categories/priority_labels.txt": {
                "sources": ["trace_synthetic_categories"],
                "count": manifest_counts["categories/priority_labels.txt"],
                "description": "Synthetic priority and risk category labels for categorical legends.",
            },
            "categories/product_labels.txt": {
                "sources": ["trace_synthetic_categories"],
                "count": manifest_counts["categories/product_labels.txt"],
                "description": "Synthetic product or service category labels for chart categories and page labels.",
            },
            "categories/status_labels.txt": {
                "sources": ["trace_synthetic_categories"],
                "count": manifest_counts["categories/status_labels.txt"],
                "description": "Synthetic workflow status category labels for categorical legends and document/page tasks.",
            },
            "occupations/occupations_bls_oews.txt": {
                "sources": ["bls_occupations_oews"],
                "count": manifest_counts["occupations/occupations_bls_oews.txt"],
                "description": "Occupation titles from BLS Occupational Employment and Wage Statistics.",
            },
            "industries/industries_bls_qcew.txt": {
                "sources": ["bls_industries_qcew"],
                "count": manifest_counts["industries/industries_bls_qcew.txt"],
                "description": "Industry titles from BLS QCEW NAICS classification data.",
            },
            "mixed/proper_labels.txt": {
                "sources": [
                    "ssa_baby_names",
                    "census_surnames_2010",
                    "natural_earth",
                    "sec_company_tickers",
                    "bls_occupations_oews",
                    "bls_industries_qcew",
                ],
                "count": manifest_counts["mixed/proper_labels.txt"],
                "description": "Broad proper-label pool spanning people, places, organization terms, occupations, and industry titles.",
            },
            "mixed/compact_labels.txt": {
                "sources": [
                    "ssa_baby_names",
                    "census_surnames_2010",
                    "natural_earth",
                    "sec_company_tickers",
                    "bls_occupations_oews",
                    "bls_industries_qcew",
                ],
                "count": manifest_counts["mixed/compact_labels.txt"],
                "description": "Compact alphabetic labels suitable for tighter render surfaces before task-local filtering.",
            },
        },
    }
    (LABEL_ROOT / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest_counts, indent=2))


if __name__ == "__main__":
    main()
