# Plans Progress

This file tracks short status notes for active or blocked planning work that should be easy to scan without opening the full task records.

> Non-current calibration thresholds: this file is not a calibration plan. Use
> `plans/CALIBRATION_PLAN.md` for all current model choices, rollout counts,
> response caps, acceptance gates, and domain completion rules.

## Current Status

### Active Calibration Acceptance Plan

- See `plans/CALIBRATION_PLAN.md`.

### Three-D Object Resource Registry

- 2026-05-25: `three_d` object resources are consolidated under `trace/tasks/three_d/shared/object_resources.py` with explicit resource kinds (`standalone`, `mounted`, `composite`, `variant`, `reference`), shared support/mounting metadata, and shared warehouse robot/shelf render-attribute pools. Scene modules should consume this registry rather than inventing local object identities, names, dimensions, colors, or style axes.
- Current inventory sheets live under `plans/task-reviews/three_d/named_object_inventory/`: standalone small objects, standalone large objects, and mounted/composite/variant/reference resources.
