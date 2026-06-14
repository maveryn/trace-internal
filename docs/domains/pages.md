# Pages Domain Contract

Use this document for pages-domain rules. Exact active scenes and tasks live in
`docs/ACTIVE_TASK_INVENTORY.md` and `docs/tasks/pages/`.

## Scope
Pages covers structured page reasoning over forms, documents, process diagrams,
timelines, schedules, calendars, schema diagrams, GUI/web screens, static maps,
and infographic-style layouts. Tasks should be OCR-light: they may use typed
labels and short fields, but should not depend on long-form prose extraction.

Use `pages` when page layout, section structure, controls, fields, routes,
steps, or document regions are the semantic source of truth. Use `charts` when
the semantic source is a data display, and `graphs` when topology is the source.

## Scene Boundary
A scene is a reusable page scaffold: calendar grid, form, schedule, GUI, map,
process flow, hierarchy, concept map, schema, infographic, or route/layout
surface. Variant styling, fonts, section titles, themes, and short text pools
may vary inside a scene.

Create a new scene when the page grammar changes enough that fields, controls,
nodes, sections, or routes no longer share a common verifier structure.

## Task And Query Boundary
Split tasks when the program changes between field lookup, section-local count,
route/path reasoning, control selection, process step reasoning, schema
relation, option matching, or calendar/schedule computation.

Valid `query_id` axes include mirrored directions, named field/section choices,
threshold direction, selected control type, or bounded target attributes inside
one stable program.

## Annotation Policy
Annotation should mark the decisive visible field, section, checkbox/control,
event block, route landmark, process step, schema row/edge, map region, or
option image. Use keyed annotation when multiple roles matter, such as source
field vs target field, action header vs target row, route start vs route end,
or input vs output step.

For zero-count tasks, an empty set is allowed when the countable witness set is
empty; do not widen annotation to a whole section unless the section itself is
the queried witness.

## Prompt And Text
Prompts should name the queried field, section, event, control, route, node, or
step explicitly. Avoid requiring hidden page-layout conventions.

Use controlled short text, shared label pools, and shared context text. Keep
distractor text non-answering and visibly separated from required fields,
labels, and annotation targets.

## Shared Code
Reusable page layout, text fitting, form/control rendering, route mapping,
schema drawing, and section indexing helpers belong under
`trace/tasks/pages/shared/`. Scene-local helpers should stay inside the scene
package when tied to one scaffold.
