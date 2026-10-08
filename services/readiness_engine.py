def calculate_readiness_score(scholarship, missing_docs, doc_checks, elig_checks):
    """
    Calculates deterministic Application Readiness Score (0 to 100) based on 4 pillars:
    1. Required Documents: 35 points
    2. Eligibility Requirements: 30 points
    3. Cross-Document Consistency: 25 points
    4. Data Completeness & Validity: 10 points

    Returns:
    {
        "score": int (0-100),
        "status_label": "Looks Ready" | "Almost Ready" | "Needs Attention" | "Several Issues Found",
        "status_color": str,
        "summary_text": str,
        "breakdown": {
            "documents": {"score": float, "max": 35},
            "eligibility": {"score": float, "max": 30},
            "consistency": {"score": float, "max": 25},
            "completeness": {"score": float, "max": 10}
        },
        "stats": {
            "passed_count": int,
            "attention_count": int,
            "missing_count": int
        }
    }
    """
    req_docs = scholarship.get("required_documents", [])
    total_req_count = len(req_docs) if req_docs else 1
    missing_count = len(missing_docs)
    uploaded_req_count = max(0, total_req_count - missing_count)

    # 1. Required Documents (Max 35 points)
    doc_ratio = uploaded_req_count / float(total_req_count)
    doc_score = doc_ratio * 35.0

    # 2. Eligibility Requirements (Max 30 points)
    # Income (15 pts) + Marks (15 pts)
    elig_passed = elig_checks.get("eligibility_passed", [])
    elig_warnings = elig_checks.get("eligibility_warnings", [])
    
    income_pts = 15.0
    marks_pts = 15.0

    for w in elig_warnings:
        if w.get("id") == "income_check":
            income_pts = 0.0
        elif w.get("id") == "marks_check":
            marks_pts = 0.0
            
    # If missing marksheet, marks check cannot be fully awarded
    if any(m.get("doc_type") == "previous_marksheet" for m in missing_docs):
        marks_pts = 5.0  # partial pending upload
    if any(m.get("doc_type") == "income_certificate" for m in missing_docs):
        income_pts = 5.0  # partial pending upload

    eligibility_score = income_pts + marks_pts

    # 3. Cross-Document Consistency (Max 25 points)
    consistency_score = 25.0
    doc_attention = doc_checks.get("needs_attention", [])
    for att in doc_attention:
        sev = att.get("severity", "Medium Impact")
        if sev == "High Impact":
            consistency_score -= 8.0
        else:
            consistency_score -= 4.0
    consistency_score = max(0.0, consistency_score)

    # 4. Data Completeness & Validity (Max 10 points)
    completeness_score = 10.0
    cert_val = elig_checks.get("certificate_validity")
    if cert_val:
        if cert_val.get("state") == "EXPIRED":
            completeness_score -= 6.0
        elif cert_val.get("state") == "EXPIRING_SOON":
            completeness_score -= 3.0

    could_not_verify = doc_checks.get("could_not_verify", [])
    if could_not_verify:
        completeness_score -= min(4.0, len(could_not_verify) * 2.0)
    completeness_score = max(0.0, completeness_score)

    # Total Score
    total_score = round(doc_score + eligibility_score + consistency_score + completeness_score)
    total_score = max(0, min(100, total_score))

    # Readiness Category
    if total_score >= 90:
        status_label = "Looks Ready"
        status_color = "#15803D"
        summary_text = "Based on your verified records and configured requirements, your folder appears complete and ready for portal submission."
    elif total_score >= 70:
        status_label = "Almost Ready"
        status_color = "#D97706"
        issues_count = missing_count + len(doc_attention) + len(elig_warnings)
        item_word = "item" if issues_count == 1 else "items"
        summary_text = f"Based on the documents and configured requirements, your application appears almost ready with {issues_count} {item_word} to address."
    elif total_score >= 40:
        status_label = "Needs Attention"
        status_color = "#D97706"
        summary_text = "Several key documents or record differences require correction before submitting your scholarship form."
    else:
        status_label = "Several Issues Found"
        status_color = "#E5322D"
        summary_text = "Multiple mandatory documents or eligibility criteria need resolution. Complete the action items below."

    all_passed = doc_checks.get("checks_passed", []) + elig_checks.get("eligibility_passed", [])
    all_attention = doc_checks.get("needs_attention", []) + elig_checks.get("eligibility_warnings", [])

    return {
        "score": total_score,
        "status_label": status_label,
        "status_color": status_color,
        "summary_text": summary_text,
        "breakdown": {
            "documents": {"score": round(doc_score, 1), "max": 35},
            "eligibility": {"score": round(eligibility_score, 1), "max": 30},
            "consistency": {"score": round(consistency_score, 1), "max": 25},
            "completeness": {"score": round(completeness_score, 1), "max": 10}
        },
        "stats": {
            "passed_count": len(all_passed),
            "attention_count": len(all_attention),
            "missing_count": missing_count
        }
    }
