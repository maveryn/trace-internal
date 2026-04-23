from verl.utils.trace_validation import (
    filter_trace_validation_sources,
    normalize_validation_sources,
    trace_validation_name_from_source,
)


def test_trace_validation_name_from_source_parquet_path():
    path = "/tmp/validation/mathvista_mini.parquet"
    assert trace_validation_name_from_source(path) == "mathvista_mini"


def test_normalize_validation_sources_string_to_list():
    assert normalize_validation_sources("a.parquet") == ["a.parquet"]


def test_filter_trace_validation_sources_excludes_requested_benchmarks():
    val_files = [
        "/tmp/mathverse_mini.parquet",
        "/tmp/mathvista_mini.parquet",
        "/tmp/countqa.parquet",
        "/tmp/blink.parquet",
    ]
    filtered = filter_trace_validation_sources(
        val_files,
        excluded_benchmarks=["mathverse_mini", "countqa"],
    )
    assert filtered == [
        "/tmp/mathvista_mini.parquet",
        "/tmp/blink.parquet",
    ]
