# Shared Font Assets

TRACE keeps repo-wide reusable font assets under `assets/fonts/`. Use this
layer when a renderer draws visible text and has access to a deterministic
instance seed.

## Source Policy

The current TRACE font subset is vendored from the Google Fonts GitHub
repository. Google Fonts stores font families under top-level license
directories, and each family directory carries the font files, metadata, and
the applicable license file. The current TRACE subset uses 500 Latin-capable
OFL/Apache families with family-local license files and metadata recorded in
`assets/fonts/sources.json`.

Runtime task generation must use local files only. Do not download fonts while
generating task instances.

## Runtime Rules

1. Sample fonts deterministically from seed and namespace through
   `trace/tasks/shared/font_assets.py`.
2. Render fonts through `trace/tasks/shared/text_rendering.py`.
3. Keep existing text roles internally consistent:
   - all chart axis/category/value labels in one chart or chart panel should use
     one sampled family unless the scene explicitly has separate text regions;
   - all option labels in one option set should use one sampled family;
   - each page/document section may use one sampled family for that section;
   - context boxes may use a different sampled family per box, but heading/body
     text inside one box should normally share the same family.
4. Mixing multiple families in one image is allowed when it follows meaningful
   visual regions: title/chrome, body text, option set, chart labels, sidebar
   note, callout box, etc. Do not sample a different family per glyph, per word,
   or per answer candidate unless that variation is the task itself.
5. Record sampled answer-bearing font families in `render_spec` or scene entity
   metadata. Non-answer context text should record font family in each
   `context_text_layer.elements[]` record.
6. Font choice must be independent of answer value, correct option, query id,
   and difficulty bucket.
7. Exclude unsuitable styles per role when needed. Examples:
   - exclude `display` for tiny labels or dense tables;
   - exclude `mono` for paragraph-like body text unless the scene is technical;
   - exclude `condensed` when small labels already approach their bbox width.
8. Do not use unlicensed system fonts as the planned source of variation.
   System fonts remain fallback only.

## Available Families

The current target set is 500 readable Latin-capable families covering sans,
serif, monospace, condensed, rounded, accessible, technical, editorial,
slab-like, display, pixel, stencil, handwriting, and script styles. The expanded
set keeps the original neutral families and adds more visually distinct fonts
such as `bangers`, `black_ops_one`, `caveat`, `cookie`, `dancing_script`,
`lobster`, `pacifico`, `patrick_hand`, `press_start_2p`, and `righteous`.

The builder starts from a stable hand-curated core, then fills the remaining
families from the live Google Fonts catalog using conservative filters:
Latin coverage, open source, OFL/Apache source directories with local license
files, no color/symbol/emoji/icon/math families, no Noto script-expansion
families beyond the core Noto text families, and bounded catalog size. It also
uses category quotas so the pack has broad visual variety without sampling the
full Google Fonts catalog blindly.

Use `assets/fonts/sources.json` as the authoritative family list. It records
the family key, display name, local regular and bold font paths, license path,
source URL, and role-filter tags for every family.

See `assets/fonts/sources.json` for source URL, license path, selected regular
and bold file paths, and role-filter tags.

## API

Use deterministic family sampling:

```python
from trace.tasks.shared.font_assets import sample_font_family
from trace.tasks.shared.text_rendering import load_font

font_family = sample_font_family(
    instance_seed=instance_seed,
    namespace=f"{TASK_ID}.chart_labels_font",
    params=params,
    exclude_tags=("display",),
)
label_font = load_font(14, bold=True, font_family=font_family)
```

If a scene needs a fixed family for debugging or calibration, pass
`font_family=<family_key>` in params for the relevant sampling call, or define a
role-specific explicit key in the scene adapter.

## Regeneration

Use:

```bash
python scripts/build_font_assets.py
```

After regeneration, inspect `assets/fonts/sources.json`, compile
`trace/tasks/shared/font_assets.py` and `trace/tasks/shared/text_rendering.py`,
and generate at least one scene review for any renderer that changed font
sampling behavior.
