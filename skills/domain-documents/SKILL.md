---
name: domain-documents
description: Use when designing, implementing, or reviewing TRACE documents-domain tasks, especially structured forms, invoices, receipts, and other OCR-light field-based document reasoning.
---

# Documents Domain

Use this whenever the task lives under `domain=documents`.

## Read first
1. `docs/project/STATUS.md`
2. `docs/project/TODO.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`
5. `docs/workflows/CODE_REVIEW_GUIDELINES.md`
6. `docs/domains/DOCUMENT_TASK_SETUP.md`

## Documents-domain rules
- Treat `documents` as structured page reasoning, not generic OCR over arbitrary prose.
- Prefer broad families such as `readout`, `forms`, `line_items`, and later `selection` over one-off page templates.
- Keep one reusable page grammar whenever multiple tasks share the same document scaffold.
- Keep prompts explicit about the requested field so correctness does not depend on hidden assumptions about layout conventions.

## Boundary rules
- If the scene is really just a table on paper, it probably belongs in `tables` unless the surrounding document layout materially changes the task.
- If the task depends mostly on long paragraphs or free-form OCR, it is not a good v1 documents task.
- If the task can stay local to one or two typed fields with clear visible boxes, it is a strong early `documents` fit.

## Early-family guidance
- `readout`: one queried field, one exact visible value.
- Early scene variants can range from boxed forms to invoice sheets and receipt rows, as long as they reuse the same label/value field semantics.
- Keep text generation typed and controlled:
  - identifiers,
  - names,
  - dates,
  - contact fields,
  - amounts.

## Evidence rules
- Field lookup tasks should usually ground prompt-facing evidence on the queried field label bbox plus the queried field value bbox, in that order.
- Keep page-level boxes and section chrome in trace for review, but do not widen simple field-readout evidence to the entire document.

## Text policy
- Use realistic upstream text sources only through typed wrappers.
- Prefer normalization + resampling over blind truncation.
- Visible field values should be unique inside one document when the answer is one exact text string.

## First-family lessons
- A few strong layout grammars beat unconstrained page randomness.
- Structured-random documents should vary through reusable blocks, spacing, and field selection rather than arbitrary paragraph noise.
- Typed field generators make later document tasks much easier to verify than raw free-form text.
