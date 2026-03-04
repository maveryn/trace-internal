# TRACE Validation Error Codes

## Purpose
This document catalogs machine-readable `error_code` values used in
`validation_report.json` produced by pre-finalize validation.

Each validation error entry should include:
1. `error_code` (machine-readable)
2. `message` (human-readable)
3. concise context references (for example `instance_id`, `field_path`, `trace_ref`, `image_path`)

## Naming conventions
Use lowercase snake case with category prefix:
1. `schema_*`
2. `trace_ref_*`
3. `image_*`
4. `count_*`
5. `version_*`
6. `identity_*`
7. `io_*`
8. `config_*`

## Initial code set
### Schema
1. `schema_missing_field`
2. `schema_type_mismatch`
3. `schema_invalid_value`

### Schema/Canonical Serializer
1. `schema_non_string_key`
2. `schema_non_finite_number`
3. `schema_unsupported_type`
4. `schema_canonicalization_failed`

### Trace reference
1. `trace_ref_missing`
2. `trace_ref_not_found`
3. `trace_ref_hash_mismatch`
4. `trace_ref_index_out_of_range`

### Image integrity
1. `image_path_not_relative`
2. `image_file_not_found`
3. `image_hash_missing`
4. `image_hash_mismatch`

### Count/expectation
1. `count_per_task_shortfall`
2. `count_unexpected_task_present`

### Version consistency
1. `version_mixed_instance_version`
2. `version_unsupported_instance_version`

### Identity/determinism
1. `identity_instance_id_mismatch`
2. `identity_non_deterministic_order`

### I/O/finalization
1. `io_trace_write_failed`
2. `io_atomic_finalize_failed`
3. `io_validation_report_write_failed`
4. `io_failure_bundle_write_failed`

### Config/registry
1. `config_task_not_registered`
2. `config_registry_file_missing`
3. `config_registry_hash_mismatch`
4. `config_build_report_schema_mismatch`

## Evolution policy
Codes may be renamed when needed, but changes should be reflected in:
1. validator implementation,
2. this catalog,
3. release/change notes if consumers depend on code names.
