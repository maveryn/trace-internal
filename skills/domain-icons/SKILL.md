---
name: domain-icons
description: Use when designing, implementing, or reviewing TRACE icon-domain tasks, especially curated icon-pool selection, reference-vs-scene layout choices, evidence typing, and icon-specific ambiguity checks.
---

# Icons Domain

Use this whenever the task lives under `domain=icons`.

## Read first
1. `docs/domains/ICON_TASK_SETUP.md`
2. `docs/ACTIVE_TASK_INVENTORY.md` for the generated active scene/task list.
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- `docs/domains/ICON_TASK_SETUP.md` owns the active icons contract, asset policy, and evidence policy.
- Active icon tasks emit public `query_variant="default"` and put the concrete branch in `query_id`; old `query_variant` params may still be used to force a query for reviews.
- Use icon manifests only through `trace/tasks/icons/shared/icon_assets.py`.
- Use asymmetric icons when orientation, mirror symmetry, transformation identity, or attribute binding can collapse under icon symmetry.
- Keep prompt-facing evidence on the semantic visual unit: icon-instance `bbox_set`, scene-cell `bbox_set`, or one local bbox for missing/violating slots.

## Practical review checklist
- Prefer explicit target/distractor construction over relying on random icon placement to realize the answer.
- Keep visual ambiguity checks tied to the queried predicate: size gaps for size tasks, rendered signatures for mirror tasks, rule-hypothesis rejection for pattern tasks.
- Reuse icon helpers under `trace/tasks/icons/shared/` before adding task-local layout or rendering utilities.
- Add new icon-query variants inside an existing task when the scaffold and witness semantics stay the same.
- Split only when a new icon query changes the perceptual contract enough to be a healthy standalone task.
