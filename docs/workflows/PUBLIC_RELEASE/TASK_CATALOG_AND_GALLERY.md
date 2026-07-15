# Agent Brief: Task Catalog And Visual Gallery

## Objective

Build a generated, visually compelling catalog that demonstrates Trace's task
breadth without creating a second hand-maintained inventory or committing the
internal review workspace.

## Read First

- `AGENTS.md`
- `docs/README.md`
- `docs/workflows/PUBLIC_RELEASE/README.md`
- `docs/ACTIVE_TASK_INVENTORY.md`
- `docs/contracts/TAXONOMY.md`
- `docs/contracts/PROGRAM_SCHEMA_CATALOG.md`
- `docs/tasks/README.md`
- `scripts/generate_active_task_inventory.py`

## Ownership

Own catalog-generation scripts, generated catalog pages, gallery manifests,
and optimized public gallery images. Do not edit task implementations,
prompts, configs, root README prose, paper prose, or canonical result data.

## Required Deliverables

1. Generate domain and scene indexes from the active registry/inventory.
2. Represent all active tasks without manually duplicating task IDs.
3. For each task expose, where available:
   - public task ID;
   - domain and scene;
   - objective/contract name;
   - answer type;
   - annotation type as secondary metadata;
   - program or reasoning contract;
   - links to source and task documentation.
4. Produce a curated gallery spanning all 11 domains and varied visual
   grammars. Use deterministic examples generated through the public task
   system, not copied review-app artifacts.
5. Produce a high-quality hero montage for the README/docs handoff.
6. Optimize web assets while preserving legibility. Keep original generation
   provenance in a machine-readable manifest.
7. Add a freshness check that detects disagreement among registry, active
   inventory, task documentation, and generated catalog.

## Constraints

- Do not commit `review/task-reviews/` or issue-state data.
- Do not generate a giant manually curated navigation entry for every task.
- Avoid adding hundreds of unnecessary full-resolution images to Git history.
- Do not silently skip tasks that fail catalog extraction. Report failures.
- A visual defect found during gallery generation is a release issue to report,
  not permission to redesign the task in this workstream.

## Validation

- Regenerate the catalog from a clean checkout.
- Confirm the reported totals equal the active inventory.
- Confirm every public source/doc link resolves.
- Inspect every selected gallery image at rendered documentation size.
- Record generation seeds, task IDs, dimensions, and source revisions.

Use the shared handoff format in `README.md` and identify the catalog and
gallery manifest paths consumed by the documentation and paper agents.

