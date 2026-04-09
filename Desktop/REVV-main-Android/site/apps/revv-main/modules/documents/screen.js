export function render(container, context) {
  const STORE_KEY = 'cherp_documents';
  const getStore = () => JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
  const setStore = (v) => localStorage.setItem(STORE_KEY, JSON.stringify(v));

  const CATEGORIES = ['Safety Docs', 'Employee Records', 'Permits', 'Manuals'];
  const CAT_ICONS = { 'Safety Docs': '\uD83D\uDEE1\uFE0F', 'Employee Records': '\uD83D\uDC64', Permits: '\uD83D\uDCC4', Manuals: '\uD83D\uDCD8' };
  const CAT_COLORS = { 'Safety Docs': '#22c55e', 'Employee Records': '#60a5fa', Permits: '#f59e0b', Manuals: '#a78bfa' };

  // Seed sample docs
  if (!localStorage.getItem(STORE_KEY)) {
    setStore([
      { id: 1, name: 'OSHA 300 Log 2026', category: 'Safety Docs', description: 'Annual injury and illness log', uploadDate: '2026-01-15', size: '245 KB' },
      { id: 2, name: 'Fire Watch Permit - Building C', category: 'Permits', description: 'Hot work permit for welding operations', uploadDate: '2026-04-01', size: '128 KB' },
      { id: 3, name: 'Crane Operation Manual', category: 'Manuals', description: 'Liebherr LTM 1100 operator manual', uploadDate: '2025-11-20', size: '4.2 MB' },
      { id: 4, name: 'New Hire Packet Template', category: 'Employee Records', description: 'W4, I9, emergency contacts, union enrollment', uploadDate: '2026-03-10', size: '512 KB' },
      { id: 5, name: 'Confined Space Entry SOP', category: 'Safety Docs', description: 'Standard operating procedure for confined spaces', uploadDate: '2026-02-28', size: '320 KB' },
      { id: 6, name: 'Building Permit #2026-0412', category: 'Permits', description: 'City permit for mechanical room renovation', uploadDate: '2026-04-05', size: '89 KB' }
    ]);
  }

  container.innerHTML = `
    <style>
      .doc-wrap { max-width: 800px; margin: 0 auto; padding: 16px; font-family: -apple-system, system-ui, sans-serif; color: var(--text-primary, #e0e0e0); }
      .doc-card { background: var(--bg-secondary, #1e1e2e); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
      .doc-label { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary, #888); margin-bottom: 6px; display: block; }
      .doc-input, .doc-select, .doc-textarea { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 0.9rem; margin-bottom: 12px; box-sizing: border-box; min-height: 48px; }
      .doc-textarea { min-height: 60px; resize: vertical; font-family: inherit; }
      .doc-btn { padding: 14px 20px; border: none; border-radius: 12px; background: var(--accent, #60a5fa); color: #fff; font-weight: 700; cursor: pointer; min-height: 48px; font-size: 0.9rem; }
      .doc-btn.full { width: 100%; }
      .doc-btn.sm { padding: 8px 14px; min-height: 36px; font-size: 0.8rem; border-radius: 8px; }
      .doc-btn.outline { background: transparent; border: 1px solid var(--accent, #60a5fa); color: var(--accent, #60a5fa); }
      .doc-row { display: flex; gap: 12px; }
      .doc-row > * { flex: 1; }
      @media (max-width: 500px) { .doc-row { flex-direction: column; } }
      .doc-search-row { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
      .doc-search { flex: 1; min-width: 180px; padding: 12px; border-radius: 8px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 0.9rem; min-height: 48px; box-sizing: border-box; }
      .doc-filter-btn { padding: 10px 16px; border: 1px solid var(--border, #333); border-radius: 8px; background: var(--bg-primary, #12121a); color: var(--text-secondary, #888); cursor: pointer; font-size: 0.8rem; font-weight: 600; min-height: 48px; }
      .doc-filter-btn.active { border-color: var(--accent, #60a5fa); color: var(--accent, #60a5fa); background: rgba(96, 165, 250, 0.1); }
      .doc-list { display: flex; flex-direction: column; gap: 8px; }
      .doc-item { background: var(--bg-primary, #12121a); border-radius: 8px; padding: 14px 16px; display: flex; align-items: center; gap: 14px; transition: outline 0.15s; }
      .doc-item:hover { outline: 1px solid var(--border, #333); }
      .doc-item-icon { font-size: 1.6rem; min-width: 36px; text-align: center; }
      .doc-item-info { flex: 1; min-width: 0; }
      .doc-item-name { font-weight: 600; font-size: 0.9rem; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .doc-item-desc { font-size: 0.8rem; color: var(--text-secondary, #888); margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .doc-item-meta { display: flex; gap: 12px; font-size: 0.7rem; color: var(--text-secondary, #666); }
      .doc-cat-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; color: #fff; }
      .doc-item-actions { display: flex; gap: 6px; flex-shrink: 0; }
      .doc-del-btn { background: transparent; border: 1px solid #ef4444; color: #ef4444; border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 0.75rem; min-height: 32px; }
      .doc-section-title { font-size: 1rem; font-weight: 700; margin-bottom: 14px; }
      .doc-count { color: var(--text-secondary, #888); font-size: 0.85rem; font-weight: 400; }
      .doc-empty { text-align: center; padding: 40px; color: var(--text-secondary, #888); font-size: 0.9rem; }
    </style>
    <div class="doc-wrap">
      <div class="doc-card">
        <div class="doc-section-title">Upload Document</div>
        <div class="doc-row">
          <div><label class="doc-label">File Name</label><input class="doc-input" id="doc-name" placeholder="e.g., Safety_Plan_2026.pdf"></div>
          <div><label class="doc-label">Category</label>
            <select class="doc-select" id="doc-cat">${CATEGORIES.map(c => `<option>${c}</option>`).join('')}</select>
          </div>
        </div>
        <label class="doc-label">Description</label>
        <textarea class="doc-textarea" id="doc-desc" placeholder="Brief description of this document..."></textarea>
        <button class="doc-btn full" id="doc-upload-btn">Upload Document</button>
      </div>

      <div class="doc-card">
        <div class="doc-search-row">
          <input class="doc-search" id="doc-search" placeholder="Search documents...">
          <button class="doc-filter-btn active" data-cat="all">All</button>
          ${CATEGORIES.map(c => `<button class="doc-filter-btn" data-cat="${c}">${c}</button>`).join('')}
        </div>
        <div class="doc-section-title">Documents <span class="doc-count" id="doc-count"></span></div>
        <div class="doc-list" id="doc-list"></div>
      </div>
    </div>
  `;

  let activeFilter = 'all';

  function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  function renderDocs() {
    const docs = getStore();
    const search = (container.querySelector('#doc-search').value || '').toLowerCase();
    let filtered = docs;
    if (activeFilter !== 'all') filtered = filtered.filter(d => d.category === activeFilter);
    if (search) filtered = filtered.filter(d => d.name.toLowerCase().includes(search) || d.description.toLowerCase().includes(search));

    container.querySelector('#doc-count').textContent = `(${filtered.length})`;

    if (filtered.length === 0) {
      container.querySelector('#doc-list').innerHTML = '<div class="doc-empty">No documents found.</div>';
      return;
    }

    container.querySelector('#doc-list').innerHTML = filtered.map((doc) => `
      <div class="doc-item">
        <div class="doc-item-icon">${CAT_ICONS[doc.category] || '\uD83D\uDCC4'}</div>
        <div class="doc-item-info">
          <div class="doc-item-name">${esc(doc.name)}</div>
          <div class="doc-item-desc">${esc(doc.description)}</div>
          <div class="doc-item-meta">
            <span class="doc-cat-badge" style="background:${CAT_COLORS[doc.category] || '#888'}">${doc.category}</span>
            <span>${doc.uploadDate}</span>
            <span>${doc.size || '--'}</span>
          </div>
        </div>
        <div class="doc-item-actions">
          <button class="doc-btn sm outline" data-view="${doc.id}">View</button>
          <button class="doc-del-btn" data-del="${doc.id}">X</button>
        </div>
      </div>
    `).join('');

    container.querySelectorAll('[data-view]').forEach(btn => {
      btn.addEventListener('click', () => {
        const doc = getStore().find(d => d.id === parseInt(btn.dataset.view));
        if (doc) alert(`Document: ${doc.name}\n\nCategory: ${doc.category}\nDescription: ${doc.description}\nUploaded: ${doc.uploadDate}\nSize: ${doc.size || 'N/A'}\n\n(In production, this would open the file viewer.)`);
      });
    });

    container.querySelectorAll('[data-del]').forEach(btn => {
      btn.addEventListener('click', () => {
        if (!confirm('Delete this document?')) return;
        let docs = getStore();
        docs = docs.filter(d => d.id !== parseInt(btn.dataset.del));
        setStore(docs);
        renderDocs();
      });
    });
  }

  // Upload
  container.querySelector('#doc-upload-btn').addEventListener('click', () => {
    const name = container.querySelector('#doc-name').value.trim();
    if (!name) return;
    const docs = getStore();
    docs.push({
      id: Date.now(),
      name,
      category: container.querySelector('#doc-cat').value,
      description: container.querySelector('#doc-desc').value.trim(),
      uploadDate: new Date().toISOString().split('T')[0],
      size: Math.floor(Math.random() * 900 + 50) + ' KB'
    });
    setStore(docs);
    container.querySelector('#doc-name').value = '';
    container.querySelector('#doc-desc').value = '';
    renderDocs();
  });

  // Filter buttons
  container.querySelectorAll('.doc-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.doc-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.dataset.cat;
      renderDocs();
    });
  });

  // Search
  container.querySelector('#doc-search').addEventListener('input', renderDocs);

  renderDocs();
}

export const meta = { id: 'documents', name: 'Documents', icon: '\uD83D\uDCC1', navLabel: 'Documents' };
