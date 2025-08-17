from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional, Dict, Any, List
import uuid

from app.db import models
from app.external_service.aws_service import AWSService

async def create_service_report(
    service_report_data: Dict[str, Any],
    user_id: str,
    parts: List[Dict[str, Any]],
    files: List[UploadFile],
    db: Session
) -> Dict[str, Any]:
    """
    Helper function to create a service report with parts and files
    """
    try:
        # Validate service type exists
        service_type = db.query(models.ServiceType).filter(
            models.ServiceType.id == service_report_data["service_type_id"]
        ).first()
        
        if not service_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service type not found"
            )

        # Validate machine exists if machine_id is provided
        machine = None
        if service_report_data.get("machine_id"):
            machine = db.query(models.Machine).filter(
                models.Machine.id == service_report_data["machine_id"]
            ).first()
            
            if not machine:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Machine not found"
                )


        # Create service report
        new_service_report = models.ServiceReport(
            id=uuid.uuid4(),
            user_id=user_id,
            machine_id=service_report_data.get("machine_id"),
            problem=service_report_data.get("problem"),
            solution=service_report_data.get("solution"),
            service_person_name=service_report_data.get("service_person_name"),
            service_type_id=service_report_data["service_type_id"]
        )

        print("this is done ")

        db.add(new_service_report)
        db.flush()  # Flush to get the ID

        # Add service report parts
        for part_data in parts:
            # Validate part machine exists
            part_machine = db.query(models.Machine).filter(
                models.Machine.id == part_data["machine_id"]
            ).first()
            
            if not part_machine:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Part machine with ID {part_data['machine_id']} not found"
                )

            service_part = models.ServiceReportPart(
                id=uuid.uuid4(),
                service_report_id=new_service_report.id,
                machine_id=part_data["machine_id"],
                quantity=part_data.get("quantity", 1)
            )
            db.add(service_part)



        # Handle file uploads
        if files:
            aws_service = AWSService()
            
            for file in files:
                if file.filename:  # Only process files with names
                    upload_result = aws_service.upload_file(
                        file=file.file,
                        folder=f"service_reports/{new_service_report.id}",
                        content_type=file.content_type,
                        file_name=file.filename
                    )
                    
                    if upload_result["success"]:
                        file_record = models.ServiceReportFiles(
                            id=uuid.uuid4(),
                            service_report_id=new_service_report.id,
                            file_key=upload_result["file_key"]
                        )
                        db.add(file_record)

        db.commit()
        db.refresh(new_service_report)

        print("files uploaded")

        # Build response with related data
        return {
            "success": True,
            "message": "Service report created successfully",
            "service_report": build_service_report_response(new_service_report, db)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create service report: {str(e)}"
        )

async def get_user_service_reports(
    user_id: str,
    db: Session,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    page: int = 1,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Helper function to get service reports for a specific user
    """
    # Start building the query
    user = db.query(models.User).filter(models.User.id == user_id).first()
    is_admin = False
    
    if user and user.role:
        is_admin = user.role.role_name.lower() == "admin"
    
    # Start building the query
    query = db.query(models.ServiceReport)
    
    # Filter by user_id only if not admin
    if not is_admin:
        query = query.filter(models.ServiceReport.user_id == user_id)
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.ServiceReport.problem.ilike(search_term)) |
            (models.ServiceReport.solution.ilike(search_term)) |
            (models.ServiceReport.service_person_name.ilike(search_term))
        )

    # Count total items for pagination
    total_items = query.count()

    # Apply sorting
    if hasattr(models.ServiceReport, sort_by):
        sort_column = getattr(models.ServiceReport, sort_by)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(models.ServiceReport.created_at))

    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)

    # Execute query
    service_reports = query.all()

    # Calculate pagination metadata
    has_next = (page * limit) < total_items
    has_previous = page > 1

    # Build response
    result_reports = []
    for report in service_reports:
        result_reports.append(build_service_report_response(report, db))

    return {
        "total": total_items,
        "page": page,
        "limit": limit,
        "has_next": has_next,
        "has_previous": has_previous,
        "items": result_reports
    }



def build_service_report_response(service_report: models.ServiceReport, db: Session) -> Dict[str, Any]:
    """
    Helper function to build service report response with related data
    """
    return {
        "id": str(service_report.id),
        "user_id": str(service_report.user_id),
        "machine_id": str(service_report.machine_id) if service_report.machine_id else None,
        "problem": service_report.problem,
        "solution": service_report.solution,
        "service_person_name": service_report.service_person_name,
        "service_type_id": str(service_report.service_type_id),
        "created_at": service_report.created_at,
        "updated_at": service_report.updated_at,
        "service_type": {
            "id": str(service_report.service_type.id),
            "service_type": service_report.service_type.service_type
        } if service_report.service_type else None,
        "machine": {
            "id": str(service_report.machine.id),
            "serial_no": service_report.machine.serial_no,
            "model_no": service_report.machine.model_no,
            "part_no": service_report.machine.part_no
        } if service_report.machine else None,
        "parts": [
            {
                "id": str(part.id),
                "service_report_id": str(part.service_report_id),
                "machine_id": str(part.machine_id),
                "quantity": part.quantity,
                "created_at": part.created_at,
                "updated_at": part.updated_at
            }
            for part in service_report.parts
        ],
        "files": [
            {
                "id": str(file.id),
                "service_report_id": str(file.service_report_id),
                "file_key": file.file_key,
                "created_at": file.created_at,
                "updated_at": file.updated_at
            }
            for file in service_report.service_report_files  # Changed from .files to .service_report_files
        ]
    }

async def get_machine_by_serial_no(
    serial_no: str,
    db: Session
) -> Dict[str, Any]:
    """
    Helper function to get machine information by serial number
    """
    try:
        # Find machine by serial number
        machine = db.query(models.Machine).filter(
            models.Machine.serial_no == serial_no
        ).first()
        
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine with serial number '{serial_no}' not found"
            )
        
        # Get sold machine info if available
        sold_machine = db.query(models.SoldMachine).filter(
            models.SoldMachine.machine_id == machine.id
        ).first()
        
        # Generate presigned URL for machine file if exists
        file_url = None
        if machine.file_key:
            aws_service = AWSService()
            url_result = aws_service.get_presigned_url(machine.file_key)
            if url_result["success"]:
                file_url = url_result["url"]
        
        return {
            "success": True,
            "machine": {
                "machine_id": str(machine.id),
                "serial_no": machine.serial_no,
                "model_no": machine.model_no,
                "part_no": machine.part_no,
                "sold_machine_id": str(sold_machine.id) if sold_machine else None,
                "date_of_manufacturing": machine.date_of_manufacturing,
                "customer_name": sold_machine.customer_name if sold_machine else None,
                "customer_contact": sold_machine.customer_contact if sold_machine else None,
                "customer_email": sold_machine.customer_email if sold_machine else None,
                "customer_address": sold_machine.customer_address if sold_machine else None,
                
                "file_url": file_url,
                "is_sold": bool(sold_machine)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve machine information: {str(e)}"
        )

async def create_customer_record(
    customer_data: Dict[str, Any],
    user_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Helper function to create a sold machine record with customer details
    """
    try:
        # Validate machine exists
        machine = db.query(models.Machine).filter(
            models.Machine.id == customer_data["machine_id"]
        ).first()
        
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Machine not found"
            )

        # Check if machine is already sold
        existing_sold_machine = db.query(models.SoldMachine).filter(
            models.SoldMachine.machine_id == customer_data["machine_id"]
        ).first()
        
        if existing_sold_machine:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Machine is already sold to another customer"
            )

        # Create sold machine record
        new_sold_machine = models.SoldMachine(
            id=uuid.uuid4(),
            user_id=user_id,
            machine_id=customer_data["machine_id"],
            customer_name=customer_data["customer_name"],
            customer_contact=customer_data.get("customer_contact"),
            customer_email=customer_data.get("customer_email"),
            customer_address=customer_data.get("customer_address")
        )

        db.add(new_sold_machine)
        db.commit()
        db.refresh(new_sold_machine)

        return {
            "success": True,
            "message": "Customer record created successfully",
            "sold_machine": {
                "id": str(new_sold_machine.id),
                "user_id": str(new_sold_machine.user_id),
                "machine_id": str(new_sold_machine.machine_id),
                "customer_name": new_sold_machine.customer_name,
                "customer_contact": new_sold_machine.customer_contact,
                "customer_email": new_sold_machine.customer_email,
                "customer_address": new_sold_machine.customer_address,
                "created_at": new_sold_machine.created_at,
                "updated_at": new_sold_machine.updated_at,
                "machine": {
                    "serial_no": machine.serial_no,
                    "model_no": machine.model_no,
                    "part_no": machine.part_no
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create customer record: {str(e)}"
        )
