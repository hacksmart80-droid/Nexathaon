import os
import json
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename

import config
from utils.helpers import (
    generate_case_id,
    generate_reference_number,
    sanitize_filename,
    get_case_folder,
    cleanup_case_folder,
    cleanup_stale_cases
)
from utils.validators import is_allowed_file, validate_applicant_data
from services.ocr_service import ocr_service
from services.field_extractor import extract_fields_by_doc_type
from services.document_checker import run_cross_document_checks
from services.scholarship_engine import (
    load_all_scholarships,
    get_scholarship_by_id,
    evaluate_scholarship_eligibility
)
from services.readiness_engine import calculate_readiness_score
from services.report_generator import generate_pdf_report

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Ensure essential directories exist
os.makedirs(config.TEMP_CASES_DIR, exist_ok=True)
os.makedirs(config.SAMPLE_DATA_DIR, exist_ok=True)

@app.route('/')
def index():
    """Serves the ScholarProof Single Page Application."""
    cleanup_stale_cases()
    return render_template('index.html')

@app.route('/api/create-check', methods=['POST'])
def create_check():
    """Initializes a new ephemeral ScholarProof session."""
    case_id = generate_case_id()
    ref_no = generate_reference_number()
    # Create temp case directory
    get_case_folder(case_id)
    return jsonify({
        "caseId": case_id,
        "referenceNumber": ref_no,
        "createdAt": datetime.now().isoformat()
    })

@app.route('/api/scholarships', methods=['GET'])
def get_scholarships():
    """Returns configured scholarship schemes."""
    scholarships = load_all_scholarships()
    return jsonify(scholarships)

@app.route('/api/scholarship/<scholarship_id>', methods=['GET'])
def get_scholarship(scholarship_id):
    """Returns configuration for a specific scholarship."""
    sch = get_scholarship_by_id(scholarship_id)
    if not sch:
        return jsonify({"error": "Scholarship configuration not found."}), 404
    return jsonify(sch)

@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Uploads a document associated with a declared document type."""
    case_id = request.form.get('caseId')
    doc_type = request.form.get('docType')

    if not case_id or not doc_type:
        return jsonify({"error": "caseId and docType are required."}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected."}), 400

    if not is_allowed_file(file.filename):
        return jsonify({"error": "Unsupported file format. Please upload PDF, JPG, or PNG."}), 400

    case_folder = get_case_folder(case_id)
    uploads_dir = os.path.join(case_folder, 'uploads')

    raw_filename = sanitize_filename(file.filename)
    stored_filename = f"{doc_type}_{raw_filename}"
    file_path = os.path.join(uploads_dir, stored_filename)

    file.save(file_path)
    file_size = os.path.getsize(file_path)

    # Format file size nicely
    if file_size > 1024 * 1024:
        size_fmt = f"{file_size / (1024 * 1024):.1f} MB"
    else:
        size_fmt = f"{file_size / 1024:.0f} KB"

    ext = os.path.splitext(file.filename)[1].upper().replace('.', '')
    fmt_label = f"{ext} Document" if ext == 'PDF' else "Image Document"

    return jsonify({
        "success": True,
        "docType": doc_type,
        "originalName": file.filename,
        "storedFilename": stored_filename,
        "size": file_size,
        "sizeFormatted": size_fmt,
        "formatLabel": fmt_label,
        "uploadedAt": datetime.now().isoformat()
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_document():
    """Performs OCR and deterministic field extraction on an uploaded document."""
    data = request.get_json() or {}
    case_id = data.get('caseId')
    doc_type = data.get('docType')
    stored_filename = data.get('storedFilename')

    if not case_id or not doc_type or not stored_filename:
        return jsonify({"error": "caseId, docType, and storedFilename are required."}), 400

    case_folder = get_case_folder(case_id)
    file_path = os.path.join(case_folder, 'uploads', stored_filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "Uploaded document file not found."}), 404

    # Run OCR Service
    ocr_result = ocr_service.extract_text(file_path)

    # Run Field Extractor
    extracted = extract_fields_by_doc_type(doc_type, ocr_result)

    return jsonify({
        "success": True,
        "docType": doc_type,
        "storedFilename": stored_filename,
        "fields": extracted["fields"],
        "rawText": extracted.get("raw_text", ""),
        "ocrError": ocr_result.get("error")
    })

@app.route('/api/check', methods=['POST'])
def perform_check():
    """
    Performs full pre-check analysis:
    - Cross-document consistency verification
    - Scheme eligibility evaluation
    - Deterministic readiness scoring
    """
    payload = request.get_json() or {}
    case_id = payload.get('caseId')
    ref_no = payload.get('referenceNumber', 'SP-2026-DEMO')
    scholarship_id = payload.get('scholarshipId')
    applicant = payload.get('applicant', {})
    verified_docs = payload.get('verifiedDocs', {})

    if not scholarship_id:
        return jsonify({"error": "Scholarship ID is required."}), 400

    scholarship = get_scholarship_by_id(scholarship_id)
    if not scholarship:
        return jsonify({"error": "Scholarship configuration not found."}), 404

    # 1. Run Cross-Document Checks
    doc_checks = run_cross_document_checks(applicant, verified_docs)

    # 2. Run Scholarship Eligibility Rules
    elig_checks = evaluate_scholarship_eligibility(scholarship, applicant, verified_docs)

    # 3. Calculate Readiness Score
    missing_docs = elig_checks["missing_documents"]
    readiness = calculate_readiness_score(scholarship, missing_docs, doc_checks, elig_checks)

    timestamp = datetime.now().strftime("%d %B %Y, %H:%M IST")

    return jsonify({
        "caseId": case_id,
        "referenceNumber": ref_no,
        "scholarship": scholarship,
        "applicant": applicant,
        "readiness": readiness,
        "checksPassed": doc_checks["checks_passed"] + elig_checks["eligibility_passed"],
        "needsAttention": doc_checks["needs_attention"] + elig_checks["eligibility_warnings"],
        "missingDocuments": missing_docs,
        "couldNotVerify": doc_checks["could_not_verify"],
        "comparisonMatrix": elig_checks["comparison_matrix"],
        "nameDiscrepancies": doc_checks["name_discrepancies"],
        "timestamp": timestamp
    })

@app.route('/api/generate-report', methods=['POST'])
def create_report():
    """Generates official ScholarProof PDF report using ReportLab."""
    payload = request.get_json() or {}
    case_id = payload.get('caseId')
    ref_no = payload.get('referenceNumber', 'SP-2026-DEMO')

    if not case_id:
        return jsonify({"error": "caseId is required."}), 400

    case_folder = get_case_folder(case_id)
    report_dir = os.path.join(case_folder, 'report')
    safe_filename = f"ScholarProof_Report_{ref_no}.pdf"
    pdf_path = os.path.join(report_dir, safe_filename)

    try:
        generate_pdf_report(payload, pdf_path)
        return jsonify({
            "success": True,
            "filename": safe_filename,
            "downloadUrl": f"/api/report/{case_id}/{safe_filename}"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to generate report PDF: {str(e)}"}), 500

@app.route('/api/report/<case_id>/<filename>', methods=['GET'])
def download_report(case_id, filename):
    """Downloads generated PDF report."""
    clean_fn = secure_filename(filename)
    case_folder = get_case_folder(case_id)
    report_dir = os.path.join(case_folder, 'report')
    file_path = os.path.join(report_dir, clean_fn)

    if not os.path.exists(file_path):
        abort(404)

    return send_from_directory(
        report_dir,
        clean_fn,
        as_attachment=True,
        download_name=clean_fn,
        mimetype='application/pdf'
    )

@app.route('/api/cleanup', methods=['POST'])
def cleanup_session():
    """Deletes temporary case files after workflow completion."""
    data = request.get_json() or {}
    case_id = data.get('caseId')
    if case_id:
        cleanup_case_folder(case_id)
    return jsonify({"success": True})

@app.route('/api/load-sample', methods=['POST'])
def load_sample_file():
    """
    Convenience endpoint for testing: copies a sample test document into active case uploads.
    """
    data = request.get_json() or {}
    case_id = data.get('caseId')
    sample_key = data.get('sampleKey')
    doc_type = data.get('docType')

    if not case_id or not sample_key or not doc_type:
        return jsonify({"error": "caseId, sampleKey, and docType are required."}), 400

    sample_map = {
        "aadhaar_mohd_saif": "aadhaar_mohd_saif.pdf",
        "aadhaar_mohammed_saif": "aadhaar_mohammed_saif.pdf",
        "college_bonafide": "college_bonafide_saif.pdf",
        "income_valid": "income_certificate_valid.pdf",
        "income_expired": "income_certificate_expired.pdf",
        "income_high": "income_certificate_high.pdf",
        "marksheet_passed": "previous_marksheet_passed.pdf",
        "marksheet_low": "previous_marksheet_low.pdf",
        "bank_passbook": "bank_passbook_sbi.pdf",
        "unreadable_blurry": "unreadable_blurry.png"
    }

    sample_filename = sample_map.get(sample_key)
    if not sample_filename:
        return jsonify({"error": "Unknown sample key."}), 400

    src_path = os.path.join(config.SAMPLE_DATA_DIR, sample_filename)
    if not os.path.exists(src_path):
        return jsonify({"error": "Sample file not found on server."}), 404

    case_folder = get_case_folder(case_id)
    uploads_dir = os.path.join(case_folder, 'uploads')
    dest_filename = f"{doc_type}_{sample_filename}"
    dest_path = os.path.join(uploads_dir, dest_filename)

    import shutil
    shutil.copyfile(src_path, dest_path)
    file_size = os.path.getsize(dest_path)

    if file_size > 1024 * 1024:
        size_fmt = f"{file_size / (1024 * 1024):.1f} MB"
    else:
        size_fmt = f"{file_size / 1024:.0f} KB"

    ext = os.path.splitext(sample_filename)[1].upper().replace('.', '')
    fmt_label = f"{ext} Document" if ext == 'PDF' else "Image Document"

    return jsonify({
        "success": True,
        "docType": doc_type,
        "originalName": sample_filename,
        "storedFilename": dest_filename,
        "size": file_size,
        "sizeFormatted": size_fmt,
        "formatLabel": fmt_label,
        "uploadedAt": datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
