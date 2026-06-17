# `task_games__nine_mens_morris__pieces_in_mill_count`

## Contract
1. Domain: `games`
2. Scene id: `nine_mens_morris`
3. Public task id: `task_games__nine_mens_morris__pieces_in_mill_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`

## Program Contract
`count(filter(pieces, participates_in_mill(piece)=true)); scene=nine_mens_morris; scope=pieces_in_mill_count`

The rendered board shows light and dark pieces on Nine Men's Morris
intersections. A mill is three same-color pieces on one straight board line.
The program counts each visible piece that belongs to at least one mill,
deduplicating pieces that are in multiple mills, and annotates the bbox of
every counted piece.

## Generation Notes
1. Query ids are internal replay/sampling keys and do not define public task units.
2. The public query id is `single`; the prompt query key remains `all_pieces_in_mill_count`.
3. Annotation is projected from the same generated game state used for answer verification.
