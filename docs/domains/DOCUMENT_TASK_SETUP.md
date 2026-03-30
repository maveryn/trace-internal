# Documents Task Setup

This document captures the concrete reusable setup for the first `documents` task family.

## 1) Domain scope
1. `domain=documents` is for visually structured page-like artifacts such as forms, invoices, receipts, tickets, and other field-heavy layouts.
2. V1 document tasks should stay layout-first and OCR-light:
   - short typed fields,
   - stable labeled regions,
   - no long paragraphs or handwriting.
3. The domain should test reading and local field reasoning over structured pages, not generic table QA with a paper skin.

## 2) First reusable scene contract
1. V1 document scenes use one page on a light background.
2. The first active scene variants are:
   - `form_sheet`
   - `invoice_sheet`
   - `receipt_sheet`
3. Every scene variant keeps the same semantic contract:
   - visible labeled fields,
   - one associated visible field value,
   - one queried field chosen from the rendered document itself.
4. Layout variation should come from reusable block grammars, not free-form random page composition:
   - boxed field grids,
   - structured header bands,
   - receipt-style labeled rows.

## 3) Text-generation policy
1. Use typed field generators, not raw free-form text generation.
2. Good early field families:
   - identifiers,
   - names,
   - dates,
   - contact fields,
   - currency amounts.
3. Upstream text sources may be realistic, but rendered values should always be:
   - normalized,
   - short enough to fit the active layout,
   - resampled rather than blindly truncated if they overflow,
   - unique among visible field values in the same document.
4. Record the final visible field text in trace metadata; that visible string is the source of truth for both answer and verifier payload.

## 4) Active family
1. `task_group=readout`
2. Active task:
   - `task_documents_readout_field_value`
3. Active semantic variants:
   - `lookup_identifier`
   - `lookup_name`
   - `lookup_date`
   - `lookup_contact`
   - `lookup_amount`
4. Active visual variants:
   - `form_sheet`
   - `invoice_sheet`
   - `receipt_sheet`

## 5) Evidence policy
1. Field-readout tasks should keep prompt-facing evidence local and ordered:
   - first the queried field label bbox,
   - then the queried field value bbox.
2. Do not use the full page bbox as prompt-facing evidence for simple field lookup.
3. If a later document task uses keyed region counts or checkbox counts, prefer the smallest visible witness units rather than page-level evidence.

## 6) Reuse guidance
1. Keep document-axis resolution and bbox evidence helpers under `trace/tasks/documents/shared/common.py`.
2. Keep typed field-value generation under `trace/tasks/documents/shared/text_generation.py`.
3. Keep reusable document layout sampling and render-param resolution under `trace/tasks/documents/shared/document_common.py`.
4. Keep reusable document page rendering under `trace/tasks/documents/shared/document_scene.py`.
5. Future document tasks should reuse the same page grammar before adding genuinely new task groups.
