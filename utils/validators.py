from config import ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH
from utils.helpers import parse_currency_to_number, parse_percentage_to_float, normalize_date

def is_allowed_file(filename):
    """Checks if file extension is allowed."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def validate_file_size(size_bytes):
    """Checks if file size is within limits."""
    return 0 < size_bytes <= MAX_CONTENT_LENGTH

def validate_applicant_data(data):
    """
    Validates applicant profile input fields.
    Returns (is_valid, errors_dict)
    """
    errors = {}
    if not isinstance(data, dict):
        return False, {"general": "Invalid data format."}
        
    name = (data.get('full_name') or '').strip()
    if not name:
        errors['full_name'] = "Full Name is required."
    elif len(name) < 2:
        errors['full_name'] = "Full Name must be at least 2 characters."
        
    dob = (data.get('dob') or '').strip()
    if dob:
        iso_date, dt = normalize_date(dob)
        if not dt:
            errors['dob'] = "Please provide a valid date (e.g. DD/MM/YYYY or YYYY-MM-DD)."
            
    income = data.get('annual_income')
    if income is not None and str(income).strip() != "":
        parsed_inc = parse_currency_to_number(income)
        if parsed_inc is None or parsed_inc < 0:
            errors['annual_income'] = "Please enter a valid positive income amount."
            
    percentage = data.get('percentage')
    if percentage is not None and str(percentage).strip() != "":
        parsed_pct = parse_percentage_to_float(percentage)
        if parsed_pct is None or parsed_pct < 0 or parsed_pct > 100:
            errors['percentage'] = "Percentage must be between 0.0% and 100.0%."
            
    return len(errors) == 0, errors
