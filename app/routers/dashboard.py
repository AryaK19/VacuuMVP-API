from fastapi import APIRouter, Depends, Query, HTTPException, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Any


from app.db.session import get_db

from app.middleware.auth import require_any_role, require_admin

from app.external_service.pdf_service import PDFService
from app.schema.dashboard import PaginatedRecentActivitiesResponse, DashboardStatsResponse, ServiceTypeStatsResponse, PumpNumberStatsResponse, CustomerMachineStatsResponse


from app.helper.dashboard import get_recent_activities, get_dashboard_statistics, get_service_type_statistics, get_part_number_statistics, get_customer_machine_statistics



router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard/statistics", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_any_role)
):
    """
    Get dashboard statistics including:
    - Total distributors
    - Sold vs available machines
    - Monthly service reports count
    Accessible by any authenticated user.
    """
    try:
        return await get_dashboard_statistics(db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






@router.get("/dashboard/service-type-statistics", response_model=ServiceTypeStatsResponse)
async def get_service_type_stats(
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_any_role)
):
    """
    Get service type statistics for bar chart.
    Returns count of service reports for each service type.
    Accessible by any authenticated user.
    """
    try:
        return await get_service_type_statistics(db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    For admin users: shows all reports
    For distributors: shows only their own reports
    Accessible by any authenticated user.
    """
    return await get_recent_activities(
        db=db,
        user_id=str(current_user.id),  # Pass the current user ID
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit
    )



@router.get("/dashboard/part-number-statistics", response_model=PumpNumberStatsResponse)
async def get_part_number_stats(
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_any_role)
):
    """
    Get part number statistics for dashboard.
    Returns count of service reports for each part number along with model number.
    Results are ordered by service count (highest first).
    Accessible by any authenticated user.
    """
    try:
        return await get_part_number_statistics(db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/customer-machines", response_model=CustomerMachineStatsResponse)
async def get_customer_machine_stats(
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_admin)
):
    """
    Get customer machine statistics for dashboard.
    Returns count of machines for each customer.
    Accessible by any authenticated user.
    """
    try:
        return await get_customer_machine_statistics(db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

