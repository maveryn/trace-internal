# `task_pages__ranked_list__ordinal_entry_label`

## Taxonomy
1. Domain: `pages`
2. Scene id: `ranked_list`
3. Task id: `task_pages__ranked_list__ordinal_entry_label`
4. Implementation group: `pages/document_lookup`

## Contract
Reads one item from a sectioned numbered/ranked list page.

Query ids: `nth_entry_label|from_end_entry_label|entry_after_named_entry`.

Answers are exact visible item labels. Evidence is a `keyed_bbox_map` over the role-bound lookup witnesses:
- `section_title`: the title of the queried list section,
- `target_item`: the answer item text,
- `source_item`: the named source item text, only for `entry_after_named_entry`.

## Prompt + Trace
1. Prompt bundle: `pages_document_lookup_v0`
2. Scene key: `ranked_list`
3. Task key: `ranked_list_entry_query`
4. Trace records section ids, section titles, item order, target item index, optional source item index, final rendered item bboxes, and role-keyed projected evidence.
