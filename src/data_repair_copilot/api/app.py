"""Small in-memory CSV analysis prototype for local synthetic data only."""

from threading import Lock
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request

from data_repair_copilot.csv_loader import CsvLoadError, load_csv_bytes
from data_repair_copilot.detectors.duplicates import detect_duplicates
from data_repair_copilot.detectors.missing import detect_missing

_MAX_BYTES = 1_000_000
_MAX_UPLOADS = 16


def create_app() -> FastAPI:
    """Create isolated, bounded in-memory state; never expose this to customers."""
    app = FastAPI(title="Local CSV analysis prototype")
    uploads: dict[UUID, bytes] = {}
    lock = Lock()

    @app.post("/uploads", status_code=201)
    async def upload_csv(request: Request) -> dict:
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "text/csv":
            raise HTTPException(status_code=415, detail="Send raw CSV with Content-Type: text/csv")
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > _MAX_BYTES:
                raise HTTPException(status_code=413, detail="CSV exceeds upload limit")
            content.extend(chunk)
        try:
            frame = load_csv_bytes(bytes(content))
        except CsvLoadError:
            raise HTTPException(status_code=400, detail="Invalid CSV") from None
        with lock:
            if len(uploads) >= _MAX_UPLOADS:
                raise HTTPException(status_code=503, detail="Local upload capacity reached")
            upload_id = uuid4()
            uploads[upload_id] = bytes(content)
        return {"upload_id": str(upload_id), "row_count": frame.height, "column_count": frame.width}

    @app.post("/analyses/{upload_id}")
    def analyze_csv(upload_id: UUID) -> dict:
        with lock:
            content = uploads.get(upload_id)
        if content is None:
            raise HTTPException(status_code=404, detail="Upload not found")
        frame = load_csv_bytes(content)
        missing = detect_missing(frame)
        duplicates = detect_duplicates(frame)
        issues = [
            {
                "kind": "missing_value",
                "column": column.column,
                "row_indices": column.missing_row_indices,
            }
            for column in missing.columns
            if column.missing_row_indices
        ]
        issues.extend(
            {"kind": "exact_duplicate_row", "column": None, "row_indices": group.row_indices}
            for group in duplicates.duplicate_rows
        )
        return {"upload_id": str(upload_id), "row_count": frame.height, "issues": issues}

    return app
