---
name: domain-tables
description: Use when designing, implementing, or reviewing TRACE table-domain tasks, especially for styled table scene variants, bbox evidence policy, row/column summary structure, and table shared-helper reuse.
---

# Tables Domain

Use this whenever the task lives under `domain=tables`.

## Read first
1. `docs/domains/TABLE_TASK_SETUP.md`
2. `docs/project/STATUS.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- Treat `docs/domains/TABLE_TASK_SETUP.md` as the active table contract; do not duplicate its task/evidence inventory here.
- Keep `task_group` aligned to reasoning family, not table style.
- Use `scene_variant` for visual table styling only; `spreadsheet`, `zebra`, `ledger`, and `card_table` must not change table semantics.
- Keep table evidence prompt-facing as `bbox_set`, with ordering and minimal supporting regions defined by the setup doc.
- Reuse `trace/tasks/shared/name_assets.py` for visible person-style row labels.

## Review checklist
- Confirm prompts name queried rows, columns, cells, years, filters, ranks, or intervals explicitly enough that the supporting bbox evidence is unambiguous.
- Preserve deterministic bbox ordering whenever prompt order or row order matters.
- Keep table helper reuse under `trace/tasks/tables/shared/` unless the helper is cross-domain enough for `trace/tasks/shared/`.
- Add a `task_variant` when answer/evidence contracts stay the same; split the task only when the prompt or evidence contract materially changes.
- Prefer readable tables over schema complexity: short labels, moderate row/column counts, and style variation through borders, shading, and framing.
