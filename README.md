# SCHOLARPROOF
> **“Check before you apply.”**

ScholarProof is an intelligent, privacy-first pre-checking web application that helps students verify scholarship applications **before** submitting them to official government and institutional portals. It combines optical character recognition (PaddleOCR), deterministic field parsing, RapidFuzz cross-record verification, and an automated rule engine to catch clerical mistakes, missing documents, and eligibility mismatches.

---

## 1. Problem & Solution

Every year, thousands of deserving students lose scholarship awards due to minor clerical errors:
- Name spelling variations across records (e.g., *“Ansari Mohd Saif”* vs *“Ansari Mohammed Saif”*).
- Expired income certificates issued outside the valid date window.
- Missing mandatory documents (e.g., previous year semester marksheet).
- Annual family income exceeding configured scheme thresholds.

**ScholarProof provides an instant pre-audit:**
1. Student selects a scholarship scheme (e.g., Post-Matric, State Merit, National Portal).
2. Views configured eligibility requirements and document checklist.
3. Enters basic profile details (no Aadhaar number required).
4. Uploads required documents (PDF, JPG, PNG).
5. Documents are analyzed locally with OCR & deterministic regex parsing.
6. Extracted details are cross-compared across all documents for consistency.
7. Student reviews and can correct or confirm any field.
8. Calculates a transparent **Application Readiness Score (0–100%)**.
9. Explains any issues found with actionable *“How to fix this”* guidance.
10. Generates a downloadable, professional **ScholarProof Check Report (PDF)**.

---

## 2. Technology Stack

- **Frontend:** HTML5, CSS3, Vanilla JavaScript (Single Page Architecture, Google Stitch Source of Truth).
- **Backend:** Python 3.12, Flask.
- **Local OCR:** PaddleOCR 2.9.1 with PaddlePaddle 2.6.2 (100% on-device, zero external AI APIs).
- **PDF Extraction:** PyMuPDF (`fitz`).
- **Image Processing:** OpenCV (`cv2`), Pillow (`PIL`).
- **Record Similarity & Matching:** RapidFuzz.
- **PDF Report Generation:** ReportLab.
- **Storage:** Ephemeral temporary case directories (`temp/cases/<uuid>/`), automatic cleanup, **zero permanent databases**.

---

## 3. Project Directory Structure

```
ScholarProof/
│
├── app.py                      # Flask backend application entry point
├── config.py                   # Paths, upload limits, and runtime configurations
├── requirements.txt            # Python dependencies
├── README.md                   # Complete system documentation
│
├── templates/
│   └── index.html              # Single Page Application matching Google Stitch design
│
├── static/
│   ├── css/
│   │   └── style.css           # Utilitarian design tokens, responsive layout, iLovePDF styling
│   └── js/
│       └── app.js              # Client state management, OCR workflow, API interactions
│
├── services/
│   ├── __init__.py
│   ├── ocr_service.py          # Local PaddleOCR & text extraction singleton
│   ├── image_processor.py      # OpenCV contrast, sharpening, and sizing
│   ├── pdf_processor.py        # PyMuPDF digital text layer and scan rasterizer
│   ├── field_extractor.py      # Deterministic per-document regex & heuristics
│   ├── document_checker.py     # Cross-document consistency (name, DOB, bank, category)
│   ├── similarity_checker.py   # RapidFuzz name matching & date validity calculations
│   ├── scholarship_engine.py   # Data-driven scheme rule validation
│   ├── readiness_engine.py     # Deterministic 4-pillar readiness score calculator
│   └── report_generator.py     # ReportLab multi-page branded PDF generator
│
├── data/
│   └── scholarships.json       # Configured demo scholarship schemes
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py              # Case IDs, reference numbers, masking, currency parsing
│   └── validators.py           # Upload constraints & form field validation
│
├── sample_data/                # Synthetic test documents
│   ├── generate_samples.py     # Programmatic generator for demo test cases
│   ├── aadhaar_mohd_saif.pdf
│   ├── aadhaar_mohammed_saif.pdf
│   ├── college_bonafide_saif.pdf
│   ├── income_certificate_valid.pdf
│   ├── income_certificate_expired.pdf
│   ├── income_certificate_high.pdf
│   ├── previous_marksheet_passed.pdf
│   ├── previous_marksheet_low.pdf
│   └── bank_passbook_sbi.pdf
│
└── temp/
    └── cases/                  # Ephemeral session directories (uploads, reports)
```

---

## 4. Installation & Setup

### Prerequisites
- Windows 10/11, macOS, or Linux.
- **Python 3.12 (64-bit)** is recommended for binary compatibility with PaddlePaddle 2.6.2.

### Step 1: Create Virtual Environment
```powershell
# In PowerShell:
py -3.12 -m venv venv
.\venv\Scripts\activate
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Run the Application
```powershell
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 5. How to Configure & Add Scholarships

Scholarship rules are stored in `data/scholarships.json`. To add a new scholarship scheme, simply add a new object:

```json
{
  "id": "demo_girls_stem_scholarship",
  "name": "State Women in STEM Excellence Scholarship",
  "provider": "Department of Science & Technology",
  "tag": "State Special Scheme",
  "description": "Financial aid for female engineering and pure sciences undergraduates.",
  "target_level": "Undergraduate B.Tech / B.Sc",
  "deadline": "31 March 2026",
  "income_limit": 350000,
  "minimum_percentage": 65.0,
  "education_levels": ["B.Tech", "B.Sc"],
  "required_documents": [
    "identity_proof",
    "income_certificate",
    "college_proof",
    "previous_marksheet",
    "bank_proof"
  ],
  "optional_documents": [
    "category_certificate"
  ],
  "certificate_validity_required": true
}
```

---

## 6. Verification Pillars & Readiness Formula

The **Application Readiness Score (0–100%)** is calculated deterministically across 4 key pillars:
1. **Required Documents (35 points):** Evaluates whether all scheme-mandatory certificates have been attached.
2. **Eligibility Requirements (30 points):** Verifies that income is under the scheme ceiling (15 pts) and marks meet or exceed qualifying thresholds (15 pts).
3. **Cross-Document Consistency (25 points):** Evaluates character-level and token similarity across Identity, College, Bank, and Income certificates using RapidFuzz.
4. **Data Completeness & Validity (10 points):** Verifies certificate expiry dates against current calendar dates, checks IFSC code syntax, and confirms active account status.

### Readiness Bands
- **90–100%:** `Looks Ready` (Green) — All parameters verified, minimal risk of rejection.
- **70–89%:** `Almost Ready` (Amber) — 1 or 2 minor variances or missing optional items.
- **40–69%:** `Needs Attention` (Amber/Red) — Important document missing or threshold mismatch.
- **0–39%:** `Several Issues Found` (Red) — Critical criteria unfulfilled.

---

## 7. Privacy & Security Rules

- **Ephemeral Storage:** All uploads are stored in temporary case folders (`temp/cases/<uuid>/`) and cleaned up automatically.
- **Data Masking:** Full Aadhaar numbers are immediately masked (`XXXX XXXX 1234`) and bank account numbers are protected (`XXXXXX1234`).
- **No Third-Party AI APIs:** Document OCR runs strictly on-device using local PaddleOCR. No student documents are ever sent to ChatGPT, Gemini, Claude, or external cloud LLMs.
