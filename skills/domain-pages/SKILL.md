---
name: domain-pages
description: Use when designing, implementing, or reviewing TRACE pages-domain tasks, especially structured forms, process diagrams, static maps, GUI/web screens, schedules, schemas, and OCR-light page reasoning.
---

# Pages Domain

Use this whenever the task lives under `domain=pages`.

## Read first
1. `docs/domains/PAGES_TASK_SETUP.md`
2. `docs/ACTIVE_TASK_INVENTORY.md` for the generated active scene/task list.
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- Treat `pages` as structured page reasoning over forms, diagrams, static maps, timelines, schedules, schemas, and GUI/web screens, not generic OCR over arbitrary prose.
- Active page tasks put the concrete query branch in `query_id`; `query_id` is an internal replay selector.
- Prefer broad task groups such as `arithmetic`, `calendar`, `concept_map`, `cross_form`, `cycle`, `hierarchy`, `infographic`, `map`, `process_flow`, `schedule`, `schema`, `counting`, and `relation` over one-off page templates.
- Keep one reusable page grammar whenever multiple tasks share the same scaffold.
- Keep prompts explicit about the requested field, section, control, event, route, or node so correctness does not depend on hidden layout assumptions.
- `docs/domains/PAGES_TASK_SETUP.md` owns the active pages contract.

## Boundary reminders
- If the chart data model is the semantic source of truth, use `charts` even when the visual looks like a table or report.
- If the page layout, document sections, controls, form fields, process steps, or structured regions are the semantic source of truth, use `pages`.
- If the task depends mostly on long paragraphs or free-form OCR, it is not a good pages task.
- Strong pages tasks stay local to typed fields, route landmarks, node boxes, controls, rows, event blocks, guide cards, or other clear visible boxes.

## Practical review checklist
- Keep prompts explicit about the queried field, section, step, event, or control; do not rely on layout conventions alone.
- Keep text typed and controlled; prefer normalization plus resampling over blind truncation.
- Keep prompt-facing evidence local to the decisive field, section header, value, checkbox, control, route landmark, step, event, or schema witness.
- For role-keyed page evidence, use concrete visible-role keys. Prefer names like `purchase_code`, `receiving_code`, `action_code_header`, `code_target_row`, `target_button`, or `endpoint_step` over generic keys like `context`, `guide_card`, `path_context`, or `target_control` when the scene has a specific witness type.
- Reuse one page grammar across families before adding a new scaffold.
- Preserve the layout-first, OCR-light boundary; avoid drifting into long-form paragraph OCR or generic table-on-paper tasks.
