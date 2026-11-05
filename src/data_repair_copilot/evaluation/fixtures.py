"""Generate a deterministic synthetic corruption fixture and separate labels."""

import csv
import hashlib
import io
import json

_HEADERS = ["customer_id", "email", "signup_date", "zip", "status"]
# Each edit includes an expected clean value so fixture drift fails explicitly.
_EDITS = (
    (1, "status", "Active", " active ", "category_variant"),
    (2, "zip", "02110", "2110", "invalid_zip_format"),
    (3, "signup_date", "2024-04-30", "2024-02-30", "invalid_iso_date"),
    (4, "email", "customer005@example.com", "", "missing_value"),
)


def generate_fixture(clean_bytes: bytes) -> tuple[bytes, bytes]:
    """Return UTF-8 CSV and JSON bytes; never alter the clean source.

    Data row indices are zero-based and exclude the header. The labels describe
    injected changes, not all possible quality findings in arbitrary datasets.
    """
    try:
        text = clean_bytes.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if reader.fieldnames != _HEADERS:
            raise ValueError("Unexpected clean fixture headers")
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError("Invalid clean fixture CSV") from exc
    if len(rows) != 6 or any(None in row or None in row.values() for row in rows):
        raise ValueError("Clean fixture must contain exactly six complete rows")
    labels = []
    for index, column, expected, replacement, kind in _EDITS:
        if rows[index][column] != expected:
            raise ValueError(f"Clean fixture value changed at row {index}, column {column}")
        rows[index][column] = replacement
        labels.append(
            {
                "kind": kind,
                "row_index": index,
                "column": column,
                "original": expected,
                "corrupted": replacement,
            }
        )
    rows.append(rows[0].copy())
    labels.append({"kind": "exact_duplicate_row", "row_indices": [0, 6]})
    labels.append({"kind": "duplicate_id", "column": "customer_id", "row_indices": [0, 6]})
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=_HEADERS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    corrupted = output.getvalue().encode("utf-8")
    ground_truth = {
        "schema_version": 1,
        "description": (
            "Synthetic injected changes only; row indices exclude header and start at zero."
        ),
        "clean_sha256": hashlib.sha256(clean_bytes).hexdigest(),
        "corrupted_sha256": hashlib.sha256(corrupted).hexdigest(),
        "clean_rows": 6,
        "corrupted_rows": 7,
        "issues": labels,
    }
    labels_bytes = (
        json.dumps(ground_truth, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    return corrupted, labels_bytes
