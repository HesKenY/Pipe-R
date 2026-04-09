export function render(container, context) {
  const STORE_KEY = 'revv_timeclock_punches';
  const getPunches = () => JSON.parse(localStorage.getItem(STORE_KEY) || '[]');
  const savePunches = (p) => localStorage.setItem(STORE_KEY, JSON.stringify(p));

  let timerInterval = null;

  container.innerHTML = `
    <style>
      .tc-wrap { max-width: 600px; margin: 0 auto; padding: 16px; font-family: -apple-system, system-ui, sans-serif; color: var(--text-primary, #e0e0e0); }
      .tc-card { background: var(--bg-secondary, #1e1e2e); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
      .tc-clock-display { text-align: center; font-size: 2.4rem; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--accent, #60a5fa); margin-bottom: 8px; }
      .tc-date { text-align: center; font-size: 0.9rem; color: var(--text-secondary, #888); margin-bottom: 16px; }
      .tc-gps { display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 0.85rem; margin-bottom: 16px; }
      .tc-gps-dot { width: 10px; height: 10px; border-radius: 50%; }
      .tc-gps-dot.active { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
      .tc-gps-dot.inactive { background: #ef4444; }
      .tc-btn-punch { display: block; width: 100%; padding: 20px; border: none; border-radius: 12px; font-size: 1.3rem; font-weight: 700; cursor: pointer; min-height: 64px; transition: background 0.2s; }
      .tc-btn-punch.clock-in { background: #22c55e; color: #fff; }
      .tc-btn-punch.clock-in:hover { background: #16a34a; }
      .tc-btn-punch.clock-out { background: #ef4444; color: #fff; }
      .tc-btn-punch.clock-out:hover { background: #dc2626; }
      .tc-shift-timer { text-align: center; font-size: 1.6rem; font-weight: 600; color: var(--accent, #60a5fa); margin: 12px 0; font-variant-numeric: tabular-nums; }
      .tc-shift-label { text-align: center; font-size: 0.8rem; color: var(--text-secondary, #888); text-transform: uppercase; letter-spacing: 1px; }
      .tc-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
      .tc-table th { text-align: left; padding: 8px; border-bottom: 1px solid var(--border, #333); color: var(--text-secondary, #888); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.5px; }
      .tc-table td { padding: 8px; border-bottom: 1px solid var(--border, #222); }
      .tc-ot { margin-top: 12px; padding: 12px; background: var(--bg-primary, #12121a); border-radius: 8px; }
      .tc-ot-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 0.9rem; }
      .tc-ot-val { font-weight: 600; color: var(--accent, #60a5fa); }
      .tc-section-title { font-size: 1rem; font-weight: 700; margin-bottom: 12px; }
      .tc-clear-btn { background: var(--bg-primary, #12121a); color: var(--text-secondary, #888); border: 1px solid var(--border, #333); border-radius: 8px; padding: 10px 16px; font-size: 0.85rem; cursor: pointer; margin-top: 8px; min-height: 48px; }
    </style>
    <div class="tc-wrap">
      <div class="tc-card">
        <div class="tc-clock-display" id="tc-live-clock"></div>
        <div class="tc-date" id="tc-live-date"></div>
        <div class="tc-gps"><div class="tc-gps-dot inactive" id="tc-gps-dot"></div><span id="tc-gps-text">Checking GPS...</span></div>
        <button class="tc-btn-punch clock-in" id="tc-punch-btn">CLOCK IN</button>
        <div class="tc-shift-label" id="tc-shift-label" style="display:none;">Current Shift</div>
        <div class="tc-shift-timer" id="tc-shift-timer" style="display:none;">00:00:00</div>
      </div>
      <div class="tc-card">
        <div class="tc-section-title">Weekly Timecard</div>
        <table class="tc-table">
          <thead><tr><th>Day</th><th>In</th><th>Out</th><th>Hours</th></tr></thead>
          <tbody id="tc-timecard-body"></tbody>
        </table>
        <div class="tc-ot" id="tc-ot-summary"></div>
        <button class="tc-clear-btn" id="tc-clear-btn">Clear History</button>
      </div>
    </div>
  `;

  const clockEl = container.querySelector('#tc-live-clock');
  const dateEl = container.querySelector('#tc-live-date');
  const gpsDot = container.querySelector('#tc-gps-dot');
  const gpsText = container.querySelector('#tc-gps-text');
  const punchBtn = container.querySelector('#tc-punch-btn');
  const shiftLabel = container.querySelector('#tc-shift-label');
  const shiftTimer = container.querySelector('#tc-shift-timer');
  const tcBody = container.querySelector('#tc-timecard-body');
  const otSummary = container.querySelector('#tc-ot-summary');
  const clearBtn = container.querySelector('#tc-clear-btn');

  function updateClock() {
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    dateEl.textContent = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  }

  function checkGPS() {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        () => { gpsDot.classList.replace('inactive', 'active'); gpsText.textContent = 'GPS Active'; },
        () => { gpsText.textContent = 'GPS Unavailable'; }
      );
    } else {
      gpsText.textContent = 'GPS Not Supported';
    }
  }

  function getOpenPunch() {
    const punches = getPunches();
    return punches.find(p => p.clockIn && !p.clockOut);
  }

  function fmtTime(iso) {
    if (!iso) return '--';
    return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }

  function diffHours(a, b) {
    return ((new Date(b) - new Date(a)) / 3600000).toFixed(2);
  }

  function fmtDuration(ms) {
    const s = Math.floor(ms / 1000);
    const h = String(Math.floor(s / 3600)).padStart(2, '0');
    const m = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
    const sec = String(s % 60).padStart(2, '0');
    return `${h}:${m}:${sec}`;
  }

  function updateShiftTimer() {
    const open = getOpenPunch();
    if (open) {
      const elapsed = Date.now() - new Date(open.clockIn).getTime();
      shiftTimer.textContent = fmtDuration(elapsed);
    }
  }

  function syncUI() {
    const open = getOpenPunch();
    if (open) {
      punchBtn.textContent = 'CLOCK OUT';
      punchBtn.className = 'tc-btn-punch clock-out';
      shiftLabel.style.display = '';
      shiftTimer.style.display = '';
      if (!timerInterval) timerInterval = setInterval(updateShiftTimer, 1000);
      updateShiftTimer();
    } else {
      punchBtn.textContent = 'CLOCK IN';
      punchBtn.className = 'tc-btn-punch clock-in';
      shiftLabel.style.display = 'none';
      shiftTimer.style.display = 'none';
      if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
    }
    renderTimecard();
  }

  function renderTimecard() {
    const punches = getPunches();
    const now = new Date();
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay());
    startOfWeek.setHours(0, 0, 0, 0);

    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    let totalHours = 0;
    let rows = '';

    for (let d = 0; d < 7; d++) {
      const day = new Date(startOfWeek);
      day.setDate(startOfWeek.getDate() + d);
      const dayStr = day.toISOString().split('T')[0];
      const dayPunches = punches.filter(p => p.date === dayStr);
      if (dayPunches.length === 0) {
        rows += `<tr><td>${days[d]}</td><td>--</td><td>--</td><td>0.00</td></tr>`;
      } else {
        dayPunches.forEach((p, i) => {
          const hrs = p.clockOut ? parseFloat(diffHours(p.clockIn, p.clockOut)) : 0;
          totalHours += hrs;
          rows += `<tr><td>${i === 0 ? days[d] : ''}</td><td>${fmtTime(p.clockIn)}</td><td>${fmtTime(p.clockOut)}</td><td>${hrs.toFixed(2)}</td></tr>`;
        });
      }
    }
    tcBody.innerHTML = rows;

    const regular = Math.min(totalHours, 40);
    const overtime = Math.max(totalHours - 40, 0);
    otSummary.innerHTML = `
      <div class="tc-ot-row"><span>Regular Hours</span><span class="tc-ot-val">${regular.toFixed(2)}</span></div>
      <div class="tc-ot-row"><span>Overtime Hours</span><span class="tc-ot-val">${overtime.toFixed(2)}</span></div>
      <div class="tc-ot-row"><span>Total Hours</span><span class="tc-ot-val">${totalHours.toFixed(2)}</span></div>
    `;
  }

  punchBtn.addEventListener('click', () => {
    const punches = getPunches();
    const open = punches.find(p => p.clockIn && !p.clockOut);
    if (open) {
      open.clockOut = new Date().toISOString();
      savePunches(punches);
    } else {
      const now = new Date();
      punches.push({
        id: Date.now(),
        date: now.toISOString().split('T')[0],
        clockIn: now.toISOString(),
        clockOut: null
      });
      savePunches(punches);
    }
    syncUI();
  });

  clearBtn.addEventListener('click', () => {
    if (confirm('Clear all punch history?')) {
      localStorage.removeItem(STORE_KEY);
      syncUI();
    }
  });

  updateClock();
  setInterval(updateClock, 1000);
  checkGPS();
  syncUI();
}

export const meta = { id: 'timeclock', name: 'Time Clock', icon: '\u23F0', navLabel: 'Time Clock' };
