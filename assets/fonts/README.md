# Shared Font Assets

This directory stores a curated TRACE-vendored subset of permissively
licensed fonts for deterministic visual variation in generated tasks.
The current subset is downloaded from the Google Fonts GitHub repository
and uses family-local license files recorded in `sources.json`.

Task renderers should sample font families through
`trace/tasks/shared/font_assets.py` and render them through
`trace/tasks/shared/text_rendering.py`. Do not download font files at
runtime generation time.

Run:

```bash
python scripts/build_font_assets.py
```
