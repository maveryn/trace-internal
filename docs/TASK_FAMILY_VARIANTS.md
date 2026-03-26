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
3. Multi-object geometry class-membership tasks belong under `counting`; scenes should label whole objects and count how many match one requested class.
4. `analytical_2d` should use one primary annotated scene where area/length/perimeter must be inferred from symbolic/numeric relationships (not direct readout); auxiliary constructions or coupled shapes are acceptable when they are part of the derivation.
5. `comparison` should enforce exactly one winner by construction and use one reusable winner-gap policy (`gap_norm >= 0.20` plus optional task-level absolute floors) so scenes stay readable without hand-tuned per-instance ambiguity checks.

## Planned geometry measurement variants
1. **Angle measurement**
   - One angle per image.
   - Ask for the angle value rounded to the nearest integer degree.
   - Evidence: unlabeled 3-point set in graph-unit integer coordinates.
2. **Polygon area measurement**
   - One shape per image: triangle/quadrilateral polygon or ellipse.
   - Ask for area (`integer` for polygons, `kπ` for ellipses).
   - Evidence: polygon/circle-specific graph-point evidence in graph-unit coordinates.
3. **Polygon perimeter measurement**
   - One shape per image: triangle/quadrilateral polygon or circle.
   - Ask for perimeter/circumference (`integer` for polygons, `kπ` for circles).
   - Evidence: polygon/circle-specific graph-point evidence in graph-unit coordinates.
4. **Slope measurement**
   - One finite line per image on graph paper.
   - Line crosses x-axis at an integer lattice coordinate and at least one other integer lattice point.
   - Ask for slope to one decimal place.
   - Evidence: one x-axis crossing lattice point.

## Implemented analytical variant
1. **Comparison angle (`task_geometry_comparison_angle`)**
   - One graph-paper image with 4–6 labeled angles.
   - Query type: `largest` or `smallest`.
   - Answer type: winner label (`option_letter`) with no textual option list in the prompt.
   - Evidence: `graph_point_set` for the winning angle's vertex + two ray endpoints.
2. **Comparison area (`task_geometry_comparison_area`)**
   - One graph-paper image with 4–6 labeled rectangles.
   - Query type: `largest` or `smallest`.
   - Answer type: winner label (`option_letter`) with no textual option list in the prompt.
   - Evidence: `graph_point_set` for the winning rectangle vertices.
3. **Comparison length (`task_geometry_comparison_length`)**
   - One graph-paper image with 4–6 labeled line segments.
   - Query type: `largest` or `smallest`.
   - Answer type: winner label (`option_letter`) with no textual option list in the prompt.
   - Evidence: `graph_point_set` for the winning segment endpoints.
4. **Comparison perimeter (`task_geometry_comparison_perimeter`)**
   - One graph-paper image with 4–6 labeled rectangles.
   - Query type: `largest` or `smallest`.
   - Answer type: winner label (`option_letter`) with no textual option list in the prompt.
   - Evidence: `graph_point_set` for the winning rectangle vertices.
5. **Counting angle (`task_geometry_counting_angle`)**
   - One non-graph-paper image with 6–10 labeled angles.
   - Query variants: `acute_angle`, `right_angle`, `obtuse_angle`.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching angle labels.
6. **Counting triangle (`task_geometry_counting_triangle`)**
   - One non-graph-paper image with 5–8 labeled triangles.
   - Query variants: `equilateral_triangle`, `isosceles_triangle`, `scalene_triangle`, `right_triangle`, `acute_triangle`, `obtuse_triangle`.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching triangle labels.
   - Overlap wording: the isosceles query is phrased as `isosceles triangles but not equilateral triangles` so the task does not rely on competing textbook conventions.
7. **Analytical area (`task_geometry_analytical_2d_area`)**
   - One annotated shape per image: rectangle, triangle, parallelogram, trapezoid, rhombus, circle, ellipse.
   - One explicit + one derived variant per shape.
   - Ask for area (`integer` for polygonal shapes, `kπ` for circle/ellipse).
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for all quantities used in the area computation.
8. **Analytical length (`task_geometry_analytical_2d_length`)**
   - One annotated analytical scene per image, including auxiliary constructions or coupled shapes.
   - Derived-only variants: triangle altitude side, rectangle diagonal side, rhombus diagonal side, isosceles trapezoid leg, inscribed square side, circle chord length.
   - Ask for a target segment length rounded to one decimal place.
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for the givens used in the derivation.
9. **Analytical perimeter (`task_geometry_analytical_2d_perimeter`)**
   - One annotated analytical scene per image, including auxiliary constructions or coupled shapes.
   - Derived-only variants: right triangle from leg+hypotenuse, rectangle from side+diagonal, rhombus from diagonals, isosceles trapezoid from bases+height, inscribed square from circle diameter.
   - Ask for the perimeter rounded to one decimal place.
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for the givens used in the derivation.
10. **Analytical composite area (`task_geometry_analytical_2d_composite_area`)**
   - One annotated analytical scene per image with one shaded target region; auxiliary cuts/unions and coupled polygons are allowed.
   - Derived-only variants: inner-rectangle cutout, triangle cutout, rectangle+triangle union, L-shape cutout, step-rectangle union.
   - Ask for the shaded/composite area as an integer number of square units.
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for the givens used in the derivation.
11. **Analytical 3D volume (`task_geometry_analytical_3d_volume`)**
   - One annotated 3D solid per image: rectangular prism, triangular prism, square pyramid, cylinder, cone, sphere.
   - Ask for volume (`integer` for polyhedra, `kπ` for cylinder/cone/sphere).
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for the required measurement labels.
12. **Analytical 3D surface area (`task_geometry_analytical_3d_surface_area`)**
   - One annotated 3D solid per image: rectangular prism, triangular prism, square pyramid, cylinder, cone, sphere.
   - Ask for total surface area (`integer` for polyhedra, `kπ` for cylinder/cone/sphere).
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for the required measurement labels.

## Future polygon variants (deferred)
1. Polygon diameter measurement.
2. Polygon minimum-side query.
3. Polygon maximum-side query.

## Evidence formatting notes
1. Evidence coordinate frame is task/domain declared (`graph_unit`, `pixel`, `cell`, etc.), not globally fixed.
2. If exact integer projection is impossible for a shape family, keep values as close as possible and document canonicalization in task docs.
3. Evidence schema must be declared in each task contract and remain stable for verifier compatibility.
4. For counting families with object labels, prefer `label_set` evidence over geometric coordinates so multi-object grounding stays compact and readable.
