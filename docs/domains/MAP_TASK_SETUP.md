# Maps Task Setup

This document captures the concrete reusable setup for the first `maps` task family.

## 1) Domain scope
1. `domain=maps` is for image-native map reasoning, not generic pathfinding or graph problems with a map skin.
2. The first family focuses on `region` reasoning over stylized thematic maps with visible legends.
3. Transit-map tasks may come later, but they should stay transit-native (line colors, transfer stations, ordered stops) rather than re-skinning existing tile/graph reachability tasks.

## 2) First reusable scene contract
1. V1 region scenes use one stylized choropleth-like map on the left and one legend on the right.
2. The region geometry is synthetic and reusable:
   - start from a hidden `6..7 x 4..5` cell grid,
   - partition it into `5..7` contiguous regions,
   - render only the merged region boundaries so the scene reads like a thematic map instead of a visible square grid.
3. Every region gets exactly one uppercase visible label.
4. The legend uses one ordered category list and one color swatch per category.
5. Region tasks should treat the legend order as the semantic category order; do not make correctness depend on inferring a numeric value from unspoken color intensity alone.

## 3) Active family
1. `task_group=region`
2. Active task:
   - `task_maps_region_association_label`
3. Active semantic variants:
   - `max_category_region`
   - `min_category_region`
   - `matches_legend_bin`
4. Active visual variants:
   - `map_strip`
   - `map_card`
   - `map_outline`

## 4) Evidence policy
1. Label-answer region tasks should keep prompt-facing evidence local:
   - `bbox_set` with exactly one bbox for the answer region.
2. Future count-style region tasks may use one bbox per counted region in reading order.
3. Do not ask for legend swatch evidence unless the task is specifically about the legend item itself.

## 5) Color policy
1. Region tasks depend on color identity through the legend, so category palettes must be sampled or validated in Lab space.
2. The active floor is `ΔE*ab >= 60` between legend colors.
3. Record the active color-distance threshold and color-distance space in trace metadata.

## 6) Reuse guidance
1. Keep region partitioning, legend generation, and region-scene rendering under `trace/tasks/maps/shared/`.
2. Future region tasks should reuse:
   - the same region partition generator,
   - the same legend panel renderer,
   - the same region bbox projection contract.
3. If a later map family needs a different visual grammar (for example transit maps), split it into a different task group rather than overloading the region renderer with transit-specific branching.
