# `task_pages__hierarchy__path_length_count`

## Identity
1. Domain: `pages`
2. Scene id: `hierarchy`
3. Scene: `hierarchy`

## Contract
Counts parent-child hops on the path between two queried nodes in one rooted hierarchy diagram.

Query id: `path_length_between_two_nodes`.

Answers are integers. Annotation is a `bbox_sequence` over the node boxes on the path from the first queried node to the second queried node. The answer is one less than the annotation-node count.
