from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, or_, and_
from typing import Optional
from math import ceil

from app.db.models import ServiceReport, User, ServiceType, Machine
from app.schema.dashboard import PaginatedRecentActivitiesResponse, RecentActivityResponse, ServiceReportDetailResponse

async def get_recent_activities(
    db: Session,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 10
) -> PaginatedRecentActivitiesResponse:
    """
    Get recent activities from service reports with pagination, search, and sorting.
    """
    try:
        # Base query with joins to get all related data in one query
        query = db.query(
            ServiceReport,
            User.name.label('user_name'),
            User.email.label('user_email'),
            ServiceType.service_type.label('service_type_name')
        ).join(User, ServiceReport.user_id == User.id)\
         .join(ServiceType, ServiceReport.service_type_id == ServiceType.id)
        
        # Apply search filter if provided
        if search:
            search_filter = or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                ServiceType.service_type.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Apply sorting
        if hasattr(ServiceReport, sort_by):
            sort_column = getattr(ServiceReport, sort_by)
        else:
            sort_column = ServiceReport.created_at
            
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        # Get total count for pagination
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        results = query.offset(offset).limit(limit).all()
        
        # Transform data to response format
        activities = []
        for result in results:
            report, user_name, user_email, service_type_name = result
            
            # Use name as the display name, fallback to email if name is None
            display_name = user_name or user_email or "Unknown User"
            
            activity = RecentActivityResponse(
                user_name=display_name,
                service_type_name=service_type_name,
                created_at=report.created_at,
                report_id=str(report.id)
            )
            activities.append(activity)
        
        # Calculate pagination info
        total_pages = ceil(total / limit) if total > 0 else 1
        has_next = page < total_pages
        has_previous = page > 1
        
        return PaginatedRecentActivitiesResponse(
            total=total,
            page=page,
            limit=limit,
            has_next=has_next,
            has_previous=has_previous,
            items=activities
        )
        
    except Exception as e:
        print(f"Dashboard error: {str(e)}")  # For debugging
        raise Exception(f"Error fetching recent activities: {str(e)}")

async def get_service_report_detail(
    db: Session,
    report_id: str
) -> ServiceReportDetailResponse:
    """
    Get detailed information about a specific service report.
    """
    try:
        # Query with all joins to get complete information
        result = db.query(
            ServiceReport,
            User.name.label('user_name'),
            User.email.label('user_email'),
            ServiceType.service_type.label('service_type_name'),
            Machine.serial_no.label('machine_serial_no'),
            Machine.model_no.label('machine_model_no')
        ).join(User, ServiceReport.user_id == User.id)\
         .join(ServiceType, ServiceReport.service_type_id == ServiceType.id)\
         .outerjoin(Machine, ServiceReport.machine_id == Machine.id)\
         .filter(ServiceReport.id == report_id)\
         .first()
        
        if not result:
            raise Exception("Service report not found")
        
        report, user_name, user_email, service_type_name, machine_serial_no, machine_model_no = result
        
        # Use name as display name, fallback to email
        display_name = user_name or user_email or "Unknown User"
        
        return ServiceReportDetailResponse(
            id=str(report.id),
            user_name=display_name,
            user_email=user_email,
            service_type_name=service_type_name,
            machine_serial_no=machine_serial_no,
            machine_model_no=machine_model_no,
            problem=report.problem,
            solution=report.solution,
            service_person_name=report.service_person_name,
            created_at=report.created_at,
            updated_at=report.updated_at
        )
        
    except Exception as e:
        print(f"Service report detail error: {str(e)}")
        raise Exception(f"Error fetching service report details: {str(e)}")