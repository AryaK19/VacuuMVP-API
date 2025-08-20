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
from app.schema.service_report import (
 
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
        sold_machine = None
        if service_report_data.get("sold_machine_id"):
            sold_machine = db.query(models.SoldMachine).filter(
                models.SoldMachine.id == service_report_data["sold_machine_id"]
            ).first()
            
            if not sold_machine:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sold machine not found"
                )


        # Create service report
        new_service_report = models.ServiceReport(
            id=uuid.uuid4(),
            user_id=user_id,
            sold_machine_id=service_report_data.get("sold_machine_id"),
            problem=service_report_data.get("problem"),
            solution=service_report_data.get("solution"),
            service_person_name=service_report_data.get("service_person_name"),
            service_type_id=service_report_data["service_type_id"]
        )


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
    Helper function to get service reports for a specific user.
    Search works across service_person_name, serial/model/part no (from sold_machine/machine), and service type.
    """
    # Get user and check admin
    user = db.query(models.User).filter(models.User.id == user_id).first()
    is_admin = False
    if user and user.role:
        is_admin = user.role.role_name.lower() == "admin"

    # Start query with necessary joins for search
    query = db.query(models.ServiceReport) \
        .outerjoin(models.SoldMachine, models.ServiceReport.sold_machine_id == models.SoldMachine.id) \
        .outerjoin(models.Machine, models.SoldMachine.machine_id == models.Machine.id) \
        .outerjoin(models.ServiceType, models.ServiceReport.service_type_id == models.ServiceType.id)

    # Filter by user_id only if not admin
    if not is_admin:
        query = query.filter(models.ServiceReport.user_id == user_id)

    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.ServiceReport.service_person_name.ilike(search_term)) |
            (models.ServiceReport.problem.ilike(search_term)) |
            (models.ServiceReport.solution.ilike(search_term)) |
            (models.SoldMachine.serial_no.ilike(search_term)) |
            (models.Machine.model_no.ilike(search_term)) |
            (models.Machine.part_no.ilike(search_term)) |
            (models.ServiceType.service_type.ilike(search_term))
        )

    # Count total items for pagination
    total_items = query.distinct().count()

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
    # Get sold_machine and machine
    sold_machine = service_report.sold_machine
    machine = sold_machine.machine if sold_machine else None

    return {
        "id": str(service_report.id),
        "user_id": str(service_report.user_id),
        "machine_id": str(machine.id) if machine.id else None,
        "sold_machine_id": str(sold_machine.id) if sold_machine else None,
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
            "id": str(machine.id),
            "serial_no": sold_machine.serial_no if sold_machine else None,
            "model_no": machine.model_no if machine else None,
            "part_no": machine.part_no if machine else None
        } if machine else None,
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
            for file in service_report.service_report_files
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

        sold_machine = db.query(models.SoldMachine).filter(
            models.SoldMachine.serial_no == serial_no
        ).first()



        machine = db.query(models.Machine).join(
            models.Type, models.Machine.type_id == models.Type.id
        ).filter(
            models.Machine.id == sold_machine.machine_id if sold_machine else None,
            models.Type.type.ilike('%pump%')
        ).first()
        
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Machine with serial number '{serial_no}' not found"
            )
        
    

        
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
                "serial_no": sold_machine.serial_no if sold_machine else None,
                "model_no": machine.model_no,
                "part_no": machine.part_no,
                "sold_machine_id": str(sold_machine.id) if sold_machine else None,
                "date_of_manufacturing": sold_machine.date_of_manufacturing,
                "customer_name": sold_machine.customer_name if sold_machine else None,
                "customer_company": sold_machine.customer_company if sold_machine else None,
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
            machine_id=customer_data["machine_id"],
            customer_name=customer_data["customer_name"],
            customer_company=customer_data.get("customer_company"),
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
    Generate a PDF service report matching the web layout, with logo at top right.
    """
 
    try:
        def clean_text(val):
            if not val:
                return "N/A"
            return str(val).strip().replace('\n', ' ').replace('\r', ' ')

        result = await get_service_report_detail(report_id=report_id, db=db)
        

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        normal = styles['Normal']
        bold = styles['Heading4']

        # Add a smaller font style for the address
        small_address = ParagraphStyle(
            'small_address',
            parent=normal,
            fontSize=8,   # or any size you prefer
            leading=9
        )

        story = []

        # Add logo and title in a table for alignment
        from reportlab.platypus import Image as RLImage
        import os

        logo_path = os.path.join(os.path.dirname(__file__), '..', 'public', 'vacuubrand-logo-removebg.png')
        # Make sure the path is absolute and normalized
        logo_path = os.path.abspath(logo_path)
        try:
            logo = RLImage(logo_path, width=90, height=15)
        except Exception:
            logo = None

        title_para = Paragraph("Service Report Details", styles['Title'])
        if logo:
            header_table = Table(
                [[title_para, logo]],
                colWidths=[370, 110]
            )
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ]))
            story.append(header_table)
        else:
            story.append(title_para)
        story.append(Spacer(1, 12))

        # Service Report Details Table
        details_data = [
            ["Service Type", Paragraph(f"<b>{result.service_type_name or 'N/A'}</b>", normal),"Distributor", Paragraph(f"<b>{result.user_name or 'N/A'}</b>", normal) ],
            ["Service Person", clean_text(result.service_person_name or "N/A"), "Date", result.created_at.strftime("%d-%m-%Y") if result.created_at else "N/A"],
            ["Problem", clean_text(result.problem)],
            ["Solution", clean_text(result.solution)]
        ]
        details_table = Table(details_data, colWidths=[80, 150, 80, 150])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 16))

        # Customer Information Header
        story.append(Paragraph("Customer Information", bold))
        story.append(Spacer(1, 6))

        # Customer Info Table
        customer_data = [
            ["Customer", clean_text(result.customer_info.customer_company), "Contact Person", clean_text(result.customer_info.customer_name)],
            ["Email", clean_text(result.customer_info.customer_email), "Contact Number", clean_text(result.customer_info.customer_contact)]
        ]
        customer_table = Table(customer_data, colWidths=[80, 150, 80, 150])
        customer_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
        ]))

        # Address row: 2 columns, same total width as customer_table (80+150+80+150=460)
        address_text = (result.customer_info.customer_address or "N/A").strip().replace('\n', '<br/>')
        customer_address = [["Address", Paragraph(address_text, small_address)]]
        customer_address_table = Table(customer_address, colWidths=[80, 380])
        customer_address_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
        ]))

        story.append(customer_table)
        story.append(customer_address_table)
        story.append(Spacer(1, 16))

        # Machine Information Header
        story.append(Paragraph("Machine Information", bold))
        story.append(Spacer(1, 6))

        # Machine Info Table
        machine_data = [
            ["Serial No", result.machine_info.serial_no or "N/A", "Model No", result.machine_info.model_no or "N/A"],
            ["Part No", result.machine_info.part_no or "N/A", "Type", result.machine_info.type_name or "N/A"],
            
        ]

        machine_data_manufacturing = [
            ["Manufacturing Date", str(result.machine_info.date_of_manufacturing) if result.machine_info.date_of_manufacturing else "Not specified"]
        ]
        machine_data_manufacturing_table = Table(machine_data_manufacturing, colWidths=[80, 380])
        machine_data_manufacturing_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
        ]))
        machine_table = Table(machine_data, colWidths=[80, 150, 80, 150])
        machine_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            # Add faint grid
            ('GRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
        ]))
        story.append(machine_table)
        story.append(machine_data_manufacturing_table)
        story.append(Spacer(1, 16))

        # Service Parts Header
        story.append(Paragraph("Service Parts", bold))
        story.append(Spacer(1, 6))

        # Service Parts Table
        parts_data = [[ "Part No", "Model No",  "Quantity"]]
        for part_info in result.parts:
            parts_data.append([
                part_info.machine_part_no or "N/A",
                part_info.machine_model_no or "N/A",
                str(part_info.quantity)
            ])


        parts_table = Table(parts_data, colWidths=[70, 120, 80, 50, 110])
        parts_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(parts_table)
        story.append(Spacer(1, 16))

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
            Role.role_name.label('user_role'),
            User.name.label('user_name'),
            User.email.label('user_email'),
            ServiceType.service_type.label('service_type_name'),
            Machine.model_no.label('machine_model_no'),
            Machine.part_no.label('machine_part_no'),
            Type.type.label('machine_type_name'),
            SoldMachine.serial_no.label('machine_serial_no'),
            SoldMachine.date_of_manufacturing.label('machine_manufacturing_date'),
            SoldMachine.customer_name.label('customer_name'),
            SoldMachine.customer_company.label('customer_company'),
            SoldMachine.customer_email.label('customer_email'),
            SoldMachine.customer_contact.label('customer_contact'),
            SoldMachine.customer_address.label('customer_address'),
            SoldMachine.created_at.label('sold_date')
        ).join(User, ServiceReport.user_id == User.id)\
         .join(Role, User.role_id == Role.id)\
         .join(ServiceType, ServiceReport.service_type_id == ServiceType.id)\
         .outerjoin(SoldMachine, SoldMachine.id == ServiceReport.sold_machine_id)\
         .outerjoin(Machine, SoldMachine.machine_id == Machine.id)\
         .outerjoin(Type, Machine.type_id == Type.id)\
         .filter(ServiceReport.id == report_id)\
         .first()
        
        if not result:
            raise Exception("Service report not found")
        
        (report, user_role , user_name, user_email, service_type_name, 
         machine_model_no, machine_part_no,  machine_type_name, machine_serial_no,
         machine_manufacturing_date, 
         customer_name, customer_company, customer_email, customer_contact, 
         customer_address, sold_date) = result

        if user_role == "admin":
            display_name = "BRAND Scientific Equipment PVT. LTD."
        else:
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
                customer_company=customer_company,
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
                url_result = aws_service.get_presigned_url(file_record.file_key, expires_in=3600)
                if url_result["success"]:
                    file_url = url_result["url"]
                else:
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
                continue
        
        # Process parts information
        parts_info = []
        for part_result in report_parts:
            part_record, part_model_no, part_part_no = part_result
            part_info = ServiceReportPartInfo(
                id=str(part_record.id),
                machine_serial_no=None,  # Serial no is not in Machine anymore
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