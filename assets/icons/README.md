# Prism Curated Icon Set

This folder contains the finalized manually curated icon pool for Prism tasks.

Contents:
- `non_symmetry.txt`: 2000 icons
- `symmetry.txt`: 1000 icons
- `all_icons.txt`: union (3000 icons)
- `non_symmetry_train.txt` / `non_symmetry_dev.txt`: fixed split manifests
- `symmetry_train.txt` / `symmetry_dev.txt`: fixed split manifests
- `all_train.txt` / `all_dev.txt`: combined split manifests (2400 / 600)
- `svgs/`: copied SVG files (`light-<icon>.svg`) for the 3000 curated icons
- `licenses/`: upstream licenses for the included icon sources
- `source_counts.json`: source distribution across the curated set

Split generation is deterministic and reproducible:
- script: `python-scripts/split_prism_icon_sets.py`
- seed: `42`
- train fraction: `0.8`
