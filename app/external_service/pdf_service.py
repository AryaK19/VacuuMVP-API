from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
import os

class PDFService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom styles for the PDF"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1890ff'),
            fontName='Helvetica-Bold'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=12,
            textColor=colors.HexColor('#262626'),
            fontName='Helvetica-Bold',
            backColor=colors.HexColor('#f5f5f5'),
            borderWidth=0,
            leftIndent=6,
            rightIndent=6,
            topPadding=4,
            bottomPadding=4
        ))


    def generate_service_report_pdf(self, report_data) -> BytesIO:
        """Generate PDF for service report"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        # Build the PDF content
        content = []
        
        # Title
        title = Paragraph("Service Report", self.styles['CustomTitle'])
        content.append(title)
        content.append(Spacer(1, 15))
        
        # Basic Information
        content.append(Paragraph("Basic Information", self.styles['SectionHeader']))
        content.append(Spacer(1, 5))
        
        basic_info_data = [
            ['Service Type:', report_data.get('service_type_name', 'N/A')],
            ['Service Person:', report_data.get('service_person_name', 'Not specified')],
            ['Created By:', report_data.get('user_name', 'N/A')],
            ['Email:', report_data.get('user_email', 'N/A')],
            ['Created At:', self.format_date(report_data.get('created_at'))],
            ['Updated At:', self.format_date(report_data.get('updated_at'))]
        ]
        
        basic_info_table = Table(basic_info_data, colWidths=[1.8*inch, 4.2*inch])
        basic_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        content.append(basic_info_table)
        content.append(Spacer(1, 12))
        
        # Customer Information
        if report_data.get('customer_info'):
            content.append(Paragraph("Customer Information", self.styles['SectionHeader']))
            content.append(Spacer(1, 5))
            
            customer_info = report_data['customer_info']
            customer_data = [
                ['Customer Name:', customer_info.get('customer_name', 'Not specified')],
                ['Contact:', customer_info.get('customer_contact', 'Not specified')],
                ['Email:', customer_info.get('customer_email', 'Not specified')],
                ['Address:', customer_info.get('customer_address', 'Not specified')],
                ['Purchase Date:', self.format_date(customer_info.get('sold_date'))]
            ]
            
            customer_table = Table(customer_data, colWidths=[1.8*inch, 4.2*inch])
            customer_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            content.append(customer_table)
            content.append(Spacer(1, 12))
        
        # Machine Information
        if report_data.get('machine_info'):
            content.append(Paragraph("Machine Information", self.styles['SectionHeader']))
            content.append(Spacer(1, 5))
            
            machine_info = report_data['machine_info']
            machine_data = [
                ['Serial No:', machine_info.get('serial_no', 'Not specified')],
                ['Model No:', machine_info.get('model_no', 'Not specified')],
                ['Part No:', machine_info.get('part_no', 'Not specified')],
                ['Type:', machine_info.get('type_name', 'Not specified')],
                ['Manufacturing Date:', self.format_manufacturing_date(machine_info.get('date_of_manufacturing'))]
            ]
            
            machine_table = Table(machine_data, colWidths=[1.8*inch, 4.2*inch])
            machine_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            
            content.append(machine_table)
            content.append(Spacer(1, 10))
        
        # --- PAGE BREAK HERE ---
        content.append(PageBreak())
        
        # Service Parts
        if report_data.get('parts') and len(report_data['parts']) > 0:
            content.append(Paragraph("Service Parts", self.styles['SectionHeader']))
            content.append(Spacer(1, 5))
            
            parts_data = [['Serial No', 'Model No', 'Part No', 'Qty']]
            
            for part in report_data['parts']:
                parts_data.append([
                    part.get('machine_serial_no', 'N/A'),
                    part.get('machine_model_no', 'N/A'),
                    part.get('machine_part_no', 'N/A'),
                    str(part.get('quantity', 0))
                ])
            
            # Set the table width to match other tables (1.8 + 4.2 = 6.0 inches)
            parts_table = Table(parts_data, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 0.6*inch])
            parts_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#212529')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ]))
            
            content.append(parts_table)
            content.append(Spacer(1, 10))
        
        # Problem and Solution
        content.append(Paragraph("Problem & Solution", self.styles['SectionHeader']))
        content.append(Spacer(1, 5))
        
        problem_text = report_data.get('problem', 'No problem description provided')
        solution_text = report_data.get('solution', 'No solution provided')
        
        # Truncate long text to fit on one page
        if len(problem_text) > 150:
            problem_text = problem_text[:150] + "..."
        if len(solution_text) > 150:
            solution_text = solution_text[:150] + "..."
        
        problem_solution_data = [
            ['Problem:', problem_text],
            ['Solution:', solution_text]
        ]
        
        problem_solution_table = Table(problem_solution_data, colWidths=[1.2*inch, 4.8*inch])
        problem_solution_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        content.append(problem_solution_table)
        
        # Footer
        content.append(Spacer(1, 15))
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#6c757d'),
            alignment=TA_RIGHT
        )
        footer_text = f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        footer = Paragraph(footer_text, footer_style)
        content.append(footer)
        
        # Build PDF
        doc.build(content)
        buffer.seek(0)
        return buffer
    def format_date(self, date_string):
        """Format date string for PDF"""
        if not date_string:
            return 'Not specified'
        try:
            if isinstance(date_string, str):
                date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            else:
                date_obj = date_string
            return date_obj.strftime('%B %d, %Y at %I:%M %p')
        except:
            return str(date_string)
    
    def format_manufacturing_date(self, date_string):
        """Format manufacturing date for PDF"""
        if not date_string:
            return 'Not specified'
        try:
            if isinstance(date_string, str):
                date_obj = datetime.fromisoformat(date_string)
            else:
                date_obj = date_string
            return date_obj.strftime('%B %d, %Y')
        except:
            return str(date_string)
    
    def is_image_file(self, file_key):
        """Check if file is an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return any(file_key.lower().endswith(ext) for ext in image_extensions)