---
name: domain-maps
description: Use when designing, implementing, or reviewing TRACE maps-domain tasks, especially region/legend reasoning, transit-map follow-ons, and clean evidence contracts for synthetic map scenes.
---

# Maps Domain

Use this whenever the task lives under `domain=maps`.

## Read first
1. `docs/project/STATUS.md`
2. `docs/project/TODO.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`
5. `docs/workflows/CODE_REVIEW_GUIDELINES.md`
6. `docs/domains/MAP_TASK_SETUP.md`

## Maps-domain rules
- Treat `maps` as map-native visual reasoning, not generic graph problems with map styling.
- Prefer broad families such as `region`, `transit`, `legend`, and later `orientation` over one-off map templates.
- Reuse one shared scene contract whenever multiple tasks use the same map grammar.
- Keep prompts explicit about the visual rule when the legend order or transit convention matters.

## Boundary rules
- If the task is mostly generic pathfinding or reachability, it probably belongs in `tile` or a future graph family rather than `maps`.
- If the reasoning depends on map-native features such as region fills, legend bins, line colors, transfer stations, or ordered named stops, it is a good fit for `maps`.

## Early-family guidance
- `region`: thematic/choropleth maps with labeled regions plus legends.
- Early `region` scene variants can range from clean card/outline presentations to more atlas-style region maps, as long as they reuse the same region partition + legend semantics and keep evidence grounded on the answer region.
- Current region family tasks are a good template: association uses one winning region bbox, while count-style tasks should use one ordered bbox per counted region.
- `transit` later: subway or rail maps with line colors, transfers, and ordered stations.
- Avoid OCR-heavy or free-form route-string tasks in the first wave.

## Evidence rules
- Region-label tasks should usually ground prompt-facing evidence on the winning region bbox.
- Region-count tasks may use one bbox per counted region in reading order.
- Keep legend evidence local only when the prompt truly asks about the legend item itself.

## Color policy
- Whenever a map task's reasoning depends on legend colors, enforce or validate per-instance palette separation in Lab space.
- Record the active color-distance threshold and space in trace metadata.

## First-family lessons
- The first reusable map scene should be synthetic and stylized rather than tied to real country outlines.
- A contiguous hidden cell partition rendered as merged regions is a good early contract because it stays reusable for multiple region tasks.
- Legend order should carry the category semantics explicitly so tasks do not depend on users guessing an unstated darker-is-higher rule.
