# `task_puzzles__tangram__contact_count`

## Program Contract
`count(marked_pieces union edge_touching_neighbors(marked_pieces)); scene=tangram; scope=contact_count`

## Contract
1. Domain: `puzzles`
2. Scene id: `tangram`
3. Public task id: `task_puzzles__tangram__contact_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`

## Annotation
`annotation` is an array of image-pixel bounding boxes `[x0,y0,x1,y1]` for every counted Tangram piece. The set contains the marked piece or pieces and every unmarked piece that shares an edge with any marked piece.

## Generation Notes
The visual layout variant, target count, selected marked set, style, font, and layout are generation/render metadata, not public query ids.
