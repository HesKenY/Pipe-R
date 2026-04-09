export function render(container, context) {
  const EQUIP_KEY = 'cherp_mro_equipment';
  const WO_KEY = 'cherp_mro_workorders';
  const getStore = (k, def) => JSON.parse(localStorage.getItem(k) || JSON.stringify(def));
  const setStore = (k, v) => localStorage.setItem(k, JSON.stringify(v));

  const STATUSES = ['Operational', 'Needs Service', 'Out of Service', 'Retired'];
  const STATUS_COLORS = { Operational: '#22c55e', 'Needs Service': '#f59e0b', 'Out of Service': '#ef4444', Retired: '#6b7280' };
  const TYPES = ['Heavy Equipment', 'Power Tools', 'Hand Tools', 'Vehicles', 'Safety Equipment', 'HVAC', 'Electrical', 'Plumbing', 'Other'];
  const WO_PRIORITIES = ['Low', 'Medium', 'High', 'Emergency'];
  const WO_PRI_COLORS = { Low: '#22c55e', Medium: '#f59e0b', High: '#f97316', Emergency: '#ef4444' };

  container.innerHTML = `
    <style>
      .mro-wrap { max-width: 800px; margin: 0 auto; padding: 16px; font-family: -apple-system, system-ui, sans-serif; color: var(--text-primary, #e0e0e0); }
      .mro-tabs { display: flex; gap: 4px; margin-bottom: 16px; }
      .mro-tab { flex: 1; padding: 14px 8px; border: none; border-radius: 12px 12px 0 0; font-size: 0.85rem; font-weight: 600; cursor: pointer; min-height: 48px; background: var(--bg-secondary, #1e1e2e); color: var(--text-secondary, #888); }
      .mro-tab.active { background: var(--accent, #60a5fa); color: #fff; }
      .mro-card { background: var(--bg-secondary, #1e1e2e); border-radius: 0 0 12px 12px; padding: 20px; margin-bottom: 16px; }
      .mro-panel { display: none; }
      .mro-panel.active { display: block; }
      .mro-label { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary, #888); margin-bottom: 6px; display: block; }
      .mro-input, .mro-select, .mro-textarea { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 0.9rem; margin-bottom: 12px; box-sizing: border-box; min-height: 48px; }
      .mro-textarea { min-height: 80px; resize: vertical; font-family: inherit; }
      .mro-btn { padding: 14px 20px; border: none; border-radius: 12px; background: var(--accent, #60a5fa); color: #fff; font-weight: 700; cursor: pointer; min-height: 48px; font-size: 0.9rem; }
      .mro-btn.full { width: 100%; }
      .mro-row { display: flex; gap: 12px; }
      .mro-row > * { flex: 1; }
      @media (max-width: 500px) { .mro-row { flex-direction: column; } }
      .mro-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
      .mro-table th { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border, #333); color: var(--text-secondary, #888); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }
      .mro-table td { padding: 10px 8px; border-bottom: 1px solid var(--border, #222); }
      .mro-badge { padding: 3px 10px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; color: #fff; display: inline-block; }
      .mro-del-btn { background: transparent; border: 1px solid #ef4444; color: #ef4444; border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 0.75rem; min-height: 32px; }
      .mro-section-title { font-size: 1rem; font-weight: 700; margin-bottom: 14px; }
      .mro-stat-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
      .mro-stat { flex: 1; min-width: 100px; background: var(--bg-primary, #12121a); border-radius: 8px; padding: 12px; text-align: center; }
      .mro-stat-num { font-size: 1.5rem; font-weight: 700; }
      .mro-stat-label { font-size: 0.7rem; color: var(--text-secondary, #888); text-transform: uppercase; margin-top: 4px; }
    </style>
    <div class="mro-wrap">
      <div class="mro-tabs">
        <button class="mro-tab active" data-tab="equipment">Equipment</button>
        <button class="mro-tab" data-tab="workorders">Work Orders</button>
      </div>
      <div class="mro-card">
        <!-- EQUIPMENT -->
        <div class="mro-panel active" id="mro-equipment">
          <div class="mro-stat-row" id="mro-stats"></div>
          <div class="mro-section-title">Add Equipment</div>
          <div class="mro-row">
            <div><label class="mro-label">Equipment Name</label><input class="mro-input" id="eq-name" placeholder="e.g., CAT 320 Excavator"></div>
            <div><label class="mro-label">Type</label>
              <select class="mro-select" id="eq-type">${TYPES.map(t => `<option>${t}</option>`).join('')}</select>
            </div>
          </div>
          <div class="mro-row">
            <div><label class="mro-label">Status</label>
              <select class="mro-select" id="eq-status">${STATUSES.map(s => `<option>${s}</option>`).join('')}</select>
            </div>
            <div><label class="mro-label">Last Service Date</label>
              <input class="mro-input" type="date" id="eq-service">
            </div>
          </div>
          <button class="mro-btn full" id="eq-add-btn">+ Add Equipment</button>
          <div style="overflow-x:auto; margin-top:16px;">
            <table class="mro-table">
              <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Last Service</th><th></th></tr></thead>
              <tbody id="eq-list"></tbody>
            </table>
          </div>
        </div>

        <!-- WORK ORDERS -->
        <div class="mro-panel" id="mro-workorders">
          <div class="mro-section-title">Create Work Order</div>
          <label class="mro-label">Equipment</label>
          <select class="mro-select" id="wo-equip"></select>
          <label class="mro-label">Issue Description</label>
          <textarea class="mro-textarea" id="wo-issue" placeholder="Describe the issue..."></textarea>
          <div class="mro-row">
            <div><label class="mro-label">Priority</label>
              <select class="mro-select" id="wo-priority">${WO_PRIORITIES.map(p => `<option>${p}</option>`).join('')}</select>
            </div>
            <div><label class="mro-label">Requested By</label>
              <input class="mro-input" id="wo-requester" placeholder="Your name">
            </div>
          </div>
          <button class="mro-btn full" id="wo-add-btn">Submit Work Order</button>
          <div style="overflow-x:auto; margin-top:16px;">
            <table class="mro-table">
              <thead><tr><th>Equipment</th><th>Issue</th><th>Priority</th><th>Date</th><th></th></tr></thead>
              <tbody id="wo-list"></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  `;

  // Tab switching
  container.querySelectorAll('.mro-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      container.querySelectorAll('.mro-tab').forEach(t => t.classList.remove('active'));
      container.querySelectorAll('.mro-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      container.querySelector(`#mro-${tab.dataset.tab}`).classList.add('active');
      if (tab.dataset.tab === 'workorders') populateEquipDropdown();
    });
  });

  function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function renderStats() {
    const equip = getStore(EQUIP_KEY, []);
    const counts = {};
    STATUSES.forEach(s => counts[s] = 0);
    equip.forEach(e => { if (counts[e.status] !== undefined) counts[e.status]++; });
    container.querySelector('#mro-stats').innerHTML = STATUSES.map(s => `
      <div class="mro-stat">
        <div class="mro-stat-num" style="color:${STATUS_COLORS[s]}">${counts[s]}</div>
        <div class="mro-stat-label">${s}</div>
      </div>
    `).join('');
  }

  function renderEquipment() {
    const equip = getStore(EQUIP_KEY, []);
    container.querySelector('#eq-list').innerHTML = equip.map((e, i) => `
      <tr>
        <td>${esc(e.name)}</td>
        <td>${esc(e.type)}</td>
        <td><span class="mro-badge" style="background:${STATUS_COLORS[e.status] || '#888'}">${e.status}</span></td>
        <td>${e.lastService || 'N/A'}</td>
        <td><button class="mro-del-btn" data-idx="${i}" data-store="eq">X</button></td>
      </tr>
    `).join('');
    container.querySelectorAll('[data-store="eq"]').forEach(btn => {
      btn.addEventListener('click', () => {
        const items = getStore(EQUIP_KEY, []);
        items.splice(parseInt(btn.dataset.idx), 1);
        setStore(EQUIP_KEY, items);
        renderEquipment();
        renderStats();
      });
    });
    renderStats();
  }

  function populateEquipDropdown() {
    const equip = getStore(EQUIP_KEY, []);
    container.querySelector('#wo-equip').innerHTML = equip.length === 0
      ? '<option>No equipment added yet</option>'
      : equip.map(e => `<option value="${esc(e.name)}">${esc(e.name)}</option>`).join('');
  }

  function renderWorkOrders() {
    const orders = getStore(WO_KEY, []);
    container.querySelector('#wo-list').innerHTML = orders.map((o, i) => `
      <tr>
        <td>${esc(o.equipment)}</td>
        <td>${esc(o.issue.length > 40 ? o.issue.slice(0, 40) + '...' : o.issue)}</td>
        <td><span class="mro-badge" style="background:${WO_PRI_COLORS[o.priority] || '#888'}">${o.priority}</span></td>
        <td>${o.date}</td>
        <td><button class="mro-del-btn" data-idx="${i}" data-store="wo">X</button></td>
      </tr>
    `).join('');
    container.querySelectorAll('[data-store="wo"]').forEach(btn => {
      btn.addEventListener('click', () => {
        const items = getStore(WO_KEY, []);
        items.splice(parseInt(btn.dataset.idx), 1);
        setStore(WO_KEY, items);
        renderWorkOrders();
      });
    });
  }

  container.querySelector('#eq-add-btn').addEventListener('click', () => {
    const name = container.querySelector('#eq-name').value.trim();
    if (!name) return;
    const equip = getStore(EQUIP_KEY, []);
    equip.push({
      id: Date.now(), name,
      type: container.querySelector('#eq-type').value,
      status: container.querySelector('#eq-status').value,
      lastService: container.querySelector('#eq-service').value || null
    });
    setStore(EQUIP_KEY, equip);
    container.querySelector('#eq-name').value = '';
    container.querySelector('#eq-service').value = '';
    renderEquipment();
  });

  container.querySelector('#wo-add-btn').addEventListener('click', () => {
    const issue = container.querySelector('#wo-issue').value.trim();
    if (!issue) return;
    const orders = getStore(WO_KEY, []);
    orders.push({
      id: Date.now(),
      equipment: container.querySelector('#wo-equip').value,
      issue,
      priority: container.querySelector('#wo-priority').value,
      requester: container.querySelector('#wo-requester').value.trim(),
      date: new Date().toISOString().split('T')[0]
    });
    setStore(WO_KEY, orders);
    container.querySelector('#wo-issue').value = '';
    container.querySelector('#wo-requester').value = '';
    renderWorkOrders();
  });

  renderEquipment();
  renderWorkOrders();
  populateEquipDropdown();
}

export const meta = { id: 'mro', name: 'MRO Tracker', icon: '\uD83D\uDD27', navLabel: 'MRO' };
