"""Small in-memory CSV analysis prototype for local synthetic data only."""

import csv
import io
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from data_repair_copilot.audit.report import DecisionMetadata, build_audit_report
from data_repair_copilot.csv_loader import CsvLoadError, load_csv_bytes
from data_repair_copilot.detectors.duplicates import detect_duplicates
from data_repair_copilot.detectors.missing import detect_missing
from data_repair_copilot.profiler import profile_dataframe
from data_repair_copilot.repairs.approval import Decision, apply_decisions, create_review
from data_repair_copilot.repairs.preview import CellProposal

_MAX_BYTES = 1_000_000
_MAX_UPLOADS = 16
_MAX_REVIEWS = 32


class PreviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposals: list[CellProposal] = Field(min_length=1, max_length=100)


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decisions: list[Decision] = Field(min_length=1, max_length=100)
    metadata: dict[int, DecisionMetadata]


def create_app() -> FastAPI:
    """Create isolated, bounded in-memory state; never expose this to customers."""
    app = FastAPI(title="Local CSV analysis prototype")
    uploads: dict[UUID, bytes] = {}
    lock = Lock()
    reviews: dict[UUID, dict] = {}

    @app.get("/", response_class=Response)
    def overview_screen() -> Response:
        html = (Path(__file__).parent / "static" / "overview.html").read_text(encoding="utf-8")
        return Response(content=html, media_type="text/html")

    @app.get("/uploads/{upload_id}/profile")
    def get_profile(upload_id: UUID) -> dict:
        with lock:
            content = uploads.get(upload_id)
        if content is None:
            raise HTTPException(status_code=404, detail="Upload not found")
        frame = load_csv_bytes(content)
        return profile_dataframe(frame, sample_limit=0).model_dump(mode="json")

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

    @app.post("/uploads/{upload_id}/previews", status_code=201)
    def create_preview(upload_id: UUID, request: PreviewInput) -> dict:
        with lock:
            source = uploads.get(upload_id)
            if source is None:
                raise HTTPException(status_code=404, detail="Upload not found")
            if len(reviews) >= _MAX_REVIEWS:
                raise HTTPException(status_code=503, detail="Local review capacity reached")
            try:
                packet = create_review(load_csv_bytes(source), request.proposals)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid proposals") from None
            review_id = uuid4()
            reviews[review_id] = {"upload_id": upload_id, "packet": packet, "result": None}
        return {
            "review_id": str(review_id),
            "upload_id": str(upload_id),
            "preview": packet.model_dump(mode="json"),
        }

    @app.post("/reviews/{review_id}/decisions")
    def decide_review(review_id: UUID, request: ReviewInput) -> dict:
        with lock:
            entry = reviews.get(review_id)
            if entry is None:
                raise HTTPException(status_code=404, detail="Review not found")
            if entry["result"] is not None:
                raise HTTPException(status_code=409, detail="Review already decided")
            frame = load_csv_bytes(uploads[entry["upload_id"]])
            try:
                outcome = apply_decisions(frame, entry["packet"], request.decisions)
                report = build_audit_report(entry["packet"], outcome.records, request.metadata)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid decisions or metadata"
                ) from None
            entry["result"] = (outcome, report)
        return {"review_id": str(review_id), "status": "decided_locally"}

    @app.get("/reviews/{review_id}/audit")
    def get_audit(review_id: UUID) -> dict:
        with lock:
            entry = reviews.get(review_id)
            if entry is None:
                raise HTTPException(status_code=404, detail="Review not found")
            if entry["result"] is None:
                raise HTTPException(status_code=409, detail="Review is not decided")
            return entry["result"][1].model_dump(mode="json")

    @app.get("/reviews/{review_id}/export")
    def get_export(review_id: UUID) -> Response:
        with lock:
            entry = reviews.get(review_id)
            if entry is None:
                raise HTTPException(status_code=404, detail="Review not found")
            if entry["result"] is None:
                raise HTTPException(status_code=409, detail="Review is not decided")
            frame = entry["result"][0].dataset
            if any(series.null_count() for series in frame):
                raise HTTPException(status_code=409, detail="Cannot export nulls losslessly as CSV")
            output = io.StringIO(newline="")
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(frame.columns)
            writer.writerows(frame.iter_rows())
        return Response(content=output.getvalue(), media_type="text/csv")

    return app
