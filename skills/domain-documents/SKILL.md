---
name: domain-documents
description: Use when designing, implementing, or reviewing TRACE documents-domain tasks, especially structured forms, invoices, receipts, and other OCR-light field-based document reasoning.
---

# Documents Domain

Use this whenever the task lives under `domain=documents`.

## Read first
1. `docs/domains/DOCUMENT_TASK_SETUP.md`
2. `docs/project/STATUS.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- Treat `documents` as structured page reasoning, not generic OCR over arbitrary prose.
- Prefer broad families such as `readout`, `arithmetic`, `layout`, `relation`, `selection`, `forms`, and later `line_items` over one-off page templates.
- Keep one reusable page grammar whenever multiple tasks share the same document scaffold.
- Keep prompts explicit about the requested field so correctness does not depend on hidden assumptions about layout conventions.
- `docs/domains/DOCUMENT_TASK_SETUP.md` owns the active documents contract.

## Boundary reminders
- If the scene is really just a table on paper, it probably belongs in `tables` unless the surrounding document layout materially changes the task.
- If the task depends mostly on long paragraphs or free-form OCR, it is not a good v1 documents task.
- If the task can stay local to one or two typed fields with clear visible boxes, it is a strong early `documents` fit.

## Practical review checklist
- Keep prompts explicit about the queried field or section; do not rely on layout conventions alone.
- Keep text typed and controlled; prefer normalization + resampling over blind truncation.
- Keep prompt-facing evidence local to the decisive field, section header, value, or checkbox witness.
- Reuse one page grammar across families before adding a new document scaffold.
- Preserve the layout-first, OCR-light boundary; avoid drifting into long-form paragraph OCR or generic table-on-paper tasks.
