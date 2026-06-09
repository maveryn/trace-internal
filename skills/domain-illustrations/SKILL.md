---
name: domain-illustrations
description: Use when designing, implementing, or reviewing TRACE illustration-domain tasks, especially synthetic object drawing, semantic part metadata, visible-part annotation, and object-scene visual diversity.
---

# Illustrations Domain

Use this whenever the task lives under `domain=illustrations`.

## Read first
1. `docs/domains/ILLUSTRATIONS_TASK_SETUP.md`
2. `docs/ACTIVE_TASK_INVENTORY.md` for the generated active scene/task list.
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- `docs/domains/ILLUSTRATIONS_TASK_SETUP.md` owns the active illustrations contract and object-part annotation policy.
- Illustrations use synthetic drawings of recognizable objects, not natural images, icon silhouettes, or free-form captions.
- Reuse object drawers and scene helpers under `trace/tasks/illustrations/shared/` before adding task-local rendering.
- Each rendered object should expose object bboxes plus semantic part bboxes from the same drawing trace.
- Environment scenes should expose roads/rivers/buildings as semantic entities with pixel-space paths, bboxes, and relation metadata; task verifiers must use those records, not rendered pixels.
- Keep placement context natural: sky-capable objects in sky bands, vehicles on roads, water objects in water, and land/surface objects outside road/river feature bands. Use theme-specific land-object pools so city scenes favor pedestrians/street fixtures and meadow/park scenes favor animals/plants/outdoor objects. Dense city/canal themes can use lower foreground-object caps to preserve readability.
- Treat clouds/sun as sky décor unless a future task explicitly promotes them to counted foreground objects.
- Treat benches, signs, streetlamps, traffic lights, trash bins, and similar placed scene fixtures as foreground objects unless a task explicitly marks them as non-counted décor.
- Prompt-facing annotation should stay in final-image pixel coordinates, usually as `bbox_set` over counted objects or parts.

## Practical review checklist
- Verify the answer comes from rendered object/part records, not canonical real-world assumptions.
- Keep style and background variation non-semantic.
- Prefer explicit target/distractor construction over hoping random object mixtures realize the requested count.
- Ensure visible-part tasks count only parts actually rendered and grounded by part bboxes.
- Add new tasks only when the answer/annotation contract or visual scaffold is meaningfully different; otherwise use `query_id` or sampled params.
