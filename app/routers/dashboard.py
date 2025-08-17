from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.orm import Session
from typing import Optional, Any

from app.db.session import get_db
from app.schema.dashboard import PaginatedRecentActivitiesResponse, ServiceReportDetailResponse
from app.middleware.auth import require_any_role
from app.helper.dashboard import get_recent_activities, get_service_report_detail

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard/recent-activities", response_model=PaginatedRecentActivitiesResponse)
async def get_recent_service_activities(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by user name or service type"),
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Any = Depends(require_any_role)
):
    """
    Get recent activities from service reports with filtering, sorting, and pagination.
    Shows user name, service type, and creation time for each report.
    Accessible by any authenticated user.
    """
    return await get_recent_activities(
        db=db,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit
    )

@router.get("/dashboard/service-report/{report_id}", response_model=ServiceReportDetailResponse)
async def get_service_report_details(
    report_id: str = Path(..., description="Service report ID"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_any_role)
):
    """
    Get detailed information about a specific service report.
    Shows complete service report details including user, machine, and service information.
    Accessible by any authenticated user.
    """
    try:
        return await get_service_report_detail(db=db, report_id=report_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))