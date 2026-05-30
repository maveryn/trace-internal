# Shared Font Assets

This directory stores a curated TRACE-vendored subset of permissively
licensed fonts for deterministic visual variation in generated tasks.
The current subset is downloaded from the Google Fonts GitHub repository
and uses family-local license files recorded in `sources.json`.

Task renderers should sample font families through
`trace/tasks/shared/font_assets.py` and render them through
`trace/tasks/shared/text_rendering.py`. Do not download font files at
runtime generation time.

`readout_pool_v0.json` shortlists 100 narrow, legible families for answer-bearing/read-required
text such as measurements, chart labels, table cells, graph node labels, and
compact game option text. Decorative titles, context text, and non-semantic
visual dressing may still use the broader 500-family manifest when readability
does not affect solving.

Runtime renderers should sample through the shared role-aware font dispatcher:
`readout` for required labels/readouts, `context` for non-answer chrome or
side notes, and `decorative` for non-semantic visual dressing. System fonts such
as DejaVu Sans and Liberation Sans are fallback/reference fonts only, not
vendored TRACE dataset assets.

To regenerate the readout-pool inspection artifact, run:

```bash
python scripts/generate_readout_font_spritesheet.py
```

Run:

```bash
python scripts/build_font_assets.py
```
