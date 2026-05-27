# Prism Curated Icon Set

This folder contains the finalized manually curated icon pool for Prism tasks.

Contents:
- `non_symmetry.txt`: 2000 icons
- `symmetry.txt`: 1000 icons
- `all_icons.txt`: union (3000 icons)
- `svgs/`: copied SVG files (`light-<icon>.svg`) for the 3000 curated icons
- `licenses/`: upstream licenses for the included icon sources
- `source_counts.json`: source distribution across the curated set

Tasks should resolve only the full curated manifests through
`trace/tasks/icons/shared/icon_assets.py`; the default full pool is
`all_icons.txt` with all 3000 icons.
