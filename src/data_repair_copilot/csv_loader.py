"""Read UTF-8 CSV fields without type or null inference."""

import csv
import io
from pathlib import Path
from typing import TextIO

import polars as pl


class CsvLoadError(ValueError):
    """A CSV file cannot be safely interpreted by the loader."""


def _parse_csv(file: TextIO) -> pl.DataFrame:
    reader = csv.reader(file, strict=True)
    header = next(reader, None)
    if not header or any(not name for name in header):
        raise CsvLoadError("CSV requires non-empty column names")
    if len(set(header)) != len(header):
        raise CsvLoadError("CSV column names must be unique")
    columns: dict[str, list[str]] = {name: [] for name in header}
    for row in reader:
        if len(row) != len(header):
            raise CsvLoadError(
                f"CSV record ending at line {reader.line_num} has {len(row)} fields; "
                f"expected {len(header)}"
            )
        for name, value in zip(header, row, strict=True):
            columns[name].append(value)
    return pl.DataFrame(columns, schema={name: pl.String for name in header})


def load_csv(path: str | Path) -> pl.DataFrame:
    """Load comma-separated UTF-8 data with a required, unique header.

    All parsed fields remain strings, including empty fields and null-like text.
    A UTF-8 BOM is removed from the header. Original file bytes are untouched.
    """
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8-sig", newline="") as file:
            return _parse_csv(file)
    except FileNotFoundError as exc:
        raise CsvLoadError(f"CSV file not found: {source}") from exc
    except UnicodeDecodeError as exc:
        raise CsvLoadError("CSV must be valid UTF-8") from exc
    except csv.Error as exc:
        raise CsvLoadError(f"Malformed CSV: {exc}") from exc
    except OSError as exc:
        raise CsvLoadError(f"Could not read CSV file: {exc}") from exc


def load_csv_bytes(content: bytes) -> pl.DataFrame:
    """Parse CSV bytes in memory with the same rules as the file loader."""
    try:
        with io.TextIOWrapper(io.BytesIO(content), encoding="utf-8-sig", newline="") as file:
            return _parse_csv(file)
    except UnicodeDecodeError as exc:
        raise CsvLoadError("CSV must be valid UTF-8") from exc
    except csv.Error as exc:
        raise CsvLoadError(f"Malformed CSV: {exc}") from exc
