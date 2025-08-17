from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from typing import Optional, Dict, Any, List
import uuid

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
import os

from app.db import models
from app.external_service.aws_service import AWSService

from sqlalchemy import desc, asc,  and_



from app.db.models import ServiceReport, User, ServiceType, Machine, ServiceReportFiles, ServiceReportPart, Type, SoldMachine, Role
from app.schema.dashboard import (
 
    ServiceReportDetailResponse, 
    ServiceReportFileInfo,
    ServiceReportPartInfo,
    ServiceReportMachineInfo,
    ServiceReportCustomerInfo,

)


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
        machine = db.query(models.Machine).join(
            models.Type, models.Machine.type_id == models.Type.id
        ).filter(
            models.Machine.serial_no == serial_no,
            models.Type.type.ilike('%pump%')
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


async def get_service_report_detail_pdf(
    db: Session,
    report_id: str
) -> BytesIO:
    """
    Generate a PDF service report with professional formatting matching the company template.
    """
    try:
        # Get service report data (reuse existing function logic)
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
         .outerjoin(SoldMachine, SoldMachine.machine_id == ServiceReport.machine_id)\
         .filter(ServiceReport.id == report_id)\
         .first()
        
        if not result:
            raise Exception("Service report not found")
        
        (report, user_name, user_email, service_type_name, 
         machine_serial_no, machine_model_no, machine_part_no, 
         machine_manufacturing_date, machine_type_name,
         customer_name, customer_email, customer_contact, 
         customer_address, sold_date) = result

        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)

        # Define styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.black
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            textColor=colors.black
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )

        # Build PDF content
        story = []

        # Header with company info
        header_data = [
            ['BRAND Scientific Equipment Pvt. Ltd.', '', 'BRAND'],
            ['304, 3rd Floor - G - Wing', '', ''],
            ['Dolphin, Himmatinagar Business Park', '', ''],
            ['Powai, Mumbai - 400076 (INDIA)', '', ''],
            ['', '', ''],
            ['Tel: +91 22 42957730', '', '']
        ]
        
        header_table = Table(header_data, colWidths=[4*inch, 1*inch, 1.5*inch])
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 20))

        # Service Report Title
        story.append(Paragraph("SERVICE REPORT", title_style))
        story.append(Spacer(1, 10))

        # Report details table
        report_details = [
            [f"Ref No: {report_id[:8].upper()}", f"Date: {report.created_at.strftime('%d/%m/%Y')}"]
        ]
        
        details_table = Table(report_details, colWidths=[3*inch, 3*inch])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 20))

        # Customer Information
        story.append(Paragraph("Customer Name:", heading_style))
        story.append(Paragraph(customer_name or "N/A", normal_style))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Address:", heading_style))
        story.append(Paragraph(customer_address or "N/A", normal_style))
        story.append(Spacer(1, 15))

        # Contact Information Table
        contact_data = [
            ['Contact Person:', '', 'Designation:', ''],
            ['Contact No.:', customer_contact or 'N/A', 'Email:', customer_email or 'N/A']
        ]
        
        contact_table = Table(contact_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        contact_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(contact_table)
        story.append(Spacer(1, 20))

        # Nature of Service checkboxes
        service_data = [
            ['Nature of Service:', 'Paid ☐', 'Health Check ☐', 'Warranty ☐', 'AMC ☐']
        ]
        
        # Mark the appropriate service type
        if service_type_name:
            service_lower = service_type_name.lower()
            for i, item in enumerate(service_data[0][1:], 1):
                service_name = item.split(' ')[0].lower()
                if service_name in service_lower:
                    service_data[0][i] = item.replace('☐', '☑')
        
        service_table = Table(service_data, colWidths=[1.8*inch, 1*inch, 1.2*inch, 1*inch, 1*inch])
        service_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(service_table)
        story.append(Spacer(1, 20))

        # Contamination Free Declaration
        contamination_data = [
            ['Contamination Free Declaration Submitted', 'YES', 'NO', 'NA']
        ]
        
        contamination_table = Table(contamination_data, colWidths=[3*inch, 0.8*inch, 0.8*inch, 0.8*inch])
        contamination_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        story.append(contamination_table)
        story.append(Spacer(1, 30))

        # Product Details
        story.append(Paragraph("Product Details", heading_style))
        story.append(Spacer(1, 10))

        product_data = [
            ['Model No:', machine_model_no or 'N/A', 'Sr. No. / Mfg:', machine_serial_no or 'N/A']
        ]
        
        product_table = Table(product_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 1.5*inch])
        product_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(product_table)
        story.append(Spacer(1, 20))

        # Complaint section
        story.append(Paragraph("Complaint:", heading_style))
        story.append(Paragraph(report.problem or "No complaint specified", normal_style))
        story.append(Spacer(1, 100))  # Space for writing

        # Observation/Action section
        story.append(Paragraph("Observation / Action:", heading_style))
        story.append(Paragraph(report.solution or "No action specified", normal_style))
        story.append(Spacer(1, 100))  # Space for writing

        # Service person name
        if report.service_person_name:
            story.append(Spacer(1, 50))
            story.append(Paragraph(f"Service Engineer: {report.service_person_name}", normal_style))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
        
    except Exception as e:
        print(f"PDF generation error: {str(e)}")
        raise Exception(f"Error generating PDF: {str(e)}")

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