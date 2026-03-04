# `<task_id>` Task Documentation Template

## Overview
1. Domain:
2. Task group:
3. Task id:
4. High-level objective:

## Scene and Query
1. Scene entities and relations:
2. Supported query types:
3. Answer type:
4. Default evidence type:
5. Alternate evidence forms (if any):

## Prompt Bundle
1. `prompt_bundle_id`:
2. `task_type_key`:
3. Query type to template-key mapping:
4. Required slot schema (placeholder names and meanings):
5. Variant counts:
- task-type variants (must be >= 10),
- each query-type variants (must be >= 10).

## Prompt Examples
1. Example prompt for query type A:
2. Example prompt for query type B:

## Determinism and Metadata
1. Prompt seed namespaces used:
2. Prompt-variant metadata emitted in trace (`bundle/key/index/count` fields):

## Generation Constraints
1. Unique-answer-by-construction rules:
2. Reject/resample conditions:
3. No auto-relaxation guarantees:

## Complexity
1. Complexity score definition:
2. Complexity components:

## Tests
1. Determinism test:
2. Answer/evidence consistency test:
3. Prompt rendering/placeholder test:
4. Prompt variant-count validation test:
