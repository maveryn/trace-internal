# `task_puzzles__turing_tape__turing_written_symbol_count`

## Summary
1. Domain: `puzzles`
2. Task group: `automaton`
3. Task id: `task_puzzles__turing_tape__turing_written_symbol_count`
4. Scene id: `turing_tape`
5. Goal: simulate a compact tape-machine transition table for a fixed number of steps and count a queried tape symbol afterward.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `written_symbol_count`
3. Answer type: `integer`
4. Evidence type: `bbox_set`
5. Evidence target: starting tape/head panel and transition-table bbox
6. Scene variants: `clean_grid|lab_panel|notebook_grid`
7. Generation controls: tape length `8..11`, step count `3..6`, symbol alphabet size `2`, answer range `1..7`
