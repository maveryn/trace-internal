# Agent Brief: Public API And Examples

## Objective

Make the released Trace environment understandable through small executable
examples and verify that users can generate, inspect, replay, and score tasks
without relying on internal review or migration APIs.

## Read First

- `AGENTS.md`
- `docs/README.md`
- `docs/workflows/PUBLIC_RELEASE/README.md`
- `docs/contracts/BLUEPRINT.md`
- `docs/contracts/SYSTEM_ARCHITECTURE.md`
- `docs/contracts/SOURCE_LAYOUT.md`
- `docs/workflows/TASK_AUTHORING.md`
- Current builder, registry, export, and verifier public surfaces
- The installation/import contract supplied by release engineering

## Ownership

Own `examples/`, example-focused public scripts, and focused tests that execute
those examples. Do not edit root README prose, the documentation site, paper,
canonical results, task implementations, or packaging/import names without
coordination.

## Required Examples

Provide small, deterministic examples for:

1. Listing or selecting an active task.
2. Generating one instance by public task ID.
3. Saving or viewing its image and prompt.
4. Inspecting its typed answer, verifier payload, metadata, and `trace_ref`.
5. Replaying the instance from its recorded seed/specification.
6. Scoring a correct and incorrect candidate response.
7. Exporting a tiny multi-task dataset.
8. Understanding the files required to add a minimal new task, without adding
   a fake production task to the active registry.

Annotation may appear as an optional field in inspection output, but examples
and recommended training should default to answer-only behavior.

## Public API Audit

Identify internal imports, global-registration side effects, source-checkout
assumptions, or undocumented environment variables required by the examples.
Prefer a small stable public API over examples that reach through many private
modules. Coordinate any API change with release engineering, and obtain user
approval before a package-wide import rename or compatibility layer.

## Validation

- Run examples from a clean package installation, outside the source root.
- Turn the quickstart examples into focused CI smoke tests.
- Verify deterministic replay rather than merely successful generation.
- Verify both accepted and rejected candidate answers.
- Keep runtime and output small enough for ordinary contributor hardware.
- Ensure examples contain no local absolute paths or private assets.

Provide runnable scripts, not notebook-only demonstrations. Use the shared
handoff format in `README.md` and include observed clean-install runtimes.

