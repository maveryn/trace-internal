# task_illustrations__library__section_book_count

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

## Overview

- domain: `illustrations`
- scene_id: `library`
- task_group: `counting`
- task: `library_book_count`
- module: `trace/tasks/illustrations/counting/library_book_count.py`
- default enabled: yes

The task renders an illustrated library with labeled shelf sections and asks
for a count of books in one section. Query ids are:

- `books_in_section_count`: count all books in a named section.
- `book_color_in_section_count`: count books with a named canonical color in a named section.
- `upright_book_in_section_count`: count upright books in a named section.
- `horizontal_book_in_section_count`: count horizontal books in a named section.

## Answer And Evidence

- `answer_gt.type = integer`
- `evidence_gt.type = bbox_set`
- Evidence is one `[x0, y0, x1, y1]` final-image pixel bbox for every counted book.
- Answer and evidence are projected from rendered book records, not pixels.
- `bbox_set` is intentional: all evidence witnesses are homogeneous counted
  books, so no keyed role binding is needed.

## Prompt

- `bundle_id = illustrations_counting_v0`
- `scene_key = library_canvas`
- `task_key = library_book_count_task`
- `query_id` is one of the branches listed above.

## Calibration Notes

The section-total variant samples target counts `3..8`; color and orientation
variants sample target counts `1..6`. The renderer keeps distractor books in
the target section so filtered queries require scanning color or orientation,
not only reading the section label.

Fresh artifact review on 2026-05-28 regenerated
`review/task-reviews/illustrations/library/scene_review.xlsx`. Section label text
uses one sampled global-approved font family per scene, recorded in render
metadata and kept consistent across all labeled shelf sections.
