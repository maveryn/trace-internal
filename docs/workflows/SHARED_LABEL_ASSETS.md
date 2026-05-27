# Shared Label Assets

TRACE keeps repo-wide reusable text labels under `assets/labels/`. Use this
layer for visible node labels, chart categories, page names, legend names,
organization-style tokens, place names, and other prompt/render labels that are
not task-specific.

## Rules

1. Load labels through `trace.tasks.shared.name_assets`.
   Graph-domain tasks should use `trace.tasks.graph.shared.label_assets`
   instead, which applies the graph label caps and eligible-bucket rules on top
   of these same manifests.
2. Keep task-specific constraints at the task call site. For example, a graph
   task that needs short edge labels should filter `mixed/compact_labels.txt`
   with `min_chars`, `max_chars`, `allow_spaces`, and `allow_punctuation`
   instead of creating a graph-only manifest.
3. Do not hardcode new one-off proper-name lists inside task modules.
4. Use only permissively licensed or public-domain sources. Add the source and
   local license metadata to `assets/labels/sources.json` when a manifest is
   added or regenerated.
5. Runtime generation must read vendored manifests only. Do not download label
   data during task generation.
6. If a task needs answer strings, make sure the rendered label, answer value,
   and verifier normalization policy are decided together. Avoid silent
   case-folding unless the verifier explicitly supports it.

## Available Pools

- `people/first_names_ssa.txt`
- `people/surnames_census_2010.txt`
- `places/countries_natural_earth.txt`
- `places/cities_natural_earth.txt`
- `organizations/company_tickers_sec.txt`
- `organizations/company_terms_sec.txt`
- `categories/abstract_group_labels.txt`
- `categories/priority_labels.txt`
- `categories/product_labels.txt`
- `categories/status_labels.txt`
- `occupations/occupations_bls_oews.txt`
- `industries/industries_bls_qcew.txt`
- `mixed/proper_labels.txt`
- `mixed/compact_labels.txt`

For chart-domain tasks, prefer `trace.tasks.charts.shared.label_assets` over
calling `load_label_manifest(...)` directly. That helper exposes reusable
entity-label and category-label bucket selection while still recording the
manifest/filter metadata needed for trace/debug review.

## API

```python
from trace.tasks.shared.name_assets import load_label_manifest

labels = load_label_manifest(
    "mixed/compact_labels.txt",
    min_chars=5,
    max_chars=10,
    allow_spaces=False,
    allow_punctuation=False,
    compact_length=False,
)
```

Use `load_label_sources()` when review tooling or documentation needs source
and license metadata.

## Regeneration

Use `scripts/build_label_assets.py` to refresh the vendored manifests. The
script fetches the upstream sources, normalizes ASCII label strings, deduplicates
case-insensitively, writes the manifests, and updates `sources.json`.
