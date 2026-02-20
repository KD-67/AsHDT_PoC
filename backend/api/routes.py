import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from core.state_store.archive_reader import read_timeseries
from core.analysis.trajectory import compute_trajectory
from core.state_store.database import get_connection
from core.output.report_serializer import save_timegraph_report


router = APIRouter()


# Pydantic request models

class TimeframeModel(BaseModel):
    start_time: str
    end_time: str

    model_config = {"populate_by_name": True}


class ZoneBoundariesModel(BaseModel):
    healthy_min: float
    healthy_max: float
    vulnerability_margin: float


class FittingModel(BaseModel):
    polynomial_degree: int


class TimegraphRequest(BaseModel):
    subject_id: str
    module_id: str
    marker_id: str
    timeframe: TimeframeModel
    zone_boundaries: ZoneBoundariesModel
    fitting: FittingModel


# Routes
@router.get("/registry")
def get_registry(request: Request):
    return request.app.state.registry


@router.get("/subjects")
def get_subjects(request: Request):
    archive_root = request.app.state.archive_root
    if not os.path.isdir(archive_root):
        return []
    return [
        name for name in os.listdir(archive_root)
        if os.path.isdir(os.path.join(archive_root, name))
    ]


@router.post("/timegraph")
def post_timegraph(body: TimegraphRequest, request: Request):
    db_path      = request.app.state.db_path
    archive_root = request.app.state.archive_root
    reports_root = request.app.state.reports_root

    # 1. Parse timeframe strings to timezone-aware datetimes
    try:
        from_time = datetime.fromisoformat(body.timeframe.start_time.replace("Z", "+00:00"))
        to_time   = datetime.fromisoformat(body.timeframe.end_time.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid timeframe timestamp: {e}")

    # 2. Read data points from the archive
    try:
        data_points = read_timeseries(
            archive_root,
            body.subject_id,
            body.module_id,
            body.marker_id,
            from_time,
            to_time,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not data_points:
        raise HTTPException(
            status_code=404,
            detail="No data points found in the requested timeframe.",
        )

    # 3. Run trajectory computation
    zone_boundaries_dict = {
        "healthy_min":          body.zone_boundaries.healthy_min,
        "healthy_max":          body.zone_boundaries.healthy_max,
        "vulnerability_margin": body.zone_boundaries.vulnerability_margin,
    }
    try:
        trajectory_result = compute_trajectory(
            data_points,
            zone_boundaries_dict,
            body.fitting.polynomial_degree,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 4. Build report metadata and pass to save_timegraph_report()
    report_id    = str(uuid4())
    requested_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    timeframe_dict = {"from": body.timeframe.start_time, "to": body.timeframe.end_time}
    fitting_dict   = {"polynomial_degree": body.fitting.polynomial_degree}

    save_timegraph_report(
        db_path=db_path,
        reports_root=reports_root,
        report_id=report_id,
        subject_id=body.subject_id,
        module_id=body.module_id,
        marker_id=body.marker_id,
        requested_at=requested_at,
        timeframe=timeframe_dict,
        zone_boundaries=zone_boundaries_dict,
        fitting=fitting_dict,
        trajectory_result=trajectory_result,
    )

    # 5. Ensure subject row exists, return data needed for frontend to render chart
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO subjects (subject_id, created_at) VALUES (?, ?)",
            (body.subject_id, requested_at),
        )

    return {
        "report_id":    report_id,
        "data_points":  trajectory_result["data_points"],
        "fit_metadata": trajectory_result["fit_metadata"],
    }
