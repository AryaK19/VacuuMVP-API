from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, or_, and_, func, extract
from typing import Optional
from math import ceil
from datetime import datetime, timedelta

from app.db.models import ServiceReport, User, ServiceType, Machine, ServiceReportFiles, ServiceReportPart, Type, SoldMachine, Role
from app.schema.dashboard import (
    PaginatedRecentActivitiesResponse, 
    RecentActivityResponse, 
    ServiceReportDetailResponse, 
    ServiceReportFileInfo,
    ServiceReportPartInfo,
    ServiceReportMachineInfo,
    ServiceReportCustomerInfo,
    DashboardStatsResponse,
    ServiceTypeStatsResponse,
    ServiceTypeStatsItem
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


async def get_service_report_detail(
    db: Session,
    report_id: str
) -> ServiceReportDetailResponse:
    """
    Get detailed information about a specific service report including files, machine details, customer info, and parts.
    """
    try:
        # Query with all joins to get complete information including customer data
        result = db.query(
            ServiceReport,
            User.name.label('user_name'),
            User.email.label('user_email'),
            ServiceType.service_type.label('service_type_name'),
            Machine.serial_no.label('machine_serial_no'),
            Machine.model_no.label('machine_model_no'),
            Machine.part_no.label('machine_part_no'),
            Machine.date_of_manufacturing.label('machine_manufacturing_date'),
            Type.type.label('machine_type_name'),
            SoldMachine.customer_name.label('customer_name'),
            SoldMachine.customer_email.label('customer_email'),
            SoldMachine.customer_contact.label('customer_contact'),
            SoldMachine.customer_address.label('customer_address'),
            SoldMachine.created_at.label('sold_date')
        ).join(User, ServiceReport.user_id == User.id)\
         .join(ServiceType, ServiceReport.service_type_id == ServiceType.id)\
         .outerjoin(Machine, ServiceReport.machine_id == Machine.id)\
         .outerjoin(Type, Machine.type_id == Type.id)\
         .outerjoin(SoldMachine, and_(
             SoldMachine.machine_id == ServiceReport.machine_id,
             SoldMachine.user_id == ServiceReport.user_id
         ))\
         .filter(ServiceReport.id == report_id)\
         .first()
        
        if not result:
            raise Exception("Service report not found")
        
        (report, user_name, user_email, service_type_name, 
         machine_serial_no, machine_model_no, machine_part_no, 
         machine_manufacturing_date, machine_type_name,
         customer_name, customer_email, customer_contact, 
         customer_address, sold_date) = result
        
        # Use name as display name, fallback to email
        display_name = user_name or user_email or "Unknown User"
        
        # Create machine info object
        machine_info = None
        if machine_serial_no or machine_model_no or machine_part_no:
            machine_info = ServiceReportMachineInfo(
                serial_no=machine_serial_no,
                model_no=machine_model_no,
                part_no=machine_part_no,
                type_name=machine_type_name,
                date_of_manufacturing=machine_manufacturing_date
            )
        
        # Create customer info object
        customer_info = None
        if customer_name or customer_email or customer_contact or customer_address:
            customer_info = ServiceReportCustomerInfo(
                customer_name=customer_name,
                customer_email=customer_email,
                customer_contact=customer_contact,
                customer_address=customer_address,
                sold_date=sold_date
            )
        
        # Get service report files
        report_files = db.query(ServiceReportFiles).filter(
            ServiceReportFiles.service_report_id == report_id
        ).all()
        
        # Get service report parts with machine details
        report_parts = db.query(
            ServiceReportPart,
            Machine.serial_no.label('part_machine_serial_no'),
            Machine.model_no.label('part_machine_model_no'),
            Machine.part_no.label('part_machine_part_no')
        ).join(Machine, ServiceReportPart.machine_id == Machine.id)\
         .filter(ServiceReportPart.service_report_id == report_id)\
         .all()
        
        # Initialize AWS service for generating file URLs
        aws_service = AWSService()
        
        # Process files and generate URLs
        files_info = []
        for file_record in report_files:
            try:
                # Try to generate presigned URL for secure access
                url_result = aws_service.get_presigned_url(file_record.file_key, expires_in=3600)
                
                if url_result["success"]:
                    file_url = url_result["url"]
                else:
                    # Fallback to direct URL if presigned URL fails
                    bucket_name = aws_service.bucket_name
                    region = aws_service.region
                    file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_record.file_key}"
                
                file_info = ServiceReportFileInfo(
                    id=str(file_record.id),
                    file_key=file_record.file_key,
                    file_url=file_url,
                    created_at=file_record.created_at
                )
                files_info.append(file_info)
                
            except Exception as file_error:
                print(f"Error processing file {file_record.file_key}: {str(file_error)}")
                # Continue with other files even if one fails
                continue
        
        # Process parts information
        parts_info = []
        for part_result in report_parts:
            part_record, part_serial_no, part_model_no, part_part_no = part_result
            
            part_info = ServiceReportPartInfo(
                id=str(part_record.id),
                machine_serial_no=part_serial_no,
                machine_model_no=part_model_no,
                machine_part_no=part_part_no,
                quantity=part_record.quantity,
                created_at=part_record.created_at
            )
            parts_info.append(part_info)
        
        return ServiceReportDetailResponse(
            id=str(report.id),
            user_name=display_name,
            user_email=user_email,
            service_type_name=service_type_name,
            machine_info=machine_info,
            customer_info=customer_info,
            problem=report.problem,
            solution=report.solution,
            service_person_name=report.service_person_name,
            files=files_info,
            parts=parts_info,
            created_at=report.created_at,
            updated_at=report.updated_at
        )
        
    except Exception as e:
        print(f"Service report detail error: {str(e)}")
        raise Exception(f"Error fetching service report details: {str(e)}")