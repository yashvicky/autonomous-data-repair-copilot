from pathlib import Path

import polars as pl
import pytest

from data_repair_copilot.csv_loader import CsvLoadError, load_csv


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_preserves_raw_field_values(tmp_path: Path, newline: str) -> None:
    source = tmp_path / "input.csv"
    content = (
        '\ufeffid,zip,value,note\n00123,00501,2024-01-01,"hello, world"\n'
        '00002,00000,NULL,""\n'
        '00003,00001,NA,"line one\nline two"\n'
    )
    source.write_bytes(content.replace("\n", newline).encode("utf-8"))
    result = load_csv(source)
    assert result.schema == {name: pl.String for name in ["id", "zip", "value", "note"]}
    assert result.rows() == [
        ("00123", "00501", "2024-01-01", "hello, world"),
        ("00002", "00000", "NULL", ""),
        ("00003", "00001", "NA", f"line one{newline}line two"),
    ]


def test_source_is_not_modified(tmp_path: Path) -> None:
    source = tmp_path / "input.csv"
    original = b'id,value\r\n001,"hello"\r\n'
    source.write_bytes(original)
    load_csv(source)
    assert source.read_bytes() == original


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (None, "not found"),
        (b"id\n\xff\n", "UTF-8"),
        (b'id,value\n001,"unclosed\n', "Malformed CSV"),
        (b"id,value\n001\n", "expected 2"),
        (b"id,id\n001,002\n", "unique"),
    ],
)
def test_invalid_input(tmp_path: Path, content: bytes | None, message: str) -> None:
    source = tmp_path / "input.csv"
    if content is not None:
        source.write_bytes(content)
    with pytest.raises(CsvLoadError, match=message):
        load_csv(source)
