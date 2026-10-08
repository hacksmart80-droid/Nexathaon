/**
 * ScholarProof — Complete Client-Side Application Controller
 * Connects Google Stitch UI to Flask backend APIs
 */

(function () {
  'use strict';

  // Master Application State
  const state = {
    caseId: null,
    referenceNumber: null,
    scholarships: [],
    selectedScholarship: null,
    applicant: {
      full_name: '',
      dob: '',
      gender: 'Male',
      category: 'General',
      state: 'Maharashtra',
      institute: '',
      course: '',
      academic_year: '2nd Year (2024-25)',
      annual_income: '',
      percentage: ''
    },
    uploadedDocuments: [], // Array of { docType, originalName, storedFilename, sizeFormatted, formatLabel }
    extractedData: {},     // docType -> { fields: {...}, rawText: "..." }
    verifiedDocs: {},      // docType -> { filename: "...", fields: {...} }
    checkResults: null,
    currentStep: 0,        // 0: Home, 1: Scheme, 2: Details, 3: Upload, 4: Review, 5: Results
    editingTarget: null    // { docType, fieldKey, fieldLabel }
  };

  // DOM Elements
  const screens = {
    home: document.getElementById('screenHome'),
    step1: document.getElementById('screenStep1'),
    step2: document.getElementById('screenStep2'),
    step3: document.getElementById('screenStep3'),
    step4: document.getElementById('screenStep4'),
    step5: document.getElementById('screenStep5')
  };

  const stepperContainer = document.getElementById('stepperContainer');
  const stepIndicators = [
    null,
    document.getElementById('stepIndicator1'),
    document.getElementById('stepIndicator2'),
    document.getElementById('stepIndicator3'),
    document.getElementById('stepIndicator4'),
    document.getElementById('stepIndicator5')
  ];
  const stepLines = [
    null,
    document.getElementById('stepLine1'),
    document.getElementById('stepLine2'),
    document.getElementById('stepLine3'),
    document.getElementById('stepLine4')
  ];

  const processingModal = document.getElementById('processingModal');
  const editFieldModal = document.getElementById('editFieldModal');
  const editModalFieldLabel = document.getElementById('editModalFieldLabel');
  const editModalInput = document.getElementById('editModalInput');

  // Initialization
  async function init() {
    setupEventListeners();
    await createOrRestoreCase();
    await fetchScholarships();
  }

  // --------------------------------------------------------------------------
  // API Calls
  // --------------------------------------------------------------------------
  async function createOrRestoreCase() {
    try {
      const res = await fetch('/api/create-check', { method: 'POST' });
      const data = await res.json();
      state.caseId = data.caseId;
      state.referenceNumber = data.referenceNumber;
      const refEl = document.getElementById('caseRefDisplay');
      if (refEl) refEl.textContent = `Check Ref: ${state.referenceNumber}`;
    } catch (e) {
      console.error('Failed to create check case:', e);
    }
  }

  async function fetchScholarships() {
    try {
      const res = await fetch('/api/scholarships');
      const data = await res.json();
      state.scholarships = data;
      if (data.length > 0) {
        state.selectedScholarship = data[0];
      }
      renderScholarshipCards();
      renderSelectedCriteria();
    } catch (e) {
      console.error('Failed to fetch scholarships:', e);
    }
  }

  // --------------------------------------------------------------------------
  // Navigation & Step Control
  // --------------------------------------------------------------------------
  function goToStep(stepNum) {
    state.currentStep = stepNum;

    // Show or hide stepper
    if (stepNum === 0) {
      stepperContainer.style.display = 'none';
    } else {
      stepperContainer.style.display = 'block';
      updateStepperUI(stepNum);
    }

    // Switch screens
    Object.values(screens).forEach(s => s.classList.remove('active'));

    switch (stepNum) {
      case 0:
        screens.home.classList.add('active');
        break;
      case 1:
        screens.step1.classList.add('active');
        break;
      case 2:
        syncApplicantForm();
        screens.step2.classList.add('active');
        break;
      case 3:
        updateUploadChecklistCoverage();
        screens.step3.classList.add('active');
        break;
      case 4:
        renderReviewScreen();
        screens.step4.classList.add('active');
        break;
      case 5:
        renderResultsScreen();
        screens.step5.classList.add('active');
        break;
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function updateStepperUI(activeStep) {
    for (let i = 1; i <= 5; i++) {
      const ind = stepIndicators[i];
      if (!ind) continue;
      ind.classList.remove('active', 'completed');

      if (i < activeStep) {
        ind.classList.add('completed');
        ind.querySelector('.step-num').innerHTML = '&#10003;';
      } else if (i === activeStep) {
        ind.classList.add('active');
        ind.querySelector('.step-num').textContent = i;
      } else {
        ind.querySelector('.step-num').textContent = i;
      }
    }

    for (let j = 1; j <= 4; j++) {
      const line = stepLines[j];
      if (!line) continue;
      if (j < activeStep) {
        line.classList.add('completed');
      } else {
        line.classList.remove('completed');
      }
    }
  }

  // --------------------------------------------------------------------------
  // Step 1: Scholarship Selection & Criteria
  // --------------------------------------------------------------------------
  function renderScholarshipCards(filterText = '') {
    const container = document.getElementById('scholarshipsCardsContainer');
    if (!container) return;
    container.innerHTML = '';

    const query = filterText.toLowerCase().trim();
    const filtered = state.scholarships.filter(s => {
      return s.name.toLowerCase().includes(query) ||
             (s.description && s.description.toLowerCase().includes(query)) ||
             (s.provider && s.provider.toLowerCase().includes(query));
    });

    filtered.forEach(sch => {
      const isSelected = state.selectedScholarship && state.selectedScholarship.id === sch.id;
      const card = document.createElement('div');
      card.className = `scheme-card ${isSelected ? 'selected' : ''}`;
      card.dataset.id = sch.id;

      const incLimitFormatted = sch.income_limit ? `₹${sch.income_limit.toLocaleString('en-IN')} / year` : 'No Cap';
      const minMarksFormatted = sch.minimum_percentage ? `Min ${sch.minimum_percentage}%` : 'Standard';

      card.innerHTML = `
        <div class="scheme-card-header">
          <span class="badge ${isSelected ? 'badge-danger' : 'badge-neutral'}">${sch.tag || 'Scheme'}</span>
          ${isSelected ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="var(--primary)" stroke="#fff" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="16 9 10 15 7 12"></polyline></svg>' : '<div style="width:16px;height:16px;border-radius:50%;border:1px solid var(--border-hover);"></div>'}
        </div>
        <div class="scheme-card-title">${sch.name}</div>
        <div class="scheme-card-target">${sch.target_level || 'Higher Education'}</div>
        <div class="scheme-card-desc">${sch.description || ''}</div>
        <div class="scheme-card-criteria-row">
          <div class="crit-item">
            <span class="crit-label">Income Limit</span>
            <span class="crit-val">${incLimitFormatted}</span>
          </div>
          <div class="crit-item">
            <span class="crit-label">Qualifying Marks</span>
            <span class="crit-val">${minMarksFormatted}</span>
          </div>
        </div>
        <div class="scheme-card-footer">
          <span>Deadline: ${sch.deadline || '31 Dec 2026'}</span>
          <span style="font-weight: 600; color: ${isSelected ? 'var(--primary)' : 'var(--text-secondary)'};">
            ${isSelected ? 'Selected Scheme' : 'Click to select &rarr;'}
          </span>
        </div>
      `;

      card.addEventListener('click', () => {
        state.selectedScholarship = sch;
        renderScholarshipCards(filterText);
        renderSelectedCriteria();
      });

      container.appendChild(card);
    });
  }

  function renderSelectedCriteria() {
    const sch = state.selectedScholarship;
    if (!sch) return;

    document.getElementById('selectedSchemeTitle').textContent = sch.name;
    document.getElementById('critIncomeLimit').textContent = sch.income_limit ? `Up to ₹${sch.income_limit.toLocaleString('en-IN')}` : 'No Ceiling';
    document.getElementById('critMinMarks').textContent = sch.minimum_percentage ? `${sch.minimum_percentage}% Aggregate` : 'Pass Grade';
    document.getElementById('critCourses').textContent = sch.education_levels ? sch.education_levels.slice(0, 3).join(', ') + '...' : 'All Degrees';

    const matrix = document.getElementById('requiredDocsListMatrix');
    if (!matrix) return;
    matrix.innerHTML = '';

    const docLabels = {
      identity_proof: { name: 'Identity Proof', sub: 'Aadhaar card or Voter ID' },
      income_certificate: { name: 'Income Certificate', sub: 'Competent State Authority' },
      college_proof: { name: 'College Admission Proof', sub: 'Fee receipt / Bonafide letter' },
      previous_marksheet: { name: 'Previous Marksheet', sub: 'Class 12th or Semester record' },
      bank_proof: { name: 'Bank Passbook / Statement', sub: 'Clear IFSC & Account Number' },
      category_certificate: { name: 'Domicile / Category Proof', sub: 'Caste / EWS / Residence slip' }
    };

    const reqKeys = sch.required_documents || [];
    reqKeys.forEach(k => {
      const meta = docLabels[k] || { name: k.replace('_', ' ').toUpperCase(), sub: 'Required document' };
      const tile = document.createElement('div');
      tile.className = 'doc-req-tile';
      tile.innerHTML = `
        <svg class="check-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
        <div>
          <div style="font-size: 12px; font-weight: 700; color: var(--text-primary);">${meta.name}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${meta.sub}</div>
        </div>
      `;
      matrix.appendChild(tile);
    });
  }

  // --------------------------------------------------------------------------
  // Step 2: Applicant Details
  // --------------------------------------------------------------------------
  function syncApplicantForm() {
    const a = state.applicant;
    document.getElementById('inpFullName').value = a.full_name || '';
    document.getElementById('inpDob').value = a.dob || '';
    document.getElementById('inpGender').value = a.gender || 'Male';
    document.getElementById('inpCategory').value = a.category || 'General';
    document.getElementById('inpState').value = a.state || '';
    document.getElementById('inpInstitute').value = a.institute || '';
    document.getElementById('inpCourse').value = a.course || '';
    document.getElementById('inpAcademicYear').value = a.academic_year || '';
    document.getElementById('inpIncome').value = a.annual_income || '';
    document.getElementById('inpPercentage').value = a.percentage || '';
  }

  function validateApplicantForm() {
    let isValid = true;
    const nameInput = document.getElementById('inpFullName');
    const dobInput = document.getElementById('inpDob');
    const instInput = document.getElementById('inpInstitute');
    const incInput = document.getElementById('inpIncome');
    const pctInput = document.getElementById('inpPercentage');

    // Name
    if (!nameInput.value.trim()) {
      nameInput.classList.add('invalid');
      isValid = false;
    } else {
      nameInput.classList.remove('invalid');
      state.applicant.full_name = nameInput.value.trim();
    }

    // DOB
    if (!dobInput.value.trim()) {
      dobInput.classList.add('invalid');
      isValid = false;
    } else {
      dobInput.classList.remove('invalid');
      state.applicant.dob = dobInput.value.trim();
    }

    // Institute
    if (!instInput.value.trim()) {
      instInput.classList.add('invalid');
      isValid = false;
    } else {
      instInput.classList.remove('invalid');
      state.applicant.institute = instInput.value.trim();
    }

    // Income
    if (!incInput.value.trim()) {
      incInput.classList.add('invalid');
      isValid = false;
    } else {
      incInput.classList.remove('invalid');
      state.applicant.annual_income = incInput.value.trim();
    }

    // Others
    state.applicant.gender = document.getElementById('inpGender').value;
    state.applicant.category = document.getElementById('inpCategory').value;
    state.applicant.state = document.getElementById('inpState').value.trim();
    state.applicant.course = document.getElementById('inpCourse').value.trim();
    state.applicant.academic_year = document.getElementById('inpAcademicYear').value.trim();
    state.applicant.percentage = pctInput.value.trim();

    return isValid;
  }

  function autofillDemoApplicant() {
    state.applicant = {
      full_name: 'Ansari Mohd Saif',
      dob: '14/07/2007',
      gender: 'Male',
      category: 'General',
      state: 'Maharashtra',
      institute: 'Pune Institute of Eng.',
      course: 'B.Tech Comp (Yr 2)',
      academic_year: '2023-2024',
      annual_income: '2,20,000',
      percentage: '78.50'
    };
    syncApplicantForm();
  }

  // --------------------------------------------------------------------------
  // Step 3: Document Uploads & Queue Management
  // --------------------------------------------------------------------------
  async function uploadFile(file, docType) {
    if (!file) return;
    const formData = new FormData();
    formData.append('caseId', state.caseId);
    formData.append('docType', docType);
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (data.success) {
        // Replace existing upload of same type if present, or push
        const existingIdx = state.uploadedDocuments.findIndex(d => d.docType === docType);
        if (existingIdx >= 0) {
          state.uploadedDocuments[existingIdx] = data;
        } else {
          state.uploadedDocuments.push(data);
        }
        renderUploadedFilesList();
        updateUploadChecklistCoverage();
      } else {
        alert(data.error || 'Failed to upload document.');
      }
    } catch (e) {
      console.error('Upload error:', e);
      alert('Upload failed. Please check network connection.');
    }
  }

  async function loadSampleDocument(sampleKey, docType) {
    try {
      const res = await fetch('/api/load-sample', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          caseId: state.caseId,
          sampleKey: sampleKey,
          docType: docType
        })
      });
      const data = await res.json();
      if (data.success) {
        const existingIdx = state.uploadedDocuments.findIndex(d => d.docType === docType);
        if (existingIdx >= 0) {
          state.uploadedDocuments[existingIdx] = data;
        } else {
          state.uploadedDocuments.push(data);
        }
        renderUploadedFilesList();
        updateUploadChecklistCoverage();
      }
    } catch (e) {
      console.error('Error loading sample doc:', e);
    }
  }

  async function loadCompleteDemoSet() {
    autofillDemoApplicant();
    await loadSampleDocument('aadhaar_mohd_saif', 'identity_proof');
    await loadSampleDocument('college_bonafide', 'college_proof');
    await loadSampleDocument('income_valid', 'income_certificate');
    await loadSampleDocument('marksheet_passed', 'previous_marksheet');
    await loadSampleDocument('bank_passbook', 'bank_proof');
  }

  async function loadMissingDocDemoSet() {
    autofillDemoApplicant();
    // Remove previous marksheet if present
    state.uploadedDocuments = state.uploadedDocuments.filter(d => d.docType !== 'previous_marksheet');
    await loadSampleDocument('aadhaar_mohd_saif', 'identity_proof');
    await loadSampleDocument('college_bonafide', 'college_proof');
    await loadSampleDocument('income_valid', 'income_certificate');
    await loadSampleDocument('bank_passbook', 'bank_proof');
  }

  function renderUploadedFilesList() {
    const list = document.getElementById('filesQueueList');
    const badge = document.getElementById('uploadedFilesCountBadge');
    if (!list) return;

    badge.textContent = `(${state.uploadedDocuments.length} Files)`;

    if (state.uploadedDocuments.length === 0) {
      list.innerHTML = `
        <div style="font-size: 13px; color: var(--text-muted); padding: 14px 0; text-align: center;">
          No documents uploaded yet. Choose a document type above and drop or select files.
        </div>
      `;
      return;
    }

    list.innerHTML = '';
    state.uploadedDocuments.forEach(doc => {
      const row = document.createElement('div');
      row.className = 'file-row-item';
      row.innerHTML = `
        <div class="file-info-group">
          <div class="file-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
          </div>
          <div class="file-name-meta">
            <div class="file-name">
              <span>${doc.originalName}</span>
              <span class="badge badge-success">✓ Ready</span>
            </div>
            <div class="file-meta-sub">
              ${doc.sizeFormatted} &bull; ${doc.formatLabel} &bull; ${formatDocTypeName(doc.docType)}
            </div>
          </div>
        </div>
        <div class="file-actions">
          <button class="btn-icon-link btn-delete-file" data-type="${doc.docType}" type="button" title="Delete file">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      `;

      row.querySelector('.btn-delete-file').addEventListener('click', (e) => {
        const typeToRemove = e.currentTarget.dataset.type;
        state.uploadedDocuments = state.uploadedDocuments.filter(d => d.docType !== typeToRemove);
        delete state.extractedData[typeToRemove];
        delete state.verifiedDocs[typeToRemove];
        renderUploadedFilesList();
        updateUploadChecklistCoverage();
      });

      list.appendChild(row);
    });
  }

  function updateUploadChecklistCoverage() {
    const sch = state.selectedScholarship;
    const container = document.getElementById('coverageChecklistContainer');
    const badge = document.getElementById('coverageCountBadge');
    if (!sch || !container) return;

    const reqKeys = sch.required_documents || [];
    const uploadedMap = {};
    state.uploadedDocuments.forEach(d => {
      uploadedMap[d.docType] = d;
    });

    let uploadedReqCount = 0;
    container.innerHTML = '';

    reqKeys.forEach((key, idx) => {
      const isUploaded = !!uploadedMap[key];
      if (isUploaded) uploadedReqCount++;
      const matchedDoc = uploadedMap[key];
      const docName = formatDocTypeName(key);

      const row = document.createElement('div');
      row.className = 'coverage-row';
      row.innerHTML = `
        <div>
          <div class="coverage-item-title" style="display: flex; align-items: center; gap: 8px;">
            ${isUploaded ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--status-success)" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>' : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--status-error)" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>'}
            <span>${idx + 1}. ${docName}</span>
            ${!isUploaded ? '<span class="badge badge-danger">MANDATORY</span>' : ''}
          </div>
          <div class="coverage-item-sub">
            ${isUploaded ? `Matched file: <strong>${matchedDoc.originalName}</strong>` : 'Required to verify scholarship eligibility thresholds.'}
          </div>
        </div>
        <div>
          ${isUploaded ?
            '<span class="badge badge-success">&#10003; Uploaded</span>' :
            `<button class="btn btn-outline-danger btn-sm btn-upload-now-inline" data-type="${key}" type="button">Missing Required &bull; Upload Now</button>`
          }
        </div>
      `;

      if (!isUploaded) {
        row.querySelector('.btn-upload-now-inline').addEventListener('click', () => {
          document.getElementById('selDocType').value = key;
          document.getElementById('hiddenFileInput').click();
        });
      }

      container.appendChild(row);
    });

    // Optional category certificate
    const hasCategory = state.applicant.category && state.applicant.category !== 'General';
    const isCatUploaded = !!uploadedMap['category_certificate'];
    const catRow = document.createElement('div');
    catRow.className = 'coverage-row';
    catRow.innerHTML = `
      <div>
        <div class="coverage-item-title" style="display: flex; align-items: center; gap: 8px;">
          ${isCatUploaded ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--status-success)" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>' : '<div style="width:16px;height:16px;border-radius:50%;border:1px solid var(--border-hover);"></div>'}
          <span>6. Category / Caste Certificate</span>
        </div>
        <div class="coverage-item-sub">
          ${hasCategory ? `Required for quota benefits (${state.applicant.category} category)` : 'Not required for general category profile.'}
        </div>
      </div>
      <div>
        ${isCatUploaded ? '<span class="badge badge-success">&#10003; Uploaded</span>' : '<span class="badge badge-neutral">Optional</span>'}
      </div>
    `;
    container.appendChild(catRow);

    badge.textContent = `${uploadedReqCount} of ${reqKeys.length} Mandatory Uploaded`;
    if (uploadedReqCount === reqKeys.length) {
      badge.className = 'badge badge-success';
    } else {
      badge.className = 'badge badge-warning';
    }
  }

  function formatDocTypeName(typeKey) {
    const map = {
      identity_proof: 'Identity Proof (Aadhaar / National ID)',
      income_certificate: 'Income Certificate (State Authority)',
      college_proof: 'College Admission / Bonafide',
      previous_marksheet: 'Previous Year Marksheet / Transcript',
      bank_proof: 'Bank Proof (Passbook / Statement)',
      category_certificate: 'Category / Caste Certificate'
    };
    return map[typeKey] || typeKey.replace('_', ' ').toUpperCase();
  }

  // --------------------------------------------------------------------------
  // Step 4: OCR Analysis & Review Screen
  // --------------------------------------------------------------------------
  async function triggerOcrAndChecks() {
    if (state.uploadedDocuments.length === 0) {
      alert('Please upload at least one document to analyze.');
      return;
    }

    // Open Processing Modal with live stages
    processingModal.classList.add('active');
    setProcStage(1);

    try {
      // 1. Analyze each uploaded document
      setProcStage(2);
      for (const doc of state.uploadedDocuments) {
        const res = await fetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            caseId: state.caseId,
            docType: doc.docType,
            storedFilename: doc.storedFilename
          })
        });
        const anData = await res.json();
        if (anData.success) {
          state.extractedData[doc.docType] = anData;
          // By default, initialize verifiedDocs from extracted fields
          state.verifiedDocs[doc.docType] = {
            filename: doc.originalName,
            fields: { ...anData.fields }
          };
        }
      }

      setProcStage(3);
      setProcStage(4);

      // 2. Run Cross-Check and Scholarship Rules
      const checkRes = await fetch('/api/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          caseId: state.caseId,
          referenceNumber: state.referenceNumber,
          scholarshipId: state.selectedScholarship.id,
          applicant: state.applicant,
          verifiedDocs: state.verifiedDocs
        })
      });
      const checkData = await checkRes.json();
      state.checkResults = checkData;

      setProcStage(5);
      // Small tick delay to let user see final stage before transition
      setTimeout(() => {
        processingModal.classList.remove('active');
        goToStep(4); // Move to Review Screen
      }, 350);

    } catch (e) {
      console.error('OCR & Check pipeline failed:', e);
      processingModal.classList.remove('active');
      alert('Analysis encountered an issue. You can still review and verify your fields manually.');
      goToStep(4);
    }
  }

  function setProcStage(num) {
    for (let i = 1; i <= 5; i++) {
      const el = document.getElementById(`procStage${i}`);
      if (!el) continue;
      el.classList.remove('active', 'done');
      if (i < num) {
        el.classList.add('done');
      } else if (i === num) {
        el.classList.add('active');
      }
    }
  }

  function renderReviewScreen() {
    const container = document.getElementById('ocrRecordsContainer');
    const missingCallouts = document.getElementById('missingFieldCalloutsContainer');
    const discCard = document.getElementById('discrepancyAlertCard');
    const docsCount = document.getElementById('ocrDocsCountText');
    if (!container) return;

    docsCount.textContent = `(${Object.keys(state.verifiedDocs).length} Files)`;
    container.innerHTML = '';
    missingCallouts.innerHTML = '';

    // Discrepancy Alert Check
    const nameDiscs = (state.checkResults && state.checkResults.nameDiscrepancies) || [];
    if (nameDiscs.length > 0) {
      const firstDisc = nameDiscs[0];
      discCard.style.display = 'block';
      document.getElementById('discrepancyTitle').textContent = `Possible Differences Detected (1 Item Needs Review)`;
      document.getElementById('discDoc1Label').textContent = firstDisc.doc1_name || 'Identity Proof';
      document.getElementById('discDoc1Val').textContent = firstDisc.val1 || '';
      document.getElementById('discDoc2Label').textContent = firstDisc.doc2_name || 'College Record';
      document.getElementById('discDoc2Val').textContent = firstDisc.val2 || '';
      document.getElementById('discrepancyExplanation').textContent = firstDisc.detail || '';

      const btnKeep = document.getElementById('btnKeepCollegeName');
      btnKeep.textContent = `Keep '${firstDisc.val2}' as Primary`;
      btnKeep.onclick = () => {
        // Standardize name across verifiedDocs and applicant profile
        state.applicant.full_name = firstDisc.val2;
        if (state.verifiedDocs.identity_proof) {
          state.verifiedDocs.identity_proof.fields.full_name = firstDisc.val2;
        }
        discCard.style.display = 'none';
        renderReviewScreen();
      };

      document.getElementById('btnEditNameManual').onclick = () => {
        openFieldEditModal('identity_proof', 'full_name', 'Student Full Name', firstDisc.val1);
      };

      document.getElementById('btnConfirmMismatchNote').onclick = () => {
        discCard.style.display = 'none';
      };
    } else {
      discCard.style.display = 'none';
    }

    // Render Each Document's Extracted Fields
    const docTypesOrder = [
      'identity_proof',
      'income_certificate',
      'college_proof',
      'bank_proof',
      'previous_marksheet',
      'category_certificate'
    ];

    docTypesOrder.forEach(typeKey => {
      const docRecord = state.verifiedDocs[typeKey];
      if (!docRecord) return;

      const card = document.createElement('div');
      card.className = 'ocr-record-card';
      const typeName = formatDocTypeName(typeKey);

      card.innerHTML = `
        <div class="ocr-record-header">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div class="feat-icon" style="width: 32px; height: 32px; background: var(--surface-subtle); display: flex; align-items: center; justify-content: center; border-radius: var(--radius-sm);">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path></svg>
            </div>
            <div>
              <div style="font-size: 14px; font-weight: 700; color: var(--text-primary);">${typeName}</div>
              <div style="font-size: 11px; color: var(--text-muted);">${docRecord.filename}</div>
            </div>
          </div>
          <span class="badge badge-success">&#10003; Text clearly legible</span>
        </div>
        <div class="extracted-fields-grid" id="fieldsGrid_${typeKey}">
        </div>
      `;

      const grid = card.querySelector(`#fieldsGrid_${typeKey}`);
      const fields = docRecord.fields;

      for (const [fKey, fVal] of Object.entries(fields)) {
        if (fKey === 'cgpa_needs_confirmation' || fKey === 'text_detected' || fKey === 'line_count') continue;
        const cell = document.createElement('div');
        cell.className = 'field-cell';
        const displayLabel = formatFieldLabel(fKey);
        const displayVal = formatFieldValue(fKey, fVal);

        cell.innerHTML = `
          <div class="field-cell-top">
            <span class="field-label">${displayLabel}</span>
            <button class="btn-edit" type="button" data-type="${typeKey}" data-key="${fKey}" data-label="${displayLabel}" data-val="${fVal || ''}">Edit</button>
          </div>
          <div class="field-value">${displayVal}</div>
        `;

        cell.querySelector('.btn-edit').addEventListener('click', (e) => {
          const t = e.currentTarget.dataset.type;
          const k = e.currentTarget.dataset.key;
          const l = e.currentTarget.dataset.label;
          const v = e.currentTarget.dataset.val;
          openFieldEditModal(t, k, l, v);
        });

        grid.appendChild(cell);
      }

      container.appendChild(card);
    });

    // Check if marksheet wasn't uploaded or percentage undetected
    const marksheetRec = state.verifiedDocs.previous_marksheet;
    if (!marksheetRec || !marksheetRec.fields || marksheetRec.fields.percentage == null) {
      const callout = document.createElement('div');
      callout.className = 'card';
      callout.style.border = '1px solid var(--primary-border)';
      callout.style.backgroundColor = 'var(--primary-subtle)';
      callout.style.padding = '16px 20px';
      callout.style.marginBottom = '1.5rem';
      callout.style.display = 'flex';
      callout.style.alignItems = 'center';
      callout.style.justifyContent = 'space-between';
      callout.style.gap = '1rem';

      callout.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
          <div style="width: 36px; height: 36px; border-radius: var(--radius-md); background: #ffffff; color: var(--primary); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><line x1="12" y1="18" x2="12" y2="12"></line><line x1="9" y1="15" x2="15" y2="15"></line></svg>
          </div>
          <div>
            <div style="font-size: 14px; font-weight: 700; color: var(--text-primary);">
              Previous Academic Percentage: <span style="color: var(--primary);">Not detected</span>
            </div>
            <div style="font-size: 12px; color: var(--text-secondary);">
              Previous Year Marksheet was not uploaded or percentage was unclear. You can enter it manually below.
            </div>
          </div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <input type="text" id="inpManualPercentage" placeholder="e.g. 78.50%" value="${state.applicant.percentage || ''}" style="width: 110px; height: 36px; border: 1px solid var(--border-crisp); border-radius: var(--radius-sm); padding: 0 8px; font-size: 13px;">
          <button class="btn btn-primary btn-sm" id="btnSaveManualPct" type="button">Save</button>
        </div>
      `;

      callout.querySelector('#btnSaveManualPct').addEventListener('click', () => {
        const val = callout.querySelector('#inpManualPercentage').value.trim();
        if (val) {
          state.applicant.percentage = val;
          if (!state.verifiedDocs.previous_marksheet) {
            state.verifiedDocs.previous_marksheet = {
              filename: 'Manual Entry',
              fields: { percentage: parseFloat(val.replace('%', '')) || 78.5 }
            };
          } else {
            state.verifiedDocs.previous_marksheet.fields.percentage = parseFloat(val.replace('%', '')) || 78.5;
          }
          renderReviewScreen();
        }
      });

      missingCallouts.appendChild(callout);
    }
  }

  function formatFieldLabel(key) {
    const map = {
      full_name: 'Full Name',
      dob: 'Date of Birth',
      gender: 'Gender',
      state: 'State',
      id_number: 'ID Number',
      beneficiary_name: 'Beneficiary / Guardian',
      annual_income: 'Annual Family Income',
      valid_until: 'Valid Until',
      issue_date: 'Issue Date',
      certificate_number: 'Certificate No.',
      issuing_authority: 'Issuing Authority',
      candidate_name: 'Candidate Name',
      institute_name: 'Institute Name',
      enrolled_course: 'Enrolled Course',
      admission_year: 'Admission Year',
      roll_number: 'Roll Number',
      student_name: 'Student Name',
      percentage: 'Percentage',
      cgpa: 'CGPA',
      pass_status: 'Pass Status',
      exam_year: 'Exam Year',
      account_holder: 'Account Holder',
      bank_name: 'Bank Name',
      ifsc_code: 'IFSC Code',
      account_number: 'Account Number',
      account_status: 'Account Status',
      category: 'Category'
    };
    return map[key] || key.replace('_', ' ').toUpperCase();
  }

  function formatFieldValue(key, val) {
    if (val == null || val === '') return '<span style="color:var(--text-muted);font-weight:400;">Not detected</span>';
    if (key === 'annual_income' && typeof val === 'number') {
      return `₹${val.toLocaleString('en-IN')}`;
    }
    if (key === 'percentage' && typeof val === 'number') {
      return `${val.toFixed(2)}%`;
    }
    return String(val);
  }

  function openFieldEditModal(docType, fieldKey, fieldLabel, currentVal) {
    state.editingTarget = { docType, fieldKey, fieldLabel };
    editModalFieldLabel.textContent = fieldLabel;
    editModalInput.value = currentVal || '';
    editFieldModal.classList.add('active');
    editModalInput.focus();
  }

  function saveFieldEditModal() {
    if (!state.editingTarget) return;
    const newVal = editModalInput.value.trim();
    const { docType, fieldKey } = state.editingTarget;

    if (state.verifiedDocs[docType] && state.verifiedDocs[docType].fields) {
      if (fieldKey === 'annual_income') {
        const num = parseInt(newVal.replace(/[^\d]/g, ''), 10);
        state.verifiedDocs[docType].fields[fieldKey] = isNaN(num) ? newVal : num;
      } else if (fieldKey === 'percentage') {
        const fl = parseFloat(newVal.replace(/[^\d.]/g, ''));
        state.verifiedDocs[docType].fields[fieldKey] = isNaN(fl) ? newVal : fl;
      } else {
        state.verifiedDocs[docType].fields[fieldKey] = newVal;
      }
    }

    editFieldModal.classList.remove('active');
    renderReviewScreen();
  }

  // --------------------------------------------------------------------------
  // Step 5: Application Readiness Results Screen
  // --------------------------------------------------------------------------
  async function runFinalCheckAndShowResults() {
    try {
      const res = await fetch('/api/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          caseId: state.caseId,
          referenceNumber: state.referenceNumber,
          scholarshipId: state.selectedScholarship.id,
          applicant: state.applicant,
          verifiedDocs: state.verifiedDocs
        })
      });
      const data = await res.json();
      state.checkResults = data;
      goToStep(5);
    } catch (e) {
      console.error('Final check failed:', e);
      alert('Unable to calculate final score.');
    }
  }

  function renderResultsScreen() {
    const cr = state.checkResults;
    if (!cr) return;

    // Subtitle & Header Info
    const subhead = document.getElementById('resultsSubheading');
    if (subhead) {
      subhead.textContent = `Based on the configured ${cr.scholarship.name} criteria and your uploaded records.`;
    }

    // Readiness Gauge & Score
    const r = cr.readiness;
    const scoreVal = r.score;
    document.getElementById('gaugeScoreNumber').textContent = `${scoreVal}%`;
    const circle = document.getElementById('gaugeValCircle');
    if (circle) {
      const circumference = 314;
      const offset = circumference - (circumference * scoreVal / 100);
      circle.style.strokeDashoffset = offset;
      circle.style.stroke = r.status_color || 'var(--primary)';
    }

    const badge = document.getElementById('scoreReadinessBadge');
    badge.textContent = r.status_label;
    if (scoreVal >= 90) {
      badge.className = 'badge badge-success';
    } else if (scoreVal >= 70) {
      badge.className = 'badge badge-warning';
    } else {
      badge.className = 'badge badge-danger';
    }

    document.getElementById('scoreSummaryText').textContent = r.summary_text;

    // Stat counts
    document.getElementById('statPassedCount').textContent = `${r.stats.passed_count} Checks`;
    document.getElementById('statAttentionCount').textContent = `${r.stats.attention_count} Need Attention`;
    document.getElementById('statMissingCount').textContent = `${r.stats.missing_count} Missing File${r.stats.missing_count === 1 ? '' : 's'}`;

    // Score Breakdown Accordion
    const b = r.breakdown;
    document.getElementById('scorePtsDocs').textContent = `${b.documents.score} / ${b.documents.max} pts`;
    document.getElementById('scorePtsElig').textContent = `${b.eligibility.score} / ${b.eligibility.max} pts`;
    document.getElementById('scorePtsCons').textContent = `${b.consistency.score} / ${b.consistency.max} pts`;
    document.getElementById('scorePtsComp').textContent = `${b.completeness.score} / ${b.completeness.max} pts`;

    // 1. Missing Documents Section
    const missingSec = document.getElementById('resultsMissingSection');
    missingSec.innerHTML = '';
    if (cr.missingDocuments && cr.missingDocuments.length > 0) {
      missingSec.innerHTML = `
        <div style="margin-bottom: 12px;">
          <h3 style="font-size: 16px; font-weight: 700; color: var(--status-error); display: flex; align-items: center; gap: 8px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            Action Required: Missing Document
          </h3>
        </div>
      `;

      cr.missingDocuments.forEach(item => {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.borderLeft = '4px solid var(--status-error)';
        card.style.marginBottom = '12px';
        card.style.display = 'flex';
        card.style.justifyContent = 'space-between';
        card.style.alignItems = 'center';
        card.style.gap = '1rem';

        card.innerHTML = `
          <div style="display: flex; align-items: flex-start; gap: 14px;">
            <div style="width: 40px; height: 40px; border-radius: var(--radius-md); background: var(--status-error-bg); color: var(--status-error); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><line x1="9" y1="15" x2="15" y2="15"></line></svg>
            </div>
            <div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 15px; font-weight: 700;">${item.title}</span>
                <span class="badge badge-danger">Mandatory</span>
              </div>
              <div style="font-size: 13px; color: var(--text-secondary); margin-top: 2px;">
                ${item.detail}
              </div>
              <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">
                Accepted formats: PDF, JPG, PNG (Max 15MB)
              </div>
            </div>
          </div>
          <button class="btn btn-outline-danger btn-sm btn-inline-upload-missing" data-type="${item.doc_type}" type="button">
            Upload ${item.title} Now &rarr;
          </button>
        `;

        card.querySelector('.btn-inline-upload-missing').addEventListener('click', () => {
          document.getElementById('selDocType').value = item.doc_type;
          goToStep(3);
        });

        missingSec.appendChild(card);
      });
    }

    // 2. Needs Attention Section
    const attSec = document.getElementById('resultsAttentionSection');
    attSec.innerHTML = '';
    if (cr.needsAttention && cr.needsAttention.length > 0) {
      attSec.innerHTML = `
        <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
          <h3 style="font-size: 16px; font-weight: 700; color: var(--status-warning); display: flex; align-items: center; gap: 8px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            Needs Your Attention (${cr.needsAttention.length} Items)
          </h3>
          <span style="font-size: 12px; color: var(--text-muted);">Action recommended before submission</span>
        </div>
      `;

      cr.needsAttention.forEach((item, idx) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.borderLeft = '4px solid var(--status-warning)';
        card.style.marginBottom = '12px';

        const exp = item.explanation || {};

        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div style="font-size: 15px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
              <span>${item.title}</span>
              <span class="badge badge-warning">${item.severity || 'Review'}</span>
            </div>
          </div>
          <p style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
            ${item.detail}
          </p>

          <div class="accordion-item" id="attAccordion_${idx}">
            <div class="accordion-header" style="background: var(--surface-subtle); padding: 10px 14px;">
              <span style="font-size: 12px; font-weight: 600; color: var(--primary);">How to fix this issue &darr;</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </div>
            <div class="accordion-body" style="padding: 12px 14px;">
              <div style="margin-bottom: 8px;">
                <strong style="font-size: 11px; text-transform: uppercase; color: var(--text-muted);">What We Found:</strong>
                <div style="font-size: 13px; color: var(--text-primary);">${exp.what_we_found || item.detail}</div>
              </div>
              <div style="margin-bottom: 8px;">
                <strong style="font-size: 11px; text-transform: uppercase; color: var(--text-muted);">Why It May Matter:</strong>
                <div style="font-size: 13px; color: var(--text-secondary);">${exp.why_it_matters || 'Portals reject conflicting applicant records.'}</div>
              </div>
              <div>
                <strong style="font-size: 11px; text-transform: uppercase; color: var(--text-muted);">What To Do Next:</strong>
                <div style="font-size: 13px; color: var(--status-success); font-weight: 600;">${exp.what_to_do_next || 'Verify spelling or obtain required certification prior to submission.'}</div>
              </div>
            </div>
          </div>
        `;

        const accHeader = card.querySelector('.accordion-header');
        accHeader.addEventListener('click', () => {
          const accItem = card.querySelector('.accordion-item');
          accItem.classList.toggle('open');
        });

        attSec.appendChild(card);
      });
    }

    // 3. Passed Verifications
    const passList = document.getElementById('passedChecksListContainer');
    document.getElementById('passedCountHeaderBadge').textContent = `(${cr.checksPassed.length} Validated)`;
    passList.innerHTML = '';
    cr.checksPassed.forEach(chk => {
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.alignItems = 'center';
      row.style.justifyContent = 'space-between';
      row.style.padding = '12px 0';
      row.style.borderBottom = '1px solid var(--border-crisp)';

      row.innerHTML = `
        <div style="display: flex; align-items: flex-start; gap: 10px;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--status-success)" stroke-width="2.5" style="flex-shrink: 0; margin-top: 2px;">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <div>
            <div style="font-size: 13px; font-weight: 600; color: var(--text-primary);">${chk.title}</div>
            <div style="font-size: 12px; color: var(--text-muted);">${chk.detail || ''}</div>
          </div>
        </div>
        <span class="badge badge-success">${chk.badge || 'Passed'}</span>
      `;
      passList.appendChild(row);
    });

    // 4. Eligibility Comparison Matrix
    const tbody = document.getElementById('resultsMatrixTbody');
    tbody.innerHTML = '';
    cr.comparisonMatrix.forEach(row => {
      const tr = document.createElement('tr');
      const badgeCls = row.status_type === 'success' ? 'badge-success' : (row.status_type === 'warning' ? 'badge-warning' : 'badge-danger');
      tr.innerHTML = `
        <td><strong>${row.parameter}</strong></td>
        <td>${row.uploaded_value}</td>
        <td>${row.requirement}</td>
        <td><span class="badge ${badgeCls}">${row.status_label}</span></td>
      `;
      tbody.appendChild(tr);
    });

    // Timestamp & Reference
    document.getElementById('caseRefDisplay').textContent = `Check Ref: ${cr.referenceNumber}`;
    document.getElementById('caseCheckedTimeDisplay').textContent = `Checked on ${cr.timestamp}`;
  }

  async function downloadReportPdf() {
    if (!state.checkResults) return;
    const btn = document.getElementById('btnDownloadReportPdf');
    btn.disabled = true;
    btn.textContent = 'Generating PDF...';

    try {
      const res = await fetch('/api/generate-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(state.checkResults)
      });
      const data = await res.json();
      if (data.success && data.downloadUrl) {
        window.location.href = data.downloadUrl;
      } else {
        alert(data.error || 'Failed to generate report PDF.');
      }
    } catch (e) {
      console.error('Report error:', e);
      alert('Could not generate PDF report.');
    } finally {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        Download Check Report (PDF)
      `;
    }
  }

  // --------------------------------------------------------------------------
  // Event Listeners & Bindings
  // --------------------------------------------------------------------------
  function setupEventListeners() {
    // Brand Logo & Nav Links
    document.getElementById('navBrandLogo').addEventListener('click', () => goToStep(0));
    document.getElementById('footerBrandLogo').addEventListener('click', () => goToStep(0));
    document.getElementById('btnHeaderCheck').addEventListener('click', () => goToStep(1));
    document.getElementById('btnHeroStart').addEventListener('click', () => goToStep(1));
    document.getElementById('btnBottomPreCheck').addEventListener('click', () => goToStep(1));

    document.getElementById('navLinkScholarships').addEventListener('click', () => goToStep(1));
    document.getElementById('footScholarships').addEventListener('click', () => goToStep(1));

    document.getElementById('navLinkHowItWorks').addEventListener('click', () => {
      goToStep(0);
      document.getElementById('sectionHowItWorksAnchor').scrollIntoView({ behavior: 'smooth' });
    });
    document.getElementById('linkHowItWorksScroll').addEventListener('click', () => {
      document.getElementById('sectionHowItWorksAnchor').scrollIntoView({ behavior: 'smooth' });
    });
    document.getElementById('footHowItWorks').addEventListener('click', () => {
      goToStep(0);
      document.getElementById('sectionHowItWorksAnchor').scrollIntoView({ behavior: 'smooth' });
    });

    // Home Quick Drop Zone
    const homeDrop = document.getElementById('homeDropZone');
    homeDrop.addEventListener('click', () => goToStep(1));

    // Step 1 Scheme Search
    const searchInp = document.getElementById('schemeSearchInput');
    searchInp.addEventListener('input', (e) => {
      renderScholarshipCards(e.target.value);
    });

    document.getElementById('btnContinueToDetails').addEventListener('click', () => {
      goToStep(2);
    });

    // Step 2 Form Controls
    document.getElementById('btnBackToStep1').addEventListener('click', () => goToStep(1));
    document.getElementById('btnAutofillDemo').addEventListener('click', autofillDemoApplicant);
    document.getElementById('btnContinueToUpload').addEventListener('click', () => {
      if (validateApplicantForm()) {
        goToStep(3);
      }
    });

    // Step 3 Upload Controls
    document.getElementById('btnBackToStep2').addEventListener('click', () => goToStep(2));
    document.getElementById('btnCheckMyDocuments').addEventListener('click', triggerOcrAndChecks);

    const hiddenFileInput = document.getElementById('hiddenFileInput');
    const btnSelectFiles = document.getElementById('btnSelectFiles');
    const selDocType = document.getElementById('selDocType');

    btnSelectFiles.addEventListener('click', () => hiddenFileInput.click());
    document.getElementById('btnAddMoreDocs').addEventListener('click', () => hiddenFileInput.click());

    hiddenFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        uploadFile(e.target.files[0], selDocType.value);
        hiddenFileInput.value = '';
      }
    });

    // Drag and Drop
    const fileDropZone = document.getElementById('fileDropZone');
    ['dragenter', 'dragover'].forEach(evt => {
      fileDropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        fileDropZone.classList.add('drag-over');
      });
    });
    ['dragleave', 'drop'].forEach(evt => {
      fileDropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        fileDropZone.classList.remove('drag-over');
      });
    });
    fileDropZone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        uploadFile(e.dataTransfer.files[0], selDocType.value);
      }
    });

    // Instant Demo Loaders
    document.getElementById('btnLoadCompleteDemoDocs').addEventListener('click', loadCompleteDemoSet);
    document.getElementById('btnLoadMissingDocDemo').addEventListener('click', loadMissingDocDemoSet);

    // Step 4 Review Controls
    document.getElementById('btnBackToUpload').addEventListener('click', () => goToStep(3));
    document.getElementById('btnRunFullReadiness').addEventListener('click', runFinalCheckAndShowResults);

    // Edit Field Modal
    document.getElementById('btnCancelEditModal').addEventListener('click', () => {
      editFieldModal.classList.remove('active');
    });
    document.getElementById('btnSaveEditModal').addEventListener('click', saveFieldEditModal);

    // Step 5 Results Controls
    document.getElementById('btnDownloadReportPdf').addEventListener('click', downloadReportPdf);
    document.getElementById('btnRescanRecords').addEventListener('click', () => goToStep(4));
    document.getElementById('btnStartNewCheckLink').addEventListener('click', () => {
      state.uploadedDocuments = [];
      state.extractedData = {};
      state.verifiedDocs = {};
      state.checkResults = null;
      createOrRestoreCase();
      goToStep(1);
    });

    // Score breakdown accordion toggle
    const scoreAccHead = document.getElementById('scoreAccordionHeader');
    if (scoreAccHead) {
      scoreAccHead.addEventListener('click', () => {
        document.getElementById('scoreAccordion').classList.toggle('open');
      });
    }
  }

  // Start app on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', init);
})();
