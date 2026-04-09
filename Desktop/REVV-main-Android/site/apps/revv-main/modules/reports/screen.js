export function render(container, context) {
  container.innerHTML = `
    <style>
      .rpt-wrap { max-width: 800px; margin: 0 auto; padding: 16px; font-family: -apple-system, system-ui, sans-serif; color: var(--text-primary, #e0e0e0); }
      .rpt-card { background: var(--bg-secondary, #1e1e2e); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
      .rpt-label { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary, #888); margin-bottom: 6px; display: block; }
      .rpt-input, .rpt-select { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 0.9rem; margin-bottom: 14px; box-sizing: border-box; min-height: 48px; }
      .rpt-btn { padding: 14px 20px; border: none; border-radius: 12px; background: var(--accent, #60a5fa); color: #fff; font-weight: 700; cursor: pointer; min-height: 48px; font-size: 0.9rem; }
      .rpt-btn.full { width: 100%; }
      .rpt-btn.print { background: #22c55e; margin-top: 12px; }
      .rpt-btn.secondary { background: var(--bg-primary, #12121a); color: var(--text-secondary, #888); border: 1px solid var(--border, #333); }
      .rpt-row { display: flex; gap: 12px; }
      .rpt-row > * { flex: 1; }
      @media (max-width: 500px) { .rpt-row { flex-direction: column; } }
      .rpt-section-title { font-size: 1rem; font-weight: 700; margin-bottom: 14px; }
      .rpt-type-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; margin-bottom: 16px; }
      .rpt-type-btn { padding: 16px 12px; border: 2px solid var(--border, #333); border-radius: 12px; background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); cursor: pointer; text-align: center; transition: all 0.15s; min-height: 48px; }
      .rpt-type-btn.active { border-color: var(--accent, #60a5fa); background: rgba(96, 165, 250, 0.1); }
      .rpt-type-icon { font-size: 1.5rem; margin-bottom: 6px; }
      .rpt-type-label { font-size: 0.8rem; font-weight: 600; }
      .rpt-output { background: var(--bg-primary, #12121a); border-radius: 8px; padding: 20px; margin-top: 16px; line-height: 1.6; }
      .rpt-output h2 { font-size: 1.2rem; margin: 0 0 4px 0; color: var(--accent, #60a5fa); }
      .rpt-output h3 { font-size: 1rem; margin: 16px 0 8px 0; color: var(--text-primary, #e0e0e0); border-bottom: 1px solid var(--border, #333); padding-bottom: 4px; }
      .rpt-output table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 8px 0; }
      .rpt-output th { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border, #333); color: var(--text-secondary, #888); font-size: 0.75rem; text-transform: uppercase; }
      .rpt-output td { padding: 6px 8px; border-bottom: 1px solid var(--border, #222); }
      .rpt-output .rpt-meta { font-size: 0.8rem; color: var(--text-secondary, #888); margin-bottom: 12px; }
      .rpt-output .rpt-stat { display: inline-block; background: var(--bg-secondary, #1e1e2e); padding: 8px 14px; border-radius: 8px; margin: 4px; text-align: center; }
      .rpt-output .rpt-stat-val { font-size: 1.2rem; font-weight: 700; color: var(--accent, #60a5fa); }
      .rpt-output .rpt-stat-label { font-size: 0.7rem; color: var(--text-secondary, #888); }
      .rpt-empty { text-align: center; padding: 40px; color: var(--text-secondary, #888); }

      @media print {
        .rpt-wrap > .rpt-card:first-child { display: none; }
        .rpt-btn.print { display: none; }
        .rpt-output { background: #fff; color: #000; border: 1px solid #ccc; }
        .rpt-output h2 { color: #333; }
        .rpt-output h3 { color: #333; }
        .rpt-output th, .rpt-output td { border-color: #ccc; color: #333; }
      }
    </style>
    <div class="rpt-wrap">
      <div class="rpt-card">
        <div class="rpt-section-title">Generate Report</div>
        <div class="rpt-type-grid">
          <div class="rpt-type-btn active" data-type="daily">
            <div class="rpt-type-icon">\uD83D\uDCCB</div>
            <div class="rpt-type-label">Daily Summary</div>
          </div>
          <div class="rpt-type-btn" data-type="weekly">
            <div class="rpt-type-icon">\uD83D\uDCC5</div>
            <div class="rpt-type-label">Weekly</div>
          </div>
          <div class="rpt-type-btn" data-type="timecard">
            <div class="rpt-type-icon">\u23F0</div>
            <div class="rpt-type-label">Timecard</div>
          </div>
          <div class="rpt-type-btn" data-type="safety">
            <div class="rpt-type-icon">\uD83D\uDEE1\uFE0F</div>
            <div class="rpt-type-label">Safety</div>
          </div>
          <div class="rpt-type-btn" data-type="mro">
            <div class="rpt-type-icon">\uD83D\uDD27</div>
            <div class="rpt-type-label">MRO</div>
          </div>
        </div>
        <div class="rpt-row">
          <div><label class="rpt-label">Start Date</label><input class="rpt-input" type="date" id="rpt-start"></div>
          <div><label class="rpt-label">End Date</label><input class="rpt-input" type="date" id="rpt-end"></div>
        </div>
        <button class="rpt-btn full" id="rpt-generate">Generate Report</button>
      </div>

      <div id="rpt-output-wrap"></div>
    </div>
  `;

  let selectedType = 'daily';

  // Set default dates
  const today = new Date();
  const weekAgo = new Date(today);
  weekAgo.setDate(today.getDate() - 7);
  container.querySelector('#rpt-start').value = weekAgo.toISOString().split('T')[0];
  container.querySelector('#rpt-end').value = today.toISOString().split('T')[0];

  // Report type selection
  container.querySelectorAll('.rpt-type-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.rpt-type-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedType = btn.dataset.type;
    });
  });

  function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }

  function fmtDate(iso) {
    if (!iso) return 'N/A';
    return new Date(iso + 'T12:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  }

  function generateDaily(startDate, endDate) {
    const logs = JSON.parse(localStorage.getItem('revv_dailylog') || '{}');
    const dates = Object.keys(logs).filter(d => d >= startDate && d <= endDate).sort();
    const CREW_NAMES = ['Mike R.', 'Dave L.', 'Sarah K.', 'Tom B.', 'Chris M.', 'Jake P.', 'Ana G.', 'Luis H.'];

    if (dates.length === 0) return '<div class="rpt-empty">No daily logs found for this date range.</div>';

    let html = `<h2>Daily Summary Report</h2>
      <div class="rpt-meta">Period: ${fmtDate(startDate)} to ${fmtDate(endDate)} | ${dates.length} day(s) logged</div>`;

    dates.forEach(d => {
      const entry = logs[d];
      const crewNames = (entry.crew || []).map(i => CREW_NAMES[i] || `Worker ${i}`);
      html += `
        <h3>${fmtDate(d)} - ${entry.weather || 'N/A'}</h3>
        <p><strong>Crew (${crewNames.length}):</strong> ${crewNames.join(', ') || 'None recorded'}</p>
        <p><strong>Work:</strong> ${esc(entry.work) || 'No notes'}</p>
        ${entry.notes ? `<p><strong>Notes:</strong> ${esc(entry.notes)}</p>` : ''}
      `;
    });
    return html;
  }

  function generateWeekly(startDate, endDate) {
    const logs = JSON.parse(localStorage.getItem('revv_dailylog') || '{}');
    const punches = JSON.parse(localStorage.getItem('revv_timeclock_punches') || '[]');
    const incidents = JSON.parse(localStorage.getItem('revv_safety_incidents') || '[]');
    const workorders = JSON.parse(localStorage.getItem('revv_mro_workorders') || '[]');

    const logDates = Object.keys(logs).filter(d => d >= startDate && d <= endDate);
    const rangePunches = punches.filter(p => p.date >= startDate && p.date <= endDate);
    const rangeIncidents = incidents.filter(i => i.date >= startDate && i.date <= endDate);
    const rangeWO = workorders.filter(w => w.date >= startDate && w.date <= endDate);

    let totalHours = 0;
    rangePunches.forEach(p => {
      if (p.clockIn && p.clockOut) {
        totalHours += (new Date(p.clockOut) - new Date(p.clockIn)) / 3600000;
      }
    });

    return `
      <h2>Weekly Report</h2>
      <div class="rpt-meta">Period: ${fmtDate(startDate)} to ${fmtDate(endDate)}</div>
      <div style="margin:12px 0;">
        <span class="rpt-stat"><div class="rpt-stat-val">${logDates.length}</div><div class="rpt-stat-label">Days Logged</div></span>
        <span class="rpt-stat"><div class="rpt-stat-val">${totalHours.toFixed(1)}</div><div class="rpt-stat-label">Total Hours</div></span>
        <span class="rpt-stat"><div class="rpt-stat-val">${rangeIncidents.length}</div><div class="rpt-stat-label">Incidents</div></span>
        <span class="rpt-stat"><div class="rpt-stat-val">${rangeWO.length}</div><div class="rpt-stat-label">Work Orders</div></span>
      </div>
      <h3>Hours Summary</h3>
      <p>Regular: ${Math.min(totalHours, 40).toFixed(1)} hrs | Overtime: ${Math.max(totalHours - 40, 0).toFixed(1)} hrs</p>
      ${rangeIncidents.length > 0 ? `<h3>Incidents</h3><table><thead><tr><th>Date</th><th>Severity</th><th>Location</th></tr></thead><tbody>${rangeIncidents.map(i => `<tr><td>${i.date}</td><td>${i.severity}</td><td>${esc(i.location)}</td></tr>`).join('')}</tbody></table>` : ''}
      ${rangeWO.length > 0 ? `<h3>Work Orders</h3><table><thead><tr><th>Equipment</th><th>Priority</th><th>Date</th></tr></thead><tbody>${rangeWO.map(w => `<tr><td>${esc(w.equipment)}</td><td>${w.priority}</td><td>${w.date}</td></tr>`).join('')}</tbody></table>` : ''}
    `;
  }

  function generateTimecard(startDate, endDate) {
    const punches = JSON.parse(localStorage.getItem('revv_timeclock_punches') || '[]');
    const range = punches.filter(p => p.date >= startDate && p.date <= endDate).sort((a, b) => a.date.localeCompare(b.date));

    if (range.length === 0) return '<div class="rpt-empty">No timecard data found for this date range.</div>';

    let totalHours = 0;
    const rows = range.map(p => {
      const hrs = p.clockIn && p.clockOut ? (new Date(p.clockOut) - new Date(p.clockIn)) / 3600000 : 0;
      totalHours += hrs;
      return `<tr>
        <td>${p.date}</td>
        <td>${p.clockIn ? new Date(p.clockIn).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : '--'}</td>
        <td>${p.clockOut ? new Date(p.clockOut).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }) : 'Active'}</td>
        <td>${hrs.toFixed(2)}</td>
      </tr>`;
    }).join('');

    const regular = Math.min(totalHours, 40);
    const ot = Math.max(totalHours - 40, 0);

    return `
      <h2>Timecard Report</h2>
      <div class="rpt-meta">Period: ${fmtDate(startDate)} to ${fmtDate(endDate)} | ${range.length} punch(es)</div>
      <div style="margin:12px 0;">
        <span class="rpt-stat"><div class="rpt-stat-val">${regular.toFixed(1)}</div><div class="rpt-stat-label">Regular Hrs</div></span>
        <span class="rpt-stat"><div class="rpt-stat-val">${ot.toFixed(1)}</div><div class="rpt-stat-label">Overtime Hrs</div></span>
        <span class="rpt-stat"><div class="rpt-stat-val">${totalHours.toFixed(1)}</div><div class="rpt-stat-label">Total Hrs</div></span>
      </div>
      <table>
        <thead><tr><th>Date</th><th>Clock In</th><th>Clock Out</th><th>Hours</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  function generateSafety(startDate, endDate) {
    const incidents = JSON.parse(localStorage.getItem('revv_safety_incidents') || '[]');
    const jsa = JSON.parse(localStorage.getItem('revv_safety_jsa') || '[]');
    const certs = JSON.parse(localStorage.getItem('revv_safety_certs') || '[]');
    const checklist = JSON.parse(localStorage.getItem('revv_safety_checklist') || '[]');

    const rangeInc = incidents.filter(i => i.date >= startDate && i.date <= endDate);
    const today = new Date().toISOString().split('T')[0];
    const expiredCerts = certs.filter(c => c.expiry && c.expiry < today);

    return `
      <h2>Safety Report</h2>
      <div class="rpt-meta">Period: ${fmtDate(startDate)} to ${fmtDate(endDate)}</div>
      <div style="margin:12px 0;">
        <span class="rpt-stat"><div class="rpt-stat-val">${rangeInc.length}</div><div class="rpt-stat-label">Incidents</div></span>
        <span class="rpt-stat"><div class="rpt-stat-val">${jsa.length}</div><div class="rpt-stat-label">JSA Pairs</div></span>
        <span class="rpt-stat"><div class="rpt-stat-val">${certs.length}</div><div class="rpt-stat-label">Certifications</div></span>
        <span class="rpt-stat"><div class="rpt-stat-val">${checklist.length}/10</div><div class="rpt-stat-label">Checklist Done</div></span>
      </div>
      ${rangeInc.length > 0 ? `
        <h3>Incident Reports</h3>
        <table><thead><tr><th>Date</th><th>Severity</th><th>Location</th><th>Description</th></tr></thead><tbody>
        ${rangeInc.map(i => `<tr><td>${i.date}</td><td>${i.severity}</td><td>${esc(i.location)}</td><td>${esc(i.description)}</td></tr>`).join('')}
        </tbody></table>` : '<p>No incidents reported in this period.</p>'}
      ${jsa.length > 0 ? `
        <h3>Active JSA Items</h3>
        <table><thead><tr><th>Hazard</th><th>Control Measure</th></tr></thead><tbody>
        ${jsa.map(j => `<tr><td>${esc(j.hazard)}</td><td>${esc(j.control)}</td></tr>`).join('')}
        </tbody></table>` : ''}
      ${expiredCerts.length > 0 ? `
        <h3 style="color:#ef4444;">Expired Certifications (${expiredCerts.length})</h3>
        <table><thead><tr><th>Name</th><th>Type</th><th>Expired</th></tr></thead><tbody>
        ${expiredCerts.map(c => `<tr><td>${esc(c.name)}</td><td>${esc(c.type)}</td><td>${c.expiry}</td></tr>`).join('')}
        </tbody></table>` : ''}
    `;
  }

  function generateMRO(startDate, endDate) {
    const equipment = JSON.parse(localStorage.getItem('revv_mro_equipment') || '[]');
    const workorders = JSON.parse(localStorage.getItem('revv_mro_workorders') || '[]');
    const rangeWO = workorders.filter(w => w.date >= startDate && w.date <= endDate);

    const statusCounts = {};
    equipment.forEach(e => { statusCounts[e.status] = (statusCounts[e.status] || 0) + 1; });

    return `
      <h2>MRO Report</h2>
      <div class="rpt-meta">Period: ${fmtDate(startDate)} to ${fmtDate(endDate)}</div>
      <div style="margin:12px 0;">
        <span class="rpt-stat"><div class="rpt-stat-val">${equipment.length}</div><div class="rpt-stat-label">Total Equipment</div></span>
        <span class="rpt-stat"><div class="rpt-stat-val">${statusCounts['Operational'] || 0}</div><div class="rpt-stat-label">Operational</div></span>
        <span class="rpt-stat"><div class="rpt-stat-val">${statusCounts['Needs Service'] || 0}</div><div class="rpt-stat-label">Needs Service</div></span>
        <span class="rpt-stat"><div class="rpt-stat-val">${rangeWO.length}</div><div class="rpt-stat-label">Work Orders</div></span>
      </div>
      ${equipment.length > 0 ? `
        <h3>Equipment Status</h3>
        <table><thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Last Service</th></tr></thead><tbody>
        ${equipment.map(e => `<tr><td>${esc(e.name)}</td><td>${esc(e.type)}</td><td>${e.status}</td><td>${e.lastService || 'N/A'}</td></tr>`).join('')}
        </tbody></table>` : '<p>No equipment tracked.</p>'}
      ${rangeWO.length > 0 ? `
        <h3>Work Orders</h3>
        <table><thead><tr><th>Equipment</th><th>Issue</th><th>Priority</th><th>Requested By</th><th>Date</th></tr></thead><tbody>
        ${rangeWO.map(w => `<tr><td>${esc(w.equipment)}</td><td>${esc(w.issue)}</td><td>${w.priority}</td><td>${esc(w.requester)}</td><td>${w.date}</td></tr>`).join('')}
        </tbody></table>` : '<p>No work orders in this period.</p>'}
    `;
  }

  // Generate report
  container.querySelector('#rpt-generate').addEventListener('click', () => {
    const startDate = container.querySelector('#rpt-start').value;
    const endDate = container.querySelector('#rpt-end').value;
    if (!startDate || !endDate) { alert('Please select a date range.'); return; }

    let html = '';
    switch (selectedType) {
      case 'daily': html = generateDaily(startDate, endDate); break;
      case 'weekly': html = generateWeekly(startDate, endDate); break;
      case 'timecard': html = generateTimecard(startDate, endDate); break;
      case 'safety': html = generateSafety(startDate, endDate); break;
      case 'mro': html = generateMRO(startDate, endDate); break;
    }

    container.querySelector('#rpt-output-wrap').innerHTML = `
      <div class="rpt-card">
        <div class="rpt-output">${html}</div>
        <button class="rpt-btn full print" id="rpt-print-btn">Print Report</button>
      </div>
    `;

    container.querySelector('#rpt-print-btn').addEventListener('click', () => {
      window.print();
    });
  });
}

export const meta = { id: 'reports', name: 'Reports', icon: '\uD83D\uDCCA', navLabel: 'Reports' };
