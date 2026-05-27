# `task_graph__metro__station_membership_count`

## 1) Identity
1. Domain: `graph`
2. Task group: `counting`
3. Scene id: `metro`
4. Task id: `task_graph__metro__station_membership_count`
5. Objective: count stations satisfying a route-membership predicate.

## 2) Scene + Task Contract
1. Public `query_variant`: `default`
2. `query_id`: `metro_transfer_station_count` or `metro_single_route_station_count`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `point_set`
5. A transfer station is served by two or more colored routes.
6. A single-route station is served by exactly one colored route.
7. Evidence is an unordered set of station-center pixel points, one point per matching station.

## 3) Prompt Contract
1. Bundle: `graph_counting_v0`
2. `scene_key`: `metro_route_counting`
3. Task/query wording is branch-specific.
4. Answer-only JSON: `{"answer":2}`
5. Answer+evidence JSON: `{"evidence":[[180,220],[310,180]],"answer":2}`

## 4) Verification
1. The verifier payload records route station lists, station route memberships, and the witness station set.
2. `answer_gt.value == len(evidence_gt.value)`.
3. Route membership is computed from finalized station-to-route metadata, not from route-color pixels.
4. Earlier narrower public ids were absorbed into this task's `query_id` branches and should not be reintroduced.
