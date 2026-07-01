# Semantic Sampling Modulo Audit: First Pass

This report flags source patterns where modulo/index cycling may be standing in for semantic random sampling. Task random sampling should draw from an explicit support or bounded range with uniform or weighted probabilities. It is a static first pass; each refactor site still needs source-level confirmation before editing.

## Summary

- Raw line findings: 16
- Grouped selection sites: 16
- Needs refactor: 0
- Needs manual review: 0
- Review harness stratification / round-robin: 1
- Allowed deterministic visual/layout enumeration: 15

## Needs Refactor

None found.

## Needs Manual Review

None found.

## Review Harness Stratification / Round-Robin

| File | Lines | Kind | Raw Lines | Reason | Snippets |
| --- | ---: | --- | ---: | --- | --- |
| `trace/core/task_review_sampling.py` | 188 | modulo_index | 1 | allowed only because this is explicit review/dataset coverage, not task randomness | `query_id_value = str(pending_query_ids[int(query_id_index) % len(pending_query_ids)])` |

## Allowed Deterministic Visual/Layout Enumeration

| File | Lines | Kind | Raw Lines | Reason | Snippets |
| --- | ---: | --- | ---: | --- | --- |
| `trace/core/review_overlays.py` | 282 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 290 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 300 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 309 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 329 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 336 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 345 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 350 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 353 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/tasks/symbolic/agent_automaton/shared/rendering.py` | 70 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = tuple(int(value) for value in state_colors[state % len(state_colors)])` |
| `trace/tasks/symbolic/music_staff/shared/components.py` | 1042 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `step = int(steps[index % len(steps)])` |
| `trace/tasks/symbolic/organic_structure/shared/rules.py` | 203 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `ring_atoms[(edge_index + 1) % len(ring_atoms)],` |
| `trace/tasks/symbolic/radial_code_wheel/shared/rendering.py` | 253 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `base = fill_sources[sector_index % len(fill_sources)]` |
| `trace/tasks/symbolic/radial_code_wheel/shared/rendering.py` | 298 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `symbol = CODE_SYMBOLS[sector_index % len(CODE_SYMBOLS)]` |
| `trace/tasks/symbolic/turing_tape/shared/rendering.py` | 89 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `symbol: tuple(style.state_colors[index % len(style.state_colors)])` |
