# Shared Label Assets

This directory is the repo-wide source for reusable prompt/render labels and
names. Task modules should load these manifests through
`trace.tasks.shared.name_assets` and then apply task-local filters for length,
spacing, punctuation, and answer-support needs.

## Manifests

- `people/first_names_ssa.txt` - SSA first names, sorted by aggregate frequency.
- `people/surnames_census_2010.txt` - 2010 U.S. Census surnames.
- `places/countries_natural_earth.txt` - Natural Earth country/region labels.
- `places/cities_natural_earth.txt` - Natural Earth populated-place labels.
- `organizations/company_tickers_sec.txt` - alphabetic SEC ticker labels.
- `organizations/company_terms_sec.txt` - generic organization terms extracted
  from SEC company names after removing corporate suffixes.
- `categories/abstract_group_labels.txt` - synthetic short neutral category labels.
- `categories/priority_labels.txt` - synthetic priority and risk category labels.
- `categories/product_labels.txt` - synthetic product or service category labels.
- `categories/status_labels.txt` - synthetic workflow status category labels.
- `occupations/occupations_bls_oews.txt` - BLS OEWS occupation titles.
- `industries/industries_bls_qcew.txt` - BLS QCEW NAICS industry titles.
- `mixed/proper_labels.txt` - broad people/place/organization/occupation/industry
  pool.
- `mixed/compact_labels.txt` - alphabetic compact pool for tight render slots.

## Source Metadata

`sources.json` records the source URL, metadata URL, license, local license file,
and row count for every manifest. The raw source downloads are intentionally not
used at runtime; they are only inputs to `scripts/build_label_assets.py`.

## Chart Label Roles

Chart tasks use `trace.tasks.charts.shared.label_assets` as the adapter layer.
Dense categorical axes and repeated chart marks should use the synthetic compact
ID resolver exposed through `sample_chart_labels()` rather than these word
manifests. Semantic legends, series names, panel names, table headers, and map
categories should use the manifest-backed entity/category resolvers with
task-local length and spacing filters.

## Regeneration

Run:

```bash
python scripts/build_label_assets.py
```

The script fetches the upstream permissive/public-domain sources, normalizes
ASCII labels, deduplicates case-insensitively, writes manifests, and refreshes
`sources.json`.
