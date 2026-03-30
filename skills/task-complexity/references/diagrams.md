# Diagrams Complexity Notes

Use these criteria when assigning or reviewing diagrams-domain complexity.

## Active family: `flow`
1. `visual_scan`
   - driven by visible node count, lane count, and whether the reader must scan across multiple rows/bands.
2. `reasoning_load`
   - driven by whether the query is a direct successor lookup or a branch-conditioned successor lookup.
3. `scene_variant_load`
   - flowcharts are the lighter baseline; swimlanes add one more layout layer because the solver must separate lane chrome from the connector structure.

## General rule
1. Normalize each criterion inside the task before combining them.
2. Keep the weighted aggregate inside `[0, 1]`.
3. Prefer reasoning-local measures (number of candidate outgoing paths, branch conditioning, depth scanned) over purely aesthetic scene styling.
