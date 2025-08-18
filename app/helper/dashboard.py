from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, or_, and_, func, extract
from typing import Optional
from math import ceil
from datetime import datetime, timedelta

from app.db.models import ServiceReport, User, ServiceType, Machine, ServiceReportFiles, ServiceReportPart, Type, SoldMachine, Role
from app.schema.dashboard import (
    PaginatedRecentActivitiesResponse, 
    RecentActivityResponse, 

    DashboardStatsResponse,
    ServiceTypeStatsResponse,
    ServiceTypeStatsItem,
    PumpNumberStatsResponse,
    PumpNumberStatsItem
)
from app.external_service.aws_service import AWSService

async def get_dashboard_statistics(db: Session) -> DashboardStatsResponse:
    """
    Get dashboard statistics including distributors, sold/available machines, and monthly service reports.
    """
    try:
        # Get total distributors (users with 'distributor' role)
        distributor_role = db.query(Role).filter(Role.role_name.ilike('%distributor%')).first()
        total_distributors = 0
        
        if distributor_role:
            total_distributors = db.query(User).filter(User.role_id == distributor_role.id).count()
        
        # Get sold vs available machines
        total_machines = db.query(Machine).count()
        sold_machines_count = db.query(SoldMachine.machine_id).distinct().count()
        available_machines = total_machines - sold_machines_count
        
        # Get current month's service reports
        current_date = datetime.now()
        current_month = current_date.month
        current_year = current_date.year
        
        monthly_service_reports = db.query(ServiceReport).filter(
            extract('month', ServiceReport.created_at) == current_month,
            extract('year', ServiceReport.created_at) == current_year
        ).count()
        
        return DashboardStatsResponse(
            total_distributors=total_distributors,
            sold_machines=sold_machines_count,
            available_machines=available_machines,
            monthly_service_reports=monthly_service_reports
        )
        
    except Exception as e:
        print(f"Dashboard statistics error: {str(e)}")
        raise Exception(f"Error fetching dashboard statistics: {str(e)}")

async def get_service_type_statistics(db: Session) -> ServiceTypeStatsResponse:
    """
    Get service type statistics for bar chart.
    """
    try:
        # Define the service types we want to track
        expected_service_types = ['Warranty', 'AMC', 'Paid', 'Installation', 'Health Check']
        
        # Get counts for each service type from service reports
        service_type_counts = db.query(
            ServiceType.service_type,
            func.count(ServiceReport.id).label('count')
        ).outerjoin(ServiceReport, ServiceReport.service_type_id == ServiceType.id)\
         .group_by(ServiceType.service_type)\
         .all()
        
        # Create a dictionary for quick lookup
        counts_dict = {service_type: count for service_type, count in service_type_counts}
        
        # Ensure all expected service types are included, even if count is 0
        service_type_stats = []
        for service_type in expected_service_types:
            # Check for exact match first, then case-insensitive match
            count = 0
            for db_service_type, db_count in counts_dict.items():
                if db_service_type and db_service_type.lower() == service_type.lower():
                    count = db_count
                    break
            
            service_type_stats.append(ServiceTypeStatsItem(
                service_type=service_type,
                count=count
            ))
        
        return ServiceTypeStatsResponse(service_types=service_type_stats)
        
    except Exception as e:
        print(f"Service type statistics error: {str(e)}")
        raise Exception(f"Error fetching service type statistics: {str(e)}")

async def get_recent_activities(
    db: Session,
    user_id: str,  # Add user_id parameter
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    page: int = 1,
    limit: int = 10
) -> PaginatedRecentActivitiesResponse:
    """
    Get recent activities from service reports with pagination, search, and sorting.
    For admin users: show all activities
    For distributors: show only their own activities
    """
    try:
        # Check if user is admin
        user = db.query(User).filter(User.id == user_id).first()
        is_admin = False
        
        if user and user.role:
            is_admin = user.role.role_name.lower() == "admin"
        
        # Base query with joins to get all related data in one query
        query = db.query(
            ServiceReport,
            User.name.label('user_name'),
            User.email.label('user_email'),
            ServiceType.service_type.label('service_type_name')
        ).join(User, ServiceReport.user_id == User.id)\
         .join(ServiceType, ServiceReport.service_type_id == ServiceType.id)
        
        # Filter by user_id only if not admin
        if not is_admin:
            query = query.filter(ServiceReport.user_id == user_id)
            
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



async def get_part_number_statistics(db: Session) -> PumpNumberStatsResponse:
    """
    Get service statistics grouped by part number.
    Returns count of service reports for each part number along with model number.
    """
    try:
        # Query to get part_no, model_no and count of service reports
        pump_stats_query = db.query(
            Machine.part_no,
            Machine.model_no,
            func.count(ServiceReport.id).label('service_count')
        ).outerjoin(ServiceReport, ServiceReport.machine_id == Machine.id)\
         .filter(Machine.part_no.isnot(None))\
         .group_by(Machine.part_no, Machine.model_no)\
         .order_by(desc(func.count(ServiceReport.id)))
        
        results = pump_stats_query.all()
        
        # Transform results to response format
        pump_statistics = []
        for result in results:
            part_no, model_no, service_count = result
            
            stat_item = PumpNumberStatsItem(
                part_no=part_no,
                model_no=model_no,
                service_count=service_count
            )
            pump_statistics.append(stat_item)

        return PumpNumberStatsResponse(part_statistics=pump_statistics)

    except Exception as e:
        print(f"Pump number statistics error: {str(e)}")
        raise Exception(f"Error fetching pump number statistics: {str(e)}")


