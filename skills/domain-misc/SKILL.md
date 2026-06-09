---
name: domain-misc
description: Use when designing, implementing, or reviewing TRACE misc-domain tasks such as abacus readouts, clocks, automata, music notation, Braille-cell notation, organic-structure notation, dice probability, and spinner probability.
---

# Misc Domain

Use this whenever the task lives under `domain=misc`.

## Read first
1. `docs/domains/MISC_TASK_SETUP.md`
2. `docs/ACTIVE_TASK_INVENTORY.md` for the generated active scene/task list.
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- `misc` is a bounded parking domain for synthetic renderer families that do not yet justify a dedicated top-level domain.
- Current families are `abacus`, `automaton`, `clock`, `notation`, and `probability`.
- Do not add to `misc` when an existing renderer domain fits cleanly.
- Promote a renderer family out of `misc` if it grows into a coherent domain-scale surface.
- Public task ids use `task_misc__<scene_id>__<objective_contract>`.

## Practical review checklist
- Keep annotation minimal and role-keyed when witnesses have distinct roles.
- Abacus, clocks, and probability devices should preserve semantic marks under style/noise variation.
- Music, Braille, and chemistry notation should prioritize legibility over decorative variation.
- Automata tasks must make the rule table, initial state, and queried step/count scope visible.
- Reuse helpers under `trace/tasks/misc/shared/` before adding task-local layout or rule-building utilities.
