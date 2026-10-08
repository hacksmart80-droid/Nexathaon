import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import urllib.request
import json
import os

BASE_URL = 'http://127.0.0.1:5000'

def post_json(endpoint, data):
    req = urllib.request.Request(
        f'{BASE_URL}{endpoint}',
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def test_missing_document_case():
    print("\n--- TEST CASE: Missing Document (Marksheet Omitted) ---")
    session = post_json('/api/create-check', {})
    case_id = session['caseId']
    
    # Upload only 4 documents (omit previous_marksheet)
    docs = [
        ('aadhaar_mohd_saif', 'identity_proof'),
        ('college_bonafide', 'college_proof'),
        ('income_valid', 'income_certificate'),
        ('bank_passbook', 'bank_proof')
    ]
    verified_docs = {}
    for sample_key, doc_type in docs:
        up = post_json('/api/load-sample', {'caseId': case_id, 'sampleKey': sample_key, 'docType': doc_type})
        an = post_json('/api/analyze', {'caseId': case_id, 'docType': doc_type, 'storedFilename': up['storedFilename']})
        verified_docs[doc_type] = {'filename': up['originalName'], 'fields': an['fields']}

    applicant = {
        'full_name': 'Ansari Mohd Saif', 'dob': '14/07/2007',
        'annual_income': '2,20,000', 'percentage': '78.50'
    }
    res = post_json('/api/check', {
        'caseId': case_id,
        'scholarshipId': 'post_matric_higher_ed',
        'applicant': applicant,
        'verifiedDocs': verified_docs
    })

    print(f"Score: {res['readiness']['score']}% ({res['readiness']['status_label']})")
    print(f"Missing count: {len(res['missingDocuments'])}")
    assert len(res['missingDocuments']) == 1
    assert res['missingDocuments'][0]['doc_type'] == 'previous_marksheet'
    print("✓ TEST PASSED: 1 missing document detected ('previous_marksheet') and score reduced!")

def test_expired_certificate_case():
    print("\n--- TEST CASE: Expired Certificate (Valid Until 31/03/2023) ---")
    session = post_json('/api/create-check', {})
    case_id = session['caseId']

    up = post_json('/api/load-sample', {'caseId': case_id, 'sampleKey': 'income_expired', 'docType': 'income_certificate'})
    an = post_json('/api/analyze', {'caseId': case_id, 'docType': 'income_certificate', 'storedFilename': up['storedFilename']})
    
    verified_docs = {'income_certificate': {'filename': up['originalName'], 'fields': an['fields']}}
    applicant = {'full_name': 'Ansari Mohd Saif', 'annual_income': '2,20,000'}

    res = post_json('/api/check', {
        'caseId': case_id,
        'scholarshipId': 'post_matric_higher_ed',
        'applicant': applicant,
        'verifiedDocs': verified_docs
    })

    expired_flag = any('expired' in att['title'].lower() or 'expired' in att.get('detail', '').lower() for att in res['needsAttention'])
    print(f"Certificate validity warning detected: {expired_flag}")
    assert expired_flag
    print("✓ TEST PASSED: Expired income certificate properly flagged in Needs Attention!")

def test_income_limit_exceeded_case():
    print("\n--- TEST CASE: Income Exceeds Limit (₹3,50,000 vs ₹2,50,000 Limit) ---")
    session = post_json('/api/create-check', {})
    case_id = session['caseId']

    up = post_json('/api/load-sample', {'caseId': case_id, 'sampleKey': 'income_high', 'docType': 'income_certificate'})
    an = post_json('/api/analyze', {'caseId': case_id, 'docType': 'income_certificate', 'storedFilename': up['storedFilename']})
    
    verified_docs = {'income_certificate': {'filename': up['originalName'], 'fields': an['fields']}}
    applicant = {'full_name': 'Ansari Mohd Saif', 'annual_income': '3,50,000'}

    res = post_json('/api/check', {
        'caseId': case_id,
        'scholarshipId': 'post_matric_higher_ed',
        'applicant': applicant,
        'verifiedDocs': verified_docs
    })

    income_warn = any('income' in att['title'].lower() for att in res['needsAttention'])
    print(f"Income ceiling warning detected: {income_warn}")
    assert income_warn
    print("✓ TEST PASSED: Income above scheme limit flagged as Needs Attention!")

def test_ocr_failure_fallback():
    print("\n--- TEST CASE: Unreadable Blurry Image Fallback ---")
    session = post_json('/api/create-check', {})
    case_id = session['caseId']

    up = post_json('/api/load-sample', {'caseId': case_id, 'sampleKey': 'unreadable_blurry', 'docType': 'identity_proof'})
    an = post_json('/api/analyze', {'caseId': case_id, 'docType': 'identity_proof', 'storedFilename': up['storedFilename']})
    print(f"OCR Error message: {an.get('ocrError')}")
    print(f"Fields returned safely: {an['fields']}")
    assert an['fields']['full_name'] is None
    print("✓ TEST PASSED: Unreadable image handled gracefully without crashing!")

if __name__ == '__main__':
    test_missing_document_case()
    test_expired_certificate_case()
    test_income_limit_exceeded_case()
    test_ocr_failure_fallback()
    print("\n" + "="*60)
    print("ALL SPECIFIED TEST CASES PASSED!")
    print("="*60)
