# Repo Declutter Plan

## Purpose
Reduce documentation and skill clutter without losing important source-of-truth guidance.

This plan is about making the repo easier to navigate and maintain. The goal is not to delete useful information; it is to remove duplicated active inventories, shorten skills back into thin operational overlays, and make it obvious which document owns each contract.

## Working principles
1. `docs/` remains the source of truth; `skills/` should stay thin.
2. Each domain should have one clear active-contract surface. Long-term planning notes are fine only when they stay future-facing instead of repeating active setup details.
3. Index pages should route readers to the right source-of-truth doc, not restate large chunks of domain/workflow policy.
4. Repeated status/coverage/task inventories should live in the narrowest canonical place possible.
5. Cleanup should happen incrementally: domain by domain first, then a global pass over shared docs and skills.

## What we are cleaning up
- duplicated active setup details across domain planning docs and setup docs
- skills that restate large parts of domain/workflow docs instead of pointing to them
- index pages that repeat too much detail instead of acting as navigation
- stale or weakly differentiated planning notes that can be folded into a clearer canonical doc

## Domain-pass checklist
For each domain:
1. Identify the active contract doc(s).
2. Separate active contract content from long-term planning content.
3. Remove duplicated active inventories from planning docs.
4. Trim the domain skill so it mostly points to the contract docs plus a short operational checklist.
5. Update navigation text if the canonical entry point changed.

## Pass order
1. `charts`
2. `diagrams`
3. `documents`
4. `games`
5. `geometry`
6. `graph`
7. `icons`
8. `physics`
9. `puzzles`
10. `tables`
11. `temporal`
12. `tile`

## Global pass checklist
After the domain passes:
1. simplify `docs/README.md`, `docs/domains/README.md`, and `docs/workflows/README.md`
2. trim cross-cutting skills so they remain execution overlays
3. retire or merge weakly differentiated planning docs
4. remove repeated coverage/status callouts that already live in `docs/project/STATUS.md` or `docs/domains/TASK_FAMILY_VARIANTS.md`
5. check that every surviving doc has a clear ownership boundary

## Progress tracker
| Surface | Status | Notes |
| --- | --- | --- |
| `charts` | completed | `CHART_DOMAIN_PLAN.md` is now future-facing, the active contract stays in `CHART_TASK_SETUP.md`, and `skills/domain-charts/` is back to a thin overlay |
| `diagrams` | completed | active contract clarified in `DIAGRAM_TASK_SETUP.md`; `skills/domain-diagrams/` trimmed back to a thin overlay |
| `documents` | completed | active contract clarified in `DOCUMENT_TASK_SETUP.md`; `skills/domain-documents/` trimmed back to a thin overlay |
| `games` | completed | repeated active coverage snapshot removed from `GAMES_TASK_SETUP.md`; `skills/domain-games/` now points to the active contract instead of duplicating coverage/helper inventories |
| `geometry` | completed | duplicate geometry headings clarified in `TASK_FAMILY_VARIANTS.md`; stale evidence note removed and `skills/domain-geometry/` trimmed back to an overlay |
| `graph` | completed | active contract clarified in `GRAPH_TASK_SETUP.md`; `skills/domain-graph/` trimmed back to a thin overlay instead of duplicating evidence/coverage/helper inventories |
| `icons` | completed | new `ICON_TASK_SETUP.md` owns active icon contract/asset policy; duplicated icon task blocks removed from `TASK_FAMILY_VARIANTS.md`; `skills/domain-icons/` trimmed to an overlay |
| `physics` | completed | repeated active coverage snapshot removed from `PHYSICS_TASK_SETUP.md`; `skills/domain-physics/` trimmed back to a thin overlay |
| `puzzles` | completed | active contract clarified in `PUZZLE_TASK_SETUP.md`; `skills/domain-puzzles/` rewritten as a thin overlay instead of duplicating family/evidence lessons |
| `tables` | completed | active contract clarified in `TABLE_TASK_SETUP.md`; `skills/domain-tables/` trimmed back to a thin overlay instead of duplicating task/evidence/design inventories |
| `temporal` | completed | active contract clarified in `TEMPORAL_TASK_SETUP.md`; prompt-contract numbering fixed; `skills/domain-temporal/` trimmed back to a thin overlay |
| `tile` | completed | active contract clarified in `TILE_TASK_SETUP.md`; `skills/domain-tile/` trimmed back to a thin overlay instead of duplicating setup and coverage references |
| global docs/skills pass | completed | root/domain/workflow indexes simplified, stale cross-cutting skill references removed, and orphaned graph inventory dropped from `TASK_FAMILY_VARIANTS.md` |
