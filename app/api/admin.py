"""Admin endpoints — usage reports and CSV export."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_admin
from app.models.db import GenerationRequest, UsageCost

router = APIRouter(tags=["admin"])


@router.get("/admin/reports/usage")
def usage_report(
    request: Request,
    from_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    status: str | None = Query(None, description="Filter by status"),
    format: str = Query("json", description="Output format: json or csv"),
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Return usage/cost report with optional filters. Supports JSON and CSV."""

    # Build query joining GenerationRequest and UsageCost
    query = (
        db.query(GenerationRequest, UsageCost)
        .outerjoin(
            UsageCost,
            UsageCost.generation_request_id == GenerationRequest.id,
        )
    )

    # Apply filters
    if from_date:
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            query = query.filter(GenerationRequest.created_at >= from_dt)
        except ValueError:
            pass

    if to_date:
        try:
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
            # Include the entire to_date day
            to_dt = to_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(GenerationRequest.created_at <= to_dt)
        except ValueError:
            pass

    if status:
        query = query.filter(GenerationRequest.status == status)

    # Order by most recent first
    query = query.order_by(GenerationRequest.created_at.desc())

    results = query.all()

    # Build rows
    rows = []
    for gen, usage in results:
        row = {
            "id": gen.id,
            "session_id": gen.session_id,
            "status": gen.status,
            "output_count": gen.output_count,
            "prompt_template_version": gen.prompt_template_version,
            "model_name": usage.model_name if usage else None,
            "input_tokens": usage.input_tokens if usage else None,
            "output_tokens": usage.output_tokens if usage else None,
            "estimated_cost_usd": (
                float(usage.estimated_cost_usd)
                if usage and usage.estimated_cost_usd is not None
                else None
            ),
            "duration_ms": usage.duration_ms if usage else None,
            "error_message": gen.error_message,
            "created_at": gen.created_at.isoformat() if gen.created_at else None,
            "updated_at": gen.updated_at.isoformat() if gen.updated_at else None,
        }
        rows.append(row)

    # Return as CSV if requested
    if format == "csv":
        if not rows:
            csv_content = "No data"
        else:
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            csv_content = output.getvalue()

        return StreamingResponse(
            io.BytesIO(csv_content.encode("utf-8")),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=usage_report.csv"
            },
        )

    # Default: JSON
    return JSONResponse(content=rows)
