# Task Families & Variants

## Purpose
Define how we split tasks into reusable families so each dataset slice stays comparable and avoids hidden weighting bias.

## Core rule
1. **Family = reasoning mode** (for example `measurement`, `comparison`).
2. **Variant = visual/semantic subtype inside a family** (for example polygon `n`-gon subtype, query subtype).
3. Keep family boundaries stable; add variants before adding new families unless reasoning mode changes.

## Geometry direction (current)
1. `measurement` should use **one primary object per image**.
2. Multi-object value-query geometry tasks belong under `comparison` (separate from single-object `measurement`).
3. `analytical_2d` should use one primary object with symbolic/numeric annotations where area/length/perimeter must be inferred from relationships (not direct readout).

## Planned geometry measurement variants
1. **Angle measurement**
   - One angle per image.
   - Ask for the angle value rounded to the nearest integer degree.
   - Evidence: labeled 3-point map in graph-unit integer coordinates.
2. **Polygon area measurement**
   - One shape per image: triangle/quadrilateral polygon or ellipse.
   - Ask for area (`integer` for polygons, `kπ` for ellipses).
   - Evidence: labeled polygon-vertex map for polygons; labeled reference-point map for ellipses.
3. **Polygon perimeter measurement**
   - One shape per image: triangle/quadrilateral polygon or circle.
   - Ask for perimeter/circumference (`integer` for polygons, `kπ` for circles).
   - Evidence: labeled polygon-vertex map for polygons; labeled center/radius-point map for circles.
4. **Slope measurement**
   - One finite line per image on graph paper.
   - Line crosses x-axis at an integer lattice coordinate and at least one other integer lattice point.
   - Ask for slope to one decimal place.
   - Evidence: labeled x-axis crossing lattice point.

## Implemented analytical variant
1. **Analytical area (`task_geometry_analytical_2d_area`)**
   - One annotated shape per image: rectangle, triangle, parallelogram, trapezoid, rhombus, circle, ellipse.
   - One explicit + one derived variant per shape.
   - Ask for area (`integer` for polygonal shapes, `kπ` for circle/ellipse).
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for all quantities used in the area computation.
2. **Analytical 3D volume (`task_geometry_analytical_3d_volume`)**
   - One annotated 3D solid per image: rectangular prism, triangular prism, square pyramid, cylinder, cone, sphere.
   - Ask for volume (`integer` for polyhedra, `kπ` for cylinder/cone/sphere).
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for the required measurement labels.

## Future polygon variants (deferred)
1. Polygon diameter measurement.
2. Polygon minimum-side query.
3. Polygon maximum-side query.

## Evidence formatting notes
1. Evidence coordinate frame is task/domain declared (`graph_unit`, `pixel`, `cell`, etc.), not globally fixed.
2. If exact integer projection is impossible for a shape family, keep values as close as possible and document canonicalization in task docs.
3. Evidence schema must be declared in each task contract and remain stable for verifier compatibility.
