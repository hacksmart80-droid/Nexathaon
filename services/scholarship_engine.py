import json
import os
from config import SCHOLARSHIPS_FILE
from services.similarity_checker import check_certificate_validity
from utils.helpers import parse_currency_to_number, parse_percentage_to_float

def load_all_scholarships():
    """Loads all configured scholarships from scholarships.json."""
    if not os.path.exists(SCHOLARSHIPS_FILE):
        return []
    with open(SCHOLARSHIPS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_scholarship_by_id(scholarship_id):
    """Finds a scholarship config by ID."""
    all_sch = load_all_scholarships()
    for s in all_sch:
        if s.get("id") == scholarship_id:
            return s
    return None

DOCUMENT_TYPE_LABELS = {
    "identity_proof": "Identity Proof (Aadhaar / National ID)",
    "income_certificate": "Income Certificate (State Authority)",
    "college_proof": "College Admission Proof / Bonafide",
    "previous_marksheet": "Previous Year Marksheet / Transcript",
    "bank_proof": "Bank Proof (Passbook / Statement)",
    "category_certificate": "Category / Caste Certificate"
}

def evaluate_scholarship_eligibility(scholarship, applicant, verified_docs):
    """
    Evaluates applicant and verified document set against selected scholarship rules.
    Returns:
    {
        "missing_documents": list[dict],
        "eligibility_passed": list[dict],
        "eligibility_warnings": list[dict],
        "comparison_matrix": list[dict],
        "certificate_validity": dict
    }
    """
    missing_documents = []
    eligibility_passed = []
    eligibility_warnings = []
    comparison_matrix = []

    req_doc_keys = scholarship.get("required_documents", [])
    uploaded_keys = set(verified_docs.keys())

    # 1. Missing Required Documents
    for req_key in req_doc_keys:
        if req_key not in uploaded_keys:
            name_label = DOCUMENT_TYPE_LABELS.get(req_key, req_key.replace('_', ' ').title())
            missing_documents.append({
                "doc_type": req_key,
                "title": name_label,
                "badge": "Mandatory",
                "detail": f"The scheme mandates {name_label}. Missing from uploaded files."
            })

    # 2. Income Requirement Evaluation
    income_limit = scholarship.get("income_limit")
    user_income = None

    # Check verified income from income certificate first, fallback to applicant profile
    inc_cert_fields = verified_docs.get("income_certificate", {}).get("fields", {})
    if inc_cert_fields.get("annual_income") is not None:
        user_income = inc_cert_fields.get("annual_income")
    elif applicant.get("annual_income") is not None:
        user_income = parse_currency_to_number(applicant.get("annual_income"))

    if income_limit is not None:
        if user_income is not None:
            user_inc_formatted = f"₹{user_income:,.0f}" if isinstance(user_income, (int, float)) else str(user_income)
            limit_formatted = f"Max Limit: ₹{income_limit:,.0f}"

            if user_income <= income_limit:
                status_item = {
                    "id": "income_check",
                    "title": f"Annual Family Income ({user_inc_formatted}) is safely under the ₹{income_limit:,.0f} scheme threshold",
                    "badge": "Eligible",
                    "doc_sources": ["Income Certificate"],
                    "detail": "Verified gross annual income meets configured scheme limits."
                }
                eligibility_passed.append(status_item)
                comparison_matrix.append({
                    "parameter": "Annual Family Income",
                    "uploaded_value": user_inc_formatted,
                    "requirement": limit_formatted,
                    "status_label": "✓ Meets Requirement",
                    "status_type": "success"
                })
            else:
                warn_item = {
                    "id": "income_check",
                    "title": "Income exceeds configured limit",
                    "severity": "Medium Impact",
                    "badge": "Income Variance",
                    "detail": f"Verified income ({user_inc_formatted}) does not appear to meet configured income requirement (Limit: ₹{income_limit:,.0f}).",
                    "explanation": {
                        "what_we_found": f"Your verified income is {user_inc_formatted}, while configured ceiling is ₹{income_limit:,.0f}.",
                        "why_it_matters": "Financial assistance is targeted to students within prescribed income ceilings.",
                        "what_to_do_next": "Review family gross income calculation or apply under schemes with higher income brackets."
                    }
                }
                eligibility_warnings.append(warn_item)
                comparison_matrix.append({
                    "parameter": "Annual Family Income",
                    "uploaded_value": user_inc_formatted,
                    "requirement": limit_formatted,
                    "status_label": "⚠ Exceeds Limit",
                    "status_type": "warning"
                })
        else:
            comparison_matrix.append({
                "parameter": "Annual Family Income",
                "uploaded_value": "Not Verified",
                "requirement": f"Max Limit: ₹{income_limit:,.0f}",
                "status_label": "Pending Certificate Upload",
                "status_type": "pending"
            })

    # 3. Academic Marks Evaluation
    min_marks = scholarship.get("minimum_percentage")
    user_marks = None

    marksheet_fields = verified_docs.get("previous_marksheet", {}).get("fields", {})
    if marksheet_fields.get("percentage") is not None:
        user_marks = marksheet_fields.get("percentage")
    elif applicant.get("percentage") is not None:
        user_marks = parse_percentage_to_float(applicant.get("percentage"))

    if min_marks is not None:
        if user_marks is not None:
            user_marks_str = f"{user_marks:.1f}%"
            min_marks_str = f"Min Requirement: {min_marks:.1f}%"

            if user_marks >= min_marks:
                status_item = {
                    "id": "marks_check",
                    "title": f"Previous Academic Marks ({user_marks_str}) meets or exceeds qualifying criteria ({min_marks:.1f}%)",
                    "badge": "Qualified",
                    "doc_sources": ["Marksheet"],
                    "detail": "Academic performance satisfies scheme eligibility baseline."
                }
                eligibility_passed.append(status_item)
                comparison_matrix.append({
                    "parameter": "Previous Academic Marks",
                    "uploaded_value": user_marks_str,
                    "requirement": min_marks_str,
                    "status_label": "✓ Meets Requirement",
                    "status_type": "success"
                })
            else:
                warn_item = {
                    "id": "marks_check",
                    "title": "Academic Marks Below Configured Minimum",
                    "severity": "Medium Impact",
                    "badge": "Marks Warning",
                    "detail": f"Academic score ({user_marks_str}) appears below configured minimum ({min_marks_str}).",
                    "explanation": {
                        "what_we_found": f"Recorded percentage is {user_marks_str}, below requirement of {min_marks_str}.",
                        "why_it_matters": "Merit and Means criteria typically require minimum aggregate percentage in previous exam.",
                        "what_to_do_next": "Check if scheme allows CGPA conversion scaling or relaxed quotas."
                    }
                }
                eligibility_warnings.append(warn_item)
                comparison_matrix.append({
                    "parameter": "Previous Academic Marks",
                    "uploaded_value": user_marks_str,
                    "requirement": min_marks_str,
                    "status_label": "⚠ Below Minimum",
                    "status_type": "warning"
                })
        else:
            comparison_matrix.append({
                "parameter": "Previous Academic Marks",
                "uploaded_value": "File not uploaded",
                "requirement": f"Min Requirement: {min_marks:.1f}%",
                "status_label": "⚠ Pending Marksheet Upload",
                "status_type": "warning"
            })

    # 4. Certificate Validity Check
    cert_validity = None
    if "income_certificate" in verified_docs:
        valid_until = inc_cert_fields.get("valid_until")
        if valid_until:
            cert_val_res = check_certificate_validity(valid_until)
            cert_validity = cert_val_res

            if cert_val_res["state"] == "VALID":
                eligibility_passed.append({
                    "id": "cert_validity_check",
                    "title": cert_val_res["label"],
                    "badge": "Active",
                    "doc_sources": ["Income Certificate"],
                    "detail": "Certificate is current and unexpired."
                })
                comparison_matrix.append({
                    "parameter": "Income Certificate Validity",
                    "uploaded_value": f"Valid through {valid_until}",
                    "requirement": "Must be valid on application date",
                    "status_label": "✓ Valid Certificate",
                    "status_type": "success"
                })
            elif cert_val_res["state"] == "EXPIRING_SOON":
                eligibility_warnings.append({
                    "id": "cert_validity_check",
                    "title": cert_val_res["label"],
                    "severity": "Medium Impact",
                    "badge": "Expiring Soon",
                    "detail": cert_val_res["notes"],
                    "explanation": {
                        "what_we_found": f"Certificate valid until {valid_until}.",
                        "why_it_matters": "If the certificate expires while the committee reviews applications, processing might stall.",
                        "what_to_do_next": "Consider initiating certificate renewal with local revenue authorities."
                    }
                })
                comparison_matrix.append({
                    "parameter": "Income Certificate Validity",
                    "uploaded_value": f"Expires {valid_until}",
                    "requirement": "Must be valid on application date",
                    "status_label": "⚠ Expiring Soon",
                    "status_type": "warning"
                })
            elif cert_val_res["state"] == "EXPIRED":
                eligibility_warnings.append({
                    "id": "cert_validity_check",
                    "title": cert_val_res["label"],
                    "severity": "High Impact",
                    "badge": "Expired",
                    "detail": cert_val_res["notes"],
                    "explanation": {
                        "what_we_found": f"Certificate expired on {valid_until}.",
                        "why_it_matters": "Expired certificates are a leading cause of portal application rejection.",
                        "what_to_do_next": "Obtain a fresh certificate from the Tahsildar / Revenue Department."
                    }
                })
                comparison_matrix.append({
                    "parameter": "Income Certificate Validity",
                    "uploaded_value": f"Expired ({valid_until})",
                    "requirement": "Must be valid on application date",
                    "status_label": "✕ Expired Certificate",
                    "status_type": "error"
                })

    return {
        "missing_documents": missing_documents,
        "eligibility_passed": eligibility_passed,
        "eligibility_warnings": eligibility_warnings,
        "comparison_matrix": comparison_matrix,
        "certificate_validity": cert_validity
    }
