import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

# Brand Colors
PRIMARY_RED = colors.HexColor('#E5322D')
DARK_TEXT = colors.HexColor('#1A1D20')
MUTED_TEXT = colors.HexColor('#666666')
LIGHT_BG = colors.HexColor('#F8F9FB')
BORDER_COLOR = colors.HexColor('#E4E4E4')
SUCCESS_GREEN = colors.HexColor('#15803D')
WARNING_AMBER = colors.HexColor('#D97706')

class NumberedCanvas(canvas.Canvas):
    """Custom canvas that computes total page count dynamically for 'Page X of Y'."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED_TEXT)
        
        # Header (on pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "SCHOLARPROOF — APPLICATION PRE-CHECK REPORT")
            self.setStrokeColor(BORDER_COLOR)
            self.setLineWidth(0.5)
            self.line(54, 742, letter[0] - 54, 742)

        # Running Footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 36, page_str)
        self.drawString(54, 36, "Confidential Pre-Audit Report • ScholarProof Prototype")
        self.setStrokeColor(BORDER_COLOR)
        self.setLineWidth(0.5)
        self.line(54, 48, letter[0] - 54, 48)
        self.restoreState()

def generate_pdf_report(case_data, output_path):
    """
    Generates a high-quality ScholarProof Pre-Check PDF report using ReportLab.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY_RED
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=MUTED_TEXT
    )
    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=DARK_TEXT,
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=DARK_TEXT
    )
    body_muted = ParagraphStyle(
        'BodyMuted',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=MUTED_TEXT
    )
    badge_green = ParagraphStyle(
        'BadgeGreen',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=SUCCESS_GREEN
    )
    badge_amber = ParagraphStyle(
        'BadgeAmber',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=WARNING_AMBER
    )
    badge_red = ParagraphStyle(
        'BadgeRed',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=PRIMARY_RED
    )

    # Replace unicode rupee symbol with Rs. to prevent missing font glyphs in ReportLab
    def sanitize_pdf_text(t):
        if not t: return ""
        return str(t).replace('₹', 'Rs. ')

    ref_no = sanitize_pdf_text(case_data.get("referenceNumber", "SP-2026-DEMO"))
    checked_time = sanitize_pdf_text(case_data.get("timestamp", datetime.now().strftime("%d %B %Y, %H:%M IST")))
    scholarship = case_data.get("scholarship", {})
    applicant = case_data.get("applicant", {})
    readiness = case_data.get("readiness", {})
    checks_passed = case_data.get("checksPassed", [])
    needs_attention = case_data.get("needsAttention", [])
    missing_docs = case_data.get("missingDocuments", [])
    matrix = case_data.get("comparisonMatrix", [])

    story = []

    # 1. HEADER SECTION
    header_table_data = [
        [
            Paragraph("<b>SCHOLARPROOF</b><br/><font size=8 color='#666666'>APPLICATION PRE-CHECK REPORT</font>", title_style),
            Paragraph(f"<b>Reference:</b> {ref_no}<br/><b>Date:</b> {checked_time}<br/><b>Scheme:</b> {sanitize_pdf_text(scholarship.get('name', 'General Audit'))}", subtitle_style)
        ]
    ]
    header_table = Table(header_table_data, colWidths=[3.2 * inch, 3.8 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_RED, spaceBefore=4, spaceAfter=14))

    # 2. READINESS SCORE CARD
    score_val = readiness.get("score", 0)
    score_label = sanitize_pdf_text(readiness.get("status_label", "Evaluating"))
    score_summary = sanitize_pdf_text(readiness.get("summary_text", ""))

    score_box_data = [
        [
            Paragraph(f"<font size=28 color='#E5322D'><b>{score_val}%</b></font><br/><font size=9 color='#666666'>READINESS SCORE</font>", styles['Normal']),
            Paragraph(f"<b>Status: {score_label}</b><br/>{score_summary}<br/><font size=7 color='#888888'>*This score is an automated pre-check estimation, not an official scholarship decision.</font>", body_style)
        ]
    ]
    score_box = Table(score_box_data, colWidths=[2.0 * inch, 5.0 * inch])
    score_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
    ]))
    story.append(score_box)
    story.append(Spacer(1, 14))

    # 3. APPLICANT & SCHEME SUMMARY
    story.append(Paragraph("APPLICANT & SCHEME CONFIGURATION", h2_style))
    summary_data = [
        [
            Paragraph("<b>Applicant Name:</b>", body_muted),
            Paragraph(sanitize_pdf_text(applicant.get("full_name") or "Not provided"), body_style),
            Paragraph("<b>Configured Scheme:</b>", body_muted),
            Paragraph(sanitize_pdf_text(scholarship.get("name") or "General Audit"), body_style),
        ],
        [
            Paragraph("<b>Institute:</b>", body_muted),
            Paragraph(sanitize_pdf_text(applicant.get("institute") or "Not provided"), body_style),
            Paragraph("<b>Scheme Income Ceiling:</b>", body_muted),
            Paragraph(f"Rs. {scholarship.get('income_limit', 0):,.0f}" if scholarship.get('income_limit') else "N/A", body_style),
        ],
        [
            Paragraph("<b>Course / Year:</b>", body_muted),
            Paragraph(sanitize_pdf_text(f"{applicant.get('course', 'N/A')} ({applicant.get('academic_year', 'Current')})"), body_style),
            Paragraph("<b>Minimum Marks:</b>", body_muted),
            Paragraph(f"{scholarship.get('minimum_percentage', 0)}%" if scholarship.get('minimum_percentage') else "N/A", body_style),
        ],
        [
            Paragraph("<b>Date of Birth:</b>", body_muted),
            Paragraph(sanitize_pdf_text(applicant.get("dob") or "N/A"), body_style),
            Paragraph("<b>Category:</b>", body_muted),
            Paragraph(sanitize_pdf_text(applicant.get("category") or "General"), body_style),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[1.5 * inch, 2.1 * inch, 1.6 * inch, 1.8 * inch])
    summary_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # 4. ELIGIBILITY COMPARISON MATRIX
    if matrix:
        story.append(Paragraph("ELIGIBILITY COMPARISON MATRIX", h2_style))
        matrix_table_data = [
            [
                Paragraph("<b>Criteria Parameter</b>", body_style),
                Paragraph("<b>Your Uploaded Value</b>", body_style),
                Paragraph("<b>Scheme Requirement</b>", body_style),
                Paragraph("<b>Verification Status</b>", body_style)
            ]
        ]
        for row in matrix:
            st_text = sanitize_pdf_text(row.get("status_label", ""))
            st_style = badge_green if row.get("status_type") == "success" else badge_amber
            matrix_table_data.append([
                Paragraph(sanitize_pdf_text(row.get("parameter", "")), body_style),
                Paragraph(sanitize_pdf_text(str(row.get("uploaded_value", ""))), body_style),
                Paragraph(sanitize_pdf_text(str(row.get("requirement", ""))), body_style),
                Paragraph(st_text, st_style)
            ])
        matrix_table = Table(matrix_table_data, colWidths=[2.0 * inch, 1.7 * inch, 1.8 * inch, 1.5 * inch])
        matrix_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(matrix_table)
        story.append(Spacer(1, 14))

    # 5. ACTION REQUIRED & MISSING DOCUMENTS
    if missing_docs:
        story.append(Paragraph("MISSING MANDATORY DOCUMENTS", h2_style))
        for item in missing_docs:
            p_text = f"<b>✕ {sanitize_pdf_text(item.get('title'))}</b> — {sanitize_pdf_text(item.get('detail'))}"
            story.append(Paragraph(p_text, badge_red))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 10))

    # 6. NEEDS ATTENTION / DISCREPANCIES
    if needs_attention:
        story.append(Paragraph("ITEMS NEEDING YOUR ATTENTION", h2_style))
        for item in needs_attention:
            sev = sanitize_pdf_text(item.get("severity", "Attention"))
            title = sanitize_pdf_text(item.get("title", ""))
            det = sanitize_pdf_text(item.get("detail", ""))
            exp = item.get("explanation", {})
            p_title = f"<b>⚠ [{sev}] {title}</b>"
            story.append(Paragraph(p_title, badge_amber))
            story.append(Paragraph(f"{det}", body_style))
            if exp:
                story.append(Paragraph(f"<i>Why this matters:</i> {sanitize_pdf_text(exp.get('why_it_matters', ''))}", body_muted))
                story.append(Paragraph(f"<i>Recommended Next Step:</i> {sanitize_pdf_text(exp.get('what_to_do_next', ''))}", body_style))
            story.append(Spacer(1, 8))
        story.append(Spacer(1, 8))

    # 7. PASSED VERIFICATIONS
    if checks_passed:
        story.append(Paragraph("PASSED VERIFICATIONS", h2_style))
        for chk in checks_passed:
            p_chk = f"<b>✓ {sanitize_pdf_text(chk.get('title'))}</b>"
            story.append(Paragraph(p_chk, badge_green))
            if chk.get("detail"):
                story.append(Paragraph(f"{sanitize_pdf_text(chk.get('detail'))}", body_muted))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 12))

    # 8. OFFICIAL DISCLAIMER
    story.append(Spacer(1, 10))
    disclaimer_text = (
        "<b>IMPORTANT NOTICE:</b> ScholarProof is an independent application pre-checking tool. "
        "This report is not an official scholarship application, eligibility certificate, government verification, "
        "or guarantee of approval. Final eligibility and approval are determined exclusively by the respective "
        "scholarship authority. Ensure you review official government portal guidelines before submitting."
    )
    disclaimer_box = Table([[Paragraph(disclaimer_text, body_muted)]], colWidths=[7.0 * inch])
    disclaimer_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(disclaimer_box)

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
