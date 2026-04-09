export function render(container, context) {
  const ITEMS_KEY = 'revv_inventory_items';
  const LOG_KEY = 'revv_inventory_log';
  const getStore = (k, def) => JSON.parse(localStorage.getItem(k) || JSON.stringify(def));
  const setStore = (k, v) => localStorage.setItem(k, JSON.stringify(v));

  const UNITS = ['each', 'ft', 'lbs', 'gallons', 'boxes', 'rolls', 'bags', 'sheets', 'bundles', 'pairs'];
  const LOCATIONS = ['Warehouse A', 'Warehouse B', 'Job Trailer', 'Lay-Down Yard', 'Van Stock', 'Shop'];

  container.innerHTML = `
    <style>
      .inv-wrap { max-width: 800px; margin: 0 auto; padding: 16px; font-family: -apple-system, system-ui, sans-serif; color: var(--text-primary, #e0e0e0); }
      .inv-tabs { display: flex; gap: 4px; margin-bottom: 16px; }
      .inv-tab { flex: 1; padding: 14px 8px; border: none; border-radius: 12px 12px 0 0; font-size: 0.85rem; font-weight: 600; cursor: pointer; min-height: 48px; background: var(--bg-secondary, #1e1e2e); color: var(--text-secondary, #888); }
      .inv-tab.active { background: var(--accent, #60a5fa); color: #fff; }
      .inv-card { background: var(--bg-secondary, #1e1e2e); border-radius: 0 0 12px 12px; padding: 20px; margin-bottom: 16px; }
      .inv-panel { display: none; }
      .inv-panel.active { display: block; }
      .inv-label { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary, #888); margin-bottom: 6px; display: block; }
      .inv-input, .inv-select { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 0.9rem; margin-bottom: 12px; box-sizing: border-box; min-height: 48px; }
      .inv-btn { padding: 14px 20px; border: none; border-radius: 12px; background: var(--accent, #60a5fa); color: #fff; font-weight: 700; cursor: pointer; min-height: 48px; font-size: 0.9rem; }
      .inv-btn.full { width: 100%; }
      .inv-btn.checkout { background: #f59e0b; }
      .inv-btn.return { background: #22c55e; }
      .inv-row { display: flex; gap: 12px; }
      .inv-row > * { flex: 1; }
      @media (max-width: 500px) { .inv-row { flex-direction: column; } }
      .inv-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
      .inv-table th { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border, #333); color: var(--text-secondary, #888); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }
      .inv-table td { padding: 10px 8px; border-bottom: 1px solid var(--border, #222); }
      .inv-del-btn { background: transparent; border: 1px solid #ef4444; color: #ef4444; border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 0.75rem; min-height: 32px; }
      .inv-low { color: #ef4444; font-weight: 600; }
      .inv-ok { color: #22c55e; }
      .inv-section-title { font-size: 1rem; font-weight: 700; margin-bottom: 14px; }
      .inv-alert { background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; border-radius: 8px; padding: 12px; margin-bottom: 16px; }
      .inv-alert-title { font-weight: 700; color: #ef4444; font-size: 0.9rem; margin-bottom: 8px; }
      .inv-alert-item { font-size: 0.85rem; padding: 4px 0; }
      .inv-log-entry { background: var(--bg-primary, #12121a); border-radius: 8px; padding: 10px 12px; margin-bottom: 6px; font-size: 0.85rem; display: flex; justify-content: space-between; }
      .inv-log-type { font-weight: 600; }
      .inv-log-type.out { color: #f59e0b; }
      .inv-log-type.in { color: #22c55e; }
      .inv-search { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 0.9rem; margin-bottom: 16px; box-sizing: border-box; min-height: 48px; }
    </style>
    <div class="inv-wrap">
      <div class="inv-tabs">
        <button class="inv-tab active" data-tab="items">Inventory</button>
        <button class="inv-tab" data-tab="checkout">Checkout/Return</button>
        <button class="inv-tab" data-tab="log">Activity Log</button>
      </div>
      <div class="inv-card">
        <!-- INVENTORY LIST -->
        <div class="inv-panel active" id="inv-items">
          <div id="inv-alerts"></div>
          <input class="inv-search" id="inv-search" placeholder="Search materials...">
          <div class="inv-section-title">Add Material</div>
          <div class="inv-row">
            <div><label class="inv-label">Material Name</label><input class="inv-input" id="it-name" placeholder="e.g., 2\" Copper 90s"></div>
            <div><label class="inv-label">Quantity</label><input class="inv-input" type="number" id="it-qty" value="0" min="0"></div>
          </div>
          <div class="inv-row">
            <div><label class="inv-label">Unit</label><select class="inv-select" id="it-unit">${UNITS.map(u => `<option>${u}</option>`).join('')}</select></div>
            <div><label class="inv-label">Location</label><select class="inv-select" id="it-loc">${LOCATIONS.map(l => `<option>${l}</option>`).join('')}</select></div>
          </div>
          <label class="inv-label">Reorder Point</label>
          <input class="inv-input" type="number" id="it-reorder" value="10" min="0">
          <button class="inv-btn full" id="it-add-btn">+ Add Material</button>
          <div style="overflow-x:auto; margin-top:16px;">
            <table class="inv-table">
              <thead><tr><th>Material</th><th>Qty</th><th>Unit</th><th>Location</th><th>Status</th><th></th></tr></thead>
              <tbody id="it-list"></tbody>
            </table>
          </div>
        </div>

        <!-- CHECKOUT/RETURN -->
        <div class="inv-panel" id="inv-checkout">
          <div class="inv-section-title">Checkout Material</div>
          <label class="inv-label">Material</label>
          <select class="inv-select" id="co-item"></select>
          <div class="inv-row">
            <div><label class="inv-label">Checked Out By</label><input class="inv-input" id="co-who" placeholder="Name"></div>
            <div><label class="inv-label">Quantity</label><input class="inv-input" type="number" id="co-qty" value="1" min="1"></div>
          </div>
          <button class="inv-btn full checkout" id="co-out-btn">Checkout</button>
          <div style="height:16px;"></div>
          <div class="inv-section-title">Return Material</div>
          <label class="inv-label">Material</label>
          <select class="inv-select" id="ret-item"></select>
          <div class="inv-row">
            <div><label class="inv-label">Returned By</label><input class="inv-input" id="ret-who" placeholder="Name"></div>
            <div><label class="inv-label">Quantity</label><input class="inv-input" type="number" id="ret-qty" value="1" min="1"></div>
          </div>
          <button class="inv-btn full return" id="ret-in-btn">Return</button>
        </div>

        <!-- ACTIVITY LOG -->
        <div class="inv-panel" id="inv-log">
          <div class="inv-section-title">Recent Activity</div>
          <div id="inv-log-list"></div>
        </div>
      </div>
    </div>
  `;

  // Tab switching
  container.querySelectorAll('.inv-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      container.querySelectorAll('.inv-tab').forEach(t => t.classList.remove('active'));
      container.querySelectorAll('.inv-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      container.querySelector(`#inv-${tab.dataset.tab}`).classList.add('active');
      if (tab.dataset.tab === 'checkout') populateDropdowns();
      if (tab.dataset.tab === 'log') renderLog();
    });
  });

  function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function renderAlerts() {
    const items = getStore(ITEMS_KEY, []);
    const low = items.filter(i => i.quantity <= i.reorderPoint);
    const alertsEl = container.querySelector('#inv-alerts');
    if (low.length === 0) { alertsEl.innerHTML = ''; return; }
    alertsEl.innerHTML = `
      <div class="inv-alert">
        <div class="inv-alert-title">Low Stock Warnings (${low.length})</div>
        ${low.map(i => `<div class="inv-alert-item">${esc(i.name)}: ${i.quantity} ${i.unit} (reorder at ${i.reorderPoint})</div>`).join('')}
      </div>
    `;
  }

  function renderItems() {
    const items = getStore(ITEMS_KEY, []);
    const search = (container.querySelector('#inv-search').value || '').toLowerCase();
    const filtered = search ? items.filter(i => i.name.toLowerCase().includes(search)) : items;
    container.querySelector('#it-list').innerHTML = filtered.map((it, i) => {
      const isLow = it.quantity <= it.reorderPoint;
      const origIdx = items.indexOf(it);
      return `<tr>
        <td>${esc(it.name)}</td>
        <td class="${isLow ? 'inv-low' : 'inv-ok'}">${it.quantity}</td>
        <td>${it.unit}</td>
        <td>${esc(it.location)}</td>
        <td>${isLow ? '<span class="inv-low">LOW</span>' : '<span class="inv-ok">OK</span>'}</td>
        <td><button class="inv-del-btn" data-idx="${origIdx}">X</button></td>
      </tr>`;
    }).join('');
    container.querySelectorAll('.inv-del-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const items = getStore(ITEMS_KEY, []);
        items.splice(parseInt(btn.dataset.idx), 1);
        setStore(ITEMS_KEY, items);
        renderItems();
        renderAlerts();
      });
    });
    renderAlerts();
  }

  function populateDropdowns() {
    const items = getStore(ITEMS_KEY, []);
    const opts = items.length === 0
      ? '<option>No items in inventory</option>'
      : items.map((it, i) => `<option value="${i}">${esc(it.name)} (${it.quantity} ${it.unit})</option>`).join('');
    container.querySelector('#co-item').innerHTML = opts;
    container.querySelector('#ret-item').innerHTML = opts;
  }

  function addLog(type, who, itemName, qty) {
    const log = getStore(LOG_KEY, []);
    log.unshift({ type, who, item: itemName, qty, time: new Date().toISOString() });
    if (log.length > 50) log.length = 50;
    setStore(LOG_KEY, log);
  }

  function renderLog() {
    const log = getStore(LOG_KEY, []);
    container.querySelector('#inv-log-list').innerHTML = log.length === 0
      ? '<div style="color:var(--text-secondary,#888);font-size:0.85rem;">No activity yet.</div>'
      : log.map(l => `
        <div class="inv-log-entry">
          <div><span class="inv-log-type ${l.type === 'checkout' ? 'out' : 'in'}">${l.type === 'checkout' ? 'OUT' : 'IN'}</span> ${esc(l.item)} x${l.qty} - ${esc(l.who)}</div>
          <div style="color:var(--text-secondary,#888);font-size:0.75rem;">${new Date(l.time).toLocaleString()}</div>
        </div>
      `).join('');
  }

  container.querySelector('#it-add-btn').addEventListener('click', () => {
    const name = container.querySelector('#it-name').value.trim();
    if (!name) return;
    const items = getStore(ITEMS_KEY, []);
    items.push({
      id: Date.now(), name,
      quantity: parseInt(container.querySelector('#it-qty').value) || 0,
      unit: container.querySelector('#it-unit').value,
      location: container.querySelector('#it-loc').value,
      reorderPoint: parseInt(container.querySelector('#it-reorder').value) || 0
    });
    setStore(ITEMS_KEY, items);
    container.querySelector('#it-name').value = '';
    container.querySelector('#it-qty').value = '0';
    renderItems();
  });

  container.querySelector('#co-out-btn').addEventListener('click', () => {
    const items = getStore(ITEMS_KEY, []);
    const idx = parseInt(container.querySelector('#co-item').value);
    const who = container.querySelector('#co-who').value.trim();
    const qty = parseInt(container.querySelector('#co-qty').value) || 0;
    if (isNaN(idx) || !items[idx] || !who || qty <= 0) return;
    if (items[idx].quantity < qty) { alert('Not enough stock!'); return; }
    items[idx].quantity -= qty;
    setStore(ITEMS_KEY, items);
    addLog('checkout', who, items[idx].name, qty);
    container.querySelector('#co-who').value = '';
    container.querySelector('#co-qty').value = '1';
    populateDropdowns();
    renderItems();
  });

  container.querySelector('#ret-in-btn').addEventListener('click', () => {
    const items = getStore(ITEMS_KEY, []);
    const idx = parseInt(container.querySelector('#ret-item').value);
    const who = container.querySelector('#ret-who').value.trim();
    const qty = parseInt(container.querySelector('#ret-qty').value) || 0;
    if (isNaN(idx) || !items[idx] || !who || qty <= 0) return;
    items[idx].quantity += qty;
    setStore(ITEMS_KEY, items);
    addLog('return', who, items[idx].name, qty);
    container.querySelector('#ret-who').value = '';
    container.querySelector('#ret-qty').value = '1';
    populateDropdowns();
    renderItems();
  });

  container.querySelector('#inv-search').addEventListener('input', renderItems);

  renderItems();
}

export const meta = { id: 'inventory', name: 'Inventory', icon: '\uD83D\uDCE6', navLabel: 'Inventory' };
