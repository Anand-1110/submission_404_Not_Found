/**
 * Scrollhouse Onboarding Agent — Dashboard JS
 * USE_MOCK=false  → calls the real FastAPI backend (uvicorn agent.main:app --port 8000)
 * USE_MOCK=true   → runs a local simulation with no backend needed
 */

const WEBHOOK_URL = '/webhook/onboard';  // Cloud-compatible relative path routing
const USE_MOCK = false;   // ← false = real mode  |  true = simulation only

// ── State ────────────────────────────────────────────────────────────────────

let clientsOnboarded = 0;
let errorsCount = 0;
let lastRunTime = 0;
let isRunning = false;
let auditLog = [];

// ── DOM Refs ─────────────────────────────────────────────────────────────────

const form          = document.getElementById('clientForm');
const submitBtn     = document.getElementById('submitBtn');
const logOutput     = document.getElementById('logOutput');
const resultPanel   = document.getElementById('resultPanel');
const resultEmpty   = document.getElementById('resultEmpty');
const resultContent = document.getElementById('resultContent');
const resultClient  = document.getElementById('resultClientName');
const resultLinks   = document.getElementById('resultLinks');
const resultTime    = document.getElementById('resultTime');
const metricTime    = document.getElementById('metricTime');
const metricTotal   = document.getElementById('metricTotal');
const metricErrors  = document.getElementById('metricErrors');
const systemStatus  = document.getElementById('systemStatus');
const systemLabel   = document.getElementById('systemStatusLabel');
const logsModal     = document.getElementById('logsModal');
const modalLogContent = document.getElementById('modalLogContent');

// ── Pipeline step config ─────────────────────────────────────────────────────

const STEPS = [
  { id: 'webhook',  label: '📡 Webhook received',              delay: 300  },
  { id: 'validate', label: '🔍 LangGraph validation running...',delay: 900  },
  { id: 'email',    label: '📧 Sending welcome email...',       delay: 1100 },
  { id: 'drive',    label: '📁 Creating Google Drive folder...', delay: 1500 },
  { id: 'notion',   label: '📝 Creating Notion page...',        delay: 1200 },
  { id: 'airtable', label: '📊 Creating Airtable record...',    delay: 1000 },
  { id: 'summary',  label: '✉️  Sending completion summary...',  delay: 700  },
  { id: 'logger',   label: '🗂️  Writing audit log...',           delay: 400  },
];

// ── Logging ──────────────────────────────────────────────────────────────────

function addLog(message, level = 'info', ts = null) {
  const timestamp = ts || new Date().toISOString().slice(11, 23);
  const entry = { ts: timestamp, message, level };
  auditLog.push(entry);

  const div = document.createElement('div');
  div.className = `log-line ${level}`;
  const levelMap = { info: 'INFO', success: 'SUCCESS', warning: 'WARNING', error: 'ERROR' };
  div.textContent = `[${timestamp}] [${levelMap[level] || 'INFO'}] ${message}`;
  logOutput.appendChild(div);
  logOutput.scrollTop = logOutput.scrollHeight;
}

// ── Metrics ──────────────────────────────────────────────────────────────────

function updateMetrics() {
  metricTime.textContent  = lastRunTime > 0 ? `${lastRunTime.toFixed(1)}s` : '0s';
  metricTotal.textContent = clientsOnboarded;
  metricErrors.textContent = errorsCount;
}

function setSystemStatus(state) {
  systemStatus.className = `status-dot ${state}`;
  const labels = { '': 'System Ready', running: 'Agent Running...', error: 'Error Detected' };
  systemLabel.textContent = labels[state] || 'System Ready';
}

// ── Pipeline Steps ────────────────────────────────────────────────────────────

function resetPipeline() {
  STEPS.forEach(s => {
    const stepEl  = document.getElementById(`step-${s.id}`);
    const badgeEl = document.getElementById(`badge-${s.id}`);
    if (stepEl)  { stepEl.classList.remove('active', 'done', 'error-state'); }
    if (badgeEl) { badgeEl.textContent = 'WAITING'; badgeEl.className = 'pipe-status-badge'; }
  });
  document.querySelectorAll('.pipe-connector').forEach(c => c.classList.remove('active'));
  document.getElementById('errorBranch').classList.remove('active');
}

function setStepActive(id) {
  const stepEl  = document.getElementById(`step-${id}`);
  const badgeEl = document.getElementById(`badge-${id}`);
  if (stepEl)  { stepEl.classList.add('active'); stepEl.classList.remove('done', 'error-state'); }
  if (badgeEl) { badgeEl.textContent = 'RUNNING'; badgeEl.className = 'pipe-status-badge running'; }
}

function setStepDone(id, success = true) {
  const stepEl  = document.getElementById(`step-${id}`);
  const badgeEl = document.getElementById(`badge-${id}`);
  if (stepEl) {
    stepEl.classList.remove('active');
    stepEl.classList.add(success ? 'done' : 'error-state');
  }
  if (badgeEl) {
    badgeEl.textContent = success ? 'DONE ✓' : 'ERROR';
    badgeEl.className   = `pipe-status-badge ${success ? 'done' : 'error'}`;
  }
}

function activateConnector(idx) {
  const conn = document.getElementById(`conn-${idx}`);
  if (conn) conn.classList.add('active');
}

// ── Validation Simulation ─────────────────────────────────────────────────────

function validatePayload(data) {
  const errors = [];
  const emailRe = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  if (!data.client_name.trim()) errors.push('Client name is required');
  if (!emailRe.test(data.client_email)) errors.push(`Invalid email: "${data.client_email}"`);
  if (!data.service_plan) errors.push('Service plan is required');
  if (!data.start_date) errors.push('Start date is required');
  else {
    const start = new Date(data.start_date);
    const today = new Date();
    today.setHours(0,0,0,0);
    if (start < today) errors.push(`Start date "${data.start_date}" is in the past`);
  }

  const dupes = ['Acme Corp', 'Globex', 'Initech'];
  if (dupes.some(d => d.toLowerCase() === data.client_name.trim().toLowerCase())) {
    errors.push(`Duplicate client name: "${data.client_name}" already exists`);
  }

  return errors;
}

// ── Mock Results ──────────────────────────────────────────────────────────────

function buildMockResults(data) {
  const slug = data.client_name.toLowerCase().replace(/\s+/g, '-');
  return {
    email:    { success: true, to: data.client_email },
    drive:    { success: true, folder_url: `https://drive.google.com/drive/folders/mock_${slug}` },
    notion:   { success: true, page_url: `https://notion.so/mock-${slug}` },
    airtable: { success: true, record_id: `rec${Date.now().toString(36).toUpperCase()}` },
    summary:  { success: true, to: 'manager@scrollhouse.co' },
  };
}

// ── Run Pipeline ──────────────────────────────────────────────────────────────

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function runPipeline(data) {
  if (isRunning) return;
  isRunning = true;
  submitBtn.disabled = true;
  const t0 = performance.now();

  setSystemStatus('running');
  resetPipeline();

  addLog(`━━━ New onboarding run started ━━━`, 'info');
  addLog(`Client: ${data.client_name} (${data.client_email})`);
  addLog(`Plan: ${data.service_plan} | Start: ${data.start_date}`);

  // ── STEP 1: Webhook ────────────────────────────────────────────────────────
  setStepActive('webhook');
  addLog('Webhook trigger received — n8n dispatching to agent...');
  await sleep(STEPS[0].delay);
  setStepDone('webhook');
  activateConnector(1);

  // ── STEP 2: Validate ───────────────────────────────────────────────────────
  setStepActive('validate');
  addLog('LangGraph validation graph running...');
  await sleep(STEPS[1].delay);

  const errors = validatePayload(data);
  if (errors.length) {
    setStepDone('validate', false);
    document.getElementById('errorBranch').classList.add('active');
    errors.forEach(e => addLog(`✗ ${e}`, 'error'));
    addLog('Validation FAILED — alerting account manager', 'error');
    errorsCount++;
    updateMetrics();
    setSystemStatus('error');
    isRunning = false;
    submitBtn.disabled = false;
    return;
  }

  setStepDone('validate');
  addLog('All validation checks passed ✓', 'success');
  activateConnector(2);

  // ── STEPs 3–8: Tools ───────────────────────────────────────────────────────
  const toolSteps = ['email','drive','notion','airtable','summary','logger'];
  const toolLogs = [
    ['Sending welcome email via SendGrid...', 'Email sent ✓'],
    ['Creating Google Drive folder + subfolders...', 'Drive folder created ✓'],
    ['Creating Notion page from master template...', 'Notion page created ✓'],
    ['Creating Airtable CRM record...', 'Airtable record created ✓'],
    ['Sending completion summary to account manager...', 'Summary sent ✓'],
    ['Writing full audit log to LangSmith...', 'Audit log saved ✓'],
  ];

  for (let i = 0; i < toolSteps.length; i++) {
    const sid = toolSteps[i];
    setStepActive(sid);
    addLog(toolLogs[i][0]);
    await sleep(STEPS[i + 2].delay);
    setStepDone(sid);
    addLog(toolLogs[i][1], 'success');
    if (i < toolSteps.length - 1) activateConnector(i + 3);
  }

  // ── Finish ─────────────────────────────────────────────────────────────────
  const elapsed = ((performance.now() - t0) / 1000).toFixed(1);
  lastRunTime = parseFloat(elapsed);
  clientsOnboarded++;
  updateMetrics();
  setSystemStatus('');

  addLog(`━━━ Run complete in ${elapsed}s ━━━`, 'success');

  // Show result card
  const results = buildMockResults(data);
  renderResultCard(data, results, elapsed);

  isRunning = false;
  submitBtn.disabled = false;
}

// ── Result Card ───────────────────────────────────────────────────────────────

function renderResultCard(data, results, elapsed) {
  resultEmpty.classList.add('hidden');
  resultContent.classList.remove('hidden');

  resultClient.textContent = `✅ ${data.client_name}`;
  resultTime.textContent   = `Completed in ${elapsed}s at ${new Date().toLocaleTimeString()}`;

  const items = [
    { icon: '📧', label: 'Welcome email', val: data.client_email, href: null },
    { icon: '📁', label: 'Google Drive', val: 'Open folder →', href: results.drive.folder_url },
    { icon: '📝', label: 'Notion page',  val: 'Open page →',   href: results.notion.page_url },
    { icon: '📊', label: 'Airtable',     val: results.airtable.record_id, href: null },
  ];

  resultLinks.innerHTML = items.map(it => `
    <div class="result-link-item">
      <span class="link-icon">${it.icon}</span>
      <div style="flex:1">
        <div class="link-label">${it.label}</div>
        ${it.href
          ? `<a class="link-val" href="${it.href}" target="_blank">${it.val}</a>`
          : `<span class="link-val" style="color:var(--text-secondary)">${it.val}</span>`}
      </div>
    </div>
  `).join('');
}

// ── REAL Pipeline (calls backend) ────────────────────────────────────────────

async function runPipelineReal(data) {
  if (isRunning) return;
  isRunning = true;
  submitBtn.disabled = true;
  const t0 = performance.now();

  setSystemStatus('running');
  resetPipeline();
  addLog(`━━━ Real onboarding run started ━━━`, 'info');
  addLog(`Sending to ${WEBHOOK_URL}...`);

  // Show webhook step as active immediately
  setStepActive('webhook');
  activateConnector(1);

  // Show validate as running while we wait for the backend
  await sleep(400);
  setStepDone('webhook');
  setStepActive('validate');

  let json;
  try {
    const res = await fetch(WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    json = await res.json();

    if (res.status === 409 || json.status === 'requires_confirmation') {
      // ── Edge Case Warning Intercept ──
      const msg = "⚠️ EDGE CASE DETECTED\nThe AI Validator flagged the following warnings:\n\n- " + json.warnings.join("\n- ") + "\n\nDo you want to explicitly override and proceed?";
      if (confirm(msg)) {
        addLog('Manager explicitly overrode edge case warnings.', 'warning');
        data.ignore_warnings = true;
        isRunning = false; // Reset lock so we can re-enter safely
        return await runPipelineReal(data);
      } else {
        setStepDone('validate', false);
        document.getElementById('errorBranch').classList.add('active');
        addLog('Onboarding aborted by Account Manager.', 'error');
        errorsCount++;
        updateMetrics();
        setSystemStatus('error');
        isRunning = false;
        submitBtn.disabled = false;
        return;
      }
    }

    if (!res.ok) {
      // Validation failure
      setStepDone('validate', false);
      document.getElementById('errorBranch').classList.add('active');
      const errs = json.errors || [json.detail || 'Unknown error'];
      errs.forEach(e => addLog(`✗ ${e}`, 'error'));
      addLog('Validation FAILED — see errors above', 'error');
      errorsCount++;
      updateMetrics();
      setSystemStatus('error');
      isRunning = false;
      submitBtn.disabled = false;
      return;
    }
  } catch (err) {
    setStepDone('validate', false);
    addLog(`❌ Could not reach backend: ${err.message}`, 'error');
    addLog('Is the agent running? → uvicorn agent.main:app --port 8000', 'warning');
    setSystemStatus('error');
    isRunning = false;
    submitBtn.disabled = false;
    return;
  }

  // Backend returned success — animate remaining steps using real result data
  setStepDone('validate');
  activateConnector(2);
  addLog('All validation checks passed ✓', 'success');

  const results = json.results || {};
  const toolSteps = ['email','drive','notion','airtable','summary','logger'];
  const toolLogs = [
    ['Sending welcome email...', results.email?.mock ? 'Email sent (mock)' : 'Email sent ✓'],
    ['Creating Google Drive folder...', results.drive?.folder_url ? `Drive folder: ${results.drive.folder_url}` : 'Drive folder created ✓'],
    ['Creating Notion page...', results.notion?.page_url ? `Notion: ${results.notion.page_url}` : 'Notion page created ✓'],
    ['Creating Airtable record...', results.airtable?.record_id ? `Airtable ID: ${results.airtable.record_id}` : 'Airtable record created ✓'],
    ['Sending completion summary to manager...', 'Summary sent ✓'],
    ['Writing audit log...', 'Audit log saved ✓'],
  ];

  for (let i = 0; i < toolSteps.length; i++) {
    const sid = toolSteps[i];
    setStepActive(sid);
    addLog(toolLogs[i][0]);
    await sleep(400);
    const success = results[sid]?.success !== false;
    setStepDone(sid, success);
    addLog(toolLogs[i][1], success ? 'success' : 'error');
    if (i < toolSteps.length - 1) activateConnector(i + 3);
  }

  const elapsed = ((performance.now() - t0) / 1000).toFixed(1);
  lastRunTime = parseFloat(elapsed);
  clientsOnboarded++;
  updateMetrics();
  setSystemStatus('');
  addLog(`━━━ Real run complete in ${elapsed}s ━━━`, 'success');

  renderResultCard(data, results, elapsed);
  isRunning = false;
  submitBtn.disabled = false;
}



form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (isRunning) return;

  const data = {
    client_name:     document.getElementById('clientName').value,
    client_email:    document.getElementById('clientEmail').value,
    service_plan:    document.getElementById('clientPlan').value,
    start_date:      document.getElementById('startDate').value,
    account_manager: document.getElementById('accountManager').value || 'Anand',
    notes:           document.getElementById('notes').value,
  };

  if (USE_MOCK) {
    await runPipeline(data);
  } else {
    await runPipelineReal(data);
  }
});

// ── Demo Button ───────────────────────────────────────────────────────────────

document.getElementById('btnTriggerDemo').addEventListener('click', async () => {
  if (isRunning) return;
  // Fill form with demo data
  document.getElementById('clientName').value = 'Nova Digital';
  document.getElementById('clientEmail').value = 'ceo@novadigital.io';
  document.getElementById('clientPlan').value = 'growth';
  // Set tomorrow's date
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById('startDate').value = tomorrow.toISOString().split('T')[0];
  document.getElementById('accountManager').value = 'Anand';
  document.getElementById('notes').value = 'Hackathon demo client';

  await runPipeline({
    client_name: 'Nova Digital',
    client_email: 'ceo@novadigital.io',
    service_plan: 'growth',
    start_date: tomorrow.toISOString().split('T')[0],
    account_manager: 'Anand',
    notes: 'Hackathon demo client',
  });
});

// ── Log Clear ─────────────────────────────────────────────────────────────────

document.getElementById('btnClearLogs').addEventListener('click', () => {
  logOutput.innerHTML = '';
  auditLog = [];
  addLog('Logs cleared.', 'info');
});

// ── Modal ─────────────────────────────────────────────────────────────────────

document.getElementById('btnOpenLogs').addEventListener('click', () => {
  modalLogContent.innerHTML = '';
  auditLog.forEach(e => {
    const div = document.createElement('div');
    div.className = `log-line ${e.level}`;
    div.textContent = `[${e.ts}] ${e.message}`;
    modalLogContent.appendChild(div);
  });
  logsModal.classList.remove('hidden');
});

document.getElementById('modalClose').addEventListener('click', () => {
  logsModal.classList.add('hidden');
});

logsModal.addEventListener('click', (e) => {
  if (e.target === logsModal) logsModal.classList.add('hidden');
});

// ── Set default start date to tomorrow ───────────────────────────────────────
(function() {
  const tom = new Date();
  tom.setDate(tom.getDate() + 1);
  document.getElementById('startDate').value = tom.toISOString().split('T')[0];
})();
