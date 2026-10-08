import re
from datetime import datetime, date
from rapidfuzz import fuzz
from utils.helpers import normalize_date

# Common abbreviations and title honorifics to assist matching
NAME_EQUIVALENTS = {
    'mohd': 'mohammed',
    'md': 'mohammed',
    'mohammad': 'mohammed',
    'mohamad': 'mohammed',
    'shk': 'shaikh',
    'shk.': 'shaikh',
    'kum': 'kumar',
    'kr': 'kumar'
}

TITLES_TO_REMOVE = {'mr', 'mrs', 'ms', 'shri', 'smt', 'kumari', 'master', 'dr'}

def clean_and_normalize_name(name_str):
    """
    Cleans name: lowercase, strip punctuation, remove titles, collapse whitespace.
    """
    if not name_str:
        return ""
    text = str(name_str).lower()
    # Remove dots and punctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    tokens = text.split()
    # Filter common title tokens
    tokens = [t for t in tokens if t not in TITLES_TO_REMOVE]
    return " ".join(tokens)

def expand_abbreviations(tokens):
    """Replaces common abbreviations with canonical forms for comparison."""
    expanded = []
    for t in tokens:
        expanded.append(NAME_EQUIVALENTS.get(t, t))
    return expanded

def compare_names(name1, name2):
    """
    Compares two names using RapidFuzz and abbreviation heuristics.
    Returns:
    {
        "state": "MATCH" | "POSSIBLE_MATCH" | "MISMATCH",
        "label": "✓ Names appear consistent" | "⚠ Names are similar but not identical" | "✕ Names appear different",
        "score": float (0-100),
        "notes": str or None
    }
    """
    norm1 = clean_and_normalize_name(name1)
    norm2 = clean_and_normalize_name(name2)

    if not norm1 or not norm2:
        return {
            "state": "UNVERIFIED",
            "label": "? Could not verify name match",
            "score": 0.0,
            "notes": "One or both names were not detected."
        }

    # Exact normalized match
    if norm1 == norm2:
        return {
            "state": "MATCH",
            "label": "✓ Names appear consistent",
            "score": 100.0,
            "notes": "Exact character match across documents."
        }

    tokens1 = norm1.split()
    tokens2 = norm2.split()

    # Expand abbreviations
    exp1 = " ".join(expand_abbreviations(tokens1))
    exp2 = " ".join(expand_abbreviations(tokens2))

    if exp1 == exp2:
        return {
            "state": "POSSIBLE_MATCH",
            "label": "⚠ Names are similar but not identical",
            "score": 92.0,
            "notes": f"Detected abbreviation variance (e.g., '{norm1}' vs '{norm2}'). Scholarship portals may require consistent spelling."
        }

    # Token sort & set ratios handle name reordering (e.g. 'Saif Ansari' vs 'Ansari Saif')
    ratio = fuzz.ratio(norm1, norm2)
    sort_ratio = fuzz.token_sort_ratio(norm1, norm2)
    set_ratio = fuzz.token_set_ratio(norm1, norm2)
    exp_sort_ratio = fuzz.token_sort_ratio(exp1, exp2)

    effective_score = max(ratio, sort_ratio, set_ratio, exp_sort_ratio)

    if effective_score >= 95:
        return {
            "state": "MATCH",
            "label": "✓ Names appear consistent",
            "score": round(effective_score, 1),
            "notes": "Names match with minor character or order variance."
        }
    elif effective_score >= 70:
        return {
            "state": "POSSIBLE_MATCH",
            "label": "⚠ Names are similar but not identical",
            "score": round(effective_score, 1),
            "notes": f"Potential name difference between '{name1}' and '{name2}'. Verify spelling matches official guidelines."
        }
    else:
        return {
            "state": "MISMATCH",
            "label": "✕ Names appear different",
            "score": round(effective_score, 1),
            "notes": f"Names do not appear to match: '{name1}' vs '{name2}'."
        }

def compare_dates_of_birth(dob1, dob2):
    """
    Normalizes and compares two dates of birth.
    Returns:
    {
        "state": "MATCH" | "MISMATCH" | "UNVERIFIED",
        "label": str,
        "iso1": str,
        "iso2": str
    }
    """
    iso1, dt1 = normalize_date(dob1)
    iso2, dt2 = normalize_date(dob2)

    if not dt1 or not dt2:
        return {
            "state": "UNVERIFIED",
            "label": "? Date of birth could not be verified",
            "iso1": iso1,
            "iso2": iso2,
            "notes": "Date of birth missing or could not be parsed from one of the documents."
        }

    if dt1 == dt2:
        return {
            "state": "MATCH",
            "label": f"✓ DOB matches properly ({dt1.strftime('%d %B %Y')}) across records",
            "iso1": iso1,
            "iso2": iso2,
            "notes": "Exact date of birth match."
        }
    else:
        return {
            "state": "MISMATCH",
            "label": f"✕ DOB discrepancy ({iso1} vs {iso2})",
            "iso1": iso1,
            "iso2": iso2,
            "notes": f"Recorded dates of birth differ: {iso1} vs {iso2}."
        }

def check_certificate_validity(valid_until_str, reference_date=None):
    """
    Checks if a certificate's expiry date is valid compared to current/reference date.
    Returns:
    {
        "state": "VALID" | "EXPIRING_SOON" | "EXPIRED" | "UNKNOWN",
        "label": str,
        "expiry_iso": str or None,
        "days_remaining": int or None
    }
    """
    if not valid_until_str:
        return {
            "state": "UNKNOWN",
            "label": "? Validity date not specified",
            "expiry_iso": None,
            "days_remaining": None,
            "notes": "Certificate validity date was not detected."
        }

    iso_exp, exp_dt = normalize_date(valid_until_str)
    if not exp_dt:
        return {
            "state": "UNKNOWN",
            "label": f"? Could not parse validity date ({valid_until_str})",
            "expiry_iso": None,
            "days_remaining": None,
            "notes": "Format could not be resolved."
        }

    ref = reference_date if reference_date else date.today()
    delta = (exp_dt - ref).days

    if delta < 0:
        return {
            "state": "EXPIRED",
            "label": f"✕ Certificate expired on {exp_dt.strftime('%d %b %Y')}",
            "expiry_iso": iso_exp,
            "days_remaining": delta,
            "notes": f"Certificate expired {abs(delta)} days ago. Renewal required for submission."
        }
    elif delta <= 60:
        return {
            "state": "EXPIRING_SOON",
            "label": f"⚠ Expiry date approaching ({exp_dt.strftime('%d %b %Y')})",
            "expiry_iso": iso_exp,
            "days_remaining": delta,
            "notes": f"Certificate is valid but expires in {delta} days. Check if it remains valid throughout processing."
        }
    else:
        return {
            "state": "VALID",
            "label": f"✓ Certificate is current and valid through {exp_dt.strftime('%d %B %Y')}",
            "expiry_iso": iso_exp,
            "days_remaining": delta,
            "notes": "Appears well within valid date window."
        }
