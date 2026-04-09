export function render(container, context) {
  const STORE_KEY = 'revv_dailylog';
  const getEntries = () => JSON.parse(localStorage.getItem(STORE_KEY) || '{}');
  const saveEntries = (e) => localStorage.setItem(STORE_KEY, JSON.stringify(e));

  const WEATHER_OPTIONS = ['Sunny', 'Partly Cloudy', 'Cloudy', 'Rain', 'Snow', 'Windy', 'Fog', 'Extreme Heat'];
  const WEATHER_ICONS = { Sunny: '\u2600\uFE0F', 'Partly Cloudy': '\u26C5', Cloudy: '\u2601\uFE0F', Rain: '\uD83C\uDF27\uFE0F', Snow: '\u2744\uFE0F', Windy: '\uD83D\uDCA8', Fog: '\uD83C\uDF2B\uFE0F', 'Extreme Heat': '\uD83D\uDD25' };

  const DEFAULT_CREW = ['Mike R.', 'Dave L.', 'Sarah K.', 'Tom B.', 'Chris M.', 'Jake P.', 'Ana G.', 'Luis H.'];

  container.innerHTML = `
    <style>
      .dl-wrap { max-width: 640px; margin: 0 auto; padding: 16px; font-family: -apple-system, system-ui, sans-serif; color: var(--text-primary, #e0e0e0); }
      .dl-card { background: var(--bg-secondary, #1e1e2e); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
      .dl-label { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary, #888); margin-bottom: 6px; display: block; }
      .dl-input, .dl-select, .dl-textarea { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 0.9rem; margin-bottom: 14px; box-sizing: border-box; min-height: 48px; }
      .dl-textarea { min-height: 100px; resize: vertical; font-family: inherit; }
      .dl-btn { padding: 14px 20px; border: none; border-radius: 12px; background: var(--accent, #60a5fa); color: #fff; font-weight: 700; cursor: pointer; min-height: 48px; font-size: 0.9rem; }
      .dl-btn.full { width: 100%; }
      .dl-btn.secondary { background: var(--bg-primary, #12121a); color: var(--text-secondary, #888); border: 1px solid var(--border, #333); }
      .dl-date-nav { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
      .dl-date-nav button { background: var(--bg-secondary, #1e1e2e); color: var(--text-primary, #e0e0e0); border: 1px solid var(--border, #333); border-radius: 8px; padding: 10px 16px; cursor: pointer; min-height: 48px; font-size: 1rem; }
      .dl-date-display { flex: 1; text-align: center; font-weight: 700; font-size: 1.1rem; }
      .dl-crew-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; margin-bottom: 14px; }
      .dl-crew-item { display: flex; align-items: center; gap: 8px; padding: 10px 12px; background: var(--bg-primary, #12121a); border-radius: 8px; cursor: pointer; transition: background 0.15s; }
      .dl-crew-item.checked { background: rgba(34, 197, 94, 0.15); border: 1px solid #22c55e; }
      .dl-crew-item input { width: 20px; height: 20px; cursor: pointer; }
      .dl-crew-name { font-size: 0.9rem; }
      .dl-section-title { font-size: 1rem; font-weight: 700; margin-bottom: 12px; }
      .dl-weather-display { display: inline-block; padding: 6px 14px; border-radius: 8px; background: var(--bg-primary, #12121a); font-size: 1rem; margin-bottom: 12px; }
      .dl-saved-badge { display: inline-block; padding: 4px 12px; border-radius: 6px; background: #22c55e; color: #fff; font-size: 0.8rem; font-weight: 600; margin-left: 8px; opacity: 0; transition: opacity 0.3s; }
      .dl-saved-badge.show { opacity: 1; }
      .dl-history { margin-top: 8px; }
      .dl-history-item { background: var(--bg-primary, #12121a); border-radius: 8px; padding: 12px; margin-bottom: 8px; cursor: pointer; }
      .dl-history-item:hover { outline: 1px solid var(--accent, #60a5fa); }
      .dl-history-date { font-weight: 600; font-size: 0.9rem; }
      .dl-history-preview { font-size: 0.8rem; color: var(--text-secondary, #888); margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    </style>
    <div class="dl-wrap">
      <div class="dl-card">
        <div class="dl-date-nav">
          <button id="dl-prev">&larr;</button>
          <div class="dl-date-display" id="dl-date-display"></div>
          <button id="dl-next">&rarr;</button>
        </div>
      </div>

      <div class="dl-card">
        <div class="dl-section-title">Weather</div>
        <select class="dl-select" id="dl-weather">
          ${WEATHER_OPTIONS.map(w => `<option value="${w}">${WEATHER_ICONS[w] || ''} ${w}</option>`).join('')}
        </select>
      </div>

      <div class="dl-card">
        <div class="dl-section-title">Crew Present</div>
        <div class="dl-crew-grid" id="dl-crew-grid">
          ${DEFAULT_CREW.map((name, i) => `
            <div class="dl-crew-item" data-idx="${i}">
              <input type="checkbox" id="dl-crew-${i}">
              <label class="dl-crew-name" for="dl-crew-${i}">${name}</label>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="dl-card">
        <div class="dl-section-title">Work Accomplished</div>
        <textarea class="dl-textarea" id="dl-work" placeholder="Describe work completed today..."></textarea>
        <div class="dl-section-title">Notes</div>
        <textarea class="dl-textarea" id="dl-notes" placeholder="Additional notes, issues, delays..."></textarea>
      </div>

      <button class="dl-btn full" id="dl-save-btn">Save Daily Log</button>
      <span class="dl-saved-badge" id="dl-saved-badge">Saved!</span>

      <div class="dl-card" style="margin-top:16px;">
        <div class="dl-section-title">Recent Logs</div>
        <div class="dl-history" id="dl-history"></div>
      </div>
    </div>
  `;

  let currentDate = new Date().toISOString().split('T')[0];

  const dateDisplay = container.querySelector('#dl-date-display');
  const weatherSel = container.querySelector('#dl-weather');
  const workArea = container.querySelector('#dl-work');
  const notesArea = container.querySelector('#dl-notes');
  const savedBadge = container.querySelector('#dl-saved-badge');

  function fmtDate(iso) {
    const d = new Date(iso + 'T12:00:00');
    return d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  }

  function loadDate(dateStr) {
    currentDate = dateStr;
    dateDisplay.textContent = fmtDate(dateStr);
    const entries = getEntries();
    const entry = entries[dateStr] || {};
    weatherSel.value = entry.weather || 'Sunny';
    workArea.value = entry.work || '';
    notesArea.value = entry.notes || '';
    const crewPresent = entry.crew || [];
    container.querySelectorAll('.dl-crew-item').forEach((item, i) => {
      const cb = item.querySelector('input');
      cb.checked = crewPresent.includes(i);
      item.classList.toggle('checked', cb.checked);
    });
    renderHistory();
  }

  function saveLog() {
    const entries = getEntries();
    const crewPresent = [];
    container.querySelectorAll('.dl-crew-item input').forEach((cb, i) => {
      if (cb.checked) crewPresent.push(i);
    });
    entries[currentDate] = {
      weather: weatherSel.value,
      crew: crewPresent,
      work: workArea.value,
      notes: notesArea.value,
      savedAt: new Date().toISOString()
    };
    saveEntries(entries);
    savedBadge.classList.add('show');
    setTimeout(() => savedBadge.classList.remove('show'), 2000);
    renderHistory();
  }

  function renderHistory() {
    const entries = getEntries();
    const dates = Object.keys(entries).sort().reverse().slice(0, 7);
    container.querySelector('#dl-history').innerHTML = dates.length === 0
      ? '<div style="color:var(--text-secondary,#888);font-size:0.85rem;">No logs saved yet.</div>'
      : dates.map(d => `
        <div class="dl-history-item" data-date="${d}">
          <div class="dl-history-date">${fmtDate(d)}</div>
          <div class="dl-history-preview">${WEATHER_ICONS[entries[d].weather] || ''} ${entries[d].weather} | ${entries[d].work ? entries[d].work.slice(0, 60) + '...' : 'No work notes'}</div>
        </div>
      `).join('');
    container.querySelectorAll('.dl-history-item').forEach(item => {
      item.addEventListener('click', () => loadDate(item.dataset.date));
    });
  }

  // Crew item click toggles
  container.querySelectorAll('.dl-crew-item').forEach(item => {
    item.addEventListener('click', (e) => {
      if (e.target.tagName === 'INPUT') return;
      const cb = item.querySelector('input');
      cb.checked = !cb.checked;
      item.classList.toggle('checked', cb.checked);
    });
    item.querySelector('input').addEventListener('change', () => {
      item.classList.toggle('checked', item.querySelector('input').checked);
    });
  });

  container.querySelector('#dl-prev').addEventListener('click', () => {
    const d = new Date(currentDate + 'T12:00:00');
    d.setDate(d.getDate() - 1);
    loadDate(d.toISOString().split('T')[0]);
  });

  container.querySelector('#dl-next').addEventListener('click', () => {
    const d = new Date(currentDate + 'T12:00:00');
    d.setDate(d.getDate() + 1);
    loadDate(d.toISOString().split('T')[0]);
  });

  container.querySelector('#dl-save-btn').addEventListener('click', saveLog);

  loadDate(currentDate);
}

export const meta = { id: 'dailylog', name: 'Daily Log', icon: '\uD83D\uDCD3', navLabel: 'Daily Log' };
