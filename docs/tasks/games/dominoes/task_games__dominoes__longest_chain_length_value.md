# `task_games__dominoes__longest_chain_length_value`

## Contract
1. Domain: `games`
2. Scene: `dominoes`
3. Scene id: `dominoes`
4. Public task id: `task_games__dominoes__longest_chain_length_value`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`
8. Program schema: `max_chain_length(start=open_right_end(reference_tile), tiles=loose_dominoes); scene=dominoes; scope=longest_chain_length_value`

## Program Contract
- `max_chain_length(start=open_right_end(reference_tile), tiles=loose_dominoes); scene=dominoes; scope=longest_chain_length_value`

## Generation Notes
1. Renders the chain/tableau layout with the final chain tile marked `REF`.
2. The answer is the number of loose dominoes in the unique longest one-sided extension from `REF`, not counting `REF`.
3. Answer support is fixed to `1..5`.
4. Annotation is projected from the same generated game state used for answer verification.
