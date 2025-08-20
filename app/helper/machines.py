from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional, Dict, Any, List
import uuid

from app.db import models
from app.external_service.aws_service import AWSService

from app.schema.machine import CustomerInfo, CustomerInfoListResponse

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
    Helper function to get only sold machines by type with filtering, sorting, and pagination
    """
    # Get the type_id for the given type_name
    type_obj = db.query(models.Type).filter(models.Type.type == type_name).first()
    if not type_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Type '{type_name}' not found"
        )

    # Build base query: INNER JOIN to only get machines that are sold
    base_query = db.query(models.Machine).join(models.Type).filter(
        models.Machine.type_id == type_obj.id
    )

    # Apply search filter if provided (serial_no now from SoldMachine)
    if search:
        search_term = f"%{search}%"
        base_query = base_query.filter(
            (models.Machine.model_no.ilike(search_term)) |
            (models.Machine.part_no.ilike(search_term))
        )

    # Get all matching machine IDs (distinct)
    machine_ids_query = base_query.with_entities(models.Machine.id)
    machine_ids = [str(row.id) for row in machine_ids_query.distinct().all()]
    total_items = len(machine_ids)

    # Sorting in Python since we can't sort by other columns in DISTINCT subquery
    if hasattr(models.Machine, sort_by):
        sort_attr = sort_by
    else:
        sort_attr = "created_at"

    reverse = sort_order.lower() == "desc"

    # Fetch all machines for these IDs
    if not machine_ids:
        machines = []
    else:
        machines = db.query(models.Machine).filter(models.Machine.id.in_(machine_ids)).all()
        # Sort machines in Python
        machines = sorted(
            machines,
            key=lambda m: getattr(m, sort_attr) or "",
            reverse=reverse
        )
        # Paginate in Python
        machines = machines[(page - 1) * limit : page * limit]

    # Pagination metadata
    has_next = (page * limit) < total_items
    has_previous = page > 1

    # Prepare response with machine type info and sold info
    result_machines = []
    for machine in machines:

        machine_dict = {
            "id": str(machine.id),
            "model_no": machine.model_no,
            "part_no": machine.part_no,
            "type_id": str(machine.type_id),
            "created_at": machine.created_at,
            "updated_at": machine.updated_at,
            "machine_type": {
                "id": str(machine.machine_type.id),
                "type": machine.machine_type.type
            }
        }
        result_machines.append(machine_dict)

    return {
        "total": total_items,
        "page": page,
        "limit": limit,
        "has_next": has_next,
        "has_previous": has_previous,
        "items": result_machines
    }


async def get_sold_machines_by_type(
    type_name: str,
    db: Session,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    page: int = 1,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Helper function to get only sold machines by type with filtering, sorting, and pagination
    """
    # Get the type_id for the given type_name
    type_obj = db.query(models.Type).filter(models.Type.type == type_name).first()
    if not type_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Type '{type_name}' not found"
        )

    # Build base query: INNER JOIN to only get machines that are sold
    base_query = db.query(models.Machine).join(models.SoldMachine).join(models.Type).filter(
        models.Machine.type_id == type_obj.id
    )

    # Apply search filter if provided (serial_no now from SoldMachine)
    if search:
        search_term = f"%{search}%"
        base_query = base_query.filter(
            (models.SoldMachine.serial_no.ilike(search_term)) |
            (models.Machine.model_no.ilike(search_term)) |
            (models.Machine.part_no.ilike(search_term)) |
            (models.SoldMachine.customer_name.ilike(search_term)) |
            (models.SoldMachine.customer_email.ilike(search_term)) |
            (models.SoldMachine.customer_company.ilike(search_term))
        )

    # Get all matching machine IDs (distinct)
    machine_ids_query = base_query.with_entities(models.Machine.id)
    machine_ids = [str(row.id) for row in machine_ids_query.distinct().all()]
    total_items = len(machine_ids)

    # Sorting in Python since we can't sort by other columns in DISTINCT subquery
    if hasattr(models.Machine, sort_by):
        sort_attr = sort_by
    else:
        sort_attr = "created_at"

    reverse = sort_order.lower() == "desc"

    # Fetch all machines for these IDs
    if not machine_ids:
        machines = []
    else:
        machines = db.query(models.Machine).filter(models.Machine.id.in_(machine_ids)).all()
        # Sort machines in Python
        machines = sorted(
            machines,
            key=lambda m: getattr(m, sort_attr) or "",
            reverse=reverse
        )
        # Paginate in Python
        machines = machines[(page - 1) * limit : page * limit]

    # Pagination metadata
    has_next = (page * limit) < total_items
    has_previous = page > 1

    # Prepare response with machine type info and sold info
    result_machines = []
    for machine in machines:
        sold_info = None
        serial_no = ""
        date_of_manufacturing = None
        if hasattr(machine, "sold_info") and machine.sold_info:
            sold_info = {
                "id": str(machine.sold_info.id),
                "machine_id": str(machine.sold_info.machine_id),
                "serial_no": machine.sold_info.serial_no,
                "customer_company": machine.sold_info.customer_company,
                "customer_name": machine.sold_info.customer_name,
                "customer_contact": machine.sold_info.customer_contact,
                "customer_email": machine.sold_info.customer_email,
                "customer_address": machine.sold_info.customer_address,
                "date_of_manufacturing": machine.sold_info.date_of_manufacturing,
                "created_at": machine.sold_info.created_at,
                "updated_at": machine.sold_info.updated_at
            }
            serial_no = machine.sold_info.serial_no or ""
            date_of_manufacturing = machine.sold_info.date_of_manufacturing

        machine_dict = {
            "id": str(machine.id),
            "serial_no": serial_no,  # Always a string
            "model_no": machine.model_no,
            "part_no": machine.part_no,
            "type_id": str(machine.type_id),
            "created_at": machine.created_at,
            "updated_at": machine.updated_at,
            "date_of_manufacturing": date_of_manufacturing,
            "machine_type": {
                "id": str(machine.machine_type.id),
                "type": machine.machine_type.type
            },
            "sold_info": sold_info
        }
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
        models.Machine.part_no == machine_data["part_no"]
    ).first()
    
    if existing_machine:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Machine with Part number '{machine_data['part_no']}' already exists"
        )

    file_key = None
    
    # Handle file upload if file is provided
    if file:
        try:
            aws_service = AWSService()
            
            # Upload file to S3 using machine serial number as a unique identifier
            upload_result = aws_service.upload_file(
                file=file.file,
                folder=f"machines/{machine_data['part_no']}",
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



async def create_sold_machine(
    machine_data: Dict[str, Any],
    db: Session,
    file = None
) -> Dict[str, Any]:
    """
    Helper function to create a sold machine with specific type and optional file upload
    """

    # Check if machine with same serial number already exists
    existing_machine = db.query(models.SoldMachine).filter(
        models.SoldMachine.serial_no == machine_data.get("serial_no")
    ).first()

    machine = db.query(models.Machine).filter(
        models.Machine.part_no == machine_data.get("part_no")
    ).first()

    if existing_machine:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sold Machine with Serial number '{machine_data['serial_no']}' already exists"
        )



    # Create new sold machine
    new_sold_machine = models.SoldMachine(
        id=uuid.uuid4(),
        serial_no=machine_data.get("serial_no"),
        machine_id=machine.id,
        customer_company=machine_data.get("customer_company"),
        customer_name=machine_data.get("customer_name"),
        customer_contact=machine_data.get("customer_contact"),
        customer_email=machine_data.get("customer_email"),
        customer_address=machine_data.get("customer_address"),
        date_of_manufacturing=machine_data.get("date_of_manufacturing"),
    )

    try:
        db.add(new_sold_machine)
        db.commit()
        db.refresh(new_sold_machine)

        return {
            "success": True,
            "message": f"Sold Machine created successfully",
            "machine": {
                "id": str(new_sold_machine.id),
                "serial_no": new_sold_machine.serial_no,
                "machine_id": str(new_sold_machine.machine_id),
                "customer_company": new_sold_machine.customer_company,
                "customer_name": new_sold_machine.customer_name,
                "customer_contact": new_sold_machine.customer_contact,
                "customer_email": new_sold_machine.customer_email,
                "customer_address": new_sold_machine.customer_address,
                "date_of_manufacturing": new_sold_machine.date_of_manufacturing,
                "created_at": new_sold_machine.created_at,
                "updated_at": new_sold_machine.updated_at
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sold machine: {str(e)}"
        )


async def get_sold_machine_details(
    sold_machine_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Helper function to get comprehensive machine details without service reports
    """
    try:
        # Get machine by ID

        sold_machine = db.query(models.SoldMachine).filter(
            models.SoldMachine.id == sold_machine_id
        ).first()

        machine = db.query(models.Machine).filter(
            models.Machine.id == sold_machine.machine_id
        ).first()
        
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine with Sold ID '{sold_machine_id}' not found"
            )
        

        
        # Generate presigned URL for machine file if exists
        file_url = None
        if machine.file_key:
            aws_service = AWSService()
            url_result = aws_service.get_presigned_url(machine.file_key)
            if url_result["success"]:
                file_url = url_result["url"]

        # serial_no and date_of_manufacturing now come from sold_machine
        serial_no = sold_machine.serial_no if sold_machine else ""
        date_of_manufacturing = sold_machine.date_of_manufacturing if sold_machine else None

        return {
            "success": True,
            "machine": {
                "id": str(machine.id),
                "serial_no": serial_no,
                "model_no": machine.model_no,
                "part_no": machine.part_no,
                "date_of_manufacturing": date_of_manufacturing,
                "file_url": file_url,
                "created_at": machine.created_at,
                "updated_at": machine.updated_at,
                "machine_type": {
                    "id": str(machine.machine_type.id),
                    "type": machine.machine_type.type
                },
                "sold_info": {
                    "id": str(sold_machine.id),
                    "serial_no": sold_machine.serial_no,
                    "customer_company": sold_machine.customer_company,
                    "customer_name": sold_machine.customer_name,
                    "customer_contact": sold_machine.customer_contact,
                    "customer_email": sold_machine.customer_email,
                    "customer_address": sold_machine.customer_address,
                    "date_of_manufacturing": sold_machine.date_of_manufacturing,
                    "created_at": sold_machine.created_at,
                    "updated_at": sold_machine.updated_at,
                    # Add user info if you have a user relationship in SoldMachine
                    "user": {
                        "id": str(sold_machine.user.id),
                        "name": sold_machine.user.name,
                        "email": sold_machine.user.email
                    } if hasattr(sold_machine, "user") and sold_machine.user else None
                } if sold_machine else None,
                "is_sold": bool(sold_machine)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve machine details: {str(e)}"
        )

async def get_machine_service_reports(
    sold_machine_id: str,
    db: Session,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    page: int = 1,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Helper function to get service reports for a specific sold machine with pagination
    """
    try:
        # Verify sold machine exists
        sold_machine = db.query(models.SoldMachine).filter(
            models.SoldMachine.id == sold_machine_id
        ).first()
        if not sold_machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sold machine with ID '{sold_machine_id}' not found"
            )

        machine = sold_machine.machine

        # Start building the query
        query = db.query(models.ServiceReport).filter(
            models.ServiceReport.sold_machine_id == sold_machine_id
        )

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

        # Build service reports response
        service_reports_data = []
        for report in service_reports:
            report_data = {
                "id": str(report.id),
                "user_id": str(report.user_id),
                "problem": report.problem,
                "solution": report.solution,
                "service_person_name": report.service_person_name,
                "created_at": report.created_at,
                "updated_at": report.updated_at,
                "service_type": {
                    "id": str(report.service_type.id),
                    "service_type": report.service_type.service_type
                } if report.service_type else None,
                "user": {
                    "id": str(report.user.id),
                    "name": report.user.name,
                    "email": report.user.email
                } if report.user else None
            }
            service_reports_data.append(report_data)

        return {
            "total": total_items,
            "page": page,
            "limit": limit,
            "has_next": has_next,
            "has_previous": has_previous,
            "items": service_reports_data,
            "machine": {
                "id": str(machine.id),
                "serial_no": sold_machine.serial_no,
                "model_no": machine.model_no
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve machine service reports: {str(e)}"
        )


async def delete_sold_machine(
    sold_machine_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Helper function to delete a sold machine (and cascade service reports/files), but NOT the machine itself
   
    """
    try:
        # Get sold machine by ID
        sold_machine = db.query(models.SoldMachine).filter(
            models.SoldMachine.id == sold_machine_id
        ).first()
        
        if not sold_machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sold machine with ID '{sold_machine_id}' not found"
            )

        machine = sold_machine.machine

        # Store info for response
        machine_info = {
            "id": str(machine.id),
            "serial_no": sold_machine.serial_no,
            "model_no": machine.model_no,
            "type": machine.machine_type.type
        }

        # Delete all related service report files and parts
        for report in sold_machine.service_reports:
            # Delete service report files from S3 and DB
            for file_record in report.service_report_files:
                try:
                    aws_service = AWSService()
                    aws_service.delete_file(file_record.file_key)
                except Exception as e:
                    print(f"Warning: Failed to delete service report file from S3: {str(e)}")
                db.delete(file_record)
            # Delete service report parts
            for part in report.parts:
                db.delete(part)
            db.delete(report)

        # Delete the sold machine (now safe, all children are deleted)
        db.delete(sold_machine)
        db.commit()

        return {
            "success": True,
            "message": f"Sold machine {machine_info['serial_no']} and all related data deleted successfully",
            "deleted_machine": machine_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete sold machine: {str(e)}"
        )
    




async def delete_machine(
    machine_id: str,
    db: Session
) -> Dict[str, Any]:
    """
    Helper function to delete a machine and all its dependent data (sold machines, service reports, parts, files).
    """
    try:
        # Get the machine by ID
        machine = db.query(models.Machine).filter(models.Machine.id == machine_id).first()
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine with ID '{machine_id}' not found"
            )

        # Gather info for response
        machine_info = {
            "id": str(machine.id),
            "model_no": machine.model_no,
            "part_no": machine.part_no,
            "type": machine.machine_type.type if machine.machine_type else None
        }
        aws_service = AWSService()

        aws_service.delete_file(machine.file_key)

        # Delete all sold machines and their related data
        sold_machines = db.query(models.SoldMachine).filter(models.SoldMachine.machine_id == machine.id).all()
        for sold_machine in sold_machines:
            # Delete all related service reports and their files/parts
            for report in sold_machine.service_reports:
                # Delete service report files from S3 and DB
                for file_record in report.service_report_files:
                    try:
                        
                        aws_service.delete_file(file_record.file_key)
                    except Exception as e:
                        print(f"Warning: Failed to delete service report file from S3: {str(e)}")
                    db.delete(file_record)
                # Delete service report parts
                for part in report.parts:
                    db.delete(part)
                db.delete(report)
            db.delete(sold_machine)

        # Delete all ServiceReportPart records directly linked to this machine (not via sold_machine)
        db.query(models.ServiceReportPart).filter(models.ServiceReportPart.machine_id == machine.id).delete(synchronize_session=False)

        # Finally, delete the machine itself
        db.delete(machine)
        db.commit()

        return {
            "success": True,
            "message": f"Machine {machine_info['model_no']} and all related data deleted successfully",
            "deleted_machine": machine_info
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete machine: {str(e)}"
        )



async def update_machine_details(
    sold_machine_id: str,
    machine_data: Dict[str, Any],
    db: Session,
    file = None
) -> Dict[str, Any]:
    """
    Helper function to update comprehensive machine details including customer info and file
    """
    try:
        # Get machine by ID
        machine = db.query(models.Machine).filter(
            models.Machine.id == machine_id
        ).first()
        
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine with ID '{machine_id}' not found"
            )

        # Get sold machine info if available
        sold_machine = db.query(models.SoldMachine).filter(
            models.SoldMachine.machine_id == machine.id
        ).first()

        # Handle file upload/replacement
        new_file_key = None
        if file:
            try:
                aws_service = AWSService()
                
                # Delete old file if exists
                if machine.file_key:
                    delete_result = aws_service.delete_file(machine.file_key)
                    print(f"Old file deletion result: {delete_result}")
                
                # Upload new file
                upload_result = aws_service.upload_file(
                    file=file.file,
                    folder=f"machines/{machine.serial_no}",
                    content_type=file.content_type,
                    file_name=file.filename
                )
                
                if upload_result["success"]:
                    new_file_key = upload_result["file_key"]
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"File upload failed: {upload_result.get('message', 'Unknown error')}"
                    )
                    
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"File upload failed: {str(e)}"
                )

        # Update machine details
        update_fields = {}
        if machine_data.get("serial_no") is not None:
            # Check if new serial number already exists (excluding current machine)
            existing_machine = db.query(models.Machine).filter(
                models.Machine.serial_no == machine_data["serial_no"],
                models.Machine.id != machine_id
            ).first()
            
            if existing_machine:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Machine with serial number '{machine_data['serial_no']}' already exists"
                )
            update_fields["serial_no"] = machine_data["serial_no"]
            
        if machine_data.get("model_no") is not None:
            update_fields["model_no"] = machine_data["model_no"]
            
        if machine_data.get("part_no") is not None:
            update_fields["part_no"] = machine_data["part_no"]
            
        if machine_data.get("date_of_manufacturing") is not None:
            update_fields["date_of_manufacturing"] = machine_data["date_of_manufacturing"]
            
        if new_file_key:
            update_fields["file_key"] = new_file_key

        # Apply machine updates
        if update_fields:
            for field, value in update_fields.items():
                setattr(machine, field, value)

        # Handle customer details updates
        customer_updates = {}
        customer_fields = ["customer_name", "customer_contact", "customer_email", "customer_address"]
        
        for field in customer_fields:
            if machine_data.get(field) is not None:
                customer_updates[field] = machine_data[field]

        if customer_updates:
            if sold_machine:
                # Update existing sold machine record
                for field, value in customer_updates.items():
                    setattr(sold_machine, field, value)
            else:
                # Create new sold machine record if customer details are provided
                if any(customer_updates.values()):  # Only create if at least one field has a value
                    sold_machine = models.SoldMachine(
                        id=uuid.uuid4(),
                        machine_id=machine.id,
                        user_id=None,  # Will need to be set based on business logic
                        **customer_updates
                    )
                    db.add(sold_machine)

        # Commit all changes
        db.commit()
        db.refresh(machine)
        if sold_machine:
            db.refresh(sold_machine)

        # Get updated machine details and add the required message field
        machine_details = await get_sold_machine_details(sold_machine_id=sold_machine.id, db=db)
        machine_details["message"] = "Machine updated successfully"
        
        return machine_details
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update machine: {str(e)}"
        )







async def get_model_no_by_part_no(part_no: str, db):
    """
    Given a part_no, return the corresponding model_no.
    """
     # Adjust import if needed
    machine = db.query(models.Machine).filter(models.Machine.part_no == part_no).first()
    if machine:
        return machine.model_no
    return None


from sqlalchemy import func

async def get_unique_customers_info(
    db: Session,
    search: Optional[str] = None
) -> CustomerInfoListResponse:
    """
    Get unique customer info from sold_machines table, optionally filtered by search (ilike).
    Uniqueness is based on trimmed, lowercased customer_name.
    """
    query = db.query(
        func.max(func.trim(models.SoldMachine.customer_company)).label("customer_company"),
        func.max(func.trim(models.SoldMachine.customer_name)).label("customer_name"),
        func.max(models.SoldMachine.customer_contact).label("customer_contact"),
        func.max(models.SoldMachine.customer_address).label("customer_address"),
        func.max(models.SoldMachine.customer_email).label("customer_email")
    ).filter(models.SoldMachine.customer_name.isnot(None))
    if search:
        query = query.filter(models.SoldMachine.customer_company.ilike(f"%{search}%"))
    results = (
        query
        .group_by(func.lower(func.trim(models.SoldMachine.customer_company)))
        .all()
    )
    customers = []
    for row in results:
        if row.customer_company and row.customer_company.strip():
            customers.append(CustomerInfo(
                customer_company=row.customer_company.strip(),
                customer_name=row.customer_name.strip(),
                customer_contact=row.customer_contact,
                customer_address=row.customer_address,
                customer_email=row.customer_email
            ))

    return CustomerInfoListResponse(customers=customers)
