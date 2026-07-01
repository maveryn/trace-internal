# Visual Candidate-Set Modulo Audit

This report audits modulo use around visual attributes such as colors, styles, labels, shapes, themes, symbols, and option layouts. Random candidate-set selection should use RNG sampling from an explicit support or range. Modulo is acceptable only for deterministic assignment from an already-selected list or for intentional repeat cycling.

## Summary

- Total visual modulo sites: 15
- Random candidate selection needs refactor: 0
- Sampling-time assignment needs review: 0
- Needs manual review: 2
- Likely safe deterministic assignment: 13

## Random Candidate Selection Needs Refactor

None found.

## Sampling-Time Assignment Needs Review

None found.

## Needs Manual Review

| File | Line | Reason | Snippet |
| --- | ---: | --- | --- |
| `trace/tasks/symbolic/music_staff/shared/components.py` | 1042 | visual modulo found, but candidate-set vs assignment role is unclear | `step = int(steps[index % len(steps)])` |
| `trace/tasks/symbolic/organic_structure/shared/rules.py` | 203 | visual modulo found, but candidate-set vs assignment role is unclear | `ring_atoms[(edge_index + 1) % len(ring_atoms)],` |

## Likely Safe Deterministic Assignment

| File | Line | Reason | Snippet |
| --- | ---: | --- | --- |
| `trace/core/review_overlays.py` | 282 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 290 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 300 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 309 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 329 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 336 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 345 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 350 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 353 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/tasks/symbolic/agent_automaton/shared/rendering.py` | 70 | render/review code cycles through an already-selected palette or repeated style list | `fill = tuple(int(value) for value in state_colors[state % len(state_colors)])` |
| `trace/tasks/symbolic/radial_code_wheel/shared/rendering.py` | 253 | render/review code cycles through an already-selected palette or repeated style list | `base = fill_sources[sector_index % len(fill_sources)]` |
| `trace/tasks/symbolic/radial_code_wheel/shared/rendering.py` | 298 | render/review code cycles through an already-selected palette or repeated style list | `symbol = CODE_SYMBOLS[sector_index % len(CODE_SYMBOLS)]` |
| `trace/tasks/symbolic/turing_tape/shared/rendering.py` | 89 | render/review code cycles through an already-selected palette or repeated style list | `symbol: tuple(style.state_colors[index % len(style.state_colors)])` |
