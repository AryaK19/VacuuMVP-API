from fastapi import APIRouter, Depends, Query, File, UploadFile, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Any, List
import json
from app.db import models
from app.db.session import get_db
from app.schema.service_report import ServiceReportCreateResponse, PaginatedServiceReportResponse, SoldMachineCreateRequest, SoldMachineCreateResponse
from app.middleware.auth import require_any_role, get_current_user
from app.helper.service_report import create_service_report, get_user_service_reports, get_machine_by_serial_no, create_customer_record
from app.db.models import User
from app.config.route_config import SERVICE_REPORTS, SERVICE_REPORTS_TYPES, SERVICE_REPORTS_MACHINE, SERVICE_REPORT_CUSTOMER

router = APIRouter(tags=["Service Reports"])

@router.post(SERVICE_REPORTS, response_model=ServiceReportCreateResponse)
async def create_service_report_endpoint(
    service_type_id: str = Form(...),
    machine_id: Optional[str] = Form(None),
    problem: Optional[str] = Form(None),
    solution: Optional[str] = Form(None),
    service_person_name: Optional[str] = Form(None),
    parts: Optional[str] = Form("[]"),  # JSON string of parts
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role)
):
    """
    Create a new service report with parts and files.
    Accessible by admin and distributer users.
    """
    try:
        # Parse parts JSON
        parts_data = json.loads(parts) if parts else []

        # Validate that at least one of machine_id or sold_machine_id is provided
        if not machine_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="machine_id must be provided"
            )

        service_report_data = {
            "service_type_id": service_type_id,
            "machine_id": machine_id,
            "problem": problem,
            "solution": solution,
            "service_person_name": service_person_name
        }

        return await create_service_report(
            service_report_data=service_report_data,
            user_id=str(current_user.id),
            parts=parts_data,
            files=files or [],
            db=db
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format for parts"
        )

@router.get(SERVICE_REPORTS, response_model=PaginatedServiceReportResponse)
async def get_my_service_reports(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_any_role)
):
    """
    Get all service reports for the current user with filtering, sorting, and pagination.
    Accessible by admin and distributer users.
    """
    return await get_user_service_reports(
        user_id=str(current_user.id),
        db=db,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit
    )

@router.get(SERVICE_REPORTS_TYPES)
async def get_service_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role)
):
    """
    Get all available service types.
    Accessible by admin and distributer users.
    """
    try:
        service_types = db.query(models.ServiceType).all()
        
        return {
            "success": True,
            "service_types": [
                {
                    "id": str(service_type.id),
                    "service_type": service_type.service_type,
                    "created_at": service_type.created_at,
                    "updated_at": service_type.updated_at
                }
                for service_type in service_types
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve service types: {str(e)}"
        )

@router.get(SERVICE_REPORTS_MACHINE)
async def get_machine_info_by_serial(
    serial_no: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role)
):
    """
    Get machine information by serial number including customer details and file URL.
    Accessible by admin and distributer users.
    """
    return await get_machine_by_serial_no(
        serial_no=serial_no,
        db=db
    )

@router.post(SERVICE_REPORT_CUSTOMER, response_model=SoldMachineCreateResponse)
async def create_customer_record_endpoint(
    customer_data: SoldMachineCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_role)
):
    """
    Create a customer record by adding machine to sold_machines table.
    Accessible by admin and distributer users.
    """
    return await create_customer_record(
        customer_data=customer_data.dict(),
        user_id=str(current_user.id),
        db=db
    )


