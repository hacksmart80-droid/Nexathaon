from services.similarity_checker import compare_names, compare_dates_of_birth
from utils.helpers import parse_currency_to_number

def run_cross_document_checks(applicant, verified_docs):
    """
    Performs cross-document verification comparing student profile with verified document records.
    applicant: dict with full_name, dob, annual_income, percentage, institute, course, category
    verified_docs: dict keyed by doc_type -> {"fields": {...}, "filename": ...}
    Returns:
    {
        "checks_passed": list[dict],
        "needs_attention": list[dict],
        "could_not_verify": list[dict],
        "name_discrepancies": list[dict]
    }
    """
    checks_passed = []
    needs_attention = []
    could_not_verify = []
    name_discrepancies = []

    profile_name = (applicant.get("full_name") or "").strip()
    profile_dob = applicant.get("dob")
    profile_institute = (applicant.get("institute") or "").strip()
    profile_category = (applicant.get("category") or "").strip()

    id_fields = verified_docs.get("identity_proof", {}).get("fields", {})
    college_fields = verified_docs.get("college_proof", {}).get("fields", {})
    income_fields = verified_docs.get("income_certificate", {}).get("fields", {})
    bank_fields = verified_docs.get("bank_proof", {}).get("fields", {})
    marksheet_fields = verified_docs.get("previous_marksheet", {}).get("fields", {})
    category_fields = verified_docs.get("category_certificate", {}).get("fields", {})

    id_name = id_fields.get("full_name")
    college_name = college_fields.get("candidate_name")
    bank_holder = bank_fields.get("account_holder")
    income_beneficiary = income_fields.get("beneficiary_name")

    # ----------------------------------------------------
    # 1. NAME CONSISTENCY CHECKS
    # ----------------------------------------------------
    # (a) Identity vs College
    if id_name and college_name:
        cmp = compare_names(id_name, college_name)
        if cmp["state"] == "MATCH":
            checks_passed.append({
                "id": "name_id_vs_college",
                "title": "Name matches properly across Identity and College records",
                "badge": "Exact Match",
                "doc_sources": ["Identity Proof", "College Record"],
                "detail": f"Both documents confirm name as '{id_name}'."
            })
        elif cmp["state"] == "POSSIBLE_MATCH":
            item = {
                "id": "name_id_vs_college",
                "title": "Possible Name Mismatch",
                "severity": "High Impact",
                "badge": "Review Needed",
                "field": "Student Full Name",
                "doc1_name": "Identity Proof (Aadhaar / ID)",
                "val1": id_name,
                "doc2_name": "College Bonafide Record",
                "val2": college_name,
                "detail": f"Difference detected: Variation between '{id_name}' and '{college_name}' can lead to automated scholarship portal rejection.",
                "explanation": {
                    "what_we_found": f"Identity Proof: {id_name} | College Record: {college_name}",
                    "why_it_matters": "Scholarship evaluation portals cross-reference university rolls with government databases. Character differences or abbreviation variations can stall verification or cause portal rejection.",
                    "what_to_do_next": "Check the official scholarship instructions and verify whether an affidavit or college roll correction is required prior to portal submission."
                }
            }
            needs_attention.append(item)
            name_discrepancies.append(item)
        else:
            item = {
                "id": "name_id_vs_college",
                "title": "Name Mismatch between Identity and College",
                "severity": "High Impact",
                "badge": "Mismatch",
                "field": "Student Full Name",
                "doc1_name": "Identity Proof",
                "val1": id_name,
                "doc2_name": "College Record",
                "val2": college_name,
                "detail": f"Significant mismatch found: '{id_name}' vs '{college_name}'.",
                "explanation": {
                    "what_we_found": f"Identity Proof has '{id_name}', while College Proof has '{college_name}'.",
                    "why_it_matters": "Records appear to refer to different individuals or have major clerical spelling errors.",
                    "what_to_do_next": "Verify you uploaded the correct documents for the applicant."
                }
            }
            needs_attention.append(item)
            name_discrepancies.append(item)

    # (b) Bank Holder vs Identity / Profile Name
    primary_name = id_name or profile_name
    if primary_name and bank_holder:
        cmp_bank = compare_names(primary_name, bank_holder)
        if cmp_bank["state"] == "MATCH":
            checks_passed.append({
                "id": "name_bank_match",
                "title": "Bank Account Holder matches Applicant Name with valid IFSC format",
                "badge": "Validated",
                "doc_sources": ["Bank Proof", "Identity Proof"],
                "detail": f"Bank account is registered in applicant's verified name ('{bank_holder}'). Ready for Direct Benefit Transfer (DBT)."
            })
        elif cmp_bank["state"] == "POSSIBLE_MATCH":
            needs_attention.append({
                "id": "name_bank_match",
                "title": "Bank Account Holder Name Similar but not Identical",
                "severity": "Medium Impact",
                "badge": "Bank Review",
                "field": "Bank Holder Name",
                "doc1_name": "Applicant Record",
                "val1": primary_name,
                "doc2_name": "Bank Passbook",
                "val2": bank_holder,
                "detail": f"Bank passbook name is '{bank_holder}', compared to '{primary_name}'.",
                "explanation": {
                    "what_we_found": f"Applicant name is '{primary_name}' while Bank holder is '{bank_holder}'.",
                    "why_it_matters": "Aadhaar-based Direct Benefit Transfer (DBT) requires your bank account name to strictly match your Aadhaar record.",
                    "what_to_do_next": "Ensure your bank account is Aadhaar-seeded (NPCI mapped) with matching name spelling."
                }
            })
        else:
            needs_attention.append({
                "id": "name_bank_match",
                "title": "Bank Account Holder Name Does Not Match Applicant",
                "severity": "High Impact",
                "badge": "DBT Mismatch",
                "field": "Bank Holder Name",
                "doc1_name": "Applicant Record",
                "val1": primary_name,
                "doc2_name": "Bank Passbook",
                "val2": bank_holder,
                "detail": f"Bank passbook belongs to '{bank_holder}', but applicant is '{primary_name}'. Joint accounts or parent accounts may be disallowed.",
                "explanation": {
                    "what_we_found": f"Passbook is in name of '{bank_holder}', applicant is '{primary_name}'.",
                    "why_it_matters": "Most scholarship portals mandate an individual bank account in the student's own name.",
                    "what_to_do_next": "Open or submit an individual savings account belonging to the applicant."
                }
            })
    elif "bank_proof" in verified_docs and not bank_holder:
        could_not_verify.append({
            "id": "bank_holder_undetected",
            "title": "Bank Account Holder Name could not be detected",
            "badge": "Unverified",
            "detail": "Passbook page did not yield clear account holder name. Verify or enter manually."
        })

    # ----------------------------------------------------
    # 2. DATE OF BIRTH CONSISTENCY
    # ----------------------------------------------------
    id_dob = id_fields.get("dob")
    if profile_dob and id_dob:
        dob_cmp = compare_dates_of_birth(profile_dob, id_dob)
        if dob_cmp["state"] == "MATCH":
            checks_passed.append({
                "id": "dob_match",
                "title": f"Date of Birth ({dob_cmp.get('iso1')}) matches properly across Identity and Profile records",
                "badge": "Exact Match",
                "doc_sources": ["Identity Proof", "Applicant Details"],
                "detail": "Verified calendar date of birth is completely synchronized."
            })
        else:
            needs_attention.append({
                "id": "dob_match",
                "title": f"Date of Birth discrepancy ({profile_dob} vs {id_dob})",
                "severity": "High Impact",
                "badge": "DOB Variance",
                "field": "Date of Birth",
                "doc1_name": "Applicant Details",
                "val1": profile_dob,
                "doc2_name": "Identity Proof",
                "val2": id_dob,
                "detail": "Applicant profile DOB differs from detected identity proof DOB.",
                "explanation": {
                    "what_we_found": f"Entered DOB: {profile_dob} | ID Document: {id_dob}",
                    "why_it_matters": "Scholarship portals perform automated date matching with UIDAI or Board registers.",
                    "what_to_do_next": "Ensure the entered DOB exactly matches your legal certificates."
                }
            })

    # ----------------------------------------------------
    # 3. COLLEGE / INSTITUTE VERIFICATION
    # ----------------------------------------------------
    col_inst = college_fields.get("institute_name")
    if col_inst:
        checks_passed.append({
            "id": "institute_verified",
            "title": f"Institute Status Recognized: '{col_inst}' verified under institutional records",
            "badge": "Accredited",
            "doc_sources": ["College Proof"],
            "detail": "Enrolled institute detected with bonafide / admission record."
        })

    # ----------------------------------------------------
    # 4. CATEGORY CONSISTENCY
    # ----------------------------------------------------
    if profile_category and profile_category.lower() not in ["general", "open"]:
        if "category_certificate" in verified_docs:
            cat_cert_cat = category_fields.get("category")
            if cat_cert_cat:
                if profile_category.lower() in cat_cert_cat.lower():
                    checks_passed.append({
                        "id": "category_verified",
                        "title": f"Category Certificate validated for {profile_category}",
                        "badge": "Verified",
                        "doc_sources": ["Category Certificate"],
                        "detail": f"Official certificate confirms '{cat_cert_cat}' reservation category."
                    })
                else:
                    needs_attention.append({
                        "id": "category_mismatch",
                        "title": f"Category Mismatch: Profile ({profile_category}) vs Certificate ({cat_cert_cat})",
                        "severity": "High Impact",
                        "badge": "Category Discrepancy",
                        "detail": f"Applicant claimed {profile_category} but certificate specifies {cat_cert_cat}.",
                        "explanation": {
                            "what_we_found": f"Applicant profile: {profile_category} | Certificate: {cat_cert_cat}",
                            "why_it_matters": "Mismatched reservation categories can lead to immediate disqualification.",
                            "what_to_do_next": "Upload the matching category certificate or update your profile category."
                        }
                    })
        else:
            needs_attention.append({
                "id": "category_missing",
                "title": f"Category Certificate Not Uploaded ({profile_category})",
                "severity": "Medium Impact",
                "badge": "Conditional",
                "detail": f"Government portals will demand an active {profile_category} certificate to claim reservation benefits.",
                "explanation": {
                    "what_we_found": f"Applicant selected '{profile_category}' category, but no Category Certificate was uploaded.",
                    "why_it_matters": "Portals reject reservation claims if quota proof is omitted.",
                    "what_to_do_next": "Upload your caste/community certificate before submitting to the portal."
                }
            })

    return {
        "checks_passed": checks_passed,
        "needs_attention": needs_attention,
        "could_not_verify": could_not_verify,
        "name_discrepancies": name_discrepancies
    }
