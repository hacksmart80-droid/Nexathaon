import os
import re
import uuid
import secrets
import shutil
import time
from datetime import datetime, date
from werkzeug.utils import secure_filename
from config import TEMP_CASES_DIR, CASE_EXPIRY_SECONDS

def generate_case_id():
    """Generates a UUID for internal tracking."""
    return str(uuid.uuid4())

def generate_reference_number():
    """Generates a friendly ScholarProof check reference like SP-2026-A7C24F."""
    current_year = datetime.now().year
    random_hex = secrets.token_hex(3).upper()
    return f"SP-{current_year}-{random_hex}"

def sanitize_filename(filename):
    """Sanitizes file name and prevents path traversal."""
    cleaned = secure_filename(filename)
    if not cleaned:
        cleaned = f"doc_{int(time.time())}.dat"
    return cleaned

def mask_aadhaar(text):
    """
    Detects 12-digit Aadhaar patterns and masks all except the last 4 digits.
    Example: 1234 5678 9012 -> XXXX XXXX 9012
    """
    if not text:
        return text
    def _mask(m):
        raw = m.group(0).replace(' ', '').replace('-', '')
        return f"XXXX XXXX {raw[-4:]}"
    pattern = r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'
    return re.sub(pattern, _mask, str(text))

def mask_bank_account(account_str):
    """
    Masks bank account numbers to preserve privacy: XXXXXX1234
    """
    if not account_str:
        return ""
    digits = re.sub(r'\D', '', str(account_str))
    if len(digits) >= 4:
        return f"XXXXXX{digits[-4:]}"
    return "XXXXXX"

def parse_currency_to_number(val_str):
    """
    Parses currency strings into an integer INR amount.
    Supports:
    ₹2,20,000 | Rs. 220000 | INR 220000 | 2.20 Lakh | 2,50,000 | 250000
    """
    if val_str is None:
        return None
    if isinstance(val_str, (int, float)):
        return int(val_str)
    
    clean = str(val_str).strip()
    # Check for 'lakh' or 'lac'
    lakh_match = re.search(r'([\d.]+)\s*(?:lakh|lac)s?', clean, re.I)
    if lakh_match:
        try:
            return int(float(lakh_match.group(1)) * 100000)
        except ValueError:
            pass
            
    # Remove currency symbols and OCR artifacts (like 'I' or 'l' replacing '₹' before digits)
    clean = re.sub(r'^[Il\s₹]+(?=\d)', '', clean)
    clean = re.sub(r'[₹Rs\.INRn\s,]', '', clean, flags=re.I)
    match = re.search(r'\d+', clean)
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            return None
    return None

def parse_percentage_to_float(val_str):
    """
    Extracts percentage from string, e.g. '78.50%', '65%' -> 78.5
    """
    if val_str is None:
        return None
    if isinstance(val_str, (int, float)):
        return float(val_str)
    match = re.search(r'(\d+(?:\.\d+)?)', str(val_str))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None

def normalize_date(date_str):
    """
    Normalizes various date formats into ISO 'YYYY-MM-DD' and returns a python date object.
    Supports:
    - 14/07/2007, 14-07-2007
    - 2007-07-14, 2007/07/14
    - 14 Jul 2007, 14 July 2007
    - 31 March 2027
    """
    if not date_str:
        return None, None
    clean = str(date_str).strip()
    
    date_formats = [
        "%d/%m/%Y", "%d-%m-%Y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d %b %Y", "%d %B %Y",
        "%d-%b-%Y", "%d-%B-%Y",
        "%b %d, %Y", "%B %d, %Y"
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(clean, fmt).date()
            return dt.isoformat(), dt
        except ValueError:
            continue
            
    # Fallback heuristic: search for DD/MM/YYYY or YYYY-MM-DD in text
    match_dmy = re.search(r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b', clean)
    if match_dmy:
        d, m, y = match_dmy.groups()
        try:
            dt = datetime(int(y), int(m), int(d)).date()
            return dt.isoformat(), dt
        except ValueError:
            pass
            
    match_ymd = re.search(r'\b(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})\b', clean)
    if match_ymd:
        y, m, d = match_ymd.groups()
        try:
            dt = datetime(int(y), int(m), int(d)).date()
            return dt.isoformat(), dt
        except ValueError:
            pass
            
    return None, None

def get_case_folder(case_id):
    """Returns the base directory for a given case."""
    folder = os.path.join(TEMP_CASES_DIR, case_id)
    os.makedirs(os.path.join(folder, 'uploads'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'processed'), exist_ok=True)
    os.makedirs(os.path.join(folder, 'report'), exist_ok=True)
    return folder

def cleanup_case_folder(case_id):
    """Deletes temporary folder for a given case."""
    folder = os.path.join(TEMP_CASES_DIR, case_id)
    if os.path.exists(folder):
        shutil.rmtree(folder, ignore_errors=True)

def cleanup_stale_cases():
    """Removes temporary case folders older than CASE_EXPIRY_SECONDS."""
    if not os.path.exists(TEMP_CASES_DIR):
        return
    now = time.time()
    for entry in os.listdir(TEMP_CASES_DIR):
        case_path = os.path.join(TEMP_CASES_DIR, entry)
        if os.path.isdir(case_path):
            try:
                mtime = os.path.getmtime(case_path)
                if now - mtime > CASE_EXPIRY_SECONDS:
                    shutil.rmtree(case_path, ignore_errors=True)
            except Exception:
                pass
