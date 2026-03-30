# Diagrams Complexity Notes

Use these criteria when assigning or reviewing diagrams-domain complexity.

## Active family: `flow`
1. `visual_scan`
   - driven by visible node count, lane count, and whether the reader must scan across multiple rows/bands.
2. `reasoning_load`
   - driven by whether the query is a direct successor lookup or a branch-conditioned successor lookup.
3. `scene_variant_load`
   - flowcharts are the lighter baseline; swimlanes add one more layout layer because the solver must separate lane chrome from the connector structure.

## Active family: `hierarchy`
1. `visual_scan`
   - driven by visible node count, tree depth, and how many levels the reader must scan before reaching the queried nodes.
2. `reasoning_load`
   - driven by whether the query is a direct parent lookup or a lowest-common-ancestor lookup, plus how far upward the solver must trace the two query nodes.
3. `scene_variant_load`
   - early hierarchy currently uses one `org_chart` scene variant, so this stays a light constant baseline until additional hierarchy chrome is introduced.

## Active family: `cycle`
1. `visual_scan`
   - driven by visible stage count and how crowded the directed ring becomes.
2. `reasoning_load`
   - driven by whether the query asks for a stage before or after the anchor stage, plus the requested `k`-step offset around the cycle.
3. `scene_variant_load`
   - early cycle currently uses one `cycle_ring` scene variant, so this stays a light constant baseline until additional cycle chrome is introduced.

## Active family: `set_diagram`
1. `visual_scan`
   - driven by the fixed `3`-set overlap layout, visible digit count, and how many overlap regions the solver must inspect to gather operands.
2. `reasoning_load`
   - driven by whether the query asks for a single-set-only sum, a full-set total, a union, an intersection, or an “exactly two sets” total.
3. `scene_variant_load`
   - early set diagrams currently use one `set_diagram` scene variant, so this stays a light constant baseline until additional set chrome is introduced.

## General rule
1. Normalize each criterion inside the task before combining them.
2. Keep the weighted aggregate inside `[0, 1]`.
3. Prefer reasoning-local measures (number of candidate outgoing paths, branch conditioning, depth scanned) over purely aesthetic scene styling.
