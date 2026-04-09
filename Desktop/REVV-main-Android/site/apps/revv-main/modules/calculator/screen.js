export function render(container, context) {
  container.innerHTML = `
    <style>
      .calc-wrap { max-width: 600px; margin: 0 auto; padding: 16px; font-family: -apple-system, system-ui, sans-serif; color: var(--text-primary, #e0e0e0); }
      .calc-tabs { display: flex; gap: 4px; margin-bottom: 16px; }
      .calc-tab { flex: 1; padding: 14px 8px; border: none; border-radius: 12px 12px 0 0; font-size: 0.85rem; font-weight: 600; cursor: pointer; min-height: 48px; background: var(--bg-secondary, #1e1e2e); color: var(--text-secondary, #888); transition: all 0.2s; }
      .calc-tab.active { background: var(--accent, #60a5fa); color: #fff; }
      .calc-card { background: var(--bg-secondary, #1e1e2e); border-radius: 0 0 12px 12px; padding: 20px; margin-bottom: 16px; }
      .calc-panel { display: none; }
      .calc-panel.active { display: block; }
      .calc-label { font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary, #888); margin-bottom: 6px; display: block; }
      .calc-input, .calc-select { width: 100%; padding: 12px; border-radius: 8px; border: 1px solid var(--border, #333); background: var(--bg-primary, #12121a); color: var(--text-primary, #e0e0e0); font-size: 1rem; margin-bottom: 14px; box-sizing: border-box; min-height: 48px; }
      .calc-btn { width: 100%; padding: 14px; border: none; border-radius: 12px; background: var(--accent, #60a5fa); color: #fff; font-size: 1rem; font-weight: 700; cursor: pointer; min-height: 48px; margin-bottom: 12px; }
      .calc-btn:hover { opacity: 0.9; }
      .calc-result { background: var(--bg-primary, #12121a); border-radius: 8px; padding: 16px; }
      .calc-result-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 0.95rem; }
      .calc-result-val { font-weight: 700; color: var(--accent, #60a5fa); }
      .calc-row { display: flex; gap: 12px; }
      .calc-row > * { flex: 1; }
      .calc-section-title { font-size: 1rem; font-weight: 700; margin-bottom: 14px; }
    </style>
    <div class="calc-wrap">
      <div class="calc-tabs">
        <button class="calc-tab active" data-tab="pipe">Pipe Weight</button>
        <button class="calc-tab" data-tab="concrete">Concrete</button>
        <button class="calc-tab" data-tab="material">Materials</button>
      </div>
      <div class="calc-card">
        <!-- PIPE WEIGHT -->
        <div class="calc-panel active" id="calc-pipe">
          <div class="calc-section-title">Pipe Weight Calculator</div>
          <label class="calc-label">Nominal Diameter</label>
          <select class="calc-select" id="pipe-diameter">
            <option value="0.5">1/2"</option><option value="0.75">3/4"</option>
            <option value="1">1"</option><option value="1.25">1-1/4"</option>
            <option value="1.5">1-1/2"</option><option value="2" selected>2"</option>
            <option value="2.5">2-1/2"</option><option value="3">3"</option>
            <option value="4">4"</option><option value="6">6"</option>
            <option value="8">8"</option><option value="10">10"</option>
            <option value="12">12"</option><option value="14">14"</option>
            <option value="16">16"</option><option value="18">18"</option>
            <option value="20">20"</option><option value="24">24"</option>
          </select>
          <label class="calc-label">Schedule</label>
          <select class="calc-select" id="pipe-schedule">
            <option value="10">Schedule 10</option>
            <option value="40" selected>Schedule 40</option>
            <option value="80">Schedule 80</option>
          </select>
          <label class="calc-label">Length (feet)</label>
          <input class="calc-input" type="number" id="pipe-length" value="20" min="0" step="0.1">
          <button class="calc-btn" id="pipe-calc-btn">Calculate Weight</button>
          <div class="calc-result" id="pipe-result"></div>
        </div>

        <!-- CONCRETE -->
        <div class="calc-panel" id="calc-concrete">
          <div class="calc-section-title">Concrete Volume Calculator</div>
          <label class="calc-label">Length (feet)</label>
          <input class="calc-input" type="number" id="conc-length" value="10" min="0" step="0.1">
          <label class="calc-label">Width (feet)</label>
          <input class="calc-input" type="number" id="conc-width" value="10" min="0" step="0.1">
          <label class="calc-label">Depth (inches)</label>
          <input class="calc-input" type="number" id="conc-depth" value="4" min="0" step="0.5">
          <button class="calc-btn" id="conc-calc-btn">Calculate Volume</button>
          <div class="calc-result" id="conc-result"></div>
        </div>

        <!-- MATERIAL ESTIMATOR -->
        <div class="calc-panel" id="calc-material">
          <div class="calc-section-title">Material Estimator</div>
          <label class="calc-label">Room Square Footage</label>
          <input class="calc-input" type="number" id="mat-sqft" value="200" min="0" step="1">
          <label class="calc-label">Wall Height (feet)</label>
          <input class="calc-input" type="number" id="mat-height" value="8" min="0" step="0.5">
          <button class="calc-btn" id="mat-calc-btn">Estimate Materials</button>
          <div class="calc-result" id="mat-result"></div>
        </div>
      </div>
    </div>
  `;

  // Pipe weight data: lbs per foot by diameter and schedule
  const pipeWeights = {
    '0.5':  { '10': 0.37, '40': 0.85, '80': 1.09 },
    '0.75': { '10': 0.49, '40': 1.13, '80': 1.47 },
    '1':    { '10': 0.65, '40': 1.68, '80': 2.17 },
    '1.25': { '10': 0.88, '40': 2.27, '80': 3.00 },
    '1.5':  { '10': 1.03, '40': 2.72, '80': 3.63 },
    '2':    { '10': 1.36, '40': 3.65, '80': 5.02 },
    '2.5':  { '10': 1.83, '40': 5.79, '80': 7.66 },
    '3':    { '10': 2.46, '40': 7.58, '80': 10.25 },
    '4':    { '10': 3.47, '40': 10.79, '80': 14.98 },
    '6':    { '10': 5.37, '40': 18.97, '80': 28.57 },
    '8':    { '10': 8.40, '40': 28.55, '80': 43.39 },
    '10':   { '10': 11.51, '40': 40.48, '80': 54.74 },
    '12':   { '10': 14.58, '40': 49.56, '80': 65.42 },
    '14':   { '10': 16.05, '40': 54.57, '80': 72.09 },
    '16':   { '10': 18.65, '40': 62.58, '80': 82.77 },
    '18':   { '10': 20.78, '40': 70.59, '80': 93.45 },
    '20':   { '10': 23.12, '40': 78.60, '80': 104.13 },
    '24':   { '10': 27.83, '40': 94.62, '80': 125.49 }
  };

  // Tab switching
  container.querySelectorAll('.calc-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      container.querySelectorAll('.calc-tab').forEach(t => t.classList.remove('active'));
      container.querySelectorAll('.calc-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      container.querySelector(`#calc-${tab.dataset.tab}`).classList.add('active');
    });
  });

  // Pipe calc
  container.querySelector('#pipe-calc-btn').addEventListener('click', () => {
    const dia = container.querySelector('#pipe-diameter').value;
    const sch = container.querySelector('#pipe-schedule').value;
    const len = parseFloat(container.querySelector('#pipe-length').value) || 0;
    const perFoot = pipeWeights[dia]?.[sch] || 0;
    const total = perFoot * len;
    container.querySelector('#pipe-result').innerHTML = `
      <div class="calc-result-row"><span>Weight per Foot</span><span class="calc-result-val">${perFoot.toFixed(2)} lbs/ft</span></div>
      <div class="calc-result-row"><span>Total Weight</span><span class="calc-result-val">${total.toFixed(2)} lbs</span></div>
      <div class="calc-result-row"><span>Total Weight</span><span class="calc-result-val">${(total / 2000).toFixed(3)} tons</span></div>
    `;
  });

  // Concrete calc
  container.querySelector('#conc-calc-btn').addEventListener('click', () => {
    const l = parseFloat(container.querySelector('#conc-length').value) || 0;
    const w = parseFloat(container.querySelector('#conc-width').value) || 0;
    const d = parseFloat(container.querySelector('#conc-depth').value) || 0;
    const cubicFt = l * w * (d / 12);
    const cubicYards = cubicFt / 27;
    const bags80 = Math.ceil(cubicFt / 0.6); // 80lb bag = ~0.6 cu ft
    const bags60 = Math.ceil(cubicFt / 0.45);
    container.querySelector('#conc-result').innerHTML = `
      <div class="calc-result-row"><span>Cubic Feet</span><span class="calc-result-val">${cubicFt.toFixed(2)} ft3</span></div>
      <div class="calc-result-row"><span>Cubic Yards</span><span class="calc-result-val">${cubicYards.toFixed(2)} yd3</span></div>
      <div class="calc-result-row"><span>80lb Bags</span><span class="calc-result-val">${bags80}</span></div>
      <div class="calc-result-row"><span>60lb Bags</span><span class="calc-result-val">${bags60}</span></div>
    `;
  });

  // Material estimator
  container.querySelector('#mat-calc-btn').addEventListener('click', () => {
    const sqft = parseFloat(container.querySelector('#mat-sqft').value) || 0;
    const height = parseFloat(container.querySelector('#mat-height').value) || 8;
    const perimeter = Math.sqrt(sqft) * 4; // approximate square room
    const wallArea = perimeter * height;
    const drywallSheets = Math.ceil(wallArea / 32); // 4x8 sheet = 32 sqft
    const studs = Math.ceil(perimeter / 1.333); // stud every 16"
    const insulationRolls = Math.ceil(wallArea / 40); // ~40 sqft per roll
    const paintGallons = Math.ceil(wallArea / 350); // 350 sqft per gallon
    const ceilingSheets = Math.ceil(sqft / 32);
    container.querySelector('#mat-result').innerHTML = `
      <div class="calc-result-row"><span>Wall Area (est.)</span><span class="calc-result-val">${wallArea.toFixed(0)} sqft</span></div>
      <div class="calc-result-row"><span>Drywall Sheets (walls)</span><span class="calc-result-val">${drywallSheets}</span></div>
      <div class="calc-result-row"><span>Drywall Sheets (ceiling)</span><span class="calc-result-val">${ceilingSheets}</span></div>
      <div class="calc-result-row"><span>Studs (16" OC)</span><span class="calc-result-val">${studs}</span></div>
      <div class="calc-result-row"><span>Insulation Rolls</span><span class="calc-result-val">${insulationRolls}</span></div>
      <div class="calc-result-row"><span>Paint (gallons)</span><span class="calc-result-val">${paintGallons}</span></div>
    `;
  });
}

export const meta = { id: 'calculator', name: 'Trade Calculator', icon: '\uD83E\uDDEE', navLabel: 'Calculator' };
