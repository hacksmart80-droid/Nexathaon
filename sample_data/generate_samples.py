import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from PIL import Image, ImageDraw

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def create_pdf(filename, title, subtitle, fields, note=None):
    filepath = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(filepath, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54)
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle('Head', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=colors.HexColor('#1A1D20'), alignment=1)
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor('#666666'), alignment=1)
    field_label = ParagraphStyle('FL', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=14, textColor=colors.HexColor('#333333'))
    field_val = ParagraphStyle('FV', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor('#111111'))
    demo_badge = ParagraphStyle('Badge', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.HexColor('#BA0913'), alignment=1)

    story = [
        Paragraph("DEMO SAMPLE DOCUMENT — FOR TESTING SCHOLARPROOF ONLY", demo_badge),
        Spacer(1, 10),
        Paragraph(title, header_style),
        Paragraph(subtitle, sub_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E4E4E4'), spaceBefore=8, spaceAfter=14)
    ]

    table_data = []
    for label, val in fields:
        table_data.append([Paragraph(label, field_label), Paragraph(str(val), field_val)])

    t = Table(table_data, colWidths=[2.5 * 72, 4.5 * 72])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8F9FB')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E4E4E4')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E4E4E4')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(t)

    if note:
        story.append(Spacer(1, 14))
        story.append(Paragraph(f"<i>{note}</i>", sub_style))

    doc.build(story)
    print(f"Generated: {filepath}")

def generate_all_samples():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Identity Proof (Aadhaar with Ansari Mohd Saif)
    create_pdf(
        "aadhaar_mohd_saif.pdf",
        "GOVERNMENT OF INDIA",
        "Unique Identification Authority of India - Resident Identity",
        [
            ("Name", "Ansari Mohd Saif"),
            ("Date of Birth", "14/07/2007"),
            ("Gender", "Male"),
            ("State", "Maharashtra"),
            ("Aadhaar Number", "9876 5432 1098")
        ]
    )

    # 1b. Identity Proof with Full Name (Ansari Mohammed Saif)
    create_pdf(
        "aadhaar_mohammed_saif.pdf",
        "GOVERNMENT OF INDIA",
        "Unique Identification Authority of India - Resident Identity",
        [
            ("Name", "Ansari Mohammed Saif"),
            ("Date of Birth", "14/07/2007"),
            ("Gender", "Male"),
            ("State", "Maharashtra"),
            ("Aadhaar Number", "9876 5432 1098")
        ]
    )

    # 2. College Record / Bonafide
    create_pdf(
        "college_bonafide_saif.pdf",
        "PUNE INSTITUTE OF ENGINEERING & TECHNOLOGY",
        "Department of Academic Affairs — Bonafide Student Certificate",
        [
            ("Candidate Name", "Ansari Mohammed Saif"),
            ("Institute Name", "Pune Institute of Eng."),
            ("Enrolled Course", "B.Tech Comp (Yr 2)"),
            ("Admission Year", "2023-2024"),
            ("Roll Number", "PIET-2023-CS-042")
        ]
    )

    # 3. Income Certificate (Valid, ₹2,20,000, expires 31/03/2027)
    create_pdf(
        "income_certificate_valid.pdf",
        "GOVERNMENT OF MAHARASHTRA — REVENUE DEPARTMENT",
        "Office of the Tahsildar / Taluk Magistrate",
        [
            ("Beneficiary Name", "Ansari Mohd Saif"),
            ("Annual Family Income", "₹2,20,000"),
            ("Certificate No.", "MH/INC/2024/88921"),
            ("Issue Date", "14/04/2024"),
            ("Valid Until", "31/03/2027"),
            ("Issuing Authority", "Tahsildar")
        ]
    )

    # 4. Income Certificate (Expired, 31/03/2023)
    create_pdf(
        "income_certificate_expired.pdf",
        "GOVERNMENT OF MAHARASHTRA — REVENUE DEPARTMENT",
        "Office of the Tahsildar / Taluk Magistrate",
        [
            ("Beneficiary Name", "Ansari Mohd Saif"),
            ("Annual Family Income", "₹2,20,000"),
            ("Certificate No.", "MH/INC/2021/44102"),
            ("Issue Date", "10/04/2021"),
            ("Valid Until", "31/03/2023"),
            ("Issuing Authority", "Tahsildar")
        ]
    )

    # 5. Income Certificate (High Income ₹3,50,000 - Above ₹2.5L limit)
    create_pdf(
        "income_certificate_high.pdf",
        "GOVERNMENT OF MAHARASHTRA — REVENUE DEPARTMENT",
        "Office of the Tahsildar / Taluk Magistrate",
        [
            ("Beneficiary Name", "Ansari Mohd Saif"),
            ("Annual Family Income", "₹3,50,000"),
            ("Certificate No.", "MH/INC/2024/99120"),
            ("Issue Date", "01/05/2024"),
            ("Valid Until", "31/03/2027"),
            ("Issuing Authority", "Tahsildar")
        ]
    )

    # 6. Previous Marksheet (78.50%)
    create_pdf(
        "previous_marksheet_passed.pdf",
        "MAHARASHTRA STATE BOARD OF SECONDARY & HIGHER SECONDARY EDUCATION",
        "Higher Secondary Certificate Examination — Statement of Marks",
        [
            ("Student Name", "Ansari Mohd Saif"),
            ("Exam Year", "2023"),
            ("Aggregate Percentage", "78.50%"),
            ("Pass Status", "Passed First Class with Distinction")
        ]
    )

    # 6b. Previous Marksheet (Low Marks 44.0% - Below 50% limit)
    create_pdf(
        "previous_marksheet_low.pdf",
        "MAHARASHTRA STATE BOARD OF SECONDARY & HIGHER SECONDARY EDUCATION",
        "Higher Secondary Certificate Examination — Statement of Marks",
        [
            ("Student Name", "Ansari Mohd Saif"),
            ("Exam Year", "2023"),
            ("Aggregate Percentage", "44.00%"),
            ("Pass Status", "Passed Pass Class")
        ]
    )

    # 7. Bank Passbook
    create_pdf(
        "bank_passbook_sbi.pdf",
        "STATE BANK OF INDIA",
        "Core Banking Service — Account Passbook Summary",
        [
            ("Account Holder", "Ansari Mohd Saif"),
            ("Bank Name", "State Bank of India"),
            ("IFSC Code", "SBIN0001431"),
            ("Account Number", "XXXXXX1234"),
            ("Account Status", "Active Savings")
        ]
    )

    # 8. Unreadable blurry test image
    blurry_img = Image.new('RGB', (200, 200), color=(180, 180, 180))
    d = ImageDraw.Draw(blurry_img)
    d.line([(0, 0), (200, 200)], fill=(120, 120, 120), width=5)
    blurry_img.save(os.path.join(OUTPUT_DIR, "unreadable_blurry.png"))
    print("Generated unreadable_blurry.png")

if __name__ == "__main__":
    generate_all_samples()
