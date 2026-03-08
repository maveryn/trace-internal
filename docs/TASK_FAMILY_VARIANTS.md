# Task Families & Variants

## Purpose
Define how we split tasks into reusable families so each dataset slice stays comparable and avoids hidden weighting bias.

## Core rule
1. **Family = reasoning mode** (for example `measurement_2d`, `comparison`).
2. **Variant = visual/semantic subtype inside a family** (for example polygon `n`-gon subtype, query subtype).
3. Keep family boundaries stable; add variants before adding new families unless reasoning mode changes.

## Geometry direction (current)
1. `measurement_2d` should use **one primary object per image**.
2. Multi-object value-query geometry tasks belong under `comparison` (separate from single-object `measurement_2d`).

## Planned geometry measurement variants
1. **Angle measurement**
   - One angle per image.
   - Ask for the angle value.
   - Evidence: 3 vertex points in graph-unit integer coordinates.
2. **Polygon area measurement**
   - One shape per image: triangle/quadrilateral/pentagon polygon or ellipse.
   - Ask for area (`integer` for polygons, `kπ` for ellipses).
   - Evidence: polygon vertex coordinate set for polygons; center point for ellipses.
3. **Polygon perimeter measurement**
   - One shape per image: triangle/quadrilateral/pentagon polygon or circle.
   - Ask for perimeter/circumference (`integer` for polygons, `kπ` for circles).
   - Evidence: polygon vertex coordinate set for polygons; center point for circles.

## Future polygon variants (deferred)
1. Polygon diameter measurement.
2. Polygon minimum-side query.
3. Polygon maximum-side query.

## Evidence formatting notes
1. Evidence coordinate frame is task/domain declared (`graph_unit`, `pixel`, `cell`, etc.), not globally fixed.
2. If exact integer projection is impossible for a shape family, keep values as close as possible and document canonicalization in task docs.
3. Evidence schema must be declared in each task contract and remain stable for verifier compatibility.
