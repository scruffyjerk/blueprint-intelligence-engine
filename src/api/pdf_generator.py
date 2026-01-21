"""
PDF Report Generator for Takeoff.ai

Generates professional PDF estimates for construction projects.
"""

from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


class PDFReportGenerator:
    """Generates professional PDF reports for construction estimates."""
    
    # Brand colors
    PRIMARY_COLOR = colors.HexColor('#10B981')  # Green
    SECONDARY_COLOR = colors.HexColor('#1F2937')  # Dark gray
    LIGHT_GRAY = colors.HexColor('#F3F4F6')
    BORDER_COLOR = colors.HexColor('#E5E7EB')
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=self.SECONDARY_COLOR,
            spaceAfter=20,
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportSection',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=self.SECONDARY_COLOR,
            spaceBefore=20,
            spaceAfter=10,
            borderPadding=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportSubHeader',
            parent=self.styles['Heading3'],
            fontSize=11,
            textColor=self.SECONDARY_COLOR,
            spaceBefore=10,
            spaceAfter=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.SECONDARY_COLOR,
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportSmall',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            spaceAfter=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='ReportFooter',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER
        ))
    
    def generate_report(
        self,
        project_name: str,
        rooms: List[Dict[str, Any]],
        materials: List[Dict[str, Any]],
        cost_breakdown: Dict[str, float],
        tier_comparisons: List[Dict[str, Any]],
        selected_tier: str = 'standard',
        total_area: float = 0,
        contingency_percent: float = 10,
        filename: str = 'blueprint.jpg',
        labor_availability: str = 'average'
    ) -> BytesIO:
        """
        Generate a PDF report for the construction estimate.
        
        Returns: BytesIO buffer containing the PDF
        """
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        story = []
        
        # Header
        story.extend(self._build_header(project_name, filename))
        
        # Project Summary
        story.extend(self._build_summary(
            total_area=total_area,
            room_count=len(rooms),
            selected_tier=selected_tier,
            grand_total=cost_breakdown.get('grand_total', 0),
            labor_availability=labor_availability
        ))
        
        # Room Breakdown
        story.extend(self._build_room_breakdown(rooms))
        
        # Cost Estimate Table
        story.extend(self._build_cost_table(materials, cost_breakdown, contingency_percent))
        
        # Quality Tier Comparison
        story.extend(self._build_tier_comparison(tier_comparisons, selected_tier))
        
        # Footer/Disclaimer
        story.extend(self._build_footer())
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _build_header(self, project_name: str, filename: str) -> List:
        """Build the report header."""
        elements = []
        
        # Logo/Brand
        elements.append(Paragraph(
            '<font color="#10B981"><b>Takeoff.ai</b></font>',
            ParagraphStyle(
                name='Brand',
                fontSize=20,
                textColor=self.PRIMARY_COLOR,
                spaceAfter=5
            )
        ))
        
        elements.append(Paragraph(
            'AI-Powered Construction Estimator',
            self.styles['ReportSmall']
        ))
        
        elements.append(Spacer(1, 20))
        
        # Title
        elements.append(Paragraph(
            f'<b>Construction Cost Estimate</b>',
            self.styles['ReportTitle']
        ))
        
        # Project info
        elements.append(Paragraph(
            f'<b>Project:</b> {project_name}',
            self.styles['ReportBody']
        ))
        
        elements.append(Paragraph(
            f'<b>Source File:</b> {filename}',
            self.styles['ReportBody']
        ))
        
        elements.append(Paragraph(
            f'<b>Generated:</b> {datetime.now().strftime("%B %d, %Y at %I:%M %p")}',
            self.styles['ReportBody']
        ))
        
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=self.BORDER_COLOR,
            spaceAfter=20
        ))
        
        return elements
    
    def _build_summary(
        self,
        total_area: float,
        room_count: int,
        selected_tier: str,
        grand_total: float,
        labor_availability: str = 'average'
    ) -> List:
        """Build the project summary section."""
        elements = []
        
        elements.append(Paragraph('Project Summary', self.styles['ReportSection']))
        
        tier_labels = {
            'budget': 'Budget',
            'standard': 'Standard',
            'premium': 'Premium',
            'luxury': 'Luxury'
        }
        
        labor_labels = {
            'low': 'Low (Shortage +15%)',
            'average': 'Average',
            'high': 'High (Surplus -10%)'
        }
        
        summary_data = [
            ['Total Area', f'{total_area:,.0f} sq ft'],
            ['Rooms Detected', str(room_count)],
            ['Quality Tier', tier_labels.get(selected_tier, 'Standard')],
            ['Labor Availability', labor_labels.get(labor_availability, 'Average')],
            ['Estimated Total', f'${grand_total:,.2f}'],
        ]
        
        table = Table(summary_data, colWidths=[2*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), self.LIGHT_GRAY),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.SECONDARY_COLOR),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTSIZE', (1, -1), (1, -1), 14),
            ('TEXTCOLOR', (1, -1), (1, -1), self.PRIMARY_COLOR),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_room_breakdown(self, rooms: List[Dict[str, Any]]) -> List:
        """Build the room breakdown table."""
        elements = []
        
        elements.append(Paragraph('Room Breakdown', self.styles['ReportSection']))
        
        # Table header
        header = ['Room', 'Dimensions', 'Area', 'Confidence']
        data = [header]
        
        for room in rooms:
            dimensions = room.get('dimensions', {})
            width = dimensions.get('width', 0)
            length = dimensions.get('length', 0)
            
            if width > 0 and length > 0:
                dim_str = f"{length:.0f}' × {width:.0f}'"
            else:
                dim_str = 'Estimated'
            
            area = room.get('area', 0)
            confidence = room.get('confidence', 0.5)
            
            if confidence >= 0.8:
                conf_str = 'High'
            elif confidence >= 0.6:
                conf_str = 'Medium'
            else:
                conf_str = 'Low'
            
            data.append([
                room.get('name', 'Unknown'),
                dim_str,
                f"{area:,.0f} sq ft",
                conf_str
            ])
        
        table = Table(data, colWidths=[2.5*inch, 1.5*inch, 1.25*inch, 1*inch])
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            # Body
            ('TEXTCOLOR', (0, 1), (-1, -1), self.SECONDARY_COLOR),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.LIGHT_GRAY]),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_cost_table(
        self,
        materials: List[Dict[str, Any]],
        cost_breakdown: Dict[str, float],
        contingency_percent: float
    ) -> List:
        """Build the cost estimate table."""
        elements = []
        
        elements.append(Paragraph('Cost Estimate', self.styles['ReportSection']))
        
        # Group materials by category
        grouped = {}
        for item in materials:
            category = item.get('category', 'Other')
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(item)
        
        # Table header
        header = ['Material', 'Qty', 'Unit Cost', 'Materials', 'Labor', 'Total']
        data = [header]
        
        for category, items in grouped.items():
            # Category row
            data.append([category.upper(), '', '', '', '', ''])
            
            for item in items:
                data.append([
                    f"  {item.get('name', 'Unknown')}",
                    f"{item.get('quantity', 0)} {item.get('unit', '')}",
                    f"${item.get('unit_cost', 0):,.2f}",
                    f"${item.get('material_cost', 0):,.2f}",
                    f"${item.get('labor_cost', 0):,.2f}",
                    f"${item.get('total_cost', 0):,.2f}",
                ])
        
        col_widths = [2.25*inch, 0.9*inch, 0.85*inch, 0.95*inch, 0.95*inch, 0.95*inch]
        table = Table(data, colWidths=col_widths)
        
        # Find category row indices
        category_rows = []
        for i, row in enumerate(data):
            if row[1] == '' and row[2] == '' and i > 0:
                category_rows.append(i)
        
        style_commands = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('ALIGN', (1, 0), (-1, 0), 'RIGHT'),
            # Body
            ('TEXTCOLOR', (0, 1), (-1, -1), self.SECONDARY_COLOR),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
        ]
        
        # Style category rows
        for row_idx in category_rows:
            style_commands.extend([
                ('BACKGROUND', (0, row_idx), (-1, row_idx), self.LIGHT_GRAY),
                ('FONTNAME', (0, row_idx), (0, row_idx), 'Helvetica-Bold'),
                ('FONTSIZE', (0, row_idx), (0, row_idx), 8),
                ('SPAN', (0, row_idx), (-1, row_idx)),
            ])
        
        table.setStyle(TableStyle(style_commands))
        elements.append(table)
        
        # Summary totals
        elements.append(Spacer(1, 10))
        
        summary_data = [
            ['Materials Subtotal', f"${cost_breakdown.get('materials_subtotal', 0):,.2f}"],
            ['Labor Subtotal', f"${cost_breakdown.get('labor_subtotal', 0):,.2f}"],
            ['Subtotal', f"${cost_breakdown.get('subtotal', 0):,.2f}"],
            [f'Contingency ({contingency_percent:.0f}%)', f"${cost_breakdown.get('contingency_amount', 0):,.2f}"],
            ['Grand Total', f"${cost_breakdown.get('grand_total', 0):,.2f}"],
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), self.SECONDARY_COLOR),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            # Grand total row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('TEXTCOLOR', (1, -1), (1, -1), self.PRIMARY_COLOR),
            ('LINEABOVE', (0, -1), (-1, -1), 1, self.BORDER_COLOR),
        ]))
        
        # Right-align the summary table
        summary_wrapper = Table([[summary_table]], colWidths=[7*inch])
        summary_wrapper.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
        ]))
        
        elements.append(summary_wrapper)
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _build_tier_comparison(
        self,
        tier_comparisons: List[Dict[str, Any]],
        selected_tier: str
    ) -> List:
        """Build the quality tier comparison section."""
        elements = []
        
        elements.append(Paragraph('Quality Tier Comparison', self.styles['ReportSection']))
        
        tier_info = {
            'budget': ('Budget', 'Cost-effective materials'),
            'standard': ('Standard', 'Quality mid-range'),
            'premium': ('Premium', 'High-end finishes'),
            'luxury': ('Luxury', 'Top-tier everything'),
        }
        
        header = ['Tier', 'Description', 'Estimated Total']
        data = [header]
        
        for tier in tier_comparisons:
            tier_name = tier.get('tier', 'standard')
            label, desc = tier_info.get(tier_name, ('Unknown', ''))
            total = tier.get('grand_total', 0)
            
            # Mark selected tier
            if tier_name == selected_tier:
                label = f"✓ {label}"
            
            data.append([label, desc, f"${total:,.2f}"])
        
        table = Table(data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch])
        
        # Find selected tier row
        selected_row = None
        for i, tier in enumerate(tier_comparisons):
            if tier.get('tier') == selected_tier:
                selected_row = i + 1  # +1 for header
                break
        
        style_commands = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), self.PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            # Body
            ('TEXTCOLOR', (0, 1), (-1, -1), self.SECONDARY_COLOR),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, self.BORDER_COLOR),
        ]
        
        # Highlight selected tier
        if selected_row:
            style_commands.extend([
                ('BACKGROUND', (0, selected_row), (-1, selected_row), colors.HexColor('#D1FAE5')),
                ('FONTNAME', (0, selected_row), (-1, selected_row), 'Helvetica-Bold'),
            ])
        
        table.setStyle(TableStyle(style_commands))
        elements.append(table)
        elements.append(Spacer(1, 30))
        
        return elements
    
    def _build_footer(self) -> List:
        """Build the report footer with disclaimer."""
        elements = []
        
        elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=self.BORDER_COLOR,
            spaceBefore=20,
            spaceAfter=15
        ))
        
        disclaimer = """
        <b>Disclaimer:</b> This estimate is generated by AI-powered analysis and is intended for 
        planning purposes only. Actual costs may vary based on local labor rates, material availability, 
        site conditions, and other factors. We recommend obtaining quotes from licensed contractors 
        before making final decisions. This estimate does not include permits, design fees, or 
        unforeseen conditions.
        """
        
        elements.append(Paragraph(disclaimer.strip(), self.styles['ReportSmall']))
        
        elements.append(Spacer(1, 15))
        
        elements.append(Paragraph(
            'Generated by Takeoff.ai — AI-Powered Construction Estimator',
            self.styles['ReportFooter']
        ))
        
        elements.append(Paragraph(
            'https://takeoff.ai',
            self.styles['ReportFooter']
        ))
        
        return elements
