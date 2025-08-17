from fastapi import APIRouter, Depends, Query, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import Optional, Any, Dict

from app.db.session import get_db
from app.schema.machine import PaginatedMachineResponse, MachineCreateRequest, MachineCreateResponse, MachineDetailsResponse, MachineUpdateResponse
from app.middleware.auth import require_admin, require_any_role
from app.helper.machines import get_machines_by_type, create_machine_by_type, get_machine_details, get_machine_service_reports, delete_machine, update_machine_details
from app.config.route_config import MACHINES_PUMPS, MACHINES_PARTS, MACHINES_CREATE_PUMP, MACHINES_CREATE_PART, MACHINE_DETAILS, MACHINE_SERVICE_REPORTS, MACHINE_DELETE, MACHINE_UPDATE

router = APIRouter(tags=["Machines"])

@router.get(MACHINES_PUMPS, response_model=PaginatedMachineResponse)
async def get_pumps(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Any = Depends(require_admin)
):
    """
    Get all machines with type 'pump' with filtering, sorting, and pagination.
    Only accessible by admin users.
    """
    return await get_machines_by_type(
        type_name="pump", 
        db=db, 
        search=search, 
        sort_by=sort_by, 
        sort_order=sort_order, 
        page=page, 
        limit=limit
    )

@router.get(MACHINES_PARTS, response_model=PaginatedMachineResponse)
async def get_parts(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user : Any = Depends(require_any_role)
):
    """
    Get all machines with type 'part' with filtering, sorting, and pagination.
    Only accessible by admin users.
    """
    return await get_machines_by_type(
        type_name="part", 
        db=db, 
        search=search, 
        sort_by=sort_by, 
        sort_order=sort_order, 
        page=page, 
        limit=limit
    )

@router.post(MACHINES_CREATE_PUMP, response_model=MachineCreateResponse)
async def create_pump(
    serial_no: str = Form(...),
    model_no: str = Form(...),
    part_no: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_admin)
):
    """
    Create a new pump machine with optional file upload.
    Only accessible by admin users.
    """
    machine_data = {
        "serial_no": serial_no,
        "model_no": model_no,
        "part_no": part_no
    }
    
    return await create_machine_by_type(
        type_name="pump",
        machine_data=machine_data,
        db=db,
        file=file
    )

@router.post(MACHINES_CREATE_PART, response_model=MachineCreateResponse)
async def create_part(
    serial_no: str = Form(...),
    model_no: str = Form(...),
    part_no: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_admin)
):
    """
    Create a new part machine with optional file upload.
    Only accessible by admin users.
    """
    machine_data = {
        "serial_no": serial_no,
        "model_no": model_no,
        "part_no": part_no
    }
    
    return await create_machine_by_type(
        type_name="part",
        machine_data=machine_data,
        db=db,
        file=file
    )

@router.get(MACHINE_DETAILS, response_model=MachineDetailsResponse)
async def get_machine_details_endpoint(
    id: str,
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_any_role)
):
    """
    Get comprehensive machine details including all service reports.
    Accessible by admin and distributor users.
    """
    return await get_machine_details(
        machine_id=id,
        db=db
    )

@router.get(MACHINE_SERVICE_REPORTS, response_model=Dict[str, Any])
async def get_machine_service_reports_endpoint(
    id: str,
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Any = Depends(require_any_role)
):
    """
    Get all service reports for a specific machine with filtering, sorting, and pagination.
    Accessible by admin and distributor users.
    """
    return await get_machine_service_reports(
        machine_id=id,
        db=db,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit
    )

@router.delete(MACHINE_DELETE)
async def delete_machine_endpoint(
    id: str,
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_admin)
):
    """
    Delete a machine and all related data (service reports, sold machine info, files).
    Only accessible by admin users.
    """
    return await delete_machine(
        machine_id=id,
        db=db
    )

@router.put(MACHINE_UPDATE, response_model=MachineUpdateResponse)
async def update_machine_endpoint(
    id: str,
    serial_no: Optional[str] = Form(None),
    model_no: Optional[str] = Form(None),
    part_no: Optional[str] = Form(None),
    date_of_manufacturing: Optional[str] = Form(None),  # Will be parsed to date
    customer_name: Optional[str] = Form(None),
    customer_contact: Optional[str] = Form(None),
    customer_email: Optional[str] = Form(None),
    customer_address: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_admin)
):
    """
    Update machine details including customer information and optional file replacement.
    Only accessible by admin users.
    """
    try:
        # Parse date if provided
        parsed_date = None
        if date_of_manufacturing:
            from datetime import datetime
            try:
                parsed_date = datetime.strptime(date_of_manufacturing, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )

        machine_data = {
            "serial_no": serial_no,
            "model_no": model_no,
            "part_no": part_no,
            "date_of_manufacturing": parsed_date,
            "customer_name": customer_name,
            "customer_contact": customer_contact,
            "customer_email": customer_email,
            "customer_address": customer_address
        }
        
        # Remove None values to avoid updating fields that weren't provided
        machine_data = {k: v for k, v in machine_data.items() if v is not None}
        
        return await update_machine_details(
            machine_id=id,
            machine_data=machine_data,
            db=db,
            file=file
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update machine: {str(e)}"
        )

