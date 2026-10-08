import urllib.request
import json
import os
import pymupdf

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'http://127.0.0.1:5000'

def post_json(endpoint, data):
    req = urllib.request.Request(
        f'{BASE_URL}{endpoint}',
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

def get_json(endpoint):
    with urllib.request.urlopen(f'{BASE_URL}{endpoint}') as resp:
        return json.loads(resp.read().decode('utf-8'))

def test_full_pipeline():
    print("="*60)
    print("1. Creating New Check Session")
    print("="*60)
    session = post_json('/api/create-check', {})
    case_id = session['caseId']
    ref_no = session['referenceNumber']
    print(f"Case ID: {case_id} | Reference: {ref_no}")

    print("\n" + "="*60)
    print("2. Retrieving Configured Scholarships")
    print("="*60)
    sch_list = get_json('/api/scholarships')
    print(f"Total schemes available: {len(sch_list)}")
    for s in sch_list:
        print(f" - [{s['id']}] {s['name']} (Limit: ₹{s.get('income_limit', 0):,})")

    print("\n" + "="*60)
    print("3. Staging Demo Documents in Upload Pipeline")
    print("="*60)
    docs_to_load = [
        ('aadhaar_mohd_saif', 'identity_proof'),
        ('college_bonafide', 'college_proof'),
        ('income_valid', 'income_certificate'),
        ('marksheet_passed', 'previous_marksheet'),
        ('bank_passbook', 'bank_proof')
    ]

    uploaded_docs = []
    for sample_key, doc_type in docs_to_load:
        res = post_json('/api/load-sample', {
            'caseId': case_id,
            'sampleKey': sample_key,
            'docType': doc_type
        })
        uploaded_docs.append(res)
        print(f"✓ Uploaded {doc_type}: {res['storedFilename']} ({res['sizeFormatted']})")

    print("\n" + "="*60)
    print("4. Executing OCR & Field Extraction on Staged Documents")
    print("="*60)
    verified_docs = {}
    for doc in uploaded_docs:
        an_res = post_json('/api/analyze', {
            'caseId': case_id,
            'docType': doc['docType'],
            'storedFilename': doc['storedFilename']
        })
        verified_docs[doc['docType']] = {
            'filename': doc['originalName'],
            'fields': an_res['fields']
        }
        print(f"\n[Document: {doc['docType']}]")
        for k, v in an_res['fields'].items():
            print(f"   {k}: {v}")

    print("\n" + "="*60)
    print("5. Evaluating Cross-Document Parity, Rules & Readiness")
    print("="*60)
    applicant = {
        'full_name': 'Ansari Mohd Saif',
        'dob': '14/07/2007',
        'gender': 'Male',
        'category': 'General',
        'state': 'Maharashtra',
        'institute': 'Pune Institute of Eng.',
        'course': 'B.Tech Comp (Yr 2)',
        'academic_year': '2023-2024',
        'annual_income': '2,20,000',
        'percentage': '78.50'
    }

    check_result = post_json('/api/check', {
        'caseId': case_id,
        'referenceNumber': ref_no,
        'scholarshipId': 'post_matric_higher_ed',
        'applicant': applicant,
        'verifiedDocs': verified_docs
    })

    readiness = check_result['readiness']
    print(f"\nREADINESS SCORE: {readiness['score']}% — {readiness['status_label']}")
    print(f"Summary: {readiness['summary_text']}")
    print(f"Breakdown:")
    for k, v in readiness['breakdown'].items():
        print(f"   {k}: {v['score']} / {v['max']} points")

    print(f"\nPassed Checks ({len(check_result['checksPassed'])}):")
    for chk in check_result['checksPassed']:
        print(f"   ✓ {chk['title']}")

    print(f"\nNeeds Attention ({len(check_result['needsAttention'])}):")
    for att in check_result['needsAttention']:
        print(f"   ⚠ [{att.get('severity')}] {att['title']}")
        if att.get('explanation'):
            print(f"      Found: {att['explanation'].get('what_we_found')}")
            print(f"      Action: {att['explanation'].get('what_to_do_next')}")

    print(f"\nMissing Mandatory Documents: {len(check_result['missingDocuments'])}")

    print("\n" + "="*60)
    print("6. Generating Real PDF Pre-Check Report")
    print("="*60)
    report_res = post_json('/api/generate-report', check_result)
    print(f"Report URL: {report_res['downloadUrl']}")

    # Download report
    download_url = f"{BASE_URL}{report_res['downloadUrl']}"
    local_pdf = 'downloaded_test_report.pdf'
    urllib.request.urlretrieve(download_url, local_pdf)
    print(f"Downloaded PDF size: {os.path.getsize(local_pdf)} bytes")

    # Verify PDF content with PyMuPDF
    pdf_doc = pymupdf.open(local_pdf)
    print(f"Verified PDF page count: {len(pdf_doc)}")
    p1 = pdf_doc[0].get_text('text')
    assert "SCHOLARPROOF" in p1
    assert "APPLICATION PRE-CHECK REPORT" in p1
    assert ref_no in p1
    print("✓ Successfully verified PDF branding, reference number, and sections!")
    pdf_doc.close()

    print("\n" + "="*60)
    print("ALL WORKFLOW STEPS PASSED SUCCESSFULLY!")
    print("="*60)

if __name__ == '__main__':
    test_full_pipeline()
