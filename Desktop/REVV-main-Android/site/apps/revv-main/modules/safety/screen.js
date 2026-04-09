export function render(container, context) {
  const JSA_KEY = 'revv_safety_jsa';
  const INCIDENT_KEY = 'revv_safety_incidents';
  const CHECKLIST_KEY = 'revv_safety_checklist';
  const CERT_KEY = 'revv_safety_certs';

  const getStore = (k, def) => JSON.parse(localStorage.getItem(k) || JSON.stringify(def));
  const setStore = (k, v) => localStorage.setItem(k, JSON.stringify(v));

  const CHECKLIST_ITEMS = [
    'PPE inspection completed',
    'Fire extinguishers inspected and accessible',
    'First aid kit stocked and accessible',
    'Emergency exits clear and marked',
    'Scaffolding inspected (if applicable)',
    'Fall protection in place',
    'Electrical hazards identified and mitigated',
    'Housekeeping satisfactory',
    'Tool inspection completed',
    'Safety briefing / toolbox talk held'
  ];

  container.innerHTML = `
    <style>
      .sf-wrap { max-width: 700px; margin: 0 auto; padding: 16px; font-family: -apple-system, system-ui, sans-serif; color: var(--text-primary, #e0e0e0); }
      .sf-tabs { display: flex; gap: 4px; margin-bottom: 16px; flex-wrap: wrap; }
      .sf-tab { flex: 1; min-width: 80px; padding: 12px 6px; border: none; border-radius: 12px 12px 0 0; font-size: 0.8rem; font-weight: 600; cursor: pointer; min-height: 48px; background: var(--bg-secondary, #1e1e2e); color: var(--text-secondary, #888); }
      .sf-tab.active { background: var(--accent, #60a5fa); color: #fff; }
      .sf-card { background: var(--bg-secondary, #1e1e2e); border-radius: 0 0 12px 12px; padding: 20px; margin-bottom: 16px; }
      .sf-panel { display: none; }
      .sf-panel.active { display: block; }
      .sf-label { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary, #888); margin-bottom: 6px; display: block; }
      .sf-input, .sf-select, .sf-textarea { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 0.9rem; margin-bottom: 12px; box-sizing: border-box; min-height: 48px; }
      .sf-textarea { min-height: 80px; resize: vertical; font-family: inherit; }
      .sf-btn { padding: 14px 20px; border: none; border-radius: 12px; background: var(--accent, #60a5fa); color: #fff; font-weight: 700; cursor: pointer; min-height: 48px; font-size: 0.9rem; margin-bottom: 8px; }
      .sf-btn.danger { background: #ef4444; }
      .sf-btn.full { width: 100%; }
      .sf-row { display: flex; gap: 12px; }
      .sf-row > * { flex: 1; }
      @media (max-width: 500px) { .sf-row { flex-direction: column; } }
      .sf-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
      .sf-table th { text-align: left; padding: 8px; border-bottom: 1px solid var(--border, #333); color: var(--text-secondary, #888); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }
      .sf-table td { padding: 8px; border-bottom: 1px solid var(--border, #222); }
      .sf-pair { background: var(--bg-primary, #12121a); border-radius: 8px; padding: 12px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
      .sf-pair-text { flex: 1; }
      .sf-pair-label { font-size: 0.7rem; color: var(--text-secondary, #888); text-transform: uppercase; }
      .sf-pair-val { font-size: 0.9rem; margin-top: 2px; }
      .sf-del-btn { background: transparent; border: 1px solid #ef4444; color: #ef4444; border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 0.75rem; min-height: 32px; align-self: center; }
      .sf-check-row { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border, #222); }
      .sf-check-row input[type="checkbox"] { width: 22px; height: 22px; cursor: pointer; }
      .sf-check-label { font-size: 0.9rem; cursor: pointer; flex: 1; }
      .sf-sev-badge { padding: 3px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; color: #fff; }
      .sf-section-title { font-size: 1rem; font-weight: 700; margin-bottom: 14px; }
      .sf-count { display: inline-block; background: var(--bg-primary, #12121a); padding: 2px 8px; border-radius: 8px; font-size: 0.75rem; margin-left: 8px; }
    </style>
    <div class="sf-wrap">
      <div class="sf-tabs">
        <button class="sf-tab active" data-tab="jsa">JSA Builder</button>
        <button class="sf-tab" data-tab="incident">Incidents</button>
        <button class="sf-tab" data-tab="checklist">Checklist</button>
        <button class="sf-tab" data-tab="certs">Certifications</button>
      </div>
      <div class="sf-card">
        <!-- JSA -->
        <div class="sf-panel active" id="sf-jsa">
          <div class="sf-section-title">Job Safety Analysis</div>
          <div class="sf-row">
            <div><label class="sf-label">Hazard</label><input class="sf-input" id="jsa-hazard" placeholder="Describe the hazard..."></div>
            <div><label class="sf-label">Control Measure</label><input class="sf-input" id="jsa-control" placeholder="How to mitigate..."></div>
          </div>
          <button class="sf-btn" id="jsa-add-btn">+ Add Hazard/Control Pair</button>
          <div id="jsa-list"></div>
        </div>

        <!-- INCIDENTS -->
        <div class="sf-panel" id="sf-incident">
          <div class="sf-section-title">Incident Report</div>
          <div class="sf-row">
            <div><label class="sf-label">Date</label><input class="sf-input" type="date" id="inc-date"></div>
            <div><label class="sf-label">Severity</label>
              <select class="sf-select" id="inc-severity">
                <option value="Near Miss">Near Miss</option>
                <option value="Minor">Minor</option>
                <option value="Moderate">Moderate</option>
                <option value="Serious">Serious</option>
                <option value="Critical">Critical</option>
              </select>
            </div>
          </div>
          <label class="sf-label">Location</label>
          <input class="sf-input" id="inc-location" placeholder="Where did this occur?">
          <label class="sf-label">Description</label>
          <textarea class="sf-textarea" id="inc-desc" placeholder="Describe what happened..."></textarea>
          <button class="sf-btn full" id="inc-add-btn">Submit Incident Report</button>
          <div style="margin-top:16px;">
            <table class="sf-table">
              <thead><tr><th>Date</th><th>Location</th><th>Severity</th><th></th></tr></thead>
              <tbody id="inc-list"></tbody>
            </table>
          </div>
        </div>

        <!-- CHECKLIST -->
        <div class="sf-panel" id="sf-checklist">
          <div class="sf-section-title">Daily Safety Checklist <span class="sf-count" id="cl-count">0/10</span></div>
          <div id="cl-list"></div>
          <button class="sf-btn full" id="cl-reset-btn" style="margin-top:12px;">Reset Checklist</button>
        </div>

        <!-- CERTIFICATIONS -->
        <div class="sf-panel" id="sf-certs">
          <div class="sf-section-title">Certification Tracker</div>
          <div class="sf-row">
            <div><label class="sf-label">Employee Name</label><input class="sf-input" id="cert-name" placeholder="Full name"></div>
            <div><label class="sf-label">Certification Type</label>
              <select class="sf-select" id="cert-type">
                <option>OSHA 10</option><option>OSHA 30</option><option>First Aid/CPR</option>
                <option>Confined Space</option><option>Fall Protection</option><option>Forklift</option>
                <option>Scaffold Competent</option><option>Hot Work</option><option>Rigging</option>
                <option>Other</option>
              </select>
            </div>
          </div>
          <label class="sf-label">Expiry Date</label>
          <input class="sf-input" type="date" id="cert-expiry">
          <button class="sf-btn full" id="cert-add-btn">+ Add Certification</button>
          <table class="sf-table" style="margin-top:12px;">
            <thead><tr><th>Name</th><th>Type</th><th>Expires</th><th></th></tr></thead>
            <tbody id="cert-list"></tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  const sevColors = { 'Near Miss': '#60a5fa', Minor: '#22c55e', Moderate: '#f59e0b', Serious: '#f97316', Critical: '#ef4444' };

  // Tab switching
  container.querySelectorAll('.sf-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      container.querySelectorAll('.sf-tab').forEach(t => t.classList.remove('active'));
      container.querySelectorAll('.sf-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      container.querySelector(`#sf-${tab.dataset.tab}`).classList.add('active');
    });
  });

  // JSA
  function renderJSA() {
    const pairs = getStore(JSA_KEY, []);
    container.querySelector('#jsa-list').innerHTML = pairs.map((p, i) => `
      <div class="sf-pair">
        <div class="sf-pair-text"><div class="sf-pair-label">Hazard</div><div class="sf-pair-val">${esc(p.hazard)}</div></div>
        <div class="sf-pair-text"><div class="sf-pair-label">Control</div><div class="sf-pair-val">${esc(p.control)}</div></div>
        <button class="sf-del-btn" data-idx="${i}" data-store="jsa">X</button>
      </div>
    `).join('');
    bindDeletes('jsa', JSA_KEY, renderJSA);
  }

  container.querySelector('#jsa-add-btn').addEventListener('click', () => {
    const h = container.querySelector('#jsa-hazard').value.trim();
    const c = container.querySelector('#jsa-control').value.trim();
    if (!h || !c) return;
    const pairs = getStore(JSA_KEY, []);
    pairs.push({ hazard: h, control: c });
    setStore(JSA_KEY, pairs);
    container.querySelector('#jsa-hazard').value = '';
    container.querySelector('#jsa-control').value = '';
    renderJSA();
  });

  // Incidents
  function renderIncidents() {
    const items = getStore(INCIDENT_KEY, []);
    container.querySelector('#inc-list').innerHTML = items.map((it, i) => `
      <tr>
        <td>${it.date}</td>
        <td>${esc(it.location)}</td>
        <td><span class="sf-sev-badge" style="background:${sevColors[it.severity] || '#888'}">${it.severity}</span></td>
        <td><button class="sf-del-btn" data-idx="${i}" data-store="inc">X</button></td>
      </tr>
    `).join('');
    bindDeletes('inc', INCIDENT_KEY, renderIncidents);
  }

  container.querySelector('#inc-add-btn').addEventListener('click', () => {
    const date = container.querySelector('#inc-date').value;
    const sev = container.querySelector('#inc-severity').value;
    const loc = container.querySelector('#inc-location').value.trim();
    const desc = container.querySelector('#inc-desc').value.trim();
    if (!date || !loc || !desc) return;
    const items = getStore(INCIDENT_KEY, []);
    items.push({ date, severity: sev, location: loc, description: desc, id: Date.now() });
    setStore(INCIDENT_KEY, items);
    container.querySelector('#inc-date').value = '';
    container.querySelector('#inc-location').value = '';
    container.querySelector('#inc-desc').value = '';
    renderIncidents();
  });

  // Checklist
  function renderChecklist() {
    const checked = getStore(CHECKLIST_KEY, []);
    container.querySelector('#cl-list').innerHTML = CHECKLIST_ITEMS.map((item, i) => `
      <div class="sf-check-row">
        <input type="checkbox" id="cl-${i}" ${checked.includes(i) ? 'checked' : ''}>
        <label class="sf-check-label" for="cl-${i}">${item}</label>
      </div>
    `).join('');
    container.querySelector('#cl-count').textContent = `${checked.length}/${CHECKLIST_ITEMS.length}`;
    container.querySelectorAll('#cl-list input[type="checkbox"]').forEach((cb, i) => {
      cb.addEventListener('change', () => {
        let checked = getStore(CHECKLIST_KEY, []);
        if (cb.checked) { if (!checked.includes(i)) checked.push(i); }
        else { checked = checked.filter(x => x !== i); }
        setStore(CHECKLIST_KEY, checked);
        container.querySelector('#cl-count').textContent = `${checked.length}/${CHECKLIST_ITEMS.length}`;
      });
    });
  }

  container.querySelector('#cl-reset-btn').addEventListener('click', () => {
    setStore(CHECKLIST_KEY, []);
    renderChecklist();
  });

  // Certifications
  function renderCerts() {
    const certs = getStore(CERT_KEY, []);
    const today = new Date().toISOString().split('T')[0];
    container.querySelector('#cert-list').innerHTML = certs.map((c, i) => {
      const expired = c.expiry && c.expiry < today;
      return `<tr style="${expired ? 'color:#ef4444' : ''}">
        <td>${esc(c.name)}</td><td>${esc(c.type)}</td>
        <td>${c.expiry || 'N/A'}${expired ? ' (EXPIRED)' : ''}</td>
        <td><button class="sf-del-btn" data-idx="${i}" data-store="cert">X</button></td>
      </tr>`;
    }).join('');
    bindDeletes('cert', CERT_KEY, renderCerts);
  }

  container.querySelector('#cert-add-btn').addEventListener('click', () => {
    const name = container.querySelector('#cert-name').value.trim();
    const type = container.querySelector('#cert-type').value;
    const expiry = container.querySelector('#cert-expiry').value;
    if (!name) return;
    const certs = getStore(CERT_KEY, []);
    certs.push({ name, type, expiry, id: Date.now() });
    setStore(CERT_KEY, certs);
    container.querySelector('#cert-name').value = '';
    container.querySelector('#cert-expiry').value = '';
    renderCerts();
  });

  function bindDeletes(prefix, key, renderFn) {
    container.querySelectorAll(`[data-store="${prefix}"]`).forEach(btn => {
      btn.addEventListener('click', () => {
        const items = getStore(key, []);
        items.splice(parseInt(btn.dataset.idx), 1);
        setStore(key, items);
        renderFn();
      });
    });
  }

  function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  renderJSA();
  renderIncidents();
  renderChecklist();
  renderCerts();
}

export const meta = { id: 'safety', name: 'Safety Center', icon: '\uD83D\uDEE1\uFE0F', navLabel: 'Safety' };
