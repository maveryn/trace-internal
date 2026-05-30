# task_illustrations__environment__feature_relation_count

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

## Overview

- domain: `illustrations`
- scene_id: `environment`
- task_group: `counting`
- task: `feature_relation_object_count`
- module: `trace/tasks/illustrations/counting/feature_relation_object_count.py`
- default enabled: yes

The task renders an outdoor environment with roads and/or rivers, then asks for
a count relative to the environmental feature. Query ids are:

- `feature_side_object_count`: count foreground objects above or below a road/river.
- `on_feature_object_count`: count foreground objects on the road or in/on the river.
- `crossing_feature_count`: count bridges over rivers or crosswalks across roads.

## Answer And Evidence

- `answer_gt.type = integer`
- `evidence_gt.type = bbox_set`
- For object-count variants, evidence is one final-image pixel bbox per counted foreground object.
- For crossing counts, evidence is one final-image pixel bbox per counted bridge or crosswalk feature.
- Answer and evidence come from rendered placement/feature metadata.

## Prompt

- `bundle_id = illustrations_counting_v0`
- `scene_key = environment_object_canvas`
- `task_key = feature_relation_object_count_task`
- `query_id` is one of the branches listed above.
- Scene prompt variants name the outdoor setting without injecting irrelevant
  numeric context; the query layer names the counted relation.

## Calibration Notes

The feature-side branch keeps answer counts in `1..12`, the on-feature branch
targets `2..7`, and the crossing branch targets `1..5`. Road/river themes and
above/below relation choices are sampled as task metadata and recorded in the
trace payload.

The renderer samples large-feature visual styles for roads, rivers, and bridges
and records those style ids in the layout and feature attributes. These styles
change the visual surface treatment only; answer/evidence projection remains
based on rendered bboxes and relation metadata.
