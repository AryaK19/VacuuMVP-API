from fastapi import APIRouter, Depends, Query, HTTPException, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Any
from io import BytesIO

from app.db.session import get_db

from app.middleware.auth import require_any_role

from app.external_service.pdf_service import PDFService
from app.schema.dashboard import PaginatedRecentActivitiesResponse, ServiceReportDetailResponse, DashboardStatsResponse, ServiceTypeStatsResponse, PumpNumberStatsResponse
from app.helper.dashboard import get_recent_activities, get_service_report_detail, get_dashboard_statistics, get_service_type_statistics, get_part_number_statistics


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



@router.get("/dashboard/service-report/{report_id}/download-pdf")
async def download_service_report_pdf(
    report_id: str = Path(..., description="Service report ID"),
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_any_role)
):
    """
    Download service report as PDF.
    Generates a formatted PDF with all service report details except images.
    Accessible by any authenticated user.
    """
    try:
        # Get service report details
        report_data = await get_service_report_detail(db=db, report_id=report_id)
        
        # Convert to dict for PDF service
        report_dict = {
            'id': report_data.id,
            'user_name': report_data.user_name,
            'user_email': report_data.user_email,
            'service_type_name': report_data.service_type_name,
            'machine_info': report_data.machine_info.dict() if report_data.machine_info else None,
            'customer_info': report_data.customer_info.dict() if report_data.customer_info else None,
            'problem': report_data.problem,
            'solution': report_data.solution,
            'service_person_name': report_data.service_person_name,
            'files': [file.dict() for file in report_data.files],
            'parts': [part.dict() for part in report_data.parts],
            'created_at': report_data.created_at,
            'updated_at': report_data.updated_at
        }
        
        # Generate PDF
        pdf_service = PDFService()
        pdf_buffer = pdf_service.generate_service_report_pdf(report_dict)
        
        # Create filename
        filename = f"service_report_{report_id[:8]}.pdf"
        
        # Return PDF as streaming response
        return StreamingResponse(
            BytesIO(pdf_buffer.read()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
    


