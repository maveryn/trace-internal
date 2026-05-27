#!/usr/bin/env python3
"""Build shared context/distractor text manifests from permissive sources."""

from __future__ import annotations

import json
import random
import re
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = REPO_ROOT / "assets"
CONTEXT_ROOT = ASSET_ROOT / "context_text"

CORPORA_BASE_URL = "https://raw.githubusercontent.com/dariusk/corpora/master"
CORPORA_SOURCES = {
    "words/adjectives_corpora.txt": {
        "source_id": "corpora_project",
        "url": f"{CORPORA_BASE_URL}/data/words/adjs.json",
        "json_key": "adjs",
        "description": "English adjectives from the CC0 Corpora Project.",
    },
    "words/adverbs_corpora.txt": {
        "source_id": "corpora_project",
        "url": f"{CORPORA_BASE_URL}/data/words/adverbs.json",
        "json_key": "adverbs",
        "description": "English adverbs from the CC0 Corpora Project.",
    },
    "words/nouns_corpora.txt": {
        "source_id": "corpora_project",
        "url": f"{CORPORA_BASE_URL}/data/words/nouns.json",
        "json_key": "nouns",
        "description": "English nouns from the CC0 Corpora Project.",
    },
    "words/verbs_corpora.txt": {
        "source_id": "corpora_project",
        "url": f"{CORPORA_BASE_URL}/data/words/verbs.json",
        "json_key": "verbs",
        "description": "English verbs from the CC0 Corpora Project.",
    },
    "domains/industries_corpora.txt": {
        "source_id": "corpora_project",
        "url": f"{CORPORA_BASE_URL}/data/corporations/industries.json",
        "json_key": "industries",
        "description": "Industry labels from the CC0 Corpora Project.",
    },
}

SCRIPT_SEED = 20260524

METRICS = (
    "Access",
    "Activity",
    "Balance",
    "Capacity",
    "Coverage",
    "Demand",
    "Events",
    "Flow",
    "Growth",
    "Index",
    "Load",
    "Margin",
    "Output",
    "Pipeline",
    "Quality",
    "Reach",
    "Requests",
    "Response",
    "Risk",
    "Score",
    "Share",
    "Signal",
    "Status",
    "Supply",
    "Throughput",
    "Trend",
    "Units",
    "Volume",
)

DESCRIPTORS = (
    "Baseline",
    "Current",
    "Draft",
    "Internal",
    "Monthly",
    "Operating",
    "Planning",
    "Quarterly",
    "Reference",
    "Regional",
    "Routine",
    "Summary",
    "Weekly",
)

GROUPS = (
    "Alpha",
    "Atlas",
    "Beacon",
    "Cedar",
    "Delta",
    "Echo",
    "Harbor",
    "Iris",
    "Jade",
    "Maple",
    "Nimbus",
    "Orion",
    "Quartz",
    "River",
    "Summit",
    "Terra",
    "Vertex",
    "Willow",
)

TIME_WINDOWS = (
    "current cycle",
    "daily review",
    "monthly review",
    "planning window",
    "quarterly update",
    "reference period",
    "reporting window",
    "weekly summary",
)

SOURCE_NAMES = (
    "admin file",
    "audit sheet",
    "field note",
    "internal log",
    "planning memo",
    "review packet",
    "sample ledger",
    "source table",
    "tracking file",
)

SAFE_ADVERBS = (
    "carefully",
    "consistently",
    "lightly",
    "manually",
    "periodically",
    "regularly",
    "routinely",
    "separately",
    "systematically",
)

def _fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        str(url),
        headers={
            "User-Agent": "trace-context-text-asset-builder/1.0",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        dest.write_bytes(response.read())


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def _clean_word(value: str) -> str:
    text = _normalize_space(str(value).replace("_", " ").replace("-", " "))
    text = re.sub(r"[&+]+", " and ", text)
    text = re.sub(r"[/|]+", " ", text)
    text = re.sub(r"[^A-Za-z ]+", "", text)
    text = _normalize_space(text)
    if not text or not text.isascii() or len(text) > 28:
        return ""
    if not all(part.isalpha() for part in text.split()):
        return ""
    return text.lower()


def _title_phrase(value: str) -> str:
    small_words = {"and", "for", "in", "of", "on", "or", "the", "to"}
    parts = _normalize_space(value).split()
    title_parts = []
    for index, part in enumerate(parts):
        lowered = part.lower()
        if index > 0 and lowered in small_words:
            title_parts.append(lowered)
        else:
            title_parts.append(lowered.capitalize())
    return " ".join(title_parts)


def _write_manifest(path: Path, values: Iterable[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _normalize_space(value)
        if not text or not text.isascii():
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return len(out)


def _read_corpora_json(path: Path, key: str) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_values = payload.get(str(key), [])
    if not isinstance(raw_values, list):
        raise ValueError(f"expected list at key {key!r} in {path}")
    values = []
    for item in raw_values:
        cleaned = _clean_word(str(item))
        if cleaned:
            values.append(cleaned)
    return values


def _sample_cycle(rng: random.Random, values: Sequence[str]) -> str:
    if not values:
        raise ValueError("values must not be empty")
    return str(values[rng.randrange(len(values))])


def _build_template_manifest(
    *,
    rng: random.Random,
    templates: Sequence[str],
    count: int,
    adjectives: Sequence[str],
    nouns: Sequence[str],
    verbs: Sequence[str],
    industries: Sequence[str],
) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    attempts = 0
    while len(values) < int(count) and attempts < int(count) * 30:
        attempts += 1
        template = _sample_cycle(rng, templates)
        text = template.format(
            adjective=_title_phrase(_sample_cycle(rng, adjectives)),
            adjective_lc=_sample_cycle(rng, adjectives),
            adverb=_sample_cycle(rng, SAFE_ADVERBS),
            noun=_title_phrase(_sample_cycle(rng, nouns)),
            noun_lc=_sample_cycle(rng, nouns),
            verb=_sample_cycle(rng, verbs),
            industry=_title_phrase(_sample_cycle(rng, industries)),
            metric=_sample_cycle(rng, METRICS),
            metric_lc=_sample_cycle(rng, METRICS).lower(),
            group=_sample_cycle(rng, GROUPS),
            window=_sample_cycle(rng, TIME_WINDOWS),
            source=_sample_cycle(rng, SOURCE_NAMES),
            descriptor=_sample_cycle(rng, DESCRIPTORS),
            descriptor_lc=_sample_cycle(rng, DESCRIPTORS).lower(),
            number=rng.randrange(2, 98),
            small_number=rng.randrange(2, 12),
            percent=rng.randrange(4, 96),
            code=f"{rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{rng.randrange(10, 99)}",
        )
        text = _normalize_space(text)
        if not text or not text.isascii() or len(text) > 118:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(text)
    return values


def _build_paragraphs(rng: random.Random, sentences: Sequence[str], *, count: int = 1200) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    if len(sentences) < 3:
        return values
    attempts = 0
    while len(values) < int(count) and attempts < int(count) * 12:
        attempts += 1
        parts = rng.sample(list(sentences), k=2)
        text = _normalize_space(" ".join(parts))
        if len(text) > 260:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(text)
    return values


def _build_long_paragraphs(rng: random.Random, sentences: Sequence[str], *, count: int = 1200) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    if len(sentences) < 6:
        return values
    attempts = 0
    while len(values) < int(count) and attempts < int(count) * 20:
        attempts += 1
        part_count = int(rng.randrange(14, 23))
        parts = rng.sample(list(sentences), k=part_count)
        text = _normalize_space(" ".join(parts))
        if len(text) < 980 or len(text) > 1500:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        values.append(text)
    return values


def _build_context_sentences(
    *,
    rng: random.Random,
    count: int,
    adjectives: Sequence[str],
    nouns: Sequence[str],
    verbs: Sequence[str],
    industries: Sequence[str],
) -> list[str]:
    templates = (
        "The {descriptor_lc} {metric_lc} note was prepared for the {window}.",
        "The {source} includes {number} reference entries for {group}.",
        "The {industry} summary uses {descriptor_lc} labels for context.",
        "The {group} packet lists {metric_lc} records for review.",
        "A {descriptor_lc} note marks the {metric_lc} section.",
        "Reference item {code} is shown as context for {group}.",
        "The {window} uses {small_number} supplemental review notes.",
        "The {source} was checked {adverb} before the visual summary.",
        "The {metric_lc} field is included as a supplemental reference.",
        "The {industry} panel contains context-only text blocks.",
    )
    return _build_template_manifest(
        rng=rng,
        templates=templates,
        count=int(count),
        adjectives=adjectives,
        nouns=nouns,
        verbs=verbs,
        industries=industries,
    )


def _write_license_files() -> None:
    license_dir = CONTEXT_ROOT / "licenses"
    license_dir.mkdir(parents=True, exist_ok=True)
    (license_dir / "CC0-1.0.txt").write_text(
        "Creative Commons CC0 1.0 Universal public domain dedication.\n"
        "License URL: https://creativecommons.org/publicdomain/zero/1.0/\n",
        encoding="utf-8",
    )
    (license_dir / "TRACE-SYNTHETIC.txt").write_text(
        "TRACE synthetic context text templates.\n\n"
        "These template strings were authored for TRACE synthetic task generation\n"
        "and combined with permissively licensed source word/category pools.\n",
        encoding="utf-8",
    )


def _write_readme() -> None:
    (CONTEXT_ROOT / "README.md").write_text(
        "# Shared Context Text Assets\n\n"
        "This directory stores reusable non-answer text pools for visual context,\n"
        "chrome, captions, callouts, sidebars, source notes, and distractor text.\n"
        "These assets are intended for chart, graph, and page context layers.\n\n"
        "Task renderers should treat these strings as non-semantic unless a task\n"
        "explicitly scopes them into the verifier contract. Context-layer metadata\n"
        "must record role, bbox, source manifest, and exclusion status for every\n"
        "drawn text element.\n\n"
        "## Source Policy\n\n"
        "Assets are normalized from CC0/public-domain compatible sources and\n"
        "project-local TRACE synthetic templates. `sources.json` records source\n"
        "URLs, local license files, and per-manifest counts.\n\n"
        "## Regeneration\n\n"
        "Run:\n\n"
        "```bash\n"
        "python scripts/build_context_text_assets.py\n"
        "```\n",
        encoding="utf-8",
    )


def _source_metadata(manifest_counts: Mapping[str, int]) -> dict[str, object]:
    manifests: dict[str, dict[str, object]] = {}
    for relative_path, count in sorted(manifest_counts.items()):
        if relative_path.startswith("words/") or relative_path.startswith("domains/"):
            source_ids = ["corpora_project"]
        else:
            source_ids = ["corpora_project", "trace_context_templates"]
        manifests[str(relative_path)] = {
            "sources": source_ids,
            "count": int(count),
            "description": _manifest_description(relative_path),
        }
    return {
        "asset_version": "context_text_v0",
        "generated_by": "scripts/build_context_text_assets.py",
        "source_policy": (
            "Shared context/distractor text manifests are normalized from CC0/public-domain "
            "compatible sources and TRACE-authored templates. Runtime tasks should use these "
            "strings as non-answer context unless the verifier explicitly scopes them in."
        ),
        "sources": {
            "corpora_project": {
                "description": "Darius Kazemi's Corpora Project word and category lists.",
                "source_urls": [entry["url"] for entry in CORPORA_SOURCES.values()],
                "metadata_url": "https://github.com/dariusk/corpora",
                "license": "CC0-1.0",
                "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
                "local_license": "licenses/CC0-1.0.txt",
            },
            "trace_context_templates": {
                "description": "TRACE-authored neutral templates for chart, graph, and page context text.",
                "source_url": "",
                "metadata_url": "",
                "license": "TRACE synthetic context text templates",
                "license_url": "",
                "local_license": "licenses/TRACE-SYNTHETIC.txt",
            },
        },
        "manifests": manifests,
    }


def _manifest_description(relative_path: str) -> str:
    descriptions = {
        "phrases/headlines.txt": "Short neutral headline/title strings for report and chart/page chrome.",
        "phrases/captions.txt": "Caption strings for non-answer chart, graph, and page context.",
        "phrases/source_notes.txt": "Source-note strings for footer and margin context.",
        "phrases/footers.txt": "Footer strings for report/page framing.",
        "phrases/sidebar_notes.txt": "Sidebar-note strings for non-answer context panels.",
        "phrases/callout_phrases.txt": "Short callout labels for annotation boxes.",
        "phrases/metric_snippets.txt": "Decorative metric snippets containing numbers for distractor text.",
        "phrases/legend_notes.txt": "Legend-like explanatory strings for context panels.",
        "sentences/context_template_sentences.txt": "TRACE-generated neutral context sentences built from CC0 word pools and templates.",
        "paragraphs/context_template_blocks.txt": "TRACE-generated two-sentence context blocks built from neutral context sentence templates.",
        "paragraphs/context_long_blocks.txt": "TRACE-generated longer neutral context blocks built from CC0 word pools and templates.",
        "domains/industries_corpora.txt": "Industry labels used as topic/context fillers.",
    }
    if relative_path.startswith("words/"):
        return "Normalized CC0 word pool used by TRACE context text templates."
    return descriptions.get(str(relative_path), "Generated shared context text manifest.")


def main() -> None:
    rng = random.Random(SCRIPT_SEED)
    if CONTEXT_ROOT.exists():
        shutil.rmtree(CONTEXT_ROOT)
    with tempfile.TemporaryDirectory(prefix="trace-context-text-assets-") as raw_dir:
        raw_root = Path(raw_dir)
        corpora_values: dict[str, list[str]] = {}
        manifest_counts: dict[str, int] = {}

        for relative_path, spec in CORPORA_SOURCES.items():
            raw_path = raw_root / Path(str(relative_path)).with_suffix(".json").name
            _fetch(str(spec["url"]), raw_path)
            values = _read_corpora_json(raw_path, str(spec["json_key"]))
            corpora_values[str(relative_path)] = values
            manifest_counts[str(relative_path)] = _write_manifest(CONTEXT_ROOT / str(relative_path), values)

    adjectives = corpora_values["words/adjectives_corpora.txt"]
    nouns = corpora_values["words/nouns_corpora.txt"]
    verbs = corpora_values["words/verbs_corpora.txt"]
    industries = corpora_values["domains/industries_corpora.txt"]

    phrase_specs = {
        "phrases/headlines.txt": (
            3200,
            (
                "{metric} Review for the {window}",
                "{group} {metric} Snapshot",
                "{descriptor} {metric} Brief",
                "{industry} Context Summary",
                "{metric} Notes for {group}",
                "{group} Planning Dashboard",
                "{descriptor} {metric} Report",
                "{metric} Status Update",
                "{descriptor} Context Sheet {code}",
                "{group} Reference Brief {small_number}",
                "{metric} Summary Packet {code}",
            ),
        ),
        "phrases/captions.txt": (
            2600,
            (
                "Context note for {group} during the {window}.",
                "Reference caption for {metric_lc} in the {window}.",
                "Illustrative note from the {source}.",
                "Supplemental context only; values are not part of the answer.",
                "Review caption for {industry} records.",
                "Prepared from a {descriptor_lc} sample record.",
                "Reference caption {code} for {group}.",
                "Supplemental note {small_number} for {metric_lc}.",
                "Context line from {source} during the {window}.",
                "Non-answer caption for {industry} summary {code}.",
                "{descriptor} caption for {metric_lc} review.",
            ),
        ),
        "phrases/source_notes.txt": (
            2200,
            (
                "Source: {source}, file {code}.",
                "Source note: {group} sample record {code}.",
                "Prepared from {source}; revision {small_number}.",
                "Reference: {industry} worksheet {code}.",
                "Internal source note for the {window}.",
            ),
        ),
        "phrases/footers.txt": (
            1600,
            (
                "Footer note: prepared for internal visual review.",
                "Footer note: labels are illustrative context only.",
                "Footer note: source packet {code}; page {small_number}.",
                "Prepared for {group} review during the {window}.",
                "Context footer for {metric_lc} records.",
            ),
        ),
        "phrases/sidebar_notes.txt": (
            2800,
            (
                "Sidebar: {metric} entries were reviewed {adverb}.",
                "Sidebar: {group} is tagged for {window}.",
                "Note {small_number}: {descriptor} {metric} context.",
                "{industry} sidebar note for {metric_lc}.",
                "Reference block {code}: {metric} summary.",
                "Context block: {group} status remains {descriptor_lc}.",
            ),
        ),
        "phrases/callout_phrases.txt": (
            2400,
            (
                "Check {metric}",
                "Review {group}",
                "Note {code}",
                "{descriptor} signal",
                "{metric} watch",
                "{group} marker",
                "{metric} context",
                "{percent}% reference",
            ),
        ),
        "phrases/metric_snippets.txt": (
            3600,
            (
                "{metric}: {number}",
                "{group}: {percent}%",
                "{metric} ref: {code}",
                "{metric} delta: {small_number}",
                "{group} score: {number}",
                "{industry}: {small_number} notes",
                "{metric} index {number}",
                "{descriptor} {metric_lc}: {percent}%",
            ),
        ),
        "phrases/legend_notes.txt": (
            1800,
            (
                "Guide: filled marks show included records.",
                "Guide: muted labels are reference context.",
                "Guide: {group} marks are not answer choices.",
                "Legend note: {metric_lc} labels are illustrative.",
                "Key: {code} marks a context-only note.",
                "Guide: sidebar values are supplemental.",
            ),
        ),
    }

    for relative_path, (count, templates) in phrase_specs.items():
        values = _build_template_manifest(
            rng=rng,
            templates=templates,
            count=int(count),
            adjectives=adjectives,
            nouns=nouns,
            verbs=verbs,
            industries=industries,
        )
        manifest_counts[str(relative_path)] = _write_manifest(CONTEXT_ROOT / str(relative_path), values)

    context_sentences = _build_context_sentences(
        rng=rng,
        count=5000,
        adjectives=adjectives,
        nouns=nouns,
        verbs=verbs,
        industries=industries,
    )
    manifest_counts["sentences/context_template_sentences.txt"] = _write_manifest(
        CONTEXT_ROOT / "sentences" / "context_template_sentences.txt",
        context_sentences,
    )
    context_paragraphs = _build_paragraphs(rng, context_sentences, count=2000)
    manifest_counts["paragraphs/context_template_blocks.txt"] = _write_manifest(
        CONTEXT_ROOT / "paragraphs" / "context_template_blocks.txt",
        context_paragraphs,
    )
    context_long_paragraphs = _build_long_paragraphs(rng, context_sentences, count=2000)
    manifest_counts["paragraphs/context_long_blocks.txt"] = _write_manifest(
        CONTEXT_ROOT / "paragraphs" / "context_long_blocks.txt",
        context_long_paragraphs,
    )

    _write_license_files()
    _write_readme()
    (CONTEXT_ROOT / "sources.json").write_text(
        json.dumps(_source_metadata(manifest_counts), indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest_counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
