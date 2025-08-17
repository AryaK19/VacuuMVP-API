from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional, Dict, Any
import uuid

from app.db import models
from app.external_service.aws_service import AWSService


async def get_machines_by_type(
    type_name: str,
    db: Session,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    page: int = 1,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Helper function to get machines by type with filtering, sorting, and pagination
    """
    # Get the type_id for the given type_name
    type_obj = db.query(models.Type).filter(models.Type.type == type_name).first()
    if not type_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Type '{type_name}' not found"
        )

    # Start building the query
    query = db.query(models.Machine).outerjoin(models.SoldMachine).join(models.Type).filter(
        models.Machine.type_id == type_obj.id
    )

    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.Machine.serial_no.ilike(search_term)) |
            (models.Machine.model_no.ilike(search_term)) |
            (models.Machine.part_no.ilike(search_term)) |
            (models.SoldMachine.customer_name.ilike(search_term)) |
            (models.SoldMachine.customer_email.ilike(search_term))
        )

    # Count total items for pagination
    total_items = query.count()

    # Apply sorting
    if hasattr(models.Machine, sort_by):
        sort_column = getattr(models.Machine, sort_by)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    else:
        # Default sort by created_at desc if sort field is invalid
        query = query.order_by(desc(models.Machine.created_at))

    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)

    # Execute query and fetch results
    machines = query.all()

    # Calculate pagination metadata
    has_next = (page * limit) < total_items
    has_previous = page > 1

    # Prepare response with machine type info and sold info
    result_machines = []
    for machine in machines:
        # Convert UUID objects to strings to avoid validation errors
        machine_dict = {
            "id": str(machine.id),
            "serial_no": machine.serial_no,
            "model_no": machine.model_no,
            "part_no": machine.part_no,
            "type_id": str(machine.type_id),
            "created_at": machine.created_at,
            "updated_at": machine.updated_at,
            "date_of_manufacturing": machine.date_of_manufacturing,
            "machine_type": {
                "id": str(machine.machine_type.id),
                "type": machine.machine_type.type
            },
            "sold_info": None
        }

        # Add sold machine info if available
        if machine.sold_info:
            sold_info = {
                "id": str(machine.sold_info.id),
                "machine_id": str(machine.sold_info.machine_id),
                
                "customer_name": machine.sold_info.customer_name,
                "customer_contact": machine.sold_info.customer_contact,
                "customer_email": machine.sold_info.customer_email,
                "customer_address": machine.sold_info.customer_address,
                "created_at": machine.sold_info.created_at,
                "updated_at": machine.sold_info.updated_at
            }
            machine_dict["sold_info"] = sold_info

        result_machines.append(machine_dict)

    return {
        "total": total_items,
        "page": page,
        "limit": limit,
        "has_next": has_next,
        "has_previous": has_previous,
        "items": result_machines
    }


async def create_machine_by_type(
    type_name: str,
    machine_data: Dict[str, Any],
    db: Session,
    file = None
) -> Dict[str, Any]:
    """
    Helper function to create a machine with specific type and optional file upload
    """
    # Get the type_id for the given type_name
    type_obj = db.query(models.Type).filter(models.Type.type == type_name).first()
    if not type_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Type '{type_name}' not found"
        )

    # Check if machine with same serial number already exists
    existing_machine = db.query(models.Machine).filter(
        models.Machine.serial_no == machine_data["serial_no"]
    ).first()
    
    if existing_machine:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Machine with serial number '{machine_data['serial_no']}' already exists"
        )

    file_key = None
    
    # Handle file upload if file is provided
    if file:
        try:
            aws_service = AWSService()
            
            # Upload file to S3 using machine serial number as a unique identifier
            upload_result = aws_service.upload_file(
                file=file.file,
                folder=f"machines/{machine_data['serial_no']}",
                content_type=file.content_type,
                file_name=file.filename
            )
            
            if not upload_result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"ServiceReportFiles upload failed: {upload_result.get('message', 'Unknown error')}"
                )
            
            file_key = upload_result["file_key"]
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"ServiceReportFiles upload failed: {str(e)}"
            )

    # Create new machine
    new_machine = models.Machine(
        id=uuid.uuid4(),
        serial_no=machine_data["serial_no"],
        model_no=machine_data["model_no"],
        part_no=machine_data.get("part_no"),
        type_id=type_obj.id,
        file_key=file_key or machine_data.get("file_key")
    )
    
    try:
        db.add(new_machine)
        db.commit()
        db.refresh(new_machine)
        
        return {
            "success": True,
            "message": f"{type_name.capitalize()} created successfully",
            "machine": {
                "id": str(new_machine.id),
                "serial_no": new_machine.serial_no,
                "model_no": new_machine.model_no,
                "part_no": new_machine.part_no,
                "type_id": str(new_machine.type_id),
                "file_key": new_machine.file_key,
                "type": type_name,
                "created_at": new_machine.created_at,
                "updated_at": new_machine.updated_at
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create {type_name}: {str(e)}"
        )
