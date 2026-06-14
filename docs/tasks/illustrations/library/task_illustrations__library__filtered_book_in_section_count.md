# `task_illustrations__library__filtered_book_in_section_count`

## Summary
- Domain: `illustrations`
- Scene id: `library`
- Implementation scene: `counting`
- Implementation source: `trace/tasks/illustrations/counting/library_book_count.py`

## Task Contract
Counts visible books in one labeled section filtered by color or orientation.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `book_color_in_section_count` | `count(filter(books, section(book)=target_section and book_attribute(book)=target_attribute_value)); scene=library; scope=filtered_book_in_section_count; query_branch=book_color_in_section_count` |
| `horizontal_book_in_section_count` | `count(filter(books, section(book)=target_section and book_attribute(book)=target_attribute_value)); scene=library; scope=filtered_book_in_section_count; query_branch=horizontal_book_in_section_count` |
| `upright_book_in_section_count` | `count(filter(books, section(book)=target_section and book_attribute(book)=target_attribute_value)); scene=library; scope=filtered_book_in_section_count; query_branch=upright_book_in_section_count` |

## Program Metadata
- Program signatures: `count.scoped_attribute`
- Base program contract: `count(filter(books, section(book)=target_section and book_attribute(book)=target_attribute_value)); scene=library; scope=filtered_book_in_section_count`
- Parameter axes: `fixed_query`, `target_attribute`
- Arguments:
  - `book`: semantic_role; allowed `book_instance`; source `program_schema_concrete`
  - `books`: semantic_role; allowed `visible_books`; source `program_schema_concrete`
  - `target_attribute`: object_attribute; allowed `color`; source `query_id|parameter_axes`
  - `target_attribute_value`: object_attribute; allowed `horizontal`, `sampled_color`, `upright`; source `program_schema_concrete`
  - `target_section`: semantic_role; allowed `sampled_library_section`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `book_color_in_section_count`, `horizontal_book_in_section_count`, `upright_book_in_section_count`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a non-negative integer derived from the same execution trace as the annotation.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted/selected visual witness. Do not include labels, numeric annotations, or context-only regions.
- Annotation and answer must be projected from the same generated scene trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, and verifier payloads must be explicit in the instance trace.
- Distractor/context text may be rendered only when it is part of the scene grammar and must not be treated as annotation unless it is the queried visual witness.
