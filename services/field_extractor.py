import re
from utils.helpers import (
    mask_aadhaar,
    mask_bank_account,
    parse_currency_to_number,
    parse_percentage_to_float,
    normalize_date
)

def extract_fields_by_doc_type(doc_type, ocr_data):
    """
    Extracts structured fields from OCR output based on declared document type.
    ocr_data is a dict with {"raw_text": str, "lines": list[str]}
    Returns:
    {
        "doc_type": str,
        "fields": dict,
        "raw_text": str,
        "summary": str
    }
    """
    raw_text = ocr_data.get("raw_text", "")
    lines = ocr_data.get("lines", [])

    extractors = {
        "identity_proof": extract_identity_fields,
        "income_certificate": extract_income_fields,
        "college_proof": extract_college_fields,
        "previous_marksheet": extract_marksheet_fields,
        "bank_proof": extract_bank_fields,
        "category_certificate": extract_category_fields
    }

    extractor = extractors.get(doc_type, extract_generic_fields)
    fields = extractor(raw_text, lines)

    return {
        "doc_type": doc_type,
        "fields": fields,
        "raw_text": mask_aadhaar(raw_text)
    }

def _find_field_by_labels(lines, labels, next_line_fallback=True):
    """Searches lines for a label pattern and extracts the corresponding value."""
    for i, line in enumerate(lines):
        for label in labels:
            pattern = rf'^(?:{label})\s*[:\-\=]?\s*(.*)$'
            m = re.search(pattern, line.strip(), re.I)
            if m:
                val = m.group(1).strip()
                # If there's meaningful content (not just punctuation or empty)
                if val and len(re.sub(r'[^\w]', '', val)) > 1:
                    return val
                elif next_line_fallback and (i + 1 < len(lines)):
                    next_val = lines[i + 1].strip()
                    if next_val and not any(re.match(rf'^(?:{l})\b', next_val, re.I) for l in labels):
                        return next_val
    return None

def extract_identity_fields(raw_text, lines):
    """Extracts Identity Proof fields (Name, DOB, Gender, State, masked Aadhaar)."""
    fields = {
        "full_name": None,
        "dob": None,
        "gender": None,
        "state": None,
        "id_number": None
    }

    # 1. Full Name
    name = _find_field_by_labels(lines, [r'name', r'student\s*name', r'applicant\s*name', r'full\s*name'])
    if not name:
        # Heuristic: line after 'Government of India' or 'Unique Identification Authority'
        for i, line in enumerate(lines):
            if any(k in line.lower() for k in ['government of india', 'uidai', 'election commission']):
                if i + 1 < len(lines):
                    cand = lines[i + 1].strip()
                    if len(cand) > 3 and not re.search(r'\d', cand):
                        name = cand
                        break
    if name:
        # Clean unwanted trailing tags
        name = re.sub(r'^(?:shri|mr|smt|kumari)\.?\s*', '', name, flags=re.I)
        fields["full_name"] = name.strip()

    # 2. Date of Birth
    dob = _find_field_by_labels(lines, [r'dob', r'date\s*of\s*birth', r'birth\s*date', r'year\s*of\s*birth'])
    if not dob:
        # Search for date pattern near DOB or in text
        m_dob = re.search(r'\b(?:dob|birth|d\.o\.b)[\s:\-]+([0-9\/\-\.a-zA-Z\s]{8,15})', raw_text, re.I)
        if m_dob:
            dob = m_dob.group(1).strip()
    if dob:
        iso, dt = normalize_date(dob)
        fields["dob"] = iso if iso else dob

    # 3. Gender
    for line in lines:
        if re.search(r'\b(male|female|transgender)\b', line, re.I):
            m = re.search(r'\b(male|female|transgender)\b', line, re.I)
            fields["gender"] = m.group(1).capitalize()
            break

    # 4. State
    indian_states = [
        "Maharashtra", "Karnataka", "Tamil Nadu", "Delhi", "Gujarat", "Uttar Pradesh",
        "Kerala", "Rajasthan", "West Bengal", "Madhya Pradesh", "Punjab", "Haryana",
        "Bihar", "Telangana", "Andhra Pradesh", "Odisha", "Assam", "Goa"
    ]
    for state in indian_states:
        if re.search(rf'\b{state}\b', raw_text, re.I):
            fields["state"] = state
            break

    # 5. Masked ID Number
    aadhaar_match = re.search(r'\b(\d{4}[\s-]?\d{4}[\s-]?\d{4})\b', raw_text)
    if aadhaar_match:
        fields["id_number"] = mask_aadhaar(aadhaar_match.group(1))

    return fields

def extract_income_fields(raw_text, lines):
    """Extracts Income Certificate fields (Beneficiary, Income, Validity, Cert No, Authority)."""
    fields = {
        "beneficiary_name": None,
        "annual_income": None,
        "valid_until": None,
        "issue_date": None,
        "certificate_number": None,
        "issuing_authority": None
    }

    # 1. Beneficiary / Guardian Name
    name = _find_field_by_labels(lines, [
        r'beneficiary\s*name', r'applicant\s*name', r'name\s*of\s*applicant',
        r'candidate\s*name', r'issued\s*to', r'name'
    ])
    if name:
        fields["beneficiary_name"] = name.strip()

    # 2. Annual Income
    inc_str = _find_field_by_labels(lines, [
        r'annual\s*family\s*income', r'family\s*annual\s*income',
        r'annual\s*income', r'family\s*income', r'gross\s*income',
        r'total\s*income', r'income'
    ])
    if not inc_str:
        # Search directly for currency pattern
        m_inc = re.search(r'(?:annual|family|total|gross)?\s*income\s*[:\-\=]?\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?|\d+\.?\d*\s*lakh)', raw_text, re.I)
        if m_inc:
            inc_str = m_inc.group(1).strip()
    if inc_str:
        num = parse_currency_to_number(inc_str)
        if num is not None:
            fields["annual_income"] = num

    # 3. Validity / Valid Until
    valid_str = _find_field_by_labels(lines, [
        r'valid\s*until', r'valid\s*upto', r'valid\s*till', r'validity\s*period',
        r'expiry\s*date', r'validity'
    ])
    if not valid_str:
        m_val = re.search(r'valid\s*(?:until|upto|till)\s*[:\-\=]?\s*([0-9\/\-\.a-zA-Z\s]{8,15})', raw_text, re.I)
        if m_val:
            valid_str = m_val.group(1).strip()
    if valid_str:
        iso, dt = normalize_date(valid_str)
        fields["valid_until"] = iso if iso else valid_str

    # 4. Issue Date
    issue_str = _find_field_by_labels(lines, [r'issue\s*date', r'date\s*of\s*issue', r'dated'])
    if issue_str:
        iso, dt = normalize_date(issue_str)
        fields["issue_date"] = iso if iso else issue_str

    # 5. Certificate Number
    cert_no = _find_field_by_labels(lines, [r'certificate\s*no\.?', r'cert\s*no\.?', r'application\s*no\.?', r'ref\s*no\.?'])
    if not cert_no:
        m_cert = re.search(r'\b([A-Z]{2,4}\/[A-Z0-9\/_\-]{6,25})\b', raw_text)
        if m_cert:
            cert_no = m_cert.group(1)
    if cert_no:
        fields["certificate_number"] = cert_no.strip()

    # 6. Issuing Authority
    authorities = ["Tahsildar", "Revenue Department", "Sub-Divisional Magistrate", "Tehsildar", "Taluk Office", "District Magistrate"]
    for auth in authorities:
        if re.search(rf'\b{auth}\b', raw_text, re.I):
            fields["issuing_authority"] = auth
            break

    return fields

def extract_college_fields(raw_text, lines):
    """Extracts College / Bonafide / ID fields."""
    fields = {
        "candidate_name": None,
        "institute_name": None,
        "enrolled_course": None,
        "admission_year": None,
        "roll_number": None
    }

    # 1. Candidate Name
    name = _find_field_by_labels(lines, [r'student\s*name', r'candidate\s*name', r'name', r'name\s*of\s*student'])
    if name:
        fields["candidate_name"] = name.strip()

    # 2. Institute Name
    inst = _find_field_by_labels(lines, [r'institute\s*name', r'college\s*name', r'institution', r'university', r'college'])
    if not inst:
        for line in lines[:4]:
            if any(k in line.lower() for k in ['institute', 'college', 'university', 'technology', 'polytechnic']):
                inst = line.strip()
                break
    if inst:
        fields["institute_name"] = inst.strip()

    # 3. Enrolled Course
    course = _find_field_by_labels(lines, [r'course', r'branch', r'degree', r'enrolled\s*course', r'programme'])
    if not course:
        course_patterns = [r'b\.?tech\s*[\w\s]*', r'b\.?sc\s*[\w\s]*', r'b\.?com\s*[\w\s]*', r'm\.?tech\s*[\w\s]*', r'mbbs', r'diploma\s*[\w\s]*']
        for p in course_patterns:
            m = re.search(rf'\b({p})\b', raw_text, re.I)
            if m:
                course = m.group(1).strip()
                break
    if course:
        fields["enrolled_course"] = course.strip()

    # 4. Academic / Admission Year
    adm_year = _find_field_by_labels(lines, [r'academic\s*year', r'admission\s*year', r'year', r'batch'])
    if not adm_year:
        m_ay = re.search(r'\b(202[0-9]\s*[\-\/]\s*202[0-9]|202[0-9])\b', raw_text)
        if m_ay:
            adm_year = m_ay.group(1)
    if adm_year:
        fields["admission_year"] = adm_year.strip()

    # 5. Roll Number
    roll = _find_field_by_labels(lines, [r'roll\s*no\.?', r'enrollment\s*no\.?', r'prn', r'reg\s*no\.?'])
    if roll:
        fields["roll_number"] = roll.strip()

    return fields

def extract_marksheet_fields(raw_text, lines):
    """Extracts Marksheet / Academic Transcript fields."""
    fields = {
        "student_name": None,
        "percentage": None,
        "cgpa": None,
        "pass_status": None,
        "exam_year": None,
        "cgpa_needs_confirmation": False
    }

    # 1. Student Name
    name = _find_field_by_labels(lines, [r'student\s*name', r'candidate\s*name', r'name'])
    if name:
        fields["student_name"] = name.strip()

    # 2. Percentage
    pct_str = _find_field_by_labels(lines, [r'percentage', r'percentage\s*marks', r'aggregate\s*percentage', r'total\s*percentage'])
    if not pct_str:
        m_pct = re.search(r'(\d{1,2}(?:\.\d{1,2})?)\s*%', raw_text)
        if m_pct:
            pct_str = m_pct.group(1)
    if pct_str:
        val = parse_percentage_to_float(pct_str)
        if val is not None:
            fields["percentage"] = val

    # 3. CGPA
    cgpa_str = _find_field_by_labels(lines, [r'cgpa', r'sgpa', r'grade\s*point'])
    if not cgpa_str:
        m_cgpa = re.search(r'\b(?:cgpa|grade\s*point)\s*[:\-\=]?\s*(\d(?:\.\d{1,2})?)\b', raw_text, re.I)
        if m_cgpa:
            cgpa_str = m_cgpa.group(1)
    if cgpa_str:
        try:
            fields["cgpa"] = float(cgpa_str)
            if fields["percentage"] is None:
                # Flag manual confirmation as per guideline
                fields["cgpa_needs_confirmation"] = True
        except ValueError:
            pass

    # 4. Pass Status
    for line in lines:
        if re.search(r'\b(passed|pass|first class|distinction)\b', line, re.I):
            fields["pass_status"] = "Passed"
            break

    # 5. Exam Year
    m_yr = re.search(r'\b(202[0-9]|201[8-9])\b', raw_text)
    if m_yr:
        fields["exam_year"] = m_yr.group(1)

    return fields

def extract_bank_fields(raw_text, lines):
    """Extracts Bank Record fields (Account Holder, Bank Name, masked Account, IFSC)."""
    fields = {
        "account_holder": None,
        "bank_name": None,
        "ifsc_code": None,
        "account_number": None,
        "account_status": "Active Savings"
    }

    # 1. Account Holder
    holder = _find_field_by_labels(lines, [r'account\s*holder', r'holder\s*name', r'name', r'customer\s*name'])
    if holder:
        fields["account_holder"] = holder.strip()

    # 2. Bank Name
    banks = ["State Bank of India", "HDFC Bank", "ICICI Bank", "Punjab National Bank", "Bank of Baroda", "Canara Bank", "Union Bank of India", "Axis Bank"]
    for b in banks:
        if re.search(rf'\b{b}\b', raw_text, re.I):
            fields["bank_name"] = b
            break
    if not fields["bank_name"]:
        b_label = _find_field_by_labels(lines, [r'bank\s*name', r'bank'])
        if b_label:
            fields["bank_name"] = b_label.strip()

    # 3. IFSC Code
    m_ifsc = re.search(r'\b([A-Z]{4}0[A-Z0-9]{6})\b', raw_text)
    if m_ifsc:
        fields["ifsc_code"] = m_ifsc.group(1)

    # 4. Account Number (Masked)
    acc_val = _find_field_by_labels(lines, [r'account\s*number', r'account\s*no\.?', r'a\/c\s*no\.?'])
    if not acc_val:
        m_acc = re.search(r'(?:account\s*(?:no|number)?|a\/c\s*no\.?)\s*[:\-\=]?\s*([0-9\*\s\-X]{6,20})', raw_text, re.I)
        if m_acc:
            acc_val = m_acc.group(1)
    if acc_val:
        fields["account_number"] = mask_bank_account(acc_val)

    return fields

def extract_category_fields(raw_text, lines):
    """Extracts Category / Caste Certificate fields."""
    fields = {
        "candidate_name": None,
        "category": None,
        "certificate_number": None,
        "issue_date": None
    }

    # 1. Candidate Name
    name = _find_field_by_labels(lines, [r'name', r'candidate\s*name', r'issued\s*to'])
    if name:
        fields["candidate_name"] = name.strip()

    # 2. Category
    categories = ["OBC", "SC", "ST", "EWS", "General", "SEBC", "VJNT"]
    for cat in categories:
        if re.search(rf'\b{cat}\b', raw_text, re.I):
            fields["category"] = cat
            break

    # 3. Certificate Number
    cert = _find_field_by_labels(lines, [r'certificate\s*no\.?', r'cert\s*no\.?'])
    if cert:
        fields["certificate_number"] = cert.strip()

    # 4. Issue Date
    dt_str = _find_field_by_labels(lines, [r'issue\s*date', r'date'])
    if dt_str:
        iso, dt = normalize_date(dt_str)
        fields["issue_date"] = iso if iso else dt_str

    return fields

def extract_generic_fields(raw_text, lines):
    """Fallback extractor for unclassified documents."""
    return {
        "text_detected": len(lines) > 0,
        "line_count": len(lines)
    }
