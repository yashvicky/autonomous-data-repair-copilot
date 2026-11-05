"""Read UTF-8 CSV fields without type or null inference."""

import csv
from pathlib import Path

import polars as pl


class CsvLoadError(ValueError):
    """A CSV file cannot be safely interpreted by the loader."""


def load_csv(path: str | Path) -> pl.DataFrame:
    """Load comma-separated UTF-8 data with a required, unique header.

    All parsed fields remain strings, including empty fields and null-like text.
    A UTF-8 BOM is removed from the header. Original file bytes are untouched.
    """
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8-sig", newline="") as file:
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
    except FileNotFoundError as exc:
        raise CsvLoadError(f"CSV file not found: {source}") from exc
    except UnicodeDecodeError as exc:
        raise CsvLoadError("CSV must be valid UTF-8") from exc
    except csv.Error as exc:
        raise CsvLoadError(f"Malformed CSV: {exc}") from exc
    except OSError as exc:
        raise CsvLoadError(f"Could not read CSV file: {exc}") from exc
    return pl.DataFrame(columns, schema={name: pl.String for name in header})
